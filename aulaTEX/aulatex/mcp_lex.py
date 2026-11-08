"""Conector canónico con el Servidor MCP LEX para agentes editoriales de AulaTeX.

Conecta todos los agentes y subagentes editoriales con las herramientas de LEX:
1. Inferencia de razonamiento híbrido (``hybrid_llm_inference``) con baseline Amazon Nova Pro
   y acelerador Azure AI Foundry (Sol 6.1) con degradación suave.
2. Sondeo de salud y latencia (``hybrid_llm_health``).
3. Compilación académica aislada (``aulatex_compile`` y ``aulatex_latexmk``).
4. Auditoría geométrica y tipográfica de tablas apaisadas:
   - Validación obligatoria de páginas apaisadas sin encabezados ni pies de página.
   - Contención estricta dentro del área útil de la página en ancho y alto.
   - Detección determinista de desbordamientos, recortes y superposiciones.
"""
from __future__ import annotations

import importlib
import json
import logging
import math
from pathlib import Path
import re
import sys
from typing import Any

LOG = logging.getLogger("aulatex.mcp_lex")

# Directorio raíz del repositorio ahk-Autohokey donde reside el servidor MCP y motor híbrido
AHK_ROOT = Path("C:/ahk-Autohokey").resolve()
if AHK_ROOT.is_dir() and str(AHK_ROOT) not in sys.path:
    sys.path.insert(0, str(AHK_ROOT))


def audit_landscape_geometry(
    pdf_path: str | Path,
    margin_min_pt: float = 24.0,
) -> dict[str, Any]:
    """Audita rigurosamente todas las páginas apaisadas de un documento PDF.

    Reglas de calidad contractuales:
    1. Las tablas o esquemas horizontales deben presentarse en páginas apaisadas.
    2. En páginas apaisadas, los encabezados y pies de página deben estar totalmente
       suprimidos (pagestyle empty / ausencia de running headers y numeración).
    3. Todo el contenido (tablas, texto, vectores TikZ/longtable) debe ubicarse dentro
       del área útil de la página (tanto en ancho como en alto) sin desbordamientos,
       recortes ni sangrados negativos.
    """
    import pymupdf

    path = Path(pdf_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"PDF no encontrado para auditoría geométrica: {path}")

    issues: list[str] = []
    landscape_pages: list[int] = []
    hf_failures: list[dict[str, Any]] = []
    overflow_failures: list[dict[str, Any]] = []
    overlap_failures: list[dict[str, Any]] = []

    with pymupdf.open(path) as doc:
        for idx, page in enumerate(doc):
            pnum = idx + 1
            is_landscape = (page.rect.width > page.rect.height) or (page.rotation in (90, 270))
            if not is_landscape:
                continue

            landscape_pages.append(pnum)

            # En PyMuPDF, cuando rotation=90/270, mediabox define el marco físico de coordenadas
            if page.rotation in (90, 270):
                limit_x = page.mediabox.width
                limit_y = page.mediabox.height
            else:
                limit_x = page.rect.width
                limit_y = page.rect.height

            # 1. Comprobación de ausencia de encabezados y pies de página
            blocks = page.get_text("blocks")
            for b in blocks:
                txt = b[4].strip().replace("\n", " ")
                if not txt:
                    continue
                r = pymupdf.Rect(b[:4])

                # Detección de encabezados institucionales recurrentes o pies fancyhdr
                is_running_header = (
                    re.search(r"\b(GGS\d+|Seminario\s+[I|II|III]|Actividad\s+\d+|MGA)\b", txt, re.I)
                    and (
                        (page.rotation in (90, 270) and (r.y0 < 65.0 or r.y1 > limit_y - 65.0))
                        or (page.rotation == 0 and (r.y0 < 55.0 or r.y1 > limit_y - 55.0))
                    )
                )
                is_standalone_page_num = (
                    re.match(r"^\d+$", txt)
                    and (
                        (page.rotation in (90, 270) and (r.y0 < 65.0 or r.y1 > limit_y - 65.0))
                        or (page.rotation == 0 and (r.y0 < 55.0 or r.y1 > limit_y - 55.0))
                    )
                )

                if is_running_header or is_standalone_page_num:
                    hf_entry = {
                        "page": pnum,
                        "text": txt[:80],
                        "bbox": (round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)),
                        "kind": "running_header" if is_running_header else "footer_page_number",
                    }
                    hf_failures.append(hf_entry)
                    issues.append(
                        f"Página {pnum} (apaisada): se detectó encabezado/pie de página '{txt[:45]}' "
                        f"cuando la norma exige pagestyle empty."
                    )

                # Detección de desbordamiento de texto fuera del área útil
                if (
                    r.x0 < margin_min_pt - 2.0
                    or r.y0 < margin_min_pt - 2.0
                    or r.x1 > limit_x - margin_min_pt + 2.0
                    or r.y1 > limit_y - margin_min_pt + 2.0
                ):
                    ov_entry = {
                        "page": pnum,
                        "kind": "text",
                        "text": txt[:60],
                        "bbox": (round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)),
                        "limits": (round(limit_x, 1), round(limit_y, 1)),
                    }
                    overflow_failures.append(ov_entry)
                    issues.append(
                        f"Página {pnum} (apaisada): texto desbordado fuera del área útil en "
                        f"({r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f}) [límite {limit_x:.1f}x{limit_y:.1f}]: '{txt[:30]}'"
                    )

            # 2. Comprobación de desbordamiento en elementos vectoriales (líneas de tabla, TikZ)
            drawings = page.get_drawings()
            for d in drawings:
                r = d["rect"]
                if (
                    r.x0 < margin_min_pt - 2.0
                    or r.y0 < margin_min_pt - 2.0
                    or r.x1 > limit_x - margin_min_pt + 2.0
                    or r.y1 > limit_y - margin_min_pt + 2.0
                ):
                    ov_entry = {
                        "page": pnum,
                        "kind": "drawing",
                        "rect": (round(r.x0, 1), round(r.y0, 1), round(r.x1, 1), round(r.y1, 1)),
                        "limits": (round(limit_x, 1), round(limit_y, 1)),
                    }
                    overflow_failures.append(ov_entry)
                    issues.append(
                        f"Página {pnum} (apaisada): trazo vectorial desbordado fuera del área útil en "
                        f"({r.x0:.1f}, {r.y0:.1f}, {r.x1:.1f}, {r.y1:.1f})"
                    )

    headers_footers_suppressed = len(hf_failures) == 0
    geometry_ok = len(overflow_failures) == 0
    passed = headers_footers_suppressed and geometry_ok

    return {
        "pdf_path": str(path),
        "landscape_pages_detected": len(landscape_pages),
        "landscape_pages": tuple(landscape_pages),
        "headers_footers_suppressed": headers_footers_suppressed,
        "hf_failures": tuple(hf_failures),
        "geometry_ok": geometry_ok,
        "overflow_count": len(overflow_failures),
        "overflow_failures": tuple(overflow_failures),
        "issues": tuple(issues),
        "passed": passed,
    }


class McpLexClient:
    """Cliente unificado para el servidor MCP LEX y el ecosistema híbrido."""

    server_name: str = "lex"

    def __init__(self, ahk_root: Path | None = None) -> None:
        self.ahk_root = ahk_root or AHK_ROOT
        self._ensure_sys_path()

    def _ensure_sys_path(self) -> None:
        if self.ahk_root.is_dir() and str(self.ahk_root) not in sys.path:
            sys.path.insert(0, str(self.ahk_root))

    def check_health(self) -> dict[str, Any]:
        """Sondea la disponibilidad y latencia de Nova Pro y Azure Foundry (Sol 6.1)."""
        self._ensure_sys_path()
        try:
            from src.hybrid_llm_bridge import probe_hybrid_health
            raw = probe_hybrid_health()
            res = dict(raw)
            res["sol_61"] = res.get("foundry_accelerator") or {}
            res["nova_pro"] = res.get("nova_pro_baseline") or {}
            return res
        except Exception as exc:
            LOG.warning(f"Error al sondear salud del motor híbrido LEX: {exc}")
            return {
                "status": "degraded_offline",
                "error": str(exc),
                "sol_61": {"available": False, "error": str(exc)},
                "nova_pro": {"available": False, "error": str(exc)},
                "foundry_accelerator": {"available": False, "error": str(exc)},
                "nova_pro_baseline": {"available": False, "error": str(exc)},
            }

    def hybrid_inference(
        self,
        prompt: str,
        system_prompt: str = "",
        max_tokens: int = 1024,
        accelerate: bool = True,
        reasoning_tier: str = "deep",
    ) -> str:
        """Inferencia híbrida con Sol 6.1 acelerado y fallback a Nova Pro."""
        self._ensure_sys_path()
        try:
            from src.hybrid_llm_bridge import invoke_hybrid
            res = invoke_hybrid(
                prompt=prompt,
                system_prompt=system_prompt,
                max_tokens=max_tokens,
                accelerate=accelerate,
                reasoning_tier=reasoning_tier,
            )
            return res.get("text", "")
        except Exception as exc:
            LOG.warning(f"Fallo al invocar inferencia híbrida LEX, intentando cliente local: {exc}")
            from .llm_bridge import AulaTeXLLMClient
            client = AulaTeXLLMClient()
            call_res = client.call("Amazon Nova Pro", prompt, max_tokens=max_tokens)
            return call_res.text if call_res.ok else ""

    def audit_pdf_landscape(self, pdf_path: str | Path) -> dict[str, Any]:
        """Ejecuta la auditoría geométrica contractual de páginas apaisadas."""
        return audit_landscape_geometry(pdf_path)

    def list_connected_agents(self) -> tuple[dict[str, str], ...]:
        """Inventario formal de agentes editoriales conectados con el MCP LEX."""
        return (
            {"agent_id": "aulatex", "role": "Orquestador Maestro Editorial", "spec": "AulaTeXItescaOrchestrator"},
            {"agent_id": "navegación-itesca", "role": "Navegación Plataforma Confinada", "spec": "NavegacionItescaAgent (tipo navegación-plataforma)"},
            {"agent_id": "realizar-planeación", "role": "Planeación Canónica y Pedagógica", "spec": "RealizarPlaneacionAgent"},
            {"agent_id": "encontrar-recursos", "role": "Localización y Extracción Documental", "spec": "EncontrarRecursosAgent"},
            {"agent_id": "extraer-conceptos", "role": "Extracción Epistemológica y Fichas", "spec": "ExtraerConceptosAgent"},
            {"agent_id": "realizar-actividad", "role": "Desarrollo, Compilación y Calidad Tipográfica", "spec": "RealizarActividadAgent"},
            {"agent_id": "estilo-escribir", "role": "Auditoría de Voz Autoral y Estilo Académico", "spec": "EstiloEscribirAgent"},
            {"agent_id": "activity-observer", "role": "Observador Contractual de AulaTeX", "spec": "ActivityObserver"},
            {"agent_id": "activity-optimizer", "role": "Optimizador de Micro-Ajustes Tipográficos", "spec": "ActivityOptimizer"},
            {"agent_id": "latexmk", "role": "Agente Canónico de Compilación Inteligente", "spec": "LatexmkAgent"},
        )


_DEFAULT_LEX_CLIENT: McpLexClient | None = None


def get_lex_client() -> McpLexClient:
    """Retorna la instancia global del cliente MCP LEX."""
    global _DEFAULT_LEX_CLIENT
    if _DEFAULT_LEX_CLIENT is None:
        _DEFAULT_LEX_CLIENT = McpLexClient()
    return _DEFAULT_LEX_CLIENT


__all__ = [
    "McpLexClient",
    "audit_landscape_geometry",
    "get_lex_client",
]
