import hashlib
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path
from urllib.parse import unquote

import pymupdf


SUBJECT = Path(__file__).resolve().parents[1]
REFERENCES = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion'
LEGACY = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion-mga'
NOTES = REFERENCES / 'notas-estadistica-aplicada-para-la-administracion'
BOOKS = REFERENCES / 'libros-estadistica-aplicada-para-la-administracion'
LIBRARY = Path('C:/Users/Sysx/Documents/Libros/Administración')
EVIDENCE = NOTES / 'materiales-aula/2026-10-18'
MANIFEST = REFERENCES / 'inventario-biblioteca-unificada.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slug(text):
    text = ''.join(char for char in unicodedata.normalize('NFKD', text) if not unicodedata.combining(char))
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')


def main():
    if MANIFEST.exists():
        raise FileExistsError('Organización ya registrada; validar antes de repetir')
    inventory = json.loads((EVIDENCE / 'inventario.json').read_text(encoding='utf-8'))
    before = {str(path.relative_to(SUBJECT)): digest(path) for folder in (REFERENCES, LEGACY) for path in folder.rglob('*') if path.is_file()}
    BOOKS.mkdir(parents=True, exist_ok=True)
    mappings = {}
    records = {}

    def register(path, title, source, move=False, metadata=None):
        sha = digest(path)
        if sha in records:
            destination = SUBJECT / records[sha]['path']
        else:
            destination = BOOKS / f'{slug(title)}--{sha[:12]}.pdf'
            if destination.exists() and digest(destination) != sha:
                raise ValueError('Conflicto de contenido')
            if not destination.exists():
                shutil.copy2(path, destination)
            records[sha] = {'title': title, 'path': destination.relative_to(SUBJECT).as_posix(), 'sha256': sha, 'bytes': destination.stat().st_size, 'sources': [], 'metadata': metadata or {}}
        records[sha]['sources'].append(source)
        assert digest(destination) == sha
        if move and path != destination:
            mappings[path.relative_to(SUBJECT).as_posix()] = destination.relative_to(SUBJECT).as_posix()
            if path.with_suffix('.txt').exists():
                extraction = NOTES / 'extracciones-libros' / destination.with_suffix('.txt').name
                extraction.parent.mkdir(exist_ok=True)
                shutil.move(str(path.with_suffix('.txt')), extraction)
                mappings[path.with_suffix('.txt').relative_to(SUBJECT).as_posix()] = extraction.relative_to(SUBJECT).as_posix()
            path.unlink()
        return destination

    aula_names = {
        '2dc1be3df6cd': 'Levin y Rubin - Estadistica para administracion y economia - 7a edicion revisada',
        '7d55c7e0cacc': 'Anderson Sweeney y Williams - Estadistica para negocios y economia - 11a edicion',
        '33c7704b9ec0': 'Romero - Aprendiendo estadistica - Volumen 1',
        '22ff190b242f': 'Romero - Aprendiendo estadistica - Volumen 2',
        '6a80fdd0d977': 'Spiegel - Estadistica - 4a edicion',
        '9b3812669eea': 'Estadistica matematica con aplicaciones',
        '2ae1c84a11b0': 'Lind Marchal y Wathen - Estadistica aplicada a los negocios y la economia - 15a edicion',
        'ea624bd9e9ea': 'Canavos - Probabilidad y estadistica aplicaciones y metodos',
    }
    for record in inventory['files']:
        path = SUBJECT / record['path']
        if path.name.startswith('1734-'):
            title = aula_names[record['sha256'][:12]]
            original = record['path']
            if path.exists():
                destination = register(path, title, {'kind': 'aula', 'url': record['source'], 'original_path': original}, move=True)
            else:
                destination = SUBJECT / mappings[original]
                records[record['sha256']]['sources'].append({'kind': 'aula', 'url': record['source'], 'original_path': original})
            record['original_path'] = original
            record['path'] = destination.relative_to(SUBJECT).as_posix()
        elif 'Programa' in unquote(record['source']):
            destination = NOTES / 'programa-asignatura/Programa-Estadistica-para-la-administracion-ITESCA-2025.pdf'
            destination.parent.mkdir(exist_ok=True)
            old = record['path']
            shutil.move(str(path), destination)
            mappings[old] = destination.relative_to(SUBJECT).as_posix()
            if path.with_suffix('.txt').exists():
                shutil.move(str(path.with_suffix('.txt')), destination.with_suffix('.txt'))
                mappings[path.with_suffix('.txt').relative_to(SUBJECT).as_posix()] = destination.with_suffix('.txt').relative_to(SUBJECT).as_posix()
            assert digest(destination) == record['sha256']
            record['original_path'] = old
            record['path'] = destination.relative_to(SUBJECT).as_posix()

    library_names = {
        'David R. Anderson': ('Anderson Sweeney y Williams - Estadistica para administracion y economia - 10a edicion - 2008', {'edition': '10', 'year': 2008}),
        'Murray R. Spiegel': ('Spiegel y Stephens - Estadistica - 4a edicion - 2009', {'edition': '4', 'year': 2009}),
        'William Mendenhall': ('Mendenhall Beaver y Beaver - Introduccion a la probabilidad y estadistica - 14a edicion - 2015', {'edition': '14', 'year': 2015}),
        'Howard B. Christensen': ('Christensen - Estadistica paso a paso - 3a edicion espanola - 1990', {'edition': '3 española', 'year': 1990, 'reprint': 1994}),
        'Douglas A. Lind': ('Lind Marchal y Wathen - Estadistica aplicada a los negocios y la economia - 16a edicion - 2015', {'edition': '16 portada', 'year': 2015, 'warning': 'La página legal contiene numeración inconsistente; conservar portada y legal.'}),
        'Carlos Veliz Capunay': ('Veliz Capunay - Estadistica para la administracion y los negocios - 1a edicion - 2011', {'edition': '1', 'year': 2011}),
        'Martin Diaz Rodriguez': ('Diaz Rodriguez - Estadistica inferencial aplicada - 2a edicion - 2022', {'edition': '2', 'year': 2022}),
        'Leonard Kazmier': ('Kazmier - Estadistica aplicada a administracion y economia - 2a edicion - 1991', {'edition': '2', 'year': 1991}),
        'Alfredo Diaz Mata': ('Diaz Mata - Estadistica aplicada a la administracion y la economia - 1a edicion', {'edition': '1', 'warning': 'Página legal menciona 2015 y 2013; no fijar año único en nombre.'}),
        'Allen Webster': ('Webster - Estadistica aplicada a los negocios y a la economia', {'warning': 'Escaneo: edición y año por cotejar visualmente.'}),
    }
    for path in LIBRARY.rglob('*.pdf'):
        relative = path.relative_to(LIBRARY)
        if any(part.startswith('.') for part in relative.parts) or relative.parts[0] not in library_names:
            continue
        if not any(word in slug(path.name) for word in ('estadistica', 'probabilidad')):
            continue
        title, metadata = library_names[relative.parts[0]]
        register(path, title, {'kind': 'biblioteca-personal', 'original_path': str(path)}, metadata=metadata)

    for path in list(LEGACY.rglob('*.pdf')):
        register(path, path.stem, {'kind': 'referencias-previas', 'original_path': path.relative_to(SUBJECT).as_posix()}, move=True)
    for path in list(LEGACY.rglob('*')):
        if not path.is_file():
            continue
        relative = path.relative_to(LEGACY)
        destination = REFERENCES / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if digest(destination) != digest(path):
                destination = NOTES / 'referencias-previas' / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
        mappings[path.relative_to(SUBJECT).as_posix()] = destination.relative_to(SUBJECT).as_posix()
        if destination.exists():
            assert digest(destination) == digest(path)
            path.unlink()
        else:
            shutil.move(str(path), destination)
    for directory in sorted(LEGACY.rglob('*'), key=lambda path: len(path.parts), reverse=True):
        if directory.is_dir():
            directory.rmdir()
    LEGACY.rmdir()
    (EVIDENCE / 'inventario.json').write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')

    for path in SUBJECT.rglob('*'):
        if path == Path(__file__).resolve() or 'plantillas-previas-2026-10-18' in path.parts:
            continue
        if path.suffix not in ('.md', '.json', '.bib', '.tex') or not path.is_file():
            continue
        original = path.read_text(encoding='utf-8-sig')
        content = original
        for old, new in mappings.items():
            content = content.replace(old, new)
        content = content.replace(LEGACY.name, REFERENCES.name)
        if content != original:
            path.write_text(content, encoding='utf-8')
    for sha, record in records.items():
        assert digest(SUBJECT / record['path']) == sha
        for source in record['sources']:
            if source['kind'] == 'biblioteca-personal':
                assert digest(Path(source['original_path'])) == sha
    report = {'operation': 'unificar-referencias-copiar-biblioteca', 'date': '2026-10-18', 'library_unchanged': True, 'canonical_references': REFERENCES.name, 'books': list(records.values()), 'path_mappings': mappings, 'original_file_hashes': before}
    MANIFEST.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    rows = ['# Biblioteca unificada', '', 'Los nombres se basan en portada y página legal cuando son legibles. Los escaneos sin cotejo editorial completo no reciben año ni edición inferidos. Las copias personales se conservaron sin modificar la biblioteca externa.', '', '| Libro | Datos y límites | Procedencia |', '| --- | --- | --- |']
    for record in records.values():
        rows.append(f"| [{record['title']}]({Path(record['path']).name}) | {json.dumps(record['metadata'], ensure_ascii=False)} | {', '.join(sorted({source['kind'] for source in record['sources']}))} |")
    rows.extend(['', '[Inventario y hashes](../inventario-biblioteca-unificada.json). Dos enlaces de Estadística matemática con aplicaciones son idénticos y apuntan al mismo PDF. Disponibilidad local no acredita derechos de redistribución pública.'])
    (BOOKS / 'README.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    print(json.dumps({'books': len(records), 'canonical_folder': REFERENCES.name, 'legacy_folder_removed': not LEGACY.exists(), 'paths_updated': len(mappings)}, ensure_ascii=True))


def rename_books():
    manifest = json.loads(MANIFEST.read_text(encoding='utf-8'))
    names = {
        '2dc1be3df6cd': 'Estadística para administración y economía - Levin y Rubin. 7.ª edición revisada',
        '7d55c7e0cacc': 'Estadística para negocios y economía - Anderson, Sweeney y Williams. 11.ª edición',
        '33c7704b9ec0': 'Aprendiendo estadística, volumen 1 - Romero. Edición no verificada',
        '22ff190b242f': 'Aprendiendo estadística, volumen 2 - Romero. Edición no verificada',
        '6a80fdd0d977': 'Estadística - Spiegel y Stephens. 4.ª edición',
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
        'caade86425ea': 'Estadística - Spiegel y Stephens. 4.ª edición',
    }
    planned = []
    for book in manifest['books']:
        prefix = book['sha256'][:12]
        folder = BOOKS / 'Variantes' if prefix == 'caade86425ea' else BOOKS
        destination = folder / (names[prefix] + '.pdf')
        source = SUBJECT / book['path']
        assert digest(source) == book['sha256']
        if destination != source and destination.exists():
            raise FileExistsError(destination.name)
        planned.append((book, source, destination))
    replacements = {}
    filename_replacements = {}
    for book, source, destination in planned:
        old = source.relative_to(SUBJECT).as_posix()
        new = destination.relative_to(SUBJECT).as_posix()
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source != destination:
            source.rename(destination)
        assert digest(destination) == book['sha256']
        replacements[old] = new
        relative_name = destination.relative_to(BOOKS).as_posix()
        filename_replacements[source.name] = relative_name
        book['path'] = new
        book['title'] = names[book['sha256'][:12]]
        if book['sha256'].startswith('9b3812669eea'):
            book['metadata'].update(edition='7', year=2010, authors='Dennis D. Wackerly; William Mendenhall III; Richard L. Scheaffer', evidence='Página legal PDF 6')
        if book['sha256'].startswith('caade86425ea'):
            book['metadata'].update(edition='4', year=2009, authors='Murray R. Spiegel; Larry J. Stephens', evidence='Portada y página legal PDF 5-6')

    def rewrite(value):
        if isinstance(value, dict):
            return {key: rewrite(child) for key, child in value.items()}
        if isinstance(value, list):
            return [rewrite(child) for child in value]
        if isinstance(value, str):
            return replacements.get(value, value)
        return value

    import re
    from urllib.parse import quote
    for path in SUBJECT.rglob('*'):
        if not path.is_file() or path == MANIFEST or 'plantillas-previas-2026-10-18' in path.parts:
            continue
        if path.suffix == '.json':
            original = json.loads(path.read_text(encoding='utf-8-sig'))
            updated = rewrite(original)
            if updated != original:
                path.write_text(json.dumps(updated, ensure_ascii=False, indent=2), encoding='utf-8')
        elif path.suffix in ('.md', '.bib', '.tex'):
            original = path.read_text(encoding='utf-8-sig')
            updated = original
            for old, new in replacements.items():
                updated = updated.replace(old, new)
            for old, new in filename_replacements.items():
                updated = updated.replace(old, new)
            if path.suffix == '.md':
                updated = re.sub(r'\]\(([^)]+)\)', lambda match: '](' + quote(match.group(1), safe='/:%#?=&') + ')', updated)
            if updated != original:
                path.write_text(updated, encoding='utf-8')
    manifest['path_mappings'].update(replacements)
    manifest['filename_format'] = 'Título - Autor. Edición.pdf'
    manifest['distinct_same_edition_files'] = 'Spiegel y Stephens: segunda copia en Variantes, sin modificación de contenido'
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    assert len(list(BOOKS.rglob('*.pdf'))) == len(planned)
    print(json.dumps({'renamed_books': len(planned), 'format': manifest['filename_format'], 'hashes_preserved': True}, ensure_ascii=True))


if __name__ == '__main__':
    if sys.argv[1:] == ['--nombres-bibliograficos']:
        rename_books()
    else:
        main()