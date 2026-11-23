"""Route agent turns to the authoritative API process, shared with React.

Do not create a second in-process JourneyStore here: the MCP server normally runs
in a separate process, so that would split session state and race on STUDENT.md.
"""

import os
from uuid import UUID
import httpx


async def _request(path: str, body=None):
    base = os.getenv("KERNEL_API_URL") or os.getenv("API_BASE_URL") or "http://127.0.0.1:8000"
    try:
        async with httpx.AsyncClient(base_url=base.rstrip("/"), timeout=20) as client:
            response = await client.request("GET" if body is None else "POST", path, json=body)
        if "application/json" not in response.headers.get("content-type", ""):
            return {"status": "unavailable", "message": "The tutoring API returned an unexpected response."}
        data = response.json()
        if not response.is_success:
            return {"status": "conflict" if response.status_code == 409 else "unavailable",
                    "message": data.get("detail", "The tutoring API rejected the action."), "http_status": response.status_code}
        return data
    except httpx.HTTPError:
        return {"status": "unavailable", "message": "Cannot reach the tutoring API. Start the API and check KERNEL_API_URL. Do not replay an uncertain action without reloading the session."}


def _session_path(session_id):
    try:
        UUID(session_id)
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Use the session ID returned by start_learning_journey.") from None
    return f"/journeys/sessions/{session_id}"


async def _turn(session_id, revision, action, **fields):
    if type(revision) is not int or revision < 0:
        return {"status": "invalid_input", "message": "Use the latest nonnegative integer revision."}
    try:
        path = _session_path(session_id)
    except ValueError as exc:
        return {"status": "invalid_input", "message": str(exc)}
    return await _request(path + "/" + action, {"revision": revision, **fields})


async def start_learning_journey(learner_id: str, skill: str, topic: str | None = None) -> dict:
    """Start a server-owned journey for a pseudonymous learner; show its prompt and wait for a student attempt.

    Skills: algebra, inequalities, statistics, geometry, linear_systems.
    Server evidence determines the mode and item; do not bypass its teaching gates.
    """
    return await _request("/journeys/sessions", {"learner_id": learner_id, "skill": skill, "topic": topic})


async def get_learning_journey(session_id: str) -> dict:
    """Get the same current prompt, revision and progress used by the web frontend."""
    try:
        return await _request(_session_path(session_id))
    except ValueError as exc:
        return {"status": "invalid_input", "message": str(exc)}


async def submit_learning_attempt(session_id: str, revision: int, answer: str) -> dict:
    """Submit only the student's actual answer; never invent an attempt or override the returned grade."""
    if not isinstance(answer, str) or not 1 <= len(answer) <= 300:
        return {"status": "invalid_input", "message": "Supply a student answer of 1–300 characters."}
    return await _turn(session_id, revision, "answers", answer=answer)


async def request_learning_hint(session_id: str, revision: int, reflection: str | None = None) -> dict:
    """Request a server-authorized hint; attempt-first, reflection and unaided-check gates are enforced."""
    if reflection is not None and len(reflection) > 500:
        return {"status": "invalid_input", "message": "Use a reflection of at most 500 characters."}
    return await _turn(session_id, revision, "hints", reflection=reflection)


async def advance_learning_journey(session_id: str, revision: int) -> dict:
    """Continue to the server-selected prerequisite, original problem or fresh unaided check when allowed."""
    return await _turn(session_id, revision, "next")
