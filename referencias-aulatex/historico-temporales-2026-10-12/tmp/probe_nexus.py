from playwright.sync_api import sync_playwright
import os

user = os.getenv('NEXUS_USER')
pwd = os.getenv('NEXUS_PASS')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    page.goto('https://www.uanl.mx/enlinea/', wait_until='domcontentloaded')
    frame = page.frame_locator('iframe')
    frame.locator('#tipo').select_option(label='Alumno')
    frame.locator('#cuenta').fill(user)
    frame.locator('#pass').fill(pwd)
    frame.locator('button:has-text("Entrar")').click()
    page.wait_for_timeout(12000)

    btn = page.locator('input[name="btnNexus"]')
    print('COUNT', btn.count())
    print('VISIBLE', btn.is_visible())
    if btn.count():
        btn.click(force=True)
        page.wait_for_timeout(8000)
        print('URL_AFTER_CLICK', page.url)
        for i, fr in enumerate(page.frames):
            content = fr.content()
            if 'Nexus' in content or 'btnNexus' in content or 'App/UnidadesAprendizaje' in content:
                print('=== FRAME', i, fr.url, '===')
                print(content[:4000])
    browser.close()
