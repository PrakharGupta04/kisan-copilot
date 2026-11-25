from fastapi.testclient import TestClient

from kisan import api


def test_index_serves_new_dashboard():
    r = TestClient(api.app).get("/")
    assert r.status_code == 200
    assert "Agent trace" in r.text and "wa.me" in r.text
