#!/usr/bin/env bash
set -euo pipefail

project_dir="$(cd "$(dirname "$0")" && pwd)"
cd "$project_dir"

# The backend is loopback-scoped, does not install dependencies, and keeps all
# external RAG/AI operations fail-closed until explicitly configured.
exec ./start-backend.sh
