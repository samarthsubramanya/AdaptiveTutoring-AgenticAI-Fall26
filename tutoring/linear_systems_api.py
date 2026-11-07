"""Exact linear-system solving and student answer checks."""

from typing import Annotated

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from tutoring.linear_systems import check_linear_system_answer, solve_linear_system


Number = Annotated[str, Field(min_length=1, max_length=32, strict=True)]
router = APIRouter(prefix="/tutoring/linear-systems", tags=["Linear systems"])


class Equation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    a: Number
    b: Number
    c: Number


class LinearSystem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    equations: list[Equation] = Field(min_length=2, max_length=2)


class Answer(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: Number
    y: Number


class AnswerSubmission(LinearSystem):
    answer: Answer


@router.post("/solve")
def solve(body: LinearSystem):
    try:
        return solve_linear_system([equation.model_dump() for equation in body.equations])
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.post("/check")
def check(body: AnswerSubmission):
    try:
        return check_linear_system_answer(
            [equation.model_dump() for equation in body.equations], body.answer.model_dump()
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
