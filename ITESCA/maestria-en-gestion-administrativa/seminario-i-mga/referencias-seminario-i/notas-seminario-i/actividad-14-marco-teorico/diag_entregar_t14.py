"""Diagnostico del formulario de entrega en Moodle ITESCA para modulo 2914."""
from pathlib import Path
import sys
import time

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[6]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.itesca_activity_portal import BASE_URL, _browser_resolver_args, _get_credentials

MODULE = 2914
SUBJECT = Path(__file__).resolve().parents[3]
FILE = SUBJECT / 'entregas-seminario-i/Tarea14_DeLaCruzMunoz.docx'
OUT = Path(__file__).resolve().parent / 'comprobantes-envio/2026-11-01'
OUT.mkdir(parents=True, exist_ok=True)

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
        print("Página principal cargada:", page.title())
        
        # Click Agregar entrega
        add_btn = page.get_by_role('button', name='Agregar entrega')
        if add_btn.count() == 0:
            add_btn = page.get_by_role('link', name='Agregar entrega')
        print("Botón Agregar entrega:", add_btn.count())
        add_btn.first.click()
        page.wait_for_load_state('networkidle')
        page.screenshot(path=str(OUT / 'diag-1-form.png'), full_page=True)
        print("Formulario cargado. Título:", page.title())

        # Inspect filemanager
        fm = page.locator('.filemanager, .fitem_ffilemanager')
        print("Filemanager count:", fm.count())
        
        # Open filepicker
        add_file_btn = page.locator('.fp-btn-add a, [title="Agregar..."]')
        print("Add file button count:", add_file_btn.count())
        add_file_btn.first.click()
        time.sleep(2)
        page.screenshot(path=str(OUT / 'diag-2-dialog.png'))

        # Select upload file
        upload_tab = page.get_by_text('Subir un archivo')
        print("Upload tab count:", upload_tab.count())
        upload_tab.first.click()
        time.sleep(1)

        # File input
        file_input = page.locator('input[type="file"]')
        print("File inputs count:", file_input.count())
        file_input.first.set_input_files(str(FILE))
        time.sleep(1)
        page.screenshot(path=str(OUT / 'diag-3-selected.png'))

        # Submit upload
        submit_upload = page.get_by_role('button', name='Subir este archivo')
        print("Submit upload count:", submit_upload.count())
        submit_upload.first.click()
        
        print("Esperando que termine la subida...")
        # Wait up to 30s
        for _ in range(15):
            time.sleep(2)
            d_visible = page.locator('.moodle-dialogue-focused').count()
            print(f"Dialog visible: {d_visible}")
            if d_visible == 0:
                break
        page.screenshot(path=str(OUT / 'diag-4-after-upload.png'))

        fm_text = page.locator('.filemanager').inner_text()
        print("Filemanager innerText tras subida:\n", fm_text)
        
        if FILE.name in fm_text:
            print("¡Archivo detectado en el filemanager con éxito!")
            # Save changes
            page.locator('#id_submitbutton, button[name="submitbutton"]').first.click()
            page.wait_for_load_state('networkidle')
            print("Cambios guardados. URL actual:", page.url)
            page.screenshot(path=str(OUT / 'diag-5-saved.png'), full_page=True)
            
            # Check for final submit button
            submit_task = page.get_by_role('button', name='Enviar tarea')
            if submit_task.count():
                print("Botón 'Enviar tarea' presente. Haciendo clic...")
                submit_task.first.click()
                page.wait_for_load_state('networkidle')
                stmt = page.locator('input[name="submissionstatement"]')
                if stmt.count():
                    stmt.check()
                page.get_by_role('button', name='Continuar').first.click()
                page.wait_for_load_state('networkidle')
            
            page.goto(url, wait_until='networkidle')
            final_text = page.locator('#region-main').inner_text()
            (OUT / f'{MODULE}-despues.txt').write_text(final_text, encoding='utf-8')
            page.screenshot(path=str(OUT / f'{MODULE}-despues.png'), full_page=True)
            print("Entrega completada. Texto final:\n", final_text[:500])
        else:
            print("El archivo no apareció en el filemanager. Revisa diag-4-after-upload.png")

    finally:
        browser.close()
