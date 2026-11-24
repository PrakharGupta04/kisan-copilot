import json
import time

from kisan import config, core_tools as ct


def test_fresh_snapshot_skips_network(monkeypatch, tmp_path):
    monkeypatch.setitem(ct._SRC, "v", "agmarknet_live")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DATA_GOV_API_KEY", "x")
    (tmp_path / "mandi_snapshot.json").write_text(
        json.dumps({"Wheat|Punjab": {"ts": time.time(), "records": [[2700.0, "A"], [2650.0, "B"]]}}))

    def boom(*a, **k):
        raise AssertionError("network used")

    monkeypatch.setattr(ct.httpx, "get", boom)
    m = ct.mandi_summary("wheat", "Punjab")
    assert m.source == "agmarknet_cached"
    assert m.current_modal_price == 2675.0


def test_old_snapshot_used_when_server_fails(monkeypatch, tmp_path):
    monkeypatch.setitem(ct._SRC, "v", "agmarknet_live")
    monkeypatch.setattr(config, "DATA_DIR", tmp_path)
    monkeypatch.setattr(config, "DATA_GOV_API_KEY", "x")
    old = time.time() - 2 * 86400
    (tmp_path / "mandi_snapshot.json").write_text(
        json.dumps({"Wheat|Punjab": {"ts": old, "records": [[2800.0, "A"]]}}))

    def down(*a, **k):
        raise RuntimeError("server down")

    monkeypatch.setattr(ct.httpx, "get", down)
    m = ct.mandi_summary("wheat", "Punjab")
    assert m.source == "agmarknet_cached"
    assert m.current_modal_price == 2800.0
