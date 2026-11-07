#!/bin/bash
python -m kisan.cli seed
uvicorn kisan.insurance_adk.agent:a2a_app --host 127.0.0.1 --port 8001 &
sleep 8
exec uvicorn kisan.api:app --host 0.0.0.0 --port 7860