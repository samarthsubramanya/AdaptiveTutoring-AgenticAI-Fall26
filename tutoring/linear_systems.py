"""Exact elimination and answer checks for two equations in x and y."""

from fractions import Fraction
import re


_LITERAL = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)")


def _number(value: str) -> Fraction:
    if not isinstance(value, str) or not 1 <= len(value) <= 32:
        raise ValueError("Use numeric strings of at most 32 characters.")
    parts = value.strip().split("/")
    if len(parts) > 2 or not all(_LITERAL.fullmatch(part) for part in parts):
        raise ValueError("Use signed integers, decimals, or fractions, such as -2, 0.5, or 3/4.")
    try:
        result = Fraction(parts[0])
        return result if len(parts) == 1 else result / Fraction(parts[1])
    except (ValueError, ZeroDivisionError):
        raise ValueError("Fractions must have a nonzero numeric denominator.") from None


def _rows(equations: list[dict[str, str]]) -> list[tuple[Fraction, Fraction, Fraction]]:
    if not isinstance(equations, list) or len(equations) != 2:
        raise ValueError("Provide exactly two equations with coefficients a, b, and c.")
    rows = []
    for equation in equations:
        if not isinstance(equation, dict) or set(equation) != {"a", "b", "c"}:
            raise ValueError("Each equation must contain exactly a, b, and c for a*x + b*y = c.")
        rows.append(tuple(_number(equation[key]) for key in ("a", "b", "c")))
    return rows


def _latex(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    sign = "-" if value < 0 else ""
    return rf"{sign}\frac{{{abs(value.numerator)}}}{{{value.denominator}}}"


def _equation(row: tuple[Fraction, Fraction, Fraction]) -> str:
    a, b, c = row
    terms = []
    for coefficient, variable in ((a, "x"), (b, "y")):
        if coefficient:
            term = ("" if abs(coefficient) == 1 else _latex(abs(coefficient))) + variable
            sign = "-" if coefficient < 0 else ("+" if terms else "")
            terms.append(f"{sign}{term}")
    return " ".join(terms or ["0"]) + " = " + _latex(c)


def _classification(rows: list[tuple[Fraction, Fraction, Fraction]]) -> str:
    (a, b, c), (d, e, f) = rows
    if a * e - b * d:
        return "unique"
    if any(not a and not b and c for a, b, c in rows):
        return "none"
    if a * f != d * c or b * f != e * c:
        return "none"
    return "infinite"


def solve_linear_system(equations: list[dict[str, str]]) -> dict:
    """Solve a bounded two-by-two real system using exact rational arithmetic."""
    rows = _rows(equations)
    (a, b, c), (d, e, f) = rows
    classification = _classification(rows)
    public_equations = [
        {**dict(zip(("a", "b", "c"), map(str, row))), "latex": _equation(row)}
        for row in rows
    ]
    steps = []
    solution = None
    if classification == "unique":
        determinant = a * e - b * d
        numerator = c * e - b * f
        x = numerator / determinant
        row_number, (pa, pb, pc) = (1, rows[0]) if b else (2, rows[1])
        remainder = pc - pa * x
        y = remainder / pb
        solution = {"x": str(x), "y": str(y)}
        steps = [
            {
                "title": "Eliminate y",
                "explanation": f"Multiply equation 1 by {e} and equation 2 by {-b}, then add. The y terms cancel.",
                "latex": rf"\left({_latex(e)}\right)E_1-\left({_latex(b)}\right)E_2\;\Rightarrow\;\left({_latex(determinant)}\right)x={_latex(numerator)}",
            },
            {
                "title": "Solve for x",
                "explanation": f"Divide both sides by {determinant}, which is nonzero.",
                "latex": rf"x=\frac{{{_latex(numerator)}}}{{{_latex(determinant)}}}={_latex(x)}",
            },
            {
                "title": "Substitute to find y",
                "explanation": f"Substitute x = {x} into original equation {row_number}, then divide by {pb}.",
                "latex": rf"\left({_latex(pb)}\right)y={_latex(pc)}-\left({_latex(pa)}\right)\left({_latex(x)}\right)={_latex(remainder)}\;\Rightarrow\;y={_latex(y)}",
            },
            {
                "title": "Verify both original equations",
                "explanation": "Substituting this pair makes the left and right sides equal in both original equations.",
                "latex": r"\begin{aligned}" + r"\\".join(
                    rf"\left({_latex(ra)}\right)\left({_latex(x)}\right)+\left({_latex(rb)}\right)\left({_latex(y)}\right)&={_latex(ra * x + rb * y)}={_latex(rc)}"
                    for ra, rb, rc in rows
                ) + r"\end{aligned}",
            },
        ]
        hint = "Try multiplying the equations so the y coefficients cancel, then add them."
    elif classification == "none":
        contradictory = next((row for row in rows if not row[0] and not row[1] and row[2]), None)
        if contradictory is not None:
            explanation = "One original equation has no variable terms but a nonzero right side. It cannot be satisfied."
            contradiction = contradictory[2]
            operation = ""
        else:
            first, second = (a, d) if a or d else (b, e)
            contradiction = second * c - first * f
            explanation = f"Multiply equation 1 by {second} and equation 2 by {-first}, then add. Both variable terms cancel but the constants do not."
            operation = rf"\left({_latex(second)}\right)E_1-\left({_latex(first)}\right)E_2\;\Rightarrow\;"
        steps = [{"title": "Find the contradiction", "explanation": explanation,
                  "latex": operation + rf"0={_latex(contradiction)}"}]
        hint = "Look for an equation or an elimination result with zero variable terms and a nonzero constant."
    else:
        nonzero = next((row for row in rows if row[0] or row[1]), None)
        if nonzero is None:
            explanation = "Both equations are the identity 0 = 0, so every real pair (x, y) satisfies the system."
            latex = r"x,y\in\mathbb{R}"
        else:
            pa, pb, pc = nonzero
            explanation = "Only one independent equation remains; the other equation adds no restriction. Choose one variable freely and use the remaining equation to find the other."
            if pa:
                latex = rf"y=t,\quad x=\frac{{{_latex(pc)}-\left({_latex(pb)}\right)t}}{{{_latex(pa)}}},\quad t\in\mathbb{{R}}"
            else:
                latex = rf"x=t,\quad y={_latex(pc / pb)},\quad t\in\mathbb{{R}}"
        steps = [{"title": "Identify infinitely many solutions", "explanation": explanation, "latex": latex}]
        hint = "Check whether the equations repeat the same restriction or are identities; a free variable gives more than one solution."
    return {"classification": classification, "equations": public_equations,
            "solution": solution, "steps": steps, "hint": hint}


def check_linear_system_answer(equations: list[dict[str, str]], answer: dict[str, str]) -> dict:
    """Check a supplied pair in both original equations without returning a solution."""
    rows = _rows(equations)
    if not isinstance(answer, dict) or set(answer) != {"x", "y"}:
        raise ValueError("Provide exactly x and y as numeric strings.")
    x, y = (_number(answer[key]) for key in ("x", "y"))
    checks = [
        {"equation": _equation(row), "lhs": str(row[0] * x + row[1] * y),
         "rhs": str(row[2]), "satisfied": row[0] * x + row[1] * y == row[2]}
        for row in rows
    ]
    correct = all(check["satisfied"] for check in checks)
    classification = _classification(rows)
    if correct:
        feedback = "This pair satisfies both original equations."
        if classification == "infinite":
            feedback += " It is one of infinitely many valid pairs."
    elif classification == "none":
        feedback = "No pair can satisfy this system: the original equations are inconsistent."
    else:
        failed = ", ".join(str(index) for index, check in enumerate(checks, 1) if not check["satisfied"])
        feedback = f"This pair does not satisfy original equation(s) {failed}. Substitute both values and try again."
    return {"correct": correct, "classification": classification, "feedback": feedback, "checks": checks}
