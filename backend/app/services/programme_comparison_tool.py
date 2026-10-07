from app.services.agent_tools import search_dit_knowledge


PROGRAMME_COMPARISON_TOOL = {
    "type": "function",
    "function": {
        "name": "compare_dit_programmes",
        "description": (
            "Compare two or more DIT programmes using verified DIT knowledge. "
            "Use this for direct programme comparisons involving overview, "
            "campus, admission requirements or fees. The tool performs the "
            "required knowledge searches internally and must not invent missing facts."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "programmes": {
                    "type": "array",
                    "items": {
                        "type": "string"
                    },
                    "minItems": 2,
                    "maxItems": 4,
                    "description": (
                        "DIT programme names to compare. Use the programme names "
                        "given by the user."
                    ),
                },
                "aspects": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": [
                            "overview",
                            "campus",
                            "admission",
                            "fees",
                        ],
                    },
                    "description": (
                        "Comparison aspects. If omitted, compare overview, campus, "
                        "admission and fees."
                    ),
                },
            },
            "required": ["programmes"],
            "additionalProperties": False,
        },
    },
}


SUPPORTED_ASPECTS = (
    "overview",
    "campus",
    "admission",
    "fees",
)


ASPECT_QUERIES = {
    "overview": (
        "{programme} DIT programme details award duration course information"
    ),
    "campus": (
        "{programme} DIT campus where programme is offered"
    ),
    "admission": (
        "{programme} DIT admission requirements entry requirements GPA ACSEE"
    ),
    "fees": (
        "{programme} DIT tuition fees fee structure"
    ),
}


COMPARISON_RESULTS_PER_ASPECT = 3
MAX_ASPECT_CONTEXT_CHARS = 1800
MAX_COMPARISON_CONTEXT_CHARS = 12000
SECTION_OVERHEAD_CHARS = 120


def _normalize_programmes(
    programmes: list[str],
) -> list[str]:
    normalized = []
    seen = set()

    for programme in programmes or []:
        clean_name = str(programme).strip()

        if not clean_name:
            continue

        key = clean_name.casefold()

        if key in seen:
            continue

        seen.add(key)
        normalized.append(clean_name)

    return normalized


def _normalize_aspects(
    aspects: list[str] | None,
) -> list[str]:
    if not aspects:
        return list(SUPPORTED_ASPECTS)

    normalized = []

    for aspect in aspects:
        clean_aspect = str(aspect).strip().lower()

        if (
            clean_aspect in SUPPORTED_ASPECTS
            and clean_aspect not in normalized
        ):
            normalized.append(clean_aspect)

    return normalized


def _truncate_context(
    value: str,
    max_chars: int,
) -> str:
    clean_value = str(value or "").strip()

    if len(clean_value) <= max_chars:
        return clean_value

    marker = "\n[Verified context truncated to stay within the agent context budget.]"
    keep_chars = max(
        0,
        max_chars - len(marker),
    )

    return (
        clean_value[:keep_chars].rstrip()
        + marker
    )


def _aspect_context_budget(
    programme_count: int,
    aspect_count: int,
) -> int:
    section_count = max(
        1,
        programme_count * aspect_count,
    )

    available_per_section = (
        MAX_COMPARISON_CONTEXT_CHARS
        // section_count
        - SECTION_OVERHEAD_CHARS
    )

    return max(
        500,
        min(
            MAX_ASPECT_CONTEXT_CHARS,
            available_per_section,
        ),
    )


def _merge_sources(
    destination: list[dict],
    incoming: list[dict],
) -> None:
    seen = {
        (
            source.get("title", ""),
            source.get("url", ""),
            source.get("page"),
        )
        for source in destination
    }

    for source in incoming:
        key = (
            source.get("title", ""),
            source.get("url", ""),
            source.get("page"),
        )

        if key in seen:
            continue

        seen.add(key)
        destination.append(source)


def compare_dit_programmes(
    programmes: list[str],
    aspects: list[str] | None = None,
) -> dict:
    """
    Retrieve and group verified DIT information for programme comparison.

    The function does not infer missing facts. It returns bounded verified
    context for the model and compact structured metadata so the same long
    retrieved text is not duplicated in the tool payload.
    """

    clean_programmes = _normalize_programmes(
        programmes
    )

    if len(clean_programmes) < 2:
        return {
            "found": False,
            "context": (
                "At least two distinct DIT programme names are required "
                "for a programme comparison."
            ),
            "sources": [],
        }

    if len(clean_programmes) > 4:
        return {
            "found": False,
            "context": (
                "A maximum of four programmes can be compared in one request."
            ),
            "sources": [],
        }

    clean_aspects = _normalize_aspects(
        aspects
    )

    if not clean_aspects:
        return {
            "found": False,
            "context": (
                "No supported comparison aspects were provided. Supported "
                "aspects are overview, campus, admission and fees."
            ),
            "sources": [],
        }

    per_aspect_budget = _aspect_context_budget(
        programme_count=len(clean_programmes),
        aspect_count=len(clean_aspects),
    )

    comparison = {}
    context_sections = []
    sources = []
    found_any = False

    for programme in clean_programmes:
        programme_results = {}

        for aspect in clean_aspects:
            query = ASPECT_QUERIES[
                aspect
            ].format(
                programme=programme
            )

            result = search_dit_knowledge(
                query=query,
                n_results=COMPARISON_RESULTS_PER_ASPECT,
            )

            found = bool(
                result.get(
                    "found",
                    False,
                )
            )
            bounded_context = _truncate_context(
                result.get(
                    "context",
                    "",
                ),
                per_aspect_budget,
            )

            # Keep structured comparison metadata compact. The verified text
            # itself is already supplied once through the top-level context.
            programme_results[
                aspect
            ] = {
                "found": found,
                "query": query,
            }

            if found:
                found_any = True

            _merge_sources(
                sources,
                result.get(
                    "sources",
                    [],
                ),
            )

            context_sections.append(
                (
                    f"PROGRAMME: {programme}\n"
                    f"ASPECT: {aspect}\n"
                    f"VERIFIED RESULT:\n"
                    f"{bounded_context}"
                )
            )

        comparison[
            programme
        ] = programme_results

    if not found_any:
        return {
            "found": False,
            "context": (
                "No sufficiently relevant verified DIT information was found "
                "for the requested programme comparison."
            ),
            "sources": sources,
            "programme_comparison": {
                "programmes": clean_programmes,
                "aspects": clean_aspects,
                "results": comparison,
            },
        }

    combined_context = "\n\n---\n\n".join(
        context_sections
    )

    return {
        "found": True,
        "context": _truncate_context(
            combined_context,
            MAX_COMPARISON_CONTEXT_CHARS,
        ),
        "sources": sources,
        "programme_comparison": {
            "programmes": clean_programmes,
            "aspects": clean_aspects,
            "results": comparison,
        },
    }
