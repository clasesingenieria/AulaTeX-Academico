from __future__ import annotations

import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

COURSES = {
    3432: ("teoria-del-estado-y-constitucion", "Teoria del Estado y Constitucion", "020"),
    3482: ("derecho-penal-especial-mexicano", "Derecho penal especial mexicano", "020"),
    3441: ("antecedentes-de-los-derechos-humanos", "Antecedentes de los derechos humanos", "005"),
}
HOST = "aulavirtual.unadmexico.mx"


def main() -> None:
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    vault = PlatformCredentialVault(default_vault_path(PROJECT_ROOT))
    accounts = [
        account for account in vault.list_accounts(pin)
        if account["institution"].casefold() == "unadm"
        and urlsplit(account["url"]).hostname == HOST
    ]
    if len(accounts) != 1:
        raise RuntimeError("Se requiere una unica cuenta UnADM para el sitio autorizado.")
    credentials = vault.get_credentials(pin, accounts[0]["id"])
    root = PROJECT_ROOT / "UnADM" / "licenciatura-en-derecho-unadm"
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True)
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto(accounts[0]["url"], wait_until="domcontentloaded")
        page.get_by_role("textbox", name=re.compile("Matr")).fill(credentials["username"])
        page.locator("input[type=password]").fill(credentials["password"])
        page.get_by_role("button", name=re.compile("Inicia sesi")).click()
        page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path,
                  wait_until="domcontentloaded")
        del credentials
        for course_id, (slug, title, group) in COURSES.items():
            directory = root / f"{slug}-lde"
            references = directory / f"referencias-{slug}"
            planning = directory / f"planeaciones-{slug}"
            references.mkdir(parents=True, exist_ok=True)
            planning.mkdir(parents=True, exist_ok=True)
            course_url = f"https://{HOST}/course/view.php?id={course_id}"
            page.goto(course_url, wait_until="domcontentloaded")
            content = page.locator(".course-content")
            course_text = content.text_content() or ""
            (references / "curso-aula.txt").write_text(course_text, encoding="utf-8")
            links = content.locator("a[href]").evaluate_all(
                "links => links.map(link => ({title: link.innerText, url: link.href}))"
            )
            links = list({link["url"]: link for link in links
                          if urlsplit(link["url"]).hostname == HOST}.values())
            inventory = {"course_id": course_id, "title": title, "group": group,
                         "course_url": course_url, "links": links, "resources": []}
            for link in links:
                parsed = urlsplit(link["url"])
                if parsed.hostname != HOST or not parsed.path.startswith("/mod/"):
                    continue
                if not any(f"/mod/{kind}/" in parsed.path for kind in
                           ("resource", "folder", "page", "book", "assign", "forum", "url")):
                    continue
                record = {"title": link["title"], "url": link["url"]}
                try:
                    response = context.request.get(link["url"])
                    media_type = response.headers.get("content-type", "")
                    if "pdf" in media_type:
                        filename = re.sub(r"[^a-zA-Z0-9_-]", "-", link["title"]).strip("-")[:100]
                        destination = references / f"{filename or 'recurso'}-{len(inventory['resources'])}.pdf"
                        destination.write_bytes(response.body())
                        record["file"] = destination.name
                    else:
                        page.goto(link["url"], wait_until="domcontentloaded")
                        fragments = page.locator(".activity-description, .generalbox.mod_introbox, #intro, .resourcecontent, .book_content, .modified, .activity-dates")
                        text = "\n\n".join(fragments.all_inner_texts())
                        filename = f"modulo-{len(inventory['resources'])}.txt"
                        (references / filename).write_text(text, encoding="utf-8")
                        record["file"] = filename
                        record["attachments"] = page.locator(
                            '#region-main a[href*="pluginfile.php"], #region-main a[href*="/mod/book/view.php"], #region-main a[href*="/course/view.php"]'
                        ).evaluate_all("links => links.map(link => ({title: link.innerText, url: link.href}))")
                        if "/mod/forum/" not in parsed.path:
                            for attachment in record["attachments"]:
                                attachment_url = urlsplit(attachment["url"])
                                if attachment_url.hostname != HOST or "pluginfile.php" not in attachment_url.path:
                                    continue
                                download = context.request.get(attachment["url"])
                                if not download.ok or "text/html" in download.headers.get("content-type", ""):
                                    continue
                                name = Path(attachment_url.path).name
                                name = re.sub(r"[^a-zA-Z0-9._-]", "-", name)[:150]
                                destination = references / f"{len(inventory['resources'])}-{name}"
                                destination.write_bytes(download.body())
                                attachment["file"] = destination.name
                    record["status"] = "consultado"
                except Exception:
                    record["status"] = "pendiente-reintento"
                inventory["resources"].append(record)
            (references / "inventario-aula.json").write_text(
                json.dumps(inventory, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"{title}: {len(inventory['resources'])} recursos inventariados")
        browser.close()


if __name__ == "__main__":
    main()