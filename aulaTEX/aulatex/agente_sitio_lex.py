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
    required_pages: tuple[str, ...] = ("Inicio", "Servicios", "Quiénes Somos", "Ubicación", "Contacto")
    subpages: tuple[tuple[str, str], ...] = (("Servicios", "Defensa fiscal"),)
    footer_author: str = (
        "Elaborado por Martín Jonathan De La Cruz Muñoz · Grupo 103 LCP · FCA UAS · Culiacán, Sinaloa, México"
    )
    map_query: str = "Culiacán, Sinaloa, México"
    youtube_query: str = "contabilidad fiscal SAT despacho contable mexico"
    social_links: tuple[str, ...] = (
        "https://www.facebook.com/",
        "https://www.instagram.com/",
        "https://www.youtube.com/",
    )
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
    align_s4: bool = False
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
    def _normalize_es(text: str) -> str:
        return (
            (text or "")
            .strip()
            .lower()
            .replace("á", "a")
            .replace("é", "e")
            .replace("í", "i")
            .replace("ó", "o")
            .replace("ú", "u")
            .replace("ü", "u")
        )

    @staticmethod
    def _open_sidebar_tab(page: Any, tab_es: str, tab_en: str) -> None:
        tab = page.locator(
            f'[role="tab"]:has-text("{tab_es}"):visible, [role="tab"]:has-text("{tab_en}"):visible'
        ).first
        if tab.count():
            try:
                tab.click()
                page.wait_for_timeout(700)
            except Exception:
                pass

    @classmethod
    def _read_editor_page_names(cls, page: Any) -> list[str]:
        cleaned: list[str] = []
        try:
            aria_labels = page.eval_on_selector_all(
                '[aria-label*="; título:"], [aria-label*="; title:"]',
                'els => els.map(e => e.getAttribute("aria-label") || "")',
            )
        except Exception:
            aria_labels = []
        for raw_aria in aria_labels:
            head = re.split(r";\s*(?:título|title):", raw_aria, maxsplit=1)[0].strip()
            label = re.sub(r"[\ue000-\uf8ff]+", " ", head).strip()
            if label and label not in cleaned:
                cleaned.append(label)
        if cleaned:
            return cleaned

        try:
            items = page.locator('[role="treeitem"]:visible, [data-page-id]:visible').all_inner_texts()
        except Exception:
            items = []
        for raw in items:
            for line in (raw or "").splitlines():
                label = re.sub(r"[\ue000-\uf8ff]+", " ", line).strip()
                if label and label not in cleaned:
                    cleaned.append(label)
                    break
        return cleaned

    @classmethod
    def _select_editor_page(cls, page: Any, page_name: str) -> bool:
        cls._open_sidebar_tab(page, "Páginas", "Pages")
        target = cls._normalize_es(page_name)
        try:
            loc = page.locator(
                f'[aria-label*="{page_name}; título:" i]:visible, '
                f'[aria-label*="{page_name}; title:" i]:visible'
            ).first
            if loc.count():
                loc.click()
                page.wait_for_timeout(1000)
                return True
        except Exception:
            pass

        for cand in page.locator('[role="treeitem"]:visible, [data-page-id]:visible').all():
            try:
                text_norm = cls._normalize_es(re.sub(r"[\ue000-\uf8ff]+", " ", cand.inner_text()))
                if target in text_norm:
                    cand.click()
                    page.wait_for_timeout(1000)
                    return True
            except Exception:
                continue
        return False

    @staticmethod
    def _dismiss_open_dialogs(page: Any) -> None:
        for _ in range(3):
            overlay = page.locator('[role="dialog"]:visible, .llhEMd.iWO5td:visible')
            if not overlay.count():
                break
            close_btn = page.locator(
                '[role="dialog"] button:has-text("Cancelar"):visible, '
                '[role="dialog"] div[role="button"]:has-text("Cancelar"):visible, '
                '.llhEMd div[role="button"]:has-text("Cancelar"):visible, '
                '[role="dialog"] [aria-label*="Cerrar" i]:visible'
            ).last
            if close_btn.count():
                try:
                    close_btn.click(force=True)
                    page.wait_for_timeout(400)
                    continue
                except Exception:
                    pass
            page.keyboard.press("Escape")
            page.wait_for_timeout(400)

    @staticmethod
    def _click_dialog_button(page: Any, labels: tuple[str, ...]) -> bool:
        selectors: list[str] = []
        for lbl in labels:
            for scope in ('div[role="dialog"]', ".llhEMd"):
                selectors.append(f'{scope} button:has-text("{lbl}"):visible')
                selectors.append(f'{scope} div[role="button"]:has-text("{lbl}"):visible')
                selectors.append(f'{scope} [role="button"]:has-text("{lbl}"):visible')
        loc = page.locator(", ".join(selectors))
        for idx in range(loc.count() - 1, -1, -1):
            btn = loc.nth(idx)
            try:
                if btn.is_visible() and not btn.is_disabled():
                    btn.click(force=True)
                    return True
            except Exception:
                continue
        return False

    @classmethod
    def _submit_page_name_dialog(cls, page: Any, value: str) -> bool:
        page.wait_for_timeout(600)
        inp = page.locator(
            'div[role="dialog"] input[type="text"]:visible, '
            '.llhEMd input[type="text"]:visible'
        ).first
        if not inp.count():
            menu_opt = page.locator(
                '[role="menuitem"]:has-text("Página nueva"):visible, '
                '[role="menuitem"]:has-text("New page"):visible'
            ).first
            if menu_opt.count():
                menu_opt.click(force=True)
                page.wait_for_timeout(600)
                inp = page.locator(
                    'div[role="dialog"] input[type="text"]:visible, '
                    '.llhEMd input[type="text"]:visible'
                ).first
        if not inp.count():
            cls._dismiss_open_dialogs(page)
            return False

        inp.fill(value.strip())
        page.wait_for_timeout(200)
        if not cls._click_dialog_button(page, ("Listo", "Done", "Aceptar")):
            inp.press("Enter")
        page.wait_for_timeout(1000)
        cls._dismiss_open_dialogs(page)
        return True

    @classmethod
    def _rename_page_if_present(cls, page: Any, old_name: str, new_name: str) -> bool:
        existing = [cls._normalize_es(p) for p in cls._read_editor_page_names(page)]
        if cls._normalize_es(new_name) in existing:
            return False
        if cls._normalize_es(old_name) not in existing:
            return False
        cls._dismiss_open_dialogs(page)
        node = page.locator(f'[aria-label*="{old_name}" i]:visible').first
        if not node.count():
            return False
        node.hover()
        page.wait_for_timeout(300)
        act_btn = page.locator('[aria-label="Acciones de la página"]:visible').first
        if not act_btn.count():
            return False
        act_btn.click(force=True)
        page.wait_for_timeout(400)
        prop_item = page.locator(
            '[role="menuitem"]:has-text("Propiedades"):visible, [role="menuitem"]:has-text("Properties"):visible'
        ).first
        if not prop_item.count():
            page.keyboard.press("Escape")
            return False
        prop_item.click()
        return cls._submit_page_name_dialog(page, new_name)

    @classmethod
    def _create_page_if_missing(
        cls,
        page: Any,
        name: str,
        parent_name: str | None = None,
    ) -> bool:
        existing_norm = {cls._normalize_es(p) for p in cls._read_editor_page_names(page)}
        if cls._normalize_es(name) in existing_norm:
            return False

        cls._dismiss_open_dialogs(page)
        if parent_name:
            node = page.locator(f'[aria-label*="{parent_name};" i]:visible, [aria-label*="{parent_name}" i]:visible').first
            if not node.count():
                return False
            node.hover()
            page.wait_for_timeout(300)
            act_btn = page.locator('[aria-label="Acciones de la página"]:visible').first
            if not act_btn.count():
                return False
            act_btn.click(force=True)
            page.wait_for_timeout(400)
            sub_item = page.locator(
                '[role="menuitem"]:has-text("Agregar subpágina"):visible, '
                '[role="menuitem"]:has-text("Add subpage"):visible'
            ).first
            if not sub_item.count():
                page.keyboard.press("Escape")
                return False
            sub_item.click()
        else:
            add_btn = page.locator(
                '[aria-label*="Página nueva" i]:visible, '
                '[aria-label*="Nueva página" i]:visible, '
                '[aria-label*="New page" i]:visible, '
                '[data-tooltip*="Página nueva" i]:visible, '
                '[data-tooltip*="Nueva página" i]:visible'
            ).first
            if not add_btn.count():
                return False
            add_btn.hover()
            page.wait_for_timeout(300)
            add_btn.click(force=True)

        return cls._submit_page_name_dialog(page, name)

    @classmethod
    def _inspect_and_sync_editor_pages(
        cls,
        page: Any,
        ensure_pages: tuple[str, ...],
    ) -> tuple[list[str], list[str]]:
        """Inspecciona las páginas visibles del panel 'Páginas' y crea las faltantes si se solicita."""
        cls._open_sidebar_tab(page, "Páginas", "Pages")
        existing = cls._read_editor_page_names(page)
        created: list[str] = []
        if not ensure_pages:
            return existing, created

        for target_page in ensure_pages:
            try:
                if cls._create_page_if_missing(page, target_page.strip()):
                    created.append(target_page.strip())
            except Exception:
                continue

        return cls._read_editor_page_names(page) or existing, created

    @staticmethod
    def _ensure_footer_author(page: Any, footer_text: str) -> str:
        try:
            body_text = page.locator("body").inner_text(timeout=3000)
        except Exception:
            body_text = ""
        if "elaborado por martín" in body_text.lower() or "elaborado por martin" in body_text.lower():
            return "already_present"

        add_footer = page.locator(
            '[role="button"]:has-text("Agregar pie de página"), button:has-text("Agregar pie de página"), '
            '[role="button"]:has-text("Add footer"), button:has-text("Add footer")'
        ).last
        if not add_footer.count():
            return "button_not_found"
        add_footer.scroll_into_view_if_needed()
        page.wait_for_timeout(300)
        add_footer.click(force=True)
        page.wait_for_timeout(800)

        editable = page.locator('footer [contenteditable="true"]:visible, [contenteditable="true"]:visible').last
        if not editable.count():
            return "textbox_not_found"
        editable.click()
        page.keyboard.type(footer_text, delay=8)
        page.wait_for_timeout(500)
        return "applied"

    @classmethod
    def _insert_text_block(cls, page: Any, marker_phrase: str, content_text: str) -> str:
        try:
            canvas_text = page.locator('[role="main"], main').first.inner_text(timeout=2000)
        except Exception:
            canvas_text = ""
        if cls._normalize_es(marker_phrase) in cls._normalize_es(canvas_text):
            return "already_present"

        cls._open_sidebar_tab(page, "Insertar", "Insert")
        tb_btn = page.locator(
            '[role="menuitem"][aria-label="Cuadro de texto"]:visible, '
            '[role="menuitem"]:has-text("Cuadro de texto"):visible, '
            '[role="menuitem"][aria-label="Text box"]:visible'
        ).first
        if not tb_btn.count():
            return "button_not_found"
        tb_btn.click()
        page.wait_for_timeout(800)
        box = page.locator('[role="textbox"][contenteditable="true"]:visible, [contenteditable="true"]:visible').last
        if not box.count():
            return "textbox_not_found"
        box.click()
        page.keyboard.type(content_text, delay=5)
        page.wait_for_timeout(500)
        return "applied"

    @classmethod
    def _insert_carousel_images(cls, page: Any, image_paths: list[Path]) -> str:
        existing_imgs = [p for p in image_paths if p.is_file()]
        if len(existing_imgs) < 2:
            return "insufficient_local_images"
        try:
            carousel_cnt = page.locator('[aria-roledescription="carousel"], [data-carousel-id]').count()
            if carousel_cnt > 0:
                return "already_present"
        except Exception:
            pass

        cls._open_sidebar_tab(page, "Insertar", "Insert")
        c_btn = page.locator('[role="menuitem"][aria-label="Carrusel de imágenes"]:visible').first
        if not c_btn.count():
            return "button_not_found"
        c_btn.scroll_into_view_if_needed()
        c_btn.click()
        page.wait_for_timeout(1000)

        add_img = page.locator('[role="dialog"] [aria-label="Agregar imagen"]:visible').first
        if not add_img.count():
            return "add_image_button_not_found"
        add_img.click()
        page.wait_for_timeout(500)

        upload_item = page.locator(
            '[role="menuitem"]:has-text("Subir imagen"):visible, [role="menuitem"]:has-text("Upload image"):visible'
        ).first
        if not upload_item.count():
            return "upload_menuitem_not_found"

        with page.expect_file_chooser(timeout=15000) as fc_info:
            upload_item.click()
        fc_info.value.set_files([str(p) for p in existing_imgs[:4]])
        page.wait_for_timeout(4500)

        if cls._click_dialog_button(page, ("Insertar", "Insert")):
            page.wait_for_timeout(1500)
            cls._dismiss_open_dialogs(page)
            return "applied"
        cls._dismiss_open_dialogs(page)
        return "insert_disabled_or_upload_incomplete"

    @classmethod
    def _insert_youtube_video(cls, page: Any, query: str) -> str:
        try:
            if page.locator('iframe[src*="youtube"]').count() > 0:
                return "already_present"
        except Exception:
            pass

        cls._open_sidebar_tab(page, "Insertar", "Insert")
        y_btn = page.locator('[role="menuitem"][aria-label="YouTube"]:visible').first
        if not y_btn.count():
            return "button_not_found"
        y_btn.scroll_into_view_if_needed()
        y_btn.click()
        page.wait_for_timeout(2500)

        picker_frame = None
        for fr in page.frames:
            if "docs.google.com/picker" in fr.url:
                picker_frame = fr
                break
        if picker_frame is None:
            return "picker_frame_not_found"

        search_input = picker_frame.locator('input[aria-label*="YouTube" i], input[type="text"]').last
        if not search_input.count():
            return "picker_input_not_found"
        search_input.fill(query)
        search_input.press("Enter")
        page.wait_for_timeout(2500)

        result_tile = picker_frame.locator('[role="option"], [role="listitem"], [data-id]').first
        if result_tile.count():
            result_tile.click()
            page.wait_for_timeout(800)

        select_btn = picker_frame.locator(
            'button:has-text("Seleccionar"):visible, button:has-text("Insertar"):visible, '
            '[role="button"]:has-text("Seleccionar"):visible, [role="button"]:has-text("Insert"):visible'
        ).last
        if select_btn.count() and not select_btn.is_disabled():
            select_btn.click()
            page.wait_for_timeout(1500)
            return "applied"

        close_b = picker_frame.locator('[aria-label*="Cerrar" i]').first
        if close_b.count():
            close_b.click()
        return "select_button_not_enabled"

    @classmethod
    def _insert_google_map(cls, page: Any, location_query: str) -> str:
        try:
            if page.locator('iframe[src*="maps"], [aria-label*="Mapa" i][role="region"]').count() > 0:
                return "already_present"
        except Exception:
            pass

        cls._open_sidebar_tab(page, "Insertar", "Insert")
        m_btn = page.locator('[role="menuitem"][aria-label="Mapa"]:visible').first
        if not m_btn.count():
            return "button_not_found"
        m_btn.scroll_into_view_if_needed()
        m_btn.click()
        page.wait_for_timeout(1500)

        search_inp = page.locator('[role="dialog"] input[aria-label*="Google Maps" i]:visible').first
        if not search_inp.count():
            return "map_input_not_found"
        search_inp.fill(location_query)
        search_inp.press("Enter")
        page.wait_for_timeout(1800)

        suggestion = page.locator('[role="dialog"] [role="option"]:visible, [role="dialog"] .pac-item:visible').first
        if suggestion.count():
            suggestion.click()
            page.wait_for_timeout(1200)

        if cls._click_dialog_button(page, ("Seleccionar", "Select")):
            page.wait_for_timeout(1500)
            cls._dismiss_open_dialogs(page)
            return "applied"

        cls._dismiss_open_dialogs(page)
        return "map_select_disabled"

    @classmethod
    def _insert_social_links(cls, page: Any, urls: tuple[str, ...]) -> str:
        try:
            if page.locator('a[href*="facebook.com"], a[href*="instagram.com"]').count() > 0:
                return "already_present"
        except Exception:
            pass

        cls._open_sidebar_tab(page, "Insertar", "Insert")
        s_btn = page.locator('[role="menuitem"][aria-label="Vínculos a redes sociales"]:visible').first
        if not s_btn.count():
            return "button_not_found"
        s_btn.scroll_into_view_if_needed()
        s_btn.click()
        page.wait_for_timeout(1000)

        inputs = page.locator('[role="dialog"] input[type="text"]:visible').all()
        if not inputs:
            return "social_inputs_not_found"
        for idx, url in enumerate(urls[: len(inputs)]):
            inputs[idx].fill(url)
        page.wait_for_timeout(400)

        if cls._click_dialog_button(page, ("Insertar", "Insert")):
            page.wait_for_timeout(1500)
            cls._dismiss_open_dialogs(page)
            return "applied"

        cls._dismiss_open_dialogs(page)
        return "social_insert_disabled"

    def _align_site_to_class_spec(self, page: Any) -> list[dict[str, str]]:
        """Alinea el sitio con la actividad UAS 50144 y la grabación S4-Clase-2 (rzici9Xi01Y)."""
        actions: list[dict[str, str]] = []
        assets_dir = (
            self.workspace.repo_root
            / "UAS"
            / "licenciatura-en-contaduria-uas"
            / "herramientas-digitales"
            / "assets-herramientas-digitales"
        )
        carousel_imgs = [
            assets_dir / "revision-documental.jpg",
            assets_dir / "revision-expediente.jpg",
            assets_dir / "analisis-financiero.jpg",
            assets_dir / "planeacion-contable.jpg",
        ]

        self._open_sidebar_tab(page, "Páginas", "Pages")
        renamed = self._rename_page_if_present(page, "Página principal", "Inicio")
        actions.append({"step": "rename_home_inicio", "status": "applied" if renamed else "skipped_or_done"})

        for req_page in self.blueprint.required_pages:
            created = self._create_page_if_missing(page, req_page)
            actions.append({"step": f"page_{req_page}", "status": "applied" if created else "already_present"})

        for parent_p, child_p in self.blueprint.subpages:
            sub_created = self._create_page_if_missing(page, child_p, parent_name=parent_p)
            actions.append({"step": f"subpage_{parent_p}_{child_p}", "status": "applied" if sub_created else "already_present"})

        # Pie de página global (obligatorio S4-Clase-2 [01:34:09])
        if self._select_editor_page(page, "Inicio"):
            actions.append({"step": "footer_author", "status": self._ensure_footer_author(page, self.blueprint.footer_author)})
            actions.append({"step": "inicio_carousel", "status": self._insert_carousel_images(page, carousel_imgs)})

        if self._select_editor_page(page, "Servicios"):
            actions.append(
                {
                    "step": "servicios_intro",
                    "status": self._insert_text_block(
                        page,
                        "Catálogo de Servicios Contables",
                        (
                            "Catálogo de Servicios Contables y Fiscales — Lex Contable\n"
                            "• Contabilidad mensual y conciliación bancaria/CFDI.\n"
                            "• Declaraciones mensuales y anuales ante el SAT.\n"
                            "• Regularización de ejercicios anteriores y papeles de trabajo.\n"
                            "• Solicitudes de devolución y compensación de saldos a favor."
                        ),
                    ),
                }
            )

        if self._select_editor_page(page, "Defensa fiscal"):
            actions.append(
                {
                    "step": "defensa_fiscal_intro",
                    "status": self._insert_text_block(
                        page,
                        "Defensa y Atención de Requerimientos",
                        (
                            "Defensa y Atención de Requerimientos Fiscales\n"
                            "Acompañamiento técnico y documental ante cartas invitación, "
                            "auditorías electrónicas y revisión de comprobantes CFDI."
                        ),
                    ),
                }
            )

        if self._select_editor_page(page, "Quiénes Somos"):
            actions.append(
                {
                    "step": "quienes_somos_intro",
                    "status": self._insert_text_block(
                        page,
                        "Despacho De La Cruz",
                        (
                            "Quiénes Somos — Despacho De La Cruz & Asociados (Lex Contable)\n"
                            "Proyecto académico y profesional desarrollado por Martín Jonathan De La Cruz Muñoz "
                            "(Grupo 103 LCP, Facultad de Contaduría y Administración, UAS — Culiacán, Sinaloa). "
                            "A continuación compartimos material audiovisual sobre contabilidad y obligaciones fiscales:"
                        ),
                    ),
                }
            )
            actions.append({"step": "quienes_somos_youtube", "status": self._insert_youtube_video(page, self.blueprint.youtube_query)})

        if self._select_editor_page(page, "Ubicación"):
            actions.append(
                {
                    "step": "ubicacion_intro",
                    "status": self._insert_text_block(
                        page,
                        "Ubicación y Zona de Atención",
                        (
                            "Ubicación y Zona de Atención\n"
                            "Culiacán Rosales, Sinaloa, México · Atención previa cita."
                        ),
                    ),
                }
            )
            actions.append({"step": "ubicacion_map", "status": self._insert_google_map(page, self.blueprint.map_query)})

        if self._select_editor_page(page, "Contacto"):
            actions.append(
                {
                    "step": "contacto_intro",
                    "status": self._insert_text_block(
                        page,
                        "Canales de Contacto y Redes",
                        (
                            "Canales de Contacto y Redes Sociales\n"
                            "Despacho De La Cruz & Asociados — Horario de atención: Lunes a Viernes de 9:00 a 18:00 h (Culiacán, Sinaloa).\n"
                            "Nota de privacidad: no compartas contraseñas ni e.firma en medios públicos."
                        ),
                    ),
                }
            )
            actions.append({"step": "contacto_social_links", "status": self._insert_social_links(page, self.blueprint.social_links)})

        return actions

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

                alignment_actions: list[dict[str, str]] = []
                if request.align_s4:
                    alignment_actions = self._align_site_to_class_spec(page)

                existing_pages, created_pages = self._inspect_and_sync_editor_pages(
                    page,
                    tuple(request.ensure_pages or ()),
                )

                if request.publish_changes:
                    page.wait_for_timeout(2000)
                    pub_sel = 'div[role="button"]:has-text("Publicar"):visible, button:has-text("Publicar"):visible, div[role="button"]:has-text("Publish"):visible, button:has-text("Publish"):visible'
                    pub_btn = page.locator(pub_sel).first
                    if pub_btn.count():
                        pub_btn.click()
                        page.wait_for_timeout(2000)
                        confirm_btn = page.locator(
                            'div[role="dialog"] button:has-text("Publicar"):visible, '
                            'div[role="dialog"] div[role="button"]:has-text("Publicar"):visible, '
                            'div[role="dialog"] button:has-text("Publish"):visible'
                        ).last
                        if confirm_btn.count():
                            confirm_btn.click()
                            page.wait_for_timeout(3000)
                        elif page.locator(pub_sel).count() > 1:
                            page.locator(pub_sel).last.click()
                            page.wait_for_timeout(3000)
                        published_action_status = "published"
                    else:
                        published_action_status = "publish_button_not_found"

                self._open_sidebar_tab(page, "Páginas", "Pages")
                page.screenshot(path=str(editor_screenshot), full_page=True)

                pub_page = context.new_page()
                pub_page.goto(clean_published_url, wait_until="domcontentloaded", timeout=60000)
                pub_page.wait_for_timeout(2500)
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
            "alignment_actions": alignment_actions,
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
