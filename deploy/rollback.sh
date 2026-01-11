#!/bin/bash

################################################################################
# THE_BOT Platform - Automatic Rollback Module
#
# Performs automatic rollback on deployment failure:
# - Stops systemd services
# - Restores backend files from tar.gz backup
# - Restores frontend/dist if backup exists
# - Restores PostgreSQL database
# - Restarts services
# - Verifies service health
#
# Usage (sourced from main deploy script):
#   source deploy/rollback.sh
#   perform_rollback "$PROD_SERVER" "$PROD_HOME" "$PROD_USER" "$BACKUP_TIMESTAMP" "$BACKUP_DIR"
#
# Parameters:
#   $1 = PROD_SERVER (e.g., "mg@5.129.249.206")
#   $2 = PROD_HOME (e.g., "/home/mg/THE_BOT_platform")
#   $3 = PROD_USER (e.g., "mg")
#   $4 = BACKUP_TIMESTAMP (e.g., "20260111_143022")
#   $5 = BACKUP_DIR (e.g., "/home/mg/backups")
#
################################################################################

set -euo pipefail

# Colors (use existing from parent script or define locally)
RED="${RED:-\033[0;31m}"
GREEN="${GREEN:-\033[0;32m}"
YELLOW="${YELLOW:-\033[1;33m}"
BLUE="${BLUE:-\033[0;34m}"
CYAN="${CYAN:-\033[0;36m}"
NC="${NC:-\033[0m}"

# Logging functions (use parent or define locally)
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} ROLLBACK: $1"
}

success() {
    echo -e "${GREEN}✓${NC} ROLLBACK: $1"
}

error() {
    echo -e "${RED}✗${NC} ROLLBACK ERROR: $1"
}

warning() {
    echo -e "${YELLOW}⚠${NC} ROLLBACK: $1"
}

info() {
    echo -e "${CYAN}ℹ${NC} ROLLBACK: $1"
}

################################################################################
# Perform automatic rollback
################################################################################
perform_rollback() {
    local PROD_SERVER="$1"
    local PROD_HOME="$2"
    local PROD_USER="$3"
    local BACKUP_TIMESTAMP="$4"
    local BACKUP_DIR="$5"

    # If BACKUP_TIMESTAMP not provided, read from saved file
    if [ -z "$BACKUP_TIMESTAMP" ] && [ -f "${BACKUP_DIR}/.backup_timestamp" ]; then
        BACKUP_TIMESTAMP=$(cat "${BACKUP_DIR}/.backup_timestamp" 2>/dev/null)
        info "Read BACKUP_TIMESTAMP from file: $BACKUP_TIMESTAMP"
    fi

    # Validate that BACKUP_TIMESTAMP exists
    if [ -z "$BACKUP_TIMESTAMP" ]; then
        error "BACKUP_TIMESTAMP is required for rollback"
        return 1
    fi

    log "========== STARTING AUTOMATIC ROLLBACK =========="
    info "Backup timestamp: $BACKUP_TIMESTAMP"
    info "Backup directory: $BACKUP_DIR"
    info "Target server: $PROD_SERVER"
    info "Target home: $PROD_HOME"

    # Systemd services to manage
    local SERVICES=("thebot-daphne.service" "thebot-celery-worker.service" "thebot-celery-beat.service")

    # Check backup files exist
    log "Verifying backup files exist..."
    local BACKEND_BACKUP="${BACKUP_DIR}/backend_${BACKUP_TIMESTAMP}.tar.gz"
    local FRONTEND_BACKUP="${BACKUP_DIR}/frontend_dist_${BACKUP_TIMESTAMP}.tar.gz"
    local DB_BACKUP="${BACKUP_DIR}/db_backup_${BACKUP_TIMESTAMP}.sql.gz"

    if [ ! -f "$BACKEND_BACKUP" ]; then
        error "Backend backup not found: $BACKEND_BACKUP"
        return 1
    fi
    success "Backend backup found: $BACKEND_BACKUP"

    if [ ! -f "$DB_BACKUP" ]; then
        error "Database backup not found: $DB_BACKUP"
        return 1
    fi
    success "Database backup found: $DB_BACKUP"

    if [ -f "$FRONTEND_BACKUP" ]; then
        success "Frontend backup found: $FRONTEND_BACKUP"
    else
        warning "Frontend backup not found (optional): $FRONTEND_BACKUP"
    fi

    # Execute rollback on production server
    log "Executing rollback operations on $PROD_SERVER..."

    local ROLLBACK_SCRIPT=$(cat <<'REMOTE_ROLLBACK'
#!/bin/bash

set -euo pipefail

PROD_HOME="$1"
PROD_USER="$2"
BACKEND_BACKUP="$3"
FRONTEND_BACKUP="$4"
DB_BACKUP="$5"
BACKUP_TIMESTAMP="$6"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} REMOTE: $1"; }
success() { echo -e "${GREEN}✓${NC} REMOTE: $1"; }
error() { echo -e "${RED}✗${NC} REMOTE ERROR: $1"; }
warning() { echo -e "${YELLOW}⚠${NC} REMOTE: $1"; }

SERVICES=("thebot-daphne.service" "thebot-celery-worker.service" "thebot-celery-beat.service")

# ===== STEP 1: STOP SERVICES =====
log "Stopping systemd services..."
for service in "${SERVICES[@]}"; do
    if systemctl is-active --quiet "$service"; then
        if ! sudo systemctl stop "$service" 2>&1; then
            error "Failed to stop $service"
            exit 1
        fi
        success "Stopped $service"
    else
        warning "$service is not running"
    fi
done

sleep 2

# ===== STEP 2: RESTORE BACKEND =====
log "Restoring backend files from backup..."
if ! tar -xzf "$BACKEND_BACKUP" -C "$PROD_HOME" 2>&1; then
    error "Failed to restore backend from $BACKEND_BACKUP"
    exit 1
fi
success "Backend restored from $BACKEND_BACKUP"
log "Backend files restored to: $PROD_HOME"

# ===== STEP 3: RESTORE FRONTEND (if exists) =====
if [ -f "$FRONTEND_BACKUP" ]; then
    log "Restoring frontend/dist files from backup..."
    if ! tar -xzf "$FRONTEND_BACKUP" -C "$PROD_HOME" 2>&1; then
        warning "Failed to restore frontend, continuing with rollback..."
    else
        success "Frontend/dist restored from $FRONTEND_BACKUP"
    fi
else
    warning "Frontend backup not provided, skipping frontend restore"
fi

# ===== STEP 4: RESTORE DATABASE =====
log "Restoring PostgreSQL database..."

# Get database credentials (sourced from .env if available)
if [ -f "$PROD_HOME/.env" ]; then
    source "$PROD_HOME/.env" 2>/dev/null || true
fi

DB_NAME="${DATABASE_NAME:-thebot_db}"
DB_USER="${DATABASE_USER:-thebot_user}"
DB_HOST="${DATABASE_HOST:-localhost}"

log "Database: $DB_NAME, User: $DB_USER, Host: $DB_HOST"

# Create temporary directory for decompressed backup
TEMP_BACKUP_DIR=$(mktemp -d)
trap "rm -rf '$TEMP_BACKUP_DIR'" EXIT

log "Decompressing database backup..."
if ! gunzip -c "$DB_BACKUP" > "$TEMP_BACKUP_DIR/db_backup.sql" 2>&1; then
    error "Failed to decompress database backup"
    exit 1
fi
success "Database backup decompressed"

# Restore database
log "Executing database restore (this may take a moment)..."
if ! sudo -u postgres psql -d "$DB_NAME" -f "$TEMP_BACKUP_DIR/db_backup.sql" > /dev/null 2>&1; then
    # Try alternative approach if psql fails
    warning "Direct psql restore failed, trying pg_restore approach..."

    # Check if backup is in custom format (binary)
    if file "$DB_BACKUP" | grep -q "gzip"; then
        log "Backup is gzip compressed, attempting custom restore..."
        if ! sudo -u postgres pg_restore --dbname="$DB_NAME" --clean --if-exists "$TEMP_BACKUP_DIR/db_backup.sql" 2>&1; then
            error "Failed to restore database (both methods failed)"
            exit 1
        fi
    else
        error "Failed to restore database and unable to determine backup format"
        exit 1
    fi
fi
success "Database restored from $DB_BACKUP"

# ===== STEP 5: VERIFY DATABASE =====
log "Verifying database connectivity..."
if ! sudo -u postgres psql -d "$DB_NAME" -t -c "SELECT 1;" > /dev/null 2>&1; then
    error "Database verification failed"
    exit 1
fi
success "Database verification successful"

# ===== STEP 6: START SERVICES =====
log "Starting systemd services..."
for service in "${SERVICES[@]}"; do
    log "Starting $service..."
    if ! sudo systemctl start "$service" 2>&1; then
        error "Failed to start $service"
        exit 1
    fi
    success "Started $service"
done

sleep 2

# ===== STEP 7: VERIFY SERVICES =====
log "Verifying service health..."
for service in "${SERVICES[@]}"; do
    if sudo systemctl is-active --quiet "$service"; then
        success "$service is active"
    else
        error "$service failed to start"
        exit 1
    fi
done

success "All services verified and running"
log "========== ROLLBACK COMPLETED SUCCESSFULLY =========="

REMOTE_ROLLBACK
)

    # Execute rollback script on remote server
    if ! ssh "$PROD_SERVER" /bin/bash << EXEC_ROLLBACK 2>&1 | tee -a "${DEPLOY_LOG:-/tmp/rollback.log}"
$ROLLBACK_SCRIPT
EXEC_ROLLBACK "$PROD_HOME" "$PROD_USER" "$BACKEND_BACKUP" "$FRONTEND_BACKUP" "$DB_BACKUP" "$BACKUP_TIMESTAMP"
EXEC_ROLLBACK
    then
        error "Rollback execution failed"
        return 1
    fi

    success "========== ROLLBACK COMPLETED =========="
    info "Services restored and running on $PROD_SERVER"
    info "Backend restored from: $BACKEND_BACKUP"
    info "Database restored from: $DB_BACKUP"
    if [ -f "$FRONTEND_BACKUP" ]; then
        info "Frontend restored from: $FRONTEND_BACKUP"
    fi

    return 0
}

################################################################################
# Verify rollback was successful
################################################################################
verify_rollback() {
    local PROD_SERVER="$1"
    local SERVICES=("thebot-daphne.service" "thebot-celery-worker.service" "thebot-celery-beat.service")

    log "Verifying rollback success..."

    for service in "${SERVICES[@]}"; do
        if ! ssh "$PROD_SERVER" sudo systemctl is-active --quiet "$service" 2>&1; then
            error "Service $service is not active after rollback"
            return 1
        fi
        success "$service is active"
    done

    success "Rollback verification completed"
    return 0
}

################################################################################
# Export functions for use in parent script
################################################################################
export -f perform_rollback
export -f verify_rollback
