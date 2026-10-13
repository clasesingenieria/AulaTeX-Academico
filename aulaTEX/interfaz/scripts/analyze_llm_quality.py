from __future__ import annotations

import argparse
import json
import statistics
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.casefold())
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _extract_concept_labels(source_note: dict[str, Any]) -> list[str]:
    concepts = source_note.get("concepts") or []
    labels: list[str] = []
    for item in concepts:
        if isinstance(item, dict):
            label = str(item.get("term") or item.get("concept") or item.get("name") or "").strip()
            if label:
                labels.append(label)
        elif isinstance(item, str) and item.strip():
            labels.append(item.strip())
    return labels


def _extract_related_terms(source_note: dict[str, Any]) -> list[str]:
    related = source_note.get("related_terms") or []
    return [str(item).strip() for item in related if str(item).strip()]


def _coverage_ratio(terms: list[str], text: str) -> float:
    if not terms:
        return 1.0
    normalized_text = _normalize(text)
    hits = 0
    for term in terms:
        if _normalize(term) in normalized_text:
            hits += 1
    return hits / len(terms)


def _section_balance_score(parsed_sections: dict[str, str]) -> float:
    if not parsed_sections:
        return 0.0
    expected_mins = {
        "Nucleo": 60,
        "Desarrollo": 180,
        "Accionables": 80,
        "Evidencias y supuestos": 70,
        "Sintesis breve": 40,
    }
    scores: list[float] = []
    for section, min_words in expected_mins.items():
        words = len(str(parsed_sections.get(section, "")).split())
        scores.append(min(1.0, words / min_words) if words else 0.0)
    return statistics.mean(scores) if scores else 0.0


def _actionables_score(parsed_sections: dict[str, str]) -> float:
    actionables = str(parsed_sections.get("Accionables", ""))
    if not actionables.strip():
        return 0.0
    lines = [line.strip() for line in actionables.splitlines() if line.strip()]
    bullet_like = sum(1 for line in lines if line.startswith(("-", "*")) or line[:2].isdigit())
    if bullet_like >= 3:
        return 1.0
    if bullet_like == 2:
        return 0.8
    if bullet_like == 1:
        return 0.6
    return min(1.0, len(actionables.split()) / 120)


def _conciseness_score(output_words: int) -> float:
    if output_words <= 0:
        return 0.0
    if 550 <= output_words <= 950:
        return 1.0
    if 450 <= output_words < 550 or 950 < output_words <= 1200:
        return 0.85
    if 300 <= output_words < 450 or 1200 < output_words <= 1600:
        return 0.65
    return 0.4


def _quality_score(result: dict[str, Any]) -> dict[str, float]:
    source_note = dict(result.get("source_note") or {})
    raw_output = str(result.get("raw_output") or "")
    parsed_sections = dict(result.get("parsed_sections") or {})
    concept_terms = _extract_concept_labels(source_note)
    related_terms = _extract_related_terms(source_note)
    concept_coverage = _coverage_ratio(concept_terms, raw_output)
    related_coverage = _coverage_ratio(related_terms, raw_output)
    section_balance = _section_balance_score(parsed_sections)
    actionables = _actionables_score(parsed_sections)
    conciseness = _conciseness_score(int(result.get("output_words") or 0))
    total = (
        concept_coverage * 30
        + related_coverage * 10
        + section_balance * 25
        + actionables * 15
        + conciseness * 20
    )
    return {
        "concept_coverage": round(concept_coverage, 3),
        "related_coverage": round(related_coverage, 3),
        "section_balance": round(section_balance, 3),
        "actionables": round(actionables, 3),
        "conciseness": round(conciseness, 3),
        "quality_score": round(total, 2),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Analiza calidad heuristica de salidas LLM capturadas por el benchmark.")
    parser.add_argument("report", help="Ruta al JSON del benchmark con --include-raw-output.")
    parser.add_argument("--output", default="", help="Ruta opcional para guardar el analisis JSON.")
    args = parser.parse_args()

    report_path = Path(args.report).resolve()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    results = list(payload.get("results") or [])
    if not results:
        raise RuntimeError("El reporte no contiene resultados.")
    if "raw_output" not in results[0]:
        raise RuntimeError("El reporte no incluye salidas completas. Vuelve a generarlo con --include-raw-output.")

    enriched_results: list[dict[str, Any]] = []
    by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        metrics = _quality_score(result)
        enriched = dict(result)
        enriched["quality_metrics"] = metrics
        enriched_results.append(enriched)
        by_provider[str(result.get("provider"))].append(enriched)

    summary: dict[str, Any] = {}
    for provider, provider_results in by_provider.items():
        summary[provider] = {
            "runs": len(provider_results),
            "avg_quality_score": round(statistics.mean(item["quality_metrics"]["quality_score"] for item in provider_results), 2),
            "avg_concept_coverage": round(statistics.mean(item["quality_metrics"]["concept_coverage"] for item in provider_results), 3),
            "avg_related_coverage": round(statistics.mean(item["quality_metrics"]["related_coverage"] for item in provider_results), 3),
            "avg_section_balance": round(statistics.mean(item["quality_metrics"]["section_balance"] for item in provider_results), 3),
            "avg_actionables": round(statistics.mean(item["quality_metrics"]["actionables"] for item in provider_results), 3),
            "avg_conciseness": round(statistics.mean(item["quality_metrics"]["conciseness"] for item in provider_results), 3),
        }

    ranked = sorted(summary.items(), key=lambda item: item[1]["avg_quality_score"], reverse=True)
    analysis = {
        "source_report": str(report_path),
        "summary": summary,
        "ranking": [provider for provider, _ in ranked],
        "results": enriched_results,
    }

    if args.output:
        output_path = Path(args.output).resolve()
    else:
        output_path = report_path.with_name(report_path.stem + "_quality.json")
    output_path.write_text(json.dumps(analysis, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps({"ranking": analysis["ranking"], "summary": summary}, ensure_ascii=False, indent=2))
    print(f"Analisis guardado en: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())