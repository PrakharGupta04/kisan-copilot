import pytest

from kisan import core_tools as ct, db, rules, security
from kisan.schemas import RunState


@pytest.fixture
def offline_tools(monkeypatch):
    def no_weather(*a, **k):
        raise ct.ToolError("weather disabled in tests")
    monkeypatch.setattr(ct, "weather_summary", no_weather)
    monkeypatch.setattr(ct, "_live_mandi", lambda *a, **k: None)


def _run(fid):
    p = db.get_farmer(fid)
    st = RunState(run_id="t", farmer_id=fid, profile=p)
    return rules.build_report(p, st, "offline"), st


def test_overdue_farmer_gets_repayment_first(offline_tools):
    r, st = _run("F002")
    assert any(x.priority == 1 and "overdue" in x.title.lower() for x in r.recommendations)
    assert "Weather data unavailable." in r.risks
    assert st.errors
    assert r.mode == "offline"


def test_report_has_message_and_needs_review(offline_tools):
    r, _ = _run("F006")
    r = security.finalize_report(r)
    assert r.message
    assert r.message.sms
    assert r.requires_human_review
    assert r.status == "PENDING_HUMAN_REVIEW"


def test_every_farmer_produces_a_valid_report(offline_tools):
    for f in db.list_farmers():
        r, _ = _run(f["farmer_id"])
        assert r.recommendations
        assert r.farmer_id == f["farmer_id"]

