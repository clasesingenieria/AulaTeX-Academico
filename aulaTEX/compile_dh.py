import subprocess, os, shutil, sys
from pathlib import Path

root = Path('.').resolve()
subj = root / 'UnADM/licenciatura-en-derecho-unadm/antecedentes-de-los-derechos-humanos-lde'
tex_name = 'reporte-antecedentes-de-los-derechos-humanos-Actividad-9'

env = os.environ.copy()
env['PATH'] = 'C:/texlive/2026/bin/windows;' + env['PATH']
env['TEXINPUTS'] = f'{root}/aulaTEX/base/Plantilla-Informe//;{subj}//;'

print('Pass 1...')
res1 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res1.returncode != 0:
    print('Error in pass 1:')
    for line in res1.stdout.splitlines()[-30:]:
        print(line)
    sys.exit(1)

print('Pass 2...')
res2 = subprocess.run(['pdflatex', '-interaction=nonstopmode', f'{tex_name}.tex'], env=env, cwd=str(subj), capture_output=True, text=True)
if res2.returncode != 0:
    print('Error in pass 2:')
    for line in res2.stdout.splitlines()[-30:]:
        print(line)
    sys.exit(1)

print('Compilation successful!')

# Copy to deliverable path
delivery = subj / 'entregas-antecedentes-de-los-derechos-humanos/Actividad-7-Mapa-mental-Martin-Jonathan-de-la-Cruz.pdf'
delivery.parent.mkdir(parents=True, exist_ok=True)
pdf_src = subj / f'{tex_name}.pdf'
shutil.copy2(pdf_src, delivery)
print(f'Copied to deliverable: {delivery}')

