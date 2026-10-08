import os
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("GROQ_API_KEY", "test-key")

fake_dotenv = ModuleType("dotenv")
fake_dotenv.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", fake_dotenv)


class _FakeGroq:
    def __init__(self, *args, **kwargs):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=lambda **kwargs: None)
        )


fake_groq = ModuleType("groq")
fake_groq.Groq = _FakeGroq
sys.modules.setdefault("groq", fake_groq)

if "app.services.rag_service" not in sys.modules:
    fake_rag_service = ModuleType("app.services.rag_service")
    fake_rag_service.detect_categories = lambda question: ["programme"]
    sys.modules["app.services.rag_service"] = fake_rag_service

if "app.services.vector_store" not in sys.modules:
    fake_vector_store = ModuleType("app.services.vector_store")
    fake_vector_store.search_knowledge = lambda **kwargs: []
    sys.modules["app.services.vector_store"] = fake_vector_store


from app.services.agent_service import (  # noqa: E402
    COMPARISON_RESPONSE_MAX_TOKENS,
    DEFAULT_RESPONSE_MAX_TOKENS,
    MAX_TOOL_RESULT_CHARS,
    _build_tool_payload,
    _response_token_budget,
)
from app.services.task_planner import build_request_plan  # noqa: E402


class AgentContextBudgetTests(unittest.TestCase):

    def test_tool_result_is_hard_capped_before_model_injection(self):
        result = {
            "found": True,
            "context": "X" * 10000,
            "sources": [],
        }

        payload = _build_tool_payload(result)

        self.assertTrue(payload["success"])
        self.assertLessEqual(
            len(payload["tool_result"]),
            MAX_TOOL_RESULT_CHARS,
        )
        self.assertIn(
            "truncated",
            payload["tool_result"].lower(),
        )

    def test_comparison_uses_smaller_response_budget(self):
        comparison_plan = build_request_plan(
            question=(
                "Compare Computer Engineering and Information Technology at DIT."
            )
        )
        lookup_plan = build_request_plan(
            question="What programmes does DIT offer?"
        )

        self.assertEqual(
            _response_token_budget(comparison_plan),
            COMPARISON_RESPONSE_MAX_TOKENS,
        )
        self.assertEqual(
            _response_token_budget(lookup_plan),
            DEFAULT_RESPONSE_MAX_TOKENS,
        )
        self.assertLess(
            COMPARISON_RESPONSE_MAX_TOKENS,
            DEFAULT_RESPONSE_MAX_TOKENS,
        )


if __name__ == "__main__":
    unittest.main()
