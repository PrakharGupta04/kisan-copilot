import pytest

from kisan import config, llm_gate


@pytest.fixture(autouse=True)
def _tmp(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(llm_gate, "_last", -1e9)


def test_classify_daily_quota():
    e = Exception("429 RESOURCE_EXHAUSTED quotaId: GenerateRequestsPerDayPerProjectPerModel-FreeTier")
    assert llm_gate.classify(e)[0] == "daily"


def test_classify_rpm_uses_retry_delay():
    e = Exception("429 RESOURCE_EXHAUSTED GenerateRequestsPerMinutePerProjectPerModel-FreeTier 'retryDelay': '34s'")
    kind, delay = llm_gate.classify(e)
    assert kind == "rpm" and delay == 34.0


def test_classify_503():
    assert llm_gate.classify(Exception("503 UNAVAILABLE high demand"))[0] == "unavailable"


def test_classify_other():
    assert llm_gate.classify(ValueError("bad schema"))[0] == "other"


def test_record_call_counts():
    assert llm_gate.calls_today() == 0
    llm_gate.record_call()
    assert llm_gate.calls_today() == 1


def test_budget_blocks_when_exhausted(monkeypatch):
    monkeypatch.setattr(config, "GEMINI_RPD", 2)
    llm_gate.record_call()
    llm_gate.record_call()
    with pytest.raises(llm_gate.QuotaExhausted):
        llm_gate.before_call()


def test_pacing_sleeps_between_calls(monkeypatch):
    slept = []
    monkeypatch.setattr(llm_gate.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(config, "GEMINI_RPM", 12)
    llm_gate.before_call()
    llm_gate.before_call()
    assert len(slept) == 1 and slept[0] > 0
