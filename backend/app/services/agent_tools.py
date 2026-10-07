from app.services.rag_service import detect_categories
from app.services.vector_store import search_knowledge


SEARCH_DIT_KNOWLEDGE_TOOL = {
    "type": "function",
    "function": {
        "name": "search_dit_knowledge",
        "description": (
            "Search the verified DIT knowledge base for factual information "
            "about Dar es Salaam Institute of Technology, including programmes, "
            "campuses, admissions, fees, academic calendar, accommodation, "
            "student regulations, IPT and student services."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": (
                        "A focused search query describing the DIT information "
                        "needed to answer the user's request."
                    ),
                }
            },
            "required": ["query"],
            "additionalProperties": False,
        },
    },
}


def _normalize_page(value):
    if isinstance(value, int) and value > 0:
        return value

    return None


def search_dit_knowledge(
    query: str,
    n_results: int = 8,
) -> dict:
    """
    Search the verified DIT vector knowledge base.

    The function returns both model-facing context and source metadata
    that can be displayed by the API/UI.
    """

    clean_query = query.strip()

    if not clean_query:
        return {
            "query": "",
            "found": False,
            "context": (
                "No search query was provided, so no verified DIT "
                "information could be retrieved."
            ),
            "sources": [],
        }

    categories = detect_categories(
        clean_query
    )

    matches = search_knowledge(
        question=clean_query,
        n_results=n_results,
        categories=(
            categories
            if categories
            else None
        ),
    )

    context_parts = []
    sources = []
    seen_sources = set()

    for index, match in enumerate(
        matches,
        start=1,
    ):
        document = match[
            "document"
        ]

        metadata = match[
            "metadata"
        ]

        source_title = metadata.get(
            "source_title",
            "DIT Source",
        )

        source_url = metadata.get(
            "source_url",
            "",
        )

        campus = metadata.get(
            "campus",
            "unknown",
        )

        category = metadata.get(
            "category",
            "general",
        )

        page = _normalize_page(
            metadata.get("page")
        )

        header = [
            f"VERIFIED DIT SOURCE {index}",
            f"Title: {source_title}",
            f"Category: {category}",
            f"Campus: {campus}",
        ]

        if page is not None:
            header.append(
                f"Page: {page}"
            )

        context_parts.append(
            "\n".join(header)
            + "\n\nContent:\n"
            + document
        )

        unique_key = (
            source_title,
            source_url,
            page,
        )

        if unique_key in seen_sources:
            continue

        seen_sources.add(
            unique_key
        )

        sources.append(
            {
                "title": source_title,
                "url": source_url,
                "campus": campus,
                "page": page,
            }
        )

    if not context_parts:
        return {
            "query": clean_query,
            "found": False,
            "context": (
                "No sufficiently relevant information was found in the "
                "verified DIT knowledge base for this search."
            ),
            "sources": [],
        }

    return {
        "query": clean_query,
        "found": True,
        "context": "\n\n".join(
            context_parts
        ),
        "sources": sources,
    }
