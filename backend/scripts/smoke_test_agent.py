from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from uuid import uuid4


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.rate_limit_retry import (  # noqa: E402
    run_with_rate_limit_retry,
)


def _fail(message: str) -> None:
    raise RuntimeError(message)


def _tool_names(trace: dict) -> list[str]:
    return [
        event.get("tool_name", "")
        for event in trace.get("events", [])
        if event.get("type") == "tool_call"
        and event.get("tool_name")
    ]


def _assert_trace(
    trace: dict,
    *,
    expected_tools: set[str] | None = None,
    forbidden_tools: set[str] | None = None,
    min_sources: int = 0,
) -> None:
    expected_tools = expected_tools or set()
    forbidden_tools = forbidden_tools or set()

    if trace.get("status") != "completed":
        _fail(
            f"Trace did not complete successfully: {trace.get('status')}"
        )

    tools = set(_tool_names(trace))

    missing = expected_tools - tools
    if missing:
        _fail(
            "Expected tool calls were not observed: "
            + ", ".join(sorted(missing))
        )

    unexpected = forbidden_tools & tools
    if unexpected:
        _fail(
            "Forbidden tool calls were observed: "
            + ", ".join(sorted(unexpected))
        )

    if int(trace.get("source_count", 0)) < min_sources:
        _fail(
            "Trace returned fewer verified sources than expected: "
            f"{trace.get('source_count', 0)} < {min_sources}"
        )


def _print_case(
    label: str,
    answer: str,
    trace: dict,
) -> None:
    print(f"\n[PASS] {label}")
    print(
        json.dumps(
            {
                "trace_id": trace.get("trace_id"),
                "status": trace.get("status"),
                "duration_ms": trace.get("duration_ms"),
                "iterations": trace.get("iterations"),
                "source_count": trace.get("source_count"),
                "tools": _tool_names(trace),
                "answer_preview": " ".join(answer.split())[:180],
            },
            indent=2,
            ensure_ascii=False,
        )
    )


def _run_case(
    *,
    label: str,
    question: str,
    session_id: str,
    history: list[dict] | None = None,
    student_state: dict | None = None,
    expected_tools: set[str] | None = None,
    forbidden_tools: set[str] | None = None,
    min_sources: int = 0,
):
    from app.services.execution_trace import agent_traces
    from app.services.traced_agent_service import run_traced_dit_agent

    def execute_agent():
        return run_traced_dit_agent(
            question=question,
            history=history or [],
            student_state=student_state or {},
            session_id=session_id,
        )

    answer, sources, trace_id = run_with_rate_limit_retry(
        execute_agent,
        max_retries=3,
        fallback_seconds=25.0,
        label=label,
    )

    trace = agent_traces.get(trace_id)
    if trace is None:
        _fail(
            f"Trace {trace_id} was not available after the agent run."
        )

    _assert_trace(
        trace,
        expected_tools=expected_tools,
        forbidden_tools=forbidden_tools,
        min_sources=min_sources,
    )

    if not answer.strip():
        _fail("Agent returned an empty answer.")

    _print_case(
        label,
        answer,
        trace,
    )

    return answer, sources, trace


def _preflight() -> int:
    if not os.getenv("GROQ_API_KEY"):
        _fail(
            "GROQ_API_KEY is missing. Set it in the environment before running "
            "the live smoke test."
        )

    from app.services.vector_store import get_collection

    count = get_collection().count()
    if count <= 0:
        _fail(
            "The DIT ChromaDB collection is empty. Run `python -m scripts.ingest` "
            "from the backend directory before the live smoke test."
        )

    print(f"Preflight passed: DIT knowledge collection contains {count} chunks.")
    return count


def main() -> int:
    _preflight()

    run_id = uuid4().hex[:10]

    _run_case(
        label="Greeting skips institutional tools",
        question="Hello",
        session_id=f"smoke-greeting-{run_id}",
        forbidden_tools={
            "search_dit_knowledge",
            "compare_dit_programmes",
            "check_admission_eligibility",
            "calculate_total_amount",
        },
    )

    first_answer, _, _ = _run_case(
        label="Programme question uses verified retrieval",
        question="Tell me about Computer Engineering at DIT.",
        session_id=f"smoke-followup-{run_id}",
        expected_tools={"search_dit_knowledge"},
        min_sources=1,
    )

    _run_case(
        label="Programme comparison uses dedicated verified tool",
        question=(
            "Compare Computer Engineering and Information Technology at DIT "
            "in terms of campus, admission requirements and fees."
        ),
        session_id=f"smoke-comparison-{run_id}",
        expected_tools={"compare_dit_programmes"},
        min_sources=1,
    )

    _run_case(
        label="Follow-up keeps programme context and re-retrieves facts",
        question="What about the fees?",
        history=[
            {
                "role": "user",
                "content": "Tell me about Computer Engineering at DIT.",
            },
            {
                "role": "assistant",
                "content": first_answer,
            },
        ],
        student_state={
            "programme": "Computer Engineering",
            "goal": "fees",
        },
        session_id=f"smoke-followup-{run_id}",
        expected_tools={"search_dit_knowledge"},
        min_sources=1,
    )

    print("\nAll live Agentic RAG smoke tests passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"\n[FAIL] {type(error).__name__}: {error}")
        raise SystemExit(1)
