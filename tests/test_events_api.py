from fastapi.testclient import TestClient

from kisan import api, config


def test_events_endpoint_returns_log_lines(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "API_KEY", "")
    (tmp_path / "abc123.jsonl").write_text('{"kind": "start"}\n{"kind": "final"}\n', encoding="utf-8")
    c = TestClient(api.app)
    r = c.get("/api/runs/abc123/events")
    assert r.status_code == 200
    assert [e["kind"] for e in r.json()] == ["start", "final"]
    assert c.get("/api/runs/zzzz/events").status_code == 404
