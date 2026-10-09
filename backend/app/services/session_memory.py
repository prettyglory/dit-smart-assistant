from __future__ import annotations

from datetime import datetime, timedelta, timezone
from threading import RLock
from uuid import UUID, uuid4

from app.services.student_state import (
    extract_student_state_update,
    merge_student_state,
)


MAX_SESSION_MESSAGES = 12
MAX_SESSIONS = 500
SESSION_TTL = timedelta(hours=2)


class SessionMemoryStore:
    """Thread-safe, bounded, in-process conversation and student state memory.

    This is intentionally short-term session state. It is suitable for the
    current single-process demo architecture and can later be replaced by
    Redis or a database without changing the agent API contract.
    """

    def __init__(
        self,
        max_messages: int = MAX_SESSION_MESSAGES,
        max_sessions: int = MAX_SESSIONS,
        ttl: timedelta = SESSION_TTL,
    ) -> None:
        self.max_messages = max_messages
        self.max_sessions = max_sessions
        self.ttl = ttl
        self._sessions: dict[str, dict] = {}
        self._lock = RLock()

    @staticmethod
    def _now() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _is_valid_session_id(session_id: str | None) -> bool:
        if not session_id:
            return False

        try:
            UUID(session_id)
        except (ValueError, TypeError, AttributeError):
            return False

        return True

    @staticmethod
    def _new_session(now: datetime) -> dict:
        return {
            "messages": [],
            "student_state": {},
            "updated_at": now,
        }

    def _prune_expired(self, now: datetime) -> None:
        expired = [
            session_id
            for session_id, session in self._sessions.items()
            if now - session["updated_at"] > self.ttl
        ]

        for session_id in expired:
            self._sessions.pop(session_id, None)

    def _prune_capacity(self) -> None:
        overflow = len(self._sessions) - self.max_sessions
        if overflow <= 0:
            return

        oldest = sorted(
            self._sessions.items(),
            key=lambda item: item[1]["updated_at"],
        )[:overflow]

        for session_id, _ in oldest:
            self._sessions.pop(session_id, None)

    def resolve_session_id(self, session_id: str | None = None) -> str:
        """Return a valid session id and ensure a memory bucket exists."""

        resolved = (
            session_id
            if self._is_valid_session_id(session_id)
            else str(uuid4())
        )

        now = self._now()

        with self._lock:
            self._prune_expired(now)

            if resolved not in self._sessions:
                self._sessions[resolved] = self._new_session(now)

            self._sessions[resolved]["updated_at"] = now
            self._prune_capacity()

        return resolved

    def get_history(self, session_id: str) -> list[dict]:
        """Return a defensive copy of the current session transcript."""

        if not self._is_valid_session_id(session_id):
            return []

        now = self._now()

        with self._lock:
            self._prune_expired(now)
            session = self._sessions.get(session_id)

            if session is None:
                return []

            session["updated_at"] = now

            return [
                dict(message)
                for message in session["messages"]
            ]

    def get_student_state(self, session_id: str) -> dict:
        """Return a defensive copy of structured user-provided session state."""

        if not self._is_valid_session_id(session_id):
            return {}

        now = self._now()

        with self._lock:
            self._prune_expired(now)
            session = self._sessions.get(session_id)

            if session is None:
                return {}

            session["updated_at"] = now
            return dict(
                session.get(
                    "student_state",
                    {},
                )
            )

    def update_student_state(
        self,
        session_id: str,
        update: dict,
    ) -> dict:
        """Merge explicit structured context into a session and return a copy."""

        now = self._now()

        with self._lock:
            self._prune_expired(now)
            session = self._sessions.setdefault(
                session_id,
                self._new_session(now),
            )

            session["student_state"] = merge_student_state(
                session.get(
                    "student_state",
                    {},
                ),
                update,
            )
            session["updated_at"] = now
            self._prune_capacity()

            return dict(
                session["student_state"]
            )

    def update_student_state_from_message(
        self,
        session_id: str,
        message: str,
    ) -> dict:
        """Extract explicit user context from one message and merge it."""

        update = extract_student_state_update(
            message
        )

        if not update:
            return self.get_student_state(
                session_id
            )

        return self.update_student_state(
            session_id=session_id,
            update=update,
        )

    def seed_history(
        self,
        session_id: str,
        history: list[dict],
    ) -> None:
        """Seed a new session from the legacy client-supplied history.

        Existing server-side history always wins, which prevents the client
        from accidentally duplicating messages on every request. User messages
        in a newly seeded transcript also initialize structured student state.
        """

        clean_history = []
        seeded_state = {}

        for item in history:
            role = str(item.get("role", "")).strip()
            content = str(item.get("content", "")).strip()

            if role not in {"user", "assistant"} or not content:
                continue

            clean_history.append(
                {
                    "role": role,
                    "content": content,
                }
            )

            if role == "user":
                seeded_state = merge_student_state(
                    seeded_state,
                    extract_student_state_update(
                        content
                    ),
                )

        if not clean_history:
            return

        now = self._now()

        with self._lock:
            self._prune_expired(now)
            session = self._sessions.get(session_id)

            if session is None:
                session = self._new_session(now)
                self._sessions[session_id] = session

            if session["messages"]:
                return

            session["messages"] = clean_history[-self.max_messages :]
            session["student_state"] = merge_student_state(
                session.get(
                    "student_state",
                    {},
                ),
                seeded_state,
            )
            session["updated_at"] = now
            self._prune_capacity()

    def append_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_message: str,
    ) -> None:
        """Persist one user/assistant turn in bounded short-term memory."""

        now = self._now()

        with self._lock:
            self._prune_expired(now)
            session = self._sessions.setdefault(
                session_id,
                self._new_session(now),
            )

            if user_message.strip():
                session["messages"].append(
                    {
                        "role": "user",
                        "content": user_message.strip(),
                    }
                )

            if assistant_message.strip():
                session["messages"].append(
                    {
                        "role": "assistant",
                        "content": assistant_message.strip(),
                    }
                )

            session["messages"] = session["messages"][-self.max_messages :]
            session["updated_at"] = now
            self._prune_capacity()

    def clear(self, session_id: str) -> bool:
        """Delete one session from short-term memory."""

        with self._lock:
            return self._sessions.pop(session_id, None) is not None


session_memory = SessionMemoryStore()
