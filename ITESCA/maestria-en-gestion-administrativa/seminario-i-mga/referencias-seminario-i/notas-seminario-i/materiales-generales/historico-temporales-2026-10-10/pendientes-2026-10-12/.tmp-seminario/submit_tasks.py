exec(open(__file__.replace('submit_tasks.py','moodle_read.py'),encoding='utf8').read().split('with sync_playwright() as p:')[0])
import hashlib
from datetime import datetime,timezone
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(ignore_https_errors=True,viewport={'width':1365,'height':1000})
    page=context.new_page()
    page.goto(credentials['url'])
    page.locator('#username').fill(credentials['username']);page.locator('#password').fill(credentials['password']);page.locator('#loginbtn').click()
    page.wait_for_load_state('domcontentloaded')
    for mid,task in [(2908,8),(2909,9)]:
        page.goto(f'https://cursos3.e-itesca.edu.mx/mod/assign/view.php?id={mid}')
        before=page.locator('body').inner_text()
        if 'Todavía no se han realizado envíos' not in before:
            print('STOP unexpected prior submission',mid,flush=True);break
        path=ROOT/f'ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/entregas/Tarea{task}_DeLaCruzMunoz.docx'
        page.get_by_role('button',name='Agregar entrega',exact=True).click()
        page.get_by_title('Agregar...',exact=True).click()
        page.get_by_text('Subir un archivo',exact=True).click()
        page.locator('input[name=repo_upload_file]').set_input_files(path)
        page.get_by_role('button',name='Subir este archivo',exact=True).click()
        page.locator('.moodle-dialogue-focused').wait_for(state='hidden')
        page.get_by_text(path.name,exact=True).wait_for(state='visible')
        page.get_by_role('button',name='Guardar cambios',exact=True).click()
        page.wait_for_load_state('domcontentloaded')
        page.goto(f'https://cursos3.e-itesca.edu.mx/mod/assign/view.php?id={mid}')
        after=page.locator('body').inner_text()
        (OUT/f'{mid}-after-save.txt').write_text(after,encoding='utf8')
        state=after[after.find('Estado de la entrega'):after.find('Actividad previa',after.find('Estado de la entrega'))]
        print('SAVED',mid,state,flush=True)
        page.screenshot(path=str(OUT/f'{mid}-after-save.png'),full_page=True)
        links=page.locator('a[href]').evaluate_all('(els)=>els.map(e=>({text:e.innerText,url:e.href}))')
        submitted=[x for x in links if x['text']==path.name and '/pluginfile.php/' in x['url']]
        verified=False
        if submitted:
            remote=context.request.get(submitted[0]['url'])
            verified=remote.ok and hashlib.sha256(remote.body()).hexdigest()==hashlib.sha256(path.read_bytes()).hexdigest()
        evidence={'module':mid,'filename':path.name,'timestamp_utc':datetime.now(timezone.utc).isoformat(),'status_text':state,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'download_matches':verified,'final_submission_observed':'Enviado para calificar' in state}
        (OUT/f'{mid}-receipt.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
        print('RECEIPT',mid,{'download_matches':verified,'final_submission':evidence['final_submission_observed']},flush=True)
    browser.close()
