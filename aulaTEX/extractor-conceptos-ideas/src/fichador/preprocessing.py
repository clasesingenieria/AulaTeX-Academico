from __future__ import annotations

from dataclasses import dataclass
import re
from .pdf_reader import PageText


SPANISH_STOPWORDS = {
    "a", "al", "algo", "algunas", "algunos", "ante", "antes", "aquel", "aquella",
    "aquellas", "aquello", "aquellos", "aquí", "así", "cada", "como", "con", "contra",
    "cual", "cuando", "de", "del", "desde", "dicha", "dichas", "dicho", "dichos",
    "donde", "durante", "e", "el", "ella", "ellas", "ellos", "en", "entre", "era",
    "eran", "es", "esa", "esas", "ese", "eso", "esos", "esta", "estaba", "estado",
    "están", "estar", "este", "esto", "estos", "fue", "fueron", "ha", "han", "hasta",
    "hay", "la", "las", "le", "les", "lo", "los", "más", "me", "mediante", "mi", "mis",
    "misma", "mismas", "mismo", "mismos", "muy", "no", "nos", "o", "para", "pero",
    "por", "porque", "puede", "pueden", "que", "se", "ser", "si", "sin", "sobre", "son",
    "su", "sus", "también", "te", "tiene", "tienen", "través", "un", "una", "uno",
    "unos", "y", "ya", "forma", "manera", "solo", "sólo"
}

PARATEXT_PATTERNS = [
    r"esta obra forma parte del acervo",
    r"biblioteca juridica virtual",
    r"libro completo en",
    r"www\.",
    r"https?://",
    r"isbn",
    r"todos los derechos reservados",
    r"impreso en",
    r"editorial",
    r"indice$",
    r"^indice",
    r"^índice",
    r"^contenido",
    r"^tabla de contenido",
    r"^bibliografia",
    r"^bibliografía",
    r"^referencias",
    r"^anexo",
    r"^prologo$",
    r"^prólogo$",
    r"^capitulo [ivxlcdm0-9]+$",
    r"^capítulo [ivxlcdm0-9]+$",
    r"pagina \d+ de \d+",
    r"página \d+ de \d+",
]


@dataclass(frozen=True)
class Fragment:
    fragment_id: str
    page: int
    text: str
    source_id: str = "fuente"
    source_name: str = "fuente"
    source_path: str = ""
    source_type: str = "pdf"
    location_label: str = ""

    @property
    def location(self) -> str:
        return self.location_label or (f"p. {self.page}" if self.source_type == "pdf" else f"bloque {self.page}")


def normalize_spaces(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_for_vectorization(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-záéíóúñü0-9\s-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_markup_noise(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"^\s{0,3}[-*+]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"`{1,3}", "", text)
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1", text)
    return normalize_spaces(text)


def _looks_like_toc_line(line: str) -> bool:
    raw = normalize_spaces(line)
    if not raw:
        return False
    lowered = raw.lower()
    if re.search(r"\.{3,}\s*\d+$", lowered):
        return True
    if re.search(r"\b\d+\s*$", lowered) and len(lowered.split()) <= 8:
        return True
    if lowered.startswith(("capítulo ", "capitulo ", "sección ", "seccion ")) and len(lowered.split()) <= 8:
        return True
    if raw.isupper() and len(raw.split()) <= 8:
        return True
    return False


def is_probable_paratext(text: str) -> bool:
    cleaned = strip_markup_noise(text)
    if not cleaned:
        return True

    lowered = cleaned.lower()
    score = 0

    for pattern in PARATEXT_PATTERNS:
        if re.search(pattern, lowered, flags=re.I):
            score += 1

    lines = [normalize_spaces(line) for line in cleaned.splitlines() if normalize_spaces(line)]
    short_lines = sum(1 for line in lines if len(line.split()) <= 5)
    toc_like = sum(1 for line in lines if _looks_like_toc_line(line))
    url_count = len(re.findall(r"https?://|www\.", lowered))

    if url_count >= 1:
        score += 1
    if url_count >= 2:
        score += 2
    if toc_like >= 2:
        score += 2
    if lines and short_lines / max(1, len(lines)) >= 0.6:
        score += 1

    alpha_chars = sum(1 for ch in cleaned if ch.isalpha())
    total_chars = max(1, len(cleaned))
    alpha_ratio = alpha_chars / total_chars
    if alpha_ratio < 0.45:
        score += 1

    if len(cleaned) < 90 and (toc_like >= 1 or url_count >= 1):
        score += 2

    # Cabeceras corridas y títulos con numeración de página.
    title_like_words = sum(1 for token in cleaned.split() if token[:1].isupper())
    digit_tokens = sum(1 for token in cleaned.split() if any(ch.isdigit() for ch in token))
    if len(cleaned) < 100 and title_like_words >= 3 and digit_tokens >= 1:
        score += 2
    if len(cleaned.split()) <= 10 and digit_tokens >= 1 and title_like_words >= 2:
        score += 2

    return score >= 3


def _split_sentences(text: str) -> list[str]:
    cleaned = strip_markup_noise(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[\.!?])\s+(?=[A-ZÁÉÍÓÚÑ0-9])", cleaned)
    return [normalize_spaces(p) for p in parts if normalize_spaces(p)]


def extract_focus_quote(text: str, concept: str, max_chars: int = 700) -> str:
    sentences = _split_sentences(text)
    if not sentences:
        return clip_text(strip_markup_noise(text), max_chars=max_chars)

    concept_words = [w for w in clean_for_vectorization(concept).split() if len(w) >= 3]
    best_idx = -1
    best_score = -1
    for idx, sentence in enumerate(sentences):
        normalized = clean_for_vectorization(sentence)
        score = sum(3 for w in concept_words if f" {w} " in f" {normalized} ")
        if clean_for_vectorization(concept) and clean_for_vectorization(concept) in normalized:
            score += 5
        if score > best_score:
            best_score = score
            best_idx = idx

    if best_idx < 0:
        return clip_text(" ".join(sentences), max_chars=max_chars)

    chosen = [sentences[best_idx]]
    current = len(chosen[0])
    for neighbor in (best_idx - 1, best_idx + 1):
        if 0 <= neighbor < len(sentences):
            candidate = sentences[neighbor]
            if current + 1 + len(candidate) <= max_chars:
                if neighbor < best_idx:
                    chosen.insert(0, candidate)
                else:
                    chosen.append(candidate)
                current += 1 + len(candidate)
    return clip_text(" ".join(chosen), max_chars=max_chars)


def split_page_into_fragments(page: PageText, max_chars: int = 1200, min_chars: int = 160) -> list[Fragment]:
    """Divide una página/bloque en fragmentos citables y conserva metadatos de origen."""
    text = strip_markup_noise(page.text)
    if not text:
        return []

    # Intenta cortar por párrafos y oraciones; conserva suficiente contexto para que la cita tenga sentido.
    raw_parts = re.split(r"\n\s*\n|(?<=[\.!?])\s+(?=[A-ZÁÉÍÓÚÑ])", text)
    parts = [normalize_spaces(p) for p in raw_parts if normalize_spaces(p)]

    fragments: list[str] = []
    buffer = ""
    for part in parts:
        if len(part) > max_chars:
            if buffer:
                fragments.append(buffer.strip())
                buffer = ""
            for start in range(0, len(part), max_chars):
                chunk = part[start:start + max_chars].strip()
                if len(chunk) >= min_chars:
                    fragments.append(chunk)
            continue

        candidate = f"{buffer} {part}".strip() if buffer else part
        if len(candidate) <= max_chars:
            buffer = candidate
        else:
            if len(buffer) >= min_chars:
                fragments.append(buffer.strip())
            buffer = part

    if len(buffer) >= min_chars:
        fragments.append(buffer.strip())

    fragments = [fragment for fragment in fragments if not is_probable_paratext(fragment)]

    safe_source = re.sub(r"[^a-zA-Z0-9_-]+", "_", page.source_id).strip("_") or "fuente"
    return [
        Fragment(
            fragment_id=f"{safe_source}_b{page.page:04d}_f{i:03d}",
            page=page.page,
            text=f,
            source_id=page.source_id,
            source_name=page.source_name,
            source_path=page.source_path,
            source_type=page.source_type,
            location_label=page.location_label,
        )
        for i, f in enumerate(fragments, start=1)
    ]


def build_fragments(pages: list[PageText], max_chars: int = 1200, min_chars: int = 160) -> list[Fragment]:
    out: list[Fragment] = []
    for page in pages:
        if is_probable_paratext(page.text):
            continue
        out.extend(split_page_into_fragments(page, max_chars=max_chars, min_chars=min_chars))
    return out


def clip_text(text: str, max_chars: int = 700) -> str:
    text = strip_markup_noise(text).replace("\n", " ")
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:") + "..."


def load_concept_lines(path: str | None) -> list[str]:
    if not path:
        return []
    p = path.strip()
    if not p:
        return []
    from pathlib import Path
    fp = Path(p)
    if not fp.exists() or not fp.is_file():
        return []
    concepts: list[str] = []
    with fp.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            concepts.append(line)
    return unique_preserve_order(concepts)


def unique_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        text = " ".join(str(item).strip().split())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
    return out
