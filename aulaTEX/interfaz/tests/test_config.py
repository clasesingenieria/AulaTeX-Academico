from __future__ import annotations

from pathlib import Path
import importlib

import interfaz.config as config_module
from interfaz.config import _normalize_anthropic_endpoint, _normalize_azure_endpoint, load_settings, settings_for_llm_provider, validate_settings


def test_normalize_azure_endpoint_trims_openai_suffixes() -> None:
    assert _normalize_azure_endpoint("https://x.openai.azure.com/openai/") == "https://x.openai.azure.com/"
    assert _normalize_azure_endpoint("https://x.openai.azure.com/openai/v1") == "https://x.openai.azure.com/openai/v1/"
    assert _normalize_azure_endpoint("https://x.services.ai.azure.com/openai/v1") == "https://x.services.ai.azure.com/openai/v1/"
    assert _normalize_azure_endpoint("https://x.services.ai.azure.com/api/projects/p/openai/v1/responses") == (
        "https://x.services.ai.azure.com/api/projects/p/openai/v1/responses"
    )
    assert _normalize_azure_endpoint("https://x.services.ai.azure.com/api/projects/p/openai/v1/chat/completions") == (
        "https://x.services.ai.azure.com/api/projects/p/openai/v1/"
    )
    assert _normalize_azure_endpoint("https://x.services.ai.azure.com") == "https://x.services.ai.azure.com/openai/v1/"
    assert _normalize_azure_endpoint("https://x.openai.azure.com") == "https://x.openai.azure.com/"


def test_normalize_anthropic_endpoint_trims_messages_suffixes() -> None:
    assert _normalize_anthropic_endpoint("https://x.services.ai.azure.com/anthropic/v1/messages") == (
        "https://x.services.ai.azure.com/anthropic"
    )
    assert _normalize_anthropic_endpoint("https://x.services.ai.azure.com") == (
        "https://x.services.ai.azure.com/anthropic"
    )


def test_config_loads_interfaz_env_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_KEY", raising=False)
    monkeypatch.delenv("AZURE_SPEECH_REGION", raising=False)
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("MODEL_ROUTER_BASE_URL", raising=False)
    monkeypatch.delenv("MODEL_ROUTER_API_KEY", raising=False)
    monkeypatch.delenv("MODEL_ROUTER_CHAT_DEPLOYMENT", raising=False)

    (tmp_path / "interfaz.env").write_text(
        "\n".join(
            [
                "TELEGRAM_BOT_TOKEN=desde-interfaz",
                "AZURE_SPEECH_KEY=speech-key",
                "AZURE_SPEECH_REGION=eastus",
                "LLM_PROVIDER=model-router",
                "MODEL_ROUTER_BASE_URL=https://example.services.ai.azure.com/openai/v1/chat/completions",
                "MODEL_ROUTER_API_KEY=router-key",
                "MODEL_ROUTER_CHAT_DEPLOYMENT=model-router",
            ]
        ),
        encoding="utf-8",
    )

    reloaded = importlib.reload(config_module)
    settings = reloaded.load_settings()

    assert settings.telegram_bot_token == "desde-interfaz"
    assert settings.llm_provider == "model-router"
    assert settings.azure_openai_api_key == "router-key"


def test_load_settings_reads_azure_speech_values(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("TELEGRAM_DEFAULT_CHAT_ID", "123")
    monkeypatch.setenv("NOTES_DIR", "data/notes")
    monkeypatch.setenv("AUDIO_STORAGE_DIR", "data/audio")
    monkeypatch.setenv("BOT_MODE", "polling")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("AZURE_SPEECH_LANGUAGE", "es-MX")
    monkeypatch.setenv("RESEARCH_MAX_TOKENS", "2400")
    monkeypatch.setenv("TELEGRAM_REPLY_AUDIO_ENABLED", "true")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "aws-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("AWS_REGION", "us-east-1")
    monkeypatch.setenv("POLLY_VOICE_ID", "Andres")
    monkeypatch.setenv("POLLY_ENGINE", "generative")
    monkeypatch.setenv("POLLY_LANGUAGE_CODE", "es-MX")
    monkeypatch.setenv("POLLY_SAMPLE_RATE", "24000")
    monkeypatch.setenv("POLLY_MAX_CHARS", "1800")
    monkeypatch.setenv("POLLY_TTS_WORKERS", "12")
    monkeypatch.setenv("LLM_PROVIDER", "azure-openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-test")
    monkeypatch.setenv("AZURE_OPENAI_API_VERSION", "2024-10-21")
    monkeypatch.setenv("TRANSCRIPTION_PROVIDER", "realtime")
    monkeypatch.setenv("AZURE_OPENAI_REALTIME_ENDPOINT", "https://example.services.ai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME", "gpt-realtime")
    monkeypatch.setenv("AZURE_OPENAI_REALTIME_API_KEY", "realtime-key")
    monkeypatch.setenv("AZURE_OPENAI_REALTIME_TRANSCRIPTION_MODEL", "gpt-4o-transcribe")

    settings = load_settings()

    assert settings.telegram_bot_token == "token"
    assert settings.llm_provider == "azure-openai"
    assert settings.llm_api_kind == "classic-chat"
    assert settings.telegram_default_chat_id == "123"
    assert settings.notes_dir == Path("data/notes").resolve()
    assert settings.audio_storage_dir == Path("data/audio").resolve()
    assert settings.bot_mode == "polling"
    assert settings.azure_speech_key == "speech-key"
    assert settings.azure_speech_region == "eastus"
    assert settings.azure_speech_language == "es-MX"
    assert settings.research_max_tokens == 2400
    assert settings.telegram_reply_audio_enabled is True
    assert settings.aws_access_key_id == "aws-key"
    assert settings.aws_secret_access_key == "aws-secret"
    assert settings.aws_region == "us-east-1"
    assert settings.aws_polly_voice_id == "Andres"
    assert settings.aws_polly_engine == "generative"
    assert settings.aws_polly_language_code == "es-MX"
    assert settings.aws_polly_sample_rate == "24000"
    assert settings.polly_max_chars == 1800
    assert settings.polly_tts_workers == 12
    assert settings.azure_openai_endpoint == "https://example.openai.azure.com/"
    assert settings.azure_openai_api_key == "openai-key"
    assert settings.azure_openai_chat_deployment == "gpt-test"
    assert settings.azure_openai_api_version == "2024-10-21"
    assert settings.azure_openai_context_window_tokens == 1_050_000
    assert settings.azure_openai_max_input_tokens == 922_000
    assert settings.azure_openai_max_output_tokens == 128_000
    assert settings.transcription_provider == "realtime"
    assert settings.azure_openai_realtime_endpoint == "https://example.services.ai.azure.com/openai/v1/"
    assert settings.azure_openai_realtime_deployment_name == "gpt-realtime"
    assert settings.azure_openai_realtime_api_key == "realtime-key"
    assert settings.azure_openai_realtime_transcription_model == "gpt-4o-transcribe"
    assert settings.aulatex_motor_execution_mode == "delegate"


def test_load_settings_reads_aulatex_motor_execution_mode(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-test")
    monkeypatch.setenv("AULATEX_MOTOR_EXECUTION_MODE", "plan-only")

    settings = load_settings()

    assert settings.aulatex_motor_execution_mode == "plan-only"


def test_load_settings_reads_azure_openai_aliases(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("LLM_PROVIDER", "azure-openai")
    monkeypatch.delenv("AZURE_OPENAI_ENDPOINT", raising=False)
    monkeypatch.delenv("AZURE_OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("AZURE_EXISTING_AIPROJECT_ENDPOINT", "https://example.openai.azure.com/openai/v1/")
    monkeypatch.setenv("AZURE_API_KEY", "legacy-key")
    monkeypatch.setenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-legacy")

    settings = load_settings()

    assert settings.llm_provider == "azure-openai"
    assert settings.llm_api_kind == "openai-responses"
    assert settings.azure_openai_endpoint == "https://example.openai.azure.com/openai/v1/"
    assert settings.azure_openai_api_key == "legacy-key"
    assert settings.azure_openai_chat_deployment == "gpt-legacy"


def test_load_settings_selects_codex_provider(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("LLM_PROVIDER", "codex")
    monkeypatch.setenv("CODEX_BASE_URL", "https://example.services.ai.azure.com/openai/v1/responses")
    monkeypatch.setenv("CODEX_API_KEY", "codex-key")
    monkeypatch.setenv("CODEX_CHAT_DEPLOYMENT", "gpt-5.3-codex")
    monkeypatch.setenv("CODEX_API_VERSION", "2026-02-24")

    settings = load_settings()

    assert settings.llm_provider == "codex"
    assert settings.llm_api_kind == "openai-responses"
    assert settings.azure_openai_endpoint == "https://example.services.ai.azure.com/openai/v1/responses"
    assert settings.azure_openai_api_key == "codex-key"
    assert settings.azure_openai_chat_deployment == "gpt-5.3-codex"
    assert settings.azure_openai_api_version == "2026-02-24"


def test_load_settings_selects_model_router_from_auto_alias(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("MODEL_ROUTER_BASE_URL", "https://example.services.ai.azure.com/openai/v1/chat/completions")
    monkeypatch.setenv("MODEL_ROUTER_API_KEY", "router-key")
    monkeypatch.setenv("MODEL_ROUTER_CHAT_DEPLOYMENT", "model-router")

    settings = load_settings()

    assert settings.llm_provider == "model-router"
    assert settings.llm_api_kind == "openai-chat"
    assert settings.azure_openai_endpoint == "https://example.services.ai.azure.com/openai/v1/"
    assert settings.azure_openai_api_key == "router-key"
    assert settings.azure_openai_chat_deployment == "model-router"


def test_load_settings_selects_claude_foundry_provider(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("LLM_PROVIDER", "claude-foundry")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_BASE_URL", "https://example.services.ai.azure.com/anthropic/v1/messages")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_API_KEY", "claude-key")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT", "claude-opus-4-8")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_API_VERSION", "2023-06-01")

    settings = load_settings()

    assert settings.llm_provider == "claude-foundry"
    assert settings.llm_api_kind == "anthropic"
    assert settings.azure_openai_endpoint == "https://example.services.ai.azure.com/anthropic"
    assert settings.azure_openai_api_key == "claude-key"
    assert settings.azure_openai_chat_deployment == "claude-opus-4-8"
    assert settings.azure_openai_api_version == "2023-06-01"


def test_settings_for_llm_provider_does_not_mutate_base_settings(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("LLM_PROVIDER", "model-router")
    monkeypatch.setenv("MODEL_ROUTER_BASE_URL", "https://example.services.ai.azure.com/openai/v1/chat/completions")
    monkeypatch.setenv("MODEL_ROUTER_API_KEY", "router-key")
    monkeypatch.setenv("MODEL_ROUTER_CHAT_DEPLOYMENT", "model-router")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_BASE_URL", "https://example.services.ai.azure.com/anthropic/v1/messages")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_API_KEY", "claude-key")
    monkeypatch.setenv("ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT", "claude-opus-4-8")

    base_settings = load_settings()
    claude_settings = settings_for_llm_provider(base_settings, "claude-foundry")

    assert base_settings.llm_provider == "model-router"
    assert base_settings.llm_api_kind == "openai-chat"
    assert claude_settings.llm_provider == "claude-foundry"
    assert claude_settings.llm_api_kind == "anthropic"
    assert claude_settings.azure_openai_api_key == "claude-key"
    assert claude_settings.telegram_bot_token == base_settings.telegram_bot_token


def test_load_settings_validates_llm_token_limits(monkeypatch) -> None:
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "token")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "speech-key")
    monkeypatch.setenv("AZURE_SPEECH_REGION", "eastus")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com/openai/")
    monkeypatch.setenv("AZURE_OPENAI_API_KEY", "openai-key")
    monkeypatch.setenv("AZURE_OPENAI_CHAT_DEPLOYMENT", "gpt-test")
    monkeypatch.setenv("AZURE_OPENAI_CONTEXT_WINDOW_TOKENS", "1050000")
    monkeypatch.setenv("AZURE_OPENAI_MAX_INPUT_TOKENS", "950000")
    monkeypatch.setenv("AZURE_OPENAI_MAX_OUTPUT_TOKENS", "128000")

    settings = load_settings()

    assert settings.azure_openai_context_window_tokens == 1_050_000
    assert settings.azure_openai_max_output_tokens == 128_000
    assert settings.azure_openai_max_input_tokens == 922_000
    assert settings.azure_openai_max_input_tokens + settings.azure_openai_max_output_tokens == settings.azure_openai_context_window_tokens


def test_validate_settings_requires_azure_speech(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "azure-openai")
    settings = load_settings()
    object.__setattr__(settings, "transcription_provider", "speech")
    object.__setattr__(settings, "telegram_bot_token", "")
    object.__setattr__(settings, "azure_speech_key", "")
    object.__setattr__(settings, "azure_speech_region", "")
    object.__setattr__(settings, "azure_openai_endpoint", "")
    object.__setattr__(settings, "azure_openai_api_key", "")
    object.__setattr__(settings, "azure_openai_chat_deployment", "")

    missing = validate_settings(settings)

    assert "TELEGRAM_BOT_TOKEN" in missing
    assert "AZURE_SPEECH_KEY" in missing
    assert "AZURE_SPEECH_REGION" in missing
    assert "AZURE_OPENAI_ENDPOINT o AZURE_EXISTING_AIPROJECT_ENDPOINT o AZURE_ENDPOINT" in missing
    assert "AZURE_OPENAI_API_KEY o AZURE_API_KEY" in missing
    assert "AZURE_OPENAI_CHAT_DEPLOYMENT o AZURE_OPENAI_DEPLOYMENT_NAME" in missing


def test_validate_settings_realtime_does_not_require_azure_speech() -> None:
    settings = load_settings()
    object.__setattr__(settings, "transcription_provider", "realtime")
    object.__setattr__(settings, "azure_speech_key", "")
    object.__setattr__(settings, "azure_speech_region", "")
    object.__setattr__(settings, "azure_openai_realtime_endpoint", "https://example.services.ai.azure.com/openai/v1/")
    object.__setattr__(settings, "azure_openai_realtime_deployment_name", "gpt-realtime")
    object.__setattr__(settings, "azure_openai_realtime_api_key", "realtime-key")

    missing = validate_settings(settings)

    assert "AZURE_SPEECH_KEY" not in missing
    assert "AZURE_SPEECH_REGION" not in missing
    assert "AZURE_OPENAI_REALTIME_ENDPOINT" not in missing
    assert "AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME" not in missing
    assert "AZURE_OPENAI_REALTIME_API_KEY" not in missing


def test_validate_settings_requires_selected_provider_env_names(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "claude-foundry")
    settings = load_settings()
    object.__setattr__(settings, "telegram_bot_token", "token")
    object.__setattr__(settings, "azure_speech_key", "speech-key")
    object.__setattr__(settings, "azure_speech_region", "eastus")
    object.__setattr__(settings, "transcription_provider", "speech")
    object.__setattr__(settings, "azure_openai_endpoint", "")
    object.__setattr__(settings, "azure_openai_api_key", "")
    object.__setattr__(settings, "azure_openai_chat_deployment", "")

    missing = validate_settings(settings)

    assert "ANTHROPIC_FOUNDRY_BASE_URL" in missing
    assert "ANTHROPIC_FOUNDRY_API_KEY" in missing
    assert "ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT o ANTHROPIC_FOUNDRY_DEPLOYMENT_NAME" in missing
