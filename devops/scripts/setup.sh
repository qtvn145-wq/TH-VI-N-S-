#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/../.."
umask 077
mkdir -p backups
if [[ ! -f .env ]]; then cp devops/deploy/env.example .env; fi
chmod 700 backups
chmod 600 .env
printf 'Ready. Edit .env, then: docker compose up -d --build
'
