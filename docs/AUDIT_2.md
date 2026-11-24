# Kisan Copilot - System Audit 2
**Date:** 2026-11-24  
**Target:** Read-only audit of `~/kisan-copilot`  
**Execution Environment:** WSL2 Ubuntu 22.04 (Intel i3 10th gen, no GPU)

---

## STEP 1: Git Status & History

### Commands:
```bash
git log --oneline -15
git status --short
git remote -v
```

### Output:
```
99cdb69 tests: offline unit tests for guardrails, schemas, db, tools, rules
5813b3e config: per-model quota settings, validated env parsing, safe summary
0b76c00 dockerignore tweak
4947b49 add env template and dockerignore
8ab8949 baseline before roadmap

?? docs/AUDIT_2.md

origin	https://github.com/PrakharGupta04/kisan-copilot.git (fetch)
origin	https://github.com/PrakharGupta04/kisan-copilot.git (push)
```

---

## STEP 2: Tests & Coverage

### Commands:
```bash
.venv-crew/bin/python -m pytest 2>&1 | tail -25
ls tests/
grep -c "def test_" tests/*.py
```

### Output:
```
...............................................                          [100%]
47 passed in 3.52s

__pycache__
conftest.py
test_core_tools.py
test_db.py
test_rules.py
test_schemas.py
test_security.py

tests/conftest.py:0
tests/test_core_tools.py:13
tests/test_db.py:4
tests/test_rules.py:3
tests/test_schemas.py:4
tests/test_security.py:13
```
*Total test functions:* 37 across 5 test modules (47 assertions/parameterized cases passed).

---

## STEP 3: Repository Files Audit

### File Existence Check:
- `requirements.txt`: **MISSING**
- `requirements-crew.txt`: **EXISTS**
- `requirements-adk.txt`: **EXISTS**
- `requirements-obs.txt`: **EXISTS**
- `constraints-crew.txt`: **MISSING**
- `constraints-adk.txt`: **MISSING**
- `Dockerfile`: **EXISTS**
- `.dockerignore`: **EXISTS**
- `README.md`: **MISSING**
- `.env.example`: **EXISTS**
- `start.sh`: **EXISTS**
- `kisan/llm_gate.py`: **MISSING**
- `kisan/static/index.html`: **MISSING**
- `docs/`: **EXISTS**
- `tests/test_llm_gate.py`: **MISSING**
- `tests/test_mcp.py`: **MISSING**
- `tests/test_a2a.py`: **MISSING**
- `tests/test_api.py`: **MISSING**
- `tests/test_pipeline_offline.py`: **MISSING**

### `.gitignore` Content:
```
.venv/
.venv-crew/
.venv-adk/
.env
__pycache__/
*.pyc
.pytest_cache/
node_modules/
data/kisan.db
logs/
```

### `grep -n "sdk:\|app_port" README.md`:
```
README.md MISSING
```

---

## STEP 4: Code Facts (file:line)

### a) `kisan/crew.py`
- **reasoning_effort passed?** YES (`kisan/crew.py:90: llm = LLM(model=config.CREW_MODEL, temperature=0.1, max_tokens=3000, reasoning_effort="low")`)
- **TOOL_MODE read?** NOT FOUND
- **`from crewai` at module top?** YES (`kisan/crew.py:9: from crewai import LLM, Agent, Crew, Process, Task`, `kisan/crew.py:10: from crewai.mcp import MCPServerStdio`)
- **RUN_TIMEOUT used?** NOT FOUND
- **terminal log event on crash?** NOT FOUND (only logged on clean exit at `kisan/crew.py:215`; crashes terminate without writing `kind: "final"`)
- **_kickoff re-runs whole crew?** YES (`kisan/crew.py:70: def _kickoff(crew: Crew, mon: Monitor, attempts: int = 3):`, `kisan/crew.py:73: return crew.kickoff()`)
- **synthesis and communication separate tasks?** YES (`kisan/crew.py:154: synth = Task(...)`, `kisan/crew.py:164: comm = Task(...)`)
- **llm_gate imported?** NOT FOUND

### b) `kisan/a2a_client.py`
- **crewai import at top?** YES (`kisan/a2a_client.py:6: from crewai.tools import tool`)
- **A2A_TIMEOUT used?** NOT FOUND (hardcoded `timeout: float = 120.0` at `kisan/a2a_client.py:32`, `config.A2A_TIMEOUT` not imported or used)
- **any trace header?** NOT FOUND

### c) `kisan/mcp_server.py`
- **any print() to stdout?** NOT FOUND
- **logging to stderr?** NOT FOUND (uses default `FastMCP("kisan-tools")` without custom stderr handler)

### d) `kisan/core_tools.py`
- **mandi httpx timeout value?** `kisan/core_tools.py:88: timeout=12` (AgMarkNet mandi), `kisan/core_tools.py:53: timeout=10` (Open-Meteo weather)
- **any snapshot/cache-to-disk logic?** NOT FOUND (only in-memory `_CACHE = {}` at `kisan/core_tools.py:26`)

### e) `kisan/security.py`
- **Devanagari or Hinglish patterns?** NOT FOUND (only English regexes in `INJECTION_PATTERNS` and `TOXIC_WORDS` at `kisan/security.py:16-33`)
- **grounding validator?** NOT FOUND

### f) `kisan/api.py`
- **StaticFiles mounted?** NOT FOUND (returns raw inline HTML string at `kisan/api.py:54`)
- **demo/offline parameter?** NOT FOUND (`/api/recommend` at `kisan/api.py:34` takes only `farmer_id` and `question`)

### g) `kisan/observability.py`
- **"llm_requests" counter?** NOT FOUND in `kisan/observability.py` (initialized with `tool_calls` and `errors` at `kisan/observability.py:46`; set externally by `crew.py:178`)
- **env redaction?** NOT FOUND

### h) `start.sh`
- **ADK readiness polling?** NO (`start.sh:4: sleep 8`, fixed sleep, no curl polling loop)
- **VENV_CREW/VENV_ADK?** NOT FOUND (hardcoded `/opt/venv-adk/bin/uvicorn` and `/opt/venv-crew/bin/uvicorn`)
- **any --reload?** NOT FOUND (clean: no `--reload`)

### i) `evaluate.py`
- **live mode?** NOT FOUND (runs `main(offline=False)` without live flags or model gating)
- **TOOL_MODE comparison?** NOT FOUND
- **per-stage metrics?** NOT FOUND (only overall run latency `time.perf_counter() - t0` at `kisan/evaluate.py:35`)
- **offline baseline column?** NOT FOUND (no side-by-side offline vs live comparison table)

---

## STEP 5: Environment & Package Status

### `.venv-crew/bin/python -m kisan.config`:
```json
{
  "crew_model": "gemini/gemini-3.5-flash-lite",
  "adk_model": "gemini-3.5-flash-lite",
  "fallback_model": null,
  "tool_mode": "prefetch",
  "offline": false,
  "gemini_rpm": 12,
  "gemini_rpd": 450,
  "gemini_tpm": 200000,
  "max_rpm": 12,
  "price_in_per_m": 0.0,
  "price_out_per_m": 0.0,
  "run_timeout": 300,
  "mcp_tool_timeout": 60,
  "a2a_timeout": 90,
  "adk_poll_timeout": 45,
  "a2a_url": "http://localhost:8001",
  "a2a_port": 8001,
  "db_path": "/home/prakhar/kisan-copilot/data/kisan.db",
  "google_api_key_set": true,
  "gemini_api_key_set": true,
  "data_gov_api_key_set": true,
  "api_key_set": false,
  "langfuse_keys_set": false
}
```

### Key Packages in `.venv-crew`:
- `crewai`: 1.15.32
- `crewai-core`: 1.15.32
- `fastapi`: 0.162.0
- `json_repair`: 0.60.1
- `litellm`: 1.100.4
- `mcp`: 1.30.0
- `langfuse`: **NOT INSTALLED**
- `openinference-*`: **NOT INSTALLED**
- `rank_bm25`: **NOT INSTALLED**

### Key Packages in `.venv-adk`:
- `a2a-sdk`: 0.3.26
- `google-adk`: 1.39.1
- `litellm`: 1.65.0
- `openinference-*`: **NOT INSTALLED**

### System Resources:
```
Mem:  Total 5.7 GiB | Used 371 MiB | Free 4.5 GiB | Buff/Cache 840 MiB | Available 5.2 GiB
Swap: Total 2.0 GiB | Used 0 B | Free 2.0 GiB
Disk (/dev/sdd): Total 1007 GiB | Used 21 GiB | Available 935 GiB (3% used)
```

---

## STEP 6: Run Logs & Historical Performance

### Recent Run Logs:
1. `bd776819aa82.jsonl` | farmer_id: F002 | offline: True | mode: offline | latency_s: 13.41
2. `07156ad9f292.jsonl` | farmer_id: F002 | offline: True | mode: offline | latency_s: 13.45
3. `07a767c7fd0a.jsonl` | farmer_id: F002 | offline: False | mode: rule_based_fallback | latency_s: 388.79
4. `3b10eddfb574.jsonl` | farmer_id: F002 | offline: False | **NO FINAL EVENT** (crashed mid-run)
5. `9e3879e05954.jsonl` | farmer_id: F002 | offline: False | **NO FINAL EVENT** (crashed mid-run)
6. `48f485cba0db.jsonl` | farmer_id: F002 | offline: False | mode: rule_based_fallback | latency_s: 0.90
7. `a2a_client.jsonl` | A2A client log | **NO FINAL EVENT**
8. `adk_a2a.jsonl` | ADK service log | **NO FINAL EVENT**
9. `4cdba4ce7b50.jsonl` | farmer_id: F002 | offline: False | mode: rule_based_fallback | latency_s: 10.16
10. `4c0baf4f2398.jsonl` | farmer_id: F002 | offline: True | mode: offline | latency_s: 1.08

### Agentic Run Status:
- Any log has mode "agentic": **NO** (0 completed agentic runs in project history).
- Eval report files (`logs/eval_*`): **NONE**

---

## STEP 7: Requirements Traceability Matrix (Req 1 – 11)

| Req # | Requirement Description | Status | Concrete Evidence | Exact Gap to Completion |
|---|---|---|---|---|
| **1** | Context sharing & state updates between agents | **PARTIAL** | `kisan/schemas.py:135` (`RunState`), `kisan/crew.py:150` | No live agentic run has ever completed end-to-end; checkpointed sequential state machine saving specialist outputs into RunState is not implemented. |
| **2** | Tool integration using MCP (≥ 2 tools) | **PARTIAL** | `kisan/mcp_server.py:25-47` (3 tools registered) | Live agentic execution times out / crashes in subprocess; `tests/test_mcp.py` is MISSING; tool allow-list not enforced. |
| **3** | Structured final output using Pydantic | **PARTIAL** | `kisan/schemas.py:116` (`FinalReport`), `tests/test_schemas.py` PASS | Works reliably in offline/rule mode; has never successfully parsed live agentic output into `FinalReport`. |
| **4** | Suitable agentic design patterns | **PARTIAL** | Routing & fallback in `kisan/crew.py` | State machine fragile; `_kickoff` restarts entire crew on step failure; `TOOL_MODE=prefetch\|agentic` not implemented. |
| **5** | Task monitoring and logging using callbacks | **PARTIAL** | `kisan/observability.py:82` | Logs events to local JSONL, but crashes produce no terminal event (zombie logs); `llm_requests` counter missing in Monitor initialization. |
| **6** | Agent-to-Agent (A2A) protocol communication | **PARTIAL** | `kisan/a2a_client.py` ↔ `kisan/insurance_adk/agent.py` | A2A call works in isolation, but lacks trace header propagation and graceful fallback on timeout; `tests/test_a2a.py` is MISSING. |
| **7** | Use both CrewAI and ADK; no other framework | **PARTIAL** | CrewAI in `.venv-crew`, ADK in `.venv-adk` | Both environments exist, but combined end-to-end agentic workflow has never run to completion. |
| **8** | Guardrails (input, injection, toxicity, tool validation, HITL) | **PARTIAL** | `kisan/security.py`, `tests/test_security.py` PASS | Basic English regex and HITL flags pass; Devanagari/Hinglish patterns and numerical grounding validator are MISSING. |
| **9** | Observability and tracing for auditability | **PARTIAL** | Local JSONL logging active | `langfuse` v3 and OpenInference are NOT installed in either venv; traceparent headers not implemented. |
| **10** | End-to-end evaluation, cost & runtime estimates | **PARTIAL** | `kisan/evaluate.py` | Only tests offline mode; no live agentic benchmark; no TOOL_MODE comparison; no per-stage breakdown; no eval report artifacts. |
| **11** | Cloud deployment | **MISSING** | `Dockerfile`, `start.sh` | Dockerfile references missing `requirements.txt`; README.md front-matter MISSING; no Hugging Face Space deployed. |

---

## STEP 8: Roadmap Task Status Tracking

| Task ID | Roadmap Description | Status | One-Line Evidence |
|---|---|---|---|
| **T0.0** | Git init and baseline commit | **DONE** | Commit `8ab8949` exists on branch `main`. |
| **T0.1** | `.gitignore` exclusions | **DONE** | `.gitignore` contains `.venv*`, `.env`, `logs/`, `data/kisan.db`. |
| **T0.2** | Unified `requirements.txt` & constraints | **NOT DONE** | `requirements.txt` and `constraints-*.txt` are MISSING. |
| **T0.3** | `.env.example` with quota defaults | **PARTIAL** | `.env.example` updated with safe quota defaults, but key rotation docs minimal. |
| **T0.4** | Fix Dockerfile & HF front-matter | **NOT DONE** | `Dockerfile` still references missing file; `README.md` is MISSING. |
| **T0.5** | Upgrade `start.sh` with readiness polling | **NOT DONE** | `start.sh` still uses fixed `sleep 8` and hardcoded venv paths. |
| **T1.0** | Verify Google AI Studio free-tier quotas | **DONE** | `config.py` updated with validated env parsing and safe summary. |
| **T1.1** | Configurable Gemini limits and prices | **DONE** | `config.py` exports `GEMINI_RPM`, `PRICE_IN_PER_M`, `RUN_TIMEOUT`, etc. |
| **T1.2** | Remove/gate `reasoning_effort="low"` | **NOT DONE** | `kisan/crew.py:90` hardcodes `reasoning_effort="low"`. |
| **T1.3** | Checkpointed state machine & TOOL_MODE | **NOT DONE** | `kisan/crew.py` does not read `TOOL_MODE` or isolate specialist execution. |
| **T1.4** | Per-run hard timeout & terminal log event | **NOT DONE** | `kisan/crew.py` lacks timeout wrapper; crashes produce no terminal event. |
| **T1.5** | Merge Synthesis and Communication | **NOT DONE** | `kisan/crew.py:154,164` still defines two separate LLM tasks. |
| **T1.6** | 429 error body parsing & RPD fail-fast | **NOT DONE** | `kisan/crew.py` only does string match on error message; no body parsing. |
| **T1.7** | Lazy import of `crewai` | **NOT DONE** | `crewai` imported eagerly at top of `kisan/crew.py:9` and `a2a_client.py:6`. |
| **T1.8** | MCP server logging strictly to stderr | **NOT DONE** | `kisan/mcp_server.py` has no explicit stderr logging configuration. |
| **T1.9** | Inject `KISAN_DB` in MCP env | **NOT DONE** | `kisan/crew.py:_mcp` does not explicitly set `KISAN_DB` in subprocess env. |
| **T1.10** | First live agentic run completion (Gate G0) | **NOT DONE** | 0 live agentic runs completed in `logs/`. |
| **T2.1** | Install Langfuse v3 & OpenInference | **NOT DONE** | `langfuse` not present in `pip list` in either venv. |
| **T2.2** | Inject traceparent headers across A2A | **NOT DONE** | No trace headers in `kisan/a2a_client.py` or `insurance_adk/agent.py`. |
| **T2.3** | Multilingual injection patterns & whitelist | **NOT DONE** | `kisan/security.py` has only English patterns. |
| **T2.4** | Numerical grounding validator | **NOT DONE** | No numerical grounding logic in `kisan/security.py`. |
| **T2.5** | A2A client timeout & graceful degradation | **NOT DONE** | `kisan/a2a_client.py` uses hardcoded 120s timeout and raises exceptions. |
| **T3.1–T3.6** | No-build React dashboard in `kisan/static` | **NOT DONE** | `kisan/static/index.html` is MISSING; StaticFiles not mounted in `api.py`. |
| **T4.1–T4.4** | Container deployment to HF Spaces | **NOT DONE** | Cloud space not created or deployed. |

---

## STEP 9: Top 10 Live Demo Risks (Most Severe First)

1. **`kisan/crew.py:70-73` (`_kickoff` whole-crew retry):** On any specialist or tool error, `_kickoff` retries the entire multi-agent crew from scratch, re-executing completed specialists, multiplying token usage, and instantly triggering 429 quota exhaustion.
2. **`kisan/crew.py:90` (`reasoning_effort="low"` parameter):** Forces reasoning token generation on Gemini 3+ models, multiplying output token latency (110–140s per turn) and hitting TPM limits; fails on providers that reject the parameter.
3. **`logs/` (0 completed agentic runs):** Project history contains zero successful agentic runs. Every non-offline run either crashed mid-pipeline or degraded to rule-based fallback after 429 errors.
4. **`start.sh:4` (fixed `sleep 8` instead of readiness polling):** Hardcodes `sleep 8` for ADK startup; if ADK requires > 8s on the slow i3 CPU, FastAPI launches before port 8001 is ready, breaking A2A discovery.
5. **`kisan/crew.py` (missing per-run timeout & terminal event on crash):** Runs that crash (e.g., `3b10eddfb574`, `9e3879e05954`) leave no final log event, preventing state recovery and hanging consumers waiting for terminal output.
6. **`kisan/a2a_client.py:32` (unbounded A2A timeout & no graceful fallback):** Uses hardcoded 120s timeout (ignoring `config.A2A_TIMEOUT=90`) and raises unhandled exceptions instead of returning a degraded domain fallback.
7. **`Dockerfile:7` (broken container build):** References `requirements.txt` which does not exist in the repository root, guaranteeing `docker build` fails immediately.
8. **`README.md` (missing Hugging Face front-matter):** Repository root lacks `README.md` with `sdk: docker` and `app_port: 7860`, which prevents Hugging Face Spaces from configuring the container port.
9. **`kisan/api.py:54` (missing web dashboard):** `kisan/static/index.html` is missing and `StaticFiles` is not mounted, leaving the user interface as an unstyled raw HTML string.
10. **`kisan/crew.py:9` & `kisan/a2a_client.py:6` (eager `crewai` imports):** Module-level imports force loading of the entire heavy CrewAI stack during offline CLI commands and tests, adding unnecessary latency and RAM pressure.

---

## Final Verification
```bash
git status --short
```
Output:
```
?? docs/AUDIT_2.md
```
Only `docs/AUDIT_2.md` was created. No other files were modified.
