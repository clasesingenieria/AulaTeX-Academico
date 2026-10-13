"""Entrenamiento del Reward Model editorial de AulaTeX (job para GPU).

Este script se ejecuta DENTRO del contenedor de entrenamiento en la nube
(Azure ML o SageMaker) y también localmente en CPU para pruebas de humo
(``--smoke-test``), con un modelo diminuto y pocos pasos.

Objetivo
--------
Entrenar un *juez* de calidad editorial aprendido de los propios resultados de
AulaTeX, para sustituir/complementar el proxy heurístico ``_quality_score``.
Esto ataca el riesgo de Goodhart: si se optimiza contra una métrica heurística,
el sistema aprende a *hackear la métrica* en lugar de mejorar el texto.

Formulación
-----------
Regresión sobre el score de calidad a partir del texto LaTeX:
    entrada  : texto del .tex (truncado a ``--max-length`` tokens)
    objetivo : quality_after normalizado a [0, 1]

Se usa ``AutoModelForSequenceClassification`` con ``num_labels=1`` (cabeza de
regresión), que es la formulación estándar de reward model.

Entrada de datos
----------------
Un ``.jsonl`` con, al menos:
    {"text": "<contenido LaTeX>", "score": 88.0}

El consolidador ``aulatex/training_dataset.py`` produce métricas por ciclo pero
NO el texto (para no inflar el dataset). Para el reward model hace falta un
dataset con texto: ver ``--help`` de ``build_reward_corpus`` en el README del
job, o generarlo emparejando ``target``/``tex`` de cada manifest con su score.

Honestidad sobre los requisitos
-------------------------------
* Sin suficientes ejemplos con VARIANZA de calidad, el reward model no aprende
  nada útil: el script exige un mínimo y aborta con un mensaje claro.
* La métrica de éxito es la correlación de Spearman en validación: si es baja,
  el juez no es confiable y NO debe usarse para optimizar.

Uso local (prueba de humo, CPU, segundos):
    python aulaTEX/aulatex_training/train_reward_model.py --smoke-test

Uso en la nube (GPU):
    python train_reward_model.py --train-file data/reward.jsonl \
        --model-name FacebookAI/xlm-roberta-base --epochs 3 --output-dir outputs
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

MIN_EXAMPLES = 50
MIN_SCORE_STD = 2.0  # desviación mínima de los scores: sin varianza no hay señal


def load_jsonl(path: Path) -> list[dict[str, Any]]:
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


def make_smoke_data() -> list[dict[str, Any]]:
    """Datos sintéticos para validar que el pipeline corre de punta a punta."""
    good = (
        r"\section{Marco de análisis}Se argumenta que, por tanto, la norma "
        r"\cite{ref1} establece un criterio. Sin embargo, la doctrina "
        r"\cite{ref2} matiza el alcance. En consecuencia, se concluye que..."
    )
    bad = r"\section{Desarrollo}\begin{itemize}\item TODO\item pendiente\end{itemize}"
    rows: list[dict[str, Any]] = []
    for i in range(30):
        rows.append({"text": f"{good} variante {i}.", "score": 85.0 + (i % 10)})
        rows.append({"text": f"{bad} variante {i}.", "score": 40.0 + (i % 10)})
    return rows


def build_dataset(rows: list[dict[str, Any]], tokenizer, max_length: int):
    from datasets import Dataset

    texts = [str(r["text"]) for r in rows]
    # Normaliza el score a [0,1] para estabilizar la regresión.
    labels = [float(r.get("score", 0.0)) / 100.0 for r in rows]

    ds = Dataset.from_dict({"text": texts, "labels": labels})

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=max_length, padding=False)

    ds = ds.map(tokenize, batched=True, remove_columns=["text"])
    return ds


def split_rows_by_source(rows: list[dict[str, Any]], test_ratio: float = 0.2):
    """Separa por actividad fuente para impedir fuga entre original y degradaciones."""
    groups: dict[str, list[dict[str, Any]]] = {}
    for index, row in enumerate(rows):
        target = str(row.get("source_target") or row.get("target") or f"row-{index}")
        target = target.split("::", 1)[0]
        groups.setdefault(target, []).append(row)
    ordered = sorted(groups, key=lambda value: hashlib.sha256(value.encode("utf-8")).hexdigest())
    n_test = max(1, round(len(ordered) * test_ratio))
    test_groups = set(ordered[:n_test])
    train_rows = [row for group, items in groups.items() if group not in test_groups for row in items]
    test_rows = [row for group, items in groups.items() if group in test_groups for row in items]
    return train_rows, test_rows


def spearman(y_true, y_pred) -> float:
    """Spearman sin scipy: correlación de Pearson sobre los rangos."""
    import numpy as np

    def ranks(values):
        order = np.argsort(values)
        r = np.empty_like(order, dtype=float)
        r[order] = np.arange(len(values), dtype=float)
        return r

    rt, rp = ranks(np.asarray(y_true, dtype=float)), ranks(np.asarray(y_pred, dtype=float))
    if rt.std() == 0 or rp.std() == 0:
        return 0.0
    return float(np.corrcoef(rt, rp)[0, 1])


def train(args: argparse.Namespace) -> int:
    import numpy as np
    import torch
    from transformers import (
        AutoModelForSequenceClassification,
        AutoTokenizer,
        DataCollatorWithPadding,
        Trainer,
        TrainingArguments,
    )

    if args.smoke_test:
        rows = make_smoke_data()
        model_name = args.model_name or "hf-internal-testing/tiny-random-BertModel"
        epochs = 1
        print(f"[reward] SMOKE TEST: {len(rows)} ejemplos sintéticos, modelo '{model_name}'")
    else:
        train_file = Path(args.train_file).resolve()
        if not train_file.exists():
            print(f"[reward] ERROR: no existe {train_file}")
            return 2
        rows = load_jsonl(train_file)
        model_name = args.model_name or "FacebookAI/xlm-roberta-base"
        epochs = args.epochs
        print(f"[reward] ejemplos leídos: {len(rows)} de {train_file}")

        if len(rows) < MIN_EXAMPLES:
            print(f"[reward] ABORTA: se requieren >= {MIN_EXAMPLES} ejemplos con texto.")
            return 2
        scores = np.asarray([float(r.get("score", 0.0)) for r in rows])
        if scores.std() < MIN_SCORE_STD:
            print(f"[reward] ABORTA: varianza de scores insuficiente (std={scores.std():.2f} "
                  f"< {MIN_SCORE_STD}). Sin contraste no hay señal que aprender.")
            return 2

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name, num_labels=1, problem_type="regression"
    )

    train_rows, eval_rows = split_rows_by_source(rows)
    print(f"[reward] split por actividad: train={len(train_rows)}, eval={len(eval_rows)}")
    train_ds = build_dataset(train_rows, tokenizer, args.max_length)
    eval_ds = build_dataset(eval_rows, tokenizer, args.max_length)

    def compute_metrics(eval_pred):
        preds = np.asarray(eval_pred.predictions).squeeze()
        labels = np.asarray(eval_pred.label_ids).squeeze()
        mae = float(np.abs(preds - labels).mean())
        return {"mae": mae, "spearman": spearman(labels, preds)}

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    # bf16 en CPU activa AMX en Xeon 4.ª/5.ª gen: ~2.7x más rápido que fp32.
    use_bf16_cpu = (
        not torch.cuda.is_available()
        and hasattr(torch.cpu, "_is_avx512_bf16_supported")
        and torch.cpu._is_avx512_bf16_supported()
    )

    training_args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        eval_strategy="epoch",
        save_strategy="no",
        logging_steps=10,
        report_to=[],
        seed=0,
        # En CPU, transformers exige use_cpu=True para aceptar bf16 (AMX).
        use_cpu=not torch.cuda.is_available(),
        bf16=use_bf16_cpu,
        dataloader_pin_memory=torch.cuda.is_available(),
    )
    if use_bf16_cpu:
        print(f"[reward] bf16/AMX activo en CPU ({torch.get_num_threads()} hilos).")

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        data_collator=DataCollatorWithPadding(tokenizer),
        compute_metrics=compute_metrics,
    )

    trainer.train()
    metrics = trainer.evaluate()
    print("\n[reward] === Métricas de validación ===")
    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            print(f"  {key}: {value:.4f}")

    rho = float(metrics.get("eval_spearman", 0.0))
    print(f"\n[reward] Spearman = {rho:.3f}")
    if rho < 0.5 and not args.smoke_test:
        print("[reward] VEREDICTO: correlación BAJA. El juez no es confiable todavía;\n"
              "         NO lo uses para optimizar (riesgo de reforzar ruido).")
    elif not args.smoke_test:
        print("[reward] VEREDICTO: correlación aceptable. El juez puede complementar\n"
              "         el proxy heurístico _quality_score.")

    # En Azure ML / SageMaker el artefacto debe quedar en el dir de salida estándar.
    save_dir = Path(os.environ.get("SM_MODEL_DIR", str(output_dir / "model")))
    save_dir.mkdir(parents=True, exist_ok=True)
    trainer.save_model(str(save_dir))
    tokenizer.save_pretrained(str(save_dir))
    (output_dir / "metrics.json").write_text(
        json.dumps({k: v for k, v in metrics.items() if isinstance(v, (int, float))},
                   ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"[reward] modelo guardado en: {save_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="train_reward_model",
        description="Entrena el reward model editorial (regresión de calidad sobre texto LaTeX).",
    )
    parser.add_argument("--train-file", default="", help="JSONL con {'text','score'}.")
    parser.add_argument("--model-name", default="", help="Modelo base de HuggingFace.")
    parser.add_argument("--output-dir", default="outputs", help="Directorio de salida.")
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--learning-rate", type=float, default=2e-5)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--smoke-test", action="store_true",
                        help="Corre con datos sintéticos y modelo diminuto (valida el pipeline).")
    args = parser.parse_args(argv)

    if not args.smoke_test and not args.train_file:
        parser.error("se requiere --train-file (o usa --smoke-test)")
    return train(args)


if __name__ == "__main__":
    sys.exit(main())
