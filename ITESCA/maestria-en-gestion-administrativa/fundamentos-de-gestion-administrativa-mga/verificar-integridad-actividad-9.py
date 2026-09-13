"""Auditoría reproducible de solo lectura del foro 4.2; no acredita su entrega.

Compara el contenido realmente extraído del PDF con los tres TXT, además de
comprobar los bytes de sus adjuntos. La comparación textual ignora tipografía,
espacios, puntuación y mayúsculas; conserva todas las letras, cifras y su orden.
No valida por sí sola APA completa, sentido académico ni el estado de Moodle.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path


def normalized(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKC", text).casefold() if c.isalnum())


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def audit() -> dict:
    folder = Path(__file__).resolve().parent
    root = next(p for p in folder.parents if (p / "scripts/aulatex/foro_producto.py").exists())
    sys.path.insert(0, str(root))
    from scripts.aulatex.foro_producto import ForoProductoTransformer

    tex = folder / "reporte-fundamentos-de-gestion-administrativa-Actividad-9.tex"
    pdf = tex.with_suffix(".pdf")
    text = tex.read_text(encoding="utf-8")
    check(pdf.is_file(), "Falta PDF")
    attachments = re.findall(r"\\foroCopyButton\{([^}]+)\}", text)
    check(len(attachments) == 3 and len(set(attachments)) == 3, "Deben existir tres adjuntos distintos")
    paths = [root / name for name in attachments]
    check(all(p.is_file() for p in paths), "Falta un TXT")
    check(pdf.stat().st_mtime >= max(p.stat().st_mtime for p in [tex, *paths, folder / 'fundamentos-de-gestion-administrativa.bib']), "PDF desactualizado")
    sections = re.findall(r"\\section\{([^}]+)\}", text)
    check(len(sections) == 3 and sections[0] == "Introducción" and sections[-1] == "Conclusiones", "No hay tres actos")
    check(re.search(r"\\clearpage\s*\\section\{Conclusiones\}", text) is not None, "Conclusión sin página nueva")
    boxes = re.findall(r"\\begin\{forobox\}.*?\\end\{forobox\}", text, re.S)
    check(len(boxes) == 3, "Deben existir tres cajas")
    check(not ForoProductoTransformer._check_forum_apa_citation(None, text), "El verificador APA heurístico emite avisos")
    for number, box in enumerate(boxes, 1):
        check("\\textbf{Referencias}" in box and "\\hangindent" in box, f"Caja {number}: faltan referencias")
        check("¿" in box and "Saludos," in box, f"Caja {number}: falta cierre o pregunta")
    bib = (folder / 'fundamentos-de-gestion-administrativa.bib').read_text(encoding='utf-8')
    cited = {key.strip() for group in re.findall(r'\\cite[tp]?\{([^}]+)\}', text) for key in group.split(',')}
    bibkeys = set(re.findall(r'@\w+\s*\{\s*([^,]+),', bib))
    check(cited <= bibkeys and len(cited) >= 3, 'Faltan claves bibliográficas')
    raw = subprocess.check_output(['pdftotext', '-layout', str(pdf), '-'], text=True)
    check(raw.count('Copiar participación') == 3, 'PDF sin tres botones extraíbles')
    # Solo se retiran números de página aislados y el texto de los botones.
    raw = re.sub(r'(?m)^\s*\d+\s*$', '', raw).replace('Copiar participación', '')
    starts = list(re.finditer(r'Asunto:', raw))
    check(len(starts) == 3, 'No se identificaron tres intervenciones en el PDF')
    with tempfile.TemporaryDirectory(prefix='foro9-integridad-') as tmp:
        subprocess.run(['pdfdetach', '-saveall', '-o', tmp, str(pdf)], check=True, capture_output=True)
        for i, (start, path) in enumerate(zip(starts, paths), 1):
            chunk = raw[start.start():]
            end = re.search(r'(?m)^\s*\d+\.\d+\.\s+', chunk)
            check(end is not None, f'Caja {i}: no se identificó su final')
            actual = normalized(chunk[:end.start()])
            expected = normalized(path.read_text(encoding='utf-8'))
            if actual != expected:
                mismatch = next((j for j, (a, b) in enumerate(zip(actual, expected)) if a != b), min(len(actual), len(expected)))
                raise AssertionError(f'Caja {i}: diferencia PDF/TXT en {mismatch}: PDF={actual[max(0,mismatch-35):mismatch+90]!r}; TXT={expected[max(0,mismatch-35):mismatch+90]!r}')
            check((Path(tmp) / path.name).read_bytes() == path.read_bytes(), f'Adjunto {i} difiere del TXT')
    check('ARCHIVO HISTÓRICO SUSTITUIDO' in (folder/'foro-replicas-personalizadas-Actividad-9.md').read_text(), 'Variante histórica sin aviso')
    return {
        'integridad_documental': 'verificada',
        'comparacion_pdf_txt': '3/3; equivalencia alfanumérica ordenada, no identidad tipográfica',
        'adjuntos_identicos_byte_a_byte': 3,
        'citas_con_entrada_bib': sorted(cited),
        'verificador_apa_heuristico': 'sin avisos; no certifica APA completa',
        'sha256': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in [tex, pdf, *paths]},
        'limites': ['No acredita video completo', 'No acredita publicación ni calificación', 'No certifica ejecución completa de realizar-actividad'],
    }


if __name__ == '__main__':
    try:
        print(json.dumps(audit(), ensure_ascii=False, indent=2))
    except (AssertionError, OSError, subprocess.CalledProcessError) as error:
        print(f'AUDITORÍA FALLIDA: {error}', file=sys.stderr)
        sys.exit(1)