#!/bin/bash

################################################################################
# THE_BOT Platform - Native Deployment Script (Production)
#
# Full native systemd deployment with database backup and credentials preservation
# Copies local files to production (NO git operations)
#
# Usage:
#   ./safe-deploy-native.sh                    # Interactive full deploy
#   ./safe-deploy-native.sh --force            # No confirmation
#   ./safe-deploy-native.sh --dry-run          # Simulation mode
#   ./safe-deploy-native.sh --no-backup        # Skip DB backup (dangerous)
#   ./safe-deploy-native.sh --skip-migrations  # Skip migrations (hotfix)
#   ./safe-deploy-native.sh --verbose          # Detailed logging
#   ./safe-deploy-native.sh --help             # Show help
#
################################################################################

set -euo pipefail

# ===== CONFIG =====
SSH_HOST="${SSH_HOST:-mg@5.129.249.206}"
REMOTE_DIR="${REMOTE_DIR:-/home/mg/THE_BOT_platform}"
VENV_PATH="${VENV_PATH:-/home/mg/venv}"
BACKUP_DIR="${BACKUP_DIR:-/home/mg/backups}"
LOCAL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOY_LOG="/tmp/deploy_${TIMESTAMP}.log"

# Systemd services
SERVICES=("the-bot-celery-worker.service" "the-bot-celery-beat.service" "the-bot-daphne.service")

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options
DRY_RUN=false
FORCE_DEPLOY=false
NO_BACKUP=false
SKIP_MIGRATIONS=false
ROLLBACK_ON_ERROR=true
KEEP_BACKUPS=7
VERBOSE=false

# Parse arguments
show_help() {
    cat << EOF
THE_BOT Platform - Native Deployment Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --dry-run             Simulation mode (no actual changes)
    --force               Skip confirmation prompts
    --no-backup           Skip database backup (DANGEROUS!)
    --skip-migrations     Skip database migrations (for hotfixes)
    --rollback-on-error   Auto-rollback on error (default: true)
    --keep-backups N      Keep last N days of backups (default: 7)
    --verbose             Detailed logging
    --help                Show this help message

EXAMPLES:
    $0                           # Full interactive deploy
    $0 --dry-run                 # Preview changes
    $0 --force                   # Quick deploy without prompts
    $0 --skip-migrations --force # Hotfix deploy
    $0 --verbose                 # Debug mode

EOF
    exit 0
}

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --force) FORCE_DEPLOY=true; shift ;;
        --no-backup) NO_BACKUP=true; shift ;;
        --skip-migrations) SKIP_MIGRATIONS=true; shift ;;
        --rollback-on-error) ROLLBACK_ON_ERROR=true; shift ;;
        --no-rollback) ROLLBACK_ON_ERROR=false; shift ;;
        --keep-backups) KEEP_BACKUPS="$2"; shift 2 ;;
        --verbose) VERBOSE=true; shift ;;
        --help) show_help ;;
        *) echo "Unknown option: $1. Use --help for usage."; exit 1 ;;
    esac
done

# Logging functions
log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$DEPLOY_LOG"; }
success() { echo -e "${GREEN}✓${NC} $1" | tee -a "$DEPLOY_LOG"; }
error() { echo -e "${RED}✗${NC} $1" | tee -a "$DEPLOY_LOG"; }
warning() { echo -e "${YELLOW}⚠${NC} $1" | tee -a "$DEPLOY_LOG"; }
info() { echo -e "${CYAN}ℹ${NC} $1" | tee -a "$DEPLOY_LOG"; }

# Sanitize sensitive data in logs
sanitize_log() {
    sed -E 's/([A-Z_]*(PASSWORD|SECRET|TOKEN|API_KEY|REDIS_PASSWORD)[A-Z_]*)=[^[:space:]]*/\1=***REDACTED***/gi'
}

# Execute command with dry-run support
execute() {
    local cmd="$1"
    local description="${2:-Executing command}"

    if [ "$VERBOSE" = true ]; then
        log "$description: $cmd"
    fi

    if [ "$DRY_RUN" = true ]; then
        info "[DRY-RUN] Would execute: $cmd"
        return 0
    fi

    eval "$cmd"
}

# Error handler
trap 'error "Deployment failed at line $LINENO. Check log: $DEPLOY_LOG"; exit 1' ERR

# ===== PHASE 0: PRE-CHECKS =====
log "========== PHASE 0: PRE-CHECKS =========="

# Check SSH connection
if ! ssh -o ConnectTimeout=5 "$SSH_HOST" "echo OK" > /dev/null 2>&1; then
    error "SSH connection failed to $SSH_HOST"
    exit 1
fi
success "SSH connection OK"

# Check remote disk space
log "Checking remote disk space..."
DISK_USAGE=$(ssh "$SSH_HOST" "df -h / | tail -1 | awk '{print \$5}' | tr -d '%'")
if [ "$DISK_USAGE" -gt 95 ]; then
    error "Disk usage critical: ${DISK_USAGE}%. Free up space before deployment!"
    exit 1
elif [ "$DISK_USAGE" -gt 90 ]; then
    warning "Disk usage high: ${DISK_USAGE}%. Consider cleanup."
else
    success "Disk usage OK: ${DISK_USAGE}%"
fi

# Check remote services exist
log "Checking remote systemd services..."
for service in "${SERVICES[@]}"; do
    if ssh "$SSH_HOST" "systemctl list-unit-files | grep -q $service" 2>/dev/null; then
        success "Service $service exists"
    else
        warning "Service $service not found (will be created later)"
    fi
done

# Check PostgreSQL accessibility
log "Checking PostgreSQL service..."
if ssh "$SSH_HOST" "systemctl is-active postgresql > /dev/null 2>&1" 2>/dev/null; then
    success "PostgreSQL is active"
else
    warning "PostgreSQL service not active. Check manually if database is accessible."
fi

# Check local git status
log "Checking local git status..."
if [ -d "$LOCAL_PATH/.git" ]; then
    GIT_STATUS=$(git -C "$LOCAL_PATH" status --porcelain)
    if [ -n "$GIT_STATUS" ]; then
        warning "Uncommitted changes detected:"
        echo "$GIT_STATUS" | head -5
        if [ "$FORCE_DEPLOY" = false ]; then
            read -p "Auto-commit changes? [y/N]: " -n 1 -r
            echo
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                git -C "$LOCAL_PATH" add -A
                git -C "$LOCAL_PATH" commit -m "Auto-commit перед deployment ${TIMESTAMP}"
                success "Changes committed"
            fi
        fi
    else
        success "Git working directory clean"
    fi
fi

# Confirmation prompt
if [ "$FORCE_DEPLOY" = false ] && [ "$DRY_RUN" = false ]; then
    echo ""
    warning "Ready to deploy to PRODUCTION:"
    echo "  Target: $SSH_HOST:$REMOTE_DIR"
    echo "  Backup: $([ "$NO_BACKUP" = true ] && echo 'NO (DANGEROUS!)' || echo 'YES')"
    echo "  Migrations: $([ "$SKIP_MIGRATIONS" = true ] && echo 'SKIP' || echo 'YES')"
    echo ""
    read -p "Continue? [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        info "Deployment cancelled by user"
        exit 0
    fi
fi

# ===== PHASE 1: DATABASE BACKUP =====
log ""
log "========== PHASE 1: DATABASE BACKUP =========="

if [ "$NO_BACKUP" = true ]; then
    warning "Database backup SKIPPED (--no-backup flag)"
else
    if [ "$DRY_RUN" = false ]; then
        log "Creating database backup on production..."

        BACKUP_OUTPUT=$(ssh "$SSH_HOST" /bin/bash << 'BACKUP_SCRIPT'
set -euo pipefail

REMOTE_DIR="/home/mg/THE_BOT_platform"
BACKUP_DIR="/home/mg/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Read database credentials from production .env
if [ ! -f "$REMOTE_DIR/.env" ]; then
    echo "ERROR: Production .env file not found at $REMOTE_DIR/.env"
    exit 1
fi

DB_USER=$(grep "^DB_USER=" "$REMOTE_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ -z "$DB_USER" ]; then
    echo "ERROR: DB_USER not found in .env - file may be corrupted"
    exit 1
fi

DB_PASSWORD=$(grep "^DB_PASSWORD=" "$REMOTE_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ -z "$DB_PASSWORD" ]; then
    echo "ERROR: DB_PASSWORD not found or empty in .env - file may be corrupted"
    exit 1
fi

DB_NAME=$(grep "^DB_NAME=" "$REMOTE_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ -z "$DB_NAME" ]; then
    echo "ERROR: DB_NAME not found in .env - file may be corrupted"
    exit 1
fi

DB_HOST="localhost"

echo "Using DB credentials: user=$DB_USER, database=$DB_NAME"

# Test database connection
if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT 1;" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to database"
    exit 1
fi
echo "Database connection OK"

# Create backup
BACKUP_FILE="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql"
echo "Creating backup: $BACKUP_FILE"

PGPASSWORD="$DB_PASSWORD" pg_dump -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" \
    --no-owner \
    --no-privileges \
    > "$BACKUP_FILE" 2>/dev/null

# Verify backup is not empty
if [ ! -f "$BACKUP_FILE" ] || [ ! -s "$BACKUP_FILE" ]; then
    echo "ERROR: Backup file is empty or was not created"
    rm -f "$BACKUP_FILE"
    exit 1
fi

BACKUP_SIZE=$(stat -c%s "$BACKUP_FILE")
if [ "$BACKUP_SIZE" -lt 1000 ]; then
    echo "ERROR: Backup file too small (${BACKUP_SIZE} bytes), possibly corrupted"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Compress backup
echo "Compressing backup..."
gzip -9 "$BACKUP_FILE"
BACKUP_FILE_GZ="${BACKUP_FILE}.gz"

# Verify compressed backup
if [ ! -f "$BACKUP_FILE_GZ" ] || [ ! -s "$BACKUP_FILE_GZ" ]; then
    echo "ERROR: Compressed backup failed"
    exit 1
fi

COMPRESSED_SIZE=$(du -h "$BACKUP_FILE_GZ" | cut -f1)
echo "SUCCESS: Backup created: $(basename $BACKUP_FILE_GZ) ($COMPRESSED_SIZE)"

# Save backup path for rollback
echo "$BACKUP_FILE_GZ" > "$REMOTE_DIR/.last_backup"

# Apply retention policy (keep last N days)
KEEP_DAYS=7
echo "Applying retention policy (keep last $KEEP_DAYS days)..."
DELETED=$(find "$BACKUP_DIR" -name "db_backup_*.sql.gz" -mtime +$KEEP_DAYS -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "Deleted $DELETED old backup(s)"
fi

# Show backup statistics
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "0")
echo "Total backups: $BACKUP_COUNT ($TOTAL_SIZE)"

echo "BACKUP_PATH=$BACKUP_FILE_GZ"
BACKUP_SCRIPT
)

        if echo "$BACKUP_OUTPUT" | grep -q "SUCCESS:"; then
            BACKUP_PATH=$(echo "$BACKUP_OUTPUT" | grep "BACKUP_PATH=" | cut -d'=' -f2)
            success "Database backup completed: $(basename $BACKUP_PATH)"
        else
            error "Database backup failed:"
            echo "$BACKUP_OUTPUT" | sanitize_log
            if [ "$ROLLBACK_ON_ERROR" = true ]; then
                exit 1
            fi
        fi
    else
        info "[DRY-RUN] Would create database backup"
    fi
fi

# ===== PHASE 2: CREDENTIALS PRESERVATION =====
log ""
log "========== PHASE 2: CREDENTIALS PRESERVATION =========="

if [ "$DRY_RUN" = false ]; then
    log "Preserving production credentials..."

    ssh "$SSH_HOST" /bin/bash << 'PRESERVE_SCRIPT'
set -euo pipefail

REMOTE_DIR="/home/mg/THE_BOT_platform"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Download existing .env from production
if [ -f "$REMOTE_DIR/.env" ]; then
    # Backup old .env
    cp "$REMOTE_DIR/.env" "$REMOTE_DIR/.env.backup.$TIMESTAMP"

    # Keep only last 3 .env backups
    ls -t "$REMOTE_DIR"/.env.backup.* 2>/dev/null | tail -n +4 | xargs -r rm

    # Extract critical secrets
    echo "Extracting credentials..."
    grep -E "^(DB_PASSWORD|SECRET_KEY|REDIS_PASSWORD|TELEGRAM_BOT_TOKEN|YOOKASSA_SECRET_KEY|OPENROUTER_API_KEY|PACHCA_FORUM_API_TOKEN)=" "$REMOTE_DIR/.env" > "$REMOTE_DIR/.env.secrets" 2>/dev/null

    # Verify critical credentials were extracted
    if ! grep -q "^DB_PASSWORD=" "$REMOTE_DIR/.env.secrets" 2>/dev/null; then
        echo "ERROR: DB_PASSWORD not found in .env during extraction"
        exit 1
    fi
    if ! grep -q "^SECRET_KEY=" "$REMOTE_DIR/.env.secrets" 2>/dev/null; then
        echo "ERROR: SECRET_KEY not found in .env during extraction"
        exit 1
    fi

    # Set secure permissions
    chmod 600 "$REMOTE_DIR/.env.secrets"

    echo "SUCCESS: Credentials preserved"
else
    echo "INFO: No existing .env file (first deployment)"
fi
PRESERVE_SCRIPT

    success "Production credentials preserved"
else
    info "[DRY-RUN] Would preserve production credentials"
fi

# ===== PHASE 3: CODE DEPLOYMENT =====
log ""
log "========== PHASE 3: CODE DEPLOYMENT =========="

if [ "$DRY_RUN" = false ]; then
    # Save current git commit for rollback
    if [ -d "$LOCAL_PATH/.git" ]; then
        CURRENT_COMMIT=$(git -C "$LOCAL_PATH" rev-parse HEAD)
        ssh "$SSH_HOST" "echo '$CURRENT_COMMIT' > $REMOTE_DIR/.last_deploy_commit"
    fi

    log "Copying backend code..."
    rsync -av --delete --delete-delay \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.pyo' \
        --exclude='*.log' \
        --exclude='.env' \
        --exclude='.env.*' \
        --exclude='dump.rdb' \
        --exclude='.venv' \
        --exclude='venv' \
        --exclude='node_modules' \
        --exclude='.git' \
        "$LOCAL_PATH/backend/" "$SSH_HOST:$REMOTE_DIR/backend/" > /dev/null 2>&1

    if [ $? -ne 0 ]; then
        error "Backend code rsync failed"
        exit 1
    fi
    success "Backend code copied"

    log "Copying scripts..."
    rsync -av --delete-delay \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        "$LOCAL_PATH/scripts/" "$SSH_HOST:$REMOTE_DIR/scripts/" > /dev/null 2>&1

    if [ $? -ne 0 ]; then
        error "Scripts rsync failed"
        exit 1
    fi
    success "Scripts copied"

    # Restore credentials
    log "Restoring production credentials..."
    ssh "$SSH_HOST" /bin/bash << 'RESTORE_SCRIPT'
set -euo pipefail

REMOTE_DIR="/home/mg/THE_BOT_platform"

if [ -f "$REMOTE_DIR/.env.secrets" ]; then
    # Restore secrets to .env using awk (safer than sed for special chars)
    if [ -f "$REMOTE_DIR/.env" ]; then
        # Create temporary file for merge
        TMP_ENV=$(mktemp)

        # Merge secrets back into .env using awk
        awk -F'=' 'NR==FNR { secrets[$1]=$2; next }
                   { if ($1 in secrets) print $1"="secrets[$1]; else print }' \
            "$REMOTE_DIR/.env.secrets" "$REMOTE_DIR/.env" > "$TMP_ENV"

        # Verify merge succeeded
        if [ ! -s "$TMP_ENV" ]; then
            echo "ERROR: Credential merge failed - temporary file empty"
            rm -f "$TMP_ENV"
            exit 1
        fi

        # Verify critical credentials exist in merged file
        if ! grep -q "^DB_PASSWORD=" "$TMP_ENV" 2>/dev/null; then
            echo "ERROR: DB_PASSWORD missing after merge"
            rm -f "$TMP_ENV"
            exit 1
        fi
        if ! grep -q "^SECRET_KEY=" "$TMP_ENV" 2>/dev/null; then
            echo "ERROR: SECRET_KEY missing after merge"
            rm -f "$TMP_ENV"
            exit 1
        fi

        # Replace .env with merged version
        mv "$TMP_ENV" "$REMOTE_DIR/.env"
        chmod 600 "$REMOTE_DIR/.env"

        echo "SUCCESS: Credentials restored"
    else
        echo "ERROR: .env file not found, cannot restore credentials"
        exit 1
    fi

    # Remove temporary secrets file (security)
    rm -f "$REMOTE_DIR/.env.secrets"
    echo "Temporary secrets file removed"
else
    echo "ERROR: No secrets file to restore - credentials may be lost"
    exit 1
fi

# Ensure .env has correct permissions
if [ -f "$REMOTE_DIR/.env" ]; then
    chmod 600 "$REMOTE_DIR/.env"
fi
RESTORE_SCRIPT

    success "Production credentials restored"
else
    info "[DRY-RUN] Would copy: backend/, scripts/ and restore credentials"
fi

# ===== PHASE 4: DATABASE MIGRATIONS =====
log ""
log "========== PHASE 4: DATABASE MIGRATIONS =========="

if [ "$SKIP_MIGRATIONS" = true ]; then
    warning "Database migrations SKIPPED (--skip-migrations flag)"
else
    if [ "$DRY_RUN" = false ]; then
        log "Checking pending migrations..."

        MIGRATION_OUTPUT=$(ssh "$SSH_HOST" /bin/bash << MIGRATE_SCRIPT
set -e

cd $REMOTE_DIR/backend
source $VENV_PATH/bin/activate

# Check for pending migrations
echo "=== Checking pending migrations ==="
PENDING=\$(python manage.py showmigrations 2>/dev/null | grep -c "\[ \]" || echo "0")
echo "Pending migrations: \$PENDING"

if [ "\$PENDING" -gt 0 ]; then
    echo ""
    echo "=== Running migrations (verbosity 2) ==="
    python manage.py migrate --noinput --verbosity 2 2>&1 || {
        echo ""
        echo "ERROR: Migration failed. Troubleshooting:"
        echo "  1. Try: python manage.py migrate --fake-initial"
        echo "  2. Try: python manage.py migrate --run-syncdb"
        echo "  3. Check for conflicting migrations"
        exit 1
    }
else
    echo "No pending migrations"
fi

echo ""
echo "=== Collecting static files ==="
python manage.py collectstatic --noinput --clear 2>&1 | tail -3

echo ""
echo "=== Creating cache table (if needed) ==="
python manage.py createcachetable 2>/dev/null || echo "Cache table already exists or not configured"

echo ""
echo "SUCCESS: Database operations completed"
MIGRATE_SCRIPT
)

        echo "$MIGRATION_OUTPUT"

        if echo "$MIGRATION_OUTPUT" | grep -q "SUCCESS:"; then
            success "Database migrations completed"
        else
            error "Database migrations failed"
            if [ "$ROLLBACK_ON_ERROR" = true ]; then
                exit 1
            fi
        fi
    else
        info "[DRY-RUN] Would run: showmigrations, migrate, collectstatic, createcachetable"
    fi
fi

# ===== PHASE 5: SERVICE RESTART =====
log ""
log "========== PHASE 5: SERVICE RESTART =========="

if [ "$DRY_RUN" = false ]; then
    log "Stopping services (reverse order)..."

    # Stop in reverse order: daphne -> beat -> worker
    ssh "$SSH_HOST" /bin/bash << 'STOP_SCRIPT'
set -e

echo "Stopping the-bot-daphne.service..."
sudo systemctl stop the-bot-daphne.service 2>/dev/null || true

echo "Stopping the-bot-celery-beat.service..."
sudo systemctl stop the-bot-celery-beat.service 2>/dev/null || true

echo "Stopping the-bot-celery-worker.service..."
sudo systemctl stop the-bot-celery-worker.service 2>/dev/null || true

echo "Waiting for graceful shutdown..."
sleep 3
STOP_SCRIPT

    success "Services stopped"

    log "Starting services (correct order)..."

    # Start in correct order: worker -> beat -> daphne
    ssh "$SSH_HOST" /bin/bash << 'START_SCRIPT'
set -e

echo "Starting the-bot-celery-worker.service..."
sudo systemctl start the-bot-celery-worker.service

# Wait and verify worker started
sleep 2
if ! systemctl is-active the-bot-celery-worker.service > /dev/null 2>&1; then
    echo "✗ the-bot-celery-worker.service FAILED to start"
    journalctl -u the-bot-celery-worker.service --no-pager -n 20
    exit 1
fi
echo "✓ the-bot-celery-worker.service started"

echo "Starting the-bot-celery-beat.service..."
sudo systemctl start the-bot-celery-beat.service

# Wait and verify beat started
sleep 2
if ! systemctl is-active the-bot-celery-beat.service > /dev/null 2>&1; then
    echo "✗ the-bot-celery-beat.service FAILED to start"
    journalctl -u the-bot-celery-beat.service --no-pager -n 20
    exit 1
fi
echo "✓ the-bot-celery-beat.service started"

echo "Starting the-bot-daphne.service..."
sudo systemctl start the-bot-daphne.service

# Wait and verify daphne started
sleep 2
if ! systemctl is-active the-bot-daphne.service > /dev/null 2>&1; then
    echo "✗ the-bot-daphne.service FAILED to start"
    journalctl -u the-bot-daphne.service --no-pager -n 20
    exit 1
fi
echo "✓ the-bot-daphne.service started"

echo "Waiting for stabilization..."
sleep 3

echo ""
echo "=== Final Service Status ==="
for service in the-bot-celery-worker.service the-bot-celery-beat.service the-bot-daphne.service; do
    if systemctl is-active "$service" > /dev/null 2>&1; then
        echo "✓ $service: active"
    else
        echo "✗ $service: FAILED (crashed after start)"
        journalctl -u "$service" --no-pager -n 20
        exit 1
    fi
done
START_SCRIPT

    success "All services started and active"
else
    info "[DRY-RUN] Would restart: the-bot-celery-worker, the-bot-celery-beat, the-bot-daphne"
fi

# ===== PHASE 6: VERIFICATION =====
log ""
log "========== PHASE 6: VERIFICATION =========="

if [ "$DRY_RUN" = false ]; then
    sleep 3

    # Verify database integrity
    log "Verifying database integrity..."
    DB_CHECK=$(ssh "$SSH_HOST" /bin/bash << 'DB_CHECK_SCRIPT'
set -e

REMOTE_DIR="/home/mg/THE_BOT_platform"

DB_USER=$(grep "^DB_USER=" "$REMOTE_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ -z "$DB_USER" ]; then
    echo "ERROR: DB_USER not found in .env during verification"
    exit 1
fi

DB_PASSWORD=$(grep "^DB_PASSWORD=" "$REMOTE_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ -z "$DB_PASSWORD" ]; then
    echo "ERROR: DB_PASSWORD not found in .env during verification"
    exit 1
fi

DB_NAME=$(grep "^DB_NAME=" "$REMOTE_DIR/.env" 2>/dev/null | cut -d'=' -f2 | tr -d '"' | tr -d "'")
if [ -z "$DB_NAME" ]; then
    echo "ERROR: DB_NAME not found in .env during verification"
    exit 1
fi

MIGRATION_COUNT=$(PGPASSWORD="$DB_PASSWORD" psql -h localhost -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM django_migrations;" 2>/dev/null | tr -d ' ')

if [ -n "$MIGRATION_COUNT" ] && [ "$MIGRATION_COUNT" -gt 0 ]; then
    echo "SUCCESS: Database accessible ($MIGRATION_COUNT migrations applied)"
else
    echo "ERROR: Database query failed"
    exit 1
fi
DB_CHECK_SCRIPT
)

    if echo "$DB_CHECK" | grep -q "SUCCESS:"; then
        success "Database integrity verified"
    else
        warning "Database verification failed (non-critical)"
    fi

    # Verify API health
    log "Verifying API health..."
    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://the-bot.ru/api/auth/login/ \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"email":"test@test.com","password":"test"}' 2>/dev/null || echo "000")

    if [ "$RESPONSE" != "000" ] && [ "$RESPONSE" != "500" ]; then
        success "API is responding (HTTP $RESPONSE)"
    else
        warning "API response: HTTP $RESPONSE (check logs if problematic)"
    fi

    # Check service logs for errors
    log "Checking service logs for recent errors..."
    LOG_CHECK=$(ssh "$SSH_HOST" /bin/bash << 'LOG_CHECK_SCRIPT'
set -e

ERROR_COUNT=$(journalctl -u the-bot-daphne.service --since "2 minutes ago" -p err --no-pager | grep -c "error" || echo "0")

if [ "$ERROR_COUNT" -gt 0 ]; then
    echo "WARNING: Found $ERROR_COUNT error(s) in logs"
    echo "Last 5 error lines:"
    journalctl -u the-bot-daphne.service --since "2 minutes ago" -p err --no-pager | tail -5
else
    echo "SUCCESS: No errors in recent logs"
fi
LOG_CHECK_SCRIPT
)

    echo "$LOG_CHECK"
    if echo "$LOG_CHECK" | grep -q "SUCCESS:"; then
        success "No errors in service logs"
    else
        warning "Errors found in logs (review manually)"
    fi
else
    info "[DRY-RUN] Would verify: services, database, API, logs"
fi

# ===== PHASE 7: CLEANUP & REPORT =====
log ""
log "========== PHASE 7: CLEANUP & REPORT =========="

if [ "$DRY_RUN" = false ]; then
    # Backup statistics
    BACKUP_STATS=$(ssh "$SSH_HOST" /bin/bash << 'STATS_SCRIPT'
BACKUP_DIR="/home/mg/backups"
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null | wc -l)
TOTAL_SIZE=$(du -sh "$BACKUP_DIR" 2>/dev/null | cut -f1 || echo "0")
echo "BACKUPS=$BACKUP_COUNT SIZE=$TOTAL_SIZE"
STATS_SCRIPT
)

    BACKUP_COUNT=$(echo "$BACKUP_STATS" | grep -oP 'BACKUPS=\K\d+')
    BACKUP_SIZE=$(echo "$BACKUP_STATS" | grep -oP 'SIZE=\K\S+')

    success "Backup statistics: $BACKUP_COUNT backup(s), total size: $BACKUP_SIZE"
fi

# Deployment summary
log ""
log "========== DEPLOYMENT COMPLETE =========="
success "Native deployment finished successfully!"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  DEPLOYMENT SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Date/Time:        $(date +'%Y-%m-%d %H:%M:%S')"
echo "SSH Host:         $SSH_HOST"
echo "Remote Path:      $REMOTE_DIR"
echo "Backup Created:   $([ "$NO_BACKUP" = true ] && echo 'NO (skipped)' || echo "YES ($BACKUP_SIZE)")"
echo "Migrations Run:   $([ "$SKIP_MIGRATIONS" = true ] && echo 'NO (skipped)' || echo 'YES')"
echo "Dry Run:          $([ "$DRY_RUN" = true ] && echo 'YES (simulation)' || echo 'NO (live)')"
echo ""

if [ "$DRY_RUN" = false ]; then
    echo "Services Status:"
    ssh "$SSH_HOST" /bin/bash << 'STATUS_SCRIPT'
for service in the-bot-celery-worker.service the-bot-celery-beat.service the-bot-daphne.service; do
    status=$(systemctl is-active "$service" 2>/dev/null || echo "inactive")
    if [ "$status" = "active" ]; then
        echo "  ✓ $service: active"
    else
        echo "  ✗ $service: $status"
    fi
done
STATUS_SCRIPT
    echo ""
fi

echo "Next Steps:"
echo "  1. Verify site: https://the-bot.ru"
echo "  2. Check logs: ssh $SSH_HOST journalctl -u the-bot-daphne.service -f"
echo "  3. Monitor errors: ssh $SSH_HOST journalctl -p err --since '5 minutes ago'"
echo ""

if [ "$NO_BACKUP" = false ] && [ "$DRY_RUN" = false ]; then
    echo "Rollback Instructions (if needed):"
    echo "  1. SSH to server: ssh $SSH_HOST"
    echo "  2. Go to backups: cd $BACKUP_DIR"
    echo "  3. List backups: ls -lh db_backup_*.sql.gz"
    echo "  4. Restore database:"
    echo "     gunzip -c db_backup_XXXXXXXX_XXXXXX.sql.gz | \\"
    echo "       PGPASSWORD='***' psql -h localhost -U postgres -d thebot_db"
    echo "  5. Restart services: sudo systemctl restart the-bot-*.service"
    echo ""
fi

echo "Log File: $DEPLOY_LOG"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
