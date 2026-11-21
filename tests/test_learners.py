"""Learner memory (STUDENT.md), prerequisite planning and the five teaching behaviours."""

import asyncio
from datetime import timedelta

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from skills.registry import SKILLS
import tutoring.learners as memory
from tutoring import api as tutoring_api
from tutoring import learner_api
from tutoring.learners import LearnerStore

app = FastAPI()
app.include_router(learner_api.router)
app.include_router(tutoring_api.router)
client = TestClient(app)

RECT = {"kind": "rectangle_area", "params": {"width": "7", "height": "4"}}
TRI = {"kind": "triangle_area", "params": {"base": "10", "height": "6"}}
CIRCLE = {"kind": "circle_area", "params": {"radius": "3"}}
PERIM = {"kind": "rectangle_perimeter", "params": {"width": "9", "height": "5"}}
CIRC = {"kind": "circle_circumference", "params": {"radius": "5"}}
DIST = {"kind": "distance", "params": {"x1": "1", "y1": "2", "x2": "4", "y2": "6"}}
MID = {"kind": "midpoint", "params": {"x1": "2", "y1": "-1", "x2": "6", "y2": "5"}}


@pytest.fixture(autouse=True)
def isolated_store(tmp_path, monkeypatch):
    monkeypatch.setattr(learner_api.learners, "root", tmp_path)
    yield tmp_path


def check(spec, answer, learner="ana", **extra):
    response = client.post(f"/learners/{learner}/check", json={"skill": "geometry", "spec": spec, "answer": answer, **extra})
    assert response.status_code == 200, response.text
    return response.json()


def hint(spec, learner="ana", reflection=None):
    body = {"skill": "geometry", "spec": spec}
    if reflection:
        body["reflection"] = reflection
    return client.post(f"/learners/{learner}/hint", json=body).json()


def plan(skill="geometry", learner="ana"):
    return client.get(f"/learners/{learner}/plan", params={"skill": skill}).json()


def test_insufficient_evidence_makes_no_claim():
    first = plan()
    assert first["action"] == "start" and "no claim" in first["reason"]
    check(RECT, "28")
    assert plan()["action"] == "start"  # one verified result is still not enough


def test_ungraded_answers_never_touch_memory(isolated_store):
    result = check(RECT, "twenty-eight")
    assert result["verification"]["status"] == "invalid_input" and result["learning"] is None
    assert not (isolated_store / "ana").exists()


def test_status_cannot_be_injected_and_ids_are_validated():
    assert client.post("/learners/ana/check", json={"skill": "geometry", "spec": RECT, "answer": "1", "status": "correct"}).status_code == 422
    for bad in ("../x", "AB", "a", "x" * 41, "has space"):
        assert client.get(f"/learners/{bad}/plan", params={"skill": "geometry"}).status_code in {404, 422}


def test_hint_ladder_needs_attempt_then_reflection():
    assert hint(CIRCLE)["status"] == "attempt_first"           # retrieve-first gate
    check(CIRCLE, "28")
    first = hint(CIRCLE)
    assert first["status"] == "hint" and first["level"] == 1 and first["kind"] == "conceptual"
    assert hint(CIRCLE)["status"] == "reflection_required"
    second = hint(CIRCLE, reflection="I squared 3 but did not know what to do with pi")
    assert second["level"] == 2 and "π r²" in second["text"]
    third = hint(CIRCLE, reflection="I have 9 now but still unsure about the pi part")
    assert third["kind"] == "procedural"
    assert hint(CIRCLE, reflection="anything else that could help me here?")["status"] == "unavailable"


def test_assisted_success_triggers_unaided_check():
    check(CIRCLE, "28")
    hint(CIRCLE)
    result = check(CIRCLE, "9*pi")
    assert result["learning"]["assisted"] and not result["learning"]["independent"]
    next_step = result["plan"]
    assert next_step["action"] == "unassisted_check" and next_step["max_hints"] == 0
    assert next_step["teaching_skill"] == "unassisted-evidence-checkpoint"
    check(CIRC, "11", mode="unassisted_check")
    assert hint(CIRC)["status"] == "unavailable"                # no hints in an unaided check
    assert check(CIRC, "10*pi", mode="unassisted_check")["plan"]["action"] == "unassisted_check"  # 2nd try = assisted
    cleared = check(PERIM, "28", mode="unassisted_check")
    assert cleared["learning"]["independent"] and cleared["plan"]["action"] != "unassisted_check"


def test_support_fades_and_is_restored():
    assert check(RECT, "28")["learning"]["support"] == "full"
    faded = check(TRI, "30")["learning"]
    assert faded["support"] == "light" and "first, conceptual" in faded["transition"]
    check(CIRCLE, "1")
    assert hint(CIRCLE)["status"] == "hint"
    assert hint(CIRCLE, reflection="I tried the radius times two, is that right?")["status"] == "unavailable"
    check(PERIM, "28")
    assert check(CIRC, "10*pi")["learning"]["support"] == "none"
    restored = check({"kind": "rectangle_area", "params": {"width": "2", "height": "3"}}, "5")["learning"]
    assert restored["support"] == "light" and "again" in restored["transition"]


def test_prerequisite_review_uses_the_graph():
    check(DIST, "4")
    result = check(MID, "(1, 1)")
    assert result["plan"]["action"] == "prerequisite_review"
    assert result["plan"]["topic"] == "geometry.pythagoras" and result["plan"]["return_to"] == "geometry.coordinate"
    assert "geo-pythagoras-345" in result["plan"]["suggested"]


def test_returning_learner_retrieves_first_and_stale_evidence_is_ignored(monkeypatch):
    check(RECT, "28")
    check(TRI, "30")
    real_now = memory._now
    monkeypatch.setattr(memory, "_now", lambda: real_now() + timedelta(hours=2))
    retrieve = plan()
    assert retrieve["action"] == "retrieve" and retrieve["teaching_skill"] == "retrieve-first-gate"
    monkeypatch.setattr(memory, "_now", lambda: real_now() + timedelta(days=31))
    assert plan()["action"] == "start"


def test_student_file_persists_and_is_readable(isolated_store):
    check(RECT, "28", confidence_before=4)
    text = (isolated_store / "ana" / "STUDENT.md").read_text()
    assert text.startswith("---\n") and "# Learner ana" in text and "| Area and perimeter |" in text
    reopened = LearnerStore(isolated_store).load("ana")
    assert reopened["topics"]["geometry.measurement"]["independent_correct"] == 1
    assert "Area and perimeter" in client.get("/learners/ana/student.md").text
    assert client.get("/learners/nobody/student.md").status_code == 404


def test_confidence_calibration():
    events = [check(spec, ans, confidence_before=5)["learning"]["event_id"]
              for spec, ans in ((RECT, "28"), (TRI, "1"), (CIRCLE, "2"))]
    summary = client.post("/learners/ana/confidence", json={"event_id": events[0], "confidence_after": 3}).json()
    assert summary["samples"] == 3 and summary["accuracy"] == pytest.approx(0.33, abs=0.01)
    assert summary["gap"] > 0.15 and "more confident" in summary["summary"]
    assert client.post("/learners/ana/confidence", json={"event_id": "missing", "confidence_after": 3}).status_code == 404


def test_other_skills_route_to_their_topics():
    spec = {"expression": "x^2", "relation": ">=", "rhs": "4"}
    result = client.post("/learners/ana/check", json={"skill": "inequalities", "spec": spec, "answer": "(-inf, -2] U [2, inf)"}).json()
    assert result["topic"] == "inequalities.quadratic" and result["learning"]["independent"]
    stats = {"values": ["2", "4", "4", "6"], "metric": "variance", "convention": "population"}
    assert client.post("/learners/ana/check", json={"skill": "statistics", "spec": stats, "answer": "2"}).json()["topic"] == "statistics.spread"
    system = {"equations": [{"a": "1", "b": "1", "c": "3"}, {"a": "1", "b": "-1", "c": "1"}]}
    assert client.post("/learners/ana/check", json={"skill": "linear_systems", "spec": system, "answer": "(2, 1)"}).json()["verification"]["status"] == "correct"


def test_algebra_sessions_feed_memory():
    session = client.post("/tutoring/sessions", json={"learner_id": "ana"}).json()
    after = client.post(f"/tutoring/sessions/{session['session_id']}/answers",
                        json={"problem_id": "distribution-01", "answer": "6", "revision": 0}).json()
    assert after["solved"]
    row = client.get("/learners/ana").json()["topics"][0]
    assert row["topic"] == "algebra.distribution" and row["independent_correct"] == 1
    assert client.post("/tutoring/sessions", json={"learner_id": "../bad"}).status_code == 422


def test_teaching_skills_are_registered_with_memory_tools():
    names = ["retrieve_first_gate", "progressive_hint_ladder", "unassisted_evidence_checkpoint",
             "fading_manager", "confidence_calibration_check"]
    for name in names:
        assert SKILLS[name].path.exists()
        assert SKILLS[name].allowed_tools == {"get_learner_profile", "plan_learner_next_step"}


def test_mcp_memory_tools_are_read_only(isolated_store):
    from mcp_server.tools.learners import get_learner_profile, plan_learner_next_step
    assert asyncio.run(plan_learner_next_step("ana", "geometry"))["action"] == "start"
    assert asyncio.run(get_learner_profile("ana"))["exists"] is False
    assert asyncio.run(get_learner_profile("../x"))["status"] == "unsupported"
    assert not (isolated_store / "ana").exists()
