from sentence_transformers import SentenceTransformer


MODEL_NAME = (
    "sentence-transformers/"
    "paraphrase-multilingual-MiniLM-L12-v2"
)

model = SentenceTransformer(MODEL_NAME)


def embed_documents(texts: list[str]) -> list[list[float]]:
    embeddings = model.encode_document(
        texts,
        normalize_embeddings=True,
    )

    return embeddings.tolist()


def embed_query(text: str) -> list[float]:
    embedding = model.encode_query(
        text,
        normalize_embeddings=True,
    )

    return embedding.tolist()