import subprocess, os, shutil, hashlib, pymupdf, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.stderr.reconfigure(encoding='utf-8', errors='replace')

root = Path('.').resolve()
subj = root / 'UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
tex_file = subj / 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9.tex'

# Read and fix tex content
content = tex_file.read_text(encoding='utf-8')

# Ensure line 173 is the draw connection, not a duplicate node
target_dup = r"\node (lRecep1) at (-5.0, -6.8) [leafNodeWide]"
# Count occurrences
if content.count(target_dup) > 1:
    bad_block = (
        r"\node (lRecep1) at (-5.0, -6.8) [leafNodeWide] {\textbf{Reforma Constitucional 2011:}\\Art\'iculo 1$^\circ$ CPEUM; personas titulares de derechos de fuente nacional e internacional \citep{alvarezIcaza2009ADH}.};"
        + "\n"
        + r"\draw [connLeaf, draw=branchRecep] (bRecep) -- (lRecep2);"
    )
    good_block = (
        r"\draw [connLeaf, draw=branchRecep] (bRecep) -- (lRecep1);"
        + "\n"
        + r"\draw [connLeaf, draw=branchRecep] (bRecep) -- (lRecep2);"
    )
    content_norm = content.replace("\r\n", "\n")
    bad_norm = bad_block.replace("\r\n", "\n")
    good_norm = good_block.replace("\r\n", "\n")
    assert bad_norm in content_norm, "bad_block not found in content!"
    content = content_norm.replace(bad_norm, good_norm)
    tex_file.write_text(content, encoding='utf-8')
    print("Fixed duplicate node on line 173!")

env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;'

tex_name = 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9'

print('Running pdflatex pass 1...')
res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res1.returncode != 0:
    print('Error in pass 1:')
    for line in res1.stdout.splitlines()[-30:]:
        print(line)
    exit(1)

print('Running pdflatex pass 2...')
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res2.returncode != 0:
    print('Error in pass 2:')
    for line in res2.stdout.splitlines()[-30:]:
        print(line)
    exit(1)

pdf_file = subj / f'{tex_name}.pdf'
assert pdf_file.exists(), 'PDF does not exist'
doc = pymupdf.open(str(pdf_file))
print(f'Compiled successfully! Total pages: {len(doc)}')

for i, p in enumerate(doc):
    print(f'Page {i+1}: rect={p.rect}, rot={p.rotation}')

# Inspect landscape page for overlaps
p_land = None
for i, p in enumerate(doc):
    if p.rotation == 90 or p.rect.width > p.rect.height:
        p_land = (i + 1, p)
        print(f'Landscape page found at Page {i+1}: rect={p.rect}, rot={p.rotation}')

if p_land:
    page_idx, page_obj = p_land
    blocks = page_obj.get_text('blocks')
    print(f'Landscape Page {page_idx} total text blocks: {len(blocks)}')
    overlaps = []
    for bi in range(len(blocks)):
        r1 = pymupdf.Rect(blocks[bi][:4])
        for bj in range(bi + 1, len(blocks)):
            r2 = pymupdf.Rect(blocks[bj][:4])
            inter = r1 & r2
            if not inter.is_empty and inter.width > 2 and inter.height > 2:
                overlaps.append((blocks[bi][4][:25], blocks[bj][4][:25], inter))
    print(f'Landscape page text overlaps: {len(overlaps)}')
    for o in overlaps:
        print('  Overlap:', repr(o[0]), 'with', repr(o[1]))
    assert len(overlaps) == 0, f'Found {len(overlaps)} overlaps!'
    print('ZERO OVERLAPS CONFIRMED!')

# Check for undefined references
full_text = '\n'.join(p.get_text() for p in doc)
assert '??' not in full_text, 'Undefined references found'
print('ZERO UNDEFINED CITATIONS CONFIRMED!')

# Update deliverable file
entregas = subj / 'entregas-antecedentes-de-los-derechos-humanos'
entregas.mkdir(parents=True, exist_ok=True)
dest = entregas / 'Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf'
shutil.copy2(str(pdf_file), str(dest))
h = hashlib.sha256(pdf_file.read_bytes()).hexdigest()
print(f'New SHA256: {h}')
print(f'Updated delivery file: {dest.name} ({dest.stat().st_size:,} bytes)')
