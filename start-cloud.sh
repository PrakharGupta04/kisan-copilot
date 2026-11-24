#!/usr/bin/env bash
set -u
export PYTHONPATH="$(pwd)"
python -m kisan.cli seed || { echo "[FATAL] seed failed"; exit 1; }
exec python -m uvicorn kisan.api:app --host 0.0.0.0 --port "${PORT:-10000}"
