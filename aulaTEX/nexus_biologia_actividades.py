import os
import sys
import json
import time
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(r"c:\Users\Sysx\Documents\AulaTeX-Academico")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

def get_credentials():
    pin = os.getenv('AULATEX_MASTER_PIN', '5632').strip()
    vault = PlatformCredentialVault(default_vault_path(PROJECT_ROOT))
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

def main():
    USER, PASS = get_credentials()
    out_dir = PROJECT_ROOT / "UANL" / "ingeniero-agronomo" / "biologia-celular" / "planeaciones-biologia-celular"
    out_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir = out_dir / "capturas_nexus"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    print(f"Iniciando sesion con usuario {USER}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True, viewport={'width': 1280, 'height': 900})
        page = context.new_page()

        print("Navegando a https://www.uanl.mx/enlinea/ ...")
        page.goto('https://www.uanl.mx/enlinea/', wait_until='domcontentloaded')
        page.wait_for_timeout(3000)

        frame = page.frame_locator('iframe')
        frame.locator('#tipo').select_option(label='Alumno')
        frame.locator('#cuenta').fill(USER)
        frame.locator('#pass').fill(PASS)
        frame.locator('button:has-text("Entrar")').click()
        print("Login enviado, esperando respuesta de SIASE...")
        page.wait_for_timeout(10000)
        page.screenshot(path=str(screenshots_dir / "01_siase_logged.png"))

        nexus_menu = page.locator('a[onmouseover*="nexus"]')
        if nexus_menu.count():
            print("Activando menu de Nexus con mouseover...")
            nexus_menu.first.dispatch_event('mouseover')
            page.wait_for_timeout(1000)

        btn = page.locator('input[name="btnNexus"]')
        if not btn.count():
            print("Buscando enlaces directos a Nexus...")
            btn = page.locator('a:has-text("Nexus"), input[value*="Nexus"]')

        if not btn.count():
            page.screenshot(path=str(screenshots_dir / "error_no_nexus_btn.png"))
            raise RuntimeError('No se encontró el botón de Nexus en SIASE')

        print("Haciendo click en el boton de Nexus...")
        with page.expect_popup() as popup_info:
            btn.first.click(force=True)
        nexus_page = popup_info.value

        print("Esperando a que Nexus cargue...")
        nexus_page.wait_for_load_state('domcontentloaded')
        nexus_page.wait_for_timeout(12000)
        print(f"Nexus URL: {nexus_page.url}")
        nexus_page.screenshot(path=str(screenshots_dir / "02_nexus_home.png"))

        # Buscar "Biología celular"
        print("Buscando 'Biología celular'...")
        bio = nexus_page.get_by_text('Biología celular', exact=False)
        print(f"Coincidencias de 'Biología celular': {bio.count()}")

        clicked_bio = False
        for index in range(bio.count()):
            candidate = bio.nth(index)
            if candidate.is_visible():
                print(f"Haciendo click en coincidencia {index}: {candidate.inner_text()}")
                candidate.click()
                clicked_bio = True
                break

        if not clicked_bio:
            print("No se encontro boton visible, revisando todas las materias...")
            courses = nexus_page.locator('a, div, span').all_inner_texts()
            with open(out_dir / "nexus_home_text.txt", "w", encoding="utf-8") as f:
                f.write(nexus_page.locator('body').inner_text())

        nexus_page.wait_for_timeout(8000)
        print(f"Curso URL: {nexus_page.url}")
        nexus_page.screenshot(path=str(screenshots_dir / "03_curso_home.png"))

        # Navegar a Estructura si no estamos ahí
        print("Buscando seccion 'Estructura'...")
        estructura_btn = nexus_page.locator('a:has-text("Estructura"), span:has-text("Estructura"), li:has-text("Estructura")')
        if estructura_btn.count():
            for i in range(estructura_btn.count()):
                if estructura_btn.nth(i).is_visible():
                    estructura_btn.nth(i).click()
                    break
            nexus_page.wait_for_timeout(6000)
            nexus_page.screenshot(path=str(screenshots_dir / "04_estructura.png"))

        # Extraer todo el texto de Estructura
        with open(out_dir / "estructura_general_text.txt", "w", encoding="utf-8") as f:
            f.write(nexus_page.locator('body').inner_text())

        # Buscar "Producto Integrador" o PIA
        pia_btn = nexus_page.locator('a:has-text("Producto Integrador"), span:has-text("Producto Integrador"), div:has-text("Producto Integrador"), a:has-text("PIA")')
        if pia_btn.count():
            print(f"Encontrado PIA ({pia_btn.count()} elementos). Clickeando...")
            for i in range(pia_btn.count()):
                if pia_btn.nth(i).is_visible():
                    try:
                        pia_btn.nth(i).click()
                        break
                    except Exception as e:
                        print(f"Error clickeando pia_btn {i}: {e}")
            nexus_page.wait_for_timeout(6000)
            nexus_page.screenshot(path=str(screenshots_dir / "05_pia.png"))

        # Ahora navegar o extraer Contenidos, Recursos, Equipo, Entregas
        tabs = ["Contenidos", "Recursos", "Equipo", "Entregas"]
        for tab_name in tabs:
            tab = nexus_page.locator(f'a:has-text("{tab_name}"), button:has-text("{tab_name}"), li:has-text("{tab_name}")')
            if tab.count():
                for i in range(tab.count()):
                    if tab.nth(i).is_visible():
                        print(f"Navegando a tab {tab_name}...")
                        tab.nth(i).click()
                        nexus_page.wait_for_timeout(5000)
                        nexus_page.screenshot(path=str(screenshots_dir / f"06_tab_{tab_name.lower()}.png"))

                        # Extraer texto y HTML
                        with open(out_dir / f"tab_{tab_name.lower()}_text.txt", "w", encoding="utf-8") as f:
                            f.write(nexus_page.locator('body').inner_text())
                        with open(out_dir / f"tab_{tab_name.lower()}_html.html", "w", encoding="utf-8") as f:
                            f.write(nexus_page.content())

                        # Si es Recursos, checar si hay archivos para descargar
                        if tab_name == "Recursos":
                            download_icons = nexus_page.locator('i.fa-download, a[href*=".pdf"], a[href*=".docx"], a[href*=".doc"]')
                            print(f"Iconos/enlaces de descarga en Recursos: {download_icons.count()}")
                            for d_idx in range(download_icons.count()):
                                item = download_icons.nth(d_idx)
                                if item.is_visible():
                                    try:
                                        with nexus_page.expect_download(timeout=10000) as dl:
                                            item.click(force=True)
                                        download = dl.value
                                        filename = download.suggested_filename or f"recurso_{d_idx}.bin"
                                        save_path = out_dir / filename
                                        download.save_as(str(save_path))
                                        print(f"Descargado recurso: {save_path}")
                                    except Exception as exc:
                                        print(f"No se pudo descargar {d_idx}: {exc}")
                        break

        print("Scraping completado con exito.")
        browser.close()

if __name__ == '__main__':
    main()
