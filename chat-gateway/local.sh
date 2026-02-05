#!/usr/bin/env bash
set -e

# 스크립트가 있는 디렉터리로 이동 (repo 루트 또는 chat-gateway에서 실행 가능)
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

if [[ ! -f .env ]]; then
  echo "경고: .env 없음. .env.example을 복사한 뒤 값을 채워 주세요."
  echo "  cp .env.example .env"
  if [[ -f .env.example ]]; then
    cp .env.example .env
    echo "  → .env.example을 .env로 복사했습니다. .env를 편집한 뒤 다시 실행하세요."
    exit 1
  fi
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "가상환경 생성 중..."
  python3 -m venv .venv
fi
source .venv/bin/activate

echo "의존성 확인 중..."
pip install -q -r requirements.txt

echo "Chat Gateway 로컬 실행 (http://0.0.0.0:8088)"
echo "  API 문서: http://localhost:8088/docs"
echo "  채팅 페이지: http://localhost:8088/chat?token=<JWT>"
# 로그가 바로 터미널에 보이도록 버퍼링 끔
export PYTHONUNBUFFERED=1
exec uvicorn app.main:app --reload --host 0.0.0.0 --port 8088 --log-level info --access-log
