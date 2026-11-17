#!/usr/bin/env bash
set -euo pipefail
base="${1:-http://localhost:8081}"
curl --fail --silent --show-error --max-time 15 "$base/" >/dev/null
curl --fail --silent --show-error --max-time 15 "$base/ui/src/app.js" >/dev/null
curl --fail --silent --show-error --max-time 15 "$base/api/v1/health" | python3 -c 'import json,sys; assert json.load(sys.stdin)["status"] == "ok"'
curl --fail --silent --show-error --max-time 15 "$base/api/v1/books" | python3 -c 'import json,sys; assert isinstance(json.load(sys.stdin),list)'
echo 'PASS: UI, JS, database health, catalogue'
