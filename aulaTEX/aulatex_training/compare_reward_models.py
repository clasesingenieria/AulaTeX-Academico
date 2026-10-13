"""Compara candidatos a reward model en CPU ANTES de gastar GPU.

Motivacion: el corpus tiene mediana 546 tokens y maximo ~14 000. Un encoder de
512 posiciones trunca el 58% de los documentos, justo donde viven conclusion y
bibliografia. La duda es si conviene mas un modelo multilingue con ventana corta
o uno de ventana larga menos afin al espanol. Se resuelve midiendo, no opinando.

Protocolo (identico para todos los candidatos, para que la comparacion sea justa)
--------------------------------------------------------------------------------
* Misma particion train/eval, con la misma semilla.
* Split por ``target`` (documento), no por fila: dos versiones del mismo TEX
  nunca caen una en train y otra en eval. Sin esto, la metrica sale inflada.
* Metrica principal: Spearman en validacion, la misma que usa
  ``train_reward_model.py`` para dar veredicto.
* Se reporta ademas el % del corpus que cada ventana cubre sin truncar.

Uso:
    python aulaTEX/aulatex_training/compare_reward_models.py
    python aulaTEX/aulatex_training/compare_reward_models.py --epochs 3
"""

from __future__ import annotations

import argparse
import json
import os
import random
import statistics
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]

SEED = 20260808

# (nombre, ventana). La ventana se recorta al limite real del modelo.
CANDIDATES: list[tuple[str, int]] = [
    ("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2", 512),
    ("FacebookAI/xlm-roberta-base", 512),
    ("answerdotai/ModernBERT-base", 4096),
]


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
        if isinstance(payload, dict) and payload.get("text"):
            rows.append(payload)
    return rows


def split_by_document(rows: list[dict[str, Any]], eval_ratio: float
                      ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Particiona por documento para evitar fuga entre train y eval."""
    targets = sorted({str(row.get("target", "")) for row in rows})
    rng = random.Random(SEED)
    rng.shuffle(targets)
    cut = max(1, int(len(targets) * eval_ratio))
    eval_targets = set(targets[:cut])
    train = [r for r in rows if str(r.get("target", "")) not in eval_targets]
    evaluation = [r for r in rows if str(r.get("target", "")) in eval_targets]
    return train, evaluation


def evaluate_candidate(model_name: str, window: int, train_rows: list[dict[str, Any]],
                       eval_rows: list[dict[str, Any]], epochs: int,
                       batch_size: int) -> dict[str, Any]:
    import numpy as np
    import torch
    from scipy.stats import spearmanr
    from transformers import (AutoConfig, AutoModelForSequenceClassification,
                              AutoTokenizer, Trainer, TrainingArguments)

    config = AutoConfig.from_pretrained(model_name)
    hard_limit = int(getattr(config, "max_position_embeddings", window) or window)
    # xlm-roberta reserva 2 posiciones para tokens especiales.
    max_length = min(window, hard_limit - 2 if hard_limit > 512 else min(hard_limit, 512))

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=1, problem_type="regression")

    def encode(rows: list[dict[str, Any]]) -> "torch.utils.data.Dataset":
        texts = [str(r["text"]) for r in rows]
        labels = [float(r["score"]) / 100.0 for r in rows]
        batch = tokenizer(texts, truncation=True, max_length=max_length,
                          padding="max_length", return_tensors="pt")

        class Simple(torch.utils.data.Dataset):
            def __len__(self) -> int:
                return len(labels)

            def __getitem__(self, index: int) -> dict[str, Any]:
                item = {k: v[index] for k, v in batch.items()}
                item["labels"] = torch.tensor(labels[index], dtype=torch.float)
                return item

        return Simple()

    def metrics(pred) -> dict[str, float]:
        preds = np.asarray(pred.predictions).squeeze()
        refs = np.asarray(pred.label_ids).squeeze()
        rho = spearmanr(preds, refs).correlation
        return {"spearman": float(rho) if rho == rho else 0.0,
                "mae": float(np.mean(np.abs(preds - refs)))}

    args = TrainingArguments(
        output_dir=str(REPO_ROOT / ".aulatex-temp" / "model-compare" / model_name.split("/")[-1]),
        num_train_epochs=epochs,
        per_device_train_batch_size=batch_size,
        per_device_eval_batch_size=batch_size,
        learning_rate=2e-5,
        eval_strategy="no",
        save_strategy="no",
        logging_strategy="no",
        report_to=[],
        seed=SEED,
        disable_tqdm=True,
        use_cpu=True,
    )
    trainer = Trainer(model=model, args=args, train_dataset=encode(train_rows),
                      eval_dataset=encode(eval_rows), compute_metrics=metrics)
    trainer.train()
    result = trainer.evaluate()

    lengths = [len(tokenizer.encode(str(r["text"]), truncation=False,
                                    add_special_tokens=False)) for r in eval_rows]
    coverage = 100.0 * sum(1 for n in lengths if n <= max_length) / max(1, len(lengths))

    return {
        "model": model_name,
        "max_length": max_length,
        "hard_limit": hard_limit,
        "spearman": float(result.get("eval_spearman", 0.0)),
        "mae": float(result.get("eval_mae", 0.0)),
        "coverage": coverage,
    }


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

    default_corpus = (REPO_ROOT / "retroalimentacion-editorial" / "aulatex"
                      / "training" / "reward.jsonl")
    parser = argparse.ArgumentParser(prog="compare_reward_models")
    parser.add_argument("--train-file", default=str(default_corpus))
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--eval-ratio", type=float, default=0.2)
    args = parser.parse_args(argv)

    corpus = Path(args.train_file).resolve()
    if not corpus.exists():
        print(f"[compare] No existe el corpus: {corpus}")
        print("          Genera primero: python aulaTEX/aulatex_training/build_corpus_from_repo.py")
        return 1

    rows = load_rows(corpus)
    train_rows, eval_rows = split_by_document(rows, args.eval_ratio)
    scores = [float(r["score"]) for r in rows]

    print(f"[compare] corpus            : {len(rows)} filas ({corpus.name})")
    print(f"[compare] split por documento: train {len(train_rows)} / eval {len(eval_rows)}")
    print(f"[compare] desviacion scores : {statistics.pstdev(scores):.2f}")
    print(f"[compare] epochs {args.epochs}, batch {args.batch_size}, semilla {SEED}")
    print()

    results: list[dict[str, Any]] = []
    for model_name, window in CANDIDATES:
        print(f"[compare] entrenando {model_name} (ventana {window})...")
        try:
            results.append(evaluate_candidate(model_name, window, train_rows,
                                              eval_rows, args.epochs, args.batch_size))
            last = results[-1]
            print(f"[compare]   -> Spearman {last['spearman']:.4f} | "
                  f"MAE {last['mae']:.4f} | cobertura {last['coverage']:.1f}%")
        except Exception as exc:  # noqa: BLE001 - un candidato que falla no aborta la comparacion
            print(f"[compare]   -> FALLO: {exc.__class__.__name__}: {exc}")
        print()

    if not results:
        print("[compare] Ningun candidato completo el entrenamiento.")
        return 1

    print("=" * 78)
    print(f"{'MODELO':<40}{'VENTANA':>9}{'SPEARMAN':>11}{'MAE':>9}{'COBERT.':>9}")
    print("-" * 78)
    for row in sorted(results, key=lambda r: r["spearman"], reverse=True):
        print(f"{row['model'].split('/')[-1]:<40}{row['max_length']:>9}"
              f"{row['spearman']:>11.4f}{row['mae']:>9.4f}{row['coverage']:>8.1f}%")
    print("=" * 78)

    best = max(results, key=lambda r: r["spearman"])
    print(f"\n[compare] GANADOR: {best['model']} (ventana {best['max_length']})")
    if best["spearman"] < 0.5:
        print("[compare] AVISO: Spearman < 0.5. El juez no es confiable todavia;")
        print("          conviene mas corpus antes de escalar a GPU.")
    else:
        print("[compare] Correlacion suficiente para escalar este candidato a GPU.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
