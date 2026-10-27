import hashlib
import json
import shutil
from pathlib import Path


SUBJECT = Path(__file__).resolve().parents[1]
REFERENCES = SUBJECT / 'referencias-estadistica-aplicada-para-la-administracion'
SOURCE = REFERENCES / 'notas-estadistica-aplicada-para-la-administracion/materiales-aula/2026-10-18'
DESTINATION = REFERENCES / 'libros-estadistica-aplicada-para-la-administracion'
BOOKS = [
    ('2dc1be3df6cd', 'Levin-Rubin-2010-Estadistica-para-administracion-y-economia-7ed-revisada', 'Estadística para administración y economía', 'Levin, Richard I. and Rubin, David S.', '2010', '7', 'Pearson Educación', [5, 6]),
    ('7d55c7e0cacc', 'Anderson-Sweeney-Williams-2012-Estadistica-para-negocios-y-economia-11ed', 'Estadística para negocios y economía', 'Anderson, David R. and Sweeney, Dennis J. and Williams, Thomas A.', '2012', '11', 'Cengage Learning', [5, 6]),
    ('33c7704b9ec0', 'Romero-Revilla-2001-Aprendiendo-estadistica-Volumen-I-1ed', 'Aprendiendo estadística', 'Romero Revilla, Félix', '2001', '1', None, [1, 4]),
    ('22ff190b242f', 'Romero-Revilla-2001-Aprendiendo-estadistica-Volumen-II-1ed', 'Aprendiendo estadística', 'Romero Revilla, Félix', '2001', '1', None, [1, 4]),
    ('6a80fdd0d977', 'Spiegel-Stephens-2009-Estadistica-4ed', 'Estadística', 'Spiegel, Murray R. and Stephens, Larry J.', '2009', '4', 'McGraw-Hill/Interamericana', [5, 6]),
    ('9b3812669eea', 'Wackerly-Mendenhall-Scheaffer-2010-Estadistica-matematica-con-aplicaciones-7ed', 'Estadística matemática con aplicaciones', 'Wackerly, Dennis D. and Mendenhall, William and Scheaffer, Richard L.', '2010', '7', 'Cengage Learning', [6]),
    ('2ae1c84a11b0', 'Lind-Marchal-Wathen-2012-Estadistica-aplicada-a-los-negocios-y-la-economia-15ed', 'Estadística aplicada a los negocios y la economía', 'Lind, Douglas A. and Marchal, William G. and Wathen, Samuel A.', '2012', '15', 'McGraw-Hill/Interamericana', [5]),
    ('ea624bd9e9ea', 'Canavos-1988-Probabilidad-y-estadistica-Aplicaciones-y-metodos-1ed', 'Probabilidad y estadística: aplicaciones y métodos', 'Canavos, George C.', '1988', '1', 'McGraw-Hill/Interamericana de México', [1, 2]),
]


def main():
    inventory_path = SOURCE / 'inventario.json'
    inventory = json.loads(inventory_path.read_text(encoding='utf-8'))
    backup = SOURCE / 'inventario-antes-organizacion-libros.json'
    if backup.exists():
        raise FileExistsError('Existe respaldo de organización; verificar antes de repetir')
    operations = []
    for prefix, stem, title, authors, year, edition, publisher, pages in BOOKS:
        records = [record for record in inventory['files'] if record['sha256'].startswith(prefix)]
        assert records
        paths = {record['path'] for record in records}
        assert len(paths) == 1
        old = SUBJECT / paths.pop()
        new = DESTINATION / (stem + '.pdf')
        assert old.is_file() and not new.exists()
        digest = hashlib.sha256(old.read_bytes()).hexdigest()
        assert all(record['sha256'] == digest for record in records)
        operations.append((old, new, digest, records, {
            'title': title, 'authors_bibtex': authors, 'year': year, 'edition': edition,
            'publisher': publisher, 'editorial_pdf_pages': pages,
            'verification': 'visual' if prefix in ('33c7704b9ec0', '22ff190b242f', 'ea624bd9e9ea') else 'text_extraction',
            'volume': 'I' if prefix == '33c7704b9ec0' else 'II' if prefix == '22ff190b242f' else None,
        }))
    assert len(operations) == 8
    DESTINATION.mkdir(parents=True, exist_ok=True)
    shutil.copy2(inventory_path, backup)
    manifest = []
    bibliography = []
    rows = ['# Libros del material de apoyo', '',
            'Ocho PDF únicos correspondientes a nueve enlaces del aula. Contenido preservado por SHA-256. Datos cotejados en portada y página legal, no únicamente en nombres de descarga.', '',
            '| Libro | Autoría | Año y edición | Páginas PDF de cotejo |',
            '| --- | --- | --- | --- |']
    for old, new, digest, records, metadata in operations:
        old.rename(new)
        assert hashlib.sha256(new.read_bytes()).hexdigest() == digest
        extraction = old.with_suffix('.txt')
        if extraction.exists():
            extraction.rename(new.with_suffix('.txt'))
        for record in records:
            record['original_download_path'] = record['path']
            record['path'] = new.relative_to(SUBJECT).as_posix()
            record['bibliographic_metadata'] = metadata
        manifest.append(dict(metadata, path=new.relative_to(SUBJECT).as_posix(), sha256=digest,
                             previous_path=old.relative_to(SUBJECT).as_posix(),
                             sources=[record['source'] for record in records]))
        volume = f", volumen {metadata['volume']}" if metadata['volume'] else ''
        rows.append(f"| [{metadata['title']}{volume}]({new.name}) | {metadata['authors_bibtex']} | {metadata['year']}; edición {metadata['edition']} | {', '.join(map(str, metadata['editorial_pdf_pages']))} |")
        fields = {'author': metadata['authors_bibtex'], 'title': metadata['title'],
                  'year': metadata['year'], 'edition': metadata['edition'],
                  'file': new.relative_to(REFERENCES).as_posix()}
        if metadata['publisher']:
            fields['publisher'] = metadata['publisher']
        else:
            fields['note'] = 'Editor identificado en página legal: Víctor López Guzmán. Sello editorial pendiente de confirmación'
        if metadata['volume']:
            fields['volume'] = metadata['volume']
        if new.name.startswith('Lind-'):
            fields['note'] = 'Portada y página legal: decimoquinta edición; aviso de derechos menciona cuarta edición en español'
        bibliography.append('@book{aula_' + digest[:12] + ',\n' + ',\n'.join(f'  {key} = {{{value}}}' for key, value in fields.items()) + '\n}\n')
    rows.extend(['', 'Los dos enlaces de Estadística matemática con aplicaciones son idénticos; se conserva un PDF y ambas procedencias en el manifiesto.', '',
                 'Los escaneos de Romero y Canavos no tienen texto extraíble en sus páginas iniciales. El cotejo editorial fue visual; no se afirma OCR realizado.', '',
                 'Romero: primera edición, noviembre de 2001; el sello editorial no se infiere del logotipo universitario. Canavos: derechos de primera edición española de 1988; se observa además una impresión de 1995, que no se usa como año de edición.', '',
                 'Estos libros tienen autoría disciplinar verificada y pueden fundamentar conceptos mediante consulta del pasaje específico. No citar al aula como autora del contenido ni redistribuir los PDF públicamente.', '',
                 '[Manifiesto de organización](organizacion-libros.json) · [Bibliografía](../bibliografia-libros-material-apoyo.bib)'])
    inventory_path.write_text(json.dumps(inventory, ensure_ascii=False, indent=2), encoding='utf-8')
    (DESTINATION / 'organizacion-libros.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    (DESTINATION / 'README.md').write_text('\n'.join(rows) + '\n', encoding='utf-8')
    (REFERENCES / 'bibliografia-libros-material-apoyo.bib').write_text('\n'.join(bibliography), encoding='utf-8')
    print(json.dumps({'moved_books': len(manifest), 'original_links': sum(len(record['sources']) for record in manifest), 'hashes_preserved': True}, ensure_ascii=True))


if __name__ == '__main__':
    main()