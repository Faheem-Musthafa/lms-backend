#!/usr/bin/env bash
# Install the auto-deploy poller as a user-level systemd timer.
# Run once as faheem (no sudo needed for the timer itself, but we'll add a
# sudoers snippet so the script can restart lms-backend without a password).
set -euo pipefail

PROJ=/home/faheem/lincole/lms-backend
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
USER_DIR="$HOME/.config/systemd/user"
SUDOERS_FILE="/etc/sudoers.d/lms-auto-deploy"

mkdir -p "$USER_DIR"

# 1. Install units
install -m 0644 "$SCRIPT_DIR/lms-auto-deploy.service" "$USER_DIR/lms-auto-deploy.service"
install -m 0644 "$SCRIPT_DIR/lms-auto-deploy.timer"    "$USER_DIR/lms-auto-deploy.timer"
chmod +x "$SCRIPT_DIR/auto-deploy.sh"

# 2. Password-less sudo for the deploy script to restart lms-backend.
#    (The auto-deploy service runs as faheem; it needs to touch a system unit.)
if [[ $EUID -ne 0 ]]; then
  echo "[!] Need sudo once to install the sudoers snippet:"
  SUDOERS_LINE="faheem ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart lms-backend, /usr/bin/systemctl reload lms-backend, /usr/bin/systemctl status lms-backend"
  echo "    $SUDOERS_LINE"
  echo "$SUDOERS_LINE" | sudo tee "$SUDOERS_FILE" > /dev/null
  sudo chmod 0440 "$SUDOERS_FILE"
else
  SUDOERS_LINE="faheem ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart lms-backend, /usr/bin/systemctl reload lms-backend, /usr/bin/systemctl status lms-backend"
  echo "$SUDOERS_LINE" > "$SUDOERS_FILE"
  chmod 0440 "$SUDOERS_FILE"
fi

# 3. Enable lingering so the user timer runs even when faheem isn't logged in
loginctl enable-linger faheem 2>/dev/null || echo "(loginctl linger skipped — may need sudo)"

# 4. Reload user systemd + enable timer
systemctl --user daemon-reload
systemctl --user enable --now lms-auto-deploy.timer

echo
echo "Installed. Timer fires every 5 min."
echo "  status:  systemctl --user list-timers lms-auto-deploy.timer"
echo "  logs:    tail -f $PROJ/deploy/deploy.log"
echo "  run now: systemctl --user start lms-auto-deploy.service"
echo "  disable: systemctl --user disable --now lms-auto-deploy.timer"
