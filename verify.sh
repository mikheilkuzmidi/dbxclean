#!/usr/bin/env bash
set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

PYTHONPATH=src "$PYTHON_BIN" -m pytest -q tests backend/tests
npm --prefix frontend run lint
npm --prefix frontend run build

if [ "${DBXCLEAN_LARGE_SCAN:-0}" = "1" ]; then
  PYTHONPATH=src "$PYTHON_BIN" -m backend.tests.large_scan_check
fi

echo 'Credential-free checks passed. Live Dropbox account operations were not exercised.'
