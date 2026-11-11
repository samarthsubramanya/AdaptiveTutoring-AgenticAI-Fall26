# Learning studio: skill scope and verification

Inequalities: real constant, linear, and quadratic polynomials in one variable;
exact solution sets with open/closed endpoints. No variable denominators,
transcendental functions, or multivariable constraints. Infinity endpoints must
be open. Complete unions and isolated points are accepted.

Statistics: 1–100 bounded rational observations; mean, median, range, variance,
and standard deviation. Population uses n; sample uses n-1. Mode summaries return
all tied modes and no mode for all-distinct values. Sample spread is undefined for
one observation. This is descriptive analysis only, without inferential claims.

Skill instructions require the original problem/data, an explicit convention,
and a student attempt. MCP and HTTP share the same verification functions.

Validation:

```sh
python -m pytest -q tests/test_studio.py tests/test_algebra.py tests/test_custom_math.py
```

Commit provenance: the skill commit's author date is intentionally set to
November 11, 2026 at the project owner's request. Its committer timestamp records
when the commit was actually created. The frontend is a separate November 13
commit. No historical execution results are implied by those author dates.
