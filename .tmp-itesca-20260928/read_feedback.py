from moodle_common import *
from hashlib import sha256
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
dest=ROOT/'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/referencias-plan-de-negocios/correccion-sondeo-2026-09-30'
dest.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser,context,page=login(p)
 page.goto(f'{BASE}/mod/assign/view.php?id=6549')
 expand=page.get_by_role('link',name='Ver completo',exact=True)
 if expand.count():
  expand.click()
  page.get_by_text('Te invito a realizar el sondeo',exact=False).wait_for(state='visible',timeout=10000)
 body=page.locator('body').inner_text()
 (dest/'retroalimentacion-aula.txt').write_text(body,encoding='utf-8')
 print(body)
 links=page.locator('#region-main a[href]').evaluate_all('(els)=>els.map(e=>({text:e.innerText,url:e.href}))')
 for item in links:
  if '/pluginfile.php/' in item['url'] and item['text'].endswith('.docx'):
   response=context.request.get(item['url'])
   if response.ok:
    data=response.body();(dest/('entregado-'+Path(item['text']).name)).write_bytes(data)
    print('DESCARGADO',item['text'],sha256(data).hexdigest())
 browser.close()
