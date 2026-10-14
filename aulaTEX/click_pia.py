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
        print("Entrando a Biología celular...")
        bio = nexus_page.get_by_text('Biología celular', exact=False)
        for index in range(bio.count()):
            candidate = bio.nth(index)
            if candidate.is_visible():
                candidate.click()
                break
        nexus_page.wait_for_timeout(6000)

        # Clic en Estructura del menu lateral
        print("Entrando a Estructura...")
        est_menu = nexus_page.locator('.sidebar-nav a:has-text("Estructura"), a:has-text("Estructura")')
        for i in range(est_menu.count()):
            if est_menu.nth(i).is_visible():
                est_menu.nth(i).click()
                break
        nexus_page.wait_for_timeout(6000)

        # En Estructura, buscar "Artículo de revisión bibliográfica"
        print("Buscando 'Artículo de revisión bibliográfica'...")
        pia_item = nexus_page.get_by_text('Artículo de revisión bibliográfica', exact=False)
        if pia_item.count() == 0:
            pia_item = nexus_page.get_by_text('Producto Integrador de Aprendizaje', exact=False)

        print(f"Items encontrados: {pia_item.count()}")
        clicked = False
        for idx in range(pia_item.count()):
            el = pia_item.nth(idx)
            el.scroll_into_view_if_needed()
            nexus_page.wait_for_timeout(500)
            if el.is_visible():
                print(f"Clickeando elemento {idx}...")
                el.click()
                clicked = True
                break

        if not clicked:
            print("No se pudo clickear directamente, forzando click en el contenedor...")
            nexus_page.locator('div:has-text("Artículo de revisión bibliográfica")').last.click(force=True)

        nexus_page.wait_for_timeout(8000)
        print(f"URL actual: {nexus_page.url}")

        # Guardar screenshot y contenido de Contenidos
        nexus_page.screenshot(path=str(screenshots_dir / "01_pia_contenidos_cargado.png"), full_page=True)
        with open(out_dir / "PIA_contenidos_completo.txt", "w", encoding="utf-8") as f:
            f.write(nexus_page.locator('body').inner_text())
        with open(out_dir / "PIA_contenidos_html.html", "w", encoding="utf-8") as f:
            f.write(nexus_page.content())

        # Ahora navegar por los subtabs: Recursos, Equipo, Entregas
        # Para no clickear el menu lateral izquierdo, buscamos solo los tabs que estan dentro del contenedor de la actividad
        subtabs = ["Recursos", "Equipo", "Entregas"]
        for stab in subtabs:
            print(f"Buscando sub-tab {stab} dentro de la actividad...")
            tab_locator = nexus_page.locator(f'.nav-tabs a:has-text("{stab}"), .nav a:has-text("{stab}"), a[role="tab"]:has-text("{stab}")')
            if tab_locator.count():
                for t_i in range(tab_locator.count()):
                    tab_el = tab_locator.nth(t_i)
                    if tab_el.is_visible():
                        print(f"Click en sub-tab {stab} ({t_i})...")
                        tab_el.click()
                        nexus_page.wait_for_timeout(5000)
                        nexus_page.screenshot(path=str(screenshots_dir / f"02_pia_subtab_{stab.lower()}.png"), full_page=True)
                        with open(out_dir / f"PIA_subtab_{stab.lower()}_text.txt", "w", encoding="utf-8") as f:
                            f.write(nexus_page.locator('body').inner_text())
                        with open(out_dir / f"PIA_subtab_{stab.lower()}_html.html", "w", encoding="utf-8") as f:
                            f.write(nexus_page.content())

                        if stab == "Recursos":
                            # Buscar descargas dentro del panel de recursos
                            dl_buttons = nexus_page.locator('i.fa-download, a[href*="download"], a[title*="Descargar"], button:has-text("Descargar")')
                            print(f"Descargas en subtab Recursos: {dl_buttons.count()}")
                            for dl_i in range(dl_buttons.count()):
                                dl_item = dl_buttons.nth(dl_i)
                                if dl_item.is_visible():
                                    try:
                                        with nexus_page.expect_download(timeout=6000) as d_info:
                                            dl_item.click(force=True)
                                        d_file = d_info.value
                                        fn = d_file.suggested_filename or f"recurso_pia_{dl_i}.bin"
                                        d_file.save_as(str(out_dir / fn))
                                        print(f"Archivo descargado: {fn}")
                                    except Exception as exc:
                                        print(f"No descarga directa en item {dl_i}: {exc}")
                        break

        print("Completado con exito!")
        browser.close()

if __name__ == '__main__':
    main()
