#!/bin/bash
#
# Certbot Post-Renewal Hook
# Executed after successful certificate renewal
#
# Usage: Automatically called by certbot after renewal
# Location: /etc/letsencrypt/renewal-hooks/post/
#
# Actions:
# 1. Validate nginx configuration
# 2. Reload nginx (graceful restart)
# 3. Log renewal event
# 4. Send notification (optional)
#

set -e

DOMAIN="the-bot.ru"
LOG_FILE="/var/log/certbot-renewal.log"
NGINX_CONFIG="/etc/nginx/sites-available/the-bot.ru"

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

log "$LOG_LEVEL" "Post-renewal hook started for $DOMAIN"

# Step 1: Validate nginx configuration
log "$LOG_LEVEL" "Validating nginx configuration..."
if nginx -t 2>&1 | tee -a "$LOG_FILE" | grep -q "successful"; then
    log "$LOG_LEVEL" "Nginx configuration is valid"
else
    log "ERROR" "Nginx configuration is invalid"
    exit 1
fi

# Step 2: Reload nginx
log "$LOG_LEVEL" "Reloading nginx..."
if systemctl reload nginx 2>&1 | tee -a "$LOG_FILE"; then
    log "$LOG_LEVEL" "Nginx reloaded successfully"
else
    log "ERROR" "Failed to reload nginx"
    exit 1
fi

# Step 3: Verify certificate is in use
log "$LOG_LEVEL" "Verifying certificate..."
if [ -f "/etc/letsencrypt/live/$DOMAIN/cert.pem" ]; then
    EXPIRY_DATE=$(openssl x509 -enddate -noout -in "/etc/letsencrypt/live/$DOMAIN/cert.pem" | cut -d= -f2)
    log "$LOG_LEVEL" "Certificate valid until: $EXPIRY_DATE"
else
    log "ERROR" "Certificate not found"
    exit 1
fi

# Step 4: Send notification (optional)
# Uncomment to enable notifications
# HOSTNAME=$(hostname)
# SUBJECT="Certificate Renewed: $DOMAIN on $HOSTNAME"
# MESSAGE="The certificate for $DOMAIN was successfully renewed on $HOSTNAME at $TIMESTAMP. Nginx has been reloaded."
# echo "$MESSAGE" | mail -s "$SUBJECT" admin@example.com

log "$LOG_LEVEL" "Post-renewal hook completed successfully"
exit 0
