import json

from groq import Groq

from app.config import GROQ_API_KEY
from app.services.agent_tools import (
    AGENT_TOOLS,
    TOOL_HANDLERS,
)
from app.services.programme_comparison_tool import (
    PROGRAMME_COMPARISON_TOOL,
    compare_dit_programmes,
)
from app.services.rate_limit_retry import (
    run_with_rate_limit_retry,
)
from app.services.student_state import (
    format_student_state_for_agent,
)
from app.services.task_planner import (
    build_request_plan,
    format_plan_for_agent,
)


MODEL = "openai/gpt-oss-120b"
MAX_AGENT_ITERATIONS = 7
MAX_AGENT_HISTORY_MESSAGES = 10


client = Groq(
    api_key=GROQ_API_KEY
)


AVAILABLE_AGENT_TOOLS = [
    *AGENT_TOOLS,
    PROGRAMME_COMPARISON_TOOL,
]

AVAILABLE_TOOL_HANDLERS = {
    **TOOL_HANDLERS,
    "compare_dit_programmes": compare_dit_programmes,
}

TOOL_SCHEMAS_BY_NAME = {
    tool["function"]["name"]: tool
    for tool in AVAILABLE_AGENT_TOOLS
}


SYSTEM_PROMPT = """
You are DIT Smart Assistant, an agentic AI assistant for
Dar es Salaam Institute of Technology (DIT) in Tanzania.

You assist students, applicants, staff and visitors.
You can communicate naturally in both English and Kiswahili.

CORE BEHAVIOUR:

1. For factual questions about DIT, use a verified retrieval tool before
   answering. Use search_dit_knowledge for normal factual lookups and
   compare_dit_programmes for direct programme comparisons.

2. Never invent DIT programmes, campuses, fees, admission requirements,
   dates, regulations, contacts or policies.

3. Treat verified retrieval results as the institutional source of truth
   available to you.

4. If verified retrieval does not find enough information, clearly say that
   the requested information could not be verified from the available DIT
   knowledge base.

5. DIT has multiple campuses. Never assume information for one campus applies
   to another campus.

6. Use calculate_total_amount when exact monetary values need to be added.
   Only pass amounts supplied by the user or returned by verified DIT
   knowledge. Never guess missing amounts.

ADMISSION ELIGIBILITY RULES:

7. When a user asks whether they qualify, retrieve the relevant DIT admission
   requirement with search_dit_knowledge before running an eligibility check.

8. Use check_admission_eligibility only when BOTH the applicant's numeric
   value and the matching numeric requirement from verified DIT knowledge are
   available.

9. Never guess, infer or fabricate an admission threshold just to run the
   eligibility tool.

10. check_admission_eligibility evaluates one numeric criterion at a time.
    A positive result is NOT a final admission decision.

11. Never tell a user that DIT has officially admitted, accepted or rejected
    them. Final admission decisions belong to DIT.

PROGRAMME COMPARISON RULES:

12. When the user directly asks to compare two or more DIT programmes, prefer
    compare_dit_programmes instead of manually comparing from memory.

13. Compare only the programmes and aspects requested by the user. If aspects
    are not specified, compare overview, campus, admission requirements and
    fees.

14. Do not invent a value when a programme comparison aspect is missing from
    verified knowledge. State that it could not be verified.

CONVERSATION MEMORY RULES:

15. Use recent conversation history and structured student session context to
    resolve follow-up references such as "that programme", "what about the
    fees?", a campus, qualification or GPA supplied earlier.

16. Structured student state is user-provided conversation context only. It
    is NOT verified institutional data and must never substitute for retrieval
    of DIT facts.

17. For every factual DIT follow-up, still use the appropriate verified
    retrieval tool before stating current DIT facts.

18. If the current message changes programme, campus, qualification, GPA or
    goal, prefer the newest explicit information over older session state.

PLANNING RULES:

19. When an execution plan is supplied by the runtime, follow its task order
    and dependency relationships. Do not skip required tool work merely to
    produce a faster answer.

20. A dependent deterministic check must wait for its verified prerequisite.
    If a required user input is missing, do not fabricate it; ask the user for
    that input if it is necessary to continue.

21. Tool failure is a valid observation. If verified information cannot be
    retrieved, explain the limitation rather than inventing a result.

22. Greetings, thanks and ordinary non-factual conversation may be answered
    without calling a tool.

23. Answer in the same language used by the user unless the user requests
    another language.

RESPONSE STYLE:

24. Keep answers clear, factual and student-friendly.

25. Use short paragraphs, Markdown headings and bullet points when they
    improve readability.

26. For programme comparisons, use a compact comparison structure or table
    when the retrieved information supports it.

27. Do not refer to retrieved chunks as "Source 1", "Source 2" or similar
    labels. The application displays verified source metadata separately.

28. Do not create links that were not returned by verified knowledge.
""".strip()


def _build_messages(
    question: str,
    history: list[dict],
    student_state: dict | None = None,
    plan: dict | None = None,
) -> list:
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    state_context = format_student_state_for_agent(
        student_state
    )
    if state_context:
        messages.append(
            {
                "role": "system",
                "content": state_context,
            }
        )

    plan_context = format_plan_for_agent(
        plan
    )
    if plan_context:
        messages.append(
            {
                "role": "system",
                "content": plan_context,
            }
        )

    for item in history[-MAX_AGENT_HISTORY_MESSAGES:]:
        role = item.get(
            "role",
            "",
        )
        content = item.get(
            "content",
            "",
        ).strip()

        if (
            role not in {
                "user",
                "assistant",
            }
            or not content
        ):
            continue

        messages.append(
            {
                "role": role,
                "content": content,
            }
        )

    messages.append(
        {
            "role": "user",
            "content": question,
        }
    )

    return messages


def _merge_sources(
    collected_sources: list[dict],
    new_sources: list[dict],
) -> None:
    seen = {
        (
            source.get("title", ""),
            source.get("url", ""),
            source.get("page"),
        )
        for source in collected_sources
    }

    for source in new_sources:
        key = (
            source.get("title", ""),
            source.get("url", ""),
            source.get("page"),
        )
        if key in seen:
            continue

        seen.add(key)
        collected_sources.append(
            source
        )


def _execute_tool(
    tool_name: str,
    arguments: dict,
) -> dict:
    handler = AVAILABLE_TOOL_HANDLERS.get(
        tool_name
    )

    if handler is None:
        return {
            "found": False,
            "context": (
                f"The requested tool '{tool_name}' is not available."
            ),
            "sources": [],
        }

    try:
        return handler(
            **arguments
        )
    except TypeError as error:
        return {
            "found": False,
            "context": (
                "The tool request could not be executed because its "
                f"arguments were invalid: {error}"
            ),
            "sources": [],
        }


def _required_tools_for_ready_tasks(
    plan: dict,
) -> set[str]:
    required = set()

    for task in plan.get(
        "tasks",
        [],
    ):
        if not task.get(
            "ready",
            True,
        ):
            continue

        required.update(
            task.get(
                "required_tools",
                [],
            )
        )

    return required


def _tool_names_for_plan(
    plan: dict,
) -> set[str]:
    """Return only tool schemas that can be relevant to this request plan."""

    names = set()

    for task in plan.get(
        "tasks",
        [],
    ):
        names.update(
            task.get(
                "required_tools",
                [],
            )
        )

    return names


def _tools_for_plan(
    plan: dict,
) -> list[dict]:
    requested_names = _tool_names_for_plan(
        plan
    )

    return [
        TOOL_SCHEMAS_BY_NAME[name]
        for name in TOOL_SCHEMAS_BY_NAME
        if name in requested_names
    ]


def _blocked_dependency_result(
    tool_name: str,
) -> dict:
    return {
        "found": False,
        "context": (
            f"Runtime planning guard blocked '{tool_name}' because its verified "
            "prerequisite has not completed successfully. Retrieve the relevant "
            "DIT requirement first; do not guess the missing prerequisite."
        ),
        "sources": [],
    }


def _create_model_completion(
    request_kwargs: dict,
):
    """Call Groq with provider-aware TPM retry for production chat requests."""

    return run_with_rate_limit_retry(
        lambda: (
            client
            .chat
            .completions
            .create(
                **request_kwargs
            )
        ),
        max_retries=3,
        fallback_seconds=25.0,
        label="DIT agent model request",
    )


def run_dit_agent(
    question: str,
    history: list[dict] | None = None,
    student_state: dict | None = None,
):
    """Run the planned DIT agentic tool loop.

    The runtime builds an inspectable task plan before model execution. The
    model still chooses concrete tool arguments, while runtime guards enforce
    critical dependencies such as verified retrieval before eligibility checks.
    """

    history = history or []
    student_state = student_state or {}

    plan = build_request_plan(
        question=question,
        student_state=student_state,
    )

    messages = _build_messages(
        question=question,
        history=history,
        student_state=student_state,
        plan=plan,
    )

    required_tools = _required_tools_for_ready_tasks(
        plan
    )
    request_tools = _tools_for_plan(
        plan
    )
    attempted_tools: set[str] = set()
    successful_tools: set[str] = set()
    sources = []

    for _ in range(
        MAX_AGENT_ITERATIONS
    ):
        request_kwargs = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": 700,
        }

        if request_tools:
            request_kwargs[
                "tools"
            ] = request_tools
            request_kwargs[
                "tool_choice"
            ] = "auto"

        completion = _create_model_completion(
            request_kwargs
        )

        message = (
            completion
            .choices[0]
            .message
        )
        tool_calls = (
            message.tool_calls
            or []
        )

        if not tool_calls:
            pending_tools = (
                required_tools
                - attempted_tools
            )

            if pending_tools:
                messages.append(
                    message
                )
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "The execution plan is incomplete. Before producing "
                            "the final answer, attempt these pending required "
                            "tools when their inputs are available: "
                            + ", ".join(
                                sorted(
                                    pending_tools
                                )
                            )
                            + ". Do not fabricate missing inputs or facts."
                        ),
                    }
                )
                continue

            return (
                message.content
                or (
                    "I could not produce a complete answer for that request."
                ),
                sources,
            )

        messages.append(
            message
        )

        for tool_call in tool_calls:
            tool_name = (
                tool_call
                .function
                .name
            )
            attempted_tools.add(
                tool_name
            )

            try:
                arguments = json.loads(
                    tool_call
                    .function
                    .arguments
                    or "{}"
                )

                if not isinstance(
                    arguments,
                    dict,
                ):
                    raise ValueError(
                        "Tool arguments must be a JSON object."
                    )

                if (
                    tool_name
                    == "check_admission_eligibility"
                    and "search_dit_knowledge"
                    not in successful_tools
                ):
                    result = _blocked_dependency_result(
                        tool_name
                    )
                else:
                    result = _execute_tool(
                        tool_name=tool_name,
                        arguments=arguments,
                    )

            except (
                json.JSONDecodeError,
                ValueError,
            ) as error:
                result = {
                    "found": False,
                    "context": (
                        "The tool request could not be executed because its "
                        f"arguments were invalid: {error}"
                    ),
                    "sources": [],
                }

            if result.get(
                "found",
                False,
            ):
                successful_tools.add(
                    tool_name
                )

            _merge_sources(
                sources,
                result.get(
                    "sources",
                    [],
                ),
            )

            tool_payload = {
                "success": result.get(
                    "found",
                    False,
                ),
                "tool_result": result.get(
                    "context",
                    "",
                ),
            }

            for result_key in (
                "query",
                "calculation",
                "eligibility",
                "programme_comparison",
            ):
                if result.get(
                    result_key
                ):
                    tool_payload[result_key] = (
                        result[result_key]
                    )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": (
                        tool_call.id
                    ),
                    "name": tool_name,
                    "content": json.dumps(
                        tool_payload,
                        ensure_ascii=False,
                    ),
                }
            )

    return (
        "I could not complete the request within the allowed number of agent "
        "steps. Please try a more specific DIT question.",
        sources,
    )
