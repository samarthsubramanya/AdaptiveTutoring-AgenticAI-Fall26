# Descriptive statistics practice and verification

Use `verify_statistics_answer` to check mean, median, range, variance, or standard
deviation on 1–100 explicitly supplied rational observations.

1. Confirm all observations and the requested statistic. For variance or standard
   deviation, explicitly establish whether population (`n`) or sample (`n - 1`)
   is intended; never silently choose one for an ambiguous student question.
2. Ask for a student attempt. Preserve repeated observations and negative values.
3. Call the tool with the values, answer, metric, and convention. Report its status
   and rounding tolerance. Invalid input and unsupported cases are ungraded.
4. Use one small hint at a time: ordering for median, the divisor for mean,
   squared deviations for variance. Encourage the student to show their working.

Modes in the returned summary include all ties; all-distinct observations have
no mode. Sample variance/standard deviation require at least two observations.
No hypothesis testing, causal inference, population generalization, or mastery
claims. Never invent missing data or execute submitted text.
