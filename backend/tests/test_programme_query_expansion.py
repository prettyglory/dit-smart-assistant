import sys
import unittest
from pathlib import Path
from types import ModuleType
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.services.retrieval_query_expansion import (  # noqa: E402
    canonical_programme_query,
    detect_campus_hint,
    enrich_categories,
    expand_dit_search_queries,
    looks_like_programme_query,
)


class ProgrammeQueryExpansionTests(unittest.TestCase):

    def test_leather_product_singular_normalizes_to_verified_name(self):
        query = "Tell me about leather product technology at DIT"

        normalized = canonical_programme_query(query)

        self.assertIn(
            "Leather Products Technology",
            normalized,
        )

    def test_leather_programme_is_detected_as_programme_query(self):
        self.assertTrue(
            looks_like_programme_query(
                "Tell me about leather product technology at DIT"
            )
        )

    def test_programme_category_is_added_when_old_detector_misses_name(self):
        categories = enrich_categories(
            "Tell me about leather product technology at DIT",
            [],
        )

        self.assertEqual(
            categories,
            ["programme"],
        )

    def test_explicit_campus_adds_campus_category(self):
        categories = enrich_categories(
            "Leather Products Technology at Mwanza campus",
            ["programme"],
        )

        self.assertEqual(
            categories,
            ["programme", "campus"],
        )
        self.assertEqual(
            detect_campus_hint(
                "Leather Products Technology at Mwanza campus"
            ),
            "Mwanza",
        )

    def test_expansion_keeps_original_and_canonical_queries(self):
        queries = expand_dit_search_queries(
            "Tell me about leather product technology at DIT"
        )

        self.assertEqual(
            queries[0],
            "Tell me about leather product technology at DIT",
        )
        self.assertTrue(
            any(
                "Leather Products Technology" in query
                for query in queries[1:]
            )
        )


class ProgrammeSearchIntegrationTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        fake_rag = ModuleType("app.services.rag_service")
        fake_rag.detect_categories = lambda query: []
        sys.modules[
            "app.services.rag_service"
        ] = fake_rag

        fake_vector = ModuleType("app.services.vector_store")
        fake_vector.search_knowledge = lambda **kwargs: []
        sys.modules[
            "app.services.vector_store"
        ] = fake_vector

        from app.services import agent_tools

        cls.agent_tools = agent_tools

    @patch(
        "app.services.agent_tools.search_knowledge"
    )
    def test_search_uses_canonical_programme_variant_and_returns_mwanza_source(
        self,
        mock_search,
    ):
        def fake_search(**kwargs):
            question = kwargs["question"]

            if "Leather Products Technology" not in question:
                return []

            return [
                {
                    "document": (
                        "Ordinary Diploma programmes include: "
                        "Leather Products Technology."
                    ),
                    "metadata": {
                        "source_title": "DIT Official Website - Mwanza Campus",
                        "source_url": "https://www.dit.ac.tz/mwanza",
                        "campus": "Mwanza",
                        "category": "programme",
                    },
                    "distance": 0.2,
                }
            ]

        mock_search.side_effect = fake_search

        result = self.agent_tools.search_dit_knowledge(
            "Tell me about leather product technology at DIT"
        )

        self.assertTrue(
            result["found"]
        )
        self.assertIn(
            "Leather Products Technology",
            result["context"],
        )
        self.assertEqual(
            result["sources"][0]["campus"],
            "Mwanza",
        )

        for call in mock_search.call_args_list:
            self.assertIn(
                "programme",
                call.kwargs["categories"],
            )


if __name__ == "__main__":
    unittest.main()
