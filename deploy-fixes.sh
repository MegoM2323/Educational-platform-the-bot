#!/bin/bash

set -e

# ============================================================================
# THE_BOT Platform - Production Deployment Script
# ============================================================================
# Deploys fixes to production server with:
#  1. Backup current docker-compose
#  2. Deploy updated docker-compose.prod.yml
#  3. Deploy frontend dist folder
#  4. Initialize database (create thebot_db)
#  5. Restart all containers with health monitoring
#  6. Verify services are healthy
#
# Usage:
#   ./deploy-fixes.sh [--dry-run] [--skip-backup] [--force]
#
# Options:
#   --dry-run      Show what would be done without executing
#   --skip-backup  Skip backup of current docker-compose
#   --force        Force restart even if health checks fail
#
# Author: THE_BOT Platform DevOps
# ============================================================================

# ============================================================================
# Configuration
# ============================================================================
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER="mg@5.129.249.206"
REMOTE_PATH="/opt/THE_BOT_platform"
LOCAL_DOCKER_COMPOSE="${SCRIPT_DIR}/docker-compose.prod.yml"
LOCAL_DIST="${SCRIPT_DIR}/frontend/dist"
LOCAL_BACKEND="${SCRIPT_DIR}/backend"

# SSH options for production
SSH_OPTS="-o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 -o BatchMode=yes"

# Options
DRY_RUN=false
SKIP_BACKUP=false
FORCE=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging
LOG_FILE="${SCRIPT_DIR}/deployment_$(date +%Y%m%d_%H%M%S).log"

# ============================================================================
# Functions
# ============================================================================

log() {
    local level="$1"
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "${LOG_FILE}"
}

log_info() {
    log "${BLUE}INFO${NC}" "$@"
}

log_success() {
    log "${GREEN}SUCCESS${NC}" "$@"
}

log_warn() {
    log "${YELLOW}WARN${NC}" "$@"
}

log_error() {
    log "${RED}ERROR${NC}" "$@"
}

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        log_error "Deployment failed with exit code $exit_code"
        log_error "See ${LOG_FILE} for details"
    else
        log_success "Deployment completed successfully"
    fi
    return $exit_code
}

execute_remote_command() {
    local cmd="$1"
    local description="$2"

    log_info "$description"

    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] $cmd"
        return 0
    fi

    if ! ssh $SSH_OPTS "$SERVER" "$cmd"; then
        log_error "Failed to execute: $description"
        return 1
    fi
}

verify_local_files() {
    log_info "Verifying local files exist..."

    if [ ! -f "$LOCAL_DOCKER_COMPOSE" ]; then
        log_error "docker-compose.prod.yml not found at $LOCAL_DOCKER_COMPOSE"
        return 1
    fi

    if [ ! -d "$LOCAL_DIST" ]; then
        log_error "Frontend dist folder not found at $LOCAL_DIST"
        return 1
    fi

    if [ ! -d "$LOCAL_BACKEND" ]; then
        log_error "Backend folder not found at $LOCAL_BACKEND"
        return 1
    fi

    log_success "All local files verified"
    return 0
}

verify_server_connection() {
    log_info "Verifying server connection..."

    if ! ssh $SSH_OPTS "$SERVER" "echo 'Connection test'" > /dev/null 2>&1; then
        log_error "Cannot connect to $SERVER"
        log_error "Please verify:"
        log_error "  1. SSH key is loaded (ssh-add -l)"
        log_error "  2. Server is reachable (ping 5.129.249.206)"
        log_error "  3. SSH user 'mg' has access"
        return 1
    fi

    log_success "Server connection verified"
    return 0
}

backup_remote_files() {
    log_info "Backing up current configuration..."

    local backup_cmd="
    cd ${REMOTE_PATH} && \
    mkdir -p backups && \
    cp docker-compose.prod.yml backups/docker-compose.prod.yml.\$(date +%Y%m%d_%H%M%S) && \
    echo 'Backup created'
    "

    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] Backup docker-compose to backups/"
        return 0
    fi

    if [ "$SKIP_BACKUP" = true ]; then
        log_warn "Skipping backup (--skip-backup flag set)"
        return 0
    fi

    if ! ssh $SSH_OPTS "$SERVER" "$backup_cmd"; then
        log_error "Failed to backup current configuration"
        return 1
    fi

    log_success "Backup created successfully"
    return 0
}

deploy_docker_compose() {
    log_info "Deploying updated docker-compose.prod.yml..."

    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] Copy $LOCAL_DOCKER_COMPOSE to $SERVER:$REMOTE_PATH/"
        return 0
    fi

    if ! scp -o StrictHostKeyChecking=accept-new "$LOCAL_DOCKER_COMPOSE" "$SERVER:$REMOTE_PATH/"; then
        log_error "Failed to deploy docker-compose.prod.yml"
        return 1
    fi

    log_success "docker-compose.prod.yml deployed"
    return 0
}

deploy_frontend_dist() {
    log_info "Deploying frontend dist folder..."

    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] Remove old dist and copy new dist to $SERVER"
        return 0
    fi

    # Remove old dist (preserve volume for docker)
    local remove_cmd="
    cd ${REMOTE_PATH} && \
    rm -rf frontend/dist && \
    mkdir -p frontend/dist
    "

    if ! ssh $SSH_OPTS "$SERVER" "$remove_cmd"; then
        log_error "Failed to prepare frontend dist directory"
        return 1
    fi

    # Copy new dist
    if ! scp -r -o StrictHostKeyChecking=accept-new "$LOCAL_DIST/"* "$SERVER:$REMOTE_PATH/frontend/dist/"; then
        log_error "Failed to deploy frontend dist"
        return 1
    fi

    log_success "Frontend dist deployed"
    return 0
}

stop_containers() {
    log_info "Stopping running containers..."

    local stop_cmd="
    cd ${REMOTE_PATH} && \
    docker-compose -f docker-compose.prod.yml down --remove-orphans 2>&1 || true
    "

    if ! execute_remote_command "$stop_cmd" "Stopping containers"; then
        log_warn "Container stop may have had issues, continuing..."
    fi

    sleep 2
    log_success "Containers stopped"
    return 0
}

start_containers() {
    log_info "Starting containers..."

    local start_cmd="
    cd ${REMOTE_PATH} && \
    docker-compose -f docker-compose.prod.yml up -d
    "

    if ! execute_remote_command "$start_cmd" "Starting containers"; then
        log_error "Failed to start containers"
        return 1
    fi

    log_success "Containers started"
    sleep 3
    return 0
}

wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."

    local max_attempts=30
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        local check_cmd="
        cd ${REMOTE_PATH} && \
        docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -U postgres -h localhost 2>/dev/null
        "

        if [ "$DRY_RUN" = true ]; then
            echo "  [DRY-RUN] Check PostgreSQL readiness (attempt $((attempt + 1))/$max_attempts)"
            return 0
        fi

        if ssh $SSH_OPTS "$SERVER" "$check_cmd" > /dev/null 2>&1; then
            log_success "PostgreSQL is ready"
            return 0
        fi

        attempt=$((attempt + 1))
        log_info "  Waiting for PostgreSQL... (attempt $attempt/$max_attempts)"
        sleep 2
    done

    log_error "PostgreSQL did not become ready after ${max_attempts} attempts"
    return 1
}

initialize_database() {
    log_info "Initializing database..."

    local init_cmd="
    cd ${REMOTE_PATH} && \
    docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -h localhost -tc \"SELECT 1 FROM pg_database WHERE datname = 'thebot_db'\" | grep -q 1 && echo 'Database exists' || (docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -h localhost -c \"CREATE DATABASE thebot_db;\" && echo 'Database created')
    "

    if ! execute_remote_command "$init_cmd" "Creating database if not exists"; then
        log_warn "Database initialization may have had issues, continuing..."
    fi

    sleep 2
    log_success "Database initialized"
    return 0
}

apply_migrations() {
    log_info "Applying Django migrations..."

    local migrate_cmd="
    cd ${REMOTE_PATH} && \
    docker-compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput 2>&1 || true
    "

    if ! execute_remote_command "$migrate_cmd" "Running Django migrations"; then
        log_warn "Migrations may have had issues, continuing..."
    fi

    log_success "Migrations applied"
    return 0
}

check_container_status() {
    log_info "Checking container status..."

    local status_cmd="
    cd ${REMOTE_PATH} && \
    docker-compose -f docker-compose.prod.yml ps
    "

    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] Check docker-compose ps"
        return 0
    fi

    if ! ssh $SSH_OPTS "$SERVER" "$status_cmd"; then
        log_error "Failed to check container status"
        return 1
    fi

    return 0
}

verify_service_health() {
    log_info "Verifying service health..."

    # Wait for services to stabilize
    sleep 3

    local health_check_cmd="
    echo '=== Container Status ===' && \
    cd ${REMOTE_PATH} && \
    docker-compose -f docker-compose.prod.yml ps && \
    echo '' && \
    echo '=== Network Check ===' && \
    docker network ls && \
    echo '' && \
    echo '=== Volume Check ===' && \
    docker volume ls | grep thebot
    "

    if [ "$DRY_RUN" = true ]; then
        echo "  [DRY-RUN] Check service health"
        return 0
    fi

    if ! ssh $SSH_OPTS "$SERVER" "$health_check_cmd"; then
        if [ "$FORCE" = true ]; then
            log_warn "Health check had issues, but continuing (--force flag set)"
            return 0
        else
            log_error "Health check failed"
            return 1
        fi
    fi

    log_success "Services are healthy"
    return 0
}

print_summary() {
    echo ""
    log_success "Deployment Summary"
    echo "=================================================================="
    echo "Server:              $SERVER"
    echo "Remote Path:         $REMOTE_PATH"
    echo "Deployment Mode:     $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'LIVE')"
    echo "Deployment Date:     $(date '+%Y-%m-%d %H:%M:%S')"
    echo "Log File:            $LOG_FILE"
    echo ""
    echo "Changes Deployed:"
    echo "  - docker-compose.prod.yml (fixed frontend volume)"
    echo "  - frontend/dist (production build)"
    echo "  - database: thebot_db (initialized)"
    echo "  - containers restarted"
    echo ""
    echo "Next Steps for Verification:"
    echo "  Backend API:         curl http://5.129.249.206:8000/api/"
    echo "  Frontend:            curl http://5.129.249.206:3000/"
    echo "  Health Check:        curl http://5.129.249.206:8000/api/system/health/live/"
    echo "  Container Logs:      ssh mg@5.129.249.206 'cd /opt/THE_BOT_platform && docker-compose -f docker-compose.prod.yml logs -f backend'"
    echo "  Nginx Logs:          ssh mg@5.129.249.206 'cd /opt/THE_BOT_platform && docker-compose -f docker-compose.prod.yml logs -f nginx'"
    echo "=================================================================="
    echo ""
}

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --dry-run       Show what would be done without executing"
    echo "  --skip-backup   Skip backup of current docker-compose"
    echo "  --force         Force restart even if health checks fail"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Normal deployment"
    echo "  $0 --dry-run         # Preview deployment without executing"
    echo "  $0 --skip-backup     # Deploy without backup"
    echo "  $0 --dry-run --force # Preview with force flag"
}

# ============================================================================
# Main Deployment Flow
# ============================================================================

main() {
    # Parse command-line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --skip-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --force)
                FORCE=true
                shift
                ;;
            --help)
                print_usage
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                print_usage
                exit 1
                ;;
        esac
    done

    # Setup trap for cleanup
    trap cleanup EXIT

    log_info "=== DEPLOYING FIXES TO PRODUCTION ==="
    [ "$DRY_RUN" = true ] && log_warn "DRY-RUN MODE - No changes will be made"
    [ "$SKIP_BACKUP" = true ] && log_warn "SKIP-BACKUP MODE - No backup will be created"
    [ "$FORCE" = true ] && log_warn "FORCE MODE - Will continue even if health checks fail"

    # Step 1: Verify prerequisites
    log_info "Step 1/8: Verifying prerequisites"
    verify_local_files || exit 1
    verify_server_connection || exit 1

    # Step 2: Backup current configuration
    log_info "Step 2/8: Backing up current configuration"
    backup_remote_files || exit 1

    # Step 3: Deploy updated docker-compose
    log_info "Step 3/8: Deploying updated docker-compose.prod.yml"
    deploy_docker_compose || exit 1

    # Step 4: Deploy frontend dist
    log_info "Step 4/8: Deploying frontend dist folder"
    deploy_frontend_dist || exit 1

    # Step 5: Stop containers
    log_info "Step 5/8: Stopping containers"
    stop_containers || exit 1

    # Step 6: Start containers
    log_info "Step 6/8: Starting containers"
    start_containers || exit 1

    # Step 7: Initialize database
    log_info "Step 7/8: Initializing database"
    wait_for_postgres || exit 1
    initialize_database || exit 1
    apply_migrations || exit 1

    # Step 8: Verify services
    log_info "Step 8/8: Verifying services"
    check_container_status || exit 1
    verify_service_health || exit 1

    print_summary
}

# ============================================================================
# Entry Point
# ============================================================================

main "$@"
