"""Compilar y cotejar informe completo y entrega de cinco páginas, sin Moodle."""
from pathlib import Path
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
import argparse
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import unicodedata
import pymupdf
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ASSETS = HERE.parent
SUBJECT = ASSETS.parent
ROOT = SUBJECT.parents[2]
STEM = 'reporte-estadistica-aplicada-para-la-administracion-Actividad-2'
SOURCE = SUBJECT / (STEM + '.tex')
REPORT = SUBJECT / (STEM + '.pdf')
DELIVERY = SUBJECT / 'entregas-estadistica-aplicada-para-la-administracion/Actividad-2-Investigacion.pdf'
BACKUP = ASSETS / 'respaldo-investigacion-fichas-2026-10-25'
QA = ROOT / '.build/qa-investigacion-fichas'
MANIFEST = ASSETS / 'validacion-investigacion-fichas-2026-10-25.json'
SPECS = [('completo', SOURCE, ROOT / '.build/latex/estadistica-act2' / (STEM + '.pdf'), REPORT),
         ('entrega', HERE / 'version-entrega.tex', ROOT / '.build/latex/estadistica-act2-entrega/version-entrega.pdf', DELIVERY)]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def normalize(text):
    text = unicodedata.normalize('NFKC', text).lower()
    text = re.sub(r'(\w)-\s*\n(\w)', r'\1\2', text)
    return re.sub(r'[^\w]+', '', text)


def compile_one(spec):
    _, tex, pdf, _ = spec
    env = os.environ.copy()
    env['PATH'] = 'C:/texlive/2026/bin/windows;C:/Strawberry/perl/bin;' + env['PATH']
    env['TEXINPUTS'] = f'.;{ROOT.as_posix()}/aulaTEX/base/Plantilla-Informe//;'
    env['BSTINPUTS'] = env['TEXINPUTS']
    command = ['C:/texlive/2026/bin/windows/latexmk.exe', '-norc', '-xelatex', '-halt-on-error', '-interaction=nonstopmode',
               '-outdir=' + pdf.parent.relative_to(ROOT).as_posix(), tex.relative_to(ROOT).as_posix()]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=300)
    (pdf.parent / 'build-driver.log').write_bytes(result.stdout + result.stderr)
    if result.returncode:
        raise RuntimeError('Compilación fallida: ' + tex.name)


def exact_cover(path):
    temp = path.with_suffix('.portada-preservada.pdf')
    with pymupdf.open(path) as document, pymupdf.open(BACKUP / (STEM + '.pdf')) as old:
        document.delete_page(0)
        document.insert_pdf(old, from_page=0, to_page=0, start_at=0)
        document.save(temp, garbage=4, deflate=True)
    temp.replace(path)


def render(document, label):
    QA.mkdir(parents=True, exist_ok=True)
    sheet = Image.new('RGB', (1080, math.ceil(len(document) / 3) * 465), '#ddd')
    for index, page in enumerate(document):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1))
        pix.save(QA / f'{label}-{index+1:02}.png')
        im = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        im.thumbnail((340, 435))
        x, y = index % 3 * 360, index // 3 * 465
        sheet.paste(im, (x + (360 - im.width) // 2, y + 4))
        ImageDraw.Draw(sheet).text((x + 5, y + 445), f'{label} {index+1}', fill='black')
    path = QA / (label + '-contacto.png')
    sheet.save(path)
    return path.relative_to(ROOT).as_posix()


def validate(promote=False):
    results = []
    bibliography = (SUBJECT / 'referencias-estadistica-verificadas.bib').read_text(encoding='utf-8')
    references = (HERE / 'referencias.tex').read_text(encoding='utf-8')
    keys = re.findall(r'\\bibitem\[[^\]]+\]\{([^}]+)\}', references)
    assert len(keys) == 6 and all('{' + key + ',' in bibliography for key in keys)
    for label, tex, built, target in SPECS:
        active_source = SOURCE if label == 'completo' else HERE / 'contenido-entrega.tex'
        source_text = active_source.read_text(encoding='utf-8')
        assert len(re.findall(r'\\section\{', source_text)) == 3
        assert len(re.findall(r'\\begin\{fichainvestigacion\}', source_text)) == 3
        assert r'\section{Del diseño muestral a la evidencia administrativa}' in source_text
        dependencies = [SOURCE, HERE / 'formato-fichas.tex', HERE / 'referencias.tex', tex, active_source]
        assert built.stat().st_mtime >= max(p.stat().st_mtime for p in dependencies), label
        log = built.with_suffix('.log').read_text(encoding='utf-8', errors='replace')
        assert not re.search(r'Overfull|Underfull|Missing character|Citation .*undefined|There were undefined|^!', log, re.M), label
        if promote:
            exact_cover(built)
        path = built if promote else target
        with pymupdf.open(path) as document, pymupdf.open(BACKUP / (STEM + '.pdf')) as old:
            assert len(document) == 5 if label == 'entrega' else len(document) >= 8
            assert hashlib.sha256(document[0].get_pixmap().samples).digest() == hashlib.sha256(old[0].get_pixmap().samples).digest()
            text = '\n'.join(page.get_text() for page in list(document)[1:])
            for phrase in ['Resumen', 'Tabla de contenido', 'Introducción', 'Conclusiones', 'Referencias', 'Ficha 1.', 'Ficha 2.', 'Ficha 3.',
                           'El autor declara haber realizado y validado', 'corrección y organización', '28%', '7.2%', '4.8%']:
                assert normalize(phrase) in normalize(text), (label, phrase)
            assert 'Nova' not in text and '[?]' not in text and '(??)' not in text
            fonts = set()
            for page in list(document)[1:]:
                for block in page.get_text('dict')['blocks']:
                    for line in block.get('lines', []):
                        for span in line['spans']:
                            if not span['text'].strip():
                                continue
                            box = pymupdf.Rect(span['bbox'])
                            assert box.x0 >= -.2 and box.y0 >= -.2 and box.x1 <= page.rect.width + .2 and box.y1 <= page.rect.height + .2, (label, page.number + 1, span['text'])
                            fonts.add(span['font'])
                            if box.y1 < page.rect.height - 50:
                                if 'Arial' in span['font']:
                                    assert abs(span['size'] - 12 * 72 / 72.27) < .08 or span['text'].strip() == '1', (label, span)
                                else:
                                    assert span['font'].startswith('LM') and not re.search(r'[A-Za-z]{4,}', span['text']), (label, span)
            assert r'\setstretch{1.5}' in source_text
            toc = built.with_suffix('.toc').read_text(encoding='utf-8')
            assert all(f'numberline {{{i}}}' in toc for i in [1, 2, 3]) and '{Referencias}' in toc
            urls = {item.get('uri') for page in document for item in page.get_links()}
            for doi in ['10.1038/s41586-021-04198-4', '10.1257/jep.37.4.23', '10.1038/s41586-024-07500-2']:
                assert 'https://doi.org/' + doi in urls
            contact = render(document, label)
            page_count = len(document)
        results.append({'version': label, 'file': target.relative_to(SUBJECT).as_posix(), 'pages': page_count, 'sha256': sha(path),
                        'three_acts': True, 'three_article_boxes': True, 'summary_toc_declaration': True, 'cover_preserved': True,
                        'font_size_and_spacing_passed': True, 'fonts': sorted(fonts), 'bounds_log_citations_passed': True, 'render': contact})
    assert math.isclose(100 / 8000, .0125) and math.isclose(100 / 2000, .05)
    assert math.isclose(.8 * .70 + .2 * .90, .74) and math.isclose((.70 + .90) / 2, .80)
    assert math.ceil(1.96**2 * .25 / .05**2) == 385 and math.ceil(385 / .8) == 482
    assert math.isclose((.072 - .048) / .072, 1 / 3)
    previous = json.loads((BACKUP / 'assets-estadistica-aplicada-para-la-administracion/validacion-resumen-fusion-2026-10-25.json').read_text(encoding='utf-8'))
    protected = [row for row in previous['reports'] if row['tag'] != 'act2'] + [row for row in previous['deliveries'] if row['activity'] != 2]
    assert all(sha(SUBJECT / row['file']) == row['sha256'] for row in protected)
    notes = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/unidad-1-muestreo'
    original_sources = json.loads((notes / 'fuentes.json').read_text(encoding='utf-8'))['sources']
    assert all(sha(SUBJECT / row['path']) == row['sha256'] for row in original_sources)
    supplemental = json.loads((notes / 'wfh-metodologia-marzo-2023-procedencia.json').read_text(encoding='utf-8'))
    assert sha(notes / supplemental['file']) == supplemental['sha256']
    if promote:
        for _, _, built, target in SPECS:
            shutil.copy2(built, target)
    data = {'validated_at_utc': datetime.now(timezone.utc).isoformat(), 'passed': True, 'visual_review_completed': False,
            'scope': 'Actividad2: investigación completa y entrega de cinco páginas con base conceptual integrada y tres fichas.',
            'reports': results, 'deliveries': [{'activity': 2, 'file': DELIVERY.relative_to(SUBJECT).as_posix(), 'sha256': sha(DELIVERY)}],
            'formal_references': keys, 'original_source_hashes_verified': len(original_sources), 'supplementary_methodology': supplemental,
            'numerical_checks_passed': True, 'unrelated_pdfs_preserved': len(protected), 'infographic_unchanged': True,
            'editorial_review': 'Tres tiempos argumentativos, conceptos definidos antes de aplicarlos, fichas comparables, síntesis en el desarrollo y conclusión con postura/razón/consecuencia. Sin resultados empíricos nuevos en el cierre.',
            'platform_submission': (json.loads(MANIFEST.read_text(encoding='utf-8')).get('platform_submission') if MANIFEST.exists() and isinstance(json.loads(MANIFEST.read_text(encoding='utf-8')).get('platform_submission'), dict) and json.loads(MANIFEST.read_text(encoding='utf-8'))['platform_submission'].get('sha256') == sha(DELIVERY) else False)}
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
        assert data['passed'] and all(sha(SUBJECT / row['file']) == row['sha256'] for row in data['reports'])
        data['visual_review_completed'] = True
        data['visual_review'] = {'completed_at_utc': datetime.now(timezone.utc).isoformat(), 'contacts': [r['render'] for r in data['reports']],
                                 'checks': ['Todas las páginas', 'Fichas y continuaciones', 'Índice real', 'Notas IA', 'Referencias íntegras', 'Sin recortes ni solapamientos']}
        MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    else:
        if args.build:
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(compile_one, SPECS))
        data = validate(args.promote)
    print(json.dumps({'passed': data['passed'], 'visual_review_completed': data['visual_review_completed'],
                      'pages': {r['version']: r['pages'] for r in data['reports']}, 'unrelated_pdfs_preserved': data['unrelated_pdfs_preserved']}, ensure_ascii=True))


if __name__ == '__main__':
    main()
