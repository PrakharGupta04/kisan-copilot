import json

from kisan import config, core_tools as ct, evaluate


def test_offline_eval_writes_reports(monkeypatch, tmp_path):
    def no_weather(*a, **k):
        raise ct.ToolError("off")

    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(ct, "weather_summary", no_weather)
    monkeypatch.setattr(ct, "_live_mandi", lambda *a, **k: None)
    evaluate.main(offline=True)
    d = json.loads((tmp_path / "eval_results.json").read_text(encoding="utf-8"))
    g = d["summary"]["guardrails"]
    assert d["summary"]["live"] is None
    assert d["summary"]["baseline"]["scenarios"] == 8
    assert g["injection_blocked"] == g["injection_total"] == 7
    assert g["toxic_blocked"] == g["toxic_total"] == 3
    assert g["legit_allowed"] == g["legit_total"] == 3
    assert "rule-based baseline" in (tmp_path / "eval_report.md").read_text(encoding="utf-8")
