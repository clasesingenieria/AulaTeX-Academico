"""Reconstructs the 4 Herramientas Digitales Excel deliverables for UAS course 635.

Matches Dr. Dámaso Guadalupe Ruíz González's actual recorded classes
(I_H5f_gGbuc, 0FGH031UsFo, q9KgoQqUJpU, ZSLk1hRY48U, 7ZomiXX7eus):
1. 50114 -> GPO103LCP_EXCEL_BASICO_MartinJonathan_DeLaCruzMunoz.xlsx
   Tabs: MARTÍN | FACTURAS | Participantes | 02-Ventas | 02-Vendedores
2. 50130 -> GPO103LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx
   Tabs: 03-Proyectos | 03-Relativas | 03-Absolutas | 03-Mixtas | 03-Resumen |
         03-Hoteles [red] | 04-Maquillaje [red] | 05-Alumnos | 05-Estado Civil |
         05-Género 1 | 05-Goles [red] | 05-Género 2 [red]
3. 50131 -> GPO103LCP_EXAMEN_EXCEL_S3_MartinJonathan_DeLaCruzMunoz.xlsx
   Same 12 tabs as 50130 with ALL homework sheets & pending tasks solved.
4. 50144 -> EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx
   Tabs: BALANCE | REPORTE
"""
from __future__ import annotations

import argparse
from copy import copy
import datetime as dt
import json
from pathlib import Path
from typing import Any

import openpyxl
from openpyxl.cell.cell import MergedCell
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName


DEFAULT_BASE = Path(
    r"C:\Users\Sysx\Documents\AulaTeX-Academico\UAS\licenciatura-en-contaduria-uas\herramientas-digitales"
)
STUDENT_NAME = "Martín Jonathan De La Cruz Muñoz"
STUDENT_FIRST = "MARTÍN"
STUDENT_BIRTH = dt.date(1995, 5, 15)

_PESOS_FMT = '_-$* #,##0.00_-;-$* #,##0.00_-;_-$* "-"??_-;_-@_-'
_SIN_PESOS_FMT = '_- * #,##0.00_-;- * #,##0.00_-;_- * "-"??_-;_-@_-'
_EURO_FMT = '#,##0.00 "€"'


def set_cell_safe(ws: Any, coord_or_row: Any, col_or_val: Any = None, value: Any = None) -> Any:
    """Safely assign a cell value, redirecting MergedCell writes to the anchor cell."""
    if isinstance(coord_or_row, str):
        cell = ws[coord_or_row]
        val = col_or_val
    else:
        cell = ws.cell(row=int(coord_or_row), column=int(col_or_val))
        val = value
    if isinstance(cell, MergedCell):
        for rng in ws.merged_cells.ranges:
            if cell.coordinate in rng:
                cell = ws.cell(row=rng.min_row, column=rng.min_col)
                break
        else:
            return None
    cell.value = val
    return cell


def _copy_cell_style(src_cell: Any, dst_cell: Any) -> None:
    if src_cell.has_style:
        dst_cell.font = copy(src_cell.font)
        dst_cell.fill = copy(src_cell.fill)
        dst_cell.border = copy(src_cell.border)
        dst_cell.alignment = copy(src_cell.alignment)
        dst_cell.number_format = src_cell.number_format


def copy_sheet_contents(src_ws: Any, dst_ws: Any) -> None:
    """Deep-copy cell values, styles, dimensions, merges and frozen panes between workbooks."""
    for merged in list(src_ws.merged_cells.ranges):
        dst_ws.merge_cells(str(merged))

    for col_key, dim in src_ws.column_dimensions.items():
        if dim.width is not None:
            dst_ws.column_dimensions[col_key].width = dim.width
    for row_key, rdim in src_ws.row_dimensions.items():
        if rdim.height is not None:
            dst_ws.row_dimensions[row_key].height = rdim.height

    for row in src_ws.iter_rows():
        for src_cell in row:
            dst_cell = dst_ws.cell(row=src_cell.row, column=src_cell.column)
            if not isinstance(src_cell, MergedCell) and not isinstance(dst_cell, MergedCell):
                dst_cell.value = src_cell.value
            _copy_cell_style(src_cell, dst_cell)

    if src_ws.freeze_panes:
        dst_ws.freeze_panes = src_ws.freeze_panes


def _find_material(mat_dir: Path, fragment: str) -> Path:
    matches = sorted(p for p in mat_dir.rglob("*.xlsx") if fragment.lower() in p.name.lower())
    if not matches:
        raise FileNotFoundError(f"No material workbook matching {fragment!r} inside {mat_dir}")
    # Prefer direct file in mat_dir over duplicates if same suffix
    direct = [m for m in matches if m.parent == mat_dir]
    return direct[0] if direct else matches[0]


def _style_header_cell(cell: Any, bg: str = "1F4E78", fg: str = "FFFFFF", size: int = 11) -> None:
    cell.font = Font(name="Calibri", size=size, bold=True, color=fg)
    cell.fill = PatternFill("solid", fgColor=bg)
    cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _thin_border() -> Border:
    side = Side(style="thin", color="BFBFBF")
    return Border(left=side, right=side, top=side, bottom=side)


def _set_defined_name(wb: openpyxl.Workbook, name: str, attr_text: str) -> None:
    if name in wb.defined_names:
        del wb.defined_names[name]
    dn = DefinedName(name, attr_text=attr_text)
    wb.defined_names.add(dn)


# ---------------------------------------------------------------------------
# DELIVERABLE 1 (50114): EXCEL BASICO (S2)
# ---------------------------------------------------------------------------
def build_s2_excel_basico(mat_dir: Path, out_path: Path) -> dict[str, Any]:
    """Builds GPO103LCP_EXCEL_BASICO_MartinJonathan_DeLaCruzMunoz.xlsx (Módulo 50114)."""
    wb = openpyxl.Workbook()
    ws_cover = wb.active
    ws_cover.title = STUDENT_FIRST
    ws_cover.sheet_properties.tabColor = "2E75B6"

    # Cover + Dr. Damaso S2C1 exercise (CELDAS = 16384*1048576 + student block)
    ws_cover.merge_cells("B1:F1")
    h1 = set_cell_safe(ws_cover, "B1", "UNIVERSIDAD AUTÓNOMA DE SINALOA — FCA | GPO103-LCP EXCEL BÁSICO")
    _style_header_cell(h1, bg="1F4E78", size=12)
    ws_cover.row_dimensions[1].height = 26

    set_cell_safe(ws_cover, "B2", "CELDAS =").font = Font(bold=True, size=11)
    c2 = set_cell_safe(ws_cover, "C2", "=16384*1048576")
    c2.font = Font(bold=True, size=11, color="1F4E78")
    c2.number_format = "#,##0"

    set_cell_safe(ws_cover, "E2", "Estudiante:").font = Font(bold=True)
    set_cell_safe(ws_cover, "F2", STUDENT_NAME)
    set_cell_safe(ws_cover, "E3", "Grupo / Docente:").font = Font(bold=True)
    set_cell_safe(ws_cover, "F3", "GPO103-LCP — Dr. Dámaso G. Ruíz González")

    sample_vals = [1500, 1320, 1456, 1256, 1250, 1110]
    for idx in range(11):
        row = 5 + idx
        c_name = set_cell_safe(ws_cover, row, 2, STUDENT_NAME)
        c_name.alignment = Alignment(horizontal="left")
        if idx < len(sample_vals):
            c_amt = set_cell_safe(ws_cover, row, 3, sample_vals[idx])
            c_amt.number_format = "#,##0"
    ws_cover.column_dimensions["A"].width = 4
    ws_cover.column_dimensions["B"].width = 36
    ws_cover.column_dimensions["C"].width = 20
    ws_cover.column_dimensions["D"].width = 6
    ws_cover.column_dimensions["E"].width = 18
    ws_cover.column_dimensions["F"].width = 38

    # Tab 2: FACTURAS (adjusted to fit 1 landscape printed page per 0FGH031UsFo)
    wb_fact = openpyxl.load_workbook(_find_material(mat_dir, "04_Impresión.xlsx"))
    ws_fact_src = wb_fact["FACTURAS"]
    ws_fact = wb.create_sheet("FACTURAS")
    copy_sheet_contents(ws_fact_src, ws_fact)
    _style_header_cell(set_cell_safe(ws_fact, "G2", "Total Línea"), bg="1F4E78", size=10)
    last_fact_row = ws_fact.max_row
    last_item_row = 3
    for r in range(3, last_fact_row + 1):
        qty_v = ws_fact.cell(r, 4).value
        price_v = ws_fact.cell(r, 5).value
        if isinstance(qty_v, (int, float)) and isinstance(price_v, (int, float)):
            c_tot = set_cell_safe(ws_fact, r, 7, f"=D{r}*E{r}*(1-F{r})")
            c_tot.number_format = _PESOS_FMT if r == 3 else _SIN_PESOS_FMT
            last_item_row = r
        elif isinstance(qty_v, str) and "alto" in qty_v.lower() and ws_fact.cell(r, 5).value is None:
            c_max = set_cell_safe(ws_fact, r, 5, f"=MAX(E3:E{last_item_row})")
            c_max.number_format = _PESOS_FMT
        elif isinstance(qty_v, str) and "bajo" in qty_v.lower() and ws_fact.cell(r, 5).value is None:
            c_min = set_cell_safe(ws_fact, r, 5, f"=MIN(E3:E{last_item_row})")
            c_min.number_format = _PESOS_FMT
    c_grand_lbl = set_cell_safe(ws_fact, last_item_row + 1, 6, "Total:")
    c_grand_lbl.font = Font(bold=True)
    c_grand = set_cell_safe(ws_fact, last_item_row + 1, 7, f"=SUM(G3:G{last_item_row})")
    c_grand.font = Font(bold=True)
    c_grand.number_format = _PESOS_FMT
    ws_fact.page_setup.orientation = ws_fact.ORIENTATION_LANDSCAPE
    ws_fact.page_setup.paperSize = ws_fact.PAPERSIZE_LETTER
    ws_fact.sheet_properties.pageSetUpPr.fitToPage = True
    ws_fact.page_setup.fitToWidth = 1
    ws_fact.page_setup.fitToHeight = 1
    ws_fact.column_dimensions["B"].width = max(ws_fact.column_dimensions["B"].width or 0, 14)
    ws_fact.column_dimensions["F"].width = max(ws_fact.column_dimensions["F"].width or 0, 13)
    ws_fact.column_dimensions["G"].width = 16

    # Tab 3: Participantes (=RANDBETWEEN(8,40) + Conditional Formatting per 0FGH031UsFo)
    wb_part = openpyxl.load_workbook(_find_material(mat_dir, "03_Participantes.xlsx"))
    ws_part = wb.create_sheet("Participantes")
    copy_sheet_contents(wb_part["Participantes"], ws_part)
    ws_part.freeze_panes = "B3"
    max_col_ltr = get_column_letter(ws_part.max_column)
    cf_range = f"B3:{max_col_ltr}{ws_part.max_row}"
    ws_part.conditional_formatting.add(
        cf_range,
        CellIsRule(
            operator="greaterThanOrEqual",
            formula=["36"],
            fill=PatternFill(start_color="C6EFCE", end_color="C6EFCE", fill_type="solid"),
            font=Font(bold=True, color="006100"),
        ),
    )
    ws_part.conditional_formatting.add(
        cf_range,
        CellIsRule(
            operator="lessThan",
            formula=["15"],
            fill=PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid"),
            font=Font(color="9C0006"),
        ),
    )
    _set_defined_name(wb, "Datos", f"Participantes!$B$3:${max_col_ltr}${ws_part.max_row}")

    # Tab 4: 02-Ventas (=_xlfn.SEQUENCE(COUNTA(B:B)-1) shown in 0FGH031UsFo 01:08:00)
    wb_vend = openpyxl.load_workbook(_find_material(mat_dir, "04_Vendedores.xlsx"))
    ws_vend_src = wb_vend.active
    ws_vta = wb.create_sheet("02-Ventas")
    copy_sheet_contents(ws_vend_src, ws_vta)
    c_seq = set_cell_safe(ws_vta, "A3", "=_xlfn.SEQUENCE(COUNTA(B:B)-1)")
    c_seq.alignment = Alignment(horizontal="center")
    for r in range(3, ws_vta.max_row + 1):
        ws_vta.cell(r, 1).alignment = Alignment(horizontal="center")
        ws_vta.cell(r, 4).number_format = _PESOS_FMT

    # Tab 5: 02-Vendedores (Homework solved with Serie de Relleno + país + totales)
    ws_vend = wb.create_sheet("02-Vendedores")
    ws_vend.sheet_properties.tabColor = "70AD47"
    copy_sheet_contents(ws_vend_src, ws_vend)
    max_v_row = ws_vend.max_row
    for idx, r in enumerate(range(3, max_v_row + 1), start=1):
        c_id = set_cell_safe(ws_vend, r, 1, idx)
        c_id.alignment = Alignment(horizontal="center")
        if ws_vend.cell(r, 3).value is None:
            set_cell_safe(ws_vend, r, 3, "España")
        ws_vend.cell(r, 4).number_format = _PESOS_FMT if r == 3 else _SIN_PESOS_FMT
    tot_r = max_v_row + 2
    set_cell_safe(ws_vend, tot_r, 2, "Total Ventas Vendedores").font = Font(bold=True)
    c_vsum = set_cell_safe(ws_vend, tot_r, 4, f"=SUM(D3:D{max_v_row})")
    c_vsum.font = Font(bold=True)
    c_vsum.number_format = _PESOS_FMT
    set_cell_safe(ws_vend, tot_r + 1, 2, "Promedio de Ventas").font = Font(bold=True)
    c_vavg = set_cell_safe(ws_vend, tot_r + 1, 4, f"=AVERAGE(D3:D{max_v_row})")
    c_vavg.font = Font(bold=True)
    c_vavg.number_format = _PESOS_FMT

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return {"module_id": 50114, "path": str(out_path), "sheets": wb.sheetnames}


# ---------------------------------------------------------------------------
# DELIVERABLES 2 & 3 (50130 & 50131): EXCEL APLICADO & EXAMEN S3 (S3)
# ---------------------------------------------------------------------------
def _populate_maquillaje_sheet(wb: openpyxl.Workbook, ws: Any, solve_homework: bool) -> None:
    """Fills 04-Maquillaje per ZSLk1hRY48U (C16:C23 in class; C16:C26 + colors in Examen)."""
    ws.sheet_properties.tabColor = "70AD47" if solve_homework else "FF0000"
    _set_defined_name(wb, "Nombre", "'04-Maquillaje'!$H$5:$H$1904")
    _set_defined_name(wb, "Fecha", "'04-Maquillaje'!$I$5:$I$1904")
    _set_defined_name(wb, "Producto", "'04-Maquillaje'!$J$5:$J$1904")
    _set_defined_name(wb, "Unidades", "'04-Maquillaje'!$K$5:$K$1904")
    _set_defined_name(wb, "Euros", "'04-Maquillaje'!$L$5:$L$1904")

    # Vendor table B5:C13
    for r in range(5, 14):
        c_eur = set_cell_safe(ws, r, 2, f"=SUMIF(Nombre,A{r},Euros)")
        c_eur.number_format = _EURO_FMT
        c_uni = set_cell_safe(ws, r, 3, f"=SUMIF(Nombre,A{r},Unidades)")
        c_uni.number_format = "#,##0"

    # Product table B29:C33
    for r in range(29, 34):
        c_eur = set_cell_safe(ws, r, 2, f"=SUMIF(Producto,A{r},Euros)")
        c_eur.number_format = _EURO_FMT
        c_uni = set_cell_safe(ws, r, 3, f"=SUMIF(Producto,A{r},Unidades)")
        c_uni.number_format = "#,##0"

    resultados = [
        (16, '=SUMIF(Fecha,"<2005-12-10",Euros)', _EURO_FMT),
        (17, '=SUMIF(Fecha,">=2005-01-01",Euros)', _EURO_FMT),
        (18, '=SUMIF(Nombre,"M*",Unidades)', "#,##0"),
        (19, '=-SUMIF(Unidades,"<0",Unidades)', "#,##0"),
        (20, '=COUNTIF(Unidades,"<0")', "#,##0"),
        (21, '=SUMIF(Nombre,"????",Euros)', _EURO_FMT),
        (22, '=SUMIF(Nombre,"<>Susy",Unidades)', "#,##0"),
        (23, '=AVERAGEIFS(Unidades,Nombre,"Miguel",Producto,"lápiz labial",Unidades,">=50")', "0.00"),
        (24, '=SUMIFS(Euros,Producto,"lápiz labial",Nombre,"Juan",Euros,">=100")', _EURO_FMT),
        (25, '=SUMIFS(Euros,Producto,"lápiz labial",Nombre,"Juan",Euros,"<100")', _EURO_FMT),
        (26, '=SUMIFS(Unidades,Fecha,">=2004-01-15",Fecha,"<=2005-02-15")', "#,##0"),
    ]
    pink_fill = PatternFill("solid", fgColor="FCE4D6")
    for r, formula, nfmt in resultados:
        if not solve_homework and r >= 24:
            ws.cell(r, 3).fill = pink_fill
            set_cell_safe(ws, r, 4, "**")
        else:
            c = set_cell_safe(ws, r, 3, formula)
            c.number_format = nfmt
            c.fill = pink_fill
            ws.cell(r, 4, None)


def _build_s3_workbook(mat_dir: Path, out_path: Path, solve_homework: bool) -> list[str]:
    wb = openpyxl.Workbook()
    first = True

    def add_copy(title: str, src_ws: Any, tab_color: str | None = None) -> Any:
        nonlocal first
        if first:
            ws = wb.active
            ws.title = title
            first = False
        else:
            ws = wb.create_sheet(title)
        copy_sheet_contents(src_ws, ws)
        if tab_color:
            ws.sheet_properties.tabColor = tab_color
        return ws

    # 1. 03-Proyectos (green tab)
    wb_proy = openpyxl.load_workbook(_find_material(mat_dir, "01_Proyectos.xlsx"))
    ws_proy = add_copy("03-Proyectos", wb_proy.active, tab_color="92D050")
    set_cell_safe(ws_proy, "B3", 500)
    set_cell_safe(ws_proy, "B4", 600)
    set_cell_safe(ws_proy, "B5", 520)
    set_cell_safe(ws_proy, "B6", "=SUM(B3:B5)")
    set_cell_safe(ws_proy, "B11", "=SUM(B8:B10)")
    set_cell_safe(ws_proy, "B16", "=SUM(B13:B15)")
    set_cell_safe(ws_proy, "B18", 650)
    set_cell_safe(ws_proy, "B19", 720)
    set_cell_safe(ws_proy, "B20", 800)
    set_cell_safe(ws_proy, "B21", "=SUM(B18:B20)")
    set_cell_safe(ws_proy, "A22", "Total Anual").font = Font(bold=True)
    set_cell_safe(ws_proy, "B22", "=B6+B11+B16+B21").font = Font(bold=True)
    for r in range(3, 23):
        ws_proy.cell(r, 2).number_format = _PESOS_FMT

    # 2-4. 03-Relativas, 03-Absolutas, 03-Mixtas
    wb_ref = openpyxl.load_workbook(_find_material(mat_dir, "02_Referencias.xlsx"))
    ws_rel = add_copy("03-Relativas", wb_ref["Relativas"])
    for r in range(3, 11):
        c = set_cell_safe(ws_rel, r, 3, f"=A{r}*B{r}")
        c.number_format = _PESOS_FMT if r == 3 else _SIN_PESOS_FMT
    set_cell_safe(ws_rel, "B11", "Total").font = Font(bold=True)
    c_rtot = set_cell_safe(ws_rel, "C11", "=SUM(C3:C10)")
    c_rtot.font = Font(bold=True)
    c_rtot.number_format = _PESOS_FMT

    ws_abs = add_copy("03-Absolutas", wb_ref["Absolutas"])
    for r in range(3, 11):
        cb = set_cell_safe(ws_abs, r, 2, f"=A{r}*$E$3")
        cb.number_format = _PESOS_FMT if r == 3 else _SIN_PESOS_FMT
        cc = set_cell_safe(ws_abs, r, 3, f"=A{r}+B{r}")
        cc.number_format = _PESOS_FMT if r == 3 else _SIN_PESOS_FMT

    ws_mix = add_copy("03-Mixtas", wb_ref["Mixtas"])
    for r in range(3, 13):
        for col in range(2, 12):
            col_ltr = get_column_letter(col)
            set_cell_safe(ws_mix, r, col, f"=$A{r}*{col_ltr}$2")

    # 5. 03-Resumen (ResumenGanancias_Compartido + K6:N10 HOY() / SIFECHA shown in q9KgoQqUJpU)
    wb_res = openpyxl.load_workbook(_find_material(mat_dir, "ResumenGanancias_Compartido.xlsx"))
    ws_res = add_copy("03-Resumen", wb_res.active)
    set_cell_safe(ws_res, "A11", "Total").font = Font(bold=True)
    for col, col_ltr in [(1, "A"), (2, "B"), (3, "C")]:
        c = set_cell_safe(ws_res, 11, col, f"=SUM({col_ltr}3:{col_ltr}10)")
        c.font = Font(bold=True)
        c.number_format = _PESOS_FMT
    set_cell_safe(ws_res, "K6", "Nombre")
    set_cell_safe(ws_res, "L6", "Fecha")
    set_cell_safe(ws_res, "M6", "Días")
    set_cell_safe(ws_res, "N6", "Edad")
    for col in range(11, 15):
        _style_header_cell(ws_res.cell(6, col), bg="4472C4", size=10)
    set_cell_safe(ws_res, "K7", STUDENT_NAME)
    c_bday = set_cell_safe(ws_res, "L7", STUDENT_BIRTH)
    c_bday.number_format = "dd/mm/yyyy"
    c_days = set_cell_safe(ws_res, "M7", "=TODAY()-L7")
    c_days.number_format = "#,##0"
    set_cell_safe(ws_res, "N7", '=DATEDIF(L7,TODAY(),"Y")')
    c_tod = set_cell_safe(ws_res, "L9", "=TODAY()")
    c_tod.number_format = "dd/mm/yyyy"
    c_long = set_cell_safe(ws_res, "K11", "=L7")
    c_long.number_format = '[$-es-MX]dddd, d "de" mmmm "de" yyyy'
    ws_res.column_dimensions["K"].width = 34
    ws_res.column_dimensions["L"].width = 14
    ws_res.column_dimensions["M"].width = 10
    ws_res.column_dimensions["N"].width = 8

    # 6. 03-Hoteles (Red tab in Aplicado, solved in Examen)
    wb_hot = openpyxl.load_workbook(_find_material(mat_dir, "Hoteles.xlsx"))
    ws_hot = add_copy(
        "03-Hoteles",
        wb_hot["Info"],
        tab_color=None if solve_homework else "FF0000",
    )
    if solve_homework:
        for col in range(2, 6):
            cl = get_column_letter(col)
            c = set_cell_safe(ws_hot, 10, col, f"=SUM({cl}3:{cl}9)")
            c.font = Font(bold=True)
            c.number_format = _EURO_FMT
        set_cell_safe(ws_hot, "H3", "=SUM(B3:C9)").number_format = _EURO_FMT
        set_cell_safe(ws_hot, "H4", "=SUM(D3:E9)").number_format = _EURO_FMT
        for idx, r in enumerate(range(7, 14), start=3):
            set_cell_safe(ws_hot, r, 8, f"=AVERAGE(B{idx}:E{idx})").number_format = _EURO_FMT
        set_cell_safe(ws_hot, "H16", "=MAX(B3:E3)").number_format = _EURO_FMT
        set_cell_safe(ws_hot, "H17", "=MIN(B3:E3)").number_format = _EURO_FMT
        for col_ltr in ("B", "C", "D", "E"):
            ws_hot.column_dimensions[col_ltr].width = max(ws_hot.column_dimensions[col_ltr].width or 0, 16)

    # 7. 04-Maquillaje
    wb_maq = openpyxl.load_workbook(_find_material(mat_dir, "VentaMaquillaje.xlsx"))
    ws_maq = add_copy("04-Maquillaje", wb_maq["INFO"])
    _populate_maquillaje_sheet(wb, ws_maq, solve_homework=solve_homework)

    # 8. 05-Alumnos & 9. 05-Estado Civil (from 01_FunciónLogica.xlsx)
    wb_fl = openpyxl.load_workbook(_find_material(mat_dir, "01_FunciónLogica.xlsx"))
    ws_alu = add_copy("05-Alumnos", wb_fl["Alumnos"])
    for r in range(3, 11):
        set_cell_safe(ws_alu, r, 3, f'=IF(B{r}>=11,"Aprobado","Desaprobado")')

    ws_ec = add_copy("05-Estado Civil", wb_fl["Estado Civil"])
    for r in range(3, 11):
        c = set_cell_safe(ws_ec, r, 3, f'=IF(B{r}="C","CASADO","SOLTERO")')
        c.fill = PatternFill("solid", fgColor="FCE4D6")

    # 10. 05-Género 1, 11. 05-Goles [red], 12. 05-Género 2 [red] (from 02_SIAnidado.xlsx)
    wb_si = openpyxl.load_workbook(_find_material(mat_dir, "02_SIAnidado.xlsx"))
    ws_g1 = add_copy("05-Género 1", wb_si["Género 1"])
    set_cell_safe(ws_g1, "D2", "SI.CONJUNTO").font = Font(bold=True, color="FFFFFF")
    ws_g1["D2"].fill = PatternFill("solid", fgColor="375623")
    for r in range(3, 11):
        set_cell_safe(ws_g1, r, 3, f'=IF(B{r}="M","Masculino",IF(B{r}="F","Femenino","No Procede"))')
        set_cell_safe(ws_g1, r, 4, f'=_xlfn.IFS(B{r}="M","Masculino",B{r}="F","Femenino",TRUE,"No Procede")')

    ws_gol = add_copy(
        "05-Goles",
        wb_si["goles"],
        tab_color=None if solve_homework else "FF0000",
    )
    if solve_homework:
        for r in range(3, 7):
            set_cell_safe(ws_gol, r, 5, f'=IF(B{r}>D{r},"Ganó "&A{r},IF(D{r}>B{r},"Ganó "&C{r},"Empate"))')

    ws_g2 = add_copy(
        "05-Género 2",
        wb_si["Género 2"],
        tab_color=None if solve_homework else "FF0000",
    )
    if solve_homework:
        set_cell_safe(ws_g2, "D2", "si.conjunto").font = Font(bold=True, color="FFFFFF")
        ws_g2["D2"].fill = PatternFill("solid", fgColor="833C0C")
        ws_g2.column_dimensions["C"].width = max(ws_g2.column_dimensions["C"].width or 0, 19)
        ws_g2.column_dimensions["D"].width = max(ws_g2.column_dimensions["D"].width or 0, 19)
        for r in range(3, 11):
            set_cell_safe(
                ws_g2,
                r,
                3,
                f'=IF(B{r}="M","Masculino",IF(B{r}="F","Femenino",IF(B{r}="","Casilla en blanco","No Procede")))',
            )
            set_cell_safe(
                ws_g2,
                r,
                4,
                f'=_xlfn.IFS(B{r}="M","Masculino",B{r}="F","Femenino",B{r}="","Casilla en blanco",TRUE,"No Procede")',
            )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return wb.sheetnames


def build_s3_excel_aplicado(mat_dir: Path, out_path: Path) -> dict[str, Any]:
    """Builds GPO103LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx (Módulo 50130)."""
    sheets = _build_s3_workbook(mat_dir, out_path, solve_homework=False)
    dup_101 = out_path.parent / "GPO101LCP_EXCEL_APLICADO_MartinJonathan_DeLaCruzMunoz.xlsx"
    if dup_101.exists():
        dup_101.unlink()
    return {"module_id": 50130, "path": str(out_path), "sheets": sheets}


def build_s3_examen_excel(
    mat_dir: Path, out_path: Path, backup_act_path: Path | None = None
) -> dict[str, Any]:
    """Builds GPO103LCP_EXAMEN_EXCEL_S3_MartinJonathan_DeLaCruzMunoz.xlsx (Módulo 50131)."""
    sheets = _build_s3_workbook(mat_dir, out_path, solve_homework=True)
    return {"module_id": 50131, "path": str(out_path), "sheets": sheets}


# ---------------------------------------------------------------------------
# DELIVERABLE 4 (50144): CONTA APLICADO — BALANCE & REPORTE (S4)
# ---------------------------------------------------------------------------
def _build_accounting_report_sheet(
    wb: openpyxl.Workbook,
    sheet_name: str,
    entity_name: str,
    report_title: str,
    authorized_by: str,
    elaborated_by: str,
    activo_sections: list[tuple[str, list[tuple[int, str, float, int]]]],
    pasivo_sections: list[tuple[str, list[tuple[int, str, float, int]]]],
    activo_name: str,
    pasivo_name: str,
) -> None:
    """Renders Dr. Damaso's exact 8-column green accounting ledger (`BALANCE` / `REPORTE`)."""
    ws = wb.active if sheet_name == "BALANCE" else wb.create_sheet(sheet_name)
    ws.title = sheet_name
    ws.views.sheetView[0].showGridLines = True

    widths = {"A": 3, "B": 4, "C": 5, "D": 36, "E": 15, "F": 16, "G": 16, "H": 17, "I": 3}
    for col_ltr, w in widths.items():
        ws.column_dimensions[col_ltr].width = w

    ws.merge_cells("B1:I1")
    c_ent = set_cell_safe(ws, "B1", entity_name)
    c_ent.font = Font(name="Aptos Display", size=14, bold=True)
    c_ent.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[1].height = 24

    ws.merge_cells("B2:I2")
    c_tit = set_cell_safe(ws, "B2", report_title)
    c_tit.font = Font(name="Aptos Display", size=11)
    c_tit.alignment = Alignment(horizontal="center", vertical="center")
    ws.row_dimensions[2].height = 20

    # Row 3: Major section header + column numbers 1..4 on B3:I3 look like col labels above table
    ws.row_dimensions[3].height = 18
    for idx, col in enumerate(range(5, 9), start=1):
        cell = set_cell_safe(ws, 3, col, idx)
        cell.font = Font(size=10, bold=True)
        cell.alignment = Alignment(horizontal="center")

    green_band = PatternFill("solid", fgColor="E2EFDA")
    white_band = PatternFill("solid", fgColor="FFFFFF")
    grid_side = Side(style="thin", color="A9D08E")
    cut_side = Side(style="thin", color="000000")
    dbl_side = Side(style="double", color="000000")
    table_border = Border(left=grid_side, right=grid_side, top=grid_side, bottom=grid_side)

    def _band_fill(row_num: int) -> PatternFill:
        return green_band if row_num % 2 == 0 else white_band

    def _style_ledger_row(row_num: int) -> None:
        fill = _band_fill(row_num)
        for col in range(2, 9):
            c = ws.cell(row_num, col)
            c.fill = fill
            c.border = table_border
            c.font = Font(name="Aptos Display", size=11)

    r = 4
    # ACTIVO
    _style_ledger_row(r)
    c_act_hdr = set_cell_safe(ws, r, 4, "Activo")
    c_act_hdr.font = Font(name="Aptos Display", size=11, bold=True)
    c_act_hdr.alignment = Alignment(horizontal="center")
    r += 1

    activo_subtotal_cells: list[str] = []
    for sub_idx, (sub_title, items) in enumerate(activo_sections):
        _style_ledger_row(r)
        c_sub = set_cell_safe(ws, r, 4, sub_title)
        c_sub.font = Font(name="Aptos Display", size=11, italic=True)
        c_sub.alignment = Alignment(horizontal="center")
        r += 1

        start_r = r
        is_single_item = len(items) == 1
        val_col = 7 if is_single_item else 6  # col F (6) for multi-item list -> subtotal in col G (7)
        for item_i, (acct_num, acct_name, amount, _) in enumerate(items):
            _style_ledger_row(r)
            c_num = set_cell_safe(ws, r, 3, acct_num)
            c_num.alignment = Alignment(horizontal="center")
            set_cell_safe(ws, r, 4, acct_name)
            c_val = set_cell_safe(ws, r, val_col, amount)
            # Pesos on first line of block (sub_idx == 0 and item_i == 0 OR reset after subtotal)
            needs_pesos = (item_i == 0 and (sub_idx == 0 or val_col == 6))
            c_val.number_format = _PESOS_FMT if needs_pesos else _SIN_PESOS_FMT
            if not is_single_item and item_i == len(items) - 1:
                # Cut line before subtotal -> write subtotal in col G (7) on same row per Dr. Damaso!
                c_val.border = Border(left=grid_side, right=grid_side, top=grid_side, bottom=cut_side)
                c_st = set_cell_safe(ws, r, 7, f"=SUM(F{start_r}:F{r})")
                c_st.number_format = _PESOS_FMT if len(activo_subtotal_cells) == 0 else _SIN_PESOS_FMT
                activo_subtotal_cells.append(f"G{r}")
            elif is_single_item:
                activo_subtotal_cells.append(f"G{r}")
            r += 1

    # Total Activo in col H (8) on last activo row
    last_act_row = r - 1
    ws.cell(last_act_row, 7).border = Border(left=grid_side, right=grid_side, top=grid_side, bottom=cut_side)
    c_tot_act = set_cell_safe(ws, last_act_row, 8, "=" + "+".join(activo_subtotal_cells))
    c_tot_act.number_format = _PESOS_FMT
    _set_defined_name(wb, activo_name, f"'{sheet_name}'!$H${last_act_row}")

    # PASIVO
    _style_ledger_row(r)
    c_pas_hdr = set_cell_safe(ws, r, 4, "Pasivo")
    c_pas_hdr.font = Font(name="Aptos Display", size=11, bold=True)
    c_pas_hdr.alignment = Alignment(horizontal="center")
    r += 1

    pasivo_subtotal_cells: list[str] = []
    for sub_idx, (sub_title, items) in enumerate(pasivo_sections):
        _style_ledger_row(r)
        c_sub = set_cell_safe(ws, r, 4, sub_title)
        c_sub.font = Font(name="Aptos Display", size=11, italic=True)
        c_sub.alignment = Alignment(horizontal="center")
        r += 1

        start_r = r
        is_single_item = len(items) == 1
        val_col = 7 if is_single_item else 6
        for item_i, (acct_num, acct_name, amount, _) in enumerate(items):
            _style_ledger_row(r)
            c_num = set_cell_safe(ws, r, 3, acct_num)
            c_num.alignment = Alignment(horizontal="center")
            set_cell_safe(ws, r, 4, acct_name)
            c_val = set_cell_safe(ws, r, val_col, amount)
            needs_pesos = (item_i == 0 and val_col == 6)
            c_val.number_format = _PESOS_FMT if needs_pesos else _SIN_PESOS_FMT
            if not is_single_item and item_i == len(items) - 1:
                c_val.border = Border(left=grid_side, right=grid_side, top=grid_side, bottom=cut_side)
                c_st = set_cell_safe(ws, r, 7, f"=SUM(F{start_r}:F{r})")
                c_st.number_format = _PESOS_FMT if len(pasivo_subtotal_cells) == 0 else _SIN_PESOS_FMT
                pasivo_subtotal_cells.append(f"G{r}")
            elif is_single_item:
                pasivo_subtotal_cells.append(f"G{r}")
            r += 1

    last_pas_row = r - 1
    ws.cell(last_pas_row, 7).border = Border(left=grid_side, right=grid_side, top=grid_side, bottom=cut_side)
    c_tot_pas = set_cell_safe(ws, last_pas_row, 8, "=" + "+".join(pasivo_subtotal_cells))
    c_tot_pas.number_format = _SIN_PESOS_FMT
    _set_defined_name(wb, pasivo_name, f"'{sheet_name}'!$H${last_pas_row}")
    ws.cell(last_pas_row, 8).border = Border(left=grid_side, right=grid_side, top=grid_side, bottom=cut_side)

    # Capital contable row = ACTIVO - PASIVO
    _style_ledger_row(r)
    c_cap_lbl = set_cell_safe(ws, r, 4, "Capital contable")
    c_cap_lbl.font = Font(name="Aptos Display", size=11, bold=True)
    c_cap_lbl.alignment = Alignment(horizontal="center")
    c_cap = set_cell_safe(ws, r, 8, f"={activo_name}-{pasivo_name}")
    c_cap.number_format = _PESOS_FMT
    c_cap.border = Border(left=grid_side, right=grid_side, top=grid_side, bottom=dbl_side)
    r += 1

    # Trailing ledger filler + Autorizado por / Elaborado por signature block
    sig_top = r + 3
    for fill_r in range(r, sig_top + 6):
        _style_ledger_row(fill_r)

    ws.merge_cells(start_row=sig_top, start_column=3, end_row=sig_top, end_column=4)
    set_cell_safe(ws, sig_top, 3, "Autorizado por").alignment = Alignment(horizontal="center")
    ws.merge_cells(start_row=sig_top, start_column=6, end_row=sig_top, end_column=8)
    set_cell_safe(ws, sig_top, 6, "Elaborado por").alignment = Alignment(horizontal="center")

    sig_line = sig_top + 3
    for col in (3, 4, 6, 7, 8):
        ws.cell(sig_line, col).border = Border(left=grid_side, right=grid_side, top=grid_side, bottom=cut_side)

    ws.row_dimensions[sig_line + 1].height = 28
    ws.merge_cells(start_row=sig_line + 1, start_column=3, end_row=sig_line + 1, end_column=4)
    c_auth = set_cell_safe(ws, sig_line + 1, 3, authorized_by)
    c_auth.font = Font(name="Aptos Display", size=10, bold=True)
    c_auth.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.merge_cells(start_row=sig_line + 1, start_column=6, end_row=sig_line + 1, end_column=8)
    c_elab = set_cell_safe(ws, sig_line + 1, 6, elaborated_by)
    c_elab.font = Font(name="Aptos Display", size=10, bold=True)
    c_elab.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.page_setup.orientation = ws.ORIENTATION_PORTRAIT
    ws.page_setup.paperSize = ws.PAPERSIZE_LETTER
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 1


def build_s4_excel_conta(out_path: Path) -> dict[str, Any]:
    """Builds EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx (Módulo 50144, 7ZomiXX7eus).

    Contains the exact 2 sheets demonstrated by Dr. Dámaso on 10/nov/2026:
    - BALANCE: La Comercial Mercantil S.A. de C.V. (en-clase)
    - REPORTE: Primer Ejercicio Propuesto del PDF SUAD (tarea)
    """
    wb = openpyxl.Workbook()

    _build_accounting_report_sheet(
        wb=wb,
        sheet_name="BALANCE",
        entity_name="La Comercial Mercantil S.A. de C.V.",
        report_title="Balance General al 31 de diciembre del 2026",
        authorized_by=f"Propietario — {STUDENT_NAME}",
        elaborated_by=f"Contador General — {STUDENT_NAME}",
        activo_sections=[
            ("Circulante", [
                (1, "Caja", 1_000_000.0, 6),
                (2, "Bancos", 500_000.0, 6),
                (3, "Mercancías", 1_500_000.0, 6),
                (4, "Clientes", 500_000.0, 6),
                (5, "Documentos x cobrar", 700_000.0, 6),
                (6, "Deudores diversos", 300_000.0, 6),
            ]),
            ("Fijo", [
                (7, "Edificio", 2_000_000.0, 6),
                (8, "Mobiliario y equipo", 1_200_000.0, 6),
                (9, "Equipo de reparto", 800_000.0, 6),
            ]),
            ("Diferido", [
                (10, "Gastos de instalación", 200_000.0, 7),
            ]),
        ],
        pasivo_sections=[
            ("Circulante", [
                (11, "Proveedores", 1_000_000.0, 6),
                (12, "Documentos por pagar", 800_000.0, 6),
                (13, "Acreedores diversos", 200_000.0, 6),
            ]),
            ("Fijo", [
                (14, "Acreedores hipotecarios", 1_000_000.0, 7),
            ]),
            ("Diferido", [
                (15, "Rentas cobradas por anticipado", 100_000.0, 7),
            ]),
        ],
        activo_name="ACTIVO",
        pasivo_name="PASIVO",
    )

    _build_accounting_report_sheet(
        wb=wb,
        sheet_name="REPORTE",
        entity_name="Empresa Industrial / Comercial — Ejercicio Propuesto 1",
        report_title="Balance General en forma de Reporte al 31 de diciembre del 2026",
        authorized_by="Ing. Benjamín González Martínez (Propietario)",
        elaborated_by=f"CP {STUDENT_NAME} (Contador General)",
        activo_sections=[
            ("Circulante", [
                (1, "Caja", 400.0, 6),
                (2, "Bancos", 1_600_000.0, 6),
                (3, "Mercancías", 5_750_000.0, 6),
                (4, "Deudores diversos", 75_000.0, 6),
            ]),
            ("Fijo", [
                (5, "Terrenos", 1_200_000.0, 6),
                (6, "Edificios", 2_500_000.0, 6),
                (7, "Equipo de oficina", 425_000.0, 6),
                (8, "Equipo de cómputo", 200_000.0, 6),
                (9, "Depósitos en garantía", 5_200.0, 6),
                (10, "Inversiones permanentes", 350_000.0, 6),
            ]),
            ("Diferido", [
                (11, "Gastos preoperativos", 75_000.0, 6),
                (12, "Gastos de organización", 80_000.0, 6),
                (13, "Papelería y útiles", 250_000.0, 6),
                (14, "Primas de seguros", 18_000.0, 6),
            ]),
        ],
        pasivo_sections=[
            ("Circulante", [
                (15, "Proveedores", 1_400_000.0, 6),
                (16, "Documentos por pagar", 825_000.0, 6),
                (17, "Acreedores diversos", 940_000.0, 6),
                (18, "Gastos acumulados por pagar", 22_000.0, 6),
            ]),
            ("Fijo", [
                (19, "Acreedores hipotecarios", 750_000.0, 6),
                (20, "Documentos por pagar a largo plazo", 125_000.0, 6),
            ]),
            ("Diferido", [
                (21, "Rentas cobradas por anticipado", 36_000.0, 6),
                (22, "Intereses cobrados por anticipado", 125_000.0, 6),
            ]),
        ],
        activo_name="ACTIVO_REPORTE",
        pasivo_name="PASIVO_REPORTE",
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out_path)
    return {"module_id": 50144, "path": str(out_path), "sheets": wb.sheetnames}


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconstruct Herramientas Digitales Excel deliverables.")
    parser.add_argument("--base", type=Path, default=DEFAULT_BASE)
    args = parser.parse_args()

    mat_dir = args.base / "referencias-herramientas-digitales" / "materiales-aula"
    deliv_dir = args.base / "entregas-herramientas-digitales"

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
    )
    res_50144 = build_s4_excel_conta(
        out_path=deliv_dir / "EXCEL_CONTA_MartinJonathan_DeLaCruzMunoz.xlsx",
    )

    print(json.dumps({
        "50114": res_50114,
        "50130": res_50130,
        "50131": res_50131,
        "50144": res_50144,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
