"""Agent tools share the HTTP authority, including revision and hint gates."""
import asyncio
from fastapi import FastAPI
import httpx
from tutoring.journey import JourneyStore
from tutoring.journey_api import create_router
from tutoring.learners import LearnerStore
from mcp_server.tools import journeys as tools


def test_tools_use_the_http_state_and_do_not_make_a_second_engine(tmp_path, monkeypatch):
    app = FastAPI()
    engine = JourneyStore(LearnerStore(tmp_path))
    app.include_router(create_router(engine))
    real_client = httpx.AsyncClient
    def client(**kwargs):
        return real_client(transport=httpx.ASGITransport(app=app), **kwargs)
    monkeypatch.setattr(tools.httpx, 'AsyncClient', client)
    async def run():
        state = await tools.start_learning_journey('tool-student', 'statistics', 'statistics.center')
        assert state['session_id'] in engine.sessions
        state = await tools.request_learning_hint(state['session_id'], state['revision'])
        assert state['hint']['status'] == 'attempt_first'
        latest = await tools.get_learning_journey(state['session_id'])
        assert latest['revision'] == state['revision']
        solved = await tools.submit_learning_attempt(state['session_id'], state['revision'], '3')
        assert solved['solved']
        replay = await tools.submit_learning_attempt(state['session_id'], state['revision'], '3')
        assert replay['http_status'] == 409
        assert (await tools.get_learning_journey('../escape'))['status'] == 'invalid_input'
    asyncio.run(run())
