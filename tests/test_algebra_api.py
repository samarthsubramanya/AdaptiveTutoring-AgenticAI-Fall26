"""API, skill/tool integration, and actual Streamlit page interactions."""

from fastapi.testclient import TestClient
from pathlib import Path
import httpx
import pytest

from api.app import app
from mcp_server.tools.algebra import algebra_problems, verify_algebra_answer
from skills.registry import get_skill, list_skills
from tutoring import api as tutoring_api
from tutoring.sessions import SessionStore


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(tutoring_api, "sessions", SessionStore())
    with TestClient(app) as instance:
        yield instance


def test_full_api_demo_and_existing_health(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert len(client.get("/tutoring/problems").json()) == 8
    response = client.post("/tutoring/sessions", json={})
    assert response.status_code == 201
    state = response.json()
    path = f"/tutoring/sessions/{state['session_id']}"
    state = client.post(path + "/answers", json={"problem_id": "distribution-01", "answer": "2", "revision": 0}).json()
    assert state["verification"]["status"] == "incorrect"
    state = client.post(path + "/hint", json={"revision": state["revision"]}).json()
    assert state["hint_level"] == 1
    state = client.post(path + "/answers", json={"problem_id": "distribution-01", "answer": "6", "revision": state["revision"]}).json()
    assert state["solved"] and state["verification"]["residual"] == "0"
    state = client.post(path + "/next", json={"revision": state["revision"]}).json()
    assert state["problem"]["id"] == "distribution-02"
    assert client.get(path).json() == state
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404


def test_api_rejects_stale_actions_and_client_supplied_grades(client):
    state = client.post("/tutoring/sessions", json={}).json()
    path = f"/tutoring/sessions/{state['session_id']}"
    body = {"problem_id": "distribution-01", "answer": "2", "revision": 0}
    assert client.post(path + "/answers", json={**body, "correct": True}).status_code == 422
    assert client.post(path + "/answers", json={**body, "answer": 6}).status_code == 422
    assert client.post(path + "/answers", json={**body, "problem_id": "linear-01"}).status_code == 409
    assert client.post(path + "/next", json={"revision": 0}).status_code == 409
    assert client.post(path + "/answers", json=body).status_code == 200
    assert client.post(path + "/answers", json=body).status_code == 409
    assert client.post("/tutoring/sessions", json={"problem_id": "unknown"}).status_code == 422
    assert client.post("/tutoring/sessions/missing/hint", json={"revision": 0}).status_code == 404


@pytest.mark.asyncio
async def test_skill_and_mcp_share_the_same_verifier():
    assert "algebra" in {skill["name"] for skill in list_skills()}
    skill = get_skill("algebra")
    assert skill.allowed_tools == {"algebra_problems", "verify_algebra_answer", "verify_symbolic_answer"}
    assert "inconclusive" in skill.load()
    assert len(await algebra_problems()) == 8
    assert (await verify_algebra_answer("distribution-01", "2"))["status"] == "incorrect"
    assert (await verify_algebra_answer("distribution-01", "6"))["status"] == "correct"


def test_streamlit_page_attempt_hint_retry_and_next(client, monkeypatch):
    from streamlit.testing.v1 import AppTest
    def request(method, url, **kwargs):
        return client.request(method, httpx.URL(url).raw_path.decode(), json=kwargs.get("json"))
    monkeypatch.setattr(httpx, "request", request)
    page_path = Path(__file__).resolve().parents[1] / "ui/pages/3_Algebra_Tutor.py"
    page = AppTest.from_file(page_path).run(timeout=15)
    def click(label):
        next(button for button in page.button if button.label == label).click().run(timeout=15)
        assert not page.exception
    assert not page.exception
    click("Start new session")
    page.text_input[0].set_value("2")
    click("Check answer")
    assert any("SymPy verification: incorrect" in item.value for item in page.warning)
    click("Give me a hint")
    page.text_input[0].set_value("6")
    click("Check answer")
    assert any("SymPy verification: correct" in item.value for item in page.success)
    click("Next problem")
    assert any("distribution-02" in item.value for item in page.subheader)


@pytest.mark.parametrize("response", [
    httpx.Response(200, text="<!doctype html><title>another app</title>", headers={"content-type": "text/html"}),
    httpx.Response(200, text=" ", headers={"content-type": "application/json"}),
    httpx.Response(200, json={"wrong_service": True}),
    httpx.Response(200, json=[1]),
    httpx.Response(200, json=[{"id": "another-service", "equation": "1"}]),
])
def test_non_json_or_wrong_service_does_not_crash_tutor(monkeypatch, response):
    from streamlit.testing.v1 import AppTest
    response.request = httpx.Request("GET", "http://localhost/tutoring/problems")
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: response)
    page = AppTest.from_file(Path(__file__).resolve().parents[1] / "ui/pages/3_Algebra_Tutor.py").run()
    assert not page.exception
    assert any("did not return valid tutor API data" in item.value for item in page.error)
