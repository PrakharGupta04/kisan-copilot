from fastapi.testclient import TestClient

from kisan import api, config


def test_latest_events_returns_newest_run_log_only(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "API_KEY", "")
    (tmp_path / "abcdef123456.jsonl").write_text('{"kind": "start"}\n{"kind": "plan"}\n', encoding="utf-8")
    (tmp_path / "a2a_client.jsonl").write_text('{"kind": "ok"}\n', encoding="utf-8")
    r = TestClient(api.app).get("/api/latest-events?since=0")
    assert r.status_code == 200
    assert [e["kind"] for e in r.json()] == ["start", "plan"]


def test_latest_events_empty_when_nothing_recent(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "API_KEY", "")
    (tmp_path / "abcdef123456.jsonl").write_text('{"kind": "start"}\n', encoding="utf-8")
    assert TestClient(api.app).get("/api/latest-events?since=99999999999").json() == []


def test_index_has_flow_and_live_feed():
    page = TestClient(api.app).get("/").text
    assert "Agent flow" in page and "Live agent activity" in page and "Attack test" in page
