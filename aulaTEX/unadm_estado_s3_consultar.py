"""Read-only audit of UnADM Teoria del Estado S3 and its resources."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.config import load_aulatex_env
from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

HOST = "aulavirtual.unadmexico.mx"
SUBJECT = ROOT / "UnADM/licenciatura-en-derecho-unadm/teoria-del-estado-y-constitucion-lde"
NOTES = SUBJECT / "referencias-teoria-del-estado-y-constitucion/notas-teoria-del-estado-y-constitucion/actividad-03-analisis-de-hechos"
PLANS = SUBJECT / "planeaciones-teoria-del-estado-y-constitucion"


def main() -> None:
    load_aulatex_env()
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    accounts = [item for item in vault.list_accounts(pin)
                if item["institution"].casefold() == "unadm"
                and urlsplit(item["url"]).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError("No hay una cuenta UnADM autorizada unica.")
    credentials = vault.get_credentials(pin, accounts[0]["id"])
    audit = {"consulted_at": datetime.now(timezone.utc).isoformat(),
             "course": f"https://{HOST}/course/view.php?id=3432", "read_only": True,
             "resources": [], "activities": []}
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=False)
        page = context.new_page()
        page.set_default_timeout(45000)
        page.goto(accounts[0]["url"], wait_until="domcontentloaded")
        page.get_by_role("textbox", name=re.compile("Matr")).fill(credentials["username"])
        page.locator("input[type=password]").fill(credentials["password"])
        page.get_by_role("button", name=re.compile("Inicia sesi")).click()
        page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path)
        del credentials
        page.goto(audit["course"], wait_until="domcontentloaded")
        links = page.locator('.course-content a[href*="/mod/"]').evaluate_all(
            "items => items.map(item => ({title: item.innerText.trim(), url: item.href}))")
        audit["course_links"] = list({item["url"]: item for item in links}.values())
        selected = [item for item in audit["course_links"]
                    if re.search(r"S3|semana\s*3|an[aá]lisis de hechos|S2.S3|formato de actividades", item["title"], re.I)
                    or "/mod/assign/view.php" in urlsplit(item["url"]).path]
        plan_url = f"https://{HOST}/mod/resource/view.php?id=214928"
        if not any(item["url"] == plan_url for item in selected):
            selected.append({"title": "PA S2_S3 Teoria del Estado y Constitucion 2026", "url": plan_url})
        for item in selected:
            parsed = urlsplit(item["url"])
            if parsed.hostname != HOST:
                continue
            if "/mod/assign/view.php" in parsed.path:
                page.goto(item["url"], wait_until="domcontentloaded")
                audit["activities"].append({**item, "text": page.locator("#region-main").inner_text()})
                continue
            if "/mod/resource/view.php" not in parsed.path:
                continue
            response = context.request.get(item["url"])
            data = response.body()
            suffix = ".pdf" if data.startswith(b"%PDF-") else ".docx" if data.startswith(b"PK") else ""
            if not response.ok or not suffix:
                audit["resources"].append({**item, "status": response.status, "archived": False})
                continue
            original = Path(unquote(urlsplit(response.url).path)).name
            is_plan = parsed.query in {"id=214928", "id=214930"}
            target_dir = PLANS if is_plan else NOTES / "materiales-aula"
            target_dir.mkdir(parents=True, exist_ok=True)
            target = (PLANS / "Planificacion-de-actividades-S2-S3-Teoria-del-Estado-y-Constitucion.pdf"
                      if is_plan else target_dir / f"S3-aula-{parsed.query.split('=')[-1]}-{original if original.lower().endswith(suffix) else 'recurso' + suffix}")
            digest = hashlib.sha256(data).hexdigest()
            if target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"Archivo existente distinto: {target.name}")
            if not target.exists():
                target.write_bytes(data)
            audit["resources"].append({**item, "original": original, "source_url": response.url,
                                       "destination": target.relative_to(SUBJECT).as_posix(),
                                       "sha256": digest, "bytes": len(data), "archived": True})
        context.close()
        browser.close()
    NOTES.mkdir(parents=True, exist_ok=True)
    target = NOTES / "consulta-plataforma-S3.json"
    target.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"audit": str(target), "resources": len(audit["resources"]),
                      "assignments": len(audit["activities"]),
                      "selected_links": [(item["title"], item["url"]) for item in selected]}, ensure_ascii=False))


if __name__ == "__main__":
    main()