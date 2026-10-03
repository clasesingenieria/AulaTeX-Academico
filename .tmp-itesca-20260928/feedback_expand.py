from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
with sync_playwright() as p:
 b,c,page=login(p);page.goto(f'{BASE}/mod/assign/view.php?id=6549')
 print(page.locator('#region-main').locator('button,a').evaluate_all('(els)=>els.map(e=>({tag:e.tagName,text:e.innerText,title:e.title,aria:e.getAttribute("aria-label"),cls:e.className,href:e.getAttribute("href")}))'))
 print(page.locator('#region-main').locator('td.feedbacktext').count())
 for el in page.locator('#region-main .no-overflow').all():
  txt=el.inner_text()
  if 'Hola Martín' in txt: print(el.evaluate('(e)=>e.parentElement.outerHTML'))
 b.close()
