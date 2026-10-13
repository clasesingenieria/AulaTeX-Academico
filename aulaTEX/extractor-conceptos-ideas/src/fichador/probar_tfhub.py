from __future__ import annotations

from .tfhub_search import DEFAULT_TFHUB_MODEL


def main() -> None:
    try:
        from sentence_transformers import SentenceTransformer  # type: ignore
    except ImportError as exc:
        raise SystemExit("Falta sentence-transformers. Ejecuta: pip install -r requirements-tfhub.txt") from exc
    print("Cargando modelo de sentence-transformers. La primera vez puede tardar por descarga...")
    model = SentenceTransformer(DEFAULT_TFHUB_MODEL)
    vectors = model.encode(["evaluación formativa", "planeación didáctica"], normalize_embeddings=True)
    print("El motor de embeddings funciona correctamente.")
    print(f"Modelo: {DEFAULT_TFHUB_MODEL}")
    print(f"Forma de embeddings: {vectors.shape}")


if __name__ == "__main__":
    main()
