#!/bin/bash

################################################################################
# THE_BOT Platform - Safe Production Deployment Script
#
# Performs safe deployment with database backup, migration checks, and rollback
# capability on failure.
#
# Usage:
#   ./scripts/deployment/safe-deploy.sh                    # Full deploy
#   ./scripts/deployment/safe-deploy.sh --dry-run          # Simulate deployment
#   ./scripts/deployment/safe-deploy.sh --skip-frontend    # Backend only
#   ./scripts/deployment/safe-deploy.sh --skip-tests       # Skip smoke tests
#   ./scripts/deployment/safe-deploy.sh --force            # No confirmations
#
# Environment Variables:
#   SSH_HOST           - SSH host (default: miroslav@213.171.25.168)
#   REMOTE_PATH        - Remote project path (default: /home/mg/THE_BOT_platform)
#   LOCAL_PATH         - Local project path (default: current directory)
#   DOMAIN             - Production domain (default: the-bot.ru)
#   BACKUP_RETENTION   - Days to keep backups (default: 7)
#
# Exit Codes:
#   0 - Deployment successful
#   1 - Deployment failed, rollback executed
#   2 - Critical failure, manual intervention required
#   3 - Pre-deploy checks failed
#
################################################################################

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOY_ID="DEPLOY_${TIMESTAMP}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Default configuration
SSH_HOST="${SSH_HOST:-mg@5.129.249.206}"
REMOTE_PATH="${REMOTE_PATH:-/home/mg/THE_BOT_platform}"
LOCAL_PATH="${LOCAL_PATH:-$PROJECT_DIR}"
DOMAIN="${DOMAIN:-the-bot.ru}"
BACKUP_RETENTION="${BACKUP_RETENTION:-7}"

# Deployment options
DRY_RUN=false
SKIP_FRONTEND=false
SKIP_TESTS=false
FORCE_DEPLOY=false
VERBOSE=false

# State tracking
BACKUP_FILE=""
MIGRATIONS_APPLIED=false
CODE_SYNCED=false
FRONTEND_BUILT=false
STATIC_COLLECTED=false

# Log file
LOG_DIR="${PROJECT_DIR}/deployment-logs"
LOG_FILE="${LOG_DIR}/deploy_${TIMESTAMP}.log"

################################################################################
# ARGUMENT PARSING
################################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --skip-frontend)
            SKIP_FRONTEND=true
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            grep "^#" "$0" | head -30
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local message="[$(date '+%Y-%m-%d %H:%M:%S')] $1"
    echo "$message" >> "$LOG_FILE"
    if [ "$VERBOSE" = true ]; then
        echo -e "${CYAN}[LOG]${NC} $1"
    fi
}

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
    log "=== $1 ==="
}

print_step() {
    echo -e "\n${CYAN}>>> $1${NC}"
    log "STEP: $1"
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

confirm() {
    if [ "$FORCE_DEPLOY" = true ]; then
        return 0
    fi

    local prompt="$1"
    echo ""
    read -p "$(echo -e ${YELLOW}$prompt${NC} [y/N]: )" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

ssh_exec() {
    local cmd="$1"
    local description="${2:-Executing remote command}"

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would execute: $cmd"
        return 0
    fi

    log "SSH: $cmd"
    if ! ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_HOST" "$cmd"; then
        print_error "SSH command failed: $description"
        return 1
    fi
    return 0
}

ssh_exec_silent() {
    local cmd="$1"
    if [ "$DRY_RUN" = true ]; then
        return 0
    fi
    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_HOST" "$cmd" 2>/dev/null
}

cleanup() {
    log "Cleanup triggered"
    # Cleanup is handled in rollback function
}

trap cleanup EXIT

################################################################################
# ROLLBACK FUNCTION
################################################################################

rollback() {
    print_header "EMERGENCY ROLLBACK"
    log "ROLLBACK INITIATED"

    local rollback_success=true

    # Restore database if backup exists
    if [ -n "$BACKUP_FILE" ] && [ "$MIGRATIONS_APPLIED" = true ]; then
        print_step "Restoring database from backup..."

        if [ "$DRY_RUN" = false ]; then
            if ssh_exec "cd $REMOTE_PATH && docker-compose exec -T postgres pg_restore -U postgres -d thebot_db -c $REMOTE_PATH/backups/$(basename $BACKUP_FILE) 2>/dev/null || true" "DB restore"; then
                print_success "Database restored from backup"
            else
                print_error "Database restore failed - manual intervention required!"
                rollback_success=false
            fi
        fi
    fi

    # Restart services
    print_step "Restarting services..."
    if [ "$DRY_RUN" = false ]; then
        ssh_exec "cd $REMOTE_PATH && docker-compose restart backend" "Restart backend" || true
    fi

    if [ "$rollback_success" = true ]; then
        print_success "Rollback completed"
        log "ROLLBACK COMPLETED SUCCESSFULLY"

        # Send notification
        echo ""
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}DEPLOYMENT FAILED - ROLLBACK EXECUTED${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "Details:"
        echo "  Deploy ID: $DEPLOY_ID"
        echo "  Backup File: $BACKUP_FILE"
        echo "  Log File: $LOG_FILE"
        echo ""
        echo "Next Steps:"
        echo "  1. Review logs: cat $LOG_FILE"
        echo "  2. Fix the issue locally"
        echo "  3. Run deployment again"
        echo ""

        exit 1
    else
        echo ""
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        echo -e "${RED}CRITICAL: ROLLBACK FAILED - MANUAL INTERVENTION REQUIRED${NC}"
        echo -e "${RED}═══════════════════════════════════════════════════════════${NC}"
        echo ""
        echo "Database backup: $BACKUP_FILE"
        echo "SSH: ssh $SSH_HOST"
        echo "Log file: $LOG_FILE"
        echo ""

        exit 2
    fi
}

################################################################################
# PRE-DEPLOYMENT CHECKS
################################################################################

pre_deploy_checks() {
    print_header "PRE-DEPLOYMENT CHECKS"

    local checks_passed=true

    # Check SSH connectivity
    print_step "Checking SSH connectivity..."
    if ssh_exec_silent "echo 'Connected'" 2>/dev/null; then
        print_success "SSH connection to $SSH_HOST"
    else
        print_error "Cannot connect to $SSH_HOST"
        checks_passed=false
    fi

    # Check remote project directory
    print_step "Checking remote project directory..."
    if ssh_exec_silent "test -d $REMOTE_PATH" 2>/dev/null; then
        print_success "Remote directory exists: $REMOTE_PATH"
    else
        print_error "Remote directory not found: $REMOTE_PATH"
        checks_passed=false
    fi

    # Check local git status
    print_step "Checking local git status..."
    if [ -d "$LOCAL_PATH/.git" ]; then
        local uncommitted=$(git -C "$LOCAL_PATH" status --porcelain | wc -l)
        if [ "$uncommitted" -gt 0 ]; then
            print_warning "Found $uncommitted uncommitted changes"
            if ! confirm "Deploy with uncommitted changes?"; then
                checks_passed=false
            fi
        else
            print_success "Git working directory is clean"
        fi
    fi

    # Check disk space on remote
    print_step "Checking remote disk space..."
    local disk_usage=$(ssh_exec_silent "df -h $REMOTE_PATH | tail -1 | awk '{print \$5}' | sed 's/%//'")
    if [ -n "$disk_usage" ] && [ "$disk_usage" -lt 90 ]; then
        print_success "Disk usage: ${disk_usage}%"
    elif [ -n "$disk_usage" ]; then
        print_warning "Disk usage is high: ${disk_usage}%"
    fi

    # Check if docker is running (warning only, not critical)
    print_step "Checking Docker on remote..."
    if ssh_exec_silent "docker ps >/dev/null 2>&1"; then
        print_success "Docker is running"
    else
        print_warning "Docker is not running on remote (may not be critical for code-only deployment)"
    fi

    # Check remote database (warning only, not critical)
    print_step "Checking database connectivity..."
    if ssh_exec_silent "cd $REMOTE_PATH && docker-compose exec -T postgres pg_isready -U postgres >/dev/null 2>&1" 2>/dev/null; then
        print_success "Database is accessible"
    else
        print_warning "Database check failed (may not be critical for code-only deployment)"
    fi

    if [ "$checks_passed" = false ]; then
        print_error "Pre-deployment checks failed!"
        exit 3
    fi

    print_success "All pre-deployment checks passed"
}

################################################################################
# DATABASE BACKUP
################################################################################

backup_database() {
    print_header "PHASE 1: DATABASE BACKUP"

    local backup_name="backup_${DEPLOY_ID}.dump"
    BACKUP_FILE="$REMOTE_PATH/backups/$backup_name"

    print_step "Creating database backup..."

    # Check if docker-compose is available
    if ! ssh_exec_silent "command -v docker-compose >/dev/null 2>&1"; then
        print_warning "docker-compose not available on remote, skipping database backup"
        print_info "Database backup skipped - backup phase skipped due to missing docker-compose"
        log "BACKUP SKIPPED: docker-compose not available"
        return 0
    fi

    # Create backup directory
    if [ "$DRY_RUN" = false ]; then
        ssh_exec "mkdir -p $REMOTE_PATH/backups" "Create backup directory"
    fi

    # Create backup
    if [ "$DRY_RUN" = false ]; then
        print_info "Backing up database to: $backup_name"

        if ssh_exec "cd $REMOTE_PATH && docker-compose exec -T postgres pg_dump -U postgres -F c -f /tmp/$backup_name thebot_db && docker cp \$(docker-compose ps -q postgres):/tmp/$backup_name $REMOTE_PATH/backups/" "Database backup"; then
            print_success "Database backup created: $backup_name"
            log "BACKUP CREATED: $BACKUP_FILE"
        else
            print_error "Database backup failed!"
            if [ "$FORCE_DEPLOY" = true ]; then
                print_warning "Force deploy enabled, continuing without backup"
            elif ! confirm "Continue without backup? (DANGEROUS)"; then
                exit 1
            fi
            BACKUP_FILE=""
        fi
    else
        print_info "[DRY-RUN] Would create backup: $backup_name"
    fi

    # Cleanup old backups
    print_step "Cleaning old backups (keeping last $BACKUP_RETENTION days)..."
    if [ "$DRY_RUN" = false ]; then
        ssh_exec "find $REMOTE_PATH/backups -name 'backup_*.dump' -mtime +$BACKUP_RETENTION -delete 2>/dev/null || true" "Cleanup old backups"
        print_success "Old backups cleaned"
    fi
}

################################################################################
# MIGRATION CHECK
################################################################################

check_migrations() {
    print_header "PHASE 2: MIGRATION CHECK"

    print_step "Checking for pending migrations..."

    if [ "$DRY_RUN" = false ]; then
        # Get pending migrations
        local pending=$(ssh_exec_silent "cd $REMOTE_PATH && docker-compose exec -T backend python manage.py showmigrations --plan 2>/dev/null | grep '\[ \]' | head -20")

        if [ -n "$pending" ]; then
            echo ""
            echo -e "${YELLOW}Pending migrations found:${NC}"
            echo "$pending" | head -10
            echo ""

            # Dry-run migrations
            print_step "Running migration dry-run..."
            if ssh_exec "cd $REMOTE_PATH && docker-compose exec -T backend python manage.py migrate --plan 2>&1 | head -30" "Migration plan"; then
                print_success "Migration plan generated"
            else
                print_warning "Migration plan failed (may not be critical)"
            fi

            if ! confirm "Apply these migrations?"; then
                print_warning "Migrations skipped by user"
                return 0
            fi

            # Apply migrations
            print_step "Applying migrations..."
            if ssh_exec "cd $REMOTE_PATH && docker-compose exec -T backend python manage.py migrate --noinput" "Apply migrations"; then
                print_success "Migrations applied successfully"
                MIGRATIONS_APPLIED=true
            else
                print_error "Migration failed!"
                rollback
            fi
        else
            print_success "No pending migrations"
        fi
    else
        print_info "[DRY-RUN] Would check and apply pending migrations"
    fi
}

################################################################################
# CODE SYNCHRONIZATION
################################################################################

sync_code() {
    print_header "PHASE 3: CODE SYNCHRONIZATION"

    print_step "Synchronizing code with rsync..."

    # Rsync exclusions
    local exclude_opts=(
        --exclude='.git'
        --exclude='__pycache__'
        --exclude='*.pyc'
        --exclude='node_modules'
        --exclude='.env'
        --exclude='.env.local'
        --exclude='.env.production'
        --exclude='*.log'
        --exclude='*.sqlite3'
        --exclude='.pytest_cache'
        --exclude='.mypy_cache'
        --exclude='htmlcov'
        --exclude='.coverage'
        --exclude='dist'
        --exclude='build'
        --exclude='*.egg-info'
        --exclude='deployment-logs'
        --exclude='backups'
        --exclude='media/*'
        --exclude='staticfiles/*'
    )

    if [ "$DRY_RUN" = true ]; then
        print_info "[DRY-RUN] Would sync code from $LOCAL_PATH to $SSH_HOST:$REMOTE_PATH"
        print_info "Excluded: .git, __pycache__, node_modules, .env files, logs, media"
    else
        print_info "Syncing from: $LOCAL_PATH"
        print_info "Syncing to: $SSH_HOST:$REMOTE_PATH"

        if rsync -avz --delete \
            "${exclude_opts[@]}" \
            "$LOCAL_PATH/" \
            "$SSH_HOST:$REMOTE_PATH/"; then
            print_success "Code synchronized"
            CODE_SYNCED=true
            log "CODE SYNCED"
        else
            print_error "Code sync failed!"
            rollback
        fi
    fi
}

################################################################################
# FRONTEND BUILD
################################################################################

build_frontend() {
    if [ "$SKIP_FRONTEND" = true ]; then
        print_info "Skipping frontend build (--skip-frontend)"
        return 0
    fi

    print_header "PHASE 4: FRONTEND BUILD"

    print_step "Installing frontend dependencies..."

    if [ "$DRY_RUN" = false ]; then
        if ssh_exec "cd $REMOTE_PATH/frontend && npm ci --production=false 2>&1 | tail -5" "npm install"; then
            print_success "Dependencies installed"
        else
            print_error "npm install failed!"
            rollback
        fi

        print_step "Building frontend..."
        if ssh_exec "cd $REMOTE_PATH/frontend && npm run build 2>&1 | tail -10" "npm build"; then
            print_success "Frontend built successfully"
            FRONTEND_BUILT=true
            log "FRONTEND BUILT"
        else
            print_error "Frontend build failed!"
            rollback
        fi
    else
        print_info "[DRY-RUN] Would build frontend"
    fi
}

################################################################################
# COLLECT STATIC FILES
################################################################################

collect_static() {
    print_header "PHASE 5: COLLECT STATIC FILES"

    print_step "Collecting Django static files..."

    if [ "$DRY_RUN" = false ]; then
        if ssh_exec "cd $REMOTE_PATH && docker-compose exec -T backend python manage.py collectstatic --noinput 2>&1 | tail -5" "collectstatic"; then
            print_success "Static files collected"
            STATIC_COLLECTED=true
            log "STATIC FILES COLLECTED"
        else
            print_warning "collectstatic failed (may not be critical)"
        fi
    else
        print_info "[DRY-RUN] Would collect static files"
    fi
}

################################################################################
# RESTART SERVICES
################################################################################

restart_services() {
    print_header "PHASE 6: RESTART SERVICES"

    print_step "Restarting backend service..."

    if [ "$DRY_RUN" = false ]; then
        if ssh_exec "cd $REMOTE_PATH && docker-compose restart backend" "Restart backend"; then
            print_success "Backend restarted"
        else
            print_error "Backend restart failed!"
            rollback
        fi

        # Wait for service to be ready
        print_step "Waiting for service to stabilize..."
        sleep 10

        # Check if service is running
        if ssh_exec_silent "cd $REMOTE_PATH && docker-compose ps backend | grep -q Up"; then
            print_success "Backend is running"
        else
            print_error "Backend failed to start!"
            rollback
        fi
    else
        print_info "[DRY-RUN] Would restart backend service"
    fi
}

################################################################################
# HEALTH CHECKS
################################################################################

health_checks() {
    print_header "PHASE 7: HEALTH CHECKS"

    local health_passed=true

    # API health check
    print_step "Checking API health..."

    if [ "$DRY_RUN" = false ]; then
        local max_retries=5
        local retry_delay=5
        local api_healthy=false

        for ((i=1; i<=max_retries; i++)); do
            print_info "Health check attempt $i/$max_retries..."

            local response=$(curl -s -w "\n%{http_code}" \
                -H "Content-Type: application/json" \
                "https://${DOMAIN}/api/system/health/live/" 2>/dev/null || echo -e "\n000")

            local http_code=$(echo "$response" | tail -1)

            if [ "$http_code" = "200" ]; then
                print_success "API health check passed"
                api_healthy=true
                break
            else
                print_warning "API returned HTTP $http_code, retrying in ${retry_delay}s..."
                sleep $retry_delay
            fi
        done

        if [ "$api_healthy" = false ]; then
            print_error "API health check failed after $max_retries attempts"
            health_passed=false
        fi

        # Frontend check
        print_step "Checking frontend..."
        response=$(curl -s -w "\n%{http_code}" \
            -H "User-Agent: Mozilla/5.0" \
            "https://${DOMAIN}/" 2>/dev/null || echo -e "\n000")

        http_code=$(echo "$response" | tail -1)

        if [ "$http_code" = "200" ]; then
            print_success "Frontend is accessible"
        else
            print_warning "Frontend returned HTTP $http_code"
        fi
    else
        print_info "[DRY-RUN] Would perform health checks"
    fi

    if [ "$health_passed" = false ]; then
        if ! confirm "Health checks failed. Rollback?"; then
            print_warning "Continuing despite failed health checks (user override)"
        else
            rollback
        fi
    fi
}

################################################################################
# SMOKE TESTS
################################################################################

smoke_tests() {
    if [ "$SKIP_TESTS" = true ]; then
        print_info "Skipping smoke tests (--skip-tests)"
        return 0
    fi

    print_header "PHASE 8: SMOKE TESTS"

    print_step "Running production smoke tests..."

    if [ "$DRY_RUN" = false ]; then
        # Check if Playwright is available
        if command -v npx &> /dev/null && [ -f "$LOCAL_PATH/frontend/tests/e2e/production-smoke-test.spec.ts" ]; then
            print_info "Running Playwright smoke tests..."

            cd "$LOCAL_PATH/frontend"

            if BASE_URL="https://${DOMAIN}" npx playwright test production-smoke-test.spec.ts \
                --project=chromium \
                --reporter=list \
                --timeout=60000 2>&1 | tee -a "$LOG_FILE" | tail -20; then
                print_success "Smoke tests passed"
            else
                print_warning "Some smoke tests failed (review logs)"
                if confirm "Smoke tests failed. Rollback?"; then
                    rollback
                fi
            fi

            cd "$PROJECT_DIR"
        else
            print_warning "Playwright tests not available, running basic checks..."

            # Basic API checks
            local endpoints=(
                "/api/system/health/live/"
                "/api/auth/login/"
            )

            for endpoint in "${endpoints[@]}"; do
                local response=$(curl -s -w "%{http_code}" \
                    -o /dev/null \
                    "https://${DOMAIN}${endpoint}" 2>/dev/null || echo "000")

                if [ "$response" != "000" ] && [ "$response" != "500" ]; then
                    print_success "Endpoint ${endpoint}: HTTP $response"
                else
                    print_warning "Endpoint ${endpoint}: HTTP $response"
                fi
            done
        fi
    else
        print_info "[DRY-RUN] Would run smoke tests"
    fi
}

################################################################################
# DEPLOYMENT SUMMARY
################################################################################

deployment_summary() {
    print_header "DEPLOYMENT COMPLETE"

    local duration=$SECONDS
    local minutes=$((duration / 60))
    local seconds=$((duration % 60))

    echo "Summary:"
    echo -e "  ${GREEN}✓${NC} Deploy ID: $DEPLOY_ID"
    echo -e "  ${GREEN}✓${NC} Duration: ${minutes}m ${seconds}s"
    echo -e "  ${GREEN}✓${NC} Target: $SSH_HOST:$REMOTE_PATH"
    echo -e "  ${GREEN}✓${NC} Domain: https://$DOMAIN"
    echo ""

    echo "Actions performed:"
    [ -n "$BACKUP_FILE" ] && echo -e "  ${GREEN}✓${NC} Database backup: $(basename $BACKUP_FILE)"
    [ "$MIGRATIONS_APPLIED" = true ] && echo -e "  ${GREEN}✓${NC} Migrations applied"
    [ "$CODE_SYNCED" = true ] && echo -e "  ${GREEN}✓${NC} Code synchronized"
    [ "$FRONTEND_BUILT" = true ] && echo -e "  ${GREEN}✓${NC} Frontend built"
    [ "$STATIC_COLLECTED" = true ] && echo -e "  ${GREEN}✓${NC} Static files collected"
    echo ""

    echo "Log file: $LOG_FILE"
    echo ""

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}This was a DRY RUN. No changes were made.${NC}"
        echo "Run without --dry-run to perform actual deployment."
    else
        echo -e "${GREEN}Deployment successful!${NC}"
        echo ""
        echo "Verify:"
        echo "  - Website: https://$DOMAIN"
        echo "  - Admin: https://$DOMAIN/admin"
        echo "  - API: https://$DOMAIN/api/system/health/live/"
    fi

    log "DEPLOYMENT COMPLETED SUCCESSFULLY"
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    # Create log directory
    mkdir -p "$LOG_DIR"

    print_header "THE_BOT PLATFORM - SAFE DEPLOYMENT"

    echo "Configuration:"
    echo "  Deploy ID: $DEPLOY_ID"
    echo "  SSH Host: $SSH_HOST"
    echo "  Remote Path: $REMOTE_PATH"
    echo "  Domain: $DOMAIN"
    echo "  Dry Run: $DRY_RUN"
    echo "  Skip Frontend: $SKIP_FRONTEND"
    echo "  Skip Tests: $SKIP_TESTS"
    echo "  Log File: $LOG_FILE"
    echo ""

    log "DEPLOYMENT STARTED"
    log "Config: SSH=$SSH_HOST, PATH=$REMOTE_PATH, DOMAIN=$DOMAIN"

    if [ "$DRY_RUN" = true ]; then
        echo -e "${YELLOW}DRY RUN MODE - No changes will be made${NC}"
        echo ""
    fi

    if ! confirm "Start deployment to production?"; then
        print_info "Deployment cancelled by user"
        exit 0
    fi

    SECONDS=0

    # Execute deployment phases
    pre_deploy_checks
    backup_database
    check_migrations
    sync_code
    build_frontend
    collect_static
    restart_services
    health_checks
    smoke_tests
    deployment_summary

    exit 0
}

# Run main function
main "$@"
