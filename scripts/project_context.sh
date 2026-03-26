#!/bin/zsh
set -euo pipefail
cd /Users/jl/.openclaw/workspace

if [[ $# -lt 1 ]]; then
  echo "usage: scripts/project_context.sh <topic words...>" >&2
  exit 1
fi

python3 scripts/session_memory.py build-index --days 14 --limit 20 >/dev/null
python3 scripts/session_memory.py project "$*"
