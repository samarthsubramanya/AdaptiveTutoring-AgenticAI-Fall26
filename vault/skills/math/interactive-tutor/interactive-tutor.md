---
name: interactive-tutor
id: math.interactive-tutor
domain: mathematics
tags: [math, teaching, adaptive, skill]
---

# Run an interactive mathematics journey

Use start_learning_journey, get_learning_journey, submit_learning_attempt,
request_learning_hint, and advance_learning_journey. These are the same server
sessions used by the Learning journey frontend and evaluated by the session
benchmark. The server selects the item, mode, prerequisite, and fresh check.

1. Ask for a pseudonymous learner ID and subject. Start or resume the session.
2. Show only the current prompt and ask for an attempt. Do not reveal a tool’s
   answer in advance, invent student answers, or submit on the student's behalf.
3. Submit exactly the supplied answer with the latest revision. On a stale
   revision, reload; do not blindly replay the action.
4. Offer only server-authorized hints. A first attempt is required, reflections
   precede deeper hints, and unaided checks prohibit hints. Do not evade these
   gates with other tools or model-generated solutions.
5. Advance only when allowed: prerequisite review after difficulty, return to the
   original problem, then a genuinely fresh unaided check after assisted success.
6. On re-entry, explain the server's next decision using stored verified evidence.
   No public/student-learning gains or mastery claims follow from synthetic runs.

Sessions expire after one idle hour; STUDENT.md retains verified evidence.
Use a pseudonym; local demo access is not authenticated or suitable for public
student deployment without additional access controls.

## Connections

- [[skills/math/DOMAIN|Mathematics]]
- [[skills/teaching/DOMAIN|Teaching]]
- [[skills/teaching/retrieve-first-gate/retrieve-first-gate|Retrieve before help]]
- [[skills/teaching/progressive-hint-ladder/progressive-hint-ladder|Hint ladder]]
- [[skills/teaching/unassisted-evidence-checkpoint/unassisted-evidence-checkpoint|Unaided check]]
- [[skills/teaching/fading-manager/fading-manager|Fading support]]
- [[skills/math/algebra/algebra|Algebra]]
- [[skills/math/inequalities/inequalities|Inequalities]]
- [[skills/math/statistics/statistics|Statistics]]
- [[skills/math/geometry/geometry|Geometry]]
