import asyncio
import json
import os
import sys
from pathlib import Path

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parent.parent


async def _session_call(toolset, tool=None, args=None):
    env = {k: os.environ[k] for k in ("PATH", "HOME", "KISAN_DB") if k in os.environ}
    env.update({"TOOLSET": toolset, "PYTHONPATH": str(ROOT), "PYTHONUNBUFFERED": "1"})
    params = StdioServerParameters(command=sys.executable, args=["-m", "kisan.mcp_server"],
                                   env=env, cwd=str(ROOT))
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()
            names = [t.name for t in (await s.list_tools()).tools]
            result = None
            if tool:
                result = await s.call_tool(tool, args or {})
            return names, result


def _json(result):
    return json.loads(result.content[0].text)


@pytest.mark.parametrize("toolset,tool", [("weather", "get_weather_forecast"),
                                          ("mandi", "get_mandi_prices"),
                                          ("credit", "compute_kcc_metrics")])
def test_toolset_exposes_only_its_own_tool(toolset, tool):
    names, _ = asyncio.run(_session_call(toolset))
    assert names == [tool]


def test_credit_tool_returns_validated_json():
    _, res = asyncio.run(_session_call("credit", "compute_kcc_metrics", {"farmer_id": "F002"}))
    d = _json(res)
    assert d["farmer_id"] == "F002"
    assert d["overdue"] is True


def test_credit_tool_rejects_bad_farmer_id():
    _, res = asyncio.run(_session_call("credit", "compute_kcc_metrics", {"farmer_id": "../etc"}))
    assert "error" in _json(res)


def test_weather_tool_rejects_coordinates_outside_india():
    _, res = asyncio.run(_session_call("weather", "get_weather_forecast", {"latitude": 0.0, "longitude": 0.0}))
    assert "outside India" in _json(res)["error"]


def test_mandi_tool_unsupported_crop_returns_error():
    _, res = asyncio.run(_session_call("mandi", "get_mandi_prices", {"crop": "banana", "state": "Kerala"}))
    assert "error" in _json(res)
