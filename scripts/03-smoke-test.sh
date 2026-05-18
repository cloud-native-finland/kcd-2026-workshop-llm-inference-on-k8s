#!/usr/bin/env bash
# Quick sanity checks against your router. Assumes 02-port-forward.sh is
# running in another terminal (so localhost:30080 is your router).
set -euo pipefail

BASE="${BASE:-http://localhost:30080}"
MODEL="${MODEL:-Qwen/Qwen2.5-0.5B-Instruct}"

echo "== /v1/models =="
curl -fsS "$BASE/v1/models" | jq .
echo

echo "== /v1/completions (single short prompt) =="
curl -fsS -X POST "$BASE/v1/completions" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg m "$MODEL" '{model: $m, prompt: "Q: What is the capital of France?\nA:", max_tokens: 16, temperature: 0}')" | jq .
echo

echo "== /v1/chat/completions =="
curl -fsS -X POST "$BASE/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d "$(jq -n --arg m "$MODEL" '{model: $m, messages: [{role: "system", content: "You are a concise assistant."}, {role: "user", content: "Name three primary colors."}], max_tokens: 32, temperature: 0}')" | jq .
