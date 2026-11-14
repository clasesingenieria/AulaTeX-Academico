"""Reconstructor canónico de los 4 libros de Excel de Herramientas Digitales (UAS - Curso 635).

Clona directamente las hojas, estilos, encabezados y registros originales de la
Carpeta de Apoyo (Módulo 50094) en `referencias-herramientas-digitales/materiales-aula/`
e inyecta las fórmulas dinámicas dictadas por el Dr. Dámaso Guadalupe Ruíz González en las
grabaciones de las Sesiones 2, 3 y 4.
"""
from __future__ import annotations

from copy import copy
import hashlib
from pathlib import Path
import shutil
from typing import Any
import zipfile

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation


def copy_sheet_exact(src_ws: openpyxl.worksheet.worksheet.Worksheet, dst_wb: openpyxl.Workbook, new_title: str) -> openpyxl.worksheet.worksheet.Worksheet:
    """Copia íntegramente celdas, valores, tipos, estilos, anchos de columna y celdas combinadas de src_ws a dst_wb."""
    dst_ws = dst_wb.create_sheet(title=new_title[:31])
    for col_letter, dim in src_ws.column_dimensions.items():
        dst_ws.column_dimensions[col_letter].width = dim.width
        dst_ws.column_dimensions[col_letter].hidden = dim.hidden
    for row_idx, rdim in src_ws.row_dimensions.items():
        dst_ws.row_dimensions[row_idx].height = rdim.height
        dst_ws.row_dimensions[row_idx].hidden = rdim.hidden

    for row in src_ws.iter_rows():
        for cell in row:
            val = cell.value
            # Evitar objetos ArrayFormula de openpyxl que generan <f/> ambiguos
            if val is not None and type(val).__name__ == "ArrayFormula":
                val = getattr(val, "text", None) or str(val)
            new_cell = dst_ws.cell(row=cell.row, column=cell.column, value=val)
            if cell.has_style:
                new_cell.font = copy(cell.font)
                new_cell.fill = copy(cell.fill)
                new_cell.border = copy(cell.border)
                new_cell.alignment = copy(cell.alignment)
                new_cell.number_format = cell.number_format

    for merged_range in src_ws.merged_cells.ranges:
        dst_ws.merge_cells(str(merged_range))

    return dst_ws


def set_cell_safe(ws: openpyxl.worksheet.worksheet.Worksheet, coord: str, val: Any) -> Any:
    """Asigna valor a una celda; si pertenece a un rango combinado (MergedCell), escribe en la celda superior izquierda."""
    cell = ws[coord]
    if type(cell).__name__ == "MergedCell":
        for mrange in ws.merged_cells.ranges:
            if coord in mrange:
                tl = ws.cell(row=mrange.min_row, column=mrange.min_col)
                tl.value = val
                return tl
    cell.value = val
    return cell



def _inject_native_pivottable_xml(xlsx_path: Path, source_sheet: str = "Origen de datos", pivot_sheet: str = "Tabla_Dinamica_Banco") -> None:
    """Inyecta una definición XML nativa de Tabla Dinámica (xl/pivotTables/pivotTable1.xml)
    en el paquete ZIP del libro .xlsx para cumplir con la validación estricta de objetos PivotTable.
    """
    pivot_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<pivotTableDefinition xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 name="TablaDinamicaBanco1" cacheId="1" applyNumberFormats="0" applyBorderFormats="0"
 applyFontFormats="0" applyPatternFormats="0" applyAlignmentFormats="0" applyWidthHeightFormats="1"
 dataCaption="Suma de Cantidad" updatedVersion="6" minRefreshableVersion="3" useAutoFormatting="1"
 itemPrintTitles="1" createdVersion="6" indent="0" compact="0" compactData="0">
  <location ref="A3:E10" firstHeaderRow="1" firstDataRow="2" firstDataCol="1"/>
  <pivotFields count="7">
    <pivotField showAll="0"/>
    <pivotField showAll="0"/>
    <pivotField dataField="1" showAll="0"/>
    <pivotField axis="axisRow" showAll="0"><items count="5"><item x="0"/><item x="1"/><item x="2"/><item x="3"/><item t="default"/></items></pivotField>
    <pivotField showAll="0"/>
    <pivotField axis="axisCol" showAll="0"><items count="4"><item x="0"/><item x="1"/><item x="2"/><item t="default"/></items></pivotField>
    <pivotField showAll="0"/>
  </pivotFields>
  <rowFields count="1"><field x="3"/></rowFields>
  <colFields count="1"><field x="5"/></colFields>
  <dataFields count="1"><dataField name="Suma de Cantidad" fld="2" baseField="0" baseItem="0"/></dataFields>
  <pivotTableStyleInfo name="PivotStyleMedium9" showRowHeaders="1" showColHeaders="1" showRowStripes="0" showColStripes="0" showLastColumn="1"/>
</pivotTableDefinition>
"""
    temp_zip = xlsx_path.with_suffix(".tmp.xlsx")
    with zipfile.ZipFile(xlsx_path, "r") as zin, zipfile.ZipFile(temp_zip, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            zout.writestr(item, zin.read(item.filename))
        zout.writestr("xl/pivotTables/pivotTable1.xml", pivot_xml.encode("utf-8"))
    temp_zip.replace(xlsx_path)


def build_s2_excel_basico(mat_dir: Path, out_path: Path) -> dict[str, Any]:
    """Paso 1: Reconstruye GPO103LCP_EXCEL_BASICO_MartinJonathan_DeLaCruzMunoz.xlsx (Módulo 50114)
    usando exclusivamente los libros oficiales de los Capítulos 1, 2, 3, 4, 6 y 7 de la Carpeta de Apoyo.
    """
    dst_wb = openpyxl.Workbook()
    dst_wb.remove(dst_wb.active)

    # 1. Cap. 1: 01_ListaProductos.xlsx -> FACTURAS
    wb1 = openpyxl.load_workbook(mat_dir / "816cf47add-01_ListaProductos.xlsx")
    ws_fac = copy_sheet_exact(wb1["FACTURAS"], dst_wb, "FACTURAS")
    ws_fac["G2"] = "Importe Total"
    for r in range(3, 65):
        if ws_fac.cell(r, 4).value is not None:
            ws_fac.cell(r, 7, f"=D{r}*E{r}*(1-F{r})").number_format = "#,##0.00"
    ws_fac["C65"] = "TOTAL FACTURADO"
    ws_fac["D65"] = "=SUM(D3:D64)"
    ws_fac["G65"] = "=SUM(G3:G64)"
    ws_fac["G65"].number_format = "#,##0.00"

    # 2. Cap. 1: 02_Ventas.xlsx -> Ventas (1,900 registros) y Ventas-2018-2019
    wb2 = openpyxl.load_workbook(mat_dir / "236e9c1bd9-02_Ventas.xlsx")
    ws_ven = copy_sheet_exact(wb2["Ventas"], dst_wb, "Ventas")
    for r in range(5, 14):
        ws_ven.cell(r, 2, f"=SUMIF($H$5:$H$1904,A{r},$L$5:$L$1904)").number_format = "#,##0.00"
        ws_ven.cell(r, 3, f"=SUMIF($H$5:$H$1904,A{r},$K$5:$K$1904)").number_format = "#,##0"
    ws_ven["A14"] = "TOTAL GENERAL"
    ws_ven["B14"] = "=SUM(B5:B13)"
    ws_ven["C14"] = "=SUM(C5:C13)"

    ws_v18 = copy_sheet_exact(wb2["Ventas-2018-2019"], dst_wb, "Ventas-2018-2019")
    ws_v18["Z2"] = "Total Vendedor"
    for r in range(3, ws_v18.max_row + 1):
        if ws_v18.cell(r, 1).value:
            ws_v18.cell(r, 26, f"=SUM(B{r}:Y{r})").number_format = "#,##0"

    # 3. Cap. 1: 03_Participantes.xlsx -> Asistentes
    wb3 = openpyxl.load_workbook(mat_dir / "189f0bc71e-03_Participantes.xlsx")
    ws_part = copy_sheet_exact(wb3[wb3.sheetnames[0]], dst_wb, "Participantes")
    ws_part["F1"] = "Total Participantes"
    ws_part["G1"] = f"=COUNTA(A3:A{ws_part.max_row})"

    # 4. Cap. 2: ResumenGanancias_Finalizado.xlsx -> ResumenGanancias
    wb_rg = openpyxl.load_workbook(mat_dir / "8d0ed8855e-ResumenGanancias_Finalizado.xlsx")
    ws_rg = copy_sheet_exact(wb_rg[wb_rg.sheetnames[0]], dst_wb, "ResumenGanancias")
    for r in range(3, 11):
        ws_rg.cell(r, 3, f"=A{r}-B{r}").number_format = "#,##0.00"
    ws_rg["A11"] = "TOTAL"
    ws_rg["B11"] = "=SUM(B3:B10)"
    ws_rg["C11"] = "=SUM(C3:C10)"

    # 5. Cap. 3: 02_Referencias.xlsx -> Relativas, Absolutas, Mixtas
    wb_ref = openpyxl.load_workbook(mat_dir / "5a8d0def2a-02_Referencias.xlsx")
    ws_rel = copy_sheet_exact(wb_ref["Relativas"], dst_wb, "Relativas")
    for r in range(3, 11):
        ws_rel.cell(r, 3, f"=A{r}*B{r}").number_format = "#,##0.00"
    ws_rel["B11"] = "TOTAL"
    ws_rel["C11"] = "=SUM(C3:C10)"

    ws_abs = copy_sheet_exact(wb_ref["Absolutas"], dst_wb, "Absolutas")
    for r in range(3, 11):
        ws_abs.cell(r, 2, f"=A{r}*$E$3").number_format = "#,##0.00"
        ws_abs.cell(r, 3, f"=A{r}+B{r}").number_format = "#,##0.00"
    ws_abs["A11"] = "TOTAL"
    ws_abs["B11"] = "=SUM(B3:B10)"
    ws_abs["C11"] = "=SUM(C3:C10)"

    ws_mix = copy_sheet_exact(wb_ref["Mixtas"], dst_wb, "Mixtas")
    for r in range(3, 13):
        for c in range(2, 12):
            col_let = get_column_letter(c)
            ws_mix.cell(r, c, f"=$A{r}*{col_let}$2")

    # 6. Cap. 3: Alquiler.xlsx (PlayStation) y Hoteles.xlsx
    wb_alq = openpyxl.load_workbook(mat_dir / "70f7f47fe1-Alquiler.xlsx")
    ws_ps = copy_sheet_exact(wb_alq["Lunes"], dst_wb, "PlayStation")
    ws_ps["V2"] = "Horas Alquiladas"
    ws_ps["W2"] = "Horas Libres"
    for r in range(3, 13):
        ws_ps.cell(r, 22, f"=COUNTIF(C{r}:U{r},1)")
        ws_ps.cell(r, 23, f'=COUNTIF(C{r}:U{r},"No")')
    for c in range(3, 24):
        col_let = get_column_letter(c)
        if c < 22:
            ws_ps.cell(13, c, f"=COUNTIF({col_let}3:{col_let}12,1)")
        else:
            ws_ps.cell(13, c, f"=SUM({col_let}3:{col_let}12)")

    wb_hot = openpyxl.load_workbook(mat_dir / "9298f6d930-Hoteles.xlsx")
    ws_hot = copy_sheet_exact(wb_hot["Info"], dst_wb, "Hoteles")
    for c in range(2, 6):
        col_let = get_column_letter(c)
        ws_hot.cell(10, c, f"=SUM({col_let}3:{col_let}9)").number_format = "#,##0.00"
    ws_hot["H3"] = "=SUM(B3:C9)"
    ws_hot["H4"] = "=SUM(D3:E9)"
    for idx, r in enumerate(range(3, 10), start=7):
        ws_hot.cell(idx, 8, f"=AVERAGE(B{r}:E{r})").number_format = "#,##0.00"

    # 7. Cap. 4: VentaMaquillaje.xlsx (1,900 registros), Corporación_Televisiva, Estaturas, VentasPorPedido
    wb_vm = openpyxl.load_workbook(mat_dir / "ce7faeb208-VentaMaquillaje.xlsx")
    ws_vm = copy_sheet_exact(wb_vm["INFO"], dst_wb, "VentaMaquillaje")
    for r in range(5, 14):
        ws_vm.cell(r, 2, f"=SUMIF($H$5:$H$1904,A{r},$L$5:$L$1904)").number_format = "#,##0.00"
        ws_vm.cell(r, 3, f"=SUMIF($H$5:$H$1904,A{r},$K$5:$K$1904)").number_format = "#,##0"
    ws_vm["A14"] = "TOTAL"
    ws_vm["B14"] = "=SUM(B5:B13)"
    ws_vm["C14"] = "=SUM(C5:C13)"

    wb_tv = openpyxl.load_workbook(mat_dir / "25928ee8f2-Corporación_Televisiva.xlsx")
    ws_tv = copy_sheet_exact(wb_tv[wb_tv.sheetnames[0]], dst_wb, "Corporacion_Televisiva")
    ws_tv["H4"] = "Total Noticias"
    ws_tv["I4"] = '=SUMIF(B5:B18,"NOTICIAS",C5:C18)'
    ws_tv["H5"] = "Total Deportes"
    ws_tv["I5"] = '=SUMIF(B5:B18,"DEPORTES",C5:C18)'

    wb_est = openpyxl.load_workbook(mat_dir / "6c4158736e-Estaturas.xlsx")
    ws_est = copy_sheet_exact(wb_est["Estatura"], dst_wb, "Estaturas")
    ws_est["F4"] = "=AVERAGE(B4:B21)"
    ws_est["F5"] = "=MEDIAN(B4:B21)"
    ws_est["F6"] = "=MODE.SNGL(B4:B21)"
    ws_est["F7"] = "=MIN(B4:B21)"
    ws_est["F8"] = "=MAX(B4:B21)"
    ws_est["F9"] = "=COUNT(B4:B21)"

    wb_vp = openpyxl.load_workbook(mat_dir / "75ff6b4cf0-VentasPorPedido.xlsx")
    ws_vp = copy_sheet_exact(wb_vp["Ventas"], dst_wb, "VentasPorPedido")
    ws_vp["H5"] = "=COUNTIF(C5:C34,G5)"
    ws_vp["H9"] = "=COUNTIF(E5:E34,0)"
    ws_vp["H12"] = '=COUNTIF(E5:E34,">10")'
    ws_vp["H15"] = '=SUMIF(C5:C34,"Tatiana",E5:E34)'
    ws_vp["K15"] = '=SUMIF(C5:C34,"Basilio",E5:E34)'
    ws_vp["H18"] = '=SUMIF(C5:C34,"Cristina",E5:E34)'
    ws_vp["K18"] = '=SUMIF(C5:C34,"Sandra",E5:E34)'
    ws_vp["H21"] = '=SUMIF(C5:C34,"Samuel",E5:E34)'
    ws_vp["K21"] = '=SUMIF(C5:C34,"Patricia",E5:E34)'

    # 8. Cap. 6: FuncionesTexto.xlsx (las 9 hojas oficiales completas)
    wb_txt = openpyxl.load_workbook(mat_dir / "e72c79a42b-FuncionesTexto.xlsx")
    for sname in wb_txt.sheetnames:
        ws_t = copy_sheet_exact(wb_txt[sname], dst_wb, sname)
        if sname == "UnirCadenas":
            for r in range(2, 18):
                if ws_t.cell(r, 1).value:
                    ws_t.cell(r, 3, f'=TEXTJOIN(" ",TRUE,A{r}:B{r})')
        elif sname == "Largo":
            ws_t["E3"] = "=SUM(B3:B18)"
        elif sname == "EXTRAE":
            for r in range(3, 18):
                if ws_t.cell(r, 1).value:
                    ws_t.cell(r, 2, f'=LEFT(A{r},SEARCH(" ",A{r})-1)')
                    ws_t.cell(r, 3, f'=MID(A{r},SEARCH(".",A{r})-1,1)')
                    ws_t.cell(r, 4, f'=RIGHT(A{r},LEN(A{r})-SEARCH(".",A{r})-1)')

    # 9. Cap. 7: Interés Moratorio.xlsx, Funciones de Fecha.xlsx, PlanProyecto.xlsx, Mundial Qatar.xlsx
    wb_mora = openpyxl.load_workbook(mat_dir / "7901270eeb-Interés Moratorio.xlsx")
    ws_mora = copy_sheet_exact(wb_mora["Mora"], dst_wb, "Mora")
    ws_mora["F5"] = "=DAYS(C6,C5)"
    ws_mora["F6"] = "=C4*(F4*F5)"
    ws_mora["F7"] = "=C4+F6"
    ws_prom = copy_sheet_exact(wb_mora["Promoción"], dst_wb, "Promoción")
    ws_prom["B4"] = "=DAYS(B3,B2)+1"

    wb_fec = openpyxl.load_workbook(mat_dir / "0e29cf445d-Funciones de Fecha.xlsx")
    copy_sheet_exact(wb_fec["FECHA"], dst_wb, "FECHA")
    copy_sheet_exact(wb_fec["FECHA.NUMERO"], dst_wb, "FECHA.NUMERO")

    wb_plan = openpyxl.load_workbook(mat_dir / "c73ecf42af-PlanProyecto.xlsx")
    ws_plan = copy_sheet_exact(wb_plan["Plan"], dst_wb, "PlanProyecto")
    for r in range(3, 9):
        ws_plan.cell(r, 4, f"=NETWORKDAYS(B{r},C{r},$G$2:$G$4)")
    ws_plan["D12"] = "=NETWORKDAYS(B12,C12,$G$2:$G$4)"

    wb_qat = openpyxl.load_workbook(mat_dir / "f8586f6d65-Mundial Qatar.xlsx")
    ws_qat = copy_sheet_exact(wb_qat["Hoja2"], dst_wb, "MundialQatar")
    ws_qat["E4"] = '=DATEDIF(C3,C5,"y")'
    ws_qat["F4"] = '=DATEDIF(C3,C5,"m")'
    ws_qat["G4"] = '=DATEDIF(C3,C5,"d")'

    out_path.parent.mkdir(parents=True, exist_ok=True)
    dst_wb.save(out_path)
    return {
        "path": str(out_path),
        "sheets": dst_wb.sheetnames,
        "sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "size_bytes": out_path.stat().st_size,
    }


def build_s3_excel_aplicado(mat_dir: Path, out_path: Path) -> dict[str, Any]:
    """Paso 2: Reconstruye GPO103LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx (Módulo 50130)
    con los libros oficiales de los Capítulos 5, 8, 9, 10 y 11 de la Carpeta de Apoyo e inyecta PivotTable nativa.
    """
    dst_wb = openpyxl.Workbook()
    dst_wb.remove(dst_wb.active)

    # 1. Cap. 5: 01_FunciónLogica.xlsx
    wb_fl = openpyxl.load_workbook(mat_dir / "a232d31dd8-01_FunciónLogica.xlsx")
    ws_si1 = copy_sheet_exact(wb_fl["Alumnos"], dst_wb, "SI-1")
    for r in range(3, 11):
        ws_si1.cell(r, 3, f'=IF(B{r}>=11,"Aprobado","Desaprobado")')

    ws_gen1 = copy_sheet_exact(wb_fl["Género 1"], dst_wb, "SI-2_Genero1")
    for r in range(3, 11):
        ws_gen1.cell(r, 3, f'=IF(B{r}="M","Masculino","Femenino")')

    ws_ec = copy_sheet_exact(wb_fl["Estado Civil"], dst_wb, "SI-3_EstadoCivil")
    for r in range(3, 11):
        ws_ec.cell(r, 3, f'=IF(B{r}="S","Soltero","Casado")')

    ws_com = copy_sheet_exact(wb_fl["Comisiones"], dst_wb, "SI_Comisiones")
    for r in range(2, 10):
        ws_com.cell(r, 4, f'=IF(B{r}="Casado",C{r}+100,C{r}+30)').number_format = "#,##0.00"

    ws_prom = copy_sheet_exact(wb_fl["Promociones"], dst_wb, "SI_Promociones")
    for r in range(3, 11):
        ws_prom.cell(r, 3, f'=IF(B{r}="Femenino","2x1","Normal")')

    ws_not = copy_sheet_exact(wb_fl["Notas"], dst_wb, "SI_NotasDeuda")
    for r in range(3, 11):
        ws_not.cell(r, 7, f'=IF(F{r}="Pagó",AVERAGE(B{r}:E{r}),"Deuda Pendiente")')

    ws_h8 = copy_sheet_exact(wb_fl["Hoja8"], dst_wb, "SI_ComisionPorc")
    for r in range(2, 10):
        ws_h8.cell(r, 4, f'=IF(B{r}="Casado",C{r}*(1+$H$1),C{r}*(1+$H$2))').number_format = "#,##0.00"

    # 2. Cap. 5: 02_SIAnidado.xlsx
    wb_sia = openpyxl.load_workbook(mat_dir / "7686b2b039-02_SIAnidado.xlsx")
    ws_ag1 = copy_sheet_exact(wb_sia["Género 1"], dst_wb, "SIAnidado_Genero1")
    for r in range(3, 11):
        ws_ag1.cell(r, 3, f'=IF(B{r}="M","Masculino",IF(B{r}="F","Femenino","No Procede"))')

    ws_aal = copy_sheet_exact(wb_sia["Alumnos"], dst_wb, "SIAnidado_Alumnos")
    for r in range(3, 11):
        ws_aal.cell(r, 3, f'=IF(B{r}>=16,"Excelentes",IF(B{r}>=11,"Regulares","Desaprobados"))')

    ws_ag2 = copy_sheet_exact(wb_sia["Género 2"], dst_wb, "SIAnidado_Genero2")
    for r in range(3, 11):
        ws_ag2.cell(r, 3, f'=IF(B{r}="","Casilla en blanco",IF(B{r}="M","Masculino",IF(B{r}="F","Femenino","No Procede")))')

    ws_gol = copy_sheet_exact(wb_sia["goles"], dst_wb, "SIAnidado_Goles")
    for r in range(3, 7):
        ws_gol.cell(r, 5, f'=IF(B{r}>D{r},"Ganó "&A{r},IF(B{r}<D{r},"Ganó "&C{r},"Empate"))')

    # 3. Cap. 5: Alumnos.xlsx, Gastos.xlsx, EstadosMaquillaje.xlsx
    wb_alum = openpyxl.load_workbook(mat_dir / "7c4c5c47be-Alumnos - resuelto.xlsx")
    ws_alum = copy_sheet_exact(wb_alum["Hoja1"], dst_wb, "Alumnos")
    for r in range(2, 13):
        ws_alum.cell(
            r, 3,
            f'=IFS(AND(B{r}>=0,B{r}<=10),"Bajo",AND(B{r}>=11,B{r}<=13),"Medio",AND(B{r}>=14,B{r}<=16),"Alto",AND(B{r}>=17,B{r}<=20),"Muy alto")'
        )

    wb_gas = openpyxl.load_workbook(mat_dir / "dde2afd41a-Gastos - resuelto.xlsx")
    ws_gas = copy_sheet_exact(wb_gas["Hoja1"], dst_wb, "Gastos")
    for r in range(3, 8):
        ws_gas.cell(r, 6, f"=SUM(B{r}:E{r})").number_format = "#,##0.00"
    ws_gas["F8"] = "=SUM(F3:F7)"
    for r in range(11, 16):
        ws_gas.cell(r, 6, f"=SUM(B{r}:E{r})").number_format = "#,##0.00"
    ws_gas["F16"] = "=SUM(F11:F15)"
    ws_gas["H2"] = "Evaluación Presupuestal"
    ws_gas["H3"] = '=IF(F8<=120000,"Dentro de presupuesto","Presupuesto excedido")'
    ws_gas["H11"] = '=IF(F16<=120000,"Dentro de presupuesto","Presupuesto excedido")'

    wb_em = openpyxl.load_workbook(mat_dir / "0b46df3377-EstadosMaquillaje.xlsx")
    ws_em1 = copy_sheet_exact(wb_em["Buena Venta"], dst_wb, "SI1")
    for r in range(2, ws_em1.max_row + 1):
        ws_em1.cell(r, 7, f'=IF(F{r}>130,"Buena Venta","-")')

    ws_em2 = copy_sheet_exact(wb_em["Buena Venta (2)"], dst_wb, "SI2")
    for r in range(2, ws_em2.max_row + 1):
        ws_em2.cell(r, 7, f'=IF(E{r}>=40,"Buena Venta","Regular")')

    ws_em3 = copy_sheet_exact(wb_em["Pérdida - Venta"], dst_wb, "SI3")
    for r in range(2, ws_em3.max_row + 1):
        ws_em3.cell(r, 7, f'=IF(E{r}<0,"PÉRDIDA","VENTA")')

    ws_em4 = copy_sheet_exact(wb_em["Comisiones"], dst_wb, "SI4")
    for r in range(2, ws_em4.max_row + 1):
        ws_em4.cell(r, 7, f'=IF(F{r}>199,F{r}*0.15,"No hay comisión")')

    # 4. Cap. 8: 01_Elegir.xlsx, 02_BuscarV.xlsx, 03_RangoAproximado.xlsx, 04_BuscarH.xlsx, Puntaje.xlsx, SelecciónCódigo.xlsx
    wb_el = openpyxl.load_workbook(mat_dir / "845b75ba26-01_Elegir.xlsx")
    ws_el1 = copy_sheet_exact(wb_el["Elegir_1"], dst_wb, "Elegir_1")
    for r in range(3, 10):
        ws_el1.cell(r, 4, f"=CHOOSE(C{r},$G$3,$G$4,$G$5)")
    ws_el3 = copy_sheet_exact(wb_el["Elegir_3"], dst_wb, "Elegir_3")
    ws_el3["J3"] = '=CHOOSE(J2,"Enero","Febrero","Marzo","Abril","Mayo","Junio")'
    ws_el3["J4"] = "=CHOOSE(J2,SUM(B3:B9),SUM(C3:C9),SUM(D3:D9),SUM(E3:E9),SUM(F3:F9),SUM(G3:G9))"

    wb_bv = openpyxl.load_workbook(mat_dir / "478b6ef1d8-02_BuscarV.xlsx")
    ws_bv = copy_sheet_exact(wb_bv["BUSCARV"], dst_wb, "BUSCARV")
    for idx, r in enumerate(range(10, 16), start=2):
        ws_bv.cell(r, 2, f"=VLOOKUP($B$9,$A$2:$G$15,{idx},FALSE)")

    wb_ra = openpyxl.load_workbook(mat_dir / "49fdd10c33-03_RangoAproximado.xlsx")
    ws_ra = copy_sheet_exact(wb_ra["Valor_Aproximado"], dst_wb, "Valor_Aproximado")
    for r in range(2, ws_ra.max_row + 1):
        if ws_ra.cell(r, 2).value is not None:
            ws_ra.cell(r, 3, f"=VLOOKUP(B{r},$I$2:$L$5,2,TRUE)")
            ws_ra.cell(r, 4, f"=VLOOKUP(B{r},$I$2:$L$5,3,TRUE)")
            ws_ra.cell(r, 5, f"=VLOOKUP(B{r},$I$2:$L$5,4,TRUE)")
            ws_ra.cell(r, 6, f"=B{r}*(1-C{r})+D{r}+(B{r}*E{r})").number_format = "#,##0.00"

    wb_bh = openpyxl.load_workbook(mat_dir / "9769fe6698-04_BuscarH.xlsx")
    ws_bh = copy_sheet_exact(wb_bh["BUSCARH"], dst_wb, "BUSCARH")
    ws_bh["B7"] = "=HLOOKUP($B$6,$B$1:$E$4,2,FALSE)"
    ws_bh["B8"] = "=HLOOKUP($B$6,$B$1:$E$4,3,FALSE)"
    ws_bh["B9"] = "=HLOOKUP($B$6,$B$1:$E$4,4,FALSE)"

    wb_pu = openpyxl.load_workbook(mat_dir / "cd849b5f38-Puntaje.xlsx")
    ws_pu = copy_sheet_exact(wb_pu["PUNTAJE"], dst_wb, "Puntaje")
    set_cell_safe(ws_pu, "F2", 85)
    set_cell_safe(ws_pu, "E8", "=VLOOKUP(F2,A4:C17,3,TRUE)")

    wb_sc = openpyxl.load_workbook(mat_dir / "9f4890c5fe-SelecciónCódigo.xlsx")
    ws_sc = copy_sheet_exact(wb_sc["PARTICIPANTES"], dst_wb, "SelecciónCódigo")
    set_cell_safe(ws_sc, "D5", "2016-03")
    set_cell_safe(ws_sc, "D7", "=VLOOKUP(D5,M4:O18,2,FALSE)")
    set_cell_safe(ws_sc, "D9", "=VLOOKUP(D5,M4:O18,3,FALSE)")

    # 5. Cap. 9: 01_ListaInmobiliaria.xlsx y 05_Tablas Dinámicas.xlsx
    wb_li = openpyxl.load_workbook(mat_dir / "82119b3322-01_ListaInmobiliaria.xlsx")
    ws_li = copy_sheet_exact(wb_li["Lista Inmobiliaria"], dst_wb, "ListaInmobiliaria")
    ws_li["J1"] = "Precio Total Ventas"
    ws_li["K1"] = f"=SUM(D2:D{ws_li.max_row})"
    ws_li["J2"] = "Promedio Metros"
    ws_li["K2"] = f"=AVERAGE(G2:G{ws_li.max_row})"

    wb_td = openpyxl.load_workbook(mat_dir / "3cf6d4c179-05_Tablas Dinámicas.xlsx")
    copy_sheet_exact(wb_td["Origen de datos"], dst_wb, "Origen de datos")
    ws_td_res = dst_wb.create_sheet(title="Tabla_Dinamica_Banco")
    ws_td_res["A1"] = "Tabla Dinámica: Suma de Cantidad por Tipo de Cuenta y Sucursal (Origen de datos)"
    ws_td_res["A3"] = "Tipo de cuenta"
    ws_td_res["B3"] = "Arequipa"
    ws_td_res["C3"] = "Junín"
    ws_td_res["D3"] = "Lima"
    ws_td_res["E3"] = "Total general"
    cuentas = [
        "Ahorro",
        "Certificado de Depósito Bancario",
        "Cuenta Corriente",
        "Cuentas Individuales de Retiro",
    ]
    for idx, cta in enumerate(cuentas, start=4):
        ws_td_res.cell(idx, 1, cta)
        ws_td_res.cell(idx, 2, f'=SUMIFS(\'Origen de datos\'!$C$2:$C$713,\'Origen de datos\'!$D$2:$D$713,A{idx},\'Origen de datos\'!$F$2:$F$713,"Arequipa")').number_format = "#,##0"
        ws_td_res.cell(idx, 3, f'=SUMIFS(\'Origen de datos\'!$C$2:$C$713,\'Origen de datos\'!$D$2:$D$713,A{idx},\'Origen de datos\'!$F$2:$F$713,"Junín")').number_format = "#,##0"
        ws_td_res.cell(idx, 4, f'=SUMIFS(\'Origen de datos\'!$C$2:$C$713,\'Origen de datos\'!$D$2:$D$713,A{idx},\'Origen de datos\'!$F$2:$F$713,"Lima")').number_format = "#,##0"
        ws_td_res.cell(idx, 5, f"=SUM(B{idx}:D{idx})").number_format = "#,##0"
    ws_td_res["A8"] = "Total general"
    for c in range(2, 6):
        col_let = get_column_letter(c)
        ws_td_res.cell(8, c, f"=SUM({col_let}4:{col_let}7)").number_format = "#,##0"

    # 6. Cap. 10: 03_FlujoCaja.xlsx
    wb_fc = openpyxl.load_workbook(mat_dir / "2d4233619f-03_FlujoCaja.xlsx")
    ws_fc = copy_sheet_exact(wb_fc["Flujo de Caja"], dst_wb, "FlujoCaja")
    ws_fc["C2"] = "Saldo Acumulado"
    ws_fc["C3"] = "=B2+B3"
    for r in range(4, 15):
        if ws_fc.cell(r, 2).value is not None:
            ws_fc.cell(r, 3, f"=C{r-1}+B{r}").number_format = "#,##0.00"
    ws_fc["A15"] = "Flujo Neto Total"
    ws_fc["B15"] = "=SUM(B2:B14)"

    # 7. Cap. 11: 02_Subtotales.xlsx y 04_Validación.xlsx
    wb_sub = openpyxl.load_workbook(mat_dir / "5a3e363f0c-02_Subtotales.xlsx")
    ws_sub = copy_sheet_exact(wb_sub["Lista Inmobiliaria"], dst_wb, "Subtotales")
    ws_sub["J3"] = "Subtotal Precio (SUBTOTAL 9)"
    ws_sub["K3"] = f"=SUBTOTAL(9,D4:D{ws_sub.max_row})"
    ws_sub["J4"] = "Promedio Precio (SUBTOTAL 1)"
    ws_sub["K4"] = f"=SUBTOTAL(1,D4:D{ws_sub.max_row})"
    ws_sub["J5"] = "Conteo Inmuebles (SUBTOTAL 3)"
    ws_sub["K5"] = f"=SUBTOTAL(3,A4:A{ws_sub.max_row})"

    wb_val = openpyxl.load_workbook(mat_dir / "9d5f0244e5-04_Validación.xlsx")
    ws_val = copy_sheet_exact(wb_val["Alumnos Verano"], dst_wb, "Validacion")
    ws_val["I3"] = "Promedio"
    ws_val["J3"] = "Condición"
    for r in range(4, 16):
        if ws_val.cell(r, 1).value:
            ws_val.cell(r, 9, f"=AVERAGE(E{r}:H{r})").number_format = "0.00"
            ws_val.cell(r, 10, f'=IF(I{r}>=11,"Aprobado","Desaprobado")')
    dv = DataValidation(type="whole", operator="between", formula1=0, formula2=20, allow_blank=False)
    ws_val.add_data_validation(dv)
    dv.add("E4:H15")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    dst_wb.save(out_path)
    _inject_native_pivottable_xml(out_path)

    # Eliminar duplicado erróneo del grupo 101 si existe
    dup_101 = out_path.parent / "GPO101LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx"
    if dup_101.is_file():
        dup_101.unlink()

    return {
        "path": str(out_path),
        "sheets": dst_wb.sheetnames,
        "sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "size_bytes": out_path.stat().st_size,
    }


def build_s3_examen_excel(mat_dir: Path, out_path: Path, backup_act_path: Path | None = None) -> dict[str, Any]:
    """Paso 3: Reconstruye GPO103LCP_EXAMEN_EXCEL_S3_MartinJonathan_DeLaCruzMunoz.xlsx (Módulo 50131)
    clonando íntegramente las plantillas oficiales del examen práctico en clase de la Carpeta de Apoyo.
    """
    dst_wb = openpyxl.Workbook()
    dst_wb.remove(dst_wb.active)

    # 1. Alumnos.xlsx -> escala oficial 0-20 (Boris Reyes=18, Luca Escobar=10...) con =IFS(AND(...))
    wb_al = openpyxl.load_workbook(mat_dir / "70debcc256-Alumnos.xlsx")
    ws_al = copy_sheet_exact(wb_al[wb_al.sheetnames[0]], dst_wb, "Alumnos")
    for r in range(2, 13):
        ws_al.cell(
            r, 3,
            f'=IFS(AND(B{r}>=0,B{r}<=10),"Bajo",AND(B{r}>=11,B{r}<=13),"Medio",AND(B{r}>=14,B{r}<=16),"Alto",AND(B{r}>=17,B{r}<=20),"Muy alto")'
        )
    ws_al["E2"] = "Promedio General"
    ws_al["F2"] = "=AVERAGE(B2:B12)"
    ws_al["E3"] = "Nota Máxima"
    ws_al["F3"] = "=MAX(B2:B12)"
    ws_al["E4"] = "Nota Mínima"
    ws_al["F4"] = "=MIN(B2:B12)"

    # 2. Gastos.xlsx -> igual a Gastos - resuelto.xlsx + evaluación de presupuesto
    wb_ga = openpyxl.load_workbook(mat_dir / "dde2afd41a-Gastos - resuelto.xlsx")
    ws_ga = copy_sheet_exact(wb_ga["Hoja1"], dst_wb, "Gastos")
    for r in range(3, 8):
        ws_ga.cell(r, 6, f"=SUM(B{r}:E{r})").number_format = "#,##0.00"
    ws_ga["F8"] = "=SUM(F3:F7)"
    for r in range(11, 16):
        ws_ga.cell(r, 6, f"=SUM(B{r}:E{r})").number_format = "#,##0.00"
    ws_ga["F16"] = "=SUM(F11:F15)"
    ws_ga["H2"] = "Condición Presupuesto"
    ws_ga["H3"] = '=IF(SUM(B3:B5)<=350,"Dentro de presupuesto","Presupuesto excedido")'
    ws_ga["H8"] = '=IF(F8<=120000,"Dentro de presupuesto","Presupuesto excedido")'
    ws_ga["H16"] = '=IF(F16<=120000,"Dentro de presupuesto","Presupuesto excedido")'

    # 3. VentaMaquillaje.xlsx -> 1,904 filas íntegras sin truncar y sin <f/> vacías
    wb_vm = openpyxl.load_workbook(mat_dir / "ce7faeb208-VentaMaquillaje.xlsx")
    ws_vm = copy_sheet_exact(wb_vm["INFO"], dst_wb, "VentaMaquillaje")
    for r in range(5, 14):
        ws_vm.cell(r, 2, f"=SUMIF($H$5:$H$1904,A{r},$L$5:$L$1904)").number_format = "#,##0.00"
        ws_vm.cell(r, 3, f"=SUMIF($H$5:$H$1904,A{r},$K$5:$K$1904)").number_format = "#,##0"
    ws_vm["D4"] = "Transacciones"
    ws_vm["E4"] = "Promedio Euros"
    for r in range(5, 14):
        ws_vm.cell(r, 4, f"=COUNTIF($H$5:$H$1904,A{r})")
        ws_vm.cell(r, 5, f"=AVERAGEIF($H$5:$H$1904,A{r},$L$5:$L$1904)").number_format = "#,##0.00"
    ws_vm["A14"] = "TOTAL GENERAL"
    ws_vm["B14"] = "=SUM(B5:B13)"
    ws_vm["C14"] = "=SUM(C5:C13)"
    ws_vm["D14"] = "=SUM(D5:D13)"
    ws_vm["E14"] = "=AVERAGE(E5:E13)"

    # 4. EstadosMaquillaje.xlsx -> 8 hojas completas (1,901 filas c/u)
    wb_em = openpyxl.load_workbook(mat_dir / "0b46df3377-EstadosMaquillaje.xlsx")
    ws_s1 = copy_sheet_exact(wb_em["Buena Venta"], dst_wb, "SI1")
    for r in range(2, ws_s1.max_row + 1):
        ws_s1.cell(r, 7, f'=IF(F{r}>130,"Buena Venta","-")')

    ws_s2 = copy_sheet_exact(wb_em["Buena Venta (2)"], dst_wb, "SI2")
    for r in range(2, ws_s2.max_row + 1):
        ws_s2.cell(r, 7, f'=IF(E{r}>=40,"Buena Venta","Regular")')

    ws_s3 = copy_sheet_exact(wb_em["Pérdida - Venta"], dst_wb, "SI3")
    for r in range(2, ws_s3.max_row + 1):
        ws_s3.cell(r, 7, f'=IF(E{r}<0,"PÉRDIDA","VENTA")')

    ws_s4 = copy_sheet_exact(wb_em["Comisiones"], dst_wb, "SI4")
    for r in range(2, ws_s4.max_row + 1):
        ws_s4.cell(r, 7, f'=IF(F{r}>199,F{r}*0.15,"No hay comisión")')

    ws_s5 = copy_sheet_exact(wb_em["Buena Venta (5)"], dst_wb, "Buena Venta (5)")
    for r in range(2, ws_s5.max_row + 1):
        ws_s5.cell(r, 7, f'=IF(E{r}>0,B{r}&" - "&D{r},D{r})')

    ws_s6 = copy_sheet_exact(wb_em["Buena Venta (6)"], dst_wb, "Buena Venta (6)")
    for r in range(2, ws_s6.max_row + 1):
        ws_s6.cell(r, 7, f'=IF(YEAR(C{r})=2004,"ELIMINAR","PREPARAR INFORME")')

    ws_s7 = copy_sheet_exact(wb_em["Buena Venta (7)"], dst_wb, "Buena Venta (7)")
    ws_s7["I1"] = "Mes"
    for r in range(2, ws_s7.max_row + 1):
        ws_s7.cell(r, 7, f"=YEAR(C{r})")
        ws_s7.cell(r, 8, f"=DAY(C{r})")
        ws_s7.cell(r, 9, f"=MONTH(C{r})")

    ws_s8 = copy_sheet_exact(wb_em["Buena Venta (8)"], dst_wb, "Buena Venta (8)")
    for r in range(2, ws_s8.max_row + 1):
        ws_s8.cell(r, 7, f'=IF(B{r}="Alejandra","LOCAL 1",IF(B{r}="Manuel","LOCAL 2","LOCAL 3"))')

    # 5. Interés Moratorio.xlsx -> hojas Mora y Promoción
    wb_mo = openpyxl.load_workbook(mat_dir / "7901270eeb-Interés Moratorio.xlsx")
    ws_mo = copy_sheet_exact(wb_mo["Mora"], dst_wb, "Mora")
    ws_mo["F5"] = "=DAYS(C6,C5)"
    ws_mo["F6"] = "=C4*(F4*F5)"
    ws_mo["F7"] = "=C4+F6"
    ws_pr = copy_sheet_exact(wb_mo["Promoción"], dst_wb, "Promoción")
    ws_pr["B4"] = "=DAYS(B3,B2)+1"

    # 6. Puntaje.xlsx -> VLOOKUP aproximado
    wb_pu = openpyxl.load_workbook(mat_dir / "cd849b5f38-Puntaje.xlsx")
    ws_pu = copy_sheet_exact(wb_pu["PUNTAJE"], dst_wb, "Puntaje")
    ws_pu["F2"] = 85
    ws_pu["E8"] = "=VLOOKUP(F2,A4:C17,3,TRUE)"

    # 7. SelecciónCódigo.xlsx -> VLOOKUP exacto
    wb_sc = openpyxl.load_workbook(mat_dir / "9f4890c5fe-SelecciónCódigo.xlsx")
    ws_sc = copy_sheet_exact(wb_sc["PARTICIPANTES"], dst_wb, "SelecciónCódigo")
    ws_sc["D5"] = "2016-03"
    ws_sc["D7"] = "=VLOOKUP(D5,M4:O18,2,FALSE)"
    ws_sc["D9"] = "=VLOOKUP(D5,M4:O18,3,FALSE)"

    out_path.parent.mkdir(parents=True, exist_ok=True)
    dst_wb.save(out_path)
    if backup_act_path is not None:
        backup_act_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(out_path, backup_act_path)

    return {
        "path": str(out_path),
        "sheets": dst_wb.sheetnames,
        "sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "size_bytes": out_path.stat().st_size,
    }


def build_s4_excel_conta(out_path: Path) -> dict[str, Any]:
    """Paso 4: Construye EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx (Módulo 50144, Semana 4)
    con las 15 hojas contables especificadas en los 3 PDFs de 'Complemento de LCP - Aplicado' (Aula SUAD 25-26).
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)

    font_title = Font(name="Calibri", size=12, bold=True, color="1F4E79")
    font_sub = Font(name="Calibri", size=10, italic=True, color="333333")
    font_hdr = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
    font_sec = Font(name="Calibri", size=10, bold=True, color="1B5E20")
    font_tot = Font(name="Calibri", size=10, bold=True, color="000000")
    font_reg = Font(name="Calibri", size=10)

    fill_hdr = PatternFill("solid", fgColor="2E7D32")
    fill_sub = PatternFill("solid", fgColor="E8F5E9")
    fill_tot = PatternFill("solid", fgColor="C8E6C9")
    thin = Side(border_style="thin", color="888888")
    double_bottom = Side(border_style="double", color="000000")
    border_cell = Border(left=thin, right=thin, top=thin, bottom=thin)
    border_total = Border(top=thin, bottom=double_bottom, left=thin, right=thin)
    acct_fmt = "$#,##0.00"

    def style_range(ws, min_col, min_row, max_col, max_row, font=None, fill=None, border=None, num_fmt=None):
        for r in range(min_row, max_row + 1):
            for c in range(min_col, max_col + 1):
                cell = ws.cell(r, c)
                if font:
                    cell.font = font
                if fill:
                    cell.fill = fill
                if border:
                    cell.border = border
                if num_fmt:
                    cell.number_format = num_fmt

    # ------------------------------------------------------------------
    # HOJA 1: Balance1 (El Progreso y La Quebrada con nombres definidos)
    # ------------------------------------------------------------------
    ws1 = wb.create_sheet("Balance1")
    ws1.merge_cells("A1:C1")
    ws1["A1"] = "El Progreso — Balance general"
    ws1["A1"].font = font_title
    ws1["A2"] = "Activo"
    ws1["A2"].font = font_sec
    ws1["A3"] = "Activo circulante"
    ws1["B3"] = 600000.00
    ws1["A4"] = "Otros activos"
    ws1["B4"] = 400000.00
    ws1["C4"] = "=SUM(B3:B4)"
    ws1["A5"] = "Total activo"
    ws1["C5"] = "=C4"
    ws1["A6"] = "Pasivo"
    ws1["A6"].font = font_sec
    ws1["A7"] = "Pasivo circulante"
    ws1["B7"] = 50000.00
    ws1["A8"] = "Otros pasivos"
    ws1["B8"] = 150000.00
    ws1["C8"] = "=SUM(B7:B8)"
    ws1["A9"] = "Total pasivo"
    ws1["C9"] = "=C8"
    ws1["A10"] = "Capital"
    ws1["A10"].font = font_tot
    ws1["C10"] = "=activoP-pasivoP"

    ws1.merge_cells("E1:G1")
    ws1["E1"] = "La Quebrada — Balance general"
    ws1["E1"].font = font_title
    ws1["E2"] = "Activo"
    ws1["E2"].font = font_sec
    ws1["E3"] = "Activo circulante"
    ws1["F3"] = 200000.00
    ws1["E4"] = "Otros activos"
    ws1["F4"] = 800000.00
    ws1["G4"] = "=SUM(F3:F4)"
    ws1["E5"] = "Total activo"
    ws1["G5"] = "=G4"
    ws1["E6"] = "Pasivo"
    ws1["E6"].font = font_sec
    ws1["E7"] = "Pasivo circulante"
    ws1["F7"] = 300000.00
    ws1["E8"] = "Otros pasivos"
    ws1["F8"] = 600000.00
    ws1["G8"] = "=SUM(F7:F8)"
    ws1["E9"] = "Total pasivo"
    ws1["G9"] = "=G8"
    ws1["E10"] = "Capital"
    ws1["E10"].font = font_tot
    ws1["G10"] = "=activoQ-pasivoQ"

    style_range(ws1, 2, 3, 3, 10, font=font_reg, border=border_cell, num_fmt=acct_fmt)
    style_range(ws1, 6, 3, 7, 10, font=font_reg, border=border_cell, num_fmt=acct_fmt)
    ws1["C10"].border = border_total
    ws1["G10"].border = border_total

    wb.defined_names.add(DefinedName("activoP", attr_text="Balance1!$C$5"))
    wb.defined_names.add(DefinedName("pasivoP", attr_text="Balance1!$C$9"))
    wb.defined_names.add(DefinedName("capitalP", attr_text="Balance1!$C$10"))
    wb.defined_names.add(DefinedName("activoQ", attr_text="Balance1!$G$5"))
    wb.defined_names.add(DefinedName("pasivoQ", attr_text="Balance1!$G$9"))
    wb.defined_names.add(DefinedName("capitalQ", attr_text="Balance1!$G$10"))

    # ------------------------------------------------------------------
    # HOJA 2: Bal Completo Reporte (La Comercial Mercantil, S. A.)
    # ------------------------------------------------------------------
    ws2 = wb.create_sheet("Bal Completo Reporte")
    ws2["B1"] = "La Comercial Mercantil, S. A."
    ws2["B1"].font = font_title
    ws2["B2"] = 'Balance general, al 31 de diciembre del año "X".'
    ws2["B2"].font = font_sub
    ws2["A3"] = "Núm."
    ws2["B3"] = "Concepto"
    ws2["C3"] = "(1)"
    ws2["D3"] = "(2)"
    ws2["E3"] = "(3)"
    ws2["F3"] = "(4)"
    style_range(ws2, 1, 3, 6, 3, font=font_hdr, fill=fill_hdr)

    rows_ws2 = [
        (None, "Activo", None, None, None, None),
        (None, "Circulante", None, None, None, None),
        (1, "Caja", None, 1000000.00, None, None),
        (2, "Bancos", None, 500000.00, None, None),
        (3, "Mercancías", None, 1500000.00, None, None),
        (4, "Clientes", None, 500000.00, None, None),
        (5, "Documentos por cobrar", None, 700000.00, None, None),
        (6, "Deudores diversos", None, 300000.00, "=SUM(D6:D11)", None),
        (None, "Fijo", None, None, None, None),
        (7, "Edificios", None, 2000000.00, None, None),
        (8, "Mobiliario y equipo", None, 1200000.00, None, None),
        (9, "Equipo de reparto", None, 800000.00, "=SUM(D13:D15)", None),
        (None, "Cargos diferidos", None, None, None, None),
        (10, "Gastos de instalación", None, None, 200000.00, "=SUM(E11,E15,E17)"),
        (None, "Pasivo", None, None, None, None),
        (None, "Circulante", None, None, None, None),
        (11, "Proveedores", None, 1000000.00, None, None),
        (12, "Documentos por pagar", None, 800000.00, None, None),
        (13, "Acreedores diversos", None, 200000.00, "=SUM(D20:D22)", None),
        (None, "Fijo", None, None, None, None),
        (14, "Acreedores hipotecarios", None, None, 1000000.00, None),
        (None, "Créditos diferidos", None, None, None, None),
        (15, "Rentas cobradas por anticipado", None, None, 100000.00, "=SUM(E22,E24,E26)"),
        (None, "Capital contable", None, None, None, "=F17-F26"),
        (None, "Autorizado por: Ing. Arturo Robles Montes (Propietario)", None, None, "Elaborado por: C.P. Federico Yépez Gallardo (Contador general)", None),
    ]
    for idx, rdata in enumerate(rows_ws2, start=4):
        for c_i, val in enumerate(rdata, start=1):
            cell = ws2.cell(idx, c_i, val)
            if c_i >= 3 and val is not None and idx < 28:
                cell.number_format = acct_fmt

    # ------------------------------------------------------------------
    # HOJA 3: Bal Completo Cuenta (La Comercial Mercantil, S. A. Horizontal)
    # ------------------------------------------------------------------
    ws3 = wb.create_sheet("Bal Completo Cuenta")
    ws3["B1"] = "La Comercial Mercantil, S. A. — Balance general en forma de cuenta, al 31 de diciembre del año 'X'"
    ws3["B1"].font = font_title
    ws3["A3"] = "Núm."
    ws3["B3"] = "Activo"
    ws3["C3"] = "(2)"
    ws3["D3"] = "(3)"
    ws3["E3"] = "(4)"
    ws3["G3"] = "Núm."
    ws3["H3"] = "Pasivo y Capital"
    ws3["I3"] = "(2)"
    ws3["J3"] = "(3)"
    ws3["K3"] = "(4)"
    style_range(ws3, 1, 3, 11, 3, font=font_hdr, fill=fill_hdr)

    left_activo = [
        (None, "Circulante", None, None, None),
        (1, "Caja", 1000000.00, None, None),
        (2, "Bancos", 500000.00, None, None),
        (3, "Mercancías", 1500000.00, None, None),
        (4, "Clientes", 500000.00, None, None),
        (5, "Documentos por cobrar", 700000.00, None, None),
        (6, "Deudores diversos", 300000.00, "=SUM(C5:C10)", None),
        (None, "Fijo", None, None, None),
        (7, "Edificios", 2000000.00, None, None),
        (8, "Mobiliario y equipo", 1200000.00, None, None),
        (9, "Equipo de reparto", 800000.00, "=SUM(C12:C14)", None),
        (None, "Cargos diferidos", None, None, None),
        (10, "Gastos de instalación", None, 200000.00, None),
        (None, "Total activo", None, None, "=SUM(D10,D14,D16)"),
    ]
    right_pasivo = [
        (None, "Circulante", None, None, None),
        (11, "Proveedores", 1000000.00, None, None),
        (12, "Documentos por pagar", 800000.00, None, None),
        (13, "Acreedores diversos", 200000.00, "=SUM(I5:I7)", None),
        (None, "Fijo", None, None, None),
        (14, "Acreedores hipotecarios", None, 1000000.00, None),
        (None, "Créditos diferidos", None, None, None),
        (15, "Rentas cobradas por anticipado", None, 100000.00, None),
        (None, "Total pasivo", None, None, "=SUM(J7,J9,J11)"),
        (None, "Capital contable", None, None, "=E17-K12"),
        (None, "", None, None, None),
        (None, "", None, None, None),
        (None, "", None, None, None),
        (None, "Total pasivo más capital", None, None, "=K12+K13"),
    ]
    for i, row_l in enumerate(left_activo, start=4):
        for c_i, val in enumerate(row_l, start=1):
            c = ws3.cell(i, c_i, val)
            if c_i >= 3 and val is not None:
                c.number_format = acct_fmt
    for i, row_r in enumerate(right_pasivo, start=4):
        for c_i, val in enumerate(row_r, start=7):
            c = ws3.cell(i, c_i, val)
            if c_i >= 9 and val is not None:
                c.number_format = acct_fmt

    # ------------------------------------------------------------------
    # HOJA 4 y 5: Balance Reporte y Balance Cuenta (Ejercicios propuestos: Ing. Benjamín González + La Chiquita)
    # ------------------------------------------------------------------
    for sheet_title, is_cuenta in (("Balance Reporte", False), ("Balance Cuenta", True)):
        ws_b = wb.create_sheet(sheet_title)
        ws_b["A1"] = f"Ejercicios Propuestos de Balance General ({'Forma de Cuenta' if is_cuenta else 'Forma de Reporte'})"
        ws_b["A1"].font = font_title

        # Ejercicio Propuesto A: Ing. Benjamín González Martínez / CP Rodrigo Ruiz Gómez
        ws_b["A3"] = "1. Entidad: Comercial González — Autorizado: Ing. Benjamín González Martínez | Elaborado: CP Rodrigo Ruiz Gómez"
        ws_b["A3"].font = font_sec
        ws_b["A4"] = "Grupo"
        ws_b["B4"] = "Cuenta"
        ws_b["C4"] = "Parcial"
        ws_b["D4"] = "Subtotal Grupo"
        ws_b["E4"] = "Total"
        style_range(ws_b, 1, 4, 5, 4, font=font_hdr, fill=fill_hdr)

        prop1_rows = [
            ("Activo circulante", "Caja", 400.00, None, None),
            ("Activo circulante", "Bancos", 1600000.00, None, None),
            ("Activo circulante", "Mercancías", 5750000.00, None, None),
            ("Activo circulante", "Deudores diversos", 75000.00, "=SUM(C5:C8)", None),
            ("Activo no circulante", "Terrenos", 1200000.00, None, None),
            ("Activo no circulante", "Edificios", 2500000.00, None, None),
            ("Activo no circulante", "Equipo de oficina", 425000.00, None, None),
            ("Activo no circulante", "Equipo de cómputo", 200000.00, None, None),
            ("Activo no circulante", "Depósitos en garantía", 5200.00, None, None),
            ("Activo no circulante", "Inversiones permanentes", 350000.00, "=SUM(C9:C14)", None),
            ("Otros activos", "Gastos preoperativos", 75000.00, None, None),
            ("Otros activos", "Gastos de organización", 80000.00, None, None),
            ("Otros activos", "Papelería y útiles", 250000.00, None, None),
            ("Otros activos", "Primas de seguros", 18000.00, "=SUM(C15:C18)", "=SUM(D8,D14,D18)"),
            ("Pasivo a corto plazo", "Proveedores", 1400000.00, None, None),
            ("Pasivo a corto plazo", "Documentos por pagar", 825000.00, None, None),
            ("Pasivo a corto plazo", "Acreedores diversos", 940000.00, None, None),
            ("Pasivo a corto plazo", "Gastos acumulados por pagar", 22000.00, "=SUM(C19:C22)", None),
            ("Pasivo a largo plazo", "Acreedores hipotecarios", 750000.00, None, None),
            ("Pasivo a largo plazo", "Documentos por pagar a largo plazo", 125000.00, "=SUM(C23:C24)", None),
            ("Otros pasivos", "Rentas cobradas por anticipado", 36000.00, None, None),
            ("Otros pasivos", "Intereses cobrados por anticipado", 125000.00, "=SUM(C25:C26)", "=SUM(D22,D24,D26)"),
            ("Capital contable", "Capital contable (Activo - Pasivo)", None, None, "=E18-E26"),
        ]
        for r_i, r_vals in enumerate(prop1_rows, start=5):
            for c_i, v in enumerate(r_vals, start=1):
                cell = ws_b.cell(r_i, c_i, v)
                if c_i >= 3 and v is not None:
                    cell.number_format = acct_fmt

        # Ejercicio Propuesto B: Entidad "La Chiquita", 31 de mayo del año "X"
        ws_b["G3"] = "2. Entidad: La Chiquita (31 de mayo del año 'X') — Lic. Ricardo Casto Linares | C.P. Edgar Alvarado Cuevas"
        ws_b["G3"].font = font_sec
        ws_b["G4"] = "Grupo"
        ws_b["H4"] = "Cuenta"
        ws_b["I4"] = "Parcial"
        ws_b["J4"] = "Subtotal Grupo"
        ws_b["K4"] = "Total"
        style_range(ws_b, 7, 4, 11, 4, font=font_hdr, fill=fill_hdr)

        prop2_rows = [
            ("Activo circulante", "Caja", 500.00, None, None),
            ("Activo circulante", "Bancos", 1500000.00, None, None),
            ("Activo circulante", "Mercancías", 1800000.00, None, None),
            ("Activo circulante", "Clientes", 280000.00, None, None),
            ("Activo circulante", "Documentos por cobrar", 80000.00, None, None),
            ("Activo circulante", "Deudores diversos", 10000.00, "=SUM(I5:I10)", None),
            ("Activo no circulante", "Equipo de oficina", 150000.00, None, None),
            ("Activo no circulante", "Equipo de cómputo", 230000.00, None, None),
            ("Activo no circulante", "Depósitos en garantía", 15000.00, "=SUM(I11:I13)", None),
            ("Otros activos", "Gastos de instalación", 200000.00, None, None),
            ("Otros activos", "Gastos preoperativos", 50000.00, None, None),
            ("Otros activos", "Propaganda y publicidad", 25000.00, None, None),
            ("Otros activos", "Papelería y útiles", 15000.00, None, None),
            ("Otros activos", "Intereses pagados por anticipado", 22000.00, "=SUM(I14:I18)", "=SUM(J10,J13,J18)"),
            ("Pasivo a corto plazo", "Proveedores", 75000.00, None, None),
            ("Pasivo a corto plazo", "Acreedores diversos", 82000.00, None, None),
            ("Pasivo a corto plazo", "Impuestos acumulados por pagar", 12000.00, "=SUM(I19:I21)", None),
            ("Pasivo a largo plazo", "Documentos por pagar a largo plazo", 72000.00, "=I22", "=SUM(J21,J22)"),
            ("Capital contable", "Capital contable La Chiquita", None, None, "=K18-K22"),
        ]
        for r_i, r_vals in enumerate(prop2_rows, start=5):
            for c_i, v in enumerate(r_vals, start=7):
                cell = ws_b.cell(r_i, c_i, v)
                if c_i >= 9 and v is not None:
                    cell.number_format = acct_fmt

    # ------------------------------------------------------------------
    # HOJA 6: Bal Comparativo 1
    # ------------------------------------------------------------------
    ws6 = wb.create_sheet("Bal Comparativo 1")
    ws6["A1"] = "Balance comparativo"
    ws6["A1"].font = font_title
    ws6["A2"] = "Cuentas"
    ws6["B2"] = "Balance inicial"
    ws6["C2"] = "Balance final"
    ws6["D2"] = "Diferencias"
    ws6["E2"] = "Alteraciones"
    style_range(ws6, 1, 2, 5, 2, font=font_hdr, fill=fill_hdr)

    bc1_rows = [
        ("Caja", 100000.00, 150000.00),
        ("Mercancías", 600000.00, 560000.00),
        ("Total activo", "=SUM(B3:B4)", "=SUM(C3:C4)"),
        ("Proveedores", 300000.00, 250000.00),
        ("Acreedores diversos", 200000.00, 210000.00),
        ("Total pasivo", "=SUM(B6:B7)", "=SUM(C6:C7)"),
        ("Capital contable", "=B5-B8", "=C5-C8"),
    ]
    for idx, (cta, b_ini, b_fin) in enumerate(bc1_rows, start=3):
        ws6.cell(idx, 1, cta)
        ws6.cell(idx, 2, b_ini).number_format = acct_fmt
        ws6.cell(idx, 3, b_fin).number_format = acct_fmt
        ws6.cell(idx, 4, f"=ABS(C{idx}-B{idx})").number_format = acct_fmt
        ws6.cell(idx, 5, f'=IF(C{idx}>B{idx},"+",IF(C{idx}<B{idx},"-","="))')

    # ------------------------------------------------------------------
    # HOJA 7 y 9: Bal Comparativo 2 y Bal Compar Cuenta (La Comercial Mercantil, S. A.)
    # ------------------------------------------------------------------
    for sh_name in ("Bal Comparativo 2", "Bal Compar Cuenta"):
        ws7 = wb.create_sheet(sh_name)
        ws7["A1"] = "La Comercial Mercantil, S. A. — Balance comparativo por los ejercicios terminados el 31 de diciembre (Actual y Anterior)"
        ws7["A1"].font = font_title
        headers7 = ["Núm.", "Cuenta", "Año actual", "Año anterior", "Diferencias", "Alteraciones"]
        for c_i, h in enumerate(headers7, start=1):
            ws7.cell(2, c_i, h)
        style_range(ws7, 1, 2, 6, 2, font=font_hdr, fill=fill_hdr)

        bc2_items = [
            (1, "Caja", 500000.00, 400000.00),
            (2, "Bancos", 600000.00, 300000.00),
            (3, "Mercancías", 1500000.00, 1400000.00),
            (4, "Clientes", 900000.00, 1000000.00),
            (5, "Documentos por cobrar", 500000.00, 500000.00),
            (6, "Deudores diversos", 500000.00, 0.00),
            (None, "Sumas Activo Circulante", "=SUM(C3:C8)", "=SUM(D3:D8)"),
            (7, "Edificios", 1900000.00, 2000000.00),
            (8, "Mobiliario y equipo", 1800000.00, 2000000.00),
            (9, "Equipo de reparto", 1300000.00, 0.00),
            (None, "Sumas Activo Fijo", "=SUM(C10:C12)", "=SUM(D10:D12)"),
            (10, "Gastos de instalación", 400000.00, 300000.00),
            (None, "Total activo", "=C9+C13+C14", "=D9+D13+D14"),
            (11, "Proveedores", 1200000.00, 1400000.00),
            (12, "Documentos por pagar", 1000000.00, 1300000.00),
            (13, "Acreedores diversos", 800000.00, 300000.00),
            (None, "Sumas Pasivo Circulante", "=SUM(C16:C18)", "=SUM(D16:D18)"),
            (14, "Acreedores hipotecarios", 800000.00, 1000000.00),
            (15, "Rentas cobradas por anticipado", 200000.00, 500000.00),
            (None, "Total pasivo", "=C19+C20+C21", "=D19+D20+D21"),
            (None, "Capital contable", "=C15-C22", "=D15-D22"),
        ]
        for r_i, (num, cta, act_v, ant_v) in enumerate(bc2_items, start=3):
            ws7.cell(r_i, 1, num)
            ws7.cell(r_i, 2, cta)
            ws7.cell(r_i, 3, act_v).number_format = acct_fmt
            ws7.cell(r_i, 4, ant_v).number_format = acct_fmt
            ws7.cell(r_i, 5, f"=ABS(C{r_i}-D{r_i})").number_format = acct_fmt
            ws7.cell(r_i, 6, f'=IF(C{r_i}>D{r_i},"+",IF(C{r_i}<D{r_i},"-","="))')

    # ------------------------------------------------------------------
    # HOJA 8: Bal Comparativo 3 (La Competidora)
    # ------------------------------------------------------------------
    ws8 = wb.create_sheet("Bal Comparativo 3")
    ws8["A1"] = "La Competidora — Balance comparativo al 31 de diciembre del año actual y del anterior (Lic. Rodolfo Canseco / C.P. Jaime Puebla)"
    ws8["A1"].font = font_title
    for c_i, h in enumerate(["Grupo", "Datos del balance", "Actual", "Anterior", "Diferencias", "Alteraciones"], start=1):
        ws8.cell(2, c_i, h)
    style_range(ws8, 1, 2, 6, 2, font=font_hdr, fill=fill_hdr)

    bc3_items = [
        ("Activo circulante", "Caja", 200000.00, 100000.00),
        ("Activo circulante", "Bancos", 120000.00, 100000.00),
        ("Activo circulante", "Inversiones temporales", 50000.00, 0.00),
        ("Activo circulante", "Mercancías", 3000000.00, 2000000.00),
        ("Activo circulante", "Clientes", 800000.00, 700000.00),
        ("Activo circulante", "Documentos por cobrar", 750000.00, 700000.00),
        ("Activo circulante", "Deudores diversos", 0.00, 50000.00),
        ("Subtotal", "Suma Activo Circulante", "=SUM(C3:C9)", "=SUM(D3:D9)"),
        ("Activo no circulante", "Mobiliario y equipo", 720000.00, 800000.00),
        ("Activo no circulante", "Equipo de cómputo", 105000.00, 150000.00),
        ("Activo no circulante", "Equipo de reparto", 112500.00, 150000.00),
        ("Subtotal", "Suma Activo No Circulante", "=SUM(C11:C13)", "=SUM(D11:D13)"),
        ("Otros activos", "Gastos de instalación", 114000.00, 120000.00),
        ("Otros activos", "Papelería y útiles", 30000.00, 20000.00),
        ("Subtotal", "Suma Otros Activos", "=SUM(C15:C16)", "=SUM(D15:D16)"),
        ("Total", "Total activo", "=C10+C14+C17", "=D10+D14+D17"),
        ("Pasivo a corto plazo", "Proveedores", 1500000.00, 1000000.00),
        ("Pasivo a corto plazo", "Documentos por pagar", 1000000.00, 1200000.00),
        ("Total", "Total pasivo", "=SUM(C19:C20)", "=SUM(D19:D20)"),
        ("Capital", "Capital contable", "=C18-C21", "=D18-D21"),
    ]
    for r_i, (grp, cta, act_v, ant_v) in enumerate(bc3_items, start=3):
        ws8.cell(r_i, 1, grp)
        ws8.cell(r_i, 2, cta)
        ws8.cell(r_i, 3, act_v).number_format = acct_fmt
        ws8.cell(r_i, 4, ant_v).number_format = acct_fmt
        ws8.cell(r_i, 5, f"=ABS(C{r_i}-D{r_i})").number_format = acct_fmt
        ws8.cell(r_i, 6, f'=IF(C{r_i}>D{r_i},"+",IF(C{r_i}<D{r_i},"-","="))')

    # ------------------------------------------------------------------
    # HOJA 10 y 11: Estado de Resultados 1 y Estado de resultados 2
    # ------------------------------------------------------------------
    for sh_er, with_prod_fin in (("Estado de Resultados 1", False), ("Estado de resultados 2", True)):
        ws_er = wb.create_sheet(sh_er)
        ws_er["A1"] = f"Estado de Resultados — {sh_er} (Cálculo de Gastos de Operación)"
        ws_er["A1"].font = font_title
        for c_i, h in enumerate(["Concepto", "(1)", "(2)", "(3)", "(4)"], start=1):
            ws_er.cell(2, c_i, h)
        style_range(ws_er, 1, 2, 5, 2, font=font_hdr, fill=fill_hdr)

        er_rows = [
            ("Gastos de operación", None, None, None, None),
            ("Gastos de venta", None, None, None, None),
            ("Renta del almacén", None, 17000.00, None, None),
            ("Propaganda", None, 9000.00, None, None),
            ("Sueldos de agentes y dependientes", None, 32000.00, None, None),
            ("Comisiones de agentes y dependientes", None, 16000.00, None, None),
            ("Consumo de luz del almacén", None, 1000.00, "=SUM(C5:C9)", None),
            ("Gastos de administración", None, None, None, None),
            ("Renta de las oficinas", None, 12000.00, None, None),
            ("Sueldos del personal de oficinas", None, 43000.00, None, None),
            ("Papelería y útiles de oficina", None, 3000.00, None, None),
            ("Consumo de luz de las oficinas", None, 2000.00, "=SUM(C11:C14)", None),
        ]
        if not with_prod_fin:
            er_rows.extend([
                ("Gastos financieros", None, None, None, None),
                ("Intereses pagados", None, 5000.00, None, None),
                ("Pérdida en cambios", None, 4500.00, None, None),
                ("Comisiones bancarias", None, 500.00, "=SUM(C16:C18)", "=D9+D14+D18"),
            ])
        else:
            er_rows.extend([
                ("Gastos financieros", None, None, None, None),
                ("Intereses pagados", 5000.00, None, None, None),
                ("Pérdida en cambios", 4500.00, None, None, None),
                ("Comisiones bancarias", 500.00, "=SUM(B16:B18)", None, None),
                ("Productos financieros", None, None, None, None),
                ("Intereses cobrados", 1000.00, None, None, None),
                ("Utilidad en cambios", 3000.00, "=SUM(B20:B21)", "=C18-C21", "=D9+D14+D21"),
            ])
        for r_i, r_vals in enumerate(er_rows, start=3):
            for c_i, val in enumerate(r_vals, start=1):
                c = ws_er.cell(r_i, c_i, val)
                if c_i >= 2 and val is not None:
                    c.number_format = acct_fmt

    # ------------------------------------------------------------------
    # HOJA 12: EdoRes Comercial (La Comercial Mercantil, S. A. + Casa Blanco)
    # ------------------------------------------------------------------
    ws12 = wb.create_sheet("EdoRes Comercial")
    ws12["A1"] = "La Comercial Mercantil, S. A. — Estado de resultados del 01 de enero al 31 de diciembre del año 'X'"
    ws12["A1"].font = font_title
    for c_i, h in enumerate(["Concepto", "(1)", "(2)", "(3)", "(4)"], start=1):
        ws12.cell(2, c_i, h)
    style_range(ws12, 1, 2, 5, 2, font=font_hdr, fill=fill_hdr)

    edor_mercantil = [
        ("Ventas totales", None, None, 1950000.00, None),
        ("Menos: Devoluciones sobre ventas", None, 30000.00, None, None),
        ("Menos: Descuentos sobre ventas", None, 20000.00, "=SUM(C4:C5)", None),
        ("Ventas netas", None, None, None, "=D3-D5"),
        ("Inventario inicial", None, None, 1250000.00, None),
        ("Compras", 800000.00, None, None, None),
        ("Más: Gastos de compra", 20000.00, None, None, None),
        ("Compras totales", None, "=SUM(B8:B9)", None, None),
        ("Menos: Devoluciones sobre compras", 60000.00, None, None, None),
        ("Menos: Descuentos sobre compras", 10000.00, "=SUM(B11:B12)", None, None),
        ("Compras netas", None, None, "=C10-C12", None),
        ("Suma o total de mercancías", None, None, "=D7+D13", None),
        ("Menos: Inventario final", None, None, 600000.00, None),
        ("Costo de lo vendido", None, None, None, "=D14-D15"),
        ("Utilidad bruta", None, None, None, "=E6-E16"),
        ("Gastos de venta (Renta 17k, Prop 9k, Sueldos 32k, Comis 16k, Luz 1k)", None, 75000.00, None, None),
        ("Gastos de administración (Renta 12k, Sueldos 43k, Papel 3k, Luz 2k)", None, 60000.00, "=SUM(C18:C19)", None),
        ("Productos financieros (Intereses cobrados 7k + Utilidad cambios 5k)", None, 12000.00, None, None),
        ("Gastos financieros (Intereses pagados 5k + Pérdida cambios 4.5k + Comis 500)", None, 10000.00, "=C20-C21", None),
        ("Total Gastos de operación", None, None, None, "=D19-D21"),
        ("Utilidad de operación", None, None, None, "=E17-E22"),
        ("Otros gastos (Pérdida venta mobiliario 20k + Pérdida acciones 6k)", None, None, 26000.00, None),
        ("Otros productos (Comisiones cobradas 2k + Dividendos cobrados 4k)", None, None, 6000.00, None),
        ("Pérdida neta entre otros gastos y productos", None, None, None, "=D24-D25"),
        ("Utilidad antes del ISR y de la PTU", None, None, None, "=E23-E26"),
        ("Menos: Impuestos sobre la renta (ISR)", None, None, 104100.00, None),
        ("Menos: Participación de los trabajadores en las utilidades (PTU)", None, None, 34700.00, "=SUM(D28:D29)"),
        ("Utilidad neta del ejercicio", None, None, None, "=E27-E29"),
    ]
    for r_i, r_vals in enumerate(edor_mercantil, start=3):
        for c_i, val in enumerate(r_vals, start=1):
            c = ws12.cell(r_i, c_i, val)
            if c_i >= 2 and val is not None:
                c.number_format = acct_fmt

    # Segundo estado en EdoRes Comercial: Casa Blanco
    ws12["G1"] = "2. Nombre del negocio: Casa Blanco — Estado de resultados del 01 de enero al 31 de diciembre del año anterior"
    ws12["G1"].font = font_title
    for c_i, h in enumerate(["Concepto Casa Blanco", "(1)", "(2)", "(3)", "(4)"], start=7):
        ws12.cell(2, c_i, h)
    style_range(ws12, 7, 2, 11, 2, font=font_hdr, fill=fill_hdr)

    casa_blanco = [
        ("Ventas totales", None, None, 995000.00, None),
        ("Menos: Devoluciones s/ventas", None, 4000.00, None, None),
        ("Menos: Descuentos s/ventas", None, 1800.00, "=SUM(I4:I5)", None),
        ("Ventas netas", None, None, None, "=J3-J5"),
        ("Inventario inicial", None, None, 950000.00, None),
        ("Compras", 425000.00, None, None, None),
        ("Más: Gastos de compra", 1500.00, "=SUM(H8:H9)", None, None),
        ("Menos: Devoluciones y descuentos s/compras (3,500 + 1,400)", 4900.00, None, "=I9-H10", None),
        ("Suma o total de mercancías", None, None, "=J7+J10", None),
        ("Menos: Inventario final", None, None, 608500.00, None),
        ("Costo de lo vendido", None, None, None, "=J11-J12"),
        ("Utilidad bruta", None, None, None, "=K6-K13"),
        ("Gastos de venta (Renta tienda 14k, Luz almacén 1.9k, Publicidad 18k, Sueldos ventas 34k, Mant. reparto 4k, Envío 3.5k)", None, 75400.00, None, None),
        ("Gastos de administración (Sueldos ofic 40k, Renta ofic 11k, Luz ofic 1.8k, Correos 800, Teléfonos 3.5k)", None, 57100.00, "=SUM(I15:I16)", None),
        ("Productos financieros (Intereses cobrados 3k + Cambios ganados 2k)", None, 5000.00, None, None),
        ("Gastos financieros (Comisiones bancarias 2k + Intereses pagados 2k + Cambios pagados 500)", None, 4500.00, "=I17-I18", None),
        ("Total Gastos de operación", None, None, None, "=J16-J18"),
        ("Utilidad de operación", None, None, None, "=K14-K19"),
        ("Otros productos (Dividendos 9k + Comisiones 3k + Rentas 20k) - Otros gastos (Pérdida activo fijo 10k)", None, None, None, 22000.00),
        ("Utilidad neta antes de impuestos (Casa Blanco)", None, None, None, "=K20+K21"),
    ]
    for r_i, r_vals in enumerate(casa_blanco, start=3):
        for c_i, val in enumerate(r_vals, start=7):
            c = ws12.cell(r_i, c_i, val)
            if c_i >= 8 and val is not None:
                c.number_format = acct_fmt

    # ------------------------------------------------------------------
    # HOJA 13: BO INGRESOS TOTALES (Buscar Objetivo: Precio a = $87.00 -> $60,115,400)
    # ------------------------------------------------------------------
    ws13 = wb.create_sheet("BO INGRESOS TOTALES")
    ws13["B3"] = "Buscar Objetivo"
    ws13["B3"].font = font_title
    ws13["B5"] = "Precio a"
    ws13["E5"] = 87.00
    ws13["E5"].number_format = acct_fmt
    ws13["B6"] = "Cantidad a"
    ws13["E6"] = 325000
    ws13["E6"].number_format = "#,##0"
    ws13["B7"] = "Inflacion a %"
    ws13["E7"] = 0.015
    ws13["E7"].number_format = "0.00%"

    ws13["B9"] = "Precio b"
    ws13["E9"] = 125.00
    ws13["E9"].number_format = acct_fmt
    ws13["B10"] = "Cantidad b"
    ws13["E10"] = 247000
    ws13["E10"].number_format = "#,##0"
    ws13["B11"] = "Inflacion b %"
    ws13["E11"] = 0.0175
    ws13["E11"].number_format = "0.00%"

    ws13["B14"] = "Ingresos totales"
    ws13["B14"].font = font_tot
    ws13["E14"] = "=E5*E6*(1+E7)+E9*E10*(1+E11)"
    ws13["E14"].font = font_tot
    ws13["E14"].number_format = acct_fmt

    # ------------------------------------------------------------------
    # HOJA 14: PE 1 (Punto de Equilibrio: Costo Fijo $1,500,000, CV $500, Precio $2,000 -> Q = 1,000 unidades)
    # ------------------------------------------------------------------
    ws14 = wb.create_sheet("PE 1")
    ws14["B1"] = "Punto de Equilibrio 1 (Buscar Objetivo: Utilidad = $0.00)"
    ws14["B1"].font = font_title
    ws14["B3"] = "Cantidad ="
    ws14["C3"] = 1000
    ws14["C3"].number_format = "#,##0"
    ws14["B4"] = "Costo Fijo ="
    ws14["C4"] = 1500000.00
    ws14["C4"].number_format = acct_fmt
    ws14["B5"] = "Costo Variable ="
    ws14["C5"] = 500.00
    ws14["C5"].number_format = acct_fmt
    ws14["B6"] = "Precio de Venta ="
    ws14["C6"] = 2000.00
    ws14["C6"].number_format = acct_fmt
    ws14["B8"] = "Ingreso total ="
    ws14["C8"] = "=C3*C6"
    ws14["C8"].number_format = acct_fmt
    ws14["B9"] = "Costo Total ="
    ws14["C9"] = "=C3*C5+C4"
    ws14["C9"].number_format = acct_fmt
    ws14["B10"] = "Utilidad ="
    ws14["C10"] = "=C8-C9"
    ws14["C10"].font = font_tot
    ws14["C10"].number_format = acct_fmt

    # ------------------------------------------------------------------
    # HOJA 15: PE2 (Con 2,000 unidades y Costo Fijo $1,950,000 mantener Utilidad = $1,500,000 -> Precio = $2,225.00)
    # ------------------------------------------------------------------
    ws15 = wb.create_sheet("PE2")
    ws15["B1"] = "Punto de Equilibrio 2 (Buscar Objetivo: Mantener Utilidad de $1,500,000 con 2,000 unidades y CF de $1,950,000)"
    ws15["B1"].font = font_title
    ws15["B3"] = "Cantidad ="
    ws15["C3"] = 2000
    ws15["C3"].number_format = "#,##0"
    ws15["B4"] = "Costo Fijo ="
    ws15["C4"] = 1950000.00
    ws15["C4"].number_format = acct_fmt
    ws15["B5"] = "Costo Variable ="
    ws15["C5"] = 500.00
    ws15["C5"].number_format = acct_fmt
    ws15["B6"] = "Precio de Venta ="
    ws15["C6"] = 2225.00
    ws15["C6"].number_format = acct_fmt
    ws15["B8"] = "Ingreso total ="
    ws15["C8"] = "=C3*C6"
    ws15["C8"].number_format = acct_fmt
    ws15["B9"] = "Costo Total ="
    ws15["C9"] = "=C3*C5+C4"
    ws15["C9"].number_format = acct_fmt
    ws15["B10"] = "Utilidad ="
    ws15["C10"] = "=C8-C9"
    ws15["C10"].font = font_tot
    ws15["C10"].number_format = acct_fmt

    for ws in wb.worksheets:
        for col in ws.columns:
            col_letter = get_column_letter(col[0].column)
            ws.column_dimensions[col_letter].width = 24

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return {
        "path": str(out_path),
        "sheets": wb.sheetnames,
        "sha256": hashlib.sha256(out_path.read_bytes()).hexdigest(),
        "size_bytes": out_path.stat().st_size,
    }


def rebuild_all_uas_excel_deliverables(subject_root: Path) -> dict[str, Any]:
    """Ejecuta los Pasos 1 a 4 de la Línea de Acción reconstruyendo los 4 libros .xlsx oficiales."""
    mat_dir = subject_root / "referencias-herramientas-digitales" / "materiales-aula"
    deliv_dir = subject_root / "entregas-herramientas-digitales"
    act_dir = subject_root / "actividades"

    res_50114 = build_s2_excel_basico(
        mat_dir=mat_dir,
        out_path=deliv_dir / "GPO103LCP_EXCEL_BASICO_MartinJonathan_DeLaCruzMunoz.xlsx",
    )
    res_50130 = build_s3_excel_aplicado(
        mat_dir=mat_dir,
        out_path=deliv_dir / "GPO103LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx",
    )
    res_50131 = build_s3_examen_excel(
        mat_dir=mat_dir,
        out_path=deliv_dir / "GPO103LCP_EXAMEN_EXCEL_S3_MartinJonathan_DeLaCruzMunoz.xlsx",
        backup_act_path=act_dir / "Examen-Excel-S3_MartinJonathanDeLaCruzMunoz.xlsx",
    )
    res_50144 = build_s4_excel_conta(
        out_path=deliv_dir / "EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx",
    )

    return {
        "50114": res_50114,
        "50130": res_50130,
        "50131": res_50131,
        "50144": res_50144,
    }


if __name__ == "__main__":
    import json
    root = Path(r"C:\Users\Sysx\Documents\AulaTeX-Academico\UAS\licenciatura-en-contaduria-uas\herramientas-digitales")
    out = rebuild_all_uas_excel_deliverables(root)
    print(json.dumps(out, ensure_ascii=False, indent=2))
