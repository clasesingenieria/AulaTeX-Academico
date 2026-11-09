"""Agente ``navegación-itesca`` / ``navegación-unadm`` (tipo ``navegación-plataforma``) para UnADM.

Se autentica mediante ``PlatformCredentialVault`` de AulaTeX contra
``https://aulavirtual.unadmexico.mx`` en modo estrictamente de solo lectura,
confinado al origen institucional y sanitizando toda salida antes de persistirla.
Jamás expone credenciales, contraseñas, matrículas ni tokens en registros ni archivos generados.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urlsplit

from .navegacion_plataforma import (
    AGENT_TYPE_NAVEGACION_PLATAFORMA,
    MAX_PLATFORM_DOWNLOAD_BYTES,
    PlatformNavigationAgent,
    PlatformNavigationError,
    PlatformSessionSpec,
    assert_no_credential_leak,
    build_identity_variants,
    ensure_same_https_host,
    load_vault_account,
    normalize_readonly_link,
    resolve_doh_host_args,
    sanitize_platform_text,
)
from .workspace import AulaTeXWorkspace

UNADM_HOST = "aulavirtual.unadmexico.mx"
UNADM_BASE_URL = f"https://{UNADM_HOST}"
UNADM_SESSION_SPEC = PlatformSessionSpec(
    institution="UnADM",
    platform="unadmexico",
    host=UNADM_HOST,
    base_url=UNADM_BASE_URL,
    login_url=f"{UNADM_BASE_URL}/login/index.php",
)

AGENT_ID_NAVEGACION_ITESCA = "navegación-itesca"
AGENT_ID_NAVEGACION_UNADM = "navegación-unadm"

COURSES_UNADM: dict[int, tuple[str, str, str]] = {
    3432: ("teoria-del-estado-y-constitucion", "Teoria del Estado y Constitucion", "020"),
    3482: ("derecho-penal-especial-mexicano", "Derecho penal especial mexicano", "020"),
    3441: ("antecedentes-de-los-derechos-humanos", "Antecedentes de los derechos humanos", "005"),
}


@dataclass(frozen=True)
class UnadmModuleTarget:
    module_id: int
    kind: str = "assign"  # assign | forum | resource | folder | page | book | auto
    course_id: int | None = None
    local_activity_number: int | None = None
    subject_slug: str = ""


@dataclass(frozen=True)
class UnadmNavigationRequest:
    inspect_dashboard: bool = True
    course_ids: tuple[int, ...] = (3432, 3482, 3441)
    modules: tuple[UnadmModuleTarget, ...] = ()
    output_dir: str = ""


@dataclass(frozen=True)
class DownloadedUnadmFile:
    source_url: str
    filename: str
    saved_path: str
    sha256: str
    size_bytes: int
    mime_hint: str


@dataclass(frozen=True)
class UnadmNavigationResult:
    run_id: str
    run_dir: Path
    snapshot_path: Path
    manifest_path: Path
    snapshot: dict[str, Any]
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)

    @property
    def agent_id(self) -> str:
        return self.snapshot.get("agent_id", AGENT_ID_NAVEGACION_ITESCA)

    @property
    def courses_discovered(self) -> int:
        return len(self.snapshot.get("courses", {}))

    @property
    def assignments_discovered(self) -> int:
        return sum(len(c.get("assign_modules", [])) for c in self.snapshot.get("courses", {}).values())

    @property
    def forums_discovered(self) -> int:
        return sum(len(c.get("forum_modules", [])) for c in self.snapshot.get("courses", {}).values())

    @property
    def resources_discovered(self) -> int:
        return len(self.snapshot.get("modules", {}))


def _positive_int(value: int, label: str = "id") -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise PlatformNavigationError(f"invalid_{label}")
    return value


def _detect_mime_from_magic(data: bytes, filename: str = "") -> str:
    if data.startswith(b"%PDF-"):
        return "application/pdf"
    if data.startswith(b"PK\x03\x04"):
        lower = filename.lower()
        if lower.endswith(".docx"):
            return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        if lower.endswith(".xlsx"):
            return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        if lower.endswith(".pptx"):
            return "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        return "application/zip"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    head = data[:512].lstrip().lower()
    if head.startswith((b"<!doctype html", b"<html")):
        return "text/html"
    return "application/octet-stream"


class NavegacionUnadmAgent(PlatformNavigationAgent):
    """Agente especializado en navegación de la plataforma UnADM del tipo navegación-plataforma."""

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        agent_id: str = AGENT_ID_NAVEGACION_ITESCA,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        super().__init__(self.workspace.repo_root, UNADM_SESSION_SPEC)
        self._custom_agent_id = agent_id
        self.runs_root = self.workspace.feedback_root / "navegacion-itesca" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    @property
    def agent_id(self) -> str:
        return self._custom_agent_id

    @property
    def courses(self) -> dict[int, tuple[str, str, str]]:
        return COURSES_UNADM

    def _open_authenticated_session(self, playwright: Any) -> tuple[Any, Any, tuple[str, ...], tuple[str, ...], str]:
        credentials = load_vault_account(self.repo_root, "UnADM", UNADM_HOST)
        username = credentials["username"]
        password = credentials["password"]
        forbidden_secrets = (username, password)
        browser_args, dns_mode = resolve_doh_host_args(UNADM_HOST)

        browser = playwright.chromium.launch(headless=True, args=browser_args)
        context = browser.new_context(
            accept_downloads=False,
            service_workers="block",
            viewport={"width": 1440, "height": 1100},
        )
        context.set_default_timeout(30000)
        context.set_default_navigation_timeout(60000)

        def _confine_origin(route: Any) -> None:
            req_url = route.request.url
            try:
                safe_url = ensure_same_https_host(req_url, UNADM_HOST, UNADM_BASE_URL)
            except PlatformNavigationError:
                route.abort()
                return
            lowered = urlsplit(safe_url).path.lower()
            if any(
                blocked in lowered
                for blocked in (
                    "/mod/quiz/startattempt.php",
                    "/mod/quiz/processattempt.php",
                    "/login/logout.php",
                    "/admin/",
                )
            ):
                route.abort()
                return
            route.continue_()

        context.route("**/*", _confine_origin)
        page = context.new_page()
        page.goto(UNADM_SESSION_SPEC.login_url, wait_until="domcontentloaded")
        try:
            page.get_by_role("textbox", name=re.compile("Matr", re.I)).fill(username)
        except Exception:
            page.locator("input[name*='username'], input#username, input[type=text]").fill(username)

        try:
            page.locator("input[type=password]").fill(password)
        except Exception:
            page.locator("input#password").fill(password)

        try:
            page.get_by_role("button", name=re.compile("Inicia sesi|Acceder", re.I)).click()
        except Exception:
            page.locator("button#loginbtn, input#loginbtn, button[type=submit]").click()

        page.wait_for_load_state("domcontentloaded")
        ensure_same_https_host(page.url, UNADM_HOST, UNADM_BASE_URL)
        if "/login/" in urlsplit(page.url).path:
            browser.close()
            raise PlatformNavigationError("unadm_authentication_failed")

        names = page.locator(
            ".usermenu .usertext, .usermenu .userfullname, .logininfo a[href*='/user/profile.php'], .userbutton .usertext"
        ).all_text_contents()
        identities = build_identity_variants(username, names)
        del credentials, username, password
        return browser, page, identities, forbidden_secrets, dns_mode

    def inspect(self, request: UnadmNavigationRequest) -> UnadmNavigationResult:
        from playwright.sync_api import sync_playwright

        run_id = f"{self.workspace.timestamp()}-navegacion-unadm"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir.strip()
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        blockers: list[dict[str, Any]] = []
        dashboard_data: dict[str, Any] = {}
        courses_data: dict[str, Any] = {}
        modules_data: dict[str, Any] = {}

        with sync_playwright() as pw:
            browser, page, identities, forbidden_secrets, dns_mode = self._open_authenticated_session(pw)
            try:
                if request.inspect_dashboard:
                    dashboard_data = self._inspect_dashboard_page(page, identities)

                for raw_cid in dict.fromkeys(request.course_ids):
                    cid = _positive_int(raw_cid, "course_id")
                    course_info = self._inspect_course_page(page, cid, identities, blockers)
                    courses_data[str(cid)] = course_info

                for target in request.modules:
                    mid = _positive_int(target.module_id, "module_id")
                    mod_info = self._inspect_module_page(page, target, identities, blockers)
                    modules_data[str(mid)] = mod_info
            finally:
                browser.close()

        snapshot: dict[str, Any] = {
            "schema_version": "1.0.0",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "institution": "UnADM",
            "host": UNADM_HOST,
            "read_only": True,
            "dns_mode": dns_mode,
            "inspected_at_utc": datetime.now(timezone.utc).isoformat(),
            "dashboard": dashboard_data,
            "courses": courses_data,
            "modules": modules_data,
            "blockers": blockers,
        }
        assert_no_credential_leak(snapshot, forbidden_secrets)

        snapshot_path = run_dir / "snapshot-unadm.json"
        snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        manifest = {
            "run_id": run_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "read_only": True,
            "institution": "UnADM",
            "courses_inspected": sorted(courses_data.keys()),
            "modules_inspected": sorted(modules_data.keys()),
            "blockers_count": len(blockers),
            "snapshot": self.workspace.relative(snapshot_path),
        }
        assert_no_credential_leak(manifest, forbidden_secrets)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.workspace.append_bitacora(run_id, "navegacion-unadm", manifest)

        return UnadmNavigationResult(
            run_id=run_id,
            run_dir=run_dir,
            snapshot_path=snapshot_path,
            manifest_path=manifest_path,
            snapshot=snapshot,
            blockers=tuple(blockers),
        )

    def _inspect_dashboard_page(self, page: Any, identities: tuple[str, ...]) -> dict[str, Any]:
        page.goto(f"{UNADM_BASE_URL}/my/", wait_until="domcontentloaded")
        ensure_same_https_host(page.url, UNADM_HOST, UNADM_BASE_URL)
        title = page.title()
        courses_raw = page.locator(".dashboard-card, .course-info-container, [data-region='course-content'] a[href*='/course/view.php']").evaluate_all(
            """els => els.map(e => ({
                text: e.innerText || '',
                url: e.href || (e.querySelector('a') ? e.querySelector('a').href : '')
            }))"""
        )
        enrolled: list[dict[str, Any]] = []
        for cr in courses_raw:
            url = cr.get("url") or ""
            if "/course/view.php?id=" in url:
                parsed = urlsplit(url)
                enrolled.append({
                    "title": sanitize_platform_text(cr.get("text") or "", identities),
                    "url": normalize_readonly_link(url, UNADM_HOST) or url,
                })
        return {
            "title": sanitize_platform_text(title, identities),
            "enrolled_courses": enrolled[:20],
        }

    def _inspect_course_page(
        self,
        page: Any,
        course_id: int,
        identities: tuple[str, ...],
        blockers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        course_url = f"{UNADM_BASE_URL}/course/view.php?id={course_id}"
        page.goto(course_url, wait_until="domcontentloaded")
        ensure_same_https_host(page.url, UNADM_HOST, UNADM_BASE_URL)
        course_title = page.locator(".page-header-headings h1, .course-header h1, h1").first.text_content() or f"Curso {course_id}"
        
        sections_data: list[dict[str, Any]] = []
        sections = page.locator(".course-section, li.section").all()
        for idx, sec in enumerate(sections, start=1):
            sec_title_nodes = sec.locator(".sectionname, .section-title, h3").all_inner_texts()
            sec_title = sec_title_nodes[0].strip() if sec_title_nodes else f"Sección {idx}"
            full_txt = sec.inner_text()
            links = sec.locator("a[href]").evaluate_all(
                "links => links.map(link => ({title: link.innerText.trim(), url: link.href}))"
            )
            clean_links = []
            for ln in links:
                u = ln.get("url") or ""
                if UNADM_HOST in u:
                    clean_links.append({
                        "title": sanitize_platform_text(ln.get("title") or "", identities),
                        "url": normalize_readonly_link(u, UNADM_HOST) or u,
                    })
            sections_data.append({
                "section_index": idx,
                "title": sanitize_platform_text(sec_title, identities),
                "links_count": len(clean_links),
                "links": clean_links,
                "has_week5": "semana 5" in sec_title.lower() or "semana 5" in full_txt.lower(),
            })

        assign_links = page.locator('a[href*="/mod/assign/view.php"]').evaluate_all(
            "links => links.map(link => ({title: link.innerText.trim(), url: link.href}))"
        )
        forum_links = page.locator('a[href*="/mod/forum/view.php"]').evaluate_all(
            "links => links.map(link => ({title: link.innerText.trim(), url: link.href}))"
        )

        return {
            "course_id": course_id,
            "course_title": sanitize_platform_text(course_title.strip(), identities),
            "url": course_url,
            "sections": sections_data,
            "assign_modules": [
                {"title": sanitize_platform_text(a["title"], identities), "url": normalize_readonly_link(a["url"], UNADM_HOST) or a["url"]}
                for a in assign_links
            ],
            "forum_modules": [
                {"title": sanitize_platform_text(f["title"], identities), "url": normalize_readonly_link(f["url"], UNADM_HOST) or f["url"]}
                for f in forum_links
            ],
        }

    def _inspect_module_page(
        self,
        page: Any,
        target: UnadmModuleTarget,
        identities: tuple[str, ...],
        blockers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        mid = target.module_id
        kind = target.kind if target.kind != "auto" else "assign"
        mod_url = f"{UNADM_BASE_URL}/mod/{kind}/view.php?id={mid}"
        page.goto(mod_url, wait_until="domcontentloaded")
        ensure_same_https_host(page.url, UNADM_HOST, UNADM_BASE_URL)

        main = page.locator("#region-main, [role='main']").first
        if not main.count():
            blockers.append({"module_id": mid, "code": "module_main_region_missing"})
            return {"module_id": mid, "error": "main_region_missing"}

        title_nodes = main.locator("h2, h3, .activity-title").all_inner_texts()
        title = title_nodes[0].strip() if title_nodes else f"Módulo {mid}"

        intro_nodes = main.locator(".activity-description, .generalbox.mod_introbox, #intro, .resourcecontent, .book_content").all_inner_texts()
        intro_text = "\n\n".join(intro_nodes).strip()

        dates_nodes = main.locator(".activity-dates, .activity-information").all_inner_texts()
        dates_text = "\n".join(dates_nodes).strip()

        # Rubric / feedback if assign
        rubric_data: list[dict[str, Any]] = []
        rubric_tables = main.locator(".gradingform_rubric").all()
        for rt in rubric_tables:
            crit_rows = rt.locator(".criterion").all()
            for row in crit_rows:
                description = row.locator(".description").inner_text().strip()
                levels = []
                for lv in row.locator(".level").all():
                    score_txt = lv.locator(".score").inner_text().strip()
                    definition = lv.locator(".definition").inner_text().strip()
                    levels.append({"score": score_txt, "definition": sanitize_platform_text(definition, identities)})
                rubric_data.append({"criterion": sanitize_platform_text(description, identities), "levels": levels})

        # Attachments
        pluginfiles = main.locator('a[href*="pluginfile.php"]').evaluate_all(
            "links => links.map(link => ({title: link.innerText.trim(), url: link.href}))"
        )
        clean_attachments = []
        for pf in pluginfiles:
            u = pf.get("url") or ""
            if UNADM_HOST in u:
                clean_attachments.append({
                    "title": sanitize_platform_text(pf.get("title") or "", identities),
                    "url": normalize_readonly_link(u, UNADM_HOST) or u,
                })

        info = {
            "module_id": mid,
            "kind": kind,
            "course_id": target.course_id,
            "local_activity_number": target.local_activity_number,
            "subject_slug": target.subject_slug,
            "title": sanitize_platform_text(title, identities),
            "url": normalize_readonly_link(mod_url, UNADM_HOST) or mod_url,
            "intro_text": sanitize_platform_text(intro_text, identities),
            "activity_dates": sanitize_platform_text(dates_text, identities),
            "rubric": rubric_data,
            "attachments": clean_attachments,
            "full_main_text": sanitize_platform_text(main.inner_text(), identities),
        }
        return info

    def download_resources(
        self,
        items: list[dict[str, Any]],
        destination_dir: Path,
    ) -> list[DownloadedUnadmFile]:
        """Descarga recursos autenticados dentro de UnADM en modo estrictamente de solo lectura."""
        if not items:
            return []
        from playwright.sync_api import sync_playwright

        destination_dir.mkdir(parents=True, exist_ok=True)
        downloaded: list[DownloadedUnadmFile] = []

        with sync_playwright() as pw:
            browser, page, identities, forbidden_secrets, _dns_mode = self._open_authenticated_session(pw)
            try:
                for spec in items:
                    raw_url = str(spec.get("url") or "").strip()
                    prefix = str(spec.get("prefix") or "").strip()
                    safe_url = ensure_same_https_host(raw_url, UNADM_HOST, UNADM_BASE_URL)
                    raw_bytes, final_url = self._fetch_same_origin_bytes(page, safe_url)
                    raw_name = Path(unquote(urlsplit(final_url).path)).name or Path(unquote(urlsplit(safe_url).path)).name
                    clean_name = sanitize_platform_text(raw_name, identities)
                    clean_name = re.sub(r'[<>:"/\\|?*]+', "_", clean_name).strip() or "recurso.bin"
                    if prefix:
                        clean_name = f"{prefix}-{clean_name}"
                    mime = _detect_mime_from_magic(raw_bytes, clean_name)
                    dest_file = destination_dir / clean_name
                    dest_file.write_bytes(raw_bytes)
                    sha256 = hashlib.sha256(raw_bytes).hexdigest()
                    downloaded.append(
                        DownloadedUnadmFile(
                            source_url=safe_url,
                            filename=clean_name,
                            saved_path=str(dest_file),
                            sha256=sha256,
                            size_bytes=len(raw_bytes),
                            mime_hint=mime,
                        )
                    )
            finally:
                browser.close()
        return downloaded

    def _fetch_same_origin_bytes(self, page: Any, file_url: str) -> tuple[bytes, str]:
        safe_url = ensure_same_https_host(file_url, UNADM_HOST, UNADM_BASE_URL)
        payload = page.evaluate(
            """async ({url, limit}) => {
                const controller = new AbortController();
                const timer = setTimeout(() => controller.abort(), 45000);
                try {
                    const response = await fetch(url, {credentials: 'same-origin', signal: controller.signal});
                    if (!response.ok || new URL(response.url).origin !== location.origin) {
                        throw new Error('download_failed');
                    }
                    const reader = response.body.getReader();
                    const chunks = [];
                    let size = 0;
                    while (true) {
                        const {done, value} = await reader.read();
                        if (done) break;
                        size += value.length;
                        if (size > limit) {
                            await reader.cancel();
                            throw new Error('download_size_exceeded');
                        }
                        chunks.push(value);
                    }
                    let binary = '';
                    for (const chunk of chunks) {
                        for (let i = 0; i < chunk.length; i += 8192) {
                            binary += String.fromCharCode(...chunk.subarray(i, i + 8192));
                        }
                    }
                    return {b64: btoa(binary), finalUrl: response.url};
                } finally {
                    clearTimeout(timer);
                }
            }""",
            {"url": safe_url, "limit": MAX_PLATFORM_DOWNLOAD_BYTES},
        )
        final_url = ensure_same_https_host(payload["finalUrl"], UNADM_HOST, UNADM_BASE_URL)
        raw = base64.b64decode(payload["b64"], validate=True)
        if not raw or len(raw) > MAX_PLATFORM_DOWNLOAD_BYTES:
            raise PlatformNavigationError("invalid_downloaded_payload_size")
        return raw, final_url


__all__ = [
    "AGENT_ID_NAVEGACION_ITESCA",
    "AGENT_ID_NAVEGACION_UNADM",
    "AGENT_TYPE_NAVEGACION_PLATAFORMA",
    "COURSES_UNADM",
    "DownloadedUnadmFile",
    "NavegacionUnadmAgent",
    "UNADM_BASE_URL",
    "UNADM_HOST",
    "UNADM_SESSION_SPEC",
    "UnadmModuleTarget",
    "UnadmNavigationRequest",
    "UnadmNavigationResult",
]
