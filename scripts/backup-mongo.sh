#!/usr/bin/env bash
# Daily Mongo backup -> Cloudflare R2 (run via cron). Redis is
# deliberately not backed up here: everything in it is TTL'd and meant
# to be destroyed on read, there's nothing there worth preserving. This
# protects the one thing that should survive the VPS itself dying: the
# session metadata/audit trail in Mongo.
#
# Retention is handled by an R2 lifecycle rule (auto-delete objects
# older than N days), not by this script - simpler than reimplementing
# retention logic here.
set -euo pipefail

cd "$(dirname "$0")/../infra"

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
ARCHIVE="/tmp/shhecrets-mongo-${TIMESTAMP}.archive.gz"

cleanup() { rm -f "$ARCHIVE"; }
trap cleanup EXIT

# -T disables pseudo-TTY allocation - required for piping mongodump's
# binary archive output through `docker-compose exec` correctly. With a
# TTY allocated, binary data gets mangled (newline translation etc.).
if ! docker-compose -f docker-compose.prod.yml exec -T mongo mongodump --archive --gzip > "$ARCHIVE"; then
  "$(dirname "$0")/send-alert.sh" "mongo backup failed" "mongodump exited non-zero - check the cron log on the VPS."
  exit 1
fi

if ! rclone copy "$ARCHIVE" r2:shhecrets-backups/mongo/; then
  "$(dirname "$0")/send-alert.sh" "mongo backup upload failed" "mongodump succeeded but rclone copy to R2 failed - check the cron log on the VPS."
  exit 1
fi
