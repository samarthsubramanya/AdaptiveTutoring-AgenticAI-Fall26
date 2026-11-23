"""Interactive journey API. Revision checks bind all actions to server-owned state."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from tutoring.journey import JourneyStore, JourneyConflict, ITEMS, DEFAULT_TOPIC
from tutoring.learner_api import learners
from tutoring.learners import TOPICS


class Start(BaseModel):
    model_config = ConfigDict(extra="forbid")
    learner_id: str = Field(min_length=3, max_length=40)
    skill: str = Field(max_length=30)
    topic: str | None = Field(default=None, max_length=60)


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=0, strict=True)


class Answer(Action):
    answer: str = Field(min_length=1, max_length=300)
    confidence_before: int | None = Field(default=None, ge=1, le=5, strict=True)


class Hint(Action):
    reflection: str | None = Field(default=None, max_length=500)


def create_router(store: JourneyStore):
    router = APIRouter(prefix="/journeys", tags=["Interactive tutoring"])
    def call(fn, *args):
        try:
            return fn(*args)
        except KeyError as exc:
            raise HTTPException(404, str(exc).strip("'")) from None
        except JourneyConflict as exc:
            raise HTTPException(409, str(exc)) from exc
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, str(exc)) from exc

    @router.get("/catalog")
    def catalog():
        return [{"skill": skill, "topics": [{"id": t, "label": TOPICS[t],
                  "items": sum(i["topic"] == t for i in ITEMS.values())}
                 for t in TOPICS if any(i["topic"] == t for i in ITEMS.values()) and t.startswith(skill + ".")]}
                for skill in DEFAULT_TOPIC]

    @router.post("/sessions", status_code=201)
    def start(body: Start):
        return call(store.start, body.learner_id, body.skill, body.topic)

    @router.get("/sessions/{sid}")
    def get(sid: str):
        return call(store.get, sid)

    @router.post("/sessions/{sid}/answers")
    def answer(sid: str, body: Answer):
        return call(store.answer, sid, body.revision, body.answer, body.confidence_before)

    @router.post("/sessions/{sid}/hints")
    def hint(sid: str, body: Hint):
        return call(store.hint, sid, body.revision, body.reflection)

    @router.post("/sessions/{sid}/next")
    def advance(sid: str, body: Action):
        return call(store.advance, sid, body.revision)

    @router.delete("/sessions/{sid}", status_code=204)
    def close(sid: str):
        with store.lock:
            call(store._get, sid)
            del store.sessions[sid]

    return router


journeys = JourneyStore(learners)
router = create_router(journeys)
