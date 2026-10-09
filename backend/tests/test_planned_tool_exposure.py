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
            completions=SimpleNamespace(
                create=lambda **kwargs: None
            )
        )


fake_groq = ModuleType("groq")
fake_groq.Groq = _FakeGroq
sys.modules.setdefault("groq", fake_groq)

if "app.services.rag_service" not in sys.modules:
    fake_rag_service = ModuleType(
        "app.services.rag_service"
    )
    fake_rag_service.detect_categories = (
        lambda question: ["programme"]
    )
    sys.modules[
        "app.services.rag_service"
    ] = fake_rag_service

if "app.services.vector_store" not in sys.modules:
    fake_vector_store = ModuleType(
        "app.services.vector_store"
    )
    fake_vector_store.search_knowledge = (
        lambda **kwargs: []
    )
    sys.modules[
        "app.services.vector_store"
    ] = fake_vector_store


from app.services.agent_service import _tools_for_plan  # noqa: E402
from app.services.task_planner import build_request_plan  # noqa: E402


def _tool_names(tools: list[dict]) -> list[str]:
    return [
        tool["function"]["name"]
        for tool in tools
    ]


class PlannedToolExposureTests(unittest.TestCase):

    def test_conversation_exposes_no_tools(self):
        plan = build_request_plan(
            question="Hello",
        )

        self.assertEqual(
            _tools_for_plan(plan),
            [],
        )

    def test_factual_lookup_exposes_only_verified_search(self):
        plan = build_request_plan(
            question="What programmes does DIT offer?",
        )

        self.assertEqual(
            _tool_names(
                _tools_for_plan(plan)
            ),
            ["search_dit_knowledge"],
        )

    def test_programme_comparison_exposes_only_comparison_tool(self):
        plan = build_request_plan(
            question=(
                "Compare Computer Engineering and Information Technology "
                "at DIT."
            ),
        )

        self.assertEqual(
            _tool_names(
                _tools_for_plan(plan)
            ),
            ["compare_dit_programmes"],
        )

    def test_eligibility_exposes_prerequisite_and_check_tools(self):
        plan = build_request_plan(
            question=(
                "I have GPA 3.5. Do I qualify for Computer Engineering at DIT?"
            ),
        )

        self.assertEqual(
            set(
                _tool_names(
                    _tools_for_plan(plan)
                )
            ),
            {
                "search_dit_knowledge",
                "check_admission_eligibility",
            },
        )


if __name__ == "__main__":
    unittest.main()
