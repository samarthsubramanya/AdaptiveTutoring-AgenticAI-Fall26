"""Expose deterministic inequalities and statistics to skill workers."""

from typing import Literal

from tutoring.inequalities import InequalitySpec, verify as check_inequality
from tutoring.statistics import StatisticsSpec, verify as check_statistic


async def verify_inequality_answer(expression: str, answer: str,
                                   relation: Literal["<", "<=", ">", ">="] = "<=",
                                   rhs: str = "0", variable: Literal["x", "y", "t"] = "x") -> dict:
    """Verify all real intervals for a bounded linear/quadratic inequality.

    Confirm the expression, right side, variable and comparison with the user.
    Use interval notation: (-inf, 4], (-inf, -2] U [2, inf), {0}, or empty.
    """
    try:
        return check_inequality(InequalitySpec(expression=expression, relation=relation, rhs=rhs, variable=variable), answer)
    except ValueError as exc:
        return {"status": "unsupported", "message": str(exc)}


async def verify_statistics_answer(values: list[str], answer: str,
                                    metric: Literal["mean", "median", "range", "variance", "standard_deviation"] = "mean",
                                    convention: Literal["population", "sample"] = "population") -> dict:
    """Check a statistic on 1–100 rational observations; ask which variance convention applies.

    Grading uses exact arithmetic plus the documented rounding tolerance.
    This tool does not support inferential tests, correlations, or causal claims.
    """
    try:
        return check_statistic(StatisticsSpec(values=values, metric=metric, convention=convention), answer)
    except ValueError as exc:
        return {"status": "unsupported", "message": str(exc)}
