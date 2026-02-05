#!/usr/bin/env python3
"""채팅 페이지(/chat) 테스트용 JWT 발급. .env의 CHAT_GATEWAY_JWT_SECRET 사용."""
import os
import sys
from pathlib import Path

# 스크립트 기준으로 chat-gateway 루트 찾기
ROOT = Path(__file__).resolve().parent.parent


def load_env_secret() -> str:
    env_file = ROOT / ".env"
    if not env_file.exists():
        print("오류: .env 없음. chat-gateway/.env를 만든 뒤 CHAT_GATEWAY_JWT_SECRET을 넣으세요.", file=sys.stderr)
        sys.exit(1)
    secret = None
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip() == "CHAT_GATEWAY_JWT_SECRET":
            secret = value.strip().strip('"').strip("'")
            break
    if not secret:
        print("오류: .env에 CHAT_GATEWAY_JWT_SECRET이 없습니다.", file=sys.stderr)
        sys.exit(1)
    return secret


def main():
    system_id = sys.argv[1] if len(sys.argv) > 1 else "drillquiz"
    user_id = sys.argv[2] if len(sys.argv) > 2 else "12345"

    try:
        import jwt
    except ImportError:
        print("오류: PyJWT 필요. pip install pyjwt", file=sys.stderr)
        sys.exit(1)

    secret = load_env_secret()
    payload = {"system_id": system_id, "user_id": user_id, "exp": __import__("time").time() + 86400}
    token = jwt.encode(payload, secret, algorithm="HS256")
    if hasattr(token, "decode"):
        token = token.decode("utf-8")

    base = os.environ.get("CHAT_GATEWAY_URL", "http://localhost:8088")
    url = f"{base.rstrip('/')}/chat?token={token}"
    print("system_id=%s user_id=%s (인자 없으면 drillquiz / 12345)" % (system_id, user_id))
    print("JWT (24시간 유효):")
    print(token)
    print()
    print("채팅 페이지 URL:")
    print(url)
    print("  → CoinTutor용: ./scripts/gen-jwt.sh cointutor 12345")


if __name__ == "__main__":
    main()
