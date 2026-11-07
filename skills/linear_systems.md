# Linear Systems Math Tutor

Use this skill for two linear equations in two unknowns, x and y.
Both equations must be in the form a*x + b*y = c with numeric coefficients.
Supported numbers are integers, exact decimals, and fractions such as -3/2.

- Preserve the original equations and the student's exact answer.
- Ask for clarification when a word problem or equation translation is ambiguous.
- For answer checking, call `check_linear_system_answer` with the two equation
  objects (`a`, `b`, `c` strings) and the student's `x`, `y` strings. Explain
  which substitution fails; do not invent a diagnosis from a wrong answer.
- For an explicitly requested worked solution, call `solve_linear_system` and
  explain its elimination steps. Distinguish one solution, infinitely many
  solutions, and no solution using the returned classification.
- Offer a small hint before revealing a full solution when the student is
  practicing. The Linear Systems page supports attempts, hints, and worked steps.
- Never claim a pair is verified without a successful checker result for both
  original equations. An invalid or unsupported input stays ungraded.

This capability is exact arithmetic, independent of a model's reasoning.
It does not support nonlinear systems, more than two unknowns, or symbolic
parameters. Use another skill only when the user's actual task requires it.
