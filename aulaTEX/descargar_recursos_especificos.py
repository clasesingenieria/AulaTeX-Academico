import os
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(r"c:\Users\Sysx\Documents\AulaTeX-Academico")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

def main():
    pin = os.getenv('AULATEX_MASTER_PIN', '5632').strip()
    vault = PlatformCredentialVault(default_vault_path(PROJECT_ROOT))
    accounts = vault.list_accounts(pin)
    account = next(item for item in accounts if item['institution'].casefold() == 'uanl')
    creds = vault.get_credentials(pin, account['id'])
    USER, PASS = creds['username'], creds['password']

    out_dir = PROJECT_ROOT / "UANL" / "ingeniero-agronomo" / "biologia-celular" / "planeaciones-biologia-celular"
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = [
        "Características del contenido del PIA",
        "GI_PIA",
        "EV4_",
        "EV5_",
        "GI_Evidencia 4",
        "GI_Evidencia 5"
    ]

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(accept_downloads=True, viewport={'width': 1280, 'height': 900})
        page = context.new_page()

        page.goto('https://www.uanl.mx/enlinea/', wait_until='domcontentloaded')
        page.wait_for_timeout(3000)
        frame = page.frame_locator('iframe')
        frame.locator('#tipo').select_option(label='Alumno')
        frame.locator('#cuenta').fill(USER)
        frame.locator('#pass').fill(PASS)
        frame.locator('button:has-text("Entrar")').click()
        page.wait_for_timeout(10000)

        nexus_menu = page.locator('a[onmouseover*="nexus"]')
        if nexus_menu.count():
            nexus_menu.first.dispatch_event('mouseover')
            page.wait_for_timeout(1000)

        btn = page.locator('input[name="btnNexus"]')
        with page.expect_popup() as popup_info:
            btn.first.click(force=True)
        nexus_page = popup_info.value
        nexus_page.wait_for_load_state('domcontentloaded')
        nexus_page.wait_for_timeout(10000)

        # Clic Biología celular
        bio = nexus_page.get_by_text('Biología celular', exact=False)
        for index in range(bio.count()):
            candidate = bio.nth(index)
            if candidate.is_visible():
                candidate.click()
                break
        nexus_page.wait_for_timeout(6000)

        # Clic Recursos en el menú lateral
        recursos_menu = nexus_page.locator('a:has-text("Recursos")')
        for i in range(recursos_menu.count()):
            if recursos_menu.nth(i).is_visible():
                recursos_menu.nth(i).click()
                break
        nexus_page.wait_for_timeout(6000)

        print("En pagina de Recursos. Buscando archivos objetivo...")

        for target in targets:
            items = nexus_page.locator(f'a:has-text("{target}")')
            count = items.count()
            print(f"Buscando '{target}': {count} encontrados")
            for idx in range(count):
                item = items.nth(idx)
                item.scroll_into_view_if_needed()
                # Buscar icono de descarga dentro del item
                dl_icon = item.locator('i.fa-download')
                click_target = dl_icon.first if dl_icon.count() else item
                try:
                    # Puede abrir popup o generar evento download
                    with nexus_page.expect_download(timeout=7000) as dl_info:
                        click_target.click(force=True)
                    dl = dl_info.value
                    fn = dl.suggested_filename
                    dl.save_as(str(out_dir / fn))
                    print(f"Descargado con éxito: {fn}")
                except Exception as exc:
                    print(f"No fue descarga directa para {target}[{idx}]: {exc}")
                    # Probar si abrió popup
                    try:
                        with nexus_page.context.expect_page(timeout=4000) as p_info:
                            click_target.click(force=True)
                        new_p = p_info.value
                        print(f"Abrio popup: {new_p.url}")
                        new_p.close()
                    except Exception:
                        pass

        browser.close()

if __name__ == '__main__':
    main()
