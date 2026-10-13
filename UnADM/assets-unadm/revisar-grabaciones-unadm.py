from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.aulatex.config import load_aulatex_env
from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path
from playwright.sync_api import sync_playwright

HOST = 'aulavirtual.unadmexico.mx'
COURSES = [
    ('teoria-del-estado-y-constitucion', 3432, 208647),
    ('antecedentes-de-los-derechos-humanos', 3441, 208827),
    ('derecho-penal-especial-mexicano', 3482, 209647),
]


def main() -> None:
    load_aulatex_env()
    pin = os.environ.get('AULATEX_MASTER_PIN', '')
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    accounts = [account for account in vault.list_accounts(pin) if account['institution'].casefold() == 'unadm' and urlsplit(account['url']).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError('Cuenta UnADM no univoca')
    credentials = vault.get_credentials(pin, accounts[0]['id'])
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(45000)
        page.goto(accounts[0]['url'], wait_until='domcontentloaded')
        page.get_by_role('textbox', name=re.compile('Matr')).fill(credentials['username'])
        page.locator('input[type=password]').fill(credentials['password'])
        page.get_by_role('button', name=re.compile('Inicia sesi')).click()
        page.wait_for_url(lambda url: '/login/' not in urlsplit(url).path, wait_until='domcontentloaded')
        del credentials
        for slug, course, room in COURSES:
            room_url = f'https://{HOST}/mod/bigbluebuttonbn/view.php?id={room}'
            page.goto(room_url, wait_until='networkidle')
            rows = page.locator('tr').evaluate_all('rows=>rows.filter(row=>row.querySelector("a[href*=bbb_view]")).map(row=>({text:row.innerText,play:row.querySelector("a[href*=bbb_view]").href}))')
            result = {'consulta': datetime.now(ZoneInfo('America/Mexico_City')).isoformat(), 'curso': course, 'sala': room_url, 'grabaciones': [], 'sesion_en_vivo_iniciada': False, 'secretos_guardados': False}
            for row in rows:
                link = urlsplit(row['play'])
                if link.hostname != HOST or link.path != '/mod/bigbluebuttonbn/bbb_view.php':
                    continue
                item = {'descripcion_aula': re.sub(r'https?://\S+', '[enlace omitido]', row['text']), 'enlace_aula': room_url}
                try:
                    page.goto(row['play'], wait_until='networkidle')
                    try:
                        page.locator('video,audio').first.wait_for(state='attached', timeout=15000)
                    except Exception:
                        pass
                    item['dominio_reproductor'] = urlsplit(page.url).hostname
                    item['titulo_reproductor'] = page.title()
                    controls = page.locator('a,button').evaluate_all('items=>items.map(item=>({label:(item.innerText||item.getAttribute("aria-label")||item.title||"").trim(),download:item.hasAttribute("download")})).filter(item=>item.download||/download|descargar/i.test(item.label))')
                    item['controles_descarga'] = controls
                    item['medios_en_reproductor'] = page.locator('video,audio').count()
                    item['iframes'] = page.locator('iframe').count()
                    item['estado'] = 'medios y controles cargados; no acredita visionado' if item['medios_en_reproductor'] else 'pagina accesible; medios no verificados'
                    item['descarga'] = 'opcion visible; requiere revisar alcance' if controls else 'sin opcion explicita de descarga en controles inspeccionados'
                except Exception as error:
                    item['estado'] = 'reproductor no verificado'
                    item['clase_error'] = type(error).__name__
                result['grabaciones'].append(item)
            target = ROOT / 'UnADM/licenciatura-en-derecho-unadm' / f'{slug}-lde'
            output = target / f'referencias-{slug}/notas-{slug}/materiales-generales/control-grabaciones'
            output.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now(ZoneInfo('America/Mexico_City')).strftime('%Y-%m-%d-%H%M%S')
            (output / f'inventario-grabaciones-{stamp}.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(result, ensure_ascii=True))
        context.close()
        browser.close()


if __name__ == '__main__':
    main()