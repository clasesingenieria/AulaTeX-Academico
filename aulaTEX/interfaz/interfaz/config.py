from __future__ import annotations

import os
from dataclasses import dataclass, replace
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


def _load_env_files() -> None:
    load_dotenv(override=True)
    # La interfaz está ABSORBIDA en AulaTeX (aulaTEX/interfaz/): comparte el
    # único .env cifrado del proyecto (aulaTEX/aulatex.env) como fuente de
    # verdad. Ruta: este archivo es aulaTEX/interfaz/interfaz/config.py, por lo
    # que parents[2] == aulaTEX/.
    scripts_dir = Path(__file__).resolve().parents[2]
    parent_env = scripts_dir / "aulatex.env"
    if parent_env.exists():
        load_dotenv(parent_env, override=True)
    _decrypt_local_secrets()


def _decrypt_local_secrets() -> None:
    """Descifra en os.environ los valores ``enc:`` usando la clave local del
    proyecto padre AulaTeX (aulaTEX/secret.key). Best-effort y silencioso."""
    if not any(str(v).startswith("enc:") for v in os.environ.values()):
        return
    try:
        import importlib.util

        module_path = Path(__file__).resolve().parents[2] / "secrets_local.py"
        if not module_path.exists():
            return
        spec = importlib.util.spec_from_file_location("aulatex_secrets_local", module_path)
        if spec is None or spec.loader is None:
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        fernet = mod.resolve_fernet(create=False)
        if fernet is None:
            return
        from cryptography.fernet import InvalidToken

        for key, value in list(os.environ.items()):
            if isinstance(value, str) and value.startswith("enc:"):
                try:
                    os.environ[key] = fernet.decrypt(value[4:].encode("ascii")).decode("utf-8")
                except InvalidToken:
                    pass
    except Exception:
        pass


_load_env_files()


@dataclass(frozen=True)
class ResolvedLlmConfig:
    provider: str
    api_kind: str
    endpoint: str
    api_key: str
    deployment: str
    api_version: str
    endpoint_env: str
    api_key_env: str
    deployment_env_label: str


_LLM_PROVIDER_ALIASES = {
    "": "azure-openai",
    "azure": "azure-openai",
    "azure-openai": "azure-openai",
    "openai": "azure-openai",
    "codex": "codex",
    "gpt-pro": "gpt-pro",
    "gptpro": "gpt-pro",
    "model-router": "model-router",
    "modelrouter": "model-router",
    "auto": "model-router",
    "claude": "claude-foundry",
    "anthropic": "claude-foundry",
    "claude-foundry": "claude-foundry",
    "anthropic-foundry": "claude-foundry",
}

_SUPPORTED_LLM_PROVIDERS = (
    "azure-openai",
    "codex",
    "gpt-pro",
    "model-router",
    "claude-foundry",
)


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    notes_dir: Path
    audio_storage_dir: Path
    bot_mode: str
    azure_speech_key: str
    azure_speech_region: str
    azure_speech_language: str
    telegram_default_chat_id: str = ""
    research_max_tokens: int = 1800
    azure_openai_context_window_tokens: int = 1_050_000
    azure_openai_max_input_tokens: int = 922_000
    azure_openai_max_output_tokens: int = 128_000
    telegram_reply_audio_enabled: bool = False
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    aws_polly_voice_id: str = "Andres"
    aws_polly_engine: str = "generative"
    aws_polly_language_code: str = "es-MX"
    aws_polly_sample_rate: str = "24000"
    polly_max_chars: int = 2500
    polly_tts_workers: int = 12
    llm_provider: str = "azure-openai"
    llm_api_kind: str = "openai"
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_chat_deployment: str = ""
    azure_openai_api_version: str = "2024-10-21"
    transcription_provider: str = "speech"
    azure_openai_realtime_endpoint: str = ""
    azure_openai_realtime_deployment_name: str = ""
    azure_openai_realtime_api_key: str = ""
    azure_openai_realtime_transcription_model: str = "gpt-4o-mini-transcribe"
    aulatex_motor_execution_mode: str = "delegate"
    # --- Generación visual (gpt-image / sora) ---
    azure_openai_images_endpoint: str = ""
    azure_openai_image_deployment: str = "gpt-image-2"
    azure_openai_image_api_key: str = ""
    azure_openai_video_endpoint: str = ""
    azure_openai_video_deployment: str = "sora-2"
    azure_openai_video_api_key: str = ""
    azure_openai_video_max_seconds: int = 8


def _normalize_azure_endpoint(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""

    parts = urlsplit(raw)
    if parts.scheme and parts.netloc:
        path = parts.path.rstrip("/")
        if path.endswith("/openai/v1/responses"):
            return f"{parts.scheme}://{parts.netloc}{path}"
        if path.endswith("/openai/v1/chat/completions"):
            return f"{parts.scheme}://{parts.netloc}{path[: -len('/chat/completions')]}/"
        if path.endswith("/openai/v1"):
            return f"{parts.scheme}://{parts.netloc}{path}/"
        if parts.netloc.endswith(".services.ai.azure.com"):
            return f"{parts.scheme}://{parts.netloc}/openai/v1/"
        return f"{parts.scheme}://{parts.netloc}/"

    base = raw.rstrip("/")
    for suffix in ("/openai/v1", "/openai", "/openai/"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base + "/"


def _normalize_anthropic_endpoint(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""

    parts = urlsplit(raw)
    if parts.scheme and parts.netloc:
        path = parts.path.rstrip("/")
        if path.endswith("/v1/messages"):
            path = path[: -len("/v1/messages")]
        elif path.endswith("/messages"):
            path = path[: -len("/messages")]

        if "/anthropic/" in path:
            path = path[: path.index("/anthropic/") + len("/anthropic")]
        elif path.endswith("/anthropic"):
            pass
        elif parts.netloc.endswith(".services.ai.azure.com"):
            path = (path.rstrip("/") + "/anthropic") if path else "/anthropic"
        return f"{parts.scheme}://{parts.netloc}{path}"

    base = raw.rstrip("/")
    if base.endswith("/v1/messages"):
        base = base[: -len("/v1/messages")]
    elif base.endswith("/messages"):
        base = base[: -len("/messages")]
    if "/anthropic/" in base:
        base = base[: base.index("/anthropic/") + len("/anthropic")]
    elif ".services.ai.azure.com" in base and not base.endswith("/anthropic"):
        base = base + "/anthropic"
    return base


def _canonical_llm_provider(value: str) -> str:
    normalized = value.strip().lower().replace("_", "-")
    return _LLM_PROVIDER_ALIASES.get(normalized, normalized or "azure-openai")


def _first_env(*names: str) -> str:
    for name in names:
        value = os.getenv(name, "").strip()
        if value:
            return value
    return ""


def _first_mapping_value(env: dict[str, str], *names: str) -> str:
    for name in names:
        value = env.get(name, "").strip()
        if value:
            return value
    return ""


def _detect_openai_api_kind(raw_endpoint: str) -> str:
    endpoint = raw_endpoint.strip().rstrip("/").lower()
    if endpoint.endswith("/chat/completions"):
        return "openai-chat"
    if "/openai/v1" in endpoint:
        return "openai-responses"
    return "classic-chat"


def _resolve_llm_config(provider: str, env: dict[str, str] | None = None) -> ResolvedLlmConfig:
    env = env or os.environ
    if provider == "codex":
        raw_endpoint = env.get("CODEX_BASE_URL", "")
        return ResolvedLlmConfig(
            provider=provider,
            api_kind=_detect_openai_api_kind(raw_endpoint),
            endpoint=_normalize_azure_endpoint(raw_endpoint),
            api_key=env.get("CODEX_API_KEY", "").strip(),
            deployment=_first_mapping_value(env, "CODEX_CHAT_DEPLOYMENT", "CODEX_DEPLOYMENT_NAME"),
            api_version=env.get("CODEX_API_VERSION", "2026-02-24").strip() or "2026-02-24",
            endpoint_env="CODEX_BASE_URL",
            api_key_env="CODEX_API_KEY",
            deployment_env_label="CODEX_CHAT_DEPLOYMENT o CODEX_DEPLOYMENT_NAME",
        )

    if provider == "gpt-pro":
        raw_endpoint = env.get("GPT_PRO_BASE_URL", "")
        return ResolvedLlmConfig(
            provider=provider,
            api_kind=_detect_openai_api_kind(raw_endpoint),
            endpoint=_normalize_azure_endpoint(raw_endpoint),
            api_key=env.get("GPT_PRO_API_KEY", "").strip(),
            deployment=_first_mapping_value(env, "GPT_PRO_CHAT_DEPLOYMENT", "GPT_PRO_DEPLOYMENT_NAME"),
            api_version=env.get("GPT_PRO_API_VERSION", "2026-03-05").strip() or "2026-03-05",
            endpoint_env="GPT_PRO_BASE_URL",
            api_key_env="GPT_PRO_API_KEY",
            deployment_env_label="GPT_PRO_CHAT_DEPLOYMENT o GPT_PRO_DEPLOYMENT_NAME",
        )

    if provider == "model-router":
        raw_endpoint = env.get("MODEL_ROUTER_BASE_URL", "")
        return ResolvedLlmConfig(
            provider=provider,
            api_kind=_detect_openai_api_kind(raw_endpoint),
            endpoint=_normalize_azure_endpoint(raw_endpoint),
            api_key=env.get("MODEL_ROUTER_API_KEY", "").strip(),
            deployment=_first_mapping_value(env, "MODEL_ROUTER_CHAT_DEPLOYMENT", "MODEL_ROUTER_DEPLOYMENT_NAME"),
            api_version=env.get("MODEL_ROUTER_API_VERSION", "2025-11-18").strip() or "2025-11-18",
            endpoint_env="MODEL_ROUTER_BASE_URL",
            api_key_env="MODEL_ROUTER_API_KEY",
            deployment_env_label="MODEL_ROUTER_CHAT_DEPLOYMENT o MODEL_ROUTER_DEPLOYMENT_NAME",
        )

    if provider == "claude-foundry":
        return ResolvedLlmConfig(
            provider=provider,
            api_kind="anthropic",
            endpoint=_normalize_anthropic_endpoint(env.get("ANTHROPIC_FOUNDRY_BASE_URL", "")),
            api_key=env.get("ANTHROPIC_FOUNDRY_API_KEY", "").strip(),
            deployment=_first_mapping_value(env, "ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT", "ANTHROPIC_FOUNDRY_DEPLOYMENT_NAME"),
            api_version=env.get("ANTHROPIC_FOUNDRY_API_VERSION", "2023-06-01").strip() or "2023-06-01",
            endpoint_env="ANTHROPIC_FOUNDRY_BASE_URL",
            api_key_env="ANTHROPIC_FOUNDRY_API_KEY",
            deployment_env_label="ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT o ANTHROPIC_FOUNDRY_DEPLOYMENT_NAME",
        )

    raw_endpoint = _first_mapping_value(
        env,
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_EXISTING_AIPROJECT_ENDPOINT",
        "AZURE_ENDPOINT",
    )
    return ResolvedLlmConfig(
        provider="azure-openai",
        api_kind=_detect_openai_api_kind(raw_endpoint),
        endpoint=_normalize_azure_endpoint(raw_endpoint),
        api_key=_first_mapping_value(env, "AZURE_OPENAI_API_KEY", "AZURE_API_KEY"),
        deployment=_first_mapping_value(env, "AZURE_OPENAI_CHAT_DEPLOYMENT", "AZURE_OPENAI_DEPLOYMENT_NAME"),
        api_version=env.get("AZURE_OPENAI_API_VERSION", "2024-10-21").strip() or "2024-10-21",
        endpoint_env="AZURE_OPENAI_ENDPOINT o AZURE_EXISTING_AIPROJECT_ENDPOINT o AZURE_ENDPOINT",
        api_key_env="AZURE_OPENAI_API_KEY o AZURE_API_KEY",
        deployment_env_label="AZURE_OPENAI_CHAT_DEPLOYMENT o AZURE_OPENAI_DEPLOYMENT_NAME",
    )


def _validated_llm_token_limits() -> tuple[int, int, int]:
    context_window_tokens = max(1, int(os.getenv("AZURE_OPENAI_CONTEXT_WINDOW_TOKENS", "1050000")))
    max_output_tokens = max(1, int(os.getenv("AZURE_OPENAI_MAX_OUTPUT_TOKENS", "128000")))
    default_input_tokens = max(1, context_window_tokens - max_output_tokens)
    max_input_tokens = max(1, int(os.getenv("AZURE_OPENAI_MAX_INPUT_TOKENS", str(default_input_tokens))))

    if max_output_tokens >= context_window_tokens:
        max_output_tokens = context_window_tokens
        max_input_tokens = 1
    elif max_input_tokens + max_output_tokens > context_window_tokens:
        max_input_tokens = context_window_tokens - max_output_tokens

    return context_window_tokens, max_input_tokens, max_output_tokens


def llm_max_output_tokens(settings: Settings, requested: int | None = None) -> int:
    limit = max(1, settings.azure_openai_max_output_tokens)
    if requested is None:
        return limit
    return max(1, min(int(requested), limit))


def settings_for_llm_provider(settings: Settings, provider: str) -> Settings:
    llm_provider = _canonical_llm_provider(provider)
    llm_config = _resolve_llm_config(llm_provider)
    return replace(
        settings,
        llm_provider=llm_provider,
        llm_api_kind=llm_config.api_kind,
        azure_openai_endpoint=llm_config.endpoint,
        azure_openai_api_key=llm_config.api_key,
        azure_openai_chat_deployment=llm_config.deployment,
        azure_openai_api_version=llm_config.api_version,
    )


def load_settings() -> Settings:
    notes_dir = os.getenv("NOTES_DIR") or os.getenv("NOTES_OUTPUT_DIR") or "data/notes"
    context_window_tokens, max_input_tokens, max_output_tokens = _validated_llm_token_limits()
    llm_provider = _canonical_llm_provider(os.getenv("LLM_PROVIDER", ""))
    llm_config = _resolve_llm_config(llm_provider)
    research_max_tokens = max(
        400,
        min(max_output_tokens, int(os.getenv("RESEARCH_MAX_TOKENS", str(max_output_tokens)))),
    )

    return Settings(
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_default_chat_id=os.getenv("TELEGRAM_DEFAULT_CHAT_ID", "").strip(),
        notes_dir=Path(notes_dir).resolve(),
        audio_storage_dir=Path(os.getenv("AUDIO_STORAGE_DIR", "data/audio")).resolve(),
        bot_mode=os.getenv("BOT_MODE", "polling").strip().lower() or "polling",
        azure_speech_key=os.getenv("AZURE_SPEECH_KEY", "").strip(),
        azure_speech_region=os.getenv("AZURE_SPEECH_REGION", "").strip(),
        azure_speech_language=os.getenv("AZURE_SPEECH_LANGUAGE", "es-MX").strip() or "es-MX",
        research_max_tokens=research_max_tokens,
        azure_openai_context_window_tokens=context_window_tokens,
        azure_openai_max_input_tokens=max_input_tokens,
        azure_openai_max_output_tokens=max_output_tokens,
        telegram_reply_audio_enabled=os.getenv("TELEGRAM_REPLY_AUDIO_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"},
        aws_access_key_id=(
            os.getenv("AWS_ACCESS_KEY_ID")
            or os.getenv("POLLY_AWS_ACCESS_KEY_ID")
            or ""
        ).strip(),
        aws_secret_access_key=(
            os.getenv("AWS_SECRET_ACCESS_KEY")
            or os.getenv("POLLY_AWS_SECRET_ACCESS_KEY")
            or ""
        ).strip(),
        aws_region=(
            os.getenv("AWS_REGION")
            or os.getenv("POLLY_AWS_REGION")
            or "us-east-1"
        ).strip() or "us-east-1",
        aws_polly_voice_id=os.getenv("POLLY_VOICE_ID", "Andres").strip() or "Andres",
        aws_polly_engine=os.getenv("POLLY_ENGINE", "generative").strip() or "generative",
        aws_polly_language_code=os.getenv("POLLY_LANGUAGE_CODE", "es-MX").strip() or "es-MX",
        aws_polly_sample_rate=os.getenv("POLLY_SAMPLE_RATE", "24000").strip() or "24000",
        polly_max_chars=max(300, int(os.getenv("POLLY_MAX_CHARS", os.getenv("MAX_CHARS", "2500")))),
        polly_tts_workers=max(1, int(os.getenv("POLLY_TTS_WORKERS", "12"))),
        llm_provider=llm_provider,
        llm_api_kind=llm_config.api_kind,
        azure_openai_endpoint=llm_config.endpoint,
        azure_openai_api_key=llm_config.api_key,
        azure_openai_chat_deployment=llm_config.deployment,
        azure_openai_api_version=llm_config.api_version,
        transcription_provider=os.getenv("TRANSCRIPTION_PROVIDER", "speech").strip().lower() or "speech",
        azure_openai_realtime_endpoint=_normalize_azure_endpoint(os.getenv("AZURE_OPENAI_REALTIME_ENDPOINT", "")),
        azure_openai_realtime_deployment_name=os.getenv("AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME", "").strip(),
        azure_openai_realtime_api_key=(
            os.getenv("AZURE_OPENAI_REALTIME_API_KEY")
            or os.getenv("AZURE_OPENAI_API_KEY")
            or ""
        ).strip(),
        azure_openai_realtime_transcription_model=os.getenv(
            "AZURE_OPENAI_REALTIME_TRANSCRIPTION_MODEL",
            "gpt-4o-mini-transcribe",
        ).strip() or "gpt-4o-mini-transcribe",
        aulatex_motor_execution_mode=os.getenv("AULATEX_MOTOR_EXECUTION_MODE", "delegate").strip().lower() or "delegate",
        azure_openai_images_endpoint=os.getenv("AZURE_OPENAI_IMAGES_ENDPOINT", "").strip(),
        azure_openai_image_deployment=os.getenv("AZURE_OPENAI_IMAGE_DEPLOYMENT", "gpt-image-2").strip() or "gpt-image-2",
        azure_openai_image_api_key=os.getenv("AZURE_OPENAI_IMAGE_API_KEY", "").strip(),
        azure_openai_video_endpoint=os.getenv("AZURE_OPENAI_VIDEO_ENDPOINT", "").strip(),
        azure_openai_video_deployment=os.getenv("AZURE_OPENAI_VIDEO_DEPLOYMENT", "sora-2").strip() or "sora-2",
        azure_openai_video_api_key=os.getenv("AZURE_OPENAI_VIDEO_API_KEY", "").strip(),
        azure_openai_video_max_seconds=int(os.getenv("AZURE_OPENAI_VIDEO_MAX_SECONDS", "8") or "8"),
    )


def validate_settings(settings: Settings) -> list[str]:
    missing: list[str] = []
    if not settings.telegram_bot_token:
        missing.append("TELEGRAM_BOT_TOKEN")

    if settings.llm_provider not in _SUPPORTED_LLM_PROVIDERS:
        missing.append(
            "LLM_PROVIDER debe ser azure-openai, codex, gpt-pro, model-router o claude-foundry"
        )

    llm_config = _resolve_llm_config(settings.llm_provider)

    provider = settings.transcription_provider
    if provider not in {"speech", "realtime", "auto"}:
        missing.append("TRANSCRIPTION_PROVIDER debe ser speech, realtime o auto")

    if provider in {"speech", "auto"}:
        if not settings.azure_speech_key:
            missing.append("AZURE_SPEECH_KEY")
        if not settings.azure_speech_region:
            missing.append("AZURE_SPEECH_REGION")

    if provider in {"realtime", "auto"}:
        if not settings.azure_openai_realtime_endpoint:
            missing.append("AZURE_OPENAI_REALTIME_ENDPOINT")
        if not settings.azure_openai_realtime_deployment_name:
            missing.append("AZURE_OPENAI_REALTIME_DEPLOYMENT_NAME")
        if not settings.azure_openai_realtime_api_key:
            missing.append("AZURE_OPENAI_REALTIME_API_KEY")

    if not settings.azure_openai_endpoint:
        missing.append(llm_config.endpoint_env)
    if not settings.azure_openai_api_key:
        missing.append(llm_config.api_key_env)
    if not settings.azure_openai_chat_deployment:
        missing.append(llm_config.deployment_env_label)
    return missing
