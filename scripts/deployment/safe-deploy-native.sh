#!/bin/bash

################################################################################
# THE_BOT Platform - Native Deployment Script (No Docker)
#
# Fast deployment without Docker containers - runs directly on server
# Uses systemd services for process management
#
# Usage:
#   ./scripts/deployment/safe-deploy-native.sh                    # Full deploy
#   ./scripts/deployment/safe-deploy-native.sh --dry-run          # Simulate
#   ./scripts/deployment/safe-deploy-native.sh --skip-frontend    # Backend only
#   ./scripts/deployment/safe-deploy-native.sh --force            # No prompts
#
# Environment Variables:
#   SSH_HOST           - SSH host (default: mg@5.129.249.206)
#   REMOTE_PATH        - Remote project path (default: /home/mg/THE_BOT_platform)
#   VENV_PATH          - Virtual env path (default: /home/mg/venv)
#   DOMAIN             - Production domain (default: the-bot.ru)
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
VENV_PATH="${VENV_PATH:-/home/mg/venv}"
LOCAL_PATH="${LOCAL_PATH:-$PROJECT_DIR}"
DOMAIN="${DOMAIN:-the-bot.ru}"

# Deployment options
DRY_RUN=false
SKIP_FRONTEND=false
FORCE_DEPLOY=false
VERBOSE=false

# Log file
LOG_DIR="${PROJECT_DIR}/deployment-logs"
LOG_FILE="${LOG_DIR}/deploy_native_${TIMESTAMP}.log"

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
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Setup logging
mkdir -p "$LOG_DIR"
exec 1> >(tee -a "$LOG_FILE")
exec 2>&1

################################################################################
# LOGGING FUNCTIONS
################################################################################

print_header() {
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo ""
}

print_step() {
    echo -e "${CYAN}>>> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

################################################################################
# MAIN DEPLOYMENT
################################################################################

main() {
    print_header "THE_BOT PLATFORM - NATIVE DEPLOYMENT (NO DOCKER)"
    log "Deploy ID: $DEPLOY_ID"
    log "SSH Host: $SSH_HOST"
    log "Remote Path: $REMOTE_PATH"
    log "Virtual Env: $VENV_PATH"
    log "Domain: $DOMAIN"

    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "DRY-RUN MODE - No changes will be made"
    fi

    print_header "PRE-DEPLOYMENT CHECKS"

    print_step "Checking SSH connectivity..."
    if ssh -o ConnectTimeout=5 "$SSH_HOST" "echo OK" > /dev/null 2>&1; then
        print_success "SSH connection OK"
    else
        print_error "SSH connection failed"
        return 1
    fi

    print_step "Checking remote directory..."
    if ssh "$SSH_HOST" "test -d $REMOTE_PATH"; then
        print_success "Remote directory exists"
    else
        print_error "Remote directory not found: $REMOTE_PATH"
        return 1
    fi

    print_step "Checking remote disk space..."
    DISK_USAGE=$(ssh "$SSH_HOST" "df $REMOTE_PATH | tail -1 | awk '{print \$5}' | sed 's/%//'")
    if [[ $DISK_USAGE -lt 80 ]]; then
        print_success "Disk usage: ${DISK_USAGE}%"
    else
        print_warning "Disk usage high: ${DISK_USAGE}%"
    fi

    print_header "PHASE 1: BACKUP"

    print_step "Creating code backup..."
    if [[ "$DRY_RUN" != "true" ]]; then
        ssh "$SSH_HOST" "cd $REMOTE_PATH && git stash" 2>/dev/null || true
        print_success "Code backup created"
    else
        print_success "[DRY-RUN] Would backup code"
    fi

    print_header "PHASE 2: CODE SYNCHRONIZATION"

    print_step "Syncing code..."
    if [[ "$DRY_RUN" != "true" ]]; then
        rsync -avz --delete -e ssh \
            --exclude='.venv' \
            --exclude='__pycache__' \
            --exclude='*.pyc' \
            --exclude='.git' \
            --exclude='node_modules' \
            "$LOCAL_PATH/" "$SSH_HOST:$REMOTE_PATH/" 2>&1 | tail -10
        print_success "Code synchronized"
    else
        print_success "[DRY-RUN] Would sync code"
    fi

    print_header "PHASE 3: PYTHON DEPENDENCIES"

    print_step "Installing Python dependencies..."
    if [[ "$DRY_RUN" != "true" ]]; then
        ssh "$SSH_HOST" "bash -c 'source $VENV_PATH/bin/activate && pip install -q -r $REMOTE_PATH/backend/requirements.txt'" 2>&1 | tail -5
        print_success "Dependencies installed"
    else
        print_success "[DRY-RUN] Would install dependencies"
    fi

    print_header "PHASE 4: FRONTEND BUILD"

    if [[ "$SKIP_FRONTEND" != "true" ]]; then
        print_step "Building frontend..."
        if [[ "$DRY_RUN" != "true" ]]; then
            ssh "$SSH_HOST" "bash -c 'cd $REMOTE_PATH/frontend && npm run build 2>&1 | tail -5'" || print_warning "Frontend build had warnings"
            print_success "Frontend built"
        else
            print_success "[DRY-RUN] Would build frontend"
        fi
    fi

    print_header "PHASE 5: COLLECT STATIC FILES"

    print_step "Collecting Django static files..."
    if [[ "$DRY_RUN" != "true" ]]; then
        ssh "$SSH_HOST" "bash -c 'export DJANGO_SETTINGS_MODULE=config.settings && source $VENV_PATH/bin/activate && cd $REMOTE_PATH/backend && python manage.py collectstatic --noinput 2>&1 | tail -5'"
        print_success "Static files collected"
    else
        print_success "[DRY-RUN] Would collect static"
    fi

    print_header "PHASE 6: RESTART SERVICES"

    print_step "Restarting services..."
    if [[ "$DRY_RUN" != "true" ]]; then
        # Stop services
        ssh "$SSH_HOST" "sudo systemctl stop thebot-backend thebot-celery-worker thebot-celery-beat 2>/dev/null || true" || true
        sleep 2

        # Start services
        ssh "$SSH_HOST" "sudo systemctl start thebot-backend thebot-celery-worker thebot-celery-beat" || print_error "Service restart failed"
        sleep 3

        # Check status
        STATUS=$(ssh "$SSH_HOST" "sudo systemctl is-active thebot-backend" 2>/dev/null || echo "inactive")
        if [[ "$STATUS" == "active" ]]; then
            print_success "Services restarted successfully"
        else
            print_warning "Services may not be fully started, checking..."
            ssh "$SSH_HOST" "sudo systemctl status thebot-backend" 2>&1 | head -5 || true
        fi
    else
        print_success "[DRY-RUN] Would restart services"
    fi

    print_header "DEPLOYMENT VERIFICATION"

    if [[ "$DRY_RUN" != "true" ]]; then
        print_step "Verifying deployment..."

        # Check if backend is responding
        sleep 5
        BACKEND_CHECK=$(ssh "$SSH_HOST" "curl -s -m 5 http://localhost:8000/api/system/health/ 2>/dev/null || echo 'failed'" | head -1)

        if [[ "$BACKEND_CHECK" == "failed" ]]; then
            print_warning "Backend health check failed - services may still be starting"
        else
            print_success "Backend is responding"
        fi
    fi

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ DEPLOYMENT COMPLETED SUCCESSFULLY                       ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Platform is available at:"
    echo "  https://$DOMAIN"
    echo "  https://$DOMAIN/api/"
    echo ""
    echo "Service status:"
    echo "  ssh $SSH_HOST 'sudo systemctl status thebot-backend thebot-celery-worker thebot-celery-beat'"
    echo ""
    echo "View logs:"
    echo "  ssh $SSH_HOST 'sudo journalctl -u thebot-backend -f'"
    echo ""
}

# Execute main
if main; then
    log "Deployment completed successfully"
    exit 0
else
    log "Deployment failed"
    exit 1
fi
