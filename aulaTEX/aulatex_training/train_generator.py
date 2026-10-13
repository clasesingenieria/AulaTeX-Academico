"""Ajuste SFT LoRA/QLoRA del generador de actividades AulaTeX.

El modo predeterminado es ``--dry-run``: valida configuración, datos y entorno
sin descargar ni entrenar un modelo. El entrenamiento requiere ``--run``.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

from .motor_training import read_jsonl, validate_sft_row


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {"base_model", "max_seq_length", "learning_rate", "epochs", "lora_r", "lora_alpha"}
    missing = required - config.keys()
    if missing:
        raise ValueError(f"Configuración incompleta: {sorted(missing)}")
    return config


def validate_inputs(config: dict[str, Any], train_file: Path, eval_file: Path) -> dict[str, Any]:
    train_rows, eval_rows = read_jsonl(train_file), read_jsonl(eval_file)
    errors = [error for row in (*train_rows, *eval_rows) for error in validate_sft_row(row)]
    if errors:
        raise ValueError(f"Dataset inválido; primeros errores: {errors[:5]}")
    train_groups = {str(row.get("group")) for row in train_rows}
    eval_groups = {str(row.get("group")) for row in eval_rows}
    overlap = train_groups & eval_groups
    if overlap:
        raise ValueError(f"Fuga de grupos train/eval: {sorted(overlap)[:5]}")
    if not train_rows or not eval_rows:
        raise ValueError("Train y evaluación deben contener al menos un ejemplo.")
    return {
        "base_model": config["base_model"],
        "direct_response_prefix": config.get("direct_response_prefix", ""),
        "train_rows": len(train_rows),
        "eval_rows": len(eval_rows),
        "train_groups": len(train_groups),
        "eval_groups": len(eval_groups),
        "platform": platform.platform(),
    }


def render_prompt(row: dict[str, Any], tokenizer: Any,
                  direct_response_prefix: str = "") -> str:
    messages = row["messages"][:-1]
    if getattr(tokenizer, "chat_template", None):
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
    else:
        prompt = (
            "\n\n".join(
                f"{message['role'].upper()}: {message['content']}"
                for message in messages
            )
            + "\n\nASSISTANT:"
        )
    return prompt + direct_response_prefix


def render_text(row: dict[str, Any], tokenizer: Any,
                direct_response_prefix: str = "") -> str:
    if direct_response_prefix:
        return (
            render_prompt(row, tokenizer, direct_response_prefix)
            + row["messages"][-1]["content"]
            + (tokenizer.eos_token or "")
        )
    messages = row["messages"]
    if getattr(tokenizer, "chat_template", None):
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
    return "\n\n".join(f"{message['role'].upper()}: {message['content']}" for message in messages)


def train(config: dict[str, Any], train_file: Path, eval_file: Path, output_dir: Path,
          *, smoke: bool = False) -> None:
    import torch
    from datasets import Dataset
    from peft import LoraConfig, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        EarlyStoppingCallback,
        Trainer,
        TrainingArguments,
    )

    if not torch.cuda.is_available():
        raise RuntimeError("El entrenamiento real requiere CUDA; ejecute en la estación A10G o WSL2/Linux.")

    train_rows, eval_rows = read_jsonl(train_file), read_jsonl(eval_file)
    tokenizer = AutoTokenizer.from_pretrained(
        config["base_model"], trust_remote_code=bool(config.get("trust_remote_code", False))
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    use_4bit = config.get("quantization") == "4bit"
    quantization_config = None
    if use_4bit:
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16 if config.get("bf16", True) else torch.float16,
            bnb_4bit_use_double_quant=True,
        )
    model = AutoModelForCausalLM.from_pretrained(
        config["base_model"],
        trust_remote_code=bool(config.get("trust_remote_code", False)),
        quantization_config=quantization_config,
        torch_dtype=torch.bfloat16 if config.get("bf16", True) else torch.float16,
        device_map="auto",
    )
    if use_4bit:
        model = prepare_model_for_kbit_training(model)
    if config.get("gradient_checkpointing", True):
        model.gradient_checkpointing_enable()
        model.config.use_cache = False

    peft_config = LoraConfig(
        r=int(config["lora_r"]),
        lora_alpha=int(config["lora_alpha"]),
        lora_dropout=float(config.get("lora_dropout", 0.05)),
        target_modules=list(config["target_modules"]),
        bias="none",
        task_type="CAUSAL_LM",
    )
    from peft import get_peft_model
    model = get_peft_model(model, peft_config)

    max_length = int(config["max_seq_length"])
    direct_response_prefix = str(config.get("direct_response_prefix", ""))

    def encode(row: dict[str, Any]) -> dict[str, Any]:
        full_text = render_text(row, tokenizer, direct_response_prefix)
        prompt_text = render_prompt(row, tokenizer, direct_response_prefix)
        encoded = tokenizer(
            full_text, truncation=True, max_length=max_length,
            padding="max_length",
        )
        prompt_ids = tokenizer(
            prompt_text, truncation=True, max_length=max_length,
            add_special_tokens=False,
        )["input_ids"]
        labels = encoded["input_ids"].copy()
        prompt_length = min(len(prompt_ids), len(labels))
        labels[:prompt_length] = [-100] * prompt_length
        labels = [label if mask else -100 for label, mask in zip(labels, encoded["attention_mask"])]
        encoded["labels"] = labels
        return encoded

    train_ds = Dataset.from_list(train_rows).map(encode, remove_columns=list(train_rows[0].keys()))
    eval_ds = Dataset.from_list(eval_rows).map(encode, remove_columns=list(eval_rows[0].keys()))
    output_dir.mkdir(parents=True, exist_ok=True)
    args = TrainingArguments(
        output_dir=str(output_dir),
        num_train_epochs=float(config["epochs"]),
        max_steps=int(config.get("max_steps_smoke", 2)) if smoke else -1,
        per_device_train_batch_size=int(config.get("per_device_train_batch_size", 1)),
        per_device_eval_batch_size=int(config.get("per_device_eval_batch_size", 1)),
        gradient_accumulation_steps=int(config.get("gradient_accumulation_steps", 16)),
        learning_rate=float(config["learning_rate"]),
        bf16=bool(config.get("bf16", True) and torch.cuda.is_bf16_supported()),
        fp16=not bool(config.get("bf16", True) and torch.cuda.is_bf16_supported()),
        eval_strategy="steps",
        save_strategy="steps",
        eval_steps=int(config.get("eval_steps", 100)),
        save_steps=int(config.get("save_steps", 100)),
        logging_steps=int(config.get("logging_steps", 10)),
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        report_to=[],
        seed=int(config.get("seed", 42)),
    )
    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=eval_ds,
        callbacks=[EarlyStoppingCallback(early_stopping_patience=2)],
    )
    trainer.train(resume_from_checkpoint=config.get("resume_from_checkpoint") or None)
    trainer.save_model(str(output_dir))
    tokenizer.save_pretrained(str(output_dir))
    metrics = trainer.evaluate()
    (output_dir / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description="Entrena el adaptador generador AulaTeX.")
    parser.add_argument("--config", default=str(Path(__file__).parent / "configs" / "sft-a10g.json"))
    parser.add_argument("--train-file", default=str(root / "data/private/splits/sft-train.jsonl"))
    parser.add_argument("--eval-file", default=str(root / "data/private/splits/sft-validation.jsonl"))
    parser.add_argument("--output-dir", default=str(root / "aulaTEX/models/local/motor-inteligente"))
    parser.add_argument("--run", action="store_true", help="Ejecuta entrenamiento; sin esta opción solo valida.")
    parser.add_argument("--smoke", action="store_true", help="Limita el entrenamiento real a pocos pasos.")
    args = parser.parse_args(argv)

    config = load_config(Path(args.config).resolve())
    report = validate_inputs(config, Path(args.train_file).resolve(), Path(args.eval_file).resolve())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not args.run:
        print("[sft] DRY-RUN correcto. Use --run únicamente en la estación GPU.")
        return 0
    train(config, Path(args.train_file).resolve(), Path(args.eval_file).resolve(),
          Path(args.output_dir).resolve(), smoke=args.smoke)
    return 0


if __name__ == "__main__":
    sys.exit(main())
