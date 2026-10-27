# -*- coding: utf-8 -*-
"""Orquestador de extracción conceptual e investigación por actividad con Amazon Nova Pro.

Ejecuta para cada actividad (1..22) de la materia:
  1/5 Lectura de planeación, consigna oficial y conceptos semilla de la carpeta de notas por actividad.
  2/5 Extracción de páginas y fragmentos citables (TF-IDF) sobre el corpus focalizado de libros y material docente.
  3/5 Investigación conceptual profunda, formulación matemática y síntesis de tres tiempos con Amazon Nova Pro (AulaTeXLLMClient).
  4/5 Exportación de artefactos canónicos (.md, .xlsx, .csv, .json, .docx, ideas, trazabilidad, planeación, síntesis Nova Pro).
  5/5 Sincronización en las carpetas canónicas:
      - extractor-aulatex/conceptos-<materia>-actividad-<N>/
      - referencias-<materia>/conceptos-<materia>/<actividad-folder>/
      - referencias-<materia>/notas-<materia>/<actividad-folder>/investigacion/ y /conceptos/
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import shutil
import sys
import threading
import time
from typing import Any, Callable

from .concept_extractor import extract_candidate_concepts, extract_candidate_concepts_from_planeacion
from .document_reader import SUPPORTED_EXTENSIONS, extract_pages_from_sources, read_any_text_file
from .exporters import export_all
from .fichas import ConceptFicha, build_fichas
from .planeacion_parser import parse_planeacion_text, planeacion_to_dict
from .preprocessing import build_fragments, load_concept_lines, unique_preserve_order
from .search import TfidfSearchEngine

# Ensure repo root / aulaTEX is importable for AulaTeXLLMClient
REPO_ROOT = Path(__file__).resolve().parents[4]
AULATEX_DIR = REPO_ROOT / "aulaTEX"
if str(AULATEX_DIR) not in sys.path:
    sys.path.insert(0, str(AULATEX_DIR))

DEFAULT_SUBJECT_DIR = (
    REPO_ROOT
    / "ITESCA"
    / "maestria-en-gestion-administrativa"
    / "estadistica-aplicada-para-la-administracion-mga"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_activities_spec(subject_dir: Path) -> list[dict[str, Any]]:
    """Carga la especificación de las 22 actividades desde el script estructurador de la materia
    o descubre automáticamente las carpetas actividad-XX-* en notas."""
    spec_script = (
        subject_dir
        / "assets-estadistica-aplicada-para-la-administracion"
        / "estructurar_notas_y_biblioteca_22_actividades.py"
    )
    if spec_script.exists():
        import importlib.util

        spec = importlib.util.spec_from_file_location("estructurar_notas_22", spec_script)
        if spec and spec.loader:
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "ACTIVITIES_SPEC"):
                return list(mod.ACTIVITIES_SPEC)

    # Fallback: descubrir carpetas actividad-XX-* en referencias-*/notas-*
    activities: list[dict[str, Any]] = []
    for ref_dir in sorted(subject_dir.glob("referencias-*")):
        for notas_dir in sorted(ref_dir.glob("notas-*")):
            for act_dir in sorted(notas_dir.glob("actividad-*")):
                if not act_dir.is_dir():
                    continue
                m = re.match(r"actividad-0*(\d+)-(.*)", act_dir.name)
                if not m:
                    continue
                num = int(m.group(1))
                code = f"A{num:02d}"
                seed_file = act_dir / f"conceptos-semilla-{code}.txt"
                seeds = load_concept_lines(str(seed_file)) if seed_file.exists() else []
                activities.append(
                    {
                        "num": num,
                        "code": code,
                        "module_id": str(num),
                        "unit_num": 1,
                        "unit_title": f"Unidad {num}",
                        "unit_folder": "unidad-general",
                        "folder": act_dir.name,
                        "moodle_title": act_dir.name,
                        "report_title": act_dir.name.replace("-", " ").title(),
                        "report_subtitle": f"Actividad {num}",
                        "kind": "investigacion",
                        "weight": "",
                        "due_date": "",
                        "delivered": False,
                        "deliverable_rel": None,
                        "teacher_files": [],
                        "keywords": seeds[:8],
                        "seed_concepts": seeds,
                    }
                )
    return activities


def _materia_slug(subject_dir: Path) -> str:
    name = subject_dir.name
    for suffix in ("-lde", "-lic", "-mga", "-mem", "-mtia", "-lgc"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def get_paths_for_activity(subject_dir: Path, act: dict[str, Any]) -> dict[str, Path]:
    slug = _materia_slug(subject_dir)
    ref_dir = subject_dir / f"referencias-{slug}"
    notas_dir = ref_dir / f"notas-{slug}"
    conceptos_ref_root = ref_dir / f"conceptos-{slug}"
    extractor_root = subject_dir / "extractor-aulatex"

    act_notes_dir = notas_dir / act["folder"]
    code = act["code"]
    return {
        "subject_dir": subject_dir,
        "ref_dir": ref_dir,
        "notas_dir": notas_dir,
        "act_notes_dir": act_notes_dir,
        "focal_corpus_dir": act_notes_dir / "corpus-extractor-focalizado",
        "full_corpus_dir": act_notes_dir / "corpus-extractor",
        "planeacion_file": act_notes_dir / f"planeacion-{code}-entrada-extractor.txt",
        "consigna_file": act_notes_dir / f"CONSIGNA-OFICIAL-{code}.md",
        "seed_concepts_file": act_notes_dir / f"conceptos-semilla-{code}.txt",
        "extractor_conceptos_dir": extractor_root / f"conceptos-{slug}-actividad-{act['num']}",
        "ref_conceptos_dir": conceptos_ref_root / act["folder"],
        "notes_investigacion_dir": act_notes_dir / "investigacion",
        "notes_conceptos_dir": act_notes_dir / "conceptos",
        "state_file_extractor": extractor_root / "estado-trabajos-extraccion.json",
        "state_file_ref": conceptos_ref_root / "estado-trabajos-extraccion.json",
    }


def _repair_latex_json(s: str) -> str:
    """Repara barras invertidas de comandos LaTeX no escapadas dentro de cadenas JSON."""
    # Primero proteger escapes JSON legítimos dobles \\
    placeholder = "__DBL_BSLASH__"
    s = s.replace("\\\\", placeholder)
    # Comandos LaTeX que empiezan con b, f, n, r, t (que JSON confunde con \b \f \n \r \t)
    s = re.sub(
        r"\\(bar|beta|binom|textbf|textit|text|tau|theta|times|tilde|to|frac|forall|neq|ne|nu|nabla|right|rho|rangle)",
        r"\\\\\1",
        s,
    )
    # Cualquier otra barra invertida no seguida de comilla, barra, /, b, f, n, r, t, uXXXX
    s = re.sub(r'\\(?!(?:["\\/bfnrt]|u[0-9a-fA-F]{4}))', r"\\\\", s)
    s = s.replace(placeholder, "\\\\")
    s = re.sub(r",\s*([}\]])", r"\1", s)
    return s


def _extract_json_block(raw_text: str) -> dict[str, Any]:
    """Extrae el primer objeto JSON válido de la respuesta de Amazon Nova Pro."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    candidate = cleaned[start : end + 1] if (start != -1 and end != -1 and end > start) else cleaned

    for attempt in (candidate, _repair_latex_json(candidate)):
        try:
            parsed = json.loads(attempt, strict=False)
            if isinstance(parsed, dict) and ("sintesis_ejecutiva" in parsed or "estructura_tres_tiempos" in parsed):
                return parsed
        except Exception:
            pass

    # Intento de extracción estructural por expresiones regulares si el JSON fue truncado por max_tokens
    repaired = _repair_latex_json(cleaned)
    m_sint = re.search(r'"sintesis_ejecutiva"\s*:\s*"((?:[^"\\]|\\.)*)"', repaired, flags=re.DOTALL)
    m_intro = re.search(r'"introduccion"\s*:\s*"((?:[^"\\]|\\.)*)"', repaired, flags=re.DOTALL)
    m_base = re.search(r'"desarrollo_base_conceptual"\s*:\s*"((?:[^"\\]|\\.)*)"', repaired, flags=re.DOTALL)
    m_guia = re.search(r'"desarrollo_guia_aplicada"\s*:\s*"((?:[^"\\]|\\.)*)"', repaired, flags=re.DOTALL)
    m_conc = re.search(r'"conclusion"\s*:\s*"((?:[^"\\]|\\.)*)"', repaired, flags=re.DOTALL)
    if m_sint:
        def _unesc(val: str) -> str:
            try:
                return json.loads(f'"{val}"', strict=False)
            except Exception:
                return val.replace('\\"', '"').replace("\\n", "\n")

        conceptos_recovered = []
        for cm in re.finditer(
            r'\{\s*"concepto"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"definicion_rigurosa"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"formulacion_matematica_latex"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"aplicacion_administrativa"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"fuente_principal"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"localizador"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}',
            repaired,
            flags=re.DOTALL,
        ):
            conceptos_recovered.append({
                "concepto": _unesc(cm.group(1)),
                "definicion_rigurosa": _unesc(cm.group(2)),
                "formulacion_matematica_latex": _unesc(cm.group(3)),
                "aplicacion_administrativa": _unesc(cm.group(4)),
                "fuente_principal": _unesc(cm.group(5)),
                "localizador": _unesc(cm.group(6)),
            })

        ideas_recovered = []
        for im in re.finditer(
            r'\{\s*"concepto"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"tiempo_editorial"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"idea_base"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"argumento_academico"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"fuente"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"ubicacion"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}',
            repaired,
            flags=re.DOTALL,
        ):
            ideas_recovered.append({
                "concepto": _unesc(im.group(1)),
                "tiempo_editorial": _unesc(im.group(2)),
                "idea_base": _unesc(im.group(3)),
                "argumento_academico": _unesc(im.group(4)),
                "fuente": _unesc(im.group(5)),
                "ubicacion": _unesc(im.group(6)),
            })

        fichas_inv_recovered = []
        for fm in re.finditer(
            r'\{\s*"titulo_caso_o_articulo"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"autores_anio"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"problema_administrativo"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"metodologia_estadistica"\s*:\s*"((?:[^"\\]|\\.)*)"\s*,\s*"hallazgos_y_decision"\s*:\s*"((?:[^"\\]|\\.)*)"\s*\}',
            repaired,
            flags=re.DOTALL,
        ):
            fichas_inv_recovered.append({
                "titulo_caso_o_articulo": _unesc(fm.group(1)),
                "autores_anio": _unesc(fm.group(2)),
                "problema_administrativo": _unesc(fm.group(3)),
                "metodologia_estadistica": _unesc(fm.group(4)),
                "hallazgos_y_decision": _unesc(fm.group(5)),
            })

        sint_str = _unesc(m_sint.group(1))
        return {
            "sintesis_ejecutiva": sint_str,
            "conceptos_clave": conceptos_recovered,
            "ideas_estructuradas": ideas_recovered,
            "estructura_tres_tiempos": {
                "introduccion": _unesc(m_intro.group(1)) if m_intro else sint_str,
                "desarrollo_base_conceptual": _unesc(m_base.group(1)) if m_base else sint_str,
                "desarrollo_guia_aplicada": _unesc(m_guia.group(1)) if m_guia else sint_str,
                "conclusion": _unesc(m_conc.group(1)) if m_conc else sint_str,
            },
            "fichas_investigacion_articulos": fichas_inv_recovered,
        }
    return {}


def _build_nova_prompt(
    act: dict[str, Any],
    consigna_text: str,
    fichas: list[ConceptFicha],
) -> str:
    """Construye el prompt académico para Amazon Nova Pro con citas verificadas del corpus."""
    evidence_lines: list[str] = []
    for idx, ficha in enumerate(fichas[:14], start=1):
        if not ficha.hits:
            continue
        top_hit = ficha.hits[0]
        quote_short = re.sub(r"\s+", " ", top_hit.quote).strip()[:360]
        evidence_lines.append(
            f"{idx}. Concepto: {ficha.concept} | Fuente: {top_hit.source_name} ({top_hit.location}) | Cita: \"{quote_short}\""
        )
    evidence_block = "\n".join(evidence_lines) if evidence_lines else "Sin citas previas."

    return f"""Eres el motor de investigación conceptual y extracción académica de AulaTeX ejecutándose en Amazon Nova Pro.
Analiza la siguiente actividad de posgrado de la asignatura "Estadística aplicada para la administración" (Maestría en Gestión Administrativa, ITESCA) y genera una extracción conceptual rigurosa, exhaustiva y trazable al corpus bibliográfico.

DATOS OFICIALES DE LA ACTIVIDAD:
- Actividad número: {act['num']} ({act['code']}) — Módulo Moodle: {act['module_id']}
- Unidad temática: {act['unit_title']}
- Título en plataforma: {act['moodle_title']} (Ponderación: {act['weight']})
- Título del reporte AulaTeX: {act['report_title']}
- Subtítulo editorial: {act['report_subtitle']}
- Tipo de actividad: {act['kind']}
- Conceptos semilla obligatorios: {', '.join(act['seed_concepts'])}

CONSIGNA Y REQUISITOS DEL DOCENTE:
{consigna_text[:2800]}

EVIDENCIA TEXTUAL RECUPERADA DEL CORPUS DE LIBROS DE LA MATERIA:
{evidence_block}

Devuelve EXCLUSIVAMENTE un objeto JSON válido (sin bloques markdown adicionales fuera del JSON) con la siguiente estructura exacta:
{{
  "sintesis_ejecutiva": "Síntesis académica de 2 párrafos densos que explique el fundamento estadístico, matemático y gerencial de esta actividad.",
  "conceptos_clave": [
    {{
      "concepto": "Nombre del concepto",
      "definicion_rigurosa": "Definición formal y completa (3 a 5 oraciones) fundamentada en la literatura estadística.",
      "formulacion_matematica_latex": "Expresión o modelo matemático en sintaxis LaTeX (ej. \\\\bar{{X}} \\\\sim N(\\\\mu, \\\\sigma^2/n))",
      "aplicacion_administrativa": "Explicación concreta de cómo este concepto guía decisiones en administración, finanzas, operaciones o mercadotecnia.",
      "fuente_principal": "Autor y obra de referencia del corpus (ej. Anderson, Sweeney y Williams, 2012; Lind, Marchal y Wathen, 2012; Wackerly et al., 2010)",
      "localizador": "Ubicación o bloque de referencia"
    }}
  ],
  "ideas_estructuradas": [
    {{
      "concepto": "Concepto asociado",
      "tiempo_editorial": "introduccion | desarrollo | conclusion",
      "idea_base": "Tesis o proposición analítica autocontenida (2 a 4 oraciones).",
      "argumento_academico": "Desarrollo técnico y vinculación con la toma de decisiones bajo incertidumbre.",
      "fuente": "Fuente documental verificada",
      "ubicacion": "Sección o bloque"
    }}
  ],
  "estructura_tres_tiempos": {{
    "introduccion": "Texto académico en prosa (mínimo 2 párrafos amplios) para el Tiempo 1 (Introducción) del reporte, contextualizando el problema administrativo y metodológico.",
    "desarrollo_base_conceptual": "Desarrollo teórico-matemático profundo en prosa (mínimo 3 párrafos amplios) para el Tiempo 2 (Desarrollo), integrando definiciones, supuestos y propiedades de los estimadores o pruebas.",
    "desarrollo_guia_aplicada": "Guía analítica detallada para resolver o estructurar los casos, artículos, ejercicios o reactivos específicos de esta actividad según la consigna oficial.",
    "conclusion": "Síntesis conclusiva en prosa (mínimo 2 párrafos amplios) para el Tiempo 3 (Conclusiones), articulando hallazgos técnicos, reglas de decisión gerencial y limitaciones metodológicas."
  }},
  "fichas_investigacion_articulos": [
    {{
      "titulo_caso_o_articulo": "Título descriptivo del estudio empírico o caso de referencia aplicable a la unidad",
      "autores_anio": "Autores y año (de las fuentes del corpus o literatura estadística verificada)",
      "problema_administrativo": "Problema organizacional o económico analizado",
      "metodologia_estadistica": "Diseño muestral, estimador, prueba de hipótesis, serie de tiempo o modelo de regresión empleado",
      "hallazgos_y_decision": "Resultados cuantitativos e implicación para la gerencia"
    }}
  ]
}}

REGLAS ESTRICTAS:
1. Incluye entre 8 y 10 elementos en "conceptos_clave", entre 8 y 10 elementos en "ideas_estructuradas" (distribuidos entre "introduccion", "desarrollo" y "conclusion") y 3 elementos en "fichas_investigacion_articulos".
2. Todo el texto debe estar en español académico riguroso, sin muletillas conversacionales.
3. Responde únicamente con el JSON válido y completo (asegúrate de cerrar todas las llaves y corchetes)."""


def _export_nova_markdown(act: dict[str, Any], nova_payload: dict[str, Any], out_path: Path) -> None:
    """Genera un documento Markdown legible con la síntesis e investigación de Amazon Nova Pro."""
    meta = nova_payload.get("_meta", {})
    lines = [
        f"# Investigación Conceptual y Extracción AulaTeX (Amazon Nova Pro) — Actividad {act['num']}",
        "",
        f"- **Actividad**: {act['moodle_title']} (`{act['code']}`, módulo `{act['module_id']}`)",
        f"- **Unidad**: {act['unit_title']}",
        f"- **Título del reporte**: *{act['report_title']}*",
        f"- **Motor LLM utilizado**: `{meta.get('engine', 'Amazon Nova Pro')}` (`{meta.get('provider_model', 'us.amazon.nova-pro-v1:0')}`)",
        f"- **Tokens consumidos**: entrada={meta.get('prompt_tokens', 0)}, salida={meta.get('completion_tokens', 0)}, total={meta.get('total_tokens', 0)}",
        f"- **Fecha de extracción**: `{meta.get('timestamp', _utc_now())}`",
        "",
        "## 1. Síntesis Ejecutiva",
        "",
        str(nova_payload.get("sintesis_ejecutiva", "")).strip(),
        "",
        "## 2. Base Conceptual Rigurosa (`conceptos_clave`)",
        "",
    ]
    for idx, c in enumerate(nova_payload.get("conceptos_clave", []), start=1):
        if not isinstance(c, dict):
            continue
        lines.extend(
            [
                f"### 2.{idx}. {c.get('concepto', f'Concepto {idx}')}",
                "",
                f"- **Definición rigurosa**: {c.get('definicion_rigurosa', '')}",
                f"- **Formulación matemática (LaTeX)**: `$${c.get('formulacion_matematica_latex', '')}$$`",
                f"- **Aplicación administrativa**: {c.get('aplicacion_administrativa', '')}",
                f"- **Fuente principal**: {c.get('fuente_principal', '')} ({c.get('localizador', '')})",
                "",
            ]
        )

    lines.extend(["## 3. Estructura Argumentativa en Tres Tiempos", ""])
    tt = nova_payload.get("estructura_tres_tiempos", {})
    if isinstance(tt, dict):
        lines.extend(
            [
                "### Tiempo 1: Introducción",
                "",
                str(tt.get("introduccion", "")).strip(),
                "",
                "### Tiempo 2: Desarrollo — Base Conceptual y Articulación Aplicada",
                "",
                str(tt.get("desarrollo_base_conceptual", "")).strip(),
                "",
                str(tt.get("desarrollo_guia_aplicada", "")).strip(),
                "",
                "### Tiempo 3: Conclusiones",
                "",
                str(tt.get("conclusion", "")).strip(),
                "",
            ]
        )

    lines.extend(["## 4. Fichas de Investigación y Casos Aplicados", ""])
    for idx, fa in enumerate(nova_payload.get("fichas_investigacion_articulos", []), start=1):
        if not isinstance(fa, dict):
            continue
        lines.extend(
            [
                f"### Caso/Ficha {idx}: {fa.get('titulo_caso_o_articulo', '')}",
                f"- **Referencia**: {fa.get('autores_anio', '')}",
                f"- **Problema administrativo**: {fa.get('problema_administrativo', '')}",
                f"- **Metodología estadística**: {fa.get('metodologia_estadistica', '')}",
                f"- **Hallazgos y decisión gerencial**: {fa.get('hallazgos_y_decision', '')}",
                "",
            ]
        )

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


class ActivityExtractionTracker:
    """Gestiona y persiste en disco el estado en tiempo real de los 22 trabajos de extracción."""

    def __init__(
        self,
        subject_dir: Path = DEFAULT_SUBJECT_DIR,
        on_log: Callable[[str], None] | None = None,
        on_update: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.subject_dir = subject_dir.resolve()
        self.activities = _load_activities_spec(self.subject_dir)
        self.on_log = on_log
        self.on_update = on_update
        self._lock = threading.Lock()
        self.stop_requested = False

        slug = _materia_slug(self.subject_dir)
        self.extractor_root = self.subject_dir / "extractor-aulatex"
        self.conceptos_ref_root = self.subject_dir / f"referencias-{slug}" / f"conceptos-{slug}"
        self.extractor_root.mkdir(parents=True, exist_ok=True)
        self.conceptos_ref_root.mkdir(parents=True, exist_ok=True)
        self.state_path = self.extractor_root / "estado-trabajos-extraccion.json"
        self.state_ref_path = self.conceptos_ref_root / "estado-trabajos-extraccion.json"

        self.state: dict[str, Any] = self._load_or_init_state()

    def _log(self, msg: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{stamp}] {msg}"
        if self.on_log:
            self.on_log(line)
        else:
            print(line, flush=True)

    def _load_or_init_state(self) -> dict[str, Any]:
        existing_jobs: dict[int, dict[str, Any]] = {}
        if self.state_path.exists():
            try:
                raw = json.loads(self.state_path.read_text(encoding="utf-8"))
                for j in raw.get("jobs", []):
                    existing_jobs[int(j["num"])] = j
            except Exception:
                pass

        jobs: list[dict[str, Any]] = []
        for act in self.activities:
            num = int(act["num"])
            paths = get_paths_for_activity(self.subject_dir, act)
            out_dir = paths["extractor_conceptos_dir"]
            nova_json = out_dir / "investigacion_nova_pro.json"
            fichas_json = out_dir / "fichas_conceptos.json"
            ideas_json = out_dir / "ideas_detectadas.json"
            conceptos_json = out_dir / "conceptos_detectados.json"

            prev = existing_jobs.get(num, {})
            if nova_json.exists() and fichas_json.exists() and ideas_json.exists():
                try:
                    nova_data = json.loads(nova_json.read_text(encoding="utf-8"))
                    fichas_data = json.loads(fichas_json.read_text(encoding="utf-8"))
                    ideas_data = json.loads(ideas_json.read_text(encoding="utf-8"))
                    conceptos_data = json.loads(conceptos_json.read_text(encoding="utf-8")) if conceptos_json.exists() else []
                    meta = nova_data.get("_meta", {})
                    n_fichas = len({r.get("ficha") for r in fichas_data if r.get("ficha")}) or len(conceptos_data)
                    n_citas = len([r for r in fichas_data if r.get("cita_textual")])
                    n_sources = len({r.get("fuente") for r in fichas_data if r.get("fuente")})
                    jobs.append(
                        {
                            "num": num,
                            "code": act["code"],
                            "module_id": act["module_id"],
                            "unit_num": act["unit_num"],
                            "unit_title": act["unit_title"],
                            "moodle_title": act["moodle_title"],
                            "report_title": act["report_title"],
                            "kind": act["kind"],
                            "folder": act["folder"],
                            "status": "Completado",
                            "stage": "5/5 Completado (Nova Pro)",
                            "progress": 100,
                            "sources_count": n_sources or prev.get("sources_count", 11),
                            "fragments_count": meta.get("fragments_count", prev.get("fragments_count", 0)),
                            "concepts_count": len(conceptos_data),
                            "fichas_count": n_fichas,
                            "quotes_count": n_citas,
                            "ideas_count": len(ideas_data),
                            "engine": meta.get("engine", "Amazon Nova Pro"),
                            "provider_model": meta.get("provider_model", "us.amazon.nova-pro-v1:0"),
                            "total_tokens": meta.get("total_tokens", prev.get("total_tokens", 0)),
                            "elapsed_seconds": meta.get("elapsed_seconds", prev.get("elapsed_seconds", 0.0)),
                            "output_dir": str(out_dir.relative_to(self.subject_dir).as_posix()),
                            "notes_dir": str(paths["act_notes_dir"].relative_to(self.subject_dir).as_posix()),
                            "ref_conceptos_dir": str(paths["ref_conceptos_dir"].relative_to(self.subject_dir).as_posix()),
                            "updated_at": meta.get("timestamp", prev.get("updated_at", _utc_now())),
                            "error": "",
                        }
                    )
                    continue
                except Exception:
                    pass

            focal_files = list(paths["focal_corpus_dir"].glob("*.txt")) if paths["focal_corpus_dir"].exists() else []
            jobs.append(
                {
                    "num": num,
                    "code": act["code"],
                    "module_id": act["module_id"],
                    "unit_num": act["unit_num"],
                    "unit_title": act["unit_title"],
                    "moodle_title": act["moodle_title"],
                    "report_title": act["report_title"],
                    "kind": act["kind"],
                    "folder": act["folder"],
                    "status": "Pendiente",
                    "stage": "0/5 En espera",
                    "progress": 0,
                    "sources_count": len(focal_files),
                    "fragments_count": 0,
                    "concepts_count": len(act.get("seed_concepts", [])),
                    "fichas_count": 0,
                    "quotes_count": 0,
                    "ideas_count": 0,
                    "engine": "Amazon Nova Pro",
                    "provider_model": "us.amazon.nova-pro-v1:0",
                    "total_tokens": 0,
                    "elapsed_seconds": 0.0,
                    "output_dir": str(out_dir.relative_to(self.subject_dir).as_posix()),
                    "notes_dir": str(paths["act_notes_dir"].relative_to(self.subject_dir).as_posix()),
                    "ref_conceptos_dir": str(paths["ref_conceptos_dir"].relative_to(self.subject_dir).as_posix()),
                    "updated_at": _utc_now(),
                    "error": "",
                }
            )

        state = {
            "subject": self.subject_dir.name,
            "subject_path": str(self.subject_dir),
            "engine": "Amazon Nova Pro",
            "total_activities": len(jobs),
            "completed_activities": sum(1 for j in jobs if j["status"] == "Completado"),
            "overall_progress": round(sum(j["progress"] for j in jobs) / max(1, len(jobs)), 1),
            "updated_at": _utc_now(),
            "jobs": jobs,
        }
        self._save_state_unlocked(state)
        return state

    def _save_state_unlocked(self, state: dict[str, Any]) -> None:
        jobs = state.get("jobs", [])
        state["completed_activities"] = sum(1 for j in jobs if j["status"] == "Completado")
        state["overall_progress"] = round(sum(j["progress"] for j in jobs) / max(1, len(jobs)), 1)
        state["updated_at"] = _utc_now()
        payload = json.dumps(state, ensure_ascii=False, indent=2)
        self.state_path.write_text(payload, encoding="utf-8")
        try:
            self.state_ref_path.write_text(payload, encoding="utf-8")
        except Exception:
            pass
        if self.on_update:
            try:
                self.on_update(state)
            except Exception:
                pass

    def update_job(self, num: int, **updates: Any) -> None:
        with self._lock:
            for job in self.state["jobs"]:
                if int(job["num"]) == int(num):
                    job.update(updates)
                    job["updated_at"] = _utc_now()
                    break
            self._save_state_unlocked(self.state)

    def run_single_activity(self, act: dict[str, Any], *, force_nova: bool = False) -> dict[str, Any]:
        from aulatex.llm_bridge import AulaTeXLLMClient

        num = int(act["num"])
        code = act["code"]
        t0 = time.perf_counter()
        paths = get_paths_for_activity(self.subject_dir, act)

        try:
            # Etapa 1/5: Planeación y notas
            self.update_job(
                num,
                status="En ejecución",
                stage="1/5 Planeación y notas",
                progress=15,
                error="",
            )
            self._log(f"[{code}] Etapa 1/5: Cargando planeación, consigna oficial y conceptos semilla...")

            plan_text = read_any_text_file(paths["planeacion_file"]) if paths["planeacion_file"].exists() else ""
            consigna_text = read_any_text_file(paths["consigna_file"]) if paths["consigna_file"].exists() else plan_text
            seed_concepts = load_concept_lines(str(paths["seed_concepts_file"])) if paths["seed_concepts_file"].exists() else list(act.get("seed_concepts", []))
            plan_analysis = parse_planeacion_text(plan_text) if plan_text.strip() else None
            plan_concepts = extract_candidate_concepts_from_planeacion(plan_analysis, top_n=12) if plan_analysis else []

            # Etapa 2/5: Fragmentos y recuperación TF-IDF
            self.update_job(
                num,
                status="En ejecución",
                stage="2/5 Fragmentos y citas TF-IDF",
                progress=35,
            )
            source_dir = paths["focal_corpus_dir"] if paths["focal_corpus_dir"].exists() else paths["act_notes_dir"]
            pages, report = extract_pages_from_sources(source_dir, recursive=True, extensions=SUPPORTED_EXTENSIONS)
            fragments = build_fragments(pages, max_chars=1100, min_chars=140)
            corpus_concepts = extract_candidate_concepts(fragments, top_n=8) if fragments else []
            concepts = unique_preserve_order(seed_concepts + plan_concepts[:6] + corpus_concepts[:4])[:18]

            self._log(
                f"[{code}] Etapa 2/5: {len(report.loaded_files)} fuentes leídas, {len(fragments)} fragmentos citables, {len(concepts)} conceptos."
            )

            engine = TfidfSearchEngine(fragments=fragments)
            hits_by_concept = {}
            for concept in concepts:
                hits = engine.search(concept, top_k=10, threshold=0.03, max_quote_chars=680)[:6]
                hits_by_concept[concept] = hits
            fichas = build_fichas(concepts, hits_by_concept)

            self.update_job(
                num,
                sources_count=len(report.loaded_files),
                fragments_count=len(fragments),
                concepts_count=len(concepts),
                fichas_count=len(fichas),
                quotes_count=sum(len(f.hits) for f in fichas),
            )

            # Etapa 3/5: Investigación conceptual con Amazon Nova Pro
            self.update_job(
                num,
                status="En ejecución",
                stage="3/5 Extracción Amazon Nova Pro",
                progress=60,
            )

            cached_nova_path = paths["notes_investigacion_dir"] / f"investigacion-nova-pro-{code}.json"
            nova_payload: dict[str, Any] = {}
            if cached_nova_path.exists() and not force_nova:
                try:
                    loaded = json.loads(cached_nova_path.read_text(encoding="utf-8"))
                    if loaded.get("conceptos_clave") and loaded.get("estructura_tres_tiempos"):
                        nova_payload = loaded
                        self._log(f"[{code}] Etapa 3/5: Reutilizando extracción verificada de Amazon Nova Pro en caché.")
                except Exception:
                    nova_payload = {}

            if not nova_payload:
                self._log(f"[{code}] Etapa 3/5: Invocando Amazon Nova Pro (AulaTeXLLMClient) para investigación conceptual...")
                client = AulaTeXLLMClient()
                prompt = _build_nova_prompt(act, consigna_text, fichas)
                llm_res = client.call("Amazon Nova Pro", prompt, max_tokens=8192, timeout_seconds=240)
                if not llm_res.ok or not llm_res.text.strip():
                    raise RuntimeError(f"Amazon Nova Pro devolvió error en {code}: {llm_res.error}")

                nova_payload = _extract_json_block(llm_res.text)
                if not nova_payload or "estructura_tres_tiempos" not in nova_payload:
                    # Fallback estructurado preservando el texto íntegro devuelto por Nova Pro
                    nova_payload = {
                        "sintesis_ejecutiva": llm_res.text[:1500],
                        "conceptos_clave": [
                            {
                                "concepto": f.concept,
                                "definicion_rigurosa": f.hits[0].quote if f.hits else f.observation,
                                "formulacion_matematica_latex": "",
                                "aplicacion_administrativa": f"Aplicación en {act['report_title']}",
                                "fuente_principal": f.sources_text,
                                "localizador": f.locations_text,
                            }
                            for f in fichas[:10]
                        ],
                        "ideas_estructuradas": [],
                        "estructura_tres_tiempos": {
                            "introduccion": llm_res.text[:1200],
                            "desarrollo_base_conceptual": llm_res.text[1200:2800] or llm_res.text[:1200],
                            "desarrollo_guia_aplicada": llm_res.text[2800:4000] or llm_res.text[:1000],
                            "conclusion": llm_res.text[-1200:],
                        },
                        "fichas_investigacion_articulos": [],
                    }

                usage = llm_res.usage or {}
                elapsed_so_far = round(time.perf_counter() - t0, 2)
                nova_payload["_meta"] = {
                    "activity": num,
                    "code": code,
                    "module_id": act["module_id"],
                    "engine": llm_res.engine,
                    "requested_deployment": llm_res.requested_deployment or "us.amazon.nova-pro-v1:0",
                    "provider_model": llm_res.provider_model or "us.amazon.nova-pro-v1:0",
                    "finish_reason": llm_res.finish_reason,
                    "prompt_tokens": usage.get("prompt_tokens", 0),
                    "completion_tokens": usage.get("completion_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                    "fragments_count": len(fragments),
                    "sources_count": len(report.loaded_files),
                    "elapsed_seconds": elapsed_so_far,
                    "timestamp": _utc_now(),
                }
                paths["notes_investigacion_dir"].mkdir(parents=True, exist_ok=True)
                cached_nova_path.write_text(json.dumps(nova_payload, ensure_ascii=False, indent=2), encoding="utf-8")
                self._log(
                    f"[{code}] Etapa 3/5: Respuesta Amazon Nova Pro recibida ({nova_payload['_meta']['total_tokens']} tokens)."
                )

            # Etapa 4/5: Exportación y enriquecimiento de fichas, ideas y trazabilidad
            self.update_job(
                num,
                status="En ejecución",
                stage="4/5 Exportando fichas y trazabilidad",
                progress=85,
            )

            out_dir = paths["extractor_conceptos_dir"]
            out_dir.mkdir(parents=True, exist_ok=True)
            subject_slug = _materia_slug(self.subject_dir)

            exported_paths = export_all(
                fichas,
                out_dir,
                planeacion_analysis=plan_analysis,
                planeacion_remote=nova_payload.get("estructura_tres_tiempos"),
                planeacion_final=(
                    {
                        **(planeacion_to_dict(plan_analysis) if plan_analysis else {}),
                        "actividad_num": num,
                        "codigo": code,
                        "modulo_moodle": act["module_id"],
                        "titulo_actividad": act["moodle_title"],
                        "titulo_reporte": act["report_title"],
                        "unidad": act["unit_title"],
                        "sintesis_ejecutiva_nova_pro": nova_payload.get("sintesis_ejecutiva", ""),
                        "estructura_tres_tiempos": nova_payload.get("estructura_tres_tiempos", {}),
                    }
                ),
                subject_slug=subject_slug,
                concept_curation={
                    "engine": "Amazon Nova Pro",
                    "kept": concepts,
                    "conceptos_clave_nova_pro": nova_payload.get("conceptos_clave", []),
                },
                refinement_diagnostics={
                    "engine": "Amazon Nova Pro",
                    "meta": nova_payload.get("_meta", {}),
                    "fichas_investigacion_articulos": nova_payload.get("fichas_investigacion_articulos", []),
                },
                conceptos=concepts,
            )

            # Enriquecer ideas_detectadas.json combinando citas del corpus + ideas estructuradas de Nova Pro en 3 tiempos
            base_ideas = json.loads(exported_paths["ideas"].read_text(encoding="utf-8"))
            nova_ideas = []
            for item in nova_payload.get("ideas_estructuradas", []):
                if not isinstance(item, dict):
                    continue
                nova_ideas.append(
                    {
                        "concepto": item.get("concepto", ""),
                        "tipo": "idea_nova_pro",
                        "idea_base": item.get("idea_base", ""),
                        "argumento_academico": item.get("argumento_academico", ""),
                        "fuente": item.get("fuente", "Corpus bibliográfico de la materia"),
                        "ubicacion": item.get("ubicacion", ""),
                        "funcion_sugerida": item.get("tiempo_editorial", "desarrollo"),
                        "observacion": "Extraída y sintetizada con Amazon Nova Pro sobre el corpus focalizado.",
                    }
                )
            combined_ideas = nova_ideas + base_ideas
            exported_paths["ideas"].write_text(json.dumps(combined_ideas, ensure_ascii=False, indent=2), encoding="utf-8")

            # Guardar investigacion_nova_pro.json, sintesis_tres_tiempos_nova_pro.md y manifest.json
            nova_out_json = out_dir / "investigacion_nova_pro.json"
            nova_out_json.write_text(json.dumps(nova_payload, ensure_ascii=False, indent=2), encoding="utf-8")
            nova_out_md = out_dir / "sintesis_tres_tiempos_nova_pro.md"
            _export_nova_markdown(act, nova_payload, nova_out_md)

            elapsed = round(time.perf_counter() - t0, 2)
            meta = nova_payload.get("_meta", {})
            meta["elapsed_seconds"] = meta.get("elapsed_seconds") or elapsed
            meta["fragments_count"] = len(fragments)
            meta["sources_count"] = len(report.loaded_files)

            manifest_data = {
                "activity": num,
                "code": code,
                "module_id": act["module_id"],
                "unit_title": act["unit_title"],
                "moodle_title": act["moodle_title"],
                "report_title": act["report_title"],
                "engine": meta.get("engine", "Amazon Nova Pro"),
                "provider_model": meta.get("provider_model", "us.amazon.nova-pro-v1:0"),
                "ok": True,
                "sources_count": len(report.loaded_files),
                "fragments_count": len(fragments),
                "concepts_count": len(concepts),
                "fichas_count": len(fichas),
                "quotes_count": sum(len(f.hits) for f in fichas),
                "ideas_count": len(combined_ideas),
                "usage": {
                    "prompt_tokens": meta.get("prompt_tokens", 0),
                    "completion_tokens": meta.get("completion_tokens", 0),
                    "total_tokens": meta.get("total_tokens", 0),
                },
                "elapsed_seconds": meta["elapsed_seconds"],
                "timestamp": _utc_now(),
                "artifacts": sorted(p.name for p in out_dir.iterdir() if p.is_file()),
            }
            (out_dir / "manifest.json").write_text(json.dumps(manifest_data, ensure_ascii=False, indent=2), encoding="utf-8")

            # Sincronizar hacia referencias-<materia>/conceptos-<materia>/<actividad-folder>/
            # y hacia referencias-<materia>/notas-<materia>/<actividad-folder>/{investigacion, conceptos}/
            for mirror_dir in (
                paths["ref_conceptos_dir"],
                paths["notes_investigacion_dir"],
                paths["notes_conceptos_dir"],
            ):
                mirror_dir.mkdir(parents=True, exist_ok=True)
                for src_file in out_dir.iterdir():
                    if src_file.is_file():
                        shutil.copy2(src_file, mirror_dir / src_file.name)

            # Etapa 5/5: Completado
            self.update_job(
                num,
                status="Completado",
                stage="5/5 Completado (Nova Pro)",
                progress=100,
                sources_count=len(report.loaded_files),
                fragments_count=len(fragments),
                concepts_count=len(concepts),
                fichas_count=len(fichas),
                quotes_count=sum(len(f.hits) for f in fichas),
                ideas_count=len(combined_ideas),
                engine=meta.get("engine", "Amazon Nova Pro"),
                provider_model=meta.get("provider_model", "us.amazon.nova-pro-v1:0"),
                total_tokens=meta.get("total_tokens", 0),
                elapsed_seconds=meta["elapsed_seconds"],
                error="",
            )
            self._log(
                f"[{code}] Completado (5/5): {len(fichas)} fichas, {len(combined_ideas)} ideas, {meta.get('total_tokens', 0)} tokens en {meta['elapsed_seconds']}s."
            )
            return manifest_data

        except Exception as exc:
            err_msg = str(exc)
            self.update_job(
                num,
                status="Error",
                stage="Error en ejecución",
                error=err_msg,
            )
            self._log(f"[{code}] ERROR: {err_msg}")
            raise

    def run_batch(
        self,
        activity_numbers: list[int] | None = None,
        *,
        max_workers: int = 3,
        force_nova: bool = False,
    ) -> dict[str, Any]:
        self.stop_requested = False
        target_nums = set(activity_numbers) if activity_numbers else {int(a["num"]) for a in self.activities}
        selected_acts = [a for a in self.activities if int(a["num"]) in target_nums]

        self._log(
            f"Iniciando lote de extracción con Amazon Nova Pro para {len(selected_acts)} actividad(es) (workers={max_workers})..."
        )
        for a in selected_acts:
            self.update_job(int(a["num"]), status="En cola", stage="0/5 En cola", progress=5, error="")

        results: list[dict[str, Any]] = []
        errors: list[str] = []

        if max_workers <= 1:
            for act in selected_acts:
                if self.stop_requested:
                    self._log("Ejecución detenida por el usuario.")
                    break
                try:
                    results.append(self.run_single_activity(act, force_nova=force_nova))
                except Exception as exc:
                    errors.append(f"A{int(act['num']):02d}: {exc}")
        else:
            with ThreadPoolExecutor(max_workers=max_workers) as pool:
                future_map = {
                    pool.submit(self.run_single_activity, act, force_nova=force_nova): act
                    for act in selected_acts
                }
                for fut in as_completed(future_map):
                    act = future_map[fut]
                    try:
                        results.append(fut.result())
                    except Exception as exc:
                        errors.append(f"A{int(act['num']):02d}: {exc}")

        self._log(
            f"Lote finalizado. Completadas: {len(results)}/{len(selected_acts)} | Errores: {len(errors)}"
        )
        return {
            "completed": len(results),
            "total": len(selected_acts),
            "errors": errors,
            "state_path": str(self.state_path),
        }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Ejecuta el extractor conceptual e investigación con Amazon Nova Pro por actividad."
    )
    parser.add_argument(
        "--materia-dir",
        default=str(DEFAULT_SUBJECT_DIR),
        help="Ruta a la carpeta raíz de la materia.",
    )
    parser.add_argument(
        "--actividades",
        default="",
        help="Lista de números de actividad separados por coma (ej. 1,2,3) o vacío para todas (1..22).",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=4,
        help="Número de trabajadores concurrentes para llamadas a Amazon Nova Pro.",
    )
    parser.add_argument(
        "--forzar-nova",
        action="store_true",
        help="Fuerza nueva llamada a Amazon Nova Pro aunque exista caché previa.",
    )
    args = parser.parse_args(argv)

    act_nums: list[int] | None = None
    if args.actividades.strip():
        act_nums = [int(x.strip()) for x in args.actividades.split(",") if x.strip().isdigit()]

    tracker = ActivityExtractionTracker(Path(args.materia_dir))
    summary = tracker.run_batch(act_nums, max_workers=max(1, args.workers), force_nova=args.forzar_nova)
    if summary["errors"]:
        print("Errores detectados:", summary["errors"], file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
