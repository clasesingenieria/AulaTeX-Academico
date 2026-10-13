from playwright.sync_api import sync_playwright
import os

USER = os.getenv('NEXUS_USER')
PASS = os.getenv('NEXUS_PASS')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page()
    print('STEP1 goto enlinea')
    page.goto('https://www.uanl.mx/enlinea/', wait_until='domcontentloaded')
    print('URL1', page.url)
    frame = page.frame_locator('iframe')
    frame.locator('#tipo').select_option(label='Alumno')
    frame.locator('#cuenta').fill(USER)
    frame.locator('#pass').fill(PASS)
    frame.locator('button:has-text("Entrar")').click()
    page.wait_for_timeout(15000)
    print('URL2', page.url)

    btn = page.locator('input[name="btnNexus"]')
    print('BTN COUNT', btn.count())
    if btn.count():
        btn.click(force=True)
        page.wait_for_timeout(8000)
        print('URL3', page.url)

    print('TRY GOTO NEXUS')
    page.goto('https://plataformanexus.uanl.mx/#/App/UnidadesAprendizaje/UA/Recursos', wait_until='domcontentloaded')
    page.wait_for_timeout(10000)
    print('URL4', page.url)
    print('TITLE', page.title())
    body = page.locator('body').inner_text()[:1500]
    print(body)
    browser.close()
