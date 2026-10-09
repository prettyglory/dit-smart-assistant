from __future__ import annotations


ELIGIBILITY_PHRASES = (
    "do i qualify",
    "if i qualify",
    "check if i qualify",
    "whether i qualify",
    "am i eligible",
    "eligible",
    "eligibility",
    "naqualify",
    "nina qualify",
    "kama naqualify",
    "sifa za kujiunga",
)

FEE_PHRASES = (
    "fee",
    "fees",
    "tuition",
    "ada",
    "gharama",
)

TOTAL_PHRASES = (
    "total",
    "sum",
    "altogether",
    "jumla",
)

COMPARISON_PHRASES = (
    "compare",
    "comparison",
    "versus",
    " vs ",
    "tofauti kati",
    "linganisha",
)

APPLICATION_PHRASES = (
    "how to apply",
    "application process",
    "apply for",
    "nataka kuapply",
    "jinsi ya kuapply",
    "jinsi ya kuomba",
)

FACTUAL_HINTS = (
    "dit",
    "programme",
    "program",
    "programu",
    "campus",
    "kampasi",
    "admission",
    "requirement",
    "regulation",
    "accommodation",
    "ipt",
)

CONVERSATIONAL_ONLY = (
    "hello",
    "hi",
    "hey",
    "thanks",
    "thank you",
    "asante",
    "habari",
)


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(
        phrase in text
        for phrase in phrases
    )


def _task(
    task_id: str,
    task_type: str,
    description: str,
    required_tools: list[str],
    depends_on: list[str] | None = None,
    ready: bool = True,
    missing_inputs: list[str] | None = None,
) -> dict:
    return {
        "id": task_id,
        "type": task_type,
        "description": description,
        "required_tools": required_tools,
        "depends_on": depends_on or [],
        "ready": ready,
        "missing_inputs": missing_inputs or [],
    }


def build_request_plan(
    question: str,
    student_state: dict | None = None,
) -> dict:
    """Build a small ordered execution plan for a user request.

    The planner does not invent institutional facts and does not execute tools.
    It only decomposes the request into inspectable tasks so the runtime can
    guide tool selection and enforce important dependencies.
    """

    clean_question = " ".join(
        str(question or "").strip().split()
    )
    lower = f" {clean_question.lower()} "
    state = student_state or {}

    if not clean_question:
        return {
            "kind": "empty",
            "tasks": [],
        }

    stripped = clean_question.lower().strip(" .!?\t\n")
    if stripped in CONVERSATIONAL_ONLY:
        return {
            "kind": "conversation",
            "tasks": [],
        }

    wants_eligibility = (
        _contains_any(lower, ELIGIBILITY_PHRASES)
        or state.get("goal") == "admission eligibility"
    )
    wants_fees = (
        _contains_any(lower, FEE_PHRASES)
        or state.get("goal") == "fees"
    )
    wants_total = _contains_any(
        lower,
        TOTAL_PHRASES,
    )
    wants_comparison = (
        _contains_any(lower, COMPARISON_PHRASES)
        or state.get("goal") == "programme comparison"
    )
    wants_application = (
        _contains_any(lower, APPLICATION_PHRASES)
        or state.get("goal") == "application"
    )

    tasks: list[dict] = []

    if wants_eligibility:
        tasks.append(
            _task(
                task_id="retrieve_admission_requirements",
                task_type="verified_retrieval",
                description=(
                    "Retrieve the official DIT admission requirements relevant "
                    "to the student's programme, qualification and campus context."
                ),
                required_tools=[
                    "search_dit_knowledge"
                ],
            )
        )

        missing_inputs = []
        if not state.get("gpa") and "gpa" not in lower:
            missing_inputs.append(
                "applicant numeric criterion such as GPA or points"
            )

        tasks.append(
            _task(
                task_id="evaluate_admission_eligibility",
                task_type="deterministic_check",
                description=(
                    "Compare the applicant's numeric value with the verified DIT "
                    "requirement. Report only a preliminary criterion result."
                ),
                required_tools=[
                    "check_admission_eligibility"
                ],
                depends_on=[
                    "retrieve_admission_requirements"
                ],
                ready=not missing_inputs,
                missing_inputs=missing_inputs,
            )
        )

    if wants_fees:
        tasks.append(
            _task(
                task_id="retrieve_fees",
                task_type="verified_retrieval",
                description=(
                    "Retrieve verified DIT tuition and fee information for the "
                    "relevant programme and campus."
                ),
                required_tools=[
                    "search_dit_knowledge"
                ],
            )
        )

        if wants_total:
            tasks.append(
                _task(
                    task_id="calculate_fee_total",
                    task_type="deterministic_calculation",
                    description=(
                        "Add only fee amounts supplied by the user or returned by "
                        "verified DIT retrieval."
                    ),
                    required_tools=[
                        "calculate_total_amount"
                    ],
                    depends_on=[
                        "retrieve_fees"
                    ],
                )
            )

    if wants_comparison:
        tasks.append(
            _task(
                task_id="compare_programmes",
                task_type="verified_comparison",
                description=(
                    "Compare the programmes requested by the user using verified "
                    "DIT programme, campus, admission and fee information."
                ),
                required_tools=[
                    "compare_dit_programmes"
                ],
            )
        )

    if wants_application:
        tasks.append(
            _task(
                task_id="retrieve_application_process",
                task_type="verified_retrieval",
                description=(
                    "Retrieve the verified DIT application process and any relevant "
                    "application requirements or instructions."
                ),
                required_tools=[
                    "search_dit_knowledge"
                ],
            )
        )

    if not tasks and _contains_any(
        lower,
        FACTUAL_HINTS,
    ):
        tasks.append(
            _task(
                task_id="retrieve_requested_information",
                task_type="verified_retrieval",
                description=(
                    "Retrieve the verified DIT information needed to answer the "
                    "user's factual request."
                ),
                required_tools=[
                    "search_dit_knowledge"
                ],
            )
        )

    return {
        "kind": (
            "compound"
            if len(tasks) > 1
            else "single"
            if tasks
            else "conversation"
        ),
        "tasks": tasks,
    }


def format_plan_for_agent(
    plan: dict | None,
) -> str:
    tasks = (plan or {}).get(
        "tasks",
        [],
    )

    if not tasks:
        return ""

    lines = [
        "EXECUTION PLAN (runtime-generated; follow dependencies in order):"
    ]

    for index, task in enumerate(
        tasks,
        start=1,
    ):
        tools = ", ".join(
            task.get("required_tools", [])
        ) or "none"
        dependencies = ", ".join(
            task.get("depends_on", [])
        ) or "none"

        line = (
            f"{index}. [{task.get('id', '')}] {task.get('description', '')} "
            f"Required tools: {tools}. Depends on: {dependencies}."
        )

        if not task.get("ready", True):
            missing = ", ".join(
                task.get("missing_inputs", [])
            )
            line += (
                " Do not fabricate missing input; ask the user if it remains "
                f"necessary. Missing: {missing}."
            )

        lines.append(line)

    lines.append(
        "Do not skip a dependency merely to produce a faster answer. Verified "
        "retrieval must precede dependent admission checks or calculations."
    )

    return "\n".join(lines)
