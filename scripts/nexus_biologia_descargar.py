from pathlib import Path
import os
import sys
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path


def get_credentials() -> tuple[str, str]:
    user = os.getenv('NEXUS_USER', '').strip()
    password = os.getenv('NEXUS_PASS', '')
    if user and password:
        return user, password

    pin = os.getenv('AULATEX_MASTER_PIN', '').strip()
    if not pin:
        raise RuntimeError('Falta AULATEX_MASTER_PIN para leer la cuenta UANL de la GUI')
    vault = PlatformCredentialVault(default_vault_path(Path.cwd()))
    accounts = vault.list_accounts(pin)
    account = next(
        (item for item in accounts
         if item['institution'].casefold() == 'uanl'
         and item['platform'].casefold() == 'nexus / siase'),
        None,
    )
    if account is None:
        raise RuntimeError('No existe una cuenta UANL / Nexus-SIASE en la GUI')
    credentials = vault.get_credentials(pin, account['id'])
    return credentials['username'], credentials['password']


USER, PASS = get_credentials()
OUT_DIR = Path('UANL/ingeniero-agronomo/biologia-celular')
OUT_DIR.mkdir(parents=True, exist_ok=True)


def save_download(page, selector: str, dest_dir: Path, label: str):
    els = page.locator(selector)
    if els.count() == 0:
        print(f'No se encontraron elementos para {label}')
        return
    for i in range(els.count()):
        el = els.nth(i)
        href = el.get_attribute('href')
        if href:
            with page.context.expect_page() as new_page_info:
                el.click(force=True)
            new_page = new_page_info.value
            new_page.wait_for_timeout(4000)
            new_page.close()
            continue
        with page.expect_download() as d:
            el.click(force=True)
        download = d.value
        filename = download.suggested_filename or f'{label}-{i}.bin'
        download.save_as(dest_dir / filename)
        print(f'Descargado: {dest_dir / filename}')


with sync_playwright() as p:
    headless = os.getenv('NEXUS_HEADLESS', '').strip().lower() in {'1', 'true', 'yes'}
    browser = p.chromium.launch(headless=headless)
    context = browser.new_context(accept_downloads=True)
    page = context.new_page()

    page.goto('https://www.uanl.mx/enlinea/', wait_until='domcontentloaded')
    frame = page.frame_locator('iframe')
    frame.locator('#tipo').select_option(label='Alumno')
    frame.locator('#cuenta').fill(USER)
    frame.locator('#pass').fill(PASS)
    frame.locator('button:has-text("Entrar")').click()
    page.wait_for_timeout(15000)

    # SIASE deja visible la pantalla de carreras tras el login. El menú lateral
    # activa Nexus con mouseover; no se debe seleccionar ninguna carrera.
    nexus_menu = page.locator('a[onmouseover*="nexus"]')
    if nexus_menu.count():
        nexus_menu.first.dispatch_event('mouseover')
        page.wait_for_timeout(1000)

    btn = page.locator('input[name="btnNexus"]')
    if not btn.count():
        raise RuntimeError('No se encontró el botón de Nexus en SIASE')

    # SIASE abre Nexus en una pestaña nueva con un token temporal. No sustituir
    # esa URL por una ruta interna: el token es el que conserva la autenticación.
    with page.expect_popup() as popup_info:
        btn.first.click(force=True)
    nexus_page = popup_info.value
    try:
        nexus_page.wait_for_load_state('domcontentloaded', timeout=15000)
    except Exception:
        print('Nexus mantiene la carga activa; se continúa con la vista disponible')
    nexus_page.wait_for_timeout(12000)
    print('NEXUS_URL=', nexus_page.url)
    print('NEXUS_TITLE=', nexus_page.title())
    print('NEXUS_VIEW=', nexus_page.locator('body').inner_text()[:5000])

    bio = nexus_page.get_by_text('Biología celular', exact=True)
    clicked_bio = False
    for index in range(bio.count()):
        candidate = bio.nth(index)
        if candidate.is_visible():
            candidate.click()
            clicked_bio = True
            break
    if clicked_bio:
        nexus_page.wait_for_timeout(8000)
        print('BIOLOGIA_URL=', nexus_page.url)
        print('BIOLOGIA_VIEW=', nexus_page.locator('body').inner_text()[:5000])
        resources = nexus_page.get_by_text('Recursos', exact=True)
        for index in range(resources.count()):
            candidate = resources.nth(index)
            if candidate.is_visible():
                candidate.click()
                nexus_page.wait_for_timeout(8000)
                print('RECURSOS_URL=', nexus_page.url)
                print('RECURSOS_VIEW=', nexus_page.locator('body').inner_text()[:6000])
                sample = nexus_page.get_by_text('COMPROMISOS.pdf', exact=True)
                if sample.count():
                    print('RECURSO_HTML=', sample.first.evaluate("el => el.parentElement.outerHTML")[:3000])
                    print('RECURSO_CONTENEDOR=', sample.first.evaluate("el => el.parentElement.parentElement.outerHTML")[:5000])
                    print('RECURSO_ANCESTROS=', sample.first.evaluate("""el => {
                        const result = [];
                        for (let node = el; node && result.length < 6; node = node.parentElement) {
                            result.push({tag: node.tagName, className: node.className,
                                attributes: Array.from(node.attributes).map(attribute => attribute.name)
                                    .filter(name => name.startsWith('ng-') || name.includes('click'))});
                        }
                        return JSON.stringify(result);
                    }"""))
                if os.getenv('NEXUS_DIAGNOSTIC') == '1':
                    icon = nexus_page.locator('i.fa-download').first
                    try:
                        with nexus_page.context.expect_page(timeout=5000) as page_info:
                            icon.click(force=True)
                        probe_page = page_info.value
                        print('DESCARGA_ABRIO_PAGINA=', probe_page.url)
                        probe_page.close()
                    except Exception as exc:
                        print('DESCARGA_SIN_PAGINA=', type(exc).__name__)
                    browser.close()
                    raise SystemExit(0)
                break
    else:
        print('No se encontró el texto de la materia. VISTA=', nexus_page.locator('body').inner_text()[:3000])

    # intento de descarga por enlaces de recurso visibles
    selectors = [
        'a[href*=".pdf"], a[href*=".doc"], a[href*=".docx"], a[href*=".ppt"], a[href*=".pptx"], a[href*=".xls"], a[href*=".zip"], a[href*=".rar"], a[title*="Descargar"], a[title*="download"], button[title*="Descargar"]'
    ]
    download_icons = nexus_page.locator('i.fa-download')
    for index in range(download_icons.count()):
        icon = download_icons.nth(index)
        if not icon.is_visible():
            continue
        try:
            with nexus_page.expect_download(timeout=20000) as download_info:
                icon.click(force=True)
            download = download_info.value
            filename = download.suggested_filename or f'recurso_{index}.bin'
            save_path = OUT_DIR / filename
            if save_path.exists():
                save_path = OUT_DIR / f'{index}_{filename}'
            download.save_as(str(save_path))
            print(f'Descargado: {save_path}')
        except Exception as exc:
            print(f'No se pudo descargar el recurso #{index}: {type(exc).__name__}')

    for selector in selectors:
        items = nexus_page.locator(selector)
        if items.count() == 0:
            continue
        for i in range(items.count()):
            item = items.nth(i)
            with nexus_page.expect_download() as d:
                try:
                    item.click(force=True)
                except Exception:
                    item.evaluate('(el) => el.click()')
            download = d.value
            filename = download.suggested_filename or f'recurso_{i}.bin'
            save_path = OUT_DIR / filename
            download.save_as(str(save_path))
            print(f'Descargado: {save_path}')

    print('ARCHIVOS EN CARPETA:')
    for f in sorted(OUT_DIR.iterdir()):
        print(' -', f.name)

    browser.close()
