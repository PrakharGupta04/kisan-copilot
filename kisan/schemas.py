"""All Pydantic models: tool results, agent plans, final structured output."""
from datetime import datetime, timezone
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


def _conf(v):
    try:
        v = float(v)
    except (TypeError, ValueError):
        return 0.5
    if v > 1:
        v = v / 100.0
    return max(0.0, min(1.0, v))


# ---------- tool-level models (validated before an agent ever sees them) ----------
class WeatherSummary(BaseModel):
    source: str
    total_rain_mm: float
    max_daily_rain_mm: float
    rain_days: int
    max_temp_c: float
    min_temp_c: float
    risk_level: Literal["low", "medium", "high"]
    notes: list[str] = []


class MandiSummary(BaseModel):
    source: str
    commodity: str
    current_modal_price: float
    msp: Optional[float] = None
    vs_msp_pct: Optional[float] = None
    trend_7d_pct: Optional[float] = None
    markets_reporting: int = 0
    signal: Literal["rising", "falling", "stable", "below_msp"]
    note: str = ""


class CreditMetrics(BaseModel):
    farmer_id: str
    kcc_limit: float
    outstanding: float
    headroom: float
    utilization_pct: float
    due_date: Optional[str] = None
    days_to_due: Optional[int] = None
    overdue: bool = False
    effective_rate_pct: float
    standard_rate_pct: float
    interest_saving_inr: float
    note: str = ""


class PmfbyAssessment(BaseModel):
    farmer_id: str
    crop: str
    season: str
    eligible: bool
    enrolled: bool
    premium_rate_pct: float
    enrollment_deadline: str
    deadline_days_left: int
    action: Literal["enroll_now", "keep_policy_and_report_losses", "enrollment_closed_check_bank_or_csc"]
    notes: list[str] = []


# ---------- agent-level models ----------
class AgentPlan(BaseModel):
    agents: list[Literal["weather", "mandi", "credit", "insurance"]]
    rationale: str = ""


class Recommendation(BaseModel):
    priority: int = 1
    title: str
    detail: str
    source_agents: list[str] = []
    confidence: float = 0.5

    @field_validator("confidence", mode="before")
    @classmethod
    def _c(cls, v):
        return _conf(v)

    @field_validator("priority", mode="before")
    @classmethod
    def _p(cls, v):
        try:
            return max(1, min(10, int(v)))
        except (TypeError, ValueError):
            return 5


class LLMReport(BaseModel):
    """What the orchestrator LLM is asked to produce (system fields are added in code)."""
    summary: str
    recommendations: list[Recommendation]
    risks: list[str] = []
    overall_confidence: float = 0.5

    @field_validator("overall_confidence", mode="before")
    @classmethod
    def _c(cls, v):
        return _conf(v)


class FarmerMessage(BaseModel):
    hindi: str
    english: str
    sms: str


class FinalReport(BaseModel):
    run_id: str
    farmer_id: str
    generated_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    mode: Literal["agentic", "rule_based_fallback", "offline"] = "agentic"
    summary: str
    recommendations: list[Recommendation]
    risks: list[str] = []
    overall_confidence: float = 0.5
    agents_run: list[str] = []
    message: Optional[FarmerMessage] = None
    evidence: list[dict] = []
    requires_human_review: bool = False
    review_reasons: list[str] = []
    status: Literal["READY", "PENDING_HUMAN_REVIEW"] = "READY"
    disclaimer: str = ""
    metrics: dict = {}


class RunState(BaseModel):
    """Shared state: every agent's intermediate output is stored here (requirement 1)."""
    run_id: str
    farmer_id: str
    profile: dict
    plan: list[str] = []
    outputs: dict[str, str] = {}
    evidence: list[dict] = []
    errors: list[str] = []

    def add_evidence(self, tool: str, tool_input: str, result: str) -> None:
        self.evidence.append({"tool": tool, "input": tool_input[:300], "result": result[:600]})