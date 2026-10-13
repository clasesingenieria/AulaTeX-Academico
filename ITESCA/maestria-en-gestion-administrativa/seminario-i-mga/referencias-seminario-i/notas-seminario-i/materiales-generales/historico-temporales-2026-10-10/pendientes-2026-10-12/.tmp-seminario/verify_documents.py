from pathlib import Path
from zipfile import ZipFile
from lxml import etree
from docx import Document
from pypdf import PdfReader
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'ITESCA/maestria-en-gestion-administrativa/seminario-i-mga'
W=ROOT/'.tmp-seminario'
data=json.loads((W/'content.json').read_text(encoding='utf8'))
def get_background(d):
    a=[p.text for p in d.paragraphs]
    start=a.index('1 Antecedentes');end=a.index('2 Planteamiento del problema')
    return a[start:end]
docs={n:Document(C/f'entregas/Tarea{n}_DeLaCruzMunoz.docx') for n in [8,9]}
assert get_background(docs[8])==get_background(docs[9])
result={'antecedentes_identicos':True,'archivos':[],'revision_visual':'Todas las páginas revisadas; cuatro páginas de antecedentes son idénticas entre T8 y T9.'}
for n,d in docs.items():
    path=C/f'entregas/Tarea{n}_DeLaCruzMunoz.docx'
    with ZipFile(path) as z:
        assert len(z.namelist())==len(set(z.namelist()))
        xml=etree.fromstring(z.read('word/document.xml'))
        codes=xml.xpath('//*[local-name()="instrText"]/text()')
        assert any('TOC' in x for x in codes)
        assert any('PAGEREF' in x for x in codes)
    paras=[p.text for p in d.paragraphs]
    headings=[p.text for p in d.paragraphs if p.style.name.lower().startswith('heading') or p.style.name.lower().startswith('título')]
    for i in range(1,10):assert any(h.startswith(str(i)+' ') for h in headings)
    assert not any('Capítulo' in h for h in headings)
    assert data['title'] in paras
    if n==9:
        assert len(d.tables)==1
        assert len(d.tables[0].rows)==5
        assert d.tables[0].cell(2,1).text==data['problem']
        assert d.tables[0].cell(3,1).text==data['question']
        for q in data['specific_questions']:assert any(q in p for p in paras)
    pdf=W/f'qa{n}/Tarea{n}_DeLaCruzMunoz.pdf'
    reader=PdfReader(pdf)
    text='\n'.join(x.extract_text() for x in reader.pages)
    assert 'Error!' not in text and '¡Error!' not in text
    assert all(len(x.extract_text().strip())>50 for x in reader.pages)
    result['archivos'].append({'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'paginas':len(reader.pages),'titulos':headings,'indice_automatico':True})
with ZipFile(C/'entregas/RegistroTema_DeLaCruzMunoz.docx') as a,ZipFile(C/'anteproyecto/evidencias/moodle-2026-09-27/03.01 Seleccion de proyecto de titulacion 25130604.docx') as b:
    assert set(a.namelist())==set(b.namelist())
    assert all(a.read(n)==b.read(n) for n in a.namelist() if n!='word/document.xml')
result['registro']={'formato_oficial_conservado':True,'pendientes':['CVU','firma del estudiante'],'enviado':False}
(C/'anteproyecto/evidencias/moodle-2026-09-27/verificacion-documentos.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in result.items() if k!='archivos'},ensure_ascii=False))
print([(a['file'],a['paginas']) for a in result['archivos']])
