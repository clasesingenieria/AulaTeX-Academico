"""Submit the user-authorized S1 PDF and preserve the Moodle receipt."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import sys
from playwright.sync_api import sync_playwright
from aulaTEX.uas_course_inspect import BASE_URL, _credentials
from aulaTEX.aulatex.config import load_aulatex_env


def main():
    root = Path(__file__).resolve().parents[1]
    subject = root / "UAS/licenciatura-en-contaduria-uas/herramientas-digitales"
    pdf = subject / "entregas-herramientas-digitales/S1_MartinJonathanDeLaCruzMunoz.pdf"
    assert pdf.stat().st_size < 2000000
    load_aulatex_env()
    credentials = _credentials(root)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(BASE_URL + "/login/index.php", wait_until="domcontentloaded")
        page.locator("#username").fill(credentials["username"])
        page.locator("#password").fill(credentials["password"])
        page.locator("#loginbtn").click()
        page.wait_for_load_state("domcontentloaded")
        del credentials
        url = BASE_URL + "/mod/assign/view.php?id=50102"
        page.goto(url, wait_until="networkidle")
        if "--replace" in sys.argv or pdf.name not in page.locator("#region-main").inner_text():
            page.goto(url + "&action=editsubmission", wait_until="networkidle")
            if "--replace" in sys.argv:
                existing = page.locator(".filemanager").get_by_text(pdf.name, exact=True)
                if existing.count():
                    existing.click()
                    page.get_by_role("button", name="Eliminar", exact=True).click()
                    page.get_by_role("button", name="Sí", exact=True).click()
            page.locator(".fp-btn-add a").click()
            page.get_by_text("Subir un archivo", exact=True).click()
            page.locator('input[type="file"]').set_input_files(str(pdf))
            page.get_by_role("button", name="Subir este archivo", exact=True).click()
            if "--replace" in sys.argv:
                overwrite = page.get_by_role("button", name="Sobrescribir", exact=True)
                try:
                    overwrite.wait_for(state="visible", timeout=5000)
                except Exception:
                    pass
                else:
                    overwrite.click()
            page.locator(".filemanager").get_by_text(pdf.name, exact=True).wait_for()
            page.locator("#id_submitbutton").click()
            page.wait_for_load_state("networkidle")
        page.goto(url, wait_until="networkidle")
        text = page.locator("#region-main").inner_text()
        if "Enviado para calificar" not in text:
            submit = page.get_by_role("button", name="Enviar tarea", exact=True)
            if submit.count():
                submit.click()
                confirm = page.get_by_role("checkbox")
                if confirm.count() == 1:
                    confirm.check()
                page.get_by_role("button", name="Continuar", exact=True).click()
                page.goto(url, wait_until="networkidle")
                text = page.locator("#region-main").inner_text()
        assert pdf.name in text and "Enviado para calificar" in text, "Submission not confirmed"
        record = {"verified_utc":datetime.now(timezone.utc).isoformat(),"url":url,"filename":pdf.name,"bytes":pdf.stat().st_size,"sha256":hashlib.sha256(pdf.read_bytes()).hexdigest(),"state":"Enviado para calificar","text":text}
        notes = subject / "referencias-herramientas-digitales/notas-herramientas-digitales"
        (notes / "envio-S1-2026-10-22.json").write_text(json.dumps(record,ensure_ascii=False,indent=2),encoding="utf-8")
        print(json.dumps(record,ensure_ascii=True))
        browser.close()


if __name__ == "__main__":
    main()