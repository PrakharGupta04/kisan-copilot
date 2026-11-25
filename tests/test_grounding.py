import json
import time
import types

from kisan import config, crew, db
from kisan.grounding import numbers, ungrounded
from kisan.observability import Monitor
from kisan.schemas import FarmerMessage, FinalReport, Recommendation, RunState

EVID = '{"outstanding":148000.0,"interest_saving_inr":4055.0}'


def _report(sms):
    return FinalReport(run_id="t", farmer_id="F002", summary="Save Rs 4,055",
                       recommendations=[Recommendation(title="T", detail="Pay 148,000")],
                       message=FarmerMessage(hindi="h", english="e", sms=sms))


def test_numbers_normalises_commas_and_decimals():
    assert numbers("Rs 1,48,000 and 2512.0 and 6%") == {148000.0, 2512.0, 6.0}


def test_grounded_report_has_no_flags():
    assert ungrounded(_report("save 4,055"), EVID, "farmer_id: F002") == []


def test_wrong_figure_is_flagged():
    assert ungrounded(_report("save 4155"), EVID, "farmer_id: F002") == ["4155"]


BAD = ('{"summary": "Save 99999 rupees", "recommendations": [{"priority": 1, "title": "T", "detail": "d", '
       '"source_agents": ["credit"], "confidence": 0.9}], "risks": [], "overall_confidence": 0.9, '
       '"message": {"hindi": "h", "english": "e", "sms": "s"}}')


def test_pipeline_flags_ungrounded_figure_and_lowers_confidence(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(crew, "_collect_evidence",
                        lambda profile, selected, state, mon: {k: json.dumps({"k": k}) for k in selected if k != "insurance"})
    monkeypatch.setattr("kisan.a2a_client.call_insurance_agent", lambda fid: "pmfby ok")

    def fake(role, goal, backstory, description, expected, mon, usage, pyd=None):
        raw = BAD if pyd is crew._Synth else "finding"
        return types.SimpleNamespace(output=types.SimpleNamespace(raw=raw, pydantic=None))

    monkeypatch.setattr(crew, "_llm_task", fake)
    p = db.get_farmer("F002")
    st = RunState(run_id="t", farmer_id="F002", profile=p)
    r = crew._agentic(p, None, st, Monitor("t"), time.perf_counter())
    assert any("could not be verified" in x for x in r.risks)
    assert r.overall_confidence <= 0.45
