"""Full HTTP tutoring turns, not checker-only tests."""

from datetime import timedelta
from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from tutoring.journey import JourneyStore
from tutoring.journey_api import create_router
from tutoring.learners import LearnerStore
import tutoring.learners as memory


def client_at(root, **config):
    app = FastAPI()
    engine = JourneyStore(LearnerStore(root), **config)
    app.include_router(create_router(engine))
    return TestClient(app), engine


@pytest.fixture
def client(tmp_path):
    return client_at(tmp_path)[0]


def start(client, skill="statistics", topic="statistics.spread", learner="journey-test"):
    result = client.post("/journeys/sessions", json={"learner_id": learner, "skill": skill, "topic": topic})
    assert result.status_code == 201, result.text
    return result.json()


def action(client, state, path, **fields):
    response = client.post(f"/journeys/sessions/{state['session_id']}/{path}",
                           json={"revision": state["revision"], **fields})
    assert response.status_code == 200, response.text
    return response.json()


def test_full_prerequisite_return_and_unaided_loop(client):
    s = start(client)
    s = action(client, s, "hints")
    assert s["hint"]["status"] == "attempt_first"
    s = action(client, s, "answers", answer="0")
    s = action(client, s, "hints")
    assert s["hint"]["level"] == 1
    assert s["profile"]["topics"][0]["hints_used"] == 1
    s = action(client, s, "hints")
    assert s["hint"]["status"] == "reflection_required"
    s = action(client, s, "hints", reflection="I added the differences but forgot to square them.")
    assert s["hint"]["level"] == 2
    s = action(client, s, "answers", answer="0")
    original = s["item"]["id"]
    s = action(client, s, "next")
    assert s["mode"] == "prerequisite_review" and s["item"]["topic"] == "statistics.center"
    s = action(client, s, "answers", answer="3")
    s = action(client, s, "next")
    assert s["item"]["id"] == original and s["mode"] == "return"
    s = action(client, s, "answers", answer="8/3")
    assert s["solved"] and s["history"][-1]["learning"]["assisted"]
    s = action(client, s, "next")
    assert s["mode"] == "unassisted_check" and s["max_hints"] == 0 and s["item"]["id"] != original
    s = action(client, s, "answers", answer="0")
    s = action(client, s, "hints")
    assert s["hint"]["status"] == "unavailable"
    s = action(client, s, "answers", answer="8/3")
    assert not s["history"][-1]["learning"]["independent"]  # retry is not unaided evidence
    s = action(client, s, "next")
    assert s["mode"] == "unassisted_check"


def test_replay_stale_and_mode_injection_fail_closed(client):
    s = start(client)
    url = f"/journeys/sessions/{s['session_id']}/answers"
    assert client.post(url, json={"revision": 0, "answer": "8/3", "mode": "practice"}).status_code == 422
    assert client.post(url, json={"revision": 0, "answer": "8/3", "status": "correct"}).status_code == 422
    solved = action(client, s, "answers", answer="8/3")
    assert client.post(url, json={"revision": 0, "answer": "8/3"}).status_code == 409
    assert client.post(url, json={"revision": solved["revision"], "answer": "8/3"}).status_code == 409
    assert solved["profile"]["topics"][0]["attempts"] == 1


def test_invalid_input_is_ungraded(client):
    s = start(client)
    s = action(client, s, "answers", answer="__import__('os')")
    assert s["attempts"] == 0 and s["profile"]["topics"] == []
    assert s["verification"]["status"] == "invalid_input"


def test_fading_and_return_after_server_restart(tmp_path, monkeypatch):
    client, _ = client_at(tmp_path)
    s = start(client, topic="statistics.center")
    s = action(client, s, "answers", answer="3")
    s = action(client, s, "next")
    assert s["item"]["id"] == "stats-center-2"
    s = action(client, s, "answers", answer="4")
    assert s["max_hints"] == 1
    old_now = memory._now
    monkeypatch.setattr(memory, "_now", lambda: old_now() + timedelta(hours=2))
    reopened, _ = client_at(tmp_path)
    back = start(reopened, topic="statistics.center")
    assert back["mode"] == "retrieve" and back["item"]["id"] == "stats-center-3"
    assert back["profile"]["topics"][0]["independent_correct"] == 2


def test_assisted_return_without_hint_is_still_assisted(client):
    s = start(client)
    s = action(client, s, "answers", answer="0")
    s = action(client, s, "answers", answer="0")
    s = action(client, s, "next")
    s = action(client, s, "answers", answer="3")
    s = action(client, s, "next")
    s = action(client, s, "answers", answer="8/3")
    assert s["history"][-1]["learning"]["assisted"]


def test_capacity_expiry_and_closed_sessions(tmp_path):
    client, engine = client_at(tmp_path, max_sessions=1)
    s = start(client)
    assert client.post('/journeys/sessions', json={"learner_id":"another", "skill":"algebra"}).status_code == 409
    engine.sessions[s['session_id']].touched -= 4000
    assert client.get(f"/journeys/sessions/{s['session_id']}").status_code == 404
    s = start(client)
    assert client.delete(f"/journeys/sessions/{s['session_id']}").status_code == 204


def test_ablation_controls_cannot_be_selected_over_http(client):
    assert client.post('/journeys/sessions', json={"learner_id":"another", "skill":"algebra", "adaptive":False}).status_code == 422
    assert client.post('/journeys/sessions', json={"learner_id":"../escape", "skill":"algebra"}).status_code == 422


def test_nested_prerequisites_return_through_the_whole_stack(client):
    s = start(client, skill="algebra", topic="algebra.distribution")
    for _ in range(2):
        s = action(client, s, "answers", answer="0")
    s = action(client, s, "next")
    assert s["item"]["id"] == "linear-03"
    for _ in range(2):
        s = action(client, s, "answers", answer="0")
    s = action(client, s, "next")
    assert s["item"]["id"] == "linear-01"
    s = action(client, s, "answers", answer="6")
    s = action(client, s, "next")
    assert s["item"]["id"] == "linear-03" and s["mode"] == "prerequisite_review"
    s = action(client, s, "answers", answer="6")
    s = action(client, s, "next")
    assert s["item"]["id"] == "distribution-01" and s["mode"] == "return"
    s = action(client, s, "answers", answer="6")
    s = action(client, s, "next")
    assert s["mode"] == "unassisted_check" and s["item"]["id"] != "distribution-01"


def test_stale_evidence_does_not_deny_support(tmp_path, monkeypatch):
    client, _ = client_at(tmp_path)
    s = start(client, topic="statistics.center")
    for answer in ["3", "4", "5", "6"]:
        s = action(client, s, "answers", answer=answer)
        if answer != "6":
            s = action(client, s, "next")
    assert s["max_hints"] == 0
    real_now = memory._now
    monkeypatch.setattr(memory, "_now", lambda: real_now() + timedelta(days=31))
    reopened, _ = client_at(tmp_path)
    s = start(reopened, topic="statistics.center")
    assert s["mode"] == "practice" and s["max_hints"] == 3


def test_turn_limit_still_allows_reading_and_closing(tmp_path):
    client, engine = client_at(tmp_path)
    s = start(client)
    engine.sessions[s["session_id"]].history *= 200
    assert client.get(f"/journeys/sessions/{s['session_id']}").status_code == 200
    assert client.post(f"/journeys/sessions/{s['session_id']}/answers", json={"revision":0,"answer":"8/3"}).status_code == 409
    assert client.delete(f"/journeys/sessions/{s['session_id']}").status_code == 204
