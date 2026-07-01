#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LISTENER="$SCRIPT_DIR/listener.py"
UNIT_DST="/etc/systemd/system/pacefinder.service"
SERVICE_USER="${SUDO_USER:-$USER}"

if [ ! -f "$LISTENER" ]; then
  echo "Error: listener.py not found at $LISTENER" >&2
  exit 1
fi

if ! command -v python3 >/dev/null; then
  echo "Error: python3 not found. Install it first." >&2
  exit 1
fi

# platformdirs is the one pip dep (storage-path fallback + frozen-build config dir).
if ! python3 -c "import platformdirs" 2>/dev/null; then
  echo "Installing platformdirs..."
  if command -v apt >/dev/null; then
    sudo apt install -y python3-platformdirs
  else
    python3 -m pip install --user 'platformdirs>=4.0'
  fi
fi

# Migrate off the pre-rename simtelemetry.service unit if present.
if systemctl list-unit-files 2>/dev/null | grep -q '^simtelemetry\.service'; then
  echo "Migrating old simtelemetry.service -> pacefinder.service..."
  sudo systemctl stop simtelemetry 2>/dev/null || true
  sudo systemctl disable simtelemetry 2>/dev/null || true
  sudo rm -f /etc/systemd/system/simtelemetry.service
fi

# Warn (don't block) if the configured storage_path lives under a mountpoint
# that isn't actually tracked by systemd/fstab -- RequiresMountsFor would be
# a silent no-op and writes would fall through to the SD card.
CONFIG_FILE="$SCRIPT_DIR/simtelemetry.config.json"
REQUIRES_MOUNT=""
if [ -f "$CONFIG_FILE" ]; then
  STORAGE_PATH="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('storage_path',''))" "$CONFIG_FILE" 2>/dev/null || true)"
  if [ -n "$STORAGE_PATH" ] && [[ "$STORAGE_PATH" == /mnt/* || "$STORAGE_PATH" == /media/* ]]; then
    MOUNT_ROOT="/$(echo "$STORAGE_PATH" | cut -d/ -f2-3)"
    if findmnt "$MOUNT_ROOT" >/dev/null 2>&1; then
      REQUIRES_MOUNT="RequiresMountsFor=$MOUNT_ROOT"
      echo "Detected external mount $MOUNT_ROOT for storage_path -- adding RequiresMountsFor."
    else
      echo "Warning: storage_path is under $MOUNT_ROOT but that isn't a tracked mountpoint" >&2
      echo "  (not in /etc/fstab / systemd). The service will start before it's mounted" >&2
      echo "  and telemetry will silently fall back to the SD card. Add it to /etc/fstab" >&2
      echo "  or fix storage_path in $CONFIG_FILE before relying on this." >&2
    fi
  fi
fi

echo "Writing $UNIT_DST (WorkingDirectory=$SCRIPT_DIR, User=$SERVICE_USER)..."
sudo tee "$UNIT_DST" > /dev/null <<EOF
[Unit]
Description=Pacefinder UDP Listener
After=network.target local-fs.target
${REQUIRES_MOUNT}

[Service]
Type=simple
User=$SERVICE_USER
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $LISTENER
Restart=always
RestartSec=5
StartLimitIntervalSec=0
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now pacefinder

echo "Waiting for listener to come up..."
STATUS_PORT="$(python3 -c "import json,sys; print(json.load(open(sys.argv[1])).get('status_port',8000))" "$CONFIG_FILE" 2>/dev/null || echo 8000)"
UP=""
for _ in $(seq 1 10); do
  if curl -fsS "http://localhost:${STATUS_PORT}/health" >/dev/null 2>&1; then
    UP=1
    break
  fi
  sleep 1
done

if [ -z "$UP" ]; then
  echo "Error: pacefinder did not respond on http://localhost:${STATUS_PORT}/health after 10s" >&2
  echo "--- systemctl status ---" >&2
  sudo systemctl status pacefinder --no-pager >&2 || true
  echo "--- recent logs ---" >&2
  sudo journalctl -u pacefinder --no-pager -n 20 >&2 || true
  exit 1
fi

echo
echo "Pacefinder installed and running."
echo "Dashboard: http://localhost:${STATUS_PORT}"
echo "Status:    sudo systemctl status pacefinder"
echo "Logs:      sudo journalctl -u pacefinder -f"
