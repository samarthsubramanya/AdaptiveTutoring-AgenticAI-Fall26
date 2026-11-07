"""Math tools shared with the Linear Systems practice page."""

from tutoring.linear_systems import (
    check_linear_system_answer as _check,
    solve_linear_system as _solve,
)


async def solve_linear_system(equations: list[dict[str, str]]) -> dict:
    """Solve two equations a*x+b*y=c with exact elimination steps.

    Supply exactly two objects with string fields a, b, c. Values may be
    integers, decimals, or fractions such as "-3/2"; expressions are unsupported.
    Returns unique, infinite, or none, with worked steps and exact solutions.
    """
    return _solve(equations)


async def check_linear_system_answer(
    equations: list[dict[str, str]], answer: dict[str, str]
) -> dict:
    """Check a student's x/y pair by substitution into both original equations.

    Supply two a/b/c equation objects and answer fields x and y as numeric
    strings. Does not reveal the worked solution or grade unsupported inputs.
    """
    return _check(equations, answer)
