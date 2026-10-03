from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
path=ROOT/'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/Actividad-11-AM-Taller-Version-Grafica.pdf'
with sync_playwright() as p:
 browser,context,page=login(p)
 page.goto(f'{BASE}/mod/assign/view.php?id=6550')
 page.get_by_role('button',name='Agregar entrega',exact=True).click()
 page.get_by_title('Agregar...',exact=True).click()
 page.get_by_text('Subir un archivo',exact=True).click()
 page.locator('.moodle-dialogue-focused .fp-upload-form').wait_for(state='visible')
 print('FORM',page.locator('.moodle-dialogue-focused').inner_text())
 print('INPUTS',page.locator('.moodle-dialogue-focused input').evaluate_all('(els)=>els.map(e=>({type:e.type,name:e.name,id:e.id,accept:e.accept}))'))
 upload=page.locator('.moodle-dialogue-focused input[name=repo_upload_file]')
 print('BEFORE',upload.evaluate('(e)=>({html:e.outerHTML,count:e.files.length,formAction:e.form?.action})'))
 upload.set_input_files(str(path))
 print('AFTER',upload.evaluate('(e)=>({count:e.files.length,files:Array.from(e.files).map(f=>({name:f.name,size:f.size})),value:e.value})'))
 print('FORM AFTER',page.locator('.moodle-dialogue-focused').inner_text())
 page.locator('.moodle-dialogue-focused').screenshot(path=str(OUT/'6550-filepicker-diagnostic.png'))
 browser.close()
