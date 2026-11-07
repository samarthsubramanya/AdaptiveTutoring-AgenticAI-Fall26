"""Exercise the public math API and the agent's registered math tools."""

import json

import pytest
from fastapi.testclient import TestClient
from mcp.client import Client

from api.app import app
from mcp_server.server import mcp
from mcp_server.tools.linear_systems import check_linear_system_answer, solve_linear_system
from skills.registry import get_skill


EQUATIONS = [{"a": "1", "b": "1", "c": "5"}, {"a": "1", "b": "-1", "c": "1"}]
client = TestClient(app)


def test_math_routes_solve_and_check_without_external_services(monkeypatch):
    for name in ("ASU_LLM_API_KEY", "DATABASE_URL", "MCP_SERVER_URL"):
        monkeypatch.delenv(name, raising=False)
    result = client.post("/tutoring/linear-systems/solve", json={"equations": EQUATIONS})
    assert result.status_code == 200
    assert result.json()["solution"] == {"x": "3", "y": "2"}
    for answer, correct in [({"x": "3", "y": "2"}, True), ({"x": "2", "y": "3"}, False)]:
        checked = client.post("/tutoring/linear-systems/check", json={
            "equations": EQUATIONS, "answer": answer,
        })
        assert checked.status_code == 200
        assert checked.json()["correct"] is correct
        assert "solution" not in checked.json()
    assert "/requests" in app.openapi()["paths"]


@pytest.mark.parametrize("payload", [
    {"equations": EQUATIONS[:1]},
    {"equations": EQUATIONS, "unexpected": True},
    {"equations": [{"a": 1, "b": "1", "c": "5"}, EQUATIONS[1]]},
    {"equations": [{"a": "1/0", "b": "1", "c": "5"}, EQUATIONS[1]]},
    {"equations": [{"a": "2**99999", "b": "1", "c": "5"}, EQUATIONS[1]]},
    {"equations": [{"a": "9" * 33, "b": "1", "c": "5"}, EQUATIONS[1]]},
])
def test_invalid_math_is_ungraded(payload):
    assert client.post("/tutoring/linear-systems/solve", json=payload).status_code == 422


def test_invalid_answer_is_ungraded():
    response = client.post("/tutoring/linear-systems/check", json={
        "equations": EQUATIONS, "answer": {"x": "nan", "y": "2"},
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_skill_tools_share_the_exact_math_core():
    skill = get_skill("linear_systems")
    assert skill.allowed_tools == {"solve_linear_system", "check_linear_system_answer"}
    assert skill.load()
    assert (await solve_linear_system(EQUATIONS))["solution"] == {"x": "3", "y": "2"}
    assert (await check_linear_system_answer(EQUATIONS, {"x": "3", "y": "2"}))["correct"]


@pytest.mark.asyncio
async def test_mcp_advertises_and_executes_math_tools():
    async with Client(mcp) as connection:
        tools = await connection.list_tools()
        names = {tool.name for tool in tools.tools}
        assert {"solve_linear_system", "check_linear_system_answer", "web_search", "sql_executor"} <= names
        result = await connection.call_tool("check_linear_system_answer", {
            "equations": EQUATIONS, "answer": {"x": "2", "y": "3"},
        })
        assert not result.is_error
        payload = result.structured_content
        if payload is None:
            payload = json.loads("".join(item.text for item in result.content if hasattr(item, "text")))
        assert payload["correct"] is False
        assert [row["satisfied"] for row in payload["checks"]] == [True, False]
