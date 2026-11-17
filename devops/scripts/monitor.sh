#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
bash devops/scripts/smoke.sh "${MONITOR_URL:-http://localhost:8081}"
used=$(df -P . | awk 'NR==2 {gsub(/%/, "", $5); print $5}')
(( used < 85 )) || { echo "ALERT: disk usage $used%" >&2; exit 1; }
# Backups must exist and be newer than 26 hours; path matches default BACKUP_DIR.
find backups -name 'library-*.tar.gz' -mmin -1560 -print -quit | grep -q . || { echo 'ALERT: backup missing or older than 26 hours' >&2; exit 1; }
