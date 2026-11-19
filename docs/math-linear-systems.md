# Linear Systems Math Practice

A work-in-progress tutor for two linear equations in two unknowns. Enter
coefficients, try an x/y answer, request a hint, and reveal worked elimination
steps. Each proposed pair is checked against both original equations using
exact rational arithmetic.

This complements the single-variable algebra work on `samarth/math`. It runs
without model credentials or a database. The existing agent can also discover
the `linear_systems` skill and its two MCP tools.

## Run the math demo

From the repository root, using Python 3.11 or newer:

```sh
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

In a second terminal with that environment active:

```sh
python -m streamlit run ui/pages/4_Linear_Systems.py
```

The page is also available in the normal multipage app. Set `API_BASE_URL`
when the backend runs at another address. For agent delegation, also start
`python -m mcp_server.server` and configure the existing model/MCP settings.

## Demonstration

1. Start with `x + y = 5` and `x - y = 1`.
2. Try `x = 2`, `y = 3`. The first equation passes; the second fails.
3. Request a hint, then submit `x = 3`, `y = 2`. Both substitutions pass.
4. Reveal the worked solution to inspect the elimination and exact checks.
5. Try the fractional example and the no-solution/infinite-solution examples.

The API accepts exactly two objects with numeric string fields `a`, `b`, `c`
representing `a*x + b*y = c`:

```sh
curl http://127.0.0.1:8000/tutoring/linear-systems/check \
  -H 'Content-Type: application/json' \
  -d '{"equations":[{"a":"1","b":"1","c":"5"},{"a":"1","b":"-1","c":"1"}],"answer":{"x":"3","y":"2"}}'
```

Use `/tutoring/linear-systems/solve` with the same equations and no `answer`
field to obtain the classification, exact solution, hint, and worked steps.

## Scope

Integers, finite decimals, and fractions are supported. Arbitrary expressions,
nonlinear equations, symbolic parameters, and more than two unknowns are
outside this prototype. A hint or a correct final pair does not establish
student mastery; intermediate student reasoning is not graded.

The math page is deterministic. Its direct API calls do not produce agent
runtime traces or offline-learning results. No external demonstration or
learning-outcome evaluation has been recorded as part of this feature.

## Checks

```sh
python -m pytest tests/test_linear_systems.py tests/test_linear_systems_api.py tests/test_linear_systems_ui.py
```
