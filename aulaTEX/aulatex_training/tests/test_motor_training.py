from __future__ import annotations

import json
from pathlib import Path

import pytest

from aulaTEX.aulatex_training.motor_training import (
    SCHEMA_VERSION,
    assert_no_group_leakage,
    compact_training_body,
    grouped_split,
    latex_generation_checks,
    privacy_findings,
    read_jsonl,
    validate_sft_row,
    write_jsonl,
)
from aulaTEX.aulatex_training.evaluate_generator import apply_generation_contract
from aulaTEX.aulatex_training.train_generator import render_prompt


def row(index: int, group: str) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "id": str(index),
        "target": f"{group}/actividad-{index}.tex",
        "group": group,
        "technique": "actividad_academica",
        "messages": [
            {"role": "system", "content": "reglas"},
            {"role": "user", "content": "genera"},
            {"role": "assistant", "content": "resultado"},
        ],
        "allowed_citation_keys": [],
        "content_sha256": "a" * 64,
    }


def test_privacy_detects_secrets_and_pii() -> None:
    text = "correo persona@example.com y clave AKIAABCDEFGHIJKLMNOP"
    kinds = {finding.kind for finding in privacy_findings(text)}
    assert {"email", "aws_access_key"} <= kinds


def test_grouped_split_has_no_leakage() -> None:
    rows = [row(index, f"materia-{index // 2}") for index in range(20)]
    splits = grouped_split(rows, seed=7)
    assert_no_group_leakage(splits)
    assert sum(map(len, splits.values())) == len(rows)


def test_leakage_is_rejected() -> None:
    with pytest.raises(ValueError, match="Fuga"):
        assert_no_group_leakage({"train": [row(1, "m")], "validation": [row(2, "m")], "test": []})


def test_schema_validation() -> None:
    assert validate_sft_row(row(1, "m")) == []
    broken = row(2, "m")
    broken["messages"] = []
    assert validate_sft_row(broken)


def test_jsonl_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "data.jsonl"
    assert write_jsonl(path, [row(1, "m")]) == 1
    assert read_jsonl(path)[0]["id"] == "1"


def test_native_image_rule() -> None:
    bad = latex_generation_checks(r"\includegraphics{foto.png}")
    good = latex_generation_checks(r"\insertimage{foto.png}{width=.8\linewidth}{Foto}")
    assert not bad["native_image_rule_ok"]
    assert good["native_image_rule_ok"]


def test_unknown_citations() -> None:
    result = latex_generation_checks(r"Texto \cite{permitida,inventada}.", ["permitida"])
    assert result["unknown_citation_keys"] == ["inventada"]


def test_reasoning_prefix_is_rejected() -> None:
    reasoning = latex_generation_checks("Okay, I need to plan this activity first.\\section{Introducción}")
    direct = latex_generation_checks(r"\section{Introducción}Texto directo.")
    assert reasoning["has_reasoning_prefix"]
    assert not reasoning["starts_with_latex"]
    assert not direct["has_reasoning_prefix"]
    assert direct["starts_with_latex"]


def test_deepseek_direct_prefix_closes_think_block() -> None:
    class Tokenizer:
        chat_template = "template"

        @staticmethod
        def apply_chat_template(messages, tokenize=False, add_generation_prompt=True):
            assert tokenize is False
            assert add_generation_prompt is True
            return "<｜Assistant｜><think>\n"

    prompt = render_prompt(row(1, "m"), Tokenizer(), "</think>\n")
    assert prompt.endswith("<think>\n</think>\n")


def test_mojibake_is_rejected() -> None:
    broken = latex_generation_checks(r"\section{IntroducciA3n}Texto con codificaciA3n rota.")
    clean = latex_generation_checks(r"\section{Introducción}Texto bien codificado.")
    assert broken["has_mojibake"]
    assert not clean["has_mojibake"]


def test_generation_contract_does_not_mutate_source() -> None:
    source = row(1, "m")
    original = source["messages"][-2]["content"]
    contracted = apply_generation_contract(source, "Incluye conclusiones.")
    assert source["messages"][-2]["content"] == original
    assert contracted["messages"][-2]["content"].endswith("Incluye conclusiones.")


def test_structural_compaction_preserves_three_acts() -> None:
    text = (
        "\\templatePortrait\n"
        "\\section{Introduccion}\n" + "Inicio académico. " * 120 + "\n\n"
        "\\section{Tema jurídico}\n" + "Desarrollo argumentado. " * 250 + "\n\n"
        "\\section{Conclusion}\n" + "Cierre reflexivo. " * 120
    )
    compact = compact_training_body(text, max_chars=3600)
    checks = latex_generation_checks(compact)
    assert len(compact) <= 3600
    assert checks["has_introduction"]
    assert checks["has_conclusion"]
    assert "\\section{Tema jurídico}" in compact


def test_singular_accented_conclusion_is_detected() -> None:
    result = latex_generation_checks(r"\section{Conclusión}Cierre.")
    assert result["has_conclusion"]
