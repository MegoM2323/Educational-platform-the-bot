#!/bin/bash

################################################################################
# PHASE 4: Services
#
# Restarts systemd services with health checks
################################################################################

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB_DIR="$SCRIPT_DIR/lib"

source "$LIB_DIR/shared.sh"

# Validate required variables
validate_required_vars PROD_SERVER SERVICES DEPLOY_LOG

# ===== SERVICE RESTART =====

log_info "Starting service restart phase..."

if [ "${DRY_RUN:-false}" = true ]; then
    log_info "[DRY-RUN] Would restart services:"
    for service in $SERVICES; do
        log_info "  - $service"
    done
    exit 0
fi

# Restart each service
failed=false
for service in $SERVICES; do
    log_info "Restarting service: $service"

    if ! restart_service "$service"; then
        log_error "Failed to restart: $service"
        failed=true
    else
        # Wait for service to stabilize
        sleep 2
        if wait_for_service "$service" 10; then
            log_success "Service ready: $service"
        else
            log_error "Service failed to become ready: $service"
            failed=true
        fi
    fi
done

if [ "$failed" = true ]; then
    log_error "Some services failed to restart"
    exit 1
fi

log_success "Service restart phase completed"
exit 0
