"""Offline regression coverage for grading and the enforced tutoring policy."""

from concurrent.futures import ThreadPoolExecutor

import pytest
import sympy as sp

from tutoring import algebra
from tutoring.algebra import PROBLEMS, list_problems, verify_answer
from tutoring.sessions import SessionConflict, SessionStore


ANSWERS = {
    "linear-01": "6", "linear-02": "5", "linear-03": "6", "linear-04": "2",
    "linear-05": "3/2", "distribution-01": "6", "distribution-02": "6", "distribution-03": "-1",
}


@pytest.mark.parametrize("problem_id,answer", ANSWERS.items())
def test_bank_answers_and_wrong_answers(problem_id, answer):
    result = verify_answer(problem_id, answer)
    assert result["status"] == "correct"
    assert result["residual"] == "0"
    assert result["equation"] == PROBLEMS[problem_id].equation
    assert result["verifier"] == "sympy"
    wrong = str(sp.Rational(answer) + 1)
    assert verify_answer(problem_id, wrong)["status"] == "incorrect"


@pytest.mark.parametrize("answer", ["6", "x=6", " x = 12 / 2 ", "6.0", "+6", "60/10"])
def test_equivalent_numeric_answers(answer):
    assert verify_answer("distribution-01", answer)["status"] == "correct"


@pytest.mark.parametrize("answer", ["1.5", "x=3/2", "0.75/0.5"])
def test_exact_fractional_answers(answer):
    assert verify_answer("linear-05", answer)["status"] == "correct"


@pytest.mark.parametrize("answer", [
    "", "not sure", "x=2 or x=6", "6,7", "y=6", "1/0", "nan", "inf", "True",
    "2+4", "6**1000000", "__import__('os').system('id')", "9" * 81,
])
def test_unsupported_syntax_never_becomes_a_grade(answer):
    assert verify_answer("distribution-01", answer)["status"] == "invalid_input"


def test_unknown_problem_does_not_use_a_substitute():
    assert verify_answer("model-invented-problem", "6")["status"] == "unsupported"
    assert "solution" not in str(list_problems())
    assert len(list_problems()) == 8


def test_failed_or_undecidable_verifier_is_inconclusive(monkeypatch):
    def fail(_):
        raise TimeoutError("simulated verifier failure")
    monkeypatch.setattr(algebra, "_solution_set", fail)
    assert verify_answer("distribution-01", "6")["status"] == "inconclusive"
    monkeypatch.setattr(algebra, "_solution_set", lambda _: sp.S.Reals)
    assert verify_answer("distribution-01", "6")["status"] == "inconclusive"


def test_wrong_hint_correct_then_fresh_practice():
    store = SessionStore()
    state = store.create()
    sid = state["session_id"]
    with pytest.raises(SessionConflict):
        store.advance(sid, state["revision"])
    state = store.attempt(sid, "distribution-01", "x=2", state["revision"])
    assert state["verification"]["status"] == "incorrect"
    assert not state["solved"] and not state["can_advance"]
    assert not state["completed_problem_ids"]
    state = store.hint(sid, state["revision"])
    assert state["hint_level"] == 1
    state = store.attempt(sid, "distribution-01", "x=6", state["revision"])
    assert state["solved"]
    assert state["history"][-1]["independent_success"] is False
    state = store.advance(sid, state["revision"])
    assert state["problem"]["id"] == "distribution-02"
    assert state["attempts"] == state["hint_level"] == 0
    state = store.attempt(sid, "distribution-02", "6", state["revision"])
    assert state["history"][-1]["independent_success"] is True


def test_repeated_errors_offer_prerequisite_then_return_to_original():
    store = SessionStore()
    state = store.create()
    sid = state["session_id"]
    for answer in ["2", "4"]:
        state = store.attempt(sid, "distribution-01", answer, state["revision"])
    assert state["can_advance"]
    state = store.advance(sid, state["revision"])
    assert state["problem"]["id"] == "linear-03"
    state = store.attempt(sid, "linear-03", "6", state["revision"])
    state = store.advance(sid, state["revision"])
    assert state["problem"]["id"] == "distribution-01"
    state = store.attempt(sid, "distribution-01", "6", state["revision"])
    assert state["history"][-1]["independent_success"] is False


def test_invalid_and_inconclusive_answers_do_not_count_or_advance(monkeypatch):
    store = SessionStore()
    state = store.create()
    sid = state["session_id"]
    state = store.attempt(sid, "distribution-01", "not sure", state["revision"])
    assert state["attempts"] == 0 and not state["can_advance"]
    monkeypatch.setattr(algebra, "_solution_set", lambda _: sp.S.Reals)
    state = store.attempt(sid, "distribution-01", "6", state["revision"])
    assert state["verification"]["status"] == "inconclusive"
    assert not state["solved"] and not state["completed_problem_ids"]
    assert state["attempts"] == 0


def test_sessions_are_isolated_snapshots_and_reject_problem_substitution():
    store = SessionStore()
    first, second = store.create(), store.create()
    with pytest.raises(SessionConflict):
        store.attempt(first["session_id"], "linear-01", "6", 0)
    first["history"].clear()
    assert store.get(first["session_id"])["history"]
    store.attempt(first["session_id"], "distribution-01", "6", 0)
    assert not store.get(second["session_id"])["solved"]


def test_simultaneous_duplicate_submission_grades_only_once():
    store = SessionStore()
    sid = store.create()["session_id"]
    def submit(_):
        try:
            store.attempt(sid, "distribution-01", "2", 0)
            return "graded"
        except SessionConflict:
            return "stale"
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(submit, range(2))) == ["graded", "stale"]
    assert store.get(sid)["attempts"] == 1


def test_all_problems_complete_only_after_verified_answers():
    store = SessionStore()
    state = store.create()
    for _ in range(8):
        problem_id = state["problem"]["id"]
        state = store.attempt(state["session_id"], problem_id, ANSWERS[problem_id], state["revision"])
        state = store.advance(state["session_id"], state["revision"])
    assert state["finished"]
    assert set(state["completed_problem_ids"]) == set(ANSWERS)
    assert not state["can_hint"] and not state["can_advance"]


def test_hint_and_session_limits_and_expiry(monkeypatch):
    store = SessionStore(max_sessions=1, ttl_seconds=60)
    state = store.create()
    with pytest.raises(SessionConflict):
        store.create()
    for _ in range(2):
        state = store.hint(state["session_id"], state["revision"])
    with pytest.raises(SessionConflict):
        store.hint(state["session_id"], state["revision"])
    import tutoring.sessions as sessions_module
    future = store._sessions[state["session_id"]].touched + 61
    monkeypatch.setattr(sessions_module.time, "monotonic", lambda: future)
    with pytest.raises(KeyError):
        store.get(state["session_id"])
    assert store.create()["session_id"] != state["session_id"]
