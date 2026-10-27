import hashlib
import json
import ssl
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

import pymupdf
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

SUBJECT = Path(__file__).resolve().parents[1]
REFERENCES = SUBJECT / "referencias-estadistica-aplicada-para-la-administracion"
OUTPUT = REFERENCES / "articulos-muestreo"
NOTES = REFERENCES / "notas-estadistica-aplicada-para-la-administracion/unidad-1-muestreo"
SOURCES = {
    "bradley2021": ("https://www.nature.com/articles/s41586-021-04198-4", ".html"),
    "bloom2024": ("https://www.ebi.ac.uk/europepmc/webservices/rest/PMC11208135/fullTextXML", ".xml"),
    "barrero2023": ("https://wfhresearch.com/wp-content/uploads/2023/11/Evolution-of-Work-From-Home-Published.pdf", ".pdf"),
    "holmesMuestreo2023": ("https://openstax.org/books/introductory-business-statistics-2e/pages/1-2-data-sampling-and-variation-in-data-and-sampling", ".html"),
    "holmesProporcion2023": ("https://openstax.org/books/introductory-business-statistics-2e/pages/8-3-a-confidence-interval-for-a-population-proportion", ".html"),
    "nistTamano": ("https://www.itl.nist.gov/div898/handbook/prc/section2/prc242.htm", ".html"),
}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    NOTES.mkdir(parents=True, exist_ok=True)
    records = []
    for key, (url, extension) in SOURCES.items():
        print(key, flush=True)
        path = OUTPUT / (key + extension)
        if not path.exists():
            if key == "bradley2021":
                with sync_playwright() as engine:
                    browser = engine.chromium.launch(headless=True)
                    try:
                        page = browser.new_page()
                        page.goto(url, wait_until="domcontentloaded", timeout=60000)
                        page.get_by_role("heading", name="Comparing study designs", exact=True).wait_for(timeout=60000)
                        data = page.content().encode("utf-8")
                    finally:
                        browser.close()
            else:
                request = Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urlopen(request, timeout=60, context=ssl.create_default_context()) as response:
                    data = response.read(30 * 1024 * 1024 + 1)
            assert len(data) <= 30 * 1024 * 1024
            if extension == ".pdf":
                assert data.startswith(b"%PDF-")
            path.write_bytes(data)
        if extension == ".pdf":
            with pymupdf.open(path) as document:
                text = "\n\n".join(f"PAGINA PDF {number + 1}\n{page.get_text()}" for number, page in enumerate(document))
        else:
            soup = BeautifulSoup(path.read_bytes(), "xml" if extension == ".xml" else "html.parser")
            for element in soup(["script", "style", "nav", "footer"]):
                element.decompose()
            text = soup.get_text("\n", strip=True)
        assert len(text) > 1000, key
        (NOTES / (key + ".txt")).write_text(text, encoding="utf-8")
        records.append({"key": key, "url": url, "path": path.relative_to(SUBJECT).as_posix(),
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "text_characters": len(text)})
    manifest = {"checked_at_utc": datetime.now(timezone.utc).isoformat(), "sources": records}
    (NOTES / "fuentes.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()