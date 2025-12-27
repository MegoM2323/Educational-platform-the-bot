#!/bin/bash
#
# SSL/TLS Certificate Setup for THE BOT Platform
# Configures Let's Encrypt automatic certificate management with certbot
#
# Usage: sudo bash scripts/setup-ssl.sh [domain]
# Example: sudo bash scripts/setup-ssl.sh the-bot.ru
#
# This script:
# 1. Installs certbot and plugins
# 2. Creates certificate with Let's Encrypt
# 3. Configures automatic renewal
# 4. Sets up monitoring for expiration
# 5. Tests SSL/TLS configuration
#

set -e

DOMAIN="${1:-the-bot.ru}"
WEBROOT="/var/www/certbot"
CERTBOT_CONFIG="/etc/letsencrypt/renewal/$DOMAIN.conf"
CERTIFICATE_PATH="/etc/letsencrypt/live/$DOMAIN"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}THE BOT Platform - SSL/TLS Setup${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""
echo -e "${YELLOW}Domain:${NC} $DOMAIN"
echo -e "${YELLOW}Webroot:${NC} $WEBROOT"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}ERROR: This script must be run as root${NC}"
   echo "Usage: sudo bash scripts/setup-ssl.sh $DOMAIN"
   exit 1
fi

# Step 1: Install certbot
echo -e "${BLUE}[1/6] Installing certbot...${NC}"
apt-get update -qq
apt-get install -y certbot python3-certbot-nginx > /dev/null 2>&1
echo -e "${GREEN}✓ Certbot installed${NC}"

# Step 2: Create webroot directory
echo -e "${BLUE}[2/6] Creating webroot directory...${NC}"
mkdir -p "$WEBROOT"
chmod 755 "$WEBROOT"
echo -e "${GREEN}✓ Webroot created: $WEBROOT${NC}"

# Step 3: Request certificate
echo -e "${BLUE}[3/6] Requesting Let's Encrypt certificate...${NC}"
if [ -d "$CERTIFICATE_PATH" ]; then
    echo -e "${YELLOW}Certificate already exists at $CERTIFICATE_PATH${NC}"
    echo "Skipping certificate request..."
else
    certbot certonly \
        --webroot \
        -w "$WEBROOT" \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --email admin@$DOMAIN \
        --agree-tos \
        --non-interactive \
        --prefer-challenges=http \
        --register-unsafely-without-email || \
        certbot certonly \
        --webroot \
        -w "$WEBROOT" \
        -d "$DOMAIN" \
        -d "www.$DOMAIN" \
        --email admin@$DOMAIN \
        --agree-tos \
        --non-interactive \
        --preferred-challenges http
    echo -e "${GREEN}✓ Certificate obtained${NC}"
fi

# Step 4: Configure automatic renewal
echo -e "${BLUE}[4/6] Setting up automatic renewal...${NC}"

# Enable certbot timer (systemd)
systemctl enable certbot.timer > /dev/null 2>&1
systemctl start certbot.timer > /dev/null 2>&1
echo -e "${GREEN}✓ Certbot timer enabled (renewal check: twice daily)${NC}"

# Create renewal hook for nginx reload
RENEWAL_HOOKS_DIR="/etc/letsencrypt/renewal-hooks/post"
mkdir -p "$RENEWAL_HOOKS_DIR"

cat > "$RENEWAL_HOOKS_DIR/nginx-reload.sh" << 'EOF'
#!/bin/bash
# Reload nginx after certificate renewal
systemctl reload nginx
exit 0
EOF

chmod +x "$RENEWAL_HOOKS_DIR/nginx-reload.sh"
echo -e "${GREEN}✓ Renewal hook configured (nginx will auto-reload)${NC}"

# Step 5: Verify certificate
echo -e "${BLUE}[5/6] Verifying certificate...${NC}"

if [ -f "$CERTIFICATE_PATH/cert.pem" ]; then
    echo -e "${GREEN}✓ Certificate found${NC}"
    echo ""
    echo "Certificate details:"
    openssl x509 -in "$CERTIFICATE_PATH/cert.pem" -text -noout | grep -E "Subject:|Issuer:|Not Before|Not After"
    echo ""
else
    echo -e "${RED}ERROR: Certificate not found at $CERTIFICATE_PATH/cert.pem${NC}"
    exit 1
fi

# Step 6: Test SSL configuration
echo -e "${BLUE}[6/6] Testing SSL/TLS configuration...${NC}"

if command -v nginx &> /dev/null; then
    nginx -t > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
        echo -e "${YELLOW}To apply changes, run:${NC} sudo systemctl reload nginx"
    else
        echo -e "${RED}ERROR: Nginx configuration is invalid${NC}"
        nginx -t
        exit 1
    fi
else
    echo -e "${YELLOW}⚠ Nginx not found (cannot test configuration)${NC}"
fi

# Summary
echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}SSL/TLS Setup Complete!${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo "Next steps:"
echo "1. Review nginx configuration:"
echo "   cat /etc/nginx/sites-available/$DOMAIN"
echo ""
echo "2. Reload nginx:"
echo "   sudo systemctl reload nginx"
echo ""
echo "3. Test SSL/TLS with:"
echo "   openssl s_client -connect $DOMAIN:443 -tls1_2"
echo ""
echo "4. Test online with SSL Labs:"
echo "   https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
echo ""
echo "5. Monitor certificate expiration:"
echo "   certbot certificates"
echo ""
echo "6. Test renewal process:"
echo "   sudo certbot renew --dry-run"
echo ""
echo "Certificate will auto-renew 30 days before expiration."
echo "Renewal check runs twice daily via systemd timer."
echo ""
