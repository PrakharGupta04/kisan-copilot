from fastapi.testclient import TestClient

from kisan import api, config, core_tools as ct


def test_demo_flag_forces_offline_mode(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "OFFLINE", False)
    monkeypatch.setattr(config, "API_KEY", "")
    monkeypatch.setattr(ct, "weather_summary", lambda *a, **k: (_ for _ in ()).throw(ct.ToolError("off")))
    monkeypatch.setattr(ct, "_live_mandi", lambda *a, **k: None)
    r = TestClient(api.app).post("/api/recommend", json={"farmer_id": "F002", "demo": True})
    assert r.status_code == 200
    assert r.json()["mode"] == "offline"
