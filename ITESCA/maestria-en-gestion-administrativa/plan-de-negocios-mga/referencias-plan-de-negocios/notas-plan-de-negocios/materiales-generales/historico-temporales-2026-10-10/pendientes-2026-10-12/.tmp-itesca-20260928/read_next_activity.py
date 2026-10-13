from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
dest=ROOT/'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/referencias-plan-de-negocios/actividad-11-2026-09-30'
dest.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser,context,page=login(p)
 for mid in [6550,6551]:
  page.goto(f'{BASE}/mod/assign/view.php?id={mid}')
  body=page.locator('#region-main').inner_text()
  (dest/f'{mid}-consigna-estado.txt').write_text(body,encoding='utf-8')
  print('MODULE',mid,body)
  links=page.locator('#region-main a[href]').evaluate_all('(els)=>els.map(e=>({text:e.innerText,url:e.href}))')
  (dest/f'{mid}-links.json').write_text(json.dumps(links,ensure_ascii=False,indent=2),encoding='utf-8')
 browser.close()
