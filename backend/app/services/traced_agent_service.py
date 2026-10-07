from __future__ import annotations

from contextvars import ContextVar
from time import perf_counter

from app.services import agent_service
from app.services.execution_trace import agent_traces
from app.services.task_planner import build_request_plan


_current_trace_id: ContextVar[str | None] = ContextVar(
    "dit_agent_trace_id",
    default=None,
)

_WRAPPERS_INSTALLED = False


def _duration_ms(started_at: float) -> int:
    return max(
        0,
        round((perf_counter() - started_at) * 1000),
    )


def _install_tool_tracing() -> None:
    global _WRAPPERS_INSTALLED

    if _WRAPPERS_INSTALLED:
        return

    for tool_name, handler in list(
        agent_service.AVAILABLE_TOOL_HANDLERS.items()
    ):
        original_handler = handler

        def traced_handler(
            *args,
            __tool_name=tool_name,
            __handler=original_handler,
            **kwargs,
        ):
            trace_id = _current_trace_id.get()
            started = perf_counter()

            try:
                result = __handler(
                    *args,
                    **kwargs,
                )
            except Exception as error:
                if trace_id:
                    agent_traces.add_event(
                        trace_id,
                        "tool_call",
                        tool_name=__tool_name,
                        success=False,
                        blocked=False,
                        duration_ms=_duration_ms(started),
                    )
                raise

            if trace_id:
                agent_traces.add_event(
                    trace_id,
                    "tool_call",
                    tool_name=__tool_name,
                    success=bool(
                        result.get("found", False)
                    ),
                    blocked=False,
                    duration_ms=_duration_ms(started),
                )

            return result

        agent_service.AVAILABLE_TOOL_HANDLERS[
            tool_name
        ] = traced_handler

    original_blocked_result = (
        agent_service._blocked_dependency_result
    )

    def traced_blocked_result(tool_name: str):
        trace_id = _current_trace_id.get()

        if trace_id:
            agent_traces.add_event(
                trace_id,
                "dependency_block",
                tool_name=tool_name,
                success=False,
                blocked=True,
            )

        return original_blocked_result(
            tool_name
        )

    agent_service._blocked_dependency_result = (
        traced_blocked_result
    )

    _WRAPPERS_INSTALLED = True


_install_tool_tracing()


def run_traced_dit_agent(
    question: str,
    history: list[dict] | None = None,
    student_state: dict | None = None,
    session_id: str = "",
):
    """Run the DIT agent and persist privacy-conscious execution metadata."""

    history = history or []
    student_state = student_state or {}

    trace_id = agent_traces.start(
        session_id=session_id
    )

    plan = build_request_plan(
        question=question,
        student_state=student_state,
    )
    agent_traces.set_plan(
        trace_id,
        plan,
    )

    token = _current_trace_id.set(
        trace_id
    )
    started = perf_counter()

    try:
        answer, sources = agent_service.run_dit_agent(
            question=question,
            history=history,
            student_state=student_state,
        )

        trace = agent_traces.get(
            trace_id
        ) or {}
        tool_events = [
            event
            for event in trace.get("events", [])
            if event.get("type")
            in {"tool_call", "dependency_block"}
        ]

        agent_traces.finish(
            trace_id,
            status="completed",
            duration_ms=_duration_ms(started),
            iterations=(
                len(tool_events) + 1
            ),
            source_count=len(sources),
        )

        return answer, sources, trace_id

    except Exception as error:
        trace = agent_traces.get(
            trace_id
        ) or {}
        tool_events = [
            event
            for event in trace.get("events", [])
            if event.get("type")
            in {"tool_call", "dependency_block"}
        ]

        agent_traces.finish(
            trace_id,
            status="failed",
            duration_ms=_duration_ms(started),
            iterations=len(tool_events),
            source_count=0,
            error_type=type(error).__name__,
        )
        raise

    finally:
        _current_trace_id.reset(
            token
        )
