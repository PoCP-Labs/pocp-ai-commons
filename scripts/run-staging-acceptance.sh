#!/usr/bin/env bash
# Phase A public staging — verify env, then run staging acceptance (no dev-login).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

API="${1:-}"
if [[ -z "$API" ]]; then
  echo "Usage: ./scripts/run-staging-acceptance.sh https://api.your-domain.com"
  exit 1
fi

echo "=== Staging env check ==="
python backend/scripts/verify_staging_env.py
if [[ ! -f docker-compose.staging.yml ]]; then
  echo "FAIL: missing docker-compose.staging.yml"
  exit 1
fi

echo ""
echo "=== Phase A staging acceptance @ $API ==="
python backend/scripts/run_phase_a_acceptance.py "$API" --staging --skip-optional
