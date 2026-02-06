#!/usr/bin/env bash
set -e

# Change to script directory (run from repo root or chat-admin)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [[ ! -f .env ]]; then
  echo "Warning: .env not found. Copy .env.example to .env and fill in values."
  echo "  cp .env.example .env"
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "  → Copied .env.example to .env. Edit .env then run again."
    exit 1
  fi
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "Creating virtual environment..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "Checking dependencies..."
pip install -q -r requirements.txt

if [[ ! -f static/index.html ]]; then
  echo "Building Vue frontend..."
  npm install && npm run build
  mkdir -p static
  cp -R dist/* static/
  cp static/index.html static/404.html 2>/dev/null || true
fi

echo "TZ-Chat Admin running locally (http://0.0.0.0:8000)"
echo "  API docs: http://localhost:8000/docs"
echo "  Intro: http://localhost:8000/"
echo "  Chat: http://localhost:8000/chat?token=<JWT>"
# Disable buffering so logs appear immediately
export PYTHONUNBUFFERED=1
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --log-level info --access-log
