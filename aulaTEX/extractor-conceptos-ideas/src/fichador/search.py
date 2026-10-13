from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from .preprocessing import Fragment, SPANISH_STOPWORDS, clean_for_vectorization, clip_text, extract_focus_quote, is_probable_paratext


@dataclass(frozen=True)
class SearchHit:
    concept: str
    fragment_id: str
    page: int
    score: float
    quote: str
    source_id: str = "fuente"
    source_name: str = "fuente"
    source_path: str = ""
    source_type: str = "pdf"
    location_label: str = ""
    score_details: str = ""

    @property
    def location(self) -> str:
        return self.location_label or (f"p. {self.page}" if self.source_type == "pdf" else f"bloque {self.page}")

    @property
    def source_location(self) -> str:
        return f"{self.source_name}, {self.location}"


class TfidfSearchEngine:
    """Motor local: TF-IDF + similitud coseno. No descarga modelos ni usa API."""

    def __init__(self, fragments: list[Fragment]):
        self.fragments = fragments
        self.docs = [clean_for_vectorization(f.text) for f in fragments]
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 3),
            stop_words=list(SPANISH_STOPWORDS),
            min_df=1,
            token_pattern=r"(?u)\b[a-záéíóúñü0-9][a-záéíóúñü0-9-]{1,}\b",
        )
        self.matrix = self.vectorizer.fit_transform(self.docs)

    def search(self, concept: str, top_k: int = 8, threshold: float = 0.03, max_quote_chars: int = 700) -> list[SearchHit]:
        if not self.fragments:
            return []
        normalized_concept = clean_for_vectorization(concept)
        query_vec = self.vectorizer.transform([normalized_concept])
        sims = cosine_similarity(query_vec, self.matrix).ravel()
        boosted_scores: list[tuple[int, float, float, float]] = []
        for idx, raw_score in enumerate(sims):
            frag = self.fragments[int(idx)]
            normalized_text = clean_for_vectorization(frag.text)
            if is_probable_paratext(frag.text):
                boosted_scores.append((idx, float(raw_score), -1.0, -1.0))
                continue
            literal_bonus = 0.06 if normalized_concept and normalized_concept in normalized_text else 0.0
            token_bonus = min(0.04, sum(0.01 for token in normalized_concept.split() if len(token) >= 4 and token in normalized_text))
            final_score = float(raw_score) + literal_bonus + token_bonus
            boosted_scores.append((idx, float(raw_score), literal_bonus + token_bonus, final_score))
        order = [idx for idx, _raw, _bonus, _final in sorted(boosted_scores, key=lambda item: item[3], reverse=True)]

        hits: list[SearchHit] = []
        seen = set()
        score_map = {idx: (raw, bonus, final) for idx, raw, bonus, final in boosted_scores}
        for idx in order:
            raw_score, bonus_score, score = score_map[int(idx)]
            if score < threshold:
                continue
            frag = self.fragments[int(idx)]
            quote = extract_focus_quote(frag.text, concept, max_chars=max_quote_chars)
            dedupe_key = (frag.source_id, frag.page, quote[:180].lower())
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            hits.append(
                SearchHit(
                    concept=concept,
                    fragment_id=frag.fragment_id,
                    page=frag.page,
                    score=score,
                    quote=quote,
                    source_id=frag.source_id,
                    source_name=frag.source_name,
                    source_path=frag.source_path,
                    source_type=frag.source_type,
                    location_label=frag.location_label,
                    score_details=f"tfidf={raw_score:.4f}; bonus={bonus_score:.4f}",
                )
            )
            if len(hits) >= top_k:
                break
        return hits
