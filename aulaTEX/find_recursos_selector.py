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

    # Let's inspect Responsabilidad Social
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

    # Find element containing "Objetivo de la UA RSyDS.ppsx"
    target = nexus_page.locator(':has-text("Objetivo de la UA RSyDS.ppsx")')
    print("Target count:", target.count())
    if target.count() > 0:
        last_el = target.last
        print("Tag:", last_el.evaluate("el => el.tagName"))
        print("Outer HTML snippet:", last_el.evaluate("el => el.parentElement.outerHTML")[:600])

    # Check all clickable elements in main content
    content_links = nexus_page.locator(".content a, .main a, mat-sidenav-content a, mat-card a, i.fa, mat-icon")
    print(f"Total icons/links in content: {content_links.count()}")
    for i in range(min(content_links.count(), 20)):
        el = content_links.nth(i)
        tag = el.evaluate("el => el.tagName")
        cls = el.get_attribute("class")
        txt = el.inner_text().strip()
        print(f"Item {i}: tag={tag}, class={cls}, text='{txt}'")

    browser.close()
