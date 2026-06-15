#!/usr/bin/env bash
# Poll origin/main for new commits; if HEAD moved, pull and restart lms-backend.
# Designed to run from a systemd timer (or cron) as the faheem user.
#
# Safety:
#   - Only pulls if working tree is clean OR local changes merge cleanly via rebase.
#   - Never force-pushes, never resets --hard.
#   - On merge conflict, aborts and leaves tree untouched; logs the failure.
#   - Restarts lms-backend only when HEAD actually advanced.
set -uo pipefail

PROJ=/home/faheem/lincole/lms-backend
REMOTE=origin
BRANCH=main
LOG=/home/faheem/lincole/lms-backend/deploy/deploy.log
LOCK=/tmp/lms-deploy.lock

log() { echo "[$(date -Iseconds)] $*" | tee -a "$LOG"; }

# Prevent overlapping runs
exec 200>"$LOCK"
if ! flock -n 200; then
  log "another deploy is running — skipping"
  exit 0
fi

cd "$PROJ" || { log "project dir missing"; exit 1; }

# Verify we're on the expected branch
current_branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null)
if [[ "$current_branch" != "$BRANCH" ]]; then
  log "HEAD is on '$current_branch', not '$BRANCH' — skipping"
  exit 0
fi

before=$(git rev-parse HEAD)

# Fetch without touching working tree
if ! git fetch "$REMOTE" "$BRANCH" --quiet 2>>"$LOG"; then
  log "fetch failed"
  exit 1
fi

after=$(git rev-parse "$REMOTE/$BRANCH")

if [[ "$before" == "$after" ]]; then
  log "no new commits on $REMOTE/$BRANCH (HEAD=$before)"
  exit 0
fi

log "new commits detected: $before → $after"

# Attempt a rebase so local edits (if any) stay on top.
if ! git pull --rebase "$REMOTE" "$BRANCH" --quiet 2>>"$LOG"; then
  log "pull --rebase conflicted — aborting, leaving tree unchanged"
  git rebase --abort 2>/dev/null || true
  exit 1
fi

new_head=$(git rev-parse HEAD)
log "pulled: $before → $new_head"

# Run migrations (idempotent — alembic tracks applied revisions)
if ! uv run alembic upgrade head 2>>"$LOG"; then
  log "alembic upgrade failed"
  exit 1
fi

# Restart the service so new code takes effect
if ! sudo -n systemctl restart lms-backend 2>>"$LOG"; then
  log "systemctl restart failed (sudo needs password?); trying without -n"
  systemctl restart lms-backend 2>>"$LOG" || { log "restart failed"; exit 1; }
fi

log "deploy complete — lms-backend restarted at $(git rev-parse --short HEAD)"
