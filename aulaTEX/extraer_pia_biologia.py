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
    screenshots_dir = out_dir / "capturas_nexus_pia"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    print(f"Iniciando sesion con usuario {USER}...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True, viewport={'width': 1280, 'height': 1200})
        page = context.new_page()

        print("Navegando a https://www.uanl.mx/enlinea/ ...")
        page.goto('https://www.uanl.mx/enlinea/', wait_until='domcontentloaded')
        page.wait_for_timeout(3000)

        frame = page.frame_locator('iframe')
        frame.locator('#tipo').select_option(label='Alumno')
        frame.locator('#cuenta').fill(USER)
        frame.locator('#pass').fill(PASS)
        frame.locator('button:has-text("Entrar")').click()
        print("Login enviado, esperando SIASE...")
        page.wait_for_timeout(10000)

        nexus_menu = page.locator('a[onmouseover*="nexus"]')
        if nexus_menu.count():
            nexus_menu.first.dispatch_event('mouseover')
            page.wait_for_timeout(1000)

        btn = page.locator('input[name="btnNexus"]')
        if not btn.count():
            btn = page.locator('a:has-text("Nexus"), input[value*="Nexus"]')

        with page.expect_popup() as popup_info:
            btn.first.click(force=True)
        nexus_page = popup_info.value

        print("Esperando Nexus...")
        nexus_page.wait_for_load_state('domcontentloaded')
        nexus_page.wait_for_timeout(10000)

        # Clic en Biología Celular
        bio = nexus_page.get_by_text('Biología celular', exact=False)
        for index in range(bio.count()):
            candidate = bio.nth(index)
            if candidate.is_visible():
                candidate.click()
                break
        nexus_page.wait_for_timeout(6000)

        # Navegar directamente a la ruta del Producto Integrador
        print("Navegando a la URL del PIA...")
        nexus_page.goto('https://plataformanexus.uanl.mx/?#/App/UnidadesAprendizaje/UA/Estructura/ProductoIntegrador/Contenidos', wait_until='domcontentloaded')
        nexus_page.wait_for_timeout(8000)

        # Full page screenshot de Contenidos
        print("Capturando Contenidos del PIA...")
        nexus_page.screenshot(path=str(screenshots_dir / "pia_contenidos_full.png"), full_page=True)

        contenidos_text = nexus_page.locator('body').inner_text()
        with open(out_dir / "PIA_contenidos_completo.txt", "w", encoding="utf-8") as f:
            f.write(contenidos_text)
        with open(out_dir / "PIA_contenidos_html.html", "w", encoding="utf-8") as f:
            f.write(nexus_page.content())

        # Sub-tabs del PIA: buscar dentro del contenedor principal
        main_container = nexus_page.locator('.container, .main-content, #main, div[ng-view], body')

        # Subtab Recursos del PIA
        print("Buscando sub-tab Recursos del PIA...")
        recursos_tab = nexus_page.locator('ul.nav a:has-text("Recursos"), .nav-tabs a:has-text("Recursos"), a.nav-link:has-text("Recursos")')
        if recursos_tab.count():
            for i in range(recursos_tab.count()):
                if recursos_tab.nth(i).is_visible():
                    recursos_tab.nth(i).click()
                    nexus_page.wait_for_timeout(5000)
                    nexus_page.screenshot(path=str(screenshots_dir / "pia_recursos_full.png"), full_page=True)
                    with open(out_dir / "PIA_recursos_completo.txt", "w", encoding="utf-8") as f:
                        f.write(nexus_page.locator('body').inner_text())

                    # Checar descargas
                    downloads = nexus_page.locator('i.fa-download, a[href*="download"], a[title*="Descargar"], button:has-text("Descargar")')
                    print(f"Descargas en Recursos del PIA: {downloads.count()}")
                    for d_i in range(downloads.count()):
                        d_el = downloads.nth(d_i)
                        if d_el.is_visible():
                            try:
                                with nexus_page.expect_download(timeout=8000) as dl:
                                    d_el.click(force=True)
                                download = dl.value
                                fn = download.suggested_filename or f"pia_recurso_{d_i}.bin"
                                download.save_as(str(out_dir / fn))
                                print(f"Descargado de Recursos del PIA: {fn}")
                            except Exception as e:
                                print(f"No descarga directa {d_i}: {e}")
                    break

        # Subtab Equipo del PIA
        print("Buscando sub-tab Equipo del PIA...")
        equipo_tab = nexus_page.locator('ul.nav a:has-text("Equipo"), .nav-tabs a:has-text("Equipo"), a.nav-link:has-text("Equipo")')
        if equipo_tab.count():
            for i in range(equipo_tab.count()):
                if equipo_tab.nth(i).is_visible():
                    equipo_tab.nth(i).click()
                    nexus_page.wait_for_timeout(5000)
                    nexus_page.screenshot(path=str(screenshots_dir / "pia_equipo_full.png"), full_page=True)
                    with open(out_dir / "PIA_equipo_completo.txt", "w", encoding="utf-8") as f:
                        f.write(nexus_page.locator('body').inner_text())
                    break

        # Subtab Entregas del PIA
        print("Buscando sub-tab Entregas del PIA...")
        entregas_tab = nexus_page.locator('ul.nav a:has-text("Entregas"), .nav-tabs a:has-text("Entregas"), a.nav-link:has-text("Entregas")')
        if entregas_tab.count():
            for i in range(entregas_tab.count()):
                if entregas_tab.nth(i).is_visible():
                    entregas_tab.nth(i).click()
                    nexus_page.wait_for_timeout(5000)
                    nexus_page.screenshot(path=str(screenshots_dir / "pia_entregas_full.png"), full_page=True)
                    with open(out_dir / "PIA_entregas_completo.txt", "w", encoding="utf-8") as f:
                        f.write(nexus_page.locator('body').inner_text())
                    break

        print("Finalizado con exito!")
        browser.close()

if __name__ == '__main__':
    main()
