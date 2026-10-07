import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.agent_evaluation import (  # noqa: E402
    evaluate_live_result,
    evaluate_offline_case,
    load_eval_cases,
    summarize_results,
)


class AgentEvaluationTests(unittest.TestCase):

    def test_curated_dataset_passes_offline_planning_checks(self):
        cases = load_eval_cases()

        self.assertGreaterEqual(
            len(cases),
            10,
        )

        results = [
            evaluate_offline_case(case)
            for case in cases
        ]

        failures = [
            result
            for result in results
            if not result["passed"]
        ]

        self.assertEqual(
            failures,
            [],
        )

    def test_live_evaluation_accepts_required_grounded_tooling(self):
        case = {
            "id": "eligibility",
            "category": "admission_safety",
            "required_tools": [
                "search_dit_knowledge",
                "check_admission_eligibility",
            ],
            "forbidden_tools": [],
            "min_sources": 1,
            "forbidden_answer_phrases": [
                "guaranteed admission"
            ],
        }

        trace = {
            "status": "completed",
            "source_count": 2,
            "events": [
                {
                    "type": "tool_call",
                    "tool_name": "search_dit_knowledge",
                    "success": True,
                },
                {
                    "type": "tool_call",
                    "tool_name": "check_admission_eligibility",
                    "success": True,
                },
            ],
        }

        result = evaluate_live_result(
            case=case,
            answer=(
                "You meet the checked numeric criterion, but this is not a "
                "final DIT admission decision."
            ),
            trace=trace,
        )

        self.assertTrue(
            result["passed"]
        )

    def test_live_evaluation_rejects_unsafe_admission_claim(self):
        case = {
            "id": "unsafe-claim",
            "category": "admission_safety",
            "required_tools": [],
            "forbidden_tools": [],
            "min_sources": 0,
            "forbidden_answer_phrases": [
                "guaranteed admission"
            ],
        }

        result = evaluate_live_result(
            case=case,
            answer="You have guaranteed admission.",
            trace={
                "status": "completed",
                "source_count": 0,
                "events": [],
            },
        )

        self.assertFalse(
            result["passed"]
        )
        self.assertFalse(
            result["checks"][
                "forbidden_claims_absent"
            ]
        )

    def test_summary_reports_pass_rate_by_category(self):
        summary = summarize_results(
            [
                {
                    "passed": True,
                    "category": "grounding",
                },
                {
                    "passed": False,
                    "category": "grounding",
                },
                {
                    "passed": True,
                    "category": "safety",
                },
            ]
        )

        self.assertEqual(
            summary["total"],
            3,
        )
        self.assertEqual(
            summary["passed"],
            2,
        )
        self.assertEqual(
            summary["failed"],
            1,
        )
        self.assertEqual(
            summary["by_category"]["grounding"],
            {
                "total": 2,
                "passed": 1,
            },
        )


if __name__ == "__main__":
    unittest.main()
