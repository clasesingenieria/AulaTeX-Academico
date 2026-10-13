from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from scripts.aulatex.config import load_aulatex_env
from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path
from playwright.sync_api import sync_playwright

HOST = 'aulavirtual.unadmexico.mx'
MODULES = {
    214812: ('teoria-del-estado-y-constitucion', '2026_TeoriaEstado_S2_Martin Jonathan de la Cruz.pdf', 'f1fa4a382437983fbc408db57f436a8b55d8da32dd6dfe9032e4a94c0c569f22'),
    215277: ('derecho-penal-especial-mexicano', 'Actividad-S2-Cuadro-comparativo-robo-Martin-Jonathan-de-la-Cruz.pdf', '247260c59fdb334ffd90dce6f1fe210a4d50d6c074a5f030f418a994e6b6ba67'),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('module', type=int, choices=MODULES)
    parser.add_argument('--submit', action='store_true')
    parser.add_argument('--probe-upload', action='store_true')
    args = parser.parse_args()
    slug, name, expected = MODULES[args.module]
    target = ROOT / 'UnADM/licenciatura-en-derecho-unadm' / f'{slug}-lde'
    file = target / 'Entregas' / name
    if args.submit and hashlib.sha256(file.read_bytes()).hexdigest() != expected:
        raise RuntimeError('La version revisada no coincide con el archivo a enviar')
    output = target / f'referencias-{slug}/notas-{slug}' / ('actividad-02-linea-de-tiempo' if args.module == 214812 else 'actividad-02-cuadro-comparativo-robo') / 'comprobantes-envio/2026-10-11'
    output.mkdir(parents=True, exist_ok=True)
    load_aulatex_env()
    pin = os.environ.get('AULATEX_MASTER_PIN', '')
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    accounts = [account for account in vault.list_accounts(pin) if account['institution'].casefold() == 'unadm' and urlsplit(account['url']).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError('Cuenta no univoca')
    credentials = vault.get_credentials(pin, accounts[0]['id'])
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto(accounts[0]['url'], wait_until='domcontentloaded')
        page.get_by_role('textbox', name=re.compile('Matr')).fill(credentials['username'])
        page.locator('input[type=password]').fill(credentials['password'])
        page.get_by_role('button', name=re.compile('Inicia sesi')).click()
        page.wait_for_url(lambda url: '/login/' not in urlsplit(url).path, wait_until='domcontentloaded')
        del credentials
        url = f'https://{HOST}/mod/assign/view.php?id={args.module}'
        page.goto(url, wait_until='domcontentloaded')
        before = page.locator('#region-main').inner_text()
        (output / 'estado-previo.txt').write_text(before, encoding='utf-8')
        if 'Enviado para calificar' in before:
            verify_submission(context, page, output, args.module, url, name, expected, before)
            context.close()
            browser.close()
            return
        if 'Borrador' in before and args.submit:
            page.get_by_role('button', name=re.compile('Enviar tarea', re.I)).click()
            page.wait_for_load_state('networkidle')
            confirmation = page.locator('#region-main')
            print(json.dumps({'confirmacion':confirmation.inner_text()},ensure_ascii=True))
            for checkbox in confirmation.locator('input[type=checkbox]:visible').all():
                checkbox.check()
            confirmation.get_by_role('button', name=re.compile('Continuar', re.I)).click()
            page.wait_for_load_state('networkidle')
            page.goto(url, wait_until='domcontentloaded')
            before = page.locator('#region-main').inner_text()
        if 'Enviado para calificar' in before:
            after = before
        elif 'Aun no se ha hecho ninguna tarea' not in before:
            raise RuntimeError('Estado no reconocido; no reemplazar')
        if 'Enviado para calificar' in before:
            verify_submission(context, page, output, args.module, url, name, expected, before)
            context.close()
            browser.close()
            return
        page.get_by_role('button', name=re.compile('A.adir env.o', re.I)).click()
        page.wait_for_load_state('networkidle')
        if not args.submit and not args.probe_upload:
            elements = page.locator('#region-main button, #region-main input, #region-main a').evaluate_all('items=>items.map(item=>({tag:item.tagName,type:item.type,text:item.innerText,title:item.title,aria:item.getAttribute("aria-label"),name:item.name})).filter(item=>item.text||item.type||item.title)')
            print(json.dumps({'modulo':args.module,'texto':page.locator('#region-main').inner_text(),'elementos':elements}, ensure_ascii=True))
            context.close()
            browser.close()
            return
        page.locator('.fp-btn-add a').click()
        dialog = page.locator('.moodle-dialogue-focused')
        dialog.get_by_text('Subir un archivo', exact=True).click()
        page.wait_for_load_state('networkidle')
        upload_input = dialog.locator('input[type=file]')
        for attempt in range(3):
            upload_input.set_input_files({'name': name, 'mimeType': 'application/pdf', 'buffer': file.read_bytes()})
            selected_files = upload_input.evaluate('element=>Array.from(element.files).map(file=>({name:file.name,size:file.size}))')
            if len(selected_files) == 1 and selected_files[0]['size'] == file.stat().st_size:
                break
            page.wait_for_load_state('networkidle')
        if len(selected_files) != 1:
            raise RuntimeError('Selector no conserva archivo; no pulsar subir')
        responses = []
        def inspect_response(response):
            if 'repository_ajax.php' in response.url and response.request.method == 'POST':
                try:
                    data = response.json()
                    responses.append({key: value for key, value in data.items() if key in ('error', 'errorcode', 'file', 'filename', 'event')})
                except Exception:
                    responses.append({'error': 'respuesta no JSON'})
        page.on('response', inspect_response)
        dialog.get_by_role('button', name=re.compile('Subir este archivo', re.I)).click()
        page.wait_for_load_state('networkidle')
        if args.probe_upload:
            print(json.dumps({'input_files':selected_files,'respuestas':responses,'dialogo':dialog.inner_text() if dialog.is_visible() else 'cerrado','gestores':page.locator('.filemanager').all_inner_texts(),'dialogos':page.locator('[role=dialog]').all_inner_texts()},ensure_ascii=True))
            context.close()
            browser.close()
            return
        result = next((item for item in responses if item.get('error')), {})
        print(json.dumps({'subida': {key: value for key, value in result.items() if key in ('error', 'errorcode', 'file', 'filename')}}, ensure_ascii=True))
        page.wait_for_load_state('networkidle')
        if result.get('error'):
            raise RuntimeError('Carga rechazada por aula')
        print(json.dumps({'gestores':page.locator('.filemanager').all_inner_texts(),'dialogo':dialog.inner_text() if dialog.is_visible() else 'cerrado'},ensure_ascii=True))
        page.locator('.filemanager.w-100').get_by_text(name, exact=True).wait_for(state='visible')
        page.get_by_role('button', name=re.compile('Guardar cambios', re.I)).click()
        page.wait_for_load_state('networkidle')
        saved = page.locator('#region-main').inner_text()
        (output / 'despues-guardar.txt').write_text(saved, encoding='utf-8')
        final_button = page.get_by_role('button', name=re.compile('Enviar tarea', re.I))
        if final_button.count():
            final_button.click()
            page.wait_for_load_state('networkidle')
            statement = page.locator('#region-main input[type=checkbox]:visible')
            for number in range(statement.count()):
                statement.nth(number).check()
            page.get_by_role('button', name=re.compile('Continuar', re.I)).click()
            page.wait_for_load_state('networkidle')
        page.goto(url, wait_until='domcontentloaded')
        after = page.locator('#region-main').inner_text()
        verify_submission(context, page, output, args.module, url, name, expected, after)
        context.close()
        browser.close()


def verify_submission(context, page, output, module, url, name, expected, after):
        if 'Enviado para calificar' not in after:
            raise RuntimeError('No se confirma envio final')
        links = page.locator('.submissionstatustable a[href*="pluginfile.php"]').evaluate_all('items=>items.map(item=>({name:item.innerText,url:item.href}))')
        selected = [link for link in links if link['name'].strip() == name]
        if len(selected) != 1:
            raise RuntimeError('Archivo remoto no univoco')
        response = context.request.get(selected[0]['url'])
        payload = response.body()
        remote_hash = hashlib.sha256(payload).hexdigest()
        if not response.ok or remote_hash != expected:
            raise RuntimeError('Archivo remoto no coincide')
        (output / name).write_bytes(payload)
        (output / 'estado-final.txt').write_text(after, encoding='utf-8')
        page.locator('#region-main').screenshot(path=str(output / 'estado-final.png'))
        receipt = {'consulta':datetime.now(ZoneInfo('America/Mexico_City')).isoformat(),'modulo':module,'url':url,'estado':'Enviado para calificar','archivo':name,'sha256_local':expected,'sha256_remoto':remote_hash,'texto_estado':after,'autorizacion':'Usuario autorizo realizar entregas S2 el 11 de octubre de 2026'}
        (output / 'recibo.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'modulo':module,'estado':receipt['estado'],'archivo':name,'sha256_remoto':remote_hash},ensure_ascii=True))


if __name__ == '__main__':
    main()