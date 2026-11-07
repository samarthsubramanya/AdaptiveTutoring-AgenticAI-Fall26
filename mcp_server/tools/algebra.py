"""Expose the same trusted-bank verifier to the agent runtime over MCP."""

from typing import Any
from typing import Literal

from tutoring.algebra import list_problems, verify_answer
from tutoring.symbolic import MathSpec, check


async def algebra_problems() -> list[dict[str, Any]]:
    """List the eight supported algebra problems without answer keys."""
    return list_problems()


async def verify_algebra_answer(problem_id: str, answer: str) -> dict[str, Any]:
    """Check a numeric answer to an original bank equation using SymPy.

    Use algebra_problems to obtain a problem_id. Accepts numbers, decimals,
    fractions, or x=number. Does not support arbitrary equations or proofs.
    Status is correct, incorrect, invalid_input, unsupported, or inconclusive.
    """
    return verify_answer(problem_id, answer)


async def verify_symbolic_answer(
    operation: Literal["solve", "simplify", "expand", "factor", "differentiate"],
    expression: str,
    answer: str,
    rhs: str = "0",
    variable: Literal["x", "y", "t"] = "x",
) -> dict[str, Any]:
    """Check an answer against an explicit mathematical interpretation.

    Solve linear/quadratic equations over the reals (include all real roots),
    or simplify/expand/factor/differentiate rational-coefficient polynomials.
    Confirm that expression/rhs match the user's question. Use explicit *.
    Does not verify natural-language interpretation, explanations, or proofs.
    """
    spec = MathSpec(operation=operation, expression=expression, rhs=rhs, variable=variable,
                    interpretation="Caller-provided mathematical interpretation; confirm against the original question.")
    return check(spec, answer)
