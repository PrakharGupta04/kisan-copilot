"""Numeric grounding check: every figure in the advice must appear in the tool evidence or the farmer profile."""
import re

_NUM = re.compile(r"\d[\d,]*\.?\d*")
_SMALL = {float(i) for i in range(0, 32)} | {24.0, 48.0, 72.0, 100.0, 365.0}


def numbers(text) -> set:
    out = set()
    for m in _NUM.findall(str(text or "")):
        try:
            out.add(round(float(m.replace(",", "").rstrip(".")), 2))
        except ValueError:
            pass
    return out


def ungrounded(report, evidence_text: str, profile_text: str) -> list:
    """Figures used in the advice that appear in no tool evidence (small numbers such as days are tolerated)."""
    allowed = numbers(evidence_text) | numbers(profile_text) | _SMALL
    parts = [getattr(report, "summary", "")]
    for r in getattr(report, "recommendations", None) or []:
        parts += [r.title, r.detail]
    msg = getattr(report, "message", None)
    if msg:
        parts += [msg.hindi, msg.english, msg.sms]
    bad = sorted(n for n in numbers(" ".join(str(p) for p in parts)) if n not in allowed)
    return [f"{n:.10g}" for n in bad]
