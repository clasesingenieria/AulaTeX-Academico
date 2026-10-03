from pathlib import Path
import os,sys,json
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from aulatex.platform_credentials import PlatformCredentialVault,default_vault_path
BASE='https://cursos3.e-itesca.edu.mx'
OUT=ROOT/'.tmp-itesca-20260928'
def login(p):
 pin=next((v for k,v in os.environ.items() if k.lower()=='aulatex_master_pin'),None)
 if not pin: raise RuntimeError('AULATEX_MASTER_PIN no disponible en el entorno')
 vault=PlatformCredentialVault(default_vault_path(ROOT))
 accounts=[a for a in vault.list_accounts(pin) if a['institution'].upper()=='ITESCA']
 if len(accounts)!=1: raise RuntimeError('La selección de cuenta ITESCA requiere revisión')
 c=vault.get_credentials(pin,accounts[0]['id'])
 resolver_args=[]
 if os.environ.get('ITESCA_DNS_OVERRIDE'):
  import ipaddress
  server_ip=str(ipaddress.ip_address(os.environ['ITESCA_DNS_OVERRIDE']))
  resolver_args=[f'--host-resolver-rules=MAP cursos3.e-itesca.edu.mx {server_ip}']
 browser=p.chromium.launch(headless=True,args=resolver_args)
 context=browser.new_context(accept_downloads=True,viewport={'width':1365,'height':1000})
 page=context.new_page()
 page.goto(c['url'])
 page.locator('#username').fill(c['username'])
 page.locator('#password').fill(c['password'])
 page.locator('#loginbtn').click()
 page.wait_for_load_state('domcontentloaded')
 if '/login/' in page.url: raise RuntimeError('No se completó la autenticación')
 return browser,context,page
if __name__=='__main__':
 with sync_playwright() as p:
  browser,context,page=login(p)
  for kind,mid in [('quiz',6552),('assign',6549),('assign',2910)]:
   page.goto(f'{BASE}/mod/{kind}/view.php?id={mid}')
   text=page.locator('#region-main').inner_text()
   (OUT/f'{mid}-consigna.txt').write_text(text,encoding='utf-8')
   links=page.locator('#region-main a[href]').evaluate_all('(els)=>els.map(e=>({text:e.innerText,url:e.href}))')
   (OUT/f'{mid}-links.json').write_text(json.dumps(links,ensure_ascii=False,indent=2),encoding='utf-8')
   print('MODULE',mid,'\n',text,flush=True)
  browser.close()
