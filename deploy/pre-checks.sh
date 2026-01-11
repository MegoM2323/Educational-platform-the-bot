#!/bin/bash

################################################################################
# PHASE 0: Pre-Checks
#
# Validates deployment prerequisites:
# - SSH connectivity
# - Disk space
# - Service availability
# - Git status
# - Environment variables
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"

source "$LIB_DIR/shared.sh"

# Validate required variables
validate_required_vars PROD_SERVER PROD_HOME DEPLOY_LOG

# ===== CHECKS =====

log_info "Running pre-deployment checks..."

# Check SSH connection
if ! check_ssh_connection; then
    log_error "SSH connectivity check failed"
    exit 1
fi

# Check disk space
if ! check_disk_space; then
    log_error "Disk space check failed"
    exit 1
fi

# Check systemd services exist
log_info "Checking systemd services..."
for service in $SERVICES; do
    if ssh "${PROD_SERVER}" "systemctl list-unit-files | grep -q '$service'" 2>/dev/null; then
        log_success "Service exists: $service"
    else
        log_warning "Service not found: $service (will be created during deployment)"
    fi
done

# Check PostgreSQL
log_info "Checking PostgreSQL service..."
if ssh_cmd "systemctl is-active postgresql > /dev/null 2>&1" "Check PostgreSQL" 2>/dev/null; then
    log_success "PostgreSQL is active"
else
    log_warning "PostgreSQL not active. Verify database accessibility manually."
fi

# Check Redis
log_info "Checking Redis service..."
if ssh_cmd "systemctl is-active redis > /dev/null 2>&1" "Check Redis" 2>/dev/null; then
    log_success "Redis is active"
else
    log_warning "Redis not active. It should be running for deployment."
fi

# Check local git status
if [ -d "$SCRIPT_DIR/../../.git" ]; then
    log_info "Checking git status..."
    if git -C "$SCRIPT_DIR/../.." status --porcelain | grep -q .; then
        log_warning "Uncommitted changes detected"
    else
        log_success "Git working directory clean"
    fi
fi

log_success "Pre-checks completed successfully"
exit 0
