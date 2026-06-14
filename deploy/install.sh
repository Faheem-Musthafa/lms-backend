#!/usr/bin/env bash
# Deploy LMS backend behind nginx on lms.local:80.
# Run as root (or with sudo):  sudo ./deploy/install.sh
set -euo pipefail

PROJ=/home/faheem/lincole/lms-backend
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $EUID -ne 0 ]]; then
  echo "Run with sudo: sudo $0" >&2
  exit 1
fi

echo "[1/4] Install nginx if missing"
command -v nginx >/dev/null 2>&1 || pacman -S --noconfirm nginx

echo "[2/4] Install systemd unit"
install -m 0644 "$SCRIPT_DIR/lms-backend.service" /etc/systemd/system/lms-backend.service
systemctl daemon-reload

echo "[3/4] Install nginx config"
mkdir -p /etc/nginx/conf.d
install -m 0644 "$SCRIPT_DIR/lms-backend.nginx.conf" /etc/nginx/conf.d/lms-backend.conf
# Arch default nginx.conf doesn't include conf.d/*.conf — patch it once.
if ! grep -q 'include[[:space:]]*conf\.d/\*\.conf' /etc/nginx/nginx.conf; then
  cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak.$(date +%s)
  # Insert inside http { ... } block, right after "include mime.types;"
  sed -i '/include[[:space:]]*mime\.types;/a\    include       conf.d/*.conf;' /etc/nginx/nginx.conf
  echo "    patched /etc/nginx/nginx.conf to include conf.d/*.conf (backup kept)"
fi
nginx -t

echo "[4/4] Add lms.local to /etc/hosts if missing"
if ! grep -q 'lms\.local' /etc/hosts; then
  echo "127.0.0.1   lms.local" >> /etc/hosts
  echo "::1         lms.local" >> /etc/hosts
fi

echo "[5/5] Enable services"
systemctl enable --now nginx
systemctl enable --now lms-backend

echo
echo "Deployed. Test:  curl http://lms.local/health"
