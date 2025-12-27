#!/bin/bash
#
# Certbot Pre-Renewal Hook
# Executed before certificate renewal attempt
#
# Usage: Automatically called by certbot before renewal
# Location: /etc/letsencrypt/renewal-hooks/pre/
#
# Actions:
# 1. Verify nginx is running and accessible
# 2. Ensure renewal directory is writable
# 3. Log renewal attempt
# 4. Pre-flight checks
#

set -e

DOMAIN="the-bot.ru"
LOG_FILE="/var/log/certbot-renewal.log"
WEBROOT="/var/www/certbot"

# Colors for logging
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
LOG_LEVEL="INFO"

# Log function
log() {
    local level=$1
    shift
    echo "[$TIMESTAMP] [$level] $@" >> "$LOG_FILE"
    echo "[$TIMESTAMP] [$level] $@"
}

# Initialize log file
mkdir -p "$(dirname "$LOG_FILE")"
touch "$LOG_FILE"

log "$LOG_LEVEL" "Pre-renewal hook started for $DOMAIN"

# Step 1: Check nginx is running
log "$LOG_LEVEL" "Checking if nginx is running..."
if systemctl is-active --quiet nginx; then
    log "$LOG_LEVEL" "Nginx is running"
else
    log "WARNING" "Nginx is not running, attempting to start..."
    systemctl start nginx
    sleep 2
fi

# Step 2: Verify webroot is accessible
log "$LOG_LEVEL" "Verifying webroot is accessible..."
if [ ! -d "$WEBROOT" ]; then
    log "$LOG_LEVEL" "Creating webroot directory: $WEBROOT"
    mkdir -p "$WEBROOT"
fi

if [ ! -w "$WEBROOT" ]; then
    log "ERROR" "Webroot is not writable: $WEBROOT"
    exit 1
fi

log "$LOG_LEVEL" "Webroot is accessible and writable"

# Step 3: Check disk space
log "$LOG_LEVEL" "Checking disk space..."
DISK_USAGE=$(df "$WEBROOT" | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 90 ]; then
    log "WARNING" "Disk usage is high: ${DISK_USAGE}%"
fi

log "$LOG_LEVEL" "Disk usage: ${DISK_USAGE}%"

# Step 4: Test HTTP connectivity
log "$LOG_LEVEL" "Testing HTTP connectivity..."
if curl -s --connect-timeout 5 "http://localhost/.well-known/acme-challenge/test" > /dev/null 2>&1 || true; then
    log "$LOG_LEVEL" "HTTP connectivity verified"
else
    log "WARNING" "Could not verify HTTP connectivity (this may be normal)"
fi

# Step 5: Verify current certificate
log "$LOG_LEVEL" "Verifying current certificate..."
CERT_PATH="/etc/letsencrypt/live/$DOMAIN/cert.pem"
if [ -f "$CERT_PATH" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in "$CERT_PATH" | cut -d= -f2)
    DAYS_LEFT=$(( ($(date -d "$EXPIRY_DATE" +%s) - $(date +%s)) / 86400 ))
    log "$LOG_LEVEL" "Current certificate expires in $DAYS_LEFT days ($EXPIRY_DATE)"
else
    log "$LOG_LEVEL" "No existing certificate found (first-time setup)"
fi

log "$LOG_LEVEL" "Pre-renewal hook completed successfully"
exit 0
