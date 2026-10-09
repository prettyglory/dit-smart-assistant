from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation


STATE_FIELDS = (
    "programme",
    "campus",
    "qualification",
    "gpa",
    "goal",
)


def _clean_text(value: str) -> str:
    return " ".join(value.strip().split())


def _capture_first(patterns: list[str], text: str) -> str:
    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if not match:
            continue

        value = _clean_text(match.group(1))
        value = re.split(
            r"[?!,;]|\b(?:and|na|but|lakini|with|kwa|at|in)\b",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip(" .")

        if value:
            return value

    return ""


def _extract_gpa(text: str) -> str:
    patterns = [
        r"\bgpa\s*(?:is|ni|ya|=|:|of)?\s*([0-5](?:\.\d{1,2})?)\b",
        r"\b(?:i have|nina)\s+(?:a\s+)?gpa\s*(?:of)?\s*([0-5](?:\.\d{1,2})?)\b",
    ]

    raw = ""

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            flags=re.IGNORECASE,
        )

        if match:
            raw = match.group(1)
            break

    if not raw:
        return ""

    try:
        value = Decimal(raw)
    except InvalidOperation:
        return ""

    if value < 0 or value > 5:
        return ""

    return format(
        value.normalize(),
        "f",
    )


def _extract_qualification(text: str) -> str:
    patterns = [
        r"\b(?:i have|nina|qualification(?: yangu)?(?: is| ni)?|my qualification is)\s+(?:an?\s+)?((?:ordinary\s+)?diploma(?:\s+in\s+[A-Za-z][A-Za-z &/+-]{2,50})?)",
        r"\b(?:i have|nina|qualification(?: yangu)?(?: is| ni)?|my qualification is)\s+(?:an?\s+)?(certificate(?:\s+in\s+[A-Za-z][A-Za-z &/+-]{2,50})?)",
        r"\b((?:NTA\s+Level\s+[4-8])|(?:A[- ]?Level)|(?:O[- ]?Level)|(?:Form\s+Six)|(?:Form\s+Four))\b",
    ]

    return _capture_first(
        patterns,
        text,
    )


def _extract_programme(text: str) -> str:
    patterns = [
        r"\b(?:programme|program|programu)\s+(?:ya\s+|of\s+|in\s+)?([A-Za-z][A-Za-z0-9 &/+-]{2,70})",
        r"\b(?:bachelor|degree)\s+(?:of|in)\s+([A-Za-z][A-Za-z0-9 &/+-]{2,70})",
        r"\b(?:tell me about|information about|nataka kujua kuhusu|niambie kuhusu|kuhusu)\s+([A-Za-z][A-Za-z0-9 &/+-]{2,70})",
        r"\b(?:i want to study|i want to apply for|nataka kusoma|nataka kuapply)\s+([A-Za-z][A-Za-z0-9 &/+-]{2,70})",
    ]

    value = _capture_first(
        patterns,
        text,
    )

    ignored = {
        "dit",
        "dar es salaam institute of technology",
        "fees",
        "admission",
        "admissions",
        "requirements",
    }

    if value.lower() in ignored:
        return ""

    return value


def _extract_campus(text: str) -> str:
    after_label = re.search(
        r"\b(?:campus|kampasi)\s+(?:ya\s+)?([A-Za-z][A-Za-z' -]{1,40})",
        text,
        flags=re.IGNORECASE,
    )

    if after_label:
        value = _clean_text(
            after_label.group(1)
        )
        value = re.split(
            r"[.?!,;]|\b(?:and|na|but|lakini|with|kwa)\b",
            value,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0].strip()

        if value:
            return value

    before_label = re.search(
        r"\b([A-Za-z][A-Za-z' -]{1,40})\s+(?:campus|kampasi)\b",
        text,
        flags=re.IGNORECASE,
    )

    if not before_label:
        return ""

    value = _clean_text(
        before_label.group(1)
    )

    # A greedy phrase such as "interested in Mwanza campus" should retain
    # only the explicit location after the final preposition.
    parts = re.split(
        r"\b(?:in|at|kwenye|ya)\b",
        value,
        flags=re.IGNORECASE,
    )
    value = parts[-1].strip(" .")

    return value


def _extract_goal(text: str) -> str:
    lower = text.lower()

    goal_patterns = [
        (
            "admission eligibility",
            (
                "do i qualify",
                "am i eligible",
                "naqualify",
                "nina qualify",
                "eligible for",
            ),
        ),
        (
            "application",
            (
                "i want to apply",
                "nataka kuapply",
                "how to apply",
                "application process",
            ),
        ),
        (
            "programme comparison",
            (
                "compare",
                "comparison",
                "tofauti kati",
            ),
        ),
        (
            "fees",
            (
                "fee",
                "fees",
                "tuition",
                "ada",
            ),
        ),
    ]

    for goal, phrases in goal_patterns:
        if any(
            phrase in lower
            for phrase in phrases
        ):
            return goal

    return ""


def extract_student_state_update(
    message: str,
) -> dict:
    """Extract only explicit, user-provided student context from one message.

    The returned values are conversation state, not verified DIT facts. Missing
    fields are omitted so an older value remains available until the user
    explicitly supplies a replacement.
    """

    text = _clean_text(
        str(message or "")
    )

    if not text:
        return {}

    candidates = {
        "programme": _extract_programme(text),
        "campus": _extract_campus(text),
        "qualification": _extract_qualification(text),
        "gpa": _extract_gpa(text),
        "goal": _extract_goal(text),
    }

    return {
        key: value
        for key, value in candidates.items()
        if value
    }


def merge_student_state(
    current: dict | None,
    update: dict | None,
) -> dict:
    """Merge explicit state updates; newer non-empty values win."""

    merged = {
        key: value
        for key, value in (current or {}).items()
        if key in STATE_FIELDS and value not in {None, ""}
    }

    for key, value in (update or {}).items():
        if key not in STATE_FIELDS or value in {None, ""}:
            continue

        merged[key] = value

    return merged


def format_student_state_for_agent(
    state: dict | None,
) -> str:
    """Create model context that clearly distinguishes memory from DIT facts."""

    clean_state = merge_student_state(
        {},
        state,
    )

    if not clean_state:
        return ""

    lines = [
        "CURRENT STUDENT SESSION CONTEXT (user-provided, not verified DIT facts):"
    ]

    labels = {
        "programme": "Programme of interest",
        "campus": "Campus of interest",
        "qualification": "Qualification",
        "gpa": "GPA",
        "goal": "Current goal",
    }

    for key in STATE_FIELDS:
        value = clean_state.get(key)
        if value:
            lines.append(
                f"- {labels[key]}: {value}"
            )

    lines.append(
        "Use this only to resolve conversational references. Re-retrieve all "
        "factual DIT information before answering."
    )

    return "\n".join(lines)
