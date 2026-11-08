"""Entrega verificada de Teoría del Estado y Constitución S5 en UnADM."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.config import load_aulatex_env
from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

HOST = "aulavirtual.unadmexico.mx"
URL = f"https://{HOST}/mod/assign/view.php?id=218026"
SUBJECT = ROOT / "UnADM/licenciatura-en-derecho-unadm/teoria-del-estado-y-constitucion-lde"
NOTES = SUBJECT / "referencias-teoria-del-estado-y-constitucion/notas-teoria-del-estado-y-constitucion/actividad-05-valoracion-de-decisiones"
PDF = SUBJECT / "entregas-teoria-del-estado-y-constitucion/2026_TeoríaEstado_S5_Martin_Jonathan_de_la_Cruz_Munoz.pdf"
EVIDENCE = NOTES / "comprobantes-envio/2026-11-01"


def main():
    load_aulatex_env()
    assert PDF.exists(), f"El archivo PDF no existe: {PDF}"
    digest = hashlib.sha256(PDF.read_bytes()).hexdigest()
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    pin = os.environ.get("AULATEX_MASTER_PIN", "")
    accounts = [a for a in vault.list_accounts(pin) if a["institution"].casefold() == "unadm" and urlsplit(a["url"]).hostname == HOST]
    assert len(accounts) == 1
    credentials = vault.get_credentials(pin, accounts[0]["id"])
    EVIDENCE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1100})
        page = context.new_page()
        page.set_default_timeout(45000)
        page.goto(accounts[0]["url"], wait_until="domcontentloaded")
        page.get_by_role("textbox", name=re.compile("Matr")).fill(credentials["username"])
        page.locator("input[type=password]").fill(credentials["password"])
        page.get_by_role("button", name=re.compile("Inicia sesi")).click()
        page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path)
        del credentials

        page.goto(URL, wait_until="networkidle")
        main_sec = page.locator("#region-main")
        before = main_sec.inner_text()
        (EVIDENCE / "estado-anterior-S5.txt").write_text(before, encoding="utf-8")
        page.screenshot(path=str(EVIDENCE / "estado-anterior-S5.png"), full_page=True)
        print("Estado anterior registrado.", flush=True)

        if "--submit" in sys.argv:
            page.goto(URL + "&action=editsubmission", wait_until="networkidle")
            page.screenshot(path=str(EVIDENCE / "editsubmission-inicial.png"), full_page=True)
            
            # Click botón Agregar...
            add_btn = page.locator(".fp-btn-add a, [title='Agregar...']").first
            add_btn.click()
            time.sleep(2)

            # Pestaña Subir un archivo
            page.get_by_text("Subir un archivo", exact=True).first.click()
            time.sleep(1)

            # Cargar archivo
            page.locator('input[type="file"]').first.set_input_files(str(PDF))
            time.sleep(1)

            # Botón Subir este archivo
            page.get_by_role("button", name="Subir este archivo", exact=True).first.click()
            print("Subiendo archivo a Moodle...", flush=True)

            # Esperar a que el diálogo desaparezca
            for _ in range(25):
                time.sleep(2)
                if page.locator('.moodle-dialogue-focused, .moodle-dialogue-wrap').filter(has_text="Subir un archivo").count() == 0:
                    break

            page.screenshot(path=str(EVIDENCE / "archivo-cargado-filemanager.png"), full_page=True)
            fm = page.locator('.filemanager.fm-loaded, .fp-content').first
            fm.wait_for(state='visible')
            fm_text = fm.inner_text()
            print(f"Filemanager text: {fm_text}", flush=True)

            page.locator("#id_submitbutton, button[name='submitbutton']").first.click()
            page.wait_for_load_state("networkidle")
            page.goto(URL, wait_until="networkidle")

            after_upload = main_sec.inner_text()
            assert PDF.name in after_upload
            submit = page.get_by_role("button", name=re.compile("Enviar tarea|Enviar para calificar", re.I))
            if submit.count() >= 1:
                submit.first.click()
                page.wait_for_load_state("networkidle")
                statement = page.locator('#id_submissionstatement')
                if statement.count():
                    statement.check()
                page.locator('#id_submitbutton, button[name="submitbutton"]').first.click()
                page.wait_for_load_state("networkidle")

            page.goto(URL, wait_until="networkidle")
            final_text = main_sec.inner_text()
            assert PDF.name in final_text
            file_links = main_sec.locator('a[href*="pluginfile.php"]').evaluate_all("els=>els.map(e=>({name:e.innerText.trim(),url:e.href}))")
            uploaded = next(x for x in file_links if PDF.name in x['name'])
            response = context.request.get(uploaded['url'])
            assert response.ok
            downloaded = response.body()
            remote_hash = hashlib.sha256(downloaded).hexdigest()
            assert remote_hash == digest, "Submitted PDF differs from local PDF"

            page.screenshot(path=str(EVIDENCE / "entrega-confirmada-S5.png"), full_page=True)
            (EVIDENCE / "estado-final-S5.txt").write_text(final_text, encoding='utf-8')
            record = {
                "verified_at": datetime.now(ZoneInfo('America/Mexico_City')).isoformat(),
                "activity_url": URL,
                "course_id": 3432,
                "activity": "S5. Valoración de decisiones",
                "subject": "Teoría del Estado y Constitución",
                "filename": PDF.name,
                "bytes": PDF.stat().st_size,
                "sha256": digest,
                "platform_file_download_matches": True,
                "state": "Enviado para calificar" if "Enviado para calificar" in final_text else "Entregado",
                "platform_submission_performed": True,
            }
            (EVIDENCE / "comprobante-envio-S5.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
            print(json.dumps({"phase": "complete", **record}, ensure_ascii=True, indent=2), flush=True)

        browser.close()


if __name__ == "__main__":
    main()
