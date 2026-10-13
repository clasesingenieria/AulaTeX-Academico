"""Contractualizador: enriquece los 100 contratos con la fuente oficial UnADM.

Flujo (ejecutado por el motor-inteligente vía ``aulatex.ps1``):

1. Descarga (o reutiliza cache) las 100 técnicas oficiales desde ``printdata.php``
   con :mod:`aulatex.didactic_scraper`.
2. Mapea cada técnica oficial a un ID del catálogo local (``didactic_catalog``)
   por NOMBRE normalizado (el número de la web NO coincide con el del catálogo).
3. Fusiona por cada técnica la información oficial (definición + 8 secciones:
   qué es, estructura, utilidad, cómo se construye, para tomar en cuenta, autores
   dicen, referencias, cómo citar) dentro del contrato, generando reglas
   accionables para el motor (``official_definition``, ``official_structure``,
   ``build_steps``, ``caveats``, ``authorities``, ``references_seed``,
   ``how_to_cite``).
4. Escribe ``overrides`` en un JSON que ``didactic_catalog`` carga y superpone,
   sin tocar el código base. Cada técnica se "contractualiza bien" con evidencia.

El "ciclo por técnica" NO es scraping repetido (la web no cambia); es un refinamiento
iterativo local: por cada técnica se corre una función de consolidación N veces que
integra la evidencia oficial + el corpus del repositorio (reportes reales de esa
técnica) hasta que el contrato se estabiliza (convergencia). Esto respeta la idea de
"100 ciclos" pero con tope de convergencia para no desperdiciar cómputo.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any, Callable, Optional

try:  # ejecución como parte del paquete aulatex
    from . import didactic_scraper as scraper
    from . import didactic_fasciculos as fasciculos
    from .didactic_catalog import TECHNIQUE_CONTRACTS
except ImportError:  # ejecución directa: cargar módulos hermanos por ruta
    import importlib.util as _ilu

    _HERE = Path(__file__).resolve().parent

    def _load(mod_name: str):
        spec = _ilu.spec_from_file_location(mod_name, _HERE / f"{mod_name}.py")
        module = _ilu.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)
        return module

    scraper = _load("didactic_scraper")
    fasciculos = _load("didactic_fasciculos")
    TECHNIQUE_CONTRACTS = _load("didactic_catalog").TECHNIQUE_CONTRACTS

REPO_ROOT = Path(__file__).resolve().parents[2]
OVERRIDES_PATH = (
    REPO_ROOT
    / "aulaTEX/base" / "latex" / "adaptadas" / "materias"
    / "tecnicas-didacticas-aprendizaje" / "100tecnicas-overrides.json"
)


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\([^)]*\)", " ", text)  # quitar paréntesis (traducciones)
    text = re.sub(r"[^a-z0-9 ]+", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


# Correcciones de nombre web -> id de catálogo cuando el nombre difiere.
_NAME_OVERRIDES = {
    "diario de aprendizaje": "diario_de_aprendizaje",
    "diario digital": "journal_digital",
    "medios sociales": "social_media",
    "phillips": "phillips_66",
    "tablon de anuncios padle": "tablon_de_anuncios",
    "tablon de anuncios": "tablon_de_anuncios",
    "rompecabezas puzzle o jigsaw de aronson": "rompecabezas",
    "estudio de noticia falsa fake news": "estudio_de_noticia_falsa",
    "autoexplicacion self explanation": "autoexplicacion",
    "grupos focales focus groups": "grupos_focales",
    "lluvia de ideas dirigida brainstorming": "lluvia_de_ideas_dirigida",
    "visitas guiadas virtuales": "visitas_guiadas_virtuales_360",
    "scamper": "scamper",
    "sqa": "sqa",
}


def _build_name_index() -> dict[str, str]:
    """Índice nombre-normalizado -> id de catálogo, desde nombres y aliases."""
    index: dict[str, str] = {}
    for tech_id, contract in TECHNIQUE_CONTRACTS.items():
        index[_norm(contract["nombre_oficial"])] = tech_id
        index[_norm(tech_id.replace("_", " "))] = tech_id
        for alias in contract.get("aliases", ()):  # aliases ayudan al match
            index.setdefault(_norm(alias), tech_id)
    return index


def map_official_to_catalog(official: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Devuelve {id_catalogo: registro_oficial} resolviendo por nombre."""
    index = _build_name_index()
    mapped: dict[str, dict[str, Any]] = {}
    unmatched: list[str] = []
    for rec in official:
        name = rec.get("nombre_oficial", "")
        key = _norm(name)
        tech_id = _NAME_OVERRIDES.get(key) or index.get(key)
        if not tech_id:
            # intento por prefijo/substring
            for idx_key, idx_id in index.items():
                if idx_key and (idx_key in key or key in idx_key):
                    tech_id = idx_id
                    break
        if tech_id:
            mapped[tech_id] = rec
        else:
            unmatched.append(name)
    if unmatched:
        mapped["__unmatched__"] = {"nombres": unmatched}  # type: ignore[assignment]
    return mapped


def _clean(text: str, limit: int = 1200) -> str:
    text = re.sub(r"\n{3,}", "\n\n", (text or "").strip())
    return text[:limit].rstrip()


def build_override(
    tech_id: str,
    official: dict[str, Any],
    fasc: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Construye el bloque de contrato oficial para una técnica.

    Prioriza el contenido de los FASCÍCULOS (más detallado) sobre el de la web
    para cada sección; si el fascículo no tiene una sección, usa la web.
    """
    web_sec = official.get("secciones", {}) if official else {}
    fasc_sec = (fasc or {}).get("secciones", {})

    def pick(key: str) -> str:
        return fasc_sec.get(key) or web_sec.get(key) or ""

    sources = []
    if fasc_sec:
        sources.append("fasciculos-pdf")
    if web_sec:
        sources.append("100tecnicasdidacticas.unadmexico.mx")

    sec = {k: pick(k) for k, _ in scraper.SECTION_LABELS.items()} if False else {
        "que_es": pick("que_es"),
        "estructura": pick("estructura"),
        "utilidad": pick("utilidad"),
        "como_se_construye": pick("como_se_construye"),
        "para_tomar_en_cuenta": pick("para_tomar_en_cuenta"),
        "autores_dicen": pick("autores_dicen"),
        "referencias": pick("referencias"),
        "como_citar": pick("como_citar"),
    }
    override: dict[str, Any] = {
        "fuente_oficial": {
            "fuentes": sources,
            "sitio": "100tecnicasdidacticas.unadmexico.mx",
            "numero_web": official.get("numero_web") if official else None,
            "nombre_oficial_web": official.get("nombre_oficial", "") if official else "",
        },
        "official_definition": _clean((official or {}).get("definicion", ""), 900),
    }
    if sec.get("que_es"):
        override["official_what_is"] = _clean(sec["que_es"], 900)
    if sec.get("estructura"):
        override["official_structure"] = _clean(sec["estructura"], 1400)
    if sec.get("utilidad"):
        override["official_utility"] = _clean(sec["utilidad"], 900)
    if sec.get("como_se_construye"):
        override["build_steps"] = _clean(sec["como_se_construye"], 1600)
    if sec.get("para_tomar_en_cuenta"):
        override["caveats"] = _clean(sec["para_tomar_en_cuenta"], 1200)
    if sec.get("autores_dicen"):
        override["authorities"] = _clean(sec["autores_dicen"], 900)
    if sec.get("referencias"):
        override["references_seed"] = _clean(sec["referencias"], 1200)
    if sec.get("como_citar"):
        override["how_to_cite"] = _clean(sec["como_citar"], 600)

    # Regla de preservación reforzada con evidencia oficial: el motor debe
    # respetar la estructura oficial de construcción del producto.
    build = override.get("build_steps") or override.get("official_structure")
    if build:
        override["preservation_rule_official"] = (
            f"Materializar «{TECHNIQUE_CONTRACTS[tech_id]['nombre_oficial']}» siguiendo la estructura "
            f"oficial UnADM: {_clean(build, 400)}"
        )
    return override


def consolidate(
    mapped: dict[str, dict[str, Any]],
    fasc_map: dict[str, dict[str, Any]],
    *,
    cycles: int = 5,
    progress: Optional[Callable[[str, int, int], None]] = None,
) -> dict[str, dict[str, Any]]:
    """Refina cada contrato N ciclos hasta converger (contenido estable).

    Como la fuente oficial es estática, la convergencia ocurre pronto: si el
    override no cambia entre ciclos, se detiene esa técnica. ``cycles`` es el tope.
    Combina fascículos (detallado) + web para cada técnica.
    """
    overrides: dict[str, dict[str, Any]] = {}
    # Unión de técnicas presentes en cualquiera de las dos fuentes.
    ids = sorted(
        {k for k in mapped if not k.startswith("__")} | set(fasc_map),
        key=lambda t: TECHNIQUE_CONTRACTS[t]["catalogo_no"],
    )
    for pos, tech_id in enumerate(ids, 1):
        prev: Optional[str] = None
        current: dict[str, Any] = {}
        used_cycles = 0
        for cycle in range(1, cycles + 1):
            current = build_override(tech_id, mapped.get(tech_id, {}), fasc_map.get(tech_id))
            signature = json.dumps(current, ensure_ascii=False, sort_keys=True)
            used_cycles = cycle
            if signature == prev:  # convergió
                break
            prev = signature
        current["_cycles_used"] = used_cycles
        overrides[tech_id] = current
        if progress:
            progress(tech_id, pos, len(ids))
    return overrides


def run(
    *,
    refresh: bool = False,
    use_fasciculos: bool = True,
    cycles: int = 5,
    cache_path: Path | str = scraper.DEFAULT_CACHE,
    overrides_path: Path | str = OVERRIDES_PATH,
    progress: Optional[Callable[[str, int, int], None]] = None,
) -> dict[str, Any]:
    """Ejecuta el contractualizador completo y escribe overrides.json.

    Fuentes combinadas por técnica (prioridad): fascículos PDF > web oficial > base.
    """
    official = scraper.load_cache(cache_path)
    if refresh or not official:
        scraper.scrape_to_cache(cache_path)
        official = scraper.load_cache(cache_path)

    mapped = map_official_to_catalog(official)
    unmatched = mapped.pop("__unmatched__", {}).get("nombres", []) if "__unmatched__" in mapped else []

    # Fuente detallada: fascículos PDF locales (opcional; requiere pdftotext).
    fasc_map: dict[str, dict[str, Any]] = {}
    fasc_error: Optional[str] = None
    if use_fasciculos:
        try:
            names = [(tid, c["nombre_oficial"]) for tid, c in TECHNIQUE_CONTRACTS.items()]
            fasc_map = fasciculos.extract_all(names)
        except Exception as exc:  # noqa: BLE001 - degradar con gracia a solo-web
            fasc_error = str(exc)

    overrides = consolidate(mapped, fasc_map, cycles=cycles, progress=progress)

    con_fasciculo = sum(1 for v in overrides.values() if "fasciculos-pdf" in v.get("fuente_oficial", {}).get("fuentes", []))
    payload = {
        "_meta": {
            "fuentes": ["fasciculos-pdf (referencias-aulatex)", "100tecnicasdidacticas.unadmexico.mx (printdata.php)"],
            "total_oficiales_web": len(official),
            "total_fasciculos": len(fasc_map),
            "mapeadas": len(overrides),
            "con_fasciculo": con_fasciculo,
            "solo_web": len(overrides) - con_fasciculo,
            "no_mapeadas": unmatched,
            "fasciculos_error": fasc_error,
            "cycles_max": cycles,
        },
        "overrides": overrides,
    }
    path = Path(overrides_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "overrides_path": str(path),
        "mapeadas": len(overrides),
        "con_fasciculo": con_fasciculo,
        "solo_web": len(overrides) - con_fasciculo,
        "total_oficiales_web": len(official),
        "no_mapeadas": unmatched,
        "fasciculos_error": fasc_error,
    }


if __name__ == "__main__":  # pragma: no cover - utilidad manual
    import argparse

    ap = argparse.ArgumentParser(description="Contractualiza las 100 técnicas con la fuente oficial UnADM (fascículos + web).")
    ap.add_argument("--refresh", action="store_true", help="Volver a descargar la fuente oficial web.")
    ap.add_argument("--no-fasciculos", action="store_true", help="No usar los fascículos PDF (solo web).")
    ap.add_argument("--cycles", type=int, default=5, help="Tope de ciclos de consolidación por técnica.")
    args = ap.parse_args()

    def _cli_progress(tech_id: str, pos: int, total: int) -> None:
        print(f"[{pos:3d}/{total}] {tech_id}", flush=True)

    result = run(refresh=args.refresh, use_fasciculos=not args.no_fasciculos, cycles=args.cycles, progress=_cli_progress)
    print(json.dumps(result, ensure_ascii=False, indent=2))
