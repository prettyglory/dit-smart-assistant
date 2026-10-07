import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# Keep these tests independent from the production RAG dependencies.
fake_agent_tools = ModuleType(
    "app.services.agent_tools"
)
fake_agent_tools.search_dit_knowledge = (
    lambda **kwargs: {
        "found": False,
        "context": "No data.",
        "sources": [],
    }
)
sys.modules[
    "app.services.agent_tools"
] = fake_agent_tools


from app.services.programme_comparison_tool import (  # noqa: E402
    PROGRAMME_COMPARISON_TOOL,
    compare_dit_programmes,
)


class ProgrammeComparisonTests(unittest.TestCase):

    def test_tool_schema_requires_at_least_two_programmes(self):
        parameters = (
            PROGRAMME_COMPARISON_TOOL
            ["function"]
            ["parameters"]
        )

        programmes = parameters[
            "properties"
        ]["programmes"]

        self.assertEqual(
            programmes["minItems"],
            2,
        )
        self.assertEqual(
            programmes["maxItems"],
            4,
        )

    def test_comparison_requires_two_distinct_programmes(self):
        result = compare_dit_programmes(
            [
                "Computer Engineering",
                "computer engineering",
            ]
        )

        self.assertFalse(
            result["found"]
        )
        self.assertIn(
            "At least two distinct",
            result["context"],
        )

    @patch(
        "app.services.programme_comparison_tool.search_dit_knowledge"
    )
    def test_default_comparison_searches_all_supported_aspects(
        self,
        mock_search,
    ):
        mock_search.return_value = {
            "found": True,
            "context": "Verified DIT programme information.",
            "sources": [
                {
                    "title": "DIT Prospectus",
                    "url": "https://example.com/prospectus",
                    "campus": "all",
                    "page": 12,
                }
            ],
        }

        result = compare_dit_programmes(
            [
                "Computer Engineering",
                "Information Technology",
            ]
        )

        self.assertTrue(
            result["found"]
        )

        # 2 programmes x 4 default aspects.
        self.assertEqual(
            mock_search.call_count,
            8,
        )

        comparison = result[
            "programme_comparison"
        ]

        self.assertEqual(
            comparison["aspects"],
            [
                "overview",
                "campus",
                "admission",
                "fees",
            ],
        )

        # The same source returned by multiple searches is shown once.
        self.assertEqual(
            len(result["sources"]),
            1,
        )

    @patch(
        "app.services.programme_comparison_tool.search_dit_knowledge"
    )
    def test_selected_aspects_limit_retrieval_work(
        self,
        mock_search,
    ):
        mock_search.return_value = {
            "found": True,
            "context": "Verified campus information.",
            "sources": [],
        }

        result = compare_dit_programmes(
            [
                "Computer Engineering",
                "Information Technology",
            ],
            aspects=[
                "campus",
                "fees",
            ],
        )

        self.assertTrue(
            result["found"]
        )
        self.assertEqual(
            mock_search.call_count,
            4,
        )
        self.assertEqual(
            result[
                "programme_comparison"
            ]["aspects"],
            [
                "campus",
                "fees",
            ],
        )

    @patch(
        "app.services.programme_comparison_tool.search_dit_knowledge"
    )
    def test_missing_aspect_is_preserved_as_unverified(
        self,
        mock_search,
    ):
        mock_search.side_effect = [
            {
                "found": True,
                "context": "Verified campus information.",
                "sources": [],
            },
            {
                "found": False,
                "context": "No verified fee information found.",
                "sources": [],
            },
            {
                "found": True,
                "context": "Verified campus information.",
                "sources": [],
            },
            {
                "found": False,
                "context": "No verified fee information found.",
                "sources": [],
            },
        ]

        result = compare_dit_programmes(
            [
                "Computer Engineering",
                "Information Technology",
            ],
            aspects=[
                "campus",
                "fees",
            ],
        )

        self.assertTrue(
            result["found"]
        )

        computer = (
            result
            ["programme_comparison"]
            ["results"]
            ["Computer Engineering"]
        )

        self.assertTrue(
            computer["campus"]["found"]
        )
        self.assertFalse(
            computer["fees"]["found"]
        )
        self.assertIn(
            "No verified fee information",
            computer["fees"]["context"],
        )

    def test_unsupported_aspects_fail_safely(self):
        result = compare_dit_programmes(
            [
                "Computer Engineering",
                "Information Technology",
            ],
            aspects=["ranking"],
        )

        self.assertFalse(
            result["found"]
        )
        self.assertIn(
            "No supported comparison aspects",
            result["context"],
        )


if __name__ == "__main__":
    unittest.main()
