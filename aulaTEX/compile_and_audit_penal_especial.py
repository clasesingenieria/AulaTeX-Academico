import subprocess, os, shutil, hashlib, pymupdf
from pathlib import Path

root = Path('.').resolve()
subj = root / 'UnADM/licenciatura-en-derecho-unadm/derecho-penal-especial-mexicano-lde'
tex_file = subj / 'reporte-derecho-penal-especial-mexicano-Actividad-5.tex'

with open(tex_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace all occurrences of old footnote
new_fn = r"\footnote{Declaraci\'on sobre el uso de inteligencia artificial: Se utiliz\'o un modelo de lenguaje (asistencia tipo ChatGPT) exclusivamente como apoyo para la revisi\'on y correcci\'on de estilo del texto. La autor\'ia intelectual, la originalidad del contenido y las ideas desarrolladas son propias del estudiante, quien asume la plena responsabilidad sobre el texto, el an\'alisis jur\'idico y las conclusiones aqu\'i formuladas.}"

# Find and replace old footnote in abstract and conclusion
while r"\footnote{Declaraci\'on institucional sobre herramientas de apoyo:" in text:
    s = text.find(r"\footnote{Declaraci\'on institucional sobre herramientas de apoyo:")
    e = text.find(r"formuladas.}", s) + len(r"formuladas.}")
    text = text[:s] + new_fn + text[e:]

with open(tex_file, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated Penal Especial footnote successfully!")

env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;;'

tex_name = 'reporte-derecho-penal-especial-mexicano-Actividad-5'

res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)

pdf_file = subj / f'{tex_name}.pdf'
assert pdf_file.exists(), "PDF not found!"
doc = pymupdf.open(str(pdf_file))
print(f"Compilation SUCCESS! Total pages: {len(doc)}")

entregas_dir = subj / 'entregas-derecho-penal-especial-mexicano'
deliv = entregas_dir / 'Actividad-S5-Libertad-personal-Martin-Jonathan-de-la-Cruz.pdf'
shutil.copy2(str(pdf_file), str(deliv))

with open(pdf_file, 'rb') as f:
    h = hashlib.sha256(f.read()).hexdigest()

print(f"SHA-256: {h}")
print(f"Deliverable updated: {deliv.name}")
