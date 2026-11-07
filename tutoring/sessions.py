"""In-memory tutoring with deterministic grading and a small adaptive policy."""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
import time
from typing import Any
import uuid

from tutoring.algebra import DEFAULT_PROBLEM_ID, PROBLEMS, verify_answer


class SessionConflict(ValueError):
    """A stale or currently unavailable tutoring action."""


@dataclass
class Session:
    id: str
    problem_id: str
    touched: float = field(default_factory=time.monotonic)
    revision: int = 0
    round_number: int = 1
    attempts: int = 0
    hint_level: int = 0
    assisted: bool = False
    solved: bool = False
    finished: bool = False
    completed: list[str] = field(default_factory=list)
    return_to: list[str] = field(default_factory=list)
    history: list[dict[str, Any]] = field(default_factory=list)
    feedback: str = "Try solving the equation. You can ask for a hint when you need one."
    last_verification: dict[str, Any] | None = None


class SessionStore:
    """Single-process demo storage: bounded sessions, turns, and idle lifetime."""

    def __init__(self, max_sessions: int = 256, ttl_seconds: float = 3600) -> None:
        self.max_sessions = max_sessions
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._lock = RLock()

    def create(self, problem_id: str = DEFAULT_PROBLEM_ID) -> dict[str, Any]:
        if problem_id not in PROBLEMS:
            raise ValueError("Unknown problem ID.")
        with self._lock:
            now = time.monotonic()
            for key in list(self._sessions):
                if now - self._sessions[key].touched >= self.ttl_seconds:
                    del self._sessions[key]
            if len(self._sessions) >= self.max_sessions:
                raise SessionConflict("The demo session limit was reached. Close a session or try later.")
            session = Session(id=str(uuid.uuid4()), problem_id=problem_id)
            self._sessions[session.id] = session
            self._record(session, "session_started", problem_id=problem_id)
            return self._snapshot(session)

    def get(self, session_id: str) -> dict[str, Any]:
        with self._lock:
            return self._snapshot(self._get(session_id))

    def delete(self, session_id: str) -> None:
        with self._lock:
            self._get(session_id)
            del self._sessions[session_id]

    def _get(self, session_id: str) -> Session:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError("Session not found or expired. Start a new session.")
        if time.monotonic() - session.touched >= self.ttl_seconds:
            del self._sessions[session_id]
            raise KeyError("Session not found or expired. Start a new session.")
        session.touched = time.monotonic()
        return session

    def _check(self, session: Session, revision: int) -> None:
        if session.revision != revision:
            raise SessionConflict("Session changed. Refresh it before submitting another action.")
        if session.finished:
            raise SessionConflict("This practice session is finished. Start a new session.")
        if len(session.history) >= 200:
            raise SessionConflict("This demo session reached its turn limit. Start a new session.")

    def attempt(self, session_id: str, problem_id: str, answer: str, revision: int) -> dict[str, Any]:
        with self._lock:
            session = self._get(session_id)
            self._check(session, revision)
            if session.solved or session.problem_id != problem_id:
                raise SessionConflict("That problem is no longer awaiting an answer. Refresh the session.")
            # This call, not an LLM response or client field, is the grading gate.
            verification = verify_answer(session.problem_id, answer)
            status = verification["status"]
            session.last_verification = verification
            session.feedback = verification["message"]
            if status in {"correct", "incorrect"}:
                session.attempts += 1
            if status == "correct":
                session.solved = True
                if session.problem_id not in session.completed:
                    session.completed.append(session.problem_id)
                independent = not session.assisted and session.attempts == 1
                session.feedback += " Solved independently on the first attempt." if independent else " Good recovery. Try a fresh problem without help next."
            elif status == "incorrect":
                session.assisted = True
                session.feedback += " Show your working or request a hint; this answer alone does not identify a misconception."
                if self._can_remediate(session):
                    session.feedback += " You can also switch to a simpler prerequisite problem."
            session.revision += 1
            self._record(session, "answer_checked", problem_id=problem_id, answer=answer,
                         attempt=session.attempts, verification=verification,
                         independent_success=status == "correct" and not session.assisted and session.attempts == 1)
            return self._snapshot(session)

    def hint(self, session_id: str, revision: int) -> dict[str, Any]:
        with self._lock:
            session = self._get(session_id)
            self._check(session, revision)
            hints = PROBLEMS[session.problem_id].hints
            if session.solved or session.hint_level >= len(hints):
                raise SessionConflict("No further hint is available for this problem.")
            session.feedback = hints[session.hint_level]
            session.hint_level += 1
            session.assisted = True
            session.revision += 1
            self._record(session, "hint_given", problem_id=session.problem_id, hint_level=session.hint_level,
                         hint=session.feedback)
            return self._snapshot(session)

    def advance(self, session_id: str, revision: int) -> dict[str, Any]:
        with self._lock:
            session = self._get(session_id)
            self._check(session, revision)
            assisted = False
            if session.solved:
                if session.return_to:
                    next_id = session.return_to.pop()
                    reason = "return_after_prerequisite"
                    assisted = True
                else:
                    current = PROBLEMS[session.problem_id]
                    remaining = [p for p in PROBLEMS.values() if p.id not in session.completed]
                    remaining.sort(key=lambda p: (p.topic != current.topic, abs(p.difficulty - current.difficulty), p.id))
                    next_id = remaining[0].id if remaining else None
                    reason = "fresh_practice"
            elif self._can_remediate(session):
                next_id = PROBLEMS[session.problem_id].prerequisite
                session.return_to.append(session.problem_id)
                reason = "prerequisite_review"
            else:
                raise SessionConflict("Check an answer first. Advance after a correct answer or two incorrect attempts.")
            session.revision += 1
            self._record(session, "problem_transition", from_problem=session.problem_id, to_problem=next_id, reason=reason)
            if next_id is None:
                session.finished = True
                session.feedback = "You have completed this eight-problem practice bank. This is practice evidence, not a mastery certification."
            else:
                session.problem_id = next_id
                session.round_number += 1
                session.attempts = 0
                session.hint_level = 0
                session.assisted = assisted
                session.solved = False
                session.last_verification = None
                session.feedback = {
                    "return_after_prerequisite": "Now return to the original problem using what you practiced.",
                    "fresh_practice": "Try this fresh problem without hints to check independent success.",
                    "prerequisite_review": "Practice this simpler prerequisite first; then we will return to your original problem.",
                }[reason]
            return self._snapshot(session)

    def _can_remediate(self, session: Session) -> bool:
        return not session.solved and session.attempts >= 2 and PROBLEMS[session.problem_id].prerequisite is not None

    def _record(self, session: Session, event: str, **data: Any) -> None:
        session.history.append({"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **data})

    def _snapshot(self, session: Session) -> dict[str, Any]:
        problem = PROBLEMS[session.problem_id]
        return deepcopy({
            "session_id": session.id,
            "revision": session.revision,
            "round": session.round_number,
            "problem": problem.public(),
            "attempts": session.attempts,
            "hint_level": session.hint_level,
            "solved": session.solved,
            "finished": session.finished,
            "completed_problem_ids": session.completed,
            "feedback": session.feedback,
            "verification": session.last_verification,
            "can_hint": not session.solved and not session.finished and session.hint_level < len(problem.hints),
            "can_advance": not session.finished and (session.solved or self._can_remediate(session)),
            "history": session.history,
        })
