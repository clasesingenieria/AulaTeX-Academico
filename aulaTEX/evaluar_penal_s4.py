"""Evaluación reproducible S4 sin modificar contratos ni criterios de AulaTeX."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

import pymupdf

from aulatex.activity_observer import ActivityObserver, ActivityObservationRequest
from aulatex.activity_optimizer import ActivityOptimizer
from aulatex.workspace import AulaTeXWorkspace, CommandResult

ROOT = Path(__file__).resolve().parents[1]
SUBJECT = ROOT / "UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde"
NOTES = SUBJECT / "referencias-derecho-penal-especial-mexicano/notas-derecho-penal-especial-mexicano/actividad-04-delitos-de-peligro"
TEX = SUBJECT / "reporte-derecho-penal-especial-mexicano-Actividad-4.tex"
REVIEW = NOTES / "revisiones"


class ScopedCompilationWorkspace(AulaTeXWorkspace):
    """Conserva el compilador y limpieza originales, acotando las rutas de búsqueda.

    Las búsquedas recursivas de todas las instituciones tardan varios minutos en
    Windows y seleccionan paquetes locales de otras materias. Sólo se añade una
    configuración de rutas; no se cambia el resultado ni los checks del observador.
    """

    def compile_tex(self, tex_file: str | Path, clean_mode: str = "safe", timeout_seconds: int = 360) -> CommandResult:
        cfg = ROOT / ".build/latex/penal-s4-scoped.latexmkrc"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        paths = f"{ROOT.as_posix()}/aulaTEX/base/Plantilla-Informe//;{SUBJECT.as_posix()}//;"
        cfg.write_text("$ENV{TEXINPUTS} = '" + paths + "';\n", encoding="utf-8")
        command = ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                   str(ROOT / "aulaTEX/latexmk-build.ps1"), str(self.resolve_target(tex_file)),
                   "-CleanMode", clean_mode, "-r", str(cfg)]
        proc = subprocess.run(command, cwd=ROOT, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=timeout_seconds)
        REVIEW.mkdir(parents=True, exist_ok=True)
        (REVIEW / "compilacion-final.txt").write_text(proc.stdout + "\n" + proc.stderr, encoding="utf-8")
        (REVIEW / "comando-compilacion-final.json").write_text(
            json.dumps({"command": command, "returncode": proc.returncode,
                        "clean_mode": clean_mode, "changes_to_evaluation_contract": False},
                       ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return CommandResult(proc.returncode == 0, proc.returncode, proc.stdout, proc.stderr)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    observation = ActivityObserver(ScopedCompilationWorkspace()).observe(
        ActivityObservationRequest(target=str(SUBJECT), activity_number=4,
                                   output=str(REVIEW / "observador-final"), compile_check=True))
    evaluation = json.loads(observation.evaluation_path.read_text(encoding="utf-8"))
    concepts_path = SUBJECT / "extractor-aulatex/conceptos-derecho-penal-especial-mexicano-actividad-4/conceptos_detectados.json"
    concepts = json.loads(concepts_path.read_text(encoding="utf-8"))
    source = TEX.read_text(encoding="utf-8")
    optimizer = ActivityOptimizer.__new__(ActivityOptimizer)
    breakdown = optimizer._quality_breakdown(source, concepts)
    pdf = TEX.with_suffix(".pdf")
    document = pymupdf.open(pdf)
    decision_lines = []
    decision_page = None
    for i, page in enumerate(document, 1):
        for block in page.get_text("dict")["blocks"]:
            lines = block.get("lines", [])
            if lines and "Considero prioritario" in "".join(span["text"] for span in lines[0]["spans"]):
                decision_page = i
                decision_lines = ["".join(span["text"] for span in line["spans"]) for line in lines]
    pdf_text = "\n".join(page.get_text() for page in document)
    names = document.resolve_names()
    body_start = names["cuerpo-inicio"]["page"] + 1
    body_end = names["cuerpo-fin"]["page"] + 1
    body_pages = body_end - body_start + 1
    summary_pages = [i for i, page in enumerate(document, 1)
                     if any(block[4].strip() == "Resumen" for block in page.get_text("blocks"))]
    contents_pages = [i for i, page in enumerate(document, 1)
                      if any(block[4].strip() == "Tabla de contenido" for block in page.get_text("blocks"))]
    required_quotes = {
        "legalidad_CPEUM_14": ("ley exactamente aplicable al delito de que se trata", "CPEUM-DOF-2026-10-07.txt"),
        "interes_superior_CPEUM_4": ("interés superior de la niñez", "CPEUM-DOF-2026-10-07.txt"),
        "inocencia_CPEUM_20": ("se presuma su inocencia", "CPEUM-DOF-2026-10-07.txt"),
        "jurisprudencia_2006091": ("pruebas de cargo suficientes", "SCJN-2006091-ficha-oficial.txt"),
    }
    quote_checks = {}
    for name, (quote, filename) in required_quotes.items():
        text = (NOTES / "investigacion" / filename).read_text(encoding="utf-8")
        normal = lambda value: re.sub(r"\s+", " ", value).strip().lower()
        quote_checks[name] = normal(quote) in normal(text) and normal(quote) in normal(pdf_text)
    qa = {
        "pages": len(document), "body_pages": body_pages, "max_body_pages": 4,
        "body_start_physical_page": body_start, "body_end_physical_page": body_end,
        "excluded_from_body_limit": ["portada", "resumen", "tabla de contenido", "referencias"],
        "page_limit_passed": body_pages <= 4,
        "summary_physical_pages": summary_pages, "contents_physical_pages": contents_pages,
        "summary_present": bool(summary_pages), "contents_present": bool(contents_pages),
        "decision_page": decision_page, "decision_lines": len(decision_lines),
        "decision_line_limit_passed": 5 <= len(decision_lines) <= 7,
        "decision_text_lines": decision_lines,
        "quotes_match_primary_sources_and_final_pdf": quote_checks,
        "undefined_citation_markers_absent": "??" not in pdf_text,
        "pdf_fresh": pdf.stat().st_mtime >= TEX.stat().st_mtime,
        "pdf_sha256": hashlib.sha256(pdf.read_bytes()).hexdigest(),
        "tex_sha256": hashlib.sha256(TEX.read_bytes()).hexdigest(),
    }
    report = {
        "observer_evaluation": str(observation.evaluation_path.relative_to(ROOT)),
        "observer_score": evaluation["score"], "observer_passed": evaluation["passed"],
        "contract_score": evaluation["contract"]["score"],
        "editorial_quality_score": round(sum(breakdown.values()), 2),
        "editorial_breakdown": breakdown, "extractor_concept_count": len(concepts),
        "pdf_checks": qa,
        "meaning": "Evaluación interna de AulaTeX; no es una calificación oficial de UnADM.",
    }
    path = REVIEW / "evaluacion-integrada-S4.json"
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
