#!/usr/bin/env bash
set -u
VENV_CREW="${VENV_CREW:-/opt/venv-crew}"
VENV_ADK="${VENV_ADK:-/opt/venv-adk}"
PORT="${PORT:-7860}"
A2A_PORT="${A2A_PORT:-8001}"
POLL="${ADK_POLL_TIMEOUT:-45}"
export PYTHONPATH="$(pwd)"

echo "[START] seeding synthetic farmers"
"$VENV_CREW/bin/python" -m kisan.cli seed || { echo "[FATAL] seed failed"; exit 1; }

echo "[START] ADK insurance agent on 127.0.0.1:${A2A_PORT}"
"$VENV_ADK/bin/python" -m uvicorn kisan.insurance_adk.agent:a2a_app --host 127.0.0.1 --port "$A2A_PORT" &
ADK_PID=$!
trap 'kill $ADK_PID 2>/dev/null' EXIT

READY=0
for i in $(seq 1 "$POLL"); do
  if A2A_PORT="$A2A_PORT" "$VENV_CREW/bin/python" - <<'PY'
import os, sys, urllib.request
port = os.environ["A2A_PORT"]
for p in ("/.well-known/agent-card.json", "/.well-known/agent.json"):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{port}{p}", timeout=2)
        sys.exit(0)
    except Exception:
        pass
sys.exit(1)
PY
  then
    READY=1
    echo "[READY] ADK agent online after ${i}s"
    break
  fi
  sleep 1
done
[ "$READY" = "1" ] || echo "[WARN] ADK not ready after ${POLL}s; insurance will degrade gracefully"

echo "[START] web app on 0.0.0.0:${PORT}"
"$VENV_CREW/bin/python" -m uvicorn kisan.api:app --host 0.0.0.0 --port "$PORT"
