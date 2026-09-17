from app.services.groq_service import ask_groq
from app.services.vector_store import search_knowledge


def answer_with_rag(
    question: str,
):

    matches = search_knowledge(
        question=question,
        n_results=4,
    )

    context_parts = []
    sources = []
    seen_sources = set()

    for index, match in enumerate(
        matches,
        start=1,
    ):

        document = match["document"]
        metadata = match["metadata"]

        context_parts.append(
            f"""
SOURCE {index}
Campus: {metadata.get("campus", "unknown")}
Content:
{document}
""".strip()
        )

        source_url = metadata.get(
            "source_url",
            "",
        )

        source_title = metadata.get(
            "source_title",
            "DIT Source",
        )

        unique_key = (
            source_title,
            source_url,
        )

        if unique_key not in seen_sources:

            seen_sources.add(unique_key)

            sources.append(
                {
                    "title": source_title,
                    "url": source_url,
                    "campus": metadata.get(
                        "campus",
                        "unknown",
                    ),
                }
            )

    context = "\n\n".join(
        context_parts
    )

    answer = ask_groq(
        question=question,
        context=context,
    )

    return answer, sources