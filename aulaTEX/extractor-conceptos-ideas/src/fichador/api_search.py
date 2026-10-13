from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import numpy as np

from .api_client import ApiConfig, create_client, embed_texts
from .preprocessing import Fragment, clip_text
from .search import SearchHit


def _hash_texts(texts: list[str], model: str) -> str:
    h = hashlib.sha256()
    h.update(model.encode("utf-8"))
    for text in texts:
        h.update(b"\0")
        h.update(text.encode("utf-8", errors="ignore"))
    return h.hexdigest()[:24]


@dataclass
class ApiEmbeddingSearchEngine:
    fragments: list[Fragment]
    config: ApiConfig
    batch_size: int = 64
    cache_dir: Path | None = Path(".cache")

    def __post_init__(self) -> None:
        self._texts = [f.text for f in self.fragments]
        self._client = create_client(self.config)
        self._embeddings = self._load_or_embed(self._texts)

    def _load_or_embed(self, texts: list[str]) -> np.ndarray:
        cache_file: Path | None = None
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            cache_file = self.cache_dir / f"embeddings_{self.config.provider}_{_hash_texts(texts, self.config.embedding_model)}.json"
            if cache_file.exists():
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                return self._normalize(np.array(data["vectors"], dtype=np.float32))

        vectors = embed_texts(self._client, self.config.embedding_model, texts, batch_size=self.batch_size)
        if cache_file:
            cache_file.write_text(json.dumps({"model": self.config.embedding_model, "vectors": vectors}), encoding="utf-8")
        return self._normalize(np.array(vectors, dtype=np.float32))

    @staticmethod
    def _normalize(vectors: np.ndarray) -> np.ndarray:
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return vectors / norms

    def _embed_query(self, query: str) -> np.ndarray:
        vector = embed_texts(self._client, self.config.embedding_model, [query], batch_size=1)[0]
        arr = np.array(vector, dtype=np.float32)
        norm = np.linalg.norm(arr)
        return arr if norm == 0 else arr / norm

    def search(self, concept: str, top_k: int = 8, threshold: float = 0.20, max_quote_chars: int = 700) -> list[SearchHit]:
        if not self.fragments:
            return []
        q = self._embed_query(concept)
        sims = self._embeddings @ q
        order = np.argsort(sims)[::-1]
        hits: list[SearchHit] = []
        seen = set()
        for idx in order:
            score = float(sims[int(idx)])
            if score < threshold:
                continue
            frag = self.fragments[int(idx)]
            quote = clip_text(frag.text, max_chars=max_quote_chars)
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
                )
            )
            if len(hits) >= top_k:
                break
        return hits
