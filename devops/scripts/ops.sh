#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
exec 9>.ops.lock
flock -n 9 || { echo 'Another maintenance job is running'; exit 1; }
case "${1:-}" in
  backup)
    docker compose stop backend
    trap 'docker compose start backend' EXIT
    docker compose run --rm --no-deps maintenance
    docker compose start backend
    trap - EXIT
    if [[ -n "${BACKUP_REMOTE:-}" ]]; then
      rsync -a -- backups/ "$BACKUP_REMOTE"
    fi
    ;;
  deploy)
    docker compose build --pull
    docker compose stop backend
    trap 'echo "Deployment failed: inspect logs; backend stays stopped to protect schema compatibility" >&2' ERR
    docker compose run --rm --no-deps maintenance
    docker compose run --rm --no-deps migrate
    docker compose up -d --no-deps --wait backend web
    # Start/reload the production proxy separately for first deployment or config changes.
    ;;
  *) echo 'Usage: bash devops/scripts/ops.sh backup|deploy'; exit 2 ;;
esac
