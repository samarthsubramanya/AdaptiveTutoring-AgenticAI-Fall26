"""Trusted problems and exact answer verification without evaluating user code."""

from dataclasses import dataclass
from functools import lru_cache
import re
from typing import Any

import sympy as sp


X = sp.Symbol("x", real=True)
MAX_ANSWER_LENGTH = 80
_NUMBER = r"[+-]?(?:[0-9]{1,24}(?:\.[0-9]{1,24})?|\.[0-9]{1,24})"
_ANSWER = re.compile(rf"(?:x\s*=\s*)?({_NUMBER})(?:\s*/\s*({_NUMBER}))?\Z")


@dataclass(frozen=True)
class Problem:
    id: str
    equation: str
    latex: str
    lhs: sp.Expr
    rhs: sp.Expr
    topic: str
    difficulty: int
    hints: tuple[str, ...]
    prerequisite: str | None = None

    def public(self) -> dict[str, Any]:
        """Exclude answer keys and undisplayed hints from student-facing data."""
        return {
            "id": self.id,
            "equation": self.equation,
            "latex": self.latex,
            "topic": self.topic,
            "difficulty": self.difficulty,
            "instruction": "Solve for x over the real numbers.",
        }


_PROBLEMS = (
    Problem("linear-01", "x + 4 = 10", r"x+4=10", X + 4, sp.Integer(10),
            "one-step equations", 1,
            ("Undo the addition while keeping both sides equal.",
             "Subtract 4 from both sides, then simplify.")),
    Problem("linear-02", "2x = 10", r"2x=10", 2 * X, sp.Integer(10),
            "one-step equations", 1,
            ("Undo multiplication using the same operation on both sides.",
             "Divide both sides by 2.")),
    Problem("linear-03", "3x - 6 = 12", r"3x-6=12", 3 * X - 6, sp.Integer(12),
            "two-step equations", 2,
            ("First isolate the term containing x.",
             "Add 6 to both sides, then divide both sides by 3."), "linear-01"),
    Problem("linear-04", "4x + 3 = 11", r"4x+3=11", 4 * X + 3, sp.Integer(11),
            "two-step equations", 2,
            ("Undo addition before undoing multiplication.",
             "Subtract 3 from both sides, then divide by 4."), "linear-02"),
    Problem("linear-05", "2x + 3 = 6", r"2x+3=6", 2 * X + 3, sp.Integer(6),
            "two-step equations", 2,
            ("The solution need not be a whole number.",
             "Subtract 3 from both sides and divide by 2. A fraction is fine."), "linear-02"),
    Problem("distribution-01", "3(x - 2) = 12", r"3(x-2)=12", 3 * (X - 2), sp.Integer(12),
            "distribution", 3,
            ("Try dividing both sides by the factor outside the parentheses.",
             "Divide both sides by 3 to obtain x - 2 = 4. What undoes subtracting 2?"), "linear-03"),
    Problem("distribution-02", "2(x + 3) = 18", r"2(x+3)=18", 2 * (X + 3), sp.Integer(18),
            "distribution", 3,
            ("You can divide first or distribute the factor to every term.",
             "Divide both sides by 2, then subtract 3 from both sides."), "linear-04"),
    Problem("distribution-03", "-2(x - 3) = 8", r"-2(x-3)=8", -2 * (X - 3), sp.Integer(8),
            "distribution", 3,
            ("Keep track of the negative sign when dividing or distributing.",
             "Divide both sides by -2, then add 3 to both sides."), "linear-03"),
)
PROBLEMS = {problem.id: problem for problem in _PROBLEMS}
DEFAULT_PROBLEM_ID = "distribution-01"


def list_problems() -> list[dict[str, Any]]:
    return [problem.public() for problem in PROBLEMS.values()]


def _parse_answer(answer: str) -> sp.Rational:
    if not isinstance(answer, str) or len(answer) > MAX_ANSWER_LENGTH:
        raise ValueError("Use at most 80 characters for your answer.")
    match = _ANSWER.fullmatch(answer.strip().replace("−", "-"))
    if match is None:
        raise ValueError("Enter a number, decimal, or fraction, optionally prefixed by x=.")
    numerator, denominator = match.groups()
    value = sp.Rational(numerator)
    if denominator is not None:
        divisor = sp.Rational(denominator)
        if divisor == 0:
            raise ValueError("A fraction cannot have a zero denominator.")
        value /= divisor
    return value


@lru_cache(maxsize=len(PROBLEMS))
def _solution_set(problem_id: str) -> sp.Set:
    problem = PROBLEMS[problem_id]
    return sp.solveset(problem.lhs - problem.rhs, X, domain=sp.S.Reals)


def verify_answer(problem_id: str, answer: str) -> dict[str, Any]:
    """Verify against the bank's original equation, never an LLM-provided key.

    Only bounded rational numeric literals are accepted. No eval, sympify, or
    parse_expr is used on user input. Symbolic operations use trusted bank data.
    """
    evidence: dict[str, Any] = {
        "problem_id": problem_id,
        "verifier": "sympy",
        "verifier_version": sp.__version__,
        "domain": "real",
    }
    if problem_id not in PROBLEMS:
        return {**evidence, "status": "unsupported", "message": "Unknown problem ID. Choose a bank problem."}
    problem = PROBLEMS[problem_id]
    evidence["equation"] = problem.equation
    try:
        value = _parse_answer(answer)
    except ValueError as exc:
        return {**evidence, "status": "invalid_input", "message": str(exc)}
    try:
        solutions = _solution_set(problem_id)
        if not isinstance(solutions, sp.FiniteSet) or len(solutions) != 1:
            return {**evidence, "status": "inconclusive", "message": "The checker could not establish one real solution."}
        residual = (problem.lhs - problem.rhs).subs(X, value)
        matches = solutions.contains(value)
        if matches not in (sp.S.true, sp.S.false):
            return {**evidence, "status": "inconclusive", "message": "The checker could not decide this answer."}
        correct = matches == sp.S.true and residual == 0
        return {
            **evidence,
            "status": "correct" if correct else "incorrect",
            "normalized_answer": str(value),
            "residual": str(residual),
            "message": "Verified by SymPy: your answer satisfies the equation." if correct else
                       "SymPy checked your answer in the original equation; the two sides are unequal.",
        }
    except Exception:
        return {**evidence, "status": "inconclusive", "message": "The verifier failed. No grade was assigned; please retry."}
