#!/usr/bin/env bash
# Local/CI verification; no deployment, email or production data writes.
set -euo pipefail
cd "$(dirname "$0")/../.."
python -m unittest discover -s backend/tests -v
python -m unittest discover -s devops/tests -v
PYTHONPATH=. python qa/integration_test.py
npm --prefix frontend run check
npm --prefix frontend test
for script in devops/scripts/*.sh; do bash -n "$script"; done
