"""Exporta el contenido del Word validado sin modificarlo ni su formato.

El archivo principal emplea la plantilla institucional; este exportador conserva
los párrafos, las tablas, las figuras y las referencias en su orden original.
"""

from pathlib import Path
import hashlib
import json
import re

from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

ROOT = Path(__file__).resolve().parent
COURSE = ROOT.parent
WORD = COURSE / "entregas" / "Tarea6_DeLaCruzMunoz.docx"
ASSETS = "ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/tarea6/fuentes/"


def escape(text):
    substitutions = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%", "$": r"\$",
                     "#": r"\#", "_": r"\_", "{": r"\{", "}": r"\}",
                     "~": r"\textasciitilde{}", "^": r"\textasciicircum{}",
                     "\n": " ", "\t": " ", "\u00a0": "~"}
    parts = re.split(r"(https?://[^\s)]+)", text)
    out = []
    for part in parts:
        if part.startswith(("https://", "http://")):
            url = part.rstrip(".,;")
            out.append(r"\url{" + url + "}" + part[len(url):])
        else:
            out.append("".join(substitutions.get(char, char) for char in part))
    return "".join(out)


def rich(paragraph):
    out = []
    for run in paragraph.runs:
        text = escape(run.text)
        if not text:
            continue
        if run.italic:
            text = r"\emph{" + text + "}"
        if run.bold:
            text = r"\textbf{" + text + "}"
        out.append(text)
    return "".join(out)


def cross_references(text):
    """Vincula menciones del cuerpo a etiquetas, sin alterar notas de fuentes."""
    for noun, label in [("Tabla", "tab"), ("Figura", "fig")]:
        text = re.sub(
            rf"\b{noun}s ([12]) y ([12])\b",
            lambda match: (noun + "s~\\ref{" + label + ":tarea6-" + match[1]
                           + "} y~\\ref{" + label + ":tarea6-" + match[2] + "}"),
            text,
        )
        text = re.sub(
            rf"\b{noun} ([12])\b",
            lambda match: noun + "~\\ref{" + label + ":tarea6-" + match[1] + "}",
            text,
        )
    return text


def render_table(table, number, title, note):
    assert len(table.columns) in (3, 4)
    cols = (r"@{}>{\RaggedRight\arraybackslash}p{0.14\linewidth}"
            r">{\RaggedRight\arraybackslash}p{0.22\linewidth}ZZ@{}"
            if len(table.columns) == 4 else r"@{}>{\hsize=1.35\hsize\linewidth=\hsize}Z"
            r">{\hsize=.825\hsize\linewidth=\hsize}Z>{\hsize=.825\hsize\linewidth=\hsize}Z@{}")
    out = [r"\begin{table}[H]", r"\begin{minipage}{\linewidth}",
           r"\caption{" + escape(title) + r"}\label{tab:tarea6-" + number + "}",
           r"\begin{singlespace}", r"\small\setlength{\tabcolsep}{4pt}",
           r"\setlength{\RaggedRightParindent}{0pt}\setlength{\parindent}{0pt}",
           r"\renewcommand{\arraystretch}{1.25}", r"\begin{tabularx}{\linewidth}{" + cols + "}", r"\toprule"]
    for i, row in enumerate(table.rows):
        values = [escape(cell.text) for cell in row.cells]
        if i == 0:
            values = [r"\textbf{" + text + "}" for text in values]
        out.append(" & ".join(values) + r" \\")
        if i == 0:
            out.append(r"\midrule")
    out.extend([r"\bottomrule", r"\end{tabularx}", r"\end{singlespace}",
                r"\apanota{" + rich(note) + "}", r"\end{minipage}", r"\end{table}"])
    return "\n".join(out)


def render_figure(number, title, note):
    filename = "figura1-metodo-cientifico-es.png" if number == "1" else "figura2-cuestionario.png"
    width = r"\linewidth" if number == "1" else r"0.82\linewidth"
    return "\n".join([
        r"\begin{figure}[H]", r"\begin{minipage}{\linewidth}",
        r"\caption{" + escape(title) + r"}\label{fig:tarea6-" + number + "}",
        r"\centering\includegraphics[width=" + width + "]{" + ASSETS + filename + "}",
        r"\apanota{" + rich(note) + "}", r"\end{minipage}", r"\end{figure}",
    ])


def main():
    checksum = hashlib.sha256(WORD.read_bytes()).hexdigest()
    doc = Document(WORD)
    blocks = []
    for element in doc.element.body:
        if element.tag == qn("w:p"):
            blocks.append(Paragraph(element, doc))
        elif element.tag == qn("w:tbl"):
            blocks.append(Table(element, doc))
    start = next(i for i, p in enumerate(blocks) if isinstance(p, Paragraph)
                 and p.text == "Presentación del ejercicio")
    output = ["% Contenido exportado del Word validado; regenerar con exportar_latex.py."]
    headings, tables, figures, references = 0, 0, 0, 0
    in_refs = False
    i = start
    while i < len(blocks):
        p = blocks[i]
        assert isinstance(p, Paragraph), "Tabla sin título detectada"
        text = p.text.strip()
        if not text:
            i += 1
            continue
        style = p.style.name
        match = re.fullmatch(r"(Tabla|Figura) (\d+)", text)
        if match:
            kind, number = match.groups()
            title, item, note = blocks[i + 1:i + 4]
            assert isinstance(title, Paragraph) and isinstance(note, Paragraph)
            assert note.text.startswith("Nota.")
            if kind == "Tabla":
                assert isinstance(item, Table)
                output.append(render_table(item, number, title.text, note))
                tables += 1
            else:
                assert isinstance(item, Paragraph) and item._p.xpath(".//w:drawing")
                output.append(render_figure(number, title.text, note))
                figures += 1
            i += 4
            continue
        if style == "APA referencia":
            if not in_refs:
                output.append(r"\begin{apareferences}")
                in_refs = True
            output.append(r"\item " + rich(p))
            references += 1
        else:
            if in_refs:
                output.append(r"\end{apareferences}")
                in_refs = False
            if style.startswith("Heading "):
                level = int(style.rsplit(" ", 1)[1])
                headings += 1
                if level == 1:
                    if text.startswith("Capítulo "):
                        title = text.split(". ", 1)[1]
                        output.append(r"\clearpage\section{" + escape(title) + "}")
                    else:
                        output.append(r"\section*{" + escape(text) + "}\n" +
                                      r"\phantomsection\addcontentsline{toc}{section}{" + escape(text) + "}")
                elif level in (2, 3):
                    title = re.sub(r"^\d+(?:\.\d+)+\s+", "", text)
                    command = "subsection" if level == 2 else "subsubsection"
                    output.append("\\" + command + "{" + escape(title) + "}")
                else:
                    match = re.match(r"^\d+(?:\.\d+)+\s+(.+?)\.\s+(.*)$", text)
                    assert match, text
                    title, body = match.groups()
                    output.append(r"\subsubsubsection{" + escape(title) + "}\n\n" + escape(body))
            else:
                output.append(cross_references(rich(p)))
        i += 1
    if in_refs:
        output.append(r"\end{apareferences}")
    assert (headings, tables, figures, references) == (74, 2, 2, 5)
    content = "\n\n".join(output) + "\n"
    (ROOT / "contenido-actividad-6.tex").write_text(content)
    assert hashlib.sha256(WORD.read_bytes()).hexdigest() == checksum
    report = {"word_sha256_sin_cambios": checksum, "encabezados": headings,
              "tablas": tables, "figuras": figures, "referencias": references,
              "archivo": "tarea6/contenido-actividad-6.tex"}
    (ROOT / "validacion" / "exportacion-latex.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()