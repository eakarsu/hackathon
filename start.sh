#!/usr/bin/env bash
set -euo pipefail
# Runtime governance modes: check|start. The original backend remains available through start-backend.sh.
PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
load_env_file(){ local line key value;while IFS= read -r line||[ -n "$line" ];do [[ "$line" =~ ^[[:space:]]*# || "$line" =~ ^[[:space:]]*$ ]]&&continue;line="${line#export }";key="${line%%=*}";value="${line#*=}";key="${key//[[:space:]]/}";[[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]||continue;[ -n "${!key+x}" ]&&continue;if [[ "$value" == \"*\" && "$value" == *\" ]];then value="${value:1:${#value}-2}";elif [[ "$value" == \'*\' && "$value" == *\' ]];then value="${value:1:${#value}-2}";fi;export "$key=$value";done < "$ENV_FILE"; }
[ -f "$ENV_FILE" ]||{ echo "Missing required file: $ENV_FILE" >&2;exit 1; };load_env_file
export PATH="/opt/homebrew/bin:$PATH"
case "${1:-start}" in
  check) cd "$PROJECT_DIR";python3 -m compileall -q backend ;;
  start) ;;
  *) echo "Usage: $0 [start|check]" >&2;exit 64 ;;
esac
: "${BACKEND_PORT:?BACKEND_PORT is required}";: "${FRONTEND_PORT:?FRONTEND_PORT is required}";: "${DATABASE_URL:?DATABASE_URL is required}"
: "${OPENROUTER_API_KEY:?OPENROUTER_API_KEY is required}";: "${OPENROUTER_MODEL:?OPENROUTER_MODEL is required}"
[ "${OPENROUTER_BASE_URL:-}" = "https://openrouter.ai/api/v1" ]||{ echo "Exact OPENROUTER_BASE_URL is required" >&2;exit 1; }
[ "$BACKEND_PORT" != "$FRONTEND_PORT" ]||{ echo "Assigned ports must differ" >&2;exit 1; }
for assigned_port in "$BACKEND_PORT" "$FRONTEND_PORT";do [[ "$assigned_port" =~ ^[0-9]+$ ]]||exit 1;nc -z 127.0.0.1 "$assigned_port" >/dev/null 2>&1&&{ echo "Assigned port $assigned_port is occupied" >&2;exit 1; };done
[ -d "$PROJECT_DIR/frontend/node_modules" ]&&[ -d "$PROJECT_DIR/runtime" ]||{ echo "Runtime dependencies are missing" >&2;exit 1; }
export RUNTIME_PROJECT_NAME=hackathon RUNTIME_AI_ENDPOINT=/api/ai/rag-knowledge-review RUNTIME_AI_FEATURE=rag-knowledge-review
export RUNTIME_AI_SYSTEM_PROMPT='You are a governed retrieval assistant. Produce a concise evidence-aware answer, distinguish retrieved evidence from inference, flag missing sources, and require human review for consequential use.'
node "$PROJECT_DIR/runtime/setup.mjs"
CHILD_PIDS=()
(cd "$PROJECT_DIR"&&exec node runtime/api.mjs)&CHILD_PIDS+=("$!")
(cd "$PROJECT_DIR/frontend";export HOST=127.0.0.1 PORT="$FRONTEND_PORT" BROWSER=none;exec npm start)&CHILD_PIDS+=("$!")
kill_tree(){ local pid="$1" child;for child in $(pgrep -P "$pid" 2>/dev/null||true);do kill_tree "$child";done;kill -TERM "$pid" 2>/dev/null||true; }
cleanup(){ trap - EXIT INT TERM;for pid in "${CHILD_PIDS[@]}";do kill_tree "$pid";done;for pid in "${CHILD_PIDS[@]}";do wait "$pid" 2>/dev/null||true;done; }
trap cleanup EXIT INT TERM
wait "${CHILD_PIDS[@]}"
