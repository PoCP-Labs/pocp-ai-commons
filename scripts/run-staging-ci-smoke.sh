#!/usr/bin/env bash
# CI-equivalent staging OAuth smoke (ENABLE_DEV_LOGIN=false, no real GitHub secrets).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${POCP_STAGING_CI_PORT:-8765}"
BASE="http://127.0.0.1:${PORT}"
DB="sqlite:///${ROOT}/backend/data/pocp_staging_ci_local.db"

echo "=== Staging env example check ==="
python backend/scripts/verify_staging_env.py --check-example

echo ""
echo "=== Staging compose profile check ==="
python -c "
import pathlib
text = pathlib.Path('docker-compose.staging.yml').read_text(encoding='utf-8')
for needle in ('ENABLE_DEV_LOGIN', '\"false\"', 'APP_ENV', 'staging'):
    assert needle in text, needle
print('docker-compose.staging.yml OK')
"

echo ""
echo "=== Start API @ ${BASE} (staging profile) ==="
export DATABASE_URL="$DB"
export POCP_WAIT_FOR_DB=false
export POCP_FULL_SEED=true
export APP_ENV=staging
export ENABLE_DEV_LOGIN=false
export JWT_SECRET=local-staging-ci-jwt-not-for-production
export GITHUB_CLIENT_ID=local-staging-oauth-client
export GITHUB_CLIENT_SECRET=local-staging-oauth-secret
export GITHUB_OAUTH_CALLBACK_URL="${BASE}/api/v1/auth/github/callback"
export BACKEND_URL="$BASE"
export FRONTEND_URL=http://127.0.0.1:3000
export POCP_REQUIRE_RECEIPT_SIGNATURE=true
export POCP_SIGN_COMPUTE_RECEIPTS=true

mkdir -p backend/data
(cd backend && uvicorn main:app --host 127.0.0.1 --port "$PORT") &
PID=$!
trap 'kill "$PID" 2>/dev/null || true' EXIT

for i in $(seq 1 30); do
  if curl -sf "${BASE}/health" >/dev/null; then
    break
  fi
  sleep 1
done

echo ""
echo "=== Phase A staging acceptance ==="
python backend/scripts/run_phase_a_acceptance.py "$BASE" --staging --skip-optional
