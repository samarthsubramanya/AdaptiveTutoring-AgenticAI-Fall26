"""Read-only learner memory for teaching skills; only verified checks write to it."""

from typing import Literal

from tutoring.learner_api import learners, suggestions


async def get_learner_profile(learner_id: str) -> dict:
    """Per-topic verified evidence, support level and confidence calibration for one learner.

    Use it to personalise support. Never treat it as a mastery certificate, and
    never infer facts it does not contain.
    """
    try:
        return learners.profile(learner_id)
    except ValueError as exc:
        return {"status": "unsupported", "message": str(exc)}


async def plan_learner_next_step(
    learner_id: str,
    skill: Literal["algebra", "inequalities", "statistics", "geometry", "linear_systems"],
) -> dict:
    """The evidence-based first action for a skill: start, retrieve, unassisted_check,
    prerequisite_review or practice, with the reason, support level and suggested items.
    """
    try:
        return suggestions(learners.plan(learner_id, skill))
    except ValueError as exc:
        return {"status": "unsupported", "message": str(exc)}
