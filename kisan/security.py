"""Guardrails: input screening, ID validation, PII redaction, output policy, rate limiting."""
import re
import threading
import time
import unicodedata
from collections import defaultdict, deque

from .schemas import FinalReport

MAX_Q = 300
FARMER_ID_RE = re.compile(r"^F\d{3}$")
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")

_INJ = [re.compile(p) for p in [
    r"ignore (all |any |the )?(previous|prior|above|earlier) (instructions|prompts|rules)",
    r"disregard (all |any |the )?(previous|prior|above|earlier|your)",
    r"(reveal|show|print|repeat) (your |the )?(system|hidden|initial) (prompt|instructions)",
    r"you are now ", r"act as (a |an )?(dan|developer|unrestricted)", r"developer mode", r"jailbreak",
    r"<\s*/?\s*(system|assistant)\s*>", r"\bapi[_ -]?key\b", r"override (the )?(guardrail|safety|policy)",
    r"(send|email|post) .{0,40}(password|secret|token)",
]]
# Starter list only. Extend with a library such as `better-profanity` plus Hindi terms.
_TOXIC = ["idiot", "stupid", "moron", "hate you", "kill you", "scam you"]

DISCLAIMER = ("AI-generated decision support using synthetic profiles and indicative rules. Not financial, legal or "
              "insurance advice. Confirm loan, KCC and insurance actions with your bank/agriculture officer.")
_SENSITIVE = re.compile(r"loan|kcc|credit|repay|interest|limit|insurance|premium|enrol|pmfby", re.I)
_PHONE = re.compile(r"(?<!\d)[6-9]\d{9}(?!\d)")
_AADHAAR = re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)")


class GuardrailViolation(ValueError):
    pass


def validate_farmer_id(fid: str) -> str:
    fid = (fid or "").strip().upper()
    if not FARMER_ID_RE.match(fid):
        raise GuardrailViolation("invalid farmer_id format (expected like F001)")
    return fid


def scan_untrusted(text: str) -> list:
    """Return injection patterns found in tool/agent output (indirect prompt injection)."""
    low = unicodedata.normalize("NFKC", text or "").lower()
    return [p.pattern for p in _INJ if p.search(low)]


def screen_user_text(text) -> str:
    if not text:
        return ""
    t = _CTRL.sub(" ", str(text)).strip()
    if len(t) > MAX_Q:
        raise GuardrailViolation(f"question too long (max {MAX_Q} chars)")
    if scan_untrusted(t):
        raise GuardrailViolation("possible prompt-injection detected")
    low = unicodedata.normalize("NFKC", t).lower()
    for w in _TOXIC:
        if re.search(rf"\b{re.escape(w)}\b", low):
            raise GuardrailViolation("abusive language is not allowed")
    return t


def redact_pii(s: str) -> str:
    return _AADHAAR.sub("[REDACTED]", _PHONE.sub("[REDACTED]", s or ""))


def finalize_report(r: FinalReport) -> FinalReport:
    """Output guardrail + human-in-the-loop policy."""
    r.summary = redact_pii(r.summary)
    r.risks = [redact_pii(x) for x in r.risks][:6]
    for rec in r.recommendations:
        rec.title, rec.detail = redact_pii(rec.title), redact_pii(rec.detail)
    r.recommendations = sorted(r.recommendations, key=lambda x: x.priority)[:5]
    if r.message:
        r.message.hindi, r.message.english, r.message.sms = (
            redact_pii(r.message.hindi), redact_pii(r.message.english), redact_pii(r.message.sms)[:160])
    reasons = []
    if any(_SENSITIVE.search(f"{x.title} {x.detail}") for x in r.recommendations):
        reasons.append("Contains financial/insurance guidance: human confirmation required.")
    if r.overall_confidence < 0.5:
        reasons.append("Low overall confidence.")
    if r.mode != "agentic":
        reasons.append(f"Generated in degraded mode ({r.mode}).")
    if not r.recommendations:
        reasons.append("No recommendations produced.")
    r.review_reasons = reasons
    r.requires_human_review = bool(reasons)
    r.status = "PENDING_HUMAN_REVIEW" if reasons else "READY"
    r.disclaimer = DISCLAIMER
    return r


class RateLimiter:
    def __init__(self, limit: int = 12, window: int = 60):
        self.limit, self.window = limit, window
        self.hits = defaultdict(deque)
        self.lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.time()
        with self.lock:
            q = self.hits[key]
            while q and now - q[0] > self.window:
                q.popleft()
            if len(q) >= self.limit:
                return False
            q.append(now)
            return True