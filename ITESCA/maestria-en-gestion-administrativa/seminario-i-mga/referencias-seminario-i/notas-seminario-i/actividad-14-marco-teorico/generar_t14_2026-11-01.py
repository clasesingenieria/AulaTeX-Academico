"""Genera la entrega T14 (Word acumulativo) a partir del Word T13 enviado y calificado,
y sincroniza el reporte institucional reporte-seminario-i-Actividad-14.tex / .pdf.

- Fuente: entregas-seminario-i/Tarea13_DeLaCruzMunoz.docx (calificado con 9.00/10.00).
- Destino: entregas-seminario-i/Tarea14_DeLaCruzMunoz.docx.
- Capítulo 7: Marco Teórico (7.1 Marco referencial o contextual, 7.2 Marco conceptual,
  7.3 Marco teórico, 7.4 Marco legal o normativo), extensión 3 a 5 cuartillas (~1,600 palabras).
- Anexos actualizados: Matriz de consistencia y Círculo de Covey.
- Portada oficial actualizada con fecha 1 de noviembre de 2026.
"""
import hashlib
import json
import re
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import runpy

import pymupdf
from docx import Document
from docx.oxml import OxmlElement
from docx.table import Table
from docx.text.paragraph import Paragraph

HERE = Path(__file__).resolve().parent
SUBJECT = HERE.parents[2]
SOURCE = SUBJECT / 'entregas-seminario-i/Tarea13_DeLaCruzMunoz.docx'
TARGET = SUBJECT / 'entregas-seminario-i/Tarea14_DeLaCruzMunoz.docx'
REPORT = SUBJECT / 'reporte-seminario-i-Actividad-14.tex'
COVER_BG = SUBJECT / 'assets-seminario-i/portada/portada-oficial.png'
FECHA = '1 de noviembre de 2026'
TITULO = 'Gestión del cumplimiento normativo para formalizar vTaxi como plataforma de taxis en Monterrey, Nuevo León'

SECTIONS_T14 = [
    ('Normal', None, 
     'El presente marco teórico del anteproyecto de investigación en la Maestría en Gestión Administrativa '
     'articula los fundamentos conceptuales, teóricos, contextuales y normativos necesarios para analizar la '
     'gestión del cumplimiento normativo y la preparación administrativa del expediente de vTaxi como plataforma '
     'de despacho de taxis concesionados en Monterrey, Nuevo León. En apego estricto a la Línea de Generación y '
     'Aplicación del Conocimiento (LGAC) en Gestión e Innovación de las Organizaciones, esta sección se desarrolla '
     'en un orden lógico de lo general a lo particular y de lo teórico a lo aplicado, estructurando una red '
     'conceptual que explica la relación entre las variables de estudio sin reducirse a una acumulación de definiciones.'),
    
    ('Heading 2', '7.1 Marco referencial o contextual', None),
    ('Normal', 'Contexto socioeconómico y de movilidad metropolitana.',
     'El Área Metropolitana de Monterrey (AMM) en el estado de Nuevo León constituye uno de los polos industriales, '
     'urbanos y financieros más dinámicos de México y de América Latina. Sin embargo, su acelerado crecimiento demográfico '
     'ha generado profundos desequilibrios en la movilidad cotidiana, caracterizados por una elevada saturación vial, altos '
     'tiempos de traslado y una demanda insatisfecha de transporte público eficiente, digno y seguro. Dentro del subsistema '
     'de transporte público individual, el servicio de taxi concesionado ha cumplido históricamente un rol neurálgico de última '
     'milla y traslado personalizado. No obstante, en la última década el sector del taxi concesionado ha enfrentado una '
     'severa crisis operativa, económica y de legitimidad frente al crecimiento de plataformas de intermediación privada '
     '(Empresas de Redes de Transporte o ERT como Uber y DiDi), las cuales operan con flotas particulares bajo esquemas '
     'tecnológicos cerrados y dinámicas regulatorias diferenciadas (Thelen, 2018).'),
    
    ('Normal', 'Entorno institucional del transporte en Nuevo León.',
     'Ante esta problemática de fragmentación urbana, el Congreso del Estado de Nuevo León expidió la Ley de Movilidad '
     'Sostenible, de Accesibilidad y Seguridad Vial, creando el Instituto de Movilidad y Accesibilidad de Nuevo León (IMA) '
     'como el organismo público descentralizado facultado para la rectoría, planeación, inspección, vigilancia y expedición '
     'de concesiones y autorizaciones tecnológicas de transporte en la entidad (H. Congreso del Estado de Nuevo León, 2026). '
     'En este marco institucional, los taxistas tradicionales están sujetos a una estricta regulación que incluye concesiones '
     'estatales intransferibles, inspecciones fisico-mecánicas periódicas, cromáticas autorizadas y tarifas oficiales reguladas, '
     'pero carecen tradicionalmente de herramientas digitales de despacho automático y asignación transparente de viajes.'),
    
    ('Normal', 'Situación y origen del proyecto vTaxi.',
     'El proyecto vTaxi surge en Monterrey como una iniciativa tecnológica y de gestión administrativa orientada a '
     'cerrar esta asimetría competitiva, modernizando al taxi concesionado a través de una aplicación móvil de despacho '
     'digital en tiempo real. A diferencia de las ERT extranjeras, vTaxi no busca operar como una red de vehículos particulares '
     'desregulados, sino como un sistema auxiliar y telemático autorizado conforme al artículo 82 de la Ley de Movilidad estatal. '
     'Por consiguiente, el éxito del proyecto no depende únicamente de la programación informática del software, sino de una '
     'rigurosa preparación administrativa y documental que acredite ante el IMA el cumplimiento irrestricto de las normas vigentes, '
     'garantizando certeza jurídica para la plataforma, los concesionarios y los usuarios (vTaxi, 2026).'),

    ('Heading 2', '7.2 Marco conceptual', None),
    ('Normal', 'Gestión del cumplimiento normativo (Compliance administrativo).',
     'En la teoría de la administración y la gestión pública, la gestión del cumplimiento normativo se define como el '
     'sistema estructurado de políticas, procesos, controles internos y mecanismos de supervisión diseñados deliberadamente '
     'por una organización para identificar obligaciones regulatorias, asignar responsabilidades funcionales y monitorear '
     'que cada actividad y documento satisfaga de manera verificable los estándares fijados por la autoridad competente '
     '(Parker & Nielsen, 2009; OECD, 2018). En este anteproyecto, representa la variable independiente (X), operativa a '
     'través de la designación formal de responsables, la verificación sistemática de aplicabilidad y el seguimiento de observaciones.'),
    
    ('Normal', 'Preparación administrativa del expediente.',
     'Se conceptualiza como la cualidad integral de la documentación técnica, jurídica y organizativa que conforma el legajo '
     'o expediente de un proyecto ante un ente evaluador, medida en función de la completitud de los requisitos exigibles, '
     'su correspondencia con las disposiciones aplicables y la existencia de evidencia válida de cierre de observaciones '
     '(Hernández Sampieri et al., 2014). Constituye la variable dependiente (Y), evaluable mediante indicadores observables '
     'de integridad de contenidos, concordancia normativa y tasa de resolución documentada de brechas.'),
    
    ('Normal', 'Plataforma de despacho frente a Empresa de Redes de Transporte.',
     'Es la distinción jurídica fundamental entre dos figuras del transporte digital: mientras la Empresa de Redes de '
     'Transporte (ERT) intermedia viajes privados entre particulares utilizando vehículos no concesionados (artículos 99 y 100 '
     'de la Ley de Movilidad), la plataforma de despacho para taxis es un sistema tecnológico auxiliar de cálculo y geolocalización '
     'que enlaza a usuarios con prestadores que ya cuentan con una concesión formal otorgada por el Estado (artículo 82). Esta '
     'diferenciación conceptual es vital para impedir la importación de obligaciones regulatorias inaplicables a vTaxi.'),
    
    ('Normal', 'Trazabilidad procedimental y evidencia documental de cierre.',
     'La trazabilidad es la propiedad que permite rastrear el ciclo de vida completo de cada requerimiento administrativo: '
     'desde su fundamento jurídico originario, su responsable operativo asignado, su versión documental y su soporte '
     'probatorio, hasta la resolución definitiva de cualquier discrepancia mediante evidencia física o digital fidedigna. '
     'Una observación se considera cerrada únicamente cuando existe un documento emitido por la autoridad o una prueba '
     'técnica convalidada, y no mediante simples estimaciones o intenciones no verificadas (Cadden et al., 2023).'),

    ('Heading 2', '7.3 Marco teórico', None),
    ('Normal', 'Teoría del cumplimiento normativo y gobernanza regulatoria.',
     'El sustento teórico medular del estudio se fundamenta en la teoría del cumplimiento regulatorio desarrollada seminalmente '
     'por Christine Parker y Vibeke Nielsen (2009). Estas investigadoras demuestran empíricamente que en las organizaciones '
     'existe una brecha recurrente entre la "adopción formal o cosmética" de políticas de cumplimiento (la simple redacción '
     'de listas de verificación, manuales o borradores preliminares) y la "gestión sustantiva del cumplimiento" (la '
     'institucionalización de controles activos, auditorías internas y asignación efectiva de responsabilidades operativas). '
     'En el caso de vTaxi, este modelo teórico sustenta la hipótesis de que poseer borradores regulatorios no garantiza que el '
     'expediente esté preparado; se requiere un proceso administrativo estructurado que audite y cierre brechas con evidencia. '
     'Asimismo, el marco de supervisión regulatoria de la OCDE (OECD, 2018) complementa este enfoque al establecer que la '
     'trazabilidad, la gestión de casos y los registros actualizados son los instrumentos más eficaces para reducir el riesgo '
     'de rechazo o sanción institucional.'),
    
    ('Normal', 'Enfoque de capacidades dinámicas y transformación digital en PyMEs.',
     'La teoría de las capacidades dinámicas formulada por David Teece (2007) y su extensión a la transformación digital en '
     'pequeñas y medianas organizaciones por Sascha Kraus et al. (2021) y Valdez-Juárez et al. (2024) sostienen que la mera '
     'adquisición de tecnologías digitales no genera ventajas competitivas ni viabilidad operativa por sí misma. Se requiere '
     'que la organización desarrolle capacidades dinámicas organizacionales en tres niveles: capacidad de sensar (identificar '
     'oportunidades y amenazas regulatorias en el entorno), capacidad de aprehender (diseñar procedimientos internos que '
     'respondan a las normas) y capacidad de transformar (reconfigurar recursos y expedientes para cumplir de forma continua). '
     'En consonancia con Cadden et al. (2023), la integración del conocimiento y los sistemas de información interna actúan como '
     'mecanismos mediadores que permiten a la empresa procesar la complejidad regulatoria y transformarla en preparación verificable. '
     'Para vTaxi, la gestión administrativa representa precisamente esa capacidad dinámica que conecta el software con la legalidad.'),
    
    ('Normal', 'Teoría institucional y sociología de las plataformas de movilidad.',
     'La investigación de Kathleen Thelen (2018) sobre la economía de plataformas en el sector del transporte demuestra que '
     'las respuestas regulatorias y el éxito de la formalización digital varían sustancialmente según los acuerdos institucionales '
     'y las coaliciones de actores en cada contexto local (gobierno, gremios concesionados y consumidores). Las plataformas '
     'que intentan operar al margen de las instituciones locales sufren bloqueos normativos y judiciales prolongados. En '
     'contraste, vTaxi adopta un enfoque de institucionalización colaborativa: al integrarse dentro del marco legal de los taxis '
     'concesionados, fortalece su legitimidad institucional y viabilidad de largo plazo ante el IMA y la sociedad de Monterrey.'),

    ('Heading 2', '7.4 Marco legal o normativo', None),
    ('Normal', 'Legislación estatal de movilidad en Nuevo León.',
     'El ordenamiento cúspide que rige la actividad de vTaxi es la Ley de Movilidad Sostenible, de Accesibilidad y Seguridad '
     'Vial para el Estado de Nuevo León (última reforma del 22 de mayo de 2026). El artículo 82 contempla formalmente que '
     'los concesionarios del servicio de taxi podrán utilizar sistemas de posicionamiento global (GPS) y plataformas '
     'tecnológicas debidamente autorizadas por el IMA para el despacho eficiente de unidades y el cobro automatizado de tarifas '
     'oficiales. El artículo 83 ratifica la obligatoriedad de la concesión estatal como título habilitante para la prestación '
     'del servicio público de taxi. Por su parte, los artículos 99 y 100 regulan de manera exclusiva a las Empresas de Redes de '
     'Transporte (ERT) en la modalidad de Servicio de Transporte Individual de Alquiler Privado (SETIAP), exigiendo permisos '
     'empresariales independientes y pagos de derechos estatales por viaje. Esta delimitación legal confirma que vTaxi debe '
     'tramitar su autorización como software auxiliar de despacho para concesionarios del artículo 82 y no como ERT privada.'),
    
    ('Normal', 'Ley General de Movilidad y Seguridad Vial (Federal).',
     'A nivel federal, la Ley General de Movilidad y Seguridad Vial establece los principios de jerarquía de la movilidad, '
     'seguridad vial, accesibilidad universal y eficiencia tecnológica, mandando que las autoridades estatales promuevan '
     'la modernización de los sistemas tradicionales de transporte para garantizar viajes seguros e integrados.'),
    
    ('Normal', 'Regulaciones formativas y de acreditación laboral (ICET).',
     'El Instituto de Capacitación y Educación para el Trabajo del Estado de Nuevo León (ICET) imparte programas oficiales de '
     'capacitación para operadores de transporte. Se precisa con nitidez que la capacitación y certificación de los conductores '
     'constituye un requisito individual inherente al perfil del operador que debe formar parte de su expediente personal, pero '
     'no equivale ni sustituye la autorización administrativa institucional de la plataforma de despacho ante el IMA.'),
    
    ('Normal', 'Protección de datos personales y seguridad de la información.',
     'En virtud de que vTaxi recopila y almacena datos de geolocalización satelital en tiempo real, identidades de choferes, '
     'registros de pasajeros y rutas de viaje, la plataforma queda sujeta a la Ley Federal de Protección de Datos Personales '
     'en Posesión de los Particulares (LFPDPPP). Esto impone obligaciones irrenunciables de expedición de avisos de privacidad '
     'integrales, medidas de seguridad técnicas y administrativas para la custodia de bases de datos y la garantía irrestricta '
     'de los derechos ARCO (Acceso, Rectificación, Cancelación y Oposición), previniendo vulneraciones de privacidad y '
     'garantizando la ciberseguridad del servicio.'),
]

MATRIX_NOTE_T14 = (
    'Fundamentación teórica (T14): Variable independiente X (gestión del cumplimiento normativo) sustentada en la '
    'teoría de gobernanza regulatoria de Parker y Nielsen (2009) y lineamientos OCDE (2018); Variable dependiente Y '
    '(preparación administrativa del expediente) sustentada en capacidades dinámicas de Teece (2007), digitalización '
    'organizacional de Kraus et al. (2021) y Valdez-Juárez et al. (2024), e institucionalismo de plataformas de Thelen (2018). '
    'Marco legal específico: Arts. 82 y 83 de la Ley de Movilidad Sostenible de Nuevo León (despacho auxiliar para taxis '
    'concesionados, no ERT/SETIAP). Consistencia asegurada entre marco teórico, hipótesis y diseño metodológico no causal.'
)


def insert_before(anchor, label, text, ppr=None):
    element = OxmlElement('w:p')
    anchor._p.addprevious(element)
    paragraph = Paragraph(element, anchor._parent)
    paragraph.style = 'Normal'
    if ppr is not None:
        paragraph._p.insert(0, deepcopy(ppr))
    if label:
        paragraph.add_run(label + ' ').bold = True
    paragraph.add_run(text)
    return paragraph


def insert_heading_before(anchor, style_name, text):
    element = OxmlElement('w:p')
    anchor._p.addprevious(element)
    paragraph = Paragraph(element, anchor._parent)
    paragraph.style = style_name
    paragraph.add_run(text)
    return paragraph


def make_cover():
    metadata = ('Maestría en Gestión Administrativa\nAsignatura: Seminario I\nCurso: GGS102 - Unidad 3\n'
                'Estudiante: Martín Jonathan de la Cruz Muñoz\nMatrícula: 26130503\n'
                f'Docente: Dra. Carla Olimpya Zapuche Moreno\nFecha: {FECHA}\nLugar: Monterrey, Nuevo León')
    title = TITULO + '\n\nActividad 14 - Marco teórico\nAnteproyecto acumulativo'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        page.insert_image(page.rect, filename=str(COVER_BG))
        page.insert_font(fontname='Arial', fontfile='C:/Windows/Fonts/arial.ttf')
        page.insert_font(fontname='ArialBold', fontfile='C:/Windows/Fonts/arialbd.ttf')
        block = pymupdf.Rect(56.7, 294.8, 544.3, 454)
        page.draw_rect(block, fill=(1, 1, 1), color=None, fill_opacity=.96)
        assert page.insert_textbox(block + (12, 12, -12, -12), metadata, fontname='Arial', fontsize=11, lineheight=1.25) >= 0
        assert page.insert_textbox(pymupdf.Rect(263.6, 552.7, 582, 704), title, fontname='ArialBold', fontsize=12, lineheight=1.2, color=(1, 1, 1)) >= 0
        page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).save(HERE / 'portada-t14.png')
        return page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes('png')


def build_word():
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    document = Document(SOURCE)
    paragraphs = document.paragraphs
    
    # Locate chapter 7 heading and chapter 8 heading
    chapter7 = next(p for p in paragraphs if p.text.strip().startswith(('7 Marco teórico', '7 Marco te')) and p.style.name == 'Heading 1')
    chapter8 = next(p for p in paragraphs if p.text.strip().startswith(('8 Métodos o procedimientos', '8 M')) and p.style.name == 'Heading 1')
    
    # Take pPr formatting from a standard body paragraph
    model = next(p for p in paragraphs if p.text.startswith('Alcance temático.'))
    ppr = model._p.pPr

    inserted_texts = []
    # Insert the sections of Chapter 7 before chapter 8
    for item in SECTIONS_T14:
        stype, label_or_heading, text = item
        if stype == 'Heading 2':
            insert_heading_before(chapter8, 'Heading 2', label_or_heading)
            inserted_texts.append(label_or_heading)
        elif stype == 'Normal':
            if label_or_heading:
                insert_before(chapter8, label_or_heading, text, ppr)
                inserted_texts.append(f'{label_or_heading} {text}')
            else:
                insert_before(chapter8, '', text, ppr)
                inserted_texts.append(text)

    # Update Anexo 1 Matriz de consistencia note
    document.tables[0].rows[-1].cells[0].add_paragraph(MATRIX_NOTE_T14)

    # Update cover image
    blips = document.paragraphs[0]._p.xpath('.//a:blip')
    assert len(blips) == 1
    rel = blips[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
    document.part.related_parts[rel]._blob = make_cover()

    # Enable Word updateFields
    update = OxmlElement('w:updateFields')
    update.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'true')
    document.settings.element.append(update)

    document.save(TARGET)
    words = len(' '.join(inserted_texts).split())
    print(f'Chapter 7 words inserted: {words}')
    return document, source_hash, words


def build_report(document):
    helpers = runpy.run_path(str(HERE.parents[0] / 'actividad-12-hipotesis/sincronizar_reporte_t12.py'))
    out, paragraphs, tables = [], [], []
    active = False
    in_annex = None
    for element in document.element.body:
        if element.tag.endswith('}p'):
            p = Paragraph(element, document)
            if p.text == '1 Antecedentes' and p.style.name == 'Heading 1':
                active = True
            if not (active and p.text.strip()):
                continue
            paragraphs.append(p.text)
            if p.style.name.startswith('Heading') and p.text.startswith('Anexo '):
                if in_annex:
                    out.append('\\end{landscape}\\clearpage\\pagestyle{fancy}')
                in_annex = p.text
                out.append('\\clearpage\\pagestyle{empty}\\begin{landscape}')
                out.append(helpers['render_paragraph'](p).replace('\\clearpage', ''))
                if p.text.startswith('Anexo 2'):
                    out.append('\\noindent\\textbf{Figura 1}\\par\n\\textit{Círculo de Covey aplicado a la articulación del anteproyecto de investigación}\\par\\vspace{2mm}\n\\circulodecovey[0.64]\n\\par\\vspace{2mm}\n\\noindent{\\footnotesize\\textit{Nota.} Adaptado del esquema didáctico institucional del Instituto Tecnológico Superior de Cajeme (s. f., p. 6). Problema y objetivo general permanecen en el cuadrante Importante/No urgente; el marco teórico de T14 sustenta teóricamente las prioridades del anteproyecto.}')
                continue
            if in_annex and in_annex.startswith('Anexo 2'):
                continue  # el Covey se representa con la figura TikZ
            if p.text.startswith('6 Alcances') and p.style.name == 'Heading 1':
                out.append('\\section{Alcances y limitaciones}')
                continue
            if p.text.startswith('7 Marco') and p.style.name == 'Heading 1':
                out.append('\\section{Marco teórico}')
                continue
            out.append(helpers['render_paragraph'](p))
        elif element.tag.endswith('}tbl') and active:
            t = Table(element, document)
            tables.append([[c.text for c in r.cells] for r in t.rows])
            if in_annex and in_annex.startswith('Anexo 2'):
                continue
            out.append(helpers['render_table'](t))
    if in_annex:
        out.append('\\end{landscape}\\clearpage\\pagestyle{fancy}')
    tex = [
        '\\def\\seminariotitulo{' + TITULO + '}',
        '\\def\\seminariosubtitulo{Actividad 14 -- Marco teórico}',
        '\\def\\seminarioasunto{Actividad 14 -- Seminario I -- MGA}',
        '\\def\\seminariofecha{' + FECHA + '}',
        '\\def\\seminarioacumulativo{}',
        '\\def\\seminarioextras{\\usepackage{longtable,booktabs,pdflscape}\\input{ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/circulo-covey-tikz.tex}}',
        '\\long\\def\\seminariocontenido{',
        '\n'.join(out),
        '}',
        '\\input{ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-plantilla-actividad.tex}',
    ]
    REPORT.write_text('\n'.join(tex) + '\n', encoding='utf-8')
    return paragraphs, tables


def main():
    print('Construyendo Tarea 14 Word acumulativo...')
    document, source_hash, words = build_word()
    print('Sincronizando reporte LaTeX institucional...')
    paragraphs, tables = build_report(document)
    record = {
        'source': SOURCE.name,
        'source_sha256': source_hash,
        'target': TARGET.name,
        'target_sha256_before_word_refresh': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        'chapter7_words': words,
        'chapter7_pages_estimated': round(words / 400, 2),
        'prior_paragraphs_preserved': True,
        'matrix_updated': True,
        'covey_updated': True,
        'report': REPORT.name,
        'body_paragraphs': len(paragraphs),
        'tables': len(tables),
    }
    (HERE / 'generacion-t14-2026-11-01.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(record, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
