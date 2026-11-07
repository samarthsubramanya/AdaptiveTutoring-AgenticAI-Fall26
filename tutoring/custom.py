"""Immutable model-interpreted cases, bound to server-side math specifications."""

from copy import deepcopy
from dataclasses import dataclass, field
from threading import RLock
import time
import uuid

from tutoring.model import Proposal
from tutoring.sessions import SessionConflict
from tutoring.symbolic import check, public_problem, target


@dataclass
class Case:
    id: str
    prompt: str
    proposal: Proposal
    touched: float = field(default_factory=time.monotonic)
    answer: str | None = None
    verification: dict | None = None
    hints: list[str] = field(default_factory=list)
    checks: int = 0


class CaseStore:
    def __init__(self):
        self._cases: dict[str, Case] = {}
        self._lock = RLock()

    def create(self, prompt: str, proposal: Proposal) -> dict:
        # Reject unsupported model output before storing or offering verification.
        target(proposal.problem)
        with self._lock:
            now = time.monotonic()
            for key in list(self._cases):
                if now - self._cases[key].touched >= 3600:
                    del self._cases[key]
            if len(self._cases) >= 128:
                raise SessionConflict("The custom-problem limit was reached. Close a case or try later.")
            case = Case(id=str(uuid.uuid4()), prompt=prompt, proposal=proposal.model_copy(deep=True))
            self._cases[case.id] = case
            return self._public(case)

    def _get(self, case_id: str) -> Case:
        case = self._cases.get(case_id)
        if case is None or time.monotonic() - case.touched >= 3600:
            self._cases.pop(case_id, None)
            raise KeyError("Custom problem not found or expired. Prepare it again.")
        case.touched = time.monotonic()
        return case

    def get(self, case_id: str) -> dict:
        with self._lock:
            return self._public(self._get(case_id))

    def verify(self, case_id: str, answer: str) -> dict:
        with self._lock:
            case = self._get(case_id)
            if case.checks >= 50:
                raise SessionConflict("This case reached its answer-check limit. Prepare a new case.")
            case.verification = check(case.proposal.problem, answer)
            case.answer = answer
            case.checks += 1
            return self._public(case)

    def add_hint(self, case_id: str, hint: str) -> dict:
        with self._lock:
            case = self._get(case_id)
            if len(case.hints) >= 3:
                raise SessionConflict("Three hints have already been provided for this case.")
            case.hints.append(hint)
            return self._public(case)

    def delete(self, case_id: str) -> None:
        with self._lock:
            self._get(case_id)
            del self._cases[case_id]

    def _public(self, case: Case) -> dict:
        return deepcopy({
            "case_id": case.id, "question": case.prompt,
            "problem": public_problem(case.proposal.problem),
            "proposed_answer": case.proposal.proposed_answer,
            "explanation": case.proposal.explanation,
            "answer": case.answer, "verification": case.verification,
            "hints": case.hints,
            "notice": "SymPy verification applies to the displayed interpretation. Review it against your original question. LLM explanation steps are not individually verified.",
        })
