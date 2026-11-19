"""Prove experiment settings flow through the public API and MCP tools."""

import json

import pytest
from fastapi.testclient import TestClient
from mcp.client import Client

from api.app import app
from mcp_server.server import mcp
from skills.registry import get_skill


client = TestClient(app)
URL = "/math/probability/experiments"


def test_seeded_api_runs_without_model_or_database_credentials(monkeypatch):
    for name in ("ASU_LLM_API_KEY", "DATABASE_URL", "MCP_SERVER_URL"):
        monkeypatch.delenv(name, raising=False)
    body = {"experiment": "dice_sum", "trials": 100, "seed": 17}
    first = client.post(URL, json=body)
    assert first.status_code == 200
    result = first.json()
    assert result == client.post(URL, json=body).json()
    assert result["parameters"] == {"trials": 100, "seed": 17}
    assert sum(row["count"] for row in result["distribution"]) == 100
    assert result["summary"]["theoretical_mean"] == 7
    assert result["convergence"][-1]["trial"] == 100
    assert "/requests" in app.openapi()["paths"]


def test_coin_settings_are_applied_and_recorded():
    result = client.post(URL, json={
        "experiment": "coin_heads", "trials": 4, "seed": 0,
        "coin_tosses": 3, "heads_probability": 1.0,
    })
    assert result.status_code == 200
    data = result.json()
    assert data["parameters"]["coin_tosses"] == 3
    assert data["parameters"]["heads_probability"] == 1.0
    assert data["distribution"][-1]["count"] == 4
    assert data["summary"]["max_probability_gap"] == 0


@pytest.mark.parametrize("changes", [
    {"experiment": "roulette"}, {"trials": 0}, {"trials": 10001},
    {"trials": True}, {"seed": -1}, {"seed": 2**32}, {"seed": "42"},
    {"coin_tosses": 21}, {"heads_probability": 1.1},
    {"heads_probability": True}, {"unexpected": "value"},
])
def test_invalid_request_is_rejected(changes):
    body = {"experiment": "coin_heads", **changes}
    assert client.post(URL, json=body).status_code == 422


def test_dice_does_not_silently_ignore_coin_parameters():
    response = client.post(URL, json={"experiment": "dice_sum", "heads_probability": 0.9})
    assert response.status_code == 422


def test_event_settings_reach_the_simulation():
    body = {"experiment": "dice_sum", "event_operator": "gte", "event_value": 9}
    response = client.post(URL, json=body)
    assert response.status_code == 200
    event = response.json()["event"]
    assert event["count"] == 300
    assert event["theoretical_probability"] == pytest.approx(10 / 36)
    earlier = next(point for point in event["convergence"] if point["trial"] == 100)
    assert earlier["count"] == 28
    assert earlier["confidence_interval"] == pytest.approx({
        "level": 0.95, "lower": 0.20139685, "upper": 0.37488029,
    })
    for invalid in ({"event_value": True}, {"event_value": 1}, {"event_operator": None}):
        assert client.post(URL, json={**body, **invalid}).status_code == 422


@pytest.mark.asyncio
async def test_probability_skill_is_advertised_and_callable_through_mcp():
    skill = get_skill("probability")
    assert skill.allowed_tools == {"run_probability_experiment"}
    assert skill.load()
    async with Client(mcp) as connection:
        advertised = await connection.list_tools()
        names = {tool.name for tool in advertised.tools}
        assert {"run_probability_experiment", "sql_executor", "web_search"} <= names
        result = await connection.call_tool("run_probability_experiment", {
            "experiment": "dice_sum", "trials": 10, "seed": 42,
            "event_operator": "gte", "event_value": 9,
        })
        assert not result.is_error
        payload = result.structured_content
        if payload is None:
            payload = json.loads("".join(item.text for item in result.content if hasattr(item, "text")))
        assert sum(row["count"] for row in payload["distribution"]) == 10
        assert payload["summary"]["theoretical_mean"] == 7
        assert payload["event"]["theoretical_probability"] == pytest.approx(10 / 36)


@pytest.mark.asyncio
async def test_mcp_does_not_coerce_booleans_or_strings_into_experiment_settings():
    async with Client(mcp) as connection:
        for invalid in ({"trials": True}, {"seed": "42"}, {"coin_tosses": True},
                        {"heads_probability": False}, {"event_operator": "eq", "event_value": True}):
            result = await connection.call_tool("run_probability_experiment", {
                "experiment": "coin_heads", **invalid,
            })
            assert result.is_error, invalid
