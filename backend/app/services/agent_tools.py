from decimal import Decimal, InvalidOperation

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


CALCULATE_TOTAL_AMOUNT_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_total_amount",
        "description": (
            "Add monetary amounts exactly. Use this only when every amount "
            "comes from the user's message or from verified DIT knowledge. "
            "Never invent or estimate missing fees."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "amounts": {
                    "type": "array",
                    "items": {
                        "type": "number"
                    },
                    "minItems": 1,
                    "description": (
                        "The verified monetary amounts to add together."
                    ),
                },
                "currency": {
                    "type": "string",
                    "description": (
                        "Currency label such as TZS or USD."
                    ),
                    "default": "TZS",
                },
                "description": {
                    "type": "string",
                    "description": (
                        "Short description of what is being totalled."
                    ),
                    "default": "",
                },
            },
            "required": ["amounts"],
            "additionalProperties": False,
        },
    },
}


CHECK_ADMISSION_ELIGIBILITY_TOOL = {
    "type": "function",
    "function": {
        "name": "check_admission_eligibility",
        "description": (
            "Perform a deterministic preliminary comparison between one "
            "applicant numeric value and one verified DIT admission requirement. "
            "Use this only AFTER search_dit_knowledge has returned the relevant "
            "official requirement. This tool does not make a final admission "
            "decision and must not be used with guessed requirements."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "applicant_value": {
                    "type": "number",
                    "description": (
                        "The applicant's numeric value, for example GPA, points, "
                        "number of passes or another numeric admission criterion."
                    ),
                },
                "required_value": {
                    "type": "number",
                    "description": (
                        "The numeric requirement retrieved from verified DIT "
                        "knowledge."
                    ),
                },
                "comparison": {
                    "type": "string",
                    "enum": [
                        "gte",
                        "gt",
                        "lte",
                        "lt",
                        "eq",
                    ],
                    "description": (
                        "How the applicant value must compare with the verified "
                        "requirement: gte, gt, lte, lt or eq."
                    ),
                },
                "criterion": {
                    "type": "string",
                    "description": (
                        "Human-readable criterion, such as Ordinary Diploma GPA "
                        "or ACSEE points."
                    ),
                },
                "unit": {
                    "type": "string",
                    "description": (
                        "Optional unit or scale label, such as GPA, points or passes."
                    ),
                    "default": "",
                },
                "programme": {
                    "type": "string",
                    "description": (
                        "Optional programme or admission route being checked."
                    ),
                    "default": "",
                },
            },
            "required": [
                "applicant_value",
                "required_value",
                "comparison",
                "criterion",
            ],
            "additionalProperties": False,
        },
    },
}


AGENT_TOOLS = [
    SEARCH_DIT_KNOWLEDGE_TOOL,
    CALCULATE_TOTAL_AMOUNT_TOOL,
    CHECK_ADMISSION_ELIGIBILITY_TOOL,
]


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


def calculate_total_amount(
    amounts: list[float],
    currency: str = "TZS",
    description: str = "",
) -> dict:
    """Add verified monetary amounts without using floating-point math."""

    if not amounts:
        return {
            "found": False,
            "context": "No monetary amounts were provided for calculation.",
            "sources": [],
        }

    decimal_amounts = []

    try:
        for amount in amounts:
            value = Decimal(str(amount))

            if not value.is_finite():
                raise InvalidOperation

            if value < 0:
                return {
                    "found": False,
                    "context": (
                        "Negative monetary amounts are not accepted by this "
                        "fee calculator."
                    ),
                    "sources": [],
                }

            decimal_amounts.append(value)

    except (InvalidOperation, ValueError, TypeError):
        return {
            "found": False,
            "context": "One or more monetary amounts were invalid.",
            "sources": [],
        }

    total = sum(
        decimal_amounts,
        Decimal("0"),
    )

    clean_currency = (
        currency.strip().upper()
        if currency and currency.strip()
        else "TZS"
    )

    label = (
        description.strip()
        if description
        else "requested amounts"
    )

    formatted_total = format(total, ",.2f")

    return {
        "found": True,
        "context": (
            f"Exact calculated total for {label}: "
            f"{clean_currency} {formatted_total}."
        ),
        "sources": [],
        "calculation": {
            "amounts": [
                str(value)
                for value in decimal_amounts
            ],
            "currency": clean_currency,
            "total": str(total),
        },
    }


def check_admission_eligibility(
    applicant_value: float,
    required_value: float,
    comparison: str,
    criterion: str,
    unit: str = "",
    programme: str = "",
) -> dict:
    """
    Compare one applicant numeric value against one verified requirement.

    This is intentionally a preliminary criterion check, not a final
    admission decision. Other programme-specific requirements may apply.
    """

    try:
        applicant = Decimal(
            str(applicant_value)
        )
        required = Decimal(
            str(required_value)
        )

        if (
            not applicant.is_finite()
            or not required.is_finite()
        ):
            raise InvalidOperation

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        return {
            "found": False,
            "context": (
                "The applicant value or verified requirement was invalid."
            ),
            "sources": [],
        }

    if applicant < 0 or required < 0:
        return {
            "found": False,
            "context": (
                "Admission comparison values cannot be negative."
            ),
            "sources": [],
        }

    comparisons = {
        "gte": lambda left, right: left >= right,
        "gt": lambda left, right: left > right,
        "lte": lambda left, right: left <= right,
        "lt": lambda left, right: left < right,
        "eq": lambda left, right: left == right,
    }

    comparator = comparisons.get(
        comparison
    )

    if comparator is None:
        return {
            "found": False,
            "context": (
                "Unsupported admission comparison. Use gte, gt, lte, lt or eq."
            ),
            "sources": [],
        }

    meets_requirement = comparator(
        applicant,
        required,
    )

    clean_criterion = (
        criterion.strip()
        if criterion and criterion.strip()
        else "admission criterion"
    )

    clean_unit = (
        unit.strip()
        if unit
        else ""
    )

    clean_programme = (
        programme.strip()
        if programme
        else ""
    )

    unit_suffix = (
        f" {clean_unit}"
        if clean_unit
        else ""
    )

    programme_text = (
        f" for {clean_programme}"
        if clean_programme
        else ""
    )

    status = (
        "MEETS"
        if meets_requirement
        else "DOES NOT MEET"
    )

    return {
        "found": True,
        "context": (
            f"Preliminary numeric admission check{programme_text}: "
            f"{clean_criterion}. Applicant value: {applicant}{unit_suffix}. "
            f"Verified requirement: {comparison} {required}{unit_suffix}. "
            f"Result: {status} this numeric criterion. This is not a final "
            "admission decision; other DIT requirements may still apply."
        ),
        "sources": [],
        "eligibility": {
            "criterion": clean_criterion,
            "programme": clean_programme,
            "applicant_value": str(applicant),
            "required_value": str(required),
            "comparison": comparison,
            "unit": clean_unit,
            "meets_requirement": meets_requirement,
            "final_admission_decision": False,
        },
    }


TOOL_HANDLERS = {
    "search_dit_knowledge": search_dit_knowledge,
    "calculate_total_amount": calculate_total_amount,
    "check_admission_eligibility": check_admission_eligibility,
}
