#!/bin/zsh
set -euo pipefail
cd /Users/jl/.openclaw/workspace

if [[ $# -lt 1 ]]; then
  echo "usage: scripts/project_resume.sh <topic words...>" >&2
  exit 1
fi

topic="$*"
python3 scripts/chat_memory_rollup.py --llm-limit 1 >/dev/null || true
printf "\n=== PROJECT MATCHES ===\n"
python3 scripts/session_memory.py project "$topic"
printf "\n=== PROJECT FILES ===\n"
rg -n -i "${topic}" memory/projects || true
