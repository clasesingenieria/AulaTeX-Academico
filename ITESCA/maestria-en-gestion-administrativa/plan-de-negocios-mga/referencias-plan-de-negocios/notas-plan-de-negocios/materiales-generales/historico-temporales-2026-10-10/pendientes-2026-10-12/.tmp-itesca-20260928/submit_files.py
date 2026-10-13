from moodle_common import *
import hashlib
from datetime import datetime,timezone
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
mid=int(sys.argv[1]);paths=[(ROOT/arg).resolve() for arg in sys.argv[2:]]
assert paths and all(x.is_file() for x in paths)
with sync_playwright() as p:
 browser,context,page=login(p)
 page.goto(f'{BASE}/mod/assign/view.php?id={mid}')
 before=page.locator('#region-main').inner_text()
 if 'Todavía no se han realizado envíos' not in before:raise RuntimeError('Ya existe entrega; inspeccionar antes de modificar')
 page.get_by_role('button',name='Agregar entrega',exact=True).click()
 for path in paths:
  page.get_by_title('Agregar...',exact=True).click()
  page.get_by_text('Subir un archivo',exact=True).click()
  page.locator('.moodle-dialogue-focused .fp-upload-form').wait_for(state='visible')
  upload=page.locator('.moodle-dialogue-focused input[name=repo_upload_file]')
  upload.wait_for(state='visible')
  page.wait_for_load_state('networkidle')
  upload.set_input_files(str(path))
  page.wait_for_function('(name) => Array.from(document.querySelectorAll("input[name=repo_upload_file]")).some(e=>e.files.length===1 && e.files[0].name===name)',arg=path.name)
  print('ARCHIVO PREPARADO',upload.evaluate('(e)=>({name:e.files[0].name,size:e.files[0].size})'))
  with page.expect_response(lambda response: 'repository_ajax.php' in response.url and 'upload' in response.url) as pending_upload:
   page.get_by_role('button',name='Subir este archivo',exact=True).click()
  upload_result=pending_upload.value.json()
  print('RESPUESTA DE CARGA',{'http':pending_upload.value.status,'fields':list(upload_result),'error':upload_result.get('error')})
  if upload_result.get('error'):
   raise RuntimeError('Moodle rechazó la carga: '+str(upload_result['error']))
  try:page.locator('.moodle-dialogue-focused').wait_for(state='hidden')
  except Exception:
   print('UPLOAD DIALOG',page.locator('.moodle-dialogue-focused').inner_text())
   page.screenshot(path=str(OUT/f'{mid}-upload-error.png'),full_page=True)
   raise
  page.get_by_text(path.name,exact=True).wait_for(state='visible')
 page.get_by_role('button',name='Guardar cambios',exact=True).click()
 page.wait_for_load_state('domcontentloaded')
 page.goto(f'{BASE}/mod/assign/view.php?id={mid}')
 after=page.locator('#region-main').inner_text()
 (OUT/f'{mid}-after-save.txt').write_text(after,encoding='utf-8')
 page.locator('#region-main').screenshot(path=str(OUT/f'{mid}-after-save.png'))
 links=page.locator('#region-main a[href]').evaluate_all('(els)=>els.map(e=>({text:e.innerText,url:e.href}))')
 files=[]
 for path in paths:
  matched=[l for l in links if l['text']==path.name and '/pluginfile.php/' in l['url']]
  localhash=hashlib.sha256(path.read_bytes()).hexdigest();verified=False
  if matched:
   remote=page.evaluate('''async (url) => {
    const r=await fetch(url);
    if(!r.ok) return {ok:false};
    const bytes=await r.arrayBuffer();
    const hash=await crypto.subtle.digest('SHA-256', bytes);
    return {ok:true,sha256:Array.from(new Uint8Array(hash)).map(x=>x.toString(16).padStart(2,'0')).join('')};
   }''',matched[0]['url'])
   verified=remote.get('ok',False) and remote.get('sha256')==localhash
  files.append({'filename':path.name,'sha256':localhash,'download_matches':verified})
 state=after[after.index('Estado de la entrega'):]
 evidence={'module':mid,'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status_text':state,'files':files,'final_submission_observed':'Enviado para calificar' in state}
 (OUT/f'{mid}-receipt.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(evidence,ensure_ascii=False,indent=2))
 browser.close()
