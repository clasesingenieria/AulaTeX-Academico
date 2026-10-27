"""Verifica integridad del reporte contra los veinte reactivos del aula."""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pymupdf

HERE = Path(__file__).resolve().parent
SUBJECT = HERE.parents[2]
REPORT = SUBJECT / "reporte-estadistica-aplicada-para-la-administracion-Actividad-5.pdf"
TEX = REPORT.with_suffix(".tex")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFC", text).lower()
    text = re.sub(r"(\w)-\s*\n(\w)", r"\1\2", text)
    return re.sub(r"[^\w]+", "", text)


def main() -> None:
    source = json.loads((HERE / "respuestas-validadas.json").read_text(encoding="utf-8-sig"))
    enriched = json.loads((HERE / "respuestas-soporte-editorial.json").read_text(encoding="utf-8"))
    document = pymupdf.open(REPORT)
    all_text = "\n".join(page.get_text() for page in document)
    normalized = normalize(all_text)
    questions = source["preguntas"]
    missing_questions = []
    missing_answers = []
    for q in questions:
        question = q["pregunta"]
        if q["numero"] == 7:
            found = normalize("En la fórmula n") in normalized and normalize("el valor Z representa") in normalized
        else:
            found = normalize(question) in normalized
        if not found:
            missing_questions.append(q["numero"])
        if normalize(q["respuesta"]) not in normalized:
            missing_answers.append(q["numero"])
    bibliography = (HERE / "cuestionario-fuentes-verificadas.bib").read_text(encoding="utf-8")
    keys = set(re.findall(r"@\w+\s*\{\s*([^,]+),", bibliography))
    used = {key for q in enriched["preguntas"] for key in q["fuentes"]}
    pages = []
    outside = []
    for index, page in enumerate(document):
        pages.append({"page": index + 1, "width": round(page.rect.width, 2), "height": round(page.rect.height, 2),
                      "rotation": page.rotation, "text_length": len(page.get_text())})
        bounds = page.mediabox
        for block in page.get_text("blocks"):
            if block[6] == 0 and (block[0] < -1 or block[1] < -1 or block[2] > bounds.width + 1 or block[3] > bounds.height + 1):
                outside.append({"page": index + 1, "bbox": list(block[:4])})
    checks = {
        "questions_20_in_order": [q["numero"] for q in questions] == list(range(1, 21)),
        "all_questions_visible": not missing_questions,
        "all_selected_answers_visible": not missing_answers,
        "all_answers_from_options": all(q["respuesta"] in q["opciones"] for q in questions),
        "every_justification_has_sources": all(q.get("justificacion") and q.get("fuentes") for q in enriched["preguntas"]),
        "bibliography_support": used <= keys,
        "fresh_pdf": REPORT.stat().st_mtime >= TEX.stat().st_mtime,
        "landscape_table_present": any(p["width"] > p["height"] for p in pages),
        "official_cover_identity": all(word in document[0].get_text() for word in ("Muestreo", "representatividad", "Actividad 5", "26130503")),
        "no_undefined_citations": "[?]" not in all_text and "(??)" not in all_text,
        "no_operational_ids": not any(term in all_text for term in ("Módulo Moodle", "mod/quiz/", "Vencimiento publicado")),
        "no_outside_text": not outside,
    }
    result = {"checks": checks, "passed": all(checks.values()), "pages": pages,
              "missing_questions": missing_questions, "missing_answers": missing_answers,
              "outside_blocks": outside, "pdf_sha256": hashlib.sha256(REPORT.read_bytes()).hexdigest(),
              "source_snapshot_sha256": enriched["source_sha256"],
              "visual_review": "pendiente; no se presume a partir de la extracción"}
    (HERE / "validacion-reporte.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (HERE / "reporte-texto-extraido.txt").write_text(all_text, encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
