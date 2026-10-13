from __future__ import annotations

from typing import Any

from .api_client import ApiConfig, create_client, chat_json_data
from .search import SearchHit


def _serialize_hits(hits: list[SearchHit], limit: int = 5) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = []
    for hit in hits[:limit]:
        data.append(
            {
                "fuente": hit.source_name,
                "ubicacion": hit.location,
                "similitud": round(hit.score, 4),
                "cita": hit.quote,
            }
        )
    return data


def _merge_hits(existing: list[SearchHit], new_hits: list[SearchHit]) -> list[SearchHit]:
    merged: list[SearchHit] = []
    seen: set[tuple[str, str]] = set()
    for hit in existing + new_hits:
        key = (hit.fragment_id, hit.quote[:180].lower())
        if key in seen:
            continue
        seen.add(key)
        merged.append(hit)
    merged.sort(key=lambda h: (-h.score, h.source_name.lower(), h.page, h.fragment_id))
    return merged


def _evaluate_concept_iteration(client: Any, config: ApiConfig, concept: str, hits: list[SearchHit], round_index: int, max_queries: int) -> dict[str, Any]:
    system = (
        "Eres un evaluador editorial de fichas conceptuales jurídicas y académicas. "
        "Debes decidir si la evidencia recuperada cubre suficientemente el concepto y, si falta profundidad, proponer nuevas consultas de búsqueda. "
        "Devuelve únicamente JSON válido."
    )
    user = (
        "Evalúa la calidad de la ficha para este concepto. Considera si las citas cubren: definición, fundamento, autor, ejemplo o aplicación y crítica/límite. "
        "Si faltan elementos, propone consultas adicionales de búsqueda muy concretas.\n\n"
        f"CONCEPTO: {concept}\n"
        f"RONDA: {round_index}\n"
        f"CITAS RECUPERADAS: {_serialize_hits(hits)}\n\n"
        "Devuelve un JSON con esta estructura:\n"
        "{\n"
        '  "suficiente": true/false,\n'
        '  "cobertura": {"definicion": bool, "fundamento": bool, "autor": bool, "ejemplo": bool, "critica": bool},\n'
        '  "faltantes": ["..."],\n'
        f'  "consultas": [hasta {max_queries} consultas concretas],\n'
        '  "nota": "..."\n'
        "}"
    )
    data = chat_json_data(client, config, system, user)
    if not isinstance(data, dict):
        return {
            "suficiente": False,
            "cobertura": {},
            "faltantes": ["No se pudo interpretar la evaluación del modelo"],
            "consultas": [],
            "nota": str(data),
        }
    data.setdefault("suficiente", False)
    data.setdefault("cobertura", {})
    data.setdefault("faltantes", [])
    data.setdefault("consultas", [])
    data.setdefault("nota", "")
    if not isinstance(data["consultas"], list):
        data["consultas"] = []
    return data


def refine_hits_by_concept(
    concepts: list[str],
    hits_by_concept: dict[str, list[SearchHit]],
    engine: Any,
    *,
    config: ApiConfig,
    threshold: float,
    max_rounds: int = 2,
    max_queries: int = 3,
    hits_per_query: int = 4,
    max_quote_chars: int = 700,
) -> tuple[dict[str, list[SearchHit]], dict[str, Any]]:
    client = create_client(config)
    diagnostics: dict[str, Any] = {}
    updated = {concept: list(hits_by_concept.get(concept, [])) for concept in concepts}

    for concept in concepts:
        current_hits = updated.get(concept, [])
        concept_diag: dict[str, Any] = {"rondas": []}

        for round_index in range(1, max_rounds + 1):
            evaluation = _evaluate_concept_iteration(client, config, concept, current_hits, round_index, max_queries)
            round_diag = {
                "ronda": round_index,
                "hits_iniciales": len(current_hits),
                "evaluacion": evaluation,
                "consultas_ejecutadas": [],
            }

            if evaluation.get("suficiente"):
                concept_diag["rondas"].append(round_diag)
                break

            queries = [str(q).strip() for q in evaluation.get("consultas", []) if str(q).strip()][:max_queries]
            if not queries:
                concept_diag["rondas"].append(round_diag)
                break

            new_hits_accum: list[SearchHit] = []
            for query in queries:
                hits = engine.search(query, top_k=hits_per_query, threshold=threshold, max_quote_chars=max_quote_chars)
                round_diag["consultas_ejecutadas"].append({"consulta": query, "hits": len(hits)})
                new_hits_accum.extend(hits)

            merged_hits = _merge_hits(current_hits, new_hits_accum)
            round_diag["hits_finales"] = len(merged_hits)
            concept_diag["rondas"].append(round_diag)

            if len(merged_hits) == len(current_hits):
                current_hits = merged_hits
                break
            current_hits = merged_hits

        final_eval = concept_diag["rondas"][-1]["evaluacion"] if concept_diag["rondas"] else {}
        concept_diag["suficiente_final"] = bool(final_eval.get("suficiente", False))
        concept_diag["hits_finales"] = len(current_hits)
        updated[concept] = current_hits
        diagnostics[concept] = concept_diag

    return updated, diagnostics
