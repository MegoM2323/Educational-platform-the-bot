#!/bin/bash

################################################################################
# THE_BOT Platform - Production Deployment + User Setup Script
#
# Automates production deployment and user account creation
#
# Usage:
#   ./setup_production.sh                  # Interactive (with confirmations)
#   ./setup_production.sh --force          # Auto (skip confirmations)
#   ./setup_production.sh --dry-run        # Preview mode
#   ./setup_production.sh --skip-deploy    # User setup only
#   ./setup_production.sh --skip-users     # Deployment only
#
################################################################################

set -euo pipefail

# ===== CONFIG =====
REMOTE_USER="${REMOTE_USER:-mg}"
REMOTE_HOST="${REMOTE_HOST:-5.129.249.206}"
REMOTE_DIR="${REMOTE_DIR:-/home/mg/THE_BOT_platform}"
LOCAL_PATH="$(cd "$(dirname "$0")/.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOY_SCRIPT="${LOCAL_PATH}/scripts/deployment/rsync-deploy-native.sh"

# Systemd services
SERVICES=("thebot-daphne.service" "thebot-celery-worker.service" "thebot-celery-beat.service")

# Expected users configuration
EXPECTED_USER_COUNT=7

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options
DRY_RUN=false
FORCE=false
SKIP_DEPLOY=false
SKIP_USERS=false
VERBOSE=false

# Counters
STEP_COUNT=0
SUCCESS_COUNT=0
FAILED_STEPS=()
START_TIME=$(date +%s)

# ===== LOGGING FUNCTIONS =====
log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
    ((SUCCESS_COUNT++))
}

error() {
    echo -e "${RED}✗${NC} $1"
    FAILED_STEPS+=("$1")
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

separator() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

step() {
    local step_num=$1
    local description=$2
    ((STEP_COUNT++))
    echo ""
    log "[${step_num}] ${description}..."
}

confirm() {
    if [[ "$FORCE" == true ]]; then
        return 0
    fi

    local prompt="$1"
    local response
    read -p "$(echo -e ${BLUE}${prompt}${NC}) (y/n) " -n 1 -r response
    echo
    [[ "$response" =~ ^[Yy]$ ]]
}

# ===== VALIDATION FUNCTIONS =====
validate_git_status() {
    log "Validating git repository..."

    cd "$LOCAL_PATH"

    # Check for uncommitted changes (excluding __pycache__ and audit.log)
    local status=$(git status --porcelain | grep -v '__pycache__\|audit\.log' || true)
    if [[ -n "$status" ]]; then
        error "Git has uncommitted changes:"
        echo "$status" | sed 's/^/  /'
        return 1
    fi

    # Check if on main branch
    local current_branch=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$current_branch" != "main" ]]; then
        error "Not on main branch (current: $current_branch)"
        return 1
    fi

    # Show latest commit
    local latest_commit=$(git log -1 --oneline)
    success "Git status OK (branch: main)"
    info "Latest commit: $latest_commit"

    return 0
}

validate_ssh_access() {
    log "Testing SSH access to production server..."

    if ! timeout 5 ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "${REMOTE_USER}@${REMOTE_HOST}" "echo OK" &>/dev/null; then
        error "Cannot connect to ${REMOTE_USER}@${REMOTE_HOST}"
        return 1
    fi

    success "SSH access OK"
    return 0
}

validate_deploy_script() {
    log "Checking deployment script..."

    if [[ ! -x "$DEPLOY_SCRIPT" ]]; then
        error "Deploy script not found or not executable: $DEPLOY_SCRIPT"
        return 1
    fi

    success "Deploy script found"
    return 0
}

validate_production_env() {
    log "Checking production environment..."

    local cmd="cd ${REMOTE_DIR} && test -f .env && echo OK || echo MISSING"
    local result=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "$cmd" 2>/dev/null || echo "ERROR")

    if [[ "$result" != "OK" ]]; then
        error "Production environment not properly configured"
        return 1
    fi

    success "Production environment OK"
    return 0
}

# ===== GIT OPERATIONS =====
push_code() {
    step "2" "Pushing code to origin/main"

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would push code to origin/main"
        return 0
    fi

    cd "$LOCAL_PATH"

    if ! git push origin main; then
        error "Failed to push code"
        return 1
    fi

    success "Code pushed successfully"
    return 0
}

# ===== DEPLOYMENT =====
run_deployment() {
    step "3" "Running deployment script"

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would run: $DEPLOY_SCRIPT --force"
        return 0
    fi

    if [[ "$VERBOSE" == true ]]; then
        if ! "$DEPLOY_SCRIPT" --force --verbose; then
            error "Deployment failed"
            return 1
        fi
    else
        if ! "$DEPLOY_SCRIPT" --force &>/dev/null; then
            error "Deployment failed"
            return 1
        fi
    fi

    success "Deployment completed"
    return 0
}

# ===== USER SETUP =====
create_production_users() {
    step "4" "Creating production users"

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would create 7 production users"
        return 0
    fi

    local cmd="cd ${REMOTE_DIR}/backend && python manage.py setup_production_users --force"
    local result=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "$cmd" 2>&1)

    if [[ $? -ne 0 ]]; then
        error "Failed to create production users"
        echo "$result" | sed 's/^/  /'
        return 1
    fi

    success "Production users created"
    info "Output: $(echo "$result" | tail -1)"

    return 0
}

verify_user_count() {
    log "Verifying user count..."

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would verify 7 users exist"
        return 0
    fi

    local cmd="cd ${REMOTE_DIR}/backend && python manage.py shell -c \"from accounts.models import User; print(User.objects.count())\""
    local count=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "$cmd" 2>&1 | grep -oP '\d+' | tail -1)

    if [[ -z "$count" ]]; then
        error "Could not verify user count"
        return 1
    fi

    if [[ $count -eq $EXPECTED_USER_COUNT ]]; then
        success "User count verified: $count users"
        return 0
    else
        warning "Expected $EXPECTED_USER_COUNT users, found $count"
        return 1
    fi
}

# ===== SERVICE MANAGEMENT =====
restart_services() {
    step "5" "Restarting systemd services"

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would restart: ${SERVICES[@]}"
        return 0
    fi

    local service_list=$(IFS=' '; echo "${SERVICES[*]}")
    local cmd="sudo systemctl restart $service_list"

    if ! ssh "${REMOTE_USER}@${REMOTE_HOST}" "$cmd"; then
        error "Failed to restart services"
        return 1
    fi

    success "Services restarted"
    return 0
}

wait_for_services() {
    log "Waiting for services to stabilize..."

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would wait 5 seconds for services"
        return 0
    fi

    sleep 5

    local all_healthy=true
    for service in "${SERVICES[@]}"; do
        local cmd="systemctl is-active $service"
        local status=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "$cmd" 2>&1)

        if [[ "$status" == "active" ]]; then
            success "Service healthy: $service"
        else
            error "Service unhealthy: $service ($status)"
            all_healthy=false
        fi
    done

    if [[ "$all_healthy" == true ]]; then
        return 0
    else
        return 1
    fi
}

# ===== VERIFICATION =====
verify_api_health() {
    step "6" "Verifying API health"

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would check https://the-bot.ru/api/health/"
        return 0
    fi

    log "Checking API health endpoint..."

    local response=$(curl -s -o /dev/null -w "%{http_code}" https://the-bot.ru/api/health/ 2>/dev/null || echo "000")

    if [[ "$response" == "200" ]]; then
        success "API health check passed (HTTP 200)"
        return 0
    else
        warning "API health check returned HTTP $response (expected 200)"
        return 1
    fi
}

verify_login() {
    log "Verifying login functionality..."

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would test login for alexander@master.com"
        return 0
    fi

    local response=$(curl -s -X POST https://the-bot.ru/api/auth/login/ \
        -H "Content-Type: application/json" \
        -d '{"email":"alexander@master.com","password":"bangbang"}' 2>/dev/null || echo "")

    if echo "$response" | grep -q '"token"'; then
        success "Login test passed for alexander@master.com"
        return 0
    else
        warning "Login test failed or returned unexpected response"
        return 1
    fi
}

# ===== REPORTING =====
report_service_status() {
    echo ""
    separator
    info "Service Status Report:"
    separator

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would check service status"
        for service in "${SERVICES[@]}"; do
            echo "  ${CYAN}□${NC} $service"
        done
        return 0
    fi

    for service in "${SERVICES[@]}"; do
        local cmd="systemctl is-active $service"
        local status=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "$cmd" 2>&1)

        if [[ "$status" == "active" ]]; then
            echo "  ${GREEN}✓${NC} $service (active)"
        else
            echo "  ${RED}✗${NC} $service ($status)"
        fi
    done
}

report_users() {
    echo ""
    separator
    info "Production Users:"
    separator

    if [[ "$DRY_RUN" == true ]]; then
        info "DRY-RUN: Would list production users"
        echo "  alexander@master.com (admin)"
        echo "  mikhail@master.com (admin)"
        echo "  student@test.com (student)"
        echo "  [...4 more users...]"
        return 0
    fi

    local cmd="cd ${REMOTE_DIR}/backend && python manage.py shell -c \"from accounts.models import User; [print(f'{u.email} ({u.role})') for u in User.objects.all()[:10]]\""
    local users=$(ssh "${REMOTE_USER}@${REMOTE_HOST}" "$cmd" 2>&1)

    if [[ -n "$users" ]]; then
        echo "$users" | sed 's/^/  /'
    else
        warning "Could not retrieve user list"
    fi
}

report_summary() {
    echo ""
    separator
    log "DEPLOYMENT SUMMARY"
    separator

    local end_time=$(date +%s)
    local duration=$((end_time - START_TIME))
    local duration_min=$((duration / 60))
    local duration_sec=$((duration % 60))

    echo ""
    if [[ ${#FAILED_STEPS[@]} -eq 0 ]]; then
        echo -e "${GREEN}✓ ALL STEPS COMPLETED SUCCESSFULLY${NC}"
    else
        echo -e "${RED}✗ SOME STEPS FAILED:${NC}"
        for failed in "${FAILED_STEPS[@]}"; do
            echo "  - $failed"
        done
    fi

    echo ""
    echo "Successful steps: $SUCCESS_COUNT/$STEP_COUNT"
    echo "Total duration: ${duration_min}m ${duration_sec}s"

    if [[ "$DRY_RUN" == true ]]; then
        echo ""
        warning "This was a DRY-RUN. No changes were made."
    fi

    separator
}

# ===== MAIN FLOW =====
show_help() {
    cat << EOF
THE_BOT Platform - Production Deployment + User Setup Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --force               Skip confirmation prompts
    --dry-run             Preview mode (no changes)
    --skip-deploy         User setup only (skip code deployment)
    --skip-users          Code deployment only (skip user creation)
    --verbose             Detailed logging
    --help                Show this help message

EXAMPLES:
    $0                                    # Interactive (with prompts)
    $0 --force                            # Auto (no prompts)
    $0 --dry-run                          # Preview
    $0 --skip-deploy                      # User setup only
    $0 --skip-users --force               # Deployment only

FLOW:
    1. Git validation (check clean status, main branch)
    2. Code push to origin/main
    3. Run rsync-deploy-native.sh (code deployment)
    4. Create production users
    5. Restart systemd services
    6. Verify API health and login

REQUIRED:
    - SSH access to ${REMOTE_USER}@${REMOTE_HOST}
    - Deployment script at: ${DEPLOY_SCRIPT}
    - .env file on production server

EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --force) FORCE=true; shift ;;
        --dry-run) DRY_RUN=true; shift ;;
        --skip-deploy) SKIP_DEPLOY=true; shift ;;
        --skip-users) SKIP_USERS=true; shift ;;
        --verbose) VERBOSE=true; shift ;;
        --help) show_help ;;
        *) echo "Unknown option: $1. Use --help for usage."; exit 1 ;;
    esac
done

# ===== MAIN EXECUTION =====
main() {
    separator
    log "THE_BOT PRODUCTION DEPLOYMENT + USER SETUP"
    separator

    if [[ "$DRY_RUN" == true ]]; then
        warning "DRY-RUN MODE: No changes will be made"
        echo ""
    fi

    if [[ "$SKIP_DEPLOY" == true && "$SKIP_USERS" == true ]]; then
        error "Cannot skip both deployment and user setup"
        exit 1
    fi

    # Phase 1: Validation
    echo ""
    log "PHASE 1: PRE-FLIGHT CHECKS"
    separator

    if ! validate_git_status; then
        error "Git validation failed"
        exit 1
    fi

    if ! validate_ssh_access; then
        error "SSH validation failed"
        exit 1
    fi

    if [[ "$SKIP_DEPLOY" == false ]]; then
        if ! validate_deploy_script; then
            error "Deployment script validation failed"
            exit 1
        fi

        if ! validate_production_env; then
            error "Production environment validation failed"
            exit 1
        fi
    fi

    success "All pre-flight checks passed"

    # Phase 2: User confirmation
    if [[ "$FORCE" == false && "$DRY_RUN" == false ]]; then
        echo ""
        warning "This will deploy code and create production users"
        if ! confirm "Continue with deployment?"; then
            log "Deployment cancelled by user"
            exit 0
        fi
    fi

    # Phase 3: Code deployment
    if [[ "$SKIP_DEPLOY" == false ]]; then
        echo ""
        log "PHASE 2: CODE DEPLOYMENT"
        separator

        if ! push_code; then
            error "Code push failed"
            exit 1
        fi

        if ! run_deployment; then
            error "Deployment failed"
            exit 1
        fi
    fi

    # Phase 4: User setup
    if [[ "$SKIP_USERS" == false ]]; then
        echo ""
        log "PHASE 3: USER SETUP"
        separator

        if ! create_production_users; then
            error "User creation failed"
            exit 1
        fi

        if ! verify_user_count; then
            warning "User count verification failed"
        fi
    fi

    # Phase 5: Service management
    echo ""
    log "PHASE 4: SERVICE MANAGEMENT"
    separator

    if ! restart_services; then
        error "Service restart failed"
        exit 1
    fi

    if ! wait_for_services; then
        warning "Some services may not be healthy"
    fi

    # Phase 6: Verification
    echo ""
    log "PHASE 5: VERIFICATION"
    separator

    if ! verify_api_health; then
        warning "API health check failed"
    fi

    if ! verify_login; then
        warning "Login verification failed"
    fi

    # Phase 7: Reporting
    echo ""
    log "PHASE 6: REPORTING"
    separator

    report_service_status
    report_users
    report_summary

    exit 0
}

# Run main function
main
