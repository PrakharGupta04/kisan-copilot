"""MCP server (stdio). TOOLSET env var decides which tools this instance exposes (least privilege)."""
import json
import os

from mcp.server.fastmcp import FastMCP

from kisan import core_tools as ct
from kisan.security import validate_farmer_id

mcp = FastMCP("kisan-tools")
TOOLSET = os.getenv("TOOLSET", "all")


def _safe(fn) -> str:
    """Run a tool; always return validated JSON (a Pydantic model dump) or {'error': ...}."""
    try:
        return fn().model_dump_json()
    except ct.ToolError as e:
        return json.dumps({"error": str(e)})
    except Exception as e:
        return json.dumps({"error": f"internal error ({type(e).__name__})"})


if TOOLSET in ("weather", "all"):
    @mcp.tool()
    def get_weather_forecast(latitude: float, longitude: float) -> str:
        """7-day weather risk summary (rain, heat, frost) for an Indian location. Returns JSON."""
        if not (6 <= latitude <= 38 and 68 <= longitude <= 98):
            return json.dumps({"error": "coordinates outside India"})
        return _safe(lambda: ct.weather_summary(round(latitude, 2), round(longitude, 2)))

if TOOLSET in ("mandi", "all"):
    @mcp.tool()
    def get_mandi_prices(crop: str, state: str) -> str:
        """Mandi modal price (Rs/quintal), MSP comparison and trend signal for a crop in an Indian state. Returns JSON."""
        return _safe(lambda: ct.mandi_summary(crop[:40], state[:40]))

if TOOLSET in ("credit", "all"):
    @mcp.tool()
    def compute_kcc_metrics(farmer_id: str) -> str:
        """Look up a synthetic farmer's KCC account and compute utilization, days to due date and interest benefit. Returns JSON."""
        try:
            fid = validate_farmer_id(farmer_id)
        except ValueError as e:
            return json.dumps({"error": str(e)})
        return _safe(lambda: ct.kcc_metrics(fid))

if __name__ == "__main__":
    mcp.run(transport="stdio")