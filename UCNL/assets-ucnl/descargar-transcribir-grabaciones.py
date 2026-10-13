from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, unquote, urljoin, urlsplit

import srt
import yt_dlp
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from aulaTEX.aulatex.config import load_aulatex_env
from aulaTEX.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path

HOST = 'https://licenciatura.ucnl.edu.mx'
COURSES = [(20297, 'administracion-ii', 'ADM2'), (20322, 'macroeconomia', 'MACRO'), (20328, 'matematicas-ii', 'MAT2'), (20308, 'contabilidad-ii', 'CONT2'), (20311, 'derecho-constitucional', 'CONST'), (20336, 'ingles-ii', 'ING2')]
ENGINE = Path(os.environ['APPDATA']) / 'Subtitle Edit/SpeechToText/Purfview-Faster-Whisper-XXL/faster-whisper-xxl.exe'
REPORT = Path(__file__).with_name('resultado-grabaciones-2026-10-12.json')


def deno_runtime():
    executable = shutil.which('deno')
    config = Path(os.environ['APPDATA']) / 'yt-dlp/config'
    if config.exists():
        match = re.search(r'^\s*--js-runtimes\s+"deno:([^"\r\n]+)"\s*$', config.read_text(encoding='utf-8-sig'), re.M)
        if match:
            executable = match.group(1)
    if not executable or not Path(executable).is_file():
        raise RuntimeError('Deno no localizado; configurar --js-runtimes "deno:RUTA" en APPDATA/yt-dlp/config')
    return {'deno': {'path': executable}}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    if not any(item['codec_type'] == 'video' for item in data['streams']) or not any(item['codec_type'] == 'audio' for item in data['streams']):
        raise RuntimeError('video_o_audio_ausente')
    return float(data['format']['duration'])


def video_id(value):
    for _ in range(3):
        value = unquote(value)
    match = re.search(r'(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|live/))([\w-]{11})', value)
    if match:
        return match.group(1)
    return None


def clean_name(value):
    value = re.sub(r'[<>:"/\\|?*\x00-\x1f]', ' ', value)
    return re.sub(r'\s+', ' ', value).strip().rstrip('.')[:90]


def recording_blocks(soup):
    main = soup.select_one('.course-content') or soup.select_one('#region-main') or soup
    markers = main.find_all(string=re.compile(r'grabaci[o\u00f3]n|clase grabada|sesi[o\u00f3]n grabada', re.I))
    result = []
    seen = set()
    for marker in markers:
        if marker.parent.name in ('script', 'style'):
            continue
        container = marker.parent
        if container.name == 'a' and container.get('href'):
            elements = [container]
        else:
            for _ in range(4):
                if container.name in ('details', 'section', 'body'):
                    break
                if container.select('a[href],iframe[src],video[src],source[src]'):
                    break
                if container.parent is None:
                    break
                container = container.parent
            if container.name in ('details', 'section', 'body'):
                continue
            elements = container.select('a[href],iframe[src],video[src],source[src]')
        week_container = container.find_parent('details')
        week_text = week_container.get_text(' ', strip=True) if week_container else ''
        week = re.search(r'Semana\s+(\d+)', week_text, re.I)
        for element in elements:
            destination = element.get('href') or element.get('src') or ''
            if not destination or destination == '#' or destination in seen:
                continue
            seen.add(destination)
            result.append({'url': destination, 'block': None, 'embedded': True, 'section': 'Semana ' + week.group(1) if week else '', 'rotulo': 'Enlace dentro de bloque de grabacion'})
    return result


def teams_link_kind(value):
    decoded = value
    for _ in range(3):
        decoded = unquote(decoded)
    if re.search(r'/meet/|/meetup-join/|/meeting/join', decoded, re.I):
        return 'Enlace de reunion Teams; no es un archivo de grabacion y no se inicia'
    if re.search(r'meetingrecap|/l/message/|/recap/', decoded, re.I):
        return 'Resumen o mensaje Teams; requiere comprobar acceso y archivo de grabacion'
    return 'Enlace Teams pendiente de identificar; descarga no declarada imposible'


def resource_recordings(page, original_html, course_url):
    from bs4 import BeautifulSoup

    pending = [(course_url, original_html)]
    seen = set()
    recordings = []
    audit = {'solo_lectura': True, 'paginas': [], 'alcance': 'Curso, paginas, URL, recursos HTML y discusiones accesibles; sin evaluaciones ni reuniones. Adjuntos y recursos restringidos no acreditados.'}
    while pending and len(seen) < 100:
        url, soup = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if soup is None:
            try:
                response = page.evaluate('async url=>{const response=await fetch(url,{redirect:"manual"});const type=response.headers.get("content-type")||"";return {status:response.status,type,text:response.status===200&&type.includes("text/html")?await response.text():""}}', url)
            except Exception as error:
                audit['paginas'].append({'origen': url, 'estado': 'Consulta no completada', 'clase_error': type(error).__name__})
                continue
            audit['paginas'].append({'origen': url, 'http': response['status'], 'html': bool(response['text'])})
            if not response['text']:
                continue
            soup = BeautifulSoup(response['text'], 'html.parser')
        else:
            audit['paginas'].append({'origen': url, 'http': 200, 'html': True})
        if soup.select_one('input[type=password]'):
            audit['paginas'][-1]['estado'] = 'Sesion caducada; contenido no inspeccionado'
            continue
        for link in recording_blocks(soup):
            link['url'] = urljoin(url, link['url'])
            link['origin'] = url
            recordings.append(link)
        main = soup.select_one('#region-main') or soup
        for anchor in main.select('a[href]'):
            destination = urljoin(url, anchor['href'])
            parsed = urlsplit(destination)
            query = parse_qs(parsed.query)
            if parsed.hostname != urlsplit(HOST).hostname:
                continue
            safe = None
            if re.fullmatch(r'/mod/(page|resource|url|forum)/view.php', parsed.path) and query.get('id', [''])[0].isdigit():
                safe = HOST + parsed.path + '?id=' + query['id'][0]
            elif parsed.path == '/mod/forum/discuss.php' and query.get('d', [''])[0].isdigit():
                safe = HOST + parsed.path + '?d=' + query['d'][0]
            if safe and safe not in seen:
                pending.append((safe, None))
    audit['limite_alcanzado'] = bool(pending)
    audit['video_ids'] = sorted({identity for link in recordings if (identity := video_id(link['url']))})
    return recordings, audit


def academic_metadata(entry):
    if entry.get('curso') != 20297:
        return {}
    path = ROOT / 'UCNL/licenciatura-en-administracion/administracion-ii-lad/referencias-administracion-ii/notas-administracion-ii/materiales-generales/control-grabaciones/sesiones-por-semana.json'
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding='utf-8'))
    for session in data['sesiones']:
        if session['video_id'] == entry.get('video_id'):
            return {**session, 'materia_nombre': data['materia'], 'fuente_metadata_academica': {'origen': data['origen'], 'consulta': data['consulta'], 'criterio': data['criterio']}}
    return {}


def academic_basename(entry):
    if entry.get('curso') != 20297 or not all(entry.get(key) for key in ('semana', 'fecha_sesion', 'tema_archivo')):
        return None
    return f'Semana {entry["semana"]:02d} - {clean_name(entry["tema_archivo"])} - {entry["fecha_sesion"]} - UCNL ADM2'


class SafeLogger:
    def debug(self, message):
        pass

    def warning(self, message):
        pass

    def error(self, message):
        pass


def download_failure(error):
    message = str(error).lower()
    if 'live event will begin' in message or 'premieres in' in message:
        return 'Emision futura; todavia no es una grabacion disponible; no se inicia la reunion'
    if 'cookie database' in message or 'could not copy' in message:
        return 'Base de cookies del perfil autorizado bloqueada por el navegador'
    if 'decrypt' in message or 'dpapi' in message:
        return 'No fue posible descifrar cookies del perfil autorizado; no se fuerza acceso'
    if 'not a bot' in message or 'sign in' in message:
        return 'YouTube exige inicio de sesion o verificacion humana'
    if 'javascript' in message or 'challenge' in message or 'ejs' in message:
        return 'Resolucion JavaScript/EJS no completada; independiente de autenticacion'
    if 'requested format is not available' in message or 'no video formats found' in message:
        return 'YouTube no ofrece formatos de audio/video descargables a este acceso; no demuestra fallo de Deno'
    if 'private video' in message or 'unavailable' in message or 'this video is not available' in message:
        return 'Video privado o no disponible para este acceso'
    return 'Descarga no completada; mensaje externo omitido para proteger datos de acceso'


def preserve_existing(entry, previous, folder):
    known = previous.get(entry['video_id'], {})
    matches = list(folder.glob(f'*{entry["video_id"]}*.mp4'))
    if known.get('archivo') and (ROOT / known['archivo']).exists():
        matches.append(ROOT / known['archivo'])
    matches = list(dict.fromkeys(matches))
    if len(matches) > 1:
        raise RuntimeError('Varias copias locales del mismo video; no se descarga otra')
    if not matches or not matches[0].with_suffix('.srt').exists():
        return None
    video = matches[0]
    subtitle = video.with_suffix('.srt')
    duration = probe(video)
    cues = list(srt.parse(subtitle.read_text(encoding='utf-8-sig')))
    validate_cues(cues, duration)
    video_hash, subtitle_hash = digest(video), digest(subtitle)
    result = {**known, **entry, 'archivo': video.relative_to(ROOT).as_posix(), 'srt': subtitle.relative_to(ROOT).as_posix(), 'sha256': video_hash, 'duracion_segundos': duration, 'estado': 'Existente preservada; MP4 y SRT revalidados sin acceso a YouTube'}
    result['hash_mp4_coincide_previo'] = video_hash == known.get('sha256') if known.get('sha256') else None
    original_subtitle = known.get('transcripcion', {})
    result['hash_srt_coincide_previo'] = subtitle_hash == original_subtitle.get('sha256') if original_subtitle.get('sha256') else None
    result['transcripcion'] = {**original_subtitle, 'segmentos': len(cues), 'sha256': subtitle_hash, 'preservada_sin_modificar': True}
    if result['hash_srt_coincide_previo'] is False:
        result['transcripcion']['estado'] = 'SRT modificado localmente; preservado, revision del usuario no sobreescrita'
    return result


def recording_language(metadata):
    language = (metadata.get('language') or '').split('-')[0]
    if language:
        return language
    originals = {code.removesuffix('-orig') for code in metadata.get('automatic_captions', {}) if code.endswith('-orig')}
    return next(iter(originals)) if len(originals) == 1 else 'es'


def existing_captions(metadata, output, control, duration, options):
    candidates = []
    preferred = recording_language(metadata)
    for field, source in [('subtitles', 'Autor'), ('automatic_captions', 'Automaticos de YouTube; revision humana pendiente')]:
        for language, formats in metadata.get(field, {}).items():
            if language != preferred and not language.startswith(preferred + '-'):
                continue
            for item in formats:
                if item.get('ext') in ('srt', 'vtt') and not parse_qs(urlsplit(item['url']).query).get('tlang'):
                    candidates.append((source, language, item))
    for source, language, item in candidates:
        try:
            with yt_dlp.YoutubeDL(options) as downloader:
                with downloader.urlopen(item['url']) as response:
                    content = response.read(20_000_001)
            if not content or len(content) > 20_000_000:
                continue
            with tempfile.TemporaryDirectory(prefix='ucnl-captions-', dir=ROOT / 'tmp') as temporary:
                raw = Path(temporary) / ('original.' + item['ext'])
                raw.write_bytes(content)
                generated = raw if item['ext'] == 'srt' else Path(temporary) / 'convertido.srt'
                if item['ext'] != 'srt':
                    subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(raw), str(generated)], capture_output=True, check=True)
                cues = list(srt.parse(generated.read_text(encoding='utf-8-sig')))
                validate_cues(cues, duration)
                original = control / (output.stem + ' - subtitulos-originales.' + item['ext'])
                if not original.exists():
                    shutil.copy2(raw, original)
                with output.open('x', encoding='utf-8') as stream:
                    stream.write(srt.compose(cues, reindex=False))
            return {'estado': source, 'origen': 'Subtitulos accesibles del video', 'idioma': language, 'segmentos': len(cues), 'sha256': digest(output)}
        except FileExistsError:
            raise RuntimeError('SRT existente; no se sobreescribe')
        except Exception:
            continue
    return None


def repair_zero_cues(cues):
    from datetime import timedelta

    repaired = []
    changes = []
    position = 0
    while position < len(cues):
        cue = cues[position]
        if cue.start != cue.end:
            repaired.append(cue)
            position += 1
            continue
        end = cue.start + timedelta(milliseconds=100)
        if position + 1 == len(cues) or end <= cues[position + 1].start:
            changes.append({'indices_originales': [cue.index], 'accion': 'Duracion nula ampliada 100 ms'})
            cue.end = end
            repaired.append(cue)
            position += 1
            continue
        following = position
        while following < len(cues) and cues[following].start == cue.start and cues[following].end == cue.start:
            following += 1
        if following == len(cues) or cues[following].start != cue.start or cues[following].end <= cue.start:
            raise RuntimeError('tiempo_nulo_sin_intervalo_existente')
        group = cues[position:following + 1]
        if repaired and repaired[-1].end == cue.start:
            group.insert(0, repaired.pop())
        changes.append({'indices_originales': [item.index for item in group], 'accion': 'Agrupacion sin cambiar palabras; limites existentes; revision temporal pendiente', 'inicio': group[0].start.total_seconds(), 'fin': group[-1].end.total_seconds()})
        repaired.append(srt.Subtitle(group[0].index, group[0].start, group[-1].end, '\n'.join(item.content for item in group)))
        position = following + 1
    for number, cue in enumerate(repaired, 1):
        cue.index = number
    return repaired, changes


def transcribe(video, output, control, duration, language='Spanish'):
    if output.exists():
        cues = list(srt.parse(output.read_text(encoding='utf-8-sig')))
        validate_cues(cues, duration)
        return {'estado': 'SRT existente preservado', 'segmentos': len(cues), 'sha256': digest(output)}
    original = control / (output.stem + ' - salida-original.srt')
    log = control / (output.stem + ' - motor.log')
    receipt = control / (output.stem + ' - resultado-motor.json')
    if original.exists() and log.exists() and 'Operation finished' in log.read_text(encoding='utf-8', errors='replace'):
        cues, repairs = repair_zero_cues(list(srt.parse(original.read_text(encoding='utf-8-sig'))))
        validate_cues(cues, duration)
        with output.open('x', encoding='utf-8') as stream:
            stream.write(srt.compose(cues, reindex=False))
        run = json.loads(receipt.read_text(encoding='utf-8')) if receipt.exists() else {'codigo_motor': None, 'incidencia': 'Codigo no registrado antes del fallo de validacion; no se certifica codigo cero'}
        (control / (output.stem + ' - reparaciones.json')).write_text(json.dumps(repairs, ensure_ascii=False, indent=2), encoding='utf-8')
        return {**run, 'estado': 'Automatica recuperada; revision humana y temporal pendientes', 'segmentos': len(cues), 'sha256': digest(output), 'motor': 'Purfview Faster Whisper XXL', 'modelo': 'large-v3', 'idioma': language, 'dispositivo': 'CUDA', 'preset': '--standard', 'salida_original_recuperada': True, 'marcador_fin_motor': True, 'reparaciones': repairs}
    with tempfile.TemporaryDirectory(prefix='ucnl-stt-', dir=ROOT / 'tmp') as temporary:
        temporary = Path(temporary)
        audio = temporary / 'audio.wav'
        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(video), '-vn', '-ac', '1', '-ar', '16000', str(audio)], check=True)
        audio_probe = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(audio)], capture_output=True, text=True, check=True)
        audio_duration = float(json.loads(audio_probe.stdout)['format']['duration'])
        if abs(audio_duration - duration) > 2:
            raise RuntimeError('Duracion de audio extraido no coincide con el video')
        log = control / (output.stem + ' - motor.log')
        with log.open('w', encoding='utf-8') as stream:
            process = subprocess.run([str(ENGINE), str(audio), '--model', 'large-v3', '--model_dir', str(ENGINE.parent / '_models'), '--language', language, '--device', 'cuda', '--task', 'transcribe', '--output_dir', str(temporary), '--output_format', 'srt', '--standard', '--beep_off'], stdout=stream, stderr=subprocess.STDOUT)
        receipt.write_text(json.dumps({'codigo_motor': process.returncode, 'idioma': language, 'duracion_audio_segundos': audio_duration, 'sha256_mp4': digest(video)}, indent=2), encoding='utf-8')
        generated_candidates = list(temporary.glob('*.srt'))
        generated = generated_candidates[0] if len(generated_candidates) == 1 else temporary / 'audio.srt'
        if generated.exists():
            shutil.copy2(generated, control / (output.stem + ' - salida-original.srt'))
        if not generated.exists() or (process.returncode and 'Operation finished' not in log.read_text(encoding='utf-8', errors='replace')):
            raise RuntimeError('motor_no_completo')
        cues, repairs = repair_zero_cues(list(srt.parse(generated.read_text(encoding='utf-8-sig'))))
        validate_cues(cues, duration)
        if repairs:
            shutil.copy2(generated, control / (output.stem + ' - salida-original.srt'))
            (control / (output.stem + ' - reparaciones.json')).write_text(json.dumps(repairs, ensure_ascii=False, indent=2), encoding='utf-8')
        with output.open('x', encoding='utf-8') as stream:
            stream.write(srt.compose(cues, reindex=False))
        return {'estado': 'Automatica; revision humana pendiente', 'segmentos': len(cues), 'sha256': digest(output), 'motor': 'Purfview Faster Whisper XXL', 'modelo': 'large-v3', 'idioma': language, 'dispositivo': 'CUDA', 'preset': '--standard', 'codigo_motor': process.returncode, 'duracion_audio_segundos': audio_duration, 'marcador_fin_motor': 'Operation finished' in log.read_text(encoding='utf-8', errors='replace'), 'duraciones_nulas_corregidas': repairs}


def validate_cues(cues, duration):
    if not cues:
        raise RuntimeError('SRT_vacio')
    previous = -1
    for number, cue in enumerate(cues, 1):
        start, end = cue.start.total_seconds(), cue.end.total_seconds()
        if not cue.content.strip():
            raise RuntimeError('SRT_texto_vacio')
        if cue.index != number or start < 0 or start < previous or end <= start or end > duration + 2:
            raise RuntimeError('SRT_tiempos_invalidos')
        previous = start


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--browser', choices=('edge', 'chrome', 'firefox'))
    parser.add_argument('--profile', help='Perfil identificado expresamente por el usuario; no se busca automaticamente')
    parser.add_argument('--video-id', help='Procesar solo este ID, comprobando que esta enlazado en el aula')
    parser.add_argument('--local-video', type=Path, help='Medio autorizado ya descargado; se conserva el original')
    parser.add_argument('--audit-only', action='store_true', help='Consultar candidatos y validar existentes sin descargar ni transcribir')
    parser.add_argument('--deep-audit', action='store_true', help='Revisar tambien paginas, recursos y avisos sin abrir evaluaciones')
    arguments = parser.parse_args()
    if bool(arguments.browser) != bool(arguments.profile):
        parser.error('--browser y --profile deben indicarse juntos')
    if arguments.video_id and not re.fullmatch(r'[\w-]{11}', arguments.video_id):
        parser.error('--video-id debe ser un ID de YouTube de 11 caracteres')
    if arguments.local_video and (not arguments.video_id or not arguments.local_video.is_file() or arguments.video_id not in arguments.local_video.stem):
        parser.error('--local-video requiere un archivo existente con el --video-id en su nombre')
    previous_report = json.loads(REPORT.read_text(encoding='utf-8')) if REPORT.exists() else {'resultados': []}
    previous = {item['video_id']: item for item in previous_report['resultados'] if item.get('video_id')}
    stamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
    for _, slug, _ in COURSES:
        control = ROOT / f'UCNL/licenciatura-en-administracion/{slug}-lad/referencias-{slug}/notas-{slug}/materiales-generales/control-grabaciones'
        control.mkdir(parents=True, exist_ok=True)
        history = [item for item in previous_report['resultados'] if item.get('materia') == slug]
        (control / f'inventario-previo-{stamp}.json').write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding='utf-8')
    load_aulatex_env()
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    pin = os.environ.get('AULATEX_MASTER_PIN', '')
    accounts = [item for item in vault.list_accounts(pin) if urlsplit(item['url']).hostname == 'licenciatura.ucnl.edu.mx']
    if len(accounts) != 1:
        raise RuntimeError('cuenta_no_univoca')
    credentials = vault.get_credentials(pin, accounts[0]['id'])
    report = {'fecha_utc': datetime.now(timezone.utc).isoformat(), 'autorizacion': 'Usuario solicita descargar, ubicar, renombrar y transcribir UCNL', 'resultados': [item for item in previous_report['resultados'] if arguments.video_id and item.get('video_id') != arguments.video_id]}
    def save():
        REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        for _, slug, _ in COURSES:
            control = ROOT / f'UCNL/licenciatura-en-administracion/{slug}-lad/referencias-{slug}/notas-{slug}/materiales-generales/control-grabaciones'
            items = [item for item in report['resultados'] if item.get('materia') == slug]
            (control / f'resultado-grabaciones-{stamp}.json').write_text(json.dumps({'fecha_utc': report['fecha_utc'], 'resultados': items}, ensure_ascii=False, indent=2), encoding='utf-8')
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(45000)
        for attempt in range(2):
            page.goto(HOST + '/login/index.php', wait_until='domcontentloaded')
            if page.locator('#username').count():
                page.locator('#username').fill(credentials['username'])
                page.locator('#password').fill(credentials['password'])
                page.locator('#loginbtn').click()
                page.wait_for_load_state('domcontentloaded')
            page.goto(HOST + '/course/view.php?id=20322', wait_until='domcontentloaded')
            if '/login/' not in urlsplit(page.url).path and page.locator('.course-content').count():
                break
        else:
            raise RuntimeError('acceso_UCNL_no_completado')
        del credentials
        candidates = []
        for course, slug, identifier in COURSES:
            course_response = page.goto(HOST + f'/course/view.php?id={course}', wait_until='domcontentloaded')
            page.locator('.course-content').wait_for()
            links = page.locator('.course-content a[href]').evaluate_all('items=>items.filter(e=>/sesi.n grabada|grabaci.n/i.test(e.innerText)).flatMap((e,index)=>{const embedded=Array.from(e.parentElement.querySelectorAll("iframe[src],video[src],audio[src],source[src]")).map(m=>m.src);const direct=e.getAttribute("href");const urls=embedded.length&&!direct?embedded:[...embedded,e.href];return urls.map(url=>({url,block:index+1,embedded:embedded.includes(url),section:e.closest("li.section,section,[data-sectionid]")?.querySelector(".sectionname,h3")?.innerText||""}));})')
            original_html = None
            if course_response and course_response.status == 200:
                from bs4 import BeautifulSoup
                original_html = BeautifulSoup(course_response.text(), 'html.parser')
                links.extend(recording_blocks(original_html))
                anchors = [anchor for anchor in original_html.select('.course-content a[href]') if re.search(r'sesi.n grabada|grabaci.n', anchor.get_text(' ', strip=True), re.I)]
                for block, anchor in enumerate(anchors, 1):
                    for media in anchor.parent.select('iframe[src],video[src],audio[src],source[src],video a[href]'):
                        links.append({'url': media.get('src') or media.get('href'), 'block': block, 'embedded': True, 'section': ''})
            existing_ids = {identity for identity, item in previous.items() if item.get('curso') == course and item.get('archivo')}
            if arguments.video_id:
                existing_ids.add(arguments.video_id)
            if existing_ids:
                sources = page.locator('.course-content a[href],.course-content iframe[src],.course-content video[src],.course-content source[src]').evaluate_all('items=>items.map(item=>item.src||item.href)')
                if original_html:
                    sources.extend(item.get('src') or item.get('href') for item in original_html.select('.course-content a[href],.course-content iframe[src],.course-content video[src],.course-content source[src]'))
                for source in sources:
                    if video_id(source) in existing_ids:
                        links.append({'url': source, 'block': None, 'embedded': True, 'section': ''})
            if arguments.deep_audit and original_html:
                extra, audit = resource_recordings(page, original_html, HOST + f'/course/view.php?id={course}')
                links.extend(extra)
                control = ROOT / f'UCNL/licenciatura-en-administracion/{slug}-lad/referencias-{slug}/notas-{slug}/materiales-generales/control-grabaciones'
                (control / f'auditoria-recursos-{stamp}.json').write_text(json.dumps({'fecha_utc': report['fecha_utc'], 'curso': course, **audit}, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f'{identifier}: {len(audit["paginas"])} paginas de lectura comprobadas', flush=True)
            seen = set()
            embedded_blocks = {link['block'] for link in links if link['embedded'] and video_id(link['url'])}
            for link in links:
                link['url'] = urljoin(HOST + f'/course/view.php?id={course}', link['url'])
                identity = video_id(link['url'])
                if arguments.video_id and identity != arguments.video_id:
                    continue
                entry = {'curso': course, 'materia': slug, 'origen': link.get('origin', HOST + f'/course/view.php?id={course}'), 'bloque_aula': link['block'], 'fuente_incrustada': link['embedded'], 'seccion_aula': re.sub(r'https?://\S+', '[enlace omitido]', link['section'])[:160]}
                if identity:
                    if identity in seen:
                        continue
                    seen.add(identity)
                    entry.update(video_id=identity, url='https://www.youtube.com/watch?v=' + identity)
                    entry.update(academic_metadata(entry))
                    candidates.append((slug, identifier, entry))
                else:
                    parsed = urlsplit(link['url'])
                    if link['block'] in embedded_blocks and parsed.hostname == urlsplit(HOST).hostname and parsed.path == '/course/view.php':
                        continue
                    if parsed.hostname == 'teams.microsoft.com':
                        entry['estado'] = teams_link_kind(link['url'])
                    elif (parsed.hostname or '').endswith('.zoom.us') and '/j/' in parsed.path:
                        entry['estado'] = 'Enlace de reunion Zoom; no es una grabacion y no se inicia'
                    elif parsed.hostname == urlsplit(HOST).hostname and parsed.path == '/course/view.php':
                        entry['estado'] = 'Enlace vacio o autorreferente al curso; sin destino de grabacion'
                    else:
                        entry['estado'] = 'Enlace no identificado como video; pendiente de correccion o inspeccion'
                    report['resultados'].append(entry)
        context.close()
        browser.close()
    if arguments.video_id and not candidates:
        raise RuntimeError('El video indicado no se encontro en los cursos UCNL; no se asigna una materia por suposicion')
    save()
    for slug, identifier, entry in candidates:
        control = ROOT / f'UCNL/licenciatura-en-administracion/{slug}-lad/referencias-{slug}/notas-{slug}/materiales-generales/control-grabaciones'
        control.mkdir(parents=True, exist_ok=True)
        try:
            folder = ROOT / f'UCNL/licenciatura-en-administracion/{slug}-lad/referencias-{slug}/grabaciones-{slug}'
            preserved = preserve_existing(entry, previous, folder)
            if preserved:
                report['resultados'].append(preserved)
                save()
                print(f'{identifier} {entry["video_id"]}: MP4 y SRT existentes preservados', flush=True)
                continue
            if arguments.audit_only:
                entry['estado'] = 'Enlace rotulado grabacion; metadatos y disponibilidad pendientes de comprobar'
                report['resultados'].append(entry)
                save()
                print(f'{identifier} {entry["video_id"]}: candidato de grabacion localizado', flush=True)
                continue
            options = {'quiet': True, 'no_warnings': True, 'logger': SafeLogger(), 'noplaylist': True, 'retries': 2, 'socket_timeout': 30}
            options['js_runtimes'] = deno_runtime()
            entry['motor_javascript'] = 'Deno; ruta explicita de la configuracion de yt-dlp'
            if arguments.browser:
                options['cookiesfrombrowser'] = (arguments.browser, arguments.profile, None, None)
            try:
                with yt_dlp.YoutubeDL(options) as downloader:
                    metadata = downloader.extract_info(entry['url'], download=False)
            except yt_dlp.utils.DownloadError as error:
                if not arguments.local_video:
                    raise
                entry['consulta_subtitulos_bloqueada'] = download_failure(error)
                local_title = re.sub(r'\s*\[' + re.escape(entry['video_id']) + r'\]\s*$', '', arguments.local_video.stem)
                metadata = {'title': local_title, 'duration': probe(arguments.local_video)}
            if arguments.local_video:
                entry['fuente_local'] = {'nombre': arguments.local_video.name, 'bytes': arguments.local_video.stat().st_size, 'sha256': digest(arguments.local_video), 'original_preservado': True}
            title = clean_name(metadata['title'])
            if metadata.get('is_live') or metadata.get('live_status') in ('is_live', 'is_upcoming'):
                raise RuntimeError('Emision en vivo o futura; no se descarga como grabacion')
            entry.update(titulo=metadata['title'], fecha_publicacion=metadata.get('upload_date'), duracion_anunciada=metadata.get('duration'))
            session = re.search(r'sesi.n\s*#?\s*(\d+)', title, re.I)
            session_name = 'S' + session.group(1) if session else 'Sesion no indicada'
            chapter = re.search(r'sesi.n\s+cap.tulo\s+(\d+)', title, re.I)
            if chapter:
                session_name = 'Sesion capitulo ' + chapter.group(1)
            name = f'UCNL - {identifier} - {session_name} - Fecha no indicada - {title} [{entry["video_id"]}].mp4'
            if academic_basename(entry):
                name = academic_basename(entry) + '.mp4'
            local_videos = list(folder.glob(f'*{entry["video_id"]}*.mp4'))
            if previous.get(entry['video_id'], {}).get('archivo'):
                previous_video = ROOT / previous[entry['video_id']]['archivo']
                if previous_video.exists() and previous_video not in local_videos:
                    local_videos.append(previous_video)
            video = local_videos[0] if local_videos else folder / name
            if not video.exists():
                with tempfile.TemporaryDirectory(prefix='ucnl-video-', dir=ROOT / 'tmp') as temporary:
                    source = Path(temporary) / 'video.mp4'
                    if arguments.local_video:
                        subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-i', str(arguments.local_video), '-map', '0:v:0', '-map', '0:a:0', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', str(source)], capture_output=True, check=True)
                        if abs(probe(source) - probe(arguments.local_video)) > 2:
                            raise RuntimeError('Duracion MP4 no coincide con el original; no se publica')
                    else:
                        options.update({'outtmpl': str(Path(temporary) / 'video.%(ext)s'), 'format': 'bestvideo[ext=mp4][height<=720]+bestaudio[ext=m4a]/best[ext=mp4][height<=720]', 'merge_output_format': 'mp4'})
                        with yt_dlp.YoutubeDL(options) as downloader:
                            downloader.download([entry['url']])
                    probe(source)
                    folder.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(source), str(video))
            duration = probe(video)
            entry.update(archivo=video.relative_to(ROOT).as_posix(), sha256=digest(video), duracion_segundos=duration, estado='Video descargado y validado')
            print(f'{identifier} {entry["video_id"]}: video validado; transcribiendo', flush=True)
            save_entry = dict(entry)
            (control / (entry['video_id'] + ' - procedencia.json')).write_text(json.dumps(save_entry, ensure_ascii=False, indent=2), encoding='utf-8')
            subtitle = video.with_suffix('.srt')
            caption = None if subtitle.exists() else existing_captions(metadata, subtitle, control, duration, options)
            language = recording_language(metadata)
            entry['idioma_detectado'] = language
            entry['subtitulos_video'] = 'Recuperados y validados' if caption else 'Sin subtitulos recuperables y validos en el idioma detectado; se conserva SRT local o se usa motor'
            entry['transcripcion'] = caption or transcribe(video, subtitle, control, duration, {'es': 'Spanish', 'en': 'English'}.get(language, language))
            entry['srt'] = subtitle.relative_to(ROOT).as_posix()
            entry['estado'] = 'Video y SRT validados; revision humana pendiente'
            print(f'{identifier} {entry["video_id"]}: SRT validado', flush=True)
        except Exception as error:
            entry['estado'] = 'Proceso no completado; conservar archivos existentes'
            entry['clase_error'] = type(error).__name__
            if isinstance(error, RuntimeError):
                entry['motivo'] = str(error)
            elif isinstance(error, yt_dlp.utils.DownloadError):
                entry['motivo'] = download_failure(error)
                if entry['motivo'].startswith('Emision futura;'):
                    entry['estado'] = 'Excluida: emision futura, no grabacion disponible'
            print(f'{identifier} {entry["video_id"]}: pendiente ({type(error).__name__})', flush=True)
        report['resultados'].append(entry)
        save()
    print(json.dumps({'videos': sum('archivo' in item for item in report['resultados']), 'srt': sum('srt' in item for item in report['resultados']), 'pendientes': sum('srt' not in item for item in report['resultados'])}))


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        reasons = {'acceso_UCNL_no_completado', 'cuenta_no_univoca', 'El video indicado no se encontro en los cursos UCNL; no se asigna una materia por suposicion'}
        message = str(error) if isinstance(error, RuntimeError) and str(error) in reasons else 'Detalle externo omitido para proteger datos de acceso'
        print(json.dumps({'estado': 'Lote no completado', 'clase_error': type(error).__name__, 'motivo': message}))
        raise SystemExit(1) from None