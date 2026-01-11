#!/bin/bash

################################################################################
# PHASE 1: Backup
#
# Creates database and configuration backups before deployment
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"

source "$LIB_DIR/shared.sh"

# Validate required variables
validate_required_vars PROD_SERVER PROD_HOME BACKUP_DIR DEPLOY_LOG

# ===== BACKUP EXECUTION =====

log_info "Starting backup phase..."

if [ "${DRY_RUN:-false}" = true ]; then
    log_info "[DRY-RUN] Would create database backup"
    log_info "[DRY-RUN] Would preserve .env credentials"
    exit 0
fi

# Create backup directory
if ! create_remote_dir "$BACKUP_DIR"; then
    log_error "Failed to create backup directory"
    exit 1
fi

# Execute backup script on remote server
log_info "Creating database backup..."

if ! ssh_cmd "cd '$PROD_HOME' && python manage.py dumpdata > '$BACKUP_DIR/db_dump_${TIMESTAMP}.json' 2>&1" "Database dump"; then
    log_warning "Database dump failed (may be expected if DB not initialized)"
fi

# Compress backup
log_info "Compressing backup..."
ssh_cmd "gzip -f '$BACKUP_DIR/db_dump_${TIMESTAMP}.json' 2>/dev/null || true" "Compress dump"

# Preserve .env credentials
log_info "Preserving production credentials..."

if ssh_cmd "[ -f '$PROD_HOME/.env' ]" "" 2>/dev/null; then
    ssh_cmd "cp '$PROD_HOME/.env' '$PROD_HOME/.env.backup.$TIMESTAMP'" "Backup .env"
    log_success "Credentials backed up"
else
    log_warning "No .env file found (first deployment?)"
fi

log_info "Saving backup timestamp for rollback..."
echo "$TIMESTAMP" > "${BACKUP_DIR}/.backup_timestamp"
chmod 600 "${BACKUP_DIR}/.backup_timestamp"
log_success "Backup phase completed"
exit 0
