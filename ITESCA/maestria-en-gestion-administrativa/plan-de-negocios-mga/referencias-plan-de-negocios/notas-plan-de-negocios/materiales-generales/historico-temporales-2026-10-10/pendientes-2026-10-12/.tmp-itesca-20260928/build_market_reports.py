from pathlib import Path
from hashlib import sha256
from copy import deepcopy
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT=Path(__file__).resolve().parents[1]
COURSE=ROOT/'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga'
REF=COURSE/'reporte-plan-de-negocios-Actividad-10-Resultados-Mercados.docx'
ref_hash=sha256(REF.read_bytes()).hexdigest()

def replace(p,text):
    props=deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
    for child in list(p._p):
        if child.tag != qn('w:pPr'): p._p.remove(child)
    r=p.add_run(text)
    if props is not None:r._r.insert(0,props)
    return p

def base(case):
    d=Document(REF)
    keep={p._p for p in d.paragraphs[:9]}
    for el in list(d._element.body):
        if el not in keep and el.tag != qn('w:sectPr'): d._element.body.remove(el)
    p=d.paragraphs
    replace(p[4],'Resultados de la investigación de mercados')
    p[4].style='Title'
    p[4].alignment=WD_ALIGN_PARAGRAPH.CENTER
    for r in p[4].runs:r.font.size=Pt(20);r.font.color.rgb=RGBColor(0,0,0);r.bold=True
    replace(p[5],case+'\nInvestigación documental de la oferta y la demanda potencial')
    replace(p[6],'Martín Jonathan de la Cruz Muñoz\nMatrícula 26130503\nDocente Celia Velázquez Reyna')
    replace(p[7],'Monterrey, Nuevo León\n28 de septiembre de 2026')
    for i in range(1,8):p[i].alignment=WD_ALIGN_PARAGRAPH.CENTER
    for name in ['Title','Subtitle','Heading 1','Heading 2']:
        d.styles[name].font.color.rgb=RGBColor(0,0,0)
    d.core_properties.title='Resultados de la investigación de mercados de '+case
    d.core_properties.author='Martín Jonathan de la Cruz Muñoz'
    d.core_properties.subject='Plan de Negocios GGPN01 Actividad 10'
    return d

def para(d,text):
    p=d.add_paragraph(text,style='Normal')
    p.paragraph_format.space_after=Pt(7)
    p.paragraph_format.widow_control=True
    return p

def head(d,text):
    p=d.add_paragraph(text,style='Heading 1')
    p.paragraph_format.keep_with_next=True
    return p

def newpage(d):d.add_page_break()

def table(d,headers,rows,widths):
    t=d.add_table(rows=1,cols=len(headers));t.alignment=WD_TABLE_ALIGNMENT.CENTER;t.autofit=False
    for c,w in zip(t.columns,widths):c.width=Inches(w)
    for c,h in zip(t.rows[0].cells,headers):c.text=h
    for vals in rows:
        cells=t.add_row().cells
        for c,s in zip(cells,vals):c.text=s
    for row_i,row in enumerate(t.rows):
        trPr=row._tr.get_or_add_trPr()
        cant=OxmlElement('w:cantSplit');trPr.append(cant)
        if row_i==0:
            rep=OxmlElement('w:tblHeader');trPr.append(rep)
        for j,c in enumerate(row.cells):
            c.width=Inches(widths[j]);c.vertical_alignment=WD_CELL_VERTICAL_ALIGNMENT.CENTER
            tcPr=c._tc.get_or_add_tcPr()
            borders=OxmlElement('w:tcBorders')
            for edge in ['top','left','bottom','right']:
                e=OxmlElement('w:'+edge);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'5');e.set(qn('w:color'),'D9D9D9');borders.append(e)
            tcPr.append(borders)
            margins=OxmlElement('w:tcMar')
            for side in ['top','left','bottom','right']:
                e=OxmlElement('w:'+side);e.set(qn('w:w'),'95');e.set(qn('w:type'),'dxa');margins.append(e)
            tcPr.append(margins)
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'DCE6F1' if row_i==0 else ('FFFFFF' if row_i%2 else 'F5F7FA'));tcPr.append(shade)
            for p in c.paragraphs:
                p.paragraph_format.line_spacing=1.05;p.paragraph_format.space_before=Pt(2);p.paragraph_format.space_after=Pt(2)
                for r in p.runs:r.font.name='Arial';r.font.size=Pt(10.5);r.bold=row_i==0;r.font.color.rgb=RGBColor(0,0,0)
    d.add_paragraph().paragraph_format.space_after=Pt(2)
    return t

def refs(d,items):
    head(d,'Referencias')
    for author,date,title,url,retrieved in items:
        p=d.add_paragraph(style='Normal')
        p.paragraph_format.left_indent=Inches(.3);p.paragraph_format.first_line_indent=Inches(-.3)
        p.paragraph_format.line_spacing=1.05;p.paragraph_format.space_after=Pt(8)
        p.add_run(f'{author} ({date}). ')
        p.add_run(title).italic=True
        p.add_run('. '+('Recuperado el 28 de septiembre de 2026, de ' if retrieved else '')+url)
        for r in p.runs:r.font.size=Pt(10.5)

def questions(d,demand,offer):
    newpage(d);head(d,'Anexo de preguntas para el formulario')
    p=para(d,'Propuesta para revisión y carga en Google Forms. No se ha creado ni distribuido el formulario. La consigna solicita enviarlo a por lo menos 30 personas; ese envío y sus respuestas siguen pendientes. Participación voluntaria, sin nombres ni contactos personales. Incluir no sabe y prefiere no responder cuando corresponda.')
    for r in p.runs:r.font.size=Pt(10.5)
    p.paragraph_format.line_spacing=1.1
    for title,qs in [('Demanda',demand),('Competencia y sustitutos',offer)]:
        p=d.add_paragraph(title,style='Heading 2');p.paragraph_format.space_before=Pt(5)
        for i,q in enumerate(qs,1):
            p=d.add_paragraph(f'{i}. {q}',style='Normal');p.paragraph_format.line_spacing=1.05;p.paragraph_format.space_after=Pt(3)
            for r in p.runs:r.font.size=Pt(10.5)

am=base('AM Taller Autocentro')
head(am,'Propósito y resultado principal')
para(am,'La investigación documental identifica una oferta local de mantenimiento automotriz que coincide con los servicios previstos para AM Taller Autocentro. Se encontraron cuatro oferentes con establecimientos publicados en Monterrey y dos modalidades alternativas de atención. Esta evidencia permite comparar servicios y acceso, pero no cuantifica compradores ni demuestra demanda insatisfecha. La decisión propuesta es definir un servicio de entrada con alcance y cotización claros antes de proyectar ventas.')
para(am,'El proyecto continúa los instrumentos de demanda y oferta de la actividad 5, la delimitación municipal de la actividad 7 y la propuesta de difusión de la actividad 8. AM Taller se plantea como taller, llantera y refaccionaria; la integración de estos servicios constituye una propuesta comercial que debe contrastarse con las necesidades de los usuarios y con la capacidad propia.')
head(am,'Método de investigación documental')
para(am,'El 28 de septiembre de 2026 se revisaron páginas de los propios prestadores y el servicio estadístico oficial de INEGI. La selección fue intencional: establecimientos publicados en Monterrey con mantenimiento, reparación o diagnóstico automotriz. Se registraron ubicación, servicios anunciados, recepción, cotización y disponibilidad de precios comparables. La observación corresponde a publicaciones comerciales; no se realizaron visitas, llamadas, reservas ni solicitudes de cotización.')
para(am,'La consigna solicita preguntas de demanda y competencia, un Google Form enviado a por lo menos 30 personas y revisión de 5 a 10 empresas similares o sustitutas. Se documentan cinco empresas distintas: cuatro oferentes y Mazda. Pronto móvil es una modalidad, no una sexta empresa. El formulario, su distribución y los resultados del sondeo siguen pendientes; no se reportan encuestados ni porcentajes de preferencia.')

newpage(am);head(am,'Contexto territorial y oferta observada')
para(am,'El municipio de Monterrey, clave 19039, registró 1,142,994 habitantes y 329,095 viviendas habitadas en el Censo 2020 (INEGI, 2020). Son unidades y fecha históricas; no representan vehículos, compradores o demanda de 2026. El instrumento regional permite otros municipios, cuyas respuestas deberán analizarse por separado para mantener la delimitación municipal del proyecto.')
table(am,['Oferente y ubicación publicada','Servicios pertinentes','Acceso anunciado'],[
('Grease Monkey by Automart\nObispado\nFrancisco Garza Sada 2806, Deportivo Obispado','Aceite, afinación, frenos, suspensión, diagnóstico y mantenimiento preventivo. Catálogo de la red.','Sin cita; contacto por WhatsApp. Horarios por sucursal.'),
('Midas Ruiz Cortines\nRuiz Cortines 306 Pte., Mitras Centro','Diagnóstico por computadora, prevención, aceite, llantas, frenos y transmisión.','Formulario; proceso de diagnóstico, cotización, servicio y entrega.'),
('AutoCenter MTY Centro\nJosé María Arteaga 1450, Centro','Mecánica de gasolina y diésel, prevención, diagnóstico, refaccionaria y flotillas. Oferta del grupo.','Contacto web; anuncia recolección a domicilio.'),
('Pronto Autoservicio Gonzalitos\nGonzalitos 108, Vista Hermosa','Ficha de mantenimiento preventivo; la red anuncia afinación, frenos, llantas y reparación.','Reserva web y pago en sucursal; confirmar servicio en la sede.')
],[2.0,2.6,1.9])
para(am,'Fuentes: Automart (s. f.), Midas México (s. f.), AutoCenter MTY (s. f.) y Pronto Autoservicio (s. f.-a, s. f.-c). Consulta del 28/09/2026. El catálogo de una red no garantiza disponibilidad de cada servicio en cada establecimiento. La selección no constituye un censo de talleres ni permite estimar participación de mercado.')

newpage(am);head(am,'Competencia y alternativas de atención')
para(am,'La superposición de mantenimiento, diagnóstico y reparación indica que ofrecer esas categorías por sí solo no acredita una ventaja competitiva. El contacto digital también aparece en la oferta revisada. La agenda propuesta para AM Taller puede facilitar la operación, pero su utilidad para atraer clientes deberá comprobarse con usuarios y tiempos reales de respuesta. La comparación pertinente debe incluir alcance técnico, autorización del trabajo y claridad de la entrega.')
table(am,['Alternativa','Evidencia publicada','Interpretación'],[
('Agencia por marca\nMazda Gonzalitos','Distribuidor en Gonzalitos 296 Sur, San Jerónimo; cuenta con citas y mantenimiento programado.','Para propietarios de Mazda es una alternativa al taller independiente. No representa todo el parque vehicular.'),
('Taller móvil para flotillas\nPronto Autoservicio','Publica atención en instalaciones del cliente y rutas que incluyen Monterrey.','Puede reemplazar el traslado al taller fijo. Es otra modalidad del mismo oferente, no una empresa adicional.')
],[1.5,2.5,2.5])
para(am,'Fuentes: Mazda Motor de México (s. f.-a, s. f.-b) y Pronto Autoservicio (s. f.-b). La clasificación como sustitutos es una interpretación por modalidad de atención. No se observó qué alternativa prefieren los clientes ni con qué frecuencia la contratan.')
para(am,'No se identificó una tarifa homogénea para el diagnóstico definido en D18 y O06–O07 del instrumento previo. La inspección de cortesía asociada a un servicio no equivale a un diagnóstico independiente gratuito. Tampoco el tiempo asignado a una reserva prueba la duración del trabajo. Por ello, no se calcula precio promedio ni se afirma que AM Taller será más económico.')

newpage(am);head(am,'Demanda potencial y validación pendiente')
para(am,'El mercado de referencia se propone como personas adultas que deciden o comparten la contratación de atención para vehículos ligeros en Monterrey. La población censal no permite saber cuántas cumplen esos filtros. La demanda potencial permanece sin cuantificar: la presencia de establecimientos no demuestra necesidad insatisfecha, disposición a cambiar de proveedor ni presupuesto para comprar.')
table(am,['Variable','Dato real necesario','Decisión que apoyaría'],[
('Elegibilidad y territorio\nD01–D06','Edad elegible, decisión sobre vehículo, municipio, tipo y uso; filtros y folio anónimo.','Delimitar a quiénes describen las respuestas.'),
('Necesidad y compra previa\nD07–D11','Servicio, frecuencia, gasto y satisfacción; denominador válido por pregunta.','Priorizar servicios y comparar importes de igual alcance.'),
('Elección y acceso\nD12–D17','Factores, canal, horario y traslado aceptable; sin inducir la marca.','Diseñar recepción, ubicación y comunicación.'),
('Intención y diagnóstico\nD18–D22','Valoración hipotética, necesidad próxima, apertura a proveedores y mejoras.','Formular hipótesis comerciales sin confundir intención con venta.'),
('Oferta comparable\nO01–O16','Ficha fechada por sucursal, alcance del diagnóstico y condiciones publicadas.','Comparar atributos; registrar no observable cuando falte información.')
],[1.65,2.8,2.05])
para(am,'El levantamiento propuesto en la actividad 5 es exploratorio, no una muestra ejecutada. Deben conservarse versión del cuestionario, fechas, modo de aplicación, selección, respuestas válidas, omisiones y duplicados. No se asigna margen de error probabilístico a una selección por conveniencia. Los resultados deberán contrastarse después con costos y capacidad.')

newpage(am);head(am,'Conclusiones y recomendaciones')
para(am,'La oferta documentada muestra alternativas de mantenimiento general, especialización por marca y atención móvil. Este resultado justifica comparar modalidades y definir el segmento inicial de AM Taller. No permite concluir que el mercado esté saturado o desatendido, ni que la propuesta sea rentable. La demanda sólo podrá estimarse con evidencia de compradores compatibles con el territorio y con el servicio definido.')
para(am,'Se recomienda especificar un paquete de entrada que distinga diagnóstico, mano de obra, refacciones, autorización y entrega. Para una futura comparación de precios deben mantenerse constantes tipo de vehículo, alcance, impuestos, vigencia y condiciones. Las afirmaciones sobre rapidez o garantía deberán corresponder a recursos y procedimientos que el proyecto pueda demostrar.')
para(am,'El paso siguiente es aplicar y depurar el instrumento de demanda, y completar las fichas de oferta con criterios uniformes. La tabulación utilizará frecuencias y denominadores explícitos, separará respuestas de otros municipios y conservará el carácter hipotético de la disposición a pagar. No se sumarán personas, viviendas y servicios como si fueran la misma unidad.')
para(am,'La investigación documental permite avanzar en la identificación de competidores y sustitutos, mientras el requisito de resultados del sondeo continúa pendiente. La decisión de abrir, fijar tarifas o proyectar ventas debe esperar la validación de necesidades, costos, recursos y capacidad. No se acredita apertura comercial ni contratación de proveedores.')
head(am,'Transparencia del trabajo')
para(am,'Se utilizó asistencia de inteligencia artificial para organizar fuentes públicas, estructurar la comparación y revisar la redacción. No se generaron respuestas de campo, cotizaciones recibidas ni datos de ventas. Las conclusiones conservan el alcance documental y las referencias permiten revisar su procedencia.')

questions(am,[
'¿Tiene 18 años o más y participa en decidir la atención de un vehículo ligero? Si no, terminar.',
'¿En qué municipio utiliza el vehículo? Registrar Monterrey y separar otros municipios.',
'¿Qué tipo y antigüedad tiene el vehículo elegido para responder?',
'¿Qué servicios requirió en los últimos doce meses: prevención, reparación, llantas o refacciones?',
'¿Cuántas visitas o compras realizó en ese periodo? Contar una vez cada ocasión.',
'¿Cuál fue la atención más reciente y cuánto pagó, indicando piezas, servicio e impuestos?',
'¿Qué tan satisfecho quedó: muy insatisfecho, insatisfecho, neutral, satisfecho o muy satisfecho?',
'¿Qué tres factores valora más: precio, confianza, cercanía, tiempo, garantía o disponibilidad?',
'¿Cómo busca establecimientos y por qué canal preferiría solicitar cita?',
'¿Qué horario y cuántos minutos de traslado de ida consideraría aceptables?',
'¿Qué monto pagaría por revisión visual, lectura compatible de códigos y explicación, sin reparación?',
'¿Prevé necesitar servicio en tres meses y consideraría un proveedor nuevo? Explicar por separado.'
],[
'¿Qué establecimiento o alternativa utilizó y por qué lo eligió? Evitar nombres de personas.',
'¿Qué servicios, ubicación, horario y canales anuncia cada proveedor? Registrar URL y fecha.',
'¿Publica un diagnóstico equivalente, su precio total, alcance y vigencia?',
'¿Qué autorización, garantía, plazo y modalidad de suministro comunica?',
'¿Qué elegiría entre taller independiente, agencia y atención móvil, y por qué?'
])
newpage(am);refs(am,[
('AutoCenter MTY','s. f.','Inicio','https://autocentermty.com.mx/',True),
('Automart','s. f.','Grease Monkey by Automart','https://www.automartgp.com/',True),
('Instituto Nacional de Estadística y Geografía','2020','Censo de Población y Vivienda 2020 Indicadores del municipio de Monterrey clave 19039','https://gaia.inegi.org.mx/wscatgeo/v2/mgem/19/039',True),
('Mazda Motor de México','s. f.-a','Mazda Gonzalitos','https://www.mazda.mx/distribuidores/mazda-gonzalitos',True),
('Mazda Motor de México','s. f.-b','Servicios y mantenimiento Mazda Gonzalitos','https://www.mazda.mx/distribuidores/mazda-gonzalitos/servicios/servicios-y-mantenimiento',True),
('Midas México','s. f.','Ruiz Cortinez','https://www.midas.com.mx/ruiz-cortinez',True),
('Pronto Autoservicio','s. f.-a','Mantenimiento preventivo','https://www.pronto-autoservicio.com/service-page/mantenimiento-preventivo-1',True),
('Pronto Autoservicio','s. f.-b','Taller móvil','https://www.pronto-autoservicio.com/taller-movil',True),
('Pronto Autoservicio','s. f.-c','Taller tradicional','https://www.pronto-autoservicio.com/taller-tradicional',True)
])

ir=base('Industrial Revolucionaria')
head(ir,'Propósito y resultado principal')
para(ir,'La revisión documental muestra proveedores de mantenimiento industrial con especialización por equipo y técnica en Monterrey. Se identificaron cinco oferentes y dos alternativas a la contratación de un prestador generalista. El resultado orienta a Industrial Revolucionaria a delimitar una familia de activos y un alcance técnico verificable. La información reunida no cuantifica contratos potenciales ni demuestra demanda insatisfecha.')
para(ir,'El caso continúa la descripción empresarial de la actividad 4: mantenimiento y soluciones industriales para micro, pequeñas y medianas empresas de Monterrey y su zona metropolitana. La oferta propuesta incluye diagnóstico, prevención, reparación y gestión de refacciones. El segmento inicial contempla organizaciones sin departamento especializado o que necesitan apoyo externo. No se acredita una empresa operando, cartera de clientes o capacidad instalada.')
head(ir,'Método de investigación documental')
para(ir,'El 28 de septiembre de 2026 se revisaron páginas propias de proveedores y una publicación de INEGI. Se seleccionaron intencionalmente oferentes que anuncian diagnóstico, mantenimiento o reparación de activos industriales y ubicación en Monterrey. Se compararon especialidad, modalidad de servicio y documentación anunciada. Las páginas permiten verificar publicaciones comerciales, no certificar desempeño, capacidad disponible o atención específica a MIPYMES.')
para(ir,'La consigna solicita preguntas, un Google Form enviado a por lo menos 30 personas y búsqueda de 5 a 10 empresas similares o sustitutas. Se documentan seis empresas distintas contando Atlas Copco. Las quince entrevistas propuestas antes no se realizaron ni sustituyen la nueva meta de distribución. El formulario, su envío y los resultados del sondeo siguen pendientes. La selección documental no es exhaustiva ni representativa estadísticamente.')

newpage(ir);head(ir,'Contexto productivo de referencia')
para(ir,'Los Censos Económicos 2024 identificaron 212,676 establecimientos en Nuevo León. Para el sector privado y empresas paraestatales, el comunicado registra 181,791 unidades económicas y 1,925,137 personas ocupadas con referencia a 2023. Las microempresas representan 89.3 % y las pymes 10.2 % de ese segmento; las manufacturas aportan 47.2 % del valor agregado censal bruto (INEGI, 2025, pp. 1–3).')
para(ir,'Los datos describen al estado, no sólo a los municipios del proyecto. Incluyen actividades ajenas al mantenimiento industrial y no indican cuántas empresas contratarían a Industrial Revolucionaria. El valor agregado censal bruto no es venta de servicios de mantenimiento ni PIB estatal. No procede multiplicar el total de unidades por una tarifa supuesta para calcular ingresos.')
head(ir,'Delimitación comercial propuesta')
para(ir,'El peso de la actividad manufacturera justifica explorar empresas con activos productivos, pero el marco de prospectos requiere precisar municipio, giro, tamaño, equipos y responsable de compra. La continuidad con el proyecto previo comprende Monterrey y una ampliación gradual a municipios metropolitanos condicionada a capacidad; esa cobertura sigue siendo una propuesta, no disponibilidad acreditada.')
para(ir,'La unidad de análisis será la organización que decide una contratación. Una planta puede contener varios equipos, recibir varios servicios y autorizar compras mediante distintas áreas; por tanto, empresa, activo, orden y contrato no deben contarse como equivalentes. Antes de elegir una muestra conviene definir qué necesidad se evaluará y quién conoce su historial técnico y presupuesto.')

newpage(ir);head(ir,'Oferentes industriales identificados')
table(ir,['Proveedor y ubicación publicada','Oferta anunciada relevante','Implicación analítica'],[
('Vibratek\nSantiago Tapia Ote. 1637, Monterrey','Vibraciones, diagnóstico de maquinaria, alineación láser, balanceo y monitoreo.','Delimitar técnicas y herramientas propias; prever canalización especializada.'),
('FD Predictive\nIxtapa 501, Mitras Norte, Monterrey','Mantenimiento de motores, bombas y tableros; póliza con inventario, reporte y calendario.','Comparar inclusiones de refacciones y alcance de prevención y corrección.'),
('Industrias Lowe y ProMtto\nMonterrey','Mantenimiento y reparación de motores, variadores y bombeo; soporte de piezas.','Precisar familias de activos; no prometer una cobertura técnica indefinida.'),
('INDASA\nRío San Joaquín 2112, Bernardo Reyes, Monterrey','Montacargas y grúas viajeras; contratos anuales, eventos e historial por equipo.','Evaluar modalidades recurrentes y por evento, sin asumir preferencia del cliente.'),
('ConfiabilidadMX\nHilario Martínez 711, Nuevo Repueblo, Monterrey','Soluciones predictivas, equipos y capacitación en condición, vibraciones y termografía.','Reconocer oferta especializada y formación del personal del cliente.')
],[2.0,2.5,2.0])
para(ir,'Fuentes: Vibratek (s. f.), FD México (s. f.), Industrias Lowe (s. f.), INDASA (s. f.) y ConfiabilidadMX (s. f.-a, s. f.-b). Consulta del 28/09/2026. Las ubicaciones y los servicios son declaraciones de los prestadores; no se verificaron físicamente. No se observaron precios comparables ni se afirma que todos atiendan el mismo tamaño de cliente.')
para(ir,'La pluralidad de especialidades demuestra oferta anunciada, no saturación del mercado. Inventario, calendario e historial ya aparecen en propuestas competidoras; llevar una bitácora no basta para atribuir una ventaja exclusiva a Industrial Revolucionaria. Su valor dependería de exactitud, utilidad y cumplimiento comprobados.')

newpage(ir);head(ir,'Alternativas a la contratación generalista')
para(ir,'Una primera alternativa es resolver tareas con personal interno y comprar capacitación o diagnóstico puntual. Vibratek y ConfiabilidadMX publican formación técnica. A partir de esa oferta se infiere que una organización con personal, herramientas y procedimientos suficientes podría cubrir parte del trabajo sin contratar una póliza externa. No se ha medido cuántas MIPYMES poseen esa capacidad ni su costo relativo.')
para(ir,'Una segunda alternativa es acudir al fabricante o a su red especializada. Atlas Copco (s. f.) anuncia soporte y planes para aire comprimido, bombas de vacío y herramientas industriales. Para determinados activos, ese servicio puede sustituir al proveedor generalista. La cobertura local, compatibilidad, garantía y costo deben verificarse caso por caso; no se asume que el fabricante sea siempre más costoso o mejor.')
head(ir,'Criterios para una comparación útil')
para(ir,'La comparación futura debe basarse en el mismo inventario y alcance: activos incluidos, frecuencia, pruebas, entregables, refacciones, mano de obra, traslados, impuestos, exclusiones y ventanas de atención. Una cuota anual y una reparación por evento no son precios intercambiables. Tampoco una promesa publicada de respuesta demuestra su cumplimiento.')
para(ir,'Se propone una oferta inicial complementaria al personal del cliente, concentrada en una familia de activos que el equipo pueda atender con competencia acreditable. El diagnóstico, la autorización de intervenciones y los criterios de cierre deberán quedar documentados. La selección definitiva de activos y modalidad comercial depende de entrevistas y evaluación de recursos; no se presenta como resultado probado de preferencia del mercado.')

newpage(ir);head(ir,'Demanda potencial y evidencia pendiente')
para(ir,'La demanda permanece sin cuantificar. La presencia industrial estatal y los servicios anunciados no revelan intención de contratar, presupuesto o frecuencia de mantenimiento externalizado. La siguiente matriz organiza el levantamiento propuesto con responsables de operaciones, mantenimiento o compras, conservando confidencialidad y evitando datos personales innecesarios.')
table(ir,['Variable','Evidencia requerida','Uso en la decisión'],[
('Segmento y activos','Municipio, giro, tamaño, inventario pertinente y criticidad de equipos.','Definir prospectos comparables y límites de cobertura.'),
('Necesidad y externalización','Fallas, trabajos programados, tareas internas y servicios externos realmente contratados.','Elegir especialidad y modalidad de apoyo.'),
('Compra B2B','Responsables, criterios, autorización, documentación y condiciones de pago.','Diseñar cotización y proceso de contratación.'),
('Gasto comparable','Importes de igual alcance y periodo; mano de obra, piezas e impuestos separados.','Evaluar precio junto con costos propios, sin mezclar contratos.'),
('Proveedor actual e intención','Razones de elección, problemas concretos y disposición a evaluar alternativas.','Formular hipótesis; una intención no equivale a contrato.'),
('Capacidad del proyecto','Competencias, equipos, tiempos, seguridad y costos acreditables.','Evitar promesas superiores a recursos disponibles.')
],[1.4,2.8,2.3])
head(ir,'Conclusión')
para(ir,'Se recomienda delimitar activos, documentar entregables y validar la compra B2B antes de proyectar contratos. El informe aporta identificación de oferta y sustitutos; no demuestra rentabilidad. Deben aplicarse las entrevistas, registrar su selección y analizar evidencia sin extrapolación automática. Se utilizó asistencia de inteligencia artificial para organizar fuentes y redacción, sin generar respuestas de campo ni cotizaciones.')

questions(ir,[
'¿Participa en decisiones de mantenimiento, operaciones o compras de la empresa? Si no, terminar.',
'¿En qué municipio y actividad opera la empresa y cuál es su rango de personal?',
'¿Qué familias de equipos requieren atención y cuáles son críticas para la operación?',
'¿Qué mantenimiento preventivo o correctivo requirió en los últimos doce meses?',
'¿Qué tareas realiza su personal y cuáles contrata externamente? Registrar por separado.',
'¿Con qué frecuencia contrata servicios externos y cuál fue el más reciente?',
'¿Qué incluyó ese servicio y cuánto pagó, separando piezas, mano de obra e impuestos si los conoce?',
'¿Qué problemas encontró en tiempos, diagnóstico, documentación o seguimiento?',
'¿Qué criterios pesan al elegir proveedor y qué área autoriza la contratación?',
'¿Qué documentos, condiciones de pago y ventanas operativas debe cumplir un proveedor?',
'¿Qué activos requerirán atención en tres meses y qué presupuesto está autorizado, si puede informarlo?',
'¿Evaluaría un proveedor nuevo y bajo qué condiciones, sin asumir compromiso de compra?'
],[
'¿Qué modalidad utiliza: personal interno, proveedor independiente, fabricante o combinación?',
'¿Qué proveedores conoce y qué servicios anuncia cada uno? Registrar fuente y fecha.',
'¿Qué equipos, técnicas, cobertura y entregables incluye la oferta observada?',
'¿Qué refacciones, traslados, impuestos, exclusiones y plazos incluye una cotización comparable?',
'¿Qué motivo llevaría a mantener o cambiar su modalidad actual de mantenimiento?'
])
newpage(ir);refs(ir,[
('Atlas Copco','s. f.','Servicio y asistencia técnica','https://www.atlascopco.com/es-mx/service',True),
('ConfiabilidadMX','s. f.-a','Capacitación','https://confiabilidadmx.com/capacitacion/',True),
('ConfiabilidadMX','s. f.-b','Soluciones integrales de mantenimiento predictivo','https://confiabilidadmx.com/',True),
('FD México','s. f.','FD Predictive','https://www.fdmexico.com/fd-predictive/',True),
('INDASA','s. f.','Mantenimiento y proyectos industriales','https://www.indasamty.com/',True),
('Industrias Lowe','s. f.','Nosotros','https://www.industriaslowe.com/nosotros/',True),
('Instituto Nacional de Estadística y Geografía','2025, 24 de julio','Censos Económicos 2024 Resultados definitivos Nuevo León (Comunicado 98/25; cifras corregidas)','https://www.inegi.org.mx/contenidos/saladeprensa/boletines/2025/ce/CE_2024_Def_NL.pdf',False),
('Vibratek','s. f.','Servicios de monitoreo de maquinaria industrial','https://vibratek.mx/',True)
])

out=[]
for doc,name in [(am,'AM-Taller'),(ir,'Industrial-Revolucionaria')]:
    path=COURSE/f'reporte-plan-de-negocios-Actividad-10-{name}.docx'
    doc.save(path);out.append(str(path))
assert sha256(REF.read_bytes()).hexdigest()==ref_hash
(ROOT/'.tmp-itesca-20260928/artifact-mercados.md').write_text(f'''# Contrato de los informes de mercados

Referencia conservada: {REF}
SHA256: {ref_hash}
Página carta, una sección, márgenes 2.54 cm. Cuerpo Arial 12 e interlineado 1.5 de Normal. Se preservan estilos, imagen y estructura institucional inicial. Encabezados negros con estilos reales de referencia. Se conserva el logo del párrafo 0, los párrafos institucionales 1 a 3 y el salto de página 8; se editan únicamente título 4, caso 5, alumno y docente 6, fecha 7. El cuerpo 9 en adelante se sustituye en copias con análisis específico. Tablas nuevas con anchos deliberados, Arial 10.5, bordes grises y cabecera repetida. Referencias con sangría francesa. Los dos documentos tienen siete saltos de página deliberados; objetivo ocho páginas por caso, sujeto a render.

Referencia original inalterada por hash. Root realizará render y revisión visual integral antes de entregar. No se ha acreditado todavía la paginación renderizada.
''',encoding='utf-8')
print('\n'.join(out))
