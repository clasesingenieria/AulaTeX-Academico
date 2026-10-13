from __future__ import annotations

from dataclasses import dataclass
from typing import Any
import numpy as np

from .preprocessing import Fragment, clip_text
from .search import SearchHit


DEFAULT_TFHUB_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@dataclass
class TfHubSearchEngine:
    """Motor opcional: sentence-transformers con modelo multilingüe.

    Requiere requirements-tfhub.txt. La primera ejecución descarga el modelo y después queda en caché.
    También acepta una ruta local en TFHUB_MODEL.
    """

    fragments: list[Fragment]
    model_url_or_path: str = DEFAULT_TFHUB_MODEL
    batch_size: int = 32

    def __post_init__(self) -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Falta sentence-transformers. Ejecuta: pip install -r requirements-tfhub.txt") from exc

        # Los modelos de TensorFlow Hub ya no se soportan: no hay ruedas de TF para Python 3.14.
        if self.model_url_or_path.startswith(("http://tfhub.dev", "https://tfhub.dev")):
            raise RuntimeError(
                f"TFHUB_MODEL apunta a TensorFlow Hub ({self.model_url_or_path}), que ya no se soporta. "
                f"Usa un modelo de sentence-transformers, por ejemplo {DEFAULT_TFHUB_MODEL}."
            )

        self._model: Any = SentenceTransformer(self.model_url_or_path)
        self._texts = [f.text for f in self.fragments]
        self._embeddings = self._embed(self._texts)

    def _embed(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.empty((0, 0))
        return np.asarray(
            self._model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            ),
            dtype=np.float32,
        )

    def search(self, concept: str, top_k: int = 8, threshold: float = 0.20, max_quote_chars: int = 700) -> list[SearchHit]:
        if not self.fragments:
            return []
        q = self._embed([concept])[0]
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
