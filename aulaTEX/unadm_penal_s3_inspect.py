from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

import pymupdf
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

HOST = "aulavirtual.unadmexico.mx"
SUBJECT = ROOT / "UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde"
REFERENCES = SUBJECT / "referencias-derecho-penal-especial-mexicano"
NOTES = REFERENCES / "notas-derecho-penal-especial-mexicano/actividad-03-estudio-caso-vida-integridad"
RESOURCES = {
    216749: SUBJECT / "planeaciones-derecho-penal-especial-mexicano/originales-docentes/Planificacion-S3-docente.pdf",
    216763: NOTES / "material-docente/Material-de-apoyo-S3.pdf",
    216785: REFERENCES / "fuentes-oficiales-2026-10-11/CPEUM-copia-aula-S3.pdf",
    216786: REFERENCES / "fuentes-oficiales-2026-10-11/Codigo-Penal-CDMX-copia-aula-S3.pdf",
    216787: REFERENCES / "fuentes-oficiales-2026-10-11/Codigo-Penal-Federal-copia-aula-S3.pdf",
}


def main() -> None:
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    accounts = [
        account for account in vault.list_accounts(pin)
        if account["institution"].casefold() == "unadm"
        and urlsplit(account["url"]).hostname == HOST
    ]
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
        section = next(section for section in page.locator(".course-section, li.section").all()
                       if section.locator(".sectionname, .section-title").count()
                       and "Semana 3" in section.locator(".sectionname, .section-title").first.inner_text())
        links = section.locator("a[href]").evaluate_all(
            "links => links.map(link => ({title: link.innerText.trim(), url: link.href}))"
        )
        records = []
        for resource_id, destination in RESOURCES.items():
            url = f"https://{HOST}/mod/resource/view.php?id={resource_id}"
            link = next(link for link in links if link["url"] == url)
            response = context.request.get(url)
            body = response.body()
            if not response.ok or not body.startswith(b"%PDF-"):
                raise RuntimeError(f"Recurso {resource_id} no devolvio un PDF valido: {response.status}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists() and destination.read_bytes() != body:
                raise RuntimeError(f"El destino ya existe con contenido diferente: {destination}")
            destination.write_bytes(body)
            records.append({"title": link["title"], "url": url,
                            "file": str(destination.relative_to(SUBJECT)).replace("\\", "/"),
                            "sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body),
                            "source_url": response.url})
        assignment = context.request.get(f"https://{HOST}/mod/assign/view.php?id=216751")
        if not assignment.ok:
            raise RuntimeError(f"La tarea S3 no respondio correctamente: {assignment.status}")
        page.goto(f"https://{HOST}/mod/assign/view.php?id=216751", wait_until="domcontentloaded")
        assignment_text = page.locator("#region-main").inner_text()
        NOTES.mkdir(parents=True, exist_ok=True)
        (NOTES / "consigna-aula-S3.txt").write_text(assignment_text, encoding="utf-8")
        (NOTES / "inventario-descargas-S3.json").write_text(
            json.dumps(records, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        support = pymupdf.open(RESOURCES[216763])
        (NOTES / "material-docente/Material-de-apoyo-S3.txt").write_text(
            "\n\n".join(f"Pagina {number}\n{page.get_text()}"
                        for number, page in enumerate(support, 1)), encoding="utf-8")
        print(json.dumps(records, ensure_ascii=False, indent=2))
        print("Consigna S3:", assignment_text[:4500])
        browser.close()


if __name__ == "__main__":
    main()