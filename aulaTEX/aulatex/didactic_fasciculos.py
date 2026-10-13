"""Extractor de los 5 fascículos oficiales (PDF) de las 100 Técnicas Didácticas.

Fuente local: ``referencias-aulatex/100tecnicasdidacticas Fasciculo N - Armando Lopez Martinez.pdf``.
Los fascículos contienen el desarrollo COMPLETO de cada técnica (más detallado que
la web), con las mismas 8 secciones:

    ¿Qué es? · Estructura · ¿Cuál es su utilidad? · ¿Cómo se construye? ·
    Para tomar en cuenta · Los autores dicen · Referencias · ¿Cómo citar esta técnica?

Requiere ``pdftotext`` (incluido en TeX Live / MiKTeX). Extrae el texto a UTF-8,
segmenta por técnica usando los nombres del catálogo local como anclas y devuelve,
por técnica, un dict con sus secciones. Solo biblioteca estándar + pdftotext.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from typing import Any, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
FASCICULOS_DIR = REPO_ROOT / "referencias-aulatex"
FASCICULO_GLOB = "100tecnicasdidacticas Fasciculo *.pdf"

# Encabezados de sección tal como aparecen en los fascículos.
_SECTION_HEADERS: tuple[tuple[str, str], ...] = (
    ("que_es", "¿Qué es?"),
    ("estructura", "Estructura"),
    ("utilidad", "¿Cuál es su utilidad?"),
    ("como_se_construye", "¿Cómo se construye?"),
    ("para_tomar_en_cuenta", "Para tomar en cuenta"),
    ("autores_dicen", "Los autores dicen"),
    ("referencias", "Referencias"),
    ("como_citar", "¿Cómo citar esta técnica?"),
)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\([^)]*\)", " ", text)
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


def pdf_to_text(pdf_path: Path) -> str:
    """Extrae texto UTF-8 de un PDF usando pdftotext (-layout)."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        subprocess.run(
            ["pdftotext", "-enc", "UTF-8", "-layout", str(pdf_path), str(tmp_path)],
            check=True,
            capture_output=True,
        )
        return tmp_path.read_text(encoding="utf-8", errors="replace")
    finally:
        tmp_path.unlink(missing_ok=True)


def _dehyphenate(text: str) -> str:
    # Unir palabras cortadas por guion al final de línea: "informa-\n ción" -> "información".
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return text


# Encabezado/pie de página que pdftotext arrastra en cada página del fascículo.
_RUNNING_HEAD = re.compile(
    r"[ \t]*100\s+T[eé]cnicas\s+Did[aá]cticas\s+de\s+Ense[nñ]anza\s+y\s+Aprendizaje"
    r"(?:\s*\|\s*Fasc[ií]culo\s*\d*)?[ \t]*",
    re.IGNORECASE,
)

# Número de página suelto en su propia línea.
_PAGE_NUMBER = re.compile(r"(?m)^[ \t]*\d{1,3}[ \t]*$")

# Marcador decorativo de los fascículos, sin valor semántico.
_PULL_QUOTE = re.compile(r"(?m)^[ \t]*Para\s+recordar\.{2,3}[ \t]*$", re.IGNORECASE)


def _strip_pdf_furniture(text: str) -> str:
    """Elimina encabezados, pies y números de página del texto extraído.

    Sin esto el texto oficial que se inyecta al prompt del LLM queda salpicado de
    '100 Técnicas Didácticas ... | Fascículo 2' y números sueltos.
    """
    text = _RUNNING_HEAD.sub(" ", text)
    text = _PULL_QUOTE.sub("", text)
    text = _PAGE_NUMBER.sub("", text)
    return text


def _collapse(text: str) -> str:
    text = _dehyphenate(text)
    text = _strip_pdf_furniture(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"(?m)[ \t]+$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_sections(block: str) -> dict[str, str]:
    """Dado el texto de una técnica, separa sus 8 secciones por encabezado."""
    # Posiciones de cada encabezado dentro del bloque.
    marks: list[tuple[int, str]] = []
    for key, header in _SECTION_HEADERS:
        # (?!\w) evita que "Estructura" haga match dentro de "Estructuras textuales",
        # que truncaba la ficha de la técnica #26 a 11 caracteres.
        for m in re.finditer(re.escape(header) + r"(?!\w)", block):
            marks.append((m.start(), key))
    marks.sort()
    sections: dict[str, str] = {}
    for i, (pos, key) in enumerate(marks):
        if key in sections:
            continue  # primera aparición gana
        header = dict(_SECTION_HEADERS)[key]
        start = pos + len(header)
        end = marks[i + 1][0] if i + 1 < len(marks) else len(block)
        sections[key] = _collapse(block[start:end])
    return sections


def parse_fasciculo(text: str, technique_names: list[tuple[str, str]]) -> dict[str, dict[str, Any]]:
    """Segmenta un fascículo por técnica.

    ``technique_names``: lista de (id_catalogo, nombre_oficial) candidatos. Se
    localizan como títulos y se corta el texto de cada técnica hasta el siguiente.
    """
    # Trabajar sobre una versión normalizada (sin acentos) manteniendo el mapeo
    # de posiciones al texto original mediante un índice paralelo.
    norm_chars: list[str] = []
    pos_map: list[int] = []
    for i, ch in enumerate(text):
        nch = unicodedata.normalize("NFKD", ch)
        nch = "".join(c for c in nch if not unicodedata.combining(c)).lower()
        for c in nch:
            norm_chars.append(c)
            pos_map.append(i)
    norm_flat = "".join(norm_chars)
    # Marcador normalizado de "¿qué es?" -> "que es"
    que_es_marks = [m.start() for m in re.finditer(r"que es\b", norm_flat)]

    found: list[tuple[int, str]] = []
    for tech_id, name in technique_names:
        name_norm = _norm(name)
        if not name_norm:
            continue
        for m in re.finditer(re.escape(name_norm), norm_flat):
            # Aceptar como título si hay un "¿qué es?" dentro de ~600 chars normalizados.
            if any(0 < (q - m.end()) < 600 for q in que_es_marks):
                found.append((pos_map[m.start()], tech_id))
                break
    # Deduplicar por técnica conservando primera aparición.
    seen: set[str] = set()
    dedup: list[tuple[int, str]] = []
    for pos, tid in sorted(found):
        if tid not in seen:
            seen.add(tid)
            dedup.append((pos, tid))
    found = sorted(dedup)
    result: dict[str, dict[str, Any]] = {}
    for i, (pos, tech_id) in enumerate(found):
        end = found[i + 1][0] if i + 1 < len(found) else len(text)
        block = text[pos:end]
        sections = _split_sections(block)
        if sections:
            result[tech_id] = {"secciones": sections, "fuente": "fasciculo"}
    return result


def extract_all(
    technique_names: list[tuple[str, str]],
    *,
    fasciculos_dir: Path | str = FASCICULOS_DIR,
) -> dict[str, dict[str, Any]]:
    """Extrae y segmenta las técnicas de los 5 fascículos disponibles."""
    directory = Path(fasciculos_dir)
    combined: dict[str, dict[str, Any]] = {}
    for pdf in sorted(directory.glob(FASCICULO_GLOB)):
        text = _collapse(pdf_to_text(pdf))
        parsed = parse_fasciculo(text, technique_names)
        for tech_id, data in parsed.items():
            combined.setdefault(tech_id, data)  # primer fascículo que la contenga
    return combined
