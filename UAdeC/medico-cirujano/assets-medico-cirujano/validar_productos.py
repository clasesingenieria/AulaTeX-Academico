from pathlib import Path
import json
import re
import unicodedata
import pymupdf
from organizar_productos import CAREER, ROOT, digest, existing_questions


def main():
    model = json.loads(Path(__file__).with_name("productos.json").read_text(encoding="utf-8"))
    results = []
    for area in model["areas"]:
        slug = area["slug"]
        subject = CAREER / slug
        notes = subject / f"referencias-{slug}/notas-{slug}"
        source = subject / f"reporte-{slug}.tex"
        pdf_path = source.with_suffix(".pdf")
        content = source.read_text(encoding="utf-8")
        questions = area.get("preguntas") or existing_questions(content)
        bank = notes / "actividad-02-cuestionario/banco-reactivos.json"
        bank.write_text(json.dumps({"origen": "practica local", "preguntas": questions, "respondido_por_aspirante": False}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        solved = notes / "actividad-02-cuestionario/cuestionario-resuelto.md"
        solved.write_text("# Cuestionario resuelto - " + area["titulo"] + "\n\nPráctica local, no examen oficial ni calificación del aspirante. Las fórmulas y comandos de los bancos científicos conservan su notación TeX; el PDF del reporte es la versión de lectura.\n\n" + "\n\n".join(
            f"## Pregunta {number}\n\n{question}\n\n" + "\n".join(f"{chr(65 + index)}. {option}" for index, option in enumerate(options)) + f"\n\n**Respuesta propuesta: {chr(65 + answer)}.** {reason}"
            for number, (question, options, answer, reason) in enumerate(questions, 1)
        ) + "\n", encoding="utf-8")
        inventory = json.loads((subject / f"referencias-{slug}/inventario-libros.json").read_text(encoding="utf-8"))
        checks = {
            "plantilla_comun": "assets-medico-cirujano/plantilla/reporte-uadec.tex" in content,
            "sintesis_y_representacion": all(label in content for label in ("Actividad 1", "tikzpicture", "longtable")),
            "referencias_presentes": "Fuentes de apoyo" in content and all(entry["url"] in content for entry in area["fuentes"]),
            "sin_marcadores_incompletos": not re.search(r"Agrega \d+|(?-i:\bTODO\b)(?=\s*[:\[]|\s*$)|completar aquí", content, re.I | re.M),
            "reactivos_y_claves": len(questions) >= 10 and all(len(options) == 4 and answer in range(4) and bool(reason.strip()) for _, options, answer, reason in questions),
            "libros_integridad": all(digest(subject / entry["archivo"]) == entry["sha256"] for entry in inventory),
        }
        broken = []
        for markdown in [subject / "README.md", subject / "guia-de-estudio.md", *list((subject / f"planeaciones-{slug}").glob("*.md"))]:
            for link in re.findall(r"\]\(([^)]+)\)", markdown.read_text(encoding="utf-8")):
                if not link.startswith(("http", "#")) and not (markdown.parent / link.split("#")[0]).exists():
                    broken.append(link)
        checks["enlaces_locales"] = not broken
        log = ROOT / f".build/latex/aux-files/{source.stem}.log"
        log_text = log.read_text(encoding="utf-8", errors="replace")
        checks["compilacion_limpia"] = not re.search(r"^!|Overfull|Missing \$|undefined citations|Fatal error", log_text, re.M)
        with pymupdf.open(pdf_path) as pdf:
            text = unicodedata.normalize("NFKC", " ".join(page.get_text() for page in pdf))
            checks["pdf_productos_visibles"] = all(label in text for label in ("Actividad 1", "Actividad 2", "Conclusiones", "Fuentes de apoyo"))
            checks["pdf_no_vacio"] = all(len(page.get_text().strip()) > 20 for page in pdf)
            pages = len(pdf)
            render = CAREER / "assets-medico-cirujano/revision-visual"
            render.mkdir(parents=True, exist_ok=True)
            pdf[0].get_pixmap(matrix=pymupdf.Matrix(0.85, 0.85)).save(render / f"{slug}-portada.png")
            pdf[min(2, len(pdf) - 1)].get_pixmap(matrix=pymupdf.Matrix(0.85, 0.85)).save(render / f"{slug}-contenido.png")
        result = {"area": slug, "checks": checks, "passed": all(checks.values()), "pages": pages, "reactivos": len(questions), "sha256_pdf": digest(pdf_path), "sha256_tex": digest(source), "revision_visual": "capturas generadas; revisión humana independiente", "revision_cientifica_integral": False, "alineacion_oficial_confirmada": False, "submitted": False}
        (notes / "materiales-generales/validacion-productos.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        results.append(result)
    (CAREER / "validacion-productos.json").write_text(json.dumps(results, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"areas": len(results), "reactivos": sum(item["reactivos"] for item in results), "passed": all(item["passed"] for item in results), "fallos": [{"area": item["area"], "checks": [key for key, value in item["checks"].items() if not value]} for item in results if not item["passed"]]}, ensure_ascii=True))
    if not all(item["passed"] for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()