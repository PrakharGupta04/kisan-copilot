"""A2A client tool: CrewAI agent talks to the remote ADK agent using A2A JSON-RPC (message/send)."""
import time
import uuid

import httpx
from crewai.tools import tool

from . import config, security
from .observability import append_jsonl


def _texts(parts) -> list:
    return [p.get("text", "") for p in (parts or []) if isinstance(p, dict) and p.get("text")]


def extract_text(result: dict) -> str:
    out = []
    for art in result.get("artifacts") or []:
        out += _texts(art.get("parts"))
    if not out:
        out += _texts(((result.get("status") or {}).get("message") or {}).get("parts"))
    if not out:
        out += _texts(result.get("parts"))
    if not out:
        for m in reversed(result.get("history") or []):
            if m.get("role") == "agent":
                out += _texts(m.get("parts"))
                break
    return "\n".join(t for t in out if t).strip()


def call_insurance_agent(farmer_id: str, timeout: float = 120.0) -> str:
    t0 = time.perf_counter()
    log = config.LOG_DIR / "a2a_client.jsonl"
    try:
        fid = security.validate_farmer_id(farmer_id)
        with httpx.Client(timeout=timeout) as http:
            card = None
            for path in ("/.well-known/agent-card.json", "/.well-known/agent.json"):  # A2A discovery
                r = http.get(config.A2A_URL + path)
                if r.status_code == 200:
                    card = r.json()
                    break
            if card is None:
                return "ERROR: insurance agent card not found"
            payload = {"jsonrpc": "2.0", "id": uuid.uuid4().hex, "method": "message/send",
                       "params": {"message": {"kind": "message", "role": "user", "messageId": uuid.uuid4().hex,
                                              "parts": [{"kind": "text",
                                                         "text": f"Assess PMFBY insurance status for farmer {fid}."}]}}}
            resp = http.post(card.get("url") or config.A2A_URL + "/", json=payload)
            resp.raise_for_status()
            body = resp.json()
        if "error" in body:
            return f"ERROR: remote agent error: {str(body['error'])[:200]}"
        result = body.get("result") or {}
        state = (result.get("status") or {}).get("state")
        if state in ("failed", "rejected", "canceled"):
            return f"ERROR: remote task {state}"
        text = extract_text(result)
        if not text:
            return "ERROR: empty response from insurance agent"
        if security.scan_untrusted(text):  # trust boundary: screen what other agents send us
            append_jsonl(log, {"kind": "blocked_remote_response", "fid": fid})
            return "ERROR: remote response blocked by guardrail"
        append_jsonl(log, {"kind": "ok", "fid": fid, "agent": card.get("name"),
                           "latency_s": round(time.perf_counter() - t0, 2)})
        return text[:1500]
    except Exception as e:
        append_jsonl(log, {"kind": "error", "error": f"{type(e).__name__}: {e}"})
        return f"ERROR: insurance agent unreachable ({type(e).__name__})"


@tool("ask_insurance_agent")
def ask_insurance_agent(farmer_id: str) -> str:
    """Ask the remote PMFBY Insurance Agent (Google ADK, via A2A) about a farmer's crop-insurance eligibility,
    enrollment status, premium and deadline. Input: farmer id like F001."""
    return call_insurance_agent(farmer_id)