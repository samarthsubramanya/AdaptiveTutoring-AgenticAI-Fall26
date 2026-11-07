# Algebra answer checking

Use `algebra_problems` and `verify_algebra_answer` for the predefined bank.
For custom problems, use `verify_symbolic_answer`: real linear/quadratic equation
solving, polynomial simplification, expansion, factoring, and differentiation.
Expressions must use explicit multiplication and one variable (x, y, or t),
numeric constant denominators, and bounded integer powers. All real roots must
be provided for equation solving. Systems, inequalities, variable denominators,
transcendental equations, geometry, and proofs are outside the checker scope.

1. Obtain the problem list and match the user's problem ID or exact equation.
   Never substitute a different equation or invent an answer key. If there is
   no matching bank problem, use the custom checker for a supported operation.
   Preserve both equation sides and the requested variable. Ask the user to
   confirm a word-problem translation or ambiguous interpretation before checking.
2. Ask for a student attempt before grading. Accept a number, decimal, fraction,
   or `x=number`. Do not interpret an ambiguous response as an incorrect answer.
3. Call `verify_algebra_answer` with the original problem ID and the exact student
   response, or call `verify_symbolic_answer` on the confirmed custom problem.
   Only report the tool's status; never replace its verdict with your
   own. Invalid input, unsupported problems, and inconclusive results are ungraded.
4. For an incorrect answer, invite the student's working or a small hint. The
   final answer alone is insufficient evidence of a specific misconception.
5. For continued practice, direct the user to the **Algebra Tutor** page. That
   page has guided practice and LLM-assisted custom problems. It provides
   interpretation review, generated explanations/hints, and separate symbolic
   verification. General chat is not the authoritative practice-session grade.

Never call shell to evaluate student text. Never claim that the student's full
reasoning, mastery, or an unsupported problem has been verified.
