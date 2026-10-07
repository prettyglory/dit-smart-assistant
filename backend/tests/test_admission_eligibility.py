import sys
import unittest
from pathlib import Path
from types import ModuleType


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Replace retrieval dependencies so these tests stay isolated from Chroma
# and embedding packages.
fake_rag_service = ModuleType(
    "app.services.rag_service"
)
fake_rag_service.detect_categories = (
    lambda question: ["admission"]
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

from app.services.agent_tools import (  # noqa: E402
    AGENT_TOOLS,
    TOOL_HANDLERS,
    check_admission_eligibility,
)


class AdmissionEligibilityToolTests(unittest.TestCase):

    def test_meets_minimum_numeric_requirement(self):
        result = check_admission_eligibility(
            applicant_value=3.5,
            required_value=3.0,
            comparison="gte",
            criterion="Ordinary Diploma GPA",
            unit="GPA",
            programme="Bachelor of Engineering",
        )

        self.assertTrue(result["found"])
        self.assertTrue(
            result["eligibility"]["meets_requirement"]
        )
        self.assertFalse(
            result["eligibility"]["final_admission_decision"]
        )
        self.assertIn(
            "MEETS this numeric criterion",
            result["context"],
        )

    def test_does_not_meet_minimum_numeric_requirement(self):
        result = check_admission_eligibility(
            applicant_value=2.8,
            required_value=3.0,
            comparison="gte",
            criterion="Ordinary Diploma GPA",
            unit="GPA",
        )

        self.assertTrue(result["found"])
        self.assertFalse(
            result["eligibility"]["meets_requirement"]
        )
        self.assertIn(
            "DOES NOT MEET this numeric criterion",
            result["context"],
        )

    def test_rejects_invalid_comparison(self):
        result = check_admission_eligibility(
            applicant_value=3.5,
            required_value=3.0,
            comparison="approximately",
            criterion="Ordinary Diploma GPA",
        )

        self.assertFalse(result["found"])
        self.assertIn(
            "Unsupported admission comparison",
            result["context"],
        )

    def test_rejects_negative_values(self):
        result = check_admission_eligibility(
            applicant_value=-1,
            required_value=3.0,
            comparison="gte",
            criterion="Ordinary Diploma GPA",
        )

        self.assertFalse(result["found"])
        self.assertIn(
            "cannot be negative",
            result["context"],
        )

    def test_tool_is_registered_for_agent_use(self):
        tool_names = {
            tool["function"]["name"]
            for tool in AGENT_TOOLS
        }

        self.assertIn(
            "check_admission_eligibility",
            tool_names,
        )
        self.assertIs(
            TOOL_HANDLERS["check_admission_eligibility"],
            check_admission_eligibility,
        )


if __name__ == "__main__":
    unittest.main()
