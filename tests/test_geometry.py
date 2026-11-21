"""Exact geometry checks, unsafe input, the problem bank and HTTP contracts."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from skills.registry import SKILLS
from tutoring.geometry import GeometrySpec, expected, problems, verify
from tutoring.studio_api import router

client = TestClient(FastAPI(routes=router.routes))
CIRCLE = {"radius": "3"}
POINTS = {"x1": "0", "y1": "0", "x2": "3", "y2": "3"}
VERTICAL = {"x1": "2", "y1": "1", "x2": "2", "y2": "7"}


@pytest.mark.parametrize("kind,params,answer,status", [
    ("rectangle_area", {"width": "7", "height": "4"}, "28", "correct"),
    ("rectangle_perimeter", {"width": "9", "height": "5"}, "28", "correct"),
    ("triangle_area", {"base": "7", "height": "3"}, "21/2", "correct"),
    ("triangle_area", {"base": "7", "height": "3"}, "10.5", "correct"),
    ("circle_area", CIRCLE, "9*pi", "correct"),
    ("circle_area", CIRCLE, "9π", "correct"),
    ("circle_area", CIRCLE, "28.27", "correct"),      # correctly rounded to 2 places
    ("circle_area", CIRCLE, "28.2", "incorrect"),     # wrongly rounded
    ("circle_area", CIRCLE, "28", "incorrect"),
    ("circle_circumference", {"radius": "5"}, "10*pi", "correct"),
    ("pythagoras_hypotenuse", {"a": "1", "b": "1"}, "sqrt(2)", "correct"),
    ("pythagoras_hypotenuse", {"a": "3", "b": "4"}, "5", "correct"),
    ("pythagoras_leg", {"hypotenuse": "13", "leg": "5"}, "12", "correct"),
    ("triangle_angle", {"angle_a": "50", "angle_b": "60"}, "70°", "correct"),
    ("distance", POINTS, "3*sqrt(2)", "correct"),
    ("distance", POINTS, "sqrt(18)", "correct"),
    ("midpoint", {"x1": "2", "y1": "-1", "x2": "6", "y2": "5"}, "(4, 2)", "correct"),
    ("midpoint", {"x1": "2", "y1": "-1", "x2": "6", "y2": "5"}, "(4, 3)", "incorrect"),
    ("slope", {"x1": "1", "y1": "2", "x2": "3", "y2": "8"}, "3", "correct"),
    ("slope", {"x1": "1", "y1": "2", "x2": "3", "y2": "8"}, "undefined", "incorrect"),
    ("slope", VERTICAL, "undefined", "correct"),
    ("slope", VERTICAL, "0", "incorrect"),
    ("slope", VERTICAL, "steep", "invalid_input"),
    ("circle_area", CIRCLE, "__import__('os')", "invalid_input"),
    ("circle_area", CIRCLE, "pi*sqrt(2)", "invalid_input"),
    ("circle_area", CIRCLE, "t*9", "invalid_input"),
    ("midpoint", {"x1": "2", "y1": "-1", "x2": "6", "y2": "5"}, "4", "invalid_input"),
])
def test_geometry_answers(kind, params, answer, status):
    assert verify(GeometrySpec(kind=kind, params=params), answer)["status"] == status


def test_exact_value_is_returned_only_when_correct():
    spec = GeometrySpec(kind="circle_area", params=CIRCLE)
    assert "exact" not in verify(spec, "28")
    assert verify(spec, "9*pi")["exact"] == "9*π"


@pytest.mark.parametrize("kind,params", [
    ("circle_area", {}),
    ("circle_area", {"radius": "3", "extra": "1"}),
    ("circle_area", {"radius": "-3"}),
    ("pythagoras_leg", {"hypotenuse": "5", "leg": "5"}),
    ("triangle_angle", {"angle_a": "100", "angle_b": "80"}),
    ("rectangle_area", {"width": "x", "height": "2"}),
])
def test_invalid_specs_are_rejected(kind, params):
    with pytest.raises(ValueError):
        expected(GeometrySpec(kind=kind, params=params))


def test_bank_is_solvable_and_hides_answers():
    bank = problems()
    assert len(bank) == 14 and len({p["id"] for p in bank}) == 14
    assert {p["topic"] for p in bank} == {"measurement", "pythagoras", "angles", "coordinate"}
    for item in bank:
        expected(GeometrySpec(kind=item["kind"], params=item["params"]))
        assert set(item) == {"id", "kind", "params", "topic", "prompt"}


def test_http_routes_and_catalogue():
    assert client.post("/studio/geometry/check", json={"kind": "distance", "params": POINTS, "answer": "3*sqrt(2)"}).json()["status"] == "correct"
    assert client.post("/studio/geometry/check", json={"kind": "circle_area", "params": {"radius": "0"}, "answer": "0"}).status_code == 422
    assert len(client.get("/studio/geometry/problems").json()) == 14
    assert "geometry" in {s["id"] for s in client.get("/studio/skills").json()}


def test_geometry_skill_is_registered():
    assert SKILLS["geometry"].allowed_tools == {"verify_geometry_answer"}
    assert SKILLS["geometry"].path.exists()
