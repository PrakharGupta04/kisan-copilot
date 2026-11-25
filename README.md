# Kisan Copilot

Autonomous multi-agent AI for farmer decision support: weather risk, mandi prices, KCC credit and PMFBY crop insurance.
Built with **CrewAI** and **Google ADK**, linked by the **A2A** protocol, with tools served over **MCP**.
Synthetic farmer profiles only. Not financial, legal or insurance advice.

## How it works
1. Guardrails check the farmer ID and any typed question (length, prompt injection, abusive language).
2. A policy router selects the agents: weather and insurance always, credit if the farmer has a loan, mandi if harvest is within 60 days. If the farmer typed a question, one LLM call routes instead.
3. One MCP stdio session runs the weather (Open-Meteo), mandi (data.gov.in) and KCC credit tools. The CrewAI side calls the Google ADK PMFBY agent over A2A.
4. Four CrewAI specialists (weather, mandi, credit, insurance) reason in sequence. Each reads the earlier findings through a shared `RunState`. Finished steps are checkpointed and never re-run.
5. One synthesis call returns a validated Pydantic `FinalReport` with a Hindi, English and SMS message.
6. Output guardrails: PII redaction, a numeric grounding check against tool evidence, and a human-review gate (Approve or Reject).
7. Every step is written to `logs/<run_id>.jsonl`. Traces go to Langfuse when keys are set.

If the LLM path fails or quota runs out, a rule engine produces the same report (`rule_based_fallback`). Demo mode forces it (`offline`).

## Requirement map
| Req | Where |
|---|---|
| 1 Context sharing | `schemas.RunState`, `crew._agentic` |
| 2 MCP tools | `mcp_server.py`, `crew._mcp_evidence` |
| 3 Pydantic output | `schemas.py` |
| 4 Design patterns | policy router, sequential specialists with checkpoints, fallback, human-in-the-loop |
| 5 Callbacks and monitoring | `observability.Monitor`, ADK callbacks in `insurance_adk/agent.py` |
| 6 A2A | `a2a_client.py` and `insurance_adk/agent.py` |
| 7 CrewAI and ADK only | `.venv-crew` and `.venv-adk` |
| 8 Guardrails | `security.py`, `grounding.py`, ADK callbacks |
| 9 Observability | JSONL audit trail and Langfuse |
| 10 Evaluation | `evaluate.py`, output in `logs/eval_report.md` |
| 11 Cloud | `Dockerfile.render` (light Demo-mode build) |

## Run locally (WSL or Linux, Python 3.11)
```bash
python -m venv .venv-crew && .venv-crew/bin/pip install -r requirements.txt -r requirements-obs.txt
python -m venv .venv-adk && .venv-adk/bin/pip install -r requirements-adk.txt
cp .env.example .env            # then add GOOGLE_API_KEY and DATA_GOV_API_KEY
.venv-crew/bin/python -m kisan.cli seed
.venv-adk/bin/python -m uvicorn kisan.insurance_adk.agent:a2a_app --host 127.0.0.1 --port 8001
.venv-crew/bin/python -m uvicorn kisan.api:app --port 7860     # open http://localhost:7860
```
Or run both with `VENV_CREW=.venv-crew VENV_ADK=.venv-adk bash start.sh`.

Other commands:
```bash
.venv-crew/bin/python -m pytest                       # offline tests
.venv-crew/bin/python -m kisan.cli run F002           # one live run
.venv-crew/bin/python -m kisan.cli run F002 --offline # rule engine only
.venv-crew/bin/python -m kisan.cli eval               # live evaluation of 8 farmers plus offline baseline
.venv-crew/bin/python -m kisan.mandi_refresh          # refresh the mandi price snapshot
KISAN_VERBOSE=1 ...                                   # show CrewAI agent boxes in the terminal
```

## Honest limits
- Only the `prefetch` tool mode is implemented: the orchestrator calls the MCP and A2A tools, and each specialist makes one LLM call over the evidence.
- Injection and abuse patterns are English-only regexes.
- Mandi prices come from the government feed (median over mixed varieties, indicative). If the feed is slow, a recent on-disk snapshot is used, otherwise a labelled synthetic series.
- Free Gemini tier: roughly 5 LLM calls per run.
- The cloud build runs in Demo mode (rule engine, no LLM) because the free host has 512 MB RAM.
- WhatsApp: a click-to-chat button (officer-assisted, unlocked after approval). Automatic sending through the WhatsApp Cloud API is future work.
