from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
from urllib.parse import urlsplit, unquote

import pymupdf
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

HOST = "aulavirtual.unadmexico.mx"
SUBJECT = ROOT / "UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde"
NOTES = SUBJECT / "referencias-derecho-penal-especial-mexicano/notas-derecho-penal-especial-mexicano/actividad-04-delitos-de-peligro"
MATERIAL = NOTES / "material-docente"
PLANNING = SUBJECT / "planeaciones-derecho-penal-especial-mexicano/originales-docentes/Planificacion-S4-delitos-de-peligro-docente.pdf"


def preserve_write(path: Path, body: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.read_bytes() != body:
        raise RuntimeError(f"El destino ya existe con contenido diferente: {path}")
    path.write_bytes(body)


def normalized_title(title: str) -> str:
    upper = title.upper()
    if "PLANIFICACI" in upper:
        return "Planificacion-S4-delitos-de-peligro-docente"
    if "MATERIAL" in upper:
        return "Material-de-apoyo-S4-delitos-de-peligro"
    if "CPEUM" in upper:
        return "CPEUM-copia-aula-S4"
    if "FEDERAL" in upper:
        return "Codigo-Penal-Federal-copia-aula-S4"
    if "PENAL" in upper:
        return "Codigo-Penal-CDMX-copia-aula-S4"
    return re.sub(r"[^A-Za-z0-9-]+", "-", title).strip("-")


def main() -> None:
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    accounts = [a for a in vault.list_accounts(pin)
                if a["institution"].casefold() == "unadm"
                and urlsplit(a["url"]).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError("Se requiere una unica cuenta UnADM autorizada.")
    credentials = vault.get_credentials(pin, accounts[0]["id"])
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.goto(accounts[0]["url"], wait_until="domcontentloaded")
        page.get_by_role("textbox", name=re.compile("Matr")).fill(credentials["username"])
        page.locator("input[type=password]").fill(credentials["password"])
        page.get_by_role("button", name=re.compile("Inicia sesi")).click()
        page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path)
        del credentials
        page.goto(f"https://{HOST}/course/view.php?id=3482", wait_until="domcontentloaded")
        section = next(s for s in page.locator(".course-section, li.section").all()
                       if s.locator(".sectionname, .section-title").count()
                       and "Semana 4" in s.locator(".sectionname, .section-title").first.inner_text())
        links = section.locator("a[href]").evaluate_all(
            "links => links.map(link => ({title: link.innerText.trim(), url: link.href}))")
        preserve_write(NOTES / "seccion-aula-S4.txt", section.inner_text().encode("utf-8"))
        preserve_write(NOTES / "enlaces-aula-S4.json", (json.dumps(links, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        records = []
        for link in links:
            if "/mod/resource/view.php" not in link["url"]:
                continue
            response = context.request.get(link["url"])
            body = response.body()
            if not response.ok or not body.startswith(b"%PDF-"):
                raise RuntimeError(f"Recurso {link['title']} no devolvio PDF valido: {response.status}")
            name = normalized_title(link["title"])
            destination = MATERIAL / f"{name}.pdf"
            preserve_write(destination, body)
            if "Planificacion" in name:
                preserve_write(PLANNING, body)
            doc = pymupdf.open(stream=body, filetype="pdf")
            extracted = "\n\n".join(f"Pagina {i}\n{p.get_text()}" for i, p in enumerate(doc, 1))
            preserve_write(destination.with_suffix(".txt"), extracted.encode("utf-8"))
            # Teaching PDFs can contain only raster pages; preserve a render for exact reading.
            if len(extracted.strip()) < 300 or "Material" in name or "Planificacion" in name:
                renderdir = MATERIAL / "renders" / name
                renderdir.mkdir(parents=True, exist_ok=True)
                for i, pdfpage in enumerate(doc, 1):
                    out = renderdir / f"pagina-{i:02}.png"
                    preserve_write(out, pdfpage.get_pixmap(matrix=pymupdf.Matrix(1.6, 1.6)).tobytes("png"))
            records.append({"title": link["title"], "url": link["url"],
                            "file": str(destination.relative_to(SUBJECT)).replace("\\", "/"),
                            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                            "pages": len(doc), "extracted_characters": len(extracted), "source_url": response.url})
        assignment_link = next(link for link in links if "/mod/assign/view.php" in link["url"])
        page.goto(assignment_link["url"], wait_until="domcontentloaded")
        main = page.locator("#region-main")
        assignment_text = main.inner_text()
        preserve_write(NOTES / "consigna-aula-S4.txt", assignment_text.encode("utf-8"))
        preserve_write(NOTES / "consigna-aula-S4.html", main.inner_html().encode("utf-8"))
        images = main.locator("img[src]").evaluate_all("images => images.map(img => ({alt: img.alt, url: img.src}))")
        for i, img in enumerate(images, 1):
            if urlsplit(img["url"]).hostname != HOST or "/pluginfile.php/" not in img["url"]:
                continue
            response = context.request.get(img["url"])
            if not response.ok:
                raise RuntimeError(f"Imagen docente no disponible: {response.status}")
            body = response.body()
            filename = Path(unquote(urlsplit(img["url"]).path)).name
            destination = MATERIAL / f"Consigna-S4-{i:02}-{filename}"
            preserve_write(destination, body)
            records.append({"title": img["alt"] or filename, "url": img["url"],
                            "file": str(destination.relative_to(SUBJECT)).replace("\\", "/"),
                            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)})
        preserve_write(NOTES / "inventario-descargas-S4.json", (json.dumps(records, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(json.dumps({"resources": records, "assignment_url": assignment_link["url"], "assignment_text": assignment_text}, ensure_ascii=False, indent=2))
        browser.close()


if __name__ == "__main__":
    main()
