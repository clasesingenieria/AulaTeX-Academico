from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
with sync_playwright() as p:
 browser,context,page=login(p)
 page.goto(BASE+'/mod/quiz/view.php?id=6552')
 print('VIEW',page.locator('#region-main').inner_text())
 if page.get_by_role('button',name='Continuar el último intento',exact=True).count():
  page.get_by_role('button',name='Continuar el último intento',exact=True).click()
  links=page.locator('a[href]').evaluate_all('(es)=>es.filter(e=>e.href.includes("summary.php")).map(e=>({text:e.innerText,url:e.href}))')
  print('SUMMARYLINKS',links)
  if links:page.goto(links[0]['url'])
  else:page.get_by_role('button',name='Terminar intento...',exact=True).click()
  print('SUMMARY',page.locator('#region-main').inner_text())
  page.get_by_role('button',name='Enviar todo y terminar',exact=True).click()
  page.wait_for_timeout(800)
  print('AFTERCLICK',page.locator('body').inner_text()[-5000:])
  print('BUTTONS',page.get_by_role('button').evaluate_all('(es)=>es.map(e=>({text:e.innerText,value:e.value,id:e.id,type:e.type,visible:!!(e.offsetWidth||e.offsetHeight),parent:e.parentElement.outerHTML.slice(0,300)}))'))
  (OUT/'quiz-2-active-summary-url.txt').write_text(page.url,encoding='utf-8')
 browser.close()
