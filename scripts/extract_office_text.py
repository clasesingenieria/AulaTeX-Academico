import zipfile
import sys
import re
from pathlib import Path

files = [
    Path(r"D:\Documentos\AulaTeX-Academico\UANL\ingeniero-agronomo\responsabilidad-social-y-desarrollo-sustentable\Formato Evidencia 1_RSyDS1.docx"),
    Path(r"D:\Documentos\AulaTeX-Academico\UANL\ingeniero-agronomo\responsabilidad-social-y-desarrollo-sustentable\Doc1.docx"),
    Path(r"D:\Documentos\AulaTeX-Academico\UANL\ingeniero-agronomo\responsabilidad-social-y-desarrollo-sustentable\Evidencia 1 Cuadro Comparativo.ppsx")
]

def extract_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path, 'r') as z:
        names = z.namelist()
        if 'word/document.xml' not in names:
            return ''
        data = z.read('word/document.xml').decode('utf-8', errors='ignore')
        texts = re.findall(r'<w:t[^>]*>(.*?)</w:t>', data, flags=re.DOTALL)
        return '\n'.join([re.sub(r'\s+', ' ', t).strip() for t in texts if t.strip()])

def extract_ppsx_text(path: Path) -> str:
    with zipfile.ZipFile(path, 'r') as z:
        names = z.namelist()
        slides = [n for n in names if n.startswith('ppt/slides/slide') and n.endswith('.xml')]
        all_text = []
        for s in slides:
            data = z.read(s).decode('utf-8', errors='ignore')
            texts = re.findall(r'<a:t[^>]*>(.*?)</a:t>', data, flags=re.DOTALL)
            all_text.extend([re.sub(r'\s+', ' ', t).strip() for t in texts if t.strip()])
        return '\n'.join(all_text)

out_dir = files[0].parent

for p in files:
    if not p.exists():
        print(f'MISSING: {p}')
        continue
    try:
        if p.suffix.lower() == '.docx':
            text = extract_docx_text(p)
        else:
            text = extract_ppsx_text(p)
        out = out_dir / (p.stem + '.txt')
        out.write_text(text, encoding='utf-8')
        print(f'WROTE: {out}')
    except Exception as e:
        print(f'ERROR processing {p}: {e}')

print('Done')
