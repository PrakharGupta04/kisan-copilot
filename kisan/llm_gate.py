"""LLM quota gate: pacing (RPM), daily budget (RPD) and error classification. Makes no network calls."""
import json
import re
import threading
import time
from datetime import date

from . import config


class QuotaExhausted(RuntimeError):
    pass


_lock = threading.Lock()
_last = -1e9


def _path():
    return config.LOG_DIR / f"quota_{date.today().isoformat()}.json"


def calls_today() -> int:
    try:
        return int(json.loads(_path().read_text()).get("calls", 0))
    except Exception:
        return 0


def record_call() -> None:
    with _lock:
        try:
            _path().write_text(json.dumps({"calls": calls_today() + 1}))
        except Exception:
            pass


def before_call() -> None:
    """Raise QuotaExhausted if the daily budget is used up; otherwise sleep just enough to respect RPM."""
    global _last
    if calls_today() >= config.GEMINI_RPD:
        raise QuotaExhausted(f"daily budget reached ({config.GEMINI_RPD} calls)")
    with _lock:
        wait = 60.0 / max(config.GEMINI_RPM, 1) - (time.monotonic() - _last)
        if wait > 0:
            time.sleep(wait)
        _last = time.monotonic()


def classify(exc) -> tuple:
    """Return (kind, delay_seconds). kind: daily | rpm | unavailable | other."""
    low = str(exc).lower()
    flat = re.sub(r"[^a-z]", "", low)
    m = re.search(r"retry(?:delay|\s+in)\D{0,12}(\d+(?:\.\d+)?)", low)
    delay = float(m.group(1)) if m else 0.0
    if "429" in low or "resource_exhausted" in low or "quota" in low:
        if "perday" in flat:
            return "daily", 0.0
        return "rpm", max(delay, 20.0)
    if any(k in low for k in ("503", "unavailable", "overloaded", "high demand", "timeout", "timed out", "connection")):
        return "unavailable", max(delay, 8.0)
    return "other", 0.0


if __name__ == "__main__":
    print(json.dumps({"day": date.today().isoformat(), "limits": {"rpm": config.GEMINI_RPM, "rpd": config.GEMINI_RPD},
                      "calls_today": calls_today()}))
