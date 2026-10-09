import json

from groq import Groq

from app.config import GROQ_API_KEY
from app.services.agent_tools import AGENT_TOOLS, TOOL_HANDLERS
from app.services.programme_comparison_tool import (
    PROGRAMME_COMPARISON_TOOL,
    compare_dit_programmes,
)
from app.services.rate_limit_retry import run_with_rate_limit_retry
from app.services.student_state import format_student_state_for_agent
from app.services.task_planner import build_request_plan, format_plan_for_agent


MODEL = "openai/gpt-oss-120b"
MAX_AGENT_ITERATIONS = 7
MAX_AGENT_HISTORY_MESSAGES = 10
MAX_TOOL_RESULT_CHARS = 3200
DEFAULT_RESPONSE_MAX_TOKENS = 650
COMPARISON_RESPONSE_MAX_TOKENS = 450


client = Groq(api_key=GROQ_API_KEY)

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
You are DIT Smart Assistant for Dar es Salaam Institute of Technology (DIT).
Answer in the user's language and keep answers clear and student-friendly.

Rules:
- For factual DIT information, use the verified tool required by the runtime plan.
- Never invent programmes, campuses, fees, admission rules, dates, contacts or policies.
- If verified information is missing, say it could not be verified. Do not turn
  "not found in the current retrieval" into a claim that a programme does not exist.
- Never assume facts for one DIT campus apply to another.
- For programme questions, state only the campus or campuses explicitly supported
  by retrieved evidence. Never write "all DIT campuses" unless a verified source
  explicitly says the programme is offered at all campuses.
- When a programme appears at more than one qualification level, list each verified
  level separately. Preserve the official programme name from the retrieved source.
- Use calculate_total_amount only with user-supplied or verified amounts.
- For admission eligibility, retrieve the official requirement first, then use
  check_admission_eligibility only when both numeric values are available.
  Eligibility results are preliminary; DIT makes final admission decisions.
- For direct programme comparisons, use compare_dit_programmes and state when
  an aspect could not be verified.
- Use conversation history and student state only to resolve follow-ups; they
  are not institutional truth. Factual follow-ups still require verified retrieval.
- Follow runtime task dependencies. Never fabricate a missing prerequisite.
- Greetings and ordinary conversation may be answered without tools.
- Do not invent links. Verified source metadata is displayed separately.
- Prefer a short direct answer first, followed by concise verified details.
- When tabular data genuinely improves clarity, output a valid Markdown table:
  one header row, one separator row using dashes, then data rows. Do not output
  broken pipe-delimited text or use a table when a short list is clearer.
""".strip()


def _build_messages(
    question: str,
    history: list[dict],
    student_state: dict | None = None,
    plan: dict | None = None,
) -> list:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    state_context = format_student_state_for_agent(student_state)
    if state_context:
        messages.append({"role": "system", "content": state_context})

    plan_context = format_plan_for_agent(plan)
    if plan_context:
        messages.append({"role": "system", "content": plan_context})

    for item in history[-MAX_AGENT_HISTORY_MESSAGES:]:
        role = item.get("role", "")
        content = item.get("content", "").strip()
        if role not in {"user", "assistant"} or not content:
            continue
        messages.append({"role": role, "content": content})

    messages.append({"role": "user", "content": question})
    return messages


def _merge_sources(
    collected_sources: list[dict],
    new_sources: list[dict],
) -> None:
    seen = {
        (source.get("title", ""), source.get("url", ""), source.get("page"))
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
        collected_sources.append(source)


def _execute_tool(tool_name: str, arguments: dict) -> dict:
    handler = AVAILABLE_TOOL_HANDLERS.get(tool_name)
    if handler is None:
        return {
            "found": False,
            "context": f"The requested tool '{tool_name}' is not available.",
            "sources": [],
        }

    try:
        return handler(**arguments)
    except TypeError as error:
        return {
            "found": False,
            "context": (
                "The tool request could not be executed because its arguments "
                f"were invalid: {error}"
            ),
            "sources": [],
        }


def _required_tools_for_ready_tasks(plan: dict) -> set[str]:
    required = set()
    for task in plan.get("tasks", []):
        if task.get("ready", True):
            required.update(task.get("required_tools", []))
    return required


def _tool_names_for_plan(plan: dict) -> set[str]:
    names = set()
    for task in plan.get("tasks", []):
        names.update(task.get("required_tools", []))
    return names


def _tools_for_plan(plan: dict) -> list[dict]:
    requested_names = _tool_names_for_plan(plan)
    return [
        TOOL_SCHEMAS_BY_NAME[name]
        for name in TOOL_SCHEMAS_BY_NAME
        if name in requested_names
    ]


def _blocked_dependency_result(tool_name: str) -> dict:
    return {
        "found": False,
        "context": (
            f"Runtime planning guard blocked '{tool_name}' because its verified "
            "prerequisite has not completed successfully. Retrieve the relevant "
            "DIT requirement first; do not guess the missing prerequisite."
        ),
        "sources": [],
    }


def _bounded_text(value: str, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    clean_value = str(value or "").strip()
    if len(clean_value) <= max_chars:
        return clean_value

    marker = "\n[Tool result truncated to stay within the model context budget.]"
    keep_chars = max(0, max_chars - len(marker))
    return clean_value[:keep_chars].rstrip() + marker


def _build_tool_payload(result: dict) -> dict:
    """Build a bounded model-facing payload while preserving UI source metadata."""

    payload = {
        "success": result.get("found", False),
        "tool_result": _bounded_text(result.get("context", "")),
    }

    for result_key in (
        "query",
        "calculation",
        "eligibility",
        "programme_comparison",
    ):
        if result.get(result_key):
            payload[result_key] = result[result_key]

    return payload


def _response_token_budget(plan: dict) -> int:
    task_ids = {
        task.get("id", "")
        for task in plan.get("tasks", [])
    }
    if "compare_programmes" in task_ids:
        return COMPARISON_RESPONSE_MAX_TOKENS
    return DEFAULT_RESPONSE_MAX_TOKENS


def _create_model_completion(request_kwargs: dict):
    """Call Groq with provider-aware rate-limit retry for production requests."""

    return run_with_rate_limit_retry(
        lambda: client.chat.completions.create(**request_kwargs),
        max_retries=3,
        fallback_seconds=25.0,
        label="DIT agent model request",
    )


def run_dit_agent(
    question: str,
    history: list[dict] | None = None,
    student_state: dict | None = None,
):
    """Run the planned DIT agentic tool loop with bounded context."""

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

    required_tools = _required_tools_for_ready_tasks(plan)
    request_tools = _tools_for_plan(plan)
    response_max_tokens = _response_token_budget(plan)
    attempted_tools: set[str] = set()
    successful_tools: set[str] = set()
    sources = []

    for _ in range(MAX_AGENT_ITERATIONS):
        request_kwargs = {
            "model": MODEL,
            "messages": messages,
            "temperature": 0.1,
            "max_tokens": response_max_tokens,
        }

        if request_tools:
            request_kwargs["tools"] = request_tools
            request_kwargs["tool_choice"] = "auto"

        completion = _create_model_completion(request_kwargs)
        message = completion.choices[0].message
        tool_calls = message.tool_calls or []

        if not tool_calls:
            pending_tools = required_tools - attempted_tools
            if pending_tools:
                messages.append(message)
                messages.append(
                    {
                        "role": "system",
                        "content": (
                            "The execution plan is incomplete. Attempt these pending "
                            "required tools when their inputs are available: "
                            + ", ".join(sorted(pending_tools))
                            + ". Do not fabricate missing inputs or facts."
                        ),
                    }
                )
                continue

            return (
                message.content
                or "I could not produce a complete answer for that request.",
                sources,
            )

        messages.append(message)

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            attempted_tools.add(tool_name)

            try:
                arguments = json.loads(tool_call.function.arguments or "{}")
                if not isinstance(arguments, dict):
                    raise ValueError("Tool arguments must be a JSON object.")

                if (
                    tool_name == "check_admission_eligibility"
                    and "search_dit_knowledge" not in successful_tools
                ):
                    result = _blocked_dependency_result(tool_name)
                else:
                    result = _execute_tool(
                        tool_name=tool_name,
                        arguments=arguments,
                    )
            except (json.JSONDecodeError, ValueError) as error:
                result = {
                    "found": False,
                    "context": (
                        "The tool request could not be executed because its arguments "
                        f"were invalid: {error}"
                    ),
                    "sources": [],
                }

            if result.get("found", False):
                successful_tools.add(tool_name)

            _merge_sources(sources, result.get("sources", []))
            tool_payload = _build_tool_payload(result)

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_payload, ensure_ascii=False),
                }
            )

    return (
        "I could not complete the request within the allowed number of agent "
        "steps. Please try a more specific DIT question.",
        sources,
    )
