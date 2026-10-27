import argparse
import hashlib
import itertools
import json
import math
import re
import shutil
import statistics
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

import pymupdf
from scipy.stats import binom, norm

from validar_unidad_1 import BASE, ROOT, SUBJECT, build

NOTES = SUBJECT / "referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/unidad-2-distribuciones"


def numerical_checks():
    population = (3, 7, 11, 15)
    samples = list(itertools.product(population, repeat=2))
    means = [statistics.mean(sample) for sample in samples]
    assert len(samples) == 16
    assert statistics.mean(population) == statistics.mean(means) == 9
    assert statistics.pvariance(population) == 20
    assert statistics.pvariance(means) == 10
    results = {"1": {"population_mean": 9, "population_sd": math.sqrt(20), "means_mean": 9,
                     "means_sd": math.sqrt(10), "sample_means": means}, "binomial": {}, "normal": {}}
    for label, size, probability, cutoff, upper in (
        ("2a", 400, 0.02, 12, True), ("2b", 400, 0.02, 8, False),
        ("4a", 200, 0.46, 101, True), ("4b", 1000, 0.46, 501, True),
    ):
        exact = float(binom.sf(cutoff - 1, size, probability) if upper else binom.cdf(cutoff, size, probability))
        counts = range(cutoff, size + 1) if upper else range(cutoff + 1)
        independent = math.fsum(math.comb(size, count) * probability ** count * (1 - probability) ** (size - count) for count in counts)
        assert math.isclose(exact, independent, rel_tol=1e-10, abs_tol=1e-13)
        mean = size * probability
        deviation = math.sqrt(size * probability * (1 - probability))
        boundary = cutoff - 0.5 if upper else cutoff + 0.5
        zscore = (boundary - mean) / deviation
        approximate = float(norm.sf(zscore) if upper else norm.cdf(zscore))
        results["binomial"][label] = {"exact": exact, "normal_continuity": approximate, "z": zscore, "cutoff": cutoff}
    normal = statistics.NormalDist()
    for label, mean, deviation, size, lower, upper in (
        ("3a", 800, 60, 16, 790, 810), ("3b", 800, 60, 16, None, 785),
        ("3c", 800, 60, 16, 820, None), ("3d", 800, 60, 16, 770, 830),
        ("5.1a", 172, 29, 1, None, 167), ("5.1b", 172, 29, 36, None, 167),
        ("5.2a", 172, 29, 1, 180, None), ("5.2b", 172, 29, 100, 180, None),
        ("5.3a", 172, 29, 1, 170, 175), ("5.3b", 172, 29, 64, 170, 175),
        ("5.4a", 172, 29, 1, 100, 165), ("5.4b", 172, 29, 81, 100, 165),
    ):
        standard_error = deviation / math.sqrt(size)
        lower_z = (lower - mean) / standard_error if lower is not None else None
        upper_z = (upper - mean) / standard_error if upper is not None else None
        if lower_z is None:
            value = float(norm.cdf(upper_z))
            independent = normal.cdf(upper_z)
        elif upper_z is None:
            value = float(norm.sf(lower_z))
            independent = normal.cdf(-lower_z)
        else:
            value = float(norm.cdf(upper_z) - norm.cdf(lower_z))
            independent = normal.cdf(upper_z) - normal.cdf(lower_z)
        assert math.isclose(value, independent, abs_tol=1e-12)
        results["normal"][label] = {"probability": value, "se": standard_error, "lower_z": lower_z, "upper_z": upper_z}
    assert statistics.mean((180, 200, 220, 240)) == 210
    assert math.sqrt(100 / 400) == 0.5
    return results


def validate(number):
    source = SUBJECT / f"{BASE}{number}.tex"
    path = ROOT / f".build/latex/estadistica-act{number}" / f"{BASE}{number}.pdf"
    assert path.stat().st_mtime >= source.stat().st_mtime
    source_text = source.read_text(encoding="utf-8")
    log = path.with_suffix(".log").read_text(encoding="utf-8", errors="replace")
    assert not re.search(r"Overfull|Underfull|Missing character|Citation .*undefined|There were undefined|^!", log, re.MULTILINE)
    citations = {key.strip() for group in re.findall(r"\\cite\w*\*?(?:\[[^\]]*\]){0,2}\{([^}]+)\}", source_text) for key in group.split(",")}
    bibliography = (SUBJECT / "referencias-estadistica-verificadas.bib").read_text(encoding="utf-8")
    assert len(citations) >= 3
    for key in citations:
        assert "{" + key + "," in bibliography
        assert re.search(r"\\bibitem\[[^\]]+\]\{" + re.escape(key) + r"\}", source_text)
    assert len(re.findall(r"\\section\{", source_text)) == 3
    assert r"\setstretch{1.5}" in source_text and r"\justifying" in source_text
    with pymupdf.open(path) as document:
        assert len(document) == (5 if number == 3 else 8), len(document)
        assert document[0].get_images()
        text = unicodedata.normalize("NFKC", "\n".join(page.get_text() for page in document))
        for required in ("Introducción", "Conclusiones", "Referencias", "26130503"):
            assert required in text
        for prohibited in ("Módulo Moodle", "Actividad local", "Vencimiento publicado", "por definir", "[?]", "esta actividad", "producto solicitado"):
            assert prohibited.casefold() not in text.casefold()
        if number == 4:
            calculations = numerical_checks()
            expected_values = [calculations["1"]["population_sd"], calculations["1"]["means_sd"]]
            expected_values.extend(item["probability"] for item in calculations["normal"].values())
            for item in calculations["binomial"].values():
                expected_values.extend((item["exact"], item["normal_continuity"]))
            for value in expected_values:
                assert f"{value:.6f}" in text, value
        fonts = set()
        for page in document:
            assert abs(page.rect.width - 612) < 1 and abs(page.rect.height - 792) < 1
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line["spans"]:
                        if not span["text"].strip():
                            continue
                        bounds = pymupdf.Rect(span["bbox"])
                        assert bounds.x0 >= 0 and bounds.y0 >= 0 and bounds.x1 <= page.rect.width + 0.2 and bounds.y1 <= page.rect.height + 0.2
                        if page.number > 0 and bounds.y1 < page.rect.height - 50:
                            fonts.add(span["font"])
                            assert "Arial" in span["font"], span["font"]
                            if span["text"] != "a":
                                assert abs(span["size"] - 12 * 72 / 72.27) < 0.08, (span["text"], span["size"])
            page.get_pixmap(matrix=pymupdf.Matrix(1.3, 1.3)).save(NOTES / f"actividad-{number}-pagina-{page.number + 1}.png")
        (NOTES / f"actividad-{number}-texto.pdf.txt").write_text(text, encoding="utf-8")
        return {"activity": number, "pages": len(document), "pdf": path.relative_to(ROOT).as_posix(),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "body_fonts": sorted(fonts),
                "references": sorted(citations), "checks_passed": True,
                "font_warnings": re.findall(r"LaTeX Font Warning:[^\n]+", log)}


def archive_sources():
    from bs4 import BeautifulSoup
    from playwright.sync_api import sync_playwright

    path = NOTES / "fuentes.json"
    if path.exists():
        records = json.loads(path.read_text(encoding="utf-8"))["sources"]
    else:
        records = []
        with sync_playwright() as engine:
            browser = engine.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                for key, url, marker in (
                    ("holmesBusiness2023", "https://openstax.org/books/introductory-business-statistics-2e/pages/7-introduction", "Central Limit Theorem"),
                    ("holmesBusiness2023", "https://openstax.org/books/introductory-business-statistics-2e/pages/8-introduction", "confidence interval"),
                    ("nistHandbook", "https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm", "Confidence Limits for the Mean"),
                    ("nistHandbook", "https://www.itl.nist.gov/div898/handbook/eda/section3/eda366i.htm", "Binomial Distribution"),
                ):
                    response = page.goto(url, wait_until="networkidle", timeout=60000)
                    assert response is not None and response.ok
                    content = page.content()
                    soup = BeautifulSoup(content, "html.parser")
                    for element in soup(("script", "style")):
                        element.decompose()
                    text = soup.get_text("\n", strip=True)
                    assert marker.casefold() in text.casefold(), url
                    destination = NOTES / f"fuente-{len(records) + 1}.html"
                    destination.write_text(content, encoding="utf-8")
                    destination.with_suffix(".txt").write_text(text, encoding="utf-8")
                    records.append({"key": key, "url": url, "path": destination.relative_to(SUBJECT).as_posix(),
                                    "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()})
            finally:
                browser.close()
        previous = json.loads((NOTES.parent / "unidad-1-muestreo/fuentes.json").read_text(encoding="utf-8"))
        records.extend(item for item in previous["sources"] if item["key"] == "bradley2021")
        path.write_text(json.dumps({"retrieved_at_utc": datetime.now(timezone.utc).isoformat(), "sources": records}, indent=2), encoding="utf-8")
    for record in records:
        assert hashlib.sha256((SUBJECT / record["path"]).read_bytes()).hexdigest() == record["sha256"]
    return len(records)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--numbers-only", action="store_true")
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--promote", action="store_true")
    parser.add_argument("--archive-sources", action="store_true")
    parser.add_argument("--activities", type=int, nargs="+", choices=(3, 4), default=(3, 4))
    arguments = parser.parse_args()
    NOTES.mkdir(parents=True, exist_ok=True)
    results = numerical_checks()
    (NOTES / "calculos-verificados.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    if arguments.numbers_only:
        print(json.dumps(results, indent=2))
        return
    source_count = archive_sources() if arguments.archive_sources else None
    documents = []
    for number in arguments.activities:
        if arguments.build:
            build(number)
        document = validate(number)
        if arguments.promote:
            original = ROOT / document["pdf"]
            name = "Actividad-3-Investigacion-estimacion.pdf" if number == 3 else "Actividad-4-Ejercicios-distribuciones.pdf"
            delivery = SUBJECT / "entregas-estadistica-aplicada-para-la-administracion" / name
            for target in (SUBJECT / original.name, delivery):
                shutil.copy2(original, target)
                assert hashlib.sha256(target.read_bytes()).hexdigest() == document["sha256"]
            document["delivery"] = delivery.relative_to(SUBJECT).as_posix()
        documents.append(document)
    manifest = {"validated_at_utc": datetime.now(timezone.utc).isoformat(), "platform_submission": False,
                "quiz_started": False, "numerical_checks_passed": True, "source_hashes_verified": source_count,
                "documents": documents}
    (NOTES / "validacion.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()