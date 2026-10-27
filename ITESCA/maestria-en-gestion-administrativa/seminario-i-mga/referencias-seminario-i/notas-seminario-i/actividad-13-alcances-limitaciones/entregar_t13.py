"""Entrega T13 (módulo 2913) en Moodle ITESCA: un solo Word acumulativo.

Usa la bóveda de credenciales de AulaTeX. Guarda recibo, estado y captura en
comprobantes-envio/2026-10-25/ y verifica la descarga remota por SHA-256.
"""
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SUBJECT = HERE.parents[2]
ROOT = SUBJECT.parents[2]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.itesca_activity_portal import BASE_URL, _browser_resolver_args, _get_credentials  # noqa: E402

MODULE = 2913
FILE = SUBJECT / 'entregas-seminario-i/Tarea13_DeLaCruzMunoz.docx'
OUT = HERE / 'comprobantes-envio/2026-10-25'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    local_hash = hashlib.sha256(FILE.read_bytes()).hexdigest()
    load_dotenv(ROOT / 'aulaTEX/aulatex.env', override=False)
    creds = _get_credentials(ROOT)
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, args=_browser_resolver_args()[0])
        try:
            context = browser.new_context(service_workers='block', accept_downloads=True)
            context.set_default_timeout(60000)
            page = context.new_page()
            page.goto(BASE_URL + '/login/index.php')
            page.locator('#username').fill(creds['username'])
            page.locator('#password').fill(creds['password'])
            page.locator('#loginbtn').click()
            del creds
            url = f'{BASE_URL}/mod/assign/view.php?id={MODULE}'
            page.goto(url, wait_until='networkidle')
            before = page.locator('#region-main').inner_text()
            (OUT / f'{MODULE}-antes.txt').write_text(before, encoding='utf-8')
            if 'Todavía no se han realizado envíos' not in before:
                raise RuntimeError('El módulo ya registra un envío; no se sobrescribe automáticamente')
            page.get_by_role('button', name='Agregar entrega', exact=True).click()
            page.wait_for_load_state('networkidle')
            page.get_by_title('Agregar...', exact=True).first.click()
            page.get_by_text('Subir un archivo', exact=True).click()
            upload = page.locator('.moodle-dialogue-focused input[name=repo_upload_file]')
            upload.wait_for(state='visible')
            upload.set_input_files(str(FILE))
            page.get_by_role('button', name='Subir este archivo', exact=True).click()
            page.locator('.filemanager .fp-filename', has_text=FILE.name).first.wait_for()
            page.get_by_role('button', name='Guardar cambios', exact=True).click()
            page.wait_for_load_state('networkidle')
            submit = page.get_by_role('button', name='Enviar tarea')
            if submit.count():
                submit.first.click()
                page.wait_for_load_state('networkidle')
                statement = page.locator('input[name=submissionstatement]')
                if statement.count():
                    statement.check()
                page.get_by_role('button', name='Continuar').first.click()
                page.wait_for_load_state('networkidle')
            page.goto(url, wait_until='networkidle')
            after = page.locator('#region-main').inner_text()
            (OUT / f'{MODULE}-despues.txt').write_text(after, encoding='utf-8')
            page.screenshot(path=str(OUT / f'{MODULE}-despues.png'), full_page=True)
            link = page.locator('a[href*="pluginfile.php"][href*="submission_files"]', has_text=FILE.name).first
            response = context.request.get(link.get_attribute('href'))
            remote_hash = hashlib.sha256(response.body()).hexdigest()
            idx = after.find('Estado de la entrega')
            receipt = {
                'module': MODULE,
                'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'status_text': after[idx:idx + 900] if idx != -1 else after[-900:],
                'files': [{'filename': FILE.name, 'sha256': local_hash, 'remote_sha256': remote_hash,
                           'download_matches': remote_hash == local_hash}],
                'final_submission_observed': 'Enviado para calificar' in after,
            }
            (OUT / f'{MODULE}-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(receipt, ensure_ascii=True, indent=2))
        finally:
            browser.close()


if __name__ == '__main__':
    main()

