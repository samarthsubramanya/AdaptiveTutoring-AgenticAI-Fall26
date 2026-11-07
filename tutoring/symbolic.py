"""Bounded symbolic checking for custom, user-reviewed algebra problems."""

import ast
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
import sympy as sp


class MathSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    operation: Literal["solve", "simplify", "expand", "factor", "differentiate", "unsupported"]
    expression: str = Field(max_length=300)
    rhs: str = Field(default="0", max_length=300)
    variable: Literal["x", "y", "t"] = "x"
    interpretation: str = Field(min_length=1, max_length=1200)


def expression(text: str, variable: str, *, numeric: bool = False) -> sp.Expr:
    """Construct SymPy nodes from an allowlisted AST, never eval/parse_expr.

    One variable, polynomial degree <= 8, rational constant denominators,
    small powers, and (in numeric answers) square roots of numeric constants.
    Bounds are checked before polynomial expansion or solving.
    """
    if not isinstance(text, str) or not text.strip() or len(text) > 300:
        raise ValueError("Use a mathematical expression of at most 300 characters.")
    source = text.strip().replace("^", "**").replace("−", "-")
    try:
        tree = ast.parse(source, mode="eval")
    except (SyntaxError, ValueError, RecursionError):
        raise ValueError("Use explicit multiplication, such as 3*x, and standard parentheses.") from None
    nodes = list(ast.walk(tree))
    if len(nodes) > 65 or sum(isinstance(n, ast.Call) for n in nodes) > 4:
        raise ValueError("The expression is too complex for this algebra checker.")
    symbol = sp.Symbol(variable, real=True)

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            literal = ast.get_source_segment(source, node)
            if len(literal) > 24 or abs(node.value) > 1_000_000:
                raise ValueError("Numeric literals must be small finite numbers.")
            result, degree = sp.Rational(literal), 0
        elif isinstance(node, ast.Name) and node.id == variable and not numeric:
            result, degree = symbol, 1
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            result, degree = visit(node.operand)
            if isinstance(node.op, ast.USub):
                result = -result
        elif isinstance(node, ast.BinOp):
            left, dl = visit(node.left)
            right, dr = visit(node.right)
            if isinstance(node.op, ast.Add):
                result, degree = left + right, max(dl, dr)
            elif isinstance(node.op, ast.Sub):
                result, degree = left - right, max(dl, dr)
            elif isinstance(node.op, ast.Mult):
                if dl + dr > 8:
                    raise ValueError("Polynomial degree must be at most 8.")
                result, degree = left * right, dl + dr
            elif isinstance(node.op, ast.Div) and dr == 0 and right.is_Rational and right != 0:
                result, degree = left / right, dl
            elif isinstance(node.op, ast.Pow) and right.is_Integer and 0 <= right <= 6:
                degree = dl * int(right)
                if degree > 8 or (left.is_Rational and max(abs(int(left.p)).bit_length(), int(left.q).bit_length()) * int(right) > 256):
                    raise ValueError("That power exceeds the checker's computation limits.")
                result = left ** right
            else:
                raise ValueError("Use +, -, *, constant division, and integer powers from 0 to 6.")
        elif numeric and isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "sqrt" and len(node.args) == 1 and not node.keywords:
            value, degree = visit(node.args[0])
            if not value.is_Rational or not 0 <= value <= 1_000_000:
                raise ValueError("sqrt accepts only a nonnegative numeric constant.")
            result = sp.sqrt(value)
        else:
            raise ValueError(f"Only the variable {variable}, numeric constants, and supported arithmetic are allowed.")
        if result.is_Rational and max(abs(int(result.p)).bit_length(), int(result.q).bit_length()) > 256:
            raise ValueError("The numeric value exceeds the checker's computation limits.")
        return result, degree

    return visit(tree.body)[0]


def target(spec: MathSpec):
    if spec.operation == "unsupported":
        raise ValueError("This question is outside the supported algebra and polynomial-calculus scope.")
    symbol = sp.Symbol(spec.variable, real=True)
    lhs = expression(spec.expression, spec.variable)
    if spec.operation == "solve":
        rhs = expression(spec.rhs, spec.variable)
        polynomial = sp.Poly(lhs - rhs, symbol, domain=sp.QQ)
        if polynomial.is_zero or polynomial.degree() > 2:
            raise ValueError("Solving supports linear or quadratic equations with finite real solution sets.")
        result = sp.solveset(lhs - rhs, symbol, domain=sp.S.Reals)
        if result is not sp.S.EmptySet and not isinstance(result, sp.FiniteSet):
            raise ValueError("The real solution set could not be established.")
        return result
    # These operations are polynomial-only; no rational-function domain loss.
    sp.Poly(lhs, symbol, domain=sp.QQ)
    return {
        "simplify": sp.expand,
        "expand": sp.expand,
        "factor": sp.factor,
        "differentiate": lambda value: sp.diff(value, symbol),
    }[spec.operation](lhs)


def public_problem(spec: MathSpec) -> dict:
    lhs = expression(spec.expression, spec.variable)
    latex = sp.latex(lhs)
    if spec.operation == "solve":
        latex += " = " + sp.latex(expression(spec.rhs, spec.variable))
    elif spec.operation == "differentiate":
        latex = rf"\frac{{d}}{{d{spec.variable}}}\left({latex}\right)"
    return {**spec.model_dump(), "latex": latex, "domain": "real"}


def check(spec: MathSpec, answer: str) -> dict:
    evidence = {"verifier": "sympy", "verifier_version": sp.__version__,
                "operation": spec.operation, "expression": spec.expression,
                "rhs": spec.rhs if spec.operation == "solve" else None,
                "variable": spec.variable, "domain": "real"}
    try:
        expected = target(spec)
    except ValueError as exc:
        return {**evidence, "status": "unsupported", "message": str(exc)}
    except Exception:
        return {**evidence, "status": "inconclusive", "message": "The symbolic target could not be established; no grade was assigned."}
    try:
        if not isinstance(answer, str) or not answer.strip() or len(answer) > 300:
            raise ValueError("Enter an answer of at most 300 characters.")
        if spec.operation == "solve":
            if answer.strip().lower() in {"none", "no real solutions", "no real solution", "{}", "∅"}:
                given = sp.S.EmptySet
            else:
                parts = answer.strip().strip("{}").split(",")
                if len(parts) > 2:
                    raise ValueError("Enter all real roots separated by commas (at most two).")
                values = []
                for part in parts:
                    part = part.strip()
                    if part.startswith(spec.variable + "=") or part.startswith(spec.variable + " ="):
                        part = part.split("=", 1)[1]
                    values.append(expression(part, spec.variable, numeric=True))
                given = sp.FiniteSet(*values)
            equivalent = given == expected
            evidence["normalized_answer"] = str(given)
        else:
            given = expression(answer, spec.variable)
            equivalent = sp.expand(given - expected) == 0
            evidence["normalized_answer"] = str(given)
            if equivalent and spec.operation in {"factor", "expand"} and given != expected:
                return {**evidence, "status": "needs_form", "equivalent": True,
                        "message": "The expression is equivalent, but use the requested factored or expanded form before completing this check."}
        return {**evidence, "status": "correct" if equivalent else "incorrect",
                "message": "SymPy verified the complete answer for the confirmed interpretation." if equivalent else
                           "This answer does not match the confirmed problem. For equations, include every real solution."}
    except ValueError as exc:
        return {**evidence, "status": "invalid_input", "message": str(exc)}
    except Exception:
        return {**evidence, "status": "inconclusive", "message": "The symbolic check failed; no grade was assigned."}
