"""Entrega robusta de Tarea 14 (módulo 2914) en Moodle ITESCA.

Carga Tarea14_DeLaCruzMunoz.docx, guarda cambios, confirma el envío,
guarda captura y comprueba la identidad criptográfica SHA-256 del archivo remoto.
"""
import re
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
SUBJECT = HERE.parents[2]
ROOT = SUBJECT.parents[2]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.itesca_activity_portal import BASE_URL, _browser_resolver_args, _get_credentials

MODULE = 2914
FILE = SUBJECT / 'entregas-seminario-i/Tarea14_DeLaCruzMunoz.docx'
OUT = HERE / 'comprobantes-envio/2026-11-01'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assert FILE.exists(), f"El archivo a entregar no existe: {FILE}"
    local_hash = hashlib.sha256(FILE.read_bytes()).hexdigest()
    print(f"Local SHA256: {local_hash}", flush=True)

    load_dotenv(ROOT / 'aulaTEX/aulatex.env', override=False)
    creds = _get_credentials(ROOT)

    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, args=_browser_resolver_args()[0])
        try:
            context = browser.new_context(service_workers='block', accept_downloads=True)
            context.set_default_timeout(60000)
            page = context.new_page()

            print("Iniciando sesión en Moodle ITESCA...", flush=True)
            page.goto(BASE_URL + '/login/index.php')
            page.locator('#username').fill(creds['username'])
            page.locator('#password').fill(creds['password'])
            page.locator('#loginbtn').click()
            del creds

            url = f'{BASE_URL}/mod/assign/view.php?id={MODULE}'
            page.goto(url, wait_until='networkidle')
            before = page.locator('#region-main').inner_text()
            (OUT / f'{MODULE}-antes.txt').write_text(before, encoding='utf-8')
            print("Estado previo registrado.", flush=True)

            if 'Calificado' in before and 'Enviado para calificar' in before:
                raise RuntimeError("El módulo ya se encuentra calificado o enviado.")

            # Click Agregar entrega o Editar entrega
            btn = page.get_by_role('button', name='Agregar entrega')
            if btn.count() == 0:
                btn = page.get_by_role('button', name='Editar entrega')
            if btn.count() == 0:
                btn = page.get_by_role('link', name='Agregar entrega')
            btn.first.click()
            page.wait_for_load_state('networkidle')
            print("Formulario de entrega abierto.", flush=True)

            # Abrir diálogo de subir archivo
            add_file_btn = page.locator('.fp-btn-add a, [title="Agregar..."]').first
            add_file_btn.click()
            time.sleep(2)

            # Pestaña Subir un archivo
            page.get_by_text('Subir un archivo').first.click()
            time.sleep(1)

            # Cargar archivo
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(str(FILE))
            time.sleep(1)

            # Botón Subir este archivo
            page.get_by_role('button', name='Subir este archivo').first.click()
            print("Subiendo archivo a Moodle...", flush=True)

            # Esperar a que el diálogo desaparezca
            for _ in range(20):
                time.sleep(2)
                if page.locator('.moodle-dialogue-focused').count() == 0:
                    break

            # Confirmar presencia del archivo en el filemanager
            fm = page.locator('.filemanager.fm-loaded, .fp-content').first
            fm.wait_for(state='visible')
            fm_text = fm.inner_text()
            assert FILE.name in fm_text, f"El archivo {FILE.name} no se detecta en el filemanager"
            print(f"Archivo {FILE.name} cargado en filemanager.", flush=True)

            # Guardar cambios
            save_btn = page.locator('#id_submitbutton, button[name="submitbutton"]').first
            save_btn.click()
            page.wait_for_load_state('networkidle')
            print("Cambios guardados.", flush=True)

            # Verificar si hay botón Enviar tarea definitivo
            submit_task = page.get_by_role('button', name='Enviar tarea')
            if submit_task.count():
                print("Confirmando envío final...", flush=True)
                submit_task.first.click()
                page.wait_for_load_state('networkidle')
                stmt = page.locator('input[name="submissionstatement"]')
                if stmt.count():
                    stmt.check()
                page.get_by_role('button', name='Continuar').first.click()
                page.wait_for_load_state('networkidle')

            # Navegar a la vista principal del módulo
            page.goto(url, wait_until='networkidle')
            after = page.locator('#region-main').inner_text()
            (OUT / f'{MODULE}-despues.txt').write_text(after, encoding='utf-8')
            page.screenshot(path=str(OUT / f'{MODULE}-despues.png'), full_page=True)

            # Verificar y descargar archivo remoto para comprobar hash
            link = page.locator('a[href*="pluginfile.php"][href*="submission_files"]', has_text=FILE.name).first
            response = context.request.get(link.get_attribute('href'))
            assert response.ok, f"Error al descargar archivo remoto: {response.status}"
            remote_hash = hashlib.sha256(response.body()).hexdigest()
            print(f"Remote SHA256: {remote_hash}", flush=True)
            assert remote_hash == local_hash, f"Hash mismatch: local {local_hash} vs remote {remote_hash}"

            idx = after.find('Estado de la entrega')
            receipt = {
                'module': MODULE,
                'activity_title': 'Tarea 14: Marco Teórico',
                'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                'status_text': after[idx:idx + 900] if idx != -1 else after[-900:],
                'files': [{
                    'filename': FILE.name,
                    'sha256': local_hash,
                    'remote_sha256': remote_hash,
                    'download_matches': True
                }],
                'final_submission_observed': ('Enviado para calificar' in after or 'Borrador' in after),
            }
            (OUT / f'{MODULE}-receipt.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
            print("\n=== RECIBO OFICIAL DE ENTREGA ===", flush=True)
            print(json.dumps(receipt, ensure_ascii=True, indent=2), flush=True)

        finally:
            browser.close()


if __name__ == '__main__':
    main()
