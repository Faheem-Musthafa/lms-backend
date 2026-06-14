#!/usr/bin/env bash
# Update the Cloudflare quick-tunnel URL in .env and restart the backend.
# Usage:  ./scripts/update_tunnel.sh <new-tunnel-url>
# Example: ./scripts/update_tunnel.sh https://foo-bar-baz.trycloudflare.com
set -euo pipefail

PROJ=/home/faheem/lincole/lms-backend
ENV_FILE=$PROJ/.env

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <https://xxx.trycloudflare.com>" >&2
  exit 2
fi

NEW_URL="$1"
# Strip trailing slash if user pasted one
NEW_URL="${NEW_URL%/}"

if [[ ! "$NEW_URL" =~ ^https://[a-z0-9-]+\.trycloudflare\.com$ ]]; then
  echo "Invalid tunnel URL: $NEW_URL" >&2
  echo "Expected: https://<subdomain>.trycloudflare.com" >&2
  exit 1
fi

# Replace tunnel URL on CORS_ORIGINS line (keep other origins intact)
sed -i -E "s#https://[a-z0-9-]+\.trycloudflare\.com#${NEW_URL}#g" "$ENV_FILE"

echo "Updated $ENV_FILE"
grep -i cors "$ENV_FILE"
echo

echo "Restarting lms-backend..."
if command -v sudo >/dev/null 2>&1; then
  sudo systemctl restart lms-backend
else
  systemctl restart lms-backend
fi

echo
echo "Backend now accepting requests from:"
echo "  $NEW_URL"
echo
echo "Update your MFE env var:"
echo "  NEXT_PUBLIC_API_URL=$NEW_URL"
