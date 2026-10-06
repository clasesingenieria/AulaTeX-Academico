import hashlib
import json
from pathlib import Path

import pymupdf

ASSETS = Path(__file__).resolve().parent
COURSE = ASSETS.parents[1]
ROOT = COURSE.parents[2]
STEM = "reporte-plan-de-negocios-Actividad-12-Recursos-Humanos"


def main():
    reference = ROOT / "ITESCA/maestria-en-gestion-administrativa/fundamentos-de-gestion-administrativa-mga/assets-fundamentos-de-gestion-administrativa/actividad-10/portada-oficial.png"
    image = ASSETS / "portada-oficial.png"
    image.write_bytes(reference.read_bytes())
    source = COURSE / (STEM + ".pdf")
    destination = COURSE / (STEM + "-Portada-Oficial.pdf")
    font = Path("C:/Windows/Fonts/arial.ttf")
    bold = Path("C:/Windows/Fonts/arialbd.ttf")
    with pymupdf.open(source) as original, pymupdf.open() as output:
        page = output.new_page(width=612, height=792)
        page.insert_image(page.rect, filename=str(image))
        page.insert_font(fontname="Arial", fontfile=str(font))
        page.insert_font(fontname="ArialBold", fontfile=str(bold))
        block = pymupdf.Rect(56.7, 294.8, 544.3, 454)
        page.draw_rect(block, fill=(1, 1, 1), color=None, fill_opacity=0.96)
        metadata = "Maestría en Gestión Administrativa\nAsignatura: Plan de Negocios\nCurso: GGPN01 - Unidad 2\nEstudiante: Martín Jonathan de la Cruz Muñoz\nMatrícula: 26130503\nDocente: Celia Velázquez Reyna\nFecha: 5 de octubre de 2026\nLugar: Monterrey, Nuevo León"
        assert page.insert_textbox(block + (12, 12, -12, -12), metadata, fontname="Arial", fontsize=11, lineheight=1.35) >= 0
        title_box = pymupdf.Rect(263.6, 552.7, 582, 696)
        title = "AM Taller Autocentro\nAdministración de recursos humanos\nPuestos y funciones\n\nActividad 12 - Plan de Negocios\nPropuesta de organización del personal"
        assert page.insert_textbox(title_box, title, fontname="ArialBold", fontsize=14, lineheight=1.25, color=(1, 1, 1)) >= 0
        output.insert_pdf(original, from_page=1)
        assert len(output) == len(original)
        assert all(output[index].get_text() == original[index].get_text() for index in range(1, len(original)))
        output.set_metadata({"title": "AM Taller Autocentro: puestos y funciones", "author": "Martín Jonathan de la Cruz Muñoz", "subject": "Actividad 12 - Plan de Negocios"})
        output.subset_fonts()
        output.save(destination, garbage=4, deflate=True)
        output[0].get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(ASSETS / "portada-oficial-verificada.png")
    with pymupdf.open(destination) as document:
        text = " ".join(document[0].get_text().split())
        assert all(value in text for value in ["Plan de Negocios", "26130503", "Celia Velázquez Reyna", "Actividad 12"])
        assert "Fundamentos" not in text
        receipt = {
            "reference": reference.relative_to(ROOT).as_posix(),
            "reference_sha256": hashlib.sha256(reference.read_bytes()).hexdigest(),
            "local_image_sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
            "same_cover_resource": reference.read_bytes() == image.read_bytes(),
            "body_unchanged": True,
            "pages": len(document),
            "submission_pdf": destination.relative_to(ROOT).as_posix(),
            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
        }
    (ASSETS / "verificacion-portada.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()