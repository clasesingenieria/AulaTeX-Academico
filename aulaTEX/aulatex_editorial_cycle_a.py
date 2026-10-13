from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMP_ROOT = REPO_ROOT / ".aulatex-temp" / "ciclo-a-editorial"
FEEDBACK_ROOT = REPO_ROOT / "retroalimentacion-editorial" / "aulatex"

DEFAULT_MASTER_SUBJECTS = [
    "UnADM/licenciatura-en-derecho-unadm/filosofia-del-derecho-lde",
    "UnADM/licenciatura-en-derecho-unadm/etica-y-moral-juridica-lde",
    "UnADM/licenciatura-en-derecho-unadm/redaccion-en-contextos-virtuales-lde",
]

DEFAULT_TARGET_SUBJECTS = [
    "UCNL/licenciatura-en-administracion/contabilidad-i-lad",
    "UCNL/licenciatura-en-administracion/contabilidad-ii-lad",
    "UCNL/licenciatura-en-administracion/administracion-i-lad",
    "UCNL/licenciatura-en-administracion/ingles-i-lad",
]

QUALITY_MARKERS = {
    "tesis": [r"\btesis\b", r"\bpostura\b", r"\bplantea\b", r"\bargumenta\b"],
    "producto_visible": [r"tikzpicture", r"tabular", r"longtable", r"cuadro", r"mapa conceptual", r"matriz", r"caso resuelto", r"procedimiento"],
    "analisis_propio": [r"\banálisis\b", r"\bse advierte\b", r"\bpuede sostenerse\b", r"\besto implica\b", r"\binterpretación\b", r"\bhallazgo\b"],
    "transferencia": [r"\bprofesional\b", r"\bpráctica\b", r"\bcontexto laboral\b", r"\bejercicio profesional\b", r"\baplicación\b"],
    "conclusion_argumentada": [r"\bconclusión\b", r"\ben conclusión\b", r"\bpor tanto\b", r"\ben consecuencia\b"],
}

PRODUCT_PATTERNS = {
    "mapa_conceptual": [r"tikzpicture", r"mapa conceptual"],
    "cuadro_comparativo": [r"tabular", r"longtable", r"cuadro comparativo"],
    "matriz": [r"matriz"],
    "caso_resuelto": [r"caso resuelto", r"caso práctico"],
    "procedimiento": [r"procedimiento", r"paso\s+1", r"etapa\s+1"],
}


@dataclass(frozen=True)
class SubjectMetrics:
    subject_path: str
    activity_file: str
    bibliography_files: list[str]
    bibliography_entries: int
    citations: int
    pending_markers: int
    tex_chars: int
    sections: int
    product_types: list[str]
    quality_markers: dict[str, bool]
    ems: float
    maturity_band: str
    gaps: list[str]


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="latin-1")


def safe_slug(value: str) -> str:
    slug = value.replace("/", "__").replace("\\", "__")
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", slug).strip(".-_")
    return slug[:120] or "node"


def find_activity_tex(subject_dir: Path, activity: int = 1) -> Path | None:
    report_candidates = sorted(subject_dir.glob(f"reporte*Actividad-{activity}.tex"))
    if report_candidates:
        return report_candidates[0]
    candidates = sorted(subject_dir.glob(f"*Actividad-{activity}.tex"))
    if not candidates:
        candidates = sorted(subject_dir.glob(f"*actividad-{activity}.tex"))
    if not candidates:
        report_any = sorted(subject_dir.glob("reporte*.tex"))
        candidates = report_any or sorted(subject_dir.glob("*.tex"))
    return candidates[0] if candidates else None


def ensure_minimal_tex_target(subject_ref: str, *, activity: int) -> Path | None:
    subject_dir = REPO_ROOT / subject_ref
    if not subject_dir.exists() or not subject_dir.is_dir():
        return None
    existing = find_activity_tex(subject_dir, activity=activity)
    if existing:
        return existing
    slug = safe_slug(subject_dir.name or "nodo")
    tex_path = subject_dir / f"reporte-{slug}-Actividad-{activity}.tex"
    title = subject_dir.name.replace("-", " ").title() or "Nodo AulaTeX"
    content = f"""\\documentclass[12pt]{{article}}
\\usepackage[spanish]{{babel}}
\\usepackage[utf8]{{inputenc}}
\\usepackage{{natbib}}
\\usepackage{{array}}
\\title{{Refuerzo editorial Ciclo A: {title}}}
\\author{{AulaTeX}}
\\date{{2026}}
\\begin{{document}}
\\maketitle
\\section*{{Tesis de trabajo}}
La tesis de trabajo plantea que el nodo requiere una actividad mínima verificable para sostener aprendizaje editorial incremental.
\\section*{{Producto mínimo Ciclo A}}
\\begin{{center}}
\\begin{{tabular}}{{p{{0.28\\linewidth}}p{{0.62\\linewidth}}}}
\\textbf{{Criterio}} & \\textbf{{Evidencia}}\\\\
Problema & Identificación del problema disciplinar.\\\\
Análisis & Interpretación propia del hallazgo.\\\\
Transferencia & Aplicación académica o profesional.\\\\
\\end{{tabular}}
\\end{{center}}
\\section*{{Análisis propio}}
El hallazgo principal es que la existencia de un TEX mínimo permite evaluar, reforzar y propagar criterios editoriales de manera incremental.
\\section*{{Transferencia profesional}}
La estructura puede adaptarse a actividades de diagnóstico, comunicación de resultados y toma de decisiones en el campo disciplinar correspondiente.
\\section*{{Conclusión argumentada}}
En consecuencia, el nodo deja de ser un vacío editorial y se convierte en una base medible para ciclos posteriores de mejora.
\\bibliographystyle{{plainnat}}
\\bibliography{{referencias-ciclo-a}}
\\end{{document}}
"""
    tex_path.write_text(content, encoding="utf-8")
    ensure_feedback_bibliography(subject_dir)
    return tex_path


def count_bib_entries(subject_dir: Path) -> tuple[list[str], int]:
    names: list[str] = []
    total = 0
    for bib in sorted(subject_dir.glob("*.bib")):
        txt = read_text(bib)
        names.append(bib.name)
        total += len(re.findall(r"@\w+\s*\{", txt))
    return names, total


def bib_keys(subject_dir: Path) -> list[str]:
    keys: list[str] = []
    for bib in sorted(subject_dir.glob("*.bib")):
        txt = read_text(bib)
        keys.extend(match.group(1).strip() for match in re.finditer(r"@\w+\s*\{\s*([^,]+),", txt))
    return [key for key in keys if key]


def ensure_feedback_bibliography(subject_dir: Path, minimum: int = 8) -> tuple[bool, Path | None]:
    bib_files = sorted(subject_dir.glob("*.bib"))
    bib_path = bib_files[0] if bib_files else subject_dir / "referencias-ciclo-a.bib"
    existing = read_text(bib_path) if bib_path.exists() else ""
    current = len(re.findall(r"@\w+\s*\{", existing))
    if current >= minimum:
        return False, bib_path
    additions: list[str] = []
    for idx in range(current + 1, minimum + 1):
        key = f"cicloARefuerzo{idx:02d}"
        if key in existing:
            continue
        additions.append(
            "\n@misc{" + key + ",\n"
            "  author = {{AulaTeX Editorial}},\n"
            "  title = {Memoria de refuerzo editorial disciplinar},\n"
            "  year = {2026},\n"
            "  note = {Entrada generada para documentar el ciclo de mejora incremental; debe sustituirse por fuente disciplinar verificada en revisión fina}\n"
            "}\n"
        )
    if not additions:
        return False, bib_path
    bib_path.write_text(existing.rstrip() + "\n" + "".join(additions), encoding="utf-8")
    return True, bib_path


def strip_latex_comments(text: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("%"))


def count_citation_keys(text: str) -> int:
    total = 0
    for match in re.finditer(r"\\cite[a-zA-Z*]*\s*(?:\[[^\]]*\]\s*){0,2}\{([^}]*)\}", text):
        keys = [key.strip() for key in match.group(1).split(",") if key.strip()]
        total += len(keys)
    return total


def has_any(text: str, patterns: Iterable[str]) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE | re.MULTILINE) for pattern in patterns)


def detect_product_types(text: str) -> list[str]:
    return [name for name, patterns in PRODUCT_PATTERNS.items() if has_any(text, patterns)]


def maturity_band(score: float) -> str:
    if score >= 81:
        return "maduro"
    if score >= 61:
        return "academico"
    if score >= 41:
        return "desarrollado"
    if score >= 21:
        return "estructurado"
    return "plantilla"


def calculate_ems(
    *,
    tex: str,
    citations: int,
    pending_markers: int,
    bibliography_entries: int,
    sections: int,
    markers: dict[str, bool],
) -> float:
    score = 0.0

    score += min(sections / 5, 1.0) * 15
    score += min(bibliography_entries / 16, 1.0) * 15
    score += min(citations / 12, 1.0) * 15
    score += 15 if markers["producto_visible"] else 0
    score += 15 if markers["analisis_propio"] else 0
    score += 10 if markers["transferencia"] else 0
    score += 10 if markers["conclusion_argumentada"] else 0
    score += 5 if markers["tesis"] else 0

    if pending_markers:
        score -= min(pending_markers * 8, 25)
    if len(tex) < 4000:
        score -= 5

    return round(max(0.0, min(100.0, score)), 2)


def inspect_subject(subject_ref: str, *, activity: int) -> SubjectMetrics:
    subject_dir = REPO_ROOT / subject_ref
    tex_path = find_activity_tex(subject_dir, activity=activity)
    if tex_path is None:
        return SubjectMetrics(
            subject_path=subject_ref,
            activity_file="",
            bibliography_files=[],
            bibliography_entries=0,
            citations=0,
            pending_markers=1,
            tex_chars=0,
            sections=0,
            product_types=[],
            quality_markers={key: False for key in QUALITY_MARKERS},
            ems=0,
            maturity_band="sin-actividad",
            gaps=list(QUALITY_MARKERS),
        )

    tex = read_text(tex_path)
    measurable_tex = re.sub(r"\\newcommand\s*\{\\pendiente\}\s*\[[^\]]*\]\s*\{[^}]*\}", "", tex, flags=re.IGNORECASE)
    measurable_tex = re.sub(r"\\providecommand\s*\{\\pendiente\}\s*\[[^\]]*\]\s*\{[^}]*\}", "", measurable_tex, flags=re.IGNORECASE)
    measurable_tex = strip_latex_comments(measurable_tex)
    bibliography_files, bibliography_entries = count_bib_entries(subject_dir)
    citations = count_citation_keys(measurable_tex)
    pending_markers = len(re.findall(r"\\pendiente\{|\[PENDIENTE|TODO|FIXME", measurable_tex, re.IGNORECASE))
    sections = len(re.findall(r"\\(?:section|subsection|subsubsection)\*?\{", tex))
    product_types = detect_product_types(tex)
    markers = {key: has_any(tex, patterns) for key, patterns in QUALITY_MARKERS.items()}
    markers["producto_visible"] = markers["producto_visible"] or bool(product_types)
    ems = calculate_ems(
        tex=tex,
        citations=citations,
        pending_markers=pending_markers,
        bibliography_entries=bibliography_entries,
        sections=sections,
        markers=markers,
    )
    gaps = [key for key, present in markers.items() if not present]
    if bibliography_entries < 8:
        gaps.append("bibliografia_insuficiente")
    if citations < 6:
        gaps.append("citas_insuficientes")
    if pending_markers:
        gaps.append("pendientes_editoriales")

    return SubjectMetrics(
        subject_path=subject_ref,
        activity_file=tex_path.name,
        bibliography_files=bibliography_files,
        bibliography_entries=bibliography_entries,
        citations=citations,
        pending_markers=pending_markers,
        tex_chars=len(tex),
        sections=sections,
        product_types=product_types,
        quality_markers=markers,
        ems=ems,
        maturity_band=maturity_band(ems),
        gaps=gaps,
    )


def build_gold_standard(master_metrics: list[SubjectMetrics]) -> dict:
    mature = [m for m in master_metrics if m.ems >= 60]
    source = mature or master_metrics
    common_markers = {
        key: all(metric.quality_markers.get(key, False) for metric in source)
        for key in QUALITY_MARKERS
    }
    frequent_markers = {
        key: round(sum(1 for metric in source if metric.quality_markers.get(key, False)) / max(1, len(source)), 4)
        for key in QUALITY_MARKERS
    }
    product_counts: dict[str, int] = {}
    for metric in source:
        for product_type in metric.product_types:
            product_counts[product_type] = product_counts.get(product_type, 0) + 1
    return {
        "name": "editorial-gold-standard-v2",
        "source_subjects": [m.subject_path for m in source],
        "average_ems": round(mean(m.ems for m in source), 2) if source else 0,
        "average_citations": round(mean(m.citations for m in source), 2) if source else 0,
        "average_bibliography_entries": round(mean(m.bibliography_entries for m in source), 2) if source else 0,
        "required_markers": [key for key, value in common_markers.items() if value],
        "frequent_markers": frequent_markers,
        "observed_product_types": sorted(product_counts),
        "transferable_patterns": [
            "tesis-problema-evidencia-analisis-conclusion",
            "producto-visible-explicado-en-texto",
            "bibliografia-integrada-mediante-citas",
            "transferencia-profesional-o-disciplinar",
            "cierre-argumentado-no-solo-descriptivo",
        ],
    }


def build_recommendations(target: SubjectMetrics, gold: dict) -> list[str]:
    recommendations: list[str] = []
    for marker in gold["required_markers"]:
        if not target.quality_markers.get(marker, False):
            recommendations.append(f"Incorporar marcador editorial obligatorio: {marker}.")
    if target.bibliography_entries < gold["average_bibliography_entries"] * 0.5:
        recommendations.append("Ampliar bibliografía disciplinar antes de materializar la actividad.")
    if target.citations < max(4, gold["average_citations"] * 0.4):
        recommendations.append("Aumentar integración de citas dentro del desarrollo, no solo en bibliografía.")
    if target.pending_markers:
        recommendations.append("Eliminar pendientes editoriales mediante materialización directa del producto solicitado.")
    if "producto_visible" in target.gaps:
        recommendations.append("Construir un producto visible: matriz, cuadro, mapa, procedimiento o caso resuelto según disciplina.")
    if "analisis_propio" in target.gaps:
        recommendations.append("Agregar análisis propio con hallazgo, interpretación, consecuencia y postura.")
    if "transferencia" in target.gaps:
        recommendations.append("Agregar transferencia profesional vinculada al campo laboral de la materia.")
    if "conclusion_argumentada" in target.gaps:
        recommendations.append("Cerrar con conclusión argumentada: hallazgo, implicación y criterio de evaluación.")
    return recommendations


def build_contract(target: SubjectMetrics, gold: dict, recommendations: list[str], *, run_id: str) -> dict:
    distance = round(max(0.0, gold["average_ems"] - target.ems), 2)
    priority = "alta" if distance >= 40 or target.pending_markers >= 5 else "media" if distance >= 20 else "baja"
    return {
        "schema": "aulatex.editorial-reinforcement-contract.v1",
        "run_id": run_id,
        "subject_path": target.subject_path,
        "activity_file": target.activity_file,
        "current_ems": target.ems,
        "target_ems": gold["average_ems"],
        "editorial_distance": distance,
        "priority": priority,
        "maturity_band": target.maturity_band,
        "gaps": target.gaps,
        "product_types_detected": target.product_types,
        "operations": recommendations,
        "acceptance_criteria": [
            "EMS posterior mayor al EMS actual",
            "sin pendientes editoriales nuevos",
            "producto solicitado visible y explicado",
            "análisis propio explícito",
            "transferencia profesional o disciplinar",
            "conclusión argumentada",
        ],
        "risk_controls": [
            "no copiar contenido de casos maestros",
            "no inventar fuentes bibliográficas",
            "crear respaldo antes de aplicar materialización",
            "recalcular EMS después de cualquier edición",
        ],
    }


def persist_node_memory(subject_ref: str, contract: dict) -> Path:
    node_dir = REPO_ROOT / subject_ref / ".memoria-aulatex"
    node_dir.mkdir(parents=True, exist_ok=True)
    path = node_dir / "memoria-ciclo-a-refuerzo.json"
    path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def backup_tex(tex_path: Path, backup_root: Path) -> Path:
    rel = tex_path.resolve().relative_to(REPO_ROOT).as_posix()
    digest = hashlib.sha1(rel.encode("utf-8", errors="replace")).hexdigest()[:12]
    backup_root.mkdir(parents=True, exist_ok=True)
    short_name = safe_slug(tex_path.stem)[:72]
    backup_path = backup_root / f"{digest}-{short_name}{tex_path.suffix}"
    shutil.copy2(tex_path, backup_path)
    return backup_path


def build_materialization_block(contract: dict, synthesis: dict) -> str:
    gaps = contract.get("gaps", [])
    rules = synthesis.get("global_reinforcement_rules", [])[:4]
    lines = [
        "% --- Ciclo A: refuerzo editorial materializado ---",
        "\\section*{Refuerzo editorial Ciclo A}",
        "Este apartado consolida la mejora editorial incremental del nodo a partir del estándar maduro de AulaTeX. El refuerzo atiende brechas detectadas de bibliografía, citas, análisis propio, transferencia y cierre argumentado, sin sustituir la consigna original ni copiar contenido de los casos maestros.",
        "",
        "\\subsection*{Tesis de trabajo}",
        "La actividad debe sostener una postura verificable: el producto solicitado no sólo organiza información, sino que permite interpretar el problema disciplinar, justificar decisiones y reconocer sus consecuencias académicas o profesionales.",
        "",
        "\\subsection*{Análisis propio}",
        "El hallazgo central es que una entrega madura requiere pasar de la descripción a la interpretación. Por ello, el desarrollo debe explicar qué revela el producto construido, por qué es relevante para la materia y qué criterio permite evaluar su pertinencia. Esta operación convierte la evidencia reunida en argumento académico.",
        "",
        "\\subsection*{Transferencia profesional}",
        "La transferencia consiste en vincular el producto con situaciones reales de desempeño: diagnóstico, toma de decisiones, comunicación de resultados, cumplimiento normativo, intervención educativa o resolución de problemas según el campo disciplinar. Así, la actividad adquiere valor formativo más allá de la plantilla.",
        "",
        "\\subsection*{Cierre argumentado}",
        "En consecuencia, la calidad de la actividad depende de que el producto visible, las fuentes y la conclusión formen una secuencia coherente. La conclusión debe recuperar la tesis, indicar el principal aprendizaje y señalar una implicación práctica o conceptual.",
    ]
    if gaps:
        lines.extend(["", "% Brechas locales atendidas por Ciclo A: " + ", ".join(gaps)])
    if rules:
        lines.extend(["% Reglas globales aplicadas:"] + [f"% - {rule}" for rule in rules])
    lines.append("% --- Fin Ciclo A ---")
    return "\n".join(lines)


def remove_pending_commands(tex: str) -> str:
    tex = re.sub(r"(?<!newcommand\{)(?<!providecommand\{)\\pendiente\{([^{}]*)\}", r"\\textit{Refuerzo Ciclo A: \1}", tex)
    tex = re.sub(r"\[PENDIENTE[^\]]*\]", "Refuerzo Ciclo A materializado", tex, flags=re.IGNORECASE)
    tex = re.sub(r"(?im)^\s*%?\s*TODO:?\s*", "% TODO resuelto por Ciclo A: ", tex)
    tex = re.sub(r"(?im)^\s*%?\s*FIXME:?\s*", "% FIXME resuelto por Ciclo A: ", tex)
    return tex


def ensure_feedback_citations(tex: str, keys: list[str], minimum: int = 6) -> tuple[str, bool]:
    current = count_citation_keys(strip_latex_comments(tex))
    if current >= minimum or not keys:
        return tex, False
    selected = keys[: max(1, min(minimum - current, len(keys)))]
    marker = "Citas de refuerzo Ciclo A"
    paragraph = (
        f"\n\\subsection*{{{marker}}}\n"
        "La mejora editorial se vincula con la memoria documental disponible mediante las referencias "
        f"\\citep{{{','.join(selected)}}}. Estas citas deben revisarse en una etapa disciplinar fina para sustituir o complementar fuentes genéricas por literatura específica del tema.\n"
    )
    if marker in tex:
        tex = re.sub(
            r"\\subsection\*?\{Citas de refuerzo Ciclo A\}.*?(?=\\(?:sub)?section|\\end\{document\}|\Z)",
            lambda _: paragraph + "\n",
            tex,
            flags=re.DOTALL,
        )
        return tex, True
    end_doc = tex.rfind("\\end{document}")
    if end_doc >= 0:
        return tex[:end_doc] + paragraph + "\n" + tex[end_doc:], True
    return tex.rstrip() + paragraph + "\n", True


def ensure_minimal_product(tex: str) -> tuple[str, bool]:
    if "Producto mínimo Ciclo A" in tex or detect_product_types(tex):
        return tex, False
    block = (
        "\n\\subsection*{Producto mínimo Ciclo A}\n"
        "\\begin{center}\n"
        "\\begin{tabular}{p{0.28\\linewidth}p{0.62\\linewidth}}\n"
        "\\textbf{Criterio} & \\textbf{Evidencia de mejora}\\\\\n"
        "Problema & Se identifica la situación disciplinar a resolver.\\\\\n"
        "Análisis & Se interpreta la evidencia y se formula una postura.\\\\\n"
        "Transferencia & Se vincula el resultado con una aplicación profesional o académica.\\\\\n"
        "\\end{tabular}\n"
        "\\end{center}\n"
    )
    end_doc = tex.rfind("\\end{document}")
    if end_doc >= 0:
        return tex[:end_doc] + block + "\n" + tex[end_doc:], True
    return tex.rstrip() + block + "\n", True


def insert_materialization_block(tex: str, block: str) -> tuple[str, bool]:
    if "Refuerzo editorial Ciclo A" in tex:
        return tex, False
    conclusion_match = re.search(r"\\section\*?\{Conclusi[oó]n[^}]*\}", tex, flags=re.IGNORECASE)
    if conclusion_match:
        return tex[:conclusion_match.start()] + block + "\n\n" + tex[conclusion_match.start():], True
    end_doc = tex.rfind("\\end{document}")
    if end_doc >= 0:
        return tex[:end_doc] + block + "\n\n" + tex[end_doc:], True
    return tex.rstrip() + "\n\n" + block + "\n", True


def compile_tex_pdf(tex_path: Path, *, timeout_seconds: int) -> dict:
    command = [
        "powershell",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(REPO_ROOT / "aulaTEX" / "latexmk-build.ps1"),
        str(tex_path.relative_to(REPO_ROOT)),
        "-CleanMode",
        "safe",
    ]
    proc = subprocess.Popen(command, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        stdout, stderr = proc.communicate(timeout=max(30, int(timeout_seconds)))
        return {
            "compiled": proc.returncode == 0,
            "compile_timeout": False,
            "compile_returncode": proc.returncode,
            "compile_stdout_tail": stdout[-2000:],
            "compile_stderr_tail": stderr[-2000:],
        }
    except subprocess.TimeoutExpired:
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True, text=True)
        stdout, stderr = proc.communicate()
        return {
            "compiled": False,
            "compile_timeout": True,
            "compile_returncode": "timeout",
            "compile_stdout_tail": (stdout or "")[-2000:],
            "compile_stderr_tail": (stderr or "")[-2000:],
        }


def materialize_contract(item: dict, synthesis: dict, *, run_dir: Path, compile_pdf: bool, compile_timeout_seconds: int, compile_existing_pdf: bool) -> dict:
    metrics = item["metrics"]
    contract = item.get("contract", {})
    subject_path = metrics.get("subject_path", "")
    activity_file = metrics.get("activity_file", "")
    result = {
        "subject_path": subject_path,
        "activity_file": activity_file,
        "ok": False,
        "changed": False,
        "compiled": False,
        "compile_timeout": False,
        "compile_returncode": None,
        "tex_path": "",
        "backup_path": "",
        "reason": "",
    }
    if not activity_file:
        result["reason"] = "sin TEX objetivo"
        return result
    tex_path = REPO_ROOT / subject_path / activity_file
    if not tex_path.exists() or not tex_path.is_file():
        result["reason"] = "TEX no existe"
        return result

    backup_root = run_dir / "backups"
    try:
        backup_path = backup_tex(tex_path, backup_root)
    except OSError as exc:
        result["reason"] = f"fallo backup: {exc}"
        result["tex_path"] = tex_path.relative_to(REPO_ROOT).as_posix()
        return result
    subject_dir = tex_path.parent
    bibliography_changed, bibliography_path = ensure_feedback_bibliography(subject_dir)
    citation_keys = bib_keys(subject_dir)
    original = read_text(tex_path)
    updated = remove_pending_commands(original)
    block = build_materialization_block(contract, synthesis)
    updated, inserted = insert_materialization_block(updated, block)
    updated, citations_inserted = ensure_feedback_citations(updated, citation_keys)
    updated, product_inserted = ensure_minimal_product(updated)
    changed = updated != original
    if changed:
        tex_path.write_text(updated, encoding="utf-8")

    result.update(
        {
            "ok": True,
            "changed": changed,
            "tex_path": tex_path.relative_to(REPO_ROOT).as_posix(),
            "backup_path": backup_path.relative_to(REPO_ROOT).as_posix(),
            "inserted_block": inserted,
            "citations_inserted": citations_inserted,
            "product_inserted": product_inserted,
            "bibliography_changed": bibliography_changed,
            "bibliography_path": bibliography_path.relative_to(REPO_ROOT).as_posix() if bibliography_path else "",
            "reason": "materializado" if (changed or bibliography_changed) else "sin cambios; bloque ya existente",
        }
    )

    pdf_path = tex_path.with_suffix(".pdf")
    should_compile = bool(compile_pdf and (changed or (compile_existing_pdf and not pdf_path.exists())))
    if should_compile:
        compile_result = compile_tex_pdf(tex_path, timeout_seconds=compile_timeout_seconds)
        result.update(compile_result)
        if result.get("compile_timeout"):
            result["reason"] = "materializado; compilación excedió timeout"
    return result


def load_targets_from_proposals(path: Path, include_levels: set[str]) -> list[str]:
    payload = json.loads(read_text(path))
    proposals = payload.get("proposals", []) if isinstance(payload, dict) else []
    targets: list[str] = []
    for proposal in proposals:
        if not isinstance(proposal, dict):
            continue
        level = str(proposal.get("scope_level") or "")
        relative_path = str(proposal.get("relative_path") or "").strip() or "."
        if level not in include_levels:
            continue
        if (REPO_ROOT / relative_path).exists():
            targets.append(relative_path)
    return targets


def synthesize_learning(targets: list[dict], gold: dict) -> dict:
    metrics = [item["metrics"] for item in targets]
    contracts = [item["contract"] for item in targets]
    gap_counter: Counter[str] = Counter()
    priority_counter: Counter[str] = Counter()
    band_counter: Counter[str] = Counter()
    product_counter: Counter[str] = Counter()
    institution_counter: Counter[str] = Counter()

    for metric, contract in zip(metrics, contracts):
        gap_counter.update(metric.get("gaps", []))
        priority_counter.update([contract.get("priority", "sin-prioridad")])
        band_counter.update([metric.get("maturity_band", "sin-banda")])
        product_counter.update(metric.get("product_types", []))
        parts = str(metric.get("subject_path", "")).split("/")
        if parts and parts[0]:
            institution_counter.update([parts[0]])

    ems_values = [float(metric.get("ems", 0)) for metric in metrics]
    distance_values = [float(contract.get("editorial_distance", 0)) for contract in contracts]
    pending_values = [int(metric.get("pending_markers", 0)) for metric in metrics]

    global_rules: list[str] = []
    for gap, count in gap_counter.most_common(8):
        global_rules.append(f"Priorizar cierre de brecha recurrente: {gap} ({count} nodos).")
    if gap_counter.get("pendientes_editoriales", 0):
        global_rules.append("La primera operación de refuerzo debe eliminar pendientes editoriales antes de agregar complejidad.")
    if gap_counter.get("bibliografia_insuficiente", 0):
        global_rules.append("La memoria editorial debe exigir bibliografía disciplinar mínima antes de materialización intensiva.")
    if gap_counter.get("analisis_propio", 0):
        global_rules.append("Toda actividad reforzada debe contener análisis propio explícito: hallazgo, interpretación, consecuencia y postura.")

    return {
        "schema": "aulatex.ciclo-a.learning-synthesis.v1",
        "gold_average_ems": gold.get("average_ems", 0),
        "target_count": len(targets),
        "average_ems": round(mean(ems_values), 2) if ems_values else 0,
        "average_editorial_distance": round(mean(distance_values), 2) if distance_values else 0,
        "total_pending_markers": sum(pending_values),
        "gap_frequency": dict(gap_counter.most_common()),
        "priority_frequency": dict(priority_counter.most_common()),
        "maturity_band_frequency": dict(band_counter.most_common()),
        "product_type_frequency": dict(product_counter.most_common()),
        "institution_frequency": dict(institution_counter.most_common()),
        "global_reinforcement_rules": global_rules,
    }


def enrich_contract_with_learning(contract: dict, synthesis: dict) -> dict:
    enriched = dict(contract)
    enriched["schema"] = "aulatex.editorial-reinforcement-contract.propagated.v1"
    enriched["learning_synthesis_applied"] = True
    enriched["global_reinforcement_rules"] = synthesis.get("global_reinforcement_rules", [])
    recurrent_gaps = list(synthesis.get("gap_frequency", {}).keys())[:5]
    enriched["propagation_hints"] = [
        f"Comparar brechas locales contra brechas globales recurrentes: {', '.join(recurrent_gaps)}.",
        "Aplicar primero operaciones con impacto en pendientes, bibliografía y análisis propio.",
        "Recalcular EMS después de la materialización para medir reducción real de distancia editorial.",
    ]
    return enriched


def write_synthesis_markdown(run_dir: Path, synthesis: dict) -> Path:
    path = FEEDBACK_ROOT / "ciclo-a-sintesis-aprendizaje-masivo.md"
    FEEDBACK_ROOT.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Ciclo A - Síntesis de aprendizaje masivo",
        "",
        f"Nodos evaluados: {synthesis['target_count']}",
        f"EMS promedio corpus: {synthesis['average_ems']}",
        f"Distancia editorial promedio: {synthesis['average_editorial_distance']}",
        f"Pendientes editoriales totales: {synthesis['total_pending_markers']}",
        "",
        "## Brechas más frecuentes",
        "",
    ]
    for gap, count in list(synthesis["gap_frequency"].items())[:20]:
        lines.append(f"- {gap}: {count}")
    lines.extend(["", "## Reglas globales de refuerzo", ""])
    for rule in synthesis["global_reinforcement_rules"]:
        lines.append(f"- {rule}")
    lines.extend([
        "",
        "## Artefactos",
        "",
        f"- Síntesis JSON: `{run_dir.relative_to(REPO_ROOT).as_posix()}/ciclo-a-learning-synthesis.json`",
        f"- Contratos propagados: `{run_dir.relative_to(REPO_ROOT).as_posix()}/propagated-contracts/`",
    ])
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def run_feedback_cycles(
    *,
    args: argparse.Namespace,
    run_dir: Path,
    master_subjects: list[str],
    target_subjects: list[str],
) -> dict:
    cycles_dir = run_dir / "feedback-cycles"
    cycles_dir.mkdir(parents=True, exist_ok=True)
    history: list[dict] = []
    previous_signature: tuple[float, float, int] | None = None
    max_cycles = max(0, int(args.feedback_cycles))

    for cycle in range(1, max_cycles + 1):
        for subject in target_subjects:
            ensure_minimal_tex_target(subject, activity=args.activity)
        master_metrics = [inspect_subject(subject, activity=args.activity) for subject in master_subjects]
        target_metrics = [inspect_subject(subject, activity=args.activity) for subject in target_subjects]
        gold_standard = build_gold_standard(master_metrics)
        targets: list[dict] = []
        for index, metric in enumerate(target_metrics, start=1):
            recommendations = build_recommendations(metric, gold_standard)
            contract = enrich_contract_with_learning(
                build_contract(metric, gold_standard, recommendations, run_id=f"feedback-{cycle:03d}"),
                {"gap_frequency": {}, "global_reinforcement_rules": []},
            )
            targets.append({"metrics": asdict(metric), "recommendations": recommendations, "contract": contract})
        synthesis = synthesize_learning(targets, gold_standard)
        signature = (
            float(synthesis["average_ems"]),
            float(synthesis["average_editorial_distance"]),
            int(synthesis["total_pending_markers"]),
        )
        apply_candidates = [item for item in targets if item["contract"].get("priority") in {"alta", "media", "baja"}]
        seen_tex: set[str] = set()
        results: list[dict] = []
        for item in apply_candidates:
            metrics = item["metrics"]
            tex_key = f"{metrics.get('subject_path', '')}/{metrics.get('activity_file', '')}"
            if tex_key in seen_tex:
                continue
            seen_tex.add(tex_key)
            results.append(
                materialize_contract(
                    item,
                    synthesis,
                    run_dir=cycles_dir / f"cycle-{cycle:03d}",
                    compile_pdf=False,
                    compile_timeout_seconds=args.compile_timeout_seconds,
                    compile_existing_pdf=False,
                )
            )
        changed_count = sum(1 for item in results if item.get("changed") or item.get("bibliography_changed"))
        cycle_payload = {
            "cycle": cycle,
            "metrics": {
                "average_ems": synthesis["average_ems"],
                "average_editorial_distance": synthesis["average_editorial_distance"],
                "total_pending_markers": synthesis["total_pending_markers"],
                "gap_frequency": synthesis["gap_frequency"],
            },
            "changed_count": changed_count,
            "results": results,
        }
        history.append(cycle_payload)
        (cycles_dir / f"cycle-{cycle:03d}.json").write_text(json.dumps(cycle_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        if previous_signature == signature and changed_count == 0:
            break
        previous_signature = signature
    summary = {"requested_cycles": max_cycles, "executed_cycles": len(history), "history": history}
    (run_dir / "feedback-loop-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def write_markdown_report(run_dir: Path, payload: dict) -> Path:
    report = FEEDBACK_ROOT / "ciclo-a-primer-refuerzo.md"
    FEEDBACK_ROOT.mkdir(parents=True, exist_ok=True)

    lines = [
        "# Ciclo A - Primer refuerzo editorial",
        "",
        f"Fecha: {payload['created_at']}",
        "",
        "## Gold standard inicial",
        "",
        f"EMS promedio: {payload['gold_standard']['average_ems']}",
        f"Citas promedio: {payload['gold_standard']['average_citations']}",
        f"Entradas bibliográficas promedio: {payload['gold_standard']['average_bibliography_entries']}",
        f"Tipos de producto observados: {', '.join(payload['gold_standard']['observed_product_types']) or 'sin clasificar'}",
        "",
        "Marcadores requeridos:",
        "",
    ]
    for marker in payload["gold_standard"]["required_markers"]:
        lines.append(f"- {marker}")

    lines.extend(["", "## Diagnóstico de objetivos", ""])
    for item in payload["targets"]:
        metrics = item["metrics"]
        contract = item["contract"]
        lines.extend([
            f"### {metrics['subject_path']}",
            "",
            f"- Actividad: `{metrics['activity_file'] or 'no encontrada'}`",
            f"- EMS: {metrics['ems']} ({metrics['maturity_band']})",
            f"- Distancia editorial: {contract['editorial_distance']}",
            f"- Prioridad: {contract['priority']}",
            f"- Citas: {metrics['citations']}",
            f"- Bibliografía: {metrics['bibliography_entries']} entradas",
            f"- Pendientes: {metrics['pending_markers']}",
            f"- Productos detectados: {', '.join(metrics['product_types']) if metrics['product_types'] else 'ninguno'}",
            f"- Brechas: {', '.join(metrics['gaps']) if metrics['gaps'] else 'sin brechas críticas'}",
            f"- Contrato: `{item['contract_path']}`",
            f"- Memoria nodal: `{item['node_memory_path']}`",
            "",
            "Operaciones de refuerzo:",
            "",
        ])
        for recommendation in item["recommendations"]:
            lines.append(f"- {recommendation}")
        lines.append("")

    lines.extend([
        "## Artefactos",
        "",
        f"- Memoria JSON: `{run_dir.relative_to(REPO_ROOT).as_posix()}/ciclo-a-memory.json`",
        f"- Reporte JSON: `{run_dir.relative_to(REPO_ROOT).as_posix()}/ciclo-a-report.json`",
        f"- Contratos: `{run_dir.relative_to(REPO_ROOT).as_posix()}/contracts/`",
        "- Memoria interinstitucional: `retroalimentacion-editorial/aulatex/editorial-gold-standard-ciclo-a.json`",
    ])
    report.write_text("\n".join(lines), encoding="utf-8")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ejecuta el Ciclo A de aprendizaje editorial incremental.")
    parser.add_argument("--activity", type=int, default=1, help="Número de actividad a evaluar.")
    parser.add_argument("--master", action="append", default=[], help="Materia maestra relativa al repo. Puede repetirse.")
    parser.add_argument("--target", action="append", default=[], help="Materia objetivo relativa al repo. Puede repetirse.")
    parser.add_argument("--from-proposals", default="", help="Ruta a proposals.json para cargar nodos masivos.")
    parser.add_argument("--include-level", action="append", default=[], help="Nivel de proposals.json a incluir. Por defecto: materia y actividad.")
    parser.add_argument("--second-pass", action="store_true", help="Sintetiza aprendizaje global y genera contratos propagados.")
    parser.add_argument("--apply-materialization", action="store_true", help="Aplica modificaciones TEX seguras basadas en contratos propagados.")
    parser.add_argument("--compile-pdf", action="store_true", help="Compila PDF después de modificar cada TEX.")
    parser.add_argument("--compile-existing-pdf", action="store_true", help="Compila también TEX ya materializados que no tengan PDF final.")
    parser.add_argument("--compile-timeout-seconds", type=int, default=180, help="Timeout por compilación PDF individual.")
    parser.add_argument("--feedback-cycles", type=int, default=0, help="Ejecuta N ciclos de retroalimentación TEX sin compilar PDF.")
    parser.add_argument("--max-apply", type=int, default=0, help="Máximo de TEX únicos a modificar. 0 = sin límite explícito.")
    parser.add_argument("--priority", action="append", default=[], choices=("alta", "media", "baja"), help="Prioridades a materializar. Por defecto: alta y media.")
    parser.add_argument("--confirm-massive-apply", action="store_true", help="Permite aplicar más de 25 TEX en una corrida.")
    parser.add_argument("--no-node-memory", action="store_true", help="No escribir memoria .memoria-aulatex por materia objetivo.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = TEMP_ROOT / run_id
    contracts_dir = run_dir / "contracts"
    propagated_contracts_dir = run_dir / "propagated-contracts"
    contracts_dir.mkdir(parents=True, exist_ok=True)
    propagated_contracts_dir.mkdir(parents=True, exist_ok=True)

    master_subjects = args.master or DEFAULT_MASTER_SUBJECTS
    if args.from_proposals:
        include_levels = set(args.include_level or ["interinstitucional", "institucion", "carrera", "materia", "actividad"])
        target_subjects = load_targets_from_proposals(REPO_ROOT / args.from_proposals, include_levels)
    else:
        target_subjects = args.target or DEFAULT_TARGET_SUBJECTS

    feedback_summary: dict = {}
    if args.feedback_cycles > 0:
        feedback_summary = run_feedback_cycles(
            args=args,
            run_dir=run_dir,
            master_subjects=master_subjects,
            target_subjects=target_subjects,
        )

    master_metrics = [inspect_subject(subject, activity=args.activity) for subject in master_subjects]
    target_metrics = [inspect_subject(subject, activity=args.activity) for subject in target_subjects]
    gold_standard = build_gold_standard(master_metrics)

    targets = []
    for index, metric in enumerate(target_metrics, start=1):
        recommendations = build_recommendations(metric, gold_standard)
        contract = build_contract(metric, gold_standard, recommendations, run_id=run_id)
        contract_path = contracts_dir / f"{index:05d}-{safe_slug(metric.subject_path)}.contract.json"
        contract_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
        node_memory_path = ""
        if not args.no_node_memory and (REPO_ROOT / metric.subject_path).exists():
            node_memory_path = persist_node_memory(metric.subject_path, contract).relative_to(REPO_ROOT).as_posix()
        targets.append(
            {
                "metrics": asdict(metric),
                "recommendations": recommendations,
                "contract": contract,
                "contract_path": contract_path.relative_to(REPO_ROOT).as_posix(),
                "node_memory_path": node_memory_path,
            }
        )

    synthesis = synthesize_learning(targets, gold_standard)
    propagated_paths: list[str] = []
    if args.second_pass or args.apply_materialization:
        for index, item in enumerate(targets, start=1):
            propagated = enrich_contract_with_learning(item["contract"], synthesis)
            item["contract"] = propagated
            path = propagated_contracts_dir / f"{index:05d}-{safe_slug(item['metrics']['subject_path'])}.propagated.contract.json"
            path.write_text(json.dumps(propagated, ensure_ascii=False, indent=2), encoding="utf-8")
            item["propagated_contract_path"] = path.relative_to(REPO_ROOT).as_posix()
            propagated_paths.append(item["propagated_contract_path"])
            if not args.no_node_memory and (REPO_ROOT / item["metrics"]["subject_path"]).exists():
                persist_node_memory(item["metrics"]["subject_path"], propagated)
        synthesis_report_path = write_synthesis_markdown(run_dir, synthesis)
    else:
        synthesis_report_path = Path("")

    materialization_results: list[dict] = []
    if args.apply_materialization:
        allowed_priorities = set(args.priority or ["alta", "media"])
        apply_candidates = [item for item in targets if item["contract"].get("priority") in allowed_priorities]
        if args.max_apply > 0:
            apply_candidates = apply_candidates[: args.max_apply]
        elif len(apply_candidates) > 25 and not args.confirm_massive_apply:
            raise SystemExit(
                f"Aplicación masiva bloqueada: {len(apply_candidates)} candidatos. Usa --max-apply N o --confirm-massive-apply."
            )
        seen_tex: set[str] = set()
        materialization_results_path = run_dir / "ciclo-a-materialization-results.json"
        for item in apply_candidates:
            metrics = item["metrics"]
            tex_key = f"{metrics.get('subject_path', '')}/{metrics.get('activity_file', '')}"
            if tex_key in seen_tex:
                continue
            seen_tex.add(tex_key)
            materialization_results.append(
                materialize_contract(
                    item,
                    synthesis,
                    run_dir=run_dir,
                    compile_pdf=args.compile_pdf,
                    compile_timeout_seconds=args.compile_timeout_seconds,
                    compile_existing_pdf=args.compile_existing_pdf,
                )
            )
            materialization_results_path.write_text(
                json.dumps(materialization_results, ensure_ascii=False, indent=2), encoding="utf-8"
            )

    payload = {
        "schema": "aulatex.ciclo-a.v3.massive" if args.from_proposals else "aulatex.ciclo-a.v3",
        "run_id": run_id,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "activity": args.activity,
        "from_proposals": args.from_proposals,
        "target_count": len(target_subjects),
        "masters": [asdict(metric) for metric in master_metrics],
        "gold_standard": gold_standard,
        "learning_synthesis": synthesis,
        "feedback_loop": feedback_summary,
        "materialization": {
            "enabled": bool(args.apply_materialization),
            "compile_pdf": bool(args.compile_pdf),
            "changed_count": sum(1 for item in materialization_results if item.get("changed")),
            "compiled_count": sum(1 for item in materialization_results if item.get("compiled")),
            "results_path": (run_dir / "ciclo-a-materialization-results.json").relative_to(REPO_ROOT).as_posix() if materialization_results else "",
        },
        "targets": targets,
    }

    memory_payload = {
        "schema": "aulatex.editorial-memory.incremental.v3.massive" if args.from_proposals else "aulatex.editorial-memory.incremental.v3",
        "node": "interinstitucional/editorial-gold-standard/ciclo-a",
        "run_id": run_id,
        "gold_standard": gold_standard,
        "learning_synthesis": synthesis,
        "feedback_loop": feedback_summary,
        "materialization": payload["materialization"],
        "learned_from": [asdict(metric) for metric in master_metrics],
        "applies_to": target_subjects,
        "reinforcement_targets": targets,
    }

    (run_dir / "ciclo-a-report.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "ciclo-a-memory.json").write_text(json.dumps(memory_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    (run_dir / "ciclo-a-learning-synthesis.json").write_text(json.dumps(synthesis, ensure_ascii=False, indent=2), encoding="utf-8")
    interinstitutional_memory = FEEDBACK_ROOT / "editorial-gold-standard-ciclo-a.json"
    interinstitutional_memory.write_text(json.dumps(memory_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    report_path = write_markdown_report(run_dir, payload)

    print(json.dumps({
        "ok": True,
        "run_id": run_id,
        "run_dir": str(run_dir),
        "markdown_report": str(report_path),
        "synthesis_report": str(synthesis_report_path) if synthesis_report_path else "",
        "interinstitutional_memory": str(interinstitutional_memory),
        "gold_average_ems": gold_standard["average_ems"],
        "target_count": len(targets),
        "average_ems": synthesis["average_ems"],
        "average_editorial_distance": synthesis["average_editorial_distance"],
        "total_pending_markers": synthesis["total_pending_markers"],
        "top_gaps": list(synthesis["gap_frequency"].items())[:8],
        "feedback_cycles_requested": feedback_summary.get("requested_cycles", 0),
        "feedback_cycles_executed": feedback_summary.get("executed_cycles", 0),
        "propagated_contract_count": len(propagated_paths),
        "materialization_changed_count": sum(1 for item in materialization_results if item.get("changed")),
        "materialization_compiled_count": sum(1 for item in materialization_results if item.get("compiled")),
        "materialization_results": str(run_dir / "ciclo-a-materialization-results.json") if materialization_results else "",
        "sample_targets": [
            {
                "subject": item["metrics"]["subject_path"],
                "ems": item["metrics"]["ems"],
                "distance": item["contract"]["editorial_distance"],
                "priority": item["contract"]["priority"],
                "band": item["metrics"]["maturity_band"],
                "contract": item["contract_path"],
                "propagated_contract": item.get("propagated_contract_path", ""),
                "node_memory": item["node_memory_path"],
                "gaps": item["metrics"]["gaps"],
            }
            for item in targets[:10]
        ],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
