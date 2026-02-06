#!/usr/bin/env python3
"""Issue JWT for testing the chat page (/chat). Uses CHAT_GATEWAY_JWT_SECRET from .env."""
import os
import sys
from pathlib import Path

# Resolve chat-admin root relative to this script
ROOT = Path(__file__).resolve().parent.parent


def load_env_secret() -> str:
    env_file = ROOT / ".env"
    if not env_file.exists():
        print("Error: No .env. Create chat-admin/.env and set CHAT_GATEWAY_JWT_SECRET.", file=sys.stderr)
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
        print("Error: CHAT_GATEWAY_JWT_SECRET not found in .env.", file=sys.stderr)
        sys.exit(1)
    return secret


def main():
    system_id = sys.argv[1] if len(sys.argv) > 1 else "drillquiz"
    user_id = sys.argv[2] if len(sys.argv) > 2 else "12345"

    try:
        import jwt
    except ImportError:
        print("Error: PyJWT required. pip install pyjwt", file=sys.stderr)
        sys.exit(1)

    secret = load_env_secret()
    payload = {"system_id": system_id, "user_id": user_id, "exp": __import__("time").time() + 86400}
    token = jwt.encode(payload, secret, algorithm="HS256")
    if hasattr(token, "decode"):
        token = token.decode("utf-8")

    base = os.environ.get("CHAT_GATEWAY_URL", "http://localhost:8000")
    url = f"{base.rstrip('/')}/chat?token={token}"
    print("system_id=%s user_id=%s (defaults: drillquiz / 12345 if no args)" % (system_id, user_id))
    print("JWT (24h validity):")
    print(token)
    print()
    print("Chat page URL:")
    print(url)
    print("  → For CoinTutor: ./scripts/gen-jwt.sh cointutor 12345")


if __name__ == "__main__":
    main()
