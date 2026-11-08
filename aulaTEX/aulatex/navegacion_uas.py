"""Agente ``navegación-itesca`` / ``navegación-uas`` (tipo ``navegación-plataforma``) para UAS Virtual.

Se autentica mediante ``PlatformCredentialVault`` de AulaTeX contra
``https://virtual.uas.edu.mx/fca`` en modo estrictamente de solo lectura,
confinado al origen institucional y sanitizando toda salida antes de persistirla.
Jamás expone credenciales ni tokens en archivos generados ni registros.
"""
from __future__ import annotations

import base64
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import parse_qsl, unquote, urlencode, urljoin, urlsplit, urlunsplit

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

UAS_HOST = "virtual.uas.edu.mx"
UAS_BASE_URL = f"https://{UAS_HOST}/fca"
UAS_LOGIN_URL = f"{UAS_BASE_URL}/login/index.php"

UAS_SESSION_SPEC = PlatformSessionSpec(
    institution="UAS",
    platform="virtual.uas",
    host=UAS_HOST,
    base_url=UAS_BASE_URL,
    login_url=UAS_LOGIN_URL,
)

AGENT_ID_NAVEGACION_ITESCA = "navegación-itesca"
AGENT_ID_NAVEGACION_UAS = "navegación-uas"


@dataclass(frozen=True)
class UasModuleTarget:
    module_id: int
    kind: str = "assign"  # assign | forum | page | resource | folder | quiz
    course_id: int | None = None
    local_activity_number: int | None = None
    subject_slug: str = ""


@dataclass(frozen=True)
class UasNavigationRequest:
    inspect_dashboard: bool = True
    course_ids: tuple[int, ...] = (632,)
    modules: tuple[UasModuleTarget, ...] = ()
    output_dir: str = ""
    download_resources: bool = False


@dataclass(frozen=True)
class DownloadedUasFile:
    source_url: str
    filename: str
    saved_path: str
    sha256: str
    size_bytes: int
    mime_hint: str


@dataclass(frozen=True)
class UasNavigationResult:
    run_id: str
    run_dir: Path
    snapshot_path: Path
    manifest_path: Path
    snapshot: dict[str, Any]
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    downloaded_files: tuple[DownloadedUasFile, ...] = field(default_factory=tuple)


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


class NavegacionUasAgent(PlatformNavigationAgent):
    """Agente especializado en navegación de la plataforma UAS (virtual.uas.edu.mx/fca).
    
    Implementa el tipo ``navegación-plataforma`` con confinamiento estricto de origen,
    autenticación mediante bóveda cifrada en memoria y sanitización absoluta contra fugas.
    """

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        agent_id: str = AGENT_ID_NAVEGACION_ITESCA,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        super().__init__(self.workspace.repo_root, UAS_SESSION_SPEC)
        self._custom_agent_id = agent_id
        self.runs_root = self.workspace.feedback_root / "navegacion-uas" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    @property
    def agent_id(self) -> str:
        return self._custom_agent_id

    def _open_authenticated_session(
        self, playwright: Any
    ) -> tuple[Any, Any, tuple[str, ...], tuple[str, ...], str]:
        credentials = load_vault_account(self.repo_root, "UAS", UAS_HOST)
        username = credentials["username"]
        password = credentials["password"]
        forbidden_secrets = (username, password)
        browser_args, dns_mode = resolve_doh_host_args(UAS_HOST)

        browser = playwright.chromium.launch(headless=True, args=browser_args)
        context = browser.new_context(accept_downloads=False, service_workers="block")
        context.set_default_timeout(30000)
        context.set_default_navigation_timeout(60000)

        def _confine_origin(route: Any) -> None:
            req_url = route.request.url
            try:
                safe_url = ensure_same_https_host(req_url, UAS_HOST, UAS_BASE_URL)
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
                    "/user/edit",
                )
            ):
                route.abort()
                return
            route.continue_()

        context.route("**/*", _confine_origin)
        page = context.new_page()
        page.goto(UAS_SESSION_SPEC.login_url, wait_until="domcontentloaded")
        page.locator("#username, input[name=username]").first.fill(username)
        page.locator("#password, input[name=password]").first.fill(password)
        page.locator("#loginbtn, button[type=submit]").first.click()
        page.wait_for_load_state("domcontentloaded")
        ensure_same_https_host(page.url, UAS_HOST, UAS_BASE_URL)
        if "/login/" in urlsplit(page.url).path:
            browser.close()
            raise PlatformNavigationError("uas_authentication_failed")

        names = page.locator(
            ".usermenu .usertext, .usermenu .userfullname, .logininfo a[href*='/user/profile.php'], h2"
        ).all_text_contents()
        identities = build_identity_variants(username, names)
        del credentials, username, password
        return browser, page, identities, forbidden_secrets, dns_mode

    def inspect(self, request: UasNavigationRequest) -> UasNavigationResult:
        from playwright.sync_api import sync_playwright

        run_id = f"{self.workspace.timestamp()}-navegacion-uas"
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
        downloaded_files: list[DownloadedUasFile] = []

        with sync_playwright() as pw:
            browser, page, identities, forbidden_secrets, dns_mode = self._open_authenticated_session(pw)
            try:
                if request.inspect_dashboard:
                    dashboard_data = self._inspect_dashboard_page(page, identities)

                for raw_cid in dict.fromkeys(request.course_ids):
                    cid = _positive_int(raw_cid, "course_id")
                    courses_data[str(cid)] = self._inspect_course_page(page, cid, identities)

                for target in request.modules:
                    mid = _positive_int(target.module_id, "module_id")
                    mod_info = self._inspect_module_page(page, target, identities, blockers)
                    modules_data[str(mid)] = mod_info

                    if request.download_resources and mod_info.get("attachment_urls"):
                        for att_url in mod_info["attachment_urls"]:
                            try:
                                dl_file = self._download_platform_attachment(
                                    page, att_url, run_dir / "descargas"
                                )
                                if dl_file:
                                    downloaded_files.append(dl_file)
                            except Exception as dl_err:
                                blockers.append({
                                    "kind": "download_failed",
                                    "url": att_url,
                                    "module_id": mid,
                                    "error": str(dl_err),
                                })
            finally:
                browser.close()

        snapshot: dict[str, Any] = {
            "schema_version": "1.0.0",
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "institution": "UAS",
            "host": UAS_HOST,
            "base_url": UAS_BASE_URL,
            "read_only": True,
            "dns_mode": dns_mode,
            "inspected_at_utc": datetime.now(timezone.utc).isoformat(),
            "dashboard": dashboard_data,
            "courses": courses_data,
            "modules": modules_data,
            "blockers": blockers,
            "downloaded_files": [asdict(f) for f in downloaded_files],
        }
        assert_no_credential_leak(snapshot, forbidden_secrets)

        snapshot_path = run_dir / "snapshot-uas.json"
        snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        manifest = {
            "run_id": run_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "read_only": True,
            "institution": "UAS",
            "courses_inspected": sorted(courses_data.keys()),
            "modules_inspected": sorted(modules_data.keys()),
            "files_downloaded": len(downloaded_files),
            "blockers_count": len(blockers),
            "snapshot": self.workspace.relative(snapshot_path),
        }
        assert_no_credential_leak(manifest, forbidden_secrets)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.workspace.append_bitacora(run_id, "navegacion-uas", manifest)

        return UasNavigationResult(
            run_id=run_id,
            run_dir=run_dir,
            snapshot_path=snapshot_path,
            manifest_path=manifest_path,
            snapshot=snapshot,
            blockers=tuple(blockers),
            downloaded_files=tuple(downloaded_files),
        )

    def _inspect_dashboard_page(self, page: Any, identities: tuple[str, ...]) -> dict[str, Any]:
        dashboard_url = f"{UAS_BASE_URL}/my/"
        page.goto(dashboard_url, wait_until="domcontentloaded")
        ensure_same_https_host(page.url, UAS_HOST, UAS_BASE_URL)

        course_links = page.locator("a[href*='/course/view.php?id=']").evaluate_all(
            "els => els.map(e => ({href: e.href, text: e.innerText}))"
        )
        enrolled_courses: list[dict[str, Any]] = []
        seen_cids: set[int] = set()
        for item in course_links:
            href = item.get("href", "")
            title = sanitize_platform_text(item.get("text", "").strip(), identities)
            cid_match = re.search(r"[?&]id=(\d+)", href)
            if cid_match:
                cid = int(cid_match.group(1))
                if cid not in seen_cids:
                    seen_cids.add(cid)
                    enrolled_courses.append({
                        "course_id": cid,
                        "title": title,
                        "url": f"{UAS_BASE_URL}/course/view.php?id={cid}",
                    })
        return {
            "title": "Área personal UAS",
            "enrolled_courses": enrolled_courses,
        }

    def _inspect_course_page(
        self, page: Any, course_id: int, identities: tuple[str, ...]
    ) -> dict[str, Any]:
        course_url = f"{UAS_BASE_URL}/course/view.php?id={course_id}"
        page.goto(course_url, wait_until="domcontentloaded")
        ensure_same_https_host(page.url, UAS_HOST, UAS_BASE_URL)

        heading_locator = page.locator("h1, .page-header-headings, .page-title").first
        raw_heading = heading_locator.inner_text().strip() if heading_locator.count() else f"Curso {course_id}"
        heading = sanitize_platform_text(raw_heading, identities)

        links = page.locator("#region-main a[href], .course-content a[href]").evaluate_all(
            "els => els.map(e => ({href: e.href, text: e.innerText.trim()}))"
        )
        activities: list[dict[str, Any]] = []
        resources: list[dict[str, Any]] = []
        seen_module_ids: set[int] = set()

        for link in links:
            url = urljoin(UAS_BASE_URL, link.get("href", ""))
            try:
                safe_url = ensure_same_https_host(url, UAS_HOST, UAS_BASE_URL)
            except PlatformNavigationError:
                continue

            parsed = urlsplit(safe_url)
            query = dict(parse_qsl(parsed.query))
            mid_val = query.get("id")
            if not mid_val or not mid_val.isdigit():
                continue
            mid = int(mid_val)
            if mid in seen_module_ids:
                continue
            seen_module_ids.add(mid)

            text = sanitize_platform_text(link.get("text", "").strip(), identities)
            lowered_path = parsed.path.lower()
            if "/mod/assign/" in lowered_path:
                activities.append({
                    "module_id": mid,
                    "kind": "assign",
                    "title": text,
                    "url": f"{UAS_BASE_URL}/mod/assign/view.php?id={mid}",
                })
            elif "/mod/forum/" in lowered_path:
                activities.append({
                    "module_id": mid,
                    "kind": "forum",
                    "title": text,
                    "url": f"{UAS_BASE_URL}/mod/forum/view.php?id={mid}",
                })
            elif any(mod in lowered_path for mod in ("/mod/page/", "/mod/resource/", "/mod/folder/")):
                kind = "page" if "/mod/page/" in lowered_path else ("resource" if "/mod/resource/" in lowered_path else "folder")
                resources.append({
                    "module_id": mid,
                    "kind": kind,
                    "title": text,
                    "url": f"{UAS_BASE_URL}/mod/{kind}/view.php?id={mid}",
                })

        return {
            "course_id": course_id,
            "title": heading,
            "activities_count": len(activities),
            "resources_count": len(resources),
            "activities": activities,
            "weekly_resources": resources,
        }

    def _inspect_module_page(
        self,
        page: Any,
        target: UasModuleTarget,
        identities: tuple[str, ...],
        blockers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        module_url = f"{UAS_BASE_URL}/mod/{target.kind}/view.php?id={target.module_id}"
        page.goto(module_url, wait_until="domcontentloaded")
        ensure_same_https_host(page.url, UAS_HOST, UAS_BASE_URL)

        main = page.locator("#region-main, .main-content").first
        if not main.count():
            blockers.append({
                "kind": "module_main_region_missing",
                "module_id": target.module_id,
                "url": module_url,
            })
            return {
                "module_id": target.module_id,
                "kind": target.kind,
                "url": module_url,
                "error": "missing_main_region",
            }

        title_loc = page.locator("h1, h2, .activityname").first
        raw_title = title_loc.inner_text().strip() if title_loc.count() else f"Módulo {target.module_id}"
        title = sanitize_platform_text(raw_title, identities)

        # Intro / Consigna
        intro_loc = main.locator("#intro, .activity-description, .generalbox").first
        raw_intro = intro_loc.inner_text().strip() if intro_loc.count() else ""
        intro = sanitize_platform_text(raw_intro, identities)

        # Submission status & dates
        status_table = main.locator(".submissionstatustable, .generaltable, .activity-dates")
        raw_status = "\n".join(status_table.all_inner_texts()).strip() if status_table.count() else ""
        status_text = sanitize_platform_text(raw_status, identities)

        # Extraer fechas y deadline
        deadline = None
        dates_search = re.search(
            r"(?i)(?:fecha de entrega|entrega|cierre|due date)\s*[:#]?\s*([^\n\r]+)",
            status_text,
        )
        if dates_search:
            deadline = dates_search.group(1).strip()

        # Enlaces a adjuntos / recursos dentro del módulo
        att_links = main.locator("a[href*='/pluginfile.php/']").evaluate_all(
            "els => els.map(e => e.href)"
        )
        attachment_urls: list[str] = []
        for raw_href in att_links:
            try:
                safe_att = ensure_same_https_host(raw_href, UAS_HOST, UAS_BASE_URL)
                if safe_att not in attachment_urls:
                    attachment_urls.append(safe_att)
            except PlatformNavigationError:
                continue

        return {
            "module_id": target.module_id,
            "kind": target.kind,
            "title": title,
            "url": module_url,
            "raw_consigna": intro,
            "submission_status": status_text,
            "deadline": deadline,
            "attachment_urls": attachment_urls,
            "local_activity_number": target.local_activity_number,
            "subject_slug": target.subject_slug,
        }

    def _download_platform_attachment(
        self, page: Any, file_url: str, dest_dir: Path
    ) -> DownloadedUasFile | None:
        dest_dir.mkdir(parents=True, exist_ok=True)
        raw_bytes, final_url = self._fetch_same_origin_bytes(page, file_url)
        parsed = urlsplit(final_url)
        raw_name = unquote(Path(parsed.path).name)
        filename = re.sub(r'[\\/*?:"<>|]', "_", raw_name) or "recurso-uas.bin"

        dest_file = dest_dir / filename
        dest_file.write_bytes(raw_bytes)
        sha = hashlib.sha256(raw_bytes).hexdigest()
        mime = _detect_mime_from_magic(raw_bytes, filename)

        return DownloadedUasFile(
            source_url=final_url,
            filename=filename,
            saved_path=str(dest_file),
            sha256=sha,
            size_bytes=len(raw_bytes),
            mime_hint=mime,
        )

    def _fetch_same_origin_bytes(self, page: Any, file_url: str) -> tuple[bytes, str]:
        safe_url = ensure_same_https_host(file_url, UAS_HOST, UAS_BASE_URL)
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
        final_url = ensure_same_https_host(payload["finalUrl"], UAS_HOST, UAS_BASE_URL)
        raw = base64.b64decode(payload["b64"], validate=True)
        if not raw or len(raw) > MAX_PLATFORM_DOWNLOAD_BYTES:
            raise PlatformNavigationError("invalid_downloaded_payload_size")
        return raw, final_url


# Alias canónico
NavegacionItescaUasAgent = NavegacionUasAgent

__all__ = [
    "AGENT_ID_NAVEGACION_ITESCA",
    "AGENT_ID_NAVEGACION_UAS",
    "AGENT_TYPE_NAVEGACION_PLATAFORMA",
    "DownloadedUasFile",
    "NavegacionItescaUasAgent",
    "NavegacionUasAgent",
    "UAS_BASE_URL",
    "UAS_HOST",
    "UAS_LOGIN_URL",
    "UAS_SESSION_SPEC",
    "UasModuleTarget",
    "UasNavigationRequest",
    "UasNavigationResult",
]
