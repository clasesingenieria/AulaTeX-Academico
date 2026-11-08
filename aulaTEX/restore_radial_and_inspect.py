import subprocess, os, shutil, sys
from pathlib import Path
import pymupdf

tex_path = Path("UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde/reporte-antecedentes-de-los-derechos-humanos-Actividad-9.tex")
content = tex_path.read_text(encoding="utf-8")

# Let's restore the exact radial landscape block from fix_dh_proper.py
s_landscape = content.find(r"\begin{landscape}")
e_landscape = content.find(r"\end{landscape}") + len(r"\end{landscape}")

# Read the radial block from fix_dh_proper.py
proper_path = Path("aulaTEX/fix_dh_proper.py")
proper_code = proper_path.read_text(encoding="utf-8")

# Extract the landscape block from fix_dh_proper.py
s_p = proper_code.find(r"\begin{landscape}")
e_p = proper_code.find(r"\end{landscape}") + len(r"\end{landscape}")
radial_block = proper_code[s_p:e_p]

# Also ensure the color definitions in preamble match fix_dh_proper.py
old_colors = r"""\definecolor{mainCore}{HTML}{1A365D}
\definecolor{branchHist}{HTML}{2B6CB0}
\definecolor{branchTeor}{HTML}{2C7A7B}
\definecolor{branchDoc}{HTML}{C05621}
\definecolor{branchInt}{HTML}{742A2A}
\definecolor{branchRecep}{HTML}{44337A}"""

# Check if old_colors is present or if we have mc*
if r"\definecolor{mainCore}" not in content:
    # Replace the mc* definitions with mainCore etc.
    s_mc = content.find(r"% ---- Estilos del mapa conceptual")
    e_mc = content.find(r"\setlength{\emergencystretch}")
    if s_mc >= 0 and e_mc > s_mc:
        content = content[:s_mc] + old_colors + "\n\n" + content[e_mc:]

content = content[:s_landscape] + radial_block + content[e_landscape:]
tex_path.write_text(content, encoding="utf-8")
print("Restored radial landscape block from fix_dh_proper.py!")

# Compile
root = Path('.').resolve()
subj = tex_path.parent
tex_name = 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9'

env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;'

res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
assert res2.returncode == 0, f"Compilation failed: {res2.stdout[-300:]}"

delivery = subj / 'entregas-antecedentes-de-los-derechos-humanos/Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf'
shutil.copy2(subj / f'{tex_name}.pdf', delivery)

doc = pymupdf.open(subj / f'{tex_name}.pdf')
print(f"Total pages: {len(doc)}")
p6 = doc[5]
print("Page 6 Rect:", p6.rect, "Rotation:", p6.rotation)
blocks = p6.get_text("blocks")
words = p6.get_text("words")
print(f"Page 6 Blocks: {len(blocks)}, Words: {len(words)}")

w_ov = []
for i in range(len(words)):
    for j in range(i + 1, len(words)):
        b1, b2 = words[i][:4], words[j][:4]
        ix1, iy1 = max(b1[0], b2[0]), max(b1[1], b2[1])
        ix2, iy2 = min(b1[2], b2[2]), min(b1[3], b2[3])
        if ix2 > ix1 + 1 and iy2 > iy1 + 1:
            w_ov.append((words[i][4], words[j][4]))

print(f"Word overlaps on Page 6: {len(w_ov)}")
for w in w_ov:
    print("  Word overlap:", w)

