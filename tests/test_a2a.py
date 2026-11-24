from kisan import a2a_client, config


def test_extract_text_from_artifacts():
    r = {"artifacts": [{"parts": [{"kind": "text", "text": "hello"}]}]}
    assert a2a_client.extract_text(r) == "hello"


def test_extract_text_from_status_message():
    r = {"status": {"message": {"parts": [{"text": "from status"}]}}}
    assert a2a_client.extract_text(r) == "from status"


def test_extract_text_from_history():
    r = {"history": [{"role": "user", "parts": [{"text": "q"}]}, {"role": "agent", "parts": [{"text": "a"}]}]}
    assert a2a_client.extract_text(r) == "a"


def test_unreachable_agent_returns_error_string(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "A2A_URL", "http://127.0.0.1:9")
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    out = a2a_client.call_insurance_agent("F001")
    assert out.startswith("ERROR")
    assert (tmp_path / "a2a_client.jsonl").exists()


def test_invalid_farmer_id_returns_error_string(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    assert a2a_client.call_insurance_agent("bad id").startswith("ERROR")


def test_uses_configured_timeout(monkeypatch, tmp_path):
    captured = {}

    class Boom:
        def __init__(self, *a, **k):
            captured["timeout"] = k.get("timeout")
            raise RuntimeError("stop")

    monkeypatch.setattr(config, "LOG_DIR", tmp_path)
    monkeypatch.setattr(config, "A2A_TIMEOUT", 7)
    monkeypatch.setattr(a2a_client.httpx, "Client", Boom)
    assert a2a_client.call_insurance_agent("F001").startswith("ERROR")
    assert captured["timeout"] == 7.0
