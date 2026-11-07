"""Custom math checks use independent SymPy results, never model grades."""

import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import httpx
import pytest

from api.app import app
from tutoring import api as tutor_api, model, symbolic
from tutoring.custom import CaseStore
from tutoring.symbolic import MathSpec, check, expression, target


def spec(operation="solve", expression="x^2-5*x+6", rhs="0", variable="x"):
    return MathSpec(operation=operation, expression=expression, rhs=rhs, variable=variable,
                    interpretation="Find every real solution of the displayed quadratic equation.")


@pytest.mark.parametrize("problem,answer,status", [
    (spec(), "2,3", "correct"),
    (spec(), "2", "incorrect"),
    (spec(), "2,4", "incorrect"),
    (spec(), "{x=3, x=2}", "correct"),
    (spec(expression="x^2-2"), "-sqrt(2),sqrt(2)", "correct"),
    (spec(expression="x^2+1"), "no real solutions", "correct"),
    (spec(expression="x^2-x+6"), "no real solutions", "correct"),
    (spec(expression="x^2-4"), "-2,2", "correct"),
    (spec(expression="2*x+3", rhs="17"), "7", "correct"),
    (spec("factor", "x^2-9"), "(x-3)*(x+3)", "correct"),
    (spec("factor", "x^2-9"), "x^2-9", "needs_form"),
    (spec("expand", "(x+2)*(x-3)"), "x^2-x-6", "correct"),
    (spec("expand", "(x+2)*(x-3)"), "(x+2)*(x-3)", "needs_form"),
    (spec("simplify", "3*x+2*x-4"), "5*x-4", "correct"),
    (spec("differentiate", "x^3-2*x"), "3*x^2-2", "correct"),
    (spec("differentiate", "x^3-2*x"), "x^3-2*x", "incorrect"),
    (spec("differentiate", "t^2+2*t", variable="t"), "2*t+2", "correct"),
    (spec(expression="x^3-1"), "1", "unsupported"),
    (spec(expression="x", rhs="x"), "1", "unsupported"),
    (spec(), "__import__('os').system('id')", "invalid_input"),
    (spec(), "1/0", "invalid_input"),
])
def test_supported_operations_and_fail_closed_statuses(problem, answer, status):
    result = check(problem, answer)
    assert result["status"] == status
    assert result["expression"] == problem.expression
    assert result["domain"] == "real"


@pytest.mark.parametrize("text", [
    "__import__('os')", "x.__class__", "[x for x in range(100)]", "lambda: 1",
    "open('file')", "sin(x)", "y+1", "True", "x/(x-1)", "x**999999", "(x**6)**6",
    "9999999", "(999999**6)**6", "x+" * 100 + "x", "sqrt(x)",
])
def test_parser_rejects_code_unsupported_syntax_and_large_work(text):
    with pytest.raises(ValueError):
        expression(text, "x")


def test_failed_symbolic_target_is_never_a_grade(monkeypatch):
    monkeypatch.setattr(symbolic, "target", lambda _: (_ for _ in ()).throw(RuntimeError("failed")))
    assert check(spec(), "2,3")["status"] == "inconclusive"


@pytest.fixture
def fake_model(monkeypatch):
    calls = []
    class FakeClient:
        async def close(self):
            pass
    class FakeCaller:
        def __init__(self):
            self.client = FakeClient()
        async def call(self, **kwargs):
            data = json.loads(kwargs["messages"][1]["content"])
            calls.append(data)
            if "student_answer" in data:
                content = {"hint": "Which two integers multiply to 6 and add to 5?"}
            else:
                # Deliberately omit a root: the model must not be trusted to grade.
                content = {"problem": spec().model_dump(), "proposed_answer": "2",
                           "explanation": "Factor the polynomial and set each factor to zero."}
            return SimpleNamespace(content=json.dumps(content))
    monkeypatch.setattr(model, "LLMCaller", FakeCaller)
    return calls


@pytest.fixture
def client(monkeypatch, fake_model):
    monkeypatch.setattr(tutor_api, "cases", CaseStore())
    with TestClient(app) as instance:
        yield instance


def test_model_proposal_needs_confirmation_and_independent_verification(client, fake_model):
    response = client.post("/tutoring/math/cases", json={"prompt": "Solve x^2-5*x+6=0"})
    assert response.status_code == 201, response.text
    state = response.json()
    assert state["verification"] is None
    assert state["proposed_answer"] == "2"
    path = "/tutoring/math/cases/" + state["case_id"]
    assert client.post(path + "/answers", json={"answer": "2"}).status_code == 422
    assert client.post(path + "/answers", json={"answer": "2", "confirmed": False}).status_code == 422
    forged = {"answer": "2", "confirmed": True, "expression": "x-2", "correct": True}
    assert client.post(path + "/answers", json=forged).status_code == 422
    wrong = client.post(path + "/answers", json={"answer": "2", "confirmed": True}).json()
    assert wrong["verification"]["status"] == "incorrect"
    assert wrong["problem"]["expression"] == "x^2-5*x+6"
    hint = client.post(path + "/hint", json={"confirmed": True}).json()
    assert len(hint["hints"]) == 1
    correct = client.post(path + "/answers", json={"answer": "2,3", "confirmed": True}).json()
    assert correct["verification"]["status"] == "correct"
    assert fake_model[-1]["student_answer"] == "2"
    assert client.delete(path).status_code == 204
    assert client.get(path).status_code == 404


def test_provider_failure_is_actionable_and_does_not_create_case(client, monkeypatch):
    class MissingConfig:
        def __init__(self):
            raise ValueError("missing configuration")
    monkeypatch.setattr(model, "LLMCaller", MissingConfig)
    response = client.post("/tutoring/math/cases", json={"prompt": "Solve x^2=4"})
    assert response.status_code == 503
    assert "ASU_LLM_API_KEY" in response.json()["detail"]
    assert not tutor_api.cases._cases


@pytest.mark.asyncio
@pytest.mark.parametrize("content", ["not JSON", "[]", '{"problem":{"operation":"solve"}}'])
async def test_invalid_model_responses_are_rejected(monkeypatch, content):
    class FakeCaller:
        def __init__(self):
            async def close():
                pass
            self.client = SimpleNamespace(close=close)
        async def call(self, **kwargs):
            return SimpleNamespace(content=content)
    monkeypatch.setattr(model, "LLMCaller", FakeCaller)
    with pytest.raises(model.ModelResponseInvalid):
        await model.propose("Solve x^2=4")


@pytest.mark.asyncio
async def test_equation_only_reply_is_repaired_without_inventing_an_answer(monkeypatch):
    question = "Solve x^2 - x + 6 = 0 over the real numbers."
    fields = spec(expression="x^2-x+6").model_dump()
    responses = [fields, {**fields, "proposed_answer": "no real solutions",
                          "explanation": "The discriminant is 1 - 24 = -23, so there are no real roots."}]
    requests = []
    async def reply(system, data):
        requests.append(data)
        assert "ONE FLAT JSON object" in system
        return responses.pop(0)
    monkeypatch.setattr(model, "_json_reply", reply)
    proposal = await model.propose(question)
    assert len(requests) == 2
    assert requests[0]["question"] == requests[1]["question"] == question
    assert "format_feedback" in requests[1]
    assert proposal.problem.expression == "x^2-x+6"
    assert check(proposal.problem, proposal.proposed_answer)["status"] == "correct"


@pytest.mark.asyncio
async def test_complete_flat_response_needs_no_repair(monkeypatch):
    calls = []
    async def reply(system, data):
        calls.append(data)
        return {**spec().model_dump(), "proposed_answer": "2,3", "explanation": "Factor and check both roots."}
    monkeypatch.setattr(model, "_json_reply", reply)
    assert (await model.propose("Solve x^2-5*x+6=0")).proposed_answer == "2,3"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_format_repair_is_bounded_and_never_fills_missing_fields(monkeypatch):
    calls = []
    async def reply(system, data):
        calls.append(data)
        return spec().model_dump()
    monkeypatch.setattr(model, "_json_reply", reply)
    with pytest.raises(model.ModelResponseInvalid, match="one format-repair"):
        await model.propose("Solve x^2-5*x+6=0")
    assert len(calls) == 2


def test_llm_custom_ui_reviews_then_checks_wrong_model_answer(client, monkeypatch):
    from streamlit.testing.v1 import AppTest
    def request(method, url, **kwargs):
        return client.request(method, httpx.URL(url).raw_path.decode(), json=kwargs.get("json"))
    monkeypatch.setattr(httpx, "request", request)
    page = AppTest.from_file(Path(__file__).resolve().parents[1] / "ui/pages/3_Algebra_Tutor.py").run(timeout=15)
    page.radio[0].set_value("LLM-assisted problems").run(timeout=15)
    def click(label):
        next(button for button in page.button if button.label == label).click().run(timeout=15)
        assert not page.exception
    click("Ask math tutor")
    assert next(button for button in page.button if button.label == "Verify model answer").disabled
    page.checkbox[0].set_value(True).run(timeout=15)
    click("Verify model answer")
    assert any("does not match" in item.value for item in page.warning)
    page.text_input[0].set_value("2,3").run(timeout=15)
    click("Check my answer")
    assert any("SymPy verified" in item.value for item in page.success)
