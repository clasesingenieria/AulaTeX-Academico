from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 browser,context,page=login(p)
 page.goto((OUT/'quiz-summary-url.txt').read_text(encoding='utf-8'))
 text=page.locator('#region-main').inner_text()
 print(text)
 if 'Resumen del intento' in text and text.count('Respuesta guardada')==12:
  page.get_by_role('button',name='Enviar todo y terminar',exact=True).click()
  page.get_by_role('dialog').get_by_role('button',name='Enviar todo y terminar',exact=True).click()
  page.wait_for_load_state('domcontentloaded')
 review=page.locator('#region-main').inner_text()
 (OUT/'quiz-1-review.txt').write_text(review,encoding='utf-8')
 (OUT/'quiz-1-review-url.txt').write_text(page.url,encoding='utf-8')
 page.screenshot(path=str(OUT/'quiz-1-review.png'),full_page=True)
 print('REVIEW',page.url,'\n',review)
 browser.close()
