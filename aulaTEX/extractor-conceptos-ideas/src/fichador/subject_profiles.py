from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Iterable

from .preprocessing import unique_preserve_order


def _strip_accents(text: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", text) if not unicodedata.combining(ch))


def slugify(text: str) -> str:
    text = _strip_accents(text.lower())
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


SUBJECT_PROFILES: dict[str, dict] = {
    "filosofia-del-derecho": {
        "focus": [
            "derecho natural",
            "positivismo juridico",
            "escepticismo juridico",
            "jerarquia normativa",
            "filosofia del derecho",
            "interpretacion juridica",
            "sistema juridico",
            "teorias contemporaneas del derecho",
            "funcion social del derecho",
        ],
        "ban_tokens": {
            "calificacion", "porcentaje", "lineamientos", "comentario", "pagina", "paginas",
            "estudiante", "estudiantes", "actividad", "evidencia", "rubrica", "evaluacion",
        },
        "boost_tokens": {
            "derecho", "juridico", "juridica", "normativa", "filosofia", "natural",
            "positivismo", "interpretacion", "sistema", "jerarquia", "teoria", "teorias",
        },
    },
    "etica-y-moral-juridica": {
        "focus": [
            "dignidad humana",
            "derechos humanos",
            "libertad personal",
            "acceso a la justicia",
            "responsabilidad profesional",
            "ley secundaria",
            "reparacion integral",
            "moral juridica",
        ],
        "ban_tokens": {
            "calificacion", "porcentaje", "lineamientos", "comentario", "pagina", "paginas",
            "estudiante", "estudiantes", "actividad", "evidencia", "rubrica", "evaluacion",
        },
        "boost_tokens": {
            "etica", "moral", "juridica", "dignidad", "derechos", "victimas",
            "libertad", "justicia", "responsabilidad", "violacion", "humanos",
        },
    },
    "redaccion-en-contextos-virtuales": {
        "focus": [
            "comunicacion",
            "proceso comunicativo",
            "comunicacion digital",
            "redaccion academica",
            "lenguaje academico",
            "canal",
            "contexto",
            "emisor",
            "receptor",
            "mensaje",
        ],
        "ban_tokens": {
            "calificacion", "porcentaje", "lineamientos", "comentario", "pagina", "paginas",
            "estudiante", "estudiantes", "actividad", "evidencia", "rubrica", "evaluacion",
        },
        "boost_tokens": {
            "comunicacion", "digital", "redaccion", "academica", "mensaje", "canal",
            "receptor", "emisor", "contexto", "virtuales", "lenguaje",
        },
    },
}


DEFAULT_BAN_TOKENS = {
    "calificacion", "porcentaje", "lineamientos", "comentario", "pagina", "paginas",
    "actividad", "rubrica", "evaluacion", "evidencia", "entrega", "instrumento",
}


def infer_subject_slug(source_path: str | Path | None, planeacion_path: str | Path | None = None) -> str | None:
    candidates: list[Path] = []
    if source_path:
        candidates.append(Path(source_path))
    if planeacion_path:
        candidates.append(Path(planeacion_path))

    prefixes = (
        "libros-",
        "referencias-",
        "planeaciones-",
        "notas-",
        "conceptos-",
        "reporte-",
    )

    for path in candidates:
        parts = [path.name] + [p.name for p in path.parents if p.name][:6]
        for part in parts:
            low = _strip_accents(part.lower())
            for prefix in prefixes:
                if low.startswith(prefix):
                    return slugify(low[len(prefix):])
    return None


def score_concept_for_subject(concept: str, subject_slug: str | None) -> float:
    profile = SUBJECT_PROFILES.get(subject_slug or "", {})
    concept_norm = _strip_accents(concept.lower())
    words = set(concept_norm.split())
    score = 0.0

    if subject_slug and concept_norm in {_strip_accents(c.lower()) for c in profile.get("focus", [])}:
        score += 2.5

    ban_tokens = set(profile.get("ban_tokens", set())) | DEFAULT_BAN_TOKENS
    if words & ban_tokens:
        score -= 2.0 * len(words & ban_tokens)

    boost_tokens = set(profile.get("boost_tokens", set()))
    score += 0.4 * len(words & boost_tokens)

    if len(words) == 1 and next(iter(words), "") in ban_tokens:
        score -= 3.0
    if len(concept_norm) < 5:
        score -= 1.0
    return score


def filter_concepts_by_subject(concepts: Iterable[str], subject_slug: str | None, top_n: int | None = None) -> list[str]:
    scored: list[tuple[str, float]] = []
    for concept in unique_preserve_order(list(concepts)):
        score = score_concept_for_subject(concept, subject_slug)
        if score > -1.5:
            scored.append((concept, score))
    scored.sort(key=lambda item: (-item[1], item[0].lower()))
    out = [concept for concept, _ in scored]
    if top_n is not None:
        out = out[:top_n]
    return out
