from __future__ import annotations


PROGRAMME_ALIASES = {
    "leather product technology": "Leather Products Technology",
    "leather products technology": "Leather Products Technology",
    "leather processing technology": "Leather Processing Technology",
    "science laboratory technology": "Science and Laboratory Technology",
    "science and laboratory technology": "Science and Laboratory Technology",
    "agro bio process technology": "Agro Bio Processing Technology",
    "agro bio processing technology": "Agro Bio Processing Technology",
    "agro post harvest technology": "Agro Post Harvest Technology",
    "fashion design technology": "Fashion and Design Technology",
    "fashion and design technology": "Fashion and Design Technology",
    "footwear leather goods": "Footwear and Leather Goods",
    "footwear and leather goods": "Footwear and Leather Goods",
}


PROGRAMME_INTENT_TERMS = (
    "programme",
    "programmes",
    "program",
    "programs",
    "course",
    "courses",
    "degree",
    "diploma",
    "certificate",
    "bachelor",
    "master",
    "engineering",
    "technology",
)


CAMPUS_ALIASES = {
    "mwanza": "Mwanza",
    "songwe": "Songwe",
    "dodoma": "Dodoma",
    "dar es salaam": "Dar es Salaam",
    "main campus": "Dar es Salaam",
}


def _normalize_space(value: str) -> str:
    return " ".join(
        str(value or "").strip().split()
    )


def canonical_programme_query(query: str) -> str:
    """Normalize known programme-name variants without changing user intent."""

    clean_query = _normalize_space(query)
    lower_query = clean_query.casefold()

    for alias, canonical in PROGRAMME_ALIASES.items():
        if alias in lower_query:
            start = lower_query.index(alias)
            end = start + len(alias)
            return (
                clean_query[:start]
                + canonical
                + clean_query[end:]
            )

    return clean_query


def looks_like_programme_query(query: str) -> bool:
    lower_query = _normalize_space(query).casefold()

    if any(
        alias in lower_query
        for alias in PROGRAMME_ALIASES
    ):
        return True

    return any(
        term in lower_query
        for term in PROGRAMME_INTENT_TERMS
    )


def detect_campus_hint(query: str) -> str | None:
    lower_query = _normalize_space(query).casefold()

    for alias, campus in CAMPUS_ALIASES.items():
        if alias in lower_query:
            return campus

    return None


def enrich_categories(
    query: str,
    categories: list[str] | None,
) -> list[str]:
    """Add metadata categories implied by programme/campus wording."""

    enriched = list(categories or [])

    if looks_like_programme_query(query):
        enriched.append("programme")

    if detect_campus_hint(query):
        enriched.append("campus")

    return list(dict.fromkeys(enriched))


def expand_dit_search_queries(query: str) -> list[str]:
    """Build a small deterministic set of retrieval queries for DIT facts."""

    clean_query = _normalize_space(query)

    if not clean_query:
        return []

    canonical_query = canonical_programme_query(
        clean_query
    )

    queries = [
        clean_query,
    ]

    if canonical_query != clean_query:
        queries.append(canonical_query)

    if looks_like_programme_query(canonical_query):
        queries.append(
            f"{canonical_query} DIT programme campus availability official"
        )

        campus = detect_campus_hint(canonical_query)

        if campus:
            queries.append(
                f"{canonical_query} DIT {campus} Campus programme offered"
            )

    return list(dict.fromkeys(queries))[:4]
