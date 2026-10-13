from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .api_client import ApiConfig, create_client
from .document_reader import read_any_text_file
from .pdf_reader import extract_pdf_blocks
from .planeacion_parser import PlaneacionAnalizada, planeacion_to_dict
from .preprocessing import normalize_spaces, unique_preserve_order


def planeacion_confidence(analysis: PlaneacionAnalizada) -> float:
    score = 0.0
    total = 6.0
    if analysis.tema:
        score += 1.0
    if analysis.objetivo:
        score += 1.0
    if analysis.tecnica_didactica:
        score += 1.0
    if analysis.actividad:
        score += 1.0
    if analysis.bibliografia:
        score += 1.0
    if analysis.criterios_entrega:
        score += 1.0
    return score / total


def _strip_json_fence(text: str) -> str:
    fence = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.S | re.I)
    if fence:
        return fence.group(1).strip()
    return text.strip()


def _extract_content_text(response: Any) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def build_planeacion_payload(path: str | Path) -> str:
    p = Path(path)
    if p.suffix.lower() == ".pdf":
        blocks = extract_pdf_blocks(p)
        lines: list[str] = []
        for block in blocks:
            lines.append(f"[{block.location_label}] {normalize_spaces(block.text)}")
        return "\n".join(lines)
    return read_any_text_file(p)


def extract_planeacion_with_anthropic(path: str | Path, config: ApiConfig) -> dict:
    if config.provider != "anthropicfoundry":
        raise RuntimeError("La extracción asistida de planeación está implementada para Anthropic Foundry.")
    client = create_client(config)
    payload = build_planeacion_payload(path)
    system = (
        "Eres un analista de planeaciones académicas. "
        "Debes extraer la estructura relevante sin inventar contenido. "
        "Devuelve únicamente JSON válido."
    )
    user = (
        "Analiza la siguiente planeación académica y devuelve un JSON con estas claves: "
        "tema, objetivo, tecnica_didactica, actividad, bibliografia, criterios_entrega, "
        "aprendizajes, conceptos_clave, page_evidence, warnings. "
        "Si un dato no aparece claramente, devuelve cadena vacía o lista vacía, pero no inventes.\n\n"
        f"PLANEACION:\n{payload}"
    )
    response = client.messages.create(
        model=config.chat_model,
        system=system,
        messages=[{"role": "user", "content": user}],
        max_tokens=4096,
    )
    content = _strip_json_fence(_extract_content_text(response))
    try:
        data = json.loads(content)
    except json.JSONDecodeError:
        data = {
            "tema": "",
            "objetivo": "",
            "tecnica_didactica": "",
            "actividad": "",
            "bibliografia": [],
            "criterios_entrega": [],
            "aprendizajes": [],
            "conceptos_clave": [],
            "page_evidence": {},
            "warnings": ["La respuesta del modelo no pudo parsearse como JSON válido."],
            "raw_response": content,
        }
    return data


def merge_planeacion_analysis(local: PlaneacionAnalizada, remote: dict | None) -> dict:
    local_dict = planeacion_to_dict(local)
    if not remote:
        return local_dict

    merged = dict(local_dict)
    scalar_keys = ["tema", "objetivo", "tecnica_didactica", "actividad", "general_context"]
    list_keys = ["bibliografia", "criterios_entrega", "aprendizajes", "conceptos_explicitos"]

    for key in scalar_keys:
        local_val = str(local_dict.get(key, "") or "").strip()
        remote_key = key if key in remote else ("conceptos_clave" if key == "conceptos_explicitos" else key)
        remote_val = str(remote.get(remote_key, "") or "").strip()
        if (not local_val or len(local_val) < 20) and remote_val:
            merged[key] = remote_val

    merged["bibliografia"] = unique_preserve_order(list(local_dict.get("bibliografia", [])) + list(remote.get("bibliografia", [])))
    merged["criterios_entrega"] = unique_preserve_order(list(local_dict.get("criterios_entrega", [])) + list(remote.get("criterios_entrega", [])))
    merged["aprendizajes"] = unique_preserve_order(list(local_dict.get("aprendizajes", [])) + list(remote.get("aprendizajes", [])))
    merged["conceptos_explicitos"] = unique_preserve_order(list(local_dict.get("conceptos_explicitos", [])) + list(remote.get("conceptos_clave", [])))
    merged["anthropic_page_evidence"] = remote.get("page_evidence", {})
    merged["anthropic_warnings"] = remote.get("warnings", [])
    return merged


def concepts_from_remote_planeacion(remote: dict | None) -> list[str]:
    if not remote:
        return []
    concepts = remote.get("conceptos_clave", []) or []
    if not isinstance(concepts, list):
        return []
    return unique_preserve_order([str(c).strip() for c in concepts if str(c).strip()])
