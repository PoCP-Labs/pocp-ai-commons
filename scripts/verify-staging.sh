#!/usr/bin/env bash
# Phase A — verify backend/.env before public staging deploy.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python backend/scripts/verify_staging_env.py "$@"
