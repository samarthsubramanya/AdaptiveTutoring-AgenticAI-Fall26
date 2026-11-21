"""Exact measurement and coordinate geometry checks; student text is never executed."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
import sympy as sp

from tutoring.symbolic import expression


Kind = Literal[
    "rectangle_area", "rectangle_perimeter", "triangle_area", "circle_area",
    "circle_circumference", "pythagoras_hypotenuse", "pythagoras_leg",
    "triangle_angle", "distance", "midpoint", "slope",
]

PARAMS: dict[str, tuple[str, ...]] = {
    "rectangle_area": ("width", "height"),
    "rectangle_perimeter": ("width", "height"),
    "triangle_area": ("base", "height"),
    "circle_area": ("radius",),
    "circle_circumference": ("radius",),
    "pythagoras_hypotenuse": ("a", "b"),
    "pythagoras_leg": ("hypotenuse", "leg"),
    "triangle_angle": ("angle_a", "angle_b"),
    "distance": ("x1", "y1", "x2", "y2"),
    "midpoint": ("x1", "y1", "x2", "y2"),
    "slope": ("x1", "y1", "x2", "y2"),
}
TOPIC = {
    "rectangle_area": "measurement", "rectangle_perimeter": "measurement",
    "triangle_area": "measurement", "circle_area": "measurement",
    "circle_circumference": "measurement", "pythagoras_hypotenuse": "pythagoras",
    "pythagoras_leg": "pythagoras", "triangle_angle": "angles",
    "distance": "coordinate", "midpoint": "coordinate", "slope": "coordinate",
}
PROMPTS = {
    "rectangle_area": "A rectangle is {width} units wide and {height} units tall. Find its area.",
    "rectangle_perimeter": "A rectangle is {width} units wide and {height} units tall. Find its perimeter.",
    "triangle_area": "A triangle has base {base} and height {height}. Find its area.",
    "circle_area": "A circle has radius {radius}. Find its exact area.",
    "circle_circumference": "A circle has radius {radius}. Find its exact circumference.",
    "pythagoras_hypotenuse": "A right triangle has legs {a} and {b}. Find the hypotenuse.",
    "pythagoras_leg": "A right triangle has hypotenuse {hypotenuse} and one leg {leg}. Find the other leg.",
    "triangle_angle": "Two angles of a triangle are {angle_a}° and {angle_b}°. Find the third angle in degrees.",
    "distance": "Find the distance between ({x1}, {y1}) and ({x2}, {y2}).",
    "midpoint": "Find the midpoint of ({x1}, {y1}) and ({x2}, {y2}). Answer as (x, y).",
    "slope": "Find the slope of the line through ({x1}, {y1}) and ({x2}, {y2}).",
}
HINTS = {
    "rectangle_area": ("Area counts the unit squares that cover the shape.",
                       "For a rectangle, area = width × height.",
                       "Multiply {width} × {height}."),
    "rectangle_perimeter": ("Perimeter is the distance all the way around the edge.",
                            "A rectangle has two widths and two heights: P = 2(w + h).",
                            "Add {width} + {height}, then double the sum."),
    "triangle_area": ("A triangle is half of a rectangle with the same base and height.",
                      "Area = ½ × base × height.",
                      "Multiply {base} × {height}, then halve the result."),
    "circle_area": ("A circle's area depends only on its radius.",
                    "Area = π r². Keep π in the answer, for example 9*pi.",
                    "Square the radius {radius}, then multiply by π."),
    "circle_circumference": ("Circumference is the distance around the circle.",
                             "Circumference = 2 π r. Keep π in the answer.",
                             "Double the radius {radius}, then multiply by π."),
    "pythagoras_hypotenuse": ("The hypotenuse is the longest side, opposite the right angle.",
                              "a² + b² = c², so c = √(a² + b²).",
                              "Compute {a}² + {b}², then take the square root; sqrt(…) is fine."),
    "pythagoras_leg": ("The missing leg is shorter than the hypotenuse.",
                       "Rearrange a² + b² = c²: the missing leg is √(c² − a²).",
                       "Compute {hypotenuse}² − {leg}², then take the square root."),
    "triangle_angle": ("What do the three interior angles of any triangle add up to?",
                       "The interior angles of a triangle sum to 180°.",
                       "Subtract {angle_a} and {angle_b} from 180."),
    "distance": ("The distance between two points is the hypotenuse of a right triangle.",
                 "d = √((x₂ − x₁)² + (y₂ − y₁)²).",
                 "Horizontal change: {x2} − {x1}. Vertical change: {y2} − {y1}. Square both, add, take the root."),
    "midpoint": ("The midpoint lies halfway along each coordinate.",
                 "M = ((x₁ + x₂)/2, (y₁ + y₂)/2).",
                 "Average {x1} and {x2}; then average {y1} and {y2}. Answer as (x, y)."),
    "slope": ("Slope compares vertical change with horizontal change.",
              "m = (y₂ − y₁)/(x₂ − x₁). A vertical line has an undefined slope.",
              "Compute ({y2} − {y1}) ÷ ({x2} − {x1})."),
}
_POSITIVE = {"width", "height", "base", "radius", "a", "b", "hypotenuse", "leg", "angle_a", "angle_b"}
_UNDEFINED = {"undefined", "none", "vertical", "no slope"}
_DECIMAL = re.compile(r"[+-]?\d{1,7}\.(\d{1,6})")


class GeometrySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: Kind
    params: dict[str, str] = Field(min_length=1, max_length=4)


def values(spec: GeometrySpec) -> dict[str, sp.Rational]:
    expected = PARAMS[spec.kind]
    if set(spec.params) != set(expected):
        raise ValueError(f"{spec.kind} needs exactly: {', '.join(expected)}.")
    out = {}
    for name in expected:
        value = expression(spec.params[name], "x", numeric=True)
        if not value.is_Rational or abs(value) > 1_000_000:
            raise ValueError(f"{name} must be a rational number between -1,000,000 and 1,000,000.")
        if name in _POSITIVE and value <= 0:
            raise ValueError(f"{name} must be positive.")
        out[name] = value
    return out


def expected(spec: GeometrySpec):
    """The exact answer: a SymPy number, an (x, y) pair, or None for an undefined slope."""
    v = values(spec)
    k = spec.kind
    if k == "rectangle_area":
        return v["width"] * v["height"]
    if k == "rectangle_perimeter":
        return 2 * (v["width"] + v["height"])
    if k == "triangle_area":
        return v["base"] * v["height"] / 2
    if k == "circle_area":
        return sp.pi * v["radius"] ** 2
    if k == "circle_circumference":
        return 2 * sp.pi * v["radius"]
    if k == "pythagoras_hypotenuse":
        return sp.sqrt(v["a"] ** 2 + v["b"] ** 2)
    if k == "pythagoras_leg":
        if v["hypotenuse"] <= v["leg"]:
            raise ValueError("The hypotenuse must be longer than the leg.")
        return sp.sqrt(v["hypotenuse"] ** 2 - v["leg"] ** 2)
    if k == "triangle_angle":
        third = 180 - v["angle_a"] - v["angle_b"]
        if third <= 0:
            raise ValueError("Two triangle angles must add to less than 180°.")
        return third
    dx, dy = v["x2"] - v["x1"], v["y2"] - v["y1"]
    if k == "distance":
        return sp.sqrt(dx ** 2 + dy ** 2)
    if k == "midpoint":
        return ((v["x1"] + v["x2"]) / 2, (v["y1"] + v["y2"]) / 2)
    return None if dx == 0 else dy / dx


def prompt(spec: GeometrySpec) -> str:
    return PROMPTS[spec.kind].format(**spec.params)


def hints(spec: GeometrySpec) -> tuple[str, str, str]:
    return tuple(text.format(**spec.params) for text in HINTS[spec.kind])


def parse_number(text: str) -> sp.Expr:
    """Numbers, fractions, sqrt(constant), or a multiple of pi, through the allowlisted parser."""
    if not isinstance(text, str) or not text.strip() or len(text) > 120:
        raise ValueError("Enter a number of at most 120 characters.")
    source = text.strip().replace("π", "pi").replace("−", "-")
    source = re.sub(r"\s*(°|degrees?)\s*$", "", source, flags=re.I)
    source = re.sub(r"(?<=[\d)])\s*(?=pi\b)", "*", source)  # 9pi, 9 π, (3/2)pi
    if re.search(r"\bpi\b", source):
        if re.search(r"\bt\b|sqrt", source):
            raise ValueError("Use either pi or sqrt(…) in one answer, not both.")
        return expression(re.sub(r"\bpi\b", "t", source), "t").subs(sp.Symbol("t", real=True), sp.pi)
    return expression(source, "x", numeric=True)


def _same(given: sp.Expr, target: sp.Expr, text: str) -> tuple[bool, bool]:
    """(correct, rounded): exact equality, or a decimal correctly rounded to its own places."""
    if sp.simplify(given - target) == 0:
        return True, False
    match = _DECIMAL.fullmatch(text.strip())
    if match and abs(float(given) - float(target)) <= 0.5 * 10 ** -len(match.group(1)) + 1e-12:
        return True, True
    return False, False


def verify(spec: GeometrySpec, answer: str) -> dict:
    target = expected(spec)
    base = {"kind": spec.kind, "topic": TOPIC[spec.kind], "prompt": prompt(spec),
            "verifier": "sympy exact arithmetic", "verifier_version": sp.__version__}
    try:
        if spec.kind == "midpoint":
            parts = answer.strip().strip("()[] ").split(",")
            if len(parts) != 2:
                raise ValueError("Answer a midpoint as (x, y).")
            checks = [_same(parse_number(p), t, p) for p, t in zip(parts, target)]
            correct, rounded = all(c for c, _ in checks), any(r for _, r in checks)
            exact = f"({target[0]}, {target[1]})"
        elif target is None:
            correct, rounded, exact = answer.strip().lower() in _UNDEFINED, False, "undefined"
            if not correct:
                parse_number(answer)  # a numeric answer is gradable (and wrong); garbage is not
        else:
            if answer.strip().lower() in _UNDEFINED:
                correct, rounded = False, False
            else:
                correct, rounded = _same(parse_number(answer), target, answer)
            exact = str(target).replace("pi", "π")
    except (ValueError, TypeError) as exc:
        return {**base, "status": "invalid_input", "message": str(exc)}
    if correct:
        note = " (accepted as correctly rounded; the exact value is " + exact + ")" if rounded else ""
        return {**base, "status": "correct", "exact": exact,
                "message": "Verified exactly with SymPy." + note}
    return {**base, "status": "incorrect",
            "message": "SymPy compared your answer with the exact value; they differ. Recheck the formula and arithmetic."}


_BANK = (
    ("geo-rect-area", "rectangle_area", {"width": "7", "height": "4"}),
    ("geo-rect-perimeter", "rectangle_perimeter", {"width": "9", "height": "5"}),
    ("geo-triangle-area", "triangle_area", {"base": "10", "height": "6"}),
    ("geo-circle-area", "circle_area", {"radius": "3"}),
    ("geo-circle-circumference", "circle_circumference", {"radius": "5"}),
    ("geo-pythagoras-345", "pythagoras_hypotenuse", {"a": "3", "b": "4"}),
    ("geo-pythagoras-root2", "pythagoras_hypotenuse", {"a": "1", "b": "1"}),
    ("geo-pythagoras-leg", "pythagoras_leg", {"hypotenuse": "13", "leg": "5"}),
    ("geo-triangle-angle", "triangle_angle", {"angle_a": "50", "angle_b": "60"}),
    ("geo-distance-5", "distance", {"x1": "1", "y1": "2", "x2": "4", "y2": "6"}),
    ("geo-distance-root", "distance", {"x1": "0", "y1": "0", "x2": "3", "y2": "3"}),
    ("geo-midpoint", "midpoint", {"x1": "2", "y1": "-1", "x2": "6", "y2": "5"}),
    ("geo-slope", "slope", {"x1": "1", "y1": "2", "x2": "3", "y2": "8"}),
    ("geo-slope-vertical", "slope", {"x1": "2", "y1": "1", "x2": "2", "y2": "7"}),
)


def problems() -> list[dict]:
    """Student-facing bank: prompts and parameters, never answers."""
    return [{"id": pid, "kind": kind, "params": params, "topic": TOPIC[kind],
             "prompt": PROMPTS[kind].format(**params)} for pid, kind, params in _BANK]
