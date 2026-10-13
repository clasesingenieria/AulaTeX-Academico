from __future__ import annotations

from dataclasses import dataclass
import json
import os
import re
from typing import Any, Iterable

from .env_config import load_env


@dataclass(frozen=True)
class ApiConfig:
    provider: str
    api_key: str
    base_url: str | None
    embedding_model: str
    chat_model: str | None = None


def normalize_azure_base_url(value: str) -> str:
    base = value.strip()
    if not base:
        raise ValueError("AZURE_OPENAI_BASE_URL/AZURE_OPENAI_ENDPOINT está vacío.")

    # Quita query string o fragmentos si el usuario pegó una URL operacional completa.
    base = base.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    lowered = base.lower()

    if "/api/projects/" in lowered:
        raise ValueError(
            "El endpoint configurado parece ser un endpoint de proyecto de Azure AI Foundry ('/api/projects/...'). "
            "Ese formato no es el adecuado para este extractor cuando usa el SDK OpenAI para embeddings. "
            "Usa un endpoint base tipo 'https://<recurso>.openai.azure.com/openai/v1/' o "
            "'https://<recurso>.services.ai.azure.com/openai/v1/'."
        )

    # Si el usuario pegó una URL de operación, reducirla al base_url esperado.
    operation_suffixes = (
        "/chat/completions",
        "/responses",
        "/embeddings",
        "/completions",
    )
    for suffix in operation_suffixes:
        if lowered.endswith(suffix):
            base = base[: -len(suffix)]
            lowered = base.lower()
            break

    if base.endswith("/openai/v1"):
        return base + "/"
    if base.endswith("/openai"):
        return base + "/v1/"
    if lowered.endswith("/openai/v1/"):
        return base + ("" if base.endswith("/") else "/")
    return base + "/openai/v1/"


def normalize_anthropic_base_url(value: str) -> str:
    base = value.strip()
    if not base:
        raise ValueError("ANTHROPIC_FOUNDRY_BASE_URL/ANTHROPIC_FOUNDRY_ENDPOINT está vacío.")
    base = base.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    lowered = base.lower()
    if lowered.endswith("/v1/messages"):
        base = base[: -len("/v1/messages")]
        lowered = base.lower()
    if lowered.endswith("/anthropic"):
        return base + "/"
    return base + "/anthropic/"


def get_api_config(
    provider: str,
    *,
    azure_base_url: str | None = None,
    azure_api_key: str | None = None,
    azure_embedding_deployment: str | None = None,
    azure_chat_deployment: str | None = None,
    anthropic_base_url: str | None = None,
    anthropic_api_key: str | None = None,
    anthropic_chat_deployment: str | None = None,
    openai_api_key: str | None = None,
    openai_embedding_model: str | None = None,
    openai_chat_model: str | None = None,
) -> ApiConfig:
    load_env()
    provider = provider.lower().strip()
    if provider == "azure":
        raw_base = azure_base_url or os.getenv("AZURE_OPENAI_BASE_URL") or os.getenv("AZURE_OPENAI_ENDPOINT") or os.getenv("OPENAI_BASE_URL")
        key = azure_api_key or os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        emb = azure_embedding_deployment or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
        chat = azure_chat_deployment or os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
        if not raw_base:
            raise RuntimeError("Falta AZURE_OPENAI_BASE_URL o AZURE_OPENAI_ENDPOINT en .env.")
        if not key:
            raise RuntimeError("Falta AZURE_OPENAI_API_KEY en .env.")
        if not emb:
            raise RuntimeError("Falta AZURE_OPENAI_EMBEDDING_DEPLOYMENT en .env.")
        return ApiConfig(provider="azure", api_key=key, base_url=normalize_azure_base_url(raw_base), embedding_model=emb, chat_model=chat)

    if provider == "anthropicfoundry":
        raw_base = anthropic_base_url or os.getenv("ANTHROPIC_FOUNDRY_BASE_URL") or os.getenv("ANTHROPIC_FOUNDRY_ENDPOINT")
        key = anthropic_api_key or os.getenv("ANTHROPIC_FOUNDRY_API_KEY")
        chat = anthropic_chat_deployment or os.getenv("ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT")
        if not raw_base:
            raise RuntimeError("Falta ANTHROPIC_FOUNDRY_BASE_URL o ANTHROPIC_FOUNDRY_ENDPOINT en .env.")
        if not key:
            raise RuntimeError("Falta ANTHROPIC_FOUNDRY_API_KEY en .env.")
        if not chat:
            raise RuntimeError("Falta ANTHROPIC_FOUNDRY_CHAT_DEPLOYMENT en .env.")
        return ApiConfig(provider="anthropicfoundry", api_key=key, base_url=normalize_anthropic_base_url(raw_base), embedding_model="", chat_model=chat)

    if provider == "openai":
        key = openai_api_key or os.getenv("OPENAI_API_KEY")
        emb = openai_embedding_model or os.getenv("OPENAI_EMBEDDING_MODEL") or "text-embedding-3-small"
        chat = openai_chat_model or os.getenv("OPENAI_CHAT_MODEL")
        if not key:
            raise RuntimeError("Falta OPENAI_API_KEY en .env.")
        return ApiConfig(provider="openai", api_key=key, base_url=os.getenv("OPENAI_BASE_URL") or None, embedding_model=emb, chat_model=chat)

    raise ValueError(f"Proveedor no soportado: {provider}")


def create_client(config: ApiConfig) -> Any:
    if config.provider == "anthropicfoundry":
        try:
            from anthropic import AnthropicFoundry  # type: ignore
        except ImportError as exc:
            raise RuntimeError("Falta anthropic. Ejecuta: pip install -r requirements-anthropic.txt") from exc
        return AnthropicFoundry(api_key=config.api_key, base_url=config.base_url)

    try:
        from openai import OpenAI  # type: ignore
    except ImportError as exc:
        raise RuntimeError("Falta openai. Ejecuta: pip install -r requirements-azure.txt") from exc
    kwargs: dict[str, Any] = {"api_key": config.api_key}
    if config.base_url:
        kwargs["base_url"] = config.base_url
    return OpenAI(**kwargs)


def extract_text_from_chat_response(response: Any, provider: str) -> str:
    if provider == "anthropicfoundry":
        parts: list[str] = []
        for block in getattr(response, "content", []) or []:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "\n".join(parts).strip()
    return (response.choices[0].message.content or "").strip()


def batch_iter(items: list[str], batch_size: int) -> Iterable[list[str]]:
    batch_size = max(1, int(batch_size))
    for i in range(0, len(items), batch_size):
        yield items[i:i + batch_size]


def embed_texts(client: Any, model: str, texts: list[str], batch_size: int = 64) -> list[list[float]]:
    if not model:
        raise RuntimeError("El proveedor configurado no soporta embeddings en este extractor.")
    vectors: list[list[float]] = []
    for batch in batch_iter(texts, batch_size=batch_size):
        response = client.embeddings.create(model=model, input=batch)
        ordered = sorted(response.data, key=lambda item: item.index)
        vectors.extend([list(item.embedding) for item in ordered])
    return vectors


def chat_json_data(client: Any, config: ApiConfig, system: str, user: str) -> Any:
    if config.provider == "anthropicfoundry":
        response = client.messages.create(
            model=config.chat_model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=4096,
        )
    else:
        response = client.chat.completions.create(
            model=config.chat_model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0,
        )

    content = extract_text_from_chat_response(response, config.provider)
    fence = re.search(r"```(?:json)?\s*(.*?)```", content, flags=re.S | re.I)
    if fence:
        content = fence.group(1).strip()

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        obj_match = re.search(r"\{.*\}", content, flags=re.S)
        list_match = re.search(r"\[.*\]", content, flags=re.S)
        for match in (obj_match, list_match):
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return {"_raw": content}


def chat_json_list(client: Any, config: ApiConfig, system: str, user: str, max_items: int) -> list[str]:
    data = chat_json_data(client, config, system, user)
    if isinstance(data, dict) and "_raw" in data:
        content = str(data.get("_raw", ""))
        data = [line.strip(" -•\t") for line in content.splitlines() if line.strip()]
    if not isinstance(data, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in data:
        if not isinstance(item, str):
            continue
        text = " ".join(item.strip().split())
        if not text:
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(text)
        if len(out) >= max_items:
            break
    return out
