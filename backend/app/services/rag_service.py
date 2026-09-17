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

        page_value = metadata.get(
            "page"
        )

        # TXT documents use page 0.
        # Only real PDF page numbers should be displayed.
        if (
            isinstance(page_value, int)
            and page_value > 0
        ):
            page = page_value
        else:
            page = None

        context_header = (
            f"SOURCE {index}\n"
            f"Title: {source_title}\n"
            f"Campus: {campus}"
        )

        if page is not None:
            context_header += (
                f"\nPage: {page}"
            )

        context_parts.append(
            f"""
{context_header}

Content:
{document}
""".strip()
        )

        # Different PDF pages can now appear
        # as separate citations.
        unique_key = (
            source_title,
            source_url,
            page,
        )

        if unique_key not in seen_sources:

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

    context = "\n\n".join(
        context_parts
    )

    answer = ask_groq(
        question=question,
        context=context,
    )

    return answer, sources