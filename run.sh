#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

required=(AI_CLIENT_ID AI_CLIENT_SECRET AI_TOKEN_URL AI_CHAT_URL)
for name in "${required[@]}"; do
  if [[ -z "${!name:-}" ]]; then
    echo "Missing required configuration: ${name}" >&2
    exit 1
  fi
done

exec python rag_app.py \
  --json "${JSON_DATA_PATH:-lead_data.json}" \
  --rules "${RULES_PATH:-lead_intelligence.txt}" \
  --question "${QUESTION:-What actions should the store team prioritize?}" \
  --token-url "$AI_TOKEN_URL" \
  --chat-url "$AI_CHAT_URL" \
  --client-id "$AI_CLIENT_ID" \
  --client-secret "$AI_CLIENT_SECRET" \
  --model "${AI_MODEL:-gpt-4o}" \
  --json-limit "${JSON_LIMIT:-4000}" \
  --output "${OUTPUT_PATH:-response.json}"
