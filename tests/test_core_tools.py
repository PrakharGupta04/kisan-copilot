import pytest

from kisan import core_tools as ct


class _Resp:
    def __init__(self, payload):
        self._p = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._p


def _fake_weather(rain, tmax=30.0, tmin=18.0):
    n = len(rain)
    return {"daily": {"precipitation_sum": rain,
                      "temperature_2m_max": [tmax] * n,
                      "temperature_2m_min": [tmin] * n}}


def test_weather_heavy_rain_is_high(monkeypatch):
    monkeypatch.setattr(ct.httpx, "get", lambda *a, **k: _Resp(_fake_weather([60, 0, 0, 0, 0, 0, 0])))
    w = ct.weather_summary(26.85, 80.95)
    assert w.risk_level == "high"
    assert w.total_rain_mm == 60.0
    assert w.rain_days == 1


def test_weather_calm_is_low(monkeypatch):
    monkeypatch.setattr(ct.httpx, "get", lambda *a, **k: _Resp(_fake_weather([0] * 7)))
    assert ct.weather_summary(10.1, 79.1).risk_level == "low"


def test_weather_failure_becomes_tool_error(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(ct.httpx, "get", boom)
    with pytest.raises(ct.ToolError):
        ct.weather_summary(20.0, 70.0)


def test_mandi_synthetic_fallback(monkeypatch):
    monkeypatch.setattr(ct, "_live_mandi", lambda *a, **k: None)
    m = ct.mandi_summary("Wheat", "Punjab")
    assert m.source == "synthetic_fallback"
    assert m.commodity == "Wheat"
    assert m.msp == 2585.0
    assert m.signal in ("rising", "falling", "stable", "below_msp")


def test_mandi_live_path_has_no_trend(monkeypatch):
    monkeypatch.setattr(ct, "_live_mandi", lambda *a, **k: [(2700.0, "A"), (2650.0, "B"), (2750.0, "C")])
    m = ct.mandi_summary("paddy", "Uttar Pradesh")
    assert m.source == "agmarknet_live"
    assert m.trend_7d_pct is None
    assert m.markets_reporting == 3
    assert m.current_modal_price == 2700.0


def test_mandi_unsupported_crop():
    with pytest.raises(ct.ToolError):
        ct.mandi_summary("banana", "Kerala")


def test_kcc_overdue_farmer():
    c = ct.kcc_metrics("F002")
    assert c.overdue is True
    assert c.effective_rate_pct == 9.0
    assert c.utilization_pct == 98.7
    assert c.days_to_due < 0
    assert c.headroom == 2000.0


def test_kcc_no_outstanding():
    c = ct.kcc_metrics("F006")
    assert c.outstanding == 0
    assert c.utilization_pct == 0.0
    assert c.days_to_due is None
    assert c.overdue is False
    assert c.interest_saving_inr == 0


def test_kcc_on_time_interest_saving():
    c = ct.kcc_metrics("F001")
    assert c.overdue is False
    assert c.effective_rate_pct == 4.0
    assert c.interest_saving_inr == 497.0


def test_pmfby_enrolled_farmer():
    a = ct.pmfby_assessment("F003")
    assert a.enrolled
    assert a.action == "keep_policy_and_report_losses"
    assert a.premium_rate_pct == 1.5


def test_pmfby_cotton_commercial_rate():
    assert ct.pmfby_assessment("F004").premium_rate_pct == 5.0


def test_pmfby_action_consistent_with_deadline():
    a = ct.pmfby_assessment("F001")
    assert not a.enrolled
    expected = "enroll_now" if a.deadline_days_left >= 0 else "enrollment_closed_check_bank_or_csc"
    assert a.action == expected


def test_unknown_farmer_raises_tool_error():
    with pytest.raises(ct.ToolError):
        ct.kcc_metrics("F999")

