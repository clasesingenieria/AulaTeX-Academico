from pathlib import Path
from docx import Document
from docx.shared import Pt,Inches,RGBColor
from docx.oxml.ns import qn
import sys
sys.stdout.reconfigure(encoding='utf-8')
ROOT=Path(__file__).resolve().parents[1]
COURSE=ROOT/'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
SRC=COURSE/'reporte-plan-de-negocios-Actividad-5-Preguntas-Demanda-Oferta.docx'
d=Document(SRC)
# Working questionnaire: retain page geometry and remove the original report cover.
for node in list(d._element.body):
 if node.tag!=qn('w:sectPr'):d._element.body.remove(node)
for name in ['Normal','Title','Heading 1','Heading 2']:
 s=d.styles[name];s.font.name='Arial';s.font.color.rgb=RGBColor(0,0,0)
d.styles['Normal'].font.size=Pt(10.5)
d.styles['Normal'].paragraph_format.line_spacing=1.05
d.styles['Normal'].paragraph_format.space_after=Pt(5)
d.styles['Title'].font.size=Pt(16)
def para(t,bold=False):
 p=d.add_paragraph(t);p.paragraph_format.keep_with_next=False
 if bold:
  for r in p.runs:r.bold=True
 return p
def question(code,t,options):
 p=para(code+'  '+t,True);p.paragraph_format.keep_with_next=True
 para(options)
p=d.add_paragraph('Sondeo sobre atención automotriz en Monterrey',style='Title')
para('Versión de aplicación del 30 de septiembre de 2026 · Plan de Negocios ITESCA')
para('Participación voluntaria con fines académicos. Puede omitir preguntas o terminar. No se piden nombre, teléfono, domicilio, placas ni datos bancarios; no se enviará publicidad. Responda sobre el vehículo ligero que utiliza con mayor frecuencia. No responda mientras conduce.')
para('Acepto participar: [ ] Sí  [ ] No. Si marca No, finalizar.')
para('Registro del aplicador: folio ______  fecha __________  canal __________\nZona general de aplicación (sin domicilio personal) __________________________')
para('Marque una opción salvo indicación distinta. NS = no sabe o no recuerda; NR = prefiere no responder; NA = no aplica por salto. Los últimos doce meses se cuentan desde la fecha de aplicación.')
question('D01','¿Tiene 18 años o más?','[ ] Sí  [ ] No  [ ] NR. Si responde No o NR, finalizar.')
question('D02','¿Participa en la decisión de contratar servicios o comprar refacciones para un vehículo ligero?','[ ] Decide principalmente  [ ] Comparte la decisión  [ ] No participa  [ ] NS  [ ] NR. Si no participa, NS o NR, finalizar.')
question('D03R','¿En qué municipio reside habitualmente?','Municipio __________________  [ ] NS  [ ] NR. El grupo principal se limita a residentes de Monterrey; registrar otras respuestas por separado.')
question('D03','¿En qué municipio utiliza principalmente ese vehículo?','[ ] Monterrey  [ ] Guadalupe  [ ] San Nicolás de los Garza  [ ] Apodaca\n[ ] General Escobedo  [ ] Santa Catarina  [ ] García  [ ] Otro ______  [ ] NS  [ ] NR. Si Otro, NS o NR, finalizar conforme al instrumento previo.')
question('D04','¿Qué tipo de vehículo eligió para responder?','[ ] Automóvil  [ ] SUV o camioneta de pasajeros  [ ] Pickup ligera\n[ ] Otro tipo  [ ] NS  [ ] NR. Si Otro, NS o NR, finalizar.')
d.add_page_break()
p=d.add_paragraph('Necesidades y experiencia de atención',style='Heading 1')
para('Folio ______  Periodo de los últimos doce meses: desde __________ hasta __________')
question('D07','En los últimos doce meses, ¿requirió las siguientes atenciones para ese vehículo?','Marque una opción en cada renglón.\nMantenimiento preventivo:  [ ] Sí  [ ] No  [ ] NS  [ ] NR\nDiagnóstico o reparación mecánica:  [ ] Sí  [ ] No  [ ] NS  [ ] NR\nServicio o compra de llantas:  [ ] Sí  [ ] No  [ ] NS  [ ] NR\nCompra independiente de refacciones:  [ ] Sí  [ ] No  [ ] NS  [ ] NR')
para('Salto: si todas son No, D08=0 y D09–D11=NA; pasar a D19. Si no hay ningún Sí y hay NS o NR, D08=NS y D09–D11=NA; pasar a D19.')
question('D08','¿Cuántas ocasiones contrató alguna de esas atenciones en los últimos doce meses?','Número entero de ocasiones ______  [ ] NS  [ ] NR. Cuente cada visita o compra independiente una vez, aunque incluya varios trabajos. Si es 0, NS o NR, marque D09–D11=NA y pase a D19.')
question('D09','¿Cuál fue la atención principal en la ocasión más reciente de ese periodo?','[ ] Mantenimiento preventivo  [ ] Diagnóstico o reparación\n[ ] Llantas  [ ] Compra independiente de refacciones  [ ] NS  [ ] NR  [ ] NA\nSi hubo varias, elija la que motivó la visita o compra.')
question('D10','¿Cuánto pagó en total en esa ocasión?','Importe aproximado en MXN, incluidos impuestos: $____________\n[ ] NS  [ ] NR  [ ] NA. Alcance del pago: [ ] Sólo servicio  [ ] Sólo piezas\n[ ] Ambos  [ ] NS  [ ] NR  [ ] NA. No es una valoración hipotética.')
question('D11','¿Qué tan satisfecho quedó con esa atención?','[ ] Muy insatisfecho  [ ] Insatisfecho  [ ] Ni satisfecho ni insatisfecho\n[ ] Satisfecho  [ ] Muy satisfecho  [ ] NS  [ ] NR  [ ] NA')
question('D19','En los próximos tres meses, ¿prevé contratar alguna atención de las categorías de D07?','[ ] Sí  [ ] No  [ ] Todavía no lo sabe  [ ] NR')
question('D20','¿Qué tan probable sería que considerara un establecimiento que aún no ha utilizado?','[ ] Nada probable  [ ] Poco probable  [ ] Ni probable ni improbable\n[ ] Probable  [ ] Muy probable  [ ] NS  [ ] NR')
question('D22','¿Qué mejoraría de la atención automotriz que encuentra actualmente?','Respuesta opcional, sin nombres ni datos personales: _________________________\n_____________________________________________________________________')
para('Gracias por participar. Una respuesta por persona; sus respuestas se analizarán de forma agrupada.')
d.core_properties.title='Sondeo sobre atención automotriz en Monterrey'
d.core_properties.author='Martín Jonathan de la Cruz Muñoz'
out=COURSE/'Sondeo-AM-Taller-Aplicacion.docx';d.save(out);print(out)
