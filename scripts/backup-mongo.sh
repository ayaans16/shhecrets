#!/usr/bin/env bash
# Daily Mongo backup -> AWS S3 (run via cron). Redis is deliberately not
# backed up here: everything in it is TTL'd and meant to be destroyed on
# read, there's nothing there worth preserving. This protects the one
# thing that should survive the VPS itself dying: the session
# metadata/audit trail in Mongo.
#
# Retention is handled by an S3 lifecycle rule (auto-delete objects
# older than N days), not by this script - simpler than reimplementing
# retention logic here.
#
# Uses the AWS CLI directly with a dedicated IAM user scoped to only
# this one bucket (s3:PutObject/GetObject/ListBucket, nothing else) -
# see DEPLOY.md for the exact policy and setup.
set -euo pipefail

cd "$(dirname "$0")/../infra"

TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
ARCHIVE="/tmp/shhecrets-mongo-${TIMESTAMP}.archive.gz"
S3_BUCKET="s3://shhecrets-backups-ayaanshaikh/mongo/"

cleanup() { rm -f "$ARCHIVE"; }
trap cleanup EXIT

# -T disables pseudo-TTY allocation - required for piping mongodump's
# binary archive output through `docker-compose exec` correctly. With a
# TTY allocated, binary data gets mangled (newline translation etc.).
if ! docker-compose -f docker-compose.prod.yml exec -T mongo mongodump --archive --gzip > "$ARCHIVE"; then
  "$(dirname "$0")/send-alert.sh" "mongo backup failed" "mongodump exited non-zero - check the cron log on the VPS."
  exit 1
fi

if ! aws s3 cp "$ARCHIVE" "$S3_BUCKET"; then
  "$(dirname "$0")/send-alert.sh" "mongo backup upload failed" "mongodump succeeded but aws s3 cp failed - check the cron log on the VPS."
  exit 1
fi
