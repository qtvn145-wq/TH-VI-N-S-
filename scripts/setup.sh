#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
umask 077
mkdir -p secrets backups
if [[ ! -f .env ]]; then cp deploy/env.example .env; fi
if [[ ! -f secrets/smtp_password.txt ]]; then : > secrets/smtp_password.txt; fi
# The directory is host-private; the mounted file must be readable by container UID 10001.
chmod 700 secrets backups
chmod 644 secrets/smtp_password.txt
chmod 600 .env
printf 'Ready. Edit .env, then: docker compose up -d --build
'
