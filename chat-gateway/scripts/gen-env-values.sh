#!/usr/bin/env bash
# Generate sample CHAT_GATEWAY_JWT_SECRET and CHAT_GATEWAY_API_KEY for .env
# Usage: ./scripts/gen-env-values.sh  → copy output into .env

echo "# Add the following to .env:"
echo ""
echo "CHAT_GATEWAY_JWT_SECRET=$(openssl rand -hex 32)"
echo "CHAT_GATEWAY_API_KEY=key_drillquiz_$(openssl rand -hex 8),key_cointutor_$(openssl rand -hex 8)"
echo ""
echo "# DIFY_API_KEY must be copied from Dify web (API Access):"
echo "#   https://dify.drillquiz.com → select app → API Access → API Key"
