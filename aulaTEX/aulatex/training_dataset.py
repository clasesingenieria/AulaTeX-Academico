"""Consolidador de dataset de entrenamiento para AulaTeX.

Lee los ``manifest.json`` producidos por :mod:`aulatex.activity_optimizer`
(``aulaTEX/retroalimentacion-editorial/aulatex/activity-optimize/runs/<run_id>/``) y
los aplana en un ``dataset.jsonl`` con UNA fila por CICLO de optimización.

Cada ciclo es la unidad de aprendizaje natural:
  * Estado (features)  : quality_before, contract_before, semantic_blocking_before,
                         improvement_kind, engine, activity_number, target.
  * Acción             : (engine, improvement_kind).
  * Recompensa         : quality_delta = quality_after - quality_before.
  * Etiqueta binaria   : accepted (¿la mejora se aplicó y verificó?).

Esto sirve como insumo compartido para:
  - análisis inmediato en CPU (tasa de aceptación por motor/tipo);
  - un bandit/regresión que calibre la política del orquestador;
  - un reward model / DPO entrenado en GPU (AWS/Azure).

NO ejecuta LLMs ni toca la nube: solo lee JSON ya persistido y escribe un
dataset + un reporte de análisis. Es idempotente y seguro de re-ejecutar.

Uso:
    python -m aulatex.training_dataset            # usa rutas por defecto
    python -m aulatex.training_dataset --runs-dir <dir> --output <dataset.jsonl>
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


# Campos por-ciclo que emite activity_optimizer._cycle_dict.
CYCLE_FIELDS = (
    "cycle",
    "engine",
    "accepted",
    "reason",
    "improvement_kind",
    "quality_before",
    "quality_after",
    "contract_before",
    "contract_after",
    "semantic_blocking_before",
    "semantic_blocking_after",
    "quality_breakdown_before",
    "quality_breakdown_after",
)
QUALITY_COMPONENTS = (
    "citas",
    "estructura",
    "base_conceptual",
    "listas",
    "conectores",
    "extension",
    "integridad",
)


@dataclass
class DatasetStats:
    """Resumen analítico del dataset consolidado."""

    manifests_read: int = 0
    manifests_skipped: int = 0
    total_cycles: int = 0
    accepted_cycles: int = 0
    quality_deltas: list[float] = field(default_factory=list)
    by_engine: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    by_kind: dict[str, list[int]] = field(default_factory=lambda: defaultdict(list))
    targets: set[str] = field(default_factory=set)
    skipped_reasons: Counter = field(default_factory=Counter)

    @property
    def acceptance_rate(self) -> float:
        if self.total_cycles == 0:
            return 0.0
        return round(self.accepted_cycles / self.total_cycles, 4)

    @property
    def mean_quality_delta(self) -> float:
        return round(statistics.fmean(self.quality_deltas), 4) if self.quality_deltas else 0.0


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _coerce_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def iter_manifests(runs_dir: Path) -> Iterable[Path]:
    """Devuelve los manifest.json de activity-optimize bajo ``runs_dir``.

    Recorre recursivamente para tolerar tanto la estructura
    ``runs/<run_id>/manifest.json`` como salidas personalizadas (--output).
    """
    if not runs_dir.exists():
        return []
    return sorted(runs_dir.rglob("manifest.json"))


def _load_manifest(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None
    if not isinstance(payload, dict):
        return None
    # Solo consumimos manifiestos de activity-optimize (tienen 'cycles').
    if payload.get("kind") != "activity-optimize":
        return None
    if not isinstance(payload.get("cycles"), list):
        return None
    return payload


def _cycle_to_row(manifest: dict[str, Any], cycle: dict[str, Any]) -> dict[str, Any]:
    """Aplana un ciclo + contexto del run en una fila del dataset."""
    quality_before = _coerce_float(cycle.get("quality_before"))
    quality_after = _coerce_float(cycle.get("quality_after"))
    breakdown_before = cycle.get("quality_breakdown_before")
    if not isinstance(breakdown_before, dict):
        breakdown_before = {}
    component_features = {
        f"quality_{component}_before": _coerce_float(breakdown_before.get(component))
        for component in QUALITY_COMPONENTS
    }
    return {
        # --- Identidad / trazabilidad ---
        "run_id": str(manifest.get("run_id", "")),
        "target": str(manifest.get("target", "")),
        "activity_number": _coerce_int(manifest.get("activity_number")),
        "cycle": _coerce_int(cycle.get("cycle")),
        # --- Acción ---
        "engine": str(cycle.get("engine", "")),
        "improvement_kind": str(cycle.get("improvement_kind", "")),
        # --- Estado (features de entrada) ---
        "quality_before": quality_before,
        "contract_before": _coerce_float(cycle.get("contract_before")),
        "semantic_blocking_before": _coerce_int(cycle.get("semantic_blocking_before")),
        **component_features,
        # --- Resultado (features de salida) ---
        "quality_after": quality_after,
        "contract_after": _coerce_float(cycle.get("contract_after")),
        "semantic_blocking_after": _coerce_int(cycle.get("semantic_blocking_after")),
        # --- Recompensa y etiqueta ---
        "quality_delta": round(quality_after - quality_before, 4),
        "accepted": bool(cycle.get("accepted", False)),
        "reason": str(cycle.get("reason", "")),
        # --- Contexto del run (útil para estratificar) ---
        "stop_mode": str(manifest.get("stop_mode", "")),
        "converged": bool(manifest.get("converged", False)),
        "run_ok": bool(manifest.get("ok", False)),
    }


def build_dataset(runs_dir: Path, output_path: Path) -> DatasetStats:
    """Consolida todos los manifiestos en un dataset.jsonl y devuelve estadísticas."""
    stats = DatasetStats()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    manifests = list(iter_manifests(runs_dir))
    with output_path.open("w", encoding="utf-8") as out:
        for manifest_path in manifests:
            manifest = _load_manifest(manifest_path)
            if manifest is None:
                stats.manifests_skipped += 1
                stats.skipped_reasons[manifest_path.parent.name or "sin-nombre"] += 1
                continue
            stats.manifests_read += 1
            target = str(manifest.get("target", ""))
            if target:
                stats.targets.add(target)
            for cycle in manifest["cycles"]:
                if not isinstance(cycle, dict):
                    continue
                row = _cycle_to_row(manifest, cycle)
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                stats.total_cycles += 1
                accepted_flag = 1 if row["accepted"] else 0
                stats.accepted_cycles += accepted_flag
                stats.quality_deltas.append(row["quality_delta"])
                stats.by_engine[row["engine"] or "(sin-motor)"].append(accepted_flag)
                stats.by_kind[row["improvement_kind"] or "(sin-tipo)"].append(accepted_flag)

    return stats


def _rate(flags: list[int]) -> float:
    return round(sum(flags) / len(flags), 4) if flags else 0.0


def render_report(stats: DatasetStats, runs_dir: Path, output_path: Path) -> str:
    """Genera un reporte Markdown con la tasa de aceptación por motor/tipo."""
    lines: list[str] = []
    lines.append("# Dataset de entrenamiento AulaTeX — reporte de consolidación")
    lines.append("")
    lines.append(f"- Origen (runs): `{runs_dir}`")
    lines.append(f"- Dataset generado: `{output_path}`")
    lines.append(f"- Manifiestos leídos: {stats.manifests_read} (omitidos: {stats.manifests_skipped})")
    lines.append(f"- Objetivos distintos: {len(stats.targets)}")
    lines.append(f"- Ciclos totales (filas): {stats.total_cycles}")
    lines.append(f"- Ciclos aceptados: {stats.accepted_cycles}")
    lines.append(f"- **Tasa de aceptación global: {stats.acceptance_rate:.1%}**")
    lines.append(f"- **Δ calidad promedio por ciclo: {stats.mean_quality_delta:+.2f}**")
    lines.append("")

    if stats.total_cycles == 0:
        lines.append("> No se encontraron ciclos. Ejecuta primero `activity-optimize` "
                     "para generar manifiestos, o apunta `--runs-dir` a la ubicación correcta.")
        return "\n".join(lines) + "\n"

    lines.append("## Tasa de aceptación por motor")
    lines.append("")
    lines.append("| Motor | Ciclos | Aceptados | Tasa |")
    lines.append("|---|---:|---:|---:|")
    for engine, flags in sorted(stats.by_engine.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"| {engine} | {len(flags)} | {sum(flags)} | {_rate(flags):.1%} |")
    lines.append("")

    lines.append("## Tasa de aceptación por tipo de mejora")
    lines.append("")
    lines.append("| improvement_kind | Ciclos | Aceptados | Tasa |")
    lines.append("|---|---:|---:|---:|")
    for kind, flags in sorted(stats.by_kind.items(), key=lambda kv: -len(kv[1])):
        lines.append(f"| {kind} | {len(flags)} | {sum(flags)} | {_rate(flags):.1%} |")
    lines.append("")

    lines.append("## Lectura")
    lines.append("")
    lines.append("- Motores/tipos con **tasa baja** son candidatos a filtrar antes de gastar "
                 "llamadas LLM (optimización sin ML).")
    lines.append("- El campo `quality_delta` es la **recompensa** para un bandit contextual o "
                 "reward model.")
    lines.append("- El campo `accepted` es la **etiqueta binaria** para un clasificador de "
                 "propuestas aplicables.")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="aulatex.training_dataset",
        description="Consolida manifiestos de activity-optimize en un dataset.jsonl entrenable.",
    )
    # Rutas por defecto relativas a la raíz del repo (aulaTEX/aulatex/ -> parents[2]).
    repo_root = Path(__file__).resolve().parents[2]
    default_runs = repo_root / "aulaTEX" / "retroalimentacion-editorial" / "aulatex" / "activity-optimize" / "runs"
    default_out = repo_root / "aulaTEX" / "retroalimentacion-editorial" / "aulatex" / "training" / "dataset.jsonl"

    parser.add_argument("--runs-dir", default=str(default_runs),
                        help="Directorio con los run_id/manifest.json de activity-optimize.")
    parser.add_argument("--output", default=str(default_out),
                        help="Ruta del dataset.jsonl de salida.")
    parser.add_argument("--report", default="",
                        help="Ruta del reporte Markdown (por defecto, junto al dataset).")
    args = parser.parse_args(argv)

    # La consola de Windows usa cp1252 y aborta con UnicodeEncodeError ante 'Δ' o acentos.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    runs_dir = Path(args.runs_dir).resolve()
    output_path = Path(args.output).resolve()
    report_path = Path(args.report).resolve() if args.report else output_path.with_name("dataset-report.md")

    stats = build_dataset(runs_dir, output_path)
    report = render_report(stats, runs_dir, output_path)
    report_path.write_text(report, encoding="utf-8")

    print(f"[dataset] manifiestos leídos : {stats.manifests_read} (omitidos {stats.manifests_skipped})")
    print(f"[dataset] ciclos (filas)     : {stats.total_cycles}")
    print(f"[dataset] tasa de aceptación : {stats.acceptance_rate:.1%}")
    print(f"[dataset] Δ calidad promedio : {stats.mean_quality_delta:+.2f}")
    print(f"[dataset] salida             : {output_path}")
    print(f"[dataset] reporte            : {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
