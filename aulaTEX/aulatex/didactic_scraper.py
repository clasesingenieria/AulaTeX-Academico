"""Extractor oficial de las 100 Técnicas Didácticas (UnADM).

Fuente: endpoint ``POST https://100tecnicasdidacticas.unadmexico.mx/printdata.php``
con cuerpo ``numeroDeTecnica=N`` (N = 1..100). Devuelve el HTML de la técnica
con su nombre, definición y 8 secciones en pestañas:

    ¿Qué es? · Estructura · ¿Cuál es su utilidad? · ¿Cómo se construye? ·
    Para tomar en cuenta · Los autores dicen · Referencias · ¿Cómo citar esta técnica?

IMPORTANTE: el ``numeroDeTecnica`` de la web usa un orden DISTINTO al catálogo
LaTeX local. El mapeo hacia los IDs del repositorio se hace por NOMBRE/slug
normalizado (ver ``didactic_enricher.py``), no por número.

Este módulo solo usa la biblioteca estándar (urllib + html.parser), sin
dependencias externas, para poder ejecutarse en cualquier venv del proyecto.
"""

from __future__ import annotations

import json
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Callable, Optional

PRINTDATA_URL = "https://100tecnicasdidacticas.unadmexico.mx/printdata.php"
DEFAULT_CACHE = Path(__file__).resolve().parents[2] / "aulaTEX/base" / "latex" / "adaptadas" / "materias" / "tecnicas-didacticas-aprendizaje" / "100tecnicas-oficial.json"

# Etiquetas de las 8 pestañas -> clave normalizada del contrato.
# Las claves se comparan tras _normalize() (sin acentos, sin signos ¿?, minúsculas).
SECTION_LABELS = {
    "que es": "que_es",
    "estructura": "estructura",
    "cual es su utilidad": "utilidad",
    "como se construye": "como_se_construye",
    "para tomar en cuenta": "para_tomar_en_cuenta",
    "los autores dicen": "autores_dicen",
    "referencias": "referencias",
    "como citar esta tecnica": "como_citar",
}


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("¿", "").replace("?", "").replace("¡", "").replace("!", "")
    return re.sub(r"\s+", " ", text).strip().lower()


class _TextExtractor(HTMLParser):
    """Convierte HTML a texto plano legible, preservando saltos por bloque."""

    _BLOCK = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "h5", "tr", "ul", "ol"}

    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        if tag == "li":
            self._chunks.append("\n- ")
        elif tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        if tag in self._BLOCK:
            self._chunks.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skip and data.strip():
            self._chunks.append(data)

    def get_text(self) -> str:
        raw = "".join(self._chunks)
        raw = re.sub(r"[ \t]+", " ", raw)
        raw = re.sub(r"\n\s*\n\s*\n+", "\n\n", raw)
        return raw.strip()


def _html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    return parser.get_text()


def fetch_technique_raw(numero: int, timeout: int = 20) -> str:
    """Descarga el HTML crudo de una técnica por su número oficial (1..100)."""
    body = urllib.parse.urlencode({"numeroDeTecnica": str(numero)}).encode("utf-8")
    req = urllib.request.Request(
        PRINTDATA_URL,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (AulaTeX didactic-scraper)",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "text/html,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 (URL fija oficial)
        charset = resp.headers.get_content_charset() or "utf-8"
        return resp.read().decode(charset, errors="replace")


def parse_technique_html(html: str, numero: int) -> dict[str, Any]:
    """Extrae nombre, definición y las 8 secciones desde el HTML de una técnica."""
    # Nombre oficial: primer <h4 ...>Nombre</h4>.
    name_match = re.search(r"<h4[^>]*>(.*?)</h4>", html, re.IGNORECASE | re.DOTALL)
    nombre = _html_to_text(name_match.group(1)) if name_match else ""

    # Definición: texto entre el </h4> y el primer contenedor de pestañas (div class="tab").
    definicion = ""
    if name_match:
        after = html[name_match.end():]
        tab_split = re.split(r'<div[^>]*class="tab"', after, maxsplit=1, flags=re.IGNORECASE)
        definicion = _html_to_text(tab_split[0]) if tab_split else ""

    # Secciones: los paneles tienen id="<numero>_uno", "_dos", ... y un botón con la etiqueta.
    # Estrategia: emparejar cada botón (openCity(event,'ID')) + su etiqueta, y luego el div id=ID.
    buttons = re.findall(
        r"openCity\(event,\s*'([^']+)'\)[^>]*>(.*?)</button>",
        html,
        re.IGNORECASE | re.DOTALL,
    )
    label_by_id = {bid: _normalize(_html_to_text(lbl)) for bid, lbl in buttons}

    # Localizar todos los paneles tabcontent y su posición para cortar cada uno
    # hasta el inicio del siguiente panel (los <div> anidados impiden un cierre
    # confiable por </div>, así que segmentamos por posición de apertura).
    panel_starts = [
        (mt.group(1), mt.start())
        for mt in re.finditer(
            r'<div[^>]*id="([^"]+)"[^>]*class="[^"]*tabcontent[^"]*"[^>]*>',
            html,
            re.IGNORECASE,
        )
    ]

    secciones: dict[str, str] = {}
    for idx, (panel_id, pos) in enumerate(panel_starts):
        label_norm = label_by_id.get(panel_id, "")
        key = SECTION_LABELS.get(label_norm)
        if not key:
            continue
        open_end = html.index(">", pos) + 1
        end = panel_starts[idx + 1][1] if idx + 1 < len(panel_starts) else len(html)
        segment = html[open_end:end]
        secciones[key] = _html_to_text(segment)

    return {
        "numero_web": numero,
        "nombre_oficial": nombre,
        "definicion": definicion,
        "secciones": secciones,
        "slug": _slugify(nombre),
    }


def _slugify(name: str) -> str:
    norm = _normalize(name)
    norm = re.sub(r"[^a-z0-9]+", "_", norm).strip("_")
    return norm


def scrape_all(
    *,
    start: int = 1,
    end: int = 100,
    delay: float = 0.4,
    progress: Optional[Callable[[int, int, str], None]] = None,
    timeout: int = 20,
) -> list[dict[str, Any]]:
    """Descarga y parsea las técnicas ``start..end`` del sitio oficial."""
    results: list[dict[str, Any]] = []
    for numero in range(start, end + 1):
        try:
            html = fetch_technique_raw(numero, timeout=timeout)
            parsed = parse_technique_html(html, numero)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
            parsed = {"numero_web": numero, "nombre_oficial": "", "error": str(exc), "secciones": {}}
        results.append(parsed)
        if progress:
            progress(numero, end, parsed.get("nombre_oficial", ""))
        if delay:
            time.sleep(delay)
    return results


def scrape_to_cache(
    cache_path: Path | str = DEFAULT_CACHE,
    *,
    progress: Optional[Callable[[int, int, str], None]] = None,
    **kwargs: Any,
) -> Path:
    """Descarga las 100 técnicas y las guarda como JSON canónico local."""
    data = scrape_all(progress=progress, **kwargs)
    path = Path(cache_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_cache(cache_path: Path | str = DEFAULT_CACHE) -> list[dict[str, Any]]:
    path = Path(cache_path)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


if __name__ == "__main__":  # pragma: no cover - utilidad manual
    import argparse

    ap = argparse.ArgumentParser(description="Extractor oficial de las 100 Técnicas Didácticas (UnADM).")
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=100)
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--out", default=str(DEFAULT_CACHE))
    args = ap.parse_args()

    def _cli_progress(i: int, total: int, name: str) -> None:
        print(f"[{i:3d}/{total}] {name}", flush=True)

    out = scrape_to_cache(args.out, start=args.start, end=args.end, delay=args.delay, progress=_cli_progress)
    print(f"Guardado: {out}")
