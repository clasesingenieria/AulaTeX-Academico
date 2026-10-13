from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 browser,context,page=login(p)
 page.goto(BASE+'/mod/quiz/view.php?id=6552')
 print(page.locator('#region-main').inner_text())
 print('BUTTONS',page.get_by_role('button').evaluate_all('(es)=>es.map(e=>({text:e.innerText,value:e.value,type:e.type}))'))
 browser.close()
