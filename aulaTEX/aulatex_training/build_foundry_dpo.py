"""Convierte el corpus de preferencias al formato de fine-tuning de Azure OpenAI.

Via B del plan de entrenamiento: mientras se resuelven las solicitudes de cuota
para H100/A100 (necesarias para entrenar un reward model propio), Foundry SI
tiene capacidad de fine-tuning disponible sin tramite. Esta ruta afina un modelo
GENERADOR con las preferencias observadas, en vez de entrenar un juez.

Formato de destino (preference fine-tuning / DPO de Azure OpenAI):

    {"input": {"messages": [{"role": "system", ...},
                            {"role": "user", ...}]},
     "preferred_output":     [{"role": "assistant", "content": "<mejor>"}],
     "non_preferred_output": [{"role": "assistant", "content": "<peor>"}]}

Entrada: ``preference.jsonl`` de ``build_corpus_from_repo.py``, con campos
``prompt`` / ``chosen`` / ``rejected`` / ``quality_gain``.

Decisiones de diseno
--------------------
* Se filtra por ``--min-gain``: un par con ganancia marginal ensena ruido.
  El default (5.0) es mas estricto que el del extractor porque aqui cada
  ejemplo pesa mas: son pocos y guian directamente la generacion.
* Se descartan pares que exceden ``--max-tokens``: el job los rechazaria.
* Split train/val por documento (``target``), no por fila, para que la
  validacion mida generalizacion real y no memorizacion de plantilla.
* El system prompt refleja el contrato editorial de AulaTeX, para que el
  modelo afinado se comporte igual dentro de ``realizar-actividad``.

Uso:
    python aulaTEX/aulatex_training/build_foundry_dpo.py
    python aulaTEX/aulatex_training/build_foundry_dpo.py --min-gain 10 --max-tokens 16384
"""

from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

SEED = 20260809
MIN_TRAIN_EXAMPLES = 10  # minimo que exige Azure OpenAI para aceptar el job.

SYSTEM_PROMPT = (
    "Eres un asistente editorial academico de AulaTeX. Produces LaTeX para actividades "
    "universitarias en espanol. Respetas la tecnica didactica solicitada, estructuras el "
    "cuerpo en tres actos (introduccion, un unico desarrollo con titulo tematico y "
    "conclusiones), citas toda afirmacion con \\cite y evitas metadiscurso de ejecucion: "
    "hablas del tema, no de la actividad."
)


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(payload, dict) and payload.get("chosen") and payload.get("rejected"):
            rows.append(payload)
    return rows


def token_counter():
    """Contador de tokens real si hay tiktoken; si no, estimacion por caracteres."""
    try:
        import tiktoken

        encoding = tiktoken.get_encoding("o200k_base")
        return lambda text: len(encoding.encode(text))
    except Exception:  # noqa: BLE001 - la estimacion basta para filtrar
        return lambda text: len(text) // 4


def to_foundry(row: dict[str, Any]) -> dict[str, Any]:
    user_prompt = (
        f"{row['prompt']}\n\n"
        "Fragmento actual:\n"
        "```latex\n"
        f"{row['rejected']}\n"
        "```"
    )
    return {
        "input": {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
        },
        "preferred_output": [{"role": "assistant", "content": row["chosen"]}],
        "non_preferred_output": [{"role": "assistant", "content": row["rejected"]}],
    }


def split_by_document(rows: list[dict[str, Any]], val_ratio: float
                      ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    targets = sorted({str(row.get("target", "")) for row in rows})
    rng = random.Random(SEED)
    rng.shuffle(targets)
    cut = max(1, int(len(targets) * val_ratio))
    val_targets = set(targets[:cut])
    train = [r for r in rows if str(r.get("target", "")) not in val_targets]
    validation = [r for r in rows if str(r.get("target", "")) in val_targets]
    return train, validation


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    training_dir = REPO_ROOT / "aulaTEX" / "retroalimentacion-editorial" / "aulatex" / "training"
    parser = argparse.ArgumentParser(
        prog="build_foundry_dpo",
        description="Convierte preference.jsonl al formato de preference fine-tuning de Azure OpenAI.")
    parser.add_argument("--input", default=str(training_dir / "preference.jsonl"))
    parser.add_argument("--out-dir", default=str(training_dir / "foundry"))
    parser.add_argument("--min-gain", type=float, default=5.0,
                        help="Ganancia minima de calidad para conservar el par.")
    parser.add_argument("--max-tokens", type=int, default=32768,
                        help="Presupuesto de tokens por ejemplo (prompt + ambas salidas).")
    parser.add_argument("--val-ratio", type=float, default=0.2)
    args = parser.parse_args(argv)

    source = Path(args.input).resolve()
    if not source.exists():
        print(f"[foundry] No existe: {source}")
        print("          Genera primero: python aulaTEX/aulatex_training/build_corpus_from_repo.py")
        return 1

    rows = load_rows(source)
    count_tokens = token_counter()

    kept: list[dict[str, Any]] = []
    dropped_gain = dropped_size = 0
    for row in rows:
        if float(row.get("quality_gain", 0.0)) < args.min_gain:
            dropped_gain += 1
            continue
        total = (count_tokens(str(row["prompt"])) + count_tokens(str(row["chosen"]))
                 + count_tokens(str(row["rejected"])))
        if total > args.max_tokens:
            dropped_size += 1
            continue
        kept.append(row)

    print(f"[foundry] pares leidos          : {len(rows)}")
    print(f"[foundry] descartados por gain  : {dropped_gain} (< {args.min_gain})")
    print(f"[foundry] descartados por tokens: {dropped_size} (> {args.max_tokens})")
    print(f"[foundry] conservados           : {len(kept)}")

    if len(kept) < MIN_TRAIN_EXAMPLES:
        print(f"\n[foundry] ABORTA: Azure OpenAI exige >= {MIN_TRAIN_EXAMPLES} ejemplos.")
        print("          Baja --min-gain o amplia el corpus con mas corridas.")
        return 1

    train_rows, val_rows = split_by_document(kept, args.val_ratio)
    if not val_rows:  # corpus pequeno: reservar al menos un ejemplo
        val_rows, train_rows = train_rows[:1], train_rows[1:]

    out_dir = Path(args.out_dir).resolve()
    train_path = out_dir / "dpo-train.jsonl"
    val_path = out_dir / "dpo-validation.jsonl"
    write_jsonl(train_path, [to_foundry(r) for r in train_rows])
    write_jsonl(val_path, [to_foundry(r) for r in val_rows])

    gains = [float(r["quality_gain"]) for r in kept]
    print()
    print(f"[foundry] train : {len(train_rows):3d} -> {train_path}")
    print(f"[foundry] valid : {len(val_rows):3d} -> {val_path}")
    print(f"[foundry] ganancia min/media/max : {min(gains):.1f} / "
          f"{statistics.mean(gains):.1f} / {max(gains):.1f}")

    if len(train_rows) < MIN_TRAIN_EXAMPLES:
        print(f"\n[foundry] AVISO: el split dejo train con {len(train_rows)} ejemplos"
              f" (< {MIN_TRAIN_EXAMPLES}). Reduce --val-ratio.")
        return 1

    print("\n[foundry] Listo. Siguiente paso: subir los archivos y crear el job")
    print("          con el deployment de fine-tuning (o4-mini o gpt4.1-mini).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
