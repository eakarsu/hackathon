#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/backend"

port="${PORT:-5001}"
if command -v lsof >/dev/null 2>&1 && lsof -tiTCP:"$port" -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port ${port} is already in use; stop that process explicitly or choose PORT." >&2
  exit 1
fi

exec python app.py
