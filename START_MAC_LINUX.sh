#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r apps/api/requirements.txt
[ -f apps/api/.env ] || cp apps/api/.env.example apps/api/.env
(cd apps/web && npm install)
python -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000 --reload &
API_PID=$!
trap 'kill $API_PID 2>/dev/null || true' EXIT
(cd apps/web && npm run dev)
