#!/usr/bin/env bash
# Run periodically via cron. Checks two things an external uptime
# monitor (e.g. UptimeRobot hitting https://shhecrets.ca) can't see on
# its own: whether every container is actually running (not
# crash-looping) and whether disk space is running low. The external
# monitor covers "is the site reachable from the internet"; this covers
# "is the box itself healthy," which matters even while the site still
# happens to respond (e.g. a stale container serving cached responses).
set -euo pipefail

cd "$(dirname "$0")/../infra"

DISK_THRESHOLD_PERCENT=85

problems=()

# --- container health ---
all_services=$(docker-compose -f docker-compose.prod.yml config --services | sort)
running_services=$(docker-compose -f docker-compose.prod.yml ps --status=running --services | sort)
down_services=$(comm -23 <(echo "$all_services") <(echo "$running_services") || true)
if [ -n "$down_services" ]; then
  problems+=("Containers not running: $(echo "$down_services" | tr '\n' ' ')")
fi

# --- disk space ---
disk_used_percent=$(df / | awk 'NR==2 { gsub("%","",$5); print $5 }')
if [ "$disk_used_percent" -ge "$DISK_THRESHOLD_PERCENT" ]; then
  problems+=("Disk usage at ${disk_used_percent}% (threshold ${DISK_THRESHOLD_PERCENT}%)")
fi

if [ "${#problems[@]}" -gt 0 ]; then
  body=$(printf '%s\n' "${problems[@]}")
  "$(dirname "$0")/send-alert.sh" "health check failed" "$body"
  exit 1
fi
