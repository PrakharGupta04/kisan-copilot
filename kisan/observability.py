"""Monitoring callbacks (JSONL audit trail) + Langfuse tracing (optional)."""
import json
import os
import sys
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config

_lock = threading.Lock()
_lf = None


def append_jsonl(path, ev: dict) -> None:
    try:
        with _lock, open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(ev, ensure_ascii=False, default=str) + "\n")
    except Exception:
        pass


def init_langfuse(service: str, instrumentors: list) -> bool:
    """Never raises. Returns True when Langfuse tracing is active."""
    global _lf
    if not (os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")):
        return False
    os.environ.setdefault("OTEL_SERVICE_NAME", service)
    os.environ.setdefault("LANGFUSE_BASE_URL", os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"))
    try:
        from langfuse import get_client
        _lf = get_client()
        if not _lf.auth_check():
            print("[obs] Langfuse auth failed; tracing disabled", file=sys.stderr)
            _lf = None
            return False
    except Exception as e:
        print(f"[obs] Langfuse unavailable: {e}", file=sys.stderr)
        _lf = None
        return False
    for name in instrumentors:
        try:
            if name == "crewai":
                from openinference.instrumentation.crewai import CrewAIInstrumentor
                CrewAIInstrumentor().instrument()
            elif name == "adk":
                from openinference.instrumentation.google_adk import GoogleADKInstrumentor
                GoogleADKInstrumentor().instrument()
            elif name == "litellm":
                from openinference.instrumentation.litellm import LiteLLMInstrumentor
                LiteLLMInstrumentor().instrument()
        except Exception as e:
            print(f"[obs] instrumentor '{name}' skipped: {e}", file=sys.stderr)
    return True


@contextmanager
def trace_run(name: str, **attrs):
    cm = None
    if _lf is not None:
        try:
            cm = _lf.start_as_current_span(name=name, input=attrs)
            cm.__enter__()
        except Exception:
            cm = None
    try:
        yield
    finally:
        if cm is not None:
            try:
                cm.__exit__(None, None, None)
            except Exception:
                pass
        if _lf is not None:
            try:
                _lf.flush()
            except Exception:
                pass


class Monitor:
    """Callback target for CrewAI step/task events. Writes logs/<run_id>.jsonl."""

    def __init__(self, run_id: str):
        self.run_id = run_id
        self.t0 = time.perf_counter()
        self.path = config.LOG_DIR / f"{run_id}.jsonl"
        self.on_tool = None
        self.counts = {"steps": 0, "tool_calls": 0, "errors": 0, "tasks": 0}

    def add(self, kind: str, name: str = "", **data) -> None:
        append_jsonl(self.path, {"ts": datetime.now(timezone.utc).isoformat(),
                                 "t": round(time.perf_counter() - self.t0, 2),
                                 "run": self.run_id, "kind": kind, "name": name, **data})

    def error(self, name: str, exc: Exception) -> None:
        self.counts["errors"] += 1
        self.add("error", name, error=f"{type(exc).__name__}: {str(exc)[:300]}")

    def step_cb(self, step) -> None:  # CrewAI step_callback
        try:
            self.counts["steps"] += 1
            tool = getattr(step, "tool", None)
            if tool:
                self.counts["tool_calls"] += 1
                tin, res = str(getattr(step, "tool_input", "")), str(getattr(step, "result", ""))
                self.add("tool_call", str(tool), input=tin[:300], result=res[:600])
                from .security import scan_untrusted
                hits = scan_untrusted(res)
                if hits:
                    self.add("guardrail_warning", str(tool), detail="possible injection in tool output", patterns=hits)
                if self.on_tool:
                    self.on_tool(str(tool), tin, res)
            else:
                self.add("agent_step", type(step).__name__, text=str(getattr(step, "output", step))[:300])
        except Exception:
            pass

    def task_cb(self, output) -> None:  # CrewAI task_callback
        try:
            self.counts["tasks"] += 1
            self.add("task_done", str(getattr(output, "agent", "")), summary=str(getattr(output, "raw", ""))[:300])
        except Exception:
            pass