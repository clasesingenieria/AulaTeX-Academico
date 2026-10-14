import os
import sys
import re
from pathlib import Path
from playwright.sync_api import sync_playwright

PROJECT_ROOT = Path(r"c:\Users\Sysx\Documents\AulaTeX-Academico")
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

pin = "5632"
vault = PlatformCredentialVault(default_vault_path(PROJECT_ROOT))
acc = next(a for a in vault.list_accounts(pin) if a["institution"].casefold() == "uanl" and a["platform"].casefold() == "nexus / siase")
creds = vault.get_credentials(pin, acc["id"])
USER, PASS = creds["username"], creds["password"]

COURSES = [
    {"name": "Responsabilidad social y desarrollo sustentable", "slug": "responsabilidad-social-y-desarrollo-sustentable"},
    {"name": "Cálculo integral", "slug": "calculo-integral"},
    {"name": "Ética y cultura de la legalidad", "slug": "etica-y-cultura-de-la-legalidad"},
    {"name": "Álgebra lineal", "slug": "algebra-lineal"},
    {"name": "Física", "slug": "fisica"},
]

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(accept_downloads=True, viewport={"width": 1366, "height": 900})
    page = context.new_page()
    page.goto("https://www.uanl.mx/enlinea/", wait_until="domcontentloaded")
    page.wait_for_timeout(3000)
    frame = page.frame_locator("iframe")
    frame.locator("#tipo").select_option(label="Alumno")
    frame.locator("#cuenta").fill(USER)
    frame.locator("#pass").fill(PASS)
    frame.locator('button:has-text("Entrar")').click()
    page.wait_for_timeout(10000)

    nexus_menu = page.locator('a[onmouseover*="nexus"]')
    if nexus_menu.count():
        nexus_menu.first.dispatch_event("mouseover")
        page.wait_for_timeout(1000)

    btn = page.locator('input[name="btnNexus"], a:has-text("Nexus"), input[value*="Nexus"]')
    with page.expect_popup() as popup_info:
        btn.first.click(force=True)
    nexus_page = popup_info.value
    nexus_page.wait_for_load_state("domcontentloaded")
    nexus_page.wait_for_timeout(12000)

    dashboard_url = "https://plataformanexus.uanl.mx/?#/App/UnidadesAprendizaje"

    for course in COURSES:
        c_name = course["name"]
        c_slug = course["slug"]
        print(f"\n========================================================")
        print(f">>> DESCARGANDO RECURSOS: {c_name} ({c_slug})")
        print(f"========================================================")

        target_dir = PROJECT_ROOT / "UANL" / "ingeniero-agronomo" / c_slug / f"recursos-{c_slug}"
        target_dir.mkdir(parents=True, exist_ok=True)

        nexus_page.goto(dashboard_url, wait_until="domcontentloaded")
        nexus_page.wait_for_timeout(5000)

        card = nexus_page.locator("mat-card.nx-mat-card-curso").filter(has_text=re.compile(rf"{re.escape(c_name)}", re.I)).locator(".text-ellipsis").first
        if not card.count():
            print(f"No se encontró tarjeta para {c_name}")
            continue

        card.click()
        nexus_page.wait_for_timeout(5000)

        # Dismiss dialog
        dialogs = nexus_page.locator("mat-dialog-container, .mat-dialog-container, [role='dialog']")
        if dialogs.count() > 0:
            buttons = dialogs.first.locator("button")
            if buttons.count() > 0:
                buttons.first.click()
            else:
                nexus_page.keyboard.press("Escape")
            nexus_page.wait_for_timeout(2000)

        # Click Recursos
        rec_link = nexus_page.locator('a:has-text("Recursos")')
        if not rec_link.count():
            print("No se encontró link de Recursos")
            continue
        rec_link.first.click(force=True)
        nexus_page.wait_for_timeout(5000)

        archive_items = nexus_page.locator('a.d-flex.py-2:has-text("Archivo")')
        count = archive_items.count()
        print(f"Archivos descargables encontrados: {count}")

        for i in range(count):
            item = archive_items.nth(i)
            try:
                title_el = item.locator("div.line-height-initial.text-ellipsis.line-1")
                title = title_el.nth(1).inner_text().strip() if title_el.count() > 1 else f"recurso_{i+1}"
            except Exception:
                title = f"recurso_{i+1}"

            print(f"[{i+1}/{count}] Descargando: {title}")
            try:
                with nexus_page.expect_download(timeout=12000) as download_info:
                    item.click()
                download = download_info.value
                fname = download.suggested_filename or title
                # Limpiar caracteres inválidos
                fname = re.sub(r'[\\/*?:"<>|]', '_', fname)
                out_path = target_dir / fname
                download.save_as(str(out_path))
                print(f"   -> Guardado: {out_path.name} ({out_path.stat().st_size} bytes)")
            except Exception as e:
                print(f"   -> Omitido o no descargable {title}: {e}")
            nexus_page.wait_for_timeout(1000)

    browser.close()
    print("\n>>> TODOS LOS RECURSOS DESCARGADOS CON ÉXITO!")
