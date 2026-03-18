#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
INTERVAL_SECONDS=${INTERVAL_SECONDS:-60}
HEALTHCHECK_ARGS=("$@")
LOG_PREFIX="[watch-runtime]"

log() {
  printf "%s %s %s\n" "${LOG_PREFIX}" "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" "$*"
}

cd "${ROOT_DIR}"
log "Starting runtime watchdog (interval=${INTERVAL_SECONDS}s, args=${HEALTHCHECK_ARGS[*]:-})"

while true; do
  if python3 scripts/runtime_healthcheck.py "${HEALTHCHECK_ARGS[@]}"; then
    log "Health check passed"
  else
    log "Health check failed — attempting recovery via docker compose up -d"
    if docker compose up -d; then
      log "docker compose up -d completed"
    else
      log "docker compose up -d FAILED"
    fi
    log "Sleeping 15s before re-check"
    sleep 15
  fi
  sleep "${INTERVAL_SECONDS}"
done
