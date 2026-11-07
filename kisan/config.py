"""Central configuration. Imported first by every process."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

# Keep CrewAI's own telemetry off so it does not fight our Langfuse/OTel setup
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("CREWAI_DISABLE_TRACKING", "true")
os.environ.setdefault("LITELLM_LOG", "ERROR")

DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
DATA_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

DB_PATH = Path(os.getenv("KISAN_DB", str(DATA_DIR / "kisan.db")))
CREW_MODEL = os.getenv("CREW_MODEL", "groq/llama-3.3-70b-versatile")
ADK_MODEL = os.getenv("ADK_MODEL", CREW_MODEL)
A2A_URL = os.getenv("INSURANCE_A2A_URL", "http://localhost:8001").rstrip("/")
A2A_PORT = int(os.getenv("A2A_PORT", "8001"))
MAX_RPM = int(os.getenv("MAX_RPM", "10"))
OFFLINE = os.getenv("OFFLINE", "0") == "1"
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "")
API_KEY = os.getenv("API_KEY", "")
PRICE_IN_PER_M = float(os.getenv("PRICE_IN_PER_M", "0.59"))
PRICE_OUT_PER_M = float(os.getenv("PRICE_OUT_PER_M", "0.79"))