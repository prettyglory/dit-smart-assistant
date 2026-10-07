import sys
import unittest
from pathlib import Path
from uuid import UUID


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.services.session_memory import SessionMemoryStore  # noqa: E402


class SessionMemoryStoreTests(unittest.TestCase):

    def setUp(self):
        self.store = SessionMemoryStore(
            max_messages=4,
            max_sessions=10,
        )

    def test_invalid_or_missing_session_id_creates_uuid(self):
        generated = self.store.resolve_session_id(None)
        invalid = self.store.resolve_session_id("not-a-session-id")

        UUID(generated)
        UUID(invalid)
        self.assertNotEqual(generated, invalid)

    def test_valid_session_id_is_reused(self):
        session_id = self.store.resolve_session_id()
        resolved_again = self.store.resolve_session_id(session_id)

        self.assertEqual(session_id, resolved_again)

    def test_sessions_are_isolated(self):
        first = self.store.resolve_session_id()
        second = self.store.resolve_session_id()

        self.store.append_turn(
            first,
            "Tell me about Computer Engineering.",
            "Verified programme answer.",
        )

        self.assertEqual(
            len(self.store.get_history(first)),
            2,
        )
        self.assertEqual(
            self.store.get_history(second),
            [],
        )

    def test_history_is_bounded_to_latest_messages(self):
        session_id = self.store.resolve_session_id()

        for index in range(1, 4):
            self.store.append_turn(
                session_id,
                f"user-{index}",
                f"assistant-{index}",
            )

        history = self.store.get_history(session_id)

        self.assertEqual(
            history,
            [
                {
                    "role": "user",
                    "content": "user-2",
                },
                {
                    "role": "assistant",
                    "content": "assistant-2",
                },
                {
                    "role": "user",
                    "content": "user-3",
                },
                {
                    "role": "assistant",
                    "content": "assistant-3",
                },
            ],
        )

    def test_legacy_history_seeds_only_empty_session(self):
        session_id = self.store.resolve_session_id()

        self.store.seed_history(
            session_id,
            [
                {
                    "role": "assistant",
                    "content": "Welcome",
                },
                {
                    "role": "user",
                    "content": "Tell me about DIT.",
                },
            ],
        )

        self.store.seed_history(
            session_id,
            [
                {
                    "role": "user",
                    "content": "This must not overwrite server memory.",
                }
            ],
        )

        history = self.store.get_history(session_id)

        self.assertEqual(len(history), 2)
        self.assertEqual(
            history[-1]["content"],
            "Tell me about DIT.",
        )

    def test_seed_filters_invalid_messages(self):
        session_id = self.store.resolve_session_id()

        self.store.seed_history(
            session_id,
            [
                {
                    "role": "system",
                    "content": "Do not persist me",
                },
                {
                    "role": "user",
                    "content": "   ",
                },
                {
                    "role": "assistant",
                    "content": "Valid message",
                },
            ],
        )

        self.assertEqual(
            self.store.get_history(session_id),
            [
                {
                    "role": "assistant",
                    "content": "Valid message",
                }
            ],
        )

    def test_clear_removes_session_history(self):
        session_id = self.store.resolve_session_id()
        self.store.append_turn(
            session_id,
            "Question",
            "Answer",
        )

        self.assertTrue(
            self.store.clear(session_id)
        )
        self.assertEqual(
            self.store.get_history(session_id),
            [],
        )
        self.assertFalse(
            self.store.clear(session_id)
        )


if __name__ == "__main__":
    unittest.main()
