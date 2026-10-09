import sys
import unittest
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


from app.services.session_memory import SessionMemoryStore  # noqa: E402
from app.services.student_state import (  # noqa: E402
    extract_student_state_update,
    format_student_state_for_agent,
    merge_student_state,
)


class StudentStateExtractionTests(unittest.TestCase):

    def test_extracts_explicit_student_context(self):
        state = extract_student_state_update(
            "I want to apply for Computer Engineering. "
            "I have an Ordinary Diploma in ICT, GPA 3.5. "
            "I am interested in Mwanza campus."
        )

        self.assertEqual(
            state["programme"],
            "Computer Engineering",
        )
        self.assertEqual(
            state["qualification"].lower(),
            "ordinary diploma",
        )
        self.assertEqual(
            state["gpa"],
            "3.5",
        )
        self.assertEqual(
            state["campus"].lower(),
            "mwanza",
        )
        self.assertEqual(
            state["goal"],
            "application",
        )

    def test_missing_fields_are_not_fabricated(self):
        state = extract_student_state_update(
            "What about the fees?"
        )

        self.assertNotIn(
            "programme",
            state,
        )
        self.assertNotIn(
            "campus",
            state,
        )
        self.assertEqual(
            state["goal"],
            "fees",
        )

    def test_new_explicit_values_override_old_state(self):
        original = {
            "programme": "Computer Engineering",
            "campus": "Dar es Salaam",
            "gpa": "3.2",
        }

        updated = merge_student_state(
            original,
            {
                "programme": "Information Technology",
                "gpa": "3.6",
            },
        )

        self.assertEqual(
            updated["programme"],
            "Information Technology",
        )
        self.assertEqual(
            updated["campus"],
            "Dar es Salaam",
        )
        self.assertEqual(
            updated["gpa"],
            "3.6",
        )

    def test_agent_context_marks_state_as_unverified_user_context(self):
        context = format_student_state_for_agent(
            {
                "programme": "Computer Engineering",
                "gpa": "3.5",
            }
        )

        self.assertIn(
            "user-provided, not verified DIT facts",
            context,
        )
        self.assertIn(
            "Programme of interest: Computer Engineering",
            context,
        )
        self.assertIn(
            "GPA: 3.5",
            context,
        )
        self.assertIn(
            "Re-retrieve all factual DIT information",
            context,
        )


class StructuredSessionStateTests(unittest.TestCase):

    def setUp(self):
        self.store = SessionMemoryStore(
            max_messages=6,
            max_sessions=10,
        )

    def test_state_is_isolated_between_sessions(self):
        first = self.store.resolve_session_id()
        second = self.store.resolve_session_id()

        self.store.update_student_state_from_message(
            first,
            "I want to study Computer Engineering. GPA 3.5.",
        )

        self.assertEqual(
            self.store.get_student_state(first)["gpa"],
            "3.5",
        )
        self.assertEqual(
            self.store.get_student_state(second),
            {},
        )

    def test_current_message_overrides_previous_state(self):
        session_id = self.store.resolve_session_id()

        self.store.update_student_state_from_message(
            session_id,
            "I want to study Computer Engineering. GPA 3.2.",
        )
        state = self.store.update_student_state_from_message(
            session_id,
            "Actually I want to study Information Technology. GPA 3.7.",
        )

        self.assertEqual(
            state["programme"],
            "Information Technology",
        )
        self.assertEqual(
            state["gpa"],
            "3.7",
        )

    def test_legacy_history_initializes_structured_state(self):
        session_id = self.store.resolve_session_id()

        self.store.seed_history(
            session_id,
            [
                {
                    "role": "user",
                    "content": (
                        "I want to apply for Computer Engineering. "
                        "GPA 3.4."
                    ),
                },
                {
                    "role": "assistant",
                    "content": "How can I help?",
                },
            ],
        )

        state = self.store.get_student_state(
            session_id
        )

        self.assertEqual(
            state["programme"],
            "Computer Engineering",
        )
        self.assertEqual(
            state["gpa"],
            "3.4",
        )
        self.assertEqual(
            state["goal"],
            "application",
        )

    def test_clear_removes_structured_state_too(self):
        session_id = self.store.resolve_session_id()

        self.store.update_student_state_from_message(
            session_id,
            "I want to study Computer Engineering. GPA 3.5.",
        )

        self.assertTrue(
            self.store.clear(session_id)
        )
        self.assertEqual(
            self.store.get_student_state(session_id),
            {},
        )


if __name__ == "__main__":
    unittest.main()
