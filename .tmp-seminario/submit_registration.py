exec(open(__file__.replace('submit_registration.py','moodle_read.py'),encoding='utf8').read().split('with sync_playwright() as p:')[0])
import hashlib
from datetime import datetime,timezone

mid=2907
paths=[ROOT/'ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/entregas'/n for n in ['RegistroTema_DeLaCruzMunoz.docx','RegistroTema_DeLaCruzMunoz_Firmado.pdf']]
assert all(path.is_file() for path in paths)
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(ignore_https_errors=True,viewport={'width':1365,'height':1000})
    page=context.new_page()
    page.goto(credentials['url'])
    page.locator('#username').fill(credentials['username'])
    page.locator('#password').fill(credentials['password'])
    page.locator('#loginbtn').click()
    page.wait_for_load_state('domcontentloaded')
    page.goto(f'https://cursos3.e-itesca.edu.mx/mod/assign/view.php?id={mid}')
    before=page.locator('body').inner_text()
    if 'Todavía no se han realizado envíos' not in before:
        print('STOP unexpected prior submission',flush=True)
        print(before[before.find('Estado de la entrega'):before.find('Actividad previa',before.find('Estado de la entrega'))],flush=True)
        browser.close()
        raise SystemExit(2)
    page.get_by_role('button',name='Agregar entrega',exact=True).click()
    for path in paths:
        print('UPLOADING',path.name,flush=True)
        page.get_by_title('Agregar...',exact=True).click()
        page.get_by_text('Subir un archivo',exact=True).click()
        page.locator('.moodle-dialogue-focused input[name=title]').fill('')
        page.locator('input[name=repo_upload_file]').set_input_files(path)
        page.get_by_role('button',name='Subir este archivo',exact=True).click()
        try:
            page.locator('.moodle-dialogue-focused').wait_for(state='hidden',timeout=15000)
        except Exception:
            print('UPLOAD DIALOG',page.locator('.moodle-dialogue-focused').inner_text(),flush=True)
            page.screenshot(path=str(OUT/'2907-upload-inspection.png'),full_page=True)
            raise SystemExit(3)
        page.get_by_text(path.name,exact=True).wait_for(state='visible')
    page.get_by_role('button',name='Guardar cambios',exact=True).click()
    page.wait_for_load_state('domcontentloaded')
    page.goto(f'https://cursos3.e-itesca.edu.mx/mod/assign/view.php?id={mid}')
    after=page.locator('body').inner_text()
    (OUT/f'{mid}-after-save.txt').write_text(after,encoding='utf8')
    start=after.find('Estado de la entrega')
    state=after[start:after.find('Actividad previa',start)]
    print('SAVED',state,flush=True)
    page.screenshot(path=str(OUT/f'{mid}-after-save.png'),full_page=True)
    links=page.locator('a[href]').evaluate_all('(els)=>els.map(e=>({text:e.innerText,url:e.href}))')
    files=[]
    for path in paths:
        submitted=[x for x in links if x['text'].strip()==path.name and '/pluginfile.php/' in x['url']]
        verified=False
        if len(submitted)==1:
            try:
                remote=context.request.get(submitted[0]['url'])
                verified=remote.ok and hashlib.sha256(remote.body()).hexdigest()==hashlib.sha256(path.read_bytes()).hexdigest()
            except Exception:
                print('Download verification failed',path.name,flush=True)
        files.append({'filename':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'download_matches':verified})
    evidence={'module':mid,'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status_text':state,'files':files,'final_submission_observed':'Enviado para calificar' in state,'student_signature':'Provided by user in original scanned PDF; not modified','cvu':'Blank in both submitted files'}
    (OUT/f'{mid}-receipt.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
    print('VERIFIED',json.dumps(evidence,ensure_ascii=False),flush=True)
    browser.close()
