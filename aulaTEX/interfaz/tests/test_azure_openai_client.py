from __future__ import annotations

from interfaz.azure_openai_client import invoke_chat, normalize_anthropic_messages_url
from interfaz.config import load_settings


class DummyResp:
    def __init__(self, status_code: int = 200, json_data=None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def raise_for_status(self) -> None:
        if not (200 <= self.status_code < 300):
            raise Exception(f"HTTP {self.status_code}")

    def json(self):
        return self._json


def test_normalize_anthropic_messages_url() -> None:
    assert normalize_anthropic_messages_url("https://example.services.ai.azure.com/anthropic") == (
        "https://example.services.ai.azure.com/anthropic/v1/messages"
    )
    assert normalize_anthropic_messages_url("https://example.services.ai.azure.com") == (
        "https://example.services.ai.azure.com/anthropic/v1/messages"
    )


def test_invoke_chat_routes_to_claude_foundry(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("LLM_PROVIDER", "claude-foundry")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_BASE_URL", "https://example.services.ai.azure.com/anthropic")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_API_KEY", "claude-key")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT", "claude-opus-4-8")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_API_VERSION", "2023-06-01")

    calls: list[dict[str, object]] = []

    def fake_post(url, headers=None, json=None, timeout=None):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return DummyResp(
            200,
            {
                "content": [
                    {"type": "text", "text": "Respuesta Claude"},
                ]
            },
        )

    monkeypatch.setattr("requests.post", fake_post)

    settings = load_settings()
    result = invoke_chat(
        settings,
        [
            {"role": "system", "content": "Responde breve."},
            {"role": "user", "content": "Hola"},
        ],
        max_tokens=321,
        temperature=0.2,
        response_format_json=True,
    )

    assert result == "Respuesta Claude"
    assert calls[0]["url"] == "https://example.services.ai.azure.com/anthropic/v1/messages"
    assert calls[0]["headers"]["x-api-key"] == "claude-key"
    assert calls[0]["headers"]["anthropic-version"] == "2023-06-01"
    assert calls[0]["json"]["model"] == "claude-opus-4-8"
    assert calls[0]["json"]["max_tokens"] == 321
    assert "temperature" not in calls[0]["json"]
    assert calls[0]["json"]["messages"] == [
        {"role": "user", "content": [{"type": "text", "text": "Hola"}]}
    ]
    assert "JSON valido" in calls[0]["json"]["system"]


def test_invoke_chat_uses_openai_responses_for_codex(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("LLM_PROVIDER", "codex")
    monkeypatch.setenv("CODEX_BASE_URL", "https://example.services.ai.azure.com/openai/v1/responses")
    monkeypatch.setenv("CODEX_API_KEY", "codex-key")
    monkeypatch.setenv("CODEX_CHAT_DEPLOYMENT", "gpt-5.3-codex")

    captured: dict[str, object] = {}

    class FakeResponses:
        def create(self, **payload):
            captured.update(payload)
            return {"output_text": "Respuesta Codex"}

    class FakeClient:
        def __init__(self, api_key=None, base_url=None):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            self.responses = FakeResponses()

    monkeypatch.setattr("interfaz.azure_openai_client.OpenAI", FakeClient)

    settings = load_settings()
    result = invoke_chat(
        settings,
        [{"role": "user", "content": "Hola"}],
        max_tokens=222,
        temperature=0.3,
    )

    assert result == "Respuesta Codex"
    assert captured["api_key"] == "codex-key"
    assert captured["base_url"] == "https://example.services.ai.azure.com/openai/v1/"
    assert captured["model"] == "gpt-5.3-codex"
    assert captured["max_output_tokens"] == 222


def test_invoke_chat_uses_openai_chat_completions_for_model_router(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("LLM_PROVIDER", "model-router")
    monkeypatch.setenv("MODEL_ROUTER_BASE_URL", "https://example.services.ai.azure.com/openai/v1/chat/completions")
    monkeypatch.setenv("MODEL_ROUTER_API_KEY", "router-key")
    monkeypatch.setenv("MODEL_ROUTER_CHAT_DEPLOYMENT", "model-router")

    captured: dict[str, object] = {}

    class FakeChatCompletions:
        def create(self, **payload):
            captured.update(payload)
            return type(
                "ChatCompletionResp",
                (),
                {
                    "choices": [
                        type(
                            "Choice",
                            (),
                            {"message": type("Message", (), {"content": "Respuesta Router"})()},
                        )()
                    ]
                },
            )()

    class FakeChat:
        def __init__(self):
            self.completions = FakeChatCompletions()

    class FakeClient:
        def __init__(self, api_key=None, base_url=None):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            self.chat = FakeChat()

    monkeypatch.setattr("interfaz.azure_openai_client.OpenAI", FakeClient)

    settings = load_settings()
    result = invoke_chat(
        settings,
        [{"role": "user", "content": "Hola"}],
        max_tokens=333,
        temperature=0.1,
        response_format_json=True,
    )

    assert result == "Respuesta Router"
    assert captured["api_key"] == "router-key"
    assert captured["base_url"] == "https://example.services.ai.azure.com/openai/v1/"
    assert captured["model"] == "model-router"
    assert captured["max_tokens"] == 333
    assert captured["response_format"] == {"type": "json_object"}