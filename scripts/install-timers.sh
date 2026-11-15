#!/usr/bin/env bash
# Install systemd units using this checkout's real path. No timers are enabled here.
set -euo pipefail
cd "$(dirname "$0")/.."
if [[ "$EUID" -ne 0 ]]; then echo 'Run: sudo bash scripts/install-timers.sh'; exit 1; fi
repo_path=$(pwd -P)
# Keep systemd path syntax unambiguous; ordinary WSL/Linux checkout paths work.
if [[ ! "$repo_path" =~ ^/[A-Za-z0-9_./-]+$ ]]; then
  echo 'Use a checkout path containing only letters, numbers, slash, dot, dash or underscore.' >&2
  exit 1
fi
systemctl show-environment >/dev/null
if ! docker info >/dev/null 2>&1; then
  echo 'Docker is not accessible as root. Start Docker/Desktop and check WSL integration.' >&2
  exit 1
fi
for job in backup reminders monitor; do
  temp_unit=$(mktemp)
  sed "s|/opt/thu-vien-so|$repo_path|g" "deploy/library-$job.service" > "$temp_unit"
  # Docker Desktop's daemon lives outside this WSL distribution.
  if ! systemctl cat docker.service >/dev/null 2>&1; then
    sed -i '/^Requires=docker.service$/d; /^After=docker.service$/d' "$temp_unit"
  fi
  install -m 644 "$temp_unit" "/etc/systemd/system/library-$job.service"
  rm -f "$temp_unit"
  install -m 644 "deploy/library-$job.timer" "/etc/systemd/system/library-$job.timer"
done
systemctl daemon-reload
# Avoid creating a root-owned lock file that the checkout owner cannot open later.
if [[ ! -e .ops.lock ]]; then
  touch .ops.lock
  chown --reference=. .ops.lock
  chmod 660 .ops.lock
fi
echo 'Installed units. Enable backup/monitor now; enable reminders only after SMTP verification.'
