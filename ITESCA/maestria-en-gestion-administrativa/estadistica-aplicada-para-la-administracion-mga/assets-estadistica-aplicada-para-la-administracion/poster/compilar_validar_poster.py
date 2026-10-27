"""Compilar y validar exclusivamente la alternativa local de póster ITESCA."""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import pymupdf

HERE = Path(__file__).resolve().parent
SUBJECT = HERE.parents[1]
ROOT = SUBJECT.parents[2]
STEM = "muestra-infografia-muestreo-alternativa"
SOURCE = HERE / (STEM + ".tex")
PDF = HERE / (STEM + ".pdf")
BUILD = ROOT / ".build/latex/estadistica-poster-local"
QA = ROOT / ".build/qa-estadistica-poster"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protected_files():
    baseline = json.loads((HERE / "conservacion-antes.json").read_text(encoding="utf-8"))
    changed = [name for name, value in baseline.items() if digest(ROOT / name) != value]
    assert not changed, f"Archivos protegidos modificados: {changed}"
    return len(baseline)


def build():
    protected_files()
    environment = os.environ.copy()
    environment["PATH"] = "C:/texlive/2026/bin/windows;C:/Strawberry/perl/bin;" + environment["PATH"]
    environment["TEXINPUTS"] = f".;{ROOT.as_posix()}/aulaTEX/base/Plantilla-Informe//;"
    environment["BSTINPUTS"] = environment["TEXINPUTS"]
    command = ["C:/texlive/2026/bin/windows/latexmk.exe", "-norc", "-xelatex", "-halt-on-error",
               "-interaction=nonstopmode", f"-outdir={BUILD.relative_to(ROOT).as_posix()}",
               SOURCE.relative_to(ROOT).as_posix()]
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, timeout=300)
    if result.returncode:
        raise RuntimeError(result.stdout.decode("utf-8", errors="replace")[-6000:])
    log = BUILD / (STEM + ".log")
    if re.search(r"Citation .*undefined|There were undefined", log.read_text(encoding="utf-8", errors="replace")):
        result = subprocess.run(command[:2] + ["-g"] + command[2:], cwd=ROOT, env=environment, capture_output=True, timeout=300)
        if result.returncode:
            raise RuntimeError(result.stdout.decode("utf-8", errors="replace")[-6000:])
    temporary = BUILD / (STEM + ".pdf")
    assert temporary.exists()
    os.replace(temporary, PDF)
    protected_files()


def validate(visual_reviewed=False):
    count = protected_files()
    assert PDF.stat().st_mtime >= max(SOURCE.stat().st_mtime, (HERE / "adaptador-poster-estadistica-itesca.tex").stat().st_mtime)
    log = (BUILD / (STEM + ".log")).read_text(encoding="utf-8", errors="replace")
    assert not re.search(r"Overfull|Underfull|Missing character|Citation .*undefined|There were undefined|^!", log, re.MULTILINE)
    recorder = (BUILD / (STEM + ".fls")).read_text(encoding="utf-8", errors="replace").replace("\\", "/")
    assert "aulaTEX/base/Plantilla-Informe/template_poster.tex" in recorder
    assert "tex/latex/beamerposter/beamerposter.sty" in recorder
    with pymupdf.open(PDF) as document:
        assert len(document) == 1
        page = document[0]
        assert abs(page.rect.width - 297 * 72 / 25.4) < 1
        assert abs(page.rect.height - 420 * 72 / 25.4) < 1
        text = page.get_text()
        for required in ("Introducción", "Conclusiones", "Referencias", "Población", "Marco muestral", "Muestra",
                         "385", "482", "26130503", "Martín Jonathan de la Cruz Muñoz",
                         "Yoana Elizeth Tauitmes Delgado", "25 de octubre de 2026", "VARIANTE LOCAL"):
            assert required in text, required
        for forbidden in ("Pablo Pizarro", "John Doe", "Universidad de Chile", "Título del póster", "[?]"):
            assert forbidden not in text, forbidden
        assert len(page.get_images()) >= 1
        drawings = page.get_drawings()
        assert len(drawings) >= 8
        panels = [item["rect"] for item in drawings if item.get("fill") and len(item["fill"]) == 3 and abs(item["fill"][0] - 244/255) < 0.01 and item["rect"].width > page.rect.width * 0.8]
        assert panels
        reference_panel = max(panels, key=lambda item: item.y0)
        links = {item.get("uri") for item in page.get_links() if item.get("uri")}
        expected_urls = {"https://doi.org/10.1038/s41586-021-04198-4", "https://openstax.org/details/books/introductory-business-statistics-2e", "https://doi.org/10.18434/M32189"}
        assert expected_urls <= links
        flattened_text = re.sub(r"\s+", "", text)
        assert all(url in flattened_text for url in expected_urls)
        fonts = set()
        for block in page.get_text("dict")["blocks"]:
            for line in block.get("lines", []):
                for span in line["spans"]:
                    if not span["text"].strip():
                        continue
                    bounds = pymupdf.Rect(span["bbox"])
                    assert bounds.x0 >= 0 and bounds.y0 >= 0 and bounds.x1 <= page.rect.width + 0.2 and bounds.y1 <= page.rect.height + 0.2, span["text"]
                    if reference_panel.y0 <= bounds.y0 <= reference_panel.y1:
                        # El primer renglón APA comienza al ras del panel; comprobar
                        # pertenencia real, con tolerancia de redondeo PDF de 0.2 pt.
                        assert bounds.x0 >= reference_panel.x0 - 0.2 and bounds.x1 <= reference_panel.x1 + 0.2, ("Referencia fuera de su panel", span["text"], list(bounds), list(reference_panel))
                    fonts.add(span["font"])
        assert any("Arial" in font for font in fonts)
        QA.mkdir(parents=True, exist_ok=True)
        page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(QA / "muestra-poster.png")
    assert math.ceil(1.96**2 * 0.5 * 0.5 / 0.05**2) == 385
    assert math.ceil(385 / 0.8) == 482
    source_text = SOURCE.read_text(encoding="utf-8")
    for key in ("holmesBusiness2023", "bradley2021", "nistHandbook"):
        assert re.search(r"\\bibitem\[[^\]]+\]\{" + key + r"\}", source_text)
        assert "{" + key + "," in (SUBJECT / "referencias-estadistica-verificadas.bib").read_text(encoding="utf-8")
    baseline = json.loads((HERE / "conservacion-antes.json").read_text(encoding="utf-8"))
    preserved_deliveries = [{"path": name, "sha256": value} for name, value in baseline.items() if "/entregas-estadistica-aplicada-para-la-administracion/Actividad-" in name]
    preserved_reports = [{"path": path.relative_to(ROOT).as_posix(), "sha256": digest(path)} for number in range(1, 6) if (path := SUBJECT / f"reporte-estadistica-aplicada-para-la-administracion-Actividad-{number}.pdf").exists()]
    assert len(preserved_deliveries) == 4 and len(preserved_reports) == 5
    report = {"validated_at_utc": datetime.now(timezone.utc).isoformat(), "role": "alternativa_local_sin_envio",
              "pdf": PDF.relative_to(ROOT).as_posix(), "sha256": digest(PDF), "pages": 1,
              "size_mm": [297, 420], "core": "aulaTEX/base/Plantilla-Informe/template_poster.tex",
              "core_loaded_verified": True, "protected_files_verified": count,
              "delivery_and_root_reports_unchanged": True, "preserved_deliveries": preserved_deliveries, "preserved_reports": preserved_reports, "reference_panel_bounds_passed": True, "reference_full_urls_verified": True, "conceptual_sources": ["holmesBusiness2023", "bradley2021", "nistHandbook"],
              "numerical_checks_passed": True, "glyph_bounds_passed": True, "body_fonts": sorted(fonts),
              "visual_review_completed": visual_reviewed, "render": (QA / "muestra-poster.png").relative_to(ROOT).as_posix(),
              "font_warnings": re.findall(r"LaTeX Font Warning:[^\n]+", log)}
    (HERE / "validacion-poster.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--visual-reviewed", action="store_true", help="Usar solo después de inspeccionar el render actual")
    arguments = parser.parse_args()
    if arguments.build:
        build()
    validate(arguments.visual_reviewed)
