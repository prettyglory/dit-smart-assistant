from pathlib import Path

import chromadb

from app.services.embedding_service import (
    embed_documents,
    embed_query,
)


BACKEND_DIR = Path(__file__).resolve().parents[2]

CHROMA_PATH = BACKEND_DIR / "chroma_db"

COLLECTION_NAME = "dit_knowledge"


# Smaller cosine distance = more relevant.
#
# General searches use a stricter threshold.
# Category-filtered searches can use a slightly
# wider threshold because we already know that
# the document belongs to the correct category.
MAX_COSINE_DISTANCE = 0.45

FILTERED_MAX_COSINE_DISTANCE = 0.65


client = chromadb.PersistentClient(
    path=str(CHROMA_PATH)
)


def get_collection():
    """
    Return the DIT knowledge collection.

    Cosine distance is used because our sentence
    embeddings are normalized.
    """
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        configuration={
            "hnsw": {
                "space": "cosine"
            }
        },
    )


def reset_collection():
    """
    Delete the existing collection and recreate it.

    This is used whenever the knowledge base
    is re-ingested.
    """
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
    """
    Generate embeddings for knowledge chunks
    and store them in ChromaDB.
    """

    if not documents:
        return

    embeddings = embed_documents(
        documents
    )

    collection = get_collection()

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )


def search_knowledge(
    question: str,
    n_results: int = 6,
    categories: list[str] | None = None,
) -> list[dict]:
    """
    Search the DIT knowledge base.

    If categories are provided, ChromaDB searches
    only documents belonging to those categories.

    Examples:

        categories=["fees"]

        categories=["academic_calendar"]

        categories=["programme", "admission"]
    """

    collection = get_collection()

    count = collection.count()

    if count == 0:
        return []

    query_embedding = embed_query(
        question
    )

    # -----------------------------------------
    # Build metadata filter
    # -----------------------------------------

    where_filter = None

    if categories:

        # Remove duplicate categories
        categories = list(
            dict.fromkeys(categories)
        )

        if len(categories) == 1:
            where_filter = {
                "category": categories[0]
            }

        else:
            where_filter = {
                "category": {
                    "$in": categories
                }
            }

    # -----------------------------------------
    # Build Chroma query
    # -----------------------------------------

    query_kwargs = {
        "query_embeddings": [
            query_embedding
        ],
        "n_results": min(
            n_results,
            count,
        ),
        "include": [
            "documents",
            "metadatas",
            "distances",
        ],
    }

    if where_filter is not None:
        query_kwargs["where"] = (
            where_filter
        )

    try:
        results = collection.query(
            **query_kwargs
        )

    except Exception as error:
        print(
            f"Vector search error: {error}"
        )
        return []

    # -----------------------------------------
    # Validate results
    # -----------------------------------------

    if (
        not results.get("documents")
        or not results["documents"][0]
    ):
        return []

    documents = results[
        "documents"
    ][0]

    metadatas = results[
        "metadatas"
    ][0]

    distances = results[
        "distances"
    ][0]

    matches = []

    # Category-filtered searches are already
    # restricted to the correct document type,
    # so we allow a slightly larger distance.
    if categories:
        max_distance = (
            FILTERED_MAX_COSINE_DISTANCE
        )
    else:
        max_distance = (
            MAX_COSINE_DISTANCE
        )

    # -----------------------------------------
    # Filter irrelevant results
    # -----------------------------------------

    for (
        document,
        metadata,
        distance,
    ) in zip(
        documents,
        metadatas,
        distances,
    ):

        if distance > max_distance:
            continue

        matches.append(
            {
                "document": document,
                "metadata": metadata,
                "distance": distance,
            }
        )

    return matches