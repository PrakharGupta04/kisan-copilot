from kisan.schemas import LLMReport, Recommendation


def test_confidence_percent_is_normalised():
    assert Recommendation(title="t", detail="d", confidence=85).confidence == 0.85


def test_confidence_garbage_defaults():
    assert Recommendation(title="t", detail="d", confidence="high").confidence == 0.5


def test_priority_clamped():
    assert Recommendation(title="t", detail="d", priority=99).priority == 10
    assert Recommendation(title="t", detail="d", priority="x").priority == 5
    assert Recommendation(title="t", detail="d", priority=0).priority == 1


def test_llm_report_confidence_string():
    r = LLMReport(summary="s", recommendations=[], overall_confidence="90")
    assert r.overall_confidence == 0.9

