from __future__ import annotations

import json
import os
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from scripts.aulatex import config, llm_bridge


MINI = "GPT-5-Mini"


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    """No real credentials, key files, environment, or provider requests."""
    env_file = tmp_path / "aulatex.env"
    env_file.write_text(
        "GPT_5_MINI_BASE_URL=https://example.invalid/openai/v1\n"
        "GPT_5_MINI_API_KEY=fake-unit-test-key\n"
        "GPT_5_MINI_CHAT_DEPLOYMENT=academic-mini-deployment\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(os, "environ", {"AULATEX_ENV_PATH": str(env_file)})
    monkeypatch.setattr(config, "_decrypt_local_secrets", lambda: None)
    monkeypatch.setattr(llm_bridge._requests, "post", Mock(side_effect=AssertionError("External call forbidden")))
    return env_file


def test_policy_preserves_normal_routing_when_unset():
    assert config.required_llm_engine() is None
    assert llm_bridge.normalize_llm_engine_label("unrecognized") == "Codex"
    assert "Claude Foundry" in llm_bridge.engine_chain_for_task("revision", forced_engine=MINI)


def test_required_engine_has_one_route_and_no_rescue(monkeypatch):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", MINI)
    client = llm_bridge.AulaTeXLLMClient()
    call = Mock(return_value=llm_bridge.LLMCallResult(MINI, False, "", "HTTP 429"))
    monkeypatch.setattr(client, "call", call)
    result = client.call_with_safety_net("A safe test prompt", task="revision", engine=MINI)
    assert not result.ok
    assert call.call_count == 1
    assert call.call_args.args[0] == MINI
    assert llm_bridge.engine_chain_for_task("razonamiento") == [MINI]


@pytest.mark.parametrize("requested", ["Codex", "Claude Foundry", "unknown-label"])
def test_wrong_engine_rejected_before_any_transport(monkeypatch, requested):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", MINI)
    client = llm_bridge.AulaTeXLLMClient()
    with pytest.raises(config.LLMEnginePolicyError):
        client.call(requested, "Safe test prompt")
    with pytest.raises(config.LLMEnginePolicyError):
        client.call_image(requested, "Safe test prompt", image_bytes=b"image", media_type="image/png")
    with pytest.raises(config.LLMEnginePolicyError):
        llm_bridge.engine_chain_for_task("revision", forced_engine=requested)
    llm_bridge._requests.post.assert_not_called()


@pytest.mark.parametrize("required", ["unknown-label", "invalid https://secret.invalid"])
def test_invalid_policy_has_sanitized_failure(monkeypatch, required):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", required)
    with pytest.raises(config.LLMEnginePolicyError) as error:
        config.required_llm_engine()
    assert required not in str(error.value)


def test_router_only_conflict_fails_closed(monkeypatch):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", MINI)
    monkeypatch.setenv("AULATEX_MODEL_ROUTER_ONLY", "true")
    with pytest.raises(config.LLMEnginePolicyError, match="conflicto"):
        config.restrict_engines_to_available([MINI])
    with pytest.raises(config.LLMEnginePolicyError):
        llm_bridge.engine_chain_for_task("rapido")


def test_restriction_does_not_silently_remap_mixed_list(monkeypatch):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", MINI)
    assert config.restrict_engines_to_available(["gpt-5-mini"]) == [MINI]
    assert config.restrict_engines_to_available([]) == [MINI]
    with pytest.raises(config.LLMEnginePolicyError):
        config.restrict_engines_to_available([MINI, "Codex"])


def test_cycle_defaults_to_required_engine_and_rejects_invalid_labels(monkeypatch):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", MINI)
    client = llm_bridge.AulaTeXLLMClient()
    call = Mock(return_value=llm_bridge.LLMCallResult(MINI, True, "Safe answer"))
    monkeypatch.setattr(client, "call", call)
    assert client.cycle(["Safe prompt"])[0].engine == MINI
    assert call.call_args.args[0] == MINI
    with pytest.raises(config.LLMEnginePolicyError):
        client.cycle(["Safe prompt"], [MINI, "invalid-label"])


def test_env_reload_cannot_disable_explicit_process_policy(isolated_runtime, monkeypatch):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", MINI)
    with isolated_runtime.open("a", encoding="utf-8") as file:
        file.write("AULATEX_REQUIRED_ENGINE=\nAULATEX_LLM_REVIEW_ENGINE=Codex\n")
    candidate = llm_bridge.AulaTeXLLMConfig.from_env()
    assert candidate.engine_label == MINI
    assert config.required_llm_engine() == MINI


def test_policy_from_env_is_validated_before_transport(isolated_runtime):
    with isolated_runtime.open("a", encoding="utf-8") as file:
        file.write("AULATEX_REQUIRED_ENGINE=GPT-5-Mini\nAULATEX_MODEL_ROUTER_ONLY=1\n")
    with pytest.raises(config.LLMEnginePolicyError):
        llm_bridge.AulaTeXLLMClient()
    llm_bridge._requests.post.assert_not_called()


def test_explicit_candidate_cannot_bypass_policy(monkeypatch):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", MINI)
    candidate = llm_bridge.AulaTeXLLMConfig("Codex", "https://example.invalid", "fake-key", "other")
    result = llm_bridge.validate_llm_response(MINI, config=candidate)
    assert not result["ok"]
    llm_bridge._requests.post.assert_not_called()


@pytest.mark.parametrize("image", [False, True])
@pytest.mark.parametrize("reported", ["gpt-5-mini-2025-08-07", "other-provider-model", None])
def test_provider_evidence_is_not_inferred_from_requested_deployment(monkeypatch, image, reported):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", MINI)
    payload = {"model": reported, "choices": [{"message": {"content": "Generated answer"}}]}
    reply = SimpleNamespace(raise_for_status=lambda: None, json=lambda: payload)
    post = Mock(return_value=reply)
    monkeypatch.setattr(llm_bridge._requests, "post", post)
    client = llm_bridge.AulaTeXLLMClient()
    if image:
        result = client.call_image(MINI, "Safe test prompt", image_bytes=b"image", media_type="image/png", max_tokens=2048)
    else:
        result = client.call(MINI, "Safe test prompt", max_tokens=2048)
    assert result.ok and result.text == "Generated answer"
    assert result.requested_deployment == "academic-mini-deployment"
    assert result.provider_model == (reported or "")
    assert post.call_count == 1
    assert "fake-unit-test-key" not in json.dumps(asdict(result))


def test_arbitrary_provider_metadata_is_not_copied(monkeypatch):
    monkeypatch.setenv("AULATEX_REQUIRED_ENGINE", MINI)
    reply = SimpleNamespace(raise_for_status=lambda: None, json=lambda: {
        "model": "https://user:password@example.invalid/", "choices": [{"message": {"content": "Safe answer"}}],
    })
    monkeypatch.setattr(llm_bridge._requests, "post", Mock(return_value=reply))
    result = llm_bridge.AulaTeXLLMClient().call(MINI, "Safe prompt", max_tokens=2048)
    assert result.provider_model == ""
    assert "password" not in json.dumps(asdict(result))


def test_json_mode_and_reasoning_are_opt_in(monkeypatch):
    monkeypatch.setenv('AULATEX_LLM_JSON_OBJECT','1')
    monkeypatch.setenv('AULATEX_LLM_REASONING_EFFORT','low')
    candidate=llm_bridge.AulaTeXLLMConfig(MINI,'https://example.invalid/openai/v1','fake','gpt-5-mini')
    for path in ('/chat/completions','/responses'):
        payload=llm_bridge._openai_payload('https://example.invalid'+path,candidate,'Return JSON',4000,temperature=0)
        if path=='/responses':
            assert payload['text']['format']=={'type':'json_object'}
            assert payload['reasoning']=={'effort':'low'}
        else:
            assert payload['response_format']=={'type':'json_object'}
            assert payload['reasoning_effort']=='low'


def test_usage_and_truncation_are_safe_metadata():
    candidate=llm_bridge.AulaTeXLLMConfig(MINI,'https://example.invalid','fake','gpt-5-mini')
    value=llm_bridge._response_text({'model':'gpt-5-mini','choices':[{'message':{'content':'{"partial":'},'finish_reason':'length'}],
        'usage':{'completion_tokens':1000,'completion_tokens_details':{'reasoning_tokens':800},'secret':'must-not-copy'}},candidate)
    result=llm_bridge._successful_result(MINI,value)
    assert result.finish_reason=='length'
    assert result.usage=={'completion_tokens':1000,'reasoning_tokens':800}
