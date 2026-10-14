"""Construye los corpus de TEXTO para entrenar el reward model y hacer DPO.

Cierra el hueco que dejaba ``aulatex/training_dataset.py``: ese consolidador
produce METRICAS por ciclo (estado, accion, recompensa, etiqueta), pero no el
TEXTO, y un reward model necesita aprender de texto.

Este script recorre las corridas de ``activity-optimize`` y produce dos corpus:

1. ``reward.jsonl``  — regresion de calidad sobre texto:
       {"text": "<bloque LaTeX>", "score": 74.0, ...}
   Se toma de cada ciclo el bloque propuesto por el LLM y se le asigna el score
   de calidad correspondiente (``quality_after`` si la mejora fue aceptada,
   ``quality_before`` si fue rechazada). Asi el juez aprende a distinguir texto
   que ELEVA la calidad de texto que no.

2. ``preference.jsonl`` — pares de preferencia para DPO:
       {"prompt": "...", "chosen": "<mejorado>", "rejected": "<original>"}
   Solo de ciclos ACEPTADOS: ahi consta que el bloque mejorado fue verificado
   (compilo, contrato >= 100, calidad subio). Es una preferencia observada, no
   supuesta.

Fuente de datos por ciclo (escrita por activity_optimizer):
    <run>/cycle-NN/proposal.json   -> original_block, improved_block, kind
    <run>/manifest.json            -> cycles[] con accepted y quality_*

Honestidad sobre los limites:
  * Si no hay corridas, el script lo dice y no inventa datos.
  * Reporta la varianza de scores: sin contraste, el reward model no aprende
    nada util y ``train_reward_model.py`` abortara (por diseno).
  * Los ciclos sin ``proposal.json`` (el LLM no devolvio propuesta) se omiten.

Uso:
    python aulaTEX/aulatex_training/build_reward_corpus.py
    python aulaTEX/aulatex_training/build_reward_corpus.py --runs-dir <dir> --out-dir <dir>
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path
from typing import Any, Iterator

# Longitud minima de un bloque para ser util como ejemplo de entrenamiento.
MIN_BLOCK_CHARS = 80


def load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def iter_runs(runs_dir: Path) -> Iterator[tuple[Path, dict[str, Any]]]:
    """Devuelve (run_dir, manifest) de cada corrida de activity-optimize."""
    if not runs_dir.exists():
        return
    for manifest_path in sorted(runs_dir.rglob("manifest.json")):
        manifest = load_json(manifest_path)
        if manifest is None or manifest.get("kind") != "activity-optimize":
            continue
        if not isinstance(manifest.get("cycles"), list):
            continue
        yield manifest_path.parent, manifest


def build(runs_dir: Path, out_dir: Path) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    reward_path = out_dir / "reward.jsonl"
    preference_path = out_dir / "preference.jsonl"

    reward_rows: list[dict[str, Any]] = []
    preference_rows: list[dict[str, Any]] = []
    runs = 0
    cycles_total = 0
    cycles_without_proposal = 0

    for run_dir, manifest in iter_runs(runs_dir):
        runs += 1
        target = str(manifest.get("target", ""))
        activity = int(manifest.get("activity_number") or 0)

        for cycle in manifest["cycles"]:
            if not isinstance(cycle, dict):
                continue
            cycles_total += 1
            index = int(cycle.get("cycle") or 0)
            proposal = load_json(run_dir / f"cycle-{index:02d}" / "proposal.json")
            if proposal is None:
                cycles_without_proposal += 1
                continue

            original = str(proposal.get("original_block", "")).strip()
            improved = str(proposal.get("improved_block", "")).strip()
            if len(improved) < MIN_BLOCK_CHARS:
                continue

            accepted = bool(cycle.get("accepted"))
            quality_before = float(cycle.get("quality_before") or 0.0)
            quality_after = float(cycle.get("quality_after") or 0.0)
            # El score del bloque mejorado: si se acepto, la calidad resultante;
            # si se rechazo, no elevo la calidad -> conserva la previa.
            score = quality_after if accepted else quality_before

            reward_rows.append({
                "text": improved,
                "score": round(score, 2),
                "accepted": accepted,
                "improvement_kind": str(cycle.get("improvement_kind", "")),
                "engine": str(cycle.get("engine", "")),
                "target": target,
                "activity_number": activity,
                "run_id": str(manifest.get("run_id", "")),
                "cycle": index,
            })

            # El bloque ORIGINAL tambien es un ejemplo valido, con su score previo.
            if len(original) >= MIN_BLOCK_CHARS:
                reward_rows.append({
                    "text": original,
                    "score": round(quality_before, 2),
                    "accepted": False,
                    "improvement_kind": "original",
                    "engine": "",
                    "target": target,
                    "activity_number": activity,
                    "run_id": str(manifest.get("run_id", "")),
                    "cycle": index,
                })

            # Par de preferencia: solo si la mejora fue VERIFICADA.
            if accepted and len(original) >= MIN_BLOCK_CHARS:
                preference_rows.append({
                    "prompt": (
                        "Mejora el siguiente fragmento LaTeX academico elevando rigor, "
                        "fuentes citadas y densidad argumentativa, conservando la tecnica didactica."
                    ),
                    "chosen": improved,
                    "rejected": original,
                    "quality_gain": round(quality_after - quality_before, 2),
                    "target": target,
                    "run_id": str(manifest.get("run_id", "")),
                    "cycle": index,
                })

    with reward_path.open("w", encoding="utf-8") as handle:
        for row in reward_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    with preference_path.open("w", encoding="utf-8") as handle:
        for row in preference_rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")

    # ------------------------------------------------------------------ reporte
    print(f"[corpus] corridas leidas        : {runs}")
    print(f"[corpus] ciclos totales         : {cycles_total}")
    print(f"[corpus] ciclos sin propuesta   : {cycles_without_proposal}")
    print(f"[corpus] ejemplos reward        : {len(reward_rows)}  -> {reward_path}")
    print(f"[corpus] pares de preferencia   : {len(preference_rows)}  -> {preference_path}")

    if not reward_rows:
        print("\n[corpus] AVISO: no se genero ningun ejemplo.")
        if runs == 0:
            print("         No hay corridas de activity-optimize. Ejecuta primero:")
            print("           aulatex activity-optimize --target <ruta> --activity <n>")
        else:
            print("         Las corridas existen pero sin proposal.json utilizables.")
        return 1

    scores = [row["score"] for row in reward_rows]
    stdev = statistics.pstdev(scores) if len(scores) > 1 else 0.0
    print(f"\n[corpus] score min/media/max    : {min(scores):.1f} / "
          f"{statistics.fmean(scores):.1f} / {max(scores):.1f}")
    print(f"[corpus] desviacion estandar    : {stdev:.2f}")
    if stdev < 2.0:
        print("[corpus] ADVERTENCIA: varianza baja. Sin contraste de calidad el reward")
        print("         model no aprendera nada util (train_reward_model.py abortara).")
    if len(reward_rows) < 50:
        print(f"[corpus] ADVERTENCIA: solo {len(reward_rows)} ejemplos; se requieren >= 50.")
        print("         Acumula mas corridas de activity-optimize.")
    return 0


def main(argv: list[str] | None = None) -> int:
    repo_root = Path(__file__).resolve().parents[2]
    default_runs = repo_root / "aulaTEX" / "retroalimentacion-editorial" / "aulatex" / "activity-optimize" / "runs"
    default_out = repo_root / "aulaTEX" / "retroalimentacion-editorial" / "aulatex" / "training"

    parser = argparse.ArgumentParser(
        prog="build_reward_corpus",
        description="Genera reward.jsonl y preference.jsonl desde las corridas de activity-optimize.",
    )
    parser.add_argument("--runs-dir", default=str(default_runs))
    parser.add_argument("--out-dir", default=str(default_out))
    args = parser.parse_args(argv)

    return build(Path(args.runs_dir).resolve(), Path(args.out_dir).resolve())


if __name__ == "__main__":
    sys.exit(main())
