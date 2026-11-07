"""Orchestration: plan -> specialist crew (MCP + A2A tools) -> synthesis -> communication -> guardrails."""
import json
import os
import re
import sys
import time
import uuid

from crewai import LLM, Agent, Crew, Process, Task
from crewai.mcp import MCPServerStdio

from . import config, db, rules, security
from .a2a_client import ask_insurance_agent
from .observability import Monitor, init_langfuse, trace_run
from .schemas import AgentPlan, FarmerMessage, FinalReport, LLMReport, RunState

init_langfuse("kisan-crewai", ["crewai", "litellm"])
ORDER = ["weather", "mandi", "credit", "insurance"]


def _profile_text(p: dict) -> str:
    """PII minimisation: name and any contact data are NEVER sent to the LLM."""
    keys = ("farmer_id", "state", "district", "lat", "lon", "crop", "season", "area_acres", "sowing_date",
            "harvest_date", "kcc_limit", "outstanding", "due_date", "pmfby_enrolled", "has_crop_loan", "language")
    return "\n".join(f"{k}: {p.get(k)}" for k in keys)


def _mcp(toolset: str) -> MCPServerStdio:
    env = {k: os.environ[k] for k in ("PATH", "HOME", "DATA_GOV_API_KEY", "KISAN_DB") if k in os.environ}
    env.update({"TOOLSET": toolset, "PYTHONPATH": str(config.ROOT), "PYTHONUNBUFFERED": "1"})  # no LLM keys leak
    return MCPServerStdio(command=sys.executable, args=["-m", "kisan.mcp_server"], env=env)


def _agent(role, goal, backstory, llm, tools=None, mcps=None) -> Agent:
    kw = dict(role=role, goal=goal, backstory=backstory, llm=llm, allow_delegation=False, verbose=False, max_iter=4)
    if tools:
        kw["tools"] = tools
    if mcps:
        kw["mcps"] = mcps
    return Agent(**kw)


def _parse(task: Task, model):
    out = getattr(task, "output", None)
    if out is None:
        return None
    p = getattr(out, "pydantic", None)
    if isinstance(p, model):
        return p
    m = re.search(r"\{.*\}", getattr(out, "raw", "") or "", re.S)
    if m:
        try:
            return model.model_validate_json(m.group(0))
        except Exception:
            return None
    return None


def _enforce_plan(agents, p) -> list:
    """Policy overrides: the LLM plan can add agents but cannot drop mandatory ones."""
    s = {a for a in (agents or []) if a in ORDER} | {"weather", "insurance"}
    if (p.get("outstanding") or 0) > 0 or p.get("has_crop_loan"):
        s.add("credit")
    h = db.days_until(p.get("harvest_date"))
    if h is not None and h <= 60:
        s.add("mandi")
    return [a for a in ORDER if a in s]


def _kickoff(crew: Crew, mon: Monitor, attempts: int = 3):
    for i in range(attempts):
        try:
            return crew.kickoff()
        except Exception as e:
            mon.error("crew_kickoff", e)
            transient = any(k in str(e).lower() for k in ("rate", "429", "timeout", "overload", "temporar", "connection"))
            if transient and i < attempts - 1:
                time.sleep(20 * (i + 1))
                continue
            raise


def _tokens(out) -> tuple:
    u = getattr(out, "token_usage", None)
    return (int(getattr(u, "prompt_tokens", 0) or 0), int(getattr(u, "completion_tokens", 0) or 0),
            int(getattr(u, "successful_requests", 0) or 0))


def _agentic(profile: dict, question: str, state: RunState, mon: Monitor) -> FinalReport:
    llm = LLM(model=config.CREW_MODEL, temperature=0.1, max_tokens=3000, reasoning_effort="low")
    ptxt = _profile_text(profile)
    usage = [0, 0, 0]

    def acc(out):
        a, b, c = _tokens(out)
        usage[0] += a; usage[1] += b; usage[2] += c

    orch = _agent("Orchestrator", "Plan which specialists are needed, then merge their findings into prioritized advice",
                  "Senior agricultural advisor. Only uses facts found in specialist reports; never invents numbers.", llm)

    # ---- 1. PLANNING / ROUTING ----
    plan_task = Task(
        description=("Farmer profile:\n" + ptxt + (f"\nFarmer question: {question}" if question else "") +
                     "\nChoose which specialist agents are relevant from: weather, mandi, credit, insurance. "
                     "Return the list in 'agents' and a one-sentence 'rationale'."),
        expected_output="AgentPlan JSON", agent=orch, output_pydantic=AgentPlan)
    plan = None
    try:
        out = _kickoff(Crew(agents=[orch], tasks=[plan_task], verbose=False, step_callback=mon.step_cb), mon)
        acc(out)
        plan = _parse(plan_task, AgentPlan)
    except Exception as e:
        mon.error("planning", e)
    selected = _enforce_plan(plan.agents if plan else [], profile)
    state.plan = selected
    mon.add("plan", "orchestrator", selected=selected, rationale=(plan.rationale if plan else "fallback: rules"))

    # ---- 2. SPECIALISTS with shared context ----
    def keep(key):
        def cb(output):
            state.outputs[key] = str(getattr(output, "raw", ""))[:1200]  # shared state update
            mon.task_cb(output)
        return cb

    lat, lon, crop, st, fid = profile["lat"], profile["lon"], profile["crop"], profile["state"], profile["farmer_id"]
    defs = {
        "weather": (_agent("Weather Risk Analyst", "Assess 7-day weather risk for the crop", "Agrometeorologist who trusts only tool data.",
                           llm, mcps=[_mcp("weather")]),
                    f"Call get_weather_forecast with latitude={lat} and longitude={lon}. In at most 70 words give weather "
                    f"risks for {crop} over the next 7 days and concrete field actions. Use only tool data."),
        "mandi": (_agent("Mandi Intelligence Analyst", "Advise sell/hold using price data", "Market analyst for Indian mandis.",
                         llm, mcps=[_mcp("mandi")]),
                  f"Call get_mandi_prices with crop='{crop}' and state='{st}'. Using the weather findings from context "
                  "(rain affects harvest, transport, storage), advise sell_now, hold or sell_partial in at most 70 words. "
                  "Quote the price numbers returned and say if data is synthetic."),
        "credit": (_agent("Credit Lifecycle Analyst", "Assess KCC repayment status", "Rural banking officer. Never advises borrowing beyond limits.",
                          llm, mcps=[_mcp("credit")]),
                   f"Call compute_kcc_metrics with farmer_id='{fid}'. Using the mandi outlook from context, in at most "
                   "70 words state utilization, days to due date, interest benefit and a repayment recommendation."),
        "insurance": (_agent("Insurance Liaison", "Get PMFBY status from the remote insurance agent via A2A", "Crop-insurance coordinator.",
                             llm, tools=[ask_insurance_agent]),
                      f"Call ask_insurance_agent with farmer_id='{fid}'. Using the weather findings from context, in at most "
                      "70 words explain eligibility, enrollment, deadline and the recommended action. If the tool returns "
                      "an ERROR, say insurance data is unavailable."),
    }
    tasks, agents, spec_tasks = [], [orch], []
    for key in selected:
        ag, desc = defs[key]
        t = Task(description=f"Farmer profile:\n{ptxt}\n\n{desc}", expected_output="Plain-text findings, max 70 words",
                 agent=ag, context=list(spec_tasks), callback=keep(key))
        agents.append(ag); tasks.append(t); spec_tasks.append(t)

    # ---- 3. SYNTHESIS ----
    synth = Task(
        description=("Using ALL specialist findings in context, write the final advice for the farmer. Priority 1 = most urgent; "
                     "at most 4 recommendations; each lists source_agents and a confidence between 0 and 1. Do NOT invent numbers "
                     "that are not in the findings. List real risks (including unavailable data) in 'risks'."
                     + (f" Farmer asked: {question}" if question else "")),
        expected_output="LLMReport JSON", agent=orch, context=list(spec_tasks), output_pydantic=LLMReport)

    # ---- 4. COMMUNICATION ----
    comm_agent = _agent("Farmer Communication Agent", "Explain advice in simple farmer-friendly language",
                        "Rural extension worker fluent in Hindi and simple English.", llm)
    comm = Task(description="Rewrite the top recommendations for the farmer in very simple words. hindi: Devanagari, max 80 words. "
                            "english: max 60 words. sms: English, max 160 characters. Keep all numbers exactly as in the report.",
                expected_output="FarmerMessage JSON", agent=comm_agent, context=[synth], output_pydantic=FarmerMessage)
    agents.append(comm_agent)

    crew = Crew(agents=agents, tasks=tasks + [synth, comm], process=Process.sequential, verbose=False,
                step_callback=mon.step_cb, task_callback=None, max_rpm=config.MAX_RPM)
    out = _kickoff(crew, mon)
    acc(out)

    llm_report = _parse(synth, LLMReport)
    if llm_report is None:
        raise RuntimeError("synthesis produced no valid structured output")
    message = _parse(comm, FarmerMessage)
    mon.counts["llm_requests"] = usage[2]
    cost = usage[0] / 1e6 * config.PRICE_IN_PER_M + usage[1] / 1e6 * config.PRICE_OUT_PER_M
    return FinalReport(
        run_id=state.run_id, farmer_id=fid, mode="agentic", summary=llm_report.summary,
        recommendations=llm_report.recommendations, risks=llm_report.risks,
        overall_confidence=llm_report.overall_confidence, agents_run=selected, message=message,
        evidence=state.evidence[:12],
        metrics={"prompt_tokens": usage[0], "completion_tokens": usage[1], "llm_requests": usage[2],
                 "est_cost_usd_if_paid": round(cost, 5), "actual_cost_inr": 0.0})


def run_pipeline(farmer_id: str, question=None) -> FinalReport:
    run_id = uuid.uuid4().hex[:12]
    fid = security.validate_farmer_id(farmer_id)  # guardrail 1
    q = security.screen_user_text(question)       # guardrail 2
    profile = db.get_farmer(fid)
    if not profile:
        raise LookupError(f"farmer {fid} not found")
    mon = Monitor(run_id)
    state = RunState(run_id=run_id, farmer_id=fid, profile=profile)
    mon.on_tool = state.add_evidence
    t0 = time.perf_counter()
    mon.add("start", "pipeline", farmer_id=fid, offline=config.OFFLINE, has_question=bool(q))
    with trace_run("kisan-copilot-run", farmer_id=fid, run_id=run_id):
        report = None
        if not config.OFFLINE:
            try:
                report = _agentic(profile, q, state, mon)
            except Exception as e:
                mon.error("agentic_pipeline", e)
                state.errors.append(f"agentic failed: {type(e).__name__}")
        if report is None:
            report = rules.build_report(profile, state, "offline" if config.OFFLINE else "rule_based_fallback")
    report.metrics.update(latency_s=round(time.perf_counter() - t0, 2), errors=state.errors,
                          tool_calls=mon.counts["tool_calls"], log_file=str(mon.path.name))
    report = security.finalize_report(report)     # guardrail 3 + HITL
    db.save_run(run_id, fid, report.status, report.model_dump_json())
    mon.add("final", "pipeline", status=report.status, mode=report.mode, latency_s=report.metrics["latency_s"])
    return report