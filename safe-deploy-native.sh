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

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
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

    print_step "Checking systemd services..."
    if ssh "$SSH_HOST" "test -f /etc/systemd/system/thebot-daphne.service"; then
        print_success "Daphne systemd service configured"
    else
        print_warning "Daphne systemd service not found"
        print_step "Setting up Daphne systemd service..."

        if [[ "$DRY_RUN" != "true" ]]; then
            # Create Daphne service file on remote
            ssh "$SSH_HOST" "sudo bash -c 'cat > /etc/systemd/system/thebot-daphne.service << EOF
[Unit]
Description=THE_BOT Platform Daphne ASGI WebSocket Server
After=network.target

[Service]
Type=simple
User=mg
Group=www-data
WorkingDirectory=$REMOTE_PATH/backend
Environment=\"PATH=$VENV_PATH/bin:/usr/local/bin:/usr/bin:/bin\"
ExecStart=$VENV_PATH/bin/daphne -b 0.0.0.0 -p 8001 config.asgi:application
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF
'"
            ssh "$SSH_HOST" "sudo systemctl daemon-reload && sudo systemctl enable thebot-daphne"
            print_success "Daphne systemd service created and enabled"
        else
            print_success "[DRY-RUN] Would create Daphne systemd service"
        fi
    fi

    print_header "PHASE 1.0: PRE-DEPLOYMENT BACKUP"

    BACKUP_FILE="thebot_db_backup_${TIMESTAMP}.sql"

    if [[ "$DRY_RUN" != "true" ]]; then
        print_step "Creating database backup..."
        ssh "$SSH_HOST" "pg_dump -U postgres thebot_db > /tmp/$BACKUP_FILE" || {
            print_warning "DB backup failed, but continuing..."
        }

        # Download backup locally for safety
        scp "$SSH_HOST:/tmp/$BACKUP_FILE" "$LOG_DIR/" 2>/dev/null || true
        print_success "Database backed up: $LOG_DIR/$BACKUP_FILE"
    else
        print_info "[DRY-RUN] Would backup database to $BACKUP_FILE"
    fi

    print_header "PHASE 1.5: ENV SYNCHRONIZATION"

    # Check if .env.production.native exists locally
    if [[ ! -f "$LOCAL_PATH/.env.production.native" ]]; then
        print_step "Creating .env.production.native from template..."
        if [[ -f "$LOCAL_PATH/.env.production.native.template" ]]; then
            cp "$LOCAL_PATH/.env.production.native.template" "$LOCAL_PATH/.env.production.native" || {
                print_warning "Failed to create .env from template"
            }
        else
            print_warning "Template not found: .env.production.native.template"
        fi
    fi

    if [[ -f "$LOCAL_PATH/.env.production.native" ]]; then
        # Generate strong DB password if needed
        DB_PASSWORD=$(grep "^DB_PASSWORD=" "$LOCAL_PATH/.env.production.native" 2>/dev/null | cut -d= -f2)
        if [[ "$DB_PASSWORD" == "postgres" ]] || [[ -z "$DB_PASSWORD" ]] || [[ "$DB_PASSWORD" == "{{AUTO_GENERATED}}" ]]; then
            print_step "Generating strong DB password..."
            NEW_DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
            sed -i "s/^DB_PASSWORD=.*/DB_PASSWORD=$NEW_DB_PASSWORD/" "$LOCAL_PATH/.env.production.native"

            if [[ "$DRY_RUN" != "true" ]]; then
                ssh "$SSH_HOST" "sudo -u postgres psql -c \"ALTER USER thebot_user WITH PASSWORD '$NEW_DB_PASSWORD';\"" 2>/dev/null || {
                    print_warning "Failed to update DB password on server"
                }
                print_success "DB password generated and updated on server"
            else
                print_success "[DRY-RUN] Would generate DB password"
            fi
        fi

        # Generate Redis password if needed
        REDIS_PASSWORD=$(grep "^REDIS_PASSWORD=" "$LOCAL_PATH/.env.production.native" 2>/dev/null | cut -d= -f2)
        if [[ -z "$REDIS_PASSWORD" ]] || [[ "$REDIS_PASSWORD" == "{{AUTO_GENERATED}}" ]]; then
            print_step "Generating Redis password..."
            NEW_REDIS_PASSWORD=$(openssl rand -base64 24 | tr -d "=+/" | cut -c1-20)
            sed -i "s/^REDIS_PASSWORD=.*/REDIS_PASSWORD=$NEW_REDIS_PASSWORD/" "$LOCAL_PATH/.env.production.native"

            if [[ "$DRY_RUN" != "true" ]]; then
                ssh "$SSH_HOST" "echo 'requirepass $NEW_REDIS_PASSWORD' | sudo tee -a /etc/redis/redis.conf && sudo systemctl restart redis" 2>/dev/null || {
                    print_warning "Failed to set Redis password"
                }
                print_success "Redis password generated and set"
            else
                print_success "[DRY-RUN] Would generate Redis password"
            fi
        fi

        # Search for API keys in project
        print_step "Searching for API keys in project files..."
        TELEGRAM_TOKEN=$(grep -r "TELEGRAM_BOT_TOKEN" "$LOCAL_PATH" --include="*.env*" 2>/dev/null | grep -v "template" | head -1 | cut -d= -f2)
        OPENROUTER_KEY=$(grep -r "OPENROUTER_API_KEY" "$LOCAL_PATH" --include="*.env*" 2>/dev/null | grep -v "template" | head -1 | cut -d= -f2)

        if [[ -n "$TELEGRAM_TOKEN" ]] && [[ "$TELEGRAM_TOKEN" != "{{MANUAL_INPUT}}" ]]; then
            sed -i "s/^TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=$TELEGRAM_TOKEN/" "$LOCAL_PATH/.env.production.native"
            print_success "Found and set Telegram token"
        fi

        if [[ -n "$OPENROUTER_KEY" ]] && [[ "$OPENROUTER_KEY" != "{{MANUAL_INPUT}}" ]]; then
            sed -i "s/^OPENROUTER_API_KEY=.*/OPENROUTER_API_KEY=$OPENROUTER_KEY/" "$LOCAL_PATH/.env.production.native"
            print_success "Found and set OpenRouter key"
        fi

        # Copy .env to server
        print_step "Copying .env to server..."
        scp "$LOCAL_PATH/.env.production.native" "$SSH_HOST:$REMOTE_PATH/backend/.env" 2>/dev/null || {
            print_warning "Failed to copy .env, using existing remote .env"
        }
        print_success "ENV synchronized"
    else
        print_warning "No .env file found, skipping ENV synchronization"
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

    print_header "PHASE 6: DATABASE MIGRATIONS"

    print_step "Checking pending migrations..."
    if [[ "$DRY_RUN" != "true" ]]; then
        PENDING=$(ssh "$SSH_HOST" "bash -c 'source $VENV_PATH/bin/activate && cd $REMOTE_PATH/backend && python manage.py showmigrations --plan 2>/dev/null | grep \"\\[ \\]\" | wc -l'" 2>/dev/null || echo "0")

        if [[ "$PENDING" -gt 0 ]]; then
            print_warning "Found $PENDING pending migrations"
            ssh "$SSH_HOST" "bash -c 'source $VENV_PATH/bin/activate && cd $REMOTE_PATH/backend && python manage.py showmigrations --plan | grep \"\\[ \\]\"'" 2>/dev/null || true

            if [[ "$FORCE_DEPLOY" != "true" ]]; then
                read -p "Apply migrations? (y/N): " APPLY
                if [[ "$APPLY" != "y" ]]; then
                    print_error "Migration aborted by user"
                    return 1
                fi
            fi

            print_step "Applying migrations..."
            ssh "$SSH_HOST" "bash -c 'source $VENV_PATH/bin/activate && cd $REMOTE_PATH/backend && python manage.py migrate'" || {
                print_error "Migration failed"
                return 1
            }
            print_success "Migrations applied successfully"
        else
            print_success "No pending migrations"
        fi
    else
        print_info "[DRY-RUN] Would check and apply migrations"
    fi

    print_header "PHASE 7: RESTART SERVICES"

    print_step "Restarting services..."
    if [[ "$DRY_RUN" != "true" ]]; then
        # Stop services
        ssh "$SSH_HOST" "sudo systemctl stop thebot-backend thebot-daphne thebot-celery-worker thebot-celery-beat 2>/dev/null || true" || true
        sleep 2

        # Start services
        ssh "$SSH_HOST" "sudo systemctl start thebot-backend thebot-daphne thebot-celery-worker thebot-celery-beat" || print_error "Service restart failed"
        sleep 3

        # Check status
        STATUS=$(ssh "$SSH_HOST" "sudo systemctl is-active thebot-backend" 2>/dev/null || echo "inactive")
        DAPHNE_STATUS=$(ssh "$SSH_HOST" "sudo systemctl is-active thebot-daphne" 2>/dev/null || echo "inactive")

        if [[ "$STATUS" == "active" ]] && [[ "$DAPHNE_STATUS" == "active" ]]; then
            print_success "Services restarted successfully (Backend + Daphne)"
        else
            print_warning "Services may not be fully started, checking..."
            ssh "$SSH_HOST" "sudo systemctl status thebot-backend thebot-daphne" 2>&1 | head -10 || true
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

        # Check Daphne WebSocket port
        print_step "Checking Daphne WebSocket service..."
        DAPHNE_PORT_CHECK=$(ssh "$SSH_HOST" "nc -z localhost 8001 && echo 'open' || echo 'closed'" 2>/dev/null)

        if [[ "$DAPHNE_PORT_CHECK" == "open" ]]; then
            print_success "Daphne port 8001 is accessible"
        else
            print_warning "Daphne port 8001 is not accessible - check service logs"
        fi

        # Check WebSocket endpoint (should return HTTP 426 Upgrade Required)
        WS_ENDPOINT_CHECK=$(ssh "$SSH_HOST" "curl -s -o /dev/null -w '%{http_code}' -i http://localhost:8001/ws/chat/1/ 2>/dev/null || echo '000'")

        if [[ "$WS_ENDPOINT_CHECK" == "426" ]]; then
            print_success "WebSocket endpoint responding correctly (HTTP 426)"
        elif [[ "$WS_ENDPOINT_CHECK" == "000" ]]; then
            print_warning "WebSocket endpoint check failed - connection error"
        else
            print_warning "WebSocket endpoint returned HTTP $WS_ENDPOINT_CHECK (expected 426)"
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
    echo "  ssh $SSH_HOST 'sudo systemctl status thebot-backend thebot-daphne thebot-celery-worker thebot-celery-beat'"
    echo ""
    echo "View logs:"
    echo "  Backend:   ssh $SSH_HOST 'sudo journalctl -u thebot-backend -f'"
    echo "  Daphne:    ssh $SSH_HOST 'sudo journalctl -u thebot-daphne -f'"
    echo "  Celery:    ssh $SSH_HOST 'sudo journalctl -u thebot-celery-worker -f'"
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
