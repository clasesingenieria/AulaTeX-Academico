from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.units import inch
import sys
from pathlib import Path

def md_to_paragraphs(md_text):
    lines = [l.rstrip() for l in md_text.splitlines()]
    paras = []
    buf = []
    for ln in lines:
        if ln.strip() == "":
            if buf:
                paras.append(" ".join(buf))
                buf = []
        else:
            # remove markdown headers and bullets simple
            if ln.startswith('#'):
                ln = ln.lstrip('#').strip()
            if ln.startswith('- '):
                ln = '\u2022 ' + ln[2:]
            buf.append(ln)
    if buf:
        paras.append(" ".join(buf))
    return paras

def generate(pdf_path, md_path):
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter,
                            rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=TA_CENTER, spaceAfter=12)
    meta_style = ParagraphStyle('Meta', parent=styles['Normal'], alignment=TA_CENTER, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], alignment=TA_JUSTIFY, leading=14)

    md_text = Path(md_path).read_text(encoding='utf-8')
    # Extract front matter title/author/date
    title = ''
    author = ''
    date = ''
    lines = md_text.splitlines()
    for i,l in enumerate(lines[:20]):
        if l.lower().startswith('title:'):
            title = l.split(':',1)[1].strip().strip('"')
        if l.lower().startswith('author:'):
            author = l.split(':',1)[1].strip().strip('"')
        if l.lower().startswith('date:'):
            date = l.split(':',1)[1].strip().strip('"')

    story = []
    if title:
        story.append(Paragraph(title, title_style))
    if author or date:
        meta = f"{author} — {date}" if author and date else author or date
        story.append(Paragraph(meta, meta_style))
    story.append(Spacer(1, 0.2*inch))

    # Remove front-matter block
    if md_text.startswith('---'):
        parts = md_text.split('---',2)
        if len(parts) == 3:
            md_body = parts[2]
        else:
            md_body = md_text
    else:
        md_body = md_text

    paras = md_to_paragraphs(md_body)
    for p in paras:
        story.append(Paragraph(p, body_style))
        story.append(Spacer(1, 0.12*inch))

    doc.build(story)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: generate_report_pdf.py input.md output.pdf')
        sys.exit(1)
    md = sys.argv[1]
    pdf = sys.argv[2]
    generate(pdf, md)
