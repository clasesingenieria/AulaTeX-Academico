from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sys
from datetime import datetime
from urllib.parse import unquote, urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.aulatex.config import load_aulatex_env
from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path
from playwright.sync_api import sync_playwright

COURSES = {3432: "teoria-del-estado-y-constitucion", 3441: "antecedentes-de-los-derechos-humanos", 3482: "derecho-penal-especial-mexicano"}
HOST = "aulavirtual.unadmexico.mx"


def main() -> None:
    load_aulatex_env()
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    accounts = [account for account in vault.list_accounts(pin) if account["institution"].casefold() == "unadm" and urlsplit(account["url"]).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError("Cuenta UnADM no univoca")
    credentials = vault.get_credentials(pin, accounts[0]["id"])
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto(accounts[0]["url"], wait_until="domcontentloaded")
        page.get_by_role("textbox", name=re.compile("Matr")).fill(credentials["username"])
        page.locator("input[type=password]").fill(credentials["password"])
        page.get_by_role("button", name=re.compile("Inicia sesi")).click()
        page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path, wait_until="domcontentloaded")
        del credentials
        for course, slug in COURSES.items():
            target = ROOT / "UnADM/licenciatura-en-derecho-unadm" / f"{slug}-lde"
            output = target / f"referencias-{slug}" / f"notas-{slug}/materiales-generales/auditorias/semana2-2026-10-11"
            output.mkdir(parents=True, exist_ok=True)
            url = f"https://{HOST}/course/view.php?id={course}"
            page.goto(url, wait_until="domcontentloaded")
            links = page.locator('.course-content a[href*="/mod/"]').evaluate_all("items=>items.map(item=>({title:item.innerText,url:item.href}))")
            links = list({link["url"]: link for link in links if urlsplit(link["url"]).hostname == HOST}.values())
            record = {"consulta": datetime.now(ZoneInfo("America/Mexico_City")).isoformat(), "curso": course, "solo_lectura": True, "enlaces": links, "actividades": []}
            for link in links:
                is_task = "/mod/assign/" in link["url"]
                is_forum = "/mod/forum/" in link["url"] and re.search("actividad|diagn|participa", link["title"], re.I)
                if not (is_task or is_forum):
                    continue
                page.goto(link["url"], wait_until="domcontentloaded")
                module = urlsplit(link["url"]).query.split("=")[-1]
                item = dict(link, modulo=module, texto=page.locator("#region-main").inner_text(), archivos=[])
                if is_task:
                    files = page.locator('#region-main a[href*="pluginfile.php"]').evaluate_all("items=>items.map(item=>({title:item.innerText,url:item.href}))")
                    for file in files:
                        parsed = urlsplit(file["url"])
                        if parsed.hostname != HOST or not unquote(parsed.path).lower().endswith((".pdf", ".docx")):
                            continue
                        response = context.request.get(file["url"])
                        payload = response.body()
                        if not response.ok or payload[:2] not in (b"%P", b"PK"):
                            raise RuntimeError("Adjunto no recuperado")
                        name = Path(unquote(parsed.path)).name
                        destination = output / f"{module}-{name}"
                        digest = hashlib.sha256(payload).hexdigest()
                        if destination.exists() and hashlib.sha256(destination.read_bytes()).hexdigest() != digest:
                            raise RuntimeError("Adjunto existente diferente")
                        destination.write_bytes(payload)
                        item["archivos"].append({"archivo": name, "local": destination.relative_to(target).as_posix(), "sha256": digest, "url": file["url"]})
                record["actividades"].append(item)
            (output / "plataforma.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
            print(json.dumps({"curso": course, "consulta": record["consulta"], "actividades": [{"modulo": item["modulo"], "titulo": item["title"], "texto": item["texto"][:8000], "archivos": item["archivos"]} for item in record["actividades"]]}, ensure_ascii=True))
        context.close()
        browser.close()


if __name__ == "__main__":
    main()