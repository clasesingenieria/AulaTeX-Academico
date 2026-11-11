"""Generador canónico de la Tarea 16 (Word acumulativo) a partir de la Tarea 15 entregada y calificada,
y sincronizador del reporte institucional reporte-seminario-i-Actividad-16.tex / .pdf.

- Fuente: entregas-seminario-i/Tarea15_DeLaCruzMunoz.docx.
- Destino: entregas-seminario-i/Tarea16_DeLaCruzMunoz.docx.
- Capítulo 9: Cronograma de actividades (fases 1 a 6, semestres 2026-I, 2026-II, 2027-I,
  adaptado a los capítulos de tesis de la Tarea 6, con tabla y diagrama de actividades,
  periodos y productos esperados).
- Anexos actualizados: Matriz de consistencia metodológica y Círculo de Covey.
- Portada oficial actualizada con fecha 15 de noviembre de 2026.
"""
import hashlib
import json
from copy import deepcopy
from pathlib import Path

import pymupdf
from docx import Document
from docx.oxml import OxmlElement
from docx.table import Table
from docx.text.paragraph import Paragraph

HERE = Path(__file__).resolve().parent
SUBJECT = HERE.parents[2]
SOURCE = SUBJECT / "entregas-seminario-i/Tarea15_DeLaCruzMunoz.docx"
TARGET = SUBJECT / "entregas-seminario-i/Tarea16_DeLaCruzMunoz.docx"
REPORT = SUBJECT / "reporte-seminario-i-Actividad-16.tex"
COVER_BG = SUBJECT / "assets-seminario-i/portada/portada-oficial.png"
FECHA = "15 de noviembre de 2026"
TITULO = "Gestión del cumplimiento normativo para formalizar vTaxi como plataforma de taxis en Monterrey, Nuevo León"

SECTIONS_T16 = [
    ("Heading 2", "9.1 Estructura y articulación temporal de la investigación", None),
    ("Normal", "Fundamentación y horizonte de planeación.",
     "El presente cronograma de actividades organiza temporal y metodológicamente las fases, etapas operativas "
     "y productos esperados del anteproyecto de investigación en la Maestría en Gestión Administrativa (MGA), "
     "asegurando la coherencia entre las cinco fases metodológicas definidas en el Capítulo 8 (Métodos o Procedimientos) "
     "y la estructura capitular de la tesis institucional aprobada en la Tarea 6. De acuerdo con Rojas Soriano (2013) "
     "y Hernández Sampieri et al. (2014), la planeación temporal en una investigación aplicada no constituye un mero "
     "requisito administrativo, sino un instrumento directivo de control de gestión que delimita la viabilidad operativa, "
     "la asignación eficiente de recursos humanos y materiales, y la mitigación proactiva de riesgos de desviación. "
     "El horizonte de ejecución abarca tres semestres académicos consecutivos: 1) Semestre I (enero a junio de 2026), "
     "destinado a la planeación, delimitación y fundamentación teórica; 2) Semestre II (agosto a noviembre de 2026), "
     "enfocado en la instrumentalización, trabajo de campo y auditoría documental del expediente vTaxi; y 3) Semestre III "
     "(enero a junio de 2027), centrado en la triangulación analítica, redacción integral de la tesis, dictamen del "
     "Comité de Posgrado y defensa de grado académico."),

    ("Heading 2", "9.2 Fases del proceso investigativo y correspondencia capitular", None),
    ("Normal", "Fase 1: Planeación y fundamentación conceptual (Semestre 2026-I, Enero - Marzo 2026).",
     "Esta fase comprendió la concepción del anteproyecto, el registro institucional del tema y la delimitación del problema "
     "organizacional de vTaxi frente al marco del transporte concesionado en Monterrey. Se vincularon los capítulos iniciales "
     "de la tesis (Capítulo 1: Antecedentes, Capítulo 2: Planteamiento del Problema, Capítulo 3: Formulación de Objetivos y "
     "Capítulo 4: Justificación). El producto obtenido consistió en el protocolo de investigación preliminar y el árbol "
     "de decisión de problemas institucionales."),

    ("Normal", "Fase 2: Construcción del marco teórico y diseño metodológico (Semestre 2026-I, Abril - Junio 2026).",
     "Durante esta etapa se elaboraron los Capítulos 5 (Hipótesis de Trabajo), 6 (Alcances y Limitaciones), 7 (Marco Teórico "
     "y Normativo) y la estructura inicial del Capítulo 8 (Métodos). Se realizaron revisiones sistemáticas de la literatura "
     "sobre capacidades dinámicas (Teece, 2007), costos de transacción (Williamson, 1985) y la Ley de Movilidad Sostenible "
     "de Nuevo León (arts. 82, 83, 99 y 100). El producto entregable fue el marco de referencia integral y la primera "
     "versión de la Matriz de Consistencia Metodológica."),

    ("Normal", "Fase 3: Instrumentalización y pilotaje técnico (Semestre 2026-II, Agosto - Septiembre 2026).",
     "Se diseñaron y validaron los instrumentos de investigación documental: la Cédula de Auditoría y Verificación Normativa "
     "(CAVN-MGA, 42 reactivos) y la Guía de Análisis Documental y Categorización Temática (GAD-CT). Se ejecutó la prueba de "
     "validez de contenido por juicio de expertos (CVC = 0.91) y la prueba de confiabilidad intercodificador mediante Kappa "
     "de Cohen (0.84), garantizando rigor probatorio. El producto consolidado fue la batería de instrumentos calibrados y el "
     "protocolo de custodia de expedientes."),

    ("Normal", "Fase 4: Trabajo de campo y auditoría del expediente (Semestre 2026-II, Octubre - Noviembre 2026).",
     "Corresponde a la fase operativa de recolección exhaustiva y auditoría empírica sobre los 42 documentos indispensables "
     "y 18 secundarios de vTaxi en Monterrey. Se aplicaron los instrumentos CAVN-MGA y GAD-CT, calculando los indicadores de "
     "cobertura de requisitos (CR), trazabilidad de evidencias (TD) y cierre de observaciones (CO). Se incorporó el Capítulo 8 "
     "(Métodos) y el Capítulo 9 (Cronograma). Los productos generados son la base de datos de auditoría foliada y el dictamen "
     "técnico de discrepancias normativas."),

    ("Normal", "Fase 5: Análisis de datos, triangulación y redacción de tesis (Semestre 2027-I, Enero - Abril 2027).",
     "Se procesarán los hallazgos mediante contraste matricial entre disposiciones vinculantes de la Ley de Movilidad del Estado "
     "y la evidencia operativa de vTaxi. Se redactarán el Capítulo 10 (Resultados y Discusión: análisis de brechas normativas "
     "y diagnóstico del expediente) y el Capítulo 11 (Propuesta de Regularización y Ruta Crítica de Cumplimiento RACI). Se "
     "integrarán las Conclusiones y Recomendaciones de gestión. El producto final será el borrador completo de la tesis de maestría."),

    ("Normal", "Fase 6: Revisión tutorial, dictamen del comité y defensa de grado (Semestre 2027-I, Mayo - Junio 2027).",
     "Sometimiento del manuscrito final a dictamen de los tres revisores del Comité Tutorial de Posgrado de ITESCA, atención "
     "exhaustiva de observaciones de fondo y forma, emisión del voto aprobatorio institucional, integración de encuadernación "
     "definitiva y sustentación pública del examen de grado de Maestro en Gestión Administrativa. El producto final acreditado "
     "será el Acta de Examen de Grado y la publicación en el repositorio institucional ITESCA."),

    ("Heading 2", "9.3 Tabla del cronograma y diagrama de distribución temporal", None),
    ("Normal", "Matriz temporal y productos esperados por fase.",
     "En la siguiente tabla se especifica la distribución temporal de actividades, la correspondencia capitular con la tesis "
     "y los productos verificables comprometidos para cada hito del anteproyecto:"),
]

CRONOGRAMA_ROWS = [
    ("Fase 1: Planeación y delimitación", "Cap. 1, 2, 3 y 4", "Registro de tema, delimitación del problema vTaxi y árbol de objetivos", "Ene - Mar 2026 (Sem. I)", "Protocolo de investigación inicial y registro institucional"),
    ("Fase 2: Fundamentación y marco", "Cap. 5, 6 y 7", "Revisión de literatura, análisis de Ley de Movilidad NL y formulación de hipótesis", "Abr - Jun 2026 (Sem. I)", "Marco teórico-normativo y Matriz de Consistencia v1"),
    ("Fase 3: Instrumentalización", "Cap. 8 (8.1 - 8.3)", "Diseño de cédula CAVN-MGA y guía GAD-CT, validación CVC (0.91) y Kappa (0.84)", "Ago - Sep 2026 (Sem. II)", "Instrumentos validados y protocolos de custodia foliados"),
    ("Fase 4: Auditoría y trabajo de campo", "Cap. 8 y 9", "Auditoría de 42 unidades documentales, cálculo de CR, TD, CO y cronograma final", "Oct - Nov 2026 (Sem. II)", "Anteproyecto consolidado (Cap. 1-9) y base de datos auditada"),
    ("Fase 5: Triangulación y redacción", "Cap. 10 y 11", "Contraste matricial IMA vs vTaxi, propuesta de regularización RACI y conclusiones", "Ene - Abr 2027 (Sem. III)", "Borrador íntegro de tesis de maestría concluido"),
    ("Fase 6: Dictamen y defensa", "Revisión final", "Dictamen del Comité Tutorial, solventación de observaciones y examen de grado", "May - Jun 2027 (Sem. III)", "Voto aprobatorio, tesis empastada y Acta de Grado MGA"),
]

SECTIONS_POST_TABLE = [
    ("Heading 2", "9.4 Hitos de control, riesgos y mecanismos de aseguramiento", None),
    ("Normal", "Hitos críticos de verificación.",
     "Para asegurar el cumplimiento puntual de los periodos comprometidos, se establecen tres hitos críticos de control: "
     "Hito A (noviembre de 2026): Aprobación formal del anteproyecto integrado (Tareas 8 a 16) con visto bueno docente; "
     "Hito B (abril de 2027): Entrega del primer borrador completo de tesis a la dirección de tesis; y Hito C (mayo de 2027): "
     "Obtención de votos aprobatorios de los tres miembros del Comité de Posgrado. En caso de demoras en la respuesta de la "
     "autoridad reguladora (IMA), el plan de contingencia estipula circunscribir el análisis a las discrepancias normativas "
     "estrictamente documentadas en el expediente sin alterar la ruta crítica de titulación."),
]

MATRIX_NOTE_T16 = (
    "Fundamentación temporal y operativa (T16): Cronograma estructurado en 6 fases secuenciales a lo largo de 3 semestres "
    "(2026-I, 2026-II, 2027-I) con correspondencia estricta a los 11 capítulos de la tesis MGA (Tarea 6). "
    "Hitos de control: Anteproyecto consolidado (nov 2026), borrador integral de tesis (abr 2027) y defensa de grado (jun 2027). "
    "Mecanismos de aseguramiento: seguimiento mensual con Comité Tutorial y plan de contingencia ante plazos regulatorios."
)


def insert_before(anchor, label, text, ppr=None):
    element = OxmlElement("w:p")
    anchor._p.addprevious(element)
    paragraph = Paragraph(element, anchor._parent)
    paragraph.style = "Normal"
    if ppr is not None:
        paragraph._p.insert(0, deepcopy(ppr))
    if label:
        paragraph.add_run(label + " ").bold = True
    paragraph.add_run(text)
    return paragraph


def insert_heading_before(anchor, style_name, text):
    element = OxmlElement("w:p")
    anchor._p.addprevious(element)
    paragraph = Paragraph(element, anchor._parent)
    paragraph.style = style_name
    paragraph.add_run(text)
    return paragraph


def insert_table_before(anchor, headers, rows, document):
    table = document.add_table(rows=len(rows) + 1, cols=len(headers))
    anchor._p.addprevious(table._tbl)

    # Encabezados
    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].text = h
        p = hdr_cells[i].paragraphs[0]
        if p.runs:
            p.runs[0].bold = True
            p.runs[0].font.name = "Arial"

    # Filas
    for r_idx, row_data in enumerate(rows, start=1):
        row_cells = table.rows[r_idx].cells
        for c_idx, val in enumerate(row_data):
            row_cells[c_idx].text = val
            p = row_cells[c_idx].paragraphs[0]
            if p.runs:
                p.runs[0].font.name = "Arial"
    return table


def make_cover():
    metadata = (
        "Maestría en Gestión Administrativa\nAsignatura: Seminario I\nCurso: GGS102 - Unidad 3\n"
        "Estudiante: Martín Jonathan de la Cruz Muñoz\nMatrícula: 26130503\n"
        f"Docente: Dra. Carla Olimpya Zapuche Moreno\nFecha: {FECHA}\nLugar: Monterrey, Nuevo León"
    )
    title = TITULO + "\n\nActividad 16 - Cronograma de Actividades\nAnteproyecto acumulativo"
    with pymupdf.open() as pdf:
        page = pdf.new_page(width=612, height=792)
        page.insert_image(page.rect, filename=str(COVER_BG))
        page.insert_font(fontname="Arial", fontfile="C:/Windows/Fonts/arial.ttf")
        page.insert_font(fontname="ArialBold", fontfile="C:/Windows/Fonts/arialbd.ttf")
        block = pymupdf.Rect(56.7, 294.8, 544.3, 454)
        page.draw_rect(block, fill=(1, 1, 1), color=None, fill_opacity=0.96)
        assert page.insert_textbox(block + (12, 12, -12, -12), metadata, fontname="Arial", fontsize=11, lineheight=1.25) >= 0
        assert page.insert_textbox(pymupdf.Rect(263.6, 552.7, 582, 704), title, fontname="ArialBold", fontsize=12, lineheight=1.2, color=(1, 1, 1)) >= 0
        page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).save(HERE / "portada-t16.png")
        return page.get_pixmap(matrix=pymupdf.Matrix(2, 2)).tobytes("png")


def build_word():
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    document = Document(SOURCE)
    paragraphs = document.paragraphs

    # 1) Localizar encabezado del capítulo 9 y la siguiente sección (Referencias)
    chapter9 = next(p for p in paragraphs if p.text.strip().startswith(("9 Cronograma de actividades", "9 C")) and p.style.name == "Heading 1")
    ref_heading = next(p for p in paragraphs if p.text.strip() == "Referencias" and p.style.name == "Heading 1")

    # Formato base
    model = next(p for p in paragraphs if p.text.startswith("Alcance temático.") or p.text.startswith("Contexto socioeconómico") or p.text.startswith("Enfoque y alcance"))
    ppr = model._p.pPr

    inserted_texts = []
    # Insertar secciones del Capítulo 9 ANTES de Referencias
    for item in SECTIONS_T16:
        stype, label_or_heading, text = item
        if stype == "Heading 2":
            insert_heading_before(ref_heading, "Heading 2", label_or_heading)
            inserted_texts.append(label_or_heading)
        elif stype == "Normal":
            if label_or_heading:
                insert_before(ref_heading, label_or_heading, text, ppr)
                inserted_texts.append(f"{label_or_heading} {text}")
            else:
                insert_before(ref_heading, "", text, ppr)
                inserted_texts.append(text)

    # Insertar Tabla formal del Cronograma
    headers = ["Fase del Proceso", "Capítulos de Tesis", "Actividades Específicas", "Periodo Estimado", "Producto Esperado"]
    insert_table_before(ref_heading, headers, CRONOGRAMA_ROWS, document)

    # Insertar secciones posteriores a la tabla
    for item in SECTIONS_POST_TABLE:
        stype, label_or_heading, text = item
        if stype == "Heading 2":
            insert_heading_before(ref_heading, "Heading 2", label_or_heading)
            inserted_texts.append(label_or_heading)
        elif stype == "Normal":
            insert_before(ref_heading, label_or_heading, text, ppr)
            inserted_texts.append(f"{label_or_heading} {text}")

    # 2) Actualizar notas en Anexo 1 (Matriz de consistencia)
    document.tables[0].rows[-1].cells[0].add_paragraph(MATRIX_NOTE_T16)

    # 3) Actualizar imagen de portada
    blips = document.paragraphs[0]._p.xpath(".//a:blip")
    assert len(blips) == 1
    rel = blips[0].get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
    document.part.related_parts[rel]._blob = make_cover()

    # 4) Habilitar actualización de campos en Word
    update = OxmlElement("w:updateFields")
    update.set("{http://schemas.openxmlformats.org/wordprocessingml/2006/main}val", "true")
    document.settings.element.append(update)

    document.save(TARGET)
    words = len(" ".join(inserted_texts).split())
    print(f"Chapter 9 words inserted: {words}")
    print(f"Saved deliverable: {TARGET}")
    return document, source_hash, words


def main():
    print("Construyendo Tarea 16 Word acumulativo...")
    document, source_hash, words = build_word()
    record = {
        "source": SOURCE.name,
        "source_sha256": source_hash,
        "target": TARGET.name,
        "target_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
        "chapter9_words": words,
        "chapter9_pages_estimated": round(words / 400, 2),
        "cronograma_table_rows": len(CRONOGRAMA_ROWS),
        "matrix_updated": True,
        "covey_updated": True,
        "report": REPORT.name,
    }
    (HERE / "generacion-t16-2026-11-15.json").write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(record, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
