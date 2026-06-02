#!/usr/bin/env bash
# Phase A — one-command local acceptance (single node or federation).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
FEDERATION=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --federation|-f) FEDERATION=true; shift ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

cd "$ROOT"

if $FEDERATION; then
  echo "Starting federation stack (node-a :8100, node-b :8101)…"
  docker compose -f docker-compose.federation.yml up -d --build
  BASE="http://127.0.0.1:8100"
  NODE_B="http://127.0.0.1:8101"
  FED_ARG="--federation $NODE_B"
else
  echo "Starting single-node stack (:8008 API, :3000 UI)…"
  docker compose up -d --build
  BASE="http://127.0.0.1:8008"
  FED_ARG=""
fi

echo "Waiting for API health at $BASE (first boot may take up to 6 min)…"
for i in $(seq 1 180); do
  if curl -sf "$BASE/health" >/dev/null 2>&1; then
    echo "API ready."
    break
  fi
  if [[ $i -eq 180 ]]; then
    echo "Timeout waiting for $BASE/health"
    exit 1
  fi
  sleep 2
done

if $FEDERATION; then
  for i in $(seq 1 180); do
    if curl -sf "$NODE_B/health" >/dev/null 2>&1; then
      echo "Node B ready."
      break
    fi
    sleep 2
  done
fi

python "$ROOT/backend/scripts/run_phase_a_acceptance.py" "$BASE" $FED_ARG
