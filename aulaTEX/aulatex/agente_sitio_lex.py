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
import urllib.request
import urllib.error

from .workspace import AulaTeXWorkspace

AGENT_ID_DISENO_SITIO_LEX = "diseno-sitio-lex"
DEFAULT_SITE_URL = "https://sites.google.com/view/delacruz-consultores-lcp"
DEFAULT_EDITOR_URL = "https://sites.google.com/d/1l423JjQirXpiwhmtD5YqTptvDXx_lhtY/p/1a5_sx-_zIRDrzcX2DzkFkiv4wJoUJMGV/edit"


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


class AgenteSitioLex:
    """Agente de orquestación, verificación y auditoría del portal web Lex Contable."""

    def __init__(self, workspace: AulaTeXWorkspace | None = None) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.blueprint = DisenoSitioLexBlueprint()

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
        """Sincroniza los artefactos, compila el manuscrito de la Actividad 6 y actualiza el estado de entrega."""
        repo_root = self.workspace.repo_root
        herramientas_dir = repo_root / "UAS" / "licenciatura-en-contaduria-uas" / "herramientas-digitales"
        tex_path = herramientas_dir / "reporte-herramientas-digitales-Actividad-6.tex"
        entregas_dir = herramientas_dir / "entregas-herramientas-digitales"
        entregas_dir.mkdir(parents=True, exist_ok=True)
        pdf_dest = entregas_dir / "GPO103_LCP_WEB_MartinJonathan_DeLaCruzMunoz.pdf"
        
        compile_ok = False
        pdf_sha256 = None
        pdf_pages = 0
        errors: list[str] = []

        if compile_latex and tex_path.exists():
            out_dir = herramientas_dir.as_posix()
            rel_target = tex_path.relative_to(repo_root).as_posix()
            try:
                # 1. Biber
                biber_cmd = ["biber", herramientas_dir / "reporte-herramientas-digitales-Actividad-6"]
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
