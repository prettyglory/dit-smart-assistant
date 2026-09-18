from app.services.groq_service import ask_groq
from app.services.vector_store import search_knowledge


def is_follow_up(question: str) -> bool:
    """
    Decide whether the current question depends
    on previous conversation context.
    """

    q = question.lower().strip()

    follow_up_starters = [
        "what about",
        "how about",
        "and ",
        "what of",
        "na ",
        "vipi",
        "je ",
        "then ",
        "also ",
    ]

    if any(
        q.startswith(starter)
        for starter in follow_up_starters
    ):
        return True

    # Very short questions are often follow-ups.
    if len(q.split()) <= 4:
        ambiguous_words = [
            "diploma",
            "bachelor",
            "master",
            "mwanza",
            "songwe",
            "dodoma",
            "fees",
            "fee",
            "hostel",
            "admission",
        ]

        if any(
            word in q
            for word in ambiguous_words
        ):
            return True

    return False


def get_last_user_question(
    history: list[dict],
) -> str:
    """
    Return the most recent user question.
    """

    for message in reversed(history):

        if message.get("role") != "user":
            continue

        content = message.get(
            "content",
            "",
        ).strip()

        if content:
            return content

    return ""


def build_retrieval_query(
    question: str,
    history: list[dict],
) -> str:
    """
    Use previous conversation only when the
    current question is genuinely a follow-up.

    This prevents an old topic such as fees
    from contaminating a new programme or
    campus question.
    """

    if not is_follow_up(question):
        return question

    previous_question = (
        get_last_user_question(
            history
        )
    )

    if not previous_question:
        return question

    q = question.lower().strip()
    previous = previous_question.lower()

    # -------------------------------------------------
    # Fee follow-ups
    # -------------------------------------------------

    fee_words = [
        "fee",
        "fees",
        "tuition",
        "cost",
        "payment",
        "ada",
        "gharama",
        "malipo",
    ]

    previous_is_fee_question = any(
        word in previous
        for word in fee_words
    )

    if previous_is_fee_question:

        if "diploma" in q:
            return (
                "DIT Ordinary Diploma tuition fees "
                "and fee structure"
            )

        if "bachelor" in q:
            return (
                "DIT Bachelor degree tuition fees "
                "and fee structure"
            )

        if "master" in q:
            return (
                "DIT Master degree tuition fees "
                "and fee structure"
            )

        if "hostel" in q:
            return (
                "DIT hostel accommodation fees "
                "and charges"
            )

    # -------------------------------------------------
    # Programme follow-ups
    # -------------------------------------------------

    programme_words = [
        "programme",
        "program",
        "programmes",
        "programs",
        "course",
        "courses",
    ]

    previous_is_programme_question = any(
        word in previous
        for word in programme_words
    )

    if previous_is_programme_question:

        if "mwanza" in q:
            return (
                "programmes offered at "
                "DIT Mwanza Campus"
            )

        if "songwe" in q:
            return (
                "programmes offered at "
                "DIT Songwe Campus"
            )

        if "dodoma" in q:
            return (
                "programmes offered at "
                "DIT Dodoma Campus"
            )

        if (
            "dar" in q
            or "main campus" in q
        ):
            return (
                "programmes offered at "
                "DIT Main Campus Dar es Salaam"
            )

    # -------------------------------------------------
    # Admission follow-ups
    # -------------------------------------------------

    admission_words = [
        "admission",
        "requirement",
        "requirements",
        "joining",
        "join",
        "qualification",
        "qualify",
        "gpa",
        "grade",
        "pass mark",
        "passmark",
        "sifa",
        "kujiunga",
    ]

    previous_is_admission_question = any(
        word in previous
        for word in admission_words
    )

    if previous_is_admission_question:

        if "diploma" in q:
            return (
                "DIT Ordinary Diploma admission "
                "requirements minimum CSEE passes "
                "and minimum grades"
            )

        if "bachelor" in q:
            return (
                "DIT Bachelor degree admission "
                "requirements Ordinary Diploma GPA "
                "and ACSEE direct entry"
            )

        if "gpa" in q:
            return (
                "DIT minimum GPA required for "
                "Bachelor degree admission"
            )

        if (
            "grade" in q
            or "pass" in q
        ):
            return (
                "DIT Ordinary Diploma minimum "
                "CSEE passes grades and admission "
                "requirements"
            )

    # -------------------------------------------------
    # Generic follow-up
    # -------------------------------------------------

    return (
        f"Previous question: {previous_question}\n"
        f"Follow-up question: {question}"
    )


def format_conversation_history(
    history: list[dict],
) -> str:
    """
    Format recent chat messages for Groq.
    """

    lines = []

    for message in history[-6:]:

        role = message.get(
            "role",
            "",
        )

        content = message.get(
            "content",
            "",
        ).strip()

        if not content:
            continue

        if role == "user":
            label = "Student"

        elif role == "assistant":
            label = "DIT Assistant"

        else:
            continue

        lines.append(
            f"{label}: {content}"
        )

    return "\n".join(lines)


def detect_categories(
    question: str,
) -> list[str]:
    """
    Detect the most appropriate DIT knowledge
    category for the retrieval query.
    """

    q = question.lower()

    categories = []

    # -------------------------------------------------
    # Fees
    # -------------------------------------------------

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
        categories.append(
            "fees"
        )

    # -------------------------------------------------
    # Academic calendar
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Accommodation
    # -------------------------------------------------

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

    # -------------------------------------------------
    # IPT
    # -------------------------------------------------

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
        categories.append(
            "ipt"
        )

    # -------------------------------------------------
    # Student regulations
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Admissions
    # -------------------------------------------------

    admission_keywords = [
        "admission",
        "admissions",
        "admission requirement",
        "admission requirements",
        "entry requirement",
        "entry requirements",
        "joining dit",
        "join dit",
        "joining requirements",
        "requirements for joining",
        "requirements to join",
        "how to join",
        "apply to dit",
        "application",
        "minimum gpa",
        "minimum grade",
        "pass mark",
        "passmark",
        "qualification",
        "qualifications",
        "qualify",
        "eligible",
        "eligibility",
        "kujiunga dit",
        "kujiunga na dit",
        "sifa za kujiunga",
        "vigezo vya kujiunga",
        "gpa ya kujiunga",
        "grade ya kujiunga",
    ]

    if any(
        keyword in q
        for keyword in admission_keywords
    ):
        categories.append(
            "admission"
        )

    # -------------------------------------------------
    # Programmes
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Campuses
    # -------------------------------------------------

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

    # -------------------------------------------------
    # Priority categories
    # -------------------------------------------------

    # Fee questions should search only fee documents.
    if "fees" in categories:
        return ["fees"]

    # Calendar questions should search Almanac only.
    if "academic_calendar" in categories:
        return [
            "academic_calendar"
        ]

    # Accommodation questions should use policy docs.
    if "accommodation" in categories:
        return [
            "accommodation"
        ]

    # IPT questions should search IPT knowledge.
    if "ipt" in categories:
        return ["ipt"]

    # Regulations questions should use regulations.
    if "student_regulations" in categories:
        return [
            "student_regulations"
        ]

    # IMPORTANT:
    # Admission questions take priority over general
    # programme searches. This ensures questions such
    # as "requirements for joining DIT" retrieve the
    # admission requirements rather than programme or
    # prospectus information.
    if "admission" in categories:
        return ["admission"]

    return list(
        dict.fromkeys(categories)
    )


def answer_with_rag(
    question: str,
    history: list[dict] | None = None,
):
    """
    Retrieve relevant verified DIT knowledge and
    generate a grounded response using Groq.
    """

    history = history or []

    retrieval_query = (
        build_retrieval_query(
            question=question,
            history=history,
        )
    )

    conversation_history = (
        format_conversation_history(
            history
        )
    )

    # Detect categories from the rewritten retrieval
    # query, not the full old conversation.
    categories = detect_categories(
        retrieval_query
    )

    matches = search_knowledge(
        question=retrieval_query,
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
        conversation_history=(
            conversation_history
        ),
    )

    return answer, sources