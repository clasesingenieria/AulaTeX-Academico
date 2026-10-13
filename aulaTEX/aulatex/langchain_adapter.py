from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlsplit

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from .llm_bridge import (
    DEFAULT_MAX_TOKENS,
    DEFAULT_TIMEOUT_SECONDS,
    AulaTeXLLMClient,
    AulaTeXLLMConfig,
    LLMCallResult,
    _friendly_error,
    _normalize_requested_max_tokens,
    _normalize_timeout,
    _should_retry_with_lower_max_tokens,
    normalize_llm_engine_label,
)


class AulaTeXLLMInterface(Protocol):
    def engines(self) -> tuple[str, ...]: ...

    def check(self, engine: str, timeout_seconds: int = 10) -> LLMCallResult: ...

    def call(
        self,
        engine: str,
        prompt: str,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> LLMCallResult: ...


@dataclass(frozen=True)
class LangChainInvocationConfig:
    engine: str
    max_tokens: int
    timeout_seconds: int


class AulaTeXLangChainAdapter:
    """LangChain wrapper over AulaTeX LLM config without duplicating provider credentials."""

    def __init__(self, client: AulaTeXLLMClient | None = None, *, fallback_to_direct: bool = True) -> None:
        self.client = client or AulaTeXLLMClient()
        self.fallback_to_direct = fallback_to_direct

    def engines(self) -> tuple[str, ...]:
        return self.client.engines()

    def check(self, engine: str, timeout_seconds: int = 10) -> LLMCallResult:
        return self.client.check(engine, timeout_seconds=timeout_seconds)

    def call(
        self,
        engine: str,
        prompt: str,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> LLMCallResult:
        selected = normalize_llm_engine_label(engine)
        config = AulaTeXLLMConfig.from_env(selected)
        if config is None:
            return LLMCallResult(selected, False, "", f"Configuracion LLM incompleta para {selected}")

        last_exc: Exception | None = None
        for candidate_max_tokens in self._max_token_attempts(max_tokens):
            invoke_cfg = LangChainInvocationConfig(
                engine=selected,
                max_tokens=candidate_max_tokens,
                timeout_seconds=_normalize_timeout(timeout_seconds, candidate_max_tokens, config.timeout_seconds),
            )
            try:
                model = self._build_model(config, invoke_cfg)
                response = model.invoke([HumanMessage(content=prompt)])
                text = self._extract_message_text(response.content)
                if text.strip():
                    return LLMCallResult(selected, True, text)
                last_exc = RuntimeError(f"{selected} devolvió una respuesta vacía mediante LangChain.")
                break
            except Exception as exc:
                last_exc = exc
                if not _should_retry_with_lower_max_tokens(exc):
                    break

        if self.fallback_to_direct:
            direct = self.client.call(selected, prompt, max_tokens=max_tokens, timeout_seconds=timeout_seconds)
            if direct.ok and direct.text.strip():
                return direct
            return LLMCallResult(selected, False, "", direct.error or _friendly_error(last_exc or RuntimeError("Respuesta vacía.")))
        return LLMCallResult(selected, False, "", _friendly_error(last_exc or RuntimeError("Fallo desconocido.")))

    def cycle(
        self,
        prompts: list[str],
        engines: list[str] | tuple[str, ...] | None = None,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> list[LLMCallResult]:
        engine_list = [engine for engine in list(engines or self.engines()) if engine in self.engines()]
        if not engine_list:
            engine_list = ["Codex"]
        results: list[LLMCallResult] = []
        for index, prompt in enumerate(prompts):
            engine = engine_list[index % len(engine_list)]
            results.append(self.call(engine, prompt, max_tokens=max_tokens, timeout_seconds=timeout_seconds))
        return results

    def _build_model(self, config: AulaTeXLLMConfig, invoke_cfg: LangChainInvocationConfig) -> Any:
        if config.is_anthropic():
            return ChatAnthropic(
                model=config.deployment,
                anthropic_api_key=config.api_key,
                anthropic_api_url=config.base_url,
                max_tokens=invoke_cfg.max_tokens,
                temperature=config.temperature,
                default_request_timeout=invoke_cfg.timeout_seconds,
                streaming=False,
            )

        return ChatOpenAI(
            model_name=config.deployment,
            openai_api_key=config.api_key,
            openai_api_base=self._openai_base_url(config.base_url),
            max_tokens=invoke_cfg.max_tokens,
            temperature=config.temperature,
            request_timeout=invoke_cfg.timeout_seconds,
            use_responses_api=self._uses_responses_api(config.base_url),
            streaming=False,
        )

    def _extract_message_text(self, content: Any) -> str:
        if isinstance(content, str):
            return content.strip()
        if isinstance(content, list):
            parts: list[str] = []
            for item in content:
                if isinstance(item, str):
                    parts.append(item)
                    continue
                if isinstance(item, dict):
                    text = item.get("text")
                    if isinstance(text, str):
                        parts.append(text)
            return "".join(parts).strip()
        return str(content or "").strip()

    def _openai_base_url(self, base_url: str) -> str:
        trimmed = base_url.rstrip("/")
        for suffix in ("/chat/completions", "/responses"):
            if trimmed.lower().endswith(suffix):
                return trimmed[: -len(suffix)]
        return trimmed

    def _uses_responses_api(self, base_url: str) -> bool:
        return urlsplit(base_url).path.lower().endswith("/responses")

    def _max_token_attempts(self, max_tokens: int) -> list[int]:
        requested = _normalize_requested_max_tokens(max_tokens)
        attempts: list[int] = []
        candidate = requested
        while candidate >= 2048:
            if candidate not in attempts:
                attempts.append(candidate)
            candidate //= 2
        if 2048 not in attempts:
            attempts.append(2048)
        return attempts
