import os
import sys
import re
import json
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

c_slug = "responsabilidad-social-y-desarrollo-sustentable"
c_name = "Responsabilidad social y desarrollo sustentable"
subject_dir = PROJECT_ROOT / "UANL" / "ingeniero-agronomo" / c_slug
planeaciones_dir = subject_dir / f"planeaciones-{c_slug}"
recursos_dir = subject_dir / f"recursos-{c_slug}"
capturas_dir = planeaciones_dir / "capturas_nexus"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(viewport={"width": 1366, "height": 900})
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

    card = nexus_page.locator("mat-card.nx-mat-card-curso").filter(has_text=re.compile(rf"{re.escape(c_name)}", re.I)).locator(".text-ellipsis").first
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
    if rec_link.count() > 0:
        rec_link.first.click(force=True)
        nexus_page.wait_for_timeout(6000)
        nexus_page.screenshot(path=str(capturas_dir / "02_recursos_vista.png"), full_page=True)

        rec_text = nexus_page.locator("body").inner_text()
        with open(planeaciones_dir / "recursos_listado.txt", "w", encoding="utf-8") as f:
            f.write(rec_text)

        # Download any files listed in Recursos
        # Nexus lists resources in a table or list
        items = nexus_page.locator("table tbody tr, mat-list-item, .resource-item, .nx-resource-row")
        print(f"Items encontrados en recursos: {items.count()}")

        # Look for download links/buttons
        links = nexus_page.locator("a[href*='download'], a[href*='Recursos'], button:has-text('Descargar'), a:has(.fa-download), a:has(.fa-file)")
        print(f"Descargas detectadas: {links.count()}")

    browser.close()
    print("Recursos scrapeados con éxito!")
