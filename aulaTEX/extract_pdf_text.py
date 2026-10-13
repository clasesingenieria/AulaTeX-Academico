from pathlib import Path
import sys
from pypdf import PdfReader

pdf_path = Path(r"c:\Users\Sysx\Documents\AulaTeX-Academico\UANL\ingeniero-agronomo\algebra-lineal\Segundo Laboratorio Álgebra Lineal EJ 25.pdf")
if not pdf_path.exists():
    print(f"PDF no encontrado: {pdf_path}")
    sys.exit(2)
reader = PdfReader(str(pdf_path))
texts = []
for p in reader.pages:
    try:
        texts.append(p.extract_text() or "")
    except Exception as e:
        texts.append(f"[ERROR extracting page: {e}]")
out = pdf_path.with_suffix('.txt')
out.write_text('\n\n'.join(texts), encoding='utf-8')
print(f"WROTE: {out}")
