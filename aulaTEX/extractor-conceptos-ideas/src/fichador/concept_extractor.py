from __future__ import annotations

import re
import unicodedata
from typing import Iterable

from sklearn.feature_extraction.text import TfidfVectorizer

from .preprocessing import Fragment, SPANISH_STOPWORDS, clean_for_vectorization, strip_markup_noise, unique_preserve_order, is_probable_paratext
from .planeacion_parser import PlaneacionAnalizada, parse_planeacion_text


GENERIC_CONCEPTS = {
    "actividad", "aprendizaje", "aprendizajes", "cierre", "conceptos", "conceptual", "criterio",
    "criterios", "desarrollo", "didáctica", "ejemplo", "ejemplos", "general", "inicio",
    "mapa conceptual", "objetivo", "objetivos", "planeación", "planeación didáctica", "propósito",
    "propósito general", "secuencia", "secuencia trabajo", "tema", "temas", "trabajo"
}
GENERIC_TOKENS = {
    "actividad", "actividades", "aprendizaje", "aprendizajes", "caso", "casos", "cierre", "concepto",
    "conceptos", "criterio", "criterios", "desarrollo", "didáctica", "ejemplo", "ejemplos", "esperados",
    "evaluación", "general", "inicio", "mapa", "objetivo", "objetivos", "planeación", "propósito",
    "propósitos", "recurso", "recursos", "secuencia", "tema", "temas", "trabajo"
}
BAD_EDGE_TOKENS = {
    "debe", "deben", "ejemplo", "ejemplos", "esperados", "general", "guía", "lista", "para",
    "plan", "planeación", "propósito", "secuencia", "tema"
}
VERB_LIKE_TOKENS = {
    "analizar", "comparar", "comprender", "conocer", "describir", "debe", "deben", "distinguir",
    "elaborar", "explicar", "identificar", "organizar", "reconocer", "recuperar", "relacionar",
    "resolver", "usar"
}


def _split_docs(text: str) -> list[str]:
    cleaned = strip_markup_noise(text)
    if not cleaned:
        return []
    if is_probable_paratext(cleaned):
        return []
    parts = re.split(r"\n+|(?<=[\.!?;:])\s+", cleaned)
    out: list[str] = []
    for part in parts:
        normalized = _normalize_term(part)
        if normalized and len(normalized) >= 30 and not is_probable_paratext(normalized):
            out.append(normalized)
    return out


def _strip_accents(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))


def _normalize_term(term: str) -> str:
    term = clean_for_vectorization(strip_markup_noise(term))
    term = re.sub(r"\s+", " ", term).strip()
    return term


def _doc_tokens(text: str) -> set[str]:
    return set(_normalize_term(text).split())


def _score_term(term: str, raw_score: float, docs_token_sets: list[set[str]]) -> float:
    words = term.split()
    coverage = sum(1 for tokens in docs_token_sets if all(word in tokens for word in words))
    score = raw_score
    if len(words) == 2:
        score += 0.24
    elif len(words) == 3:
        score += 0.18
    elif len(words) == 1:
        score -= 0.10
    else:
        score -= 0.12
    score += coverage * 0.04
    if any(word in GENERIC_TOKENS for word in words):
        score -= 0.12 * sum(1 for word in words if word in GENERIC_TOKENS)
    return score


def _is_useful_concept(term: str) -> bool:
    normalized = _normalize_term(term)
    if not normalized or normalized in GENERIC_CONCEPTS:
        return False
    words = normalized.split()
    if len(words) > 3:
        return False
    if any(word in SPANISH_STOPWORDS for word in words):
        return False
    if any(word in VERB_LIKE_TOKENS for word in words):
        return False
    if words[0] in BAD_EDGE_TOKENS or words[-1] in BAD_EDGE_TOKENS:
        return False
    if len(words) == 1:
        word = words[0]
        return len(word) >= 10 and word not in GENERIC_TOKENS
    if len(words) == 2 and all(word in GENERIC_TOKENS for word in words):
        return False
    if sum(1 for word in words if word in GENERIC_TOKENS) >= max(1, len(words) - 1):
        return False
    if sum(1 for word in words if len(word) <= 3) > 0:
        return False
    return True


def _is_redundant(candidate: str, accepted: list[str]) -> bool:
    candidate_words = candidate.split()
    candidate_set = set(candidate_words)
    candidate_root = _strip_accents(candidate)
    for current in accepted:
        current_words = current.split()
        current_set = set(current_words)
        current_root = _strip_accents(current)
        if candidate == current:
            return True
        if len(candidate_words) == 1 and candidate in current_set:
            return True
        if candidate_set and candidate_set.issubset(current_set):
            return True
        if candidate_root in current_root and len(candidate_words) <= len(current_words):
            return True
    return False


def _extract_from_docs(docs: list[str], top_n: int = 25) -> list[str]:
    cleaned_docs: list[str] = []
    for doc in docs:
        cleaned_docs.extend(_split_docs(doc))
    if not cleaned_docs:
        return []
    docs_token_sets = [_doc_tokens(doc) for doc in cleaned_docs]
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        stop_words=list(SPANISH_STOPWORDS),
        max_features=8000,
        min_df=1,
        token_pattern=r"(?u)\b[a-záéíóúñü0-9][a-záéíóúñü0-9-]{2,}\b",
    )
    matrix = vectorizer.fit_transform(cleaned_docs)
    scores = matrix.sum(axis=0).A1
    terms = vectorizer.get_feature_names_out()
    ranked = sorted(
        ((term, _score_term(term, score, docs_token_sets)) for term, score in zip(terms, scores)),
        key=lambda item: item[1],
        reverse=True,
    )

    candidates: list[str] = []
    for term, score in ranked:
        if score <= 0:
            continue
        if not _is_useful_concept(term):
            continue
        candidates.append(term)
        if len(candidates) >= top_n * 6:
            break

    out: list[str] = []
    for candidate in candidates:
        if _is_redundant(candidate, out):
            continue
        out.append(candidate)
        if len(out) >= top_n:
            break
    return unique_preserve_order(out)


def extract_candidate_concepts(fragments: list[Fragment], top_n: int = 25) -> list[str]:
    return _extract_from_docs([f.text for f in fragments], top_n=top_n)


def extract_candidate_concepts_from_blocks(blocks: Iterable[str], top_n: int = 20) -> list[str]:
    cleaned_blocks = [b.strip() for b in blocks if b and b.strip()]
    if len(cleaned_blocks) < 3:
        merged = "\n".join(cleaned_blocks).strip()
        cleaned_blocks = [merged] if merged else []
    return _extract_from_docs(cleaned_blocks, top_n=top_n)


def extract_candidate_concepts_from_planeacion(analysis: PlaneacionAnalizada, top_n: int = 20) -> list[str]:
    explicit = list(analysis.conceptos_explicitos)
    weighted_blocks = analysis.relevant_text_blocks()
    inferred = extract_candidate_concepts_from_blocks(weighted_blocks, top_n=max(top_n, 8))
    prioritized = unique_preserve_order(explicit + inferred)
    return prioritized[:top_n]


def extract_candidate_concepts_from_text(text: str, top_n: int = 20) -> list[str]:
    analysis = parse_planeacion_text(text)
    concepts = extract_candidate_concepts_from_planeacion(analysis, top_n=top_n)
    if concepts:
        return concepts
    blocks = [b.strip() for b in text.split("\n") if b.strip()]
    return extract_candidate_concepts_from_blocks(blocks, top_n=top_n)
