#!/bin/bash
#
# SSL/TLS Certificate Monitoring and Renewal Management
# Monitors certificate expiration and triggers alerts
#
# Usage: bash scripts/ssl-monitor.sh [check|renew-dry|renew|status]
# Examples:
#   bash scripts/ssl-monitor.sh check       # Check all certificates
#   bash scripts/ssl-monitor.sh status      # Show certificate details
#   bash scripts/ssl-monitor.sh renew-dry   # Test renewal without applying
#   bash scripts/ssl-monitor.sh renew       # Force renewal
#
# Can be run as cron job:
#   0 0 * * * /path/to/scripts/ssl-monitor.sh check >> /var/log/ssl-monitor.log 2>&1
#

set -e

COMMAND="${1:-check}"
ALERT_DAYS=30
CRITICAL_DAYS=7
CERTIFICATE_DIR="/etc/letsencrypt/live"
LOG_FILE="${LOG_FILE:-/var/log/ssl-monitor.log}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
ORANGE='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Initialize log
mkdir -p "$(dirname "$LOG_FILE")"

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" >> "$LOG_FILE"
}

check_expiration() {
    local domain=$1
    local cert_path="$CERTIFICATE_DIR/$domain/cert.pem"

    if [ ! -f "$cert_path" ]; then
        echo -e "${RED}✗ Certificate not found: $cert_path${NC}"
        log "ERROR" "Certificate not found: $cert_path"
        return 1
    fi

    # Get expiration date
    local expiration_date=$(openssl x509 -enddate -noout -in "$cert_path" | cut -d= -f2)
    local expiration_epoch=$(date -d "$expiration_date" +%s)
    local now_epoch=$(date +%s)
    local days_left=$(( ($expiration_epoch - $now_epoch) / 86400 ))

    # Determine status
    if [ $days_left -lt 0 ]; then
        echo -e "${RED}✗ EXPIRED${NC}: $domain (expired $((days_left * -1)) days ago)"
        log "CRITICAL" "$domain: Certificate EXPIRED $((days_left * -1)) days ago"
        return 2
    elif [ $days_left -lt $CRITICAL_DAYS ]; then
        echo -e "${RED}✗ CRITICAL${NC}: $domain ($days_left days until expiration)"
        log "CRITICAL" "$domain: Certificate expires in $days_left days"
        return 1
    elif [ $days_left -lt $ALERT_DAYS ]; then
        echo -e "${YELLOW}⚠ WARNING${NC}: $domain ($days_left days until expiration)"
        log "WARNING" "$domain: Certificate expires in $days_left days"
        return 0
    else
        echo -e "${GREEN}✓ OK${NC}: $domain ($days_left days until expiration)"
        log "INFO" "$domain: Certificate valid for $days_left days"
        return 0
    fi
}

show_certificate_info() {
    local domain=$1
    local cert_path="$CERTIFICATE_DIR/$domain/cert.pem"

    if [ ! -f "$cert_path" ]; then
        echo -e "${RED}Certificate not found: $cert_path${NC}"
        return 1
    fi

    echo ""
    echo -e "${BLUE}Certificate Information: $domain${NC}"
    echo "=================================="
    openssl x509 -in "$cert_path" -text -noout | grep -E "Subject:|Issuer:|Not Before|Not After|Public-Key:" | sed 's/^/  /'

    # Show certificate chain
    local chain_path="$CERTIFICATE_DIR/$domain/chain.pem"
    if [ -f "$chain_path" ]; then
        echo ""
        echo -e "${BLUE}Certificate Chain:${NC}"
        local count=$(grep "BEGIN CERTIFICATE" "$chain_path" | wc -l)
        echo "  Certificates in chain: $count"
    fi

    # Show full chain
    local fullchain_path="$CERTIFICATE_DIR/$domain/fullchain.pem"
    if [ -f "$fullchain_path" ]; then
        echo ""
        echo -e "${BLUE}Full Chain Details:${NC}"
        openssl x509 -in "$fullchain_path" -text -noout | grep -E "Subject:|Issuer:" | head -4 | sed 's/^/  /'
    fi
}

check_ocsp() {
    local domain=$1
    local cert_path="$CERTIFICATE_DIR/$domain/cert.pem"
    local chain_path="$CERTIFICATE_DIR/$domain/chain.pem"

    if [ ! -f "$cert_path" ] || [ ! -f "$chain_path" ]; then
        echo -e "${YELLOW}⚠ Cannot check OCSP (certificate files not found)${NC}"
        return 1
    fi

    echo ""
    echo -e "${BLUE}OCSP Status Check:${NC}"

    # Extract OCSP responder URL
    local ocsp_url=$(openssl x509 -ocsp_uri -noout -in "$cert_path")
    if [ -z "$ocsp_url" ]; then
        echo -e "${YELLOW}  No OCSP responder configured${NC}"
        return 0
    fi

    echo "  OCSP Responder: $ocsp_url"

    # Check OCSP status
    if openssl ocsp -no_nonce -issuer "$chain_path" -cert "$cert_path" \
        -url "$ocsp_url" 2>/dev/null | grep -q "good"; then
        echo -e "${GREEN}  Status: Good (certificate valid)${NC}"
        return 0
    else
        echo -e "${YELLOW}  Status: Could not verify via OCSP${NC}"
        return 0
    fi
}

verify_chain() {
    local domain=$1
    local fullchain_path="$CERTIFICATE_DIR/$domain/fullchain.pem"

    if [ ! -f "$fullchain_path" ]; then
        echo -e "${YELLOW}⚠ Cannot verify chain (fullchain.pem not found)${NC}"
        return 1
    fi

    echo ""
    echo -e "${BLUE}Certificate Chain Verification:${NC}"

    if openssl verify -CAfile "$fullchain_path" "$fullchain_path" > /dev/null 2>&1; then
        echo -e "${GREEN}  ✓ Chain verified successfully${NC}"
        return 0
    else
        echo -e "${YELLOW}  ⚠ Chain verification warning${NC}"
        return 0
    fi
}

# Command: check (default)
cmd_check() {
    echo -e "${BLUE}Checking SSL/TLS Certificates${NC}"
    echo "=============================="

    if [ ! -d "$CERTIFICATE_DIR" ]; then
        echo -e "${RED}Certificate directory not found: $CERTIFICATE_DIR${NC}"
        log "ERROR" "Certificate directory not found: $CERTIFICATE_DIR"
        return 1
    fi

    local exit_code=0

    # Check all domains in certificate directory
    if ls "$CERTIFICATE_DIR" > /dev/null 2>&1; then
        for domain_dir in "$CERTIFICATE_DIR"/*; do
            if [ -d "$domain_dir" ]; then
                local domain=$(basename "$domain_dir")
                check_expiration "$domain" || exit_code=$?
            fi
        done
    else
        echo -e "${YELLOW}No certificates found${NC}"
        exit_code=1
    fi

    echo ""
    echo "Timestamp: $(date '+%Y-%m-%d %H:%M:%S')"

    return $exit_code
}

# Command: status
cmd_status() {
    echo -e "${BLUE}SSL/TLS Certificate Status Report${NC}"
    echo "===================================="

    if [ ! -d "$CERTIFICATE_DIR" ]; then
        echo -e "${RED}Certificate directory not found: $CERTIFICATE_DIR${NC}"
        return 1
    fi

    for domain_dir in "$CERTIFICATE_DIR"/*; do
        if [ -d "$domain_dir" ]; then
            local domain=$(basename "$domain_dir")
            echo ""
            echo -e "${BLUE}Domain: $domain${NC}"
            echo "---"
            check_expiration "$domain"
            show_certificate_info "$domain"
            check_ocsp "$domain"
            verify_chain "$domain"
        fi
    done
}

# Command: renew-dry
cmd_renew_dry() {
    echo -e "${BLUE}Testing Certificate Renewal (Dry Run)${NC}"
    echo "======================================"
    echo ""

    if command -v certbot &> /dev/null; then
        certbot renew --dry-run --non-interactive
        log "INFO" "Dry-run renewal test completed"
    else
        echo -e "${RED}ERROR: certbot not found${NC}"
        log "ERROR" "certbot not found"
        return 1
    fi
}

# Command: renew
cmd_renew() {
    echo -e "${BLUE}Renewing Certificates${NC}"
    echo "======================"
    echo ""

    if command -v certbot &> /dev/null; then
        certbot renew --non-interactive

        # Reload nginx if running
        if systemctl is-active --quiet nginx; then
            echo ""
            echo "Reloading nginx..."
            systemctl reload nginx
            echo -e "${GREEN}✓ Nginx reloaded${NC}"
        fi

        log "INFO" "Certificate renewal completed"
    else
        echo -e "${RED}ERROR: certbot not found${NC}"
        log "ERROR" "certbot not found"
        return 1
    fi
}

# Main
case "$COMMAND" in
    check)
        cmd_check
        ;;
    status)
        cmd_status
        ;;
    renew-dry)
        if [ $EUID -ne 0 ]; then
            echo "ERROR: renew-dry requires root access"
            exit 1
        fi
        cmd_renew_dry
        ;;
    renew)
        if [ $EUID -ne 0 ]; then
            echo "ERROR: renew requires root access"
            exit 1
        fi
        cmd_renew
        ;;
    *)
        echo "Usage: $0 [check|status|renew-dry|renew]"
        echo ""
        echo "Commands:"
        echo "  check       - Check certificate expiration (default)"
        echo "  status      - Show detailed certificate information"
        echo "  renew-dry   - Test renewal without applying changes"
        echo "  renew       - Renew certificates (requires root)"
        echo ""
        echo "Environment variables:"
        echo "  LOG_FILE    - Log file path (default: /var/log/ssl-monitor.log)"
        exit 1
        ;;
esac
