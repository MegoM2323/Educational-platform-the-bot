#!/bin/bash

################################################################################
# Install systemd services for THE_BOT Platform
# Usage: sudo bash install-systemd-services.sh
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICES_DIR="$SCRIPT_DIR"

echo "Installing systemd services for THE_BOT Platform..."

# Copy service files to systemd directory
sudo cp "$SERVICES_DIR/thebot-backend.service" /etc/systemd/system/
sudo cp "$SERVICES_DIR/thebot-celery-worker.service" /etc/systemd/system/
sudo cp "$SERVICES_DIR/thebot-celery-beat.service" /etc/systemd/system/

# Set correct permissions
sudo chmod 644 /etc/systemd/system/thebot-*.service

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable services
sudo systemctl enable thebot-backend
sudo systemctl enable thebot-celery-worker
sudo systemctl enable thebot-celery-beat

echo "✓ Services installed successfully"
echo ""
echo "Available commands:"
echo "  sudo systemctl start thebot-backend"
echo "  sudo systemctl stop thebot-backend"
echo "  sudo systemctl restart thebot-backend"
echo "  sudo systemctl status thebot-backend"
echo ""
echo "  sudo journalctl -u thebot-backend -f"
echo "  sudo journalctl -u thebot-celery-worker -f"
echo "  sudo journalctl -u thebot-celery-beat -f"
