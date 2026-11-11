"""Mathematical edge cases and HTTP contracts for the two added skills."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from tutoring.inequalities import InequalitySpec, solve, verify
from tutoring.statistics import StatisticsSpec, summarize, verify as statistics_verify
from tutoring.studio_api import router
from skills.registry import SKILLS

app = FastAPI()
app.include_router(router)
client = TestClient(app)


@pytest.mark.parametrize("lhs,relation,rhs,answer,status", [
    ("2*x+3", "<=", "11", "(-inf, 4]", "correct"),
    ("2*x+3", "<=", "11", "(-inf, 4)", "incorrect"),
    ("-2*x+3", "<", "11", "(-4, inf)", "correct"),
    ("x^2", ">=", "4", "(-inf, -2] U [2, inf)", "correct"),
    ("x^2", ">=", "4", "[2, inf)", "incorrect"),
    ("x^2", "<=", "0", "{0}", "correct"),
    ("x^2", "<", "0", "empty", "correct"),
    ("x^2", ">=", "0", "R", "correct"),
    ("1", "<", "2", "(-inf, inf)", "correct"),
    ("2", "<", "1", "empty", "correct"),
    ("x^2", "<", "2", "(-sqrt(2), sqrt(2))", "correct"),
    ("x", "<", "1", "[-inf, 1)", "invalid_input"),
    ("x", "<", "1", "(2, 1)", "invalid_input"),
    ("x", "<", "1", "__import__('os')", "invalid_input"),
])
def test_inequality_solution_sets(lhs, relation, rhs, answer, status):
    assert verify(InequalitySpec(expression=lhs, relation=relation, rhs=rhs), answer)["status"] == status


@pytest.mark.parametrize("text", ["x^3", "x/(x-1)", "__import__('os')", "x^999999", "sin(x)"])
def test_unsupported_or_unsafe_inequality(text):
    with pytest.raises(ValueError):
        solve(InequalitySpec(expression=text))


@pytest.mark.parametrize("metric,convention,answer", [
    ("mean", "population", "3"), ("median", "population", "3"),
    ("range", "population", "4"), ("variance", "population", "2"),
    ("variance", "sample", "5/2"), ("standard_deviation", "sample", "sqrt(5/2)"),
])
def test_statistics_conventions(metric, convention, answer):
    spec = StatisticsSpec(values=["1", "2", "3", "4", "5"], metric=metric, convention=convention)
    assert statistics_verify(spec, answer)["status"] == "correct"


def test_statistics_ties_and_rounding():
    assert summarize(StatisticsSpec(values=["-2", "-2", "1", "1"]))["modes"] == ["-2", "1"]
    spec = StatisticsSpec(values=["1", "2", "2"])
    assert statistics_verify(spec, "1.666667")["status"] == "correct"
    assert statistics_verify(spec, "1.67")["status"] == "incorrect"
    assert statistics_verify(spec, "nan")["status"] == "invalid_input"


def test_single_observation_and_fractional_data():
    assert summarize(StatisticsSpec(values=["1/3"]))["exact"] == "1/3"
    assert summarize(StatisticsSpec(values=["7"], convention="sample"))["metrics"]["variance"] is None
    with pytest.raises(ValueError):
        summarize(StatisticsSpec(values=["7"], convention="sample", metric="variance"))


@pytest.mark.parametrize("values", [["1/0"], ["inf"], ["sqrt(2)"], ["1000001"]])
def test_invalid_statistics(values):
    with pytest.raises(ValueError):
        summarize(StatisticsSpec(values=values))


def test_http_validation_and_skill_discovery():
    assert len(client.get("/studio/skills").json()) == 3
    result = client.post("/studio/inequalities/check", json={"expression": "x^2", "relation": ">=", "rhs": "4", "answer": "(-inf, -2] U [2, inf)"})
    assert result.status_code == 200 and result.json()["status"] == "correct"
    assert result.json()["segments"] == [
        {"low": None, "high": -2.0, "left_open": True, "right_open": False},
        {"low": 2.0, "high": None, "left_open": False, "right_open": True},
    ]
    assert client.post("/studio/statistics/check", json={"values": [], "answer": "0"}).status_code == 422
    assert client.post("/studio/statistics/check", json={"values": ["1"], "answer": "0", "metric": "variance", "convention": "sample"}).status_code == 422
    assert client.post("/studio/inequalities/check", json={"expression": "x", "relation": "=", "answer": "1"}).status_code == 422
    for skill in SKILLS.values():
        assert skill.load().strip()
