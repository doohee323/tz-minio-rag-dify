#!/usr/bin/env bash
# Use chat-admin/.venv to issue JWT (avoids PyJWT import errors)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  echo "Error: .venv not found. Run ./admin.sh once or: python3 -m venv .venv && pip install -r requirements.txt"
  exit 1
fi
exec .venv/bin/python scripts/gen-jwt.py "$@"
