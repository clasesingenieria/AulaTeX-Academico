import base64
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urljoin, urlsplit, urlunsplit

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright


SUBJECT = Path(__file__).resolve().parents[1]
ROOT = SUBJECT.parents[2]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.itesca_activity_portal import (
    BASE_URL, _browser_resolver_args, _get_credentials, _identity_variants,
    _same_host_url, _sanitize,
)
from aulaTEX.aulatex.planning_layout import generate_plans, subject_layout


COURSE_URL = BASE_URL + '/course/view.php?id=209'
STAMP = '2026-10-18'
LAYOUT = subject_layout(SUBJECT)
OUTPUT = LAYOUT['notes'] / 'materiales-aula' / STAMP
FILES = OUTPUT / 'archivos'


def clean_url(value, base=COURSE_URL):
    value = urljoin(base, value)
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password:
        return None
    if re.search(r'(?i)(sesskey|token|signature|authkey|password|key)=', parsed.query):
        return None
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, parsed.query, ''))


def fetch(page, url):
    _same_host_url(url)
    return page.evaluate('''async url => {
        const response = await fetch(url, {credentials: 'same-origin'});
        if (!response.ok) return {status: response.status};
        if (new URL(response.url).origin !== location.origin) return {status: 0};
        const limit = 50 * 1024 * 1024;
        const declared = Number(response.headers.get('content-length') || 0);
        if (declared > limit) return {status: 413};
        const reader = response.body.getReader();
        const chunks = []; let size = 0;
        while (true) {
            const {done, value} = await reader.read(); if (done) break;
            size += value.length;
            if (size > limit) {await reader.cancel(); return {status: 413};}
            chunks.push(value);
        }
        const type = response.headers.get('content-type') || '';
        const blob = new Blob(chunks);
        if (type.includes('text/html'))
            return {status: response.status, type, html: await blob.text()};
        let binary = '';
        for (const chunk of chunks)
            for (let offset = 0; offset < chunk.length; offset += 8192)
                binary += String.fromCharCode(...chunk.subarray(offset, offset + 8192));
        return {status: response.status, type, data: btoa(binary)};
    }''', url)


def download_record(payload, identifier, label):
    data = base64.b64decode(payload['data'], validate=True)
    digest = hashlib.sha256(data).hexdigest()
    suffix = '.pdf' if data.startswith(b'%PDF-') else Path(unquote(urlsplit(label).path)).suffix.lower()
    if not re.fullmatch(r'\.[a-z0-9]{1,6}', suffix):
        suffix = '.bin'
    path = FILES / f'{identifier}-{digest[:12]}{suffix}'
    path.write_bytes(data)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == digest
    record = {'path': path.relative_to(SUBJECT).as_posix(), 'bytes': len(data), 'sha256': digest, 'content_type': payload['type']}
    if suffix == '.pdf':
        import pymupdf
        with pymupdf.open(path) as document:
            text = '\n\n'.join(f'Pagina {index + 1}\n{page.get_text()}' for index, page in enumerate(document))
            record['pages'] = len(document)
        path.with_suffix('.txt').write_text(text, encoding='utf-8')
    return record


def prepare_indexes():
    inventory = json.loads((OUTPUT / 'inventario.json').read_text(encoding='utf-8'))
    rows = ['# Actividades y fechas verificadas', '', 'Consulta de solo lectura del 18/10/2026. Las fechas son las publicadas por Moodle; no se iniciaron intentos ni se enviaron trabajos.', '', '| Unidad | Actividad | Fechas publicadas | Planeación |', '| --- | --- | --- | --- |']
    for module in inventory['modules']:
        if module['kind'] not in ('assign', 'quiz', 'forum') or not module.get('requirements'):
            continue
        dates = module.get('dates_and_status', '').split('\n')[0]
        dates = dates.replace('|', '/').replace('\n', ' ')
        rows.append(f"| {module['section']} | {module['title']} | {dates or 'Sin fecha identificada'} | [{module['id']}](planeacion-modulo-{module['id']}.md) |")
    rows.extend(['', '## Diferencias que requieren atención', '', 'La página de especificaciones (módulo 1732) lista evidencias que no siempre coinciden en cantidad con los módulos visibles. En particular, las unidades 5 y 7 incluyen evaluación en las especificaciones, pero no se observó un módulo de cuestionario separado en sus pestañas. No se creó una actividad ni una fecha inferida. Conservar ambas fuentes y confirmar con la docente cuando corresponda.', '', 'Las rúbricas se preservan literalmente en las evidencias. Sus repeticiones o descripciones inconsistentes no se corrigen como si fueran instrucciones originales.'])
    (LAYOUT['plans'] / 'INDICE-ACTIVIDADES.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    rows = ['# Materiales originales del aula', '', 'Son apoyos e instrucciones de curso, no autoridad conceptual para entregables. No se redistribuyen públicamente por el solo hecho de estar disponibles para el estudiante.', '', '| Módulo o recurso | Archivo | Tamaño | SHA-256 |', '| --- | --- | --- | --- |']
    seen = set()
    for record in inventory['files']:
        path = SUBJECT / record['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest() == record['sha256']
        if record['path'] in seen:
            continue
        seen.add(record['path'])
        relative = Path(os.path.relpath(path, OUTPUT)).as_posix()
        rows.append(f"| {record['source'].split('/')[-1]} | [{path.name}]({relative}) | {record['bytes']} | `{record['sha256']}` |")
    rows.extend(['', f"Registros de descarga: {len(inventory['files'])}. Contenidos distintos por SHA-256: {len({record['sha256'] for record in inventory['files']})}. Archivos conservados con ruta única: {len(seen)}.", '', '[Inventario completo](inventario.json). Los PDF tienen extracción de texto junto al original; el número de página se conserva como localizador. Los enlaces externos fueron registrados, no implica descarga ni acceso a sus destinos. No se recuperaron grabaciones de videoconferencia.'])
    (OUTPUT / 'README.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    print(json.dumps({'indexes_prepared': True, 'download_records_verified': len(inventory['files']), 'distinct_hashes': len({record['sha256'] for record in inventory['files']})}, ensure_ascii=True))


def main():
    if (OUTPUT / 'inventario.json').exists():
        raise FileExistsError('La extracción fechada ya existe; conservarla y elegir otra revisión')
    load_dotenv(ROOT / 'aulaTEX/aulatex.env', override=False)
    credentials = _get_credentials(ROOT)
    FILES.mkdir(parents=True, exist_ok=True)
    inventory = {'course_id': 209, 'code': 'GGEA01', 'url': COURSE_URL, 'read_only': True,
                 'retrieved_at_utc': datetime.now(timezone.utc).isoformat(), 'sections': [], 'modules': [], 'files': [], 'limitations': []}
    modules = {}
    file_urls = {}
    with sync_playwright() as engine:
        browser = engine.chromium.launch(headless=True, args=_browser_resolver_args()[0])
        try:
            context = browser.new_context(service_workers='block')
            context.set_default_timeout(45000)
            def limit_origin(route):
                try:
                    _same_host_url(route.request.url)
                except Exception:
                    route.abort()
                    return
                route.continue_()
            context.route('**/*', limit_origin)
            page = context.new_page()
            page.goto(BASE_URL + '/login/index.php')
            page.locator('#username').fill(credentials['username'])
            page.locator('#password').fill(credentials['password'])
            page.locator('#loginbtn').click()
            page.goto(COURSE_URL)
            if '/login/' in page.url:
                raise RuntimeError('authentication_failed')
            names = page.locator('.usermenu .usertext,.usermenu .userfullname').all_text_contents()
            identities = _identity_variants(credentials['username'], names)
            del credentials
            section_links = page.locator('#region-main a[href*="section="]').evaluate_all('els=>els.map(el=>({title:el.innerText,url:el.href}))')
            sections = {clean_url(link['url']): link['title'] for link in section_links}
            assert len(sections) == 9
            for url, title in sections.items():
                page.goto(url, wait_until='networkidle')
                section_id = parse_qs(urlsplit(url).query)['section'][0]
                main = page.locator('#region-main')
                text = _sanitize(main.inner_text(), identities)
                path = OUTPUT / f'seccion-{section_id}.txt'
                path.write_text(text, encoding='utf-8')
                inventory['sections'].append({'id': section_id, 'title': title, 'url': url, 'evidence': path.relative_to(SUBJECT).as_posix()})
                links = main.locator('a[href]').evaluate_all('els=>els.map(el=>({title:el.innerText,url:el.href}))')
                for link in links:
                    target = clean_url(link['url'])
                    if not target:
                        continue
                    match = re.search(r'/mod/(assign|quiz|resource|page|folder|url|book|forum)/view.php', target)
                    if match and urlsplit(target).netloc == urlsplit(BASE_URL).netloc:
                        identifier = parse_qs(urlsplit(target).query).get('id', [''])[0]
                        if identifier.isdigit():
                            modules.setdefault(identifier, {'id': identifier, 'title': ' '.join(link['title'].split()), 'kind': match[1], 'url': target, 'section': title})
                    if '/pluginfile.php/' in target:
                        file_urls.setdefault(target, f'seccion-{section_id}')
            for identifier, module in modules.items():
                try:
                    payload = fetch(page, module['url'])
                    module['http_status'] = payload['status']
                    if payload['status'] != 200:
                        inventory['limitations'].append({'id': identifier, 'reason': 'http_or_size_limit', 'status': payload['status']})
                    elif 'data' in payload:
                        record = download_record(payload, identifier, module['url'])
                        inventory['files'].append(dict(record, source=module['url']))
                        module['file'] = record['path']
                    else:
                        soup = BeautifulSoup(payload['html'], 'html.parser')
                        main = soup.select_one('#region-main') or soup
                        intro = main.select_one('#intro')
                        content = intro if module['kind'] == 'forum' else main
                        text = _sanitize(content.get_text('\n', strip=True) if content else '', identities)
                        path = OUTPUT / f'modulo-{identifier}.txt'
                        path.write_text(text, encoding='utf-8')
                        module['evidence'] = path.relative_to(SUBJECT).as_posix()
                        module['requirements'] = _sanitize(intro.get_text('\n', strip=True), identities) if intro else text
                        module['links'] = []
                        for element in main.select('a[href], iframe[src], object[data], embed[src], source[src]'):
                            value = element.get('href') or element.get('src') or element.get('data')
                            target = clean_url(value, module['url'])
                            if not target:
                                continue
                            if '/pluginfile.php/' in target and not re.search(r'assignsubmission|/user/|draftfile', target):
                                file_urls.setdefault(target, identifier)
                            elif urlsplit(target).netloc != urlsplit(BASE_URL).netloc:
                                module['links'].append({'title': element.get_text(' ', strip=True), 'url': target})
                        dates = main.select('[data-region="activity-dates"], .activity-dates, .quizinfo, .submissionstatustable')
                        module['dates_and_status'] = _sanitize('\n'.join(block.get_text(' ', strip=True) for block in dates), identities)
                except Exception as error:
                    module['error_type'] = type(error).__name__
                    inventory['limitations'].append({'id': identifier, 'reason': type(error).__name__})
                inventory['modules'].append(module)
                print(json.dumps({'module': identifier, 'kind': module['kind'], 'status': module.get('http_status'), 'error_type': module.get('error_type')}, ensure_ascii=True), flush=True)
            for url, identifier in file_urls.items():
                try:
                    payload = fetch(page, url)
                    if payload['status'] == 200 and 'data' in payload:
                        inventory['files'].append(dict(download_record(payload, identifier, url), source=url))
                    else:
                        inventory['limitations'].append({'source': url, 'reason': 'file_unavailable', 'status': payload['status']})
                except Exception as error:
                    inventory['limitations'].append({'source': url, 'reason': type(error).__name__})
        finally:
            browser.close()
    (OUTPUT / 'inventario.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    activities = [module for module in inventory['modules'] if module['kind'] in ('assign', 'quiz', 'forum') and module.get('requirements')]
    model = {'course': {'id': 209, 'code': 'GGEA01', 'name': 'Estadística aplicada para la administración', 'url': COURSE_URL},
             'retrieved_at_utc': inventory['retrieved_at_utc'], 'mode': 'extraccion_autenticada_sin_intentos_ni_envios', 'activities': activities}
    source = OUTPUT / 'modelo-planeaciones.json'
    source.write_text(json.dumps(model, ensure_ascii=False, indent=2), encoding='utf-8')
    artifacts = generate_plans(SUBJECT, source)
    print(json.dumps({'sections': len(sections), 'modules': len(modules), 'files': len(inventory['files']), 'activities': len(activities), 'planning_artifacts': len(artifacts), 'limitations': inventory['limitations']}, ensure_ascii=True), flush=True)


if __name__ == '__main__':
    try:
        if sys.argv[1:] == ['--indices']:
            prepare_indexes()
        else:
            main()
    except Exception as error:
        print(json.dumps({'error_type': type(error).__name__}, ensure_ascii=True))
        raise SystemExit(1)