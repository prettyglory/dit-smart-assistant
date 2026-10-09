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


class _FakeGroq:
    def __init__(self, *args, **kwargs):
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(
                create=lambda **kwargs: "completion"
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


from app.services import agent_service  # noqa: E402


class AgentRuntimeRetryTests(unittest.TestCase):

    @patch(
        "app.services.agent_service.run_with_rate_limit_retry"
    )
    @patch(
        "app.services.agent_service.client.chat.completions.create"
    )
    def test_model_completion_runs_through_rate_limit_guard(
        self,
        mock_create,
        mock_retry,
    ):
        sentinel = object()
        mock_create.return_value = sentinel

        def execute_operation(operation, **kwargs):
            self.assertEqual(
                kwargs["max_retries"],
                3,
            )
            self.assertEqual(
                kwargs["fallback_seconds"],
                25.0,
            )
            return operation()

        mock_retry.side_effect = execute_operation

        request = {
            "model": "test-model",
            "messages": [
                {
                    "role": "user",
                    "content": "Hello",
                }
            ],
        }

        result = agent_service._create_model_completion(
            request
        )

        self.assertIs(
            result,
            sentinel,
        )
        mock_retry.assert_called_once()
        mock_create.assert_called_once_with(
            **request
        )


if __name__ == "__main__":
    unittest.main()
