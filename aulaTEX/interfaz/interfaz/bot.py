from __future__ import annotations

import atexit
import asyncio
from contextlib import asynccontextmanager
import json
import logging
import os
import re
from shutil import copy2
import socket
import subprocess
import tempfile
import uuid
from itertools import count
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes, MessageHandler, filters

from .analyze import analyze_text
from .azure_openai_client import invoke_chat
from .config import load_settings, settings_for_llm_provider, validate_settings
from .document_reader import SUPPORTED_DOCUMENT_SUFFIXES, read_document_text
from .intelligent_dispatch import (
    build_editorial_proposal,
    execute_intelligent_dispatch_plan,
    extract_intelligent_instruction,
    format_dispatch_plan_markdown,
    format_dispatch_summary,
    format_motor_capabilities_markdown,
    instruction_help_text,
    motor_capabilities,
    plan_intelligent_dispatch,
    run_intelligent_dispatch,
)
from .notes import (
    DERIVATIVE_STATUS_COMPLETED,
    DERIVATIVE_STATUS_ERROR,
    DERIVATIVE_STATUS_PENDING,
    DERIVATIVE_STATUS_PROCESSING,
    build_derivative_display_title,
    SavedNote,
    derivative_path,
    normalize_derivative_sections,
    read_note_derivative_statuses,
    render_derivative_sections_markdown,
    save_note,
    save_note_derivative,
    set_note_derivative_status,
)
from .polly_tts import polly_audio_enabled, synthesize_text_to_single_mp3
from .transcribe import transcribe_audio

SETTINGS = load_settings()
_INSTANCE_LOCK_SOCKET: socket.socket | None = None
NOTE_ACTION_PREFIX = "note_action"
MOTOR_ACTION_PREFIX = "motor_action"
NOTE_ACTIONS = {
    "play": "Play",
    "explain": "Explicar",
    "suggest": "Sugerencias",
    "research": "Investigar",
    "dialectic": "Dialectica",
    "proposal": "Propuesta",
    "realize": "Realizar",
}
PLAY_SEQUENCE = ["explain", "suggest", "research", "dialectic"]
DERIVATIVE_ACTION_PROVIDERS = {
    "explain": "claude-foundry",
    "suggest": "gpt-pro",
    "research": "codex",
    "dialectic": "model-router",
    "proposal": "model-router",
}
DERIVATIVE_STATUS_ICONS = {
    DERIVATIVE_STATUS_PENDING: "⌛",
    DERIVATIVE_STATUS_PROCESSING: "⏳",
    DERIVATIVE_STATUS_COMPLETED: "✅",
    DERIVATIVE_STATUS_ERROR: "⚠",
}
DERIVATIVE_JOB_PRIORITIES = {
    "play": 2,
    "explain": 3,
    "suggest": 4,
    "research": 5,
    "dialectic": 6,
    "proposal": 7,
}
_NOTE_CONTEXT_REGISTRY: dict[str, dict] = {}
_DERIVATIVE_JOB_QUEUE: asyncio.PriorityQueue[tuple[int, int, tuple[str, str, object | None]]] | None = None
_DERIVATIVE_PROCESSOR_TASK: asyncio.Task | None = None
_DERIVATIVE_PROCESSOR_LOOP: asyncio.AbstractEventLoop | None = None
_DERIVATIVE_JOB_ORDER = count()
_TELEGRAM_SEND_LOCK: asyncio.Lock | None = None
_DERIVATIVE_SAVE_LOCK: asyncio.Lock | None = None
_FOREGROUND_NOTE_EVENT: asyncio.Event | None = None
_FOREGROUND_NOTE_COUNT = 0
_TELEGRAM_SEND_LOOP: asyncio.AbstractEventLoop | None = None
LOG = logging.getLogger("notas.bot")

DERIVATIVE_SCHEMA_VERSION = "v1"
DERIVATIVE_FILTER_PATTERNS = {
    "common": [
        (re.compile(r"\r\n?"), "\n"),
        (re.compile(r"[ \t]+\n"), "\n"),
        (re.compile(r"\n{3,}"), "\n\n"),
    ],
    "telegram": [
        (re.compile(r"^\s*(Integraci[oó]n operativa|Regla pr[aá]ctica|Pregunta abierta):\s*", re.IGNORECASE | re.MULTILINE), ""),
    ],
    "audio": [
        (re.compile(r"^\s*(Integraci[oó]n operativa|Regla pr[aá]ctica|Pregunta abierta|Evidencias disponibles|Supuestos usados|Sesgos posibles(?: del an[aá]lisis)?|L[ií]mites):\s*", re.IGNORECASE | re.MULTILINE), ""),
    ],
    "clipboard": [
        (re.compile(r"^\s*(Integraci[oó]n operativa|Regla pr[aá]ctica|Pregunta abierta|Evidencias disponibles|Supuestos usados|Sesgos posibles(?: del an[aá]lisis)?|L[ií]mites):\s*", re.IGNORECASE | re.MULTILINE), ""),
    ],
}
NOTE_ACTION_KEYBOARD_EDIT_ATTEMPTS = 6
PLAY_AUDIO_DIR_NAME = "play"


def acquire_instance_lock() -> None:
    """Prevent two local polling instances from using the same Telegram token."""
    global _INSTANCE_LOCK_SOCKET
    if _INSTANCE_LOCK_SOCKET is not None:
        return

    lock_host = os.getenv("BOT_INSTANCE_LOCK_HOST", "127.0.0.1")
    lock_port = int(os.getenv("BOT_INSTANCE_LOCK_PORT", "58731"))
    lock_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if hasattr(socket, "SO_EXCLUSIVEADDRUSE"):
        lock_socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)

    try:
        lock_socket.bind((lock_host, lock_port))
    except OSError as exc:
        lock_socket.close()
        raise RuntimeError(
            "Ya hay otra instancia local del bot ejecutandose. "
            f"No se pudo adquirir el lock {lock_host}:{lock_port}."
        ) from exc

    lock_socket.listen(1)
    _INSTANCE_LOCK_SOCKET = lock_socket
    atexit.register(release_instance_lock)


def release_instance_lock() -> None:
    global _INSTANCE_LOCK_SOCKET
    if _INSTANCE_LOCK_SOCKET is None:
        return
    _INSTANCE_LOCK_SOCKET.close()
    _INSTANCE_LOCK_SOCKET = None


def _format_transcript_preview(transcript: str, limit: int | None = 1200, preserve_linebreaks: bool = False) -> str:
    if preserve_linebreaks:
        normalized = _normalize_channel_text(transcript)
    else:
        normalized = " ".join(transcript.split())
    if limit is None or len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3].rstrip() + "..."


def _preserve_visible_note_linebreaks(text_type: str) -> bool:
    return text_type in {"cuestionario", "problema_enunciado", "procedimental", "lirico"}


def _format_note_reply(analysis: dict, saved: SavedNote, limit: int | None = None, clipboard_copied: bool | None = None) -> str:
    payload = _load_note_delivery_payload(saved, analysis)
    title = str(payload.get("title", saved.title)).strip() or saved.title
    text_type = str(payload.get("text_type", "nota_libre")).strip() or "nota_libre"
    corrected_text = _format_transcript_preview(
        str(payload.get("corrected_text", "")),
        limit=limit,
        preserve_linebreaks=_preserve_visible_note_linebreaks(text_type),
    )
    concepts = payload.get("concepts", []) if isinstance(payload.get("concepts"), list) else []

    lines = [title, "", corrected_text]
    if concepts:
        lines.extend(["", "Conceptos clave:"])
        for item in concepts[:6]:
            if not isinstance(item, dict):
                continue
            term = str(item.get("term", "")).strip()
            definition = str(item.get("definition", "")).strip()
            if term:
                lines.append(f"- {term}: {definition}" if definition else f"- {term}")

    return "\n".join(lines)


def _copy_text_to_clipboard(text: str) -> bool:
    clean_text = text.strip()
    if not clean_text:
        return False
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", "Set-Clipboard -Value ([Console]::In.ReadToEnd())"],
            input=clean_text,
            text=True,
            capture_output=True,
            timeout=10,
            check=True,
        )
        return True
    except Exception:
        return False


def _copy_clean_note_to_clipboard(analysis: dict) -> bool:
    note_path = Path(str(analysis.get("_note_path", "")).strip()) if analysis.get("_note_path") else None
    if note_path and note_path.exists():
        try:
            payload = _parse_note_markdown(note_path.read_text(encoding="utf-8"))
            return _copy_text_to_clipboard(str(payload.get("corrected_text", "")))
        except Exception:
            pass
    return _copy_text_to_clipboard(str(analysis.get("corrected_text", "")))


def _build_note_audio_text(analysis: dict, saved: SavedNote, limit: int | None = None) -> str:
    """Construye una version hablada de la nota, evitando encabezados tecnicos y metadata."""
    payload = _load_note_delivery_payload(saved, analysis)
    title = str(payload.get("title", saved.title)).strip()
    corrected_text = _format_transcript_preview(str(payload.get("corrected_text", "")), limit=limit)
    concepts = payload.get("concepts", []) if isinstance(payload.get("concepts"), list) else []

    lines: list[str] = []
    if title:
        lines.append(title)
    if corrected_text:
        lines.append(corrected_text)

    concept_lines: list[str] = []
    for item in concepts[:3]:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", "")).strip()
        definition = str(item.get("definition", "")).strip()
        if term and definition:
            concept_lines.append(f"{term}: {definition}")
        elif term:
            concept_lines.append(term)

    if concept_lines:
        lines.append("Conceptos clave.")
        lines.extend(concept_lines)

    return "\n".join(line for line in lines if line).strip()


def _note_id_from_saved(saved: SavedNote) -> str:
    parts = saved.note_path.stem.split("_", 2)
    if len(parts) >= 2:
        return f"{parts[0]}_{parts[1]}"
    return saved.note_path.stem[:24]


def _store_note_context(context: ContextTypes.DEFAULT_TYPE | None, note_id: str, analysis: dict, saved: SavedNote) -> None:
    note_context = {
        "title": saved.title,
        "note_path": str(saved.note_path),
        "text_type": str(analysis.get("text_type", "nota_libre")).strip() or "nota_libre",
        "corrected_text": str(analysis.get("corrected_text", "")).strip(),
        "concepts": analysis.get("concepts", []),
        "related_terms": analysis.get("related_terms", []),
        "derivative_statuses": read_note_derivative_statuses(saved.note_path),
        "derivative_texts": {},
        "status_message": None,
        "play_active": False,
        "play_jobs_pending": 0,
    }
    note_context = _register_note_context(note_id, note_context)
    if context is None:
        return
    notes = context.user_data.setdefault("notes", {})
    notes[note_id] = note_context


def _extract_markdown_section(markdown: str, heading: str) -> str:
    marker = f"## {heading}"
    start = markdown.find(marker)
    if start < 0:
        return ""
    start = markdown.find("\n", start)
    if start < 0:
        return ""
    end = markdown.find("\n## ", start + 1)
    if end < 0:
        end = len(markdown)
    return markdown[start:end].strip()


def _parse_concepts_section(section: str) -> list[dict[str, str]]:
    concepts: list[dict[str, str]] = []
    for line in section.splitlines():
        text = line.strip()
        if not text.startswith("- **"):
            continue
        close = text.find("**", 4)
        if close < 0:
            continue
        term = text[4:close].strip()
        definition = text[close + 2 :].lstrip(": ").strip()
        if term:
            concepts.append({"term": term, "definition": definition})
    return concepts


def _parse_related_terms_section(section: str) -> list[str]:
    terms: list[str] = []
    for line in section.splitlines():
        text = line.strip()
        if text.startswith("- "):
            term = text[2:].strip()
            if term and not term.lower().startswith("sin terminos"):
                terms.append(term)
    return terms


def _extract_frontmatter_value(markdown: str, key: str) -> str:
    match = re.search(rf"(?mi)^{re.escape(key)}:\s*(.+?)\s*$", markdown)
    if not match:
        return ""
    return match.group(1).strip().strip('"').strip("'")


def _parse_note_markdown(markdown: str) -> dict[str, object]:
    title = next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), "Nota")
    corrected_text = _extract_markdown_section(markdown, "Nota limpia")
    concepts = _parse_concepts_section(_extract_markdown_section(markdown, "Conceptos clave"))
    related_terms = _parse_related_terms_section(_extract_markdown_section(markdown, "Terminos relacionados"))
    return {
        "title": title,
        "text_type": _extract_frontmatter_value(markdown, "text_type") or "nota_libre",
        "corrected_text": corrected_text,
        "concepts": concepts,
        "related_terms": related_terms,
    }


def _load_note_delivery_payload(saved: SavedNote, analysis: dict | None = None) -> dict[str, object]:
    if saved.note_path.exists():
        try:
            return _parse_note_markdown(saved.note_path.read_text(encoding="utf-8"))
        except Exception:
            pass

    analysis = analysis or {}
    return {
        "title": saved.title,
        "text_type": str(analysis.get("text_type", "nota_libre")).strip() or "nota_libre",
        "corrected_text": str(analysis.get("corrected_text", "")).strip(),
        "concepts": analysis.get("concepts", []),
        "related_terms": analysis.get("related_terms", []),
    }


def _find_saved_note_path(note_id: str) -> Path | None:
    def _is_base_note(path: Path) -> bool:
        return not any(path.name.endswith(f".{suffix}.md") for suffix in ("explain", "suggest", "research", "dialectic", "proposal"))

    date_part = note_id.split("_", 1)[0]
    if len(date_part) == 8 and date_part.isdigit():
        day_dir = SETTINGS.notes_dir / f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]}"
        if day_dir.exists():
            candidates = [p for p in sorted(day_dir.glob(f"{note_id}_*.md")) if _is_base_note(p)]
            if candidates:
                return candidates[-1]

    candidates = [p for p in sorted(SETTINGS.notes_dir.rglob(f"{note_id}_*.md")) if _is_base_note(p)]
    return candidates[-1] if candidates else None


def _load_note_context_from_disk(note_id: str) -> dict | None:
    note_path = _find_saved_note_path(note_id)
    if note_path is None:
        return None

    markdown = note_path.read_text(encoding="utf-8")
    title = next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), "Nota")
    corrected_text = _extract_markdown_section(markdown, "Nota limpia")
    concepts_section = _extract_markdown_section(markdown, "Conceptos clave")
    related_terms_section = _extract_markdown_section(markdown, "Terminos relacionados")

    return {
        "title": title,
        "note_path": str(note_path),
        "text_type": _extract_frontmatter_value(markdown, "text_type") or "nota_libre",
        "corrected_text": corrected_text,
        "concepts": _parse_concepts_section(concepts_section),
        "related_terms": _parse_related_terms_section(related_terms_section),
        "derivative_statuses": read_note_derivative_statuses(note_path),
        "derivative_texts": {},
        "status_message": None,
        "play_active": False,
        "play_jobs_pending": 0,
        "play_sent_actions": _normalize_play_sent_actions(None, note_id),
    }


def _resolve_note_path(note_id: str, note_context: dict) -> Path | None:
    raw_path = str(note_context.get("note_path", "")).strip()
    if raw_path:
        candidate = Path(raw_path)
        if candidate.exists():
            return candidate
    return _find_saved_note_path(note_id)


def _get_note_context(note_id: str) -> dict | None:
    note_context = _NOTE_CONTEXT_REGISTRY.get(note_id)
    if note_context:
        return note_context
    note_context = _load_note_context_from_disk(note_id)
    if note_context:
        note_context = _register_note_context(note_id, note_context)
    return note_context


def _default_note_statuses(note_path: Path | None = None) -> dict[str, str]:
    statuses: dict[str, str] = {}
    for action in [*PLAY_SEQUENCE, "proposal"]:
        if note_path and derivative_path(note_path, action).exists():
            statuses[action] = DERIVATIVE_STATUS_COMPLETED
        else:
            statuses[action] = DERIVATIVE_STATUS_PENDING
    return statuses


def _base_editorial_actions_completed(note_context: dict | None) -> bool:
    if not isinstance(note_context, dict):
        return False
    statuses = note_context.get("derivative_statuses")
    if not isinstance(statuses, dict):
        return False
    return all(statuses.get(action) == DERIVATIVE_STATUS_COMPLETED for action in PLAY_SEQUENCE)


def _proposal_instruction(note_id: str, note_context: dict | None) -> str:
    note_path = _resolve_note_path(note_id, note_context or {})
    if note_path is None:
        return ""
    proposal_path = derivative_path(note_path, "proposal")
    if not proposal_path.exists():
        return ""
    try:
        payload = _parse_derivative_markdown(proposal_path.read_text(encoding="utf-8"))
    except Exception:
        return ""
    metadata = payload.get("metadata") if isinstance(payload.get("metadata"), dict) else {}
    return str(metadata.get("editorial_instruction") or "").strip()


def _proposal_ready(note_id: str, note_context: dict | None) -> bool:
    if not _base_editorial_actions_completed(note_context):
        return False
    return bool(_proposal_instruction(note_id, note_context))


def _register_note_context(note_id: str, note_context: dict) -> dict:
    note_path = _resolve_note_path(note_id, note_context)
    if note_path and note_path.exists():
        statuses = read_note_derivative_statuses(note_path)
    else:
        statuses = _default_note_statuses(note_path)

    existing_statuses = note_context.get("derivative_statuses")
    if isinstance(existing_statuses, dict):
        statuses.update(existing_statuses)

    normalized = dict(note_context)
    normalized["derivative_statuses"] = statuses
    normalized.setdefault("derivative_texts", {})
    normalized.setdefault("status_message", None)
    normalized.setdefault("play_active", False)
    normalized.setdefault("play_jobs_pending", 0)
    queued_actions = note_context.get("queued_actions_after_play")
    normalized["queued_actions_after_play"] = [
        item for item in queued_actions if item in NOTE_ACTIONS and item != "play"
    ] if isinstance(queued_actions, list) else []
    normalized["play_sent_actions"] = _normalize_play_sent_actions(note_context.get("play_sent_actions"), note_id)
    _NOTE_CONTEXT_REGISTRY[note_id] = normalized
    return normalized


def _play_audio_dir() -> Path:
    output_dir = SETTINGS.audio_storage_dir / "responses" / PLAY_AUDIO_DIR_NAME
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def _play_audio_path(note_id: str, action: str) -> Path:
    return _play_audio_dir() / f"{note_id}_{action}.mp3"


def _play_state_path(note_id: str) -> Path:
    return _play_audio_dir() / f"{note_id}.json"


def _normalize_play_sent_actions(raw_actions: object, note_id: str | None = None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    candidates = raw_actions if isinstance(raw_actions, list) else None
    if candidates is None and note_id:
        candidates = _read_play_state(note_id).get("sent_actions", [])
    for action in candidates or []:
        if action not in PLAY_SEQUENCE or action in seen:
            continue
        seen.add(action)
        normalized.append(action)
    return normalized


def _read_play_state(note_id: str) -> dict[str, object]:
    state_path = _play_state_path(note_id)
    if not state_path.exists():
        return {"sent_actions": []}
    try:
        payload = json.loads(state_path.read_text(encoding="utf-8"))
    except Exception:
        return {"sent_actions": []}
    sent_actions = payload.get("sent_actions") if isinstance(payload, dict) else []
    return {"sent_actions": _normalize_play_sent_actions(sent_actions)}


def _write_play_state(note_id: str, sent_actions: list[str]) -> None:
    state_path = _play_state_path(note_id)
    state_path.write_text(
        json.dumps({"sent_actions": _normalize_play_sent_actions(sent_actions)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _get_play_sent_actions(note_id: str, note_context: dict | None = None) -> list[str]:
    context = note_context or _get_note_context(note_id)
    if context is None:
        return _normalize_play_sent_actions(None, note_id)
    sent_actions = _normalize_play_sent_actions(context.get("play_sent_actions"), note_id)
    context["play_sent_actions"] = sent_actions
    return sent_actions


def _mark_play_action_sent(note_id: str, action: str, note_context: dict | None = None) -> list[str]:
    context = note_context or _get_note_context(note_id)
    sent_actions = _get_play_sent_actions(note_id, context)
    if action not in sent_actions:
        sent_actions.append(action)
        if context is not None:
            context["play_sent_actions"] = sent_actions
        _write_play_state(note_id, sent_actions)
    return sent_actions


def _pending_play_actions(note_id: str, note_context: dict | None = None) -> list[str]:
    sent_actions = set(_get_play_sent_actions(note_id, note_context))
    return [action for action in PLAY_SEQUENCE if action not in sent_actions]


def _cleanup_play_artifacts(note_id: str, note_context: dict | None = None) -> None:
    for action in PLAY_SEQUENCE:
        _play_audio_path(note_id, action).unlink(missing_ok=True)
    _play_state_path(note_id).unlink(missing_ok=True)
    context = note_context or _get_note_context(note_id)
    if context is not None:
        context["play_sent_actions"] = []


def _queue_action_after_play(note_context: dict, action: str) -> bool:
    if action == "play":
        return False
    queued_actions = note_context.setdefault("queued_actions_after_play", [])
    if not isinstance(queued_actions, list):
        queued_actions = []
        note_context["queued_actions_after_play"] = queued_actions
    if action in queued_actions:
        return False
    queued_actions.append(action)
    return True


async def _process_note_action_after_play(note_id: str, action: str, message) -> None:
    note_context = _get_note_context(note_id)
    if not note_context or message is None:
        return

    note_path = _resolve_note_path(note_id, note_context)
    current_derivative_path = derivative_path(note_path, action) if note_path else None
    status = note_context.setdefault("derivative_statuses", {}).get(action, DERIVATIVE_STATUS_PENDING)

    if current_derivative_path and current_derivative_path.exists():
        note_context["derivative_statuses"][action] = DERIVATIVE_STATUS_COMPLETED
        await _refresh_note_action_keyboard(note_id)
        derivative_markdown = await asyncio.to_thread(current_derivative_path.read_text, "utf-8")
        derivative_payload = await asyncio.to_thread(_parse_derivative_markdown, derivative_markdown)
        clipboard_text = _build_channel_text(derivative_payload, "clipboard")
        await asyncio.to_thread(_copy_text_to_clipboard, clipboard_text)
        await _send_text_with_optional_audio(message, f"{NOTE_ACTIONS[action]}: copiado al portapapeles.", f"clipboard_{action}")
        return

    if status == DERIVATIVE_STATUS_PROCESSING:
        await _send_text_with_optional_audio(message, f"{NOTE_ACTIONS[action]}: procesando en segundo plano.", f"status_{action}")
        return

    await _update_derivative_status(note_id, action, DERIVATIVE_STATUS_PENDING)
    await _enqueue_derivative_job("derive", note_id, action)
    if status == DERIVATIVE_STATUS_ERROR:
        await _send_text_with_optional_audio(message, f"{NOTE_ACTIONS[action]}: reintentando en segundo plano.", f"retry_{action}")
    else:
        await _send_text_with_optional_audio(message, f"{NOTE_ACTIONS[action]}: pendiente. Se esta generando en segundo plano.", f"pending_{action}")


async def _drain_post_play_actions(note_id: str) -> None:
    note_context = _get_note_context(note_id)
    if not note_context:
        return
    queued_actions = list(note_context.get("queued_actions_after_play", []))
    note_context["queued_actions_after_play"] = []
    message = note_context.get("status_message")
    for action in queued_actions:
        # Keep the queued action flow independent from Play. A derivative action
        # may refresh the same inline keyboard, so make sure it cannot observe a
        # stale Play session and redraw the clock while serving its response.
        note_context["play_active"] = False
        note_context["play_jobs_pending"] = 0
        try:
            await _process_note_action_after_play(note_id, action, message)
        except Exception:
            LOG.exception("Fallo procesando accion en cola despues de Play", extra={"note_id": note_id, "action": action})


def _all_play_audio_files_exist(note_id: str) -> bool:
    for action in PLAY_SEQUENCE:
        audio_path = _play_audio_path(note_id, action)
        if not audio_path.exists() or audio_path.stat().st_size < 128:
            return False
    return True


def _persist_generated_audio(temp_audio_path: Path, target_path: Path) -> Path:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.exists():
        target_path.unlink(missing_ok=True)
    copy2(temp_audio_path, target_path)
    return target_path


def _fallback_audio_filename(text: str, prefix: str) -> str:
    title = text.splitlines()[0].strip()[:120].replace(":", "-")
    safe_name = "_".join(title.split()) or prefix
    return f"{safe_name}.mp3"


def _resolve_audio_markdown_path(prefix: str) -> Path | None:
    if prefix.startswith("note_"):
        note_id = prefix[len("note_") :]
        note_context = _get_note_context(note_id)
        return _resolve_note_path(note_id, note_context) if note_context else _find_saved_note_path(note_id)

    if prefix.startswith("action_") and prefix.endswith("_play"):
        encoded = prefix[len("action_") : -len("_play")]
        action, separator, note_id = encoded.partition("_")
        if separator and action in NOTE_ACTIONS:
            note_context = _get_note_context(note_id)
            note_path = _resolve_note_path(note_id, note_context) if note_context else _find_saved_note_path(note_id)
            if note_path is not None:
                return derivative_path(note_path, action)

    return None


def _resolve_audio_filename(prefix: str, text: str) -> str:
    markdown_path = _resolve_audio_markdown_path(prefix)
    if markdown_path is not None:
        return _telegram_compact_name(markdown_path, "mp3")
    return _fallback_audio_filename(text, prefix)


async def _send_audio_file(message, audio_path: Path, text: str, prefix: str) -> bool:
    if message is None or not audio_path.exists():
        return False
    send_lock, _ = _ensure_telegram_send_primitives()
    filename = _resolve_audio_filename(prefix, text)
    try:
        async with send_lock:
            with audio_path.open("rb") as audio_stream:
                await message.reply_audio(audio=audio_stream, filename=filename)
        return True
    except Exception:
        return False


async def _ensure_play_audio_file(note_id: str, action: str, text: str, prefix: str) -> Path | None:
    target_path = _play_audio_path(note_id, action)
    if target_path.exists() and target_path.stat().st_size >= 128:
        return target_path

    temp_audio = await asyncio.to_thread(synthesize_text_to_single_mp3, SETTINGS, text, prefix)
    if temp_audio is None:
        return None
    try:
        return await asyncio.to_thread(_persist_generated_audio, temp_audio, target_path)
    finally:
        temp_audio.unlink(missing_ok=True)


async def _send_or_resume_play_audio(message, note_id: str, action: str, text: str, prefix: str) -> bool:
    note_context = _get_note_context(note_id)
    if action in _get_play_sent_actions(note_id, note_context):
        return True
    audio_path = await _ensure_play_audio_file(note_id, action, text, prefix)
    if audio_path is None:
        return False
    sent = await _send_audio_file(message, audio_path, text, prefix)
    if sent:
        await asyncio.to_thread(_mark_play_action_sent, note_id, action, note_context)
    return sent


async def _finalize_play_session(note_id: str) -> bool:
    note_context = _get_note_context(note_id)
    if not note_context:
        return False
    note_context["play_active"] = False
    note_context["play_jobs_pending"] = 0
    refreshed = await _refresh_note_action_keyboard(note_id)
    persisted_pending = [action for action in PLAY_SEQUENCE if action not in _read_play_state(note_id).get("sent_actions", [])]
    if refreshed and not persisted_pending and _all_play_audio_files_exist(note_id):
        await asyncio.to_thread(_cleanup_play_artifacts, note_id, note_context)
    await _drain_post_play_actions(note_id)
    return refreshed


def _action_button_label(action: str, active_action: str | None = None, statuses: dict[str, str] | None = None, play_active: bool = False) -> str:
    label = NOTE_ACTIONS.get(action, action)
    if active_action == action:
        return f"⏳ {label}..."
    if action == "play":
        return "⏳ Play..." if play_active else label
    if action == "realize":
        return label
    if statuses:
        icon = DERIVATIVE_STATUS_ICONS.get(statuses.get(action, DERIVATIVE_STATUS_PENDING), "")
        if icon:
            return f"{icon} {label}"
    return label


def _build_note_action_keyboard(note_id: str, active_action: str | None = None) -> InlineKeyboardMarkup:
    note_context = _get_note_context(note_id) or {}
    statuses = note_context.get("derivative_statuses", {}) if isinstance(note_context, dict) else {}
    play_active = bool(note_context.get("play_active")) if isinstance(note_context, dict) else False
    proposal_enabled = _base_editorial_actions_completed(note_context)
    realize_enabled = _proposal_ready(note_id, note_context)
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    _action_button_label("play", active_action, statuses, play_active),
                    callback_data=f"{NOTE_ACTION_PREFIX}:play:{note_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    _action_button_label("explain", active_action, statuses, play_active),
                    callback_data=f"{NOTE_ACTION_PREFIX}:explain:{note_id}",
                ),
                InlineKeyboardButton(
                    _action_button_label("suggest", active_action, statuses, play_active),
                    callback_data=f"{NOTE_ACTION_PREFIX}:suggest:{note_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    _action_button_label("research", active_action, statuses, play_active),
                    callback_data=f"{NOTE_ACTION_PREFIX}:research:{note_id}",
                ),
                InlineKeyboardButton(
                    _action_button_label("dialectic", active_action, statuses, play_active),
                    callback_data=f"{NOTE_ACTION_PREFIX}:dialectic:{note_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    _action_button_label("proposal", active_action, statuses, play_active) if proposal_enabled or active_action == "proposal" else "🔒 Propuesta",
                    callback_data=f"{NOTE_ACTION_PREFIX}:proposal:{note_id}",
                ),
                InlineKeyboardButton(
                    _action_button_label("realize", active_action, statuses, play_active) if realize_enabled or active_action == "realize" else "🔒 Realizar",
                    callback_data=f"{NOTE_ACTION_PREFIX}:realize:{note_id}",
                ),
            ],
        ]
    )


async def _set_note_action_keyboard_state(query, note_id: str, active_action: str | None) -> None:
    if not query or not query.message:
        return
    await _edit_note_action_keyboard(query.message, note_id, active_action)


async def _refresh_note_action_keyboard(note_id: str) -> bool:
    note_context = _get_note_context(note_id)
    if not note_context:
        return False
    message = note_context.get("status_message")
    return await _edit_note_action_keyboard(message, note_id)


async def _edit_note_action_keyboard(message, note_id: str, active_action: str | None = None) -> bool:
    if message is None or not hasattr(message, "edit_reply_markup"):
        return False

    send_lock, _ = _ensure_telegram_send_primitives()
    for attempt in range(NOTE_ACTION_KEYBOARD_EDIT_ATTEMPTS):
        try:
            async with send_lock:
                await message.edit_reply_markup(reply_markup=_build_note_action_keyboard(note_id, active_action))
            return True
        except Exception:
            if attempt == NOTE_ACTION_KEYBOARD_EDIT_ATTEMPTS - 1:
                LOG.exception("No se pudo actualizar el teclado de acciones", extra={"note_id": note_id})
                return False
            await asyncio.sleep(0.25 * (attempt + 1))
    return False


def _ensure_derivative_job_queue() -> asyncio.PriorityQueue[tuple[int, int, tuple[str, str, object | None]]]:
    global _DERIVATIVE_JOB_QUEUE, _DERIVATIVE_PROCESSOR_LOOP, _DERIVATIVE_PROCESSOR_TASK
    loop = asyncio.get_running_loop()
    if _DERIVATIVE_PROCESSOR_LOOP is not loop:
        _DERIVATIVE_JOB_QUEUE = asyncio.PriorityQueue()
        _DERIVATIVE_PROCESSOR_TASK = None
        _DERIVATIVE_PROCESSOR_LOOP = loop
    if _DERIVATIVE_JOB_QUEUE is None:
        _DERIVATIVE_JOB_QUEUE = asyncio.PriorityQueue()
    return _DERIVATIVE_JOB_QUEUE


def _ensure_telegram_send_primitives() -> tuple[asyncio.Lock, asyncio.Event]:
    global _TELEGRAM_SEND_LOCK, _DERIVATIVE_SAVE_LOCK, _FOREGROUND_NOTE_EVENT, _TELEGRAM_SEND_LOOP, _FOREGROUND_NOTE_COUNT
    loop = asyncio.get_running_loop()
    if _TELEGRAM_SEND_LOOP is not loop:
        _TELEGRAM_SEND_LOCK = asyncio.Lock()
        _DERIVATIVE_SAVE_LOCK = asyncio.Lock()
        _FOREGROUND_NOTE_EVENT = asyncio.Event()
        _FOREGROUND_NOTE_EVENT.set()
        _TELEGRAM_SEND_LOOP = loop
        _FOREGROUND_NOTE_COUNT = 0
    if _TELEGRAM_SEND_LOCK is None:
        _TELEGRAM_SEND_LOCK = asyncio.Lock()
    if _DERIVATIVE_SAVE_LOCK is None:
        _DERIVATIVE_SAVE_LOCK = asyncio.Lock()
    if _FOREGROUND_NOTE_EVENT is None:
        _FOREGROUND_NOTE_EVENT = asyncio.Event()
        _FOREGROUND_NOTE_EVENT.set()
    return _TELEGRAM_SEND_LOCK, _FOREGROUND_NOTE_EVENT


def _ensure_derivative_save_lock() -> asyncio.Lock:
    _ensure_telegram_send_primitives()
    if _DERIVATIVE_SAVE_LOCK is None:
        raise RuntimeError("No se pudo inicializar el lock de guardado de derivados.")
    return _DERIVATIVE_SAVE_LOCK


@asynccontextmanager
async def _foreground_note_delivery():
    global _FOREGROUND_NOTE_COUNT
    _, foreground_event = _ensure_telegram_send_primitives()
    _FOREGROUND_NOTE_COUNT += 1
    foreground_event.clear()
    try:
        yield
    finally:
        _FOREGROUND_NOTE_COUNT = max(_FOREGROUND_NOTE_COUNT - 1, 0)
        if _FOREGROUND_NOTE_COUNT == 0:
            foreground_event.set()


async def _wait_for_foreground_note_delivery() -> None:
    _, foreground_event = _ensure_telegram_send_primitives()
    await foreground_event.wait()


async def _update_derivative_status(note_id: str, action: str, status: str) -> None:
    note_context = _get_note_context(note_id)
    if not note_context:
        return
    statuses = note_context.setdefault("derivative_statuses", {})
    statuses[action] = status
    note_path = _resolve_note_path(note_id, note_context)
    if note_path:
        await asyncio.to_thread(set_note_derivative_status, note_path, action, status)
    await _refresh_note_action_keyboard(note_id)


def _read_derivative_text(path: Path) -> str:
    markdown = path.read_text(encoding="utf-8")
    payload = _parse_derivative_markdown(markdown)
    return _build_channel_text(payload, "telegram")


def _extract_section(markdown: str, heading: str) -> str:
    marker = f"## {heading}"
    lines = markdown.splitlines()
    collecting = False
    bucket: list[str] = []

    for line in lines:
        if line.strip() == marker:
            collecting = True
            continue
        if collecting and line.startswith("## "):
            break
        if collecting:
            bucket.append(line)

    return "\n".join(bucket).strip()


def _parse_derivative_markdown(markdown: str) -> dict[str, object]:
    title = next((line[2:].strip() for line in markdown.splitlines() if line.startswith("# ")), "Resultado")
    source_title = ""
    for line in markdown.splitlines():
        text = line.strip()
        if not text.startswith("Nota origen:"):
            continue
        source_ref = text[len("Nota origen:") :].strip()
        if source_ref.startswith("[") and "](" in source_ref:
            source_title = source_ref[1 : source_ref.find("](")].strip()
        else:
            source_title = source_ref
        break

    metadata_section = _extract_section(markdown, "Metadata")
    metadata: dict[str, object] = {}
    if metadata_section:
        try:
            metadata = json.loads(metadata_section)
        except json.JSONDecodeError:
            start = metadata_section.find("{")
            end = metadata_section.rfind("}")
            if start >= 0 and end > start:
                try:
                    metadata = json.loads(metadata_section[start : end + 1])
                except json.JSONDecodeError:
                    metadata = {}
            else:
                metadata = {}

    sections: dict[str, str] = {}
    for key in ["Nucleo", "Desarrollo", "Accionables", "Evidencias y supuestos", "Sintesis breve"]:
        content = _extract_section(markdown, key)
        if content:
            sections[key] = content.strip()

    if not sections:
        fallback = []
        for line in markdown.splitlines():
            if line.startswith("# ") or line.startswith("Nota origen:") or line.startswith("## Metadata"):
                continue
            fallback.append(line)
        sections = normalize_derivative_sections("\n".join(fallback).strip())

    return {
        "title": title,
        "source_title": source_title,
        "metadata": metadata,
        "sections": sections,
    }


def _strip_note_time_prefix(title: str) -> str:
    normalized = " ".join(str(title).split())
    if len(normalized) >= 8 and normalized[:2].isdigit() and normalized[2] == ":" and normalized[3:5].isdigit():
        remainder = normalized[5:].lstrip()
        if remainder.startswith("-"):
            normalized = remainder[1:].lstrip()
    return normalized


def _split_derivative_heading(raw_title: str, source_title: str) -> tuple[str, str]:
    normalized_raw = " ".join(str(raw_title).split())
    normalized_source = " ".join(str(source_title).split())
    if normalized_source and normalized_raw.startswith(normalized_source):
        remainder = normalized_raw[len(normalized_source) :].strip()
        if remainder.startswith("·"):
            return normalized_source, remainder[1:].strip()
        if remainder.startswith("-"):
            return normalized_source, remainder[1:].strip()
    if " · " in normalized_raw:
        possible_source, possible_action = normalized_raw.rsplit(" · ", 1)
        if _strip_note_time_prefix(possible_source) == normalized_source:
            return normalized_source, possible_action.strip()
    return normalized_source, normalized_raw


def _normalize_channel_text(text: str) -> str:
    lines = [line.rstrip() for line in str(text).replace("\r\n", "\n").split("\n")]
    compacted: list[str] = []
    previous_blank = False
    for line in lines:
        blank = not line.strip()
        if blank and previous_blank:
            continue
        compacted.append(line)
        previous_blank = blank
    return "\n".join(compacted).strip()


def _apply_filter_patterns(text: str, channel: str) -> str:
    filtered = str(text)
    for pattern, replacement in DERIVATIVE_FILTER_PATTERNS["common"]:
        filtered = pattern.sub(replacement, filtered)
    for pattern, replacement in DERIVATIVE_FILTER_PATTERNS.get(channel, []):
        filtered = pattern.sub(replacement, filtered)
    return _normalize_channel_text(filtered)


def _drop_redundant_paragraphs(text: str, channel: str) -> str:
    paragraphs = [paragraph.strip() for paragraph in _normalize_channel_text(text).split("\n\n") if paragraph.strip()]
    if not paragraphs:
        return ""

    kept: list[str] = []
    seen_normalized: set[str] = set()
    for paragraph in paragraphs:
        normalized = re.sub(r"\s+", " ", paragraph).strip().casefold()
        if normalized in seen_normalized:
            continue
        seen_normalized.add(normalized)
        if channel == "telegram" and normalized.startswith(("regla practica", "pregunta abierta")):
            continue
        kept.append(paragraph)
    return "\n\n".join(kept)


def _select_channel_sections(sections: dict[str, str], channel: str) -> list[str]:
    ordered_sections = [
        ("Nucleo", str(sections.get("Nucleo", "")).strip()),
        ("Desarrollo", str(sections.get("Desarrollo", "")).strip()),
        ("Accionables", str(sections.get("Accionables", "")).strip()),
        ("Evidencias y supuestos", str(sections.get("Evidencias y supuestos", "")).strip()),
        ("Sintesis breve", str(sections.get("Sintesis breve", "")).strip()),
    ]

    selected: list[str] = []
    for name, value in ordered_sections:
        if not value:
            continue
        if channel in {"audio", "clipboard"} and name == "Evidencias y supuestos":
            continue
        if channel == "telegram" and name == "Evidencias y supuestos":
            continue
        selected.append(value)
    return selected


def _render_audio_lists(text: str) -> str:
    rendered_lines: list[str] = []
    for raw_line in _normalize_channel_text(text).splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        if re.match(r"^\d+[.)]\s+", stripped):
            rendered_lines.append(f"Punto: {re.sub(r'^\d+[.)]\s+', '', stripped)}")
            continue
        if stripped.startswith("- "):
            rendered_lines.append(f"Punto: {stripped[2:].strip()}")
            continue
        rendered_lines.append(stripped)
    return _normalize_channel_text("\n".join(rendered_lines))


def _build_filtered_channel_body(sections: dict[str, str], channel: str) -> str:
    body = "\n\n".join(_select_channel_sections(sections, channel))
    body = _apply_filter_patterns(body, channel)
    body = _drop_redundant_paragraphs(body, channel)
    if channel == "audio":
        body = _render_audio_lists(body)
    return body.strip()


def _build_channel_text(payload: dict[str, object], channel: str) -> str:
    raw_title = str(payload.get("title", "Resultado")).strip() or "Resultado"
    action_alias = {
        "Explicar": "Explicacion",
        "Investigar": "Investigacion",
    }
    clipboard_action_alias = {
        "Explicar": "Explicación",
        "Investigar": "Investigación",
        "Dialectica": "Dialéctica",
    }
    source_title = _strip_note_time_prefix(str(payload.get("source_title", "")).strip())
    heading_source_title, action_title = _split_derivative_heading(raw_title, source_title)
    title = action_alias.get(action_title, action_title)
    sections = payload.get("sections") if isinstance(payload.get("sections"), dict) else {}

    if channel == "telegram":
        telegram_action_title = clipboard_action_alias.get(action_title, action_title)
        telegram_title = f"{heading_source_title} - {telegram_action_title}" if heading_source_title else telegram_action_title
        telegram_body = _build_filtered_channel_body(sections, "telegram")
        return f"{telegram_title}\n\n{telegram_body}".strip()

    if channel == "clipboard":
        clipboard_title = clipboard_action_alias.get(action_title, action_title)
        if heading_source_title:
            clipboard_title = f"{heading_source_title} - {clipboard_title}"
        clipboard_body = _build_filtered_channel_body(sections, "clipboard")
        return f"{clipboard_title}\n\n{clipboard_body}".strip()

    body = _build_filtered_channel_body(sections, channel)
    if channel == "audio":
        return f"{title}. {body}".strip()
    return f"{title}\n\n{body}".strip()


async def _ensure_derivative_markdown(note_id: str, action: str) -> tuple[Path | None, str | None]:
    if action == "proposal":
        return await _ensure_proposal_markdown(note_id)

    note_context = _get_note_context(note_id)
    if not note_context:
        return None, None

    note_path = _resolve_note_path(note_id, note_context)
    if note_path is None:
        await _update_derivative_status(note_id, action, DERIVATIVE_STATUS_ERROR)
        return None, None

    current_path = derivative_path(note_path, action)
    if current_path.exists():
        await _update_derivative_status(note_id, action, DERIVATIVE_STATUS_COMPLETED)
        text = note_context.setdefault("derivative_texts", {}).get(action)
        if not text:
            text = await asyncio.to_thread(_read_derivative_text, current_path)
            note_context["derivative_texts"][action] = text
        return current_path, text

    await _update_derivative_status(note_id, action, DERIVATIVE_STATUS_PROCESSING)
    try:
        messages = _build_note_action_messages(action, note_context)
        max_tokens, temperature = _note_action_generation_options(action)
        action_settings = settings_for_llm_provider(SETTINGS, DERIVATIVE_ACTION_PROVIDERS.get(action, SETTINGS.llm_provider))
        result = await asyncio.to_thread(
            invoke_chat,
            action_settings,
            messages,
            max_tokens,
            temperature,
            False,
        )
        async with _ensure_derivative_save_lock():
            current_path = await asyncio.to_thread(save_note_derivative, note_path, action, result, note_context.get("title"))
        parsed = await asyncio.to_thread(_parse_derivative_markdown, current_path.read_text(encoding="utf-8"))
        note_context.setdefault("derivative_texts", {})[action] = str(parsed.get("sections", {}).get("Nucleo", "")).strip() or result
    except Exception:
        await _update_derivative_status(note_id, action, DERIVATIVE_STATUS_ERROR)
        return None, None

    await _update_derivative_status(note_id, action, DERIVATIVE_STATUS_COMPLETED)
    return current_path, result


async def _run_derivative_job(job_kind: str, note_id: str, action: str, message) -> None:
    note_context = _get_note_context(note_id)
    if not note_context:
        return

    if message is None:
        message = note_context.get("status_message")

    current_path, content = await _ensure_derivative_markdown(note_id, action)
    if job_kind == "derive":
        if current_path is not None and message is not None:
            await _wait_for_foreground_note_delivery()
            await _reply_markdown_file(message, current_path, current_path.name)
        return

    if job_kind == "play":
        try:
            if message is not None and content:
                await _wait_for_foreground_note_delivery()
                note_path = _resolve_note_path(note_id, note_context)
                if note_path is not None:
                    derivative_md = await asyncio.to_thread(derivative_path(note_path, action).read_text, "utf-8")
                    payload = await asyncio.to_thread(_parse_derivative_markdown, derivative_md)
                    audio_text = _build_channel_text(payload, "audio")
                else:
                    header = _format_action_header(action)
                    audio_text = f"{header}. {content}"
                await _send_or_resume_play_audio(message, note_id, action, audio_text, f"action_{action}_{note_id}_play")
        finally:
            pending = max(int(note_context.get("play_jobs_pending", 0)) - 1, 0)
            note_context["play_jobs_pending"] = pending
            if pending == 0:
                refreshed = await _finalize_play_session(note_id)
                if refreshed and len(_read_play_state(note_id).get("sent_actions", [])) == len(PLAY_SEQUENCE) and _all_play_audio_files_exist(note_id):
                    await asyncio.to_thread(_cleanup_play_artifacts, note_id, note_context)
            else:
                note_context["play_active"] = True
                await _refresh_note_action_keyboard(note_id)


async def _run_derive_jobs_for_note_ordered(note_id: str, payloads: list[tuple[str, str, str, object | None]]) -> bool:
    action_payloads: dict[str, tuple[str, str, str, object | None]] = {
        action: payload for payload in payloads for _, _, action, _ in [payload]
    }

    async def run_payload(payload: tuple[str, str, str, object | None]) -> tuple[str, Path | None]:
        _, payload_note_id, action, _ = payload
        try:
            current_path, _ = await _ensure_derivative_markdown(payload_note_id, action)
        except Exception:
            LOG.exception("Fallo generando derivado %s para nota %s", action, payload_note_id)
            current_path = None
        return action, current_path if current_path and current_path.exists() else None

    results = await asyncio.gather(
        *(run_payload(action_payloads[action]) for action in PLAY_SEQUENCE if action in action_payloads)
    )
    paths_by_action = {action: path for action, path in results}
    all_sent = True

    note_context = _get_note_context(note_id)
    stored_message = note_context.get("status_message") if note_context else None
    for action in PLAY_SEQUENCE:
        payload = action_payloads.get(action)
        if payload is None:
            continue
        _, _, _, payload_message = payload
        message = payload_message or stored_message
        current_path = paths_by_action.get(action)
        if current_path is None:
            all_sent = False
            continue
        if message is None:
            all_sent = False
            continue
        try:
            await _wait_for_foreground_note_delivery()
            await _reply_markdown_file(message, current_path, current_path.name)
        except Exception:
            LOG.exception("Fallo enviando Markdown derivado %s para nota %s", action, note_id)
            all_sent = False
    return all_sent


async def _drain_derivative_jobs() -> None:
    queue = _ensure_derivative_job_queue()
    while True:
        processed_notes: set[str] = set()
        auto_derive_by_note: dict[str, list[tuple[str, str, str, object | None]]] = {}
        while True:
            try:
                _, _, payload = queue.get_nowait()
            except asyncio.QueueEmpty:
                break

            job_kind, note_id, action, message = payload
            processed_notes.add(note_id)
            try:
                if job_kind == "derive" and message is None:
                    auto_derive_by_note.setdefault(note_id, []).append(payload)
                    continue
                await _run_derivative_job(job_kind, note_id, action, message)
            except Exception:
                LOG.exception("Fallo procesando job derivado")
            finally:
                if not (job_kind == "derive" and message is None):
                    queue.task_done()

        for note_id, payloads in auto_derive_by_note.items():
            try:
                delivery_completed = await _run_derive_jobs_for_note_ordered(note_id, payloads)
                note_context = _get_note_context(note_id)
                if note_context is not None:
                    note_context["derivative_markdown_delivery_completed"] = delivery_completed
            finally:
                for _ in payloads:
                    queue.task_done()

        scheduled_followup = False
        for note_id in processed_notes:
            note_context = _get_note_context(note_id)
            if not note_context or not note_context.pop("auto_play_after_derivatives", False):
                continue
            if not note_context.pop("derivative_markdown_delivery_completed", False):
                note_context["play_active"] = False
                note_context["play_jobs_pending"] = 0
                await _refresh_note_action_keyboard(note_id)
                LOG.warning("Auto-Play no se encolo porque no terminaron correctamente los envios Markdown de la nota %s", note_id)
                continue
            message = note_context.get("status_message")
            if message is not None:
                scheduled_followup = await _enqueue_play_jobs(note_id, message) or scheduled_followup

        if not scheduled_followup or queue.empty():
            break


def _start_derivative_processor() -> None:
    global _DERIVATIVE_PROCESSOR_TASK
    queue = _ensure_derivative_job_queue()
    if queue.empty():
        return
    if _DERIVATIVE_PROCESSOR_TASK is not None and not _DERIVATIVE_PROCESSOR_TASK.done():
        return
    _DERIVATIVE_PROCESSOR_TASK = asyncio.create_task(_drain_derivative_jobs())


async def _enqueue_derivative_job(job_kind: str, note_id: str, action: str, message=None, *, start: bool = True) -> None:
    queue = _ensure_derivative_job_queue()
    priority_key = "play" if job_kind == "play" else action
    await queue.put((DERIVATIVE_JOB_PRIORITIES[priority_key], next(_DERIVATIVE_JOB_ORDER), (job_kind, note_id, action, message)))
    if start:
        _start_derivative_processor()


async def _enqueue_default_derivatives(note_id: str) -> None:
    for action in PLAY_SEQUENCE:
        await _update_derivative_status(note_id, action, DERIVATIVE_STATUS_PENDING)
        await _enqueue_derivative_job("derive", note_id, action, start=False)
    _start_derivative_processor()


async def _enqueue_play_jobs(note_id: str, message) -> bool:
    note_context = _get_note_context(note_id)
    if not note_context:
        return False
    if note_context.get("play_active"):
        return False
    actions_to_queue = _pending_play_actions(note_id, note_context)
    if not actions_to_queue:
        await _finalize_play_session(note_id)
        return True
    note_context["play_active"] = True
    note_context["play_jobs_pending"] = len(actions_to_queue)
    await _refresh_note_action_keyboard(note_id)
    for action in actions_to_queue:
        await _enqueue_derivative_job("play", note_id, action, message)
    return True


async def _wait_for_background_jobs() -> None:
    queue = _ensure_derivative_job_queue()
    await queue.join()
    if _DERIVATIVE_PROCESSOR_TASK is not None:
        await asyncio.shield(_DERIVATIVE_PROCESSOR_TASK)


def _format_concepts_for_prompt(concepts: object) -> str:
    if not isinstance(concepts, list):
        return "Sin conceptos detectados."
    lines: list[str] = []
    for item in concepts:
        if not isinstance(item, dict):
            continue
        term = str(item.get("term", "")).strip()
        definition = str(item.get("definition", "")).strip()
        if term:
            lines.append(f"- {term}: {definition}" if definition else f"- {term}")
    return "\n".join(lines) or "Sin conceptos detectados."


def _render_sections_text(sections: dict[str, str]) -> str:
    blocks: list[str] = []
    for heading in ["Nucleo", "Desarrollo", "Accionables", "Evidencias y supuestos", "Sintesis breve"]:
        text = str(sections.get(heading, "")).strip()
        if text:
            blocks.append(f"## {heading}\n\n{text}")
    return "\n\n".join(blocks).strip()


def _proposal_metadata(note_context: dict, proposal) -> dict[str, object]:
    return {
        "editorial_instruction": proposal.instruction,
        "editorial_backend": proposal.backend,
        "target_hint": proposal.target_hint,
        "source_mode": "editorial-proposal",
        "note_text_type": str(note_context.get("text_type", "nota_libre")).strip() or "nota_libre",
    }


async def _ensure_proposal_markdown(note_id: str) -> tuple[Path | None, str | None]:
    note_context = _get_note_context(note_id)
    if not note_context:
        return None, None

    note_path = _resolve_note_path(note_id, note_context)
    if note_path is None:
        await _update_derivative_status(note_id, "proposal", DERIVATIVE_STATUS_ERROR)
        return None, None

    proposal_path = derivative_path(note_path, "proposal")
    if proposal_path.exists():
        await _update_derivative_status(note_id, "proposal", DERIVATIVE_STATUS_COMPLETED)
        text = note_context.setdefault("derivative_texts", {}).get("proposal")
        if not text:
            text = await asyncio.to_thread(_read_derivative_text, proposal_path)
            note_context["derivative_texts"]["proposal"] = text
        return proposal_path, text

    await _update_derivative_status(note_id, "proposal", DERIVATIVE_STATUS_PROCESSING)
    try:
        proposal = await asyncio.to_thread(
            build_editorial_proposal,
            str(note_context.get("title", "Idea")).strip() or "Idea",
            str(note_context.get("corrected_text", "")).strip(),
            _format_concepts_for_prompt(note_context.get("concepts")),
            settings_for_llm_provider(SETTINGS, DERIVATIVE_ACTION_PROVIDERS.get("proposal", SETTINGS.llm_provider)),
        )
        content = _render_sections_text(proposal.sections)
        async with _ensure_derivative_save_lock():
            proposal_path = await asyncio.to_thread(
                save_note_derivative,
                note_path,
                "proposal",
                content,
                note_context.get("title"),
                extra_metadata=_proposal_metadata(note_context, proposal),
            )
        rendered = await asyncio.to_thread(_read_derivative_text, proposal_path)
        note_context.setdefault("derivative_texts", {})["proposal"] = rendered
    except Exception:
        await _update_derivative_status(note_id, "proposal", DERIVATIVE_STATUS_ERROR)
        return None, None

    await _update_derivative_status(note_id, "proposal", DERIVATIVE_STATUS_COMPLETED)
    return proposal_path, note_context.get("derivative_texts", {}).get("proposal")


async def _run_realize_action(message, note_id: str) -> None:
    note_context = _get_note_context(note_id)
    if not note_context:
        return
    instruction = _proposal_instruction(note_id, note_context)
    if not instruction:
        await _send_text_with_optional_audio(message, "Realizar: primero genera la propuesta integral.", "realize_missing_instruction")
        return
    await _send_text_with_optional_audio(
        message,
        "Realizar: ejecutando propuesta sobre el repositorio con el motor inteligente actual...",
        "realize_start",
    )
    dispatch = await asyncio.to_thread(
        run_intelligent_dispatch,
        instruction,
        SETTINGS,
        execution_mode=SETTINGS.aulatex_motor_execution_mode,
    )
    note_context["last_dispatch_instruction"] = instruction
    note_context["last_dispatch_report"] = str(dispatch.result.report_path)
    note_context["last_dispatch_manifest"] = str(dispatch.result.manifest_path)
    note_context["last_dispatch_run_dir"] = str(dispatch.result.run_dir)
    await _reply_text_chunks(message, format_dispatch_summary(dispatch))
    await _reply_markdown_file(message, dispatch.result.report_path, dispatch.result.report_path.name)


def _build_note_action_messages(action: str, note_context: dict) -> list[dict[str, str]]:
    title = str(note_context.get("title", "Idea")).strip() or "Idea"
    corrected_text = str(note_context.get("corrected_text", "")).strip()
    concepts = _format_concepts_for_prompt(note_context.get("concepts"))

    channel_contract = (
        "Formato obligatorio en Markdown con secciones exactas: "
        "## Nucleo, ## Desarrollo, ## Accionables, ## Evidencias y supuestos, ## Sintesis breve. "
        "No escribas pensando en porcentajes ni compactacion por longitud. "
        "Redacta cada seccion para que conserve sentido incluso si luego se eliminan metadata y titulos de seccion. "
        "Evita frases como 'en esta seccion', 'como dije arriba', 'a continuacion' o cierres redundantes. "
        "Prioriza causalidad, decisiones y acciones verificables. "
        "Cuando uses listas, cada punto debe entenderse por si mismo. "
        "Todo el resultado debe quedar orientado como instruccion o criterio de trabajo sobre un proyecto editorial en repositorio."
    )

    if action == "explain":
        task = (
            "Explica la idea contenida en el texto de manera clara, didactica y directa. "
            "Desarrolla su sentido, sus supuestos, sus implicaciones y los conceptos involucrados. "
            "Traducela a criterios de lectura, diagnostico y direccion editorial sobre un repositorio. "
            "No hables de notas, transcripciones ni del proceso de guardado."
        )
        expected = (
            "En Nucleo resume la tesis y alcance. En Desarrollo expone supuestos e implicaciones. "
            "En Accionables incluye pasos para profundizar. En Evidencias y supuestos explicita incertidumbres. "
            "En Sintesis breve deja un cierre autosuficiente, sin formula metadiscursiva."
        )
    elif action == "suggest":
        task = (
            "Genera sugerencias practicas sobre como hacer, resolver, aplicar o mejorar lo que plantea el contenido. "
            "Prioriza acciones concretas, criterios de decision, pasos posibles y riesgos a cuidar. "
            "Formula las sugerencias como maniobras operativas sobre un proyecto editorial y sus lotes de trabajo. "
            "No des sugerencias sobre escribir o administrar notas."
        )
        expected = (
            "En Nucleo define objetivo practico. En Desarrollo justifica criterios. "
            "En Accionables entrega 5 sugerencias priorizadas con condiciones de aplicacion y riesgo. "
            "En Evidencias y supuestos indica que depende de validacion externa. "
            "En Sintesis breve deja una recomendacion ejecutiva autosuficiente."
        )
    elif action == "research":
        task = (
            "Investiga y sintetiza el tema central contenido en el texto para ampliar la comprension del usuario. "
            "Distingue entre hechos relativamente estables, inferencias plausibles y puntos que requieren verificacion externa. "
            "Conecta los hallazgos con rutas de intervencion editorial sobre el repositorio. "
            "No inventes fuentes, datos actuales ni citas. No hables del proceso de guardado de notas."
        )
        expected = (
            "En Nucleo entrega resumen ejecutivo. En Desarrollo separa hallazgos e inferencias. "
            "En Accionables propone consultas y verificaciones. En Evidencias y supuestos marca vacios de fuente. "
            "En Sintesis breve deja tesis operativa para continuar investigacion sin etiquetas editoriales."
        )
    elif action == "dialectic":
        task = (
            "Analiza la idea con metodo dialectico. "
            "Formula primero la tesis que sostiene el contenido; luego plantea una idea contraria fuerte como antitesis, "
            "con argumentos rigurosos y sin ridiculizar; finalmente propone una sintesis que conserve lo valioso de ambas posiciones. "
            "Enfoca la tension en decisiones editoriales, priorizacion de repo y forma de intervenir por lotes o ciclos."
        )
        expected = (
            "Incluye explicitamente la expresion 'Idea contraria' en el desarrollo dialectico. "
            "En Nucleo formula tesis y antitesis en tension. En Desarrollo argumenta ambas. "
            "En Accionables sugiere como contrastar cada postura. En Evidencias y supuestos explicita sesgos y limites. "
            "En Sintesis breve propone integracion operativa y pregunta abierta, pero redactadas como contenido y no como rotulos editoriales."
        )
    else:
        raise ValueError("Accion no reconocida.")

    return [
        {
            "role": "system",
            "content": (
                "Eres un asistente de analisis conceptual e investigacion editorial en espanol. "
                "Responde como si el usuario te hubiera enviado directamente una instruccion para trabajar un proyecto editorial. "
                "No menciones que el contenido viene de una nota. Usa estructura limpia, concreta y sin Markdown excesivo. "
                "Cumple estrictamente el contrato de secciones y redacta para filtrado organico entre canales."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Tarea: {task}\n"
                f"{expected}\n\n"
                f"Contrato de salida: {channel_contract}\n\n"
                f"Tema o titulo de referencia:\n{title}\n\n"
                f"Contenido:\n{corrected_text}\n\n"
                f"Conceptos involucrados:\n{concepts}"
            ),
        },
    ]


def _note_action_generation_options(action: str) -> tuple[int, float]:
    return SETTINGS.azure_openai_max_output_tokens, 0.4


def _play_action_generation_options(action: str) -> tuple[int, float]:
    return SETTINGS.azure_openai_max_output_tokens, 0.3


def _format_action_header(action: str) -> str:
    if action == "explain":
        return "Explicacion"
    if action == "suggest":
        return "Sugerencias"
    if action == "research":
        return "Investigacion"
    if action == "dialectic":
        return "Dialectica"
    return "Resultado"


def _split_telegram_text(text: str, limit: int = 3800) -> list[str]:
    if len(text) <= limit:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit)
        if split_at < limit // 2:
            split_at = limit
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


async def _reply_audio_copy(message, text: str, prefix: str) -> bool:
    """Genera un unico MP3 con Polly y lo envia completo como audio."""
    if message is None or not polly_audio_enabled(SETTINGS):
        return False
    merged_audio: Path | None = None
    try:
        merged_audio = await asyncio.to_thread(synthesize_text_to_single_mp3, SETTINGS, text, prefix)
        if merged_audio is None:
            return False
        return await _send_audio_file(message, merged_audio, text, prefix)
    except Exception:
        return False
    finally:
        if merged_audio is not None:
            merged_audio.unlink(missing_ok=True)


def _should_send_audio(prefix: str) -> bool:
    """Permite audio solo para respuestas de contenido (no estados/progreso/errores)."""
    content_prefixes = (
        "note_",
        "action_",
        "start",
    )
    return any(prefix.startswith(item) for item in content_prefixes)


def _safe_output_filename(filename: str) -> str:
    raw_name = Path(filename).name.strip() or "respuesta.md"
    safe_name = "".join(char if char.isalnum() or char in {"_", "-", "."} else "_" for char in raw_name)
    if not safe_name.lower().endswith(".md"):
        safe_name += ".md"
    return safe_name


def _telegram_compact_name(path: Path, extension: str) -> str:
    stem = path.stem
    action_suffix = ""
    if "." in stem:
        stem, action_suffix = stem.rsplit(".", 1)

    parts = stem.split("_", 2)
    if len(parts) >= 3:
        identifier = f"{parts[0]}_{parts[1]}"
        title = parts[2][:32]
        compact = f"{identifier}_{title}"
    else:
        compact = stem[:50]

    if action_suffix:
        compact = f"{compact}.{action_suffix}"

    return f"{compact}.{extension}"


def _write_response_document(text: str, filename: str) -> Path:
    safe_name = _safe_output_filename(filename)
    output_dir = SETTINGS.audio_storage_dir / "responses"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / safe_name
    counter = 1
    while output_path.exists():
        output_path = output_dir / f"{output_path.stem}_{counter}{output_path.suffix}"
        counter += 1
    output_path.write_text(text, encoding="utf-8")
    return output_path


def _telegram_markdown_view(markdown: str) -> str:
    start = markdown.find("# ")
    if start >= 0:
        markdown = markdown[start:]

    end = markdown.find("\n## Procesamientos derivados")
    if end >= 0:
        markdown = markdown[:end]

    return markdown.strip() + "\n"


async def _reply_markdown_file(message, source_path: Path, filename: str):
    send_lock, _ = _ensure_telegram_send_primitives()
    raw = source_path.read_text(encoding="utf-8")
    if any(source_path.name.endswith(f".{suffix}.md") for suffix in ("explain", "suggest", "research", "dialectic", "proposal")):
        payload = _parse_derivative_markdown(raw)
        filtered = _build_channel_text(payload, "telegram")
    else:
        filtered = _telegram_markdown_view(raw)
    if any(source_path.name.endswith(f".{suffix}.md") for suffix in ("explain", "suggest", "research", "dialectic", "proposal")):
        stem = source_path.stem
        note_id, action = stem.rsplit(".", 1)
        safe_filename = _safe_output_filename(_telegram_compact_name(source_path, "md"))
    else:
        safe_filename = _safe_output_filename(_telegram_compact_name(source_path, "md"))
    document_path = await asyncio.to_thread(_write_response_document, filtered, safe_filename)
    try:
        async with send_lock:
            with document_path.open("rb") as document_stream:
                return await message.reply_document(document=document_stream, filename=safe_filename)
    finally:
        document_path.unlink(missing_ok=True)


async def _reply_text_or_document(message, text: str, prefix: str, **reply_kwargs):
    send_lock, _ = _ensure_telegram_send_primitives()
    if len(text) <= 3800:
        async with send_lock:
            return await message.reply_text(text, **reply_kwargs)

    filename = prefix if str(prefix).lower().endswith(".md") else f"{prefix}.md"
    document_path = await asyncio.to_thread(_write_response_document, text, filename)
    try:
        async with send_lock:
            with document_path.open("rb") as document_stream:
                return await message.reply_document(
                    document=document_stream,
                    filename=_safe_output_filename(filename),
                    caption="Respuesta completa en un solo archivo.",
                    **reply_kwargs,
                )
    finally:
        document_path.unlink(missing_ok=True)


async def _reply_text_chunks(message, text: str, *, limit: int = 3800, **last_reply_kwargs):
    chunks = _split_telegram_text(text, limit=limit)
    send_lock, _ = _ensure_telegram_send_primitives()
    sent_message = None
    async with send_lock:
        for index, chunk in enumerate(chunks):
            kwargs = last_reply_kwargs if index == len(chunks) - 1 else {}
            sent_message = await message.reply_text(chunk, **kwargs)
    return sent_message


async def _send_text_with_optional_audio(message, text: str, prefix: str, **reply_kwargs):
    sent = await _reply_text_or_document(message, text, prefix, **reply_kwargs)
    if _should_send_audio(prefix):
        await _reply_audio_copy(message, text, prefix)
    return sent


async def _send_note_reply_with_audio(message, text: str, audio_text: str, prefix: str, **reply_kwargs):
    spoken_text = audio_text.strip() if audio_text.strip() else text
    sent = await _reply_text_or_document(message, text, prefix, **reply_kwargs)
    if _should_send_audio(prefix):
        await _reply_audio_copy(message, spoken_text, prefix)
    return sent


async def _reply_with_note_actions(update: Update, context: ContextTypes.DEFAULT_TYPE, analysis: dict, saved: SavedNote) -> None:
    if not update.message:
        return
    note_id = _note_id_from_saved(saved)
    _store_note_context(context, note_id, analysis, saved)
    clipboard_analysis = dict(analysis)
    clipboard_analysis["_note_path"] = str(saved.note_path)
    clipboard_copied = await asyncio.to_thread(_copy_clean_note_to_clipboard, clipboard_analysis)
    reply_text = _format_note_reply(analysis, saved, clipboard_copied=clipboard_copied)
    audio_text = _build_note_audio_text(analysis, saved)
    note_prefix = f"note_{note_id}"
    async with _foreground_note_delivery():
        sent_message = await _reply_text_chunks(
            update.message,
            reply_text,
            reply_markup=_build_note_action_keyboard(note_id),
        )
        note_context = _get_note_context(note_id)
        if note_context is not None:
            note_context["status_message"] = sent_message
        await _reply_markdown_file(update.message, saved.note_path, saved.note_path.name)
        if _should_send_audio(note_prefix):
            await _reply_audio_copy(update.message, audio_text, note_prefix)
    await _enqueue_default_derivatives(note_id)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    greeting = "Hola. Enviame texto, audio o documento; lo convierto en una nota limpia con conceptos clave. Usa /motor para enviar una instruccion al motor inteligente de AulaTeX."
    await _send_text_with_optional_audio(update.message, greeting, "start")


async def handle_motor_capabilities(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    capabilities = motor_capabilities(SETTINGS.aulatex_motor_execution_mode)
    await _reply_text_chunks(update.message, format_motor_capabilities_markdown(capabilities))


def _build_motor_confirmation_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Ejecutar motor", callback_data=f"{MOTOR_ACTION_PREFIX}:run:{token}"),
                InlineKeyboardButton("❌ Cancelar", callback_data=f"{MOTOR_ACTION_PREFIX}:cancel:{token}"),
            ]
        ]
    )


async def _handle_intelligent_instruction(message, instruction: str, context: ContextTypes.DEFAULT_TYPE) -> None:
    if message is None:
        return
    clean_instruction = instruction.strip()
    if not clean_instruction:
        await _send_text_with_optional_audio(message, instruction_help_text(), "motor_help")
        return

    await _send_text_with_optional_audio(
        message,
        "Instruccion recibida. Preparando plan para validacion...",
        "planning_motor",
    )

    try:
        plan = await asyncio.to_thread(plan_intelligent_dispatch, clean_instruction, SETTINGS)
        token = uuid.uuid4().hex[:12]
        pending = context.user_data.setdefault("pending_motor_dispatches", {})
        pending[token] = plan
        await _reply_text_chunks(
            message,
            format_dispatch_plan_markdown(plan),
            reply_markup=_build_motor_confirmation_keyboard(token),
        )
    except Exception as exc:
        await _send_text_with_optional_audio(message, f"No pude preparar el plan del motor inteligente: {exc}", "error_motor")


async def handle_intelligent_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return
    args = getattr(context, "args", None) or []
    await _handle_intelligent_instruction(update.message, " ".join(args).strip(), context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return

    raw_text = update.message.text.strip()
    if not raw_text:
        await _send_text_with_optional_audio(update.message, "Envía un texto no vacío.", "empty_text")
        return

    # Recuerda el último texto para los comandos /imagen y /video.
    context.user_data["last_note_text"] = raw_text

    intelligent_instruction = extract_intelligent_instruction(raw_text)
    if intelligent_instruction is not None:
        await _handle_intelligent_instruction(update.message, intelligent_instruction, context)
        return

    await _send_text_with_optional_audio(update.message, "Texto recibido. Analizando y guardando nota...", "processing_text")

    try:
        analysis = await asyncio.to_thread(
            analyze_text,
            raw_text,
            "telegram_text",
            SETTINGS,
            "telegram_text",
        )
        saved = await asyncio.to_thread(save_note, SETTINGS.notes_dir, analysis)
        await _reply_with_note_actions(update, context, analysis, saved)
    except Exception as exc:
        await _send_text_with_optional_audio(update.message, f"No pude procesar la nota: {exc}", "error_text")
        return


def _resolve_audio_attachment(update: Update) -> tuple[object, str] | None:
    if not update.message:
        return None
    if update.message.voice:
        return update.message.voice, "voice"
    if update.message.audio:
        return update.message.audio, "audio"
    return None


def _resolve_document_attachment(update: Update):
    if not update.message:
        return None
    return update.message.document


def _document_suffix(file_name: str | None) -> str:
    return Path(file_name or "").suffix.lower()


def _build_document_filename(file_unique_id: str, original_name: str | None = None) -> str:
    suffix = _document_suffix(original_name)
    if not suffix:
        suffix = ".bin"
    return f"{file_unique_id}{suffix}"


def _build_audio_filename(file_unique_id: str, media_type: str, original_name: str | None = None) -> str:
    suffix = Path(original_name).suffix if original_name else ""
    if not suffix:
        suffix = ".ogg" if media_type == "voice" else ".bin"
    return f"{file_unique_id}{suffix}"


async def handle_audio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    attachment = _resolve_audio_attachment(update)
    if not attachment:
        await _send_text_with_optional_audio(update.message, "Envía un audio válido.", "invalid_audio")
        return

    telegram_audio, media_type = attachment
    SETTINGS.audio_storage_dir.mkdir(parents=True, exist_ok=True)

    telegram_file = await telegram_audio.get_file()
    original_name = getattr(telegram_audio, "file_name", None)
    audio_path = SETTINGS.audio_storage_dir / _build_audio_filename(
        telegram_audio.file_unique_id,
        media_type,
        original_name,
    )
    await telegram_file.download_to_drive(str(audio_path))

    await _send_text_with_optional_audio(update.message, "Audio recibido. Transcribiendo, analizando y guardando nota...", "processing_audio")

    try:
        transcript = await asyncio.to_thread(transcribe_audio, str(audio_path), SETTINGS)
        analysis = await asyncio.to_thread(
            analyze_text,
            transcript,
            str(audio_path),
            SETTINGS,
            f"telegram_{media_type}",
        )
        saved = await asyncio.to_thread(save_note, SETTINGS.notes_dir, analysis)
        await _reply_with_note_actions(update, context, analysis, saved)
    except Exception as exc:
        await _send_text_with_optional_audio(update.message, f"No pude procesar el audio: {exc}", "error_audio")
        return
    audio_path.unlink(missing_ok=True)


async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    telegram_document = _resolve_document_attachment(update)
    if not telegram_document:
        await _send_text_with_optional_audio(update.message, "Envía un documento válido.", "invalid_document")
        return

    original_name = getattr(telegram_document, "file_name", None)
    suffix = _document_suffix(original_name)
    if suffix not in SUPPORTED_DOCUMENT_SUFFIXES:
        await _send_text_with_optional_audio(
            update.message,
            "Formato de documento no soportado. Usa PDF, TXT, MD o DOCX.",
            "unsupported_document",
        )
        return

    document_dir = SETTINGS.audio_storage_dir / "documents"
    document_dir.mkdir(parents=True, exist_ok=True)
    document_path = document_dir / _build_document_filename(telegram_document.file_unique_id, original_name)

    try:
        telegram_file = await telegram_document.get_file()
        await telegram_file.download_to_drive(str(document_path))

        await _send_text_with_optional_audio(
            update.message,
            "Documento recibido. Leyendo, sintetizando y guardando nota...",
            "processing_document",
        )

        document_text = await asyncio.to_thread(read_document_text, document_path)
        analysis = await asyncio.to_thread(
            analyze_text,
            document_text,
            str(document_path),
            SETTINGS,
            "telegram_document",
        )
        saved = await asyncio.to_thread(save_note, SETTINGS.notes_dir, analysis)
        await _reply_with_note_actions(update, context, analysis, saved)
    except Exception as exc:
        await _send_text_with_optional_audio(update.message, f"No pude procesar el documento: {exc}", "error_document")
        return
    finally:
        document_path.unlink(missing_ok=True)


async def handle_motor_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return
    try:
        await query.answer("Procesando...")
    except Exception:
        pass
    parts = query.data.split(":", 2)
    if len(parts) != 3 or parts[0] != MOTOR_ACTION_PREFIX:
        return
    _, action, token = parts
    pending = context.user_data.setdefault("pending_motor_dispatches", {})
    plan = pending.pop(token, None)
    if plan is None:
        if query.message:
            await _send_text_with_optional_audio(query.message, "La solicitud del motor ya no está disponible o ya fue procesada.", "motor_missing")
        return
    if action == "cancel":
        if query.message:
            await query.message.edit_reply_markup(reply_markup=None)
            await _send_text_with_optional_audio(query.message, "Solicitud cancelada. No se ejecutó el motor inteligente.", "motor_cancelled")
        return
    if action != "run":
        if query.message:
            await _send_text_with_optional_audio(query.message, "Acción de motor no reconocida.", "motor_invalid")
        return
    if query.message:
        await query.message.edit_reply_markup(reply_markup=None)
        await _send_text_with_optional_audio(query.message, "Validación recibida. Ejecutando motor inteligente...", "processing_motor")
    try:
        dispatch = await asyncio.to_thread(
            execute_intelligent_dispatch_plan,
            plan,
            execution_mode=SETTINGS.aulatex_motor_execution_mode,
        )
        if query.message:
            await _reply_text_chunks(query.message, format_dispatch_summary(dispatch))
            await _reply_markdown_file(query.message, dispatch.result.report_path, dispatch.result.report_path.name)
    except Exception as exc:
        if query.message:
            await _send_text_with_optional_audio(query.message, f"No pude ejecutar el motor inteligente: {exc}", "error_motor")


async def handle_note_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query or not query.data:
        return

    try:
        await query.answer("Procesando...")
    except Exception:
        pass
    parts = query.data.split(":", 2)
    if len(parts) != 3 or parts[0] != NOTE_ACTION_PREFIX:
        if query.message:
            await _send_text_with_optional_audio(query.message, "No reconozco esa accion.", "invalid_action")
        return

    _, action, note_id = parts
    notes = context.user_data.setdefault("notes", {})
    note_context = notes.get(note_id)
    if note_context:
        note_context = _register_note_context(note_id, note_context)
        notes[note_id] = note_context
    if not note_context:
        note_context = _get_note_context(note_id)
        if note_context:
            notes[note_id] = note_context
    if not note_context:
        if query.message:
            await _send_text_with_optional_audio(query.message, "No encuentro la nota reciente para procesarla.", "missing_note")
        return

    if query.message:
        note_context["status_message"] = query.message

    if action != "play" and note_context.get("play_active"):
        if action == "realize":
            if query.message:
                await _send_text_with_optional_audio(
                    query.message,
                    "Realizar: espera a que termine Play y vuelve a presionar el boton.",
                    "queued_realize_blocked",
                )
            return
        queued = _queue_action_after_play(note_context, action)
        if query.message:
            if queued:
                await _send_text_with_optional_audio(
                    query.message,
                    f"{NOTE_ACTIONS[action]}: se agrego a la cola para despues de Play.",
                    f"queued_{action}",
                )
            else:
                await _send_text_with_optional_audio(
                    query.message,
                    f"{NOTE_ACTIONS[action]}: ya estaba en cola para despues de Play.",
                    f"queued_existing_{action}",
                )
        return

    await _set_note_action_keyboard_state(query, note_id, action)

    if action == "play":
        if not query.message:
            await _set_note_action_keyboard_state(query, note_id, None)
            return
        queued = await _enqueue_play_jobs(note_id, query.message)
        if not queued:
            try:
                await query.answer("Play ya en curso.")
            except Exception:
                pass
        return

    if not query.message:
        await _set_note_action_keyboard_state(query, note_id, None)
        return

    if action == "proposal" and not _base_editorial_actions_completed(note_context):
        await _send_text_with_optional_audio(
            query.message,
            "Propuesta: disponible cuando terminen Explicar, Sugerencias, Investigar y Dialectica.",
            "proposal_locked",
        )
        await _set_note_action_keyboard_state(query, note_id, None)
        return

    if action == "proposal":
        current_path, _ = await _ensure_proposal_markdown(note_id)
        if current_path is not None:
            await _reply_markdown_file(query.message, current_path, current_path.name)
        else:
            await _send_text_with_optional_audio(query.message, "Propuesta: no se pudo generar la propuesta integral.", "proposal_error")
        await _set_note_action_keyboard_state(query, note_id, None)
        return

    if action == "realize":
        if not _proposal_ready(note_id, note_context):
            await _send_text_with_optional_audio(
                query.message,
                "Realizar: primero genera la propuesta integral.",
                "realize_locked",
            )
            await _set_note_action_keyboard_state(query, note_id, None)
            return
        try:
            await _run_realize_action(query.message, note_id)
        except Exception as exc:
            await _send_text_with_optional_audio(query.message, f"No pude ejecutar la propuesta integral: {exc}", "realize_error")
        await _set_note_action_keyboard_state(query, note_id, None)
        return

    if action not in PLAY_SEQUENCE and action != "proposal":
        await _send_text_with_optional_audio(query.message, "No reconozco esa accion.", "invalid_action")
        await _set_note_action_keyboard_state(query, note_id, None)
        return

    note_path = _resolve_note_path(note_id, note_context)
    current_derivative_path = derivative_path(note_path, action) if note_path else None
    status = note_context.setdefault("derivative_statuses", {}).get(action, DERIVATIVE_STATUS_PENDING)
    if current_derivative_path and current_derivative_path.exists():
        note_context["derivative_statuses"][action] = DERIVATIVE_STATUS_COMPLETED
        await _refresh_note_action_keyboard(note_id)
        derivative_markdown = await asyncio.to_thread(current_derivative_path.read_text, "utf-8")
        derivative_payload = await asyncio.to_thread(_parse_derivative_markdown, derivative_markdown)
        clipboard_text = _build_channel_text(derivative_payload, "clipboard")
        await asyncio.to_thread(_copy_text_to_clipboard, clipboard_text)
        await _send_text_with_optional_audio(query.message, f"{NOTE_ACTIONS[action]}: copiado al portapapeles.", f"clipboard_{action}")
    elif status == DERIVATIVE_STATUS_PROCESSING:
        await _send_text_with_optional_audio(query.message, f"{NOTE_ACTIONS[action]}: procesando en segundo plano.", f"status_{action}")
        await _set_note_action_keyboard_state(query, note_id, None)
        return
    elif status == DERIVATIVE_STATUS_ERROR:
        await _update_derivative_status(note_id, action, DERIVATIVE_STATUS_PENDING)
        await _enqueue_derivative_job("derive", note_id, action)
        await _send_text_with_optional_audio(query.message, f"{NOTE_ACTIONS[action]}: reintentando en segundo plano.", f"retry_{action}")
    else:
        await _update_derivative_status(note_id, action, DERIVATIVE_STATUS_PENDING)
        await _enqueue_derivative_job("derive", note_id, action)
        await _send_text_with_optional_audio(query.message, f"{NOTE_ACTIONS[action]}: pendiente. Se esta generando en segundo plano.", f"pending_{action}")

    await _set_note_action_keyboard_state(query, note_id, None)


async def _generate_visual_command(update: Update, context: ContextTypes.DEFAULT_TYPE, kind: str) -> None:
    """Genera imagen/video conceptual de la última nota (conocimiento portado de
    notas-telegram/editor-inteligente). Temas conceptuales, no triviales."""
    if not update.message:
        return
    source = ""
    if context.args:
        source = " ".join(context.args).strip()
    if not source:
        source = (context.user_data.get("last_note_text") or "").strip()
    if not source:
        etq = "video" if kind == "video" else "imagen"
        await _send_text_with_optional_audio(
            update.message,
            f"No hay nota reciente. Envía una nota o usa /{etq} <texto conceptual>.",
            "visual_no_source")
        return

    etiqueta = "video" if kind == "video" else "imagen"
    espera = " varios minutos" if kind == "video" else " ~30s"
    await _send_text_with_optional_audio(
        update.message, f"Generando {etiqueta} conceptual de la nota (puede tardar{espera})...",
        f"visual_{kind}_start")
    try:
        from .visual_gen import visual_from_note
        result = await asyncio.to_thread(visual_from_note, source, kind, SETTINGS)
    except Exception as exc:
        await _send_text_with_optional_audio(update.message, f"No pude generar la {etiqueta}: {exc}", f"visual_{kind}_error")
        return
    if not result.get("ok"):
        await _send_text_with_optional_audio(
            update.message, f"No se generó la {etiqueta}: {result.get('reason', 'motivo desconocido')}",
            f"visual_{kind}_skip")
        return
    path = result["path"]
    caption = f"🎨 {etiqueta.capitalize()} conceptual de la nota."
    try:
        with open(path, "rb") as fh:
            if kind == "video":
                await update.message.reply_video(fh, caption=caption)
            else:
                await update.message.reply_photo(fh, caption=caption)
    except Exception as exc:
        await _send_text_with_optional_audio(update.message, f"Generada pero no pude enviarla: {exc}", f"visual_{kind}_send_error")


async def imagen_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _generate_visual_command(update, context, "image")


async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _generate_visual_command(update, context, "video")


def build_application():
    app = ApplicationBuilder().token(SETTINGS.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("motor", handle_intelligent_command))
    app.add_handler(CommandHandler("motor_capacidades", handle_motor_capabilities))
    app.add_handler(CommandHandler("imagen", imagen_command))
    app.add_handler(CommandHandler("video", video_command))
    app.add_handler(CallbackQueryHandler(handle_motor_action, pattern=f"^{MOTOR_ACTION_PREFIX}:"))
    app.add_handler(CallbackQueryHandler(handle_note_action, pattern=f"^{NOTE_ACTION_PREFIX}:"))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handle_audio))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    return app


def main() -> None:
    missing = validate_settings(SETTINGS)
    if missing:
        raise RuntimeError("Faltan variables de entorno requeridas: " + ", ".join(missing))

    acquire_instance_lock()
    SETTINGS.notes_dir.mkdir(parents=True, exist_ok=True)
    SETTINGS.audio_storage_dir.mkdir(parents=True, exist_ok=True)
    app = build_application()
    app.run_polling()


if __name__ == "__main__":
    main()
