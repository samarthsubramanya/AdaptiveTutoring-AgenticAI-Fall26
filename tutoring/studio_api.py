"""Credential-free deterministic skill APIs shared by both frontends."""

from fastapi import APIRouter, HTTPException
from pydantic import Field

from tutoring.inequalities import InequalitySpec, verify as verify_inequality
from tutoring.statistics import StatisticsSpec, verify as verify_statistic

router = APIRouter(prefix="/studio", tags=["Learning studio"])


class InequalityAnswer(InequalitySpec):
    answer: str = Field(min_length=1, max_length=300)


class StatisticsAnswer(StatisticsSpec):
    answer: str = Field(min_length=1, max_length=300)


@router.get("/skills")
def skills():
    return [
        {"id": "algebra", "title": "Algebra", "description": "Build confidence, one equation at a time.", "kind": "Guided practice", "topics": ["Equations", "Hints", "Guided practice"]},
        {"id": "inequalities", "title": "Inequalities", "description": "Discover the whole set of possibilities.", "kind": "Visual practice", "topics": ["Linear", "Quadratic", "Intervals"]},
        {"id": "statistics", "title": "Statistics", "description": "Find the story inside your numbers.", "kind": "Data lab", "topics": ["Center", "Spread", "Population & sample"]},
    ]


def _checked(call, spec, answer):
    try:
        return call(spec, answer)
    except (ValueError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/inequalities/check")
def inequality_check(body: InequalityAnswer):
    return _checked(verify_inequality, InequalitySpec(**body.model_dump(exclude={"answer"})), body.answer)


@router.post("/statistics/check")
def statistics_check(body: StatisticsAnswer):
    return _checked(verify_statistic, StatisticsSpec(**body.model_dump(exclude={"answer"})), body.answer)
