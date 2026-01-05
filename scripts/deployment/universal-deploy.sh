#!/bin/bash

################################################################################
#                                                                              #
#  UNIVERSAL DEPLOY SCRIPT - THE_BOT PLATFORM                                #
#  8-Phase Production Deployment Orchestrator                                #
#                                                                              #
#  Usage: ./universal-deploy.sh [OPTIONS]                                    #
#  Location: scripts/deployment/universal-deploy.sh                          #
#                                                                              #
################################################################################

set -euo pipefail

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Source deployment utilities
if [[ -f "$SCRIPT_DIR/deployment-utils.sh" ]]; then
    source "$SCRIPT_DIR/deployment-utils.sh"
else
    echo "ERROR: deployment-utils.sh not found at $SCRIPT_DIR/deployment-utils.sh"
    exit 1
fi

# Source deployment environment
DEPLOY_ENV="$SCRIPT_DIR/.deploy.env"
if [[ -f "$DEPLOY_ENV" ]]; then
    source "$DEPLOY_ENV"
else
    echo "ERROR: Configuration not found at $DEPLOY_ENV"
    echo "Please create .deploy.env from .deploy.env.template:"
    echo "  cp $SCRIPT_DIR/.deploy.env.template $DEPLOY_ENV"
    echo "  nano $DEPLOY_ENV"
    exit 1
fi

# Default values
DRY_RUN="${DRY_RUN:-false}"
ROLLBACK_ON_ERROR="${ROLLBACK_ON_ERROR:-true}"
GIT_BRANCH="${GIT_BRANCH:-main}"
ENVIRONMENT="${ENVIRONMENT:-production}"
VERBOSE="${VERBOSE:-false}"
FORCE="${FORCE:-false}"

# Parse command line arguments
DEPLOY_MODE="normal"
ROLLBACK_TIMESTAMP=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --branch)
            GIT_BRANCH="$2"
            shift 2
            ;;
        --environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        --rollback)
            DEPLOY_MODE="rollback"
            ROLLBACK_TIMESTAMP="$2"
            shift 2
            ;;
        --notify)
            NOTIFY_SERVICE="$2"
            shift 2
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help)
            show_help
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Show help
show_help() {
    cat << EOF
UNIVERSAL DEPLOYMENT SCRIPT - THE_BOT Platform

Usage: ./universal-deploy.sh [OPTIONS]

Options:
  --dry-run              Preview deployment without making changes
  --branch BRANCH        Deploy specific branch (default: main)
  --environment ENV      Environment: production|staging (default: production)
  --rollback TIMESTAMP   Rollback to specific backup instead of deploying
  --notify SERVICE       Send notifications: slack|email
  --verbose              Detailed logging output
  --force                Skip confirmation prompts
  --help                 Show this help message

Examples:
  # Full production deployment
  ./universal-deploy.sh --verbose --notify slack

  # Preview deployment (dry-run)
  ./universal-deploy.sh --dry-run --verbose

  # Deploy specific branch to staging
  ./universal-deploy.sh --branch develop --environment staging

  # Rollback to specific time
  ./universal-deploy.sh --rollback 20260105_120000

EOF
}

# Get timestamp for logs
DEPLOY_ID=$(date +%Y%m%d_%H%M%S)
LOG_DIR="${PROJECT_ROOT}/deployment-logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/universal-deploy_${DEPLOY_ID}.log"

# Initialize logging
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

print_header "UNIVERSAL DEPLOYMENT SYSTEM"
print_info "Deploy ID: $DEPLOY_ID"
print_info "Environment: $ENVIRONMENT"
print_info "Branch: $GIT_BRANCH"
[[ "$DRY_RUN" == "true" ]] && print_warning "DRY-RUN MODE - No changes will be made"
print_info "Log file: $LOG_FILE"

################################################################################
# PHASE 0: INITIALIZATION
################################################################################

phase_0_initialization() {
    local phase="PHASE 0"
    print_header "$phase: INITIALIZATION"

    # Validate configuration
    print_step "Validating configuration..."
    [[ -z "${SSH_HOST:-}" ]] && { print_error "SSH_HOST not set"; return 1; }
    [[ -z "${SSH_USER:-}" ]] && { print_error "SSH_USER not set"; return 1; }
    [[ -z "${VEXTRA_HOME:-}" ]] && { print_error "VEXTRA_HOME not set"; return 1; }

    print_success "Configuration valid"

    # Test SSH connection
    print_step "Testing SSH connection to $SSH_HOST..."
    if ssh_check "$SSH_USER@$SSH_HOST" -p "$SSH_PORT"; then
        print_success "SSH connection OK"
    else
        print_error "SSH connection failed"
        return 1
    fi

    print_success "$phase completed"
    return 0
}

################################################################################
# PHASE 1: PRE-DEPLOYMENT CHECKS
################################################################################

phase_1_prechecks() {
    local phase="PHASE 1"
    print_header "$phase: PRE-DEPLOYMENT CHECKS (22 checks)"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "[DRY-RUN] Would run: $SCRIPT_DIR/pre-deploy-check.sh"
        return 0
    fi

    # Run pre-deployment checks
    if bash "$SCRIPT_DIR/pre-deploy-check.sh" --verbose --remote; then
        print_success "$phase completed - All checks passed"
        return 0
    else
        print_error "$phase failed - Pre-deployment checks did not pass"
        return 1
    fi
}

################################################################################
# PHASE 2: BACKUP & SNAPSHOT
################################################################################

phase_2_backup() {
    local phase="PHASE 2"
    print_header "$phase: BACKUP & SNAPSHOT"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "[DRY-RUN] Would create database backup"
        print_info "[DRY-RUN] Would create code backup"
        return 0
    fi

    print_step "Creating database backup..."
    if bash "$SCRIPT_DIR/backup-manager.sh" create-db; then
        print_success "Database backup created"
    else
        print_error "Database backup failed"
        return 1
    fi

    print_step "Creating code backup..."
    if bash "$SCRIPT_DIR/backup-manager.sh" create-code; then
        print_success "Code backup created"
    else
        print_error "Code backup failed"
        return 1
    fi

    print_success "$phase completed"
    return 0
}

################################################################################
# PHASE 3: CODE DEPLOYMENT
################################################################################

phase_3_code_deploy() {
    local phase="PHASE 3"
    print_header "$phase: CODE DEPLOYMENT"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "[DRY-RUN] Would execute: git fetch origin"
        print_info "[DRY-RUN] Would execute: git checkout $GIT_BRANCH"
        print_info "[DRY-RUN] Would execute: git pull origin $GIT_BRANCH --ff-only"
        return 0
    fi

    print_step "Deploying code via git..."
    ssh_exec "$SSH_USER@$SSH_HOST" -p "$SSH_PORT" "cd $VEXTRA_HOME && git fetch origin && git checkout '$GIT_BRANCH' && git pull origin '$GIT_BRANCH' --ff-only"

    print_success "$phase completed"
    return 0
}

################################################################################
# PHASE 4: DOCKER BUILD & DEPLOY
################################################################################

phase_4_docker_deploy() {
    local phase="PHASE 4"
    print_header "$phase: DOCKER BUILD & DEPLOY"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "[DRY-RUN] Would execute: docker-compose build backend frontend"
        print_info "[DRY-RUN] Would execute: docker-compose up -d"
        print_info "[DRY-RUN] Estimated time: 10-15 minutes"
        return 0
    fi

    print_step "Building and deploying Docker services..."
    ssh_exec "$SSH_USER@$SSH_HOST" -p "$SSH_PORT" "cd $VEXTRA_HOME && docker-compose -f docker-compose.prod.yml build --no-cache backend frontend && docker-compose -f docker-compose.prod.yml up -d"

    print_step "Waiting for services to become healthy..."
    sleep 10

    print_success "$phase completed"
    return 0
}

################################################################################
# PHASE 5: DATABASE MIGRATIONS
################################################################################

phase_5_migrations() {
    local phase="PHASE 5"
    print_header "$phase: DATABASE MIGRATIONS"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "[DRY-RUN] Would show: python manage.py showmigrations --plan"
        print_info "[DRY-RUN] Would execute: python manage.py migrate --noinput"
        print_info "[DRY-RUN] Would execute: python manage.py collectstatic --noinput"
        return 0
    fi

    print_step "Checking pending migrations..."
    ssh_exec "$SSH_USER@$SSH_HOST" -p "$SSH_PORT" "cd $VEXTRA_HOME && docker-compose -f docker-compose.prod.yml exec -T backend python manage.py showmigrations --plan"

    print_step "Applying migrations..."
    ssh_exec "$SSH_USER@$SSH_HOST" -p "$SSH_PORT" "cd $VEXTRA_HOME && docker-compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput"

    print_step "Collecting static files..."
    ssh_exec "$SSH_USER@$SSH_HOST" -p "$SSH_PORT" "cd $VEXTRA_HOME && docker-compose -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput --clear"

    print_success "$phase completed"
    return 0
}

################################################################################
# PHASE 6: CELERY SETUP
################################################################################

phase_6_celery() {
    local phase="PHASE 6"
    print_header "$phase: CELERY SETUP"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "[DRY-RUN] Would restart: celery_worker"
        print_info "[DRY-RUN] Would restart: celery_beat"
        return 0
    fi

    print_step "Restarting Celery worker..."
    ssh_exec "$SSH_USER@$SSH_HOST" -p "$SSH_PORT" "cd $VEXTRA_HOME && docker-compose -f docker-compose.prod.yml restart celery_worker"

    print_step "Restarting Celery beat..."
    ssh_exec "$SSH_USER@$SSH_HOST" -p "$SSH_PORT" "cd $VEXTRA_HOME && docker-compose -f docker-compose.prod.yml restart celery_beat"

    print_success "$phase completed"
    return 0
}

################################################################################
# PHASE 7: POST-DEPLOY VERIFICATION
################################################################################

phase_7_verify() {
    local phase="PHASE 7"
    print_header "$phase: POST-DEPLOY VERIFICATION (20 checks)"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "[DRY-RUN] Would run: $SCRIPT_DIR/verify-deployment.sh"
        return 0
    fi

    # Run health checks
    if bash "$SCRIPT_DIR/verify-deployment.sh" --wait 60; then
        print_success "$phase completed - All health checks passed"
        return 0
    else
        print_warning "$phase completed with warnings - Some health checks may have failed"
        return 1
    fi
}

################################################################################
# ERROR HANDLING & ROLLBACK
################################################################################

handle_error() {
    local phase="$1"
    local exit_code="$2"

    print_error "ERROR in $phase (exit code: $exit_code)"

    if [[ "$ROLLBACK_ON_ERROR" == "true" ]] && [[ "$DRY_RUN" != "true" ]]; then
        print_warning "Automatic rollback triggered..."
        bash "$SCRIPT_DIR/rollback.sh" --latest
    fi

    print_error "Deployment failed. Check logs: $LOG_FILE"
    exit "$exit_code"
}

# Trap errors
trap 'handle_error "Deployment" $?' ERR

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    local exit_code=0

    if [[ "$DEPLOY_MODE" == "rollback" ]]; then
        print_header "ROLLBACK MODE"
        bash "$SCRIPT_DIR/rollback.sh" --rollback "$ROLLBACK_TIMESTAMP"
        return $?
    fi

    # Execute all phases
    phase_0_initialization || return 1
    phase_1_prechecks || return 2
    phase_2_backup || return 1
    phase_3_code_deploy || return 1
    phase_4_docker_deploy || return 1
    phase_5_migrations || return 1
    phase_6_celery || return 1
    phase_7_verify || { exit_code=3; }

    print_header "DEPLOYMENT COMPLETE"
    if [[ "$DRY_RUN" == "true" ]]; then
        print_success "DRY-RUN completed successfully (no changes made)"
    else
        print_success "Production deployment completed successfully!"
        print_info "Website: https://$DOMAIN"
        print_info "Check health: ./scripts/deployment/verify-deployment.sh"
    fi

    return "$exit_code"
}

# Run main function
main
exit $?
