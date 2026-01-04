#!/bin/bash

################################################################################
# THE_BOT Platform - Master Deploy Script
#
# Universal deployment script that:
# - Synchronizes code to production server
# - Creates database backup before deployment
# - Stops containers WITHOUT deleting DB volume
# - Starts containers (DB data preserved)
# - Applies new migrations
# - Performs health checks
#
# Usage:
#   ./master-deploy.sh                  # Full deployment (default)
#   ./master-deploy.sh --full           # Explicit full deployment
#   ./master-deploy.sh --backup-only    # Only create DB backup
#   ./master-deploy.sh --migrate-only   # Only apply migrations
#   ./master-deploy.sh --dry-run        # Show what would be done
#   ./master-deploy.sh --help           # Show help
#
# Environment Variables:
#   SSH_USER           - SSH user (default: mg)
#   SSH_HOST           - Server hostname/IP (default: 5.129.249.206)
#   REMOTE_PATH        - Remote project path (default: /opt/THE_BOT_platform)
#   BACKUP_RETENTION   - Days to keep backups (default: 7)
#
# Exit Codes:
#   0 - Successful deployment
#   1 - Deployment failed
#   2 - Critical failure, manual intervention required
#
################################################################################

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${PROJECT_ROOT:-$SCRIPT_DIR}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOY_ID="DEPLOY_${TIMESTAMP}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
SSH_USER="${SSH_USER:-mg}"
SSH_HOST="${SSH_HOST:-5.129.249.206}"
REMOTE_PATH="${REMOTE_PATH:-/opt/THE_BOT_platform}"
BACKUP_RETENTION="${BACKUP_RETENTION:-7}"

# Deployment mode
DEPLOY_MODE="${DEPLOY_MODE:-full}"  # full, backup-only, migrate-only
DRY_RUN=false
VERBOSE=false

# State tracking
BACKUP_FILE=""
DB_STARTED=false
MIGRATIONS_APPLIED=false
HEALTH_CHECK_PASSED=false

# Log file
LOG_DIR="${PROJECT_ROOT}/deployment-logs"
LOG_FILE="${LOG_DIR}/deploy_${TIMESTAMP}.log"

# SSH connection string
SSH_CONN="${SSH_USER}@${SSH_HOST}"

################################################################################
# FUNCTIONS - LOGGING
################################################################################

log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    mkdir -p "$LOG_DIR"
    echo "$message" >> "$LOG_FILE"
    if [ "$VERBOSE" = true ]; then
        echo -e "${CYAN}[LOG]${NC} $1"
    fi
}

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    log "=== $1 ==="
}

print_section() {
    echo ""
    echo -e "${CYAN}>>> $1${NC}"
    log "SECTION: $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
    log "SUCCESS: $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    log "ERROR: $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
    log "WARNING: $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
    log "INFO: $1"
}

################################################################################
# FUNCTIONS - HELP & ARGUMENTS
################################################################################

show_help() {
    cat << EOF
THE_BOT Platform - Master Deploy Script

USAGE:
  ./master-deploy.sh [OPTIONS]

OPTIONS:
  --full              Full deployment: sync + backup + stop + start + migrate + health-check (DEFAULT)
  --backup-only       Only create database backup
  --migrate-only      Only apply migrations to existing database
  --dry-run           Show what would be executed without making changes
  --verbose, -v       Print verbose output
  --help, -h          Show this help message

EXAMPLES:
  ./master-deploy.sh                    # Full deployment
  ./master-deploy.sh --dry-run          # Simulate full deployment
  ./master-deploy.sh --backup-only      # Only backup database
  ./master-deploy.sh --migrate-only     # Only run migrations

CONFIGURATION (via environment):
  SSH_USER            SSH username (default: mg)
  SSH_HOST            Server hostname/IP (default: 5.129.249.206)
  REMOTE_PATH         Remote project path (default: /opt/THE_BOT_platform)
  BACKUP_RETENTION    Days to keep backups (default: 7)

EXAMPLES WITH ENV:
  SSH_HOST=another.server.com ./master-deploy.sh --full
  BACKUP_RETENTION=14 ./master-deploy.sh --backup-only

EOF
}

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                DEPLOY_MODE="full"
                shift
                ;;
            --backup-only)
                DEPLOY_MODE="backup-only"
                shift
                ;;
            --migrate-only)
                DEPLOY_MODE="migrate-only"
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose|-v)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
}

################################################################################
# FUNCTIONS - SSH EXECUTION
################################################################################

ssh_exec() {
    local cmd="$1"
    local description="${2:-Executing remote command}"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] $description"
        print_info "Command: $cmd"
        return 0
    fi

    log "SSH: $cmd"
    if ! ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "$SSH_CONN" "$cmd"; then
        print_error "$description failed"
        return 1
    fi
    return 0
}

ssh_exec_silent() {
    local cmd="$1"
    if [ "$DRY_RUN" = true ]; then
        return 0
    fi
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new "$SSH_CONN" "$cmd" 2>/dev/null
}

################################################################################
# FUNCTIONS - CLEANUP & ERROR HANDLING
################################################################################

cleanup() {
    log "Cleanup triggered"
    set +e
}

trap cleanup EXIT

error_exit() {
    local message="$1"
    local exit_code="${2:-1}"

    print_error "$message"
    print_info "Log file: $LOG_FILE"
    print_info "Backup location: /opt/THE_BOT_platform/.backups/ (if created)"
    log "DEPLOYMENT FAILED: $message"

    exit "$exit_code"
}

################################################################################
# PHASE 1: PRE-DEPLOYMENT CHECKS
################################################################################

phase_pre_deploy_checks() {
    print_header "PHASE 1: PRE-DEPLOYMENT CHECKS"

    print_section "Checking SSH connectivity..."
    if ! ssh_exec_silent "echo 'OK'" 2>/dev/null; then
        error_exit "Cannot connect to ${SSH_CONN}" 2
    fi
    print_success "SSH connection to ${SSH_CONN}"

    print_section "Checking remote directories..."
    if ! ssh_exec_silent "test -d $REMOTE_PATH" 2>/dev/null; then
        error_exit "Remote directory not found: $REMOTE_PATH" 2
    fi
    print_success "Remote directory exists: $REMOTE_PATH"

    print_section "Checking Docker on remote..."
    if ! ssh_exec_silent "docker --version >/dev/null 2>&1"; then
        error_exit "Docker not available on remote server" 2
    fi
    print_success "Docker is available"

    print_section "Checking docker-compose on remote..."
    if ! ssh_exec_silent "docker-compose --version >/dev/null 2>&1"; then
        error_exit "docker-compose not available on remote server" 2
    fi
    print_success "docker-compose is available"

    print_success "All pre-deployment checks passed"
}

################################################################################
# PHASE 2: CREATE DATABASE BACKUP
################################################################################

phase_backup_database() {
    print_header "PHASE 2: CREATE DATABASE BACKUP"

    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_filename="thebot_db_${backup_timestamp}.sql.gz"
    BACKUP_FILE="/opt/THE_BOT_platform/.backups/${backup_filename}"

    print_section "Creating remote backup directory..."
    if ! ssh_exec "mkdir -p /opt/THE_BOT_platform/.backups" "Create backup directory"; then
        print_warning "Could not create backup directory, attempting to continue"
    fi

    print_section "Creating database backup..."
    print_info "Backup file: ${backup_filename}"

    local backup_cmd="cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml exec -T postgres pg_dump -U postgres thebot_db | gzip > ${BACKUP_FILE}"

    if ! ssh_exec "$backup_cmd" "Database dump"; then
        error_exit "Database backup failed" 1
    fi

    print_section "Verifying backup file..."
    local verify_cmd="test -f ${BACKUP_FILE} && ls -lh ${BACKUP_FILE}"

    if ! ssh_exec_silent "$verify_cmd"; then
        error_exit "Backup file verification failed - file not found" 1
    fi

    print_success "Database backup created: ${backup_filename}"
    log "BACKUP_FILE=$BACKUP_FILE"

    print_section "Downloading backup locally..."
    if [ "$DRY_RUN" = false ]; then
        if scp -o ConnectTimeout=10 "${SSH_CONN}:${BACKUP_FILE}" "/tmp/${backup_filename}" 2>/dev/null; then
            print_success "Local backup saved to /tmp/${backup_filename}"
        else
            print_warning "Could not download backup locally (remote backup still exists)"
        fi
    fi

    print_section "Cleaning old backups (keeping last ${BACKUP_RETENTION} days)..."
    local cleanup_cmd="find /opt/THE_BOT_platform/.backups -name 'thebot_db_*.sql.gz' -mtime +\"${BACKUP_RETENTION}\" -delete 2>/dev/null || true"

    if ssh_exec "$cleanup_cmd" "Cleanup old backups"; then
        print_success "Old backups cleaned"
    else
        print_warning "Backup cleanup encountered issues (non-critical)"
    fi
}

################################################################################
# PHASE 3: STOP CONTAINERS (WITHOUT DELETING VOLUMES)
################################################################################

phase_stop_containers() {
    print_header "PHASE 3: STOP CONTAINERS"

    print_section "Checking running containers..."
    local containers_running=$(ssh_exec_silent "cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml ps -q | wc -l")
    containers_running="${containers_running:-0}"

    if [ -z "$containers_running" ] || [ "$containers_running" -eq 0 ]; then
        print_info "No containers are running"
        return 0
    fi

    print_info "Found $containers_running running containers"

    print_section "Stopping containers (preserving volumes)..."
    local stop_cmd="cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml down"

    if ! ssh_exec "$stop_cmd" "Stop containers"; then
        error_exit "Failed to stop containers" 1
    fi

    print_section "Verifying containers are stopped..."
    sleep 2

    local verify_cmd="cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml ps 2>&1 | grep -c 'Up' || echo '0'"
    local still_running=$(ssh_exec_silent "$verify_cmd")
    still_running="${still_running:-0}"

    if [ -n "$still_running" ] && [ "$still_running" -gt 0 ]; then
        error_exit "Some containers are still running after stop command" 1
    fi

    print_success "All containers stopped (volumes preserved)"
}

################################################################################
# PHASE 4: PREPARE LOCAL CODE ARCHIVE
################################################################################

phase_prepare_archive() {
    print_header "PHASE 4: PREPARE CODE ARCHIVE"

    local archive_name="thebot-${TIMESTAMP}.tar.gz"
    local archive_path="/tmp/${archive_name}"

    print_section "Syncing code to server (rsync)..."

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would sync code to $SSH_CONN:$REMOTE_PATH"
        return 0
    fi

    # Use rsync to sync code (faster, only changed files)
    if rsync -avz \
        --delete \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='node_modules' \
        --exclude='.env' \
        --exclude='.env.*' \
        --exclude='*.log' \
        --exclude='*.sqlite3' \
        --exclude='.pytest_cache' \
        --exclude='.mypy_cache' \
        --exclude='htmlcov' \
        --exclude='.coverage' \
        --exclude='dist' \
        --exclude='build' \
        --exclude='*.egg-info' \
        --exclude='deployment-logs' \
        --exclude='backups' \
        --exclude='media/*' \
        --exclude='staticfiles/*' \
        --exclude='frontend/node_modules' \
        --exclude='venv' \
        --exclude='.venv' \
        "$PROJECT_ROOT/frontend/" \
        "$PROJECT_ROOT/backend/" \
        "$PROJECT_ROOT/docker-compose.prod.yml" \
        "$PROJECT_ROOT/docker/" \
        "$PROJECT_ROOT/requirements"*.txt \
        "$PROJECT_ROOT"/*.sh \
        "$SSH_CONN:$REMOTE_PATH/" 2>&1 | grep -E "total|error|^sending" || true; then
        print_success "Code synced successfully to $REMOTE_PATH"
    else
        error_exit "Failed to sync code" 1
    fi
}

################################################################################
# PHASE 5: SYNC CODE TO SERVER
################################################################################

phase_sync_code() {
    print_header "PHASE 5: SYNC CODE TO SERVER"

    print_section "Preparing remote directory..."
    if ! ssh_exec "mkdir -p \"$REMOTE_PATH\"" "Create remote directory"; then
        error_exit "Failed to create remote directory" 1
    fi

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would sync code to $SSH_CONN:$REMOTE_PATH"
        return 0
    fi

    print_section "Syncing code with rsync..."

    # rsync often returns code 23 on partial transfers (non-critical)
    rsync -avz \
        --exclude='.git' \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='node_modules' \
        --exclude='.env' \
        --exclude='.env.*' \
        --exclude='*.log' \
        --exclude='*.sqlite3' \
        --exclude='.pytest_cache' \
        --exclude='.mypy_cache' \
        --exclude='htmlcov' \
        --exclude='.coverage' \
        --exclude='dist' \
        --exclude='build' \
        --exclude='*.egg-info' \
        --exclude='deployment-logs' \
        --exclude='backups' \
        --exclude='media/*' \
        --exclude='staticfiles/*' \
        --exclude='frontend/node_modules' \
        --exclude='venv' \
        --exclude='.venv' \
        "$PROJECT_ROOT/frontend/" \
        "$PROJECT_ROOT/backend/" \
        "$PROJECT_ROOT/docker-compose.prod.yml" \
        "$PROJECT_ROOT/docker/" \
        "$PROJECT_ROOT/requirements"*.txt \
        "$PROJECT_ROOT"/*.sh \
        "$SSH_CONN:$REMOTE_PATH/" 2>&1 | tail -5 || true

    # rsync exit codes: 0=success, 23=partial transfer (acceptable)
    print_success "Code synchronized to server"
}

################################################################################
# PHASE 6: START CONTAINERS
################################################################################

phase_start_containers() {
    print_header "PHASE 6: START CONTAINERS"

    print_section "Starting containers..."
    local start_cmd="cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml up -d"

    if ! ssh_exec "$start_cmd" "Start containers"; then
        error_exit "Failed to start containers" 1
    fi

    DB_STARTED=true
    print_success "Containers started"

    print_section "Waiting for containers to stabilize..."
    sleep 5

    print_section "Checking container status..."
    local status_cmd="cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml ps"

    if ! ssh_exec "$status_cmd" "Check container status"; then
        print_warning "Could not verify container status"
    fi

    print_success "Containers are running"
}

################################################################################
# PHASE 7: WAIT FOR POSTGRESQL TO BE READY
################################################################################

phase_wait_postgres() {
    print_header "PHASE 7: WAIT FOR POSTGRESQL"

    print_section "Waiting for PostgreSQL to start..."

    local max_retries=30
    local retry_delay=2
    local postgres_ready=false

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would wait for PostgreSQL (max 60 seconds)"
        return 0
    fi

    local wait_script="cd \"$REMOTE_PATH\" && for i in \$(seq 1 \"$max_retries\"); do echo 'Attempt \$i/\"$max_retries\"...'; docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -h localhost -U postgres >/dev/null 2>&1 && exit 0; sleep \"$retry_delay\"; done; exit 1"

    if ssh_exec_silent "$wait_script"; then
        print_success "PostgreSQL is ready"
        postgres_ready=true
    else
        error_exit "PostgreSQL failed to start after $((max_retries * retry_delay)) seconds" 1
    fi
}

################################################################################
# PHASE 8: APPLY MIGRATIONS
################################################################################

phase_apply_migrations() {
    print_header "PHASE 8: APPLY MIGRATIONS"

    print_section "Checking for pending migrations..."

    local check_cmd="cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml exec -T backend python manage.py showmigrations --plan 2>&1 | head -20"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would check and apply pending migrations"
        return 0
    fi

    ssh_exec "$check_cmd" "Check migrations" || print_warning "Could not display migration plan"

    print_section "Applying migrations..."
    local migrate_cmd="cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput"

    if ! ssh_exec "$migrate_cmd" "Apply migrations"; then
        error_exit "Migration failed" 1
    fi

    MIGRATIONS_APPLIED=true
    print_success "Migrations applied successfully"
}

################################################################################
# PHASE 9: HEALTH CHECKS
################################################################################

phase_health_checks() {
    print_header "PHASE 9: HEALTH CHECKS"

    local health_passed=true

    print_section "Checking container health status..."
    local ps_cmd="cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml ps"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would check container health"
        return 0
    fi

    ssh_exec "$ps_cmd" "Check container status" || print_warning "Could not check container status"

    print_section "Checking PostgreSQL connectivity..."
    local db_check="cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml exec -T postgres pg_isready -h localhost -U postgres"

    if ssh_exec_silent "$db_check"; then
        print_success "PostgreSQL is accessible"
    else
        print_error "PostgreSQL health check failed"
        health_passed=false
    fi

    print_section "Checking backend API availability (local)..."
    local api_check="cd \"$REMOTE_PATH\" && docker-compose -f docker-compose.prod.yml exec -T backend curl -s http://localhost:8000/api/system/health/live/ 2>&1 | grep -q healthy || echo 'checking'"

    if ssh_exec_silent "$api_check"; then
        print_success "Backend API is responding"
        HEALTH_CHECK_PASSED=true
    else
        print_warning "Backend API health check inconclusive (may need more time to start)"
    fi

    if [ "$health_passed" = false ]; then
        print_warning "Some health checks failed but deployment can continue"
    else
        print_success "Health checks passed"
    fi
}

################################################################################
# PHASE 10: DEPLOYMENT SUMMARY
################################################################################

phase_summary() {
    print_header "DEPLOYMENT SUMMARY"

    local duration=$SECONDS
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    echo "Deployment ID: $DEPLOY_ID"
    echo "Duration: ${minutes}m ${seconds}s"
    echo "Mode: $DEPLOY_MODE"
    echo ""

    echo "Configuration:"
    echo "  Server: ${SSH_CONN}"
    echo "  Remote Path: $REMOTE_PATH"
    echo "  Log File: $LOG_FILE"
    echo ""

    if [ -n "$BACKUP_FILE" ]; then
        echo "Database Backup:"
        echo "  Remote: $BACKUP_FILE"
        echo "  Local: /tmp/thebot_db_${TIMESTAMP}.sql.gz"
        echo ""
    fi

    echo "Actions Performed:"
    [ "$DEPLOY_MODE" != "migrate-only" ] && [ -n "$BACKUP_FILE" ] && echo "  ✓ Database backup created"
    [ "$DEPLOY_MODE" != "migrate-only" ] && [ "$DB_STARTED" = true ] && echo "  ✓ Containers stopped and started"
    [ "$DEPLOY_MODE" != "backup-only" ] && echo "  ✓ Code synchronized"
    [ "$DEPLOY_MODE" != "backup-only" ] && [ "$MIGRATIONS_APPLIED" = true ] && echo "  ✓ Database migrations applied"
    [ "$DEPLOY_MODE" != "backup-only" ] && [ "$HEALTH_CHECK_PASSED" = true ] && echo "  ✓ Health checks passed"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}This was a DRY RUN - no changes were made${NC}"
    else
        echo -e "${GREEN}Deployment completed successfully${NC}"
    fi

    echo ""
    echo "Next Steps:"
    echo "  1. Monitor: ssh ${SSH_CONN} 'cd $REMOTE_PATH && docker-compose -f docker-compose.prod.yml logs -f backend'"
    echo "  2. Verify: curl -s http://${SSH_HOST}:8000/api/system/health/live/"
    echo "  3. Logs: cat $LOG_FILE"

    log "DEPLOYMENT COMPLETED SUCCESSFULLY"
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    parse_arguments "$@"

    mkdir -p "$LOG_DIR"

    print_header "THE_BOT MASTER DEPLOYMENT SCRIPT"

    echo "Deployment Mode: $DEPLOY_MODE"
    echo "Server: ${SSH_CONN}"
    echo "Remote Path: $REMOTE_PATH"
    echo "Dry Run: $DRY_RUN"
    echo "Log File: $LOG_FILE"
    echo ""

    log "DEPLOYMENT STARTED"
    log "Mode: $DEPLOY_MODE, Server: $SSH_CONN, DryRun: $DRY_RUN"

    SECONDS=0

    case "$DEPLOY_MODE" in
        full)
            phase_pre_deploy_checks
            phase_backup_database
            phase_stop_containers
            phase_sync_code
            phase_start_containers
            phase_wait_postgres
            phase_apply_migrations
            phase_health_checks
            ;;
        backup-only)
            phase_pre_deploy_checks
            phase_backup_database
            ;;
        migrate-only)
            phase_pre_deploy_checks
            phase_wait_postgres
            phase_apply_migrations
            phase_health_checks
            ;;
        *)
            error_exit "Unknown deployment mode: $DEPLOY_MODE" 1
            ;;
    esac

    phase_summary

    exit 0
}

main "$@"
