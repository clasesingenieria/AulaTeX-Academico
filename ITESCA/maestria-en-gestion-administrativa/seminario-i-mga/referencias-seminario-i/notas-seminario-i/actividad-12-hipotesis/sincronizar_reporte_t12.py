import hashlib
import json
import re
import shutil
from pathlib import Path

from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph


HERE = Path(__file__).resolve().parent
SUBJECT = HERE.parents[2]
SOURCE = SUBJECT / 'Entregas/Tarea12_DeLaCruzMunoz.docx'
TARGET = SUBJECT / 'reporte-seminario-i-Actividad-12.tex'


def escape(text):
    replacements = {'\\': r'\textbackslash{}', '&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#', '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}', '^': r'\textasciicircum{}'}
    return ''.join(replacements.get(character, character) for character in text)


def render_text(text):
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', text)
    parts = re.split(r'(https?://\S+)', text)
    return ''.join(r'\url{' + part + '}' if part.startswith(('https://', 'http://')) else escape(part) for part in parts)


def render_paragraph(paragraph):
    if paragraph.style.name.startswith('Heading'):
        level = int(paragraph.style.name.split()[-1])
        command = {1: 'section', 2: 'subsection', 3: 'subsubsection'}[level]
        label = re.sub(r'^\d+(?:\.\d+)*\s+', '', paragraph.text)
        if paragraph.text.startswith('Anexo ') or paragraph.text == 'Referencias':
            return r'\clearpage\section*{' + escape(label) + r'}\markboth{' + escape(label) + '}{' + escape(label) + r'}\addcontentsline{toc}{section}{' + escape(label) + '}'
        if not re.match(r'^\d+(?:\.\d+)*\s+', paragraph.text):
            return '\\' + command + '*{' + escape(label) + '}'
        return '\\' + command + '{' + escape(label) + '}'
    return render_text(paragraph.text) + '\n\n'


def render_table(table):
    count = len(table.columns)
    widths = [0.29, 0.29, 0.34] if count == 3 else [0.31, 0.63]
    columns = ''.join('p{' + str(width) + r'\linewidth}' for width in widths)
    output = [r'\begingroup\small\setstretch{1.15}', r'\begin{longtable}{@{}' + columns + '@{}}', r'\toprule']
    for index, row in enumerate(table.rows):
        cells = []
        column = 0
        while column < count:
            cell = row.cells[column]
            span = 1
            while column + span < count and row.cells[column + span]._tc is cell._tc:
                span += 1
            content = r'\par '.join(render_text(p.text) for p in cell.paragraphs if p.text.strip())
            if index == 0:
                content = r'\textbf{' + content + '}'
            if span > 1:
                width = sum(widths[column:column + span])
                content = r'\multicolumn{' + str(span) + '}{p{' + str(round(width, 2)) + r'\linewidth}}{' + content + '}'
            cells.append(content)
            column += span
        line = ' & '.join(cells) + r'\\'
        output.append(line)
        if index == 0:
            output.extend([r'\midrule\endfirsthead', r'\toprule', line, r'\midrule\endhead'])
        elif index < len(table.rows) - 1:
            output.append(r'\midrule')
    output.extend([r'\bottomrule\end{longtable}', r'\endgroup'])
    return '\n'.join(output)


def main():
    source_hash = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    document = Document(SOURCE)
    active = False
    paragraphs = []
    tables = []
    rendered = []
    for element in document.element.body:
        if element.tag.endswith('}p'):
            paragraph = Paragraph(element, document)
            if paragraph.style.name == 'Heading 1' and paragraph.text == '1 Antecedentes':
                active = True
            if active and paragraph.text.strip():
                paragraphs.append(paragraph.text)
                rendered.append(render_paragraph(paragraph))
        elif element.tag.endswith('}tbl') and active:
            table = Table(element, document)
            tables.append([[cell.text for cell in row.cells] for row in table.rows])
            rendered.append(render_table(table))
    assert active and len(tables) == 3
    assert '5.1 Hipótesis general' in paragraphs
    assert 'Anexo 2 Círculo de Covey' in paragraphs
    backup = HERE / 'reporte-auxiliar-anterior-2026-10-13'
    if TARGET.exists() and not backup.exists():
        backup.mkdir()
        shutil.copy2(TARGET, backup / TARGET.name)
        if TARGET.with_suffix('.pdf').exists():
            shutil.copy2(TARGET.with_suffix('.pdf'), backup / TARGET.with_suffix('.pdf').name)
    output = [
        r'\def\seminariotitulo{Gestión del cumplimiento normativo para formalizar vTaxi como plataforma de taxis en Nuevo León}',
        r'\def\seminariosubtitulo{Actividad 12 -- Anteproyecto acumulativo}',
        r'\def\seminarioasunto{Actividad 12 -- Seminario I -- MGA}',
        r'\def\seminariofecha{12 de octubre de 2026}',
        r'\def\seminarioacumulativo{}',
        r'\def\seminarioextras{\usepackage{longtable,booktabs}}',
        r'\long\def\seminariocontenido{',
        '\n'.join(rendered),
        '}',
        r'\input{ITESCA/maestria-en-gestion-administrativa/seminario-i-mga/reporte-seminario-i-plantilla-actividad.tex}',
    ]
    TARGET.write_text('\n'.join(output) + '\n', encoding='utf-8')
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == source_hash
    record = {'source': str(SOURCE.relative_to(SUBJECT)), 'source_sha256': source_hash, 'target': TARGET.name, 'target_sha256': hashlib.sha256(TARGET.read_bytes()).hexdigest(), 'body_paragraphs': paragraphs, 'tables': tables, 'conversion': 'complete_body_not_summary', 'word_unchanged': True}
    (HERE / 'sincronizacion-t12.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'paragraphs': len(paragraphs), 'tables': len(tables), 'word_unchanged': True, 'report': TARGET.name}, ensure_ascii=True))


if __name__ == '__main__':
    main()