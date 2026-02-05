#!/usr/bin/env bash
# .env에 넣을 JWT_SECRET, API_KEYS 예시 값을 생성해서 출력합니다.
# 사용: ./scripts/gen-env-values.sh  → 출력을 보고 .env에 복사

echo "# 아래 값을 .env에 넣으세요."
echo ""
echo "JWT_SECRET=$(openssl rand -hex 32)"
echo "API_KEYS=key_drillquiz_$(openssl rand -hex 8),key_cointutor_$(openssl rand -hex 8)"
echo ""
echo "# DIFY_API_KEY는 Dify 웹(API 액세스)에서 복사해야 합니다:"
echo "#   https://dify.drillquiz.com → 앱 선택 → API Access → API Key"
