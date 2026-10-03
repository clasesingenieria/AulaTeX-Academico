from moodle_common import *
import re
sys.stdout.reconfigure(encoding='utf-8',line_buffering=True)
bank=json.loads((OUT/'quiz-answer-bank.json').read_text(encoding='utf-8'))
def norm(s):return ' '.join(s.replace('\xa0',' ').split()).casefold()
with sync_playwright() as p:
 browser,context,page=login(p)
 for attempt in (3,):
  page.goto(BASE+'/mod/quiz/view.php?id=6552')
  page.get_by_role('button',name='Reintentar el cuestionario',exact=True).click()
  page.get_by_role('button',name='Comenzar intento',exact=True).click()
  page.wait_for_load_state('domcontentloaded')
  captured=[]
  for i in range(20):
   qs=page.locator('.que').evaluate_all('''(es)=>es.map(e=>({id:e.id,number:e.querySelector('.qno')?.innerText,stem:e.querySelector('.qtext')?.innerText,choices:[...e.querySelectorAll('.answer input[type=radio]')].map(i=>({id:i.id,value:i.value,text:i.closest('.r0,.r1')?.innerText||document.querySelector('label[for="'+i.id+'"]')?.innerText}))}))''')
   for q in qs:
    q['url']=page.url
    key=norm(q['stem'])
    if key not in bank:
     (OUT/f'quiz-{attempt}-new-question.json').write_text(json.dumps(q,ensure_ascii=False,indent=2),encoding='utf-8')
     raise RuntimeError('Reactivo nuevo; requiere resolución antes de continuar: '+q['stem'])
    answer=bank[key]['answer']
    choices=[c for c in q['choices'] if norm(c['text'].split('\n\n')[-1])==norm(answer)]
    assert len(choices)==1,(q['number'],answer)
    page.locator('[id="'+choices[0]['id']+'"]').check()
    q['selected']=answer;captured.append(q)
   if page.get_by_role('button',name='Siguiente página',exact=True).count():
    page.get_by_role('button',name='Siguiente página',exact=True).click()
   else:
    page.get_by_role('button',name=re.compile('Terminar intento')).click();break
   page.wait_for_load_state('domcontentloaded')
  summary=page.locator('#region-main').inner_text()
  (OUT/f'quiz-{attempt}-summary.txt').write_text(summary,encoding='utf-8')
  (OUT/f'quiz-{attempt}-questions.json').write_text(json.dumps(captured,ensure_ascii=False,indent=2),encoding='utf-8')
  assert len(captured)==12 and summary.count('Respuesta guardada')==12,summary
  page.get_by_role('button',name='Enviar todo y terminar',exact=True).click()
  confirm=page.locator('button[data-action="save"]').filter(has_text='Enviar todo y terminar')
  confirm.wait_for(state='visible')
  with page.expect_navigation(wait_until='domcontentloaded'):
   confirm.click()
  page.goto(BASE+'/mod/quiz/view.php?id=6552')
  text=page.locator('#region-main').inner_text()
  (OUT/f'quiz-{attempt}-receipt.txt').write_text(text,encoding='utf-8')
  page.screenshot(path=str(OUT/f'quiz-{attempt}-receipt.png'),full_page=True)
  print('ATTEMPT',attempt,text,flush=True)
 browser.close()
