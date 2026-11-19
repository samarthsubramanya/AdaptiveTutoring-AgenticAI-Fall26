"""Exercise the native tutoring page without a running API or model service."""

from copy import deepcopy
from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest


PAGE = Path(__file__).parents[1] / "ui/pages/4_Linear_Systems.py"


@pytest.fixture
def math_api(monkeypatch):
    calls = []

    def post(url, *, json, timeout):
        calls.append((url, deepcopy(json)))
        assert timeout == 10.0
        equations = json["equations"]
        second = equations[1]
        classification = "unique"
        if second == {"a": "2", "b": "2", "c": "5"}:
            classification = "none"
        elif second == {"a": "2", "b": "2", "c": "4"}:
            classification = "infinite"
        if url.endswith("/check"):
            correct = json["answer"] == {"x": "3", "y": "2"}
            payload = {
                "correct": correct, "classification": classification,
                "feedback": "Both equations are satisfied." if correct else "Try substituting your values again.",
                "checks": [{"equation": "x+y=5", "lhs": "5" if correct else "0", "rhs": "5", "satisfied": correct}],
            }
        else:
            payload = {
                "classification": classification,
                "equations": [{**row, "latex": f"{row['a']}x+({row['b']})y={row['c']}"} for row in equations],
                "solution": {"x": "3", "y": "2"} if classification == "unique" else None,
                "hint": "Choose multiples that cancel one variable, then add the equations.",
                "steps": [{"title": "Eliminate y", "explanation": "Add the equations to cancel y.", "latex": "2x=6"}],
            }
        return httpx.Response(200, json=payload, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", post)
    return calls


def button(app, label):
    return next(item for item in app.button if item.label == label)


def apply(app):
    button(app, "Apply system").click().run()
    assert not app.exception


def test_answer_feedback_hint_and_explicit_solution_reveal(math_api):
    app = AppTest.from_file(str(PAGE)).run()
    assert not app.exception
    assert not math_api
    apply(app)
    assert [item.value for item in app.subheader] == ["Your practice system"]

    button(app, "Give me a hint").click().run()
    assert "cancel one variable" in app.info[0].value
    assert not any(item.value == "Worked solution" for item in app.subheader)

    app.text_input(key="ls_x").input("0")
    app.text_input(key="ls_y").input("0")
    button(app, "Check my answer").click().run()
    assert app.warning[0].value == "Try substituting your values again."
    assert "Not equal" in " ".join(item.value for item in app.markdown)

    app.text_input(key="ls_x").input("3")
    app.text_input(key="ls_y").input("2")
    button(app, "Check my answer").click().run()
    assert app.success[0].value == "Both equations are satisfied."
    assert len(math_api) == 3
    assert math_api[-1][1]["answer"] == {"x": "3", "y": "2"}

    button(app, "Show worked solution").click().run()
    assert any(item.value == "Worked solution" for item in app.subheader)
    assert "Add the equations to cancel y." in [item.value for item in app.markdown]
    assert len(math_api) == 3  # Hint/reveal reuse the applied system without another request.


def test_switching_example_clears_answers_feedback_hints_and_reveal(math_api):
    app = AppTest.from_file(str(PAGE)).run()
    apply(app)
    app.text_input(key="ls_x").input("3")
    app.text_input(key="ls_y").input("2")
    button(app, "Check my answer").click().run()
    button(app, "Give me a hint").click().run()
    button(app, "Show worked solution").click().run()

    app.selectbox(key="ls_example").select("Fractional solution").run()
    assert not app.exception
    assert not app.success
    assert not app.subheader
    assert app.session_state["ls_result"] is None
    assert app.session_state["ls_feedback"] is None
    assert app.session_state["ls_x"] == app.session_state["ls_y"] == ""
    assert app.session_state["ls_hint"] is False
    assert app.session_state["ls_reveal"] is False
    assert app.text_input(key="ls_c1").value == "1"
    assert len(math_api) == 2
    apply(app)
    assert math_api[-1][1]["equations"] == [
        {"a": "1", "b": "1", "c": "1"}, {"a": "1", "b": "-1", "c": "0"},
    ]


def test_applying_custom_coefficients_replaces_previous_practice(math_api):
    app = AppTest.from_file(str(PAGE)).run()
    apply(app)
    button(app, "Give me a hint").click().run()
    button(app, "Show worked solution").click().run()
    app.text_input(key="ls_c1").input("7")
    apply(app)
    assert math_api[-1][1]["equations"][0]["c"] == "7"
    assert not app.info
    assert [item.value for item in app.subheader] == ["Your practice system"]
    assert app.text_input(key="ls_x").value == app.text_input(key="ls_y").value == ""
    assert app.session_state["ls_feedback"] is None


@pytest.mark.parametrize("example,classification,notice", [
    ("No solution", "none", "No solution:"),
    ("Infinitely many solutions", "infinite", "Infinitely many solutions:"),
])
def test_nonunique_systems_have_explanation_without_answer_form(math_api, example, classification, notice):
    app = AppTest.from_file(str(PAGE)).run()
    app.selectbox(key="ls_example").select(example).run()
    apply(app)
    assert app.session_state["ls_result"]["classification"] == classification
    assert app.info[0].value.startswith(notice)
    assert not any(item.label == "Your x" for item in app.text_input)
    assert not any(item.label == "Check my answer" for item in app.button)
    button(app, "Show worked solution").click().run()
    assert any(item.value == "Worked solution" for item in app.subheader)
    assert not app.exception


def test_failed_system_update_clears_previous_answer_and_solution(math_api, monkeypatch):
    app = AppTest.from_file(str(PAGE)).run()
    apply(app)
    button(app, "Show worked solution").click().run()

    def offline(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx, "post", offline)
    app.text_input(key="ls_c1").input("8")
    apply(app)
    assert app.error[0].value.startswith("Could not reach the math service.")
    assert not app.subheader
    assert app.session_state["ls_result"] is None
    assert app.session_state["ls_reveal"] is False


def test_invalid_coefficients_show_input_guidance(monkeypatch):
    def invalid(url, **kwargs):
        return httpx.Response(422, json={"detail": "invalid number"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", invalid)
    app = AppTest.from_file(str(PAGE)).run()
    apply(app)
    assert "nonzero denominator" in app.error[0].value
    assert not app.subheader
