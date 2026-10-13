from __future__ import annotations

from dataclasses import dataclass

try:
    import tiktoken
except ModuleNotFoundError:  # pragma: no cover - dependencia opcional
    tiktoken = None

from .llm_bridge import AulaTeXLLMConfig, normalize_llm_engine_label


@dataclass(frozen=True)
class TokenCountResult:
    engine: str
    deployment: str
    token_count: int
    tokenizer_source: str
    tokenizer_name: str
    approximate: bool
    note: str = ""


_TOKENIZER_PROFILES: dict[str, dict[str, object]] = {
    "Codex": {
        "source": "tiktoken",
        "name": "o200k_base",
        "approximate": False,
        "note": "Conteo local para la familia GPT en Azure/OpenAI.",
    },
    "GPT-Pro": {
        "source": "tiktoken",
        "name": "o200k_base",
        "approximate": False,
        "note": "Conteo local para la familia GPT en Azure/OpenAI.",
    },
    "Auto (model-router)": {
        "source": "tiktoken",
        "name": "o200k_base",
        "approximate": True,
        "note": "El router puede seleccionar modelos distintos; el conteo usa un tokenizer OpenAI como aproximación operativa.",
    },
    "Claude Foundry": {
        "source": "tiktoken",
        "name": "o200k_base",
        "approximate": True,
        "note": "No hay un tokenizer local de Anthropic configurado en el repo; se usa o200k_base como aproximación estable.",
    },
}


def count_text_tokens(engine_label: str, text: str) -> TokenCountResult:
    selected = normalize_llm_engine_label(engine_label)
    profile = _TOKENIZER_PROFILES.get(selected, _TOKENIZER_PROFILES["Codex"])
    config = AulaTeXLLMConfig.from_env(selected)
    deployment = config.deployment if config is not None else ""

    if tiktoken is None:
        return TokenCountResult(
            engine=selected,
            deployment=deployment,
            token_count=max(0, (len(text) + 3) // 4),
            tokenizer_source="fallback",
            tokenizer_name="chars_div_4",
            approximate=True,
            note="tiktoken no está instalado; se usó el fallback de 4 caracteres por token.",
        )

    encoding_name = str(profile["name"])
    encoding = tiktoken.get_encoding(encoding_name)
    token_count = len(encoding.encode(text, disallowed_special=()))
    return TokenCountResult(
        engine=selected,
        deployment=deployment,
        token_count=token_count,
        tokenizer_source=str(profile["source"]),
        tokenizer_name=encoding_name,
        approximate=bool(profile["approximate"]),
        note=str(profile["note"]),
    )