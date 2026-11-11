"""Agente ``estilo-escribir`` para auditoría y refinamiento de voz académica en AulaTeX.

Colabora con ``realizar-actividad`` para asegurar que los reportes ``.tex`` y
entregables ``.docx`` alcancen un estilo académico natural, directo y riguroso,
libre de metadiscurso de consigna, muletillas robóticas de IA, truncamientos
editoriales, dólares sin escapar, metadatos operativos de plataforma y citas no
acreditadas en la bibliografía verificada.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
from typing import Any

from .llm_bridge import AulaTeXLLMClient
from .mcp_lex import McpLexClient, get_lex_client
from .navegacion_plataforma import assert_no_credential_leak
from .workspace import AulaTeXWorkspace

AGENT_ID_ESTILO_ESCRIBIR = "estilo-escribir"
ACCEPTABLE_STYLE_THRESHOLD = 88.0

_METADISCOURSE_CRITICAL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ruptura_cuarta_pared_esta_actividad", re.compile(r"\besta actividad(?:\s+acad[ée]mica|\s+evaluativa)?\s+(?:se centra|busca|proporciona|consiste)\b", re.I)),
    ("ruptura_cuarta_pared_la_actividad", re.compile(r"\bla actividad\s+\d+(?:\.\d+)?\b", re.I)),
    ("copia_consigna_para_resolver", re.compile(r"\bpara resolver (?:esta actividad|los ejercicios de esta actividad|los reactivos espec[íi]ficos)\b", re.I)),
    ("metadiscurso_estudiantes_deben", re.compile(r"\blos estudiantes (?:deben|ser[áa]n evaluados)\b", re.I)),
    ("metadiscurso_producto_solicitado", re.compile(r"\bel producto solicitado\b", re.I)),
    ("metadiscurso_se_deben_investigar", re.compile(r"\bse deben (?:investigar|incluir|citar|utilizar|consultar)\b", re.I)),
    ("metadiscurso_artefacto_tikz", re.compile(r"\b(?:en|con|mediante|usando|diagrama|c[óo]digo|artefacto|cajas?)\s+TikZ\b", re.I)),
    ("metadiscurso_cuadro_tikz", re.compile(r"\bcuadro\s+(?:sin[óo]ptico\s+)?(?:jer[áa]rquico\s+)?en\s+TikZ\b", re.I)),
    ("metadiscurso_cuadro_desarrollado_en_este_trabajo", re.compile(r"\bel cuadro sin[óo]ptico desarrollado en este trabajo\b", re.I)),
    ("metadiscurso_este_manuscrito_organiza", re.compile(r"\b(?:este manuscrito|el presente estudio|este documento|este trabajo)\s+(?:organiza anal[íi]ticamente|presenta|desarrolla)\s+mediante\b", re.I)),
    ("metadiscurso_titulo_seccion_producto", re.compile(r"\\section\*?\{\s*(?:Cuadro\s+sin[óo]ptico|Cuadro\s+comparativo|Mapa\s+conceptual|Mapa\s+de\s+cajas|Infograf[íi]a|Ensayo|Reporte|Desarrollo\s+del\s+foro)\b", re.I)),
    ("metadiscurso_actividad_oficial_portada", re.compile(r"\bActividad\s+oficial\b", re.I)),
    ("metadiscurso_actividad_consigna_id", re.compile(r"\bActividad\s+S?\d+\b", re.I)),
)

_OPERATIONAL_LEAK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("metadato_operativo_modulo_moodle", re.compile(r"\bM[óo]dulo Moodle\b", re.I)),
    ("metadato_operativo_actividad_local", re.compile(r"\bActividad local\s+\d+\b", re.I)),
    ("metadato_operativo_vencimiento", re.compile(r"\bVencimiento publicado\b", re.I)),
    ("metadato_operativo_portal_url", re.compile(r"cursos3\.e-itesca\.edu\.mx", re.I)),
)

_ROBOTIC_CLICHE_REWRITES: tuple[tuple[re.Pattern[str], str, str], ...] = (
    (re.compile(r"\bEn conclusi[óo]n,\s*([a-záéíóúüñ])"), lambda m: m.group(1).upper(), "cliche_en_conclusion"),  # type: ignore[arg-type]
    (re.compile(r"\bEn resumen,\s*([a-záéíóúüñ])"), lambda m: m.group(1).upper(), "cliche_en_resumen"),  # type: ignore[arg-type]
    (re.compile(r"\bEs importante destacar que\s+([a-záéíóúüñ])"), lambda m: m.group(1).upper(), "cliche_es_importante_destacar"),  # type: ignore[arg-type]
    (re.compile(r"\bCabe destacar que\s+([a-záéíóúüñ])"), lambda m: m.group(1).upper(), "cliche_cabe_destacar"),  # type: ignore[arg-type]
    (re.compile(r"\bEn el [áa]mbito gerencial,\s+en\s+", re.I), "En ", "muletilla_ambito_gerencial"),
)

# Detecta "$100 y $120" donde dos signos $ no escapados encierran texto en prosa con espacios
_UNESCAPED_PROSE_DOLLAR_RE = re.compile(r"(?<!\\)\$\d[\d.,]*\s+[a-záéíóúüñA-ZÁÉÍÓÚÜÑ]+\s+(?<!\\)\$\d")


@dataclass(frozen=True)
class EstiloEvaluation:
    score: float
    passed: bool
    critical_issues: tuple[dict[str, str], ...]
    style_warnings: tuple[dict[str, str], ...]
    cited_keys: tuple[str, ...]
    missing_bib_keys: tuple[str, ...]


@dataclass(frozen=True)
class EstiloCollaborationResult:
    agent_id: str
    run_id: str
    report_path: Path
    target_path: Path
    before: EstiloEvaluation
    after: EstiloEvaluation
    applied_changes: tuple[str, ...]
    llm_refined: bool


def _strip_tex_comments(tex: str) -> str:
    out_lines: list[str] = []
    for line in tex.splitlines():
        # Conservar \% escapado y eliminar comentarios reales
        cleaned = re.sub(r"(?<!\\)%.*$", "", line)
        out_lines.append(cleaned)
    return "\n".join(out_lines)


def _extract_bib_keys(bib_text: str) -> set[str]:
    return {m.group(1).strip() for m in re.finditer(r"@\w+\s*\{\s*([^,\s]+)\s*,", bib_text)}


def _extract_cite_keys(active_tex: str) -> set[str]:
    keys: set[str] = set()
    for match in re.finditer(r"\\cite\w*\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}", active_tex):
        for piece in match.group(1).split(","):
            clean = piece.strip()
            if clean:
                keys.add(clean)
    return keys


class EstiloEscribirAgent:
    """Agente ``estilo-escribir`` para evaluación y mejora de estilo académico."""

    agent_id: str = AGENT_ID_ESTILO_ESCRIBIR

    def __init__(
        self,
        workspace: AulaTeXWorkspace | None = None,
        llm: AulaTeXLLMClient | None = None,
        lex_client: McpLexClient | None = None,
    ) -> None:
        self.workspace = workspace or AulaTeXWorkspace()
        self.lex_client = lex_client or get_lex_client()
        self.llm = llm
        self.runs_root = self.workspace.feedback_root / "estilo-escribir" / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def evaluate_tex(self, tex_text: str, bib_text: str = "") -> EstiloEvaluation:
        active = _strip_tex_comments(tex_text)
        critical: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        for code, pat in _METADISCOURSE_CRITICAL_PATTERNS:
            m = pat.search(active)
            if m:
                critical.append({"code": code, "excerpt": m.group(0)[:120]})

        for code, pat in _OPERATIONAL_LEAK_PATTERNS:
            m = pat.search(active)
            if m:
                critical.append({"code": code, "excerpt": m.group(0)[:120]})

        m_dollar = _UNESCAPED_PROSE_DOLLAR_RE.search(active)
        if m_dollar:
            critical.append({"code": "dolar_monetario_sin_escapar_en_tex", "excerpt": m_dollar.group(0)[:120]})

        cited = sorted(_extract_cite_keys(active))
        bib_keys = _extract_bib_keys(bib_text) if bib_text.strip() else set()
        missing_bib = sorted(k for k in cited if bib_keys and k not in bib_keys)
        if missing_bib:
            critical.append(
                {
                    "code": "citas_no_registradas_en_bib",
                    "excerpt": ", ".join(missing_bib),
                }
            )

        # Detectar truncamiento a mitad de palabra en celdas de tablas (ej. "Para mu &", "por ejemplo,  &")
        for m_trunc in re.finditer(r"(?:,\s*|\b(?:de|en|el|la|los|las|un|una|se|mu|res|es|ta|o)\s+)&\s", active):
            critical.append({"code": "celda_tabla_truncada", "excerpt": m_trunc.group(0).strip()})
            break

        # Muletillas robóticas y repeticiones formulaicas
        for pat, _rep, code in _ROBOTIC_CLICHE_REWRITES:
            hits = list(pat.finditer(active))
            if hits:
                warnings.append({"code": code, "count": str(len(hits)), "excerpt": hits[0].group(0)[:80]})

        gerencial_hits = len(re.findall(r"En el [áa]mbito gerencial", active, flags=re.I))
        if gerencial_hits >= 3:
            warnings.append(
                {
                    "code": "repeticion_formulaica_ambito_gerencial",
                    "count": str(gerencial_hits),
                    "excerpt": f"{gerencial_hits} ocurrencias repetidas",
                }
            )

        score = 100.0 - (18.0 * len(critical)) - (3.5 * len(warnings))
        score = max(0.0, round(score, 2))
        passed = (len(critical) == 0) and (score >= ACCEPTABLE_STYLE_THRESHOLD)

        return EstiloEvaluation(
            score=score,
            passed=passed,
            critical_issues=tuple(critical),
            style_warnings=tuple(warnings),
            cited_keys=tuple(cited),
            missing_bib_keys=tuple(missing_bib),
        )

    def evaluate_plain_prose(self, text: str) -> EstiloEvaluation:
        """Evalúa prosa académica extraída de documentos Word (.docx)."""
        critical: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        for code, pat in _METADISCOURSE_CRITICAL_PATTERNS:
            m = pat.search(text)
            if m:
                critical.append({"code": code, "excerpt": m.group(0)[:120]})

        for code, pat in _OPERATIONAL_LEAK_PATTERNS:
            m = pat.search(text)
            if m:
                critical.append({"code": code, "excerpt": m.group(0)[:120]})

        for pat, _rep, code in _ROBOTIC_CLICHE_REWRITES:
            hits = list(pat.finditer(text))
            if hits:
                warnings.append({"code": code, "count": str(len(hits)), "excerpt": hits[0].group(0)[:80]})

        score = max(0.0, round(100.0 - 18.0 * len(critical) - 3.0 * len(warnings), 2))
        return EstiloEvaluation(
            score=score,
            passed=(len(critical) == 0 and score >= ACCEPTABLE_STYLE_THRESHOLD),
            critical_issues=tuple(critical),
            style_warnings=tuple(warnings),
            cited_keys=(),
            missing_bib_keys=(),
        )

    def collaborate_on_tex(
        self,
        tex_path: str | Path,
        bib_path: str | Path | None = None,
        *,
        apply: bool = True,
        use_llm: bool = False,
        engine: str = "Amazon Nova Pro",
    ) -> EstiloCollaborationResult:
        target = Path(tex_path).resolve()
        tex_original = target.read_text(encoding="utf-8")
        bib_text = Path(bib_path).read_text(encoding="utf-8") if bib_path and Path(bib_path).is_file() else ""

        before = self.evaluate_tex(tex_original, bib_text)
        current = tex_original
        changes: list[str] = []
        llm_refined = False

        if apply and (not before.passed or before.style_warnings):
            current, det_changes = self._apply_deterministic_refinements(current)
            changes.extend(det_changes)

            mid_eval = self.evaluate_tex(current, bib_text)
            if use_llm and (not mid_eval.passed or mid_eval.score < 94.0):
                refined, llm_ok = self._refine_conclusion_with_llm(current, engine=engine)
                if llm_ok:
                    post_llm_eval = self.evaluate_tex(refined, bib_text)
                    if post_llm_eval.score >= mid_eval.score and len(post_llm_eval.critical_issues) <= len(mid_eval.critical_issues):
                        current = refined
                        llm_refined = True
                        changes.append(f"refinamiento_voz_llm:{engine}")

            if current != tex_original:
                assert_no_credential_leak(current)
                target.write_text(current, encoding="utf-8")

        after = self.evaluate_tex(current, bib_text)
        run_id = f"{self.workspace.timestamp()}-estilo-escribir"
        run_dir = self.runs_root / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        report_payload: dict[str, Any] = {
            "run_id": run_id,
            "agent_id": self.agent_id,
            "target": self.workspace.relative(target),
            "before": asdict(before),
            "after": asdict(after),
            "applied_changes": changes,
            "llm_refined": llm_refined,
        }
        assert_no_credential_leak(report_payload)
        report_path = run_dir / "reporte-estilo.json"
        report_path.write_text(json.dumps(report_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self.workspace.append_bitacora(run_id, "estilo-escribir", report_payload)

        return EstiloCollaborationResult(
            agent_id=self.agent_id,
            run_id=run_id,
            report_path=report_path,
            target_path=target,
            before=before,
            after=after,
            applied_changes=tuple(changes),
            llm_refined=llm_refined,
        )

    def _apply_deterministic_refinements(self, tex: str) -> tuple[str, list[str]]:
        updated = tex
        applied: list[str] = []

        # Escapar signos de dólar monetarios contiguos tipo "$100 y $120" -> "\$100 y \$120"
        def _escape_prose_dollars(match: re.Match[str]) -> str:
            return re.sub(r"(?<!\\)\$", r"\\$", match.group(0))

        escaped = _UNESCAPED_PROSE_DOLLAR_RE.sub(_escape_prose_dollars, updated)
        if escaped != updated:
            updated = escaped
            applied.append("escape_signos_monetarios_latex")

        for pat, repl, code in _ROBOTIC_CLICHE_REWRITES:
            candidate = pat.sub(repl, updated)
            if candidate != updated:
                updated = candidate
                applied.append(f"limpieza_{code}")

        # Limpieza de metadiscurso técnico y menciones a artefactos TikZ / consigna
        metadiscourse_rewrites = [
            (
                re.compile(r"\bmediante un cuadro sin[óo]ptico jer[áa]rquico en TikZ y matrices operativas\b", re.I),
                "mediante esquemas analíticos de articulación de fuentes y matrices operativas",
                "remocion_metadiscurso_cuadro_tikz_abstract",
            ),
            (
                re.compile(r"\bel cuadro sin[óo]ptico desarrollado en este trabajo no se limita a ilustrar una simple jerarqu[íi]a\b", re.I),
                "el análisis estructural del ordenamiento no se limita a ilustrar una simple jerarquía",
                "remocion_metadiscurso_cuadro_trabajo_intro",
            ),
            (
                re.compile(r"\\section\*?\{\s*Cuadro sin[óo]ptico(?::\s*|\s*[-—]\s*)([^}]+)\}", re.I),
                r"\\section{Estructura sistemática y garantías de \1}",
                "normalizacion_titulo_seccion_cuadro_sinoptico",
            ),
            (
                re.compile(r"\\section\*?\{\s*Desarrollo del foro\s*\}", re.I),
                r"\\section{Articulación dogmática de derechos humanos}",
                "normalizacion_titulo_seccion_desarrollo_foro",
            ),
            (
                re.compile(r"\bel producto solicitado\b", re.I),
                "el objeto de estudio",
                "remocion_metadiscurso_producto_solicitado",
            ),
            (
                re.compile(r"\b(?:diagrama|artefacto|c[óo]digo|cajas?)\s+TikZ\b", re.I),
                "esquema analítico",
                "remocion_mencion_artefacto_tikz",
            ),
            (
                re.compile(r"\b(?:este manuscrito|el presente estudio|este trabajo)\s+organiza anal[íi]ticamente mediante\b", re.I),
                "el análisis se articula mediante",
                "remocion_metadiscurso_este_manuscrito_organiza",
            ),
        ]
        for pat_m, repl_m, code_m in metadiscourse_rewrites:
            candidate = pat_m.sub(repl_m, updated)
            if candidate != updated:
                updated = candidate
                applied.append(f"refinamiento_{code_m}")

        # Limpieza de fila redundante 'Actividad oficial:' en \authortable
        authortable_clean = re.sub(
            r"[ \t]*\\textbf\{Actividad\s+oficial:\}\s*&[^\\]*\\\\\r?\n?",
            "",
            updated,
            flags=re.IGNORECASE,
        )
        if authortable_clean != updated:
            updated = authortable_clean
            applied.append("remocion_fila_actividad_oficial_authortable")

        # Normalización de \documentsubject cuando contiene metadatos de consigna (Actividad S7...)
        docsub_clean = re.sub(
            r"(\\def\\documentsubject\s*\{)\s*(?:Actividad|Evidencia)\s+S?\d+[^}]*(\})",
            r"\g<1>Licenciatura en Derecho\2",
            updated,
            flags=re.IGNORECASE,
        )
        if docsub_clean != updated:
            updated = docsub_clean
            applied.append("normalizacion_documentsubject_carrera")

        # Reubicación de declaración ética de IA desde Resumen/abstractd a Conclusiones
        ai_footnote_m = re.search(
            r"(\\begin\{abstractd?\}[\s\S]*?)(\\footnote\{[^}]*(?:inteligencia\s+artificial|Lineamientos)[^}]*\})([\s\S]*?\\end\{abstractd?\})",
            updated,
            re.I,
        )
        if ai_footnote_m:
            fn_text = ai_footnote_m.group(2)
            updated = (
                updated[:ai_footnote_m.start()]
                + ai_footnote_m.group(1)
                + ai_footnote_m.group(3)
                + updated[ai_footnote_m.end():]
            )
            applied.append("reubicacion_declaracion_ia_abstract_a_conclusiones")
            # Adherir como footnote a la última frase de la sección Conclusiones
            concl_m = re.search(
                r"(\\section\*?\{Conclusi[^}]*\}[\s\S]*?)([.\w\)]\s*)(\n\s*\\clearpage|\n\s*\\begin\{thebibliography\}|\n\s*\\printbibliography)",
                updated,
                re.I,
            )
            if concl_m and "inteligencia artificial" not in concl_m.group(1):
                updated = (
                    updated[:concl_m.start()]
                    + concl_m.group(1)
                    + concl_m.group(2).rstrip()
                    + fn_text
                    + "\n"
                    + concl_m.group(3)
                    + updated[concl_m.end():]
                )

        # Supresión de addcontentsline redundante tras \section (previene duplicados en TOC)
        dup_toc = re.sub(
            r"(\\section\{[^}]+\}\s*(?:\\label\{[^}]*\}\s*)?)\\phantomsection\s*\\addcontentsline\{toc\}\{section\}\{[^}]+\}\s*",
            r"\1\n",
            updated,
        )
        if dup_toc != updated:
            updated = dup_toc
            applied.append("remocion_addcontentsline_duplicado_tras_section")

        # Corrección de hfwidthwrap true a false para garantizar pie unilineal sin colisiones
        hf_wrap_m = re.search(r"\\def\\hfwidthwrap\s*\{\s*true\s*\}", updated)
        if hf_wrap_m:
            updated = re.sub(r"\\def\\hfwidthwrap\s*\{\s*true\s*\}", r"\\def\\hfwidthwrap{false}", updated)
            applied.append("correccion_hfwidthwrap_unilineal")

        # Supresión integral de encabezados y pies en páginas apaisadas (\begin{landscape})
        if "\\begin{landscape}" in updated and "\\pagestyle{empty}" not in updated:
            updated = re.sub(r"(\\begin\{landscape\})", r"\\clearpage\n\\pagestyle{empty}\n\1", updated)
            updated = re.sub(r"(\\end\{landscape\})", r"\1\n\\clearpage\n\\pagestyle{fancy}", updated)
            applied.append("supresion_encabezados_pies_en_landscape")

        # Garantizar que Conclusiones inicie en página nueva
        concl_sec_m = re.search(r"(?<!\\clearpage\n)(?<!\\clearpage\r\n)\\section\*?\{Conclusi", updated, re.I)
        if concl_sec_m:
            prefix_c = updated[max(0, concl_sec_m.start() - 60):concl_sec_m.start()]
            if not re.search(r"\\(?:clearpage|cleardoublepage|newpage)\s*$", prefix_c):
                updated = updated[:concl_sec_m.start()] + "\\clearpage\n" + updated[concl_sec_m.start():]
                applied.append("salto_pagina_independiente_conclusiones")

        return updated, applied

    def _refine_conclusion_with_llm(self, tex: str, engine: str = "Amazon Nova Pro") -> tuple[str, bool]:
        """Refina el bloque de Conclusiones con el motor LLM preservando citas, macros y números."""
        sec_match = re.search(
            r"(\\section\{Conclusiones\}\s*\n)(.+?)(\n\s*(?:\\input\{|\}))",
            tex,
            flags=re.DOTALL,
        )
        if not sec_match:
            return tex, False
        original_block = sec_match.group(2).strip()
        if len(original_block) < 80 or len(original_block) > 4500:
            return tex, False

        orig_cites = _extract_cite_keys(original_block)
        prompt = (
            "Eres el agente estilo-escribir de AulaTeX. Reescribe el siguiente apartado de Conclusiones "
            "en español académico directo, sobrio y fluido de posgrado, eliminando muletillas robóticas "
            "('En conclusión', 'Cabe destacar', 'Es importante señalar', 'Esta actividad') sin romper "
            "NINGUNA macro LaTeX ni omitir NINGUNA cita \\cite/\\citep ni alterar cifras.\n"
            "Devuelve ÚNICAMENTE el cuerpo LaTeX reescrito, sin bloques markdown ```.\n\n"
            f"TEXTO ORIGINAL:\n{original_block}"
        )
        candidate_block = ""
        if self.lex_client is not None:
            try:
                candidate_block = self.lex_client.hybrid_inference(
                    prompt=prompt,
                    system_prompt="Eres el agente estilo-escribir de AulaTeX.",
                    max_tokens=1200,
                    accelerate=True,
                )
            except Exception:
                candidate_block = ""
        if not candidate_block.strip():
            client = self.llm or AulaTeXLLMClient()
            try:
                resp = client.generate(engine=engine, prompt=prompt, max_tokens=1200)
                if getattr(resp, "ok", False):
                    candidate_block = getattr(resp, "text", "").strip()
            except Exception:
                return tex, False
        if not candidate_block.strip():
            return tex, False

        candidate_block = candidate_block.strip()
        candidate_block = re.sub(r"^```(?:latex|tex)?\s*|\s*```$", "", candidate_block).strip()
        if not candidate_block or "\\section" in candidate_block:
            return tex, False
        # Verificar preservación estricta de claves bibliográficas
        if _extract_cite_keys(candidate_block) != orig_cites:
            return tex, False
        if candidate_block.count("{") != candidate_block.count("}"):
            return tex, False

        new_tex = tex[: sec_match.start(2)] + candidate_block + tex[sec_match.end(2) :]
        return new_tex, True


__all__ = [
    "ACCEPTABLE_STYLE_THRESHOLD",
    "AGENT_ID_ESTILO_ESCRIBIR",
    "EstiloCollaborationResult",
    "EstiloEscribirAgent",
    "EstiloEvaluation",
]
