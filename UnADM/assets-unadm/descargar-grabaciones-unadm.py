from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.aulatex.config import load_aulatex_env
from scripts.aulatex.platform_credentials import PlatformCredentialVault, default_vault_path
from playwright.sync_api import sync_playwright

HOST = 'aulavirtual.unadmexico.mx'
RECORDINGS = [
    ('teoria-del-estado-y-constitucion', 4931, 29289, 'semana-02', '2026-10-09', 'Historia y origen del Estado'),
    ('teoria-del-estado-y-constitucion', 4931, 28868, 'semana-01', '2026-10-02', 'Introduccion e historia y origen del Estado'),
    ('antecedentes-de-los-derechos-humanos', 4940, 29086, 'semana-02', '2026-10-06', 'Clase de semana 2'),
    ('antecedentes-de-los-derechos-humanos', 4940, 28656, 'presentacion', '2026-09-29', 'Presentacion de la Experiencia Educativa'),
    ('derecho-penal-especial-mexicano', 4981, 29118, 'sesion-sin-semana-explicita', '2026-10-06', 'Conferencias Web para el aprendizaje'),
]


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def probe(path):
    result = subprocess.run(['ffprobe', '-v', 'error', '-show_format', '-show_streams', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    data = json.loads(result.stdout)
    return {'duracion_segundos': float(data['format'].get('duration', 0)), 'pistas': [{'tipo': item['codec_type'], 'codec': item.get('codec_name'), 'inicio': item.get('start_time')} for item in data['streams']]}


def download(context, url, destination):
    parsed = urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'bbbdaulas.unadmexico.mx' or parsed.query:
        raise RuntimeError('Origen no permitido o URL parametrizada: no descargar')
    temporary = destination.with_suffix('.part')
    if temporary.exists():
        raise RuntimeError('Archivo parcial existente; no sobrescribir')
    first = context.request.get(url, headers={'Range': 'bytes=0-1023'}, timeout=120000)
    payload = first.body()
    range_match = re.fullmatch(r'bytes 0-1023/(\d+)', first.headers.get('content-range', ''))
    if first.status != 206 or not range_match or payload[:4] != bytes.fromhex('1a45dfa3'):
        first.dispose()
        raise RuntimeError('Servidor no ofrece WEBM valido por rangos')
    total = int(range_match.group(1))
    first.dispose()
    if destination.exists():
        if destination.stat().st_size != total:
            raise RuntimeError('Archivo existente con tamano diferente')
        probe(destination)
        return
    with temporary.open('xb') as stream:
        for offset in range(0, total, 8 * 1024 * 1024):
            end = min(total - 1, offset + 8 * 1024 * 1024 - 1)
            response = context.request.get(url, headers={'Range': f'bytes={offset}-{end}'}, timeout=120000)
            chunk = response.body()
            if response.status != 206 or response.headers.get('content-range') != f'bytes {offset}-{end}/{total}' or len(chunk) != end - offset + 1:
                response.dispose()
                raise RuntimeError('Rango incompleto; conservar parcial para diagnostico')
            stream.write(chunk)
            response.dispose()
    if temporary.stat().st_size != total:
        raise RuntimeError('Descarga incompleta')
    probe(temporary)
    temporary.rename(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--first-only', action='store_true')
    args = parser.parse_args()
    load_aulatex_env()
    pin = os.environ.get('AULATEX_MASTER_PIN', '')
    vault = PlatformCredentialVault(default_vault_path(ROOT))
    accounts = [account for account in vault.list_accounts(pin) if account['institution'].casefold() == 'unadm' and urlsplit(account['url']).hostname == HOST]
    if len(accounts) != 1:
        raise RuntimeError('Cuenta no univoca')
    credentials = vault.get_credentials(pin, accounts[0]['id'])
    with sync_playwright() as runtime:
        browser = runtime.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        page.set_default_timeout(60000)
        page.goto(accounts[0]['url'], wait_until='domcontentloaded')
        page.get_by_role('textbox', name=re.compile('Matr')).fill(credentials['username'])
        page.locator('input[type=password]').fill(credentials['password'])
        page.get_by_role('button', name=re.compile('Inicia sesi')).click()
        page.wait_for_url(lambda url: '/login/' not in urlsplit(url).path, wait_until='domcontentloaded')
        del credentials
        for slug, room, recording, week, date, title in RECORDINGS[:1] if args.first_only else RECORDINGS:
            origin = f'https://{HOST}/mod/bigbluebuttonbn/bbb_view.php?action=play&bn={room}&rid={recording}&rtype=presentation'
            page.goto(origin, wait_until='networkidle')
            page.locator('video,audio').first.wait_for(state='attached', timeout=20000)
            sources = page.locator('video,audio').evaluate_all('items=>items.map(item=>item.currentSrc||item.src||item.querySelector("source")?.src).filter(Boolean)')
            sources = list(dict.fromkeys(sources))
            folder = ROOT / 'UnADM/licenciatura-en-derecho-unadm' / f'{slug}-lde' / f'referencias-{slug}/grabaciones-{slug}'
            folder.mkdir(parents=True, exist_ok=True)
            prefix = f'Grabacion - {date}'
            records = []
            for source in sources:
                basename = Path(urlsplit(source).path).name
                component = {'webcams.webm': 'Camara y audio', 'deskshare.webm': 'Pantalla compartida'}.get(basename)
                if not component:
                    continue
                destination = folder / f'{prefix} - {component}.webm'
                download(context, source, destination)
                info = probe(destination)
                records.append({'archivo': destination.name, 'componente': basename, 'bytes': destination.stat().st_size, 'sha256': digest(destination), **info})
                print(json.dumps({'materia': slug, 'fecha': date, 'componente': component, 'bytes': destination.stat().st_size, 'duracion': info['duracion_segundos']}, ensure_ascii=True), flush=True)
            audio_source = next((item for item in records if any(track['tipo'] == 'audio' for track in item['pistas'])), None)
            if audio_source is None:
                raise RuntimeError('No hay pista de audio para Subtitle Edit')
            audio = folder / f'{prefix} - Audio para Subtitle Edit.m4a'
            if not audio.exists():
                subprocess.run(['ffmpeg', '-nostdin', '-v', 'error', '-n', '-i', str(folder / audio_source['archivo']), '-vn', '-map', '0:a:0', '-c:a', 'aac', '-b:a', '128k', str(audio)], check=True)
            info = probe(audio)
            if not any(track['tipo'] == 'audio' for track in info['pistas']) or abs(info['duracion_segundos'] - audio_source['duracion_segundos']) > 3:
                raise RuntimeError('Audio derivado con duracion incoherente')
            records.append({'archivo': audio.name, 'derivado_de': audio_source['archivo'], 'sha256': digest(audio), 'bytes': audio.stat().st_size, **info})
            receipt = {'consulta': datetime.now(ZoneInfo('America/Mexico_City')).isoformat(), 'titulo_aula': title, 'agrupacion': week, 'fecha_aula': date, 'enlace_aula': origin, 'metodo': 'Copias de los componentes WEBM efectivamente cargados por el reproductor accesible; sin eludir autenticacion, sin URLs firmadas ni claves persistidas', 'archivos': records, 'limites': 'No es exportacion oficial del reproductor completo. Diapositivas y chat pueden ser componentes separados; pantalla compartida puede tener otra duracion. Audio derivado para transcripcion; no acredita visionado ni transcripcion revisada.'}
            (folder / f'{prefix} - procedencia.json').write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding='utf-8')
            (folder / f'{prefix} - LEEME.md').write_text('# Grabacion y transcripcion\n\n' + title + '\n\nAudio para Subtitle Edit: ' + audio.name + '\n\nGuardar el SRT generado como `Grabacion - ' + date + ' - Transcripcion.srt` aqui. No existe todavia; revisar nombres, terminos juridicos y tiempos antes de citar. Conservar registro de motor, idioma y revision.\n\nLos WEBM son componentes del reproductor, no una pelicula completa de diapositivas y chat. No redistribuir datos de participantes. Procedencia y SHA256 en el JSON fechado de esta sesion.\n', encoding='utf-8')
        context.close()
        browser.close()


if __name__ == '__main__':
    main()