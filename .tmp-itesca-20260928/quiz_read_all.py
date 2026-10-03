from moodle_common import *
sys.stdout.reconfigure(encoding='utf-8')
with sync_playwright() as p:
 browser,context,page=login(p)
 # Recurso autorizado de Tarea 10, sin iniciar otro intento.
 links=json.loads((OUT/'2910-links.json').read_text(encoding='utf-8'))
 resource=next(x for x in links if '/pluginfile.php/' in x['url'])
 response=context.request.get(resource['url'])
 if response.ok:(OUT/'3.3-Formulacion-de-objetivos.pdf').write_bytes(response.body())
 page.goto((OUT/'quiz-attempt-url.txt').read_text(encoding='utf-8'))
 nav=page.locator('a.qnbutton[href]').evaluate_all('(es)=>es.map(e=>({text:e.innerText,url:e.href}))')
 print('NAV',nav)
 urls=list(dict.fromkeys(x['url'].split('#')[0] for x in nav)) or [page.url]
 questions=[]
 for url in urls:
  page.goto(url)
  qs=page.locator('.que').evaluate_all('''(es)=>es.map(e=>({id:e.id,number:e.querySelector('.qno')?.innerText,stem:e.querySelector('.qtext')?.innerText,choices:[...e.querySelectorAll('.answer input[type=radio]')].map(i=>({id:i.id,name:i.name,value:i.value,text:i.closest('.r0,.r1')?.innerText||document.querySelector('label[for="'+i.id+'"]')?.innerText})),text:e.innerText}))''')
  for q in qs:q['url']=page.url
  questions.extend(qs)
 (OUT/'quiz-1-questions.json').write_text(json.dumps(questions,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(questions,ensure_ascii=False,indent=2))
 browser.close()
