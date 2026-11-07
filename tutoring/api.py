"""Explicit tutoring endpoints; grading never depends on model-generated prose."""

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from typing import Literal

from tutoring.algebra import DEFAULT_PROBLEM_ID, list_problems
from tutoring.sessions import SessionConflict, SessionStore
from tutoring.custom import CaseStore
from tutoring.model import ModelResponseInvalid, ModelUnavailable, make_hint, propose


router = APIRouter(prefix="/tutoring", tags=["Algebra tutor"])
sessions = SessionStore()
cases = CaseStore()


class StartSession(BaseModel):
    model_config = ConfigDict(extra="forbid")
    problem_id: str = DEFAULT_PROBLEM_ID


class SessionAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0, strict=True)


class AnswerSubmission(SessionAction):
    problem_id: str
    answer: str = Field(min_length=1, max_length=80, strict=True)


class CustomQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prompt: str = Field(min_length=1, max_length=2000, strict=True)


class ConfirmedInterpretation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    confirmed: Literal[True]


class CustomAnswer(ConfirmedInterpretation):
    answer: str = Field(min_length=1, max_length=300, strict=True)


async def _model_call(operation, *args):
    try:
        return await operation(*args)
    except ModelUnavailable as exc:
        raise HTTPException(503, str(exc)) from exc
    except ModelResponseInvalid as exc:
        raise HTTPException(502, str(exc)) from exc


def _call(operation, *args):
    try:
        return operation(*args)
    except KeyError:
        raise HTTPException(404, "Session not found or expired. Start a new session.") from None
    except SessionConflict as exc:
        raise HTTPException(409, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/problems")
def problems():
    return list_problems()


@router.post("/sessions", status_code=201)
def create_session(body: StartSession):
    return _call(sessions.create, body.problem_id)


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    return _call(sessions.get, session_id)


@router.post("/sessions/{session_id}/answers")
def answer(session_id: str, body: AnswerSubmission):
    return _call(sessions.attempt, session_id, body.problem_id, body.answer, body.revision)


@router.post("/sessions/{session_id}/hint")
def hint(session_id: str, body: SessionAction):
    return _call(sessions.hint, session_id, body.revision)


@router.post("/sessions/{session_id}/next")
def next_problem(session_id: str, body: SessionAction):
    return _call(sessions.advance, session_id, body.revision)


@router.delete("/sessions/{session_id}", status_code=204)
def delete_session(session_id: str):
    _call(sessions.delete, session_id)
    return Response(status_code=204)


@router.post("/math/cases", status_code=201)
async def prepare_custom_problem(body: CustomQuestion):
    if not body.prompt.strip():
        raise HTTPException(422, "Enter a math question.")
    proposal = await _model_call(propose, body.prompt)
    if proposal.problem.operation == "unsupported":
        raise HTTPException(422, "Outside supported scope: " + proposal.problem.interpretation)
    return _call(cases.create, body.prompt, proposal)


@router.get("/math/cases/{case_id}")
def get_custom_problem(case_id: str):
    return _call(cases.get, case_id)


@router.post("/math/cases/{case_id}/answers")
def check_custom_answer(case_id: str, body: CustomAnswer):
    return _call(cases.verify, case_id, body.answer)


@router.post("/math/cases/{case_id}/hint")
async def custom_hint(case_id: str, body: ConfirmedInterpretation):
    state = _call(cases.get, case_id)
    if len(state["hints"]) >= 3:
        raise HTTPException(409, "Three hints have already been provided for this case.")
    hint = await _model_call(make_hint, state["question"], state["problem"], state["answer"], state["verification"])
    return _call(cases.add_hint, case_id, hint)


@router.delete("/math/cases/{case_id}", status_code=204)
def delete_custom_problem(case_id: str):
    _call(cases.delete, case_id)
    return Response(status_code=204)
