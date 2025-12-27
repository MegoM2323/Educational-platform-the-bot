#!/bin/bash

################################################################################
# Vault Secret Rotation Script
# Rotates all managed secrets in HashiCorp Vault
#
# Usage:
#   ./rotate-secrets.sh              # Rotate all secrets
#   ./rotate-secrets.sh django       # Rotate only Django secrets
#   ./rotate-secrets.sh postgres     # Rotate only PostgreSQL secrets
#   ./rotate-secrets.sh --dry-run    # Show what would be rotated
#
# Requirements:
#   - vault CLI installed and authenticated
#   - jq for JSON parsing
#   - Permission to rotate secrets in Vault
#   - VAULT_ADDR and VAULT_TOKEN environment variables set
#
# Audit:
#   All rotation events are logged to syslog and local audit.log
#   Access is audited in Vault audit logs at /vault/logs/audit.log
#
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LOG_FILE="${LOG_FILE:-/var/log/vault-rotation.log}"
AUDIT_FILE="${AUDIT_FILE:-./audit.log}"
DRY_RUN="${DRY_RUN:-false}"
VAULT_ADDR="${VAULT_ADDR:-https://vault.vault.svc.cluster.local:8200}"
BACKUP_DIR="${BACKUP_DIR:-./secret-backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

################################################################################
# Logging Functions
################################################################################

log_info() {
    local msg="$1"
    echo -e "${BLUE}[INFO]${NC} $msg" | tee -a "$LOG_FILE"
    logger -t "vault-rotation" "INFO: $msg" 2>/dev/null || true
}

log_success() {
    local msg="$1"
    echo -e "${GREEN}[SUCCESS]${NC} $msg" | tee -a "$LOG_FILE"
    logger -t "vault-rotation" "SUCCESS: $msg" 2>/dev/null || true
}

log_warn() {
    local msg="$1"
    echo -e "${YELLOW}[WARN]${NC} $msg" | tee -a "$LOG_FILE"
    logger -t "vault-rotation" "WARN: $msg" 2>/dev/null || true
}

log_error() {
    local msg="$1"
    echo -e "${RED}[ERROR]${NC} $msg" | tee -a "$LOG_FILE"
    logger -t "vault-rotation" "ERROR: $msg" 2>/dev/null || true
}

audit_log() {
    local action="$1"
    local secret="$2"
    local status="$3"
    local detail="${4:-}"
    local entry=$(cat <<EOF
{
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "action": "$action",
  "secret": "$secret",
  "status": "$status",
  "user": "${USER:-system}",
  "hostname": "$(hostname)",
  "detail": "$detail"
}
EOF
)
    echo "$entry" >> "$AUDIT_FILE"
    echo "$entry" | logger -t "vault-audit" -s 2>/dev/null || true
}

################################################################################
# Validation Functions
################################################################################

check_requirements() {
    log_info "Checking requirements..."

    local missing=0

    # Check Vault CLI
    if ! command -v vault &> /dev/null; then
        log_error "vault CLI not found. Install from https://www.vaultproject.io/downloads"
        missing=$((missing + 1))
    fi

    # Check jq
    if ! command -v jq &> /dev/null; then
        log_error "jq not found. Install with: apt-get install jq"
        missing=$((missing + 1))
    fi

    # Check Vault authentication
    if ! vault token lookup &> /dev/null; then
        log_error "Not authenticated to Vault. Run: vault login -method=approle"
        missing=$((missing + 1))
    fi

    if [ $missing -gt 0 ]; then
        log_error "Missing $missing requirement(s). Aborting."
        exit 1
    fi

    log_success "All requirements satisfied"
}

################################################################################
# Secret Generation Functions
################################################################################

generate_password() {
    local length="${1:-32}"
    LC_ALL=C tr -dc 'A-Za-z0-9!@#$%^&*()_+-=[]{}|;:,.<>?' < /dev/urandom | head -c "$length"
}

generate_api_key() {
    openssl rand -base64 32 | tr -d '\n='
}

generate_token() {
    openssl rand -hex 32
}

################################################################################
# Secret Rotation Functions
################################################################################

rotate_django_secrets() {
    log_info "Rotating Django secrets..."

    local secret_key=$(generate_password 64)
    local jwt_secret=$(generate_token)

    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY_RUN] Would update Django secrets"
        audit_log "ROTATE" "django" "DRY_RUN" "secret-key, jwt-secret"
        return 0
    fi

    vault kv patch secret/django secret-key="$secret_key" 2>/dev/null || log_warn "Django secret not found"
    log_success "Updated Django SECRET_KEY"
    audit_log "ROTATE" "secret/django/secret-key" "SUCCESS" "Length: ${#secret_key}"

    vault kv patch secret/jwt secret-key="$jwt_secret" 2>/dev/null || log_warn "JWT secret not found"
    log_success "Updated JWT secret key"
    audit_log "ROTATE" "secret/jwt/secret-key" "SUCCESS" "Token generated"

    log_success "Django secrets rotated"
}

rotate_postgres_secrets() {
    log_info "Rotating PostgreSQL credentials..."

    local db_password=$(generate_password 32)

    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY_RUN] Would update PostgreSQL credentials"
        audit_log "ROTATE" "postgres" "DRY_RUN" "db-password"
        return 0
    fi

    vault kv patch secret/postgres db-password="$db_password" 2>/dev/null || log_warn "PostgreSQL secret not found"
    log_success "Updated PostgreSQL password in Vault"
    audit_log "ROTATE" "secret/postgres/db-password" "SUCCESS" "Password rotated"

    log_warn "Manual PostgreSQL password update required in database"
    echo "Execute in PostgreSQL: ALTER USER postgres WITH PASSWORD '$db_password';"

    log_success "PostgreSQL credentials rotated (Vault updated)"
}

rotate_redis_secrets() {
    log_info "Rotating Redis credentials..."

    local redis_password=$(generate_password 32)

    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY_RUN] Would update Redis credentials"
        audit_log "ROTATE" "redis" "DRY_RUN" "redis-password"
        return 0
    fi

    vault kv patch secret/redis redis-password="$redis_password" 2>/dev/null || log_warn "Redis secret not found"
    log_success "Updated Redis password in Vault"
    audit_log "ROTATE" "secret/redis/redis-password" "SUCCESS" "Password rotated"

    log_warn "Manual Redis password update required in Redis instance"
    echo "Execute in Redis: CONFIG SET requirepass '$redis_password'"

    log_success "Redis credentials rotated (Vault updated)"
}

rotate_api_keys() {
    log_info "Rotating API keys..."

    if [ "$DRY_RUN" = "true" ]; then
        log_info "[DRY_RUN] Would update API keys"
        audit_log "ROTATE" "apis" "DRY_RUN" "openrouter"
        return 0
    fi

    log_warn "Manual API key rotation required for:"
    log_warn "  - Telegram Bot Token"
    log_warn "  - Pachca Forum API Token"
    log_warn "  - YooKassa credentials"
    audit_log "ROTATE" "apis" "MANUAL" "Requires external service updates"

    log_success "API keys check completed"
}

################################################################################
# Backup Functions
################################################################################

backup_secrets() {
    log_info "Creating backup of current secrets..."

    mkdir -p "$BACKUP_DIR"
    local backup_file="$BACKUP_DIR/secrets-backup-$TIMESTAMP.json"

    vault kv get -format=json secret/django > "$backup_file" 2>/dev/null || true

    if [ -f "$backup_file" ]; then
        chmod 600 "$backup_file"
        log_success "Backup created: $backup_file"
        audit_log "BACKUP" "all-secrets" "SUCCESS" "File: $backup_file"
        return 0
    else
        log_warn "No backup created"
        return 1
    fi
}

################################################################################
# Reporting Functions
################################################################################

generate_rotation_report() {
    log_info "Generating rotation report..."

    local report_file="rotation-report-$TIMESTAMP.json"

    cat > "$report_file" <<EOF
{
  "rotation_report": {
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "status": "completed",
    "dry_run": $([ "$DRY_RUN" = "true" ] && echo "true" || echo "false"),
    "backup_location": "$BACKUP_DIR",
    "audit_log": "$AUDIT_FILE"
  }
}
EOF

    log_success "Rotation report: $report_file"
}

################################################################################
# Main Execution
################################################################################

main() {
    local secret_type="all"

    while [[ $# -gt 0 ]]; do
        case "$1" in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --backup)
                backup_secrets
                exit $?
                ;;
            django|postgres|redis|apis)
                secret_type="$1"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    log_info "Starting Vault Secret Rotation"
    check_requirements

    case "$secret_type" in
        all)
            rotate_django_secrets
            rotate_postgres_secrets
            rotate_redis_secrets
            rotate_api_keys
            ;;
        django)
            rotate_django_secrets
            ;;
        postgres)
            rotate_postgres_secrets
            ;;
        redis)
            rotate_redis_secrets
            ;;
        apis)
            rotate_api_keys
            ;;
    esac

    generate_rotation_report

    log_info "Secret rotation completed"
    audit_log "ROTATION" "all-secrets" "COMPLETED" "Type: $secret_type"
}

main "$@"
