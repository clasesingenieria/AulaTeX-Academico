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

    c_name = "Responsabilidad social y desarrollo sustentable"
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

    nexus_page.locator('a:has-text("Recursos")').first.click(force=True)
    nexus_page.wait_for_timeout(6000)

    archive_items = nexus_page.locator('a.d-flex.py-2:has-text("Archivo")')
    print(f"Total archive items found: {archive_items.count()}")
    for i in range(archive_items.count()):
        item = archive_items.nth(i)
        txt = item.inner_text().replace('\n', ' ')
        href = item.get_attribute("href")
        print(f"Item {i}: text='{txt}', href='{href}'")

    browser.close()
