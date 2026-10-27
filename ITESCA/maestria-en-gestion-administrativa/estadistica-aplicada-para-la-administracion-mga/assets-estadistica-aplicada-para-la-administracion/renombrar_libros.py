import hashlib
import json
import os
import re
from pathlib import Path
from urllib.parse import quote, unquote


SUBJECT = Path(__file__).resolve().parents[1]
REFERENCES = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion'
BOOKS = REFERENCES / 'libros-estadistica-aplicada-para-la-administracion'
NAMES = {
    '2dc1be3df6cd': 'Estadística para administración y economía - Levin y Rubin. 7.ª edición revisada',
    '7d55c7e0cacc': 'Estadística para negocios y economía - Anderson, Sweeney y Williams. 11.ª edición',
    '33c7704b9ec0': 'Aprendiendo estadística, volumen 1 - Romero. Edición no verificada',
    '22ff190b242f': 'Aprendiendo estadística, volumen 2 - Romero. Edición no verificada',
    '6a80fdd0d977': 'Estadística - Spiegel y Stephens. 4.ª edición',
    'caade86425ea': 'Estadística - Spiegel y Stephens. 4.ª edición',
    '9b3812669eea': 'Estadística matemática con aplicaciones - Wackerly, Mendenhall y Scheaffer. 7.ª edición',
    '2ae1c84a11b0': 'Estadística aplicada a los negocios y la economía - Lind, Marchal y Wathen. 15.ª edición',
    'ea624bd9e9ea': 'Probabilidad y estadística, aplicaciones y métodos - Canavos. Edición no verificada',
    '5354a4c65c69': 'Introducción a la probabilidad y estadística - Mendenhall, Beaver y Beaver. 14.ª edición',
    'ec9b01998084': 'Estadística inferencial aplicada - Díaz Rodríguez. 2.ª edición',
    '72bfb4f959b2': 'Estadística aplicada a administración y economía - Kazmier. 2.ª edición',
    '272d269d0444': 'Estadística paso a paso - Christensen. 3.ª edición española',
    '5b237ae1bf8a': 'Estadística aplicada a los negocios y la economía - Lind, Marchal y Wathen. 16.ª edición',
    '57c44bd5b451': 'Estadística para administración y economía - Anderson, Sweeney y Williams. 10.ª edición',
    '010ad3292e60': 'Estadística para la administración y los negocios - Véliz Capuñay. 1.ª edición',
    'e6ca69170e66': 'Estadística aplicada a los negocios y a la economía - Webster. Edición no verificada',
    '8fb839966606': 'Estadística aplicada a la administración y la economía - Díaz Mata. 1.ª edición',
}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest_path = REFERENCES / 'inventario-biblioteca-unificada.json'
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    changes = {}
    destinations = set()
    for book in manifest['books']:
        old = SUBJECT / book['path']
        assert sha(old) == book['sha256']
        title = NAMES[book['sha256'][:12]]
        folder = BOOKS / 'Variantes' if book['sha256'].startswith('caade') else BOOKS
        new = folder / (title + '.pdf')
        assert new not in destinations
        assert old == new or not new.exists(), new
        destinations.add(new)
        changes[book['path']] = new.relative_to(SUBJECT).as_posix()
    for old, new in changes.items():
        source, target = SUBJECT / old, SUBJECT / new
        target.parent.mkdir(parents=True, exist_ok=True)
        if source != target:
            source.rename(target)

    def update(value):
        if isinstance(value, dict):
            return {key: child if key in ('original_path', 'original_file_hashes') else update(child) for key, child in value.items()}
        if isinstance(value, list):
            return [update(child) for child in value]
        if isinstance(value, str):
            for old, new in changes.items():
                value = value.replace(old, new)
            return value
        return value

    for path in SUBJECT.rglob('*'):
        if not path.is_file() or 'plantillas-previas-2026-10-18' in path.parts:
            continue
        if path.suffix == '.json':
            data = json.loads(path.read_text(encoding='utf-8-sig'))
            revised = update(data)
            if revised != data:
                path.write_text(json.dumps(revised, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        elif path.suffix == '.md':
            original = path.read_text(encoding='utf-8-sig')
            def link(match):
                target = unquote(match.group(1))
                if target.startswith(('http:', 'https:', '#')):
                    return match.group(0)
                resolved = (path.parent / target).resolve()
                if not resolved.is_relative_to(SUBJECT):
                    return match.group(0)
                old = resolved.relative_to(SUBJECT).as_posix()
                if old not in changes:
                    return match.group(0)
                relative = Path(os.path.relpath(SUBJECT / changes[old], path.parent)).as_posix()
                return '](' + quote(relative, safe='/') + ')'
            revised = re.sub(r'\]\(([^)]+)\)', link, original)
            for old, new in changes.items():
                revised = revised.replace('[' + Path(old).name + ']', '[' + Path(new).name + ']')
            if revised != original:
                path.write_text(revised, encoding='utf-8')
        elif path.suffix == '.bib':
            original = path.read_text(encoding='utf-8-sig')
            revised = original
            for old, new in changes.items():
                revised = revised.replace(Path(old).name, Path(new).name)
            if revised != original:
                path.write_text(revised, encoding='utf-8')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    for book in manifest['books']:
        book['title'] = NAMES[book['sha256'][:12]].split(' - ')[0]
        book['display_name'] = Path(book['path']).name
        assert sha(SUBJECT / book['path']) == book['sha256']
        for source in book['sources']:
            if source['kind'] == 'biblioteca-personal':
                assert sha(Path(source['original_path'])) == book['sha256']
    manifest['filename_format'] = 'Título - Autor. Edición.pdf'
    manifest['renamed_paths'] = changes
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for path in SUBJECT.rglob('*.md'):
        if 'plantillas-previas-2026-10-18' in path.parts:
            continue
        for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8-sig')):
            if target.startswith(('http:', 'https:', '#')):
                continue
            assert (path.parent / unquote(target.split('#')[0])).exists(), (path, target)
    assert len(list(BOOKS.rglob('*.pdf'))) == 18
    print(json.dumps({'renamed': len(changes), 'hashes_unchanged': True, 'external_library_unchanged': True, 'links_valid': True}, ensure_ascii=True))


if __name__ == '__main__':
    main()