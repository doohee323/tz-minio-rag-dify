#!/usr/bin/env bash
# chat-gateway/.venv 를 사용해 JWT 발급 (PyJWT 불필요 오류 방지)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$DIR/.." && pwd)"
cd "$ROOT"
if [[ ! -d .venv ]]; then
  echo "오류: .venv 없음. 먼저 ./local.sh 한 번 실행하거나 python3 -m venv .venv && pip install -r requirements.txt"
  exit 1
fi
exec .venv/bin/python scripts/gen-jwt.py "$@"
