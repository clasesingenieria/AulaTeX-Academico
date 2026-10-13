from __future__ import annotations

from aulaTEX.aulatex.config import MODEL_ROUTER_ENGINE, restrict_engines_to_available
from aulaTEX.aulatex.llm_bridge import engine_chain_for_task


def test_router_only_restricts_explicit_engine_lists(monkeypatch) -> None:
    monkeypatch.setenv("AULATEX_MODEL_ROUTER_ONLY", "1")

    assert restrict_engines_to_available(["Codex", "Claude Foundry"]) == [MODEL_ROUTER_ENGINE]


def test_router_only_disables_cross_deployment_safety_net(monkeypatch) -> None:
    monkeypatch.setenv("AULATEX_MODEL_ROUTER_ONLY", "true")
    monkeypatch.setenv("AULATEX_LLM_ENGINE", "Claude Foundry")

    assert engine_chain_for_task("revision", forced_engine="GPT-Pro") == [MODEL_ROUTER_ENGINE]


def test_normal_mode_preserves_task_routing(monkeypatch) -> None:
    monkeypatch.delenv("AULATEX_MODEL_ROUTER_ONLY", raising=False)
    monkeypatch.delenv("AULATEX_LLM_ENGINE", raising=False)

    chain = engine_chain_for_task("rapido")

    assert chain[0] == MODEL_ROUTER_ENGINE
    assert "Claude Foundry" in chain
