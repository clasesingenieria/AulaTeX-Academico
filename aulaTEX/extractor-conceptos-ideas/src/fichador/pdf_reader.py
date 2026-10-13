from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import re

from .pandoc_utils import normalize_text_with_pandoc, pdf_pandoc_normalization_enabled


@dataclass(frozen=True)
class PageText:
    page: int
    text: str
    source_id: str = "fuente"
    source_name: str = "fuente"
    source_path: str = ""
    source_type: str = "pdf"
    location_label: str = ""


def make_source_id(path: str | Path) -> str:
    p = Path(path)
    raw = str(p.resolve()).encode("utf-8", errors="ignore")
    digest = hashlib.sha1(raw).hexdigest()[:10]
    stem = "".join(ch if ch.isalnum() else "_" for ch in p.stem).strip("_") or "fuente"
    return f"{stem}_{digest}"


def _openable_path(path: str | Path) -> str:
    """Devuelve una ruta que PyMuPDF pueda abrir aunque supere MAX_PATH (260) en
    Windows, prefijando con \\\\?\\ la ruta absoluta larga. Sin efecto fuera de
    Windows, en rutas cortas o ya prefijadas."""
    import os
    p = str(path)
    if os.name != "nt":
        return p
    try:
        full = os.path.abspath(p)
    except OSError:
        return p
    if full.startswith("\\\\?\\") or full.startswith("\\\\.\\") or len(full) < 240:
        return p
    if full.startswith("\\\\"):
        return "\\\\?\\UNC\\" + full[2:]
    return "\\\\?\\" + full


def _normalize_block_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_block_items(page) -> list[tuple[float, float, str]]:
    data = page.get_text("dict") or {}
    raw_blocks = data.get("blocks", []) or []
    items: list[tuple[float, float, str]] = []

    for block in raw_blocks:
        if block.get("type") != 0:
            continue
        x0, y0, *_ = block.get("bbox", (0, 0, 0, 0))
        lines_text: list[str] = []
        for line in block.get("lines", []) or []:
            spans = line.get("spans", []) or []
            parts: list[str] = []
            for span in spans:
                text = span.get("text", "")
                if text:
                    parts.append(text)
            line_text = _normalize_block_text("".join(parts))
            if line_text:
                lines_text.append(line_text)
        block_text = _normalize_block_text("\n".join(lines_text))
        if block_text:
            items.append((float(y0), float(x0), block_text))

    items.sort(key=lambda item: (round(item[0], 1), round(item[1], 1)))
    return items


def extract_pdf_blocks(pdf_path: str | Path) -> list[PageText]:
    """Extrae bloques textuales ordenados desde un PDF usando PyMuPDF.

    Útil cuando se necesita preservar mejor la estructura visual de una planeación.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("Falta PyMuPDF. Ejecuta: pip install -r requirements.txt") from exc

    path = Path(pdf_path)
    source_id = make_source_id(path)
    blocks: list[PageText] = []

    with fitz.open(_openable_path(path)) as doc:
        for idx, page in enumerate(doc, start=1):
            for block_idx, (_y, _x, text) in enumerate(_extract_block_items(page), start=1):
                blocks.append(
                    PageText(
                        page=idx,
                        text=text,
                        source_id=source_id,
                        source_name=path.name,
                        source_path=str(path),
                        source_type="pdf",
                        location_label=f"p. {idx}, bloque {block_idx}",
                    )
                )
    return blocks


def extract_pages_structured(pdf_path: str | Path) -> list[PageText]:
    """Extrae texto por página preservando mejor la estructura usando bloques."""
    path = Path(pdf_path)
    source_id = make_source_id(path)
    blocks = extract_pdf_blocks(path)
    pages_map: dict[int, list[str]] = {}
    for block in blocks:
        pages_map.setdefault(block.page, []).append(block.text)

    pages: list[PageText] = []
    for page_num in sorted(pages_map):
        text = _normalize_block_text("\n\n".join(pages_map[page_num]))
        if text.strip() and pdf_pandoc_normalization_enabled():
            text = normalize_text_with_pandoc(text, from_format="markdown", to_format="plain")
        pages.append(
            PageText(
                page=page_num,
                text=text,
                source_id=source_id,
                source_name=path.name,
                source_path=str(path),
                source_type="pdf",
                location_label=f"p. {page_num}",
            )
        )
    return pages


def extract_pages(pdf_path: str | Path) -> list[PageText]:
    """Extrae texto página por página de un PDF con texto seleccionable.

    Si el PDF es escaneado como imagen, esta función no hará OCR.
    Si Pandoc está disponible, puede normalizar el texto extraído para mejorar saltos y limpieza,
    pero no reemplaza la extracción base de PyMuPDF porque Pandoc no lee PDF como formato de entrada.
    """
    try:
        import fitz  # PyMuPDF
    except ImportError as exc:
        raise RuntimeError("Falta PyMuPDF. Ejecuta: pip install -r requirements.txt") from exc

    # Preferimos extracción estructurada por bloques para preservar mejor listas,
    # encabezados y separaciones lógicas del PDF.
    return extract_pages_structured(pdf_path)
