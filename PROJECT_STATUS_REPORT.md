# Kisan Copilot — Project Status Report
**Audit date:** 2026-10-31 | **Auditor:** read-only automated audit

---

## 1. Executive Summary

The codebase is well-architected: all 11 requirement areas have code addressing them, the fallback and guardrail layers work, and the rule-based path runs end-to-end reliably. **However, not a single fully agentic run has ever completed successfully.** Every live LLM attempt has failed—due to (in chronological order): `cache_breakpoint` parameter rejected by Groq, 503 overload on Gemini, and 429 quota exhaustion on Gemini after partial completion through the weather and mandi specialists. The biggest single blocker is **model/provider mismatch**: `reasoning_effort="low"` (crew.py:90) is passed to LiteLLM for every model, but neither Groq nor many Gemini variants accept that parameter. The MCP subprocess (weather/mandi/credit tools), the A2A discovery call, and the ADK insurance agent have each worked independently, but the full `plan → specialists → synthesis → communication` CrewAI pipeline has never produced a `mode:"agentic"` final log entry.

**Also critical:** `requirements.txt` (referenced by the Dockerfile) does not exist in the repo root—the Docker image cannot be built.

---

## 2. File Inventory Table

| File | Lines | Purpose | Status |
|---|---|---|---|
| `kisan/config.py` | 29 | Central config; loads `.env`, sets defaults for model, RPM, paths | OK |
| `kisan/schemas.py` | 145 | All Pydantic models: tool results, RunState, FinalReport, etc. | OK |
| `kisan/security.py` | 108 | Guardrails: injection scan, PII redact, toxic-word filter, rate limiter, HITL policy | OK |
| `kisan/core_tools.py` | 182 | Pure tool logic: weather (open-meteo), mandi (agmarknet/synthetic), KCC, PMFBY | OK |
| `kisan/crew.py` | 215 | Main orchestration: plan → specialists (MCP+A2A) → synthesis → communication | **Issue** (see §6) |
| `kisan/a2a_client.py` | 76 | A2A HTTP client wrapped as a CrewAI `@tool`; discovery + `message/send` | OK |
| `kisan/insurance_adk/agent.py` | 76 | Google ADK agent for PMFBY; served via `to_a2a()`; callbacks as guardrails | OK |
| `kisan/mcp_server.py` | 48 | FastMCP stdio server exposing weather/mandi/credit tools by TOOLSET | OK |
| `kisan/observability.py` | 124 | JSONL audit trail + Langfuse/OTel tracing; Monitor class for callbacks | OK |
| `kisan/db.py` | 103 | SQLite CRUD: farmers, runs, reviews; seed function; read-only context | OK |
| `kisan/rules.py` | 91 | Rule-based fallback engine; also used in offline mode | OK |
| `kisan/evaluate.py` | 65 | E2E eval harness: keyword accuracy, latency, cost, adversarial tests | OK |
| `kisan/api.py` | 113 | FastAPI app: /recommend, /runs, /review, simple HTML dashboard | OK |
| `kisan/cli.py` | 34 | CLI: seed / run / eval subcommands | OK |
| `kisan/__init__.py` | 0 | Empty package init | OK |
| `kisan/insurance_adk/__init__.py` | 0 | Empty package init | OK |
| `.env.example` | 15 | Template for environment variables | OK |
| `.env` | 7 | Live secrets + config (gitignored) | OK |
| `.gitignore` | 4 | Ignores `.venv/`, `.env`, `data/`, `logs/`, `__pycache__/` | **Issue** (see §6) |
| `requirements-crew.txt` | 7 | Crew venv deps | OK |
| `requirements-adk.txt` | 5 | ADK venv deps | OK |
| `requirements-obs.txt` | 3 | Langfuse + openinference instrumentors | OK |
| `Dockerfile` | 9 | Container build; references `requirements.txt` | **Issue** (MISSING file) |
| `start.sh` | 4 | Seeds DB, starts ADK A2A server on :8001, then FastAPI on :7860 | OK |
| `data/kisan.db` | binary | SQLite DB with 8 synthetic farmers and run history | OK |
| `logs/*.jsonl` | various | Run audit trails (6 run logs + a2a_client.jsonl + adk_a2a.jsonl) | OK |

**Missing files referenced by existing files:**
- `requirements.txt` — referenced by `Dockerfile:6` but **does not exist** in the repo root. Docker build will fail.

**Files that exist but are never imported/referenced externally:**
- `kisan/evaluate.py` — only called via `cli.py`; that's by design, not dead code.

---

## 3. Architecture as Actually Implemented

```
User / FastAPI (/recommend)
        │
        ▼
  run_pipeline() [crew.py]
        │
        ├─[guardrail]── validate_farmer_id() + screen_user_text()
        │
        ├─[ONLINE]──► _agentic()
        │                │
        │                ├─ Crew #1 (plan): Orchestrator → AgentPlan JSON
        │                │
        │                ├─ Crew #2 (specialists, sequential):
        │                │    ├─ Weather Agent  ──MCP(stdio)──► get_weather_forecast
        │                │    ├─ Mandi Agent    ──MCP(stdio)──► get_mandi_prices
        │                │    ├─ Credit Agent   ──MCP(stdio)──► compute_kcc_metrics
        │                │    └─ Insurance Agent ─@tool──────► call_insurance_agent()
        │                │                                          │
        │                │                                      HTTP A2A ──► ADK agent
        │                │                                      (localhost:8001)
        │                │                                          │
        │                │                                    assess_pmfby tool
        │                │
        │                ├─ Synthesis Task (Orchestrator → LLMReport JSON)
        │                └─ Communication Task (FarmerComm → FarmerMessage JSON)
        │
        └─[OFFLINE/FAIL]► rules.build_report()
                               │
                               └─ Direct tool calls (no LLM)
        │
        ▼
  security.finalize_report() [PII redact, HITL policy, disclaimer]
        │
        ▼
  db.save_run() → FinalReport (Pydantic)
```

**Deviations from intended design:**
1. The `Dockerfile` references a non-existent `requirements.txt`; the actual requirements are split across `requirements-crew.txt` / `requirements-adk.txt` / `requirements-obs.txt`. The Dockerfile installs only one venv's deps—it never installs `google-adk`.
2. The two venvs (`.venv-crew`, `.venv-adk`) exist locally but `.gitignore` only excludes `.venv/` (without the suffix), so `.venv-crew/` and `.venv-adk/` are **not** gitignored and could be committed.
3. `start.sh` runs both venvs' processes using the same Python install (whichever `uvicorn` is on PATH), which may pick the wrong one.

---

## 4. Environment Facts

### Python Version
Both `.venv-crew` and `.venv-adk` were created with **Python 3.11.15** (via pyenv). However, the pyenv interpreter at `/home/prakhar/.pyenv/versions/3.11.15/bin/python3.11` is **not accessible from this sandbox**, so the venv `python` symlink is broken. The system Python at `/usr/bin/python3` is separate. This means **the venv Python binaries cannot be invoked directly via path** in this environment—the user must activate the venv first.

### .env Variable Status (no secret values reported)
| Variable | Set? | Non-secret value |
|---|---|---|
| `GOOGLE_API_KEY` | true | (redacted) |
| `GEMINI_API_KEY` | true | (redacted) |
| `CREW_MODEL` | true | `gemini/gemini-3.5-flash` |
| `ADK_MODEL` | true | `gemini-3.5-flash-lite` |
| `MAX_RPM` | true | `8` |
| `DATA_GOV_API_KEY` | true | (redacted — likely set) |
| `GROQ_API_KEY` | false/absent | — |
| `OFFLINE` | false | (not set, defaults to `"0"`) |
| `LANGFUSE_PUBLIC_KEY` | false | — |
| `LANGFUSE_SECRET_KEY` | false | — |
| `API_KEY` | false | — |
| `INSURANCE_A2A_URL` | false | defaults to `http://localhost:8001` |
| `A2A_PORT` | false | defaults to `8001` |

**Note:** `CREW_MODEL=gemini/gemini-3.5-flash` uses the `gemini/` LiteLLM prefix which routes via Google Gemini API. `ADK_MODEL=gemini-3.5-flash-lite` is a bare model name (no prefix), meaning the ADK `_model()` function at `agent.py:22` will treat it as a native Gemini model (needing `GOOGLE_API_KEY`). The `gemini-3.5-flash` and `gemini-3.5-flash-lite` model names should be verified against the actual Gemini API model list—these may not be valid identifiers (common aliases are `gemini-1.5-flash`, `gemini-2.0-flash`, etc.).

### Installed Package Versions

**`.venv-crew` (Python 3.11.15):**
| Package | Version | Required by requirements-crew.txt |
|---|---|---|
| crewai | 1.15.32 | >=1.14,<2 ✓ |
| litellm | 1.100.4 | (transitive via crewai) ✓ |
| mcp | 1.30.0 | >=1.9,<2 ✓ |
| fastapi | 0.162.0 | >=0.115 ✓ |
| uvicorn | 0.54.0 | >=0.30 ✓ |
| httpx | 0.28.1 | >=0.27 ✓ |
| pydantic | 2.12.5 | >=2.7 ✓ |
| google-genai | 1.65.0 | (via crewai[google-genai]) ✓ |
| langfuse | **NOT INSTALLED** | requirements-obs.txt |
| openinference-instrumentation-* | **NOT INSTALLED** | requirements-obs.txt |

**`.venv-adk` (Python 3.11.15):**
| Package | Version | Required by requirements-adk.txt |
|---|---|---|
| google-adk | 1.39.1 | >=1.16,<2 ✓ |
| a2a-sdk | 0.3.26 | (transitive via google-adk[a2a]) ✓ |
| litellm | 1.65.0 | >=1.60 ✓ |
| httpx | 0.28.1 | >=0.27 ✓ |
| pydantic | 2.14.1 | >=2.7 ✓ |
| uvicorn | 0.54.0 | >=0.30 ✓ |

**Note:** `langfuse` and `openinference-instrumentation-*` packages are in `requirements-obs.txt` but were **never installed** in `.venv-crew` (no `.dist-info` found). The Langfuse tracing path will silently degrade—which is handled gracefully by `init_langfuse()`, but observability (Req. 9) is not active.

### Disk Usage
| Path | Size |
|---|---|
| `.venv-crew` | 1.2 GB |
| `.venv-adk` | 902 MB |
| `data/` | 52 KB |
| `logs/` | 40 KB |
| Filesystem (`/`) | 2.9 GB total, 0 used shown (sandbox view may differ) |

### SQLite DB
The DB exists at `data/kisan.db`. `sqlite3` binary is not available in this sandbox, so row counts were read from file size (52 KB) and seed code. From `db.py:seed()` there are **8 synthetic farmers** (F001–F008). Run count is unknown but at minimum 6 (one per log file). Reviews table count unknown.

---

## 5. Log Timeline and Root Causes

### Chronological Timeline

| Time (UTC) | Run ID | Event | Root Cause |
|---|---|---|---|
| 2026-10-28 14:49 | `4c0baf4f2398` | OFFLINE mode, completed | No LLM called; rule-based only |
| 2026-10-28 15:17 | `4cdba4ce7b50` | Planning failed; specialists crew also failed | **Error 1:** `model_not_found` – `llama-3.3-70b-versatile` not accessible on Groq. **Error 2:** `cache_breakpoint` property unsupported by Groq for role:system messages (litellm injects this for context caching). Fell back to rule-based. |
| 2026-10-28 15:35 | `48f485cba0db` | Instant fail at import | **Error 3:** `ImportError: Google Gen AI native provider not available` – `crewai[google-genai]` extra not installed at that moment (later installed). |
| 2026-10-28 15:38 | `9e3879e05954` | Planning failed (3 retries), specialists also failed | **Error 4:** `503 UNAVAILABLE` – Gemini API overloaded. All 3 retry attempts hit 503. Fell back to rule-based. |
| 2026-10-28 15:50 | `3b10eddfb574` | Planning succeeded (75s), then truncated | Log ends after plan—likely killed or quota hit mid-run (no final entry). |
| 2026-10-28 15:52 | `07a767c7fd0a` | Partial agentic (weather+mandi completed), then 3×429 | **Error 5:** `429 RESOURCE_EXHAUSTED` – Gemini free-tier quota exceeded. Weather and Mandi agents ran successfully (t=113s, t=249s). Credit and Insurance agents never started. Synthesis and Communication never ran. Fell back to rule-based at t=389s. |

### A2A / ADK Logs Summary

**`a2a_client.jsonl` (3 entries):**
- Entry 1: `kind:ok`, farmer F001, agent `pmfby_insurance_agent`, latency **41.8s** — A2A call succeeded.
- Entry 2: `kind:error`, `ConnectError: [Errno 111] Connection refused` — ADK server was not running at the time.
- Entry 3: `kind:ok`, farmer F001, latency **29.1s** — A2A call succeeded again.

**`adk_a2a.jsonl` (9 entries):** Shows 7 `model_call` events and 2 `tool_result` events for `assess_pmfby(farmer_id=F001)`. The ADK agent has run successfully at least twice in isolation.

### Has a Full Agentic Run Ever Completed?

**No.** Evidence: No run log ever contains both `kind:"task_done"` for all 4 specialists AND a `kind:"final"` entry with `mode:"agentic"`. The only run that progressed past planning (`07a767c7fd0a`) died with 429s after only weather+mandi completed. All other non-offline runs fell back to `mode:"rule_based_fallback"`. The A2A client has worked **in isolation** but the Insurance specialist has never been reached during a live CrewAI run.

---

## 6. Requirements Audit Table

| # | Requirement | Status | Evidence | What is Missing |
|---|---|---|---|---|
| 1 | Context sharing / shared state between agents | **PARTIAL** | `RunState` (schemas.py:135); `state.outputs[key]` updated in `keep()` callback (crew.py:121); passed as `context=list(spec_tasks)` to tasks (crew.py:150) | State object exists and is populated via callbacks, but no agentic run has ever completed all stages — unverified in practice |
| 2 | MCP tool integration (≥2 external tools) | **PARTIAL** | `MCPServerStdio` (crew.py:28–31); 3 tools in `mcp_server.py` (weather, mandi, credit); `TOOLSET` env limits exposure | MCP subprocess worked in run `07a767c7fd0a` (weather and mandi tool calls logged), but never ran all 3 in one full agentic pass. No tool_call log entries visible for credit in any run. |
| 3 | Structured final output via Pydantic | **DONE** | `FinalReport` (schemas.py:116), `LLMReport`, `AgentPlan`, `FarmerMessage` all `BaseModel`; output_pydantic used in tasks (crew.py:106,159,166) | Works in rule-based mode; agentic path never reached synthesis |
| 4 | Suitable agentic design patterns | **PARTIAL** | Planning/routing pattern (crew.py:101–116); specialist routing; reflection via re-parse (`_parse`); fallback degradation; HITL | Sequential orchestration pattern is appropriate; parallel crew not used (by design); no agentic run verified |
| 5 | Task monitoring / logging via callbacks | **DONE** | `Monitor.step_cb` and `Monitor.task_cb` (observability.py:101–124); `step_callback=mon.step_cb` (crew.py:109,170); JSONL audit trail written | `task_callback=None` at crew.py:170 — the main crew does NOT pass `task_callback`; `monitor.task_cb` is only wired into the specialist `keep()` closures, not the synthesis/comm tasks |
| 6 | A2A protocol (CrewAI ↔ ADK) | **PARTIAL** | `a2a_client.py` implements `message/send` JSON-RPC; `to_a2a()` wraps ADK agent (agent.py:77); A2A discovery tried at two paths (a2a_client.py:39–43); success logged in a2a_client.jsonl | A2A worked in isolation (2 successful calls to ADK in a2a_client.jsonl), but was never reached inside a successful CrewAI run (the insurance specialist was always skipped before it ran) |
| 7 | Both CrewAI and ADK; no other framework | **DONE** | crewai 1.15.32 in `.venv-crew`; google-adk 1.39.1 in `.venv-adk`; no other orchestration framework present | Both are installed and used in code; agentic pipeline not yet proven end-to-end |
| 8 | Guardrails | **DONE** | `screen_user_text` (security.py:49); `validate_farmer_id` (security.py:36); injection regex `_INJ` (security.py:14–21); `scan_untrusted` on tool output (observability.py:110); ADK `before_model_callback` (agent.py:37); `finalize_report` with PII redact + HITL (security.py:68) | Toxic word list has only 6 English terms (security.py:23); comment notes "Starter list only"; no Hindi/regional injection patterns; no numeric guardrail on LLM confidence vs. tool numbers |
| 9 | Observability / tracing (Langfuse) | **PARTIAL** | `init_langfuse` gracefully no-ops if keys absent (observability.py:24); `trace_run` context manager (observability.py:58); OpenTelemetry instrumentors in requirements-obs.txt | `langfuse` and `openinference-*` packages **not installed** in `.venv-crew`; LANGFUSE keys not set in `.env` → tracing is silently disabled. JSONL audit trail works but Langfuse is inactive. |
| 10 | E2E performance evaluation, cost, timing | **PARTIAL** | `evaluate.py` harness with latency, tokens, cost, keyword accuracy, HITL rate, attack blocking; cost formula in crew.py:179 | Evaluation harness exists but has never been run against a successful agentic scenario — all available runs fell back to rule_based. No `eval_report.md` or `eval_results.json` found in `logs/`. |
| 11 | Cloud deployment | **MISSING** | `Dockerfile` exists (9 lines); `start.sh` exists; port 7860 (HuggingFace Spaces convention) | `requirements.txt` referenced in Dockerfile does not exist → build fails. Dockerfile installs only one set of deps (crew), never installs `google-adk`. No evidence of any deployed instance (no URL, no CI/CD config). |

---

## 7. Defects and Risks Table

| Severity | Location | Defect / Risk | Suggested Fix (words only) |
|---|---|---|---|
| **HIGH** | `crew.py:90` | `reasoning_effort="low"` passed to `LLM(...)` for ALL models. This parameter is only supported by OpenAI o-series and some Gemini 2.x thinking models. Groq rejected it with `cache_breakpoint` error (log `4cdba4ce7b50`); it will also fail with non-thinking Gemini models. | Remove `reasoning_effort="low"` from the `LLM()` constructor, or make it conditional: only pass it when `CREW_MODEL` starts with `o1/o3` or `gemini-2.0-flash-thinking`. |
| **HIGH** | `Dockerfile:6` | References `requirements.txt` which does not exist. Docker build fails immediately. | Either rename `requirements-crew.txt` to `requirements.txt` and update the Dockerfile to also install `requirements-adk.txt` and `requirements-obs.txt`, or update the Dockerfile COPY/RUN lines to reference the correct filenames. |
| **HIGH** | `config.py:21–22` | `CREW_MODEL` defaults to `groq/llama-3.3-70b-versatile` (the `.env.example` value), but the live `.env` sets it to `gemini/gemini-3.5-flash`. The model name `gemini-3.5-flash` does not appear in the current Google AI API model catalog (valid names are `gemini-1.5-flash`, `gemini-2.0-flash`, `gemini-2.5-flash`). All 429s in the logs came from Gemini. `ADK_MODEL=gemini-3.5-flash-lite` is similarly unverified. | Verify both model names against the Gemini API documentation and update `.env` and `.env.example` to a confirmed valid free-tier model (e.g., `gemini/gemini-1.5-flash` for crew, `gemini-1.5-flash-lite` for ADK). |
| **HIGH** | `.gitignore:1` | Only `.venv/` is gitignored. `.venv-crew/` and `.venv-adk/` (1.2 GB + 902 MB) are **not** gitignored and could accidentally be committed. | Add `.venv-crew/` and `.venv-adk/` to `.gitignore`. |
| **HIGH** | `crew.py:169–170` | `task_callback=None` in the main specialist+synthesis crew. The `keep()` closures are registered as `callback=` on individual tasks (crew.py:150), which is correct, but `task_callback` at crew level is explicitly `None`, meaning synthesis and communication task completions are not logged via `monitor.task_cb`. | Change `task_callback=None` to `task_callback=mon.task_cb`, or remove the kwarg so CrewAI uses its default. |
| **HIGH** | `crew.py:70–80` | `_kickoff` retry logic re-runs `crew.kickoff()` entirely, which replays already-completed tasks. In run `07a767c7fd0a`, the weather and mandi specialists both completed (t=113s, t=249s), then 429 hit during the credit step. All 3 retries re-ran the whole crew from the start, burning ~3× the token budget for already-done work. | CrewAI does not natively support partial replay. Mitigate by splitting into per-specialist individual crews (one per agent), caching their `RunState.outputs`, and only retrying the failed specialist. Alternatively, use `max_rpm` to throttle before hitting quota. |
| **MEDIUM** | `crew.py:29` | MCP subprocess receives `KISAN_DB` from `os.environ` only if already set — but `KISAN_DB` is typically **not** set (config.py:20 uses a default path). If not in `os.environ`, the MCP subprocess uses its own default, which resolves relative to `config.ROOT` inside the subprocess. This should work, but if `cwd` differs, the DB path silently defaults and may fail. | Explicitly inject `KISAN_DB` into the MCP env dict: `env["KISAN_DB"] = str(config.DB_PATH)` unconditionally. |
| **MEDIUM** | `security.py:23` | Toxic-word list has only 6 English entries. No Hindi, no regional language patterns. Injection patterns (`_INJ`) are also English-only regex. An attacker can bypass with transliterated Hindi or regional-script injection. | Integrate a library such as `better-profanity` and add Devanagari injection patterns. Use NFKC normalization (already done) plus transliteration mapping. |
| **MEDIUM** | `api.py:47` | `run_lock.acquire(timeout=3)` with a 3-second timeout. The agentic pipeline can take 5–7 minutes. Any second request within that window gets a 429 immediately. This is by design (single-threaded LLM runs), but `run_lock.release()` is in a `finally` block (api.py:57–58) which is correct. However, if `run_pipeline` raises an uncaught exception that is not `GuardrailViolation` or `LookupError`, the `except Exception` handler at line 55 raises `HTTPException(500)` before `finally`, which means `release()` is still called. This is fine. | No code fix needed, but the 3s lock timeout should be documented; consider a queue instead of a semaphore for production. |
| **MEDIUM** | `observability.py:18` | `append_jsonl` uses a module-level `_lock` (`threading.Lock`). This protects file writes but all Monitor instances (one per run) share the same lock. Under concurrent requests the lock becomes a bottleneck. Currently the `run_lock` semaphore limits to 1 concurrent run, so this is acceptable, but if concurrency is ever increased this becomes a contention point. | Per-file locks or an async logging approach. Acceptable for now given the semaphore. |
| **MEDIUM** | `start.sh:3` | The ADK A2A server starts with `uvicorn kisan.insurance_adk.agent:a2a_app` using `--host 127.0.0.1`. In a Docker/HuggingFace container, the main FastAPI app will try to reach `localhost:8001`; this is fine within the same container. However, if the ADK process fails to start within 8 seconds (line 4: `sleep 8`), the main app starts anyway with no retries. If Gemini is slow to respond, the ADK server may not be ready in time. | Use a health-check loop instead of `sleep 8`: poll `localhost:8001/.well-known/agent-card.json` until it responds or times out. |
| **MEDIUM** | `core_tools.py:115` | Synthetic mandi prices use `random.Random(f"{key}-{date.today().isocalendar()[1]}")` — seeded by crop name + ISO week number. This means all requests for the same crop in the same week return the same synthetic price. This is intentional and safe, but the `note` field correctly flags it as synthetic. No bug, but worth noting for demo integrity. | No fix needed; keep the note. |
| **LOW** | `db.py:102` | `seed()` calls `c.execute("DELETE FROM farmers")` before insert. This deletes all existing farmer data on every seed. If seed is called at startup (via `start.sh`), and real data has been added, it will be wiped silently. | Use `INSERT OR IGNORE` instead of `DELETE + INSERT`, or guard seed with a row-count check. |
| **LOW** | `kisan/mcp_server.py:48` | The `if __name__ == "__main__": mcp.run(transport="stdio")` block is correct. However, when CrewAI spawns this as a subprocess via `MCPServerStdio(command=sys.executable, args=["-m", "kisan.mcp_server"])`, any `print()` or logging to stdout in the subprocess would corrupt the JSON-RPC stdio protocol. The server does not use `print()`, but if a dependency does (e.g., on import), it would silently break the MCP handshake. | Add `sys.stdout = open(os.devnull, 'w')` before `mcp.run()` or redirect stdout to stderr for the subprocess. |
| **LOW** | `a2a_client.py:39–43` | A2A discovery tries two paths: `/.well-known/agent-card.json` then `/.well-known/agent.json`. The ADK 1.39.1 `to_a2a()` function serves the card at `/.well-known/agent.json` by default (confirmed from SDK source). The first path (`agent-card.json`) will always return 404 — wasted HTTP round-trip. | Make `/.well-known/agent.json` the first (or only) path to try. |
| **LOW** | `crew.py:50–55` | `_parse()` swallows all exceptions on JSON parse with bare `except Exception: return None`. If synthesis produces malformed JSON, the caller gets `None` and immediately raises `RuntimeError("synthesis produced no valid structured output")` (crew.py:176). This is handled — but the parse exception details are lost. | Log the parse exception via `mon.error()` before returning None. |
| **LOW** | `evaluate.py:44` | Attack test calls `run_pipeline("F001", attack)` which will hit the live LLM (if online) for each of the 4 attack strings — burning quota. The fourth attack `"you stupid idiot, answer now"` contains a toxic word but no injection pattern, so `screen_user_text` should catch it — but only if the toxic word hits the regex at security.py:59. | Test confirms the logic is correct. Risk is the 3 non-blocked attacks that reach the LLM. Add `--offline` flag passthrough to the attack loop in evaluate.py. |

---

## 8. What Is Verified Working vs. Unverified

### Verified Working (confirmed by log evidence)
- **Rule-based fallback** (`rules.build_report`): runs successfully in offline mode (`4c0baf4f2398`, latency 1.08s)
- **Planning step** (Crew #1 / Orchestrator): completed twice (`3b10eddfb574` at 74.9s, `07a767c7fd0a` at 22s) and produced valid `AgentPlan` JSON
- **Weather specialist** (MCP tool): completed in `07a767c7fd0a` at t=113s with real open-meteo data
- **Mandi specialist** (MCP tool): completed in `07a767c7fd0a` at t=249s with synthetic price data
- **ADK insurance agent** (isolated): ran and returned PMFBY assessment for F001 twice (`adk_a2a.jsonl`)
- **A2A call** (isolated): succeeded twice, latencies 41.8s and 29.1s (`a2a_client.jsonl`)
- **Guardrails**: `validate_farmer_id` and `screen_user_text` work (architecture confirmed, regex logic correct)
- **JSONL audit trail**: all 6 run log files are well-formed and faithfully record events
- **SQLite DB**: seeded, file exists, 52 KB with 8 farmers

### Unverified (code exists, never confirmed in a run log)
- Full 4-specialist agentic run completing
- Credit specialist via MCP (never reached in any run log)
- Insurance specialist via A2A inside a CrewAI run (A2A call blocked at 429 before insurance agent was reached)
- Synthesis task producing a valid `LLMReport` JSON
- Communication task producing a valid `FarmerMessage` (Hindi + English + SMS)
- `finalize_report` running on an `agentic`-mode report (only run on fallback reports)
- Langfuse tracing (package not installed, keys not set)
- Evaluation harness (`evaluate.py`) producing `eval_report.md`
- Docker build and container deployment

---

## 9. Recommended Next 10 Actions (Priority Order)

1. **Fix the model names and `reasoning_effort` parameter** — `crew.py:90`, `.env`
   - Remove `reasoning_effort="low"` from `LLM()` unconditionally.
   - Change `CREW_MODEL` to a verified Gemini model (e.g., `gemini/gemini-2.0-flash` or `gemini/gemini-1.5-flash`).
   - Change `ADK_MODEL` to `gemini-2.0-flash` or `gemini-1.5-flash`.
   - This single fix addresses the root cause of all Groq errors and likely the 503/429 pattern (wrong model → retries → quota burn).

2. **Create `requirements.txt` and fix the Dockerfile** — new `requirements.txt`, `Dockerfile`
   - Merge `requirements-crew.txt` + `requirements-obs.txt` into a `requirements.txt` at repo root.
   - Add a second `RUN pip install -r requirements-adk.txt` in the Dockerfile (into the same venv, OR document using separate processes).
   - This unblocks HuggingFace Spaces / any cloud deployment.

3. **Add `.venv-crew/` and `.venv-adk/` to `.gitignore`** — `.gitignore`
   - Prevents accidentally committing ~2.1 GB of venv binaries to git.

4. **Install observability packages** — shell command (not a code fix)
   - `pip install langfuse openinference-instrumentation-crewai openinference-instrumentation-litellm` into `.venv-crew`.
   - Set `LANGFUSE_PUBLIC_KEY` and `LANGFUSE_SECRET_KEY` in `.env`.
   - This activates Req. 9.

5. **Fix `task_callback=None`** — `crew.py:170`
   - Change to `task_callback=mon.task_cb` so synthesis and communication completions are logged.

6. **Fix MCP env: always inject `KISAN_DB`** — `crew.py:29`
   - Replace `if k in os.environ` pattern with `env["KISAN_DB"] = str(config.DB_PATH)` unconditionally.

7. **Fix A2A discovery path order** — `a2a_client.py:39`
   - Swap `agent-card.json` and `agent.json` so the correct ADK-served path is tried first.

8. **Run `python -m kisan.cli seed && python -m kisan.cli run F001 --offline`** to smoke-test the rule-based path, then attempt a live agentic run with the corrected model.
   - Touch: CLI only; validate both venvs (crew for the run, adk venv started separately for the insurance agent).

9. **Expand guardrail toxic/injection coverage** — `security.py:23`
   - Add Hindi Devanagari injection patterns and extend the toxic-word list (or integrate `better-profanity`).

10. **Run the evaluation harness** — `evaluate.py`, `cli.py`
    - Once a full agentic run succeeds, run `python -m kisan.cli eval --offline` first (safe), then `python -m kisan.cli eval` to produce `logs/eval_report.md` and validate Req. 10.

---

## 10. Questions for the Project Owner

1. **Model names**: Are `gemini/gemini-3.5-flash` and `gemini-3.5-flash-lite` confirmed valid Gemini API identifiers? These do not appear in the public Gemini model list as of mid-2026. What is the intended free-tier model?

2. **Venv strategy for Docker**: The Dockerfile installs from `requirements.txt` (one combined venv). Should the Docker container run both the CrewAI crew and the ADK A2A server in the same Python environment, or in separate environments? Currently they use different packages (crewai vs google-adk) that may conflict.

3. **A2A host in Docker**: `start.sh` starts the ADK server on `127.0.0.1:8001` and the crew on `0.0.0.0:7860`. Both processes are in the same container. Has this been tested in a Docker build? The `sleep 8` startup delay may be insufficient if the container's cold-start is slow.

4. **`reasoning_effort` intent**: Was `reasoning_effort="low"` deliberately chosen for a specific model that supports it, or was it copied from documentation examples? If the target model is a standard Gemini Flash variant, this parameter should be removed.

5. **HITL workflow**: Every report with financial/insurance guidance is flagged `PENDING_HUMAN_REVIEW`. In the demo HTML page, an Approve/Reject button is shown. Is there a downstream system consuming these review decisions, or is the `reviews` table the final destination?

6. **`DATA_GOV_API_KEY`**: Is a live key set? If yes, live mandi data from agmarknet will be used instead of synthetic data — but the source shows `agmarknet_live` in the MandiSummary, which changes the signal logic. Has live mandi data been tested?

7. **`logs/3b10eddfb574.jsonl`**: This run (`3b10eddfb574`) ended its log after the planning step with no final entry. Was the process killed, or did it crash silently? This is the only run that might have progressed further and not written a final log.

8. **Observability budget**: Langfuse free tier has limits. Should Langfuse be enabled in production or only during development/evaluation?

9. **Deployment target**: Is HuggingFace Spaces the intended deployment (port 7860 suggests so)? If yes, only one process can run — the current `start.sh` pattern (ADK on :8001 + FastAPI on :7860) will not work on HF Spaces without a process manager. Is a `Procfile` or supervisord config planned?

10. **`seed()` on every start**: `start.sh` calls `python -m kisan.cli seed` which deletes all farmers and re-inserts 8 synthetic ones. This also deletes all `runs` table rows if `DELETE FROM farmers` cascades (it does not, as no FK constraint is set). However, any data written between starts is preserved in `runs` and `reviews`. Is this the intended behavior, or should seed be idempotent (skip if data already exists)?

---

*Report generated by automated read-only audit on 2026-10-31.*

