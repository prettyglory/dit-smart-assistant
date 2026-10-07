import os
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# app.config validates the key at import time. Tests never call the real API.
os.environ.setdefault("GROQ_API_KEY", "test-key")

# Keep unit tests independent from installed third-party packages and from
# external services. Production integrations are replaced with tiny stand-ins
# before importing the agent modules.
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

from app.services.agent_service import (  # noqa: E402
    MAX_AGENT_ITERATIONS,
    run_dit_agent,
)
from app.services.agent_tools import (  # noqa: E402
    search_dit_knowledge,
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
    query="DIT programmes",
    call_id="call_1",
):
    return SimpleNamespace(
        content=None,
        tool_calls=[
            SimpleNamespace(
                id=call_id,
                function=SimpleNamespace(
                    name="search_dit_knowledge",
                    arguments=(
                        '{"query": "'
                        + query
                        + '"}'
                    ),
                ),
            )
        ],
    )


class SearchDITKnowledgeTests(unittest.TestCase):

    @patch("app.services.agent_tools.search_knowledge")
    def test_search_returns_verified_context_and_unique_sources(
        self,
        mock_search,
    ):
        mock_search.return_value = [
            {
                "document": "Bachelor programmes are listed here.",
                "metadata": {
                    "source_title": "DIT Prospectus",
                    "source_url": "https://example.com/prospectus",
                    "campus": "all",
                    "category": "programme",
                    "page": 10,
                },
                "distance": 0.1,
            },
            {
                "document": "More details from the same page.",
                "metadata": {
                    "source_title": "DIT Prospectus",
                    "source_url": "https://example.com/prospectus",
                    "campus": "all",
                    "category": "programme",
                    "page": 10,
                },
                "distance": 0.2,
            },
        ]

        result = search_dit_knowledge(
            "DIT bachelor programmes"
        )

        self.assertTrue(result["found"])
        self.assertIn(
            "VERIFIED DIT SOURCE 1",
            result["context"],
        )
        self.assertIn(
            "Bachelor programmes are listed here.",
            result["context"],
        )
        self.assertEqual(len(result["sources"]), 1)
        self.assertEqual(
            result["sources"][0]["title"],
            "DIT Prospectus",
        )

    @patch("app.services.agent_tools.search_knowledge")
    def test_empty_search_result_is_reported_safely(
        self,
        mock_search,
    ):
        mock_search.return_value = []

        result = search_dit_knowledge(
            "unknown DIT fact"
        )

        self.assertFalse(result["found"])
        self.assertEqual(result["sources"], [])
        self.assertIn(
            "No sufficiently relevant information",
            result["context"],
        )


class DITAgentLoopTests(unittest.TestCase):

    @patch("app.services.agent_service.client.chat.completions.create")
    def test_agent_can_answer_conversation_without_tool(
        self,
        mock_create,
    ):
        mock_create.return_value = _completion(
            _final_message(
                "Hello! How can I help you with DIT today?"
            )
        )

        answer, sources = run_dit_agent(
            "Hello"
        )

        self.assertIn("Hello", answer)
        self.assertEqual(sources, [])
        self.assertEqual(mock_create.call_count, 1)

    @patch("app.services.agent_service._execute_tool")
    @patch("app.services.agent_service.client.chat.completions.create")
    def test_agent_executes_tool_then_returns_grounded_answer(
        self,
        mock_create,
        mock_execute,
    ):
        mock_create.side_effect = [
            _completion(
                _tool_message(
                    query="DIT programmes"
                )
            ),
            _completion(
                _final_message(
                    "DIT offers the programmes found in the verified source."
                )
            ),
        ]

        mock_execute.return_value = {
            "found": True,
            "query": "DIT programmes",
            "context": "Verified programme information.",
            "sources": [
                {
                    "title": "DIT Prospectus",
                    "url": "https://example.com/prospectus",
                    "campus": "all",
                    "page": 10,
                }
            ],
        }

        answer, sources = run_dit_agent(
            "What programmes does DIT offer?"
        )

        self.assertIn("DIT offers", answer)
        self.assertEqual(mock_create.call_count, 2)
        mock_execute.assert_called_once_with(
            tool_name="search_dit_knowledge",
            arguments={
                "query": "DIT programmes"
            },
        )
        self.assertEqual(len(sources), 1)
        self.assertEqual(
            sources[0]["title"],
            "DIT Prospectus",
        )

    @patch("app.services.agent_service._execute_tool")
    @patch("app.services.agent_service.client.chat.completions.create")
    def test_sources_are_deduplicated_across_multiple_tool_calls(
        self,
        mock_create,
        mock_execute,
    ):
        mock_create.side_effect = [
            _completion(
                _tool_message(
                    query="DIT programmes",
                    call_id="call_1",
                )
            ),
            _completion(
                _tool_message(
                    query="DIT fees",
                    call_id="call_2",
                )
            ),
            _completion(
                _final_message(
                    "Here is the verified combined answer."
                )
            ),
        ]

        source = {
            "title": "DIT Prospectus",
            "url": "https://example.com/prospectus",
            "campus": "all",
            "page": 10,
        }

        mock_execute.side_effect = [
            {
                "found": True,
                "query": "DIT programmes",
                "context": "Programme information.",
                "sources": [source],
            },
            {
                "found": True,
                "query": "DIT fees",
                "context": "Fee information.",
                "sources": [source],
            },
        ]

        _, sources = run_dit_agent(
            "Tell me about programmes and fees."
        )

        self.assertEqual(len(sources), 1)
        self.assertEqual(mock_execute.call_count, 2)

    @patch("app.services.agent_service._execute_tool")
    @patch("app.services.agent_service.client.chat.completions.create")
    def test_agent_stops_after_maximum_iterations(
        self,
        mock_create,
        mock_execute,
    ):
        mock_create.return_value = _completion(
            _tool_message()
        )
        mock_execute.return_value = {
            "found": False,
            "query": "DIT programmes",
            "context": "No data.",
            "sources": [],
        }

        answer, sources = run_dit_agent(
            "Keep searching forever"
        )

        self.assertIn(
            "allowed number of agent steps",
            answer,
        )
        self.assertEqual(sources, [])
        self.assertEqual(
            mock_create.call_count,
            MAX_AGENT_ITERATIONS,
        )


if __name__ == "__main__":
    unittest.main()
