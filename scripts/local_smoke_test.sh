#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000}"
SESSION_ID="demo-session-$(date +%s)"

echo "[1/4] API health"
curl -sS "$API_BASE/health" | tee /tmp/evermind_health.json

echo "[2/4] Evermemos health"
curl -sS "$API_BASE/health/evermemos" | tee /tmp/evermind_health_mem.json

echo "[3/4] LLM health"
curl -sS "$API_BASE/health/llm" | tee /tmp/evermind_health_llm.json

echo "[4/4] Chat e2e"
curl -sS -X POST "$API_BASE/chat" \
  -H 'Content-Type: application/json' \
  -d "{\"channel_id\":\"demo-channel\",\"session_id\":\"$SESSION_ID\",\"message\":\"请给我三条今天可执行的事项\"}" \
  | tee /tmp/evermind_chat_e2e.json

echo
echo "Smoke test done."
echo "- health: /tmp/evermind_health.json"
echo "- health_mem: /tmp/evermind_health_mem.json"
echo "- health_llm: /tmp/evermind_health_llm.json"
echo "- chat: /tmp/evermind_chat_e2e.json"
