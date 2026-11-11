"""Exact real solution sets for bounded, one-variable polynomial inequalities."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
import sympy as sp

from tutoring.symbolic import expression


class InequalitySpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    expression: str = Field(min_length=1, max_length=300)
    relation: Literal["<", "<=", ">", ">="] = "<="
    rhs: str = Field(default="0", min_length=1, max_length=300)
    variable: Literal["x", "y", "t"] = "x"


def interval_text(solution: sp.Set) -> str:
    if solution == sp.S.Reals:
        return "(-inf, inf)"
    if solution == sp.S.EmptySet:
        return "empty"
    if isinstance(solution, sp.Union):
        return " U ".join(interval_text(part) for part in solution.args)
    if isinstance(solution, sp.FiniteSet):
        return "{" + ", ".join(map(str, sorted(solution))) + "}"
    left = "(" if solution.left_open else "["
    right = ")" if solution.right_open else "]"
    return f"{left}{str(solution.start).replace('-oo', '-inf')}, {str(solution.end).replace('oo', 'inf')}{right}"


def parse_solution(text: str, variable: str) -> sp.Set:
    if not isinstance(text, str) or not text.strip() or len(text) > 300:
        raise ValueError("Enter a solution set of at most 300 characters.")
    text = text.strip().replace("∞", "inf").replace("−", "-")
    if text.lower() in {"empty", "none", "{}", "∅"}:
        return sp.S.EmptySet
    if text.lower() in {"r", "reals", "all real numbers"}:
        return sp.S.Reals

    def endpoint(value):
        value = value.strip()
        if value.lower() in {"inf", "+inf"}:
            return sp.oo
        if value.lower() == "-inf":
            return -sp.oo
        return expression(value, variable, numeric=True)

    parts = re.split(r"\s+[Uu]\s+|∪", text)
    if len(parts) > 3:
        raise ValueError("Use at most three intervals joined with U.")
    result = sp.S.EmptySet
    for part in parts:
        part = part.strip()
        if part.startswith("{") and part.endswith("}"):
            values = part[1:-1].split(",")
            if len(values) > 2:
                raise ValueError("Use at most two isolated points.")
            points = [endpoint(v) for v in values]
            if any(v in (-sp.oo, sp.oo) for v in points):
                raise ValueError("Infinity is not an isolated solution.")
            result = result.union(sp.FiniteSet(*points))
            continue
        if len(part) < 5 or part[0] not in "[(" or part[-1] not in ")]" or part.count(",") != 1:
            raise ValueError("Use interval notation, for example (-inf, 4] or (-inf, -2] U [2, inf).")
        low, high = map(endpoint, part[1:-1].split(","))
        if low > high or low == sp.oo or high == -sp.oo:
            raise ValueError("Interval endpoints must be in increasing order.")
        if (low == -sp.oo and part[0] != "(") or (high == sp.oo and part[-1] != ")"):
            raise ValueError("Always use an open parenthesis at infinity.")
        result = result.union(sp.Interval(low, high, left_open=part[0] == "(", right_open=part[-1] == ")"))
    return result


def solve(spec: InequalitySpec) -> dict:
    x = sp.Symbol(spec.variable, real=True)
    lhs, rhs = expression(spec.expression, spec.variable), expression(spec.rhs, spec.variable)
    polynomial = sp.Poly(lhs - rhs, x, domain=sp.QQ)
    if polynomial.degree() > 2:
        raise ValueError("Inequalities support constant, linear, and quadratic polynomials only.")
    relation = {"<": sp.Lt, "<=": sp.Le, ">": sp.Gt, ">=": sp.Ge}[spec.relation](lhs, rhs)
    solution = sp.solve_univariate_inequality(relation, x, relational=False)
    linear = polynomial.degree() == 1
    hint = ("Isolate the variable. Reverse the inequality when dividing by a negative number."
            if linear else "Move everything to one side, locate the roots, and test the sign between them.")
    segments = []
    for part in solution.args if isinstance(solution, sp.Union) else [solution]:
        if isinstance(part, sp.Interval):
            segments.append({"low": None if part.start == -sp.oo else float(part.start),
                             "high": None if part.end == sp.oo else float(part.end),
                             "left_open": bool(part.left_open), "right_open": bool(part.right_open)})
    return {"problem": spec.model_dump(), "solution": interval_text(solution),
            "latex": sp.latex(relation), "solution_latex": sp.latex(solution),
            "segments": segments, "hint": hint,
            "explanation": "Solve over the real numbers; include every interval and preserve open or closed endpoints.",
            "verifier": "sympy", "domain": "real"}


def verify(spec: InequalitySpec, answer: str) -> dict:
    result = solve(spec)
    expected = parse_solution(result["solution"], spec.variable)
    try:
        given = parse_solution(answer, spec.variable)
    except ValueError as exc:
        return {**result, "status": "invalid_input", "message": str(exc)}
    correct = given == expected
    return {**result, "status": "correct" if correct else "incorrect",
            "message": "The entire solution set is correct, including its endpoints." if correct else
                       "Check the inequality direction, endpoint inclusion, and every interval."}
