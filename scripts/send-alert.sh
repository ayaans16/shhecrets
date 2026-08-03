#!/usr/bin/env bash
# Shared by healthcheck.sh and backup-mongo.sh - sends a one-off alert
# email via msmtp. Requires ~/.msmtprc to already be configured on the
# VPS (see DEPLOY.md) - deliberately not part of this repo, since it
# holds a real credential (a Gmail App Password).
set -euo pipefail

: "${ALERT_EMAIL:?Set ALERT_EMAIL to the address alerts should go to}"

subject="$1"
body="${2:-$1}"

{
  echo "To: ${ALERT_EMAIL}"
  echo "Subject: [shhecrets] ${subject}"
  echo
  echo "${body}"
} | msmtp -a default "${ALERT_EMAIL}"
