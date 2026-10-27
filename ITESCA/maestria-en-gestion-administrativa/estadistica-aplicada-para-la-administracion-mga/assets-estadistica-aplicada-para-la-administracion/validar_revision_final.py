"""QA de resumen, índice, declaración IA y fusión visual autorizados el 25/10.

--promote consolida compilaciones aisladas; nunca envía a Moodle.
Actividad 2 delega al validador dedicado: informe completo y entrega de cinco páginas.
--visual-reviewed marca solo renders realmente inspeccionados, con hashes vigentes.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import hashlib
import json
import math
import re
import shutil
import unicodedata
import pymupdf
from PIL import Image, ImageDraw

ASSETS = Path(__file__).resolve().parent
SUBJECT = ASSETS.parent
ROOT = SUBJECT.parents[2]
BACKUP = ASSETS / 'respaldo-resumen-fusion-2026-10-25'
QA = ROOT / '.build/qa-estadistica-resumen-fusion'
MANIFEST = ASSETS / 'validacion-resumen-fusion-2026-10-25.json'
STEM = 'reporte-estadistica-aplicada-para-la-administracion-'
SPECS = [(f'act{i}', f'Actividad-{i}') for i in range(1, 6)] + [('encuadre', 'encuadre'), ('mga', 'mga')]
POSTER = ASSETS / 'poster/infografia-muestreo-fusionada.pdf'
DELIVERY_NAMES = ['Actividad-1-Infografia.pdf', 'Actividad-2-Investigacion.pdf', 'Actividad-3-Investigacion-estimacion.pdf', 'Actividad-4-Ejercicios-distribuciones.pdf']


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def norm(text):
    text = unicodedata.normalize('NFKC', text).lower()
    text = re.sub(r'(\w)-\s*\n(\w)', r'\1\2', text)
    return re.sub(r'[^\w]+', '', text)


def render(document, tag):
    folder = QA / tag
    folder.mkdir(parents=True, exist_ok=True)
    contact = Image.new('RGB', (960, math.ceil(len(document) / 3) * 435), '#ddd')
    for i, page in enumerate(document):
        pix = page.get_pixmap(matrix=pymupdf.Matrix(1, 1))
        pix.save(folder / f'pagina-{i+1:02}.png')
        thumbnail = Image.frombytes('RGB', (pix.width, pix.height), pix.samples)
        thumbnail.thumbnail((305, 405))
        x, y = (i % 3) * 320, (i // 3) * 435
        contact.paste(thumbnail, (x + (320 - thumbnail.width) // 2, y + 4))
        ImageDraw.Draw(contact).text((x + 5, y + 414), f'{tag} / {i+1}', fill='black')
    path = QA / f'{tag}-contacto.png'
    contact.save(path)
    return path.relative_to(ROOT).as_posix()


def poster_checks():
    log = ROOT / '.build/latex/estadistica-poster-fusion/infografia-muestreo-fusionada.log'
    assert not re.search(r'Overfull|Underfull|Missing character|Citation .*undefined|There were undefined|^!', log.read_text(encoding='utf-8', errors='replace'), re.M)
    fls = log.with_suffix('.fls').read_text(encoding='utf-8', errors='replace').replace('\\', '/')
    assert 'aulaTEX/base/Plantilla-Informe/template_poster.tex' in fls and 'beamerposter.sty' in fls
    with pymupdf.open(POSTER) as document:
        assert len(document) == 1
        page = document[0]
        assert abs(page.rect.width - 297 * 72 / 25.4) < 1 and abs(page.rect.height - 420 * 72 / 25.4) < 1
        text = page.get_text()
        for word in ['Introducción', 'Conclusiones', 'Referencias', '385', '482', '9.80', '4.99', '3.10', '26130503', 'sin datos empíricos']:
            assert word in text, word
        assert 'Nova' not in text
        assert len(page.get_images()) >= 2
        assert len(page.get_drawings()) > 25
        urls = {x.get('uri') for x in page.get_links()}
        for url in ['https://doi.org/10.1038/s41586-021-04198-4', 'https://openstax.org/details/books/introductory-business-statistics-2e', 'https://doi.org/10.18434/M32189']:
            assert url in urls and re.sub(r'\s+', '', url) in re.sub(r'\s+', '', text), url
        check_bounds(page)
        page.get_pixmap(matrix=pymupdf.Matrix(1.5, 1.5)).save(QA / 'infografia-fusionada.png')
    assert math.isclose(98 / math.sqrt(385), 4.994542475, abs_tol=1e-8)
    assert math.ceil(1.96**2 * .25 / .05**2) == 385 and math.ceil(385 / .8) == 482
    assert sha(ASSETS / 'infografia-muestreo-original.pdf') == 'fdd5b585da1fc4bc0dc7ef83f2cefddf6859163aeac52b68224717525188c2a9'
    baseline = json.loads((ASSETS / 'poster/conservacion-antes.json').read_text(encoding='utf-8'))
    core = {p: digest for p, digest in baseline.items() if p.startswith('aulaTEX/base/')}
    assert core and all(sha(ROOT / path) == digest for path, digest in core.items())
    return {'file': POSTER.relative_to(SUBJECT).as_posix(), 'sha256': sha(POSTER), 'pages': 1, 'size_mm': [297, 420],
            'original_preserved': True, 'core_unchanged_files': len(core), 'core_loaded': True,
            'curve_scenario': 'Teórico: e_pp=98/sqrt(n); 95%, p=0.5, MAS y población grande.',
            'curve_checks_passed': True, 'image': 'poster/ilustracion-muestreo-administrativo.png',
            'image_sha256': sha(ASSETS / 'poster/ilustracion-muestreo-administrativo.png'), 'bounds_and_references_passed': True}


def check_bounds(page):
    bounds = page.mediabox
    for block in page.get_text('dict')['blocks']:
        for line in block.get('lines', []):
            for span in line['spans']:
                if span['text'].strip():
                    box = pymupdf.Rect(span['bbox'])
                    assert box.x0 >= -.2 and box.y0 >= -.2 and box.x1 <= bounds.width + .2 and box.y1 <= bounds.height + .2, (page.number + 1, span['text'], list(box))


def preserve_pages(path, suffix):
    old = BACKUP / (STEM + suffix + '.pdf')
    temp = path.with_suffix('.preservado.pdf')
    with pymupdf.open(path) as document, pymupdf.open(old) as original:
        cover_changed = document[0].get_pixmap().samples != original[0].get_pixmap().samples
        visual_changed = False
        if suffix == 'Actividad-1':
            positions = [i for i, page in enumerate(document) if abs(page.rect.width - 297 * 72 / 25.4) < 1]
            assert len(positions) == 1
            with pymupdf.open(POSTER) as poster:
                visual_changed = document[positions[0]].get_pixmap().samples != poster[0].get_pixmap().samples
        if not cover_changed and not visual_changed:
            return
        if cover_changed:
            document.delete_page(0)
            document.insert_pdf(original, from_page=0, to_page=0, start_at=0)
        if visual_changed:
            document.delete_page(positions[0])
            with pymupdf.open(POSTER) as poster:
                document.insert_pdf(poster, start_at=positions[0])
        document.save(temp, garbage=4, deflate=True)
    temp.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--promote', action='store_true')
    parser.add_argument('--visual-reviewed', action='store_true')
    args = parser.parse_args()
    QA.mkdir(parents=True, exist_ok=True)
    if args.visual_reviewed:
        data = json.loads(MANIFEST.read_text(encoding='utf-8'))
        assert data['passed']
        assert all(sha(SUBJECT / row['file']) == row['sha256'] for row in data['reports'])
        assert all(sha(SUBJECT / row['file']) == row['sha256'] for row in data['deliveries'])
        assert all(sha(SUBJECT / row['file']) == row['sha256'] for row in data.get('investigation_versions', []))
        assert sha(POSTER) == data['infographic']['sha256']
        data['visual_review_completed'] = True
        data['visual_review'] = {'reviewed_at_utc': datetime.now(timezone.utc).isoformat(), 'contacts': [row['render'] for row in data['reports']],
                                 'poster_render': '.build/qa-estadistica-resumen-fusion/infografia-fusionada.png', 'checks': ['Legibilidad', 'Índice paginado', 'Notas IA', 'Tablas íntegras', 'Sin recortes ni solapamientos']}
        MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'passed': True, 'visual_review_completed': True, 'reports': len(data['reports'])}))
        return
    from validar_unidad_1 import validate_investigation
    investigation = validate_investigation(promote=args.promote)
    poster = poster_checks()
    reports = []
    for tag, suffix in SPECS:
        if tag == 'act2':
            complete = next(row for row in investigation['versions'] if row['version'] == 'completo')
            reports.append({
                'tag': tag, 'file': complete['file'], 'pages': complete['pages'], 'sha256': complete['sha256'],
                'cover_preserved': complete['cover_preserved'],
                'summary_toc_declaration': complete['summary_toc_declaration'],
                'three_acts': complete['three_acts'],
                'bounds_and_log_passed': complete['bounds_log_citations_passed'],
                'render': complete['render'], 'source': investigation['source'],
                'delivery_file': investigation['delivery'], 'delivery_pages': investigation['delivery_pages'],
                'delivery_is_root_report': False, 'dedicated_validator': investigation['dedicated_validator'],
            })
            continue
        name = STEM + suffix
        source = SUBJECT / (name + '.tex')
        build = ROOT / '.build/latex' / ('estadistica-' + tag) / (name + '.pdf')
        path = build if args.promote else SUBJECT / (name + '.pdf')
        assert path.stat().st_mtime >= source.stat().st_mtime, (tag, 'stale')
        assert len(re.findall(r'\\section\{', source.read_text(encoding='utf-8'))) == 3
        log = build.with_suffix('.log').read_text(encoding='utf-8', errors='replace')
        assert not re.search(r'Overfull|Underfull|Missing character|Citation .*undefined|There were undefined|^!', log, re.M), tag
        if args.promote:
            preserve_pages(path, suffix)
        with pymupdf.open(path) as document, pymupdf.open(BACKUP / (name + '.pdf')) as old:
            assert hashlib.sha256(document[0].get_pixmap().samples).digest() == hashlib.sha256(old[0].get_pixmap().samples).digest(), (tag, 'cover')
            body = '\n'.join(page.get_text() for page in list(document)[1:])
            for phrase in ['Resumen', 'Tabla de contenido', 'Introducción', 'Conclusiones', 'Referencias', 'corrección y organización', 'El autor declara haber realizado y validado']:
                assert norm(phrase) in norm(body), (tag, phrase)
            assert 'Nova' not in body
            for page in list(document)[1:]:
                check_bounds(page)
            toc = build.with_suffix('.toc').read_text(encoding='utf-8')
            assert len(re.findall(r'\\contentsline \{section\}', toc)) >= 3
            assert all(f'numberline {{{i}}}' in toc for i in [1, 2, 3]), (tag, 'real_toc')
            if tag == 'act3':
                assert len(document) == 5
                for page in list(document)[1:]:
                    for block in page.get_text('dict')['blocks']:
                        for line in block.get('lines', []):
                            for span in line['spans']:
                                if span['text'].strip() and span['bbox'][3] < page.rect.height - 50:
                                    assert 'Arial' in span['font'], (tag, span['text'])
                                    assert abs(span['size'] - 12 * 72 / 72.27) < .08 or span['text'].strip() in ['1', 'a', 'ª'], (tag, span)
            if tag == 'act1':
                with pymupdf.open(POSTER) as visual:
                    pages = [pg for pg in document if abs(pg.rect.width - visual[0].rect.width) < 1]
                    assert len(pages) == 1 and hashlib.sha256(pages[0].get_pixmap().samples).digest() == hashlib.sha256(visual[0].get_pixmap().samples).digest()
            if tag == 'act5':
                notes = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion/notas-estadistica-aplicada-para-la-administracion/cuestionario-2026-10-24'
                questions = json.loads((notes / 'respuestas-validadas.json').read_text(encoding='utf-8-sig'))['preguntas']
                assert [q['numero'] for q in questions] == list(range(1, 21))
                for q in questions:
                    if q['numero'] != 7:
                        assert norm(q['pregunta']) in norm(body), q['numero']
                    else:
                        assert norm('el valor Z representa') in norm(body)
                    assert norm(q['respuesta']) in norm(body) and q['respuesta'] in q['opciones']
            rendered = render(document, tag)
            pages = len(document)
        destination = SUBJECT / (name + '.pdf')
        if args.promote:
            shutil.copy2(path, destination)
        reports.append({'tag': tag, 'file': destination.relative_to(SUBJECT).as_posix(), 'pages': pages, 'sha256': sha(destination),
                        'cover_preserved': True, 'summary_toc_declaration': True, 'three_acts': True, 'bounds_and_log_passed': True, 'render': rendered})
    deliveries = []
    for number, name in enumerate(DELIVERY_NAMES, 1):
        if number == 2:
            source = SUBJECT / investigation['delivery']
        else:
            source = POSTER if number == 1 else SUBJECT / (STEM + f'Actividad-{number}.pdf')
        destination = SUBJECT / 'entregas-estadistica-aplicada-para-la-administracion' / name
        if args.promote and source.resolve() != destination.resolve():
            shutil.copy2(source, destination)
        assert sha(source) == sha(destination)
        row = {'activity': number, 'file': destination.relative_to(SUBJECT).as_posix(), 'sha256': sha(destination)}
        if number == 2:
            assert row['sha256'] == investigation['delivery_sha256']
            row.update({'pages': 5, 'source': investigation['delivery_source'],
                        'content_source': investigation['delivery_content_source'], 'is_root_report': False})
        deliveries.append(row)
    from validar_unidad_2 import numerical_checks
    numerical = numerical_checks()
    data = {'validated_at_utc': datetime.now(timezone.utc).isoformat(), 'passed': True, 'visual_review_completed': False,
            'scope': 'Siete informes y fusión de infografía; revisión posterior autorizada por el usuario el 25/10/2026.',
            'reports': reports, 'infographic': poster, 'deliveries': deliveries, 'numerical_checks_passed': True,
            'investigation_versions': investigation['versions'],
            'investigation_validation_manifest': investigation['dedicated_manifest'],
            'numerical_evidence': numerical, 'platform_submission': False}
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'pages': {r['tag']: r['pages'] for r in reports}, 'manifest': str(MANIFEST)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
