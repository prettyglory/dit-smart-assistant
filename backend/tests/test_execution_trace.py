import json
import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.services.execution_trace import (  # noqa: E402
    ExecutionTraceStore,
)


class ExecutionTraceStoreTests(unittest.TestCase):

    def setUp(self):
        self.store = ExecutionTraceStore(
            max_traces=10,
        )

    def test_trace_records_operational_metadata(self):
        trace_id = self.store.start(
            session_id="session-123"
        )

        self.store.set_plan(
            trace_id,
            {
                "kind": "compound",
                "tasks": [
                    {
                        "id": "retrieve_fees",
                        "type": "verified_retrieval",
                        "required_tools": [
                            "search_dit_knowledge"
                        ],
                        "depends_on": [],
                        "ready": True,
                        "missing_inputs": [],
                    }
                ],
            },
        )

        self.store.add_event(
            trace_id,
            "tool_call",
            tool_name="search_dit_knowledge",
            success=True,
            blocked=False,
            duration_ms=12,
        )

        self.store.finish(
            trace_id,
            status="completed",
            duration_ms=42,
            iterations=2,
            source_count=3,
        )

        trace = self.store.get(
            trace_id
        )

        self.assertIsNotNone(trace)
        self.assertEqual(
            trace["status"],
            "completed",
        )
        self.assertEqual(
            trace["plan"]["kind"],
            "compound",
        )
        self.assertEqual(
            trace["events"][0]["tool_name"],
            "search_dit_knowledge",
        )
        self.assertEqual(
            trace["duration_ms"],
            42,
        )
        self.assertEqual(
            trace["source_count"],
            3,
        )

    def test_trace_does_not_accept_sensitive_event_fields(self):
        trace_id = self.store.start()

        self.store.add_event(
            trace_id,
            "tool_call",
            tool_name="search_dit_knowledge",
            success=True,
            arguments={
                "query": "private student question"
            },
            retrieved_text="private retrieved content",
            answer="private assistant answer",
        )

        trace = self.store.get(
            trace_id
        )
        serialized = json.dumps(
            trace
        )

        self.assertNotIn(
            "private student question",
            serialized,
        )
        self.assertNotIn(
            "private retrieved content",
            serialized,
        )
        self.assertNotIn(
            "private assistant answer",
            serialized,
        )

    def test_invalid_trace_id_returns_none(self):
        self.assertIsNone(
            self.store.get("not-a-trace-id")
        )

    def test_get_returns_defensive_copy(self):
        trace_id = self.store.start()
        first = self.store.get(trace_id)
        first["status"] = "tampered"

        second = self.store.get(trace_id)

        self.assertEqual(
            second["status"],
            "running",
        )


if __name__ == "__main__":
    unittest.main()
