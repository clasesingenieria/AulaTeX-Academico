from pathlib import Path
from copy import deepcopy
from hashlib import sha256
import zipfile
from lxml import etree

ROOT=Path(__file__).resolve().parents[1]
COURSE=ROOT/'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
SOURCE=COURSE/'referencias-plan-de-negocios/correccion-sondeo-2026-09-30/entregado-reporte-plan-de-negocios-Actividad-10-AM-Taller.docx'
OUT=COURSE/'reporte-plan-de-negocios-Actividad-10-AM-Taller-Revision.docx'
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W='{'+NS['w']+'}'
before_hash=sha256(SOURCE.read_bytes()).hexdigest()
with zipfile.ZipFile(SOURCE) as z:
    parts={info.filename:(info,z.read(info.filename)) for info in z.infolist()}
root=etree.fromstring(parts['word/document.xml'][1])
body=root.find('w:body',NS)
ps=body.findall('w:p',NS)
tables=body.findall('w:tbl',NS)
preserved_tables=[etree.tostring(t) for t in tables[:2]]
preserved_offering=[etree.tostring(ps[i]) for i in (13,16,19,21,22,24,25)]
preserved_refs=[etree.tostring(p) for p in ps[62:]]

def replace(p,text):
    rp=p.find('w:r/w:rPr',NS)
    rp=deepcopy(rp) if rp is not None else None
    for el in list(p):
        if el.tag != W+'pPr':p.remove(el)
    for i,line in enumerate(text.split('\n')):
        r=etree.SubElement(p,W+'r')
        if rp is not None:r.append(deepcopy(rp))
        if i:etree.SubElement(r,W+'br')
        t=etree.SubElement(r,W+'t');t.text=line;t.set('{http://www.w3.org/XML/1998/namespace}space','preserve')

replace(ps[4],'Revisión metodológica del sondeo')
replace(ps[5],'AM Taller Autocentro\nActividad 10 Resultados de la investigación de mercados\nPendiente integrar respuestas reales')
replace(ps[7],'Monterrey, Nuevo León\n30 de septiembre de 2026')
replace(ps[9],'Propósito de la revisión')
replace(ps[10],'Esta revisión organiza el sondeo real que falta integrar al estudio de AM Taller Autocentro. La observación documental de cuatro oferentes y dos modalidades alternativas se conserva como antecedente de oferta. Para completar la demanda se requiere preguntar a personas residentes en Monterrey qué servicios utilizan, con qué frecuencia, cuánto gastan y qué tan satisfechas quedan. Todavía no se dispone de sus respuestas; esta copia es de trabajo y no acredita una corrección concluida.')
replace(ps[11],'Se mantiene la continuidad con los instrumentos de la actividad 5 y la delimitación municipal de la actividad 7. Se retoman sus códigos sin fusionar preguntas. Se agrega D03R para residencia, porque D03 pregunta dónde se utiliza principalmente el vehículo y no demuestra por sí sola que la persona resida en Monterrey.')
replace(ps[12],'Método y alcance del sondeo')
# The documentary procedure and its observation date remain unchanged in paragraph 13.
replace(ps[14],'El sondeo se aplicará por conveniencia a personas disponibles que acepten participar, tengan 18 años o más, residan en el municipio de Monterrey y decidan o compartan la atención de un vehículo ligero. Se registrarán las fechas y zonas generales reales de aplicación; aún están por registrar. No se requiere selección aleatoria para esta exploración. Se describirá a quienes respondan, sin generalizar sus porcentajes a todo Monterrey. La consigna previa solicita Google Forms y enviarlo al menos a 30 personas; la distribución y las respuestas se documentarán por separado. La investigación documental no reemplaza este sondeo.')
replace(ps[17],'El municipio de Monterrey, clave 19039, registró 1,142,994 habitantes y 329,095 viviendas habitadas en el Censo 2020 (INEGI, 2020). Son unidades y fecha históricas; no representan vehículos, compradores o demanda de 2026. Para este sondeo se verificará residencia en Monterrey mediante D03R y se conservará por separado D03, municipio de uso principal del vehículo.')
replace(ps[27],'Resultados del sondeo')
replace(ps[28],'Pendiente de integrar respuestas reales. No se han calculado indicadores ni se presenta cero como resultado de una base vacía. Se registrarán periodo y zonas generales de aplicación, invitaciones efectivamente enviadas, respuestas recibidas, casos elegibles y casos válidos. El número de invitaciones no equivale al de respuestas. La siguiente tabla especifica el formato que se completará al contar con registros verificables.')

rows=tables[2].findall('w:tr',NS)
values=[
['Indicador','Presentación al integrar los datos','Estado'],
['Servicio\nD07 y D09','D07: frecuencia y porcentaje por categoría requerida. D09: frecuencia y porcentaje del servicio principal más reciente, entre casos a los que aplica.','Pendiente\nn válidas, f y %'],
['Frecuencia de uso\nD08','Distribución del número de ocasiones en doce meses, con f, % y n válidas; mediana de ocasiones como resumen.','Pendiente\nRespuestas reales'],
['Gasto\nD10','Mediana en MXN y n de importes válidos, por categoría D09 y por alcance: sólo servicio, sólo piezas o ambos.','Pendiente\nImportes comparables'],
['Satisfacción\nD11','Frecuencia y porcentaje de cada una de las cinco categorías, con su n válida.','Pendiente\nRespuestas reales']]
for row,vals in zip(rows,values):
    cells=row.findall('w:tc',NS)
    for cell,txt in zip(cells,vals):
        pp=cell.findall('w:p',NS)
        replace(pp[0],txt)
        for p in pp[1:]:cell.remove(p)
for row in rows[len(values):]:tables[2].remove(row)
replace(ps[30],'Para cada indicador se informará su n válida y se calculará porcentaje = 100 × f / n válida. No sabe, no responde y no aplica se contarán por separado; no se convertirán en ceros. D07 tendrá denominador por categoría y sus porcentajes no tienen que sumar 100. En D08, cero se admitirá sólo si fue una respuesta válida. D09–D11 se analizarán únicamente cuando corresponda por los saltos del instrumento. D10 no mezclará tipos de servicio ni alcances distintos; no se imputarán importes faltantes.')
replace(ps[35],'El siguiente paso es aplicar el sondeo breve por conveniencia y capturar las respuestas con folio anónimo. Se comprobarán residencia, elegibilidad y saltos, se revisarán duplicados y se tabularán servicio, frecuencia, gasto y satisfacción. La intención futura se analizará por separado. Las conclusiones de demanda deberán redactarse después de observar los datos, sin atribuir a todos los habitantes lo expresado por las personas consultadas.')
replace(ps[36],'La revisión conserva los resultados documentales de competidores y sustitutos y precisa cómo obtener la información de demanda solicitada. El sondeo, su análisis y la integración final continúan pendientes. Hasta incorporarlos no se presentará esta copia como corrección completa ni se afirmará demanda suficiente, apertura comercial o rentabilidad.')
replace(ps[38],'Se utilizó asistencia de inteligencia artificial para organizar fuentes y revisar la redacción. La evidencia documental conserva su fecha y procedencia. El sondeo se integrará únicamente con respuestas reales.')

def make(template,text):
    p=deepcopy(template);replace(p,text);return p

annex=[
(ps[40],'Instrumento separado para la aplicación'),
(ps[41],'El cuestionario se presenta por separado en Sondeo-AM-Taller-Aplicacion.docx. Esta síntesis describe sus códigos; no sustituye los reactivos, opciones ni saltos del instrumento. Las preguntas de observación de competidores se mantienen fuera del cuestionario a consumidores.'),
(ps[42],'Elegibilidad y territorio'),
(ps[43],'D01 verifica mayoría de edad y D02 participación en la decisión de contratar. Si no se cumplen los criterios, se termina sin continuar.'),
(ps[43],'D03 conserva el municipio de uso principal del vehículo. D03R se añade para preguntar residencia actual en el municipio de Monterrey; ambas respuestas se registran en campos distintos.'),
(ps[43],'D04 verifica el tipo de vehículo ligero al que se referirán todas las respuestas. Se mantendrá un solo vehículo de referencia por persona.'),
(ps[42],'Experiencia de servicio'),
(ps[43],'D07 registra por separado mantenimiento preventivo, diagnóstico o reparación, llantas y compra independiente de refacciones durante los últimos doce meses.'),
(ps[43],'D08 pregunta cuántas ocasiones se contrataron esas atenciones, contando una visita o compra una sola vez. Sus saltos determinan si corresponde responder D09–D11.'),
(ps[43],'D09 identifica la atención principal más reciente. D10 registra su gasto en MXN y distingue sólo servicio, sólo piezas o ambos, con impuestos. D11 recoge satisfacción en cinco categorías.'),
(ps[42],'Necesidad futura y mejora'),
(ps[43],'D19 pregunta por atención prevista en los próximos tres meses. D20 recoge la disposición a considerar un establecimiento no utilizado; no presupone compra a AM Taller. D22 permite describir mejoras deseadas sin datos personales.'),
(ps[41],'Antes de aplicar, registrar la fecha real y los límites del periodo de referencia. La participación será voluntaria; se usarán folios anónimos y ubicación general. Conservar las omisiones, las respuestas no sabe o no responde y los saltos no aplica. No solicitar nombres, placas ni domicilios exactos.')]
anchor=ps[40]
for template,txt in annex:anchor.addprevious(make(template,txt))
for p in ps[40:61]:body.remove(p)

assert [etree.tostring(t) for t in tables[:2]]==preserved_tables
assert [etree.tostring(ps[i]) for i in (13,16,19,21,22,24,25)]==preserved_offering
assert [etree.tostring(p) for p in ps[62:]]==preserved_refs
xml=etree.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
with zipfile.ZipFile(OUT,'w') as z:
    for name,(info,data) in parts.items():z.writestr(info,xml if name=='word/document.xml' else data)
assert sha256(SOURCE.read_bytes()).hexdigest()==before_hash
with zipfile.ZipFile(OUT) as z:
    untouched=[name for name,(_,data) in parts.items() if name!='word/document.xml' and z.read(name)!=data]
assert not untouched
note=f'''# Revisión metodológica del sondeo AM Taller

Fuente exacta conservada: {SOURCE}
SHA256 de fuente: {before_hash}
Salida: {OUT}
Edición OOXML limitada a word/document.xml. Los demás componentes ZIP, estilos, márgenes, logo, tablas 0 y 1 de oferta y sustitutos y referencias se preservan. Marcador de operación edit de dos DOCX registrado previamente por agente principal. La fecha de la consulta documental sigue siendo 28/09/2026; fecha de revisión 30/09/2026. Fechas del sondeo permanecen pendientes de aplicación real.

Cambios: método simple por conveniencia de residentes Monterrey; D03R residencia separado de D03 uso; estado explícito de resultados pendientes; cuatro indicadores con reglas de tabulación y medianas de gastos por servicio y alcance; anexo remitido a instrumento separado. No se fabrican ni imputan respuestas. No es versión final para entrega. Render y QA visual a cargo del agente principal.
'''
(ROOT/'.tmp-itesca-20260928/artifact-revision-sondeo.md').write_text(note,encoding='utf-8')
print(OUT)
print('Original y componentes no editados preservados; oferta y referencias verificadas.')
