from app.services.groq_service import ask_groq
from app.services.vector_store import search_knowledge


def detect_categories(
    question: str,
) -> list[str]:
    """
    Detect the most relevant knowledge category
    from the user's question.
    """

    q = question.lower()

    categories = []

    # -----------------------------
    # Fees
    # -----------------------------
    fee_keywords = [
        "fee",
        "fees",
        "tuition",
        "cost",
        "payment",
        "ada",
        "gharama",
        "malipo",
    ]

    if any(
        keyword in q
        for keyword in fee_keywords
    ):
        categories.append("fees")

    # -----------------------------
    # Academic calendar / Almanac
    # -----------------------------
    calendar_keywords = [
        "almanac",
        "academic calendar",
        "academic year",
        "semester",
        "registration date",
        "registration week",
        "examination period",
        "exam period",
        "semester start",
        "semester end",
        "academic year start",
        "academic year end",
        "mwaka wa masomo",
        "semester inaanza",
        "semester inaisha",
        "tarehe ya usajili",
        "mitihani inaanza",
    ]

    if any(
        keyword in q
        for keyword in calendar_keywords
    ):
        categories.append(
            "academic_calendar"
        )

    # -----------------------------
    # Accommodation
    # -----------------------------
    accommodation_keywords = [
        "hostel",
        "accommodation",
        "dormitory",
        "room",
        "malazi",
        "hosteli",
    ]

    if any(
        keyword in q
        for keyword in accommodation_keywords
    ):
        categories.append(
            "accommodation"
        )

    # -----------------------------
    # IPT
    # -----------------------------
    ipt_keywords = [
        "ipt",
        "industrial practical",
        "industrial practical training",
        "industrial training",
        "field training",
        "practical training",
    ]

    if any(
        keyword in q
        for keyword in ipt_keywords
    ):
        categories.append("ipt")

    # -----------------------------
    # Student regulations
    # -----------------------------
    regulation_keywords = [
        "ethics",
        "conduct",
        "code of conduct",
        "dress code",
        "discipline",
        "disciplinary",
        "student regulation",
        "student regulations",
        "student rules",
        "academic integrity",
        "misconduct",
    ]

    if any(
        keyword in q
        for keyword in regulation_keywords
    ):
        categories.append(
            "student_regulations"
        )

    # -----------------------------
    # Admissions
    # -----------------------------
    admission_keywords = [
        "admission",
        "admissions",
        "apply",
        "application",
        "entry requirement",
        "entry requirements",
        "admission requirement",
        "admission requirements",
        "minimum gpa",
        "qualification",
        "qualify",
        "eligible",
        "eligibility",
        "kuomba",
        "sifa za kujiunga",
        "vigezo vya kujiunga",
    ]

    if any(
        keyword in q
        for keyword in admission_keywords
    ):
        categories.append(
            "admission"
        )

    # -----------------------------
    # Programmes
    # -----------------------------
    programme_keywords = [
        "programme",
        "programmes",
        "program",
        "programs",
        "course",
        "courses",
        "degree",
        "diploma",
        "bachelor",
        "master",
        "computer engineering",
        "civil engineering",
        "electrical engineering",
        "mechanical engineering",
    ]

    if any(
        keyword in q
        for keyword in programme_keywords
    ):
        categories.append(
            "programme"
        )

    # -----------------------------
    # Campus
    # -----------------------------
    campus_keywords = [
        "campus",
        "campuses",
        "mwanza",
        "songwe",
        "dodoma",
        "dar es salaam",
        "main campus",
    ]

    if any(
        keyword in q
        for keyword in campus_keywords
    ):
        categories.append(
            "campus"
        )

    # -----------------------------
    # Priority categories
    # -----------------------------
    # If the question is clearly about fees,
    # search only fee documents.
    if "fees" in categories:
        return ["fees"]

    # Calendar questions should search only
    # academic calendar documents.
    if "academic_calendar" in categories:
        return [
            "academic_calendar"
        ]

    # Accommodation questions should prefer
    # accommodation policy only.
    if "accommodation" in categories:
        return [
            "accommodation"
        ]

    # IPT questions should prefer IPT docs.
    if "ipt" in categories:
        return ["ipt"]

    # Regulations questions should prefer
    # student regulations.
    if "student_regulations" in categories:
        return [
            "student_regulations"
        ]

    return list(
        dict.fromkeys(categories)
    )


def answer_with_rag(
    question: str,
):
    """
    Retrieve relevant DIT information and
    send it to Groq to generate the answer.
    """

    categories = detect_categories(
        question
    )

    matches = search_knowledge(
        question=question,
        n_results=8,
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

        distance = match.get(
            "distance"
        )

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

        page_value = metadata.get(
            "page"
        )

        if (
            isinstance(
                page_value,
                int,
            )
            and page_value > 0
        ):
            page = page_value
        else:
            page = None

        context_header = (
            f"SOURCE {index}\n"
            f"Title: {source_title}\n"
            f"Category: {category}\n"
            f"Campus: {campus}"
        )

        if page is not None:
            context_header += (
                f"\nPage: {page}"
            )

        if distance is not None:
            context_header += (
                f"\nRetrieval distance: "
                f"{distance:.4f}"
            )

        context_parts.append(
            f"""
{context_header}

Content:
{document}
""".strip()
        )

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