"""Learner-aware checking: the server re-verifies every answer before memory changes."""

from typing import Any, Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field
import sympy as sp

from tutoring import geometry
from tutoring.algebra import PROBLEMS, verify_answer
from tutoring.inequalities import InequalitySpec, verify as verify_inequality
from tutoring.learners import ALGEBRA_TOPIC, PREREQUISITES, TOPICS, LearnerStore, item_key
from tutoring.linear_systems import check_linear_system_answer
from tutoring.statistics import StatisticsSpec, summarize, verify as verify_statistic
from tutoring.symbolic import expression


router = APIRouter(prefix="/learners", tags=["Learner memory"])
learners = LearnerStore()

Skill = Literal["algebra", "inequalities", "statistics", "geometry", "linear_systems"]
Mode = Literal["start", "practice", "retrieve", "unassisted_check", "prerequisite_review"]
EXAMPLES: dict[str, list[dict[str, Any]]] = {
    "inequalities.linear": [{"expression": "2*x+3", "relation": "<=", "rhs": "11"},
                            {"expression": "-3*x+2", "relation": ">", "rhs": "8"}],
    "inequalities.quadratic": [{"expression": "x^2", "relation": ">=", "rhs": "4"},
                               {"expression": "x^2-5*x+6", "relation": "<", "rhs": "0"}],
    "statistics.center": [{"values": ["4", "7", "7", "9", "13"], "metric": "median", "convention": "population"},
                          {"values": ["3", "8", "10", "15"], "metric": "mean", "convention": "population"}],
    "statistics.spread": [{"values": ["2", "4", "4", "6"], "metric": "variance", "convention": "population"},
                          {"values": ["1", "3", "5", "7"], "metric": "variance", "convention": "sample"}],
}


def _pair(text: str) -> dict[str, str]:
    cleaned = text.replace("x", "").replace("y", "").replace("=", "").strip().strip("()[] ")
    parts = [p.strip() for p in cleaned.split(",")]
    if len(parts) != 2 or not all(parts):
        raise ValueError("Answer as (x, y), for example (2, -1).")
    return {"x": parts[0], "y": parts[1]}


def evaluate(skill: str, spec: dict[str, Any], answer: str) -> tuple[dict, str, str, tuple[str, ...]]:
    """(verification, topic, label, hint ladder) for one learner check, using the shared checkers."""
    if skill == "geometry":
        s = geometry.GeometrySpec(**spec)
        return (geometry.verify(s, answer) if answer else {}), f"geometry.{geometry.TOPIC[s.kind]}", geometry.prompt(s), geometry.hints(s)
    if skill == "inequalities":
        s = InequalitySpec(**spec)
        x = sp.Symbol(s.variable, real=True)
        degree = sp.Poly(expression(s.expression, s.variable) - expression(s.rhs, s.variable), x).degree()
        label = f"{s.expression} {s.relation} {s.rhs}"
        ladder = ("An inequality's solution is usually a whole interval, not one number.",
                  f"Solve the matching equation {s.expression} = {s.rhs} to find the boundary points.",
                  f"The boundary points split the number line. Test one value from each region in the original inequality, and decide whether each boundary is included ({s.relation}).")
        return (verify_inequality(s, answer) if answer else {}), ("inequalities.quadratic" if degree >= 2 else "inequalities.linear"), label, ladder
    if skill == "statistics":
        s = StatisticsSpec(**spec)
        summary = summarize(s)
        ordered = ", ".join(sorted(s.values, key=lambda v: float(expression(v, "x", numeric=True))))
        ladder = ("Decide which observations the measure uses, and whether their order matters.",
                  summary["hint"],
                  f"There are {summary['count']} observations; in order they are {ordered}. Apply the previous step to these values.")
        topic = "statistics.spread" if s.metric in {"variance", "standard_deviation"} else "statistics.center"
        label = f"{s.metric.replace('_', ' ')} of {', '.join(s.values)} ({s.convention})"
        return (verify_statistic(s, answer) if answer else {}), topic, label, ladder
    if skill == "algebra":
        problem_id = spec.get("problem_id")
        if set(spec) != {"problem_id"} or problem_id not in PROBLEMS:
            raise ValueError("Algebra checks need one bank problem_id.")
        problem = PROBLEMS[problem_id]
        return (verify_answer(problem_id, answer) if answer else {}), ALGEBRA_TOPIC[problem.topic], problem.equation, problem.hints
    if skill == "linear_systems":
        equations = spec.get("equations")
        if set(spec) != {"equations"}:
            raise ValueError("Linear-system checks need equations: [{a, b, c}, {a, b, c}].")
        ladder = ("Each equation is a line; the answer is the point on both lines.",
                  "Eliminate one variable: scale the equations so the x (or y) coefficients match, then subtract.",
                  "After finding one variable, substitute it into either original equation to find the other.")
        label = " ; ".join(f"{e['a']}x + {e['b']}y = {e['c']}" for e in equations)
        verification = {}
        if answer:
            result = check_linear_system_answer(equations, _pair(answer))
            verification = {**result, "status": "correct" if result["correct"] else "incorrect", "message": result["feedback"]}
        return verification, "linear_systems.elimination", label, ladder
    raise ValueError(f"Unknown skill {skill!r}.")


class Check(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: Skill
    spec: dict[str, Any]
    answer: str = Field(min_length=1, max_length=300)
    mode: Mode = "practice"
    confidence_before: int | None = Field(default=None, ge=1, le=5)


class HintRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    skill: Skill
    spec: dict[str, Any]
    reflection: str | None = Field(default=None, max_length=500)


class ConfidenceAfter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(min_length=1, max_length=40)
    confidence_after: int = Field(ge=1, le=5)


def _guard(call, *args, **kwargs):
    try:
        return call(*args, **kwargs)
    except KeyError as exc:
        raise HTTPException(404, str(exc).strip("'\"")) from None
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


def suggestions(plan: dict[str, Any]) -> dict[str, Any]:
    """Concrete items for the planned topic, so a frontend can act on the plan."""
    topic = plan.get("topic")
    if not topic:
        return plan
    if topic.startswith("geometry."):
        items = [p["id"] for p in geometry.problems() if f"geometry.{p['topic']}" == topic]
    elif topic.startswith("algebra."):
        items = [pid for pid, p in PROBLEMS.items() if ALGEBRA_TOPIC[p.topic] == topic]
    else:
        items = EXAMPLES.get(topic, [])
    return {**plan, "suggested": items}


@router.get("/{learner_id}")
def profile(learner_id: str):
    return _guard(learners.profile, learner_id)


@router.get("/{learner_id}/student.md", response_class=PlainTextResponse)
def student_file(learner_id: str):
    path = _guard(learners.path, learner_id)
    if not path.exists():
        raise HTTPException(404, "No verified evidence has been recorded for this learner yet.")
    return path.read_text(encoding="utf-8")


@router.get("/{learner_id}/plan")
def plan(learner_id: str, skill: Skill = Query()):
    return suggestions(_guard(learners.plan, learner_id, skill))


@router.post("/{learner_id}/check")
def check(learner_id: str, body: Check):
    _guard(learners.path, learner_id)
    verification, topic, label, _ = _guard(evaluate, body.skill, body.spec, body.answer)
    learning = _guard(learners.record, learner_id, skill=body.skill, topic=topic,
                      key=item_key(body.skill, body.spec), label=label, status=verification["status"],
                      mode=body.mode, confidence_before=body.confidence_before)
    return {"verification": verification, "topic": topic, "learning": learning,
            "plan": suggestions(_guard(learners.plan, learner_id, body.skill))}


@router.post("/{learner_id}/hint")
def hint(learner_id: str, body: HintRequest):
    _, topic, _, ladder = _guard(evaluate, body.skill, body.spec, "")
    return _guard(learners.hint, learner_id, key=item_key(body.skill, body.spec), topic=topic,
                  hints=ladder, reflection=body.reflection)


@router.post("/{learner_id}/confidence")
def confidence(learner_id: str, body: ConfidenceAfter):
    return _guard(learners.confidence_after, learner_id, body.event_id, body.confidence_after)


@router.get("")
def topics():
    """Topic catalogue and prerequisite graph."""
    return [{"topic": t, "label": label, "prerequisites": list(PREREQUISITES.get(t, ()))} for t, label in TOPICS.items()]
