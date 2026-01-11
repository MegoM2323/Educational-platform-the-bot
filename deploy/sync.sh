#!/bin/bash

################################################################################
# PHASE 2: Sync
#
# Synchronizes code from local to production server using rsync
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"
LOCAL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$LIB_DIR/shared.sh"

# Validate required variables
validate_required_vars PROD_SERVER PROD_HOME DEPLOY_LOG

# ===== SYNC EXECUTION =====

log_info "Starting sync phase..."

if [ "${DRY_RUN:-false}" = true ]; then
    log_info "[DRY-RUN] Would sync backend code"
    log_info "[DRY-RUN] Would sync frontend code"
    log_info "[DRY-RUN] Would sync scripts"
    exit 0
fi

# Create necessary directories
log_info "Creating remote directories..."
ssh_cmd "mkdir -p '$PROD_HOME/backend' '$PROD_HOME/frontend' '$PROD_HOME/scripts'" "Create directories" || exit 1

# Define rsync exclusions
RSYNC_OPTS="-av --delete --delete-delay"
EXCLUSIONS=(
    --exclude='.git'
    --exclude='.gitignore'
    --exclude='.claude'
    --exclude='.pytest_cache'
    --exclude='.coverage'
    --exclude='.env'
    --exclude='.env.*'
    --exclude='.venv'
    --exclude='venv'
    --exclude='*.pyc'
    --exclude='__pycache__'
    --exclude='*.sqlite3'
    --exclude='db.sqlite3'
    --exclude='media/'
    --exclude='staticfiles/'
    --exclude='node_modules/'
    --exclude='.DS_Store'
    --exclude='*.swp'
    --exclude='*.log'
    --exclude='logs/'
    --exclude='dump.rdb'
)

# Sync backend code
log_info "Syncing backend code..."
if ! rsync $RSYNC_OPTS "${EXCLUSIONS[@]}" "$LOCAL_ROOT/backend/" "${PROD_SERVER}:${PROD_HOME}/backend/" > /dev/null 2>&1; then
    log_error "Backend code sync failed"
    exit 1
fi
log_success "Backend code synced"

# Sync scripts
log_info "Syncing scripts..."
if ! rsync $RSYNC_OPTS --exclude='__pycache__' --exclude='*.pyc' "$LOCAL_ROOT/scripts/" "${PROD_SERVER}:${PROD_HOME}/scripts/" > /dev/null 2>&1; then
    log_error "Scripts sync failed"
    exit 1
fi
log_success "Scripts synced"

# Sync frontend (if not skipped)
if [ "${SKIP_FRONTEND:-false}" = false ]; then
    log_info "Syncing frontend code..."
    if ! rsync $RSYNC_OPTS --exclude='dist' "$LOCAL_ROOT/frontend/" "${PROD_SERVER}:${PROD_HOME}/frontend/" > /dev/null 2>&1; then
        log_error "Frontend code sync failed"
        exit 1
    fi
    log_success "Frontend code synced"
else
    log_info "[SKIPPED] Frontend sync"
fi

log_success "Sync phase completed"
exit 0
