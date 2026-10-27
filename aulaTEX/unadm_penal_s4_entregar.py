"""Inspect and submit the explicitly authorized UnADM Penal S4 PDF."""
from __future__ import annotations

from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.config import load_aulatex_env
from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

HOST = "aulavirtual.unadmexico.mx"
URL = f"https://{HOST}/mod/assign/view.php?id=218337"
SUBJECT = ROOT / "UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde"
NOTES = SUBJECT / "referencias-derecho-penal-especial-mexicano/notas-derecho-penal-especial-mexicano/actividad-04-delitos-de-peligro"
PDF = SUBJECT / "entregas-derecho-penal-especial-mexicano/Actividad-S4-Delitos-de-peligro-Martin-Jonathan-de-la-Cruz.pdf"
EVIDENCE = NOTES / "comprobantes-envio/2026-10-23"


def main():
    load_aulatex_env()
    expected = json.loads((NOTES / "revisiones/entrega-preparada-S4.json").read_text(encoding="utf-8"))
    digest = hashlib.sha256(PDF.read_bytes()).hexdigest()
    assert digest == expected["sha256"]
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
        page.set_default_timeout(25000)
        page.goto(accounts[0]["url"], wait_until="domcontentloaded")
        page.get_by_role("textbox", name=re.compile("Matr")).fill(credentials["username"])
        page.locator("input[type=password]").fill(credentials["password"])
        page.get_by_role("button", name=re.compile("Inicia sesi")).click()
        page.wait_for_url(lambda url: "/login/" not in urlsplit(url).path)
        del credentials
        page.goto(URL, wait_until="networkidle")
        main = page.locator("#region-main")
        before = main.inner_text()
        print(json.dumps({"phase": "before", "url": page.url, "title": page.title(), "headings": page.locator("h1,h2").all_text_contents(), "text": before}, ensure_ascii=True), flush=True)
        (EVIDENCE / "estado-anterior.txt").write_text(before, encoding="utf-8")
        if not any(flag in sys.argv for flag in ("--submit", "--finalize")):
            page.goto(URL + "&action=editsubmission", wait_until="networkidle")
            print(json.dumps({"phase": "edit-inspection", "text": main.inner_text(), "buttons": page.get_by_role("button").all_text_contents(), "form_controls": page.locator("#region-main input, #region-main select, #region-main textarea").evaluate_all("els=>els.map(e=>({tag:e.tagName,type:e.type,id:e.id,name:e.name})).filter(e=>e.type!=='hidden')")}, ensure_ascii=True), flush=True)
            page.screenshot(path=str(EVIDENCE / "formulario-inspeccion.png"), full_page=True)
        else:
            assert page.locator('a[href*="course/view.php?id=3482"]').count(), "Course identity mismatch"
            assert "ACTIVIDAD S4" in page.title()
            if "--finalize" in sys.argv:
                assert PDF.name in before and "Borrador (no enviado)" in before
                draft_link=main.get_by_role('link',name=PDF.name,exact=True)
                response=context.request.get(draft_link.get_attribute('href'))
                assert response.ok and hashlib.sha256(response.body()).hexdigest()==digest
            else:
                assert "Aun no se ha hecho ninguna tarea" in before, "An existing attempt requires review"
                page.goto(URL + "&action=editsubmission", wait_until="networkidle")
                page.locator(".fp-btn-add a").click()
                page.get_by_text("Subir un archivo", exact=True).click()
                page.locator('input[type="file"]').set_input_files(str(PDF))
                page.get_by_role("button", name="Subir este archivo", exact=True).click()
                page.locator(".filemanager").get_by_text(PDF.name, exact=True).wait_for()
                page.locator("#id_submitbutton").click()
                page.wait_for_load_state("networkidle")
                page.goto(URL, wait_until="networkidle")
            after_upload = main.inner_text()
            print(json.dumps({"phase":"uploaded", "text":after_upload, "buttons":page.get_by_role("button").all_text_contents()},ensure_ascii=True),flush=True)
            assert PDF.name in after_upload
            if "Enviado para calificar" not in after_upload:
                submit = page.get_by_role("button",name=re.compile("Enviar tarea|Enviar para calificar",re.I))
                assert submit.count()==1, "Final submission control requires inspection"
                submit.click()
                page.wait_for_load_state("networkidle")
                confirmation = main.inner_text()
                (EVIDENCE / "confirmacion-previa.txt").write_text(confirmation,encoding="utf-8")
                print(json.dumps({"phase":"confirmation", "text":confirmation,"checkboxes":page.locator('input[type=checkbox]').evaluate_all("els=>els.map(e=>({id:e.id,name:e.name,label:e.labels?[...e.labels].map(l=>l.innerText).join(' '):''}))"),"buttons":page.get_by_role("button").all_text_contents()},ensure_ascii=True),flush=True)
                assert "--finalize" in sys.argv,"Confirmation was inspected; explicit finalize mode required"
                statement="Este envío es obra mía, excepto cuando he reconocido el uso de los trabajos de otras personas."
                assert statement in confirmation,"Unexpected authorship statement"
                # The final artifact identifies sources and explicitly discloses ChatGPT assistance.
                page.locator('#id_submissionstatement').check()
                page.locator('#id_submitbutton').click()
                page.wait_for_load_state("networkidle")
            page.goto(URL,wait_until="networkidle")
            final=main.inner_text()
            assert PDF.name in final and "Enviado para calificar" in final, "Submission not confirmed"
            file_links=main.locator('a[href*="pluginfile.php"]').evaluate_all("els=>els.map(e=>({name:e.innerText.trim(),url:e.href}))")
            uploaded=next(x for x in file_links if PDF.name in x['name'])
            response=context.request.get(uploaded['url'])
            assert response.ok
            downloaded=response.body()
            assert downloaded.startswith(b'%PDF-')
            assert hashlib.sha256(downloaded).hexdigest()==digest,"Submitted PDF differs from approved PDF"
            page.screenshot(path=str(EVIDENCE/'entrega-confirmada-S4.png'),full_page=True)
            (EVIDENCE/'estado-final-S4.txt').write_text(final,encoding='utf-8')
            record={"verified_at":datetime.now(ZoneInfo('America/Mexico_City')).isoformat(),"activity_url":URL,"course_id":3482,"activity":"ACTIVIDAD S4","subject":"Derecho penal especial mexicano","filename":PDF.name,"bytes":PDF.stat().st_size,"sha256":digest,"platform_file_download_matches":True,"state":"Enviado para calificar","platform_submission_performed":True,"text":final}
            (EVIDENCE/'comprobante-envio-S4.json').write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
            print(json.dumps({"phase":"complete",**record},ensure_ascii=True),flush=True)
        browser.close()


if __name__ == "__main__":
    main()
