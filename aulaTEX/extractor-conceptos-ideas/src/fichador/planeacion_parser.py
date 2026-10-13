from __future__ import annotations

from dataclasses import dataclass, field
import re
import unicodedata

from .preprocessing import normalize_spaces, strip_markup_noise, unique_preserve_order


SECTION_ALIASES: dict[str, tuple[str, ...]] = {
    "tema": ("tema", "contenido tematico", "contenido temático", "unidad", "bloque tematico", "bloque temático"),
    "objetivo": ("objetivo", "objetivo especifico", "objetivo específico", "proposito", "propósito", "proposito general", "propósito general"),
    "tecnica_didactica": ("tecnica didactica", "técnica didáctica", "estrategia didactica", "estrategia didáctica", "metodologia", "metodología"),
    "actividad": ("actividad", "actividad solicitada", "secuencia de trabajo", "secuencia didactica", "secuencia didáctica", "consigna operativa"),
    "bibliografia": ("bibliografia", "bibliografía", "fuentes", "referencias"),
    "criterios_entrega": ("criterios de evaluacion", "criterios de evaluación", "criterios de entrega", "evaluacion", "evaluación"),
    "aprendizajes": ("aprendizajes esperados", "aprendizajes", "resultados de aprendizaje"),
    "conceptos_clave": ("conceptos clave", "conceptos clave sugeridos", "conceptos sugeridos", "palabras clave", "conceptos"),
}

OPERATIONAL_VERBS = {
    "analizar", "argumentar", "clasificar", "comparar", "comprender", "construir", "desarrollar",
    "describir", "distinguir", "elaborar", "explicar", "identificar", "interpretar", "justificar",
    "organizar", "recuperar", "reconocer", "redactar", "relacionar", "resolver", "sintetizar", "usar",
}


@dataclass(frozen=True)
class PlaneacionAnalizada:
    raw_text: str
    normalized_text: str
    sections: dict[str, str] = field(default_factory=dict)
    tema: str = ""
    objetivo: str = ""
    tecnica_didactica: str = ""
    actividad: str = ""
    aprendizajes: tuple[str, ...] = ()
    bibliografia: tuple[str, ...] = ()
    criterios_entrega: tuple[str, ...] = ()
    conceptos_explicitos: tuple[str, ...] = ()
    verbos_operativos: tuple[str, ...] = ()
    general_context: str = ""

    def relevant_text_blocks(self) -> list[str]:
        blocks: list[str] = []
        if self.tema:
            blocks.extend([self.tema, self.tema, self.tema])
        if self.objetivo:
            blocks.extend([self.objetivo, self.objetivo])
        if self.actividad:
            blocks.extend([self.actividad, self.actividad])
        if self.tecnica_didactica:
            blocks.append(self.tecnica_didactica)
        blocks.extend(self.aprendizajes)
        blocks.extend(self.criterios_entrega)
        blocks.extend(self.conceptos_explicitos)
        if self.general_context:
            blocks.append(self.general_context)
        return [normalize_spaces(b) for b in blocks if normalize_spaces(b)]

    def detected_fields(self) -> list[str]:
        found: list[str] = []
        if self.tema:
            found.append("tema")
        if self.objetivo:
            found.append("objetivo")
        if self.tecnica_didactica:
            found.append("técnica")
        if self.actividad:
            found.append("actividad")
        if self.aprendizajes:
            found.append("aprendizajes")
        if self.bibliografia:
            found.append("bibliografía")
        if self.criterios_entrega:
            found.append("criterios")
        if self.conceptos_explicitos:
            found.append("conceptos clave")
        return found


def _strip_accents(text: str) -> str:
    return "".join(char for char in unicodedata.normalize("NFKD", text) if not unicodedata.combining(char))


def _normalize_heading(text: str) -> str:
    text = strip_markup_noise(text)
    text = re.sub(r"^\s*(?:[-*•]+|\d+[.)])\s*", "", text)
    text = text.strip().rstrip(":").strip()
    text = _strip_accents(text.lower())
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _clean_line(text: str) -> str:
    text = strip_markup_noise(text)
    text = re.sub(r"^\s*(?:[-*•]+|\d+[.)])\s*", "", text)
    return normalize_spaces(text)


def _match_section_key(label: str) -> str | None:
    normalized = _normalize_heading(label)
    if not normalized:
        return None
    for key, aliases in SECTION_ALIASES.items():
        if normalized in {_normalize_heading(alias) for alias in aliases}:
            return key
    return None


def _parse_sections(text: str) -> tuple[dict[str, str], str]:
    sections: dict[str, list[str]] = {}
    current_key: str | None = None
    general_lines: list[str] = []

    for raw_line in text.splitlines():
        line = _clean_line(raw_line)
        if not line:
            continue

        if ":" in line:
            label, remainder = line.split(":", 1)
            key = _match_section_key(label)
            if key:
                current_key = key
                sections.setdefault(key, [])
                remainder = normalize_spaces(remainder)
                if remainder:
                    sections[key].append(remainder)
                continue

        key = _match_section_key(line)
        if key:
            current_key = key
            sections.setdefault(key, [])
            continue

        if current_key:
            sections.setdefault(current_key, []).append(line)
        else:
            general_lines.append(line)

    normalized_sections = {key: normalize_spaces("\n".join(values)) for key, values in sections.items() if normalize_spaces("\n".join(values))}
    return normalized_sections, normalize_spaces("\n".join(general_lines))


def _split_items(text: str) -> list[str]:
    if not text.strip():
        return []
    parts = re.split(r"\n+|;|,|\s+y\s+(?=[a-záéíóúñ])", text)
    cleaned = []
    for part in parts:
        item = normalize_spaces(part.strip(" .:-"))
        if not item:
            continue
        cleaned.append(item)
    return unique_preserve_order(cleaned)


def _extract_inline_concepts(normalized_text: str) -> list[str]:
    patterns = [
        r"conceptos?\s+clave(?:\s+sugeridos?)?\s*:\s*(.+?)(?:\n\n|$)",
        r"debe\s+recuperar\s+conceptos?\s+de\s+(.+?)(?:\.|$)",
        r"conceptos?\s+de\s+(.+?)(?:\.|$)",
    ]
    found: list[str] = []
    for pattern in patterns:
        for match in re.finditer(pattern, normalized_text, flags=re.I | re.S):
            found.extend(_split_items(match.group(1)))
    return unique_preserve_order(found)


def _extract_operational_verbs(*texts: str) -> tuple[str, ...]:
    found: list[str] = []
    for text in texts:
        normalized = _strip_accents(text.lower())
        for token in re.findall(r"\b[a-z]{4,}(?:ar|er|ir)\b", normalized):
            if token in OPERATIONAL_VERBS:
                found.append(token)
    return tuple(unique_preserve_order(found))


def parse_planeacion_text(text: str) -> PlaneacionAnalizada:
    normalized_text = strip_markup_noise(text)
    sections, general_context = _parse_sections(normalized_text)

    tema = sections.get("tema", "")
    objetivo = sections.get("objetivo", "")
    tecnica = sections.get("tecnica_didactica", "")
    aprendizajes = tuple(_split_items(sections.get("aprendizajes", "")))
    bibliografia = tuple(_split_items(sections.get("bibliografia", "")))
    criterios = tuple(_split_items(sections.get("criterios_entrega", "")))

    actividad = sections.get("actividad", "")
    if not actividad and sections.get("aprendizajes"):
        actividad = sections["aprendizajes"]

    concepts_from_section = _split_items(sections.get("conceptos_clave", ""))
    concepts_from_text = _extract_inline_concepts(normalized_text)
    conceptos_explicitos = tuple(unique_preserve_order(concepts_from_section + concepts_from_text))

    verbos = _extract_operational_verbs(objetivo, actividad, sections.get("aprendizajes", ""), general_context)

    return PlaneacionAnalizada(
        raw_text=text,
        normalized_text=normalized_text,
        sections=sections,
        tema=tema,
        objetivo=objetivo,
        tecnica_didactica=tecnica,
        actividad=actividad,
        aprendizajes=aprendizajes,
        bibliografia=bibliografia,
        criterios_entrega=criterios,
        conceptos_explicitos=conceptos_explicitos,
        verbos_operativos=verbos,
        general_context=general_context,
    )


def summarize_planeacion_analysis(analysis: PlaneacionAnalizada) -> str:
    parts: list[str] = []
    fields = analysis.detected_fields()
    if fields:
        parts.append("campos=" + ", ".join(fields))
    if analysis.conceptos_explicitos:
        parts.append(f"conceptos_clave={len(analysis.conceptos_explicitos)}")
    if analysis.verbos_operativos:
        parts.append("verbos=" + ", ".join(analysis.verbos_operativos[:6]))
    return " | ".join(parts)


def planeacion_to_dict(analysis: PlaneacionAnalizada) -> dict:
    return {
        "tema": analysis.tema,
        "objetivo": analysis.objetivo,
        "tecnica_didactica": analysis.tecnica_didactica,
        "actividad": analysis.actividad,
        "aprendizajes": list(analysis.aprendizajes),
        "bibliografia": list(analysis.bibliografia),
        "criterios_entrega": list(analysis.criterios_entrega),
        "conceptos_explicitos": list(analysis.conceptos_explicitos),
        "verbos_operativos": list(analysis.verbos_operativos),
        "general_context": analysis.general_context,
        "sections": analysis.sections,
        "campos_detectados": analysis.detected_fields(),
        "resumen": summarize_planeacion_analysis(analysis),
    }
