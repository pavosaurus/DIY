#!/usr/bin/env bash
# Send a reminder to Telegram right now, as a test.
#
# Usage:
#   ./run_test.sh                 # sends today's exercise reminder
#   ./run_test.sh dinner_daily    # sends a different reminder
#   ./run_test.sh exercise --dry  # print instead of sending
#
# Reads credentials from a local .env file (copy .env.example -> .env first).

set -euo pipefail
cd "$(dirname "$0")"

if [[ -f .env ]]; then
  set -a; source ./.env; set +a
else
  echo "No .env file found. Run:  cp .env.example .env  then edit it." >&2
  exit 1
fi

REMINDER="${1:-exercise}"
if [[ "${2:-}" == "--dry" ]]; then export DRY_RUN=1; fi

export FORCE_REMINDER="$REMINDER"
python3 -m src.main
