#!/bin/bash

################################################################################
# THE_BOT Platform - Main Deployment Orchestrator
#
# Entry point for all deployment operations. Coordinates execution of
# deployment phases (pre-checks, backup, sync, migrations, services, health).
#
# Usage:
#   ./deploy.sh                    # Interactive full deploy
#   ./deploy.sh --force            # Skip confirmation prompts
#   ./deploy.sh --dry-run          # Simulation mode
#   ./deploy.sh --skip-migrations  # Skip migrations (hotfix)
#   ./deploy.sh --skip-frontend    # Skip frontend build
#   ./deploy.sh --verbose          # Detailed logging
#   ./deploy.sh --help             # Show help
#
################################################################################

set -euo pipefail

# ===== INITIALIZATION =====
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$SCRIPT_DIR/deploy"
LIB_DIR="$DEPLOY_DIR/lib"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOY_LOG="$SCRIPT_DIR/logs/deploy_${TIMESTAMP}.log"

# Ensure logs directory exists
mkdir -p "$SCRIPT_DIR/logs"

# Load configuration
CONFIG_FILE="$DEPLOY_DIR/.env"
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: Configuration file not found: $CONFIG_FILE"
    exit 1
fi
source "$CONFIG_FILE"

# Load shared library
if [ ! -f "$LIB_DIR/shared.sh" ]; then
    echo "ERROR: Shared library not found: $LIB_DIR/shared.sh"
    exit 1
fi
source "$LIB_DIR/shared.sh"

# ===== CONFIGURATION DEFAULTS =====
PROD_HOME="${PROD_HOME:-/home/mg/THE_BOT_platform}"
PROD_SERVER="${PROD_SERVER:-mg@5.129.249.206}"
VENV_PATH="${VENV_PATH:-/home/mg/venv}"
BACKUP_DIR="${BACKUP_DIR:-/home/mg/backups}"

# Systemd services
SERVICES=("thebot-daphne.service" "thebot-celery-worker.service" "thebot-celery-beat.service")

# Deployment options
DRY_RUN=false
FORCE_DEPLOY=false
SKIP_MIGRATIONS=false
SKIP_FRONTEND=false
VERBOSE=false
ROLLBACK_ON_ERROR=true

# Execution state
FAILED_PHASE=""
EXIT_CODE=0

# ===== FUNCTIONS =====

show_help() {
    cat << EOF
THE_BOT Platform - Deployment Orchestrator

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --dry-run              Simulation mode (no actual changes)
    --force                Skip confirmation prompts
    --skip-migrations      Skip database migrations (for hotfixes)
    --skip-frontend        Skip frontend build
    --verbose              Detailed logging
    --help                 Show this help message

EXAMPLES:
    $0                           # Full interactive deploy
    $0 --dry-run                 # Preview changes
    $0 --force                   # Quick deploy without prompts
    $0 --skip-migrations --force # Hotfix deploy
    $0 --verbose                 # Debug mode

ENVIRONMENT:
    Configuration: $DEPLOY_DIR/.env
    Logs: $SCRIPT_DIR/logs/

SERVICES:
    - thebot-daphne.service
    - thebot-celery-worker.service
    - thebot-celery-beat.service

EOF
    exit 0
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run) DRY_RUN=true; shift ;;
            --force) FORCE_DEPLOY=true; shift ;;
            --skip-migrations) SKIP_MIGRATIONS=true; shift ;;
            --skip-frontend) SKIP_FRONTEND=true; shift ;;
            --verbose) VERBOSE=true; shift ;;
            --help) show_help ;;
            *)
                log_error "Unknown option: $1. Use --help for usage."
                exit 1
                ;;
        esac
    done
}

call_phase() {
    local phase_name="$1"
    local script_path="$DEPLOY_DIR/$phase_name.sh"

    if [ ! -f "$script_path" ]; then
        log_error "Phase script not found: $script_path"
        return 1
    fi

    if [ "$VERBOSE" = true ]; then
        log_info "Executing phase: $phase_name"
    fi

    # Load BACKUP_TIMESTAMP for rollback phase
    if [ "$phase_name" = "rollback" ] && [ -f "${BACKUP_DIR}/.backup_timestamp" ]; then
        TIMESTAMP=$(cat "${BACKUP_DIR}/.backup_timestamp" 2>/dev/null)
        export TIMESTAMP
    fi

    # Export environment for subprocess
    export DRY_RUN FORCE_DEPLOY SKIP_MIGRATIONS SKIP_FRONTEND VERBOSE
    export PROD_HOME PROD_SERVER VENV_PATH BACKUP_DIR DEPLOY_LOG
    export TIMESTAMP SERVICES

    # Execute phase script
    if bash "$script_path"; then
        log_success "Phase completed: $phase_name"
        return 0
    else
        log_error "Phase failed: $phase_name"
        FAILED_PHASE="$phase_name"
        return 1
    fi
}

run_deployment() {
    local start_time=$(date +%s)

    log_section "========== DEPLOYMENT START =========="
    log_info "Configuration: $CONFIG_FILE"
    log_info "Target: $PROD_SERVER:$PROD_HOME"
    log_info "Log: $DEPLOY_LOG"

    # Display options
    echo ""
    log_info "Deployment Options:"
    log_info "  Dry-run: $DRY_RUN"
    log_info "  Force: $FORCE_DEPLOY"
    log_info "  Skip migrations: $SKIP_MIGRATIONS"
    log_info "  Skip frontend: $SKIP_FRONTEND"
    log_info "  Verbose: $VERBOSE"
    echo ""

    # Confirmation
    if [ "$FORCE_DEPLOY" = false ] && [ "$DRY_RUN" = false ]; then
        log_warning "Ready to deploy to PRODUCTION: $PROD_SERVER"
        read -p "Continue? [y/N]: " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Deployment cancelled by user"
            exit 0
        fi
    fi

    echo ""

    # PHASE 0: Pre-checks
    log_section "========== PHASE 0: PRE-CHECKS =========="
    if ! call_phase "pre-checks"; then
        EXIT_CODE=1
        if [ "$ROLLBACK_ON_ERROR" = true ]; then
            log_error "Pre-checks failed. Aborting deployment."
            return 1
        fi
    fi
    echo ""

    # PHASE 1: Backup
    log_section "========== PHASE 1: BACKUP =========="
    if ! call_phase "backup"; then
        EXIT_CODE=1
        if [ "$ROLLBACK_ON_ERROR" = true ]; then
            log_error "Backup failed. Aborting deployment."
            return 1
        fi
    fi
    echo ""

    # PHASE 2: Sync
    log_section "========== PHASE 2: SYNC =========="
    if ! call_phase "sync"; then
        EXIT_CODE=1
        if [ "$ROLLBACK_ON_ERROR" = true ]; then
            log_error "Sync failed. Aborting deployment."
            return 1
        fi
    fi
    echo ""

    # PHASE 3: Migrate (conditional)
    if [ "$SKIP_MIGRATIONS" = false ]; then
        log_section "========== PHASE 3: MIGRATE =========="
        if ! call_phase "migrate"; then
            EXIT_CODE=1
            if [ "$ROLLBACK_ON_ERROR" = true ]; then
                log_error "Migration failed. Aborting deployment."
                return 1
            fi
        fi
        echo ""
    else
        log_section "========== PHASE 3: MIGRATE (SKIPPED) =========="
        log_info "[SKIPPED] Database migrations"
        echo ""
    fi

    # PHASE 4: Services
    log_section "========== PHASE 4: SERVICES =========="
    if ! call_phase "services"; then
        EXIT_CODE=1
        if [ "$ROLLBACK_ON_ERROR" = true ]; then
            log_error "Service restart failed. Running rollback."
            call_phase "rollback" || true
            return 1
        fi
    fi
    echo ""

    # PHASE 5: Health checks
    log_section "========== PHASE 5: HEALTH CHECKS =========="
    if ! call_phase "health"; then
        EXIT_CODE=1
        if [ "$ROLLBACK_ON_ERROR" = true ]; then
            log_error "Health checks failed. Running rollback."
            call_phase "rollback" || true
            return 1
        fi
    fi
    echo ""

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_section "========== DEPLOYMENT COMPLETE =========="
    log_success "Deployment succeeded in ${duration}s"
    log_info "Log: $DEPLOY_LOG"

    return 0
}

error_handler() {
    local line_number=$1

    log_section "========== ERROR OCCURRED =========="
    log_error "Deployment failed at line $line_number"

    if [ -n "$FAILED_PHASE" ]; then
        log_error "Failed phase: $FAILED_PHASE"
    fi

    if [ "$ROLLBACK_ON_ERROR" = true ]; then
        log_info "Attempting rollback..."
        if call_phase "rollback"; then
            log_success "Rollback completed successfully"
            log_warning "Old version has been restored"
        else
            log_error "Rollback failed! Manual intervention required."
            log_error "See log: $DEPLOY_LOG"
        fi
    fi

    log_error "Log: $DEPLOY_LOG"
    exit 1
}

# ===== MAIN EXECUTION =====

# Set error trap
trap 'error_handler ${LINENO}' ERR

# Parse command-line arguments
parse_arguments "$@"

# Log execution start
{
    log_info "=== Deployment Start ==="
    log_info "Timestamp: $TIMESTAMP"
    log_info "User: $(whoami)"
    log_info "Host: $(hostname)"
    log_info "Working directory: $SCRIPT_DIR"
} | tee -a "$DEPLOY_LOG"

# Run deployment
if run_deployment | tee -a "$DEPLOY_LOG"; then
    log_success "✅ DEPLOYMENT SUCCESSFUL"
    {
        log_info "=== Deployment End ==="
        log_info "Exit code: 0"
    } | tee -a "$DEPLOY_LOG"
    exit 0
else
    log_error "❌ DEPLOYMENT FAILED"
    {
        log_info "=== Deployment End ==="
        log_info "Exit code: $?"
        log_error "Check rollback status above"
    } | tee -a "$DEPLOY_LOG"
    exit 1
fi
