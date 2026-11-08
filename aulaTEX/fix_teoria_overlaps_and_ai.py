import subprocess, os, shutil, hashlib, pymupdf
from pathlib import Path

root = Path('.').resolve()
subj = root / 'UnADM/licenciatura-en-derecho-unadm/teoria-del-estado-y-constitucion-lde'
tex_file = subj / 'reporte-teoria-del-estado-y-constitucion-Actividad-5.tex'

with open(tex_file, 'r', encoding='utf-8') as f:
    text = f.read()

# Replace subtitle and header/footer settings
old_sub = r"\def\documentsubtitle {El Tratado de Guadalupe Hidalgo (1848) y la subsistencia de los elementos constitutivos del Estado mexicano}"
new_sub = (
    r"\def\documentsubtitle {El Tratado de Guadalupe Hidalgo y la subsistencia del Estado}" + "\n" +
    r"\def\documenttitlehf {Tratado de Guadalupe Hidalgo y el Estado}" + "\n" +
    r"\def\hfwidthwrap {true}" + "\n" +
    r"\def\hfwidthtitle {0.48}" + "\n" +
    r"\def\hfwidthcourse {0.46}"
)
text = text.replace(old_sub, new_sub)

# Replace footnote
old_fn_start = text.find(r"\footnote{Declaraci\'on institucional sobre herramientas de apoyo:")
if old_fn_start != -1:
    old_fn_end = text.find(r"}", text.find(r"formuladas.", old_fn_start)) + 1
    new_fn = r"\footnote{Declaraci\'on sobre el uso de inteligencia artificial: Se utiliz\'o un modelo de lenguaje (asistencia tipo ChatGPT) exclusivamente como apoyo para la revisi\'on y correcci\'on de estilo del texto. La autor\'ia intelectual, la originalidad del contenido y las ideas desarrolladas son propias del estudiante, quien asume la plena responsabilidad sobre el texto, el an\'alisis jur\'idico y las conclusiones aqu\'i formuladas.}"
    text = text[:old_fn_start] + new_fn + text[old_fn_end:]

with open(tex_file, 'w', encoding='utf-8') as f:
    f.write(text)

print("Updated Teoria del Estado LaTeX file successfully!")

env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;;'

tex_name = 'reporte-teoria-del-estado-y-constitucion-Actividad-5'

print("Compiling pdflatex pass 1...")
res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res1.returncode != 0:
    print("Pass 1 error:")
    for l in res1.stdout.splitlines()[-30:]:
        print(l)
    exit(1)

print("Compiling pdflatex pass 2...")
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res2.returncode != 0:
    print("Pass 2 error:")
    for l in res2.stdout.splitlines()[-30:]:
        print(l)
    exit(1)

pdf_file = subj / f'{tex_name}.pdf'
assert pdf_file.exists(), "PDF not found!"
doc = pymupdf.open(str(pdf_file))
print(f"Compilation SUCCESS! Total pages: {len(doc)}")

total_overlaps = 0
for idx, page in enumerate(doc):
    blocks = [b for b in page.get_text('blocks') if b[4].strip()]
    n = len(blocks)
    page_overlaps = 0
    for i in range(n):
        for j in range(i+1, n):
            b1 = blocks[i]
            b2 = blocks[j]
            x_overlap = max(0, min(b1[2], b2[2]) - max(b1[0], b2[0]))
            y_overlap = max(0, min(b1[3], b2[3]) - max(b1[1], b2[1]))
            if x_overlap > 3 and y_overlap > 3:
                page_overlaps += 1
                total_overlaps += 1
                print(f"Overlap on Page {idx+1}: {b1[4].strip()[:30]!r} vs {b2[4].strip()[:30]!r}")
    if page_overlaps == 0:
        print(f"Page {idx+1} ({page.rect}, rot={page.rotation}): 0 overlaps (perfect!)")

print(f"\nTOTAL TEORIA DEL ESTADO OVERLAPS: {total_overlaps}")

entregas_dir = subj / 'entregas-teoria-del-estado-y-constitucion'
deliv1 = entregas_dir / '2026_TeoriaEstado_S5_Martin Jonathan de la Cruz.pdf'
deliv2 = entregas_dir / '2026_TeoríaEstado_S5_Martin_Jonathan_de_la_Cruz_Munoz.pdf'

shutil.copy2(str(pdf_file), str(deliv1))
shutil.copy2(str(pdf_file), str(deliv2))

with open(pdf_file, 'rb') as f:
    h = hashlib.sha256(f.read()).hexdigest()

print(f"SHA-256: {h}")
print(f"Deliverables updated: {deliv1.name} and {deliv2.name}")

