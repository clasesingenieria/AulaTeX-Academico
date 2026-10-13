from __future__ import annotations

from .api_client import ApiConfig, create_client, chat_json_list
from .concept_extractor import extract_candidate_concepts
from .preprocessing import Fragment
from .subject_profiles import SUBJECT_PROFILES


def normalize_concepts_with_chat(concepts: list[str], config: ApiConfig, max_items: int | None = None) -> list[str]:
    if not config.chat_model:
        raise RuntimeError("Falta deployment/modelo de chat. Configura el deployment correspondiente del proveedor activo.")
    max_items = max_items or len(concepts)
    client = create_client(config)
    system = "Eres un normalizador de conceptos académicos. Devuelve únicamente un arreglo JSON de strings. No inventes citas."
    user = (
        "Normaliza y deduplica esta lista de conceptos. Conserva términos académicos claros, en español, sin explicación:\n"
        + "\n".join(f"- {c}" for c in concepts)
    )
    return chat_json_list(client, config, system, user, max_items=max_items)


def extract_concepts_with_chat(fragments: list[Fragment], config: ApiConfig, top_n: int = 25) -> list[str]:
    local = extract_candidate_concepts(fragments, top_n=max(top_n * 3, top_n))
    return normalize_concepts_with_chat(local, config, max_items=top_n)


def curate_concepts_for_subject_with_chat(
    concepts: list[str],
    *,
    subject_slug: str | None,
    config: ApiConfig,
    top_n: int = 20,
) -> dict:
    if not config.chat_model:
        raise RuntimeError("Falta deployment/modelo de chat para depuración por materia.")

    client = create_client(config)
    profile = SUBJECT_PROFILES.get(subject_slug or "", {})
    focus = profile.get("focus", [])
    ban_tokens = sorted(profile.get("ban_tokens", []))

    system = (
        "Eres un curador editorial de conceptos académicos. "
        "Debes depurar listas de conceptos según la materia y conservar únicamente los más útiles para redactar una actividad. "
        "Devuelve únicamente JSON válido."
    )
    user = (
        f"Materia: {subject_slug or 'desconocida'}\n"
        f"Conceptos candidatos: {concepts}\n"
        f"Conceptos foco sugeridos para la materia: {focus}\n"
        f"Tokens o términos a penalizar/eliminar: {ban_tokens}\n\n"
        f"Selecciona hasta {top_n} conceptos de alto valor editorial. "
        "Elimina conceptos administrativos, ruidosos, demasiado genéricos o que no sirvan para resolver la actividad. "
        "Devuelve JSON con esta estructura: "
        '{"subject_slug":"...","kept":[...],"discarded":[...],"notes":"..."}'
    )
    from .api_client import chat_json_data

    data = chat_json_data(client, config, system, user)
    if not isinstance(data, dict):
        return {
            "subject_slug": subject_slug,
            "kept": concepts[:top_n],
            "discarded": [],
            "notes": str(data),
        }

    kept = data.get("kept", []) or []
    discarded = data.get("discarded", []) or []
    notes = data.get("notes", "")
    if not isinstance(kept, list):
        kept = []
    if not isinstance(discarded, list):
        discarded = []
    kept = [str(c).strip() for c in kept if str(c).strip()][:top_n]
    discarded = [str(c).strip() for c in discarded if str(c).strip()]
    return {
        "subject_slug": subject_slug,
        "kept": kept,
        "discarded": discarded,
        "notes": str(notes),
    }
