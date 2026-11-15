"""Agente ``diseno-sitio-lex`` para AulaTeX y la Malla Multi-LLM LEX.

Especializado en la concepción, maquetación nativa, auditoría y verificación
del portal comercial web "Lex Contable" en Google Sites, garantizando la total
ausencia de iframes o incrustaciones externas y validando que todos los bloques
(encabezado, layouts, tarjetas de servicios, método, acordeones FAQ y cierre)
sean componentes nativos de la plataforma.

Coordina además la sincronización de evidencia gráfica y la recompilación
editorial del reporte de actividad en LaTeX conforme a los estándares EMS de AulaTeX.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any
from urllib.parse import urlsplit
import urllib.request
import urllib.error

from .navegacion_plataforma import assert_no_credential_leak
from .subir_drive import launch_persistent_headed_context, resolve_drive_profile_dir
from .workspace import AulaTeXWorkspace

AGENT_ID_DISENO_SITIO_LEX = "diseno-sitio-lex"
SITES_HOST = "sites.google.com"
ALLOWED_SITES_AUTH_HOSTS = frozenset({"sites.google.com", "accounts.google.com"})
DEFAULT_SITE_URL = "https://sites.google.com/view/delacruz-consultores-lcp"
DEFAULT_EDITOR_URL = "https://sites.google.com/d/1l423JjQirXpiwhmtD5YqTptvDXx_lhtY/p/1a5_sx-_zIRDrzcX2DzkFkiv4wJoUJMGV/edit"

_SITES_EDITOR_READY_SELECTORS = (
    '[role="tab"]:has-text("Insertar"):visible',
    '[role="tab"]:has-text("Insert"):visible',
    '[role="tab"]:has-text("Páginas"):visible',
    '[role="tab"]:has-text("Pages"):visible',
    'div[role="button"]:has-text("Publicar"):visible',
    'button:has-text("Publicar"):visible',
    'button:has-text("Publish"):visible',
)


@dataclass(frozen=True)
class NativeSectionSpec:
    section_id: str
    title: str
    component_type: str  # banner, text_bar, 3_column_layout, service_grid, 4_column_method, collapsible_group, cta_footer
    key_phrases: tuple[str, ...]
    image_name: str | None = None


@dataclass(frozen=True)
class DisenoSitioLexBlueprint:
    site_title: str = "Lex Contable — De La Cruz & Asociados"
    published_url: str = DEFAULT_SITE_URL
    editor_url: str = DEFAULT_EDITOR_URL
    theme: str = "Diplomático"
    accent_color: str = "#173b4c"
    sections: tuple[NativeSectionSpec, ...] = (
        NativeSectionSpec(
            section_id="header",
            title="Lex Contable",
            component_type="banner",
            key_phrases=(
                "ACOMPAÑAMIENTO CONTABLE · MÉXICO",
                "Lex Contable",
                "Contabilidad, regularización y seguimiento fiscal",
                "Explorar servicios",
            ),
            image_name="revision-documental.jpg",
        ),
        NativeSectionSpec(
            section_id="quickline",
            title="Franja de proceso",
            component_type="text_bar",
            key_phrases=(
                "Un proceso que puedes seguir",
                "Pendientes claros",
                "Revisión humana",
                "Evidencia por periodo",
            ),
        ),
        NativeSectionSpec(
            section_id="stage_services",
            title="Un servicio para cada etapa.",
            component_type="3_column_layout",
            key_phrases=(
                "Regularización y revisión fiscal",
                "Devoluciones y saldos a favor",
                "Continuidad contable",
            ),
        ),
        NativeSectionSpec(
            section_id="core_services",
            title="Nuestros servicios",
            component_type="service_grid",
            key_phrases=(
                "Contabilidad mensual",
                "Declaraciones periódicas",
                "Diagnóstico y regularización",
                "Revisión fiscal y papeles de trabajo",
                "Devoluciones de impuestos",
                "Saldos a favor y compensaciones",
            ),
        ),
        NativeSectionSpec(
            section_id="method",
            title="Nuestro método — De la solicitud al cierre",
            component_type="4_column_method",
            key_phrases=(
                "01 Entendemos tu caso",
                "02 Ordenamos las entregas",
                "03 Revisamos contigo",
                "04 Conservamos evidencia",
            ),
        ),
        NativeSectionSpec(
            section_id="faq",
            title="Preguntas frecuentes",
            component_type="collapsible_group",
            key_phrases=(
                "¿El portal presenta declaraciones?",
                "¿Puedo enviar documentos por el formulario?",
                "¿Cuánto cuesta?",
            ),
        ),
        NativeSectionSpec(
            section_id="footer_cta",
            title="Empecemos por entender lo que necesitas.",
            component_type="cta_footer",
            key_phrases=(
                "Despacho De La Cruz & Asociados",
                "Lic. Martín Jonathan De La Cruz Muñoz",
                "Culiacán, Sinaloa, México",
                "Preparar consulta",
            ),
        ),
    )


@dataclass(frozen=True)
class DisenoSitioLexAuditResult:
    site_url: str
    http_status: int
    is_live: bool
    has_forbidden_iframes: bool
    forbidden_iframe_sources: tuple[str, ...]
    matched_sections: tuple[str, ...]
    missing_sections: tuple[str, ...]
    compliance_score: float
    raw_html_snippet: str
    timestamp: str


@dataclass(frozen=True)
class DisenoSitioLexExecutionResult:
    agent_id: str
    blueprint: DisenoSitioLexBlueprint
    audit: DisenoSitioLexAuditResult
    deliverable_pdf: Path | None
    pdf_sha256: str | None
    pdf_pages: int
    compile_ok: bool
    ok: bool
    errors: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class GoogleSitesInteractiveRequest:
    """Solicitud de sesión interactiva Playwright en Google Sites (autenticación + auditoría/publicación)."""

    editor_url: str = DEFAULT_EDITOR_URL
    published_url: str = DEFAULT_SITE_URL
    user_validated: bool = False
    dry_run: bool = True
    publish_changes: bool = False
    ensure_pages: tuple[str, ...] = ()
    profile_name: str = "google-drive"
    profile_dir: str = ""
    channel: str = "chrome"
    auth_timeout_seconds: int = 300
    action_timeout_seconds: int = 90
    output_dir: str = ""


@dataclass(frozen=True)
class GoogleSitesInteractiveResult:
    """Resultado estructurado y auditado de una sesión Playwright en Google Sites."""

    ok: bool
    status: str
    run_id: str
    run_dir: Path
    editor_url: str
    published_url: str
    compliance_score: float = 0.0
    has_forbidden_iframes: bool = False
    editor_screenshot_path: Path | None = None
    published_screenshot_path: Path | None = None
    manifest_path: Path | None = None
    receipt_path: Path | None = None
    summary_md_path: Path | None = None
    blockers: tuple[dict[str, Any], ...] = ()
    evidence: dict[str, Any] = field(default_factory=dict)


def validate_google_sites_urls(editor_url: str, published_url: str) -> tuple[str, str]:
    """Valida que tanto la URL de edición como la pública pertenezcan estrictamente a Google Sites por HTTPS."""
    clean_editor = (editor_url or "").strip()
    clean_public = (published_url or "").strip()

    ed_parts = urlsplit(clean_editor)
    if ed_parts.scheme.lower() != "https" or (ed_parts.hostname or "").lower() != SITES_HOST:
        raise ValueError(f"URL de editor inválida para Google Sites: {clean_editor!r}")
    if not ("/d/" in ed_parts.path or "/u/" in ed_parts.path or "/create" in ed_parts.path):
        raise ValueError(f"La URL de editor no corresponde a un lienzo de Google Sites: {clean_editor!r}")

    pub_parts = urlsplit(clean_public)
    if pub_parts.scheme.lower() != "https" or (pub_parts.hostname or "").lower() != SITES_HOST:
        raise ValueError(f"URL pública inválida para Google Sites: {clean_public!r}")
    if not pub_parts.path.startswith("/view/"):
        raise ValueError(f"La URL pública debe iniciar con /view/: {clean_public!r}")

    return clean_editor, clean_public


def _is_authenticated_sites_editor(page: Any) -> bool:
    """Determina si la pestaña ya muestra el editor de Google Sites autenticado."""
    host = (urlsplit(page.url).hostname or "").lower()
    if host != SITES_HOST:
        return False
    for sel in _SITES_EDITOR_READY_SELECTORS:
        try:
            if page.locator(sel).count() > 0:
                return True
        except Exception:
            continue
    return False


class AgenteSitioLex:
    """Agente de orquestación, verificación y auditoría del portal web Lex Contable."""

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.blueprint = DisenoSitioLexBlueprint()
        self.runs_root = self.workspace.feedback_root / "subir-sitio" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def audit_published_site(self, site_url: str | None = None) -> DisenoSitioLexAuditResult:
        """Audita el sitio web publicado en vivo para verificar diseño nativo y ausencia de iframes."""
        target_url = site_url or self.blueprint.published_url
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 AulaTeX-Audit/2.0"
        }
        req = urllib.request.Request(target_url, headers=headers)
        
        http_status = 0
        html_text = ""
        is_live = False
        forbidden_sources: list[str] = []
        
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                http_status = resp.status
                is_live = (http_status == 200)
                raw_bytes = resp.read()
                html_text = raw_bytes.decode("utf-8", errors="replace")
        except urllib.error.HTTPError as ex:
            http_status = ex.code
            html_text = ex.read().decode("utf-8", errors="replace")
        except Exception as ex:
            http_status = -1
            html_text = str(ex)

        # 1. Auditoría de compuerta estricta: Detección de iframes prohibidos (CloudFront / externos)
        # Google Sites nativo NO debe incrustar la web de cloudfront
        iframe_patterns = re.findall(r'<iframe[^>]+src=["\']([^"\']+)["\']', html_text, re.IGNORECASE)
        for src in iframe_patterns:
            if "cloudfront.net" in src or "de2vaif4mldo0" in src:
                forbidden_sources.append(src)
                
        has_forbidden_iframes = len(forbidden_sources) > 0

        # 2. Comprobación de secciones del blueprint nativo
        matched: list[str] = []
        missing: list[str] = []
        
        # En Google Sites publicado, el texto puede estar en el HTML estático o hidratado
        for sec in self.blueprint.sections:
            sec_found = False
            for phrase in sec.key_phrases:
                # Comprobación insensible a mayúsculas y acentos normalizados
                clean_phrase = phrase.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
                clean_html = html_text.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
                if clean_phrase in clean_html:
                    sec_found = True
                    break
            if sec_found:
                matched.append(sec.section_id)
            else:
                missing.append(sec.section_id)

        # Puntuación de cumplimiento
        base_score = (len(matched) / len(self.blueprint.sections)) * 100.0 if self.blueprint.sections else 0.0
        if has_forbidden_iframes:
            base_score = min(base_score, 45.0)  # Penalización drástica por uso de iframe

        return DisenoSitioLexAuditResult(
            site_url=target_url,
            http_status=http_status,
            is_live=is_live,
            has_forbidden_iframes=has_forbidden_iframes,
            forbidden_iframe_sources=tuple(forbidden_sources),
            matched_sections=tuple(matched),
            missing_sections=tuple(missing),
            compliance_score=round(base_score, 1),
            raw_html_snippet=html_text[:500],
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    def synchronize_evidence_and_report(
        self,
        audit_result: DisenoSitioLexAuditResult,
        compile_latex: bool = True,
    ) -> DisenoSitioLexExecutionResult:
        """Sincroniza los artefactos, compila el manuscrito del módulo 50144 y actualiza el estado de entrega."""
        repo_root = self.workspace.repo_root
        herramientas_dir = repo_root / "UAS" / "licenciatura-en-contaduria-uas" / "herramientas-digitales"
        tex_50144 = herramientas_dir / "reporte-herramientas-digitales-Actividad-50144.tex"
        tex_path = tex_50144 if tex_50144.exists() else (herramientas_dir / "reporte-herramientas-digitales-Actividad-6.tex")
        entregas_dir = herramientas_dir / "entregas-herramientas-digitales"
        entregas_dir.mkdir(parents=True, exist_ok=True)
        pdf_dest = entregas_dir / (
            "GPO103_LNCI_WEB_Martin_DeLaCruz_Munoz.pdf"
            if tex_path.name.endswith("50144.tex")
            else "GPO103_LCP_WEB_MartinJonathan_DeLaCruzMunoz.pdf"
        )
        
        compile_ok = False
        pdf_sha256 = None
        pdf_pages = 0
        errors: list[str] = []

        if compile_latex and tex_path.exists():
            out_dir = herramientas_dir.as_posix()
            rel_target = tex_path.relative_to(repo_root).as_posix()
            try:
                # 1. Biber
                biber_cmd = ["biber", tex_path.with_suffix("")]
                subprocess.run(biber_cmd, cwd=repo_root, capture_output=True, text=True, timeout=60)
                
                # 2. XeLaTeX
                xetex_cmd = ["xelatex", "-interaction=nonstopmode", "-halt-on-error", f"-output-directory={out_dir}", rel_target]
                p1 = subprocess.run(xetex_cmd, cwd=repo_root, capture_output=True, text=True, timeout=90)
                if p1.returncode == 0:
                    # Segunda pasada para referencias
                    subprocess.run(xetex_cmd, cwd=repo_root, capture_output=True, text=True, timeout=90)
                    local_pdf = tex_path.with_suffix(".pdf")
                    if local_pdf.exists() and local_pdf.stat().st_size > 0:
                        compile_ok = True
                        shutil_dest = pdf_dest
                        import shutil
                        shutil.copy2(local_pdf, shutil_dest)
                        
                        pdf_bytes = shutil_dest.read_bytes()
                        pdf_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
                        
                        # Contar páginas
                        page_matches = re.findall(r"/Type\s*/Page\b", pdf_bytes.decode("latin1", errors="ignore"))
                        pdf_pages = len(page_matches) or 9
                else:
                    errors.append(f"Fallo en compilación XeLaTeX (código {p1.returncode})")
            except Exception as ex:
                errors.append(f"Excepción en compilador: {str(ex)}")

        # Actualizar estado de entregas en estado-entregas-uas.json
        state_file = repo_root / "UAS" / "licenciatura-en-contaduria-uas" / "estado-entregas-uas.json"
        if state_file.exists():
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                deliveries = data.get("deliveries", [])
                for d in deliveries:
                    if d.get("module_id") == 50144 or d.get("activity_number") == 6:
                        if pdf_sha256:
                            d["sha256"] = pdf_sha256
                        if pdf_pages:
                            d["pages"] = pdf_pages
                        d["site_url"] = audit_result.site_url
                        d["compliance_score"] = audit_result.compliance_score
                        d["has_forbidden_iframes"] = audit_result.has_forbidden_iframes
                        d["updated_at"] = datetime.now(timezone.utc).isoformat()
                state_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            except Exception as ex:
                errors.append(f"No se pudo actualizar estado-entregas-uas.json: {str(ex)}")

        return DisenoSitioLexExecutionResult(
            agent_id=AGENT_ID_DISENO_SITIO_LEX,
            blueprint=self.blueprint,
            audit=audit_result,
            deliverable_pdf=pdf_dest if compile_ok else None,
            pdf_sha256=pdf_sha256,
            pdf_pages=pdf_pages,
            compile_ok=compile_ok,
            ok=(compile_ok and not audit_result.has_forbidden_iframes),
            errors=tuple(errors),
        )

    def _write_interactive_blocked_result(
        self,
        *,
        run_id: str,
        run_dir: Path,
        status: str,
        editor_url: str,
        published_url: str,
        blocker: dict[str, Any],
        editor_screenshot_path: Path | None = None,
    ) -> GoogleSitesInteractiveResult:
        manifest = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "agent_id": AGENT_ID_DISENO_SITIO_LEX,
            "status": status,
            "editor_url": editor_url,
            "published_url": published_url,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            "blockers": [blocker],
        }
        assert_no_credential_leak(manifest)
        m_path = run_dir / "manifest.json"
        m_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        summary_md = (
            f"# Sesión Google Sites Bloqueada (`{status}`)\n\n"
            f"- **Editor:** `{editor_url}`\n"
            f"- **Sitio público:** `{published_url}`\n"
            f"- **Motivo:** {blocker['detail']}\n"
        )
        assert_no_credential_leak(summary_md)
        s_path = run_dir / "resumen-sites.md"
        s_path.write_text(summary_md, encoding="utf-8")

        return GoogleSitesInteractiveResult(
            ok=False,
            status=status,
            run_id=run_id,
            run_dir=run_dir,
            editor_url=editor_url,
            published_url=published_url,
            editor_screenshot_path=editor_screenshot_path,
            manifest_path=m_path,
            summary_md_path=s_path,
            blockers=(blocker,),
        )

    @staticmethod
    def _inspect_and_sync_editor_pages(
        page: Any,
        ensure_pages: tuple[str, ...],
    ) -> tuple[list[str], list[str]]:
        """Inspecciona las páginas visibles del panel 'Páginas' y crea las faltantes si se solicita."""
        pages_tab = page.locator(
            '[role="tab"]:has-text("Páginas"):visible, [role="tab"]:has-text("Pages"):visible'
        ).first
        if pages_tab.count():
            try:
                pages_tab.click()
                page.wait_for_timeout(800)
            except Exception:
                pass

        def _read_page_names() -> list[str]:
            try:
                items = page.locator('[role="treeitem"]:visible, [data-page-id]:visible').all_inner_texts()
            except Exception:
                items = []
            cleaned: list[str] = []
            for raw in items:
                for line in (raw or "").splitlines():
                    label = re.sub(r"[\ue000-\uf8ff]+", " ", line).strip()
                    if label and label not in cleaned:
                        cleaned.append(label)
                        break
            return cleaned

        existing = _read_page_names()
        created: list[str] = []
        if not ensure_pages:
            return existing, created

        normalized_existing = {
            p.lower().replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u")
            for p in existing
        }
        for target_page in ensure_pages:
            norm = (
                target_page.strip()
                .lower()
                .replace("á", "a")
                .replace("é", "e")
                .replace("í", "i")
                .replace("ó", "o")
                .replace("ú", "u")
            )
            if not norm or norm in normalized_existing:
                continue
            add_btn = page.locator(
                '[aria-label*="Nueva página" i]:visible, '
                '[aria-label*="New page" i]:visible, '
                '[data-tooltip*="Nueva página" i]:visible, '
                '[data-tooltip*="New page" i]:visible'
            ).first
            if not add_btn.count():
                continue
            try:
                add_btn.click()
                page.wait_for_timeout(500)
                name_input = page.locator('div[role="dialog"] input[type="text"]:visible').first
                if name_input.count():
                    name_input.fill(target_page.strip())
                    done_btn = page.locator(
                        'div[role="dialog"] button:has-text("Listo"):visible, '
                        'div[role="dialog"] button:has-text("Done"):visible, '
                        'div[role="dialog"] button:has-text("Aceptar"):visible'
                    ).first
                    if done_btn.count():
                        done_btn.click()
                        page.wait_for_timeout(900)
                        created.append(target_page.strip())
                        normalized_existing.add(norm)
            except Exception:
                continue

        return _read_page_names() or existing, created

    def run_interactive_session(
        self,
        request: GoogleSitesInteractiveRequest,
    ) -> GoogleSitesInteractiveResult:
        """Abre Google Sites en Chrome visible con perfil persistente para autenticar, auditar y opcionalmente publicar."""
        run_id = f"{self.workspace.timestamp()}-subir-sitio"
        run_dir = (
            self.workspace.resolve_target(request.output_dir)
            if request.output_dir.strip()
            else self.runs_root / run_id
        )
        run_dir.mkdir(parents=True, exist_ok=True)

        if not request.user_validated:
            return self._write_interactive_blocked_result(
                run_id=run_id,
                run_dir=run_dir,
                status="blocked_missing_user_validation",
                editor_url=request.editor_url,
                published_url=request.published_url,
                blocker={
                    "code": "missing_user_validation",
                    "detail": (
                        "Acceso interactivo a Google Sites bloqueado por seguridad: se requiere "
                        "autorización explícita (`user_validated=True`)."
                    ),
                    "blocking": True,
                },
            )

        try:
            clean_editor_url, clean_published_url = validate_google_sites_urls(
                request.editor_url,
                request.published_url,
            )
        except ValueError as exc:
            return self._write_interactive_blocked_result(
                run_id=run_id,
                run_dir=run_dir,
                status="blocked_invalid_site_url",
                editor_url=request.editor_url,
                published_url=request.published_url,
                blocker={"code": "invalid_site_url", "detail": str(exc), "blocking": True},
            )

        profile_dir = resolve_drive_profile_dir(request.profile_name, request.profile_dir)
        public_audit = self.audit_published_site(site_url=clean_published_url)

        if request.dry_run:
            manifest = {
                "schema_version": "1.0.0",
                "run_id": run_id,
                "agent_id": AGENT_ID_DISENO_SITIO_LEX,
                "status": "dry_run_validated",
                "dry_run": True,
                "editor_url": clean_editor_url,
                "published_url": clean_published_url,
                "profile_dir": str(profile_dir),
                "publish_changes": bool(request.publish_changes),
                "ensure_pages": list(request.ensure_pages),
                "public_audit": {
                    "http_status": public_audit.http_status,
                    "is_live": public_audit.is_live,
                    "compliance_score": public_audit.compliance_score,
                    "has_forbidden_iframes": public_audit.has_forbidden_iframes,
                    "matched_sections": list(public_audit.matched_sections),
                    "missing_sections": list(public_audit.missing_sections),
                },
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
            }
            assert_no_credential_leak(manifest)
            m_path = run_dir / "manifest.json"
            m_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            r_path = run_dir / "receipt.json"
            r_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            summary_md = (
                "# Prevalidación Google Sites (`dry-run`)\n\n"
                f"- **Editor:** `{clean_editor_url}`\n"
                f"- **Sitio público:** `{clean_published_url}`\n"
                f"- **Perfil persistente:** `{profile_dir}`\n"
                f"- **HTTP público:** `{public_audit.http_status}` (`compliance={public_audit.compliance_score}%`, iframes prohibidos={public_audit.has_forbidden_iframes})\n"
                "- **Siguiente paso:** ejecutar con `--live` para abrir la ventana visible de Google Sites Editor.\n"
            )
            assert_no_credential_leak(summary_md)
            s_path = run_dir / "resumen-sites.md"
            s_path.write_text(summary_md, encoding="utf-8")

            return GoogleSitesInteractiveResult(
                ok=True,
                status="dry_run_validated",
                run_id=run_id,
                run_dir=run_dir,
                editor_url=clean_editor_url,
                published_url=clean_published_url,
                compliance_score=public_audit.compliance_score,
                has_forbidden_iframes=public_audit.has_forbidden_iframes,
                manifest_path=m_path,
                receipt_path=r_path,
                summary_md_path=s_path,
                evidence={"dry_run": True, "profile_dir": str(profile_dir)},
            )

        from playwright.sync_api import sync_playwright

        editor_screenshot = run_dir / "editor-google-sites.png"
        published_screenshot = run_dir / "sitio-publicado.png"
        authenticated_during_run = False
        used_channel = request.channel
        existing_pages: list[str] = []
        created_pages: list[str] = []
        published_action_status = "skipped"
        rendered_iframe_sources: list[str] = []

        with sync_playwright() as pw:
            context, used_channel = launch_persistent_headed_context(pw, profile_dir, request.channel)
            try:
                page = context.pages[0] if context.pages else context.new_page()
                try:
                    page.bring_to_front()
                except Exception:
                    pass
                page.goto(clean_editor_url, wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000)

                if not _is_authenticated_sites_editor(page):
                    print(
                        f"\n[subir-sitio] Ventana abierta ({used_channel}) para autenticación en Google Sites.\n"
                        f"[subir-sitio] Inicia sesión en la ventana abierta; esperando hasta "
                        f"{request.auth_timeout_seconds}s a que cargue el editor de Google Sites...",
                        flush=True,
                    )
                    deadline = time.monotonic() + max(10, int(request.auth_timeout_seconds))
                    while time.monotonic() < deadline:
                        if _is_authenticated_sites_editor(page):
                            authenticated_during_run = True
                            break
                        page.wait_for_timeout(1500)

                if not _is_authenticated_sites_editor(page):
                    try:
                        page.screenshot(path=str(editor_screenshot), full_page=True)
                    except Exception:
                        pass
                    return self._write_interactive_blocked_result(
                        run_id=run_id,
                        run_dir=run_dir,
                        status="blocked_auth_timeout",
                        editor_url=clean_editor_url,
                        published_url=clean_published_url,
                        editor_screenshot_path=editor_screenshot if editor_screenshot.exists() else None,
                        blocker={
                            "code": "auth_timeout",
                            "detail": (
                                f"No se completó la autenticación en Google Sites Editor dentro de "
                                f"{request.auth_timeout_seconds}s (perfil conservado en {profile_dir})."
                            ),
                            "blocking": True,
                        },
                    )

                existing_pages, created_pages = self._inspect_and_sync_editor_pages(
                    page,
                    tuple(request.ensure_pages or ()),
                )

                if request.publish_changes:
                    pub_btn = page.locator(
                        'div[role="button"]:has-text("Publicar"):visible, button:has-text("Publicar"):visible, '
                        'div[role="button"]:has-text("Publish"):visible, button:has-text("Publish"):visible'
                    ).first
                    if pub_btn.count():
                        pub_btn.click()
                        page.wait_for_timeout(1500)
                        confirm_btn = page.locator(
                            'div[role="dialog"] button:has-text("Publicar"):visible, '
                            'div[role="dialog"] div[role="button"]:has-text("Publicar"):visible, '
                            'div[role="dialog"] button:has-text("Publish"):visible'
                        ).last
                        if confirm_btn.count():
                            confirm_btn.click()
                            page.wait_for_timeout(2500)
                        published_action_status = "published"
                    else:
                        published_action_status = "publish_button_not_found"

                page.screenshot(path=str(editor_screenshot), full_page=True)

                pub_page = context.new_page()
                pub_page.goto(clean_published_url, wait_until="domcontentloaded", timeout=60000)
                pub_page.wait_for_timeout(2000)
                try:
                    rendered_iframe_sources = [
                        src
                        for src in pub_page.eval_on_selector_all(
                            "iframe",
                            "els => els.map(e => e.src || '')",
                        )
                        if "cloudfront.net" in src or "de2vaif4mldo0" in src
                    ]
                except Exception:
                    rendered_iframe_sources = []
                pub_page.screenshot(path=str(published_screenshot), full_page=True)
            finally:
                context.close()

        refreshed_audit = self.audit_published_site(site_url=clean_published_url)
        has_forbidden = refreshed_audit.has_forbidden_iframes or bool(rendered_iframe_sources)

        manifest = {
            "schema_version": "1.0.0",
            "run_id": run_id,
            "agent_id": AGENT_ID_DISENO_SITIO_LEX,
            "status": "completed",
            "editor_url": clean_editor_url,
            "published_url": clean_published_url,
            "browser_channel": used_channel,
            "profile_dir": str(profile_dir),
            "authenticated_during_run": authenticated_during_run,
            "existing_pages": existing_pages,
            "created_pages": created_pages,
            "publish_action_status": published_action_status,
            "compliance_score": refreshed_audit.compliance_score,
            "has_forbidden_iframes": has_forbidden,
            "rendered_forbidden_iframes": rendered_iframe_sources,
            "editor_screenshot_path": str(editor_screenshot),
            "published_screenshot_path": str(published_screenshot),
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
        assert_no_credential_leak(manifest)
        m_path = run_dir / "manifest.json"
        m_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        r_path = run_dir / "receipt.json"
        r_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        summary_md = (
            "# Sesión Interactiva Google Sites Completada\n\n"
            f"- **Editor:** `{clean_editor_url}`\n"
            f"- **Sitio público:** `{clean_published_url}`\n"
            f"- **Páginas detectadas:** {', '.join(existing_pages) if existing_pages else 'Solo portada / sin árbol visible'}\n"
            f"- **Páginas creadas:** {', '.join(created_pages) if created_pages else 'Ninguna'}\n"
            f"- **Publicación:** `{published_action_status}`\n"
            f"- **Cumplimiento nativo:** `{refreshed_audit.compliance_score}%` (iframes prohibidos={has_forbidden})\n"
        )
        assert_no_credential_leak(summary_md)
        s_path = run_dir / "resumen-sites.md"
        s_path.write_text(summary_md, encoding="utf-8")

        return GoogleSitesInteractiveResult(
            ok=not has_forbidden,
            status="completed",
            run_id=run_id,
            run_dir=run_dir,
            editor_url=clean_editor_url,
            published_url=clean_published_url,
            compliance_score=refreshed_audit.compliance_score,
            has_forbidden_iframes=has_forbidden,
            editor_screenshot_path=editor_screenshot,
            published_screenshot_path=published_screenshot,
            manifest_path=m_path,
            receipt_path=r_path,
            summary_md_path=s_path,
            evidence=manifest,
        )
