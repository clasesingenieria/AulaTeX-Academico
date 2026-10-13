from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.bot import _build_note_action_messages, _parse_derivative_markdown, _parse_note_markdown
from src.azure_openai_client import invoke_chat
from src.config import load_settings, llm_max_output_tokens


REQUIRED_SECTIONS = [
    "Nucleo",
    "Desarrollo",
    "Accionables",
    "Evidencias y supuestos",
    "Sintesis breve",
]

DEFAULT_PROVIDERS = [
    "azure-openai",
    "codex",
    "gpt-pro",
    "model-router",
    "claude-foundry",
]

DEFAULT_PROVIDER_MAX_TOKENS = {
    "codex": 128_000,
    "gpt-pro": 128_000,
    "model-router": 128_000,
    "claude-foundry": 128_000,
}


def _is_base_note(path: Path) -> bool:
    if path.name == "index.md":
        return False
    suffixes = (".explain.md", ".suggest.md", ".research.md", ".dialectic.md")
    return not any(path.name.endswith(suffix) for suffix in suffixes)


def _select_note_paths(notes_dir: Path, limit: int) -> list[Path]:
    candidates = sorted(path for path in notes_dir.rglob("*.md") if _is_base_note(path))
    if len(candidates) < limit:
        raise RuntimeError(f"Solo encontre {len(candidates)} notas base en {notes_dir}, pero pedi {limit}.")
    return candidates[-limit:]


def _summarize_text(text: str, limit: int = 240) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _parse_provider_max_tokens(items: list[str] | None) -> dict[str, int]:
    provider_limits = dict(DEFAULT_PROVIDER_MAX_TOKENS)
    for item in items or []:
        raw_item = str(item).strip()
        if not raw_item:
            continue
        provider, separator, value = raw_item.partition("=")
        if not separator:
            raise RuntimeError(
                f"Formato invalido en --provider-max-tokens: '{raw_item}'. Usa proveedor=max_tokens."
            )
        normalized_provider = provider.strip()
        if not normalized_provider:
            raise RuntimeError(f"Proveedor vacio en --provider-max-tokens: '{raw_item}'.")
        provider_limits[normalized_provider] = max(1, int(value.strip()))
    return provider_limits


def _evaluate_provider_note(provider: str, note_path: Path, action: str, max_tokens: int) -> dict[str, Any]:
    os.environ["LLM_PROVIDER"] = provider
    settings = load_settings()
    markdown = note_path.read_text(encoding="utf-8")
    note_context = _parse_note_markdown(markdown)
    messages = _build_note_action_messages(action, note_context)
    effective_max_tokens = llm_max_output_tokens(settings, max_tokens)

    started_at = time.perf_counter()
    started_iso = datetime.now().isoformat(timespec="seconds")
    raw_output = ""
    parsed_sections: dict[str, str] = {}
    error = ""
    success = False

    try:
        raw_output = invoke_chat(
            settings,
            messages,
            max_tokens=effective_max_tokens,
            temperature=0.4,
            response_format_json=False,
        )
        parsed = _parse_derivative_markdown(raw_output)
        parsed_sections = {
            key: str(value).strip()
            for key, value in dict(parsed.get("sections", {})).items()
            if str(value).strip()
        }
        success = True
    except Exception as exc:
        error = str(exc)

    elapsed = round(time.perf_counter() - started_at, 3)
    present_sections = [section for section in REQUIRED_SECTIONS if parsed_sections.get(section)]
    missing_sections = [section for section in REQUIRED_SECTIONS if section not in present_sections]
    output_words = len(raw_output.split()) if raw_output else 0

    return {
        "provider": provider,
        "action": action,
        "note_path": str(note_path),
        "note_title": str(note_context.get("title", note_path.stem)),
        "source_note": note_context,
        "started_at": started_iso,
        "latency_seconds": elapsed,
        "success": success,
        "error": error,
        "max_tokens": effective_max_tokens,
        "output_chars": len(raw_output),
        "output_words": output_words,
        "sections_present": present_sections,
        "sections_missing": missing_sections,
        "all_sections_present": not missing_sections,
        "raw_output": raw_output,
        "parsed_sections": parsed_sections,
        "preview": _summarize_text(raw_output),
    }


def _aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_provider: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        by_provider.setdefault(str(result["provider"]), []).append(result)

    summary: dict[str, Any] = {}
    for provider, provider_results in by_provider.items():
        latencies = [float(item["latency_seconds"]) for item in provider_results]
        successes = [bool(item["success"]) for item in provider_results]
        structure_successes = [bool(item["all_sections_present"]) for item in provider_results]
        word_counts = [int(item["output_words"]) for item in provider_results if int(item["output_words"]) > 0]
        summary[provider] = {
            "runs": len(provider_results),
            "successes": sum(1 for item in successes if item),
            "structure_successes": sum(1 for item in structure_successes if item),
            "avg_latency_seconds": round(statistics.mean(latencies), 3) if latencies else 0.0,
            "max_latency_seconds": round(max(latencies), 3) if latencies else 0.0,
            "avg_output_words": round(statistics.mean(word_counts), 1) if word_counts else 0.0,
        }
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Evalua proveedores LLM sobre notas existentes del proyecto.")
    parser.add_argument("--notes-dir", default=str(ROOT / "data" / "notes"), help="Directorio raiz de notas.")
    parser.add_argument("--notes", nargs="*", default=None, help="Rutas explicitas de notas base para evaluar.")
    parser.add_argument("--providers", nargs="*", default=DEFAULT_PROVIDERS, help="Lista de proveedores LLM.")
    parser.add_argument("--action", default="explain", choices=["explain", "suggest", "research", "dialectic"], help="Accion derivada a usar como benchmark.")
    parser.add_argument("--limit", type=int, default=5, help="Numero de notas base a evaluar si no se pasan rutas explicitas.")
    parser.add_argument("--max-tokens", type=int, default=3000, help="Tope uniforme de salida para el benchmark.")
    parser.add_argument(
        "--provider-max-tokens",
        nargs="*",
        default=None,
        help="Overrides por proveedor en formato proveedor=max_tokens. Si no se pasa, usa defaults del script cuando existan o --max-tokens como fallback.",
    )
    parser.add_argument(
        "--include-raw-output",
        action="store_true",
        help="Conserva `raw_output`, `parsed_sections` y `source_note` en el JSON final. Si no se activa, el reporte se compacta.",
    )
    parser.add_argument("--output", default="", help="Ruta opcional del reporte JSON.")
    args = parser.parse_args()

    notes_dir = Path(args.notes_dir).resolve()
    note_paths = [Path(item).resolve() for item in args.notes] if args.notes else _select_note_paths(notes_dir, args.limit)
    providers = [str(provider).strip() for provider in args.providers if str(provider).strip()]
    provider_max_tokens = _parse_provider_max_tokens(args.provider_max_tokens)
    if not providers:
        raise RuntimeError("No se especificaron proveedores.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = Path(args.output).resolve() if args.output else ROOT / "logs" / "monitoring" / f"llm_benchmark_{timestamp}.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)

    original_provider = os.getenv("LLM_PROVIDER")
    results: list[dict[str, Any]] = []
    try:
        print(f"Evaluando {len(providers)} proveedores sobre {len(note_paths)} notas con accion '{args.action}'...")
        for provider in providers:
            requested_max_tokens = provider_max_tokens.get(provider, args.max_tokens)
            print(f"\n== {provider} ==")
            for note_path in note_paths:
                print(f"- {note_path.name}", flush=True)
                result = _evaluate_provider_note(provider, note_path, args.action, requested_max_tokens)
                results.append(result)
                status = "ok" if result["success"] else "error"
                structure = "completa" if result["all_sections_present"] else "incompleta"
                print(
                    f"  {status} | {result['latency_seconds']}s | {structure} | {result['output_words']} palabras | max_tokens={result['max_tokens']}",
                    flush=True,
                )
                if result["error"]:
                    print(f"  error: {result['error']}", flush=True)
    finally:
        if original_provider is None:
            os.environ.pop("LLM_PROVIDER", None)
        else:
            os.environ["LLM_PROVIDER"] = original_provider

    if not args.include_raw_output:
        compact_results: list[dict[str, Any]] = []
        for result in results:
            compact = dict(result)
            compact.pop("raw_output", None)
            compact.pop("parsed_sections", None)
            compact.pop("source_note", None)
            compact_results.append(compact)
        serialized_results = compact_results
    else:
        serialized_results = results

    payload = {
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "notes": [str(path) for path in note_paths],
        "providers": providers,
        "action": args.action,
        "default_max_tokens": args.max_tokens,
        "provider_max_tokens": {provider: provider_max_tokens.get(provider, args.max_tokens) for provider in providers},
        "summary": _aggregate(results),
        "results": serialized_results,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\nReporte guardado en: {report_path}")
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())