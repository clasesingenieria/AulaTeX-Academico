from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


DERIVATIVE_ACTIONS = {
    "explain": "Explicar",
    "suggest": "Sugerencias",
    "research": "Investigar",
    "dialectic": "Dialectica",
    "proposal": "Propuesta integral",
}
DERIVATIVES_SECTION_HEADING = "## Procesamientos derivados"
DERIVATIVE_STATUS_PENDING = "pending"
DERIVATIVE_STATUS_PROCESSING = "processing"
DERIVATIVE_STATUS_COMPLETED = "completed"
DERIVATIVE_STATUS_ERROR = "error"
DERIVATIVE_STATUS_LABELS = {
    DERIVATIVE_STATUS_PENDING: "pendiente",
    DERIVATIVE_STATUS_PROCESSING: "procesando",
    DERIVATIVE_STATUS_COMPLETED: "completado",
    DERIVATIVE_STATUS_ERROR: "error",
}
DERIVATIVE_SCHEMA_VERSION = "v1"
DERIVATIVE_SECTIONS = [
    "Nucleo",
    "Desarrollo",
    "Accionables",
    "Evidencias y supuestos",
    "Sintesis breve",
]
DERIVATIVE_SECTION_ALIASES = {
    "nucleo": "Nucleo",
    "resumen ejecutivo": "Nucleo",
    "desarrollo": "Desarrollo",
    "hallazgos clave": "Desarrollo",
    "evaluacion global de tu hipotesis": "Desarrollo",
    "accionables": "Accionables",
    "implicaciones practicas": "Accionables",
    "acciones recomendadas": "Accionables",
    "acciones recomendadas para profundizar": "Accionables",
    "evidencias y supuestos": "Evidencias y supuestos",
    "preguntas abiertas": "Evidencias y supuestos",
    "sintesis breve": "Sintesis breve",
    "sintesis final": "Sintesis breve",
}


@dataclass(frozen=True)
class SavedNote:
    note_path: Path
    title: str
    daily_index_path: Path | None = None
    master_index_path: Path | None = None


def slugify(value: str) -> str:
    text = re.sub(r"[^\w-]+", "_", value.strip(), flags=re.UNICODE)
    text = re.sub(r"_+", "_", text).strip("_")
    return text.lower()[:80] or "nota"


def slugify_title(title: str) -> str:
    return slugify(title)


def _normalize_title_text(value: str) -> str:
    text = " ".join(value.strip().split())
    if not text:
        return "Nota"

    if " " not in text and any(separator in text for separator in ("_", "-")):
        text = re.sub(r"[_-]+", " ", text)
    else:
        text = text.replace("_", " ")

    text = re.sub(r"\s+", " ", text).strip(" -_:;,.")
    return text or "Nota"


def sentence_case(value: str) -> str:
    text = _normalize_title_text(value)
    if not text:
        return "Nota"

    chars = list(text.lower())
    for index, char in enumerate(chars):
        if char.isalpha():
            chars[index] = char.upper()
            break
    return "".join(chars)


def build_display_title(title: str, created_at: datetime) -> str:
    return f"{created_at.strftime('%H:%M')} - {sentence_case(title)}"


def build_title(text: str) -> str:
    first_line = next((line.strip() for line in text.splitlines() if line.strip()), "Nota")
    return _normalize_title_text(first_line)[:60]


def save_text_note(base_dir: Path, raw_text: str, source: str = "telegram_text") -> SavedNote:
    timestamp = datetime.now()
    day_dir = base_dir / timestamp.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    title = build_title(raw_text)
    filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{slugify(title)}.md"
    note_path = day_dir / filename

    content = "\n".join(
        [
            "---",
            f'title: "{title.replace(chr(34), "")}"',
            f"created_at: {timestamp.isoformat()}",
            f"source: {source}",
            "---",
            "",
            raw_text.strip(),
            "",
        ]
    )
    note_path.write_text(content, encoding="utf-8")
    return SavedNote(note_path=note_path, title=title)


def yaml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return '""'
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    return f'"{text}"'


def format_concepts_markdown(concepts: list[dict[str, str]]) -> str:
    if not concepts:
        return "- Sin conceptos extraidos."

    lines: list[str] = []
    for item in concepts:
        term = str(item.get("term", "")).strip() or "Concepto"
        definition = str(item.get("definition", "")).strip() or "Sin definicion."
        lines.append(f"- **{term}**: {definition}")
    return "\n".join(lines)


def format_related_terms_markdown(terms: list[str]) -> str:
    if not terms:
        return "- Sin terminos relacionados."
    return "\n".join(f"- {term}" for term in terms)


def unique_strings(values: list[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def concept_terms(concepts: list[Any]) -> list[str]:
    return unique_strings(
        [
            item.get("term", "")
            for item in concepts
            if isinstance(item, dict)
        ]
    )


def yaml_list(name: str, values: list[Any]) -> str:
    items = unique_strings(values)
    if not items:
        return f"{name}: []"
    lines = [f"{name}:"]
    lines.extend(f"  - {yaml_value(item)}" for item in items)
    return "\n".join(lines)


def build_note_filename(raw_title: str, created_at: datetime) -> str:
    return f"{created_at.strftime('%Y%m%d_%H%M%S')}_{slugify_title(sentence_case(raw_title))}.md"


def derivative_filename(note_path: Path, action: str) -> str:
    if action not in DERIVATIVE_ACTIONS:
        raise ValueError(f"Accion derivada no soportada: {action}")
    return f"{note_path.stem}.{action}.md"


def derivative_path(note_path: Path, action: str) -> Path:
    return note_path.with_name(derivative_filename(note_path, action))


def _default_derivative_statuses(note_path: Path) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for action in DERIVATIVE_ACTIONS:
        statuses[action] = DERIVATIVE_STATUS_COMPLETED if derivative_path(note_path, action).exists() else DERIVATIVE_STATUS_PENDING
    return statuses


def _extract_markdown_section(markdown: str, heading: str) -> str:
    start = markdown.find(heading)
    if start < 0:
        return ""
    start = markdown.find("\n", start)
    if start < 0:
        return ""
    end = markdown.find("\n## ", start + 1)
    if end < 0:
        end = len(markdown)
    return markdown[start:end].strip()


def section_text_from_markdown(markdown: str, heading: str) -> str:
    return _extract_markdown_section(markdown, heading)


def _safe_section_text(text: str) -> str:
    cleaned = str(text).strip()
    return cleaned if cleaned else "Sin contenido."


def _normalize_heading_key(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    without_accents = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", without_accents.lower()).strip()


def _extract_structured_sections_from_content(content: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_section: str | None = None
    bucket: list[str] = []
    heading_count = 0

    for raw_line in content.replace("\r\n", "\n").split("\n"):
        stripped = raw_line.strip()
        candidate = stripped[3:].strip() if stripped.startswith("## ") else stripped
        heading_key = _normalize_heading_key(candidate.rstrip(":"))
        target = DERIVATIVE_SECTION_ALIASES.get(heading_key)
        is_markdown_heading = stripped.startswith("## ") and target is not None
        is_plain_heading = (
            target is not None
            and bool(stripped)
            and len(stripped) <= 90
            and not re.match(r"^[-*]\s", stripped)
            and not re.match(r"^\d+[.)]\s", stripped)
        )

        if is_markdown_heading or is_plain_heading:
            if current_section and bucket:
                sections[current_section] = "\n".join(bucket).strip()
            current_section = target
            bucket = []
            heading_count += 1
            continue

        if current_section:
            bucket.append(raw_line.rstrip())

    if current_section and bucket:
        sections[current_section] = "\n".join(bucket).strip()

    if heading_count < 2:
        return {}
    return {name: value for name, value in sections.items() if value.strip()}


def _slice_sections_from_content(content: str) -> dict[str, str]:
    compact = " ".join(content.split())
    if not compact:
        compact = "Sin contenido."

    first_break = min(len(compact), 450)
    second_break = min(len(compact), 1100)
    tail_start = min(len(compact), 700)

    nucleus = compact[:first_break].strip()
    development = compact[:second_break].strip()
    actionables = compact[tail_start: min(len(compact), tail_start + 420)].strip() or compact[:260].strip()
    evidence = compact[min(len(compact), 280): min(len(compact), 760)].strip() or compact[:220].strip()
    synthesis = compact[:320].strip()

    return {
        "Nucleo": _safe_section_text(nucleus),
        "Desarrollo": _safe_section_text(development),
        "Accionables": _safe_section_text(actionables),
        "Evidencias y supuestos": _safe_section_text(evidence),
        "Sintesis breve": _safe_section_text(synthesis),
    }


def _derive_sections_from_content(content: str) -> dict[str, str]:
    structured = _extract_structured_sections_from_content(content)
    if not structured:
        return _slice_sections_from_content(content)

    fallback = _slice_sections_from_content(content)
    result: dict[str, str] = {}
    for name in DERIVATIVE_SECTIONS:
        result[name] = _safe_section_text(structured.get(name, "") or fallback[name])
    return result


def normalize_derivative_sections(content: str) -> dict[str, str]:
    return _derive_sections_from_content(content)


def render_derivative_sections_markdown(sections: dict[str, str]) -> str:
    lines: list[str] = []
    for name in DERIVATIVE_SECTIONS:
        value = _safe_section_text(str(sections.get(name, "")))
        lines.extend([f"## {name}", "", value, ""])
    return "\n".join(lines).rstrip() + "\n"


def _parse_derivative_statuses(note_path: Path, markdown: str) -> dict[str, str]:
    statuses = _default_derivative_statuses(note_path)
    section = _extract_markdown_section(markdown, DERIVATIVES_SECTION_HEADING)
    if not section:
        return statuses

    labels_to_actions = {label: action for action, label in DERIVATIVE_ACTIONS.items()}
    for line in section.splitlines():
        text = line.strip()
        if not text.startswith("- "):
            continue
        label, _, value = text[2:].partition(":")
        action = labels_to_actions.get(label.strip())
        if not action:
            continue
        current_derivative_path = derivative_path(note_path, action)
        normalized_value = value.strip()
        if f"]({current_derivative_path.name})" in normalized_value or current_derivative_path.exists():
            statuses[action] = DERIVATIVE_STATUS_COMPLETED
            continue
        for status, rendered in DERIVATIVE_STATUS_LABELS.items():
            if normalized_value.casefold() == rendered:
                statuses[action] = status
                break
    return statuses


def read_note_derivative_statuses(note_path: Path) -> dict[str, str]:
    if not note_path.exists():
        raise FileNotFoundError(f"No existe la nota origen: {note_path}")
    return _parse_derivative_statuses(note_path, note_path.read_text(encoding="utf-8"))


def _build_derivatives_section(note_path: Path, statuses: dict[str, str] | None = None) -> str:
    current_statuses = _default_derivative_statuses(note_path)
    if statuses:
        current_statuses.update(statuses)

    lines = [DERIVATIVES_SECTION_HEADING, ""]
    for action, label in DERIVATIVE_ACTIONS.items():
        current_path = derivative_path(note_path, action)
        state = current_statuses.get(action, DERIVATIVE_STATUS_PENDING)
        if state == DERIVATIVE_STATUS_COMPLETED and current_path.exists():
            lines.append(f"- {label}: [{current_path.name}]({current_path.name})")
        elif state == DERIVATIVE_STATUS_PROCESSING:
            lines.append(f"- {label}: {DERIVATIVE_STATUS_LABELS[DERIVATIVE_STATUS_PROCESSING]}")
        elif state == DERIVATIVE_STATUS_ERROR:
            lines.append(f"- {label}: {DERIVATIVE_STATUS_LABELS[DERIVATIVE_STATUS_ERROR]}")
        else:
            lines.append(f"- {label}: {DERIVATIVE_STATUS_LABELS[DERIVATIVE_STATUS_PENDING]}")
    return "\n".join(lines)


def _replace_markdown_section(markdown: str, heading: str, replacement: str) -> str:
    start = markdown.find(heading)
    if start < 0:
        return markdown.rstrip() + "\n\n" + replacement.strip() + "\n"

    section_end = markdown.find("\n## ", start + len(heading))
    if section_end < 0:
        section_end = len(markdown)

    prefix = markdown[:start].rstrip()
    suffix = markdown[section_end:].lstrip("\n")
    updated = prefix + "\n\n" + replacement.strip() + "\n"
    if suffix:
        updated += "\n" + suffix
    return updated


def refresh_note_derivative_links(note_path: Path) -> Path:
    markdown = note_path.read_text(encoding="utf-8")
    statuses = _parse_derivative_statuses(note_path, markdown)
    for action in DERIVATIVE_ACTIONS:
        current_path = derivative_path(note_path, action)
        if current_path.exists():
            statuses[action] = DERIVATIVE_STATUS_COMPLETED
        elif statuses.get(action) == DERIVATIVE_STATUS_COMPLETED:
            statuses[action] = DERIVATIVE_STATUS_PENDING
    updated = _replace_markdown_section(markdown, DERIVATIVES_SECTION_HEADING, _build_derivatives_section(note_path, statuses))
    if updated != markdown:
        note_path.write_text(updated, encoding="utf-8")
    return note_path


def set_note_derivative_status(note_path: Path, action: str, status: str) -> Path:
    if action not in DERIVATIVE_ACTIONS:
        raise ValueError(f"Accion derivada no soportada: {action}")
    if status not in DERIVATIVE_STATUS_LABELS:
        raise ValueError(f"Estado derivado no soportado: {status}")
    if not note_path.exists():
        raise FileNotFoundError(f"No existe la nota origen: {note_path}")

    markdown = note_path.read_text(encoding="utf-8")
    statuses = _parse_derivative_statuses(note_path, markdown)
    statuses[action] = status
    updated = _replace_markdown_section(markdown, DERIVATIVES_SECTION_HEADING, _build_derivatives_section(note_path, statuses))
    if updated != markdown:
        note_path.write_text(updated, encoding="utf-8")
    return note_path


def _read_note_title(note_path: Path) -> str:
    markdown = note_path.read_text(encoding="utf-8")
    return next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), note_path.stem)


def build_derivative_display_title(note_title: str, action: str) -> str:
    if action not in DERIVATIVE_ACTIONS:
        raise ValueError(f"Accion derivada no soportada: {action}")
    base_title = " ".join(str(note_title).strip().split()) or "Nota"
    return f"{base_title} · {DERIVATIVE_ACTIONS[action]}"


def build_derivative_markdown(
    note_path: Path,
    action: str,
    content: str,
    note_title: str | None = None,
    *,
    extra_metadata: dict[str, Any] | None = None,
) -> str:
    if action not in DERIVATIVE_ACTIONS:
        raise ValueError(f"Accion derivada no soportada: {action}")

    label = DERIVATIVE_ACTIONS[action]
    title = (note_title or _read_note_title(note_path)).strip() or note_path.stem
    display_title = build_derivative_display_title(title, action)
    body = content.strip()
    sections = _derive_sections_from_content(body)
    metadata = {
        "action": action,
        "label": label,
        "schema_version": DERIVATIVE_SCHEMA_VERSION,
        "created_at": datetime.now().isoformat(),
        "source_note": note_path.name,
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    return (
        f"# {display_title}\n\n"
        f"Nota origen: [{title}]({note_path.name})\n\n"
        f"## Metadata\n\n"
        f"{json.dumps(metadata, ensure_ascii=False, indent=2)}\n\n"
        f"{render_derivative_sections_markdown(sections)}"
    )


def save_note_derivative(
    note_path: Path,
    action: str,
    content: str,
    note_title: str | None = None,
    *,
    extra_metadata: dict[str, Any] | None = None,
) -> Path:
    if not note_path.exists():
        raise FileNotFoundError(f"No existe la nota origen: {note_path}")

    output_path = derivative_path(note_path, action)
    markdown = build_derivative_markdown(
        note_path,
        action,
        content,
        note_title=note_title,
        extra_metadata=extra_metadata,
    )
    output_path.write_text(markdown, encoding="utf-8")
    refresh_note_derivative_links(note_path)
    return output_path


def build_note_markdown(payload: dict[str, Any], created_at: datetime, note_filename: str | None = None) -> str:
    raw_title = str(payload.get("title", "Nota")).strip() or "Nota"
    title = build_display_title(raw_title, created_at)
    text_type = str(payload.get("text_type", "nota_libre")).strip() or "nota_libre"
    corrected_text = str(payload.get("corrected_text", "")).strip()
    concepts = payload.get("concepts") if isinstance(payload.get("concepts"), list) else []
    related_terms = payload.get("related_terms") if isinstance(payload.get("related_terms"), list) else []
    note_key = slugify_title(sentence_case(raw_title))
    tag_terms = concept_terms(concepts)
    note_path = Path(note_filename or build_note_filename(raw_title, created_at))

    return f"""---
id: {yaml_value(created_at.strftime('%Y%m%d%H%M%S'))}
title: {yaml_value(title)}
key: {yaml_value(note_key)}
created_at: {yaml_value(created_at.isoformat())}
text_type: {yaml_value(text_type)}
{yaml_list("tags", tag_terms)}
{yaml_list("related_terms", related_terms)}
---

# {title}

## Nota limpia

{corrected_text}

## Conceptos clave

{format_concepts_markdown(concepts)}

## Terminos relacionados

{format_related_terms_markdown([str(term) for term in related_terms])}

{_build_derivatives_section(note_path)}
"""


def save_note(base_dir: Path, analysis: dict[str, Any]) -> SavedNote:
    created_at = datetime.now()
    day_dir = base_dir / created_at.strftime("%Y-%m-%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    raw_title = str(analysis.get("title", "Nota")).strip() or "Nota"
    title = build_display_title(raw_title, created_at)
    filename = build_note_filename(raw_title, created_at)
    note_path = day_dir / filename
    note_path.write_text(build_note_markdown(analysis, created_at, note_filename=filename), encoding="utf-8")

    daily_index_path = day_dir / "index.md"
    note_entry = f"- [{title}]({filename})\n"
    if daily_index_path.exists():
        current_index = daily_index_path.read_text(encoding="utf-8")
    else:
        current_index = f"# Indice de notas - {created_at.strftime('%Y-%m-%d')}\n\n"
    daily_index_path.write_text(current_index + note_entry, encoding="utf-8")

    master_index_path = base_dir / "index.json"
    if master_index_path.exists():
        try:
            index_data = json.loads(master_index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index_data = {"notes": []}
    else:
        index_data = {"notes": []}

    index_data.setdefault("notes", []).append(
        {
            "date": created_at.strftime("%Y-%m-%d"),
            "time": created_at.strftime("%H:%M:%S"),
            "title": title,
            "key": slugify_title(sentence_case(raw_title)),
            "text_type": str(analysis.get("text_type", "nota_libre")).strip() or "nota_libre",
            "path": str(note_path.relative_to(base_dir)),
            "tags": concept_terms(analysis.get("concepts", [])),
            "related_terms": unique_strings(analysis.get("related_terms", [])),
        }
    )
    master_index_path.write_text(json.dumps(index_data, ensure_ascii=False, indent=2), encoding="utf-8")

    return SavedNote(
        note_path=note_path,
        title=title,
        daily_index_path=daily_index_path,
        master_index_path=master_index_path,
    )
