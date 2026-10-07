import json

from groq import Groq

from app.config import GROQ_API_KEY
from app.services.agent_tools import (
    SEARCH_DIT_KNOWLEDGE_TOOL,
    search_dit_knowledge,
)


MODEL = "openai/gpt-oss-120b"
MAX_AGENT_ITERATIONS = 5


client = Groq(
    api_key=GROQ_API_KEY
)


SYSTEM_PROMPT = """
You are DIT Smart Assistant, an agentic AI assistant for
Dar es Salaam Institute of Technology (DIT) in Tanzania.

You assist students, applicants, staff and visitors.
You can communicate naturally in both English and Kiswahili.

CORE BEHAVIOUR:

1. For any factual question about DIT, you MUST use the
   search_dit_knowledge tool before answering.

2. Never invent DIT programmes, campuses, fees, admission
   requirements, dates, regulations, contacts or policies.

3. Treat the search_dit_knowledge result as the verified
   institutional source of truth available to you.

4. If the tool does not find enough verified information,
   clearly say that the information could not be verified
   from the available DIT knowledge base.

5. DIT has multiple campuses. Never assume information for
   one campus applies to another campus.

6. You may call the knowledge tool more than once when the
   user's request contains multiple factual sub-questions.

7. Greetings, thanks and ordinary non-factual conversation
   may be answered without calling a tool.

8. Answer in the same language used by the user unless the
   user requests another language.

RESPONSE STYLE:

9. Keep answers clear, factual and student-friendly.

10. Use short paragraphs, Markdown headings and bullet points
    when they improve readability.

11. Do not refer to retrieved chunks as "Source 1", "Source 2"
    or similar labels. The application displays verified source
    metadata separately.

12. Do not create links that were not returned by the verified
    knowledge tool.
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
    if tool_name == "search_dit_knowledge":
        return search_dit_knowledge(
            query=arguments.get(
                "query",
                "",
            )
        )

    return {
        "found": False,
        "context": (
            f"The requested tool '{tool_name}' is not available."
        ),
        "sources": [],
    }


def run_dit_agent(
    question: str,
    history: list[dict] | None = None,
):
    """
    Run the DIT agentic loop.

    The model decides when verified DIT retrieval is required.
    Tool results are fed back into the model until it produces
    a final answer or the iteration limit is reached.
    """

    history = history or []

    messages = _build_messages(
        question=question,
        history=history,
    )

    tools = [
        SEARCH_DIT_KNOWLEDGE_TOOL
    ]

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
                tools=tools,
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
                "found": result.get(
                    "found",
                    False,
                ),
                "query": result.get(
                    "query",
                    "",
                ),
                "verified_context": (
                    result.get(
                        "context",
                        "",
                    )
                ),
            }

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
