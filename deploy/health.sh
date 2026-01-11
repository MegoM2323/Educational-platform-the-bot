#!/bin/bash

################################################################################
# PHASE 5: Health Checks
#
# Verifies health status of services and API with retry logic
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"

source "$LIB_DIR/shared.sh"

# Validate required variables
validate_required_vars PROD_SERVER SERVICES DEPLOY_LOG

# ===== HEALTH CHECKS =====

log_info "Starting health check phase..."

if [ "${DRY_RUN:-false}" = true ]; then
    log_info "[DRY-RUN] Would check:"
    log_info "  - Service status for all configured services"
    log_info "  - API health endpoint"
    log_info "  - Disk space"
    exit 0
fi

failed=false

# Check each service status
log_info "Checking service statuses..."
for service in $SERVICES; do
    if check_service_status "$service"; then
        log_success "Service active: $service"
    else
        log_error "Service not active: $service"
        failed=true
    fi
done

# Check API health endpoint (optional)
if [ -n "${HEALTH_CHECK_URL:-}" ]; then
    log_info "Checking API health endpoint..."
    if health_check_http "${HEALTH_CHECK_URL}" 5 3; then
        log_success "API health endpoint OK"
    else
        log_warning "API health endpoint check failed (may be expected)"
    fi
fi

# Check disk space
log_info "Checking disk space again..."
if check_disk_space; then
    log_success "Disk space OK"
else
    log_warning "Disk space check failed"
fi

if [ "$failed" = true ]; then
    log_error "Some health checks failed"
    exit 1
fi

log_success "Health check phase completed"
exit 0
