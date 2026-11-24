import json
import time
import types

import pytest

from kisan import config, core_tools as ct, crew, db, llm_gate
from kisan.observability import Monitor
from kisan.schemas import RunState

SYNTH_RAW = ('```json\n{"summary": "S", "recommendations": [{"priority": 1, "title": "Repay", "detail": "d", '
             '"source_agents": ["credit"], "confidence": 90},], "risks": [], "overall_confidence": 80, '
             '"message": {"hindi": "नमस्ते", "english": "hi", "sms": "hi"}}\n```')


def _fake(raw):
    return types.SimpleNamespace(output=types.SimpleNamespace(raw=raw, pydantic=None))


@pytest.fixture
def env(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "OFFLINE", False)
    monkeypatch.setattr(crew, "_collect_evidence",
                        lambda profile, selected, state, mon: {k: json.dumps({"k": k}) for k in selected if k != "insurance"})
    monkeypatch.setattr("kisan.a2a_client.call_insurance_agent", lambda fid: "pmfby evidence ok")
    monkeypatch.setattr(ct, "weather_summary", lambda *a, **k: (_ for _ in ()).throw(ct.ToolError("off")))
    monkeypatch.setattr(ct, "_live_mandi", lambda *a, **k: None)
    return tmp_path


def _agentic(fid="F002"):
    p = db.get_farmer(fid)
    st = RunState(run_id="t", farmer_id=fid, profile=p)
    mon = Monitor("t")
    return crew._agentic(p, None, st, mon, time.perf_counter()), st


def test_enforce_plan_keeps_mandatory_agents():
    p = db.get_farmer("F006")
    plan = crew._enforce_plan(["mandi"], p)
    assert "weather" in plan and "insurance" in plan


def test_parse_handles_fences_and_trailing_comma():
    s = crew._parse(_fake(SYNTH_RAW), crew._Synth)
    assert s is not None
    assert s.recommendations[0].confidence == 0.9
    assert s.message.sms == "hi"


def test_parse_garbage_returns_none():
    assert crew._parse(_fake("no json here"), crew._Synth) is None


def test_agentic_flow_shares_state_and_uses_five_calls(env, monkeypatch):
    seen = []

    def fake(role, goal, backstory, description, expected, mon, usage, pyd=None):
        seen.append((role, description))
        usage.n += 1
        return _fake(SYNTH_RAW if pyd is crew._Synth else f"finding from {role}")

    monkeypatch.setattr(crew, "_llm_task", fake)
    report, st = _agentic()
    assert report.mode == "agentic"
    assert set(st.outputs) == {"weather", "mandi", "credit", "insurance"}
    assert len(seen) == 5
    mandi_desc = [d for r, d in seen if r == "Mandi Intelligence Analyst"][0]
    assert "finding from Weather Risk Analyst" in mandi_desc
    assert report.message.sms == "hi"
    assert report.metrics["llm_requests"] == 5


def test_one_failed_specialist_is_tolerated(env, monkeypatch):
    def fake(role, goal, backstory, description, expected, mon, usage, pyd=None):
        if role == "Credit Lifecycle Analyst":
            raise RuntimeError("boom")
        return _fake(SYNTH_RAW if pyd is crew._Synth else "ok")

    monkeypatch.setattr(crew, "_llm_task", fake)
    report, st = _agentic()
    assert report.mode == "agentic"
    assert "LLM unavailable" in st.outputs["credit"]


def test_two_failed_specialists_raise(env, monkeypatch):
    def fake(role, goal, backstory, description, expected, mon, usage, pyd=None):
        if role != "Orchestrator":
            raise RuntimeError("boom")
        return _fake(SYNTH_RAW)

    monkeypatch.setattr(crew, "_llm_task", fake)
    with pytest.raises(RuntimeError):
        _agentic()


def test_quota_exhausted_falls_back_to_rules(env, monkeypatch):
    def quota(*a, **k):
        raise llm_gate.QuotaExhausted("daily")

    monkeypatch.setattr(crew, "_llm_task", quota)
    r = crew.run_pipeline("F002")
    assert r.mode == "rule_based_fallback"
    events = [json.loads(x) for x in (env / f"{r.run_id}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["kind"] == "final"
