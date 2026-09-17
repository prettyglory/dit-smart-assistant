from pathlib import Path

import chromadb

from app.services.embedding_service import (
    embed_documents,
    embed_query,
)


BACKEND_DIR = Path(__file__).resolve().parents[2]

CHROMA_PATH = BACKEND_DIR / "chroma_db"

COLLECTION_NAME = "dit_knowledge"


client = chromadb.PersistentClient(
    path=str(CHROMA_PATH)
)


def get_collection():
    return client.get_or_create_collection(
        name=COLLECTION_NAME
    )


def reset_collection():
    try:
        client.delete_collection(
            name=COLLECTION_NAME
        )
    except Exception:
        pass

    return get_collection()


def upsert_chunks(
    documents: list[str],
    metadatas: list[dict],
    ids: list[str],
):
    if not documents:
        return

    embeddings = embed_documents(documents)

    collection = get_collection()

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )


def search_knowledge(
    question: str,
    n_results: int = 4,
) -> list[dict]:

    collection = get_collection()

    count = collection.count()

    if count == 0:
        return []

    number_of_results = min(
        n_results,
        count,
    )

    query_embedding = embed_query(question)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=number_of_results,
        include=[
            "documents",
            "metadatas",
            "distances",
        ],
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    matches = []

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances,
    ):
        matches.append(
            {
                "document": document,
                "metadata": metadata,
                "distance": distance,
            }
        )

    return matches