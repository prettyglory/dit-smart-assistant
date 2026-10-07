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


MODEL = "openai/gpt-oss-120b"
MAX_AGENT_ITERATIONS = 5


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


SYSTEM_PROMPT = """
You are DIT Smart Assistant, an agentic AI assistant for
Dar es Salaam Institute of Technology (DIT) in Tanzania.

You assist students, applicants, staff and visitors.
You can communicate naturally in both English and Kiswahili.

CORE BEHAVIOUR:

1. For factual questions about DIT, use a verified retrieval tool
   before answering. Use search_dit_knowledge for normal factual
   lookups and compare_dit_programmes for direct programme comparisons.

2. Never invent DIT programmes, campuses, fees, admission
   requirements, dates, regulations, contacts or policies.

3. Treat verified retrieval results as the institutional source
   of truth available to you.

4. If a verified retrieval tool does not find enough information,
   clearly say that the information could not be verified from the
   available DIT knowledge base.

5. DIT has multiple campuses. Never assume information for one
   campus applies to another campus.

6. You may make multiple tool calls when the user's request contains
   multiple factual sub-questions.

7. Use calculate_total_amount when exact monetary values need to be
   added. Only pass amounts that came from the user or verified DIT
   knowledge. Never guess missing amounts.

ADMISSION ELIGIBILITY RULES:

8. When a user asks whether they qualify, first retrieve the relevant
   DIT admission requirement with search_dit_knowledge.

9. Use check_admission_eligibility only when BOTH of these are available:
   - the applicant's numeric value, supplied by the user; and
   - the matching numeric requirement found in verified DIT knowledge.

10. Never guess, infer or fabricate an admission threshold just to run
    the eligibility tool.

11. check_admission_eligibility evaluates only one numeric criterion at
    a time. A positive result means the applicant meets that criterion
    only; it is NOT a final admission decision.

12. If other non-numeric or programme-specific requirements are present,
    explain them separately from the numeric check.

13. Never tell a user that DIT has officially admitted, accepted or
    rejected them. Final admission decisions belong to DIT.

PROGRAMME COMPARISON RULES:

14. When the user directly asks to compare two or more DIT programmes,
    prefer compare_dit_programmes instead of manually comparing from
    memory.

15. Pass only programme names requested by the user. Compare the aspects
    the user asks for; if they do not specify aspects, compare overview,
    campus, admission requirements and fees.

16. The programme comparison tool performs verified retrieval internally.
    Do not invent a value when one programme or one aspect is missing from
    the returned knowledge. State that it could not be verified.

17. Keep factual differences separate from advice. If you recommend one
    programme, make clear that the recommendation is based on the user's
    stated goals and the verified comparison, not an official DIT ranking.

18. Greetings, thanks and ordinary non-factual conversation may be
    answered without calling a tool.

19. Answer in the same language used by the user unless the user requests
    another language.

RESPONSE STYLE:

20. Keep answers clear, factual and student-friendly.

21. Use short paragraphs, Markdown headings and bullet points when they
    improve readability.

22. For programme comparisons, use a compact comparison structure or
    table when the retrieved information supports it.

23. Do not refer to retrieved chunks as "Source 1", "Source 2" or similar
    labels. The application displays verified source metadata separately.

24. Do not create links that were not returned by verified knowledge.
""".strip()


def _build_messages(
    question: str,
    history: list[dict],
) -> list:
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        }
    ]

    for item in history[-6:]:
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


def run_dit_agent(
    question: str,
    history: list[dict] | None = None,
):
    """
    Run the DIT agentic loop.

    The model decides when verified DIT retrieval, programme comparison,
    deterministic calculation or a preliminary admission criterion check
    is required. Tool results are fed back into the model until it produces
    a final answer or the iteration limit is reached.
    """

    history = history or []

    messages = _build_messages(
        question=question,
        history=history,
    )

    sources = []

    for _ in range(
        MAX_AGENT_ITERATIONS
    ):
        completion = (
            client
            .chat
            .completions
            .create(
                model=MODEL,
                messages=messages,
                tools=AVAILABLE_AGENT_TOOLS,
                tool_choice="auto",
                temperature=0.1,
                max_tokens=700,
            )
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
            return (
                message.content
                or (
                    "I could not produce a complete "
                    "answer for that request."
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
                        "The tool request could not be executed because "
                        f"its arguments were invalid: {error}"
                    ),
                    "sources": [],
                }

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

            if result.get("query"):
                tool_payload["query"] = (
                    result["query"]
                )

            if result.get("calculation"):
                tool_payload["calculation"] = (
                    result["calculation"]
                )

            if result.get("eligibility"):
                tool_payload["eligibility"] = (
                    result["eligibility"]
                )

            if result.get("programme_comparison"):
                tool_payload["programme_comparison"] = (
                    result["programme_comparison"]
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
        "I could not complete the request within the "
        "allowed number of agent steps. Please try "
        "a more specific DIT question.",
        sources,
    )
