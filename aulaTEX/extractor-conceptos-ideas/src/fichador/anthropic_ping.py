from __future__ import annotations

from .api_client import get_api_config, create_client


def main() -> None:
    config = get_api_config("anthropicfoundry")
    client = create_client(config)
    message = client.messages.create(
        model=config.chat_model,
        messages=[{"role": "user", "content": "What is the capital of France?"}],
        max_tokens=128,
    )
    parts: list[str] = []
    for block in getattr(message, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    print("Conexión correcta con Anthropic Foundry.")
    print(f"Base URL: {config.base_url}")
    print(f"Deployment chat: {config.chat_model}")
    if parts:
        print("Respuesta de prueba:")
        print("\n".join(parts))


if __name__ == "__main__":
    main()
