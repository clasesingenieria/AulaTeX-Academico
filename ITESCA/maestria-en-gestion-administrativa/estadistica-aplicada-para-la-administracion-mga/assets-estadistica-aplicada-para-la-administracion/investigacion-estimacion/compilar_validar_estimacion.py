"""Compila, valida y promueve las dos versiones de la Actividad 4 (tarea 2.1 Investigación documental y aplicada, módulo 1754),
junto con la Actividad 3 (1.3 Cuestionario, módulo 1749, solo reporte en raíz) y la Actividad 5 (2.2 Ejercicios, módulo 1755).
"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import unicodedata

import pymupdf
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
SUBJECT = ASSETS.parent
ROOT = SUBJECT.parents[2]
QA_DIR = ROOT / '.build/qa-renumeracion-estimacion'
MANIFEST = ASSETS / 'validacion-renumeracion-estimacion-2026-10-25.json'

ACT3_TEX = SUBJECT / 'reporte-estadistica-aplicada-para-la-administracion-Actividad-3.tex'
ACT3_BUILD = ROOT / '.build/latex/estadistica-act3/reporte-estadistica-aplicada-para-la-administracion-Actividad-3.pdf'
ACT3_PDF = SUBJECT / 'reporte-estadistica-aplicada-para-la-administracion-Actividad-3.pdf'

ACT4_FULL_TEX = SUBJECT / 'reporte-estadistica-aplicada-para-la-administracion-Actividad-4.tex'
ACT4_FULL_BUILD = ROOT / '.build/latex/estadistica-act4/reporte-estadistica-aplicada-para-la-administracion-Actividad-4.pdf'
ACT4_FULL_PDF = SUBJECT / 'reporte-estadistica-aplicada-para-la-administracion-Actividad-4.pdf'

ACT4_DELIV_TEX = HERE / 'version-entrega.tex'
ACT4_DELIV_BUILD = ROOT / '.build/latex/estadistica-act4-entrega/version-entrega.pdf'
ACT4_DELIV_PDF = SUBJECT / 'entregas-estadistica-aplicada-para-la-administracion/Actividad-4-Investigacion-estimacion.pdf'

ACT5_TEX = SUBJECT / 'reporte-estadistica-aplicada-para-la-administracion-Actividad-5.tex'
ACT5_BUILD = ROOT / '.build/latex/estadistica-act5/reporte-estadistica-aplicada-para-la-administracion-Actividad-5.pdf'
ACT5_PDF = SUBJECT / 'reporte-estadistica-aplicada-para-la-administracion-Actividad-5.pdf'
ACT5_DELIV_PDF = SUBJECT / 'entregas-estadistica-aplicada-para-la-administracion/Actividad-5-Ejercicios-distribuciones.pdf'

SPECS = [
    ('act3_cuestionario', ACT3_TEX, ACT3_BUILD, [ACT3_PDF]),
    ('act4_completo', ACT4_FULL_TEX, ACT4_FULL_BUILD, [ACT4_FULL_PDF]),
    ('act4_entrega', ACT4_DELIV_TEX, ACT4_DELIV_BUILD, [ACT4_DELIV_PDF]),
    ('act5_ejercicios', ACT5_TEX, ACT5_BUILD, [ACT5_PDF, ACT5_DELIV_PDF]),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(text: str) -> str:
    text = unicodedata.normalize('NFKC', text).lower()
    text = re.sub(r'(\w)-\s*\n(\w)', r'\1\2', text)
    return re.sub(r'[^\w]+', '', text)


def compile_one(spec):
    label, tex, built, _ = spec
    built.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['PATH'] = 'C:/texlive/2026/bin/windows;C:/Strawberry/perl/bin;' + env['PATH']
    env['TEXINPUTS'] = f'.;{ROOT.as_posix()}/aulaTEX/base/Plantilla-Informe//;'
    env['BSTINPUTS'] = env['TEXINPUTS']
    cmd = [
        'C:/texlive/2026/bin/windows/latexmk.exe', '-norc', '-xelatex',
        '-halt-on-error', '-interaction=nonstopmode',
        f'-outdir={built.parent.relative_to(ROOT).as_posix()}',
        tex.relative_to(ROOT).as_posix(),
    ]
    res = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, timeout=240)
    log = built.with_suffix('.log')
    if res.returncode == 0 and log.exists() and re.search(
        r'Citation .*undefined|There were undefined|Rerun to get',
        log.read_text(encoding='utf-8', errors='replace'),
    ):
        res = subprocess.run(cmd[:2] + ['-g'] + cmd[2:], cwd=ROOT, env=env, capture_output=True, timeout=240)
    if res.returncode != 0:
        out = (res.stdout + res.stderr).decode('utf-8', errors='replace')[-4000:]
        raise RuntimeError(f'Error compilando {label}:\n{out}')


def render(doc, label: str) -> str:
    folder = QA_DIR / label
    folder.mkdir(parents=True, exist_ok=True)
    cols = 3
    contact = Image.new('RGB', (cols * 320, math.ceil(len(doc) / cols) * 435), '#e6e6e6')
    for idx, page in enumerate(doc):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1.25, 1.25))
        pix.save(folder / f'pagina-{idx + 1:02d}.png')
        thumb = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        thumb.thumbnail((305, 405))
        x, y = (idx % cols) * 320, (idx // cols) * 435
        contact.paste(thumb, (x + (320 - thumb.width) // 2, y + 4))
        ImageDraw.Draw(contact).text((x + 6, y + 414), f'{label} {idx + 1}', fill='black')
    out = QA_DIR / f'{label}-contacto.png'
    contact.save(out)
    return out.relative_to(ROOT).as_posix()


def check_bounds_and_fonts(doc, check_arial=True):
    fonts = set()
    for page in doc:
        rect = page.mediabox
        assert abs(rect.width - 612) < 1 or abs(rect.width - 792) < 1
        for block in page.get_text('dict')['blocks']:
            for line in block.get('lines', []):
                for span in line['spans']:
                    txt = span['text'].strip()
                    if not txt:
                        continue
                    box = pymupdf.Rect(span['bbox'])
                    assert box.x0 >= -0.2 and box.y0 >= -0.2 and box.x1 <= rect.width + 0.2 and box.y1 <= rect.height + 0.2, (page.number + 1, txt, list(box))
                    if page.number > 0 and box.y1 < rect.height - 48:
                        fonts.add(span['font'])
                        if check_arial and not re.fullmatch(r'[\d.,+−\-–—/=()\[\]%$:;<>≤≥±×·√∑∏∞αμσθπˆ\s]+|[a-zA-Z]', txt):
                            assert 'Arial' in span['font'] or 'LM' in span['font'], (page.number + 1, span['font'], txt)
    return sorted(fonts)


def validate(promote=False):
    QA_DIR.mkdir(parents=True, exist_ok=True)
    # Remove obsolete misnumbered deliverables if present
    for old_name in ('Actividad-3-Investigacion-estimacion.pdf', 'Actividad-4-Ejercicios-distribuciones.pdf'):
        old_path = SUBJECT / 'entregas-estadistica-aplicada-para-la-administracion' / old_name
        if promote and old_path.exists():
            old_path.unlink()

    reports = []
    for label, tex, built, targets in SPECS:
        log = built.with_suffix('.log').read_text(encoding='utf-8', errors='replace')
        assert not re.search(r'Overfull|Underfull|Missing character|Citation .*undefined|There were undefined|^!', log, re.M), label
        toc = built.with_suffix('.toc').read_text(encoding='utf-8', errors='replace')
        assert all(f'numberline {{{i}}}' in toc for i in (1, 2, 3)), (label, 'toc')
        with pymupdf.open(built) as doc:
            pages = len(doc)
            cover_text = doc[0].get_text()
            body = '\n'.join(p.get_text() for p in list(doc)[1:])
            for req in ('Resumen', 'Tabla de contenido', '1. Introducción', '3. Conclusiones', 'Referencias',
                        'Declaración de uso de IA', 'corrección y organización', 'El autor declara haber realizado y validado'):
                assert norm(req) in norm(body), (label, req)
            if label == 'act3_cuestionario':
                assert pages == 14, pages
                assert 'Actividad 3: Cuestionario' in cover_text
                notes = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/cuestionario-2026-10-24'
                questions = json.loads((notes / 'respuestas-validadas.json').read_text(encoding='utf-8-sig'))['preguntas']
                for q in questions:
                    if q['numero'] != 7:
                        assert norm(q['pregunta']) in norm(body), q['numero']
                    assert norm(q['respuesta']) in norm(body), q['numero']
            elif label == 'act4_completo':
                assert pages >= 9, pages
                assert 'Actividad 4: Investigación aplicada' in cover_text
                for f in ('Ficha 1.', 'Ficha 2.', 'Ficha 3.', '18,000', '22,000', '210', 'Chebyshev'):
                    assert norm(f) in norm(body), (label, f)
            elif label == 'act4_entrega':
                assert pages == 5, pages
                assert 'Actividad 4: Investigación aplicada' in cover_text
                for f in ('Ficha 1.', 'Ficha 2.', 'Ficha 3.', '18,000', '22,000', '210', 'Chebyshev'):
                    assert norm(f) in norm(body), (label, f)
            elif label == 'act5_ejercicios':
                assert pages == 9, pages
                assert 'Actividad 5: Ejercicios' in cover_text
                for val in ('4.472136', '3.162278', '0.109733', '0.592552', '0.495015', '0.114040', '0.005142', '0.505479'):
                    assert val in body, (label, val)
            fonts = check_bounds_and_fonts(doc)
            rendered = render(doc, label)
        if promote:
            for target in targets:
                shutil.copy2(built, target)
        primary = targets[0] if promote else built
        reports.append({
            'label': label,
            'file': targets[0].relative_to(SUBJECT).as_posix(),
            'pages': pages,
            'sha256': sha(primary),
            'fonts': fonts,
            'render': rendered,
            'deliveries': [t.relative_to(SUBJECT).as_posix() for t in targets if 'entregas-' in t.as_posix()],
        })

    deliveries_dir = SUBJECT / 'entregas-estadistica-aplicada-para-la-administracion'
    present_deliveries = sorted(p.name for p in deliveries_dir.glob('*.pdf'))
    if promote:
        assert present_deliveries == [
            'Actividad-1-Infografia.pdf',
            'Actividad-2-Investigacion.pdf',
            'Actividad-4-Investigacion-estimacion.pdf',
            'Actividad-5-Ejercicios-distribuciones.pdf',
        ], present_deliveries

    data = {
        'validated_at_utc': datetime.now(timezone.utc).isoformat(),
        'passed': True,
        'visual_review_completed': False,
        'course_activity_mapping': {
            'Actividad-1': {'aula': '1.1 Infografía 5%', 'moodle_id': 1747, 'report': 'reporte-estadistica-aplicada-para-la-administracion-Actividad-1.pdf', 'delivery': 'entregas-estadistica-aplicada-para-la-administracion/Actividad-1-Infografia.pdf'},
            'Actividad-2': {'aula': '1.2 Investigación 3%', 'moodle_id': 1748, 'report': 'reporte-estadistica-aplicada-para-la-administracion-Actividad-2.pdf', 'delivery': 'entregas-estadistica-aplicada-para-la-administracion/Actividad-2-Investigacion.pdf'},
            'Actividad-3': {'aula': '1.3 Cuestionario 5%', 'moodle_id': 1749, 'report': 'reporte-estadistica-aplicada-para-la-administracion-Actividad-3.pdf', 'delivery': None},
            'Actividad-4': {'aula': '2.1 Investigación documental y aplicada 5%', 'moodle_id': 1754, 'report': 'reporte-estadistica-aplicada-para-la-administracion-Actividad-4.pdf', 'delivery': 'entregas-estadistica-aplicada-para-la-administracion/Actividad-4-Investigacion-estimacion.pdf'},
            'Actividad-5': {'aula': '2.2 Ejercicios 5%', 'moodle_id': 1755, 'report': 'reporte-estadistica-aplicada-para-la-administracion-Actividad-5.pdf', 'delivery': 'entregas-estadistica-aplicada-para-la-administracion/Actividad-5-Ejercicios-distribuciones.pdf'},
        },
        'reports': reports,
        'present_deliveries': present_deliveries,
    }
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--promote', action='store_true')
    parser.add_argument('--visual-reviewed', action='store_true')
    args = parser.parse_args()
    if args.visual_reviewed:
        data = json.loads(MANIFEST.read_text(encoding='utf-8'))
        assert data['passed']
        data['visual_review_completed'] = True
        data['visual_review_at_utc'] = datetime.now(timezone.utc).isoformat()
        MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        if args.build:
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(compile_one, SPECS))
        data = validate(promote=args.promote)
    print(json.dumps({
        'passed': data['passed'],
        'visual_review_completed': data['visual_review_completed'],
        'pages': {r['label']: r['pages'] for r in data['reports']},
        'present_deliveries': data['present_deliveries'],
    }, ensure_ascii=True))


if __name__ == '__main__':
    main()

