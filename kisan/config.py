"""Central configuration (environment-driven). Imported first by every process.

Never prints or logs secret values. Run `python -m kisan.config` to see a safe summary.
"""
import json
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Keep CrewAI's own telemetry off so it does not fight our Langfuse/OTel setup
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
os.environ.setdefault("LITELLM_LOG", "ERROR")

# The Gemini key may be stored under either name; make both available without printing them.
if os.environ.get("GOOGLE_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
    os.environ["GEMINI_API_KEY"] = os.environ["GOOGLE_API_KEY"]
elif os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.environ["GEMINI_API_KEY"]


def _int(name: str, default: int) -> int:
    try:
        raw = str(os.getenv(name, "")).strip()
        v = int(raw) if raw else default
        return v if v > 0 else default
    except ValueError:
        return default


def _float(name: str, default: float) -> float:
    try:
        raw = str(os.getenv(name, "")).strip()
        v = float(raw) if raw else default
        return v if v >= 0 else default
    except ValueError:
        return default


def _bool(name: str, default: bool = False) -> bool:
    raw = str(os.getenv(name, "")).strip().lower()
    if not raw:
        return default
    return raw in ("1", "true", "yes", "on")


DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

DB_PATH = Path(os.getenv("KISAN_DB", str(DATA_DIR / "kisan.db")))

# ---- models (free tier: only the *-lite models have a usable daily quota) ----
CREW_MODEL = os.getenv("CREW_MODEL", "gemini/gemini-3.5-flash-lite")
ADK_MODEL = os.getenv("ADK_MODEL", "gemini-3.5-flash-lite")
FALLBACK_MODEL = os.getenv("FALLBACK_MODEL", "")

# ---- quota (UNVERIFIED defaults for gemini-3.5-flash-lite: 15 RPM / 250K TPM / 500 RPD; edit in .env) ----
GEMINI_RPM = _int("GEMINI_RPM", 12)
GEMINI_RPD = _int("GEMINI_RPD", 450)
GEMINI_TPM = _int("GEMINI_TPM", 200000)
MAX_RPM = _int("MAX_RPM", GEMINI_RPM)

# ---- cost estimate (free tier = 0; set real prices only to estimate an equivalent paid cost) ----
PRICE_IN_PER_M = _float("PRICE_IN_PER_M", 0.0)
PRICE_OUT_PER_M = _float("PRICE_OUT_PER_M", 0.0)

# ---- pipeline behaviour ----
TOOL_MODE = os.getenv("TOOL_MODE", "prefetch").strip().lower()
if TOOL_MODE not in ("prefetch", "agentic"):
    TOOL_MODE = "prefetch"
OFFLINE = _bool("OFFLINE")
RUN_TIMEOUT = _int("RUN_TIMEOUT", 300)
MCP_TOOL_TIMEOUT = _int("MCP_TOOL_TIMEOUT", 60)
A2A_TIMEOUT = _int("A2A_TIMEOUT", 90)
ADK_POLL_TIMEOUT = _int("ADK_POLL_TIMEOUT", 45)
A2A_URL = os.getenv("INSURANCE_A2A_URL", "http://localhost:8001").rstrip("/")
A2A_PORT = _int("A2A_PORT", 8001)

# ---- optional integrations ----
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "")
API_KEY = os.getenv("API_KEY", "")


def public_settings() -> dict:
    """Safe-to-print snapshot: secrets are reported only as set/unset."""
    return {
        "crew_model": CREW_MODEL,
        "adk_model": ADK_MODEL,
        "fallback_model": FALLBACK_MODEL or None,
        "tool_mode": TOOL_MODE,
        "offline": OFFLINE,
        "gemini_rpm": GEMINI_RPM,
        "gemini_rpd": GEMINI_RPD,
        "gemini_tpm": GEMINI_TPM,
        "max_rpm": MAX_RPM,
        "price_in_per_m": PRICE_IN_PER_M,
        "price_out_per_m": PRICE_OUT_PER_M,
        "run_timeout": RUN_TIMEOUT,
        "mcp_tool_timeout": MCP_TOOL_TIMEOUT,
        "a2a_timeout": A2A_TIMEOUT,
        "adk_poll_timeout": ADK_POLL_TIMEOUT,
        "a2a_url": A2A_URL,
        "a2a_port": A2A_PORT,
        "db_path": str(DB_PATH),
        "google_api_key_set": bool(os.getenv("GOOGLE_API_KEY")),
        "gemini_api_key_set": bool(os.getenv("GEMINI_API_KEY")),
        "data_gov_api_key_set": bool(DATA_GOV_API_KEY),
        "api_key_set": bool(API_KEY),
        "langfuse_keys_set": bool(os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")),
    }


if __name__ == "__main__":
    print(json.dumps(public_settings(), indent=2))
