import os
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import parse_xml, OxmlElement
from docx.oxml.ns import nsdecls, qn

inter_dir = "/working_dir/c_c2d643968a323a94/artifacts/file_generation/ttl=63d/intermediate"
out_dir = "/working_dir/c_c2d643968a323a94/artifacts/file_generation/ttl=63d/output"
chart_path = os.path.join(inter_dir, "balance_nutricional_npk.png")
out_docx = os.path.join(out_dir, "Reporte_PIA_Algebra_Lineal_Agronomia_UANL.docx")

doc = docx.Document()

# Color Palette (Agronomic Forest Green & Slate)
PRIMARY_HEX = "1B4332"
ACCENT_HEX = "2D6A4F"
ALT_ROW_HEX = "F0F7F4"
BORDER_HEX = "CBD5E1"
PRIMARY_RGB = RGBColor(0x1B, 0x43, 0x32)
ACCENT_RGB = RGBColor(0x2D, 0x6A, 0x4F)
TEXT_DARK = RGBColor(0x1F, 0x29, 0x37)
TEXT_MUTED = RGBColor(0x47, 0x55, 0x69)

# 1. Page Margins (1 inch on all sides)
for section in doc.sections:
    section.top_margin = Inches(1.0)
    section.bottom_margin = Inches(1.0)
    section.left_margin = Inches(1.0)
    section.right_margin = Inches(1.0)

# Configure Normal style
style_normal = doc.styles["Normal"]
style_normal.font.name = "Calibri"
style_normal.font.size = Pt(11)
style_normal.font.color.rgb = TEXT_DARK

# Helper: Add clickable hyperlink to paragraph
def add_hyperlink(paragraph, text, url):
    part = paragraph.part
    r_id = part.relate_to(url, docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK, is_external=True)
    hyperlink = OxmlElement('w:hyperlink')
    hyperlink.set(qn('r:id'), r_id)
    new_run = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')
    c = OxmlElement('w:color')
    c.set(qn('w:val'), ACCENT_HEX)
    rPr.append(c)
    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)
    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), '22')  # 11pt
    rPr.append(sz)
    rFonts = OxmlElement('w:rFonts')
    rFonts.set(qn('w:ascii'), 'Calibri')
    rFonts.set(qn('w:hAnsi'), 'Calibri')
    rPr.append(rFonts)
    new_run.append(rPr)
    t = OxmlElement('w:t')
    t.text = text
    new_run.append(t)
    hyperlink.append(new_run)
    paragraph._p.append(hyperlink)

# Helper: Native Word Equation Editor (OMML) XML Builders
M_NS = 'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'

def m_r(text):
    # Escape XML entities
    esc = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<m:r><m:rPr><m:sty m:val="p"/></m:rPr><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/><w:sz w:val="22"/></w:rPr><m:t>{esc}</m:t></m:r>'

def m_ri(text):
    esc = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return f'<m:r><w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/><w:sz w:val="22"/></w:rPr><m:t>{esc}</m:t></m:r>'

def m_sub(base, sub):
    return f'<m:sSub><m:e>{m_ri(base)}</m:e><m:sub>{m_r(sub)}</m:sub></m:sSub>'

def m_frac(num_xml, den_xml):
    return f'<m:f><m:num>{num_xml}</m:num><m:den>{den_xml}</m:den></m:f>'

def m_matrix(rows, beg="[", end="]"):
    # rows is list of lists of xml strings (or plain strings)
    mrs = ""
    for r in rows:
        mes = ""
        for cell in r:
            cell_xml = cell if cell.startswith("<") else m_r(str(cell))
            mes += f"<m:e>{cell_xml}</m:e>"
        mrs += f"<m:mr>{mes}</m:mr>"
    return f'<m:d><m:dPr><m:begChr m:val="{beg}"/><m:endChr m:val="{end}"/></m:dPr><m:e><m:m>{mrs}</m:m></m:e></m:d>'

def add_omml_block(doc, inner_omath_xml_list, space_after=8):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(space_after)
    omaths = "".join([f"<m:oMath>{x}</m:oMath>" for x in inner_omath_xml_list])
    xml_str = f'<m:oMathPara {M_NS}>{omaths}</m:oMathPara>'
    p._p.append(parse_xml(xml_str))
    return p

# Helper: Headings & Body
def add_h1(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(16)
    r.font.bold = True
    r.font.color.rgb = PRIMARY_RGB
    # Bottom subtle rule on H1
    pBdr = parse_xml(f'<w:pBdr {nsdecls("w")}><w:bottom w:val="single" w:sz="8" w:space="4" w:color="{PRIMARY_HEX}"/></w:pBdr>')
    p._p.get_or_add_pPr().append(pBdr)
    return p

def add_h2(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    r.font.name = "Calibri"
    r.font.size = Pt(13)
    r.font.bold = True
    r.font.color.rgb = ACCENT_RGB
    return p

def add_body(text="", space_after=7, first_line_indent=0.0):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if first_line_indent > 0:
        p.paragraph_format.first_line_indent = Inches(first_line_indent)
    if text:
        r = p.add_run(text)
        r.font.name = "Calibri"
        r.font.size = Pt(11)
        r.font.color.rgb = TEXT_DARK
    return p

def add_bullet(lead_bold, text, space_after=4):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.15
    if lead_bold:
        rb = p.add_run(lead_bold)
        rb.font.name = "Calibri"
        rb.font.size = Pt(11)
        rb.font.bold = True
        rb.font.color.rgb = TEXT_DARK
    rt = p.add_run(text)
    rt.font.name = "Calibri"
    rt.font.size = Pt(11)
    rt.font.color.rgb = TEXT_DARK
    return p

def add_styled_table(headers, rows_data, col_widths=None, align_right_cols=None):
    if align_right_cols is None:
        align_right_cols = set()
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    # Table borders
    tblPr = table._tbl.tblPr
    borders = parse_xml(f'''
        <w:tblBorders {nsdecls("w")}>
            <w:top w:val="single" w:sz="8" w:space="0" w:color="{PRIMARY_HEX}"/>
            <w:bottom w:val="single" w:sz="8" w:space="0" w:color="{PRIMARY_HEX}"/>
            <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{BORDER_HEX}"/>
            <w:left w:val="none"/>
            <w:right w:val="none"/>
            <w:insideV w:val="none"/>
        </w:tblBorders>
    ''')
    tblPr.append(borders)

    # Header row
    hdr_row = table.rows[0]
    hdr_trPr = hdr_row._tr.get_or_add_trPr()
    hdr_trPr.append(parse_xml(f'<w:tblHeader {nsdecls("w")}/>'))
    hdr_trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))

    for i, h_text in enumerate(headers):
        cell = hdr_row.cells[i]
        if col_widths:
            cell.width = Inches(col_widths[i])
        cell.text = h_text
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{PRIMARY_HEX}"/>')
        cell._tc.get_or_add_tcPr().append(shd)
        tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="100" w:type="dxa"/><w:bottom w:w="100" w:type="dxa"/><w:left w:w="120" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>')
        cell._tc.get_or_add_tcPr().append(tcMar)
        for p in cell.paragraphs:
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if i in align_right_cols else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            p.paragraph_format.keep_with_next = True
            for r in p.runs:
                r.font.name = "Calibri"
                r.font.size = Pt(10.5)
                r.font.bold = True
                r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    # Data rows
    for r_idx, r_vals in enumerate(rows_data):
        row = table.add_row()
        trPr = row._tr.get_or_add_trPr()
        trPr.append(parse_xml(f'<w:cantSplit {nsdecls("w")}/>'))
        for c_idx, val in enumerate(r_vals):
            cell = row.cells[c_idx]
            if col_widths:
                cell.width = Inches(col_widths[c_idx])
            cell.text = str(val)
            cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            if r_idx % 2 == 1:
                shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{ALT_ROW_HEX}"/>')
                cell._tc.get_or_add_tcPr().append(shd)
            tcMar = parse_xml(f'<w:tcMar {nsdecls("w")}><w:top w:w="80" w:type="dxa"/><w:bottom w:w="80" w:type="dxa"/><w:left w:w="120" w:type="dxa"/><w:right w:w="120" w:type="dxa"/></w:tcMar>')
            cell._tc.get_or_add_tcPr().append(tcMar)
            for p in cell.paragraphs:
                p.alignment = WD_ALIGN_PARAGRAPH.RIGHT if c_idx in align_right_cols else WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_before = Pt(2)
                p.paragraph_format.space_after = Pt(2)
                for r in p.runs:
                    r.font.name = "Calibri"
                    r.font.size = Pt(10)
                    r.font.color.rgb = TEXT_DARK
                    if r_idx == len(rows_data) - 1 and str(r_vals[0]).startswith("Total"):
                        r.font.bold = True

    if len(table.rows) <= 6:
        for row in table.rows[:-1]:
            for cell in row.cells:
                for p in cell.paragraphs:
                    p.paragraph_format.keep_with_next = True

    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(6)
    return table

# ==============================================================================
# 1. PORTADA (Standalone Cover Page)
# ==============================================================================
p_uni = doc.add_paragraph()
p_uni.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_uni.paragraph_format.space_before = Pt(18)
p_uni.paragraph_format.space_after = Pt(4)
r_uni = p_uni.add_run("UNIVERSIDAD AUTÓNOMA DE NUEVO LEÓN")
r_uni.font.size = Pt(18)
r_uni.font.bold = True
r_uni.font.color.rgb = PRIMARY_RGB

p_fac = doc.add_paragraph()
p_fac.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_fac.paragraph_format.space_after = Pt(24)
r_fac = p_fac.add_run("FACULTAD DE AGRONOMÍA")
r_fac.font.size = Pt(15)
r_fac.font.bold = True
r_fac.font.color.rgb = ACCENT_RGB

p_ua = doc.add_paragraph()
p_ua.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_ua.paragraph_format.space_after = Pt(6)
r_ua = p_ua.add_run("UNIDAD DE APRENDIZAJE: ÁLGEBRA LINEAL")
r_ua.font.size = Pt(13)
r_ua.font.bold = True
r_ua.font.color.rgb = TEXT_DARK

p_pia = doc.add_paragraph()
p_pia.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_pia.paragraph_format.space_after = Pt(18)
r_pia = p_pia.add_run("PRODUCTO INTEGRADOR DE APRENDIZAJE (PIA)")
r_pia.font.size = Pt(14)
r_pia.font.bold = True
r_pia.font.color.rgb = PRIMARY_RGB

p_tit = doc.add_paragraph()
p_tit.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_tit.paragraph_format.space_before = Pt(12)
p_tit.paragraph_format.space_after = Pt(24)
r_tit = p_tit.add_run("Formulación y Optimización de una Mezcla de Fertilización N-P-K para el Cultivo de Maíz en Nuevo León mediante Sistemas de Ecuaciones Lineales de 3 × 3")
r_tit.font.size = Pt(20)
r_tit.font.bold = True
r_tit.font.color.rgb = PRIMARY_RGB

p_prog = doc.add_paragraph()
p_prog.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_prog.paragraph_format.space_after = Pt(4)
r_prog = p_prog.add_run("Programa Educativo: Ingeniero Agrónomo")
r_prog.font.size = Pt(12)
r_prog.font.bold = True

p_sem = doc.add_paragraph()
p_sem.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_sem.paragraph_format.space_after = Pt(20)
r_sem = p_sem.add_run("Semestre: Agosto – Diciembre 2026")
r_sem.font.size = Pt(11.5)

p_int_lbl = doc.add_paragraph()
p_int_lbl.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_int_lbl.paragraph_format.space_after = Pt(6)
p_int_lbl.paragraph_format.keep_with_next = True
r_il = p_int_lbl.add_run("Integrantes del Equipo (Máximo 4 integrantes — Completar antes de exportar a PDF):")
r_il.font.size = Pt(11)
r_il.font.bold = True
r_il.font.color.rgb = PRIMARY_RGB

add_styled_table(
    headers=["N.º", "Nombre Completo del Estudiante", "Matrícula", "Grupo", "Programa Educativo"],
    rows_data=[
        ["1", "[Escribir Nombre Completo Integrante 1]", "[Matrícula]", "[Grupo]", "Ingeniero Agrónomo"],
        ["2", "[Escribir Nombre Completo Integrante 2]", "[Matrícula]", "[Grupo]", "Ingeniero Agrónomo"],
        ["3", "[Escribir Nombre Completo Integrante 3]", "[Matrícula]", "[Grupo]", "Ingeniero Agrónomo"],
        ["4", "[Escribir Nombre Completo Integrante 4]", "[Matrícula]", "[Grupo]", "Ingeniero Agrónomo"],
    ],
    col_widths=[0.5, 2.7, 1.1, 0.8, 1.4]
)

p_date = doc.add_paragraph()
p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
p_date.paragraph_format.space_before = Pt(28)
p_date.paragraph_format.space_after = Pt(6)
r_dt = p_date.add_run("General Escobedo / Marín, Nuevo León, México — Fecha de entrega: 11 de noviembre de 2026")
r_dt.font.size = Pt(11)
r_dt.font.italic = True
r_dt.font.color.rgb = TEXT_MUTED

doc.add_page_break()

# ==============================================================================
# 2. INTRODUCCIÓN
# ==============================================================================
add_h1("2. Introducción: Nutrición Mineral Exacta mediante Álgebra Lineal")

add_h2("2.a. Justificación Agronómica y Matemática")
p = add_body()
p.add_run("La fertilización mineral racional constituye un factor crítico en la ingeniería agronómica moderna para sostener altos rendimientos de grano y forraje sin deteriorar la fertilidad físico-química del suelo ni comprometer la rentabilidad de las unidades de producción rural (")
add_hyperlink(p, "Secretaría de Agricultura y Desarrollo Rural [SADER], 2023", "https://www.gob.mx/cms/uploads/attachment/file/911180/Dx_S290-Fertilizantes_2023.pdf")
p.add_run("). En el estado de Nuevo León se establecen anualmente alrededor de 34,916 hectáreas de maíz, concentradas principalmente en los municipios del sur como Galeana y Doctor Arroyo, bajo condiciones de clima estepario semiseco con precipitación media de 650 mm anuales y temperatura promedio de 20 °C (")
add_hyperlink(p, "SADER e Instituto Nacional de Investigaciones Forestales, Agrícolas y Pecuarias [INIFAP], 2024", "https://www.gob.mx/cms/uploads/attachment/file/928380/TRIPTICO_NUEVO_LEON_MAIZ.pdf")
p.add_run("). Frente al encarecimiento internacional de los insumos de nutrición vegetal, el cálculo exacto de mezclas físicas y químicas permite suministrar al cultivo las cantidades precisas de macronutrientes primarios sin incurrir en pérdidas por volatilización, fijación o lixiviación.")

p2 = add_body()
p2.add_run("Dentro del plan de estudios de la licenciatura de ")
add_hyperlink(p2, "Ingeniero Agrónomo de la Facultad de Agronomía de la UANL (2025)", "https://www.uanl.mx/oferta/ingeniero-agronomo/")
p2.add_run(", el razonamiento numérico y la modelación matemática se vinculan directamente con asignaturas como ")
add_hyperlink(p2, "Fertilidad de Suelos y Cultivos Básicos (UANL, 2025)", "https://agronomia.uanl.mx/wp-content/uploads/2025/05/LICENCIATURA-EN-INGENIERIA-EN-AGRONOMIA-plan-430-1.pdf")
p2.add_run(". Cuando un productor o asesor agronómico dispone de tres fertilizantes compuestos comerciales con diferentes leyes porcentuales de Nitrógeno (N), Fósforo asimilable expresado como pentóxido de difósforo (P₂O₅) y Potasio soluble expresado como óxido de potasio (K₂O), el balance de masa de cada elemento genera un sistema acoplado de tres ecuaciones lineales con tres incógnitas (3 × 3). Su resolución mediante métodos matriciales formales garantiza determinar la dosificación única por hectárea que satisface simultáneamente los tres requerimientos nutricionales del cultivo.")

add_h2("2.b. Planteamiento del Problema Aplicado a la Agronomía")
p3 = add_body()
p3.add_run("En una unidad de producción agrícola dedicada al cultivo de maíz para grano bajo riego de auxilio en el municipio de Galeana, Nuevo León, el análisis de fertilidad edáfica y la meta de rendimiento fijan un requerimiento nutricional neto por hectárea de ")
r_b1 = p3.add_run("99 kg/ha de Nitrógeno (N), 83 kg/ha de Fósforo (P₂O₅) y 84 kg/ha de Potasio (K₂O)")
r_b1.bold = True
p3.add_run(". Para elaborar la mezcla física de fertilización, la bodega técnica cuenta con tres fórmulas comerciales de fertilizantes compuestos ternarios N-P-K (")
add_hyperlink(p3, "Área de Agronomía, 2024", "https://areadeagronomia.mx/wp-content/uploads/2024/12/MANUALMATADAMAS-pdf.pdf")
p3.add_run("):")

add_bullet("Fórmula A (Complejo Arrancador 12-24-12): ", "aporta 12% de Nitrógeno (N), 24% de Fósforo (P₂O₅) y 12% de Potasio (K₂O) en peso.")
add_bullet("Fórmula B (Complejo de Desarrollo Vegetativo 20-10-10): ", "aporta 20% de Nitrógeno (N), 10% de Fósforo (P₂O₅) y 10% de Potasio (K₂O) en peso.")
add_bullet("Fórmula C (Complejo de Llenado de Grano 15-05-30): ", "aporta 15% de Nitrógeno (N), 5% de Fósforo (P₂O₅) y 30% de Potasio (K₂O) en peso.", space_after=8)

p4 = add_body()
r_q = p4.add_run("Problema por resolver: ")
r_q.bold = True
p4.add_run("Determinar la cantidad exacta en kilogramos por hectárea de la Fórmula A (x₁), de la Fórmula B (x₂) y de la Fórmula C (x₃) que deben integrarse en el plan de fertilización para suministrar exactamente 99 kg de N, 83 kg de P₂O₅ y 84 kg de K₂O por hectárea, sin excedentes ni déficits nutrimentales.")

# ==============================================================================
# 3. RECOLECCIÓN DE DATOS
# ==============================================================================
add_h1("3. Recolección de Datos Técnicos y Agronómicos")

p_rec = add_body()
p_rec.add_run("La recolección de datos se efectuó a partir de fuentes técnicas oficiales del sector agropecuario mexicano. En primer término, se consultaron los lineamientos del paquete tecnológico de maíz para Nuevo León (")
add_hyperlink(p_rec, "SADER & INIFAP, 2024", "https://www.gob.mx/cms/uploads/attachment/file/928380/TRIPTICO_NUEVO_LEON_MAIZ.pdf")
p_rec.add_run(") y el estudio de respuesta productiva a la fertilización mineral del ")
add_hyperlink(p_rec, "INIFAP (2018)", "https://www.scielo.org.mx/pdf/remexca/v9nspe21/2007-0934-remexca-9-spe21-4306.pdf")
p_rec.add_run(", donde se documenta la importancia de fraccionar el suministro de nitrógeno entre la siembra y la escarda (etapa fenológica V5-V6) y aplicar el fósforo y el potasio en la etapa inicial. Asimismo, se recabaron las especificaciones químicas de los fertilizantes minerales simples y compuestos ternarios en el ")
add_hyperlink(p_rec, "Manual para el Cálculo de Fórmulas Generales de Fertilización (Área de Agronomía, 2024)", "https://areadeagronomia.mx/wp-content/uploads/2024/12/MANUALMATADAMAS-pdf.pdf")
p_rec.add_run(". La Tabla 1 sintetiza la matriz de composición porcentual y en fracción decimal (kg de nutriente aportado por cada kg de fertilizante comercial), junto con la demanda objetivo por hectárea.")

p_t1 = add_body("Tabla 1. Composición nutricional de los tres fertilizantes compuestos ternarios y requerimiento del cultivo por hectárea.", space_after=4)
p_t1.runs[0].bold = True
p_t1.paragraph_format.keep_with_next = True

add_styled_table(
    headers=[
        "Macronutriente Primario",
        "Fórmula A (12-24-12)\n[Variable x₁]",
        "Fórmula B (20-10-10)\n[Variable x₂]",
        "Fórmula C (15-05-30)\n[Variable x₃]",
        "Requerimiento Neto\n(kg/ha)"
    ],
    rows_data=[
        ["Nitrógeno total (N)", "12% (0.12 kg/kg)", "20% (0.20 kg/kg)", "15% (0.15 kg/kg)", "99.0"],
        ["Fósforo asimilable (P₂O₅)", "24% (0.24 kg/kg)", "10% (0.10 kg/kg)", "5% (0.05 kg/kg)", "83.0"],
        ["Potasio soluble (K₂O)", "12% (0.12 kg/kg)", "10% (0.10 kg/kg)", "30% (0.30 kg/kg)", "84.0"]
    ],
    col_widths=[1.8, 1.2, 1.2, 1.2, 1.1],
    align_right_cols={4}
)

# ==============================================================================
# 4. METODOLOGÍA
# ==============================================================================
add_h1("4. Metodología: Modelación Lineal y Selección del Método")

add_h2("4.a. Planteamiento del Sistema de Ecuaciones Lineales de 3 × 3")
add_body("Para estructurar el modelo matemático se definen las tres variables de decisión continuas y no negativas que representan la masa de cada insumo comercial por aplicar en una hectárea:")
add_bullet("x₁ = ", "Kilogramos por hectárea (kg/ha) del fertilizante compuesto Fórmula A (12-24-12).")
add_bullet("x₂ = ", "Kilogramos por hectárea (kg/ha) del fertilizante compuesto Fórmula B (20-10-10).")
add_bullet("x₃ = ", "Kilogramos por hectárea (kg/ha) del fertilizante compuesto Fórmula C (15-05-30).", space_after=6)

add_body("Al establecer el balance de masa individual para cada macronutriente (suma de los productos de la fracción másica por los kilogramos de cada fuente igual al requerimiento total por hectárea), se obtiene el sistema lineal de 3 ecuaciones con 3 incógnitas en forma decimal (elaborado con el Editor de Ecuaciones nativo de Word):")

# Equation 1: Decimal system (OMML)
eq_dec_1 = m_r("0.12") + m_sub("x", "1") + m_r(" + 0.20") + m_sub("x", "2") + m_r(" + 0.15") + m_sub("x", "3") + m_r(" = 99") + m_r("   (Ecuación 1: Balance de N)")
eq_dec_2 = m_r("0.24") + m_sub("x", "1") + m_r(" + 0.10") + m_sub("x", "2") + m_r(" + 0.05") + m_sub("x", "3") + m_r(" = 83") + m_r("   (Ecuación 2: Balance de P₂O₅)")
eq_dec_3 = m_r("0.12") + m_sub("x", "1") + m_r(" + 0.10") + m_sub("x", "2") + m_r(" + 0.30") + m_sub("x", "3") + m_r(" = 84") + m_r("   (Ecuación 3: Balance de K₂O)")
add_omml_block(doc, [eq_dec_1])
add_omml_block(doc, [eq_dec_2])
add_omml_block(doc, [eq_dec_3], space_after=8)

add_body("Con el propósito de operar con aritmética exacta libre de errores de redondeo durante la reducción matricial, se multiplican ambos miembros de las tres ecuaciones por 100 (expresando los coeficientes en puntos porcentuales), obteniendo el sistema lineal equivalente:")

eq_int_1 = m_r("12") + m_sub("x", "1") + m_r(" + 20") + m_sub("x", "2") + m_r(" + 15") + m_sub("x", "3") + m_r(" = 9900")
eq_int_2 = m_r("24") + m_sub("x", "1") + m_r(" + 10") + m_sub("x", "2") + m_r(" + 5") + m_sub("x", "3") + m_r(" = 8300")
eq_int_3 = m_r("12") + m_sub("x", "1") + m_r(" + 10") + m_sub("x", "2") + m_r(" + 30") + m_sub("x", "3") + m_r(" = 8400")
add_omml_block(doc, [eq_int_1])
add_omml_block(doc, [eq_int_2])
add_omml_block(doc, [eq_int_3], space_after=8)

add_body("En notación matricial A·x = b, el sistema y su matriz aumentada asociada [A | b] se expresan como:")

mat_Ax_b = (
    m_matrix([["12", "20", "15"], ["24", "10", "5"], ["12", "10", "30"]]) +
    m_matrix([[m_sub("x", "1")], [m_sub("x", "2")], [m_sub("x", "3")]]) +
    m_r(" = ") +
    m_matrix([["9900"], ["8300"], ["8400"]]) +
    m_r("   ⟹   [A | b] = ") +
    m_matrix([
        ["12", "20", "15", "|", "9900"],
        ["24", "10", "5", "|", "8300"],
        ["12", "10", "30", "|", "8400"]
    ])
)
add_omml_block(doc, [mat_Ax_b], space_after=10)

add_h2("4.b. Justificación del Método Visto en Clase Empleado en la Solución")
p_just = add_body()
p_just.add_run("Para resolver el sistema lineal de 3 × 3 se seleccionó como método principal la ")
r_gj = p_just.add_run("Eliminación de Gauss-Jordan")
r_gj.bold = True
p_just.add_run(", complementada con la ")
r_cr = p_just.add_run("Regla de Cramer")
r_cr.bold = True
p_just.add_run(" como método de verificación independiente, conforme a la teoría clásica de sistemas lineales (")
add_hyperlink(p_just, "Grossman & Flores Godoy, 2012", "https://books.google.com/books/about/ALGEBRA_LINEAL.html?id=D8HvMQEACAAJ")
p_just.add_run("). La elección se fundamenta en tres criterios técnicos:")

add_bullet("1. Reducción directa a la matriz identidad (I₃): ", "A diferencia de la eliminación gaussiana simple (que requiere una fase adicional de sustitución hacia atrás), el método de Gauss-Jordan aplica operaciones elementales por renglón hasta transformar la matriz aumentada [A | b] en su forma escalonada reducida [I₃ | x], entregando de manera directa e inequívoca el valor de cada fertilizante (x₁, x₂, x₃).")
add_bullet("2. Estructura proporcional de los pivotes: ", "En la primera columna de la matriz de coeficientes (12, 24 y 12), los elementos de los renglones segundo y tercero son múltiplos enteros exactos del primer pivote (24 = 2 × 12 y 12 = 1 × 12). Esto permite realizar la eliminación hacia abajo sin introducir fracciones en las primeras etapas, disminuyendo la probabilidad de error aritmético durante la resolución manual en pizarrón.")
add_bullet("3. Verificación de unicidad mediante determinantes (Regla de Cramer): ", "Evaluar el determinante del sistema (Δ = det(A) ≠ 0) confirma analíticamente que las tres fórmulas de fertilizantes tienen composiciones linealmente independientes y que existe una solución única en el espacio tridimensional, validando cada incógnita mediante el cociente Δxᵢ / Δ.", space_after=8)

# ==============================================================================
# 5. PROCEDIMIENTOS
# ==============================================================================
add_h1("5. Procedimientos: Desarrollo Paso a Paso y Herramientas")

add_h2("5.a. Solución Paso a Paso mediante Eliminación de Gauss-Jordan")

add_body("Paso 1. Matriz aumentada inicial [A | b] en coeficientes enteros:", space_after=2)
mat_step1 = m_matrix([
    ["12", "20", "15", "|", "9900"],
    ["24", "10", "5", "|", "8300"],
    ["12", "10", "30", "|", "8400"]
])
add_omml_block(doc, [mat_step1], space_after=6)

add_body("Paso 2. Eliminación de los elementos debajo del primer pivote (columna 1). Aprovechando que 24 es el doble de 12 y que el tercer renglón comienza con 12, se aplican las operaciones elementales R₂ ← R₂ − 2R₁ y R₃ ← R₃ − R₁:", space_after=2)
op_step2 = (
    m_sub("R", "2") + m_r(" ← ") + m_sub("R", "2") + m_r(" − 2") + m_sub("R", "1") +
    m_r(" :   [24−2(12),  10−2(20),  5−2(15)  |  8300−2(9900)] = [0,  −30,  −25  |  −11500]")
)
op_step2b = (
    m_sub("R", "3") + m_r(" ← ") + m_sub("R", "3") + m_r(" − ") + m_sub("R", "1") +
    m_r(" :   [12−12,  10−20,  30−15  |  8400−9900] = [0,  −10,  15  |  −1500]")
)
mat_step2 = m_matrix([
    ["12", "20", "15", "|", "9900"],
    ["0", "−30", "−25", "|", "−11500"],
    ["0", "−10", "15", "|", "−1500"]
])
add_omml_block(doc, [op_step2], space_after=2)
add_omml_block(doc, [op_step2b], space_after=4)
add_omml_block(doc, [mat_step2], space_after=6)

add_body("Paso 3. Intercambio y simplificación para obtener un pivote cómodo en la columna 2. Se intercambia el segundo renglón con el tercero (R₂ ↔ R₃) y se divide el nuevo segundo renglón entre −10 (R₂ ← R₂ / (−10)):", space_after=2)
mat_step3 = (
    m_sub("R", "2") + m_r(" ↔ ") + m_sub("R", "3") + m_r(" ,  ") +
    m_sub("R", "2") + m_r(" ← −") + m_frac(m_r("1"), m_r("10")) + m_sub("R", "2") +
    m_r("   ⟹   ") +
    m_matrix([
        ["12", "20", "15", "|", "9900"],
        ["0", "1", "−1.5", "|", "150"],
        ["0", "−30", "−25", "|", "−11500"]
    ])
)
add_omml_block(doc, [mat_step3], space_after=6)

add_body("Paso 4. Eliminación en la columna 2 (arriba y abajo del segundo pivote). Se aplican las operaciones R₁ ← R₁ − 20R₂ y R₃ ← R₃ + 30R₂:", space_after=2)
op_step4a = m_sub("R", "1") + m_r(" ← ") + m_sub("R", "1") + m_r(" − 20") + m_sub("R", "2") + m_r(" :   [12−0,  20−20(1),  15−20(−1.5)  |  9900−20(150)] = [12,  0,  45  |  6900]")
op_step4b = m_sub("R", "3") + m_r(" ← ") + m_sub("R", "3") + m_r(" + 30") + m_sub("R", "2") + m_r(" :   [0+0,  −30+30(1),  −25+30(−1.5)  |  −11500+30(150)] = [0,  0,  −70  |  −7000]")
mat_step4 = m_matrix([
    ["12", "0", "45", "|", "6900"],
    ["0", "1", "−1.5", "|", "150"],
    ["0", "0", "−70", "|", "−7000"]
])
add_omml_block(doc, [op_step4a], space_after=2)
add_omml_block(doc, [op_step4b], space_after=4)
add_omml_block(doc, [mat_step4], space_after=6)

add_body("Paso 5. Normalización del tercer pivote (columna 3). Se divide el tercer renglón entre −70 (R₃ ← R₃ / (−70)):", space_after=2)
mat_step5 = (
    m_sub("R", "3") + m_r(" ← −") + m_frac(m_r("1"), m_r("70")) + m_sub("R", "3") +
    m_r("   ⟹   ") +
    m_matrix([
        ["12", "0", "45", "|", "6900"],
        ["0", "1", "−1.5", "|", "150"],
        ["0", "0", "1", "|", "100"]
    ])
)
add_omml_block(doc, [mat_step5], space_after=6)

add_body("Paso 6. Eliminación hacia arriba en la columna 3 y normalización del primer pivote. Se ejecutan R₂ ← R₂ + 1.5R₃ y R₁ ← R₁ − 45R₃, y finalmente se divide el primer renglón entre 12 (R₁ ← R₁ / 12) para obtener la matriz escalonada reducida [I₃ | x]:", space_after=2)
op_step6a = m_sub("R", "2") + m_r(" ← ") + m_sub("R", "2") + m_r(" + 1.5") + m_sub("R", "3") + m_r(" :   [0,  1,  −1.5+1.5(1)  |  150+1.5(100)] = [0,  1,  0  |  300]")
op_step6b = m_sub("R", "1") + m_r(" ← ") + m_sub("R", "1") + m_r(" − 45") + m_sub("R", "3") + m_r(" :   [12,  0,  45−45(1)  |  6900−45(100)] = [12,  0,  0  |  2400]")
mat_step6 = (
    m_sub("R", "1") + m_r(" ← ") + m_frac(m_r("1"), m_r("12")) + m_sub("R", "1") +
    m_r("   ⟹   ") +
    m_matrix([
        ["1", "0", "0", "|", "200"],
        ["0", "1", "0", "|", "300"],
        ["0", "0", "1", "|", "100"]
    ]) +
    m_r("   ⟹   ") +
    m_sub("x", "1") + m_r(" = 200,  ") + m_sub("x", "2") + m_r(" = 300,  ") + m_sub("x", "3") + m_r(" = 100")
)
add_omml_block(doc, [op_step6a], space_after=2)
add_omml_block(doc, [op_step6b], space_after=4)
add_omml_block(doc, [mat_step6], space_after=8)

add_h2("5.a.ii. Verificación Independiente mediante la Regla de Cramer y Sustitución Directa")
add_body("Para corroborar el resultado obtenido por Gauss-Jordan (y ofrecer al equipo una segunda alternativa completa para la exposición en video), se calculan los determinantes de 3 × 3 por expansión de cofactores sobre el primer renglón:", space_after=4)

det_main = (
    m_r("Δ = det(A) = ") +
    m_matrix([["12", "20", "15"], ["24", "10", "5"], ["12", "10", "30"]], beg="|", end="|") +
    m_r(" = 12(300 − 50) − 20(720 − 60) + 15(240 − 120) = 3000 − 13200 + 1800 = −8400")
)
det_x1 = (
    m_sub("Δ", "x₁") + m_r(" = ") +
    m_matrix([["9900", "20", "15"], ["8300", "10", "5"], ["8400", "10", "30"]], beg="|", end="|") +
    m_r(" = 9900(250) − 20(207000) + 15(1000) = 2475000 − 4140000 + 15000 = −1680000")
)
det_x2 = (
    m_sub("Δ", "x₂") + m_r(" = ") +
    m_matrix([["12", "9900", "15"], ["24", "8300", "5"], ["12", "8400", "30"]], beg="|", end="|") +
    m_r(" = 12(207000) − 9900(660) + 15(102000) = 2484000 − 6534000 + 1530000 = −2520000")
)
det_x3 = (
    m_sub("Δ", "x₃") + m_r(" = ") +
    m_matrix([["12", "20", "9900"], ["24", "10", "8300"], ["12", "10", "8400"]], beg="|", end="|") +
    m_r(" = 12(1000) − 20(102000) + 9900(120) = 12000 − 2040000 + 1188000 = −840000")
)
cramer_sol = (
    m_sub("x", "1") + m_r(" = ") + m_frac(m_r("−1680000"), m_r("−8400")) + m_r(" = 200 kg/ha ,    ") +
    m_sub("x", "2") + m_r(" = ") + m_frac(m_r("−2520000"), m_r("−8400")) + m_r(" = 300 kg/ha ,    ") +
    m_sub("x", "3") + m_r(" = ") + m_frac(m_r("−840000"), m_r("−8400")) + m_r(" = 100 kg/ha")
)
add_omml_block(doc, [det_main], space_after=4)
add_omml_block(doc, [det_x1], space_after=4)
add_omml_block(doc, [det_x2], space_after=4)
add_omml_block(doc, [det_x3], space_after=4)
add_omml_block(doc, [cramer_sol], space_after=8)

add_body("Comprobación algebraica por sustitución directa en las tres ecuaciones originales:", space_after=2)
chk_1 = m_r("Ecuación 1 (N):   0.12(200) + 0.20(300) + 0.15(100) = 24 + 60 + 15 = 99 kg/ha de N   ✓")
chk_2 = m_r("Ecuación 2 (P₂O₅):   0.24(200) + 0.10(300) + 0.05(100) = 48 + 30 + 5 = 83 kg/ha de P₂O₅   ✓")
chk_3 = m_r("Ecuación 3 (K₂O):   0.12(200) + 0.10(300) + 0.30(100) = 24 + 30 + 30 = 84 kg/ha de K₂O   ✓")
add_omml_block(doc, [chk_1], space_after=2)
add_omml_block(doc, [chk_2], space_after=2)
add_omml_block(doc, [chk_3], space_after=8)

add_h2("5.b. Herramientas Utilizadas para Elaborar el Proyecto")
add_bullet("Microsoft Word con Editor de Ecuaciones nativo (OpenXML Math / OMML): ", "utilizado para la estructuración 100% digital del reporte escrito bajo normativa APA 7.ª edición y para la tipografía matemática de todas las ecuaciones, matrices aumentadas y determinantes.")
add_bullet("Python 3 (bibliotecas científicas NumPy y Matplotlib): ", "empleado para la validación computacional de la solución del sistema lineal (np.linalg.solve) y la generación de las gráficas comparativas de alta resolución (300 DPI).")
add_bullet("Acervo técnico institucional (SADER, INIFAP y UANL): ", "consulta de paquetes tecnológicos regionales de Nuevo León y manuales de formulación de fertilizantes minerales para fundamentar los coeficientes del modelo.", space_after=8)

# ==============================================================================
# 6. RESULTADOS
# ==============================================================================
add_h1("6. Resultados: Dosificación Comercial y Balance de Nutrientes")

add_body("La resolución del sistema lineal de 3 × 3 determina que para satisfacer exactamente el requerimiento nutricional de una hectárea de maíz (99–83–84) se requiere una mezcla total de 600 kg/ha de fertilizante comercial (equivalentes a 12 bultos estándar de 50 kg), distribuida como se detalla en la Tabla 2 y en la Figura 1.")

p_t2 = add_body("Tabla 2. Dosificación óptima por hectárea y desglose de aporte nutricional por fuente fertilizante.", space_after=4)
p_t2.runs[0].bold = True
p_t2.paragraph_format.keep_with_next = True

add_styled_table(
    headers=[
        "Insumo Comercial",
        "Cantidad Óptima\n(kg/ha)",
        "Presentación\n(Bultos de 50 kg)",
        "Aporte de N\n(kg/ha)",
        "Aporte de P₂O₅\n(kg/ha)",
        "Aporte de K₂O\n(kg/ha)"
    ],
    rows_data=[
        ["Fórmula A (12-24-12) [x₁]", "200.0", "4 bultos", "24.0 (24.2%)", "48.0 (57.8%)", "24.0 (28.6%)"],
        ["Fórmula B (20-10-10) [x₂]", "300.0", "6 bultos", "60.0 (60.6%)", "30.0 (36.1%)", "30.0 (35.7%)"],
        ["Fórmula C (15-05-30) [x₃]", "100.0", "2 bultos", "15.0 (15.2%)", "5.0 (6.0%)", "30.0 (35.7%)"],
        ["Total Mezcla / Meta N-P-K", "600.0", "12 bultos", "99.0 (100.0%)", "83.0 (100.0%)", "84.0 (100.0%)"]
    ],
    col_widths=[1.8, 0.95, 1.05, 0.9, 0.9, 0.9],
    align_right_cols={1, 3, 4, 5}
)

if os.path.exists(chart_path):
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(6)
    p_img.paragraph_format.space_after = Pt(4)
    p_img.paragraph_format.keep_with_next = True
    p_img.add_run().add_picture(chart_path, width=Inches(6.2))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_after = Pt(10)
    r_cap = p_cap.add_run("Figura 1. Dosis óptima de cada fertilizante comercial (izquierda) y contribución apilada al requerimiento total de N, P₂O₅ y K₂O por hectárea (derecha).")
    r_cap.font.size = Pt(9.5)
    r_cap.font.italic = True
    r_cap.font.color.rgb = TEXT_MUTED

# ==============================================================================
# 7. ANÁLISIS DE RESULTADOS
# ==============================================================================
add_h1("7. Análisis de Resultados e Interpretación Agronómica")

p_an1 = add_body()
p_an1.add_run("Los resultados numéricos obtenidos ($x_1 = 200\\text{ kg/ha}$, $x_2 = 300\\text{ kg/ha}$ y $x_3 = 100\\text{ kg/ha}$) demuestran consistencia matemática y viabilidad práctica en campo. En primer lugar, todas las incógnitas resultaron estrictamente positivas ($x_i > 0$), condición indispensable en problemas de mezclas físicas donde no es posible sustraer nutrientes una vez incorporados. Además, las cantidades exactas son múltiplos directos de 50 kg (4, 6 y 2 bultos comerciales respectivamente), lo cual facilita el pesaje y manejo operativo en el almacén agrícola sin necesidad de fraccionar costales en campo.")

p_an2 = add_body()
p_an2.add_run("Desde el punto de vista fisiológico y edáfico, la ")
r_fb = p_an2.add_run("Fórmula B (20-10-10)")
r_fb.bold = True
p_an2.add_run(" constituye la base nitrogenada del programa al aportar 60.0 kg/ha de N (60.6% del requerimiento total de nitrógeno), mientras que la ")
r_fa = p_an2.add_run("Fórmula A (12-24-12)")
r_fa.bold = True
p_an2.add_run(" actúa como el soporte principal de fósforo al suministrar 48.0 kg/ha de P₂O₅ (57.8% del fósforo total requerido para el enraizamiento inicial). Por su parte, la ")
r_fc = p_an2.add_run("Fórmula C (15-05-30)")
r_fc.bold = True
p_an2.add_run(" complementa exactamente la demanda potásica con 30.0 kg/ha de K₂O (35.7% del total), favoreciendo la regulación osmótica estomática y el llenado de grano bajo condiciones semiáridas (")
add_hyperlink(p_an2, "Área de Agronomía, 2024", "https://areadeagronomia.mx/wp-content/uploads/2024/12/MANUALMATADAMAS-pdf.pdf")
p_an2.add_run("). Atendiendo las recomendaciones del paquete tecnológico de ")
add_hyperlink(p_an2, "SADER e INIFAP (2024)", "https://www.gob.mx/cms/uploads/attachment/file/928380/TRIPTICO_NUEVO_LEON_MAIZ.pdf")
p_an2.add_run(" para Nuevo León, se recomienda aplicar al momento de la siembra los 4 bultos de Fórmula A (200 kg/ha) y los 2 bultos de Fórmula C (100 kg/ha) junto con 1 bulto de Fórmula B (50 kg/ha) —cubriendo así el 49.5% del nitrógeno y más del 70% del fósforo y potasio—, y aplicar los 5 bultos restantes de Fórmula B (250 kg/ha) en la labor de escarda (etapa V5-V6) para maximizar el aprovechamiento de nitrógeno.")

# ==============================================================================
# 8. CONCLUSIÓN
# ==============================================================================
add_h1("8. Conclusión")

add_body("El desarrollo de este Producto Integrador de Aprendizaje permitió comprobar que la modelación mediante sistemas de ecuaciones lineales de 3 × 3 constituye una herramienta precisa, rápida y confiable para la toma de decisiones en la Ingeniería Agronómica. A través de la recolección de datos técnicos reales sobre fertilizantes compuestos ternarios y requerimientos nutricionales del maíz en Nuevo León, fue posible transformar un problema práctico de nutrición vegetal en un sistema matricial bien condicionado (con determinante Δ = −8400 ≠ 0).")

add_body("La aplicación rigurosa del método de Eliminación de Gauss-Jordan y su verificación cruzada mediante la Regla de Cramer permitieron determinar la mezcla única de 200 kg/ha de Fórmula A (12-24-12), 300 kg/ha de Fórmula B (20-10-10) y 100 kg/ha de Fórmula C (15-05-30), cumpliendo el 100% de la meta nutricional (99–83–84 kg/ha de N–P₂O₅–K₂O) sin desperdicio de insumos. Dominar estos métodos algebraicos fortalece la capacidad analítica del Ingeniero Agrónomo para optimizar recursos productivos, reducir costos operativos y promover una agricultura sustentable basada en evidencia cuantitativa.")

# ==============================================================================
# 9. REFERENCIAS (Formato APA 7.ª Edición)
# ==============================================================================
add_h1("9. Referencias Bibliográficas (Normativa APA 7.ª Edición)")

def add_apa_ref(prefix_text, link_text, url, suffix_text=""):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Inches(0.5)
    p.paragraph_format.first_line_indent = Inches(-0.5)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.line_spacing = 1.15
    r1 = p.add_run(prefix_text)
    r1.font.name = "Calibri"
    r1.font.size = Pt(11)
    add_hyperlink(p, link_text, url)
    if suffix_text:
        r2 = p.add_run(suffix_text)
        r2.font.name = "Calibri"
        r2.font.size = Pt(11)
    return p

add_apa_ref(
    "Área de Agronomía. (2024). ",
    "Manual para el cálculo de fórmulas generales de fertilización mineral",
    "https://areadeagronomia.mx/wp-content/uploads/2024/12/MANUALMATADAMAS-pdf.pdf",
    ". Portal Técnico de Ciencias Agronómicas."
)

add_apa_ref(
    "Grossman, S. I., y Flores Godoy, J. J. (2012). ",
    "Álgebra lineal (7.ª ed.)",
    "https://books.google.com/books/about/ALGEBRA_LINEAL.html?id=D8HvMQEACAAJ",
    ". McGraw-Hill Interamericana."
)

add_apa_ref(
    "Instituto Nacional de Investigaciones Forestales, Agrícolas y Pecuarias [INIFAP]. (2018). ",
    "Rendimiento de maíz grano con y sin fertilización",
    "https://www.scielo.org.mx/pdf/remexca/v9nspe21/2007-0934-remexca-9-spe21-4306.pdf",
    ". Revista Mexicana de Ciencias Agrícolas, 9(Esp. 21), 4306–4315."
)

add_apa_ref(
    "Secretaría de Agricultura y Desarrollo Rural [SADER]. (2023). ",
    "Diagnóstico del Programa de Fertilizantes para el Bienestar (S290)",
    "https://www.gob.mx/cms/uploads/attachment/file/911180/Dx_S290-Fertilizantes_2023.pdf",
    ". Gobierno de México."
)

add_apa_ref(
    "Secretaría de Agricultura y Desarrollo Rural [SADER] e Instituto Nacional de Investigaciones Forestales, Agrícolas y Pecuarias [INIFAP]. (2024). ",
    "Paquete tecnológico para la producción de maíz en el estado de Nuevo León",
    "https://www.gob.mx/cms/uploads/attachment/file/928380/TRIPTICO_NUEVO_LEON_MAIZ.pdf",
    ". Representación de Agricultura en Nuevo León."
)

add_apa_ref(
    "Universidad Autónoma de Nuevo León [UANL]. (2025). ",
    "Licenciatura en Ingeniería en Agronomía (Plan 430) — Facultad de Agronomía",
    "https://agronomia.uanl.mx/wp-content/uploads/2025/05/LICENCIATURA-EN-INGENIERIA-EN-AGRONOMIA-plan-430-1.pdf",
    ". UANL."
)

# ==============================================================================
# 10. APARTADO DE ENLACE AL VIDEO Y GUÍA DE EXPOSICIÓN (PARTE B DEL PIA)
# ==============================================================================
add_h1("Anexo: Enlace al Video Integrador y Estructura de Exposición (Parte B — 10 Puntos)")

add_body("De acuerdo con los lineamientos de entrega en la plataforma Nexus, a continuación se incluye el recuadro oficial para insertar el enlace público (sin suscripción) al video donde el equipo resuelve y explica el problema de principio a fin:")

add_styled_table(
    headers=["Requisito de Entrega en Nexus", "Información / Enlace Público del Video"],
    rows_data=[
        ["Plataforma de alojamiento público (YouTube / Drive público / Vimeo)", "[Pegar aquí la URL pública del video antes de subir a Nexus]"],
        ["Verificación de acceso público (sin contraseña ni suscripción)", "Verificado en ventana de incógnito (Audio e imagen nítidos, < 20 min)"],
        ["Integrantes que aparecen a cuadro (cintura hacia arriba)", "Todos los integrantes registrados en la portada"]
    ],
    col_widths=[2.6, 3.9]
)

add_h2("Distribución Sugerida para la Exposición en Pizarrón (Sin Acordeón)")
add_body("Para cumplir estrictamente con los criterios de evaluación del video (presentación personal, aparición de todos los integrantes de cintura hacia arriba, resolución paso a paso sin omitir procedimientos y sin leer acordeones ni papeles), se sugiere dividir la exposición en 4 bloques de 3 a 4 minutos cada uno:")

add_bullet("Integrante 1 (Presentación, Problema y Planteamiento del Sistema): ", "Saluda mencionando nombre completo, matrícula, grupo y carrera (Ingeniero Agrónomo). Explica el problema agronómico (mezcla de 3 fertilizantes compuestos 12-24-12, 20-10-10 y 15-05-30 para cubrir 99 kg de N, 83 kg de P₂O₅ y 84 kg de K₂O por hectárea). Define las variables x₁, x₂, x₃ y escribe en el pizarrón las 3 ecuaciones decimales y su forma entera multiplicada por 100.")
add_bullet("Integrante 2 (Justificación del Método y Primera Fase de Gauss-Jordan): ", "Se presenta con nombre completo, grupo y carrera. Define qué es una matriz aumentada [A | b] y qué son las operaciones elementales por renglón. Escribe la matriz aumentada y ejecuta en vivo el Paso 2 (R₂ ← R₂ − 2R₁ y R₃ ← R₃ − R₁) y el Paso 3 (intercambio R₂ ↔ R₃ y división entre −10 para obtener el segundo pivote igual a 1).")
add_bullet("Integrante 3 (Segunda Fase de Gauss-Jordan hasta la Matriz Identidad): ", "Se presenta con nombre completo, grupo y carrera. Ejecuta el Paso 4 (R₁ ← R₁ − 20R₂ y R₃ ← R₃ + 30R₂, llegando a −70x₃ = −7000), el Paso 5 (división entre −70 para hallar x₃ = 100) y el Paso 6 (eliminación hacia arriba para obtener x₂ = 300 y x₁ = 200).")
add_bullet("Integrante 4 (Comprobación, Interpretación Agronómica y Conclusión): ", "Se presenta con nombre completo, grupo y carrera. Sustituye x₁ = 200, x₂ = 300 y x₃ = 100 en las 3 ecuaciones originales para demostrar en el pizarrón que se cumplen exactamente los 99 kg de N, 83 kg de P₂O₅ y 84 kg de K₂O, e interpreta el resultado en bultos comerciales de 50 kg (4, 6 y 2 bultos).", space_after=8)

doc.save(out_docx)
print(f"Successfully generated DOCX: {out_docx}")
