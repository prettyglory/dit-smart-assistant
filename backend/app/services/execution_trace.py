from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import UUID, uuid4


MAX_TRACES = 500
TRACE_TTL = timedelta(hours=2)


class ExecutionTraceStore:
    """Bounded in-process observability store for agent executions.

    Traces intentionally contain operational metadata only. Full user prompts,
    tool arguments, retrieved document text and assistant responses are not
    persisted here.
    """

    def __init__(
        self,
        max_traces: int = MAX_TRACES,
        ttl: timedelta = TRACE_TTL,
    ) -> None:
        self.max_traces = max_traces
        self.ttl = ttl
        self._traces: dict[str, dict] = {}
        self._lock = RLock()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _is_valid_trace_id(trace_id: str | None) -> bool:
        if not trace_id:
            return False

        try:
            UUID(trace_id)
        except (ValueError, TypeError, AttributeError):
            return False

        return True

    def _prune_expired(self, now: datetime) -> None:
        expired = [
            trace_id
            for trace_id, trace in self._traces.items()
            if now - trace["updated_at"] > self.ttl
        ]

        for trace_id in expired:
            self._traces.pop(trace_id, None)

    def _prune_capacity(self) -> None:
        overflow = len(self._traces) - self.max_traces
        if overflow <= 0:
            return

        oldest = sorted(
            self._traces.items(),
            key=lambda item: item[1]["updated_at"],
        )[:overflow]

        for trace_id, _ in oldest:
            self._traces.pop(trace_id, None)

    def start(
        self,
        session_id: str = "",
    ) -> str:
        trace_id = str(uuid4())
        now = self._now()

        with self._lock:
            self._prune_expired(now)
            self._traces[trace_id] = {
                "trace_id": trace_id,
                "session_id": session_id,
                "status": "running",
                "started_at": now.isoformat(),
                "completed_at": None,
                "duration_ms": None,
                "plan": {
                    "kind": "conversation",
                    "tasks": [],
                },
                "events": [],
                "iterations": 0,
                "source_count": 0,
                "error_type": None,
                "updated_at": now,
            }
            self._prune_capacity()

        return trace_id

    def set_plan(
        self,
        trace_id: str,
        plan: dict,
    ) -> None:
        safe_tasks = []

        for task in plan.get("tasks", []):
            safe_tasks.append(
                {
                    "id": task.get("id", ""),
                    "type": task.get("type", ""),
                    "required_tools": list(
                        task.get("required_tools", [])
                    ),
                    "depends_on": list(
                        task.get("depends_on", [])
                    ),
                    "ready": bool(
                        task.get("ready", True)
                    ),
                    "missing_input_count": len(
                        task.get("missing_inputs", [])
                    ),
                }
            )

        now = self._now()

        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return

            trace["plan"] = {
                "kind": plan.get("kind", "conversation"),
                "tasks": safe_tasks,
            }
            trace["updated_at"] = now

    def add_event(
        self,
        trace_id: str,
        event_type: str,
        **details,
    ) -> None:
        now = self._now()

        safe_details = {
            key: value
            for key, value in details.items()
            if key in {
                "iteration",
                "duration_ms",
                "tool_call_count",
                "tool_name",
                "success",
                "blocked",
                "pending_tools",
            }
        }

        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return

            trace["events"].append(
                {
                    "type": event_type,
                    "at": now.isoformat(),
                    **safe_details,
                }
            )
            trace["updated_at"] = now

    def finish(
        self,
        trace_id: str,
        *,
        status: str,
        duration_ms: int,
        iterations: int,
        source_count: int,
        error_type: str | None = None,
    ) -> None:
        now = self._now()

        with self._lock:
            trace = self._traces.get(trace_id)
            if trace is None:
                return

            trace["status"] = status
            trace["completed_at"] = now.isoformat()
            trace["duration_ms"] = max(0, int(duration_ms))
            trace["iterations"] = max(0, int(iterations))
            trace["source_count"] = max(0, int(source_count))
            trace["error_type"] = error_type
            trace["updated_at"] = now

    def get(
        self,
        trace_id: str,
    ) -> dict | None:
        if not self._is_valid_trace_id(trace_id):
            return None

        now = self._now()

        with self._lock:
            self._prune_expired(now)
            trace = self._traces.get(trace_id)
            if trace is None:
                return None

            public_trace = {
                key: value
                for key, value in trace.items()
                if key != "updated_at"
            }
            return deepcopy(public_trace)


agent_traces = ExecutionTraceStore()
