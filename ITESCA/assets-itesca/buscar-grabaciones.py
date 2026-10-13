from datetime import datetime, timezone
import json
from pathlib import Path
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.config import load_aulatex_env
from aulaTEX.aulatex.itesca_activity_portal import _get_credentials, _browser_resolver_args, BASE_URL
from playwright.sync_api import sync_playwright


def import_sharepoint_recording(source, session, expected_bytes):
    shared = runpy.run_path(str(ROOT / 'UCNL/assets-ucnl/descargar-transcribir-grabaciones.py'))
    if not source.is_file() or source.suffix.lower() != '.mp4' or source.stat().st_size != expected_bytes:
        raise RuntimeError('Archivo local no coincide con la descarga verificada')
    duration = shared['probe'](source)
    reference = ROOT / 'ITESCA/maestria-en-gestion-administrativa/plan-de-negocios-mga/referencias-plan-de-negocios'
    control = reference / 'notas-plan-de-negocios/materiales-generales/control-grabaciones'
    folder = reference / 'grabaciones-plan-de-negocios'
    control.mkdir(parents=True, exist_ok=True)
    folder.mkdir(parents=True, exist_ok=True)
    title = shared['clean_name'](source.stem)
    name = f'ITESCA - PLAN-DE-NEGOCIOS - {session} - Fecha no indicada - {title}'
    video, subtitle = folder / (name + '.mp4'), folder / (name + '.srt')
    source_hash = shared['digest'](source)
    if video.exists():
        if shared['digest'](video) != source_hash:
            raise RuntimeError('Existe un MP4 diferente; no se sobrescribe')
    else:
        with video.open('xb') as destination, source.open('rb') as original:
            shutil.copyfileobj(original, destination)
    if shared['digest'](video) != source_hash:
        raise RuntimeError('Hash de copia no coincide con el original')
    output = control / (session + '-procedencia.json')
    previous = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    record = {**previous, 'sesion': session, 'materia': 'plan-de-negocios', 'titulo_fuente': source.stem, 'fecha_sesion': None, 'origen_aula': BASE_URL + '/course/view.php?id=213', 'dominio_fuente': 'itscajeme.sharepoint.com', 'descarga': 'Original obtenido en navegador autenticado; bytes coinciden con la respuesta del servidor', 'fuente_local_nombre': source.name, 'fuente_local_preservada': True, 'bytes': expected_bytes, 'archivo': video.relative_to(ROOT).as_posix(), 'sha256': source_hash, 'duracion_segundos': duration, 'estado': 'MP4 verificado; SRT pendiente', 'subtitulos_publicados': 'No recuperados del reproductor: pista Shaka vacia en la consulta; no se afirma inexistencia'}
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{session}: MP4 copiado y validado; obteniendo SRT local', flush=True)
    local_subtitle = source.with_suffix('.srt')
    if not subtitle.exists() and local_subtitle.exists():
        cues = list(shared['srt'].parse(local_subtitle.read_text(encoding='utf-8-sig')))
        shared['validate_cues'](cues, duration)
        with subtitle.open('xb') as destination, local_subtitle.open('rb') as original:
            shutil.copyfileobj(original, destination)
        record['transcripcion'] = {'estado': 'SRT local preservado; origen o revision por confirmar', 'sha256': shared['digest'](subtitle), 'segmentos': len(cues)}
    else:
        transcription = shared['transcribe'](video, subtitle, control, duration)
        if transcription['estado'] == 'SRT existente preservado':
            transcription = {**previous.get('transcripcion', {}), **transcription, 'estado': previous.get('transcripcion', {}).get('estado', transcription['estado']), 'preservada_sin_modificar': True}
        record['transcripcion'] = transcription
    record.update(srt=subtitle.relative_to(ROOT).as_posix(), estado='MP4 y SRT verificados; revision humana pendiente')
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return record


def recording_link_bridge(links):
    from http.server import BaseHTTPRequestHandler, HTTPServer

    pending = dict(links)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            name = self.path.removeprefix('/')
            if self.client_address[0] != '127.0.0.1' or name not in pending:
                self.send_error(404)
                return
            payload = json.dumps({'url': pending.pop(name)}).encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, format, *args):
            pass

    server = HTTPServer(('127.0.0.1', 0), Handler)
    server.pending_recordings = pending
    return server


def embedded_media(soup, origin):
    main = soup.select_one('#region-main') or soup
    found = {}
    for source in main.select('video source[src],video[src],iframe[src]'):
        destination = urljoin(origin, source['src'])
        parsed = urlsplit(destination)
        title = unquote(parsed.path.rsplit('/', 1)[-1])
        if parsed.hostname == urlsplit(BASE_URL).hostname and parsed.path.lower().endswith('.mp4'):
            video = source if source.name == 'video' else source.find_parent('video')
            tracks = [{'url': urljoin(origin, track['src']), 'language': track.get('srclang', '')} for track in video.select('track[src]')] if video else []
            kind = 'sesion_local' if re.search(r'sesi.n de arranque', title, re.I) else 'apoyo_local'
            found[(parsed.hostname, parsed.path)] = {'title': title, 'url': destination, 'origin': origin, 'kind': kind, 'tracks': tracks}
        elif parsed.hostname in ('www.youtube.com', 'www.youtube-nocookie.com') and '/embed/' in parsed.path:
            identity = parsed.path.rsplit('/', 1)[-1]
            if re.fullmatch(r'[\w-]{11}', identity) and identity != 'videoseries':
                found[('youtube', identity)] = {'title': 'Video incrustado de apoyo; no sesion acreditada', 'url': destination, 'origin': origin, 'kind': 'apoyo_youtube', 'video_id': identity}
    return list(found.values())


def invalid_recording_reason(value):
    decoded = value
    for _ in range(3):
        decoded = unquote(decoded)
    if re.search(r'gracias\s+por\s+la\s+entrega\s+de\s+la\s+evidencia', decoded, re.I):
        return 'Texto de retroalimentacion pegado como enlace; no hay URL de grabacion recuperable'
    return 'Enlace malformado o dominio inesperado; no abierto'


def sharepoint_recording_target(value):
    parsed = urlsplit(value)
    hosts = ('itscajeme.sharepoint.com', 'itscajeme-my.sharepoint.com')
    if parsed.scheme == 'https' and parsed.hostname in hosts:
        return value
    if parsed.scheme == 'https' and parsed.hostname == 'teams.microsoft.com':
        targets = parse_qs(parsed.query).get('fileUrl', [])
        if len(targets) == 1:
            target = urlsplit(targets[0])
            if target.scheme == 'https' and target.hostname in hosts and target.path.lower().endswith('.mp4'):
                return targets[0]
    return None


def browser_download(page, url, destination):
    if urlsplit(url).hostname != urlsplit(BASE_URL).hostname:
        raise RuntimeError('Descarga local fuera del dominio autorizado')
    with page.expect_download(timeout=180000) as event:
        page.evaluate('url=>{const anchor=document.createElement("a");anchor.href=url;anchor.download="medio";document.body.appendChild(anchor);anchor.click();anchor.remove()}', url)
    download = event.value
    download.save_as(str(destination))
    return download


def download_local_session(page, link, slug):
    shared = runpy.run_path(str(ROOT / 'UCNL/assets-ucnl/descargar-transcribir-grabaciones.py'))
    reference = ROOT / f'ITESCA/maestria-en-gestion-administrativa/{slug}-mga/referencias-{slug}'
    control = reference / f'notas-{slug}/materiales-generales/control-grabaciones'
    control.mkdir(parents=True, exist_ok=True)
    folder = reference / f'grabaciones-{slug}'
    name = f'ITESCA - {slug.upper()} - Sesion de arranque - Fecha no indicada - Presentacion'
    video, subtitle = folder / (name + '.mp4'), folder / (name + '.srt')
    output = control / 'sesion-arranque-procedencia.json'
    previous = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
    record = {**previous, 'nombre': 'Sesion de arranque', 'materia': slug, 'origen': link['origin'], 'fuente_nombre': link['title'], 'fecha_sesion': None, 'enlace_privado_persistido': False}
    if not video.exists():
        page.goto(link['origin'], wait_until='domcontentloaded')
        if '/login/' in urlsplit(page.url).path:
            raise RuntimeError('Sesion Moodle caducada antes de descargar')
        with tempfile.TemporaryDirectory(prefix='itesca-grabacion-', dir=ROOT / 'tmp') as temporary:
            source = Path(temporary) / 'grabacion.mp4'
            download = browser_download(page, link['url'], source)
            duration = shared['probe'](source)
            folder.mkdir(parents=True, exist_ok=True)
            if video.exists():
                raise RuntimeError('El destino aparecio durante la descarga; no se sobrescribe')
            shutil.move(str(source), str(video))
            download.delete()
    duration = shared['probe'](video)
    record.update(archivo=video.relative_to(ROOT).as_posix(), sha256=shared['digest'](video), duracion_segundos=duration, estado='MP4 validado; SRT pendiente')
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'{slug}: MP4 de arranque validado; comprobando subtitulos', flush=True)
    caption = None
    if not subtitle.exists() and link['tracks']:
        page.goto(link['origin'], wait_until='domcontentloaded')
        for track in link['tracks']:
            if track['language'] and not track['language'].startswith('es'):
                continue
            try:
                with tempfile.TemporaryDirectory(prefix='itesca-subtitulos-', dir=ROOT / 'tmp') as temporary:
                    extension = '.srt' if urlsplit(track['url']).path.lower().endswith('.srt') else '.vtt'
                    source = Path(temporary) / ('original' + extension)
                    download = browser_download(page, track['url'], source)
                    generated = source if extension == '.srt' else Path(temporary) / 'convertido.srt'
                    if extension != '.srt':
                        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(source), str(generated)], capture_output=True, check=True)
                    cues = list(shared['srt'].parse(generated.read_text(encoding='utf-8-sig')))
                    shared['validate_cues'](cues, duration)
                    original = control / (name + ' - subtitulos-originales' + extension)
                    if not original.exists():
                        shutil.copy2(source, original)
                    with subtitle.open('x', encoding='utf-8') as stream:
                        stream.write(shared['srt'].compose(cues, reindex=False))
                    caption = {'estado': 'Pista publicada en el reproductor; autoria o automatismo no indicados; revision pendiente', 'segmentos': len(cues), 'sha256': shared['digest'](subtitle)}
                    download.delete()
                break
            except FileExistsError:
                raise RuntimeError('SRT existente; no se sobrescribe')
            except Exception:
                continue
    record['pistas_subtitulos_aula'] = len(link['tracks'])
    try:
        transcription = caption or shared['transcribe'](video, subtitle, control, duration)
        if transcription['estado'] == 'SRT existente preservado':
            record['transcripcion'] = {**previous.get('transcripcion', {}), **transcription, 'estado': previous.get('transcripcion', {}).get('estado', transcription['estado']), 'preservada_sin_modificar': True}
        else:
            record['transcripcion'] = transcription
        record.update(srt=subtitle.relative_to(ROOT).as_posix(), estado='MP4 y SRT validados; revision humana pendiente')
    except Exception as error:
        record.update(estado='MP4 preservado; transcripcion no completada', clase_error=type(error).__name__)
        if isinstance(error, RuntimeError) and re.fullmatch(r'[a-zA-Z_]+', str(error)):
            record['motivo'] = str(error)
    output.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
    return record


def collect_recording_links(page, course_url):
    from bs4 import BeautifulSoup

    pending = [(course_url, '')]
    seen = set()
    found = {}
    pages = []
    host = urlsplit(BASE_URL).hostname
    while pending and len(seen) < 100:
        url, label = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        try:
            response = page.evaluate('async url=>{const response=await fetch(url,{redirect:"manual"});const type=response.headers.get("content-type")||"";return {status:response.status,type,text:response.status===200&&type.includes("text/html")?await response.text():""}}', url)
        except Exception as error:
            pages.append({'url': url, 'estado': 'Consulta no completada', 'clase_error': type(error).__name__})
            continue
        pages.append({'url': url, 'http': response['status']})
        if response['status'] != 200 or 'text/html' not in response['type']:
            continue
        soup = BeautifulSoup(response['text'], 'html.parser')
        main = soup.select_one('#region-main') or soup
        for anchor in main.select('a[href]'):
            destination = urljoin(url, anchor['href'])
            title = anchor.get_text(' ', strip=True)
            parsed = urlsplit(destination)
            query = parse_qs(parsed.query)
            if re.search('grabaci|grabada|recording', title, re.I):
                found[destination] = {'title': title, 'url': destination, 'origin': url}
            if parsed.hostname != host:
                continue
            safe = None
            if re.fullmatch('/mod/(forum|page|url|resource)/view.php', parsed.path) and query.get('id', [''])[0].isdigit():
                safe = BASE_URL + parsed.path + '?id=' + query['id'][0]
            elif parsed.path == '/mod/forum/discuss.php' and query.get('d', [''])[0].isdigit():
                safe = BASE_URL + parsed.path + '?d=' + query['d'][0]
            if safe and safe not in seen:
                pending.append((safe, title))
        for media in embedded_media(soup, url):
            parsed = urlsplit(media['url'])
            key = parsed.hostname + parsed.path
            if key not in found:
                found[key] = media
    return list(found.values()), pages, bool(pending)


def main():
    if '--import-sharepoint' in sys.argv:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('--import-sharepoint', type=Path, required=True)
        parser.add_argument('--session', choices=('S1', 'S2', 'S3'), required=True)
        parser.add_argument('--expected-bytes', type=int, required=True)
        arguments = parser.parse_args()
        print(json.dumps(import_sharepoint_recording(arguments.import_sharepoint, arguments.session, arguments.expected_bytes), ensure_ascii=True), flush=True)
        return
    load_aulatex_env()
    credentials = _get_credentials(ROOT)
    args, _ = _browser_resolver_args()
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True, args=args)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(30000)
        page.goto(BASE_URL + '/login/index.php', wait_until='domcontentloaded')
        page.locator('#username').fill(credentials['username'])
        page.locator('#password').fill(credentials['password'])
        page.locator('#loginbtn').click()
        page.wait_for_load_state('networkidle')
        del credentials
        if '/login/' in urlsplit(page.url).path:
            raise RuntimeError('Acceso Moodle no completado')
        if '--serve-links' in sys.argv:
            from bs4 import BeautifulSoup
            link_course = 372 if '--fundamentos-only' in sys.argv else 213
            expected_sessions = {'S2', 'S3', 'S4'} if link_course == 372 else {'S1', 'S2', 'S3'}
            page.goto(BASE_URL + f'/course/view.php?id={link_course}', wait_until='networkidle')
            soup = BeautifulSoup(page.content(), 'html.parser')
            links = {}
            for anchor in soup.select('.course-content a[href]'):
                match = re.fullmatch(r'Grabaci.n\s+(?:sesi.n\s+)?S?([1-4])', anchor.get_text(' ', strip=True), re.I)
                target = sharepoint_recording_target(anchor['href'])
                if match and target and 'S' + match.group(1) in expected_sessions:
                    links['S' + match.group(1)] = target
            if set(links) != expected_sessions:
                raise RuntimeError('No se localizaron las tres grabaciones esperadas')
            context.close()
            browser.close()
            with recording_link_bridge(links) as server:
                server.timeout = 300
                print(json.dumps({'puerto_local': server.server_port, 'sesiones': sorted(links), 'enlaces_persistidos': False}), flush=True)
                while server.pending_recordings:
                    server.handle_request()
            return
        if '--fundamentos-only' in sys.argv:
            courses = [(372, 'fundamentos-de-gestion-administrativa')]
        elif '--seminario-only' in sys.argv:
            courses = [(215, 'seminario-i')]
        else:
            courses = [(213, 'plan-de-negocios'), (215, 'seminario-i')]
        for course, slug in courses:
            course_url = BASE_URL + f'/course/view.php?id={course}'
            page.goto(course_url, wait_until='networkidle')
            if not page.locator('.course-content').count():
                raise RuntimeError('Curso no accesible; no se infiere ausencia de grabaciones')
            recording_links, pages, limited = collect_recording_links(page, course_url)
            record = {'consulta_utc': datetime.now(timezone.utc).isoformat(), 'curso': course, 'enlace_curso': course_url, 'sin_envios_ni_reuniones': True, 'grabaciones': [], 'medios_apoyo': [], 'paginas_consultadas': pages, 'limite_alcanzado': limited, 'alcance': 'Curso y enlaces HTML accesibles de avisos, foros y paginas, con medios incrustados; no acredita ausencia en adjuntos o recursos restringidos.'}
            for link in recording_links:
                item = {'nombre': re.sub(r'https?://\S+', '[enlace omitido]', link['title']), 'origen': link['origin'], 'enlace_privado_persistido': False}
                if link.get('kind', '').startswith('apoyo_'):
                    item.update(estado='Video de apoyo o instrucciones; no se conto como sesion grabada', tipo=link['kind'])
                    if link.get('video_id'):
                        item['video_id'] = link['video_id']
                    record['medios_apoyo'].append(item)
                    continue
                if link.get('kind') == 'sesion_local':
                    try:
                        item = download_local_session(page, link, slug)
                    except Exception as error:
                        item.update(estado='Medio local no completado; conservar existentes', clase_error=type(error).__name__)
                    record['grabaciones'].append(item)
                    continue
                target = sharepoint_recording_target(link['url'])
                parsed = urlsplit(link['url'])
                if not target and (parsed.scheme != 'https' or parsed.hostname != 'cursos3.e-itesca.edu.mx'):
                    item['estado'] = invalid_recording_reason(link['url'])
                    record['grabaciones'].append(item)
                    continue
                try:
                    if target and parsed.hostname == 'teams.microsoft.com':
                        item['tipo_enlace'] = 'Resumen Teams con fileUrl publicado; no reunion en vivo'
                    page.goto(target or link['url'], wait_until='domcontentloaded')
                    page.wait_for_load_state('networkidle', timeout=20000)
                    host = urlsplit(page.url).hostname
                    item['dominio_destino'] = host if host in ('itscajeme.sharepoint.com', 'login.microsoftonline.com', 'login.microsoft.com', 'cursos3.e-itesca.edu.mx') else 'otro dominio'
                    item['titulo_pagina'] = page.title()
                    item['medios_cargados'] = page.locator('video,audio').count()
                    item['descarga_visible'] = bool(page.get_by_role('button', name=re.compile('Download|Descargar', re.I)).count() or page.locator('a[download]').count())
                    body = page.locator('body').inner_text()
                    if host in ('login.microsoftonline.com', 'login.microsoft.com') or re.search('Sign in to your account|Iniciar sesi.n|Escriba su correo|Enter your email', body, re.I):
                        item['estado'] = 'Requiere autenticacion Microsoft; no se inicio sesion externa'
                    elif item['medios_cargados']:
                        item['estado'] = 'Reproductor localizado; no descargado ni transcrito'
                    elif re.search('access denied|acceso denegado|permission|permiso|no existe|not found', body, re.I):
                        item['estado'] = 'Acceso o existencia no confirmado; revisar permisos'
                    else:
                        item['estado'] = 'Pagina abierta; reproduccion y descarga no confirmadas'
                except Exception as error:
                    item['estado'] = 'Consulta externa no completada'
                    item['clase_error'] = type(error).__name__
                record['grabaciones'].append(item)
            folder = ROOT / f'ITESCA/maestria-en-gestion-administrativa/{slug}-mga/referencias-{slug}/notas-{slug}/materiales-generales/control-grabaciones'
            folder.mkdir(parents=True, exist_ok=True)
            stamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
            (folder / f'inventario-busqueda-{stamp}.json').write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(record, ensure_ascii=True))
        context.close()
        browser.close()


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(json.dumps({'estado': 'Busqueda no completada', 'clase_error': type(error).__name__}))
        raise SystemExit(1) from None