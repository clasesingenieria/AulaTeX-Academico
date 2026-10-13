from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 browser,context,page=login(p)
 page.goto(BASE+'/mod/quiz/view.php?id=6552')
 page.get_by_role('button',name='Intento de cuestionario',exact=True).click()
 page.wait_for_load_state('domcontentloaded')
 print('MAIN',page.locator('body').inner_text()[-13000:])
 print('BUTTONS',page.get_by_role('button').evaluate_all('(es)=>es.map(e=>({text:e.innerText,value:e.value,type:e.type}))'))
 (OUT/'quiz-start-url.txt').write_text(page.url,encoding='utf-8')
 browser.close()
