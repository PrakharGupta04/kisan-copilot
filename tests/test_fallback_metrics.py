import json
import time
import types

import pytest

from kisan import config, core_tools as ct, crew
from kisan.observability import Monitor


def _fake_out(raw):
    return types.SimpleNamespace(output=types.SimpleNamespace(raw=raw, pydantic=None))


def test_fallback_keeps_partial_usage_and_ends_with_final(monkeypatch, tmp_path):
    def no_weather(*a, **k):
        raise ct.ToolError("off")

    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "OFFLINE", False)
    monkeypatch.setattr(ct, "weather_summary", no_weather)
    monkeypatch.setattr(ct, "_live_mandi", lambda *a, **k: None)
    monkeypatch.setattr(crew, "_collect_evidence",
                        lambda profile, selected, state, mon: {k: "{}" for k in selected if k != "insurance"})
    monkeypatch.setattr("kisan.a2a_client.call_insurance_agent", lambda fid: "pmfby ok")

    def fake(role, goal, backstory, description, expected, mon, usage, pyd=None):
        if pyd is crew._Synth:
            raise RuntimeError("503 synthesis unavailable")
        usage.n += 1
        usage.p += 100
        usage.c += 20
        return _fake_out("finding")

    monkeypatch.setattr(crew, "_llm_task", fake)
    r = crew.run_pipeline("F002")
    assert r.mode == "rule_based_fallback"
    assert r.metrics["llm_requests"] == 4
    assert r.metrics["prompt_tokens"] == 400
    assert r.metrics["partial_usage_before_fallback"] is True
    events = [json.loads(x) for x in (tmp_path / f"{r.run_id}.jsonl").read_text(encoding="utf-8").splitlines()]
    assert events[-1]["kind"] == "final"


def test_deadline_stops_llm_retries(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    mon = Monitor("t")
    mon.deadline = time.perf_counter() - 1
    with pytest.raises(TimeoutError):
        crew._llm_task("r", "g", "b", "d", "e", mon, crew._Usage())
