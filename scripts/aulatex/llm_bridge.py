from __future__ import annotations

import base64
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

try:
    import requests as _requests
except ModuleNotFoundError:
    _requests = None

from .config import (
    ENGINE_ENV_PREFIX,
    LLM_ENGINES,
    MODEL_ROUTER_ENGINE,
    load_aulatex_env,
    model_router_only_enabled,
    usable_secret,
)


_FALSE_VALUES = {"0", "false", "no", "off"}
_TRUE_VALUES = {"1", "true", "yes", "on", "si", "sí"}
DEFAULT_MAX_TOKENS = 200_000
DEFAULT_TIMEOUT_SECONDS = 300

# Motor de máxima calidad que "entra al quite" cuando el resto falla.
_SAFETY_NET_ENGINE = "Claude Foundry"

# Cadenas de motores por tarea (usan los labels de config.LLM_ENGINES). El
# motor de red de seguridad (opus/Claude Foundry) se garantiza al final.
#   - redaccion / prosa académica -> Claude Foundry (juicio) -> GPT-Pro
#   - codigo LaTeX / estructura    -> Codex -> GPT-Pro -> Claude Foundry
#   - razonamiento / analisis      -> Codex -> Claude Foundry -> GPT-Pro
#   - revision / correccion        -> GPT-Pro -> Claude Foundry -> Codex
#   - rapido / borradores          -> Auto (model-router) -> Claude Foundry
#   - matematicas                  -> Mistral-Matematicas -> GPT-Pro
#   - exploracion / ideacion       -> Grok-Pensamiento-Libre -> Claude Foundry
_TASK_ENGINE_CHAINS: dict[str, list[str]] = {
    # Claude Opus DZ solo tiene 13 TPM: va tras Foundry como alivio puntual del 429.
    "redaccion": ["Claude Foundry", "Claude Opus DZ", "GPT-Pro", "Codex"],
    "codigo": ["Codex", "GPT-Pro", "Claude Foundry"],
    "razonamiento": ["Codex", "Claude Foundry", "Claude Opus DZ", "GPT-Pro"],
    "revision": ["GPT-Pro", "Claude Foundry", "Claude Sonnet 4.5", "Codex"],
    "rapido": ["Auto (model-router)", "Claude Foundry"],
    "matematicas": ["Mistral-Matematicas", "Mistral-Medium-DZ", "GPT-Pro", "Codex"],
    "exploracion": ["Grok-Pensamiento-Libre", "Claude Foundry", "GPT-Pro"],
    # Las replicas -DZ usan cuota DataZone independiente: absorben el 429 de la
    # cuota GlobalStandard, que esta saturada para los tres GPT-5.6.
    "volumen": ["GPT-5.6-SOL-DZ", "GPT-5.6-Luna-DZ", "GPT-5.6-Terra-DZ", "Auto (model-router)"],
    "default": ["Codex", "Claude Foundry", "GPT-Pro"],
}


def engine_chain_for_task(task: str | None, forced_engine: str | None = None) -> list[str]:
    """Cadena de motores a intentar para una tarea.

    Cuando ``AULATEX_MODEL_ROUTER_ONLY=1`` no se permite ningún fallback a otro
    deployment: los reintentos de transporte siguen disponibles sobre el router.
    """
    import os as _os

    if model_router_only_enabled():
        return [MODEL_ROUTER_ENGINE]

    base = list(_TASK_ENGINE_CHAINS.get((task or "default"), _TASK_ENGINE_CHAINS["default"]))
    if _SAFETY_NET_ENGINE not in base:
        base.append(_SAFETY_NET_ENGINE)
    override = (_os.getenv("AULATEX_LLM_ENGINE", "") or "").strip()
    forced = forced_engine or (override if override.lower() not in ("", "auto") else "")
    if forced:
        norm = normalize_llm_engine_label(forced)
        base = [norm] + [e for e in base if e != norm]
    return base
_MIN_MAX_TOKENS = 16
_THEORETICAL_LIMITS = {
    "gpt-5.4-pro": {"input": 922_000, "output": 128_000},
    "model-router": {"input": 1_015_808, "output": 32_768},
    "gpt-5.3-codex": {"input": 272_000, "output": 128_000},
    "claude-opus-4-8": {"input": 1_000_000, "output": 128_000},
    "mistral-matematicas": {"input": 126_976, "output": 4_096},
    "grok-pensamiento-libre": {"input": 256_000, "output": 32_768},
}


@dataclass(frozen=True)
class LLMCallResult:
    engine: str
    ok: bool
    text: str
    error: str = ""


@dataclass(frozen=True)
class AulaTeXLLMConfig:
    engine_label: str
    base_url: str
    api_key: str
    deployment: str
    api_version: str = "2023-06-01"
    timeout_seconds: int = 900
    max_tokens: int = DEFAULT_MAX_TOKENS
    temperature: float = 0.0

    @classmethod
    def from_env(cls, engine_label: str | None = None) -> "AulaTeXLLMConfig | None":
        load_aulatex_env()

        enabled = _env("AULATEX_LLM_VALIDATION_ENABLED", _env("TB_BOOKS_LLM_VALIDATION_ENABLED", "1")).lower()
        if enabled in _FALSE_VALUES:
            return None

        selected_engine = normalize_llm_engine_label(
            engine_label or _env("AULATEX_LLM_REVIEW_ENGINE", _env("TB_BOOKS_LLM_REVIEW_ENGINE", "Codex"))
        )
        prefix = ENGINE_ENV_PREFIX[selected_engine]

        base_url = _env(f"{prefix}_BASE_URL")
        api_key = _env(f"{prefix}_API_KEY")
        deployment = _env(f"{prefix}_CHAT_DEPLOYMENT")
        api_version = _env(f"{prefix}_API_VERSION", "2023-06-01")
        # Sonnet/Haiku comparten endpoint y clave con Claude Foundry (Anthropic);
        # solo aportan su propio *_DEPLOYMENT. Heredan base_url/api_key.
        if prefix in ("ANTHROPIC_SONNET", "ANTHROPIC_HAIKU", "ANTHROPIC_OPUS_DZ", "ANTHROPIC_SONNET_45"):
            base_url = base_url or _env("ANTHROPIC_FOUNDRY_BASE_URL")
            api_key = api_key or _env("ANTHROPIC_FOUNDRY_API_KEY")
            deployment = deployment or _env(f"{prefix}_DEPLOYMENT")
            api_version = _env(f"{prefix}_API_VERSION", _env("ANTHROPIC_FOUNDRY_API_VERSION", "2023-06-01"))
        timeout_seconds = _env_int(
            "AULATEX_LLM_TIMEOUT_SECONDS",
            _env_int("AULATEX_LLM_VALIDATION_TIMEOUT", _env_int("TB_BOOKS_LLM_VALIDATION_TIMEOUT", DEFAULT_TIMEOUT_SECONDS)),
        )
        max_tokens = _env_int(
            "AULATEX_LLM_MAX_TOKENS",
            _env_int("AULATEX_LLM_VALIDATION_MAX_TOKENS", _env_int("TB_BOOKS_LLM_VALIDATION_MAX_TOKENS", DEFAULT_MAX_TOKENS)),
        )
        temperature = _env_float(
            "AULATEX_LLM_VALIDATION_TEMPERATURE",
            _env_float("TB_BOOKS_LLM_VALIDATION_TEMPERATURE", 0.0),
        )

        if not (base_url and usable_secret(api_key) and deployment):
            return None

        return cls(
            engine_label=selected_engine,
            base_url=base_url.rstrip("/"),
            api_key=api_key,
            deployment=deployment,
            api_version=api_version,
            timeout_seconds=max(5, timeout_seconds),
            max_tokens=_normalize_requested_max_tokens(max_tokens),
            temperature=max(0.0, temperature),
        )

    def is_anthropic(self) -> bool:
        parsed = urlsplit(self.base_url)
        return (
            self.engine_label in ("Claude Foundry", "Claude Sonnet", "Claude Haiku")
            or "/anthropic" in parsed.path.lower()
        )


class AulaTeXLLMClient:
    """Direct AulaTeX LLM client backed by scripts/aulatex.env."""

    def __init__(self, env_path: str | Path | None = None) -> None:
        self.env_load = load_aulatex_env(env_path)

    @property
    def env_path(self) -> Path:
        return self.env_load.path

    def engines(self) -> tuple[str, ...]:
        return LLM_ENGINES

    def check(self, engine: str, timeout_seconds: int = 10) -> LLMCallResult:
        return check_llm_connection(engine, timeout_seconds=timeout_seconds)

    def call(self, engine: str, prompt: str, *, max_tokens: int = DEFAULT_MAX_TOKENS, timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS) -> LLMCallResult:
        selected = normalize_llm_engine_label(engine)
        last_exc: Exception | None = None
        for candidate_max_tokens in _max_token_attempts(max_tokens):
            try:
                text = call_llm_text(selected, prompt, max_tokens=candidate_max_tokens, timeout_seconds=timeout_seconds)
                if text.strip():
                    return LLMCallResult(selected, True, text)
                last_exc = RuntimeError(f"{selected} devolvió una respuesta vacía.")
            except Exception as exc:
                last_exc = exc
                if not _should_retry_with_lower_max_tokens(exc):
                    break
        return LLMCallResult(selected, False, "", _friendly_error(last_exc or RuntimeError("Fallo desconocido.")))

    def call_with_safety_net(
        self,
        prompt: str,
        *,
        task: str | None = None,
        engine: str | None = None,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        on_event: Callable[[str], None] | None = None,
    ) -> LLMCallResult:
        """Llama al LLM con routing por tarea y RED DE SEGURIDAD opus.

        Recorre una cadena de motores según la tarea (o el motor forzado); si
        todos fallan, Claude Foundry (opus) entra al quite como último recurso.
        """
        chain = engine_chain_for_task(task, forced_engine=engine)
        errors: list[str] = []
        for candidate in chain:
            result = self.call(candidate, prompt, max_tokens=max_tokens, timeout_seconds=timeout_seconds)
            if result.ok and result.text.strip():
                if candidate == _SAFETY_NET_ENGINE and errors and on_event:
                    on_event(f"Rescate {candidate} para la tarea '{task or 'default'}'.")
                return result
            errors.append(f"{candidate}: {result.error or 'respuesta vacía'}")
        return LLMCallResult(
            chain[-1] if chain else "Codex", False, "",
            "Ningún motor resolvió la tarea. " + " | ".join(errors[-3:]),
        )

    def call_image(
        self,
        engine: str,
        prompt: str,
        *,
        image_bytes: bytes,
        media_type: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> LLMCallResult:
        selected = normalize_llm_engine_label(engine)
        last_exc: Exception | None = None
        for candidate_max_tokens in _max_token_attempts(max_tokens):
            try:
                text = call_llm_multimodal(
                    selected,
                    prompt,
                    image_bytes=image_bytes,
                    media_type=media_type,
                    max_tokens=candidate_max_tokens,
                    timeout_seconds=timeout_seconds,
                )
                return LLMCallResult(selected, True, text)
            except Exception as exc:
                last_exc = exc
                if not _should_retry_with_lower_max_tokens(exc):
                    break
        return LLMCallResult(selected, False, "", _friendly_error(last_exc or RuntimeError("Fallo desconocido.")))

    def cycle(
        self,
        prompts: list[str],
        engines: list[str] | tuple[str, ...] | None = None,
        *,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    ) -> list[LLMCallResult]:
        engine_list = [engine for engine in list(engines or self.engines()) if engine in LLM_ENGINES]
        if not engine_list:
            engine_list = ["Codex"]
        results: list[LLMCallResult] = []
        for index, prompt in enumerate(prompts):
            engine = engine_list[index % len(engine_list)]
            results.append(self.call(engine, prompt, max_tokens=max_tokens, timeout_seconds=timeout_seconds))
        return results


def normalize_llm_engine_label(engine_label: str | None) -> str:
    selected = (engine_label or "Codex").strip() or "Codex"
    if selected not in ENGINE_ENV_PREFIX:
        return "Codex"
    return selected


def check_llm_connection(
    engine_label: str,
    *,
    timeout_seconds: int = 10,
    post_func: Callable[..., Any] | None = None,
) -> LLMCallResult:
    selected = normalize_llm_engine_label(engine_label)
    config = AulaTeXLLMConfig.from_env(selected)
    if config is None:
        return LLMCallResult(selected, False, "", "Configuracion incompleta o validacion LLM deshabilitada.")

    try:
        requests_mod = _require_requests()
    except RuntimeError as exc:
        return LLMCallResult(selected, False, "", _friendly_error(exc))

    post = post_func or requests_mod.post
    timeout = max(3, min(timeout_seconds, config.timeout_seconds))
    try:
        if config.is_anthropic():
            response = post(
                _anthropic_messages_endpoint(config),
                headers=_anthropic_headers(config),
                json=_anthropic_payload(config, "Respond with OK.", 8),
                timeout=timeout,
            )
        else:
            endpoint = _openai_compatible_endpoint(config)
            response = post(
                endpoint,
                headers=_api_key_headers(config),
                json=_openai_payload(endpoint, config, "Respond with OK.", 8, temperature=0),
                timeout=timeout,
            )
        response.raise_for_status()
    except requests_mod.Timeout:
        return LLMCallResult(selected, False, "", "Tiempo de espera agotado.")
    except requests_mod.HTTPError as exc:
        response = exc.response
        status_code = response.status_code if response is not None else "desconocido"
        return LLMCallResult(selected, False, "", f"HTTP {status_code}.")
    except requests_mod.RequestException as exc:
        return LLMCallResult(selected, False, "", f"Error de red: {type(exc).__name__}.")
    except Exception as exc:
        return LLMCallResult(selected, False, "", _friendly_error(exc))

    return LLMCallResult(selected, True, "Conexion verificada.")


def validate_llm_response(
    engine_label: str = MODEL_ROUTER_ENGINE,
    *,
    config: AulaTeXLLMConfig | None = None,
    timeout_seconds: int = 45,
    max_tokens: int = 32,
) -> dict[str, Any]:
    """Prueba funcional acotada, sin fallback, redirecciones ni datos sensibles.

    Una configuración candidata se valida en memoria: no se vuelve a cargar el
    .env ni se reutilizan los reintentos/límites de las tareas de generación.
    """
    selected = normalize_llm_engine_label(engine_label)
    marker = "AULATEX_VALIDACION_OK"
    started = time.perf_counter()
    payload: dict[str, Any] = {
        "engine": selected, "ok": False, "responded": False,
        "marker_found": False, "response_chars": 0, "latency_ms": 0, "error": "",
    }
    try:
        candidate = config if config is not None else AulaTeXLLMConfig.from_env(selected)
        if candidate is None or not (
            candidate.base_url and usable_secret(candidate.api_key) and candidate.deployment
        ):
            payload["error"] = "Configuración incompleta, API key sin descifrar o validación deshabilitada."
            return payload
        endpoint = (
            _anthropic_messages_endpoint(candidate) if candidate.is_anthropic()
            else _openai_compatible_endpoint(candidate)
        )
        parsed = urlsplit(endpoint)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
            payload["error"] = "Se requiere un endpoint HTTPS sin credenciales incrustadas ni fragmentos."
            return payload
        requests_mod = _require_requests()
        prompt = f"Responde exactamente con {marker} y no agregues ningún otro texto."
        limit = max(16, min(int(max_tokens), 128))
        headers = _anthropic_headers(candidate) if candidate.is_anthropic() else _api_key_headers(candidate)
        body = (
            _anthropic_payload(candidate, prompt, limit) if candidate.is_anthropic()
            else _openai_payload(endpoint, candidate, prompt, limit, temperature=0)
        )
        response = requests_mod.post(
            endpoint, headers=headers, json=body,
            timeout=max(5, int(timeout_seconds)), allow_redirects=False,
        )
        if not 200 <= response.status_code < 300:
            payload["error"] = f"HTTP {response.status_code}. Revisa endpoint, API key, deployment o cuota."
            return payload
        text = extract_llm_text(response.json()).strip()
        payload.update(
            responded=bool(text), response_chars=len(text),
            marker_found=text == marker, ok=text == marker,
            error="" if text == marker else "El LLM no devolvió el marcador de validación esperado.",
        )
    except Exception as exc:
        # No usar _friendly_error aquí: una excepción puede contener la URL,
        # cabeceras, API key o cuerpo devuelto por el proveedor.
        if _requests is not None and isinstance(exc, _requests.Timeout):
            payload["error"] = "Tiempo de espera agotado."
        elif _requests is not None and isinstance(exc, _requests.RequestException):
            payload["error"] = "No se pudo conectar con el proveedor; revisa la red y el endpoint."
        else:
            payload["error"] = "No se pudo validar la configuración o interpretar la respuesta del proveedor."
    finally:
        payload["latency_ms"] = round((time.perf_counter() - started) * 1000)
    return payload


def call_llm_text(
    engine_label: str,
    prompt: str,
    *,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    selected = normalize_llm_engine_label(engine_label)
    config = AulaTeXLLMConfig.from_env(selected)
    if config is None:
        raise RuntimeError(f"Configuracion LLM incompleta para {selected}")
    requests_mod = _require_requests()

    theoretical = _theoretical_limits_for(config)
    _raise_if_prompt_exceeds_theoretical_limit(prompt, theoretical)
    max_output = _normalize_requested_max_tokens(max_tokens)
    max_output = _cap_output_to_theoretical_limit(max_output, theoretical)
    timeout = _normalize_timeout(timeout_seconds, max_output, config.timeout_seconds)
    if config.is_anthropic():
        response = requests_mod.post(
            _anthropic_messages_endpoint(config),
            headers=_anthropic_headers(config),
            json=_anthropic_payload(config, prompt, max_output),
            timeout=timeout,
        )
    else:
        endpoint = _openai_compatible_endpoint(config)
        response = requests_mod.post(
            endpoint,
            headers=_api_key_headers(config),
            json=_openai_payload(endpoint, config, prompt, max_output, temperature=config.temperature),
            timeout=timeout,
        )
    response.raise_for_status()
    return extract_llm_text(response.json())


def call_llm_multimodal(
    engine_label: str,
    prompt: str,
    *,
    image_bytes: bytes,
    media_type: str,
    max_tokens: int = DEFAULT_MAX_TOKENS,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> str:
    if not image_bytes:
        raise ValueError("image_bytes no puede estar vacio")

    selected = normalize_llm_engine_label(engine_label)
    config = AulaTeXLLMConfig.from_env(selected)
    if config is None:
        raise RuntimeError(f"Configuracion LLM incompleta para {selected}")
    requests_mod = _require_requests()

    theoretical = _theoretical_limits_for(config)
    _raise_if_prompt_exceeds_theoretical_limit(prompt, theoretical)
    max_output = _normalize_requested_max_tokens(max_tokens)
    max_output = _cap_output_to_theoretical_limit(max_output, theoretical)
    timeout = _normalize_timeout(timeout_seconds, max_output, config.timeout_seconds)
    encoded = base64.b64encode(image_bytes).decode("ascii")

    if config.is_anthropic():
        response = requests_mod.post(
            _anthropic_messages_endpoint(config),
            headers=_anthropic_headers(config),
            json={
                "model": config.deployment,
                "max_tokens": max_output,
                "stream": False,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image", "source": {"type": "base64", "media_type": media_type, "data": encoded}},
                        ],
                    }
                ],
            },
            timeout=timeout,
        )
    else:
        endpoint = _openai_compatible_endpoint(config)
        data_url = f"data:{media_type};base64,{encoded}"
        response = requests_mod.post(
            endpoint,
            headers=_api_key_headers(config),
            json=_openai_multimodal_payload(endpoint, config, prompt, data_url, max_output),
            timeout=timeout,
        )
    response.raise_for_status()
    return extract_llm_text(response.json())


def extract_llm_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text.strip()

    choices = payload.get("choices", [])
    if isinstance(choices, list):
        parts: list[str] = []
        for choice in choices:
            if not isinstance(choice, dict):
                continue
            message = choice.get("message", {})
            if not isinstance(message, dict):
                continue
            content = message.get("content", "")
            if isinstance(content, str):
                parts.append(content)
            elif isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and isinstance(item.get("text"), str):
                        parts.append(item["text"])
        if parts:
            return "".join(parts).strip()

    output = payload.get("output", [])
    if isinstance(output, list):
        parts = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content", [])
            if isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict) and isinstance(content_item.get("text"), str):
                        parts.append(content_item["text"])
        if parts:
            return "".join(parts).strip()

    content = payload.get("content", [])
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        if parts:
            return "".join(parts).strip()
    return ""


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip().strip('"').strip("'")


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _api_key_headers(config: AulaTeXLLMConfig) -> dict[str, str]:
    parsed = urlsplit(config.base_url)
    headers = {"Content-Type": "application/json"}
    if "azure.com" in parsed.netloc.lower():
        headers["api-key"] = config.api_key
    else:
        headers["Authorization"] = f"Bearer {config.api_key}"
    return headers


def _anthropic_headers(config: AulaTeXLLMConfig) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-api-key": config.api_key,
        "anthropic-version": config.api_version,
    }


def _openai_compatible_endpoint(config: AulaTeXLLMConfig) -> str:
    parsed = urlsplit(config.base_url)
    if "/chat/completions" in parsed.path or "/responses" in parsed.path:
        return config.base_url
    return (
        f"{config.base_url.rstrip('/')}/openai/deployments/"
        f"{config.deployment}/chat/completions?api-version={config.api_version}"
    )


def _anthropic_messages_endpoint(config: AulaTeXLLMConfig) -> str:
    base_url = config.base_url.rstrip("/")
    if base_url.endswith("/v1/messages"):
        return base_url
    return f"{base_url}/v1/messages"


def _anthropic_payload(config: AulaTeXLLMConfig, prompt: str, max_tokens: int) -> dict[str, object]:
    return {
        "model": config.deployment,
        "max_tokens": max_tokens,
        "stream": False,
        "messages": [{"role": "user", "content": prompt}],
    }


def _openai_payload(
    endpoint: str,
    config: AulaTeXLLMConfig,
    prompt: str,
    max_tokens: int,
    *,
    temperature: float,
) -> dict[str, object]:
    if "/responses" in urlsplit(endpoint).path:
        return {
            "model": config.deployment,
            "input": prompt,
            "max_output_tokens": max(16, max_tokens),
        }
    return {
        "model": config.deployment,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }


def _openai_multimodal_payload(
    endpoint: str,
    config: AulaTeXLLMConfig,
    prompt: str,
    data_url: str,
    max_tokens: int,
) -> dict[str, object]:
    if "/responses" in urlsplit(endpoint).path:
        return {
            "model": config.deployment,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": data_url},
                    ],
                }
            ],
            "max_output_tokens": max_tokens,
        }
    return {
        "model": config.deployment,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        "max_tokens": max_tokens,
        "temperature": config.temperature,
    }


def _friendly_error(exc: Exception) -> str:
    if isinstance(exc, RuntimeError) and str(exc):
        return str(exc)
    if _requests is not None and isinstance(exc, _requests.HTTPError):
        response = exc.response
        status_code = response.status_code if response is not None else "desconocido"
        return f"HTTP {status_code}."
    if _requests is not None and isinstance(exc, _requests.Timeout):
        return "Tiempo de espera agotado."
    if _requests is not None and isinstance(exc, _requests.RequestException):
        return f"Error de red: {type(exc).__name__}."
    return f"{type(exc).__name__}: {exc}"


def _normalize_requested_max_tokens(max_tokens: int) -> int:
    return max(_MIN_MAX_TOKENS, min(DEFAULT_MAX_TOKENS, int(max_tokens)))


def _theoretical_limits_enabled() -> bool:
    return _env("AULATEX_ENFORCE_THEORETICAL_LIMITS", "1").lower() in _TRUE_VALUES


def _theoretical_limits_for(config: AulaTeXLLMConfig) -> dict[str, int]:
    deployment = config.deployment.strip()
    return _THEORETICAL_LIMITS.get(deployment, {}) if _theoretical_limits_enabled() else {}


def _cap_output_to_theoretical_limit(max_output: int, limits: dict[str, int]) -> int:
    output_limit = int(limits.get("output", 0) or 0)
    if output_limit <= 0:
        return max_output
    return max(_MIN_MAX_TOKENS, min(max_output, output_limit))


def _raise_if_prompt_exceeds_theoretical_limit(prompt: str, limits: dict[str, int]) -> None:
    input_limit = int(limits.get("input", 0) or 0)
    if input_limit <= 0:
        return
    estimated_tokens = max(1, (len(prompt) + 3) // 4)
    if estimated_tokens > input_limit:
        raise RuntimeError(
            f"El prompt excede el limite teorico de entrada del deployment ({estimated_tokens} estimados > {input_limit}). "
            "Divide el contexto o usa un deployment con mayor ventana."
        )


def _normalize_timeout(requested_timeout_seconds: int, max_tokens: int, config_timeout_seconds: int) -> int:
    suggested_timeout = min(900, max(60, 60 + max_tokens // 500))
    return max(5, min(max(int(requested_timeout_seconds), suggested_timeout), int(config_timeout_seconds)))


def _max_token_attempts(max_tokens: int) -> list[int]:
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


def _should_retry_with_lower_max_tokens(exc: Exception) -> bool:
    if _requests is not None and isinstance(exc, _requests.Timeout):
        return True
    if _requests is None or not isinstance(exc, _requests.HTTPError):
        return False
    response = exc.response
    if response is None or response.status_code != 400:
        return False
    text = ""
    try:
        text = response.text.lower()
    except Exception:
        text = ""
    retry_markers = (
        "max_tokens",
        "max_output_tokens",
        "maximum context length",
        "token",
        "too many",
        "invalid_request_error",
    )
    return any(marker in text for marker in retry_markers) or not text


def _require_requests() -> Any:
    if _requests is None:
        raise RuntimeError("Dependencia faltante: instala requests en .venv para habilitar llamadas LLM.")
    return _requests
