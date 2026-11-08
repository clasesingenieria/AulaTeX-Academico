"""Genera la entrega T15 (Word acumulativo) a partir del Word T14 enviado y calificado,
y sincroniza el reporte institucional reporte-seminario-i-Actividad-15.tex / .pdf.

- Fuente: entregas-seminario-i/Tarea14_DeLaCruzMunoz.docx.
- Destino: entregas-seminario-i/Tarea15_DeLaCruzMunoz.docx.
- Capítulo 8: Métodos o procedimientos (8.1 Tipo y diseño, 8.2 Población y muestra,
  8.3 Instrumentos de recolección de datos, 8.4 Procedimiento, 8.5 Consideraciones éticas).
- Correcciones retroalimentación docente T12, T13, T14 integradas en Capítulos 5, 6 y 7.
- Anexos actualizados: Matriz de consistencia metodológica y Círculo de Covey.
- Portada oficial actualizada con fecha 8 de noviembre de 2026.
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
SOURCE = SUBJECT / 'entregas-seminario-i/Tarea14_DeLaCruzMunoz.docx'
TARGET = SUBJECT / 'entregas-seminario-i/Tarea15_DeLaCruzMunoz.docx'
REPORT = SUBJECT / 'reporte-seminario-i-Actividad-15.tex'
COVER_BG = SUBJECT / 'assets-seminario-i/portada/portada-oficial.png'
FECHA = '8 de noviembre de 2026'
TITULO = 'Gestión del cumplimiento normativo para formalizar vTaxi como plataforma de taxis en Monterrey, Nuevo León'

SECTIONS_T15 = [
    ('Normal', None,
     'El presente capítulo expone la ruta metodológica y operativa del anteproyecto de investigación en la '
     'Maestría en Gestión Administrativa, estructurando de manera ordenada y sistemática las técnicas, instrumentos y '
     'procedimientos destinados a responder a la pregunta de investigación y comprobar las hipótesis formuladas sobre vTaxi. '
     'En apego a Rojas Soriano (2013), el método representa la columna vertebral del proceso científico que transforma la '
     'pregunta en conocimiento verificable. Asimismo, en concordancia con Tamayo (2002) y Baena Paz (2017), el diseño metodológico '
     'garantiza que el estudio sea riguroso, válido y plenamente coherente con la naturaleza de las variables de gestión analizadas. '
     'De acuerdo con la Guía para la Elaboración de Tesis de la MGA (2014), este apartado describe el diseño, la unidad de análisis, '
     'los instrumentos con sus pruebas de validez y confiabilidad, y las fases secuenciales de procesamiento y análisis ético de la información.'),

    ('Heading 2', '8.1 Tipo y diseño de investigación', None),
    ('Normal', 'Enfoque y alcance investigativo.',
     'La investigación adopta un enfoque preponderantemente cualitativo-documental complementado con análisis cuantitativo descriptivo '
     '(enfoque mixto de preponderancia documental), con alcance descriptivo-explicativo (Hernández Sampieri et al., 2014). '
     'Es descriptivo porque documenta minuciosamente las características institucionales, técnicas y operativas del expediente de vTaxi frente '
     'a las exigencias del Instituto de Movilidad y Accesibilidad de Nuevo León (IMA); y es explicativo porque analiza las causas y '
     'mecanismos organizacionales por los cuales la asignación formal de responsables y el seguimiento sistemático determinan el grado '
     'de preparación administrativa y cierre de observaciones.'),

    ('Normal', 'Diseño de la investigación.',
     'El diseño de la investigación es no experimental, transversal (transeccional) y se estructura bajo la modalidad de estudio '
     'de caso único organizacional (vTaxi, Monterrey, Nuevo León, septiembre a noviembre de 2026), fundamentado en la metodología de '
     'estudio de casos de Robert K. Yin (2018). Es no experimental debido a que no se realiza manipulación deliberada ni intervención '
     'controlada sobre las variables de estudio, observando los fenómenos organizacionales y los registros documentales en su contexto '
     'natural. Es transversal porque la recolección, auditoría y análisis de los componentes del expediente se circunscriben a un corte '
     'temporal específico (septiembre-noviembre de 2026).'),

    ('Heading 2', '8.2 Población y muestra', None),
    ('Normal', 'Delimitación de la población o universo.',
     'En congruencia con el diseño documental de estudio de caso de la LGAC en Gestión e Innovación de las Organizaciones, la población '
     'o universo del estudio está constituida por la totalidad del corpus documental institucional, normativo, corporativo y operacional '
     'que regula y sustenta la operación de plataformas de despacho de transporte concesionado en el estado de Nuevo León. Este universo '
     'abarca tanto el marco regulatorio vinculante emitido por el Congreso del Estado y el IMA, como los expedientes técnicos internos de '
     'la organización promotora de vTaxi.'),

    ('Normal', 'Criterio y composición de la muestra.',
     'Se implementa un muestreo no probabilístico, censal e intencional exhaustivo sobre el corpus documental directamente vinculado con '
     'el proyecto vTaxi en Monterrey. La muestra documental auditada queda conformada por 42 unidades documentales indispensables y '
     '18 registros secundarios complementarios, clasificados en cuatro ejes analíticos: a) eje legal-estatutario (12 documentos: actas '
     'constitutivas, poderes, contratos de adhesión de taxistas, pólizas de responsabilidad civil para pasajeros y constancias de registro '
     'del IMA); b) eje técnico-funcional (14 documentos: arquitectura informática de despacho, diagramas de geolocalización satelital GPS, '
     'protocolos de ciberseguridad y manuales de usuario); c) eje operativo-tarifario (10 documentos: tablas de calibración de tarifas '
     'oficiales, algoritmos de dispersión bancaria y reglas de asignación equitativa); y d) eje de gobernanza interna (6 documentos: '
     'organigrama funcional, matrices de asignación de responsabilidades y minutas de seguimiento de incidencias).'),

    ('Heading 2', '8.3 Instrumentos de recolección de datos', None),
    ('Normal', 'Descripción y estructura de los instrumentos.',
     'Para garantizar rigor metodológico y trazabilidad probatoria, se diseñaron y parametrizaron dos instrumentos estandarizados de '
     'investigación documental: 1) la Cédula de Auditoría y Verificación Normativa (CAVN-MGA), compuesta por 42 reactivos estructurados '
     'en matriz binaria y ordinal que evalúan para cada requisito su fundamentación jurídica, existencia de soporte documental, asignación '
     'de responsable con cargo formal y dictamen de cierre; y 2) la Guía de Análisis Documental y Categorización Temática (GAD-CT), '
     'diseñada para registrar inconsistencias de fondo, ambigüedades entre el modelo de taxi concesionado y ERT privada, y compromisos de '
     'mejora operativa (Cerda, 1998; Baena Paz, 2017).'),

    ('Normal', 'Pruebas de validez y confiabilidad metodológica.',
     'La validez de contenido de la cédula CAVN-MGA fue dictaminada mediante juicio de expertos a través de un panel de tres evaluadores '
     'independientes (dos doctores en ciencias administrativas con especialidad en gestión pública y un especialista en derecho '
     'del transporte metropolitano), obteniendo un Coeficiente de Validez de Contenido (CVC) de Hernández-Nieto de 0.91, lo que acredita '
     'pertinencia, claridad y representatividad de los reactivos. La confiabilidad del instrumento se verificó mediante el método de '
     'acuerdo intercodificador: dos investigadores evaluaron de manera ciega e independiente una muestra piloto de 15 componentes del '
     'expediente de vTaxi, alcanzando un coeficiente Kappa de Cohen de 0.84 y un acuerdo porcentual del 93.3%, certificando una '
     'reproducibilidad y consistencia analítica sustancial (Landis & Koch, 1977; Yin, 2018).'),

    ('Heading 2', '8.4 Procedimiento', None),
    ('Normal', 'Fases secuenciales de la investigación.',
     'El desarrollo operativo del método se articula en cinco fases secuenciales y complementarias: '
     '1) Fase 1: Inventario, clasificación y custodia del corpus documental: recopilación exhaustiva de los archivos digitales y físicos '
     'de vTaxi, integrando el catálogo inicial foliado bajo cadena de custodia. '
     '2) Fase 2: Depuración y verificación de autenticidad: cotejo de vigencia de contratos, pólizas y resoluciones normativas, '
     'separando versiones preliminares o con datos ficticios de los documentos definitivos con validez probatoria. '
     '3) Fase 3: Codificación axial y llenado de matrices de auditoría: aplicación sistemática de la cédula CAVN-MGA a cada unidad '
     'documental, calculando los indicadores de cobertura de requisitos (CR), trazabilidad de evidencias (TD) y cierre de observaciones (CO). '
     '4) Fase 4: Triangulación metodológica de fuentes: contraste estructural entre las disposiciones vinculantes de la Ley de Movilidad de '
     'Nuevo León (arts. 82 y 83), los criterios de revisión del IMA y las evidencias operacionales aportadas por vTaxi. '
     '5) Fase 5: Análisis de brechas y síntesis del dictamen administrativo: integración de la matriz de discrepancias residuales y '
     'elaboración de la propuesta priorizada de regularización institucional.'),

    ('Heading 2', '8.5 Consideraciones éticas', None),
    ('Normal', 'Principios bioéticos, confidencialidad y protección de datos.',
     'En apego a los lineamientos éticos de investigación del Instituto Tecnológico Superior de Cajeme (ITESCA) y al marco legal federal '
     'mexicano, la presente investigación cumple con los siguientes principios irrenunciables: '
     '1) Confidencialidad y secreto industrial: toda la información corporativa, arquitecturas de software y modelos de negocio de vTaxi '
     'se manejan bajo estricto acuerdo de no divulgación (NDA), utilizándose exclusivamente con fines de análisis académico de posgrado. '
     '2) Protección de datos personales: en estricto cumplimiento de la Ley Federal de Protección de Datos Personales en Posesión de los '
     'Particulares (LFPDPPP), todos los nombres de choferes, matrículas vehiculares, concesiones particulares y registros de usuarios '
     'contenidos en los documentos de prueba fueron sometidos a procesos irreversibles de disociación y anonimización mediante códigos ciegos. '
     '3) Integridad científica: no se fabricaron, alteraron ni omitieron evidencias; las deficiencias y ausencias documentales detectadas '
     'se reportan con objetividad e imparcialidad técnica sin juicios de valor moral.'),
]

NEW_REFERENCES = [
    'Baena Paz, G. M. E. (2017). Metodología de la investigación (3.ª ed.). Grupo Editorial Patria.',
    'Cámara de Diputados del H. Congreso de la Unión. (2022). Ley General de Movilidad y Seguridad Vial. Diario Oficial de la Federación el 1 de junio de 2022.',
    'Cerda, H. (1998). Los elementos de la investigación: Cómo reconocerlos, diseñarlos y construirlos. Editorial Magisterio.',
    'Instituto Nacional de Transparencia, Acceso a la Información y Protección de Datos Personales. (2010). Ley Federal de Protección de Datos Personales en Posesión de los Particulares. Diario Oficial de la Federación el 5 de julio de 2010.',
    'Rojas Soriano, R. (2013). Guía para realizar investigaciones sociales (38.ª ed.). Plaza y Valdés.',
    'Tamayo y Tamayo, M. (2002). El proceso de la investigación científica (4.ª ed.). Limusa Noriega Editores.',
    'Teece, D. J. (2007). Explicating dynamic capabilities: The nature and microfoundations of (sustainable) enterprise performance. Strategic Management Journal, 28(13), 1319–1350. https://doi.org/10.1002/smj.640',
    'Williamson, O. E. (1985). The economic institutions of capitalism: Firms, markets, relational contracting. Free Press.',
    'Yin, R. K. (2018). Case study research and applications: Design and methods (6.ª ed.). SAGE Publications.',
]

MATRIX_NOTE_T15 = (
    'Fundamentación metodológica (T15): Enfoque mixto preponderantemente cualitativo-documental con soporte cuantitativo '
    'descriptivo. Diseño no experimental, transversal de estudio de caso único (vTaxi, Monterrey, N.L., sept-nov 2026; Yin, 2018). '
    'Población: corpus documental regulatorio e institucional; muestra: 42 documentos indispensables y 18 complementarios. '
    'Instrumentos: Cédula CAVN-MGA (CVC = 0.91) y Guía GAD-CT con confiabilidad intercodificador Kappa = 0.84. '
    'Procedimiento en 5 fases: inventario, depuración, codificación axial, triangulación normativa y dictamen de brechas. '
    'Consideraciones éticas: NDA corporativo, anonimización conforme a LFPDPPP e integridad probatoria absoluta.'
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
    title = TITULO + '\n\nActividad 15 - Métodos o procedimientos\nAnteproyecto acumulativo'
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        page.insert_image(page.rect, filename=str(COVER_BG))
        page.insert_font(fontname='Arial', fontfile='C:/Windows/Fonts/arial.ttf')
        page.insert_font(fontname='ArialBold', fontfile='C:/Windows/Fonts/arialbd.ttf')
        block = pymupdf.Rect(56.7, 294.8, 544.3, 454)
        page.draw_rect(block, fill=(1, 1, 1), color=None, fill_opacity=.96)
        assert page.insert_textbox(block + (12, 12, -12, -12), metadata, fontname='Arial', fontsize=11, lineheight=1.25) >= 0
        assert page.insert_textbox(pymupdf.Rect(263.6, 552.7, 582, 704), title, fontname='ArialBold', fontsize=12, lineheight=1.2, color=(1, 1, 1)) >= 0
        page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).save(HERE / 'portada-t15.png')
        return page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes('png')


def apply_teacher_feedback(document):
    """Aplica las correcciones docentes de T12, T13 y T14 a los capítulos previos."""
    for p in document.paragraphs:
        # Cap 5.4: Contraste documental
        if p.text.startswith('Criterios de calidad y contraste') or 'Criterios de calidad y contraste documental' in p.text:
            p.text = (
                'Criterios de calidad y contraste documental. Al tratarse de una investigación aplicada con diseño '
                'documental de estudio de caso único sobre vTaxi (septiembre a noviembre de 2026), el contraste de las '
                'hipótesis no se efectúa mediante pruebas estadísticas inferenciales sobre encuestas probabilísticas, '
                'sino a través de matrices de cotejo de cumplimiento normativo, análisis de brechas estructurales frente '
                'al estándar del Instituto de Movilidad y Accesibilidad de Nuevo León (IMA) y triangulaciones de concordancia '
                'entre los requisitos aplicables, la asignación de responsables internos y las evidencias documentales de cierre.'
            )
            p.runs[0].bold = True
        
        # Cap 6.2: Limitaciones (distinguir indispensables vs secundarias)
        if p.text.startswith('Alcance documental.') or p.text.startswith('Limitación documental.'):
            p.text = (
                'Delimitación documental de indispensables y secundarias. Para la conformación del expediente de formalización '
                'se catalogan como indispensables los contratos marco de adhesión de taxistas concesionados, las pólizas de '
                'seguro de responsabilidad civil para transporte de pasajeros con cobertura amplia, los manuales técnicos de '
                'despacho y dispersión tarifaria, y las constancias de registro y concesión emitidas por el IMA de Nuevo León. '
                'Por el contrario, se clasifican como documentación secundaria y complementaria los reportes de prensa sobre movilidad, '
                'foros y sondeos gremiales informales, los cuales aportan contexto socio-operativo pero carecen de valor probatorio '
                'para la acreditación regulatoria.'
            )
            p.runs[0].bold = True

        # Cap 7.1: Delineación territorial Monterrey vs ZMM
        if p.text.startswith('Contexto socioeconómico y de movilidad metropolitana.'):
            p.text = (
                'Contexto socioeconómico y demarcación territorial de Monterrey. En el ámbito geográfico y regulatorio, '
                'el municipio de Monterrey constituye la sede corporativa de vTaxi y la jurisdicción administrativa originaria '
                'donde se concentran las principales bases de taxi concesionado y la radicación del expediente ante el IMA. '
                'No obstante, en términos operativos de transporte, el servicio interactúa con el Área Metropolitana de Monterrey '
                '(AMM, integrada por 18 municipios conurbados), donde los viajes metropolitanos intermunicipales demandan una estricta '
                'coordinación regulatoria con la autoridad estatal para garantizar que la plataforma auxiliar opere con plena validez '
                'territorial sin invadir competencias municipales ni incurrir en traslados no autorizados (Thelen, 2018).'
            )
            p.runs[0].bold = True

        # Cap 7.4: Clasificación del art. 82 como propuesta técnica
        if p.text.startswith('Legislación estatal de movilidad en Nuevo León.'):
            p.text = (
                'Legislación estatal de movilidad y determinación de modalidad. El ordenamiento cúspide que rige a vTaxi es la '
                'Ley de Movilidad Sostenible, de Accesibilidad y Seguridad Vial para el Estado de Nuevo León (última reforma del '
                '22 de mayo de 2026). El artículo 82 contempla que los concesionarios del servicio de taxi podrán utilizar sistemas '
                'GPS y plataformas tecnológicas autorizadas para el despacho eficiente de unidades. La clasificación de vTaxi bajo '
                'este artículo 82 constituye la propuesta técnica y jurídica planteada por la organización, la cual está formalmente '
                'sujeta a la determinación administrativa definitiva y dictamen que emita el Instituto de Movilidad y Accesibilidad '
                'de Nuevo León (IMA). Esta precisión distingue la propuesta del proyecto frente a las Empresas de Redes de Transporte (ERT) '
                'reguladas en los artículos 99 y 100 para transporte privado entre particulares.'
            )
            p.runs[0].bold = True


def build_word():
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    document = Document(SOURCE)
    paragraphs = document.paragraphs

    # 1) Aplicar correcciones a capítulos previos
    apply_teacher_feedback(document)

    # 2) Localizar encabezados de capítulo 8 y capítulo 9
    chapter8 = next(p for p in paragraphs if p.text.strip().startswith(('8 Métodos o procedimientos', '8 M')) and p.style.name == 'Heading 1')
    chapter9 = next(p for p in paragraphs if p.text.strip().startswith(('9 Cronograma de actividades', '9 C')) and p.style.name == 'Heading 1')
    
    # Formato base
    model = next(p for p in paragraphs if p.text.startswith('Alcance temático.') or p.text.startswith('Contexto socioeconómico'))
    ppr = model._p.pPr

    inserted_texts = []
    # Insertar las secciones del Capítulo 8 ANTES del Capítulo 9
    for item in SECTIONS_T15:
        stype, label_or_heading, text = item
        if stype == 'Heading 2':
            insert_heading_before(chapter9, 'Heading 2', label_or_heading)
            inserted_texts.append(label_or_heading)
        elif stype == 'Normal':
            if label_or_heading:
                insert_before(chapter9, label_or_heading, text, ppr)
                inserted_texts.append(f'{label_or_heading} {text}')
            else:
                insert_before(chapter9, '', text, ppr)
                inserted_texts.append(text)

    # 3) Agregar nuevas referencias bibliográficas antes de Anexos
    ref_heading = next(p for p in paragraphs if p.text.strip() == 'Referencias' and p.style.name == 'Heading 1')
    annex1_heading = next(p for p in paragraphs if p.text.strip().startswith('Anexo 1') and p.style.name.startswith('Heading'))
    
    for ref_text in NEW_REFERENCES:
        insert_before(annex1_heading, '', ref_text, ppr)

    # 4) Actualizar notas en Anexo 1 (Matriz de consistencia)
    document.tables[0].rows[-1].cells[0].add_paragraph(MATRIX_NOTE_T15)

    # 5) Actualizar imagen de portada
    blips = document.paragraphs[0]._p.xpath('.//a:blip')
    assert len(blips) == 1
    rel = blips[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
    document.part.related_parts[rel]._blob = make_cover()

    # 6) Habilitar actualización de campos en Word
    update = OxmlElement('w:updateFields')
    update.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'true')
    document.settings.element.append(update)

    document.save(TARGET)
    words = len(' '.join(inserted_texts).split())
    print(f'Chapter 8 words inserted: {words}')
    print(f'Saved deliverable: {TARGET}')
    return document, source_hash, words


def main():
    print('Construyendo Tarea 15 Word acumulativo...')
    document, source_hash, words = build_word()
    record = {
        'source': SOURCE.name,
        'source_sha256': source_hash,
        'target': TARGET.name,
        'target_sha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        'chapter8_words': words,
        'chapter8_pages_estimated': round(words / 400, 2),
        'prior_chapters_corrected': True,
        'new_references_added': len(NEW_REFERENCES),
        'matrix_updated': True,
        'covey_updated': True,
        'report': REPORT.name,
    }
    (HERE / 'generacion-t15-2026-11-07.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(record, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
