from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
with sync_playwright() as p:
 browser,context,page=login(p)
 page.goto((OUT/'quiz-2-active-summary-url.txt').read_text(encoding='utf-8'))
 assert page.locator('#region-main').inner_text().count('Respuesta guardada')==12
 page.get_by_role('button',name='Enviar todo y terminar',exact=True).click()
 confirmation=page.locator('button[data-action="save"]').filter(has_text='Enviar todo y terminar')
 confirmation.wait_for(state='visible')
 with page.expect_navigation(wait_until='domcontentloaded'):
  confirmation.click()
 page.goto(BASE+'/mod/quiz/view.php?id=6552')
 text=page.locator('#region-main').inner_text()
 (OUT/'quiz-2-receipt.txt').write_text(text,encoding='utf-8')
 page.screenshot(path=str(OUT/'quiz-2-receipt.png'),full_page=True)
 print(text)
 browser.close()
