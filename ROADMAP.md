# ROADMAP: Kisan Copilot — Production-Ready Completion Plan

**Document Version:** 1.0.0  
**Date:** 2026-11-01  
**Project:** Kisan Copilot (Autonomous Multi-Agent AI for Agricultural Support & KCC Finance)  
**Location:** `/home/prakhar/kisan-copilot` (WSL2 Ubuntu-22.04, Intel i3, 0 INR Budget)  
**Authors:** Prakhar Gupta (Lead Architect / Backend / Eval) & Rishabh Kumar Singh (Agent / Tool / UI / Test)  

---

## 0. Hardware and Cost Constraints

> **Every task in this roadmap MUST respect these constraints. Any task that violates them is blocked until redesigned.**

### 0.1 Development Machine

| Resource | Value |
|---|---|
| **CPU** | Intel Core i3 (10th gen) — 2 cores / 4 threads, no turbo above ~3.4 GHz |
| **GPU** | None (integrated UHD 620 only — no CUDA, no ML inference) |
| **RAM** | ~12 GB total; WSL2 capped at **6 GB** (see T0-HW.1) |
| **Disk** | Limited; WSL2 ext4 image lives on a **slow D: drive** (HDD-class latency) |
| **OS** | Windows 10/11 + WSL2 Ubuntu 22.04 |

### 0.2 Cost Target

**At least 99 % free of cost: no paid service, no credit card required.**

| Allowed (Free) | Status |
|---|---|
| Google AI Studio / Gemini API free tier | ✅ Active |
| Hugging Face Spaces — CPU basic (free) | ✅ Available |
| Langfuse Cloud — hobby tier (free) | ✅ Available |
| Open-Meteo weather API (free, no key) | ✅ Active |
| data.gov.in API key (free registration) | ✅ Available |
| GitHub free (public or private repos) | ✅ Active |
| pandoc (already installed in WSL) | ✅ Installed |
| Windows Game Bar screen recorder (Win+Alt+R) | ✅ Built-in |
| Google Slides / Google Docs (free) | ✅ Available |

### 0.3 FORBIDDEN on This Laptop

The following are **unconditionally forbidden** on the development machine due to RAM, disk, CPU or cost constraints:

| Forbidden Item | Reason |
|---|---|
| Local LLMs (Ollama, llama.cpp, vLLM, etc.) | No GPU, insufficient RAM |
| Local Docker builds (`docker build`) | OOM risk on 6 GB WSL; slow D: disk; test `start.sh` locally instead, let HF build the image in the cloud |
| PostgreSQL / MySQL / any DB server | RAM overhead; SQLite is sufficient |
| Redis / Memcached | RAM overhead; in-memory TTL dict is sufficient |
| Vector databases (Chroma, pgvector, Qdrant, Weaviate, FAISS) | Disk + RAM + model-weight downloads |
| ML moderation models (Llama Guard, Perspective API local, etc.) | No GPU; use regex/rule-based screening |
| Node.js / npm / Vite / Webpack builds | RAM + disk; use no-build UMD frontend |
| TeX / LaTeX (`texlive`, `pdflatex`) | ~2–4 GB disk; use pandoc + Word/Google Docs for PDF |
| OBS Studio | CPU-intensive; use Windows Game Bar |
| Any pip package that downloads model weights (sentence-transformers, spaCy lg/trf, etc.) | Disk + RAM |
| Any task requiring > 3 GB of extra disk | Disk is limited on D: |

### 0.4 Mandatory Per-Task Impact Statement

Every task (T-id) in this roadmap MUST declare:

| Field | Description |
|---|---|
| **Expected runtime** | Wall-clock time on this i3 laptop (e.g., "~5 min", "< 30 s") |
| **RAM impact** | Peak additional RSS (e.g., "+80 MB", "negligible") |
| **Disk impact** | Bytes written permanently (e.g., "+12 MB for venv packages", "~0") |

### 0.5 Mandatory Operational Rules

1. **WSL memory cap** (Task T0-HW.1): create/update `%USERPROFILE%\.wslconfig` with:
   ```ini
   [wsl2]
   memory=6GB
   swap=2GB
   ```
   Then `wsl --shutdown` and restart. This prevents WSL from eating all 12 GB and freezing Windows.

2. **Pip discipline**: every `pip install` command MUST be:
   ```bash
   pip install --no-cache-dir <packages> && pip cache purge && df -h /
   ```
   This prevents the pip cache from consuming disk on the slow D: drive.

3. **Uvicorn without `--reload`**: the `--reload` flag spawns a file-watcher that consumes CPU and RAM continuously. Always run `uvicorn ... --host 0.0.0.0 --port 7860` without `--reload` on this machine.

4. **Close heavy processes during live runs**: before executing a live agentic run, close Antigravity / VS Code / Chrome heavy tabs to free RAM for the CrewAI + ADK processes.

5. **Generous, configurable timeouts**: the default per-run timeout is **300 seconds** (5 minutes) because the i3 is slow. All timeouts MUST be configurable via environment variables:
   ```
   RUN_TIMEOUT=300        # seconds, per full pipeline run
   MCP_TOOL_TIMEOUT=60    # seconds, per MCP tool call
   A2A_TIMEOUT=30         # seconds, per A2A round-trip
   ADK_POLL_TIMEOUT=45    # seconds, ADK readiness polling
   ```

6. **Prefer pure-Python, small, boring solutions**: no compiled extensions, no Rust/C build steps, no large frameworks when a 50-line Python file will do.

### 0.6 Hardware Setup Tasks

| Task ID | Description | Files to Touch | Owner | Est | Runtime | RAM Impact | Disk Impact | Acceptance Test |
|---|---|---|---|---|---|---|---|---|
| **T0-HW.1** | Create `%USERPROFILE%\.wslconfig` with `memory=6GB, swap=2GB`; run `wsl --shutdown`; verify with `free -h` inside WSL. | `~/.wslconfig` (Windows side) | Prakhar | 0.25 h | < 2 min | Frees ~6 GB for Windows | ~0 | `free -h` shows ~6 GB total inside WSL |
| **T0-HW.2** | Add shell alias / wrapper: `pip-install() { pip install --no-cache-dir "$@" && pip cache purge && df -h /; }` to `~/.bashrc` in WSL. | `~/.bashrc` | Prakhar | 0.1 h | < 1 min | ~0 | ~0 | `type pip-install` shows the function |
| **T0-HW.3** | Verify `uvicorn` launch commands in `start.sh` and all docs do NOT use `--reload`. | `start.sh`, `ROADMAP.md` | Prakhar | 0.1 h | < 1 min | ~0 | ~0 | `grep -r -- '--reload' .` returns nothing (except test/doc references noting it is forbidden) |

---

## 1. Executive Summary

Kisan Copilot contains high-quality implementations of core domain logic, guardrails, MCP tools, and A2A integration, but **zero fully agentic runs have ever completed end-to-end**. The single biggest blocker is that live runs trigger **13 base LLM calls per scenario** (counted from code: 1 planning + 8 specialist tool turns + 2 ADK + 1 synthesis + 1 communication), which escalate to 20+ calls because `_kickoff(attempts=3)` retries the entire multi-task crew from scratch upon any downstream failure, instantly exhausting Gemini free-tier quotas (15 RPM / 1M TPM / 1,500 RPD). 

This roadmap transitions the system to a resilient, quota-bounded state machine that cuts live LLM calls to **≤ 7 calls per run** in `TOOL_MODE=prefetch` (or ~11 in `TOOL_MODE=agentic` — see Section 3.2 for exact arithmetic), unifies CrewAI and Google ADK into a robust dual-venv container on Hugging Face Spaces (built in the cloud — no local Docker builds), activates Langfuse v3 tracing, builds a **no-build** React dashboard (UMD + htm + Tailwind play CDN, no Node/npm) served via FastAPI `StaticFiles`, and executes a live 8-scenario evaluation from the laptop CLI with 0 INR expenditure.

---

## 2. Verified Current State

### 2.1 File Map and Responsibilities

| File | Purpose | Public Classes / Functions | Upstream Imports | Downstream Dependents | Status / Quirks |
|---|---|---|---|---|---|
| `kisan/config.py` | Central configuration & paths | `ROOT`, `DATA_DIR`, `LOG_DIR`, `DB_PATH`, `CREW_MODEL`, `ADK_MODEL`, `MAX_RPM`, `PRICE_IN_PER_M`, `PRICE_OUT_PER_M` | `dotenv`, `os`, `pathlib` | All modules | Pricing defaults ($0.59/$0.79) are Groq legacy values; must be environment-configurable (`PRICE_IN_PER_M`, `PRICE_OUT_PER_M`). Claimed Gemini rates ($1.50/$9.00) are ⚠️ UNVERIFIED. |
| `kisan/schemas.py` | Pydantic data models | `WeatherSummary`, `MandiSummary`, `CreditMetrics`, `PmfbyAssessment`, `AgentPlan`, `Recommendation`, `LLMReport`, `FarmerMessage`, `FinalReport`, `RunState` | `pydantic`, `datetime` | All modules | Fully compliant with Pydantic v2. Clean field validators. |
| `kisan/security.py` | Input screening, PII redaction, HITL policy, rate limiting | `validate_farmer_id`, `scan_untrusted`, `screen_user_text`, `redact_pii`, `finalize_report`, `RateLimiter` | `re`, `unicodedata`, `threading` | `crew.py`, `api.py`, `insurance_adk/agent.py` | English regex rules only; 6 toxic terms; needs Hindi transliterated patterns. |
| `kisan/core_tools.py` | Pure deterministic domain tools | `weather_summary`, `mandi_summary`, `kcc_metrics`, `pmfby_assessment`, `_cached` | `httpx`, `random`, `statistics`, `db.py` | `mcp_server.py`, `rules.py`, `insurance_adk/agent.py` | Mandi live retrieval returns `None` when API key missing or endpoint times out; synthetic fallback is reliable. |
| `kisan/mcp_server.py` | FastMCP stdio server exposing tools | `get_weather_forecast`, `get_mandi_prices`, `compute_kcc_metrics` | `mcp.server.fastmcp`, `core_tools.py` | Spawned as subprocess by `crew.py` | FastMCP server clean; logs must never emit to stdout to protect JSON-RPC channel. |
| `kisan/db.py` | SQLite data layer & seeding | `_rw`, `_ro`, `get_farmer`, `list_farmers`, `save_run`, `get_run`, `save_review`, `seed` | `sqlite3`, `contextlib` | `api.py`, `crew.py`, `core_tools.py` | `seed()` intentionally refreshes dates relative to today; does not delete runs or reviews. Uses default journal mode (not WAL). |
| `kisan/rules.py` | Rule-based decision engine | `build_report` | `core_tools.py`, `db.py`, `schemas.py` | `crew.py`, fallback path | Fast, deterministic, reliable (< 1.2s). Serves as offline mock and graceful fallback. |
| `kisan/observability.py` | Monitoring, JSONL logging, Langfuse tracing | `append_jsonl`, `init_langfuse`, `trace_run`, `Monitor` | `langfuse`, `openinference`, `json`, `threading` | `crew.py`, `insurance_adk/agent.py` | Gracefully degrades when Langfuse keys are absent. Uses Langfuse v3 API. |
| `kisan/a2a_client.py` | A2A JSON-RPC client tool for CrewAI | `extract_text`, `call_insurance_agent`, `ask_insurance_agent` | `httpx`, `crewai.tools`, `security.py` | `crew.py` | Implements A2A `message/send` protocol. Successfully verified in isolation. Lazy import of crewai tools. |
| `kisan/insurance_adk/agent.py` | Remote PMFBY agent (Google ADK) | `assess_pmfby`, `guard_before_model`, `validate_after_tool`, `root_agent`, `a2a_app` | `google.adk`, `google.genai`, `core_tools.py` | Run via `uvicorn` on port 8001 | ADK agent serves A2A Starlette app; includes pre-model guardrails. |
| `kisan/crew.py` | Orchestration pipeline | `run_pipeline`, `_agentic`, `_kickoff`, `_mcp`, `_agent`, `_parse` | `crewai`, `litellm`, all kisan modules | `api.py`, `cli.py` | Major bottleneck: re-runs all tasks on failure; creates 13 base calls (escalates to 20+ on retry); `reasoning_effort="low"` forces thinking token bloat. Lazy crewai import. |
| `kisan/api.py` | FastAPI application & HTML UI | `app`, `recommend`, `get_run`, `review`, `health`, `index` | `fastapi`, `crew.py`, `db.py` | Frontend / HTTP clients | Single semaphore lock serializes runs. Minimal inline HTML page. |
| `kisan/cli.py` | CLI management commands | `main` (`seed`, `run`, `eval`) | `argparse`, `crew.py`, `evaluate.py` | Terminal / Scripts | Clean CLI interface with `--offline` support. |
| `kisan/evaluate.py` | Evaluation harness | `main`, `pct` | `crew.py`, `db.py`, `security.py` | CLI `eval` | Basic harness exists; lacks detailed stage breakdown and grounding tests. |

---

### 2.2 Results of Independent Claim Verification (C1 – C10)

* **C1: Model Names (`gemini-3.5-flash` / `gemini-3.5-flash-lite`)**  
  **Status: PARTLY REFUTED.**  
  *Evidence:* LiteLLM's model database (`model_prices_and_context_window_backup.json:22887`) explicitly lists `gemini/gemini-3.5-flash` and `gemini/gemini-3.5-flash-lite` with provider `gemini`. Furthermore, log `07a767c7fd0a` lines 1–6 proves that the Google Gemini API accepted `gemini/gemini-3.5-flash`, successfully returning completions for planning, weather analysis, and mandi analysis before exhausting free-tier RPM/TPM quota. However, Gemini 1.5 and 2.0 models are scheduled for deprecation/shutdown, making Gemini 2.5 / 3.x the forward path. The model names are valid, but must be paired with low thinking overhead.
* **C2: `reasoning_effort="low"` Parameter Impact**  
  **Status: PARTLY CONFIRMED / CLARIFIED.**  
  *Evidence:* LiteLLM's `vertex_and_google_ai_studio_gemini.py:860-895` reveals that `reasoning_effort="low"` maps directly to `thinkingLevel="low", includeThoughts=True` on Gemini 3+ models. While supported, generating reasoning tokens significantly increases latency and consumes output token quota. For Groq (run `4cdba4ce7b50`), LiteLLM rejected the parameter completely with `cache_breakpoint` errors. *Verdict:* Make `reasoning_effort` provider-conditional and default to `disable` or `none` for standard extraction to preserve RPM/TPM.
* **C3: `task_callback=None` Severity**  
  **Status: REFUTED (Severity: LOW).**  
  *Evidence:* `crew.py:150` attaches a task-level callback `callback=keep(key)` to every specialist task, which explicitly executes `mon.task_cb(output)` (`crew.py:122`). In CrewAI, setting `task_callback=mon.task_cb` at the `Crew` level would cause duplicate logging for specialists. Only synthesis and communication lacked logging, which is trivial to attach per-task.
* **C4: Redirect stdout in MCP Server**  
  **Status: STRONGLY REFUTED.**  
  *Evidence:* `mcp.server.stdio:80` uses `sys.stdout` for raw JSON-RPC transport (`await stdout.write(json + "\n")`). Redirecting `sys.stdout` to `/dev/null` destroys the JSON-RPC pipe. *Correct Solution:* Enforce that all logging, debugging, and third-party warnings in `mcp_server.py` and `core_tools.py` output exclusively to `sys.stderr`.
* **C5: A2A Discovery Path Order**  
  **Status: REFUTED (Severity: NEGLIGIBLE).**  
  *Evidence:* In `a2a-sdk` 0.3.26 (`a2a/utils/constants.py:3-4`), `AGENT_CARD_WELL_KNOWN_PATH = '/.well-known/agent-card.json'` is the primary path, and `PREV_AGENT_CARD_WELL_KNOWN_PATH = '/.well-known/agent.json'` is the legacy path. `a2a_client.py:39` checks `/.well-known/agent-card.json` first, which matches the installed SDK standard.
* **C6: `seed()` Database Wipe Risk**  
  **Status: REFUTED.**  
  *Evidence:* `db.py:102` executes `DELETE FROM farmers`, leaving the `runs` and `reviews` tables untouched. Deleting and re-inserting farmers is necessary because dates (`sowing_date`, `due_date`, `harvest_date`) are calculated relative to `date.today()` (`db.py:85-98`) so evaluation scenarios remain dynamically valid.
* **C7: Specialist Crew Isolation**  
  **Status: CONFIRMED.**  
  *Evidence:* In run `07a767c7fd0a`, weather (t=113s) and mandi (t=249s) succeeded, but when credit failed at t=290s, `_kickoff` retried the entire crew (`crew.py:73`), repeating already-completed work and burning 3x tokens until hard 429 quota exhaustion.
* **C8: Hugging Face Spaces Multi-Process Support**  
  **Status: CONFIRMED.**  
  *Evidence:* Hugging Face Spaces Docker SDK runs standard OCI containers. Multiple daemon processes (such as ADK on port 8001 and FastAPI on port 7860) run seamlessly when managed via a lightweight entrypoint script or supervisor, as long as port 7860 binds publicly.
* **C9: Missing `requirements.txt` in Dockerfile**  
  **Status: CONFIRMED (Severity: HIGH).**  
  *Evidence:* `Dockerfile:6` executes `COPY --chown=user requirements.txt requirements-obs.txt ./` and line 7 runs `pip install -r requirements.txt`. Neither file exists in repo root (only `requirements-crew.txt`, `requirements-adk.txt`, `requirements-obs.txt` exist). `docker build` fails immediately.
* **C10: Mandi Live vs Synthetic Retrieval**  
  **Status: CONFIRMED.**  
  *Evidence:* In `core_tools.py:112`, live AgMarkNet retrieval sets `trend = None`, which restricts `signal` to `stable` or `below_msp`. In run `07a767c7fd0a:5`, the agent reported `rising signal`, which can only be generated by the synthetic series generator (`core_tools.py:128`). Live AgMarkNet has never produced live data in any logged run.

---

### 2.3 Facts Established (F1 – F9)

* **F1:** No full agentic run has ever completed end-to-end. Best run `07a767c7fd0a` crashed on task 3 with three 429s.
* **F2:** Five historical error classes documented in logs: Groq model not found, Groq `cache_breakpoint` rejection, Google GenAI missing import, Gemini 503 overload, and Gemini 429 quota exhaustion.
* **F3:** Active models in `.env` are `CREW_MODEL=gemini/gemini-3.5-flash` and `ADK_MODEL=gemini-3.5-flash-lite`, with `MAX_RPM=8`.
* **F4:** Two incompatible venvs exist: `.venv-crew` (crewai 1.15.32, litellm 1.100.4, pydantic 2.12.5) and `.venv-adk` (google-adk 1.39.1, a2a-sdk 0.3.26, pydantic 2.14.1). Both require Python 3.11+. `langfuse` and `openinference-*` are uninstalled.
* **F5:** A2A communication works independently: 2 successful assessments recorded in `a2a_client.jsonl` (latencies 41.8s and 29.1s) and 9 events in `adk_a2a.jsonl`.
* **F6:** High latency per task (110–140s) is driven by Gemini reasoning/thinking token generation combined with CrewAI internal RPM sleep windows.
* **F7:** Both CrewAI and ADK target the same Google Cloud project, sharing a single global pool of 15 RPM and 1,500 requests/day.
* **F8:** ⚠️ **UNVERIFIED.** Cost calculation in `crew.py:179` relies on `config.py` defaults ($0.59 / $0.79 per M tokens), which underestimate Gemini 3.5 Flash pricing (claimed $1.50 / $9.00 per M tokens — **these prices are not sourced from an official pricing page and must be verified**). All prices MUST be environment-configurable: `PRICE_IN_PER_M` (default from env or config), `PRICE_OUT_PER_M`. **Action:** Read the real per-model prices from the owner's Google AI Studio usage/billing page and update.
* **F9:** ⚠️ **UNVERIFIED.** Google Gemini free tier is *claimed* to allow 15 RPM, 1,000,000 TPM, and 1,500 RPD per model family — **these limits are not sourced and may vary by model or change without notice**. All limits MUST be environment-configurable: `GEMINI_RPM` (default 15), `GEMINI_RPD` (default 1500), `GEMINI_TPM` (default 1000000). **Action (Task T1.0):** Read the real per-model limits from the owner's Google AI Studio usage page, measure real token counts from the first successful run, and update these defaults.

---

## 3. Final Architecture Decision

### 3.1 Target System Flow Diagram

```
                        ┌────────────────────────────────────────────────────────┐
                        │                   FastAPI / React UI                   │
                        │                 (Port 7860, Public)                    │
                        └───────────────────────────┬────────────────────────────┘
                                                    │
                                         [1. Validate & Screen]
                                                    │
                                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                   Deterministic Orchestrator (crew.py)                                 │
│                                                                                                        │
│   ┌──────────────────────────┐                                                                         │
│   │ Step 0: Plan Router      │ ──[Ambiguous Query]──► LLM Router (1 call)                              │
│   │ (Deterministic Default)  │ ──[Standard Profile]─► Rule Plan (0 calls)                              │
│   └─────────────┬────────────┘                                                                         │
│                 │                                                                                      │
│                 ▼                                                                                      │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ Step 1–4: Checkpointed Specialist Execution (Independent Runs, RunState Checkpoints)           │   │
│   │                                                                                                │   │
│   │   [Weather Specialist]   ──► CrewAI (1 Call)  ──► FastMCP stdio ──► Open-Meteo API             │   │
│   │   [Mandi Specialist]     ──► CrewAI (1 Call)  ──► FastMCP stdio ──► AgMarkNet / Synthetic      │   │
│   │   [Credit Specialist]    ──► CrewAI (1 Call)  ──► FastMCP stdio ──► SQLite (KCC Metrics)       │   │
│   │   [Insurance Specialist] ──► CrewAI (1 Call)  ──► A2A Client    ──► HTTP POST (localhost:8001)│   │
│   │                                                                            │                   │   │
│   │                                                                            ▼                   │   │
│   │                                                              ┌───────────────────────────┐     │   │
│   │                                                              │ Google ADK Agent (:8001)  │     │   │
│   │                                                              │ (1-2 Calls + assess_pmfby)│     │   │
│   │                                                              └───────────────────────────┘     │   │
│   └─────────────────────────────────────────────┬──────────────────────────────────────────────────┘   │
│                                                 │                                                      │
│                                                 ▼                                                      │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ Step 5: Unified Synthesis & Farmer Communication (1 Merged Call)                               │   │
│   │ Output: Pydantic FinalReport (Recommendations + Multi-lingual FarmerMessage)                   │   │
│   └─────────────────────────────────────────────┬──────────────────────────────────────────────────┘   │
│                                                 │                                                      │
│                                                 ▼                                                      │
│   ┌────────────────────────────────────────────────────────────────────────────────────────────────┐   │
│   │ Step 6: Guardrail Finalizer & HITL Gate                                                        │   │
│   │ PII Redaction, Numerical Grounding Check, Disclaimer, SQLite Persistence (`runs` table)        │   │
│   └────────────────────────────────────────────────────────────────────────────────────────────────┘   │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

### 3.2 LLM Call Budget Arithmetic

> **IMPORTANT:** The original claim of "1 call per specialist" is incorrect when a specialist uses native tool-calling: one LLM call to request the tool + one LLM call to interpret the tool result = 2 calls per specialist. The architecture supports two modes selected by the `TOOL_MODE` environment variable.

#### `TOOL_MODE=prefetch` (Default — Recommended for Free Tier)

The **orchestrator itself** executes each MCP tool through a real MCP client session (satisfying Requirement 2), collects the tool evidence, and then makes **one LLM call per CrewAI specialist** with the tool evidence pre-injected into the specialist's context. Each specialist is a real `crewai.Agent` with a real `crewai.Task` inside a single-task `crewai.Crew` (satisfying Requirement 7). The specialist interprets the evidence and produces structured output in a single LLM turn.

| Pipeline Stage | Current Design Calls | Prefetch Target Calls | Mechanism |
|---|---|---|---|
| **0. Planning / Routing** | 1–2 | **0** (standard) / **1** (user Q) | Deterministic routing based on profile flags |
| **1. Weather Specialist** | 2–3 | **1** | MCP tool pre-executed; specialist gets evidence in context |
| **2. Mandi Specialist** | 2–3 | **1** | MCP tool pre-executed; specialist gets evidence in context |
| **3. Credit Specialist** | 2–3 | **1** | MCP tool pre-executed; specialist gets evidence in context |
| **4. Insurance Specialist** | 2–3 (Crew) + 3–4 (ADK) | **1** (Crew) + **1** (ADK) | A2A pre-executed; ADK tuned for single-turn |
| **5. Synthesis + Communication** | 2–3 + 2 | **1** | Merged into single call producing `LLMReport` with `FarmerMessage` |
| **Total** | **15–19** | **5–7** | **~65% reduction; fits comfortably in 15 RPM** |

#### `TOOL_MODE=agentic` (For Evaluation Comparison)

Each CrewAI specialist has its MCP tools bound via `crewai.tools` wrappers and autonomously decides to call them. This means 2 LLM calls per tool-using specialist (one to request the tool, one to write the answer). The ADK agent also uses 2 calls (tool request + response).

| Pipeline Stage | Agentic Target Calls | Mechanism |
|---|---|---|
| **0. Planning / Routing** | **0** / **1** | Same as prefetch |
| **1. Weather Specialist** | **2** | Tool request + interpret |
| **2. Mandi Specialist** | **2** | Tool request + interpret |
| **3. Credit Specialist** | **2** | Tool request + interpret |
| **4. Insurance Specialist** | **2** (Crew) + **2** (ADK) | Tool request + interpret, both sides |
| **5. Synthesis + Communication** | **1** | Merged call |
| **Total** | **9–12** | Higher cost but demonstrates autonomous tool use |

> **Action:** After the first successful run in each mode, count the actual LLM calls from `Monitor.counts["llm_requests"]` and update these tables with measured values. The `TOOL_MODE` switch is set via environment variable and defaults to `prefetch`.

> **Implementation note:** In both modes, each specialist is a real `crewai.Agent` with a real `crewai.Task` inside a real single-task `crewai.Crew` (one Crew per specialist). In `prefetch` mode the tools are still registered on the Agent but the orchestrator pre-populates the task description with tool output so the agent does not invoke them. In `agentic` mode the agent invokes tools autonomously. This keeps Requirement 7 (real CrewAI objects) true in both modes.

---

## 4. Decision Log (D1 – D14)

### D1: Orchestration Architecture & Call Budget
* **Decision:** Adopt a Python-driven checkpointed state machine that executes specialist agents sequentially, saves intermediate state into `RunState`, and merges synthesis and communication into a single final LLM call.
* **Alternatives Rejected:**
  1. *Single Sequential Crew (Current):* Rejected because a failure at step 4 triggers a complete restart of steps 1–3, causing quota blowouts.
  2. *Fully Autonomous Agent Loop (No structure):* Rejected due to unbounded token costs and high nondeterminism.
* **Why:** Guarantees that each specialist runs exactly once. Completed tasks are cached in memory/SQLite; retries only execute the failed specialist.
* **Acceptance Test:** Run pipeline on F001; inspect `Monitor.counts["llm_requests"]` in log file; must be $\le 7$.

### D2: Quota-Aware LLM Layer
* **Decision:** Implement a centralized `TokenBucketRateLimiter` shared across CrewAI and ADK via a file lock (`/tmp/kisan_rpm.lock`), configure LiteLLM with `num_retries=1`, disable hidden retries, and implement 429 error handling that **reads the quota metric and `retryDelay` from the error response BODY** (not a `Retry-After` header, which Gemini does not reliably send). If the exhausted quota is the **per-day (RPD)** quota, **fail fast to the rule-based fallback** instead of sleeping (sleeping would block for hours). If the exhausted quota is RPM, sleep for the `retryDelay` from the body (capped at 90 s). Optionally, if a `FALLBACK_LLM_KEY` environment variable is set (e.g., a second free-tier Gemini key or a Groq free key), add it as a second provider in the LiteLLM fallback chain — but never require it.
* **Alternatives Rejected:**
  1. *Independent in-memory limiters:* Rejected because CrewAI and ADK run in separate OS processes and would blindside each other's quota.
  2. *Redis-backed rate limiter:* Rejected to avoid running a background Redis daemon on a RAM-constrained i3 laptop.
  3. *Parsing `Retry-After` header only:* Rejected because Gemini 429 responses encode quota details in the JSON body, not HTTP headers.
* **Why:** Gemini free-tier quota is shared across the entire GCP project. Both processes must coordinate to stay below the configured `GEMINI_RPM` (safety margin under the actual limit). Fail-fast on RPD exhaustion prevents pointless multi-hour sleeps.
* **Acceptance Test:** Trigger 3 concurrent requests; verify the 2nd and 3rd queue cleanly without producing a 429 error. Simulate an RPD-exhausted 429 body; verify the pipeline falls back to rules within 2 s.

### D3: Structured Output Reliability
* **Decision:** Use Pydantic schema validation with native JSON mode (`response_format={"type": "json_object"}`) and a single repair attempt using `json_repair`.
* **Alternatives Rejected:**
  1. *Unbounded Instructor retry loop:* Rejected because failed schema validations burn free-tier RPM rapidly.
  2. *Plain regex parsing without fallback:* Rejected due to high risk of JSON truncation.
* **Why:** Gemini natively generates valid JSON when provided a Pydantic JSON schema in the system prompt. `json_repair` handles trailing commas and minor markdown fences without extra LLM round-trips.
* **Acceptance Test:** Pass intentionally noisy LLM output through `_parse()`; verify valid Pydantic model returned without secondary API call.

### D4: Zero-Quota Development & Testing Strategy
* **Decision:** All automated unit tests, CI checks, and local feature iterations MUST run using `pytest` with a deterministic mock LLM provider (`OfflineMockLLM`) or `--offline` rules mode. Live API calls are strictly gated behind an environment variable `ALLOW_LIVE_API=1` and a maximum daily budget of 10 runs.
* **Alternatives Rejected:**
  1. *Running live tests on every git commit:* Rejected because test suites would deplete the 1,500 RPD daily quota immediately.
* **Why:** Guarantees that development never blocks the team or breaks free-tier limits.
* **Acceptance Test:** Run `pytest tests/`; verify 100% test passage with 0 network calls to Google APIs.

### D5: A2A Hardening & Framework Interoperability
* **Decision:** Keep Google ADK running in `.venv-adk` exposed on port 8001 via `to_a2a()`. Hardcode the primary discovery path to `/.well-known/agent-card.json` with a 2-second timeout, inject `run_id` and OpenTelemetry traceparent headers into the JSON-RPC message context, and wrap the client with a 15-second timeout that falls back to a clean error string on timeout.
* **Alternatives Rejected:**
  1. *Rewriting the insurance agent in CrewAI:* Rejected because Requirement 7 and Requirement 6 strictly mandate using both CrewAI and ADK interoperating over A2A.
* **Why:** Ensures strict compliance with Requirements 6 and 7 while preventing ADK hangs from blocking the main orchestrator.
* **Acceptance Test:** Stop ADK server; execute pipeline; verify orchestrator logs "insurance unavailable" and proceeds to complete synthesis without crashing.

### D6: MCP Server Process & Least-Privilege Tool Access
* **Decision:** Spawn **one MCP server process per pipeline run** (not per specialist, not per tool call) to avoid process-creation overhead on the slow i3 CPU. The orchestrator maintains a **per-specialist tool allow-list** (`TOOLSET`) that restricts which MCP tools each specialist may invoke, enforced in the orchestrator before dispatching the call to the shared MCP session. This reconciles the "single warm MCP session" design with least-privilege access control. Explicitly inject `PYTHONUNBUFFERED=1`, `PYTHONPATH`, and `KISAN_DB` into the subprocess environment. Configure `logging` in `mcp_server.py` to route strictly to `sys.stderr`.
  ```python
  TOOLSET = {
      "weather":   {"get_weather_forecast"},
      "mandi":     {"get_mandi_prices"},
      "credit":    {"compute_kcc_metrics"},
      "insurance": set(),  # uses A2A, not MCP
  }
  ```
* **Alternatives Rejected:**
  1. *Spawning a new MCP subprocess for every individual tool call:* Rejected due to process creation overhead on an i3 CPU (~0.8 s per spawn).
  2. *One MCP server per specialist:* Rejected — 4 concurrent Python subprocesses would consume ~400 MB extra RAM.
  3. *SSE transport over HTTP:* Rejected as unnecessary complexity for local tool execution.
* **Why:** Protects the stdio JSON-RPC stream from corruption, reduces execution latency by ~3 seconds per specialist, keeps RAM usage minimal, and enforces least-privilege without separate server processes.
* **Acceptance Test:** Run `python -m kisan.mcp_server` and send raw JSON-RPC ping on stdin; verify pure JSON-RPC on stdout and clean logs on stderr. Verify that a specialist cannot invoke a tool outside its allow-list.
* **Runtime:** < 1 s for server startup | **RAM impact:** +40 MB (single Python process) | **Disk impact:** ~0

### D7: Observability (Langfuse v3 + JSONL Audit Trail)
* **Decision:** Install `langfuse>=3,<4` (v3 — required because `kisan/observability.py` uses the v3 API) and `openinference-instrumentation-crewai` in `.venv-crew`, and `openinference-instrumentation-google-adk` in `.venv-adk`. Install each OpenInference package in the correct venv only. Retain the local JSONL files in `logs/` as the primary, un-killable, zero-latency audit trail. Propagate `trace_id` across the A2A HTTP boundary via `traceparent` headers. **Langfuse is optional at runtime**: it is switched on (via `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` env vars) **only for evidence runs, the evaluation, and the demo**, to save CPU and RAM on the slow i3 during development. When Langfuse keys are absent, `observability.py` gracefully degrades to JSONL-only logging.
* **Alternatives Rejected:**
  1. *LangSmith:* Rejected per Requirement 9 and project constraints.
  2. *Relying only on Langfuse cloud:* Rejected because network drops or expired keys would break audit logging.
  3. *Langfuse v2 (2.59+):* Rejected because `observability.py` uses the v3 client API (`langfuse.Langfuse` constructor signature, `trace()` / `span()` methods changed in v3).
* **Why:** Dual-layer observability: local JSONL guarantees auditability even offline; Langfuse v3 provides interactive trace visualisations for evaluation and demo. Keeping it optional avoids CPU/RAM overhead during routine development.
* **Acceptance Test:** Execute 1 live run with Langfuse keys set; inspect Langfuse UI to confirm a single linked trace spanning CrewAI orchestrator and ADK insurance agent. Execute 1 run without keys; verify no import errors and JSONL logs are written.
* **Runtime:** Langfuse init ~2 s | **RAM impact:** +30 MB when active, +0 when inactive | **Disk impact:** ~0 (cloud-hosted traces)

### D8: Guardrail Enhancements (Requirement 8)
* **Decision:** Expand `kisan/security.py` to include: (a) multilingual injection patterns (Devanagari script + Hinglish transliterations), (b) tool output screening for injected prompts, (c) a numerical grounding validator ensuring any monetary value or percentage cited in recommendations exists in the tool evidence, and (d) strict preservation of agricultural vocabulary (e.g., "kill pests", "crop damage" must not trigger toxic filters).
* **Alternatives Rejected:**
  1. *Heavy ML-based moderation models (e.g. Llama Guard):* Rejected because local inference is infeasible on an i3 CPU without GPU.
* **Why:** Fast, lightweight regex and rule-based screening operates in < 2ms without consuming token quota or memory.
* **Acceptance Test:** Run adversarial test suite (`evaluate.py`); verify 100% of attack prompts blocked and 100% of legitimate farming prompts permitted.

### D9: Data Integrations & Synopsis Scope Reconciliation
* **Decision:** Adopt the following reconciliation for academic prototype delivery:
  * **Database:** Keep **SQLite** with the **default journal mode** (DELETE). Do NOT enable WAL mode — `db.py` opens read-only connections with `mode=ro`, and WAL mode can break read-only connections that lack write access to the WAL file. The default journal mode is safe for single-writer, multi-reader SQLite usage.
  * **Caching:** Keep in-memory TTL dictionary cache. Reconciles Redis.
  * **RAG / BM25 Retrieval (SHOULD tier):** Implement a **pure-Python BM25 keyword retrieval** over PMFBY official operational guidelines and KCC master circular (stored as short, officially-sourced markdown excerpts with their source URLs in `data/docs/`). Use either a small hand-written BM25 implementation (~80 lines) or the tiny `rank_bm25` pip package (pure Python, ~15 KB, **no model downloads**). The BM25 retrieval is a **deterministic tool** whose output becomes evidence — it adds **zero LLM calls**. Avoid Chroma, pgvector, FAISS, sentence-transformers, or any package that downloads model weights.
  * **Bhashini / WhatsApp:** Officially **DEFER** to future work with clear architectural placeholder documentation in report and slides.
* **Alternatives Rejected:**
  1. *Running PostgreSQL + pgvector + Redis in Docker locally:* Rejected because running 3 extra daemons on a laptop with limited disk and 12 GB RAM risks system thrashing and Docker OOMs. **FORBIDDEN per Section 0.**
  2. *Embedding-based RAG (sentence-transformers + vector DB):* Rejected because it requires downloading model weights (~400 MB) and running inference on CPU. **FORBIDDEN per Section 0.**
  3. *TF-IDF with scikit-learn:* Acceptable but heavier than `rank_bm25`; either is fine as long as no model weights are downloaded.
* **Why:** Maximizes stability, speed, and evaluation reproducibility while keeping the system 100% self-contained and within Section 0 constraints.
* **Acceptance Test:** Query BM25 retrieval function for "PMFBY 72 hours localized calamity"; verify exact rule snippet with source URL returned in < 10ms. Verify `db.py` works correctly with default journal mode.
* **Runtime:** < 10 ms per query | **RAM impact:** +5 MB (in-memory index) | **Disk impact:** +200 KB (`data/docs/` excerpts + `rank_bm25` package)

### D10: No-Build React Dashboard Architecture
* **Decision:** Build a **no-build frontend** as a single `kisan/static/index.html` that uses:
  * **React 18 UMD builds** (`react.production.min.js`, `react-dom.production.min.js`) — downloaded once with `curl` into `kisan/static/vendor/` at pinned versions.
  * **htm** tagged-template library (no JSX compiler needed) — enables JSX-like syntax in plain JavaScript via template literals.
  * **Tailwind CSS play script** (`cdn.tailwindcss.com`) — downloaded once into `kisan/static/vendor/` at a pinned version.
  All vendor files are committed to the repo so the dashboard works with **no internet access and no Node/npm installation**. FastAPI serves the `kisan/static/` folder via `StaticFiles` at `/`. There is no `frontend/` folder, no `package.json`, no `node_modules/`, no build step.
* **Features (all retained from original D10):**
  1. Farmer Profile Selector (F001–F008) with synthetic badge display.
  2. Real-time run timeline showing agent states (Plan → Weather → Mandi → Credit → Insurance → Synthesis).
  3. Recommendation cards displaying priority, action, source agents, and confidence scores.
  4. Tool Evidence inspector with JSON tree view.
  5. Human-in-the-Loop review panel with Approve / Reject buttons that update SQLite via `/api/runs/{id}/review`.
  6. Latency, token count, and cost metrics dashboard.
  7. "Demo Mode (Offline Replay)" toggle for fail-safe presentations using rule engine results.
* **Alternatives Rejected:**
  1. *Vite + React + Tailwind build pipeline:* Rejected because Node/npm/Vite are **FORBIDDEN per Section 0** (RAM + disk + slow CPU).
  2. *Streamlit / Gradio:* Rejected because the project synopsis explicitly commits to a React + Tailwind frontend.
  3. *CDN-only (no vendor/ folder):* Rejected because the dashboard must work offline on the HF Space and during demos without internet.
* **Why:** Zero build step, zero Node dependency, zero npm packages. Works offline. Keeps every feature. File size is ~300 KB total for vendor libs.
* **Acceptance Test:** Open `http://localhost:7860/` in browser; verify full interactive dashboard renders and triggers `/api/recommend`. Run with internet disabled; verify dashboard still loads from local vendor files.
* **Runtime:** N/A (no build) | **RAM impact:** ~0 (static files) | **Disk impact:** +300 KB (vendor JS/CSS files)

#### Vendor Setup Task (one-time)
```bash
mkdir -p kisan/static/vendor
# React 18 UMD (pinned)
curl -L -o kisan/static/vendor/react.production.min.js \
  "https://unpkg.com/react@18.3.1/umd/react.production.min.js"
curl -L -o kisan/static/vendor/react-dom.production.min.js \
  "https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js"
# htm (tagged template JSX alternative)
curl -L -o kisan/static/vendor/htm.module.js \
  "https://unpkg.com/htm@3.1.1/dist/htm.module.js"
# Tailwind CSS play script (pinned)
curl -L -o kisan/static/vendor/tailwindcss-play.js \
  "https://cdn.tailwindcss.com/3.4.17"
```

### D11: Deployment Architecture (Hugging Face Spaces)
* **Decision:** Target Hugging Face Spaces (Docker SDK). Create a production `Dockerfile` that builds two isolated virtual environments (`/opt/venv-crew` and `/opt/venv-adk`). Use a robust bash entrypoint script (`start.sh`) that runs `python -m kisan.cli seed`, starts ADK on `127.0.0.1:8001`, polls `http://127.0.0.1:8001/.well-known/agent-card.json` until healthy (max 15s), and finally starts FastAPI via Uvicorn on `0.0.0.0:7860` (**without `--reload`** per Section 0). **Do NOT build the Docker image locally** (FORBIDDEN per Section 0) — test `start.sh` locally in WSL with parameterised venv paths (`VENV_CREW`, `VENV_ADK` env vars defaulting to `/opt/venv-crew` and `/opt/venv-adk` but overridable to `.venv-crew` and `.venv-adk` for local testing) and let Hugging Face build the image in the cloud.
* **Fallback Strategy:** If API keys expire or the cloud space runs out of quota during an evaluation demo, the UI provides an automated toggle to "Demo Mode (Offline Replay)", which runs the deterministic rule engine without throwing errors.
* **Alternatives Rejected:**
  1. *Render / Railway:* Rejected due to strict credit card requirements and monthly runtime limits.
  2. *Local Docker builds for testing:* Rejected — OOM risk on 6 GB WSL; slow D: disk. **FORBIDDEN per Section 0.**
* **Why:** Hugging Face Spaces is 100% free, requires no credit card, supports Docker natively, and provides persistent public HTTPS URLs. Testing `start.sh` locally in WSL validates the startup sequence without needing Docker.
* **Acceptance Test:** Run `VENV_CREW=.venv-crew VENV_ADK=.venv-adk bash start.sh` in WSL; verify ADK starts, health endpoint returns `{"ok": true}`, and FastAPI serves the dashboard. Push to HF Space; verify cloud build succeeds and public URL is active.
* **Runtime:** ~30 s local start.sh test | **RAM impact:** +200 MB (ADK + FastAPI) | **Disk impact:** ~0 locally

### D12: Evaluation & Benchmarking Methodology (Requirement 10)
* **Decision:** Upgrade `kisan/evaluate.py` to run an 8-farmer benchmark suite with **live agentic runs from the laptop CLI** (not offline-only). An offline (rule-based) evaluation alone does not evaluate the agentic system. The evaluation plan is:
  1. Run all 8 farmers **live** from the laptop CLI in **both** `TOOL_MODE=prefetch` and `TOOL_MODE=agentic`, with at least 2 repeats per farmer if quota allows, spread over several days to stay within RPD limits.
  2. Run all 8 farmers in **offline (rule-based) mode** as a **baseline comparison column** — not as the primary evaluation.
  3. Report **measured** per-stage latency, LLM call counts, prompt/completion/reasoning tokens, and cost for each run.
  4. Evaluate:
     * **Functional Correctness:** Agent routing precision, mandatory recommendation presence, and numerical grounding accuracy.
     * **Latency Profiles:** Total latency, per-agent execution times, p50, and p95.
     * **Token & Cost Economics:** Prompt tokens, completion tokens, reasoning tokens, and verified costs (using measured prices — see ⚠️ UNVERIFIED note in F8).
     * **Safety & Guardrails:** Block rate across 4 adversarial injection attacks and 4 toxic abuse prompts.
     * **HITL Activation Rate:** Accuracy of the review gate on credit-overdue and high-risk profiles.
     * **Mode Comparison:** prefetch vs. agentic call counts, latency, and cost side-by-side.
  The harness outputs structured results to `logs/eval_results.json` and a formatted summary table to `logs/eval_report.md`.
* **Alternatives Rejected:**
  1. *Manual testing without metrics output:* Fails Requirement 10.
  2. *Offline-only evaluation:* Does not test the actual agentic system, LLM integration, or real-world latency/cost.
* **Why:** Provides rock-solid quantitative data from real agentic runs, with a rule-based baseline for comparison, and ready-made tables for the final report and presentation slides.
* **Acceptance Test:** Execute `python -m kisan.cli eval --live --farmers all --repeats 2`; verify `logs/eval_results.json` and `logs/eval_report.md` are populated with complete metric tables including both TOOL_MODE values and the offline baseline column.
* **Runtime:** ~60 min total for 8 farmers × 2 modes × 2 repeats (spread over days) | **RAM impact:** +50 MB during eval | **Disk impact:** +2 MB (JSON + Markdown results)

### D13: Documentation, Slide Deck, and Viva Preparation
* **Decision:** Author all documents in **Markdown** and convert using tools allowed by Section 0:
  * **Final Report:** Write in Markdown (`docs/FINAL_REPORT.md`), following university format (Problem, Multi-Agent Architecture, A2A & MCP Implementation, Guardrails, Evaluation, Conclusion). Convert to `.docx` with **pandoc** (already installed in WSL): `pandoc docs/FINAL_REPORT.md -o docs/FINAL_REPORT.docx`. Export PDF from Word or Google Docs. **Do NOT install LaTeX** (FORBIDDEN per Section 0).
  * **Presentation:** Write slide outline in `docs/PRESENTATION.md`. Build the actual 15-slide deck in **Google Slides** (free). Export PDF from Google Slides.
  * **Viva Prep Guide:** Write in Markdown (`docs/VIVA_PREPARATION.md`). Convert to `.docx` with pandoc. Curated question-and-answer guide split by member (Prakhar: Orchestration, Backend, Evaluation; Rishabh: Tools, ADK/A2A, React UI, Guardrails).
  * **Demo Script:** Write in Markdown (`docs/DEMO_SCRIPT.md`). 10-minute live demonstration script with contingency steps.
  * **Backup Demo Video:** Record with **Windows Game Bar** (`Win+Alt+R`) — built-in, zero install. **Do NOT install OBS** (FORBIDDEN per Section 0).
* **Acceptance Test:** Run `pandoc docs/FINAL_REPORT.md -o docs/FINAL_REPORT.docx`; verify clean .docx output. Verify Google Slides deck has 15 slides covering all requirements.
* **Runtime:** pandoc conversion < 5 s | **RAM impact:** ~0 | **Disk impact:** +5 MB (.docx files)

### D14: Repository Hygiene, Secret Safety & Version Control
* **Decision:** Immediately update `.gitignore` to explicitly exclude `.venv-crew/`, `.venv-adk/`, `node_modules/`, `kisan/static/vendor/` (large but committed — reconsider), and test coverage artifacts. Ensure `.env` is never committed and never included in LLM prompts. Provide sanitized environment template `.env.example`. Additionally:
  * **API Key Rotation:** Add a task to rotate the `GOOGLE_API_KEY` and `LANGFUSE_*` keys periodically (at minimum, after any accidental exposure). Document the rotation procedure in `.env.example`.
  * **Git Init & First Commit:** Run `git init` with a first commit **before any code change** so that every work order can be cleanly rolled back with `git checkout -- <file>` or `git stash`.
  * **Secrets in Prompts:** Never paste API keys, `.env` contents, or credentials into LLM prompts, chat interfaces, or log files. `observability.py` must redact any env var values from log entries.
* **Acceptance Test:** Run `git status`; verify no virtualenv files or database binaries appear in untracked files. Run `git log --oneline -1`; verify at least one commit exists. Run `grep -r 'AIza\|sk-\|LANGFUSE' logs/`; verify no API keys in logs.
* **Runtime:** < 2 min | **RAM impact:** ~0 | **Disk impact:** +1 MB (.git objects)

---

## 5. Phased Implementation Roadmap

```
  Phase 0: Hygiene & Container Fixes
                     │
                     ▼
  Phase 1: Quota-Bounded State Machine (Gate G0)
                     │
                     ▼
  Phase 2: Observability & Guardrails Hardening
                     │
                     ▼
  Phase 3: React Dashboard & Static Build
                     │
                     ▼
  Phase 4: Cloud Deployment (Hugging Face Spaces)
                     │
                     ▼
  Phase 5: Evaluation & Academic Deliverables
```

---

### Phase 0: Repository Hygiene, Dependencies & Version Control
* **Goal:** Clean repository state, ensure `.gitignore` covers all large folders, create unified requirement files, establish version control baseline, and set up secret safety.
* **Entry Condition:** Current repository state. Section 0 hardware tasks (T0-HW.*) completed.
* **Exit Gate (G-Pre):** `git status` shows clean tracking; `git log --oneline -1` shows initial commit; `.env` is in `.gitignore`; pinned constraint files exist.

| Task ID | Description | Files to Touch | Owner | Dep | Est (h) | Runtime | RAM | Disk | Acceptance Test Command & Expected Output | Rollback Plan |
|---|---|---|---|---|---|---|---|---|---|---|
| **T0.0** | Run `git init && git add -A && git commit -m "baseline before roadmap"` so every change can be rolled back. | `.git/` | Prakhar | None | 0.1 | < 10 s | ~0 | +1 MB | `git log --oneline -1` shows commit. | N/A (first commit) |
| **T0.1** | Update `.gitignore` to exclude `.venv-crew/`, `.venv-adk/`, `.venv/`, `.env`, `__pycache__/`, `*.pyc`, `data/kisan.db`, `logs/`. Verify `.env` is excluded. | `.gitignore` | Prakhar | T0.0 | 0.5 | < 30 s | ~0 | ~0 | `git status --ignored` shows `.venv-crew` ignored; `grep '\.env' .gitignore` matches. | `git checkout -- .gitignore` |
| **T0.2** | Create root `requirements.txt` (merging crew and obs) and keep `requirements-adk.txt` clean. Pin Langfuse to `>=3,<4`. Generate `constraints-crew.txt` and `constraints-adk.txt` via `pip freeze` in each venv. | `requirements.txt`, `requirements-crew.txt`, `constraints-crew.txt`, `constraints-adk.txt` | Prakhar | None | 0.5 | < 2 min | ~0 | +10 KB | `test -f requirements.txt && test -f constraints-crew.txt && echo OK` outputs `OK`. | Delete files. |
| **T0.3** | Create `.env.example` with all env vars documented (keys blanked). Document API key rotation procedure in comments. Verify `.env` is NOT in git. | `.env.example` | Prakhar | T0.1 | 0.25 | < 1 min | ~0 | +2 KB | `git ls-files .env` outputs nothing; `test -f .env.example && echo OK`. | Delete `.env.example`. |
| **T0.4** | Fix Dockerfile: add HF README.md front matter (`title`, `sdk: docker`, `app_port: 7860`), add `.dockerignore` (exclude `.venv-*`, `.git`, `logs/`, `data/kisan.db`, `__pycache__`), create and `chown` `data/` and `logs/` directories for the non-root user. Use `--no-cache-dir` for pip. Replace `< 1.8 GB` image target with "measured after first HF cloud build". Add `constraints-crew.txt` and `constraints-adk.txt` for reproducible builds. | `Dockerfile`, `.dockerignore`, `README.md` (HF front matter) | Prakhar | T0.2 | 1.5 | N/A (cloud build) | N/A | +5 KB | `.dockerignore` exists; `grep 'app_port: 7860' README.md` matches; `grep 'chown.*data' Dockerfile` matches. | Revert files. |
| **T0.5** | Upgrade `start.sh` with parameterised venv paths (`VENV_CREW`, `VENV_ADK`), readiness polling for ADK port 8001, and `--no-reload` on uvicorn. | `start.sh` | Rishabh | T0.4 | 1.0 | ~30 s to test | +200 MB (transient) | ~0 | `VENV_CREW=.venv-crew VENV_ADK=.venv-adk bash start.sh` starts ADK and FastAPI. `grep -- '--reload' start.sh` returns nothing. | Revert `start.sh`. |

---

### Phase 1: Core Engine Hardening & Single-Run Completion (Gate G0)
* **Goal:** Achieve **Gate G0**: one full run completes end-to-end with `mode="agentic"`, every pipeline stage is logged with a terminal event, a valid `FinalReport` is generated, the LLM call count is within budget (≤ 7 for `TOOL_MODE=prefetch`, ≤ 12 for `TOOL_MODE=agentic`), and the run finishes within the configurable timeout (`RUN_TIMEOUT`, default 300 s).
* **Entry Condition:** Phase 0 complete.
* **Exit Gate (G0):** `python -m kisan.cli run F001` completes with `mode: "agentic"`, a `FinalReport` JSON is persisted, every stage has a terminal JSONL event (kind `final`, `aborted`, or `timeout`), `Monitor.counts["llm_requests"]` is within budget, and wall-clock time < `RUN_TIMEOUT`. *(Replaces old G0 which required "zero 429 errors and latency < 90s" — that was unrealistic on this i3.)*

| Task ID | Description | Files to Touch | Owner | Dep | Est (h) | Runtime | RAM | Disk | Acceptance Test Command & Expected Output | Rollback Plan |
|---|---|---|---|---|---|---|---|---|---|---|
| **T1.0** | Read real per-model free-tier limits from Google AI Studio usage page. Update `GEMINI_RPM`, `GEMINI_RPD`, `GEMINI_TPM`, `PRICE_IN_PER_M`, `PRICE_OUT_PER_M` in `.env.example` and `config.py` with verified values. Mark as verified or keep UNVERIFIED flag. | `kisan/config.py`, `.env.example` | Prakhar | None | 0.5 | < 5 min | ~0 | ~0 | `python3 -c "from kisan import config; print(config.GEMINI_RPM, config.PRICE_IN_PER_M)"` prints env-configurable values. | Revert `config.py`. |
| **T1.1** | Make all Gemini limits and prices environment-configurable in `config.py`: `GEMINI_RPM`, `GEMINI_RPD`, `GEMINI_TPM`, `PRICE_IN_PER_M`, `PRICE_OUT_PER_M`, `RUN_TIMEOUT`, `MCP_TOOL_TIMEOUT`, `A2A_TIMEOUT`. | `kisan/config.py` | Prakhar | T1.0 | 0.5 | < 1 min | ~0 | ~0 | `RUN_TIMEOUT=120 python3 -c "from kisan import config; assert config.RUN_TIMEOUT == 120"` | Revert `config.py`. |
| **T1.2** | Remove `reasoning_effort="low"` in `crew.py` or make it conditional; configure model with `temperature=0.0`. | `kisan/crew.py` | Prakhar | None | 0.5 | < 1 min | ~0 | ~0 | Inspect `crew.py`; ensure no un-gated `reasoning_effort` passed to LiteLLM. | Revert `crew.py`. |
| **T1.3** | Implement `TOOL_MODE=prefetch\|agentic` switch in `crew.py`. In prefetch mode: orchestrator executes MCP tools via a real MCP client session, collects evidence, then makes one LLM call per specialist with evidence in context. In agentic mode: specialists have tools bound and call them autonomously. Both modes use real `crewai.Agent`/`crewai.Task`/`crewai.Crew` objects (one single-task Crew per specialist). | `kisan/crew.py` | Prakhar | T1.2 | 3.0 | ~2 min (prefetch), ~4 min (agentic) | +150 MB | ~0 | `TOOL_MODE=prefetch python -m kisan.cli run F002 --offline`; inspect `state.outputs`; verify 4 specialists populated. | Revert `crew.py`. |
| **T1.4** | Add per-run hard timeout (`RUN_TIMEOUT` seconds) with `try/finally` that always writes a terminal JSONL event (`kind: "final"`, `kind: "aborted"`, or `kind: "timeout"`). Fixes the bug where run `3b10eddfb574` ended with no final record. | `kisan/crew.py`, `kisan/observability.py` | Prakhar | T1.3 | 1.0 | < 1 min | ~0 | ~0 | Kill a running pipeline mid-flight; verify `logs/<run_id>.jsonl` ends with `kind: "aborted"` or `kind: "timeout"`. | Revert files. |
| **T1.5** | Merge Synthesis and Communication into a single LLM call producing structured `LLMReport` with `FarmerMessage`. | `kisan/crew.py`, `kisan/schemas.py` | Prakhar | T1.3 | 2.0 | ~3 min | ~0 | ~0 | Run pipeline; verify `FinalReport.message.hindi` is populated with valid Devanagari. | Revert to two tasks. |
| **T1.6** | Implement 429 handling: parse quota metric and `retryDelay` from error response **body**. If exhausted quota is RPD → fail fast to rule-based fallback (no sleep). If RPM → sleep for `retryDelay` (capped at 90 s). Optionally check `FALLBACK_LLM_KEY` for a second free provider. | `kisan/crew.py` | Prakhar | T1.1 | 1.5 | < 1 min | ~0 | ~0 | Simulate RPD-exhausted 429 body; verify fallback to rules within 2 s. | Revert `crew.py`. |
| **T1.7** | Import `crewai` (and `crewai.tools` wrapper in `a2a_client.py`) **lazily** — only when a live run starts. This ensures `--offline` runs, `pytest`, and the rule-based baseline start quickly on the slow CPU and do not require crewai in the test environment. | `kisan/crew.py`, `kisan/a2a_client.py` | Prakhar | None | 1.0 | < 1 min | ~0 | ~0 | `time python -m kisan.cli run F001 --offline` completes in < 3 s without importing crewai. `python -c "import kisan.crew"` does not import crewai at module level. | Revert files. |
| **T1.8** | Ensure `mcp_server.py` routes all debug/logging strictly to `sys.stderr` to keep `stdout` pristine. | `kisan/mcp_server.py` | Rishabh | None | 0.5 | < 1 min | ~0 | ~0 | Test stdio with MCP inspector or CLI; verify zero protocol parse errors. | Revert `mcp_server.py`. |
| **T1.9** | Always inject `KISAN_DB` explicitly into MCP subprocess environment in `crew.py:_mcp`. | `kisan/crew.py` | Rishabh | None | 0.5 | < 1 min | ~0 | ~0 | Run credit tool via MCP; verify database records found without error. | Revert `crew.py`. |
| **T1.10** | Execute first live test on F001; verify end-to-end completion. Measure real token counts and update the call budget tables. | `logs/` | Both | T1.1-T1.9 | 1.0 | ~5 min | +200 MB | +50 KB | `python -m kisan.cli run F001` → Output has `"mode": "agentic"`. Log shows all tasks done with terminal event. `Monitor.counts["llm_requests"]` within budget. | Inspect error log. |

---

### Phase 2: Observability, Guardrails & A2A Hardening
* **Goal:** Fulfill Requirements 5, 6, 8, and 9 with rock-solid evidence artifacts.
* **Entry Condition:** Phase 1 (Gate G0) passed.
* **Exit Gate (G1):** Langfuse v3 trace displays linked CrewAI and ADK spans; adversarial attacks are 100% blocked in `evaluate.py`.

| Task ID | Description | Files to Touch | Owner | Dep | Est (h) | Runtime | RAM | Disk | Acceptance Test Command & Expected Output | Rollback Plan |
|---|---|---|---|---|---|---|---|---|---|---|
| **T2.1** | Install `langfuse>=3,<4` (v3) and `openinference-instrumentation-crewai` in `.venv-crew`. Install `openinference-instrumentation-google-adk` in `.venv-adk`. Use `pip install --no-cache-dir` followed by `pip cache purge && df -h` per Section 0. Langfuse stays **optional at runtime** — switched on only for evidence runs, evaluation, and demo. | `requirements.txt`, `requirements-adk.txt` | Prakhar | G0 | 1.0 | ~3 min | +30 MB when active | +15 MB | `.venv-crew/bin/python -c "import langfuse; assert langfuse.VERSION.startswith('3.'); print('OK')"` | Uninstall packages. |
| **T2.2** | Inject traceparent context headers into `a2a_client.py` and extract them in `insurance_adk/agent.py`. | `kisan/a2a_client.py`, `kisan/insurance_adk/agent.py` | Prakhar | T2.1 | 2.0 | ~2 min | ~0 | ~0 | Trigger A2A call; verify unified trace ID appears in both logs. | Revert header code. |
| **T2.3** | Upgrade multilingual injection regexes and toxic word lists with agricultural term whitelisting. | `kisan/security.py` | Rishabh | G0 | 1.5 | < 30 s | ~0 | ~0 | Run attack tests in `evaluate.py`; verify 4/4 attacks blocked, "kill pests" allowed. | Revert `security.py`. |
| **T2.4** | Add numerical grounding validator in `security.py` verifying recommendation figures match evidence. | `kisan/security.py` | Rishabh | T2.3 | 2.0 | < 30 s | ~0 | ~0 | Pass report with fabricated loan number; verify flagged with review warning. | Revert validator. |
| **T2.5** | Add A2A client timeout & graceful degradation: if ADK is unreachable, return structured fallback string. | `kisan/a2a_client.py` | Rishabh | G0 | 1.0 | < 1 min | ~0 | ~0 | Kill ADK process; run `python -m kisan.cli run F001`; verify pipeline completes with fallback note. | Revert `a2a_client.py`. |

---

### Phase 3: No-Build React Dashboard & Static Integration
* **Goal:** Build the no-build React + Tailwind frontend (UMD + htm, no Node/npm), integrate with FastAPI `StaticFiles`, and enable interactive HITL reviews.
* **Entry Condition:** Phase 2 complete.
* **Exit Gate (G2):** Frontend accessible at `http://localhost:7860/`, displaying real-time agent execution, recommendation cards, and functioning review buttons. No `frontend/` folder, no `node_modules/`, no build step.

| Task ID | Description | Files to Touch | Owner | Dep | Est (h) | Runtime | RAM | Disk | Acceptance Test Command & Expected Output | Rollback Plan |
|---|---|---|---|---|---|---|---|---|---|---|
| **T3.1** | Download React 18 UMD, htm, and Tailwind play script with `curl` into `kisan/static/vendor/` at pinned versions. Create `kisan/static/index.html` shell with vendor script tags. | `kisan/static/vendor/`, `kisan/static/index.html` | Rishabh | None | 1.0 | < 2 min (curl) | ~0 | +300 KB | `test -f kisan/static/vendor/react.production.min.js && echo OK`. Open `index.html` in browser; React renders. | Delete `kisan/static/vendor/`. |
| **T3.2** | Build Farmer Profile Selector & Scenario Trigger component (in `index.html` using htm tagged templates). | `kisan/static/index.html` | Rishabh | T3.1 | 2.0 | N/A (no build) | ~0 | +5 KB | UI dropdown lists all 8 synthetic farmers with crop/state badges. | Revert `index.html`. |
| **T3.3** | Build Agent Activity Timeline displaying step-by-step progress and tool calls. | `kisan/static/index.html` | Rishabh | T3.1 | 2.5 | N/A (no build) | ~0 | +5 KB | UI renders animated timeline reflecting status events from backend. | Revert component code. |
| **T3.4** | Build Recommendation Cards, Hindi SMS preview, Tool Evidence Drawer, and cost metrics dashboard. | `kisan/static/index.html` | Rishabh | T3.1 | 2.0 | N/A (no build) | ~0 | +5 KB | UI renders priority-sorted advice with source agent badges and Devanagari text. | Revert component code. |
| **T3.5** | Implement HITL Review actions (Approve / Reject) calling `/api/runs/{id}/review`. Add "Demo Mode (Offline Replay)" toggle. | `kisan/static/index.html` | Rishabh | T3.1 | 1.5 | N/A (no build) | ~0 | +3 KB | Click "Approve"; verify DB updates `runs.status` to `REVIEW_APPROVE`. Toggle Demo Mode; verify offline runs. | Revert component code. |
| **T3.6** | Mount `kisan/static/` in `kisan/api.py` via `StaticFiles` at root URL `/`. Remove any references to `frontend/` folder. | `kisan/api.py` | Prakhar | T3.1-T3.5 | 1.0 | < 1 min | ~0 | ~0 | Open `http://localhost:7860/` in browser; dashboard loads directly from FastAPI with no build step. | Revert `api.py`. |

---

### Phase 4: Cloud Deployment (Hugging Face Spaces)
* **Goal:** Deploy to Hugging Face Spaces with public HTTPS URL and automated offline demo fallback. **No local Docker build** (FORBIDDEN per Section 0).
* **Entry Condition:** Phase 3 complete.
* **Exit Gate (G3):** Public Hugging Face Space URL active, responding to health checks and executing runs. Image size measured and recorded.

| Task ID | Description | Files to Touch | Owner | Dep | Est (h) | Runtime | RAM | Disk | Acceptance Test Command & Expected Output | Rollback Plan |
|---|---|---|---|---|---|---|---|---|---|---|
| **T4.1** | Test `start.sh` locally in WSL with `VENV_CREW=.venv-crew VENV_ADK=.venv-adk`. Verify ADK startup, health check, and FastAPI startup. No Docker build. | `start.sh` | Prakhar | G2 | 1.0 | ~30 s | +200 MB (transient) | ~0 | `VENV_CREW=.venv-crew VENV_ADK=.venv-adk bash start.sh` → `curl http://localhost:7860/health` returns `{"ok": true}`. | Fix script. |
| **T4.2** | Verify Dockerfile has HF README.md front matter (`title: Kisan Copilot`, `sdk: docker`, `app_port: 7860`), `.dockerignore` excludes `.venv-*`, `.git`, `logs/`, `__pycache__`. Verify `data/` and `logs/` are created and `chown`ed for the non-root user. Constraint files (`constraints-crew.txt`, `constraints-adk.txt`) are COPYed. | `Dockerfile`, `.dockerignore`, `README.md` | Prakhar | T4.1 | 1.0 | < 5 min | ~0 | ~0 | `grep 'app_port: 7860' README.md && grep '.venv' .dockerignore && grep 'chown.*data' Dockerfile && echo OK` | Revert files. |
| **T4.3** | Create Hugging Face Space (Docker SDK), configure repository secret keys (`GOOGLE_API_KEY`, `LANGFUSE_*`), and push code. Let HF build the image in the cloud. Record actual image size (replacing the old "< 1.8 GB" target). | Git remote | Prakhar | T4.2 | 1.5 | ~10 min (HF build) | ~0 locally | ~0 locally | Space builds and transitions to "Running" state on HF. Image size recorded in this roadmap. | Review build logs. |
| **T4.4** | Verify "Demo Mode (Offline Replay)" toggle works on deployed HF Space. Runs complete using rule engine with zero API quota. | `kisan/static/index.html`, `kisan/api.py` | Rishabh | T4.3 | 1.0 | < 2 min | ~0 | ~0 | Toggle Demo Mode in UI on HF Space; runs complete in < 2s using rule engine. | Revert toggle. |

---

### Phase 5: Live Evaluation, Documentation & Viva Preparation
* **Goal:** Execute live benchmark evaluation from laptop CLI, generate all report artifacts in Markdown (convert with pandoc), author presentation in Google Slides, record backup demo with Windows Game Bar, and prepare viva defenses.
* **Entry Condition:** Phase 4 deployed and verified.
* **Exit Gate (G4):** Complete project package ready: `eval_report.md` with live agentic data + offline baseline, project report `.docx`, Google Slides deck, demo video (Game Bar `.mp4`), and viva Q&A guide.

| Task ID | Description | Files to Touch | Owner | Dep | Est (h) | Runtime | RAM | Disk | Acceptance Test Command & Expected Output | Rollback Plan |
|---|---|---|---|---|---|---|---|---|---|---|
| **T5.1** | Upgrade `evaluate.py` to run full 8-farmer benchmark with both `TOOL_MODE` values (prefetch and agentic), measuring per-stage latency, LLM call counts, tokens, and cost. Include offline rule-based baseline as a comparison column. | `kisan/evaluate.py` | Prakhar | G3 | 2.0 | ~5 min (offline part) | +50 MB | +2 MB | `python -m kisan.cli eval --offline` outputs complete JSON & Markdown with baseline column. | Revert `evaluate.py`. |
| **T5.2** | Execute live evaluation: run 8 farmers from laptop CLI in both `TOOL_MODE` values, at least 2 repeats if quota allows, spread over several days. Collect real latency, token counts, and cost. | `logs/eval_report.md`, `logs/eval_results.json` | Prakhar | T5.1 | 3.0 | ~60 min (spread over days) | +200 MB | +1 MB | Inspect `logs/eval_report.md`; verify real measured latency, token counts, costs, and mode comparison documented. | Re-run with fewer repeats. |
| **T5.3** | Write Comprehensive Technical Final Report in Markdown (`docs/FINAL_REPORT.md`, 25–35 pages equivalent). Convert to `.docx` with `pandoc docs/FINAL_REPORT.md -o docs/FINAL_REPORT.docx`. Export PDF from Word or Google Docs. **Do NOT install LaTeX.** | `docs/FINAL_REPORT.md`, `docs/FINAL_REPORT.docx` | Both | T5.2 | 6.0 | pandoc < 5 s | ~0 | +5 MB | `pandoc docs/FINAL_REPORT.md -o docs/FINAL_REPORT.docx` produces clean .docx. All 11 requirements traced. | Edit document. |
| **T5.4** | Create slide outline in `docs/PRESENTATION.md`. Build 15-slide deck in **Google Slides** (free). Export PDF. **Do NOT install LaTeX or PowerPoint.** | `docs/PRESENTATION.md`, Google Slides | Rishabh | T5.2 | 3.0 | N/A (Google Slides) | ~0 | +1 MB | Google Slides deck has 15 slides covering problem, agent roles, A2A/MCP, evaluation, live screenshots. | Edit slides. |
| **T5.5** | Write 10-Minute Viva Demonstration Script in Markdown (`docs/DEMO_SCRIPT.md`) with contingency steps. Record backup demo video with **Windows Game Bar** (`Win+Alt+R`). **Do NOT install OBS.** | `docs/DEMO_SCRIPT.md`, `docs/demo_backup.mp4` | Rishabh | T5.4 | 1.5 | ~15 min (recording) | ~0 | +50 MB (video) | Demo script covers exact clicks and prompts. Video file plays in any browser. | Re-record. |
| **T5.6** | Compile Viva Q&A Guide in Markdown (`docs/VIVA_PREPARATION.md`) split by member responsibilities (40 questions + answers). Convert to `.docx` with pandoc. | `docs/VIVA_PREPARATION.md` | Both | T5.3 | 2.5 | pandoc < 5 s | ~0 | +500 KB | Conduct mock viva interview between team members. `pandoc docs/VIVA_PREPARATION.md -o docs/VIVA_PREPARATION.docx` succeeds. | Add missing answers. |

---

## 6. Requirement Traceability Matrix

| Req # | Requirement Description | Implementation Location | Verification Test Command | Concrete Evidence Artifact | Status Target |
|---|---|---|---|---|---|
| **1** | Context sharing & state updates between agents | `kisan/schemas.py:135` (`RunState`), `kisan/crew.py` checkpointed specialist execution | `python -m kisan.cli run F001` | `logs/<run_id>.jsonl` showing specialist inputs inheriting previous specialist outputs | **DONE** |
| **2** | Tool integration using MCP (≥ 2 tools) | `kisan/mcp_server.py:25-47` (`get_weather_forecast`, `get_mandi_prices`, `compute_kcc_metrics`) | `pytest tests/test_mcp.py` | FastMCP stdio tool invocation records in `logs/<run_id>.jsonl` (`kind: "tool_call"`) | **DONE** |
| **3** | Structured final output using Pydantic | `kisan/schemas.py:116` (`FinalReport`), `kisan/crew.py:_parse` | `pytest tests/test_schemas.py` | Validated `FinalReport` JSON in `data/kisan.db` (`runs.report_json`) | **DONE** |
| **4** | Suitable agentic design patterns | Routing (`crew.py`), Tool Use, Sequential State Machine, HITL (`security.py:68`) | `python -m kisan.cli run F002` | `Monitor` execution trail displaying step-by-step routing and fallback degradation | **DONE** |
| **5** | Task monitoring and logging using callbacks | `kisan/observability.py:82` (`Monitor.step_cb`, `Monitor.task_cb`) | `python -m kisan.cli run F001` | Granular timestamps, tool inputs/results, and task summaries in `logs/<run_id>.jsonl` | **DONE** |
| **6** | Agent-to-Agent (A2A) protocol communication | `kisan/a2a_client.py:32` (CrewAI client) ↔ `kisan/insurance_adk/agent.py:77` (ADK server) | `pytest tests/test_a2a.py` | `logs/a2a_client.jsonl` and `logs/adk_a2a.jsonl` matching transaction logs | **DONE** |
| **7** | Use both CrewAI and ADK; no other framework | CrewAI 1.15 in `.venv-crew`, Google ADK 1.39 in `.venv-adk` | `pip list` in both virtualenvs | Architecture diagram, source files, and Docker multi-venv structure | **DONE** |
| **8** | Guardrails (input, injection, toxicity, tool validation, HITL) | `kisan/security.py:36-91`, `kisan/insurance_adk/agent.py:37-60` | `pytest tests/test_security.py` | `evaluate.py` attack suite report showing 100% blocked attacks; `requires_human_review` flags | **DONE** |
| **9** | Observability and tracing for auditability | `kisan/observability.py:24` (Langfuse v3 + OpenInference), local JSONL audit trail | Execute 1 live run with Langfuse keys set | Interactive trace screenshot in Langfuse UI + local audit files in `logs/` (Langfuse optional at runtime) | **DONE** |
| **10** | End-to-end evaluation, cost & runtime estimates | `kisan/evaluate.py`, `kisan/config.py` | `python -m kisan.cli eval --live --farmers all` | `logs/eval_report.md` and `logs/eval_results.json` containing measured latency, token counts, and costs | **DONE** |
| **11** | Cloud deployment | `Dockerfile`, `start.sh`, Hugging Face Space | `curl https://<space-name>.hf.space/health` | Public HTTPS URL, live interactive no-build React dashboard, working demo | **DONE** |

---

## 7. Quota and Cost Management Plan

### 7.1 Free-Tier Quota Constraints (Google Gemini API)

> ⚠️ **UNVERIFIED:** The limits below are claimed but not sourced from an official pricing page. They may vary by model family and can change without notice. **Action:** Verify from the owner's Google AI Studio usage page and update. All values are environment-configurable.

| Limit Metric | Claimed Free Tier | Env Var | Safe Threshold (70%) | Kisan Copilot Design Value |
|---|---|---|---|---|
| **Requests Per Minute (RPM)** | 15 RPM (UNVERIFIED) | `GEMINI_RPM` | 10 RPM | **8 RPM** (enforced by `TokenBucketRateLimiter`) |
| **Tokens Per Minute (TPM)** | 1,000,000 TPM (UNVERIFIED) | `GEMINI_TPM` | 700,000 TPM | **~25,000 TPM** per full run |
| **Requests Per Day (RPD)** | 1,500 RPD (UNVERIFIED) | `GEMINI_RPD` | 1,000 RPD | **Max 40 live runs / day** during testing |

### 7.2 Daily Live-Run Allocation Schedule

```
Total Daily Budget: GEMINI_RPD (default 1,500 RPD — ⚠️ UNVERIFIED, check AI Studio)
├── Development Unit Tests (Mock LLM / Offline): 0 calls (Unlimited)
├── G0 Gate Live Smoke Testing (Phase 1): 5 runs × ~6 calls = 30 calls
├── Phase 2 A2A / Guardrail Live Verification: 5 runs × ~6 calls = 30 calls
├── Phase 4 Cloud Deployment Verification: 4 runs × ~6 calls = 24 calls
├── Phase 5 Final Benchmark Evaluation: 8 scenarios × 2 modes × 2 repeats (spread over 2–3 days):
│   ├── Day 1 (prefetch mode): 8 scenarios × 2 repeats × 6 calls = 96 calls
│   └── Day 2 (agentic mode): 8 scenarios × 2 repeats × 11 calls = 176 calls
├── Live Demo Buffer (Viva & Presentations): 10 runs × ~6 calls = 60 calls
└── Unallocated Safety Margin: > 1,000 calls remaining (stays well within daily limits)
```

### 7.3 Cost Estimation Model

> ⚠️ **UNVERIFIED:** The prices and token counts below are not sourced from official documentation or measured from real runs. All prices are environment-configurable. **Action:** Measure real token counts from the first successful run and verify prices from Google AI Studio.

* **Active Crew Model:** `gemini/gemini-3.5-flash`
  * Input: **\$`PRICE_IN_PER_M`** per 1M tokens (env-configurable; claimed \$1.50 — UNVERIFIED)
  * Output: **\$`PRICE_OUT_PER_M`** per 1M tokens (env-configurable; claimed \$9.00 — UNVERIFIED)
* **Active ADK Model:** `gemini-3.5-flash-lite`
  * Input: env-configurable (claimed \$0.30 — UNVERIFIED)
  * Output: env-configurable (claimed \$2.50 — UNVERIFIED)
* **Cost Formula (in `kisan/crew.py`):**
  $$\text{Est. Cost (USD)} = \left(\frac{\text{Prompt Tokens}}{10^6} \times \text{PRICE\_IN\_PER\_M}\right) + \left(\frac{\text{Completion Tokens}}{10^6} \times \text{PRICE\_OUT\_PER\_M}\right)$$
  *⚠️ The claim of "~3,200 prompt tokens and ~450 completion tokens" per run is UNVERIFIED — these figures were not measured from a real run. **Action:** Measure actual token counts from the first successful run (Task T1.10) and update this formula with real data. Actual cost is **0 INR on free tier** regardless of prices.*

---

## 8. Test Strategy

```
tests/
├── conftest.py               # Shared fixtures: synthetic farmer profiles, mock LLMs
├── test_security.py          # Input screening, PII redaction, toxic words, grounding
├── test_core_tools.py        # Weather, Mandi, KCC metrics, PMFBY calculation rules
├── test_mcp.py               # FastMCP tool server contracts, stdio transport validation
├── test_a2a.py               # A2A JSON-RPC client formatting, discovery, response extraction
├── test_rules.py             # Rule engine output structure, multi-lingual messages
├── test_pipeline_offline.py  # End-to-end pipeline execution with OfflineMockLLM
└── test_api.py               # FastAPI endpoints: /health, /recommend, /runs, /review
```

### 8.1 Testing Tiers & Gates
1. **Tier 1: Fast Unit Tests (Offline, < 5s):** Tests tools, schemas, security regexes, and database CRUD. Executed on every local edit.
2. **Tier 2: Subprocess & Contract Tests (Offline, < 15s):** Tests FastMCP stdio communication and A2A mock endpoints using `pytest-httpx`.
3. **Tier 3: Offline Pipeline Integration (< 10s):** Executes `run_pipeline(..., offline=True)` to verify state transitions and Pydantic validation across all 8 synthetic farmers.
4. **Tier 4: Live Gated Smoke Test (Online, 1 run):** Executed only when Gate G0 or G3 is reached. Gated by `ALLOW_LIVE_API=1`.

---

## 9. Cloud Deployment Plan (Hugging Face Spaces)

### 9.1 Container Layout & Dual Virtual Environments

```
/home/user/app/
├── /opt/venv-crew/           # Python 3.11 with crewai, fastapi, mcp, litellm
├── /opt/venv-adk/            # Python 3.11 with google-adk, a2a-sdk, uvicorn
├── kisan/                    # Core application code
│   └── static/               # No-build React dashboard (UMD + htm + Tailwind play)
│       ├── index.html         # Single-page application entry point
│       └── vendor/            # Pinned React 18, htm, Tailwind (downloaded with curl)
├── data/                     # Created and chown'd for non-root user
│   └── kisan.db              # SQLite database (seeded on start)
├── logs/                     # Created and chown'd for non-root user
├── constraints-crew.txt      # Pinned pip freeze for reproducible crew venv
├── constraints-adk.txt       # Pinned pip freeze for reproducible ADK venv
├── start.sh                  # Multi-process supervisor entrypoint (parameterised venv paths)
├── Dockerfile                # OCI container definition (built by HF, not locally)
├── .dockerignore             # Excludes .venv-*, .git, logs/, __pycache__
└── README.md                 # HF Spaces front matter (sdk: docker, app_port: 7860)
```

### 9.2 Dockerfile Blueprint

> **NOTE:** Do NOT build this image locally (FORBIDDEN per Section 0). Test `start.sh` locally in WSL with parameterised venv paths. Let Hugging Face build the image in the cloud. The actual image size will be **measured after the first HF cloud build** and recorded here (the old "< 1.8 GB" target was unrealistic given the two venvs total ~2.1 GB of packages).

**Required `README.md` front matter** (for Hugging Face Spaces):
```yaml
---
title: Kisan Copilot
emoji: 🌾
colorFrom: green
colorTo: yellow
sdk: docker
app_port: 7860
---
```

**`.dockerignore`:**
```
.venv-crew/
.venv-adk/
.venv/
.git/
logs/
data/kisan.db
__pycache__/
*.pyc
.env
```

```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && \
    rm -rf /var/lib/apt/lists/*

RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# Create two isolated virtual environments
RUN python3 -m venv /opt/venv-crew && \
    python3 -m venv /opt/venv-adk

# Install dependencies into respective venvs (with pinned constraints for reproducibility)
COPY requirements.txt requirements-adk.txt constraints-crew.txt constraints-adk.txt ./
RUN /opt/venv-crew/bin/pip install --no-cache-dir -r requirements.txt -c constraints-crew.txt
RUN /opt/venv-adk/bin/pip install --no-cache-dir -r requirements-adk.txt -c constraints-adk.txt

# Copy source code and static assets (no build step needed)
COPY --chown=user:user . .

# Create data/ and logs/ with write permissions for the non-root user
RUN mkdir -p data logs && chown -R user:user data logs

USER user
ENV PATH="/opt/venv-crew/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    VENV_CREW=/opt/venv-crew \
    VENV_ADK=/opt/venv-adk

EXPOSE 7860
CMD ["bash", "start.sh"]
```

> **Image size target:** MEASURED — to be filled after first HF cloud build (expected ~2.2–2.5 GB with two full venvs).

### 9.3 `start.sh` Startup & Readiness Script

```bash
#!/usr/bin/env bash
set -e

# Parameterised venv paths (defaults for Docker; override for local WSL testing)
VENV_CREW="${VENV_CREW:-/opt/venv-crew}"
VENV_ADK="${VENV_ADK:-/opt/venv-adk}"

echo "[START] Seeding synthetic farmer profiles into SQLite..."
"$VENV_CREW/bin/python" -m kisan.cli seed

echo "[START] Launching Google ADK PMFBY Insurance Agent on port 8001..."
# NOTE: No --reload flag (FORBIDDEN per Section 0)
"$VENV_ADK/bin/uvicorn" kisan.insurance_adk.agent:a2a_app --host 127.0.0.1 --port 8001 &
ADK_PID=$!

echo "[WAIT] Polling ADK A2A discovery endpoint..."
ADK_POLL_TIMEOUT="${ADK_POLL_TIMEOUT:-45}"
for i in $(seq 1 "$ADK_POLL_TIMEOUT"); do
    if curl -s http://127.0.0.1:8001/.well-known/agent-card.json > /dev/null 2>&1; then
        echo "[READY] ADK Insurance Agent is online (took ${i}s)."
        break
    fi
    sleep 1
done

echo "[START] Starting Kisan Copilot FastAPI Web App on port 7860..."
# NOTE: No --reload flag (FORBIDDEN per Section 0)
exec "$VENV_CREW/bin/uvicorn" kisan.api:app --host 0.0.0.0 --port 7860
```

---

## 10. Deliverables Checklist

| Deliverable Item | Description & Format | Responsible Owner | Target Phase | Status |
|---|---|---|---|---|
| **D-CODE** | Working multi-agent codebase (CrewAI + ADK + MCP + A2A) with `TOOL_MODE` switch | Prakhar & Rishabh | Phase 1 & 2 | **In Progress** |
| **D-UI** | No-build React + Tailwind dashboard (UMD + htm, no Node/npm) | Rishabh | Phase 3 | **Planned** |
| **D-DEP** | Live public deployment on Hugging Face Spaces (Port 7860), image built in cloud | Prakhar | Phase 4 | **Planned** |
| **D-EVAL** | Evaluation Report with **live agentic data** + offline baseline (`logs/eval_report.md` & `eval_results.json`) | Prakhar | Phase 5 | **Planned** |
| **D-REP** | Final Project Report — written in **Markdown**, converted to `.docx` with **pandoc** (no LaTeX) | Both (split by matrix) | Phase 5 | **Planned** |
| **D-PPT** | Project Presentation — 15 slides in **Google Slides** (free, no PowerPoint/LaTeX) | Rishabh | Phase 5 | **Planned** |
| **D-DEMO** | 10-Minute Demo Script (Markdown) & backup video recorded with **Windows Game Bar** (no OBS) | Rishabh | Phase 5 | **Planned** |
| **D-VIVA** | Viva Q&A Defense Dossier — written in Markdown, converted to `.docx` with pandoc (40 questions + answers) | Both (split by matrix) | Phase 5 | **Planned** |

---

## 11. Risk Register

| Risk ID | Risk Description | Severity | Likelihood | Early Warning Sign | Mitigation Strategy | Fallback Plan |
|---|---|---|---|---|---|---|
| **R1** | Gemini free-tier 429 quota exhaustion during live presentation | **HIGH** | Medium | HTTP 429 in log; sudden latency jump to 60s | Enforce 8 RPM limit; merge synthesis/comm calls to keep run under 7 calls | Toggle "Demo Mode (Offline Replay)" in UI; presentation continues smoothly with pre-computed runs |
| **R2** | Hugging Face Space sleeps after inactivity | **MEDIUM** | High | First page load takes 35s to spin up container | Run startup script with fast readiness checks; document cold-start behavior | Ping health endpoint 5 minutes prior to live presentation |
| **R3** | ADK agent fails to initialize due to port conflict | **MEDIUM** | Low | `Connection refused` in `a2a_client.jsonl` | `start.sh` kills any stale process on port 8001 before binding | A2A client gracefully logs error and orchestrator synthesizes report without insurance block |
| **R4** | AgMarkNet government mandi API endpoint down | **LOW** | High | API returns 502 or HTTP timeout in `core_tools.py` | `core_tools.py` catches `httpx.HTTPError` with 5s timeout | Synthetic mandi fallback automatically generates realistic prices clearly labeled as synthetic |
| **R5** | WSL2 out-of-memory during live agentic run | **MEDIUM** | Medium | WSL2 freezes; Python killed by OOM | `.wslconfig` caps WSL to 6 GB; close Chrome/Antigravity tabs before live runs (Section 0) | Fall back to offline rule-based mode; reduce `RUN_TIMEOUT` |

---

## 12. Scope Tiers and Cut-List

### MUST (Mandatory for 11 Requirements — Non-Negotiable)
* Sequential state machine in `crew.py` with RunState checkpointing (Req 1, 4).
* FastMCP stdio server exposing weather, mandi, and credit tools (Req 2).
* Structured output with Pydantic `FinalReport` (Req 3).
* Callback monitoring writing to `logs/<run_id>.jsonl` (Req 5).
* A2A client ↔ ADK agent communication over JSON-RPC (Req 6, 7).
* Guardrails: farmer ID validation, PII redaction, multilingual injection screening, HITL gate (Req 8).
* Observability: local JSONL audit trail + Langfuse integration (Req 9).
* Evaluation harness producing `eval_report.md` on 8 scenarios (Req 10).
* Dockerized deployment on Hugging Face Spaces (Req 11).

### SHOULD (Significantly Elevates Project Score & Viva Impression)
* Interactive **no-build** React + Tailwind CSS dashboard with live timeline (UMD + htm).
* Numerical grounding check verifying advice numbers against evidence.
* Automated "Demo Mode" toggle in UI for fail-safe presentations.
* Lightweight in-memory **pure-Python** BM25 retrieval (`rank_bm25` or hand-written) over official PMFBY/KCC guidelines (short excerpts with URLs, **no model downloads**).
* `TOOL_MODE=prefetch|agentic` switch for benchmark comparison.

### COULD (Nice to Have — First to Cut if Time Depletes)
* Live AgMarkNet mandi API key configuration.
* Devanagari voice synthesis via browser Web Speech API.
* Extended adversarial benchmark suite with 50+ synthetic attacks.

### Explicit Cut-List (If Deadline Pressures Arise)
1. **Cut #1:** External live AgMarkNet API fetching — rely 100% on the honest, labeled synthetic mandi generator.
2. **Cut #2:** BM25 RAG index over policy PDFs — rely on the existing structured domain rules in `core_tools.py`.
3. **Cut #3:** Custom Tailwind animations in React UI — fallback to standard clean Tailwind card components.
*Under no circumstances will any of the 11 minimum requirements be cut.*

---

## 13. Assumptions and Open Questions

1. **AI Studio Project Limits:** It is assumed that the active `GOOGLE_API_KEY` is associated with a standard Google AI Studio project with default free-tier quotas (15 RPM, 1,500 RPD).
2. **Hugging Face Account Access:** It is assumed that the team has an active Hugging Face account capable of creating a free CPU-basic Space (2 vCPU, 16 GB RAM, 50 GB disk).
3. **Primary Language for Demo:** It is assumed the live demo will focus on Hindi and English farmer communications as specified in the synopsis.
4. **Synthetic Data Sufficiency:** It is assumed that academic evaluators accept synthetic farmer profiles (F001–F008) for testing financial and insurance recommendations.
5. **Question for Owner 1:** Confirm the exact date of final project submission and viva defense.
6. **Question for Owner 2:** Does the university require a printed hard copy of the report, or is a digital PDF and GitHub link sufficient?

---

## 14. Day-by-Day Implementation Schedules

### Option A: 7-Day Sprint Schedule (Fastest Path to Complete Delivery)

* **Day 1: Hardware Setup, Version Control & Gate G0 (Engine Hardening)**
  * Morning (Prakhar): Configure `.wslconfig` (T0-HW.1), `git init` (T0.0), update `.gitignore` (T0.1), make pricing/limits env-configurable (T1.0, T1.1).
  * Afternoon (Prakhar): Refactor `crew.py` to sequential checkpointed state machine with `TOOL_MODE` (T1.3); remove `reasoning_effort` (T1.2); add hard timeout (T1.4); implement lazy `crewai` import (T1.7).
  * Evening (Both): Execute live run on F001; verify Gate G0 passed (`mode: "agentic"`, ≤ 7 calls in prefetch, terminal event logged).
* **Day 2: MCP, A2A & Guardrails Hardening**
  * Morning (Rishabh): Enforce stderr logging in `mcp_server.py`; inject `KISAN_DB` in subprocess env; enforce tool allow-list (D6).
  * Afternoon (Rishabh): Expand `security.py` with multilingual injection patterns and numerical grounding check.
  * Evening (Prakhar): Harden `a2a_client.py` with 15s timeout and graceful degradation; verify Gate G1.
* **Day 3: Observability & No-Build React Dashboard Core**
  * Morning (Prakhar): Install `langfuse` v3 in `.venv-crew`, ADK instrumentation in `.venv-adk` (T2.1); link traceparent headers across A2A boundary.
  * Afternoon (Rishabh): Download vendor assets (`curl`) into `kisan/static/vendor/` (T3.1); build Farmer Selector and Timeline in `index.html` (T3.2, T3.3).
  * Evening (Rishabh): Build Recommendation cards and HITL Review modal in `index.html` (T3.4, T3.5).
* **Day 4: Frontend Integration & Cloud Deployment**
  * Morning (Prakhar): Mount `kisan/static/` directory in `kisan/api.py` via `StaticFiles` (T3.6). Test locally without build step.
  * Afternoon (Prakhar): Test `start.sh` locally in WSL with parameterised venv paths (T4.1). Prepare Dockerfile with HF front matter, `.dockerignore`, `chown` (T4.2).
  * Evening (Prakhar): Push to Hugging Face Spaces; let HF build in cloud; verify Gate G3 (public HTTPS URL active).
* **Day 5: Live Evaluation Suite Execution**
  * Morning (Prakhar): Upgrade `kisan/evaluate.py` with `TOOL_MODE` support, latency, tokens, cost, and baseline column (T5.1).
  * Afternoon (Prakhar): Run live evaluation from laptop CLI across 8 scenarios in both modes (T5.2); generate `logs/eval_report.md`.
  * Evening (Both): Review benchmark metrics; verify all 11 requirements satisfied with proof.
* **Day 6: Documentation & Report Writing**
  * Morning (Prakhar): Author Sections 1–4 of Final Report in Markdown (`docs/FINAL_REPORT.md`).
  * Afternoon (Rishabh): Author Sections 5–8 of Final Report in Markdown.
  * Evening (Both): Consolidate and convert to `.docx` using `pandoc docs/FINAL_REPORT.md -o docs/FINAL_REPORT.docx`. Export PDF from Word/Google Docs (no LaTeX).
* **Day 7: Slides, Demo Script & Viva Rehearsal**
  * Morning (Rishabh): Create 15-slide presentation deck in **Google Slides** from `docs/PRESENTATION.md` (no LaTeX).
  * Afternoon (Both): Write Viva Q&A Guide (`docs/VIVA_PREPARATION.md`) and 10-minute demo script (`docs/DEMO_SCRIPT.md`).
  * Evening (Both): Conduct full mock viva interview; record backup demo video with **Windows Game Bar** (`Win+Alt+R`, no OBS).

---

### Option B: 14-Day Balanced Schedule (Recommended Standard Pace)

* **Days 1–2:** Phase 0 — Environment cleanup, `.wslconfig` (T0-HW.1), `git init` (T0.0), `.gitignore` (T0.1), dependency consolidation (T0.2), and parameterised `start.sh` (T0.5).
* **Days 3–4:** Phase 1 — State machine refactor in `crew.py`, `TOOL_MODE` switch (T1.3), lazy `crewai` import (T1.7), per-run timeout (T1.4), passing Gate G0.
* **Days 5–6:** Phase 2 — FastMCP stdio hardening, A2A timeout resilience, multilingual guardrails, numerical grounding, Gate G1.
* **Days 7–8:** Phase 3 — Langfuse v3 tracing integration, no-build React dashboard in `kisan/static/index.html` with vendor assets.
* **Days 9–10:** Phase 4 — Static frontend mounting in `api.py`, local `start.sh` testing in WSL, Hugging Face deployment, Gate G3.
* **Days 11–12:** Phase 5A — Live evaluation harness execution across all 8 scenarios from laptop CLI in both modes, generating `logs/eval_report.md`.
* **Days 13–14:** Phase 5B — Final project report (Markdown → pandoc `.docx`), presentation in Google Slides, demo script, Game Bar video, and mock viva defense.

---

### Option C: 21-Day Comprehensive Schedule (Deep Polish & Thorough Review)

* **Week 1 (Days 1–7): Backend Robustness, Architecture & Gate G0**
  * Complete Phase 0 and Phase 1.
  * Comprehensive unit test suite with 100% offline coverage (`pytest`).
  * Verify Gate G0 with multiple profile variants under quota limits.
  * Establish baseline measurements for token counts, latency, and costs.
* **Week 2 (Days 8–14): A2A, Observability, Guardrails & No-Build React Dashboard**
  * Complete Phase 2 and Phase 3.
  * Full Langfuse v3 tracing across CrewAI and ADK spans (optional at runtime).
  * Polished no-build React + Tailwind UI with live state animations, HITL review flow, and Demo Mode toggle.
  * Local `start.sh` testing with parameterised venv paths (no local Docker build).
* **Week 3 (Days 15–21): Cloud Deployment, Live Benchmarking & Academic Submission**
  * Deploy to Hugging Face Spaces (Phase 4, image built in cloud).
  * Run comprehensive live evaluations across 8 scenarios from laptop CLI in both `TOOL_MODE` values (Phase 5).
  * Author 30-page academic report in Markdown (convert with pandoc to `.docx`), 15-slide Google Slides deck, record backup demo with Windows Game Bar, and rehearse viva defenses.

---

## 15. Work-Order Format for Implementation

To enable a weaker coding model to execute tasks mechanically without making architectural decisions, every task implementation request MUST follow this standard work-order template:

```markdown
### WORK ORDER: [Task ID] — [Brief Title]

* **Files to Touch:** `path/to/file.py` (and only this file)
* **Pre-conditions:** [What must be true before this runs, e.g., git branch clean, venv active]
* **Target Changes:**
  - In `file.py`:
    - Replace [exact block of code or function signature]
    - With [exact replacement code]
* **Constraints Checked:**
  - [x] No forbidden libraries (Section 0)
  - [x] No local docker builds
  - [x] Pure Python, small, boring
  - [x] Uses `--no-cache-dir` if pip install
* **Acceptance Command:**
  ```bash
  [exact shell command to run]
  ```
* **Expected Output:**
  ```
  [exact stdout / exit code expected]
  ```
* **Impact Statement:**
  - Expected runtime: [e.g., < 30 s]
  - RAM impact: [e.g., +0 MB]
  - Disk impact: [e.g., +5 KB]
* **Rollback Command:**
  ```bash
  git checkout -- path/to/file.py
  ```
```

#### Example Work Order (T1.1 — Configurable Limits & Prices)

```markdown
### WORK ORDER: T1.1 — Environment-Configurable Gemini Limits and Prices

* **Files to Touch:** `kisan/config.py`
* **Pre-conditions:** Phase 0 complete; `.git` initialized.
* **Target Changes:**
  - Add `GEMINI_RPM = int(os.getenv("GEMINI_RPM", "15"))`
  - Add `GEMINI_RPD = int(os.getenv("GEMINI_RPD", "1500"))`
  - Add `GEMINI_TPM = int(os.getenv("GEMINI_TPM", "1000000"))`
  - Add `PRICE_IN_PER_M = float(os.getenv("PRICE_IN_PER_M", "1.50"))`
  - Add `PRICE_OUT_PER_M = float(os.getenv("PRICE_OUT_PER_M", "9.00"))`
  - Add `RUN_TIMEOUT = int(os.getenv("RUN_TIMEOUT", "300"))`
  - Add `MCP_TOOL_TIMEOUT = int(os.getenv("MCP_TOOL_TIMEOUT", "60"))`
  - Add `A2A_TIMEOUT = int(os.getenv("A2A_TIMEOUT", "30"))`
* **Constraints Checked:**
  - [x] Pure Python; no new dependencies; no forbidden libraries.
* **Acceptance Command:**
  ```bash
  RUN_TIMEOUT=120 PRICE_IN_PER_M=2.0 python3 -c "
  from kisan import config
  assert config.RUN_TIMEOUT == 120
  assert config.PRICE_IN_PER_M == 2.0
  assert config.GEMINI_RPM == 15
  print('CONFIG OK')
  "
  ```
* **Expected Output:**
  ```
  CONFIG OK
  ```
* **Impact Statement:**
  - Expected runtime: < 2 s
  - RAM impact: ~0
  - Disk impact: +500 B (in config.py)
* **Rollback Command:**
  ```bash
  git checkout -- kisan/config.py
  ```
```

---

*Roadmap generated and validated for Kisan Copilot on 2026-11-01. Last refined with hardware & cost constraints.*

