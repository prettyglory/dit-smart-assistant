import os
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("GROQ_API_KEY", "test-key")

fake_dotenv = ModuleType("dotenv")
fake_dotenv.load_dotenv = lambda *args, **kwargs: None
sys.modules.setdefault("dotenv", fake_dotenv)


class _FakeCompletions:
    def create(self, *args, **kwargs):
        raise AssertionError(
            "A unit test attempted to call the real Groq client."
        )


class _FakeGroq:
    def __init__(self, *args, **kwargs):
        self.chat = SimpleNamespace(
            completions=_FakeCompletions()
        )


fake_groq = ModuleType("groq")
fake_groq.Groq = _FakeGroq
sys.modules.setdefault("groq", fake_groq)

fake_rag_service = ModuleType(
    "app.services.rag_service"
)
fake_rag_service.detect_categories = (
    lambda question: ["programme"]
)
sys.modules.setdefault(
    "app.services.rag_service",
    fake_rag_service,
)

fake_vector_store = ModuleType(
    "app.services.vector_store"
)
fake_vector_store.search_knowledge = (
    lambda **kwargs: []
)
sys.modules.setdefault(
    "app.services.vector_store",
    fake_vector_store,
)

from app.services.agent_service import run_dit_agent  # noqa: E402
from app.services.task_planner import (  # noqa: E402
    build_request_plan,
    format_plan_for_agent,
)


def _completion(message):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=message
            )
        ]
    )


def _final_message(content):
    return SimpleNamespace(
        content=content,
        tool_calls=None,
    )


def _tool_message(
    name,
    arguments,
    call_id,
):
    import json

    return SimpleNamespace(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id=call_id,
                function=SimpleNamespace(
                    name=name,
                    arguments=json.dumps(
                        arguments
                    ),
                ),
            )
        ],
    )


class TaskPlannerTests(unittest.TestCase):

    def test_compound_request_is_decomposed_in_dependency_order(self):
        plan = build_request_plan(
            question=(
                "Check if I qualify, tell me the fees, and compare Computer "
                "Engineering with Information Technology."
            ),
            student_state={
                "programme": "Computer Engineering",
                "qualification": "Ordinary Diploma",
                "gpa": "3.6",
            },
        )

        self.assertEqual(
            plan["kind"],
            "compound",
        )
        self.assertEqual(
            [
                task["id"]
                for task in plan["tasks"]
            ],
            [
                "retrieve_admission_requirements",
                "evaluate_admission_eligibility",
                "retrieve_fees",
                "compare_programmes",
            ],
        )
        self.assertEqual(
            plan["tasks"][1]["depends_on"],
            ["retrieve_admission_requirements"],
        )
        self.assertTrue(
            plan["tasks"][1]["ready"]
        )

    def test_eligibility_without_numeric_input_marks_check_not_ready(self):
        plan = build_request_plan(
            question="Do I qualify for Computer Engineering?",
            student_state={
                "programme": "Computer Engineering"
            },
        )

        eligibility = plan["tasks"][1]

        self.assertFalse(
            eligibility["ready"]
        )
        self.assertIn(
            "applicant numeric criterion",
            eligibility["missing_inputs"][0],
        )

    def test_total_fee_request_adds_deterministic_calculation(self):
        plan = build_request_plan(
            question="What are the DIT fees and total amount?",
            student_state={},
        )

        self.assertEqual(
            [task["id"] for task in plan["tasks"]],
            [
                "retrieve_fees",
                "calculate_fee_total",
            ],
        )
        self.assertEqual(
            plan["tasks"][1]["depends_on"],
            ["retrieve_fees"],
        )

    def test_simple_greeting_has_no_tool_plan(self):
        plan = build_request_plan(
            question="Hello",
            student_state={},
        )

        self.assertEqual(
            plan,
            {
                "kind": "conversation",
                "tasks": [],
            },
        )

    def test_formatted_plan_exposes_dependencies_to_agent(self):
        plan = build_request_plan(
            question="Do I qualify?",
            student_state={
                "gpa": "3.5"
            },
        )

        formatted = format_plan_for_agent(
            plan
        )

        self.assertIn(
            "EXECUTION PLAN",
            formatted,
        )
        self.assertIn(
            "retrieve_admission_requirements",
            formatted,
        )
        self.assertIn(
            "Depends on: retrieve_admission_requirements",
            formatted,
        )


class PlannedAgentRuntimeTests(unittest.TestCase):

    @patch("app.services.agent_service._execute_tool")
    @patch("app.services.agent_service.client.chat.completions.create")
    def test_runtime_rejects_early_final_until_required_retrieval_is_attempted(
        self,
        mock_create,
        mock_execute,
    ):
        mock_create.side_effect = [
            _completion(
                _final_message(
                    "The fee is probably this amount."
                )
            ),
            _completion(
                _tool_message(
                    "search_dit_knowledge",
                    {"query": "DIT fees"},
                    "search_1",
                )
            ),
            _completion(
                _final_message(
                    "Here is the verified fee information."
                )
            ),
        ]

        mock_execute.return_value = {
            "found": True,
            "query": "DIT fees",
            "context": "Verified fee information.",
            "sources": [],
        }

        answer, _ = run_dit_agent(
            "What are the DIT fees?"
        )

        self.assertEqual(
            answer,
            "Here is the verified fee information.",
        )
        self.assertEqual(
            mock_create.call_count,
            3,
        )
        mock_execute.assert_called_once_with(
            tool_name="search_dit_knowledge",
            arguments={
                "query": "DIT fees"
            },
        )

    @patch("app.services.agent_service._execute_tool")
    @patch("app.services.agent_service.client.chat.completions.create")
    def test_runtime_blocks_eligibility_check_until_verified_search_succeeds(
        self,
        mock_create,
        mock_execute,
    ):
        mock_create.side_effect = [
            _completion(
                _tool_message(
                    "check_admission_eligibility",
                    {
                        "applicant_value": 3.5,
                        "required_value": 3.0,
                        "comparison": "gte",
                        "criterion": "Diploma GPA",
                    },
                    "eligibility_early",
                )
            ),
            _completion(
                _tool_message(
                    "search_dit_knowledge",
                    {
                        "query": "Computer Engineering diploma GPA requirement"
                    },
                    "search_1",
                )
            ),
            _completion(
                _tool_message(
                    "check_admission_eligibility",
                    {
                        "applicant_value": 3.5,
                        "required_value": 3.0,
                        "comparison": "gte",
                        "criterion": "Diploma GPA",
                    },
                    "eligibility_2",
                )
            ),
            _completion(
                _final_message(
                    "You meet this numeric criterion, but this is not a final "
                    "DIT admission decision."
                )
            ),
        ]

        mock_execute.side_effect = [
            {
                "found": True,
                "query": "Computer Engineering diploma GPA requirement",
                "context": "Verified minimum GPA is 3.0.",
                "sources": [],
            },
            {
                "found": True,
                "context": "Applicant meets this numeric criterion.",
                "sources": [],
                "eligibility": {
                    "meets_requirement": True
                },
            },
        ]

        answer, _ = run_dit_agent(
            question="Do I qualify for Computer Engineering?",
            student_state={
                "programme": "Computer Engineering",
                "qualification": "Ordinary Diploma",
                "gpa": "3.5",
                "goal": "admission eligibility",
            },
        )

        self.assertIn(
            "not a final DIT admission decision",
            answer,
        )
        self.assertEqual(
            mock_execute.call_count,
            2,
        )
        self.assertEqual(
            mock_execute.call_args_list[0].kwargs["tool_name"],
            "search_dit_knowledge",
        )
        self.assertEqual(
            mock_execute.call_args_list[1].kwargs["tool_name"],
            "check_admission_eligibility",
        )


if __name__ == "__main__":
    unittest.main()
