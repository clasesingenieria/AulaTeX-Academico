"""Control de compilación y vista de revisión de la versión institucional LaTeX."""

import hashlib
import json
from pathlib import Path
import re
import subprocess

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[3]
COURSE = ROOT.parent
STEM = "reporte-seminario-i-Actividad-6"


def main():
    tex = COURSE / f"{STEM}.tex"
    digest = hashlib.sha256(tex.relative_to(REPO).as_posix().encode()).hexdigest()[:16]
    build = REPO / ".build" / "latex" / f"{STEM}-{digest}"
    log = (build / f"{STEM}.log").read_text(errors="replace")
    issues = re.findall(r"^.*(?:Overfull|LaTeX Warning|Package .* Warning|LaTeX Error).*$", log, re.M)
    assert not issues, issues
    assert "Output written on" in log
    contents = (build / f"{STEM}.toc").read_text()
    entries = re.findall(r"\\contentsline \{(section|subsection|subsubsection)\}", contents)
    assert len(entries) == 53, len(entries)
    source = (ROOT / "contenido-actividad-6.tex").read_text()
    assert source.count(r"\begin{table}[H]") == 2
    assert source.count(r"\begin{figure}[H]") == 2
    assert source.count(r"\item ") == 5
    exported = json.loads((ROOT / "validacion" / "exportacion-latex.json").read_text())
    word = COURSE / "entregas" / "Tarea6_DeLaCruzMunoz.docx"
    assert hashlib.sha256(word.read_bytes()).hexdigest() == exported["word_sha256_sin_cambios"]
    pdf = COURSE / f"{STEM}.pdf"
    text = subprocess.check_output(["pdftotext", "-layout", str(pdf), "-"], text=True)
    pages = text.split("\f")
    if not pages[-1].strip():
        pages.pop()
    assert all(page.strip() for page in pages)
    selected = [1, 3]
    for i, page in enumerate(pages, 1):
        if i > 4 and any(marker in page for marker in ["Tabla 1", "Tabla 2", "Figura 1", "Figura 2", "Referencias bibliográficas"]):
            selected.append(i)
    selected = sorted(set(selected))
    destination = ROOT / "validacion"
    for page in selected:
        subprocess.run(["pdftoppm", "-f", str(page), "-l", str(page), "-scale-to", "1200",
                        "-png", str(pdf), str(destination / "latex-pagina")],
                       check=True, capture_output=True)
    rows = (len(selected) + 2) // 3
    sheet = Image.new("RGB", (960, rows * 440), "#dddddd")
    draw = ImageDraw.Draw(sheet)
    for i, page in enumerate(selected):
        with Image.open(destination / f"latex-pagina-{page:02d}.png") as image:
            image.thumbnail((305, 400))
            x, y = (i % 3) * 320 + 7, (i // 3) * 440 + 25
            sheet.paste(image, (x, y))
            draw.text((x, y - 18), f"Página física {page}", fill="black")
    sheet.save(destination / "latex-vista-general.png")
    report = {"resultado": "Correcto", "paginas_pdf": len(pages),
              "entradas_indice_niveles_1_a_3": len(entries),
              "tablas": 2, "figuras": 2, "referencias": 5,
              "advertencias_compilacion": issues,
              "plantilla": "base/Plantilla-Informe/template.tex (sin modificar)",
              "word_original_sin_cambios": True,
              "sha256_pdf": hashlib.sha256(pdf.read_bytes()).hexdigest(),
              "paginas_renderizadas": selected}
    (destination / "verificacion-latex.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()