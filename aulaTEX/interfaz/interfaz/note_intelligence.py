"""Capacidades inteligentes avanzadas para notas-telegram.

Implementa, sobre la infraestructura existente (config + invoke_chat + vector
store), cinco mejoras al estilo del catÃ¡logo de libros:

  A) Routing inteligente por tarea: cada tipo de operaciÃ³n usa el proveedor
     LLM mÃ¡s adecuado (velocidad para resÃºmenes, profundidad para anÃ¡lisis).
  B) Red de seguridad opus: si el proveedor principal falla, claude-opus
     "entra al quite" como excepciÃ³n de mÃ¡xima calidad.
  C) BÃºsqueda semÃ¡ntica mejorada: recupera candidatos del vector store y los
     re-ordena (rerank) con el LLM segÃºn relevancia real a la consulta.
  D) AuditorÃ­a de notas: detecta notas duplicadas, mal clasificadas o pobres,
     y produce recomendaciones de acciÃ³n.
  E) Enriquecimiento de notas: extrae etiquetas, tareas, fechas y entidades de
     una nota para hacerla mÃ¡s accionable y buscable.

El tiempo no es prioridad: prima la calidad. Reutiliza el mismo recurso Azure
y las credenciales cifradas ya presentes en notas.env.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable

from .config import Settings, llm_max_output_tokens, load_settings, settings_for_llm_provider
from .azure_openai_client import invoke_chat


def _noop(_message: str) -> None:
    pass


# ============================================================
#  A) Routing inteligente por tarea
# ------------------------------------------------------------
#  Cada tarea usa una cadena de proveedores (el primero disponible se usa;
#  ante error se pasa al siguiente). B) La red de seguridad opus va SIEMPRE al
#  final de cada cadena como Ãºltimo recurso.
# ============================================================
_OPUS = "claude-foundry"  # alias de claude-opus en este proyecto

# Proveedores realmente soportados por config.py de este proyecto:
#   model-router (rÃ¡pido/versÃ¡til), codex, gpt-pro, claude-foundry (opus),
#   azure-openai. El routing usa estos y deja opus como red de seguridad.
TASK_PROVIDER_CHAINS: dict[str, list[str]] = {
    # ResÃºmenes/limpieza rÃ¡pida y fiel -> model-router (Ã¡gil) -> opus
    "summarize": ["model-router", _OPUS],
    # AnÃ¡lisis profundo de nota/documento -> codex -> gpt-pro -> opus
    "analyze": ["codex", "gpt-pro", _OPUS],
    # Cuestionarios (precisiÃ³n estructural) -> opus -> codex -> gpt-pro
    "questionnaire": [_OPUS, "codex", "gpt-pro"],
    # Enriquecimiento (tags/tareas/fechas) -> codex -> model-router -> opus
    "enrich": ["codex", "model-router", _OPUS],
    # Reordenar resultados de bÃºsqueda -> model-router (rÃ¡pido) -> opus
    "rerank": ["model-router", _OPUS],
    # AuditorÃ­a/juicio -> opus (juicio) -> codex -> gpt-pro
    "audit": [_OPUS, "codex", "gpt-pro"],
    "default": ["codex", _OPUS, "gpt-pro"],
}


def provider_chain_for_task(task: str) -> list[str]:
    """Cadena de proveedores para una tarea.

    ``AULATEX_MODEL_ROUTER_ONLY=1`` impide fallbacks a otros deployments.
    """
    import os

    router_only = (os.getenv("AULATEX_MODEL_ROUTER_ONLY", "") or "").strip().lower()
    if router_only in {"1", "true", "yes", "on", "si", "sí"}:
        return ["model-router"]

    override = (os.getenv("AULATEX_LLM_PROVIDER", "auto") or "auto").strip().lower()
    base = list(TASK_PROVIDER_CHAINS.get(task, TASK_PROVIDER_CHAINS["default"]))
    # Garantiza que opus estÃ© como red de seguridad final.
    if _OPUS not in base:
        base.append(_OPUS)
    if override and override != "auto":
        return [override] + [p for p in base if p != override]
    return base


def _provider_is_configured(settings: Settings, provider: str) -> bool:
    try:
        cfg = settings_for_llm_provider(settings, provider)
    except Exception:
        return False
    return bool(cfg.azure_openai_endpoint and cfg.azure_openai_api_key and cfg.azure_openai_chat_deployment)


def smart_invoke(
    task: str,
    messages: list[dict[str, str]],
    settings: Settings | None = None,
    max_tokens: int | None = None,
    temperature: float | None = 0.2,
    response_format_json: bool = False,
    emit: Callable[[str], None] = _noop,
) -> str:
    """Invoca el LLM enrutando por tarea con red de seguridad opus (A + B).

    Recorre la cadena de proveedores; si todos fallan, opus es el Ãºltimo
    recurso. Devuelve el texto de la respuesta o lanza si nada funcionÃ³.
    """
    settings = settings or load_settings()
    chain = provider_chain_for_task(task)
    errors: list[str] = []
    rescued = False

    for provider in chain:
        if not _provider_is_configured(settings, provider):
            continue
        cfg = settings_for_llm_provider(settings, provider)
        try:
            out = invoke_chat(
                cfg,
                messages,
                max_tokens=llm_max_output_tokens(cfg, max_tokens),
                temperature=temperature,
                response_format_json=response_format_json,
            )
            if out and out.strip():
                if provider == _OPUS and errors:
                    emit(f"  ðŸ›Ÿ Rescate opus para tarea '{task}'.")
                return out
            errors.append(f"{provider}: respuesta vacÃ­a")
        except Exception as exc:  # timeout, rate-limit, red...
            errors.append(f"{provider}: {str(exc)[:120]}")
            continue

    raise RuntimeError(f"NingÃºn proveedor resolviÃ³ la tarea '{task}'. " + " | ".join(errors[-3:]))


def _extract_json(text: str) -> dict[str, Any]:
    cleaned = (text or "").strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    decoder = json.JSONDecoder()
    for i, ch in enumerate(cleaned):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(cleaned[i:])
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    raise ValueError("La respuesta del LLM no contenÃ­a un objeto JSON vÃ¡lido.")


def smart_invoke_json(
    task: str,
    system_prompt: str,
    user_payload: dict[str, Any] | str,
    settings: Settings | None = None,
    max_tokens: int | None = 4096,
    emit: Callable[[str], None] = _noop,
) -> dict[str, Any]:
    """smart_invoke devolviendo JSON parseado (con reintento de reparaciÃ³n)."""
    content = user_payload if isinstance(user_payload, str) else json.dumps(user_payload, ensure_ascii=False)
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content},
    ]
    out = smart_invoke(task, messages, settings=settings, max_tokens=max_tokens,
                       temperature=0.1, response_format_json=True, emit=emit)
    return _extract_json(out)


# ============================================================
#  C) BÃºsqueda semÃ¡ntica mejorada (rerank con LLM)
# ============================================================
@dataclass
class RankedNote:
    path: str
    title: str
    score: float
    reason: str = ""


def _lexical_candidates(settings: Settings, query: str, limit: int, emit: Callable[[str], None]) -> list[dict[str, Any]]:
    """BÃºsqueda lÃ©xica sencilla por solapamiento de tokens (fallback cuando el
    vector store de embeddings estÃ¡ deshabilitado)."""
    from pathlib import Path

    notes_dir = Path(settings.notes_dir)
    if not notes_dir.exists():
        return []
    q_tokens = {t for t in re.split(r"\W+", query.lower()) if len(t) >= 3}
    if not q_tokens:
        return []
    scored: list[tuple[float, dict[str, Any]]] = []
    for path in notes_dir.rglob("*.md"):
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        low = content.lower()
        hits = sum(low.count(tok) for tok in q_tokens)
        if hits == 0:
            continue
        title = ""
        m = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        if m:
            title = m.group(1).strip()
        body = re.sub(r"^---.*?---", "", content, flags=re.DOTALL).strip()
        scored.append((float(hits), {
            "path": str(path),
            "title": title or path.stem,
            "snippet": body[:400],
            "base_score": float(hits),
        }))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [c for _, c in scored[:limit]]


def semantic_search(
    query: str,
    top_k: int = 5,
    settings: Settings | None = None,
    emit: Callable[[str], None] = _noop,
) -> list[RankedNote]:
    """Recupera notas del vector store y las re-ordena con el LLM por
    relevancia real a la consulta (rerank), mejorando la bÃºsqueda base."""
    settings = settings or load_settings()
    candidatos: list[dict[str, Any]] = []

    # 1) Intenta el vector store semÃ¡ntico (embeddings) si estÃ¡ habilitado.
    if getattr(settings, "langchain_notes_context_enabled", False):
        try:
            from .note_vector_store import ensure_note_vector_store_synced, query_note_vector_store
            ensure_note_vector_store_synced(settings)
            raw = query_note_vector_store(settings, query, top_k=max(top_k * 3, 12))
            for r in raw:
                candidatos.append({
                    "path": getattr(r, "path", ""),
                    "title": getattr(r, "title", ""),
                    "snippet": (getattr(r, "excerpt", "") or "")[:400],
                    "base_score": float(getattr(r, "score", 0.0) or 0.0),
                })
        except Exception as exc:
            emit(f"Vector store no disponible ({exc}); uso bÃºsqueda lÃ©xica.")

    # 2) Fallback lÃ©xico: si no hay vector store, busca por solapamiento de
    #    tokens en las notas del disco (siempre funciona).
    if not candidatos:
        candidatos = _lexical_candidates(settings, query, limit=max(top_k * 4, 16), emit=emit)
    if not candidatos:
        emit("Sin candidatos para la consulta.")
        return []

    # Rerank con LLM: pide reordenar por relevancia real (0-100).
    try:
        verdict = smart_invoke_json(
            "rerank",
            system_prompt=(
                "Eres un asistente de bÃºsqueda. Reordena las notas candidatas por "
                "relevancia real a la consulta del usuario. Devuelve solo JSON."
            ),
            user_payload={
                "query": query,
                "candidates": [{"i": i, "title": c["title"], "snippet": c["snippet"]} for i, c in enumerate(candidatos)],
                "response_schema": {"ranking": [{"i": "int", "score": "0-100", "reason": "string"}]},
            },
            settings=settings,
            emit=emit,
        )
        ranking = verdict.get("ranking") or []
    except Exception as exc:
        emit(f"Rerank LLM fallÃ³, se usa orden base: {exc}")
        ranking = [{"i": i, "score": int(c["base_score"] * 100), "reason": ""} for i, c in enumerate(candidatos)]

    resultados: list[RankedNote] = []
    for item in ranking:
        idx = item.get("i")
        if not isinstance(idx, int) or not (0 <= idx < len(candidatos)):
            continue
        c = candidatos[idx]
        try:
            score = max(0.0, min(100.0, float(item.get("score", 0))))
        except Exception:
            score = 0.0
        resultados.append(RankedNote(path=c["path"], title=c["title"], score=score, reason=str(item.get("reason", "")).strip()))
    resultados.sort(key=lambda r: r.score, reverse=True)
    return resultados[:top_k]


# ============================================================
#  E) Enriquecimiento de notas (tags / tareas / fechas / entidades)
# ============================================================
@dataclass
class NoteEnrichment:
    tags: list[str] = field(default_factory=list)
    tasks: list[str] = field(default_factory=list)
    dates: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    summary: str = ""


def enrich_note(text: str, settings: Settings | None = None, emit: Callable[[str], None] = _noop) -> NoteEnrichment:
    """Extrae etiquetas, tareas accionables, fechas y entidades de una nota."""
    settings = settings or load_settings()
    if not text.strip():
        return NoteEnrichment()
    data = smart_invoke_json(
        "enrich",
        system_prompt=(
            "Eres un asistente que enriquece notas personales. Extrae metadatos "
            "accionables SIN inventar. Devuelve solo JSON."
        ),
        user_payload={
            "note": text[:12000],
            "response_schema": {
                "tags": ["string (3-8 etiquetas temÃ¡ticas)"],
                "tasks": ["string (tareas accionables detectadas, si las hay)"],
                "dates": ["string (fechas o plazos mencionados, formato libre)"],
                "entities": ["string (personas, lugares, organizaciones)"],
                "summary": "string (1 frase con la idea central)",
            },
        },
        settings=settings,
        emit=emit,
    )
    def _lst(k: str) -> list[str]:
        v = data.get(k)
        return [str(x).strip() for x in v if str(x).strip()] if isinstance(v, list) else []
    return NoteEnrichment(
        tags=_lst("tags"),
        tasks=_lst("tasks"),
        dates=_lst("dates"),
        entities=_lst("entities"),
        summary=str(data.get("summary", "")).strip(),
    )


# ============================================================
#  D) AuditorÃ­a de notas
# ============================================================
@dataclass
class NoteRecommendation:
    id: str
    severity: str
    category: str
    title: str
    detail: str
    action: str
    path: str = ""


def _iter_note_files(settings: Settings) -> list:
    from pathlib import Path
    notes_dir = Path(settings.notes_dir)
    if not notes_dir.exists():
        return []
    return sorted(notes_dir.rglob("*.md"))


def audit_notes(
    settings: Settings | None = None,
    emit: Callable[[str], None] = _noop,
    stop_check: Callable[[], bool] = lambda: False,
    limit: int | None = None,
) -> list[NoteRecommendation]:
    """Audita las notas: detecta vacÃ­as/pobres, sin tÃ­tulo y posibles
    duplicadas (por tÃ­tulo muy similar). Genera recomendaciones."""
    settings = settings or load_settings()
    files = _iter_note_files(settings)
    if limit:
        files = files[:limit]
    emit(f"Auditando {len(files)} notas...")

    recs: list[NoteRecommendation] = []
    titles: dict[str, str] = {}

    def _norm(s: str) -> str:
        import unicodedata
        n = unicodedata.normalize("NFKD", s or "")
        n = "".join(c for c in n if not unicodedata.combining(c)).lower()
        return re.sub(r"[^a-z0-9 ]", " ", n).strip()

    for idx, path in enumerate(files, start=1):
        if stop_check():
            break
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        body = re.sub(r"^---.*?---", "", content, flags=re.DOTALL).strip()
        title = ""
        m = re.search(r"^#\s+(.+)$", content, flags=re.MULTILINE)
        if m:
            title = m.group(1).strip()

        # Nota vacÃ­a o muy pobre.
        if len(body) < 40:
            recs.append(NoteRecommendation(
                id=f"note:empty:{path.name}", severity="media", category="Nota vacÃ­a o pobre",
                title=title or path.name, detail=f"Contenido muy breve ({len(body)} chars).",
                action="Revisar, completar o eliminar la nota.", path=str(path)))
        # Sin tÃ­tulo.
        if not title:
            recs.append(NoteRecommendation(
                id=f"note:untitled:{path.name}", severity="baja", category="Nota sin tÃ­tulo",
                title=path.name, detail="No se detectÃ³ encabezado H1.",
                action="AÃ±adir un tÃ­tulo descriptivo.", path=str(path)))
        # Duplicado por tÃ­tulo muy similar.
        key = _norm(title)
        if key and len(key) > 6:
            if key in titles:
                recs.append(NoteRecommendation(
                    id=f"note:dup:{path.name}", severity="media", category="Posible nota duplicada",
                    title=title, detail=f"TÃ­tulo muy similar a: {titles[key]}",
                    action="Revisar si es duplicada y fusionar/eliminar.", path=str(path)))
            else:
                titles[key] = path.name

    order = {"alta": 0, "media": 1, "baja": 2}
    recs.sort(key=lambda r: (order.get(r.severity, 3), r.title.lower()))
    emit(f"AuditorÃ­a de notas: {len(recs)} recomendaciones.")
    return recs


__all__ = [
    "smart_invoke", "smart_invoke_json", "provider_chain_for_task",
    "semantic_search", "RankedNote", "enrich_note", "NoteEnrichment",
    "audit_notes", "NoteRecommendation",
]
