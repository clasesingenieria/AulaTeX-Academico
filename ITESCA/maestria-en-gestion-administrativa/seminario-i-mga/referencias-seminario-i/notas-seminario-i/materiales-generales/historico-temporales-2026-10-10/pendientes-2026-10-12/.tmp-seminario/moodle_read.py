import json, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

OUT = ROOT / 'ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/anteproyecto/evidencias/moodle-2026-09-27'
OUT.mkdir(parents=True, exist_ok=True)
pin = next(v for k,v in os.environ.items() if k.lower() == 'aulatex_master_pin')
vault = PlatformCredentialVault(default_vault_path(ROOT))
account = next(a for a in vault.list_accounts(pin) if a['institution']=='ITESCA')
credentials = vault.get_credentials(pin, account['id'])
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(accept_downloads=True, ignore_https_errors=True)
    page = context.new_page()
    page.goto(credentials['url'])
    page.locator('#username').fill(credentials['username'])
    page.locator('#password').fill(credentials['password'])
    page.locator('#loginbtn').click()
    page.wait_for_load_state('domcontentloaded')
    print('AUTH', page.url)
    if '/login/' in page.url:
        raise RuntimeError('Login not completed')
    for mid in ([int(a) for a in sys.argv[1:]] or [2907,2908,2909]):
        page.goto(f'https://cursos3.e-itesca.edu.mx/mod/assign/view.php?id={mid}')
        body=page.locator('body').inner_text()
        (OUT/f'{mid}.txt').write_text(body, encoding='utf-8')
        links=page.locator('a[href]').evaluate_all('(els)=>els.map(e=>({text:e.innerText,url:e.href}))')
        (OUT/f'{mid}-links.json').write_text(json.dumps(links,ensure_ascii=False,indent=2),encoding='utf-8')
        print('MODULE',mid,'saved',flush=True)
        for link in links:
            if '/pluginfile.php/' in link['url'] and any(x in link['url'].lower() for x in ['.docx','.pdf']):
                import urllib.parse
                name=urllib.parse.unquote(link['url'].split('/')[-1].split('?')[0])
                response=context.request.get(link['url'])
                if response.ok:
                    (OUT/name).write_bytes(response.body())
                    print('Downloaded',name,flush=True)
    page.goto('https://cursos3.e-itesca.edu.mx/course/view.php?id=215')
    (OUT/'course.txt').write_text(page.locator('body').inner_text(),encoding='utf-8')
    (OUT/'course-links.json').write_text(json.dumps(page.locator('a[href]').evaluate_all('(els)=>els.map(e=>({text:e.innerText,url:e.href}))'),ensure_ascii=False,indent=2),encoding='utf-8')
    browser.close()
