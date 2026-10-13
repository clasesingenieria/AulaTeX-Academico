"""Evalúa un adaptador QLoRA AulaTeX sobre ejemplos reservados.

Compara, con decodificación determinista, el modelo base y el adaptador sobre
los mismos prompts. Registra pérdida de validación y controles estructurales
LaTeX; no promueve automáticamente el adaptador.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .motor_training import latex_generation_checks, read_jsonl
from .train_generator import load_config, render_prompt


def apply_generation_contract(row: dict[str, Any], instruction: str) -> dict[str, Any]:
    """Agrega restricciones de salida sin modificar el ejemplo original."""
    if not instruction:
        return row
    cloned = {**row, "messages": [dict(message) for message in row["messages"]]}
    cloned["messages"][-2]["content"] = (
        cloned["messages"][-2]["content"].rstrip() + "\n\n" + instruction.strip()
    )
    return cloned


def _generate(model: Any, tokenizer: Any, prompt: str, max_new_tokens: int) -> str:
    import torch

    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1536)
    encoded = {key: value.to(model.device) for key, value in encoded.items()}
    with torch.inference_mode():
        output = model.generate(
            **encoded,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )
    return tokenizer.decode(output[0, encoded["input_ids"].shape[1]:], skip_special_tokens=True)


def evaluate(config_path: Path, adapter_dir: Path, eval_file: Path,
             output_path: Path, samples: int, max_new_tokens: int) -> dict[str, Any]:
    import torch
    from peft import PeftModel
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    config = load_config(config_path)
    rows = read_jsonl(eval_file)[:samples]
    tokenizer = AutoTokenizer.from_pretrained(config["base_model"])
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    base = AutoModelForCausalLM.from_pretrained(
        config["base_model"], quantization_config=quantization,
        torch_dtype=torch.bfloat16, device_map="auto",
    )
    model = PeftModel.from_pretrained(base, adapter_dir)
    model.eval()

    results: list[dict[str, Any]] = []
    direct_response_prefix = str(config.get("direct_response_prefix", ""))
    generation_instruction = str(config.get("generation_instruction", ""))
    for row in rows:
        inference_row = apply_generation_contract(row, generation_instruction)
        prompt = render_prompt(inference_row, tokenizer, direct_response_prefix)
        with model.disable_adapter():
            base_text = _generate(model, tokenizer, prompt, max_new_tokens)
        adapted_text = _generate(model, tokenizer, prompt, max_new_tokens)
        allowed = row.get("allowed_citation_keys", [])
        results.append({
            "id": row.get("id"),
            "target": row.get("target"),
            "base": latex_generation_checks(base_text, allowed),
            "adapted": latex_generation_checks(adapted_text, allowed),
            "base_chars": len(base_text),
            "adapted_chars": len(adapted_text),
            "base_preview": base_text[:1000],
            "adapted_preview": adapted_text[:1000],
        })

    positive_checks = ("has_introduction", "has_conclusion", "native_image_rule_ok", "starts_with_latex")
    base_scores = [sum(bool(item["base"].get(key)) for key in positive_checks) for item in results]
    adapted_scores = [sum(bool(item["adapted"].get(key)) for key in positive_checks) for item in results]
    base_passed = sum(base_scores)
    adapted_passed = sum(adapted_scores)
    adapted_safe = all(
        not item["adapted"].get("has_reasoning_prefix")
        and not item["adapted"].get("has_placeholders")
        and not item["adapted"].get("has_mojibake")
        and not item["adapted"].get("unknown_citation_keys")
        for item in results
    )
    adapted_complete = all(
        item["adapted"].get("starts_with_latex")
        and item["adapted"].get("has_introduction")
        and item["adapted"].get("has_conclusion")
        and item["adapted"].get("native_image_rule_ok")
        for item in results
    )
    improves_every_sample = all(adapted > base for adapted, base in zip(adapted_scores, base_scores))
    summary = {
        "base_model": config["base_model"],
        "adapter": str(adapter_dir),
        "samples": len(results),
        "base_checks_passed": base_passed,
        "adapted_checks_passed": adapted_passed,
        "adapted_safe": adapted_safe,
        "adapted_complete": adapted_complete,
        "improves_every_sample": improves_every_sample,
        "promotable": bool(results and adapted_safe and adapted_complete and improves_every_sample),
        "results": results,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Compara el modelo base y el adaptador AulaTeX.")
    parser.add_argument("--config", required=True)
    parser.add_argument("--adapter-dir", required=True)
    parser.add_argument("--eval-file", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--samples", type=int, default=2)
    parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args()
    result = evaluate(Path(args.config), Path(args.adapter_dir), Path(args.eval_file),
                      Path(args.output), args.samples, args.max_new_tokens)
    print(json.dumps({key: value for key, value in result.items() if key != "results"},
                     ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
