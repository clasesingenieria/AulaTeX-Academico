"""Deterministic rendering of Mini-authored Seminario I objectives.

This module neither calls a language model nor opens a learning platform.  It
accepts reviewed JSON, continues a retained Tarea 9 DOCX, and creates a separate
three-act LaTeX companion using the institution's existing template.  Academic
prose must come from the JSON; the renderer supplies only layout and labels.

Required JSON keys::

    title, problem, general_question, specific_questions (four strings)
    content: general_objective, specific_objectives (four),
             verification_products (four), procedures (four), introduction,
             methodological_alignment, conclusion, ai_assistance_note
    references: [{key, apa, citation?, author?, year?, title?, url?, bibtex?}]
    metadata (optional): date_text, activity_title, author

Citation markers ``[@key]`` are resolved to APA text in Word and ``parencite``
in TeX.  ``citation`` is the exact parenthetical citation without parentheses;
it is required for a used key unless author and year are supplied.  Bibliography
entries need either BibTeX or author/year/title when TeX output is requested.
No original deliverable is overwritten.  Visual acceptance remains a separate
human/model review gate; structural QA never claims visual approval.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from typing import Any, Mapping
from zipfile import ZIP_DEFLATED, ZipFile

from docx import Document
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT, WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from lxml import etree


START = "1 Antecedentes"
OBJECTIVES = "3 Formulación de objetivos general y específicos"
GENERAL = "3.1 Objetivo general"
SPECIFIC = "3.2 Objetivos específicos"
FUTURE = "4 Justificación"
REFERENCES = "Referencias"
ANNEX = "Anexo 1 Matriz de consistencia"
COVEY = "Anexo 2 Círculo de Covey"
MARKER = re.compile(r"\[@([A-Za-z][A-Za-z0-9_:\-]*)\]")
KEY = re.compile(r"^[A-Za-z][A-Za-z0-9_:\-]*$")
DEFAULT_TEMPLATE = Path(
    "ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/"
    "reporte-seminario-i-plantilla-actividad.tex"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strings(value: Any, label: str, count: int | None = None) -> None:
    if not isinstance(value, list) or (count is not None and len(value) != count):
        raise ValueError(f"{label}: se requiere una lista de {count or 'varios'} textos")
    if any(not isinstance(v, str) or not v.strip() for v in value):
        raise ValueError(f"{label}: hay un texto vacío o no textual")


def validate_payload(data: Mapping[str, Any]) -> None:
    """Reject incomplete or ambiguous content before any output is written."""
    for key in ("title", "problem", "general_question"):
        if not isinstance(data.get(key), str) or not data[key].strip():
            raise ValueError(f"Falta texto obligatorio: {key}")
    _strings(data.get("specific_questions"), "specific_questions", 4)
    content = data.get("content")
    if not isinstance(content, dict):
        raise ValueError("Falta content")
    for key in ("general_objective", "introduction", "methodological_alignment", "conclusion", "ai_assistance_note"):
        if not isinstance(content.get(key), str) or not content[key].strip():
            raise ValueError(f"Falta content.{key}")
    for key in ("specific_objectives", "verification_products", "procedures"):
        _strings(content.get(key), f"content.{key}", 4)
    refs = data.get("references")
    if not isinstance(refs, list):
        raise ValueError("references debe ser una lista")
    keys: set[str] = set()
    for ref in refs:
        if not isinstance(ref, dict) or not KEY.fullmatch(str(ref.get("key", ""))):
            raise ValueError("Clave bibliográfica inválida")
        if ref["key"] in keys:
            raise ValueError("Clave bibliográfica duplicada: " + ref["key"])
        if not isinstance(ref.get("apa"), str) or not ref["apa"].strip():
            raise ValueError("Falta referencia APA: " + ref["key"])
        keys.add(ref["key"])
    used = set(MARKER.findall(json.dumps(data.get("content"), ensure_ascii=False)))
    if used - keys:
        raise ValueError("Citas sin referencia: " + ", ".join(sorted(used - keys)))
    refs_by_key = {r["key"]: r for r in refs}
    for key in used:
        ref = refs_by_key[key]
        if not ref.get("citation") and not (ref.get("author") and ref.get("year")):
            raise ValueError(f"La cita {key} requiere citation o author/year")


def word_text(text: str, data: Mapping[str, Any]) -> str:
    text = text.replace('\\n', '\n')
    refs = {r["key"]: r for r in data["references"]}

    def replace(match: re.Match[str]) -> str:
        ref = refs[match[1]]
        citation = ref.get("citation") or f'{ref["author"]}, {ref["year"]}'
        return "(" + citation.strip().strip("()") + ")"

    return MARKER.sub(replace, text)


def _paragraph(doc: Any, text: str) -> Any:
    matches = [p for p in doc.paragraphs if p.text == text]
    if len(matches) != 1:
        raise ValueError(f"Se esperaba un único anclaje exacto: {text!r}, encontrados {len(matches)}")
    return matches[0]


def _range_text(doc: Any, start: str, stop: str) -> list[str]:
    ps = [p.text for p in doc.paragraphs]
    return ps[ps.index(start):ps.index(stop)]


def _replace(p: Any, text: str) -> None:
    properties = deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
    p.clear()
    run = p.add_run(text)
    if properties is not None:
        run._r.insert(0, properties)


def _normal(p: Any, *, indent: bool = True, spacing: float = 2) -> Any:
    fmt = p.paragraph_format
    fmt.line_spacing = spacing
    fmt.space_before = Pt(0)
    fmt.space_after = Pt(0)
    fmt.first_line_indent = Inches(.5 if indent else 0)
    fmt.widow_control = True
    for run in p.runs:
        run.font.name = "Arial"
        run.font.size = Pt(11)
        run.font.color.rgb = RGBColor(0, 0, 0)
    return p


def _insert_after(doc: Any, anchor: Any, text: str, *, indent: bool = True) -> Any:
    p = _normal(doc.add_paragraph(text, style="Normal"), indent=indent)
    anchor._p.addnext(p._p)
    return p


def _table(doc: Any, headers: list[str], rows: list[list[str]], widths: list[float]) -> Any:
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for col, width in zip(t.columns, widths):
        col.width = Inches(width)
    for cell, value in zip(t.rows[0].cells, headers):
        cell.text = value
    for values in rows:
        for cell, value in zip(t.add_row().cells, values):
            cell.text = value
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + side)
        for key, value in (("val", "single"), ("sz", "4"), ("color", "D9D9D9")):
            el.set(qn("w:" + key), value)
        borders.append(el)
    t._tbl.tblPr.append(borders)
    for ri, row in enumerate(t.rows):
        row._tr.get_or_add_trPr().append(OxmlElement("w:cantSplit"))
        if ri == 0:
            row._tr.get_or_add_trPr().append(OxmlElement("w:tblHeader"))
        for ci, cell in enumerate(row.cells):
            cell.width = Inches(widths[ci])
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            margin = OxmlElement("w:tcMar")
            for side in ("top", "left", "bottom", "right"):
                el = OxmlElement("w:" + side)
                el.set(qn("w:w"), "100")
                el.set(qn("w:type"), "dxa")
                margin.append(el)
            cell._tc.get_or_add_tcPr().append(margin)
            if ri == 0:
                shade = OxmlElement("w:shd")
                shade.set(qn("w:fill"), "E7EDF2")
                cell._tc.get_or_add_tcPr().append(shade)
            for p in cell.paragraphs:
                _normal(p, indent=False, spacing=1.05)
                p.paragraph_format.keep_with_next = False
                p.paragraph_format.space_after = Pt(3)
                for run in p.runs:
                    run.font.size = Pt(10)
                    run.bold = ri == 0
    return t


def _heading(doc: Any, text: str, level: int = 1, page: bool = False) -> Any:
    p = doc.add_paragraph(text, style=f"Heading {level}")
    p.paragraph_format.page_break_before = page
    p.paragraph_format.keep_with_next = True
    return p


def _restore_package_and_footnote(source: Path, out: Path, note: str) -> None:
    """Preserve opaque recurring parts and create an actual OOXML footnote."""
    with ZipFile(source) as src, ZipFile(out) as current:
        preserved = {n: src.read(n) for n in src.namelist()
                     if n.startswith(("word/media/", "word/header", "word/footer"))}
        package = {n: current.read(n) for n in current.namelist()}
        package.update(preserved)
    wns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    path = "word/footnotes.xml"
    if path in package:
        root = etree.fromstring(package[path])
    else:
        root = etree.Element(qn("w:footnotes"), nsmap={"w": wns})
        for identifier, kind in (("-1", "separator"), ("0", "continuationSeparator")):
            foot = etree.SubElement(root, qn("w:footnote"), {qn("w:id"): identifier, qn("w:type"): kind})
            etree.SubElement(etree.SubElement(etree.SubElement(foot, qn("w:p")), qn("w:r")), qn("w:" + kind))
    identifier = str(max([int(el.get(qn("w:id"))) for el in root] + [0]) + 1)
    foot = etree.SubElement(root, qn("w:footnote"), {qn("w:id"): identifier})
    p = etree.SubElement(foot, qn("w:p"))
    pr = etree.SubElement(p, qn("w:pPr"))
    etree.SubElement(pr, qn("w:pStyle"), {qn("w:val"): "FootnoteText"})
    r = etree.SubElement(p, qn("w:r"))
    etree.SubElement(r, qn("w:footnoteRef"))
    r = etree.SubElement(p, qn("w:r"))
    rp = etree.SubElement(r, qn("w:rPr"))
    etree.SubElement(rp, qn("w:rFonts"), {qn("w:ascii"): "Arial", qn("w:hAnsi"): "Arial"})
    etree.SubElement(rp, qn("w:sz"), {qn("w:val"): "18"})
    etree.SubElement(r, qn("w:t"), {"{http://www.w3.org/XML/1998/namespace}space": "preserve"}).text = " " + note
    document = etree.fromstring(package["word/document.xml"])
    for el in document.findall(".//" + qn("w:footnoteReference")):
        if el.get(qn("w:id")) == "424242":
            el.set(qn("w:id"), identifier)
    rel_path = "word/_rels/document.xml.rels"
    rel = etree.fromstring(package[rel_path])
    rel_ns = "http://schemas.openxmlformats.org/package/2006/relationships"
    if not any(e.get("Type", "").endswith("/footnotes") for e in rel):
        ids = {e.get("Id") for e in rel}
        num = 1
        while f"rIdFootnote{num}" in ids:
            num += 1
        etree.SubElement(rel, "{" + rel_ns + "}Relationship", {
            "Id": f"rIdFootnote{num}",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footnotes",
            "Target": "footnotes.xml",
        })
    ct = etree.fromstring(package["[Content_Types].xml"])
    if not any(e.get("PartName") == "/word/footnotes.xml" for e in ct):
        etree.SubElement(ct, "{http://schemas.openxmlformats.org/package/2006/content-types}Override", {
            "PartName": "/word/footnotes.xml",
            "ContentType": "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml",
        })
    for name, element in ((path, root), ("word/document.xml", document), (rel_path, rel), ("[Content_Types].xml", ct)):
        package[name] = etree.tostring(element, xml_declaration=True, encoding="UTF-8", standalone=True)
    with ZipFile(out, "w", ZIP_DEFLATED) as output:
        for name, blob in package.items():
            output.writestr(name, blob)


def build_objectives_docx(source_docx: str | Path, data: Mapping[str, Any], output_docx: str | Path) -> dict[str, Any]:
    """Continue Tarea 9, preserving developed chapters and earlier references."""
    validate_payload(data)
    source, output = Path(source_docx).resolve(), Path(output_docx).resolve()
    if source == output:
        raise ValueError("El archivo fuente nunca puede ser el archivo de salida")
    source_hash = _sha(source)
    doc = Document(source)
    # Validate anchors before writing or removing anything.
    for label in (START, OBJECTIVES, GENERAL, SPECIFIC, FUTURE, REFERENCES, ANNEX):
        _paragraph(doc, label)
    if not any("TOC " in text for text in doc.element.xpath("//w:instrText/text()")):
        raise ValueError("La Tarea 9 debe conservar un índice Word real")
    titles = [p for p in doc.paragraphs if p.style.name == "Title"]
    if len(titles) != 1 or titles[0].text != data["title"]:
        raise ValueError("El título del JSON no coincide literalmente con el título de Tarea 9")
    prior12 = _range_text(doc, START, OBJECTIVES)
    if data["problem"] not in prior12 or data["general_question"] not in prior12:
        raise ValueError("Problema o pregunta general no coincide literalmente con Tarea 9")
    for i, question in enumerate(data["specific_questions"], 1):
        if question not in prior12 and f"{i}. {question}" not in prior12:
            raise ValueError(f"La pregunta específica {i} no coincide con Tarea 9")
    data = deepcopy(data)
    # APA disambiguation is typography, not a change to the retained study.
    old_teaching = next((p for p in doc.paragraphs if p.text.startswith('Instituto Tecnológico Superior de Cajeme. (s. f.). Introducción al uso')),None)
    new_teaching = next((r for r in data['references'] if r['key']=='itesca33'),None)
    if old_teaching is not None and new_teaching is not None:
        for run in old_teaching.runs:
            run.text = run.text.replace('(s. f.).','(s. f.-b).')
        new_teaching['apa'] = new_teaching['apa'].replace('(s. f.).','(s. f.-a).')
        new_teaching['citation'] = new_teaching['author']+', s. f.-a'
    meta, c = data.get("metadata", {}), data["content"]
    wt = lambda text: word_text(text, data)
    cover = [p for p in doc.paragraphs if "Seminario I\nTarea 9" in p.text]
    if len(cover) != 1:
        raise ValueError("Portada de Tarea 9 no identificada")
    _replace(cover[0], "Seminario I\n" + meta.get("activity_title", "Tarea 10 Formulación de objetivos"))
    dates = [p for p in doc.paragraphs if p.text.startswith("CIUDAD OBREGÓN, SONORA\n")]
    if len(dates) != 1:
        raise ValueError("Fecha de portada no identificada")
    _replace(dates[0], "CIUDAD OBREGÓN, SONORA\n" + meta.get("date_text", "4 DE OCTUBRE DE 2026"))
    # Replace only the editable chapter 3 contents, leaving every heading intact.
    h3, h31, h32, h4 = (_paragraph(doc, s) for s in (OBJECTIVES, GENERAL, SPECIFIC, FUTURE))
    for heading in (h31,h32):
        heading.paragraph_format.space_before = Pt(6)
    node = h3._p.getnext()
    while node is not h4._p:
        nxt = node.getnext()
        if node not in (h31._p, h32._p):
            node.getparent().remove(node)
        node = nxt
    intro = _insert_after(doc, h3, wt(c.get("chapter3_intro",c["introduction"])))
    reference = OxmlElement("w:footnoteReference")
    reference.set(qn("w:id"), "424242")
    run = intro.add_run()
    run.font.superscript = True
    run._r.append(reference)
    _insert_after(doc, h31, wt(c["general_objective"]))
    anchor = h32
    for i, objective in enumerate(c["specific_objectives"], 1):
        anchor = _insert_after(doc, anchor, f"{i}. {wt(objective)}", indent=False)
    anchor = _insert_after(doc, anchor, wt(c.get("chapter3_alignment",c["methodological_alignment"])))
    # Add references; the retained institutional and research bibliography is literal.
    old_refs = _range_text(doc, REFERENCES, ANNEX)[1:]
    annex = _paragraph(doc, ANNEX)
    for ref in sorted(data["references"], key=lambda r: r["apa"].casefold()):
        if ref["apa"] in old_refs:
            continue
        p = doc.add_paragraph(style="Normal")
        title = ref.get('title','')
        if title and title in ref['apa']:
            before,after = ref['apa'].split(title,1)
            p.add_run(before)
            p.add_run(title).italic = True
            p.add_run(after)
        else:
            p.add_run(ref['apa'])
        p = _normal(p, indent=False)
        p.paragraph_format.left_indent = Inches(.5)
        p.paragraph_format.first_line_indent = Inches(-.5)
        # Insert into the existing alphabetical list without rewriting old entries.
        candidates = [x for x in doc.paragraphs if x.text in old_refs and x.text.casefold() > ref["apa"].casefold()]
        (candidates[0]._p if candidates else annex._p).addprevious(p._p)
    # Keep the final three bibliography entries together to avoid a nearly empty
    # final reference page, without changing the institutional double spacing.
    reference_ps = [p for p in doc.paragraphs if p.text in old_refs]
    for p in reference_ps[-3:-1]:
        p.paragraph_format.keep_with_next = True
    node = annex._p
    while node is not None:
        nxt = node.getnext()
        if node.tag != qn("w:sectPr"):
            node.getparent().remove(node)
        node = nxt
    _heading(doc, ANNEX, page=True)
    _table(doc, ["Tema y problema general", "Pregunta general", "Objetivo general"], [[
        data["title"] + "\n\n" + data["problem"], data["general_question"], wt(c["general_objective"]),
    ]], [2.2, 2.15, 2.15])
    _heading(doc, "Correspondencia de preguntas y objetivos específicos", 2, page=True)
    rows = []
    for i in range(4):
        rows.append([
            f"{i + 1}. " + data["specific_questions"][i],
            f"Objetivo {i + 1}\n{wt(c['specific_objectives'][i])}\n\n"
            f"Procedimiento\n{wt(c['procedures'][i])}\n\n"
            f"Producto verificable\n{wt(c['verification_products'][i])}",
        ])
    _table(doc, ["Pregunta específica", "Objetivo, procedimiento y producto"], rows, [2.45, 4.05])
    _heading(doc, COVEY, page=True)
    _normal(doc.add_paragraph("Problema general y objetivo general en el cuadrante Importante y No urgente"), indent=False)
    _table(doc, ["Urgente", "No urgente"], [[
        "I Importante", "II Importante\n\nProblema general\n" + data["problem"]
        + "\n\nObjetivo general\n" + wt(c["general_objective"]),
    ], ["III No importante", "IV No importante"]], [2.15, 4.35])
    update = OxmlElement("w:updateFields")
    update.set(qn("w:val"), "true")
    if not doc.settings.element.xpath("./w:updateFields"):
        doc.settings.element.append(update)
    doc.core_properties.title = data["title"]
    if meta.get("author"):
        doc.core_properties.author = meta["author"]
    output.parent.mkdir(parents=True, exist_ok=True)
    doc.save(output)
    _restore_package_and_footnote(source, output, wt(c["ai_assistance_note"]))
    if _sha(source) != source_hash:
        raise RuntimeError("El original cambió durante la generación")
    result = validate_structure(source, output, data)
    if not result["passed"]:
        raise RuntimeError("Fallo de validación estructural: " + json.dumps(result, ensure_ascii=False))
    return {"docx": str(output), "source_sha256": source_hash, "sha256": _sha(output), "qa": result}


def validate_structure(source_docx: str | Path, generated_docx: str | Path, data: Mapping[str, Any], *, after_word_refresh: bool = False) -> dict[str, Any]:
    """Check source continuity, actual fields, annex coverage and package assets."""
    source, generated = Path(source_docx), Path(generated_docx)
    src, dst = Document(source), Document(generated)
    checks: dict[str, bool] = {
        "chapters_1_2_literal": _range_text(src, START, OBJECTIVES) == _range_text(dst, START, OBJECTIVES),
        "future_headings_literal": _range_text(src, FUTURE, REFERENCES) == _range_text(dst, FUTURE, REFERENCES),
        "real_toc_field": any("TOC " in t for t in dst.element.xpath("//w:instrText/text()")),
        "earlier_references_preserved": all(p in [v.replace('(s. f.-b). Introducción al uso','(s. f.). Introducción al uso') for v in _range_text(dst, REFERENCES, ANNEX)] for p in _range_text(src, REFERENCES, ANNEX)),
        "same_page_geometry": all(
            getattr(a, key) == getattr(b, key)
            for a, b in zip(src.sections, dst.sections)
            for key in ("page_width", "page_height", "top_margin", "bottom_margin", "left_margin", "right_margin")
        ) and len(src.sections) == len(dst.sections),
    }
    table_text = "\n".join(cell.text for table in dst.tables for row in table.rows for cell in row.cells)
    c = data["content"]
    required = [data["title"], data["problem"], data["general_question"], word_text(c["general_objective"], data)]
    for key in ("specific_questions",):
        required.extend(data[key])
    for key in ("specific_objectives", "verification_products", "procedures"):
        required.extend(word_text(v, data) for v in c[key])
    checks["complete_consistency_matrix"] = all(v in table_text for v in required)
    covey = dst.tables[-1].cell(1, 1).text
    checks["covey_important_not_urgent"] = all(v in covey for v in ("II Importante", data["problem"], word_text(c["general_objective"], data)))
    with ZipFile(source) as a, ZipFile(generated) as b:
        protected = [n for n in a.namelist() if n.startswith(("word/media/", "word/header", "word/footer"))]
        checks["protected_parts_byte_identical"] = all(n in b.namelist() and a.read(n) == b.read(n) for n in protected)
        if after_word_refresh:
            # Word rewrites XML namespaces and removes the unused old Covey image.
            # Verify the retained banner and header/footer fields semantically.
            checks.pop('protected_parts_byte_identical')
            checks['institutional_banner_byte_identical'] = a.read('word/media/image1.png') == b.read('word/media/image1.png')
            def chrome_signature(blob):
                el = etree.fromstring(blob)
                ns={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                return el.xpath('//w:t/text()',namespaces=ns),el.xpath('//w:instrText/text()',namespaces=ns)
            chrome=[n for n in protected if n.startswith(('word/header','word/footer')) and n.endswith('.xml')]
            checks['header_footer_text_and_fields_preserved'] = all(n in b.namelist() and chrome_signature(a.read(n))==chrome_signature(b.read(n)) for n in chrome)
        checks["native_ai_footnote"] = "word/footnotes.xml" in b.namelist() and bool(dst.element.xpath("//w:footnoteReference"))
        if checks["native_ai_footnote"]:
            note_xml = etree.fromstring(b.read("word/footnotes.xml"))
            checks["ai_note_complete"] = word_text(c["ai_assistance_note"], data) in "".join(note_xml.itertext())
    return {"passed": all(checks.values()), "checks": checks, "visual_review": "pending"}


def tex_escape(text: str) -> str:
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(ch, ch) for ch in text)


def tex_text(text: str) -> str:
    parts, pos = [], 0
    for match in MARKER.finditer(text):
        parts.extend((tex_escape(text[pos:match.start()]), r"\parencite{" + match[1] + "}"))
        pos = match.end()
    parts.append(tex_escape(text[pos:]))
    return "".join(parts).replace("\n\n", "\n\n\\par ")


def _bibliography(data: Mapping[str, Any]) -> str:
    entries = []
    for ref in data["references"]:
        raw = ref.get("bibtex")
        if raw:
            if not re.match(r"\s*@\w+\s*\{\s*" + re.escape(ref["key"]) + r"\s*,", raw):
                raise ValueError("La clave BibTeX no coincide: " + ref["key"])
            entries.append(raw)
            continue
        if not all(ref.get(key) for key in ("author", "year", "title")):
            raise ValueError("Para TEX faltan bibtex o author/year/title: " + ref["key"])
        fields = {"author": ref["author"], "year": ref["year"], "title": ref["title"]}
        if ref.get("url"):
            fields["howpublished"] = r"\url{" + ref["url"].replace("%", r"\%") + "}"
        body = ",\n".join("  " + k + " = {" + (v if k == "howpublished" else "{" + tex_escape(str(v)) + "}" if k in ('author','title') else tex_escape(str(v))) + "}" for k, v in fields.items())
        entries.append("@misc{" + ref["key"] + ",\n" + body + "\n}")
    return "\n\n".join(entries) + "\n"


def build_contract_tex(data: Mapping[str, Any], output_tex: str | Path, template_root: str | Path) -> dict[str, str]:
    """Write a separate three-act companion; do not replace the cumulative Word."""
    validate_payload(data)
    root, output = Path(template_root).resolve(), Path(output_tex).resolve()
    template = root / DEFAULT_TEMPLATE
    if not template.is_file():
        raise FileNotFoundError(template)
    if "UnADM" in template.read_text(encoding="utf-8"):
        raise ValueError("La plantilla institucional contiene identidad ajena a ITESCA")
    bibliography = _bibliography(data)
    c, meta = data["content"], data.get("metadata", {})
    undated = [ref for ref in data['references'] if ref.get('year')=='s. f.']
    def t(value):
        rendered=tex_text(value)
        for ref in undated:
            rendered=rendered.replace(r'\parencite{'+ref['key']+'}',r'\citepalias{'+ref['key']+'}')
        return rendered
    development = [r"\section{Objetivos de la preparación administrativa de vTaxi}", r"\subsection{Delimitación del estudio}",
                   r"\textbf{Tema.} " + t(data["title"]),
                   r"\textbf{Problema general.} " + t(data["problem"]),
                   r"\textbf{Pregunta general.} " + t(data["general_question"]),
                   r"\Needspace{8\baselineskip}\subsection{Objetivo general}", t(c["general_objective"]),
                   r"\subsection{Objetivos específicos}", r"\begin{enumerate}"]
    development.extend(r"\item " + t(v) for v in c["specific_objectives"])
    development += [r"\end{enumerate}", r"\subsection{Alineación metodológica}", t(c["methodological_alignment"]), r"\subsection{Matriz de consistencia}"]
    for i in range(4):
        development += [r"\Needspace{10\baselineskip}\subsubsection{Objetivo específico " + str(i + 1) + "}",
                        r"\begin{longtable}{p{0.19\linewidth}p{0.72\linewidth}}",
                        r"\textbf{Componente} & \textbf{Correspondencia} \\ \hline\endhead"]
        for label, value in (("Pregunta", data["specific_questions"][i]), ("Objetivo", c["specific_objectives"][i]), ("Procedimiento", c["procedures"][i]), ("Producto", c["verification_products"][i])):
            development.append(tex_escape(label) + " & " + t(value) + r" \\ \hline")
        development.append(r"\end{longtable}")
    development += [r"\Needspace{22\baselineskip}\subsection{Círculo de Covey}", r"\begin{longtable}{p{0.28\linewidth}p{0.63\linewidth}}",
                    r"\textbf{Urgente} & \textbf{No urgente} \\ \hline",
                    r"I Importante & \textbf{II Importante}\par Problema general: " + t(data["problem"]) + r"\par Objetivo general: " + t(c["general_objective"]) + r" \\ \hline",
                    r"III No importante & IV No importante \\ \hline", r"\end{longtable}"]
    body = "\n\n".join([r"\section{Introducción}", t(c["introduction"]), *development, r"\clearpage\section{Conclusiones}", t(c["conclusion"]) + r"\footnote{" + t(c["ai_assistance_note"]) + "}"])
    bib_path = output.with_suffix(".bib")
    # The retained template uses natbib. Expose the requested semantic command
    # without replacing its package configuration or introducing biblatex.
    source = "% Generated only from reviewed model JSON; cumulative Word is the principal deliverable.\n"
    source += r"\let\seminarioOriginalBibStyle\bibliographystyle" + "\n"
    source += r"\renewcommand{\bibliographystyle}[1]{\seminarioOriginalBibStyle{apalike}}" + "\n"
    source += r"\newcommand{\parencite}[1]{\citep{#1}}" + "\n"
    for ref in undated:
        source += r'\AtBeginDocument{\defcitealias{'+ref['key']+'}{'+tex_escape(ref['author']+', s. f.')+'}}\n'
    source += r"\def\seminariotitulo{Formulación de objetivos}" + "\n"
    source += r"\def\seminariosubtitulo{" + t(data["title"]) + "}\n"
    source += r"\def\seminariofecha{" + t(meta.get("date_text", "4 de octubre de 2026")) + "}\n"
    source += r"\AtBeginDocument{\def\documenttitlehf{Objetivos de vTaxi}\def\coursecode{GGS102\ }\def\indexstyle{}\def\documentsubject{Actividad 10 - Seminario I}\hypersetup{pdfsubject={Actividad 10 - Seminario I}}}" + "\n"
    source += r"\def\seminarioresumen{" + t(c["introduction"]) + "}\n"
    source += r"\long\def\seminariocontenido{" + "\n" + body + "\n}\n"
    source += r"\def\seminarioreferencias{\clearpage\bibliography{" + bib_path.with_suffix("").as_posix() + "}}\n"
    source += r"\input{" + template.as_posix() + "}\n"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding="utf-8")
    bib_path.write_text(bibliography, encoding="utf-8")
    return {"tex": str(output), "bib": str(bib_path), "compile_cwd": str(root), "template": str(template)}


def export_word_pdf(docx: str | Path, pdf: str | Path | None = None, *, timeout: int = 180) -> dict[str, Any]:
    """Refresh actual Word fields and export via a hidden, isolated COM instance."""
    source = Path(docx).resolve()
    output = Path(pdf).resolve() if pdf else source.with_suffix(".pdf")
    if source == output:
        raise ValueError("DOCX y PDF deben ser rutas distintas")
    # Paths are positional script arguments, never interpolated PowerShell code.
    script = r'''param([string]$DocxPath, [string]$PdfPath)
$ErrorActionPreference = 'Stop'
$word = $null
$document = $null
try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $document = $word.Documents.Open($DocxPath, $false, $false)
    foreach ($toc in $document.TablesOfContents) { $toc.Update() }
    $document.Fields.Update() | Out-Null
    $document.Repaginate()
    foreach ($toc in $document.TablesOfContents) { $toc.Update() }
    $document.Save()
    $document.ExportAsFixedFormat($PdfPath, 17)
    $pages = $document.ComputeStatistics(2)
    Write-Output $pages
} finally {
    if ($null -ne $document) { $document.Close(0) }
    if ($null -ne $word) { $word.Quit() }
}
'''
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="aulatex-word-") as temp:
        runner = Path(temp) / "export.ps1"
        runner.write_text(script, encoding="utf-8-sig")
        result = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", str(runner), str(source), str(output)], capture_output=True, text=True, timeout=timeout, check=True)
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Word no produjo un PDF válido")
    return {"pdf": str(output), "sha256": _sha(output), "word_pages": result.stdout.strip()}


def render_pdf_pngs(pdf: str | Path, output_dir: str | Path, poppler: str | Path, *, dpi: int = 120, timeout: int = 180) -> list[str]:
    """Render pages for the orchestrator's mandatory visual review."""
    source, folder, executable = Path(pdf).resolve(), Path(output_dir).resolve(), Path(poppler).resolve()
    if not executable.is_file():
        raise FileNotFoundError(executable)
    folder.mkdir(parents=True, exist_ok=True)
    prefix = folder / "page"
    if list(folder.glob("page-*.png")):
        raise ValueError("Use un directorio de QA nuevo para evitar imágenes obsoletas")
    subprocess.run([str(executable), "-r", str(dpi), "-png", str(source), str(prefix)], capture_output=True, text=True, check=True, timeout=timeout)
    images = sorted(folder.glob("page-*.png"), key=lambda p: int(p.stem.rsplit("-", 1)[1]))
    if not images:
        raise RuntimeError("Poppler no produjo páginas")
    return [str(p) for p in images]


def compile_contract_tex(tex: str | Path, repo_root: str | Path, *, latexmk: str = "latexmk", timeout: int = 240) -> dict[str, str]:
    source, root = Path(tex).resolve(), Path(repo_root).resolve()
    env = os.environ.copy()
    if os.name == 'nt':
        if latexmk == 'latexmk':
            executable = Path('C:/texlive/2026/bin/windows/latexmk.exe')
            if not executable.is_file():
                raise FileNotFoundError(f'El proyecto requiere TeX Live 2026: {executable}')
            latexmk = str(executable)
        executable = Path(latexmk)
        if executable.is_absolute():
            env['PATH'] = str(executable.parent) + os.pathsep + 'C:/Strawberry/perl/bin' + os.pathsep + env.get('PATH','')
    # Do not scan the repository recursively (venvs, browser caches and archives),
    # or inherit unrelated project latexmkrc output/aux directory settings.
    env['TEXINPUTS'] = os.pathsep.join([root.as_posix(),source.parent.as_posix(),(root/'base/Plantilla-Informe').as_posix()+'//',''])
    env['BIBINPUTS'] = str(source.parent).replace('\\','/') + os.pathsep + env.get('BIBINPUTS','')
    result = subprocess.run([latexmk, "-norc", "-f", "-pdf", "-bibtex", "-interaction=nonstopmode", "-file-line-error", "-outdir=" + str(source.parent), str(source)], cwd=root, env=env, capture_output=True, text=True, timeout=timeout, encoding='utf-8', errors='replace')
    log = source.with_suffix(".compile.txt")
    log.write_text(result.stdout + "\n" + result.stderr, encoding="utf-8")
    if result.returncode:
        raise RuntimeError(f"Falló latexmk ({result.returncode}); revisar {log}")
    pdf = source.with_suffix(".pdf")
    if not pdf.is_file():
        raise RuntimeError("latexmk terminó sin producir PDF")
    final_log = source.with_suffix('.log').read_text(encoding='utf-8',errors='replace')
    issues = re.findall(r'^.*(?:Overfull \\[hv]box|undefined citations|Citation .* undefined|^! ).*$',final_log,re.M)
    if issues:
        raise RuntimeError('El PDF requiere corrección de citas o desbordamientos; revisar '+str(source.with_suffix('.log')))
    return {"pdf": str(pdf), "log": str(log), "sha256": _sha(pdf),'no_undefined_citations_or_overfull_boxes':True}


def build_objectives_beamer(data: Mapping[str, Any], output_tex: str | Path) -> dict[str, str]:
    """Keep the companion presentation aligned using the same authored strings."""
    validate_payload(data)
    c = data['content']
    def t(value):
        text=word_text(value,data)
        return ''.join(r'\url{'+part.replace('%',r'\%')+'}' if re.match(r'https?://',part) else tex_escape(part)
                       for part in re.split(r'(https?://\S+)',text))
    frames = [r'\begin{frame}\titlepage\end{frame}']
    frames.append(r'\begin{frame}{Problema y pregunta general}\small ' + t(data['problem']) + r'\par\medskip ' + t(data['general_question']) + r'\end{frame}')
    frames.append(r'\begin{frame}{Objetivo general}\large '+t(c['general_objective'])+r'\end{frame}')
    for i in range(4):
        frames.append(r'\begin{frame}{Objetivo específico '+str(i+1)+r'}\small\textbf{Pregunta}\par '+t(data['specific_questions'][i])+r'\par\medskip\textbf{Objetivo}\par '+t(c['specific_objectives'][i])+r'\par\medskip\textbf{Procedimiento}\par '+t(c['procedures'][i])+r'\par\medskip\textbf{Evidencia}\par '+t(c['verification_products'][i])+r'\end{frame}')
    frames.append(r'\begin{frame}{Círculo de Covey}\small\begin{block}{Importante / No urgente}\textbf{Problema general}\par '+t(data['problem'])+r'\par\medskip\textbf{Objetivo general}\par '+t(c['general_objective'])+r'\end{block}\end{frame}')
    frames.append(r'\begin{frame}{Coherencia metodológica}\small '+t(c['methodological_alignment'].split('\n\n')[0])+r'\end{frame}')
    for i, paragraph in enumerate(c['conclusion'].split('\n\n'), 1):
        frames.append(r'\begin{frame}{Conclusiones '+str(i)+r'}\small '+t(paragraph)+r'\end{frame}')
    for ref in data['references']:
        frames.append(r'\begin{frame}{Fuente consultada}\small '+t(ref['apa'])+r'\end{frame}')
    frames.append(r'\begin{frame}{Asistencia de inteligencia artificial}\small '+t(c['ai_assistance_note'])+r'\end{frame}')
    text = r'''\documentclass[aspectratio=169,11pt]{beamer}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish]{babel}
\usepackage{xurl}
\usetheme{Madrid}
\definecolor{itescaRed}{HTML}{8F1117}
\usecolortheme[named=itescaRed]{structure}
\setbeamertemplate{navigation symbols}{}
\title[Objetivos de vTaxi]{Objetivos de investigación de vTaxi}
\subtitle{Seminario I}
\author[M. J. de la Cruz Muñoz]{Martín Jonathan de la Cruz Muñoz}
\institute[ITESCA]{Instituto Tecnológico Superior de Cajeme}
\date[04/10/2026]{4 de octubre de 2026}
\begin{document}
'''+ '\n'.join(frames)+ '\n'+r'\end{document}'+'\n'
    # Citation keys in the presentation resolve to the same actual APA references.
    for ref in data['references']:
        text=text.replace('[@'+ref['key']+']',t('('+str(ref['author'])+', '+str(ref['year'])+')'))
    output = Path(output_tex).resolve()
    output.write_text(text, encoding='utf-8')
    return {'tex':str(output)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-json", required=True, type=Path)
    parser.add_argument("--source-docx", required=True, type=Path)
    parser.add_argument("--output-docx", required=True, type=Path)
    parser.add_argument("--output-tex", type=Path)
    parser.add_argument("--repo-root", type=Path)
    parser.add_argument("--export-pdf", action="store_true")
    parser.add_argument("--compile-tex", action="store_true")
    parser.add_argument("--beamer", type=Path)
    parser.add_argument("--receipt", type=Path)
    args = parser.parse_args()
    data = json.loads(args.input_json.read_text(encoding="utf-8-sig"))
    result: dict[str, Any] = {"word": build_objectives_docx(args.source_docx, data, args.output_docx)}
    if args.output_tex:
        if not args.repo_root:
            parser.error("--repo-root es requerido con --output-tex")
        result["tex"] = build_contract_tex(data, args.output_tex, args.repo_root)
    if args.export_pdf:
        result["word_pdf"] = export_word_pdf(args.output_docx)
        result['word']['before_word_refresh_sha256'] = result['word']['sha256']
        result['word']['sha256'] = _sha(args.output_docx)
        result['word']['post_refresh_qa'] = validate_structure(args.source_docx,args.output_docx,data,after_word_refresh=True)
        if not result['word']['post_refresh_qa']['passed']:
            raise RuntimeError('Word refresh changed protected content')
    if args.compile_tex:
        if not args.output_tex:
            parser.error("--compile-tex requiere --output-tex")
        result["tex_pdf"] = compile_contract_tex(args.output_tex, args.repo_root)
    if args.beamer:
        result['beamer'] = build_objectives_beamer(data, args.beamer)
        if args.compile_tex:
            result['beamer_pdf'] = compile_contract_tex(args.beamer,args.repo_root)
    if args.receipt:
        args.receipt.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
