from __future__ import annotations

import hashlib
import json
from pathlib import Path

import fitz

ROOT = Path(__file__).resolve().parents[3]
COURSES = ROOT / "UnADM/licenciatura-en-derecho-unadm"
OUTPUT = Path(__file__).resolve().parent / "revision-visual"


def main() -> None:
    OUTPUT.mkdir(exist_ok=True)
    penal = COURSES / "derecho-penal-especial-mexicano-lde"
    references = penal / "referencias-derecho-penal-especial-mexicano"
    records = []
    for file in references.rglob("*.pdf"):
        text_file = file.with_suffix(".txt")
        with fitz.open(file) as document:
            if not text_file.exists():
                text_file.write_text("\n\f\n".join(page.get_text(sort=True) for page in document), encoding="utf-8")
            records.append({"pdf": file.relative_to(penal).as_posix(), "sha256_pdf": hashlib.sha256(file.read_bytes()).hexdigest(), "paginas": len(document), "txt": text_file.relative_to(penal).as_posix(), "sha256_txt": hashlib.sha256(text_file.read_bytes()).hexdigest(), "metodo": "TXT existente conservado; faltantes con PyMuPDF sort=True, sin OCR", "caracteres": len(text_file.read_text(encoding="utf-8-sig"))})
    target = references / "notas-derecho-penal-especial-mexicano/materiales-generales/registros-organizacion/extracciones-2026-10-11.json"
    target.write_text(json.dumps(records, indent=2, ensure_ascii=False), encoding="utf-8")
    files = [COURSES / "teoria-del-estado-y-constitucion-lde/reporte-teoria-del-estado-y-constitucion-Actividad-2.pdf", penal / "reporte-derecho-penal-especial-mexicano-Actividad-2.pdf"]
    files.extend(COURSES.glob("antecedentes-*/referencias-*/notas-*/materiales-generales/auditorias/semana2-2026-10-11/211993-*.pdf"))
    summaries = []
    for file in files:
        with fitz.open(file) as document:
            text = "\n\f\n".join(page.get_text(sort=True) for page in document)
            (OUTPUT / f"{file.stem}.txt").write_text(text, encoding="utf-8")
            selected = sorted({0, len(document) - 1, *[number for number, page in enumerate(document) if page.rect.width > page.rect.height]})
            for number in selected:
                document[number].get_pixmap(matrix=fitz.Matrix(1.3, 1.3)).save(OUTPUT / f"{file.stem}-p{number + 1}.png")
            summaries.append({"archivo": file.relative_to(ROOT).as_posix(), "paginas": len(document), "sha256": hashlib.sha256(file.read_bytes()).hexdigest(), "paginas_inspeccion": [number + 1 for number in selected]})
    (OUTPUT.parent / "validacion-pdf.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")
    print(json.dumps({"extracciones": len(records), "sin_texto": [item["pdf"] for item in records if item["caracteres"] < 100], "productos": summaries}, ensure_ascii=True))


if __name__ == "__main__":
    main()