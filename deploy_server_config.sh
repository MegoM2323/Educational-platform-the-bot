#!/bin/bash

# THE BOT Platform - Production Server Configuration Deployment Script
# This script sets up nginx, Celery, and systemd services
# Usage: sudo ./deploy_server_config.sh

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Paths
PROJECT_DIR="/home/mg/THE_BOT_platform"
NGINX_SRC="$PROJECT_DIR/nginx/the-bot.ru.conf"
NGINX_DEST="/etc/nginx/sites-available/the-bot.ru"
NGINX_ENABLED="/etc/nginx/sites-enabled/the-bot.ru"
CELERY_WORKER_SRC="$PROJECT_DIR/systemd/the-bot-celery-worker.service"
CELERY_BEAT_SRC="$PROJECT_DIR/systemd/the-bot-celery-beat.service"
CELERY_WORKER_DEST="/etc/systemd/system/the-bot-celery-worker.service"
CELERY_BEAT_DEST="/etc/systemd/system/the-bot-celery-beat.service"

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ This script must be run as root (use sudo)${NC}"
    exit 1
fi

echo "================================================"
echo "THE BOT Platform - Server Configuration Deployment"
echo "================================================"
echo ""

# 1. Check dependencies
echo -e "${YELLOW}[1/7] Checking dependencies...${NC}"

if ! command -v nginx &> /dev/null; then
    echo -e "${RED}❌ Nginx is not installed${NC}"
    echo "Install: sudo apt-get install nginx"
    exit 1
fi
echo "✓ Nginx found"

if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 is not installed${NC}"
    exit 1
fi
echo "✓ Python3 found"

# 2. Create necessary directories and logs
echo ""
echo -e "${YELLOW}[2/7] Creating directories and log files...${NC}"

# Celery logs directory
if [ ! -d "/var/log/celery" ]; then
    mkdir -p /var/log/celery
    chown www-data:www-data /var/log/celery
    chmod 755 /var/log/celery
    echo "✓ Created /var/log/celery"
else
    chown www-data:www-data /var/log/celery
    echo "✓ /var/log/celery exists"
fi

# Celery PID directory
if [ ! -d "/var/run/celery" ]; then
    mkdir -p /var/run/celery
    chown www-data:www-data /var/run/celery
    chmod 755 /var/run/celery
    echo "✓ Created /var/run/celery"
else
    chown www-data:www-data /var/run/celery
    echo "✓ /var/run/celery exists"
fi

# 3. Deploy Nginx configuration
echo ""
echo -e "${YELLOW}[3/7] Deploying Nginx configuration...${NC}"

if [ ! -f "$NGINX_SRC" ]; then
    echo -e "${RED}❌ Nginx config not found: $NGINX_SRC${NC}"
    exit 1
fi

cp "$NGINX_SRC" "$NGINX_DEST"
echo "✓ Copied Nginx config to $NGINX_DEST"

# Test Nginx configuration
if ! nginx -t &> /dev/null; then
    echo -e "${RED}❌ Nginx configuration test failed!${NC}"
    nginx -t
    exit 1
fi
echo "✓ Nginx configuration is valid"

# 4. Deploy Celery systemd services
echo ""
echo -e "${YELLOW}[4/7] Deploying Celery systemd services...${NC}"

if [ ! -f "$CELERY_WORKER_SRC" ]; then
    echo -e "${RED}❌ Celery worker service not found: $CELERY_WORKER_SRC${NC}"
    exit 1
fi

if [ ! -f "$CELERY_BEAT_SRC" ]; then
    echo -e "${RED}❌ Celery beat service not found: $CELERY_BEAT_SRC${NC}"
    exit 1
fi

cp "$CELERY_WORKER_SRC" "$CELERY_WORKER_DEST"
cp "$CELERY_BEAT_SRC" "$CELERY_BEAT_DEST"
echo "✓ Deployed Celery services"

# Reload systemd
systemctl daemon-reload
echo "✓ Systemd daemon reloaded"

# 5. Setup Redis
echo ""
echo -e "${YELLOW}[5/7] Setting up Redis...${NC}"

if ! command -v redis-cli &> /dev/null; then
    echo -e "${YELLOW}⚠ Redis is not installed, installing...${NC}"
    apt-get update
    apt-get install -y redis-server
    echo "✓ Redis installed"
else
    echo "✓ Redis already installed"
fi

# Ensure Redis is running and enabled
systemctl enable redis-server
systemctl start redis-server
echo "✓ Redis enabled and started"

# Test Redis
if ! redis-cli ping &> /dev/null; then
    echo -e "${RED}❌ Redis is not responding${NC}"
    exit 1
fi
echo "✓ Redis connection verified"

# 6. Enable and start services
echo ""
echo -e "${YELLOW}[6/7] Enabling and starting services...${NC}"

# Enable services
systemctl enable the-bot-celery-worker.service
systemctl enable the-bot-celery-beat.service
echo "✓ Services enabled for auto-start on boot"

# Stop old instances if running
systemctl stop the-bot-celery-worker.service 2>/dev/null || true
systemctl stop the-bot-celery-beat.service 2>/dev/null || true
sleep 2

# Start services
systemctl start the-bot-celery-worker.service
systemctl start the-bot-celery-beat.service
echo "✓ Services started"

# Verify services
sleep 2

WORKER_STATUS=$(systemctl is-active the-bot-celery-worker.service)
BEAT_STATUS=$(systemctl is-active the-bot-celery-beat.service)

if [ "$WORKER_STATUS" = "active" ]; then
    echo "✓ Celery worker is running"
else
    echo -e "${RED}❌ Celery worker is not running${NC}"
    systemctl status the-bot-celery-worker.service
fi

if [ "$BEAT_STATUS" = "active" ]; then
    echo "✓ Celery beat is running"
else
    echo -e "${RED}❌ Celery beat is not running${NC}"
    systemctl status the-bot-celery-beat.service
fi

# 7. Reload Nginx
echo ""
echo -e "${YELLOW}[7/7] Reloading Nginx...${NC}"

systemctl reload nginx
echo "✓ Nginx reloaded"

# Summary
echo ""
echo "================================================"
echo -e "${GREEN}✓ Server configuration deployed successfully!${NC}"
echo "================================================"
echo ""
echo "📋 DEPLOYMENT SUMMARY:"
echo "  ✓ Nginx configuration deployed for the-bot.ru"
echo "  ✓ Celery worker service installed"
echo "  ✓ Celery beat service installed"
echo "  ✓ Redis verified and running"
echo "  ✓ All services enabled for auto-start"
echo ""
echo "🔧 NEXT STEPS:"
echo ""
echo "1. CRITICAL: Update YooKassa webhook URL"
echo "   In YooKassa dashboard, set webhook URL to:"
echo "   ${YELLOW}https://the-bot.ru/yookassa-webhook/${NC}"
echo "   (Note the trailing slash)"
echo ""
echo "2. Verify services are running:"
echo "   ${YELLOW}sudo systemctl status the-bot-celery-worker.service${NC}"
echo "   ${YELLOW}sudo systemctl status the-bot-celery-beat.service${NC}"
echo ""
echo "3. Check logs:"
echo "   ${YELLOW}sudo journalctl -u the-bot-celery-worker.service -n 100 -f${NC}"
echo "   ${YELLOW}sudo journalctl -u the-bot-celery-beat.service -n 100 -f${NC}"
echo "   ${YELLOW}sudo tail -f /var/log/nginx/the-bot-error.log${NC}"
echo ""
echo "4. Verify media files are working:"
echo "   Try uploading and opening a file from the admin panel"
echo ""
echo "5. Test payment webhook:"
echo "   Create a test payment in YooKassa dashboard"
echo "   Check if payment appears in Django admin"
echo "   Check logs: ${YELLOW}sudo journalctl -u the-bot-celery-worker.service -f${NC}"
echo ""
echo "📖 SERVICE MANAGEMENT:"
echo ""
echo "Start service:   ${YELLOW}sudo systemctl start the-bot-celery-worker.service${NC}"
echo "Stop service:    ${YELLOW}sudo systemctl stop the-bot-celery-worker.service${NC}"
echo "Restart service: ${YELLOW}sudo systemctl restart the-bot-celery-worker.service${NC}"
echo "View logs:       ${YELLOW}sudo journalctl -u the-bot-celery-worker.service -f${NC}"
echo ""
echo "Same commands apply to 'the-bot-celery-beat.service'"
echo ""
echo "================================================"
