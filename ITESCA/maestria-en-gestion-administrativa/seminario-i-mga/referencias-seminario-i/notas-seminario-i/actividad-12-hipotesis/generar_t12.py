import hashlib
import json
from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.oxml import OxmlElement
from docx.text.paragraph import Paragraph


HERE = Path(__file__).resolve().parent
SUBJECT = HERE.parents[2]
SOURCE = SUBJECT / 'Entregas/Tarea11_DeLaCruzMunoz.docx'
TARGET = SUBJECT / 'Entregas/Tarea12_DeLaCruzMunoz.docx'
GENERAL = ('En los componentes documentales aplicables al proyecto vTaxi como plataforma de taxis concesionados en Nuevo León durante septiembre a noviembre de 2026, un mayor nivel de gestión del cumplimiento normativo se relaciona con un mayor grado de preparación administrativa del expediente, expresado en documentos completos y coherentes con los requisitos aplicables y en observaciones internas atendidas con respaldo verificable.')
SPECIFIC = ('En los componentes del expediente de vTaxi, la asignación documentada de responsables y el seguimiento de observaciones se relacionan con una mayor proporción de observaciones internas cerradas mediante evidencia documental aceptable en la revisión del caso.')
REFERENCE = ('Price, P. C., Jhangiani, R. S., & Chiang, I.-C. A. (2015). Research methods in psychology (2nd Canadian ed.). BCcampus. https://opentextbc.ca/researchmethods/chapter/correlational-research/')
SECTIONS = [
    ('5.1 Hipótesis general', [
        'HG. ' + GENERAL,
        'La variable independiente (VI), denominada aquí variable predictora y no factor manipulado, es el nivel de gestión del cumplimiento normativo. Comprende asignación documentada de responsabilidades, verificación de aplicabilidad y seguimiento de acciones. La variable dependiente (VD), como resultado documental observado, es el grado de preparación administrativa del expediente. Comprende integridad, coherencia con requisitos aplicables y cierre respaldado de observaciones. Preparación no significa autorización gubernamental, operación legal acreditada ni formalización consumada.',
        'La hipótesis deriva de la brecha descrita en antecedentes y planteamiento: los borradores no acreditan una ruta validada entre requisitos, responsables y evidencias. Responde a la pregunta general y al objetivo de analizar esa relación mediante contraste documental. Los antecedentes justifican examinar procedimientos y controles administrativos, pero no demuestran anticipadamente la relación en vTaxi ni permiten trasladar hallazgos de otros contextos como resultados locales.',
    ]),
    ('5.2 Hipótesis específica', [
        'HE1. ' + SPECIFIC,
        'Se vincula con la pregunta específica 3 y el objetivo específico 3: examinar la correspondencia entre responsables, verificación y seguimiento, por una parte, e integridad del expediente y resolución de observaciones, por otra. Los objetivos 1 y 2 identifican requisitos y diagnostican brechas; el objetivo 4 propone prioridades. No requieren hipótesis adicionales porque no todos los objetivos descriptivos o propositivos expresan una relación entre variables.',
    ]),
    ('5.3 Tipo de hipótesis', [
        'HG y HE1 son hipótesis de trabajo relacionales, direccionales positivas y no causales, formuladas para un estudio de caso documental con alcance correlacional exploratorio en el sentido de contrastar correspondencias. No se propone experimento, manipulación de la VI, comparación entre plataformas ni generalización estadística. Price et al. (2015) distinguen medición de relaciones y demostración causal; aquí VI y VD designan roles analíticos exigidos por la formulación, no causalidad comprobada.',
        'La unidad de análisis sigue siendo vTaxi y su preparación administrativa. Los componentes y observaciones documentales son unidades de registro internas, no empresas independientes ni una muestra poblacional. El contraste será inicialmente descriptivo y por patrones: buscar coincidencias, divergencias y explicaciones alternativas. No se calculará un coeficiente de correlación si no existe una base suficiente y compatible con sus supuestos. No se incluyen hipótesis nula y alternativa estadísticas, valores p o niveles de significación porque no se ha previsto una prueba inferencial.',
    ]),
    ('5.4 Criterios de calidad y contraste documental', [
        'Claridad. Se diferencian gestión (acciones y registros de control) y preparación (calidad de los documentos resultantes). Se utilizará una ficha por componente con identificador, requisito aplicable, fuente, documento revisado, fecha, versión y limitaciones de acceso. La clasificación previa de taxis concesionados, SETIAP/ERT y capacitación evita atribuir requisitos de otra modalidad a vTaxi.',
        'Verificabilidad de la VI. Registrar por separado: responsable documentado (sí/no/no verificable); revisión de aplicabilidad con fuente y fecha (sí/no/no verificable); y seguimiento de acciones u observaciones mediante registro fechado (sí/no/no verificable). Distinguir responsable efectivamente designado de responsable sólo propuesto. La cobertura de cada control será el número de componentes con presencia comprobada dividido entre componentes evaluables; reportar numerador, denominador y casos no verificables. No confundir una recomendación con control ejecutado.',
        'Verificabilidad de la VD. Una lista distinta registrará integridad de los contenidos exigibles y concordancia del documento con el requisito aplicable, sin puntuar como preparación la mera existencia de responsable o bitácora. Cada observación se clasificará abierta, cerrada con evidencia aceptable o no verificable. La proporción de cierre será observaciones con cierre respaldado entre observaciones evaluables en el mismo corte; informar los conteos. Ausencia de observaciones registradas no equivale a expediente completo ni se divide entre cero.',
        'Separación y revisión. Los criterios de aceptabilidad documental se fijarán antes de comparar VI y VD, con fundamento y alcance por requisito. Cuando sea viable, una segunda revisión documentará acuerdos y discrepancias; no se afirma validación experta ya realizada. Una fuente inaccesible se registra no verificable, no incumplida. Comparar sólo componentes con exigencias y cortes compatibles; las versiones repetidas del mismo documento no cuentan como casos independientes.',
        'Contraste de HG. En una matriz por componente se cotejarán los controles observados con integridad y coherencia documental en el mismo corte. Se buscará el patrón de mejor preparación cuando existen más controles documentados y se revisarán casos contrarios: controles presentes con expediente incompleto, o documentos adecuados sin controles registrados. Tales casos pueden debilitar o acotar la hipótesis. Si no hay variación, acceso suficiente o criterios comparables, el resultado será no contrastable con la evidencia disponible, no hipótesis confirmada.',
        'Contraste de HE1. Por observación se examinarán designación documentada, seguimiento fechado y evidencia de cierre. Se distinguirá el registro de acciones de la corrección verificable del documento. Se atenderán explicaciones alternativas: complejidad del requisito, disponibilidad de información y etapa de elaboración. La correspondencia observada no prueba que los controles hayan causado el cierre. Las relaciones se describirán sólo dentro del caso y con sus limitaciones.',
        'Pertinencia y consistencia. Las hipótesis responden al problema y objetivos sin sustituirlos ni ampliar el estudio a todas las plataformas. Su interés pertenece a la LGAC Gestión e Innovación de las Organizaciones: procedimientos, responsables, documentos, controles e indicadores. El Círculo de Covey conserva problema y objetivo general en Importante/No urgente; no se agrega la hipótesis al esquema. La clasificación establece una prioridad de planeación, no una prueba de la relación propuesta.',
        'Estado de evidencia. Se formulan hipótesis para orientar el estudio, no resultados. Los borradores y fuentes disponibles permiten preparar la revisión inicial, pero no se cuenta aquí con mediciones completas, entrevistas realizadas, controles implementados ni cierres verificados. El acceso adicional requerirá autorización; no se fabricarán registros ni se tratará la falta de datos como confirmación. Los alcances y procedimientos detallados se desarrollarán en sus apartados posteriores sin anticipar su ejecución.',
    ]),
]


def insert_before(anchor, text, style='Normal'):
    element = OxmlElement('w:p')
    anchor._p.addprevious(element)
    paragraph = Paragraph(element, anchor._parent)
    paragraph.style = style
    paragraph.add_run(text)
    return paragraph


def main():
    if TARGET.exists():
        raise FileExistsError('T12 ya existe; no se sobrescribe')
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    document = Document(SOURCE)
    original = [paragraph.text for paragraph in document.paragraphs]
    tables = [[[cell.text for cell in row.cells] for row in table.rows] for table in document.tables]
    chapter = next(paragraph for paragraph in document.paragraphs if paragraph.text == '5 Hipótesis de trabajo' and paragraph.style.name == 'Heading 1')
    anchor = next(paragraph for paragraph in document.paragraphs if paragraph.text == '6 Alcances y limitaciones' and paragraph.style.name == 'Heading 1')
    assert chapter._p.getnext() is anchor._p
    inserted = []
    for heading, texts in SECTIONS:
        insert_before(anchor, heading, 'Heading 2')
        inserted.append(heading)
        for text in texts:
            insert_before(anchor, text)
            inserted.append(text)
    reference_anchor = next(paragraph for paragraph in document.paragraphs if paragraph.text.startswith('Ramírez-Solís,') and paragraph.style.name == 'Normal')
    reference = insert_before(reference_anchor, REFERENCE)
    if reference_anchor._p.pPr is not None:
        if reference._p.pPr is not None:
            reference._p.remove(reference._p.pPr)
        reference._p.insert(0, deepcopy(reference_anchor._p.pPr))
    inserted.append(REFERENCE)
    cover_changes = {}
    for paragraph in document.paragraphs:
        if paragraph.text == 'Seminario I\nActividad 11 Justificación':
            cover_changes[paragraph.text] = 'Seminario I\nActividad 12 Hipótesis de trabajo'
        elif re_date(paragraph.text):
            cover_changes[paragraph.text] = paragraph.text.replace('10 de octubre de 2026', '12 de octubre de 2026').replace('10 DE OCTUBRE DE 2026', '12 DE OCTUBRE DE 2026')
        if paragraph.text in cover_changes:
            old = paragraph.text
            if paragraph.runs:
                paragraph.runs[0].text = cover_changes[old]
                for run in paragraph.runs[1:]:
                    run.text = ''
            else:
                paragraph.add_run(cover_changes[old])
    assert any('Actividad 12' in paragraph.text for paragraph in document.paragraphs)
    retained = [paragraph.text for paragraph in document.paragraphs if paragraph.text not in inserted]
    assert retained == [cover_changes.get(text, text) for text in original]
    matrix = document.tables[0]
    row = matrix.add_row()
    row.cells[0].merge(row.cells[-1]).text = 'Hipótesis general (HG)\n' + GENERAL
    specific_matrix = document.tables[1]
    specific_matrix.rows[3].cells[1].add_paragraph('Hipótesis específica (HE1)\n' + SPECIFIC)
    assert [[cell.text for cell in row.cells] for row in document.tables[2].rows] == tables[2]
    update = OxmlElement('w:updateFields')
    update.set('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val', 'true')
    document.settings.element.append(update)
    document.save(TARGET)
    result = {'source_sha256': source_hash, 'target_sha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(), 'chapters_1_4_retained': True, 'hypothesis_sections': [heading for heading, _ in SECTIONS], 'matrix_updated': True, 'covey_unchanged': True, 'submission_performed': False, 'word_fields_refresh_pending': True}
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    (HERE / 'generacion-t12.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=True))


def re_date(text):
    return '10 de octubre de 2026' in text.casefold()


if __name__ == '__main__':
    main()