from moodle_common import *
import re
sys.stdout.reconfigure(encoding='utf-8')
answers={1:('Producto','Integra atributos tangibles e intangibles destinados a satisfacer necesidades.'),2:('Descripción de la Empresa','La semblanza reúne historia, objetivos, industria y rasgos distintivos de la empresa.'),3:('Definición del nombre','El nombre identifica la empresa y genera una primera impresión; no exige describir literalmente su giro.'),4:('Falso','La descripción corresponde a documentos primarios, no a fuentes secundarias.'),5:('Verdadero','La mercadotecnia identifica y satisface necesidades, mediante estrategias que contribuyen a ventas y participación.'),6:('Verdadero','La misión expresa la razón de ser, actividad y destinatarios de la organización.'),7:('Plan de promoción','Coordina ventas personales, publicidad, promoción de ventas y relaciones públicas.'),8:('Análisis de Mercado','Es la opción que corresponde a la recopilación y análisis de información comercial; el concepto también se denomina investigación de mercados.'),9:('Falso','El rumbo y la aspiración de largo plazo describen la visión; los objetivos son resultados a alcanzar.'),10:('Verdadero','El FODA considera fortalezas y debilidades internas y oportunidades y amenazas del entorno.'),11:('Falso','Introducir productos en la distribución describe comercialización, no demanda.'),12:('Factores Claves de Éxito','Son elementos determinantes para lograr objetivos y diferenciarse de competidores.')}
questions=json.loads((OUT/'quiz-1-questions.json').read_text(encoding='utf-8'))
def norm(s):return ' '.join(s.replace('\xa0',' ').split()).casefold()
bank={norm(q['stem']):{'answer':answers[int(q['number'])][0],'rationale':answers[int(q['number'])][1]} for q in questions}
(OUT/'quiz-answer-bank.json').write_text(json.dumps(bank,ensure_ascii=False,indent=2),encoding='utf-8')
with sync_playwright() as p:
 browser,context,page=login(p)
 for q in questions:
  page.goto(q['url'])
  expected=bank[norm(q['stem'])]['answer']
  choices=[c for c in q['choices'] if norm(c['text'].split('\n\n')[-1])==norm(expected)]
  assert len(choices)==1,(q['number'],expected)
  page.locator('[id="'+choices[0]['id']+'"]').check()
  if page.get_by_role('button',name='Siguiente página',exact=True).count():
   page.get_by_role('button',name='Siguiente página',exact=True).click()
  else:
   print('LASTBUTTONS',page.get_by_role('button').evaluate_all('(es)=>es.map(e=>({text:e.innerText,value:e.value}))'))
   page.get_by_role('button',name=re.compile('Terminar intento')).click()
  page.wait_for_load_state('domcontentloaded')
  print('SAVED',q['number'],expected,flush=True)
 summary=page.locator('#region-main').inner_text()
 print('SUMMARY',summary)
 (OUT/'quiz-1-summary.txt').write_text(summary,encoding='utf-8')
 (OUT/'quiz-summary-url.txt').write_text(page.url,encoding='utf-8')
 browser.close()
