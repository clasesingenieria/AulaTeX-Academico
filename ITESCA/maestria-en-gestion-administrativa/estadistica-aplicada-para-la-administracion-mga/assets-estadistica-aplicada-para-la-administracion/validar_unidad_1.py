import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import subprocess
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

import pymupdf

SUBJECT = Path(__file__).resolve().parents[1]
ROOT = SUBJECT.parents[2]
NOTES = SUBJECT / "referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/unidad-1-muestreo"
BASE = "reporte-estadistica-aplicada-para-la-administracion-Actividad-"


@lru_cache(maxsize=1)
def investigation_validator():
    """Resolver el validador dueño de las dos versiones de la Actividad 2."""
    path = Path(__file__).resolve().parent / "investigacion-articulos/compilar_validar_investigacion.py"
    spec = importlib.util.spec_from_file_location("estadistica_investigacion_articulos", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar el validador de investigación: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def investigation_result(data, validator):
    """Mantener el contrato de unidad 1 sin equiparar informe y entrega."""
    complete = next(row for row in data["reports"] if row["version"] == "completo")
    delivery = next(row for row in data["reports"] if row["version"] == "entrega")
    assert complete["pages"] >= 8 and delivery["pages"] == 5
    assert complete["file"] != delivery["file"] and complete["sha256"] != delivery["sha256"]
    return {
        "activity": 2,
        "pdf": (SUBJECT / complete["file"]).relative_to(ROOT).as_posix(),
        "source": validator.SOURCE.relative_to(ROOT).as_posix(),
        "pages": complete["pages"],
        "sha256": complete["sha256"],
        "body_fonts": complete.get("fonts", []),
        "references": data["formal_references"],
        "checks_passed": data["passed"],
        "delivery": delivery["file"],
        "delivery_source": validator.SPECS[1][1].relative_to(ROOT).as_posix(),
        "delivery_content_source": (validator.HERE / "contenido-entrega.tex").relative_to(ROOT).as_posix(),
        "delivery_pages": delivery["pages"],
        "delivery_sha256": delivery["sha256"],
        "delivery_is_root_report": False,
        "dedicated_validator": (validator.HERE / "compilar_validar_investigacion.py").relative_to(ROOT).as_posix(),
        "dedicated_manifest": validator.MANIFEST.relative_to(SUBJECT).as_posix(),
        "versions": data["reports"],
    }


def validate_investigation(promote=False):
    validator = investigation_validator()
    data = validator.validate(promote=promote)
    for label, tex, _, target in validator.SPECS:
        active = validator.SOURCE if label == "completo" else validator.HERE / "contenido-entrega.tex"
        dependencies = [validator.SOURCE, validator.HERE / "formato-fichas.tex",
                        validator.HERE / "referencias.tex", tex, active]
        assert target.stat().st_mtime >= max(path.stat().st_mtime for path in dependencies), (label, "stale_target")
    return investigation_result(data, validator)


def infographic_asset():
    # La revisión del 25/10 autoriza la fusión; la primera lámina sigue en assets.
    return SUBJECT / "assets-estadistica-aplicada-para-la-administracion/poster/infografia-muestreo-fusionada.pdf"


def build(number):
    if number == 2:
        validator = investigation_validator()
        for spec in validator.SPECS:
            validator.compile_one(spec)
        return
    environment = os.environ.copy()
    environment["PATH"] = "C:/texlive/2026/bin/windows;C:/Strawberry/perl/bin;" + environment["PATH"]
    environment["TEXINPUTS"] = f".;{ROOT.as_posix()}/aulaTEX/base/Plantilla-Informe//;"
    environment["BSTINPUTS"] = environment["TEXINPUTS"]
    command = ["C:/texlive/2026/bin/windows/latexmk.exe", "-norc", "-xelatex", "-halt-on-error",
               "-interaction=nonstopmode", f"-outdir=.build/latex/estadistica-act{number}",
               (SUBJECT / f"{BASE}{number}.tex").relative_to(ROOT).as_posix()]
    result = subprocess.run(command, cwd=ROOT, env=environment, capture_output=True, timeout=240)
    # Una compilación previa interrumpida puede quedar marcada como actualizada.
    # Si aún hay citas sin resolver, forzar otra pasada; la validación sigue siendo estricta.
    log_path = ROOT / f".build/latex/estadistica-act{number}" / f"{BASE}{number}.log"
    if result.returncode == 0 and log_path.exists() and re.search(r"Citation .*undefined|There were undefined", log_path.read_text(encoding="utf-8", errors="replace")):
        result = subprocess.run(command[:2] + ["-g"] + command[2:], cwd=ROOT, env=environment, capture_output=True, timeout=240)
    if result.returncode:
        print(result.stdout.decode("utf-8", errors="replace")[-4000:].encode("ascii", errors="backslashreplace").decode())
        raise RuntimeError(f"latexmk_failed_{number}")
    if number == 1:
        # pdfpages introduce una transformación de centrado. Reinsertar la página
        # original como objeto PDF completo evita cualquier cambio en su arte.
        path = ROOT / ".build/latex/estadistica-act1" / f"{BASE}1.pdf"
        original = infographic_asset()
        temporary = path.with_suffix(".preservado.pdf")
        with pymupdf.open(path) as document, pymupdf.open(original) as infographic:
            positions = [index for index, page in enumerate(document) if abs(page.rect.width - infographic[0].rect.width) < 1]
            assert len(positions) == 1
            position = positions[0]
            document.delete_page(position)
            document.insert_pdf(infographic, start_at=position)
            document.save(temporary, garbage=4, deflate=True)
        os.replace(temporary, path)


def validate(number, promote=False):
    if number == 2:
        return validate_investigation(promote=promote)
    if number != 1:
        raise ValueError("Unidad 1 valida únicamente las actividades 1 y 2")
    stem = f"{BASE}{number}"
    path = ROOT / f".build/latex/estadistica-act{number}" / f"{stem}.pdf"
    source = SUBJECT / f"{stem}.tex"
    assert path.stat().st_mtime >= source.stat().st_mtime
    log = path.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
    assert not re.search(r"Overfull|Underfull|Missing character|Citation .*undefined|There were undefined|^!", log, re.MULTILINE)
    warnings = re.findall(r"(?:LaTeX Font Warning|Package \w+ Warning):[^\n]+", log)
    with pymupdf.open(path) as document:
        assert len(document) >= 7
        text = unicodedata.normalize("NFKC", "\n".join(page.get_text() for page in document))
        for prohibited in ("Módulo Moodle", "Actividad local", "Vencimiento publicado", "Refuerzo Ciclo", "por definir", "[?]", "esta actividad", "producto solicitado"):
            assert prohibited.casefold() not in text.casefold(), prohibited
        for required in ("Introducción", "Conclusiones", "Referencias", "26130503"):
            assert required in text, required
        expected = ("holmesBusiness2023", "bradley2021", "nistHandbook")
        source_text = source.read_text(encoding="utf-8")
        bib_text = (SUBJECT / "referencias-estadistica-verificadas.bib").read_text(encoding="utf-8")
        for key in expected:
            assert "{" + key + "}" in source_text
            assert "{" + key + "," in bib_text
        sizes = set()
        fonts = set()
        for page in document:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        if not span["text"].strip():
                            continue
                        bounds = pymupdf.Rect(span["bbox"])
                        assert bounds.x0 >= 0 and bounds.y0 >= 0 and bounds.x1 <= page.rect.width + 0.2 and bounds.y1 <= page.rect.height + 0.2
        if number == 1:
            assert len(re.findall(r"\\section\{", source_text)) == 3
            assert document[0].get_images(), "El informe requiere portada institucional"
            infographic = infographic_asset()
            delivery = SUBJECT / "entregas-estadistica-aplicada-para-la-administracion/Actividad-1-Infografia.pdf"
            assert hashlib.sha256(infographic.read_bytes()).hexdigest() == hashlib.sha256(delivery.read_bytes()).hexdigest()
            originals = json.loads((SUBJECT / "assets-estadistica-aplicada-para-la-administracion/respaldo-estructura-2026-10-24/conservacion-originales.json").read_text(encoding="utf-8"))
            original_asset = SUBJECT / "assets-estadistica-aplicada-para-la-administracion/infografia-muestreo-original.pdf"
            assert hashlib.sha256(original_asset.read_bytes()).hexdigest() == originals["infografia_entrega"]["sha256"]
            pages = [page for page in document if abs(page.rect.width - 297 * 72 / 25.4) < 1]
            assert len(pages) == 1, "La infografía A3 completa debe estar dentro del desarrollo"
            page = pages[0]
            with pymupdf.open(infographic) as original:
                assert hashlib.sha256(page.get_pixmap().samples).hexdigest() == hashlib.sha256(original[0].get_pixmap().samples).hexdigest(), "La lámina se debe preservar completa"
            assert "Escenario hipotético" in page.get_text() and "sin datos empíricos" in page.get_text()
            assert "385" in text and "482" in text
        (NOTES / f"actividad-{number}-texto.pdf.txt").write_text(text, encoding="utf-8")
        return {"activity": number, "pdf": str(path.relative_to(ROOT)), "pages": len(document),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "body_fonts": sorted(fonts),
                "body_pdf_point_sizes": sorted(sizes), "references": list(expected),
                "noncritical_font_warnings": warnings, "checks_passed": True}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--promote", action="store_true")
    arguments = parser.parse_args()
    NOTES.mkdir(parents=True, exist_ok=True)
    assert math.ceil(1.96 ** 2 * 0.5 * 0.5 / 0.05 ** 2) == 385
    assert math.ceil(385 / 0.8) == 482
    assert math.isclose((7.2 - 4.8) / 7.2, 1 / 3)
    results = []
    for number in (1, 2):
        if arguments.build:
            build(number)
        results.append(validate(number, promote=arguments.promote and number == 2))
    sources = json.loads((NOTES / "fuentes.json").read_text(encoding="utf-8"))
    for record in sources["sources"]:
        assert hashlib.sha256((SUBJECT / record["path"]).read_bytes()).hexdigest() == record["sha256"]
    if arguments.promote:
        deliveries = SUBJECT / "entregas-estadistica-aplicada-para-la-administracion"
        deliveries.mkdir(exist_ok=True)
        for result, name in zip(results, ("Actividad-1-Infografia.pdf", "Actividad-2-Investigacion.pdf")):
            if result["activity"] == 2:
                # El validador dedicado ya consolida cada versión desde su fuente.
                # Nunca copiar el informe completo sobre la entrega de cinco páginas.
                continue
            original = ROOT / result["pdf"]
            # La revisión autorizada integra la fusión sin borrar el arte original.
            targets = (SUBJECT / original.name,) if result["activity"] == 1 else (SUBJECT / original.name, deliveries / name)
            for target in targets:
                shutil.copy2(original, target)
                assert hashlib.sha256(target.read_bytes()).hexdigest() == result["sha256"]
            if result["activity"] == 1:
                shutil.copy2(infographic_asset(), deliveries / name)
            result["delivery"] = (deliveries / name).relative_to(SUBJECT).as_posix()
            result["delivery_sha256"] = hashlib.sha256((deliveries / name).read_bytes()).hexdigest()
            result["delivery_is_root_report"] = result["activity"] != 1
    manifest = {"validated_at_utc": datetime.now(timezone.utc).isoformat(), "platform_submission": False,
                "scope": "Unidad 1: tareas 1747 y 1748; evidencia del cuestionario documentada por separado",
                "numerical_checks_passed": True, "source_hashes_verified": len(sources["sources"]), "documents": results}
    (NOTES / "validacion.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
