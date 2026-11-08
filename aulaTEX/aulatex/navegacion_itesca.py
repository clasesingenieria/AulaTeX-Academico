"""Agente ``navegación-itesca`` (tipo ``navegación-plataforma``) para ITESCA Virtual.

Se autentica mediante ``PlatformCredentialVault`` de AulaTeX contra
``https://cursos3.e-itesca.edu.mx`` en modo estrictamente de solo lectura,
confinado al origen institucional y sanitizando toda salida antes de persistirla.
Jamás envía entregas ni inicia intentos de cuestionarios en vivo.
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
from .mcp_lex import McpLexClient, get_lex_client
from .workspace import AulaTeXWorkspace
from .navegacion_unadm import (
    COURSES_UNADM,
    DownloadedUnadmFile,
    NavegacionUnadmAgent,
    UNADM_BASE_URL,
    UNADM_HOST,
    UNADM_SESSION_SPEC,
    UnadmModuleTarget,
    UnadmNavigationRequest,
    UnadmNavigationResult,
)

ITESCA_HOST = "cursos3.e-itesca.edu.mx"
ITESCA_BASE_URL = f"https://{ITESCA_HOST}"
ITESCA_SESSION_SPEC = PlatformSessionSpec(
    institution="ITESCA",
    platform="ITESCA Virtual",
    host=ITESCA_HOST,
    base_url=ITESCA_BASE_URL,
    login_url=f"{ITESCA_BASE_URL}/login/index.php",
)

AGENT_ID_NAVEGACION_ITESCA = "navegación-itesca"


@dataclass(frozen=True)
class ItescaModuleTarget:
    module_id: int
    kind: str = "assign"  # assign | quiz | resource | folder | forum | auto
    course_id: int | None = None
    local_activity_number: int | None = None
    subject_slug: str = ""


@dataclass(frozen=True)
class ItescaNavigationRequest:
    inspect_dashboard: bool = True
    course_ids: tuple[int, ...] = ()
    modules: tuple[ItescaModuleTarget, ...] = ()
    output_dir: str = ""


@dataclass(frozen=True)
class DownloadedPlatformFile:
    source_url: str
    filename: str
    saved_path: str
    sha256: str
    size_bytes: int
    mime_hint: str


@dataclass(frozen=True)
class ItescaNavigationResult:
    run_id: str
    run_dir: Path
    snapshot_path: Path
    manifest_path: Path
    snapshot: dict[str, Any]
    blockers: tuple[dict[str, Any], ...] = field(default_factory=tuple)


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


class NavegacionItescaAgent(PlatformNavigationAgent):
    """Agente especializado de navegación de plataforma para ITESCA y UAS Virtual."""

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        institution: str = "ITESCA",
        lex_client: McpLexClient | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.lex_client = lex_client or get_lex_client()
        self.institution = institution.upper()
        if self.institution == "UAS":
            from .navegacion_uas import UAS_SESSION_SPEC, NavegacionUasAgent
            super().__init__(self.workspace.repo_root, UAS_SESSION_SPEC)
            self._uas_delegate: Any = NavegacionUasAgent(self.workspace, agent_id=AGENT_ID_NAVEGACION_ITESCA)
        else:
            super().__init__(self.workspace.repo_root, ITESCA_SESSION_SPEC)
            self._uas_delegate = None
        self.runs_root = self.workspace.feedback_root / "navegacion-itesca" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    @property
    def agent_id(self) -> str:
        return AGENT_ID_NAVEGACION_ITESCA

    def _open_authenticated_session(self, playwright: Any) -> tuple[Any, Any, tuple[str, ...], tuple[str, ...], str]:
        credentials = load_vault_account(self.repo_root, "ITESCA", ITESCA_HOST)
        username = credentials["username"]
        password = credentials["password"]
        forbidden_secrets = (username, password)
        browser_args, dns_mode = resolve_doh_host_args(ITESCA_HOST)

        browser = playwright.chromium.launch(headless=True, args=browser_args)
        context = browser.new_context(accept_downloads=False, service_workers="block")
        context.set_default_timeout(30000)
        context.set_default_navigation_timeout(60000)

        def _confine_origin(route: Any) -> None:
            req_url = route.request.url
            try:
                safe_url = ensure_same_https_host(req_url, ITESCA_HOST, ITESCA_BASE_URL)
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
                )
            ):
                route.abort()
                return
            route.continue_()

        context.route("**/*", _confine_origin)
        page = context.new_page()
        page.goto(ITESCA_SESSION_SPEC.login_url, wait_until="domcontentloaded")
        page.locator("#username").fill(username)
        page.locator("#password").fill(password)
        page.locator("#loginbtn").click()
        page.wait_for_load_state("domcontentloaded")
        ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)
        if "/login/" in urlsplit(page.url).path:
            browser.close()
            raise PlatformNavigationError("itesca_authentication_failed")

        names = page.locator(
            ".usermenu .usertext, .usermenu .userfullname, .logininfo a[href*='/user/profile.php'], h2"
        ).all_text_contents()
        identities = build_identity_variants(username, names)
        del credentials, username, password
        return browser, page, identities, forbidden_secrets, dns_mode

    def inspect(self, request: Any) -> Any:
        if self._uas_delegate is not None:
            return self._uas_delegate.inspect(request)
        from playwright.sync_api import sync_playwright

        run_id = f"{self.workspace.timestamp()}-navegacion-itesca"
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
                    courses_data[str(cid)] = self._inspect_course_page(page, cid, identities)

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
            "institution": "ITESCA",
            "host": ITESCA_HOST,
            "read_only": True,
            "dns_mode": dns_mode,
            "inspected_at_utc": datetime.now(timezone.utc).isoformat(),
            "dashboard": dashboard_data,
            "courses": courses_data,
            "modules": modules_data,
            "blockers": blockers,
        }
        assert_no_credential_leak(snapshot, forbidden_secrets)

        snapshot_path = run_dir / "snapshot-itesca.json"
        snapshot_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        manifest = {
            "run_id": run_id,
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "read_only": True,
            "courses_inspected": sorted(courses_data.keys()),
            "modules_inspected": sorted(modules_data.keys()),
            "blockers_count": len(blockers),
            "snapshot": self.workspace.relative(snapshot_path),
        }
        assert_no_credential_leak(manifest, forbidden_secrets)
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.workspace.append_bitacora(run_id, "navegacion-itesca", manifest)

        return ItescaNavigationResult(
            run_id=run_id,
            run_dir=run_dir,
            snapshot_path=snapshot_path,
            manifest_path=manifest_path,
            snapshot=snapshot,
            blockers=tuple(blockers),
        )

    def download_resources(
        self,
        items: list[dict[str, Any]],
        destination_dir: Path,
    ) -> list[DownloadedPlatformFile]:
        """Descarga archivos docentes/institucionales autenticados dentro de ITESCA Virtual.

        Cada elemento de ``items`` admite ``{"url": "https://cursos3.e-itesca.edu.mx/...", "prefix": "1762"}``.
        Si ``url`` apunta a ``/mod/resource/view.php?id=X`` o ``/mod/folder/view.php?id=X``,
        resuelve primero los enlaces ``/pluginfile.php/`` dentro de la vista de solo lectura.
        """
        if not items:
            return []
        from playwright.sync_api import sync_playwright

        destination_dir.mkdir(parents=True, exist_ok=True)
        downloaded: list[DownloadedPlatformFile] = []

        with sync_playwright() as pw:
            browser, page, identities, forbidden_secrets, _dns_mode = self._open_authenticated_session(pw)
            try:
                resolved_files: list[tuple[str, str]] = []
                for spec in items:
                    raw_url = str(spec.get("url") or "").strip()
                    prefix = str(spec.get("prefix") or "").strip()
                    safe_url = ensure_same_https_host(raw_url, ITESCA_HOST, ITESCA_BASE_URL)
                    parsed = urlsplit(safe_url)
                    if parsed.path.startswith("/pluginfile.php/"):
                        resolved_files.append((safe_url, prefix))
                    elif parsed.path in ("/mod/resource/view.php", "/mod/folder/view.php"):
                        discovered = self._discover_resource_pluginfiles(page, safe_url)
                        for p_url in discovered:
                            resolved_files.append((p_url, prefix))

                seen_urls: set[str] = set()
                for file_url, prefix in resolved_files:
                    norm_url = normalize_readonly_link(file_url, ITESCA_HOST) or file_url
                    if norm_url in seen_urls:
                        continue
                    seen_urls.add(norm_url)
                    raw_bytes, final_url = self._fetch_same_origin_bytes(page, file_url)
                    raw_name = Path(unquote(urlsplit(final_url).path)).name or Path(unquote(urlsplit(file_url).path)).name
                    clean_name = sanitize_platform_text(raw_name, identities)
                    clean_name = re.sub(r'[<>:"/\\|?*]+', "_", clean_name).strip() or "recurso.bin"
                    mime = _detect_mime_from_magic(raw_bytes, clean_name)
                    if mime == "text/html":
                        raise PlatformNavigationError(f"resource_returned_html_instead_of_file:{clean_name}")
                    sha = hashlib.sha256(raw_bytes).hexdigest()
                    out_name = f"{prefix}-{clean_name}" if prefix and not clean_name.startswith(prefix) else clean_name
                    out_path = destination_dir / out_name
                    out_path.write_bytes(raw_bytes)
                    record = DownloadedPlatformFile(
                        source_url=norm_url,
                        filename=clean_name,
                        saved_path=str(out_path.resolve()),
                        sha256=sha,
                        size_bytes=len(raw_bytes),
                        mime_hint=mime,
                    )
                    assert_no_credential_leak(asdict(record), forbidden_secrets)
                    downloaded.append(record)
            finally:
                browser.close()
        return downloaded

    def _inspect_dashboard_page(self, page: Any, identities: tuple[str, ...]) -> dict[str, Any]:
        page.goto(f"{ITESCA_BASE_URL}/my/", wait_until="domcontentloaded")
        ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)
        # Dar margen breve a que el bloque asíncrono de línea de tiempo cargue en Moodle 4.x
        try:
            page.wait_for_selector("[data-region='event-list-item'], [data-region='timeline-view']", timeout=8000)
            page.wait_for_timeout(1200)
        except Exception:
            pass
        raw_links = page.locator("a[href]").evaluate_all(
            "els => els.map(e => ({text: (e.innerText || '').trim(), url: e.href}))"
        )
        events: list[dict[str, str]] = []
        courses: list[dict[str, str]] = []
        for item in raw_links:
            norm = normalize_readonly_link(item.get("url", ""), ITESCA_HOST)
            if not norm:
                continue
            label = sanitize_platform_text(item.get("text", ""), identities).strip()
            if not label:
                continue
            if "/mod/" in norm and not any(ev["url"] == norm for ev in events):
                events.append({"title": label, "url": norm})
            elif "/course/view.php" in norm and not any(c["url"] == norm for c in courses):
                courses.append({"title": label, "url": norm})
        timeline_text = ""
        tl_loc = page.locator("[data-region='timeline-view']")
        if tl_loc.count():
            timeline_text = sanitize_platform_text(tl_loc.first.inner_text(), identities).strip()
        return {
            "url": f"{ITESCA_BASE_URL}/my/",
            "timeline_text": timeline_text,
            "discovered_events": events,
            "discovered_courses": courses,
        }

    def _inspect_course_page(self, page: Any, course_id: int, identities: tuple[str, ...]) -> dict[str, Any]:
        url = f"{ITESCA_BASE_URL}/course/view.php?id={course_id}"
        page.goto(url, wait_until="domcontentloaded")
        ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)
        if "/login/" in urlsplit(page.url).path:
            raise PlatformNavigationError("itesca_session_expired")
        title_loc = page.locator("h1")
        course_title = sanitize_platform_text(
            title_loc.first.inner_text() if title_loc.count() else f"Course {course_id}",
            identities,
        ).strip()
        raw_sections = page.evaluate(
            """() => {
                const secNodes = Array.from(document.querySelectorAll(
                    'li.section.course-section, li.section.main, [data-region="section"], .course-content .section'
                ));
                if (secNodes.length > 1) {
                    return secNodes.map((sec, idx) => {
                        const secTitleEl = sec.querySelector('.sectionname, h3.sectionname, [data-for="section_title"], h3');
                        const summaryEl = sec.querySelector('.summarytext, .summary');
                        const acts = Array.from(sec.querySelectorAll('li.activity, .activity-item')).map(act => {
                            const dataId = act.getAttribute('data-id') || (act.id || '').replace('module-', '');
                            const classes = Array.from(act.classList || []);
                            const modClass = classes.find(c => c.startsWith('modtype_')) || '';
                            const modtype = modClass.replace('modtype_', '');
                            const linkEl = act.querySelector('a.aalink, .activityname a, a[href*="/mod/"]');
                            const datesEl = act.querySelector('[data-region="activity-dates"], .activity-dates, .description');
                            return {
                                cmid: dataId || '',
                                modtype: modtype || '',
                                title: linkEl ? (linkEl.innerText || '').trim() : (act.innerText || '').split('\\n')[0].trim(),
                                url: linkEl ? linkEl.href : '',
                                dates_and_meta: datesEl ? (datesEl.innerText || '').trim() : ''
                            };
                        });
                        return {
                            index: idx,
                            title: secTitleEl ? (secTitleEl.innerText || '').trim() : `Sección ${idx}`,
                            summary: summaryEl ? (summaryEl.innerText || '').trim() : '',
                            activities: acts
                        };
                    });
                }
                // Fallback para formatos por pestañas/tarjetas: recolectar todos los enlaces /mod/ y /course/section.php
                const main = document.querySelector('#region-main') || document.body;
                const modLinks = Array.from(main.querySelectorAll('a[href*="/mod/"], a[href*="/course/view.php?id="][href*="section="], a[href*="/course/section.php"]'));
                const acts = modLinks.map(a => {
                    const m = a.href.match(/\\/mod\\/([a-z0-9_]+)\\/view\\.php\\?id=(\\d+)/i);
                    return {
                        cmid: m ? m[2] : '',
                        modtype: m ? m[1] : 'section_link',
                        title: (a.innerText || '').trim(),
                        url: a.href,
                        dates_and_meta: ''
                    };
                }).filter(x => x.title);
                return [{index: 0, title: 'Vista general del curso', summary: '', activities: acts}];
            }"""
        )
        sections_clean: list[dict[str, Any]] = []
        for sec in raw_sections:
            acts_clean: list[dict[str, Any]] = []
            for act in sec.get("activities", []):
                norm_url = normalize_readonly_link(act.get("url", ""), ITESCA_HOST)
                acts_clean.append(
                    {
                        "cmid": str(act.get("cmid") or ""),
                        "modtype": str(act.get("modtype") or ""),
                        "title": sanitize_platform_text(act.get("title", ""), identities),
                        "url": norm_url,
                        "dates_and_meta": sanitize_platform_text(act.get("dates_and_meta", ""), identities),
                    }
                )
            sections_clean.append(
                {
                    "index": int(sec.get("index", 0)),
                    "title": sanitize_platform_text(sec.get("title", ""), identities),
                    "summary": sanitize_platform_text(sec.get("summary", ""), identities),
                    "activities": acts_clean,
                }
            )
        return {
            "course_id": course_id,
            "url": url,
            "title": course_title,
            "sections": sections_clean,
        }

    def _inspect_module_page(
        self,
        page: Any,
        target: ItescaModuleTarget,
        identities: tuple[str, ...],
        blockers: list[dict[str, Any]],
    ) -> dict[str, Any]:
        mid = _positive_int(target.module_id, "module_id")
        kind = (target.kind or "assign").strip().lower()
        mod_path = {
            "assign": "/mod/assign/view.php",
            "quiz": "/mod/quiz/view.php",
            "resource": "/mod/resource/view.php",
            "folder": "/mod/folder/view.php",
            "forum": "/mod/forum/view.php",
        }.get(kind, "/mod/assign/view.php")

        view_url = f"{ITESCA_BASE_URL}{mod_path}?id={mid}"
        page.goto(view_url, wait_until="domcontentloaded")
        ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)
        if "/login/" in urlsplit(page.url).path:
            raise PlatformNavigationError("itesca_session_expired")

        main = page.locator("#region-main")
        main.wait_for(state="visible")
        h1_loc = page.locator("h1")
        page_title = sanitize_platform_text(
            h1_loc.first.inner_text() if h1_loc.count() else "",
            identities,
        ).strip()
        mod_heading_loc = main.locator("h2")
        module_heading = sanitize_platform_text(
            mod_heading_loc.first.inner_text() if mod_heading_loc.count() else page_title,
            identities,
        ).strip()

        dates_loc = main.locator("[data-region='activity-dates'], .activity-dates")
        activity_dates = sanitize_platform_text(
            dates_loc.first.inner_text() if dates_loc.count() else "",
            identities,
        ).strip()

        intro_loc = main.locator("#intro, .activity-description, [id*='intro']")
        intro_text = "\n\n".join(
            sanitize_platform_text(block.inner_text(), identities).strip()
            for block in intro_loc.all()
            if (block.inner_text() or "").strip()
        ).strip()

        main_text = sanitize_platform_text(main.inner_text(), identities).strip()

        # Capturar enlaces de archivos docentes / vistas académicas sin incluir entregas previas del alumno
        raw_links = main.evaluate(
            """(root) => {
                return Array.from(root.querySelectorAll('a[href]')).map(a => {
                    const inSubmission = Boolean(a.closest('.submissionstatustable, .feedback'));
                    return {
                        text: (a.innerText || '').trim(),
                        url: a.href,
                        in_submission_or_feedback: inSubmission
                    };
                });
            }"""
        )
        instructional_attachments: list[dict[str, str]] = []
        related_links: list[dict[str, str]] = []
        for link in raw_links:
            if link.get("in_submission_or_feedback"):
                continue
            norm = normalize_readonly_link(link.get("url", ""), ITESCA_HOST)
            if not norm or "/assignsubmission_file/" in norm:
                continue
            text_clean = sanitize_platform_text(link.get("text", ""), identities).strip()
            if "/pluginfile.php/" in norm:
                if not any(att["url"] == norm for att in instructional_attachments):
                    instructional_attachments.append({"title": text_clean, "url": norm})
            elif not any(rl["url"] == norm for rl in related_links):
                related_links.append({"title": text_clean, "url": norm})

        result: dict[str, Any] = {
            "module_id": mid,
            "kind": kind,
            "course_id": target.course_id,
            "local_activity_number": target.local_activity_number,
            "subject_slug": target.subject_slug,
            "url": view_url,
            "course_heading": page_title,
            "title": module_heading or page_title,
            "activity_dates": activity_dates,
            "intro_text": intro_text or main_text,
            "full_main_text": main_text,
            "instructional_attachments": instructional_attachments,
            "related_links": related_links,
            "read_only": True,
        }

        if kind == "assign":
            status_rows = main.evaluate(
                """(root) => {
                    const rows = {};
                    root.querySelectorAll('.submissionstatustable tr, .feedback tr').forEach(tr => {
                        const th = tr.querySelector('th, td.cell.c0');
                        const td = tr.querySelector('td.cell.c1, td:last-child');
                        if (th && td && th !== td) {
                            rows[(th.innerText || '').trim()] = (td.innerText || '').trim();
                        }
                    });
                    return rows;
                }"""
            )
            clean_status = {
                sanitize_platform_text(k, identities): sanitize_platform_text(v, identities)
                for k, v in status_rows.items()
                if k
            }
            full_fb_loc = main.locator('[class*="full_assignfeedback_comments_"]')
            full_fb = "\n\n".join(
                sanitize_platform_text(el.text_content() or "", identities).strip()
                for el in full_fb_loc.all()
                if (el.text_content() or "").strip()
            ).strip()
            rubric_rows = main.evaluate(
                """(root) => {
                    return Array.from(root.querySelectorAll('.gradingform_rubric tr.criterion')).map(tr => {
                        const desc = tr.querySelector('.description');
                        const levels = Array.from(tr.querySelectorAll('.levels .level')).map(lv => ({
                            definition: (lv.querySelector('.definition')?.innerText || '').trim(),
                            score: (lv.querySelector('.score')?.innerText || '').trim(),
                            checked: lv.classList.contains('checked') || lv.getAttribute('aria-checked') === 'true'
                        }));
                        const remark = tr.querySelector('.remark');
                        return {
                            criterion: desc ? (desc.innerText || '').trim() : '',
                            levels: levels,
                            teacher_remark: remark ? (remark.innerText || '').trim() : ''
                        };
                    });
                }"""
            )
            clean_rubric = [
                {
                    "criterion": sanitize_platform_text(r.get("criterion", ""), identities),
                    "levels": [
                        {
                            "definition": sanitize_platform_text(lv.get("definition", ""), identities),
                            "score": sanitize_platform_text(lv.get("score", ""), identities),
                            "checked": bool(lv.get("checked")),
                        }
                        for lv in r.get("levels", [])
                    ],
                    "teacher_remark": sanitize_platform_text(r.get("teacher_remark", ""), identities),
                }
                for r in rubric_rows
                if r.get("criterion")
            ]
            result["submission_and_feedback"] = {
                "status_table": clean_status,
                "teacher_feedback_full": full_fb,
                "rubric": clean_rubric,
            }

        elif kind == "quiz":
            has_start_btn = bool(
                main.locator("form[action*='startattempt.php'], button:has-text('Intente resolver')").count()
            )
            attempts_summary = main.evaluate(
                """(root) => {
                    return Array.from(root.querySelectorAll('table.quizattemptsummary tbody tr')).map(tr =>
                        Array.from(tr.querySelectorAll('td')).map(td => (td.innerText || '').trim())
                    );
                }"""
            )
            clean_attempts = [
                [sanitize_platform_text(cell, identities) for cell in row]
                for row in attempts_summary
            ]
            quiz_blocker = None
            if has_start_btn and not clean_attempts:
                quiz_blocker = {
                    "code": "live_quiz_attempt_protected",
                    "module_id": mid,
                    "title": result["title"],
                    "reason": (
                        "Cuestionario en línea abierto sin intentos previos concluidos; "
                        "navegación-itesca opera en modo solo lectura y no inicia startattempt.php "
                        "para no consumir el intento cronometrado del estudiante."
                    ),
                }
                blockers.append(quiz_blocker)
            result["quiz_state"] = {
                "live_start_button_present": has_start_btn,
                "attempt_started_by_agent": False,
                "completed_attempts_rows": clean_attempts,
                "read_only_blocker": quiz_blocker,
            }

        return result

    def _discover_resource_pluginfiles(self, page: Any, resource_view_url: str) -> list[str]:
        """Descubre URLs ``/pluginfile.php/`` de un módulo ``resource`` o ``folder`` sin mutar estado."""
        found: list[str] = []
        if "/mod/resource/view.php" in resource_view_url:
            sep = "&" if "?" in resource_view_url else "?"
            redirect_probe = f"{resource_view_url}{sep}redirect=0"
            page.goto(redirect_probe, wait_until="domcontentloaded")
            ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)
            if "/pluginfile.php/" in urlsplit(page.url).path:
                found.append(page.url)
                return found
        else:
            page.goto(resource_view_url, wait_until="domcontentloaded")
            ensure_same_https_host(page.url, ITESCA_HOST, ITESCA_BASE_URL)

        links = page.locator("#region-main a[href*='/pluginfile.php/']").evaluate_all(
            "els => els.map(e => e.href)"
        )
        for href in links:
            try:
                safe = ensure_same_https_host(href, ITESCA_HOST, ITESCA_BASE_URL)
                if safe not in found:
                    found.append(safe)
            except PlatformNavigationError:
                continue
        return found

    def _fetch_same_origin_bytes(self, page: Any, file_url: str) -> tuple[bytes, str]:
        safe_url = ensure_same_https_host(file_url, ITESCA_HOST, ITESCA_BASE_URL)
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
        final_url = ensure_same_https_host(payload["finalUrl"], ITESCA_HOST, ITESCA_BASE_URL)
        raw = base64.b64decode(payload["b64"], validate=True)
        if not raw or len(raw) > MAX_PLATFORM_DOWNLOAD_BYTES:
            raise PlatformNavigationError("invalid_downloaded_payload_size")
        return raw, final_url


__all__ = [
    "AGENT_ID_NAVEGACION_ITESCA",
    "AGENT_TYPE_NAVEGACION_PLATAFORMA",
    "COURSES_UNADM",
    "DownloadedPlatformFile",
    "DownloadedUnadmFile",
    "ITESCA_BASE_URL",
    "ITESCA_HOST",
    "ITESCA_SESSION_SPEC",
    "ItescaModuleTarget",
    "ItescaNavigationRequest",
    "ItescaNavigationResult",
    "NavegacionItescaAgent",
    "NavegacionUnadmAgent",
    "UNADM_BASE_URL",
    "UNADM_HOST",
    "UNADM_SESSION_SPEC",
    "UnadmModuleTarget",
    "UnadmNavigationRequest",
    "UnadmNavigationResult",
]
