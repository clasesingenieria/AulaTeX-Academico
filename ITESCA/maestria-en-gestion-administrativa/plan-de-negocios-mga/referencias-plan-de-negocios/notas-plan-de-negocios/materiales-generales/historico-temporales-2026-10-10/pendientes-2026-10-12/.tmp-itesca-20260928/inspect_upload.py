from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
with sync_playwright() as p:
 browser,context,page=login(p)
 for mid in [6549,2910]:
  page.goto(f'{BASE}/mod/assign/view.php?id={mid}')
  page.get_by_role('button',name='Agregar entrega',exact=True).click()
  text=page.locator('#region-main').inner_text()
  (OUT/f'{mid}-upload-form.txt').write_text(text,encoding='utf-8')
  print(mid,text)
 browser.close()
