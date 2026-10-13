from __future__ import annotations

from .api_client import get_api_config, create_client


def main() -> None:
    config = get_api_config("openai")
    client = create_client(config)
    response = client.embeddings.create(model=config.embedding_model, input=["prueba de conexión con OpenAI"])
    dims = len(response.data[0].embedding)
    print("Conexión correcta con OpenAI.")
    print(f"Modelo embeddings: {config.embedding_model}")
    print(f"Dimensiones del embedding: {dims}")


if __name__ == "__main__":
    main()
