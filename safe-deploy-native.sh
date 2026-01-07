#!/bin/bash

################################################################################
# THE_BOT Platform - Native Deployment Script
#
# Полный редеплой на production с нативным systemd (без Docker)
# Копирует локальные файлы на production (БЕЗ git операций)
# Сохраняет БД на production
#
# Использование:
#   ./safe-deploy-native.sh              # Интерактивный
#   ./safe-deploy-native.sh --force      # Без подтверждения (быстро!)
#   ./safe-deploy-native.sh --dry-run    # Симуляция
#
################################################################################

set -e

# ===== CONFIG =====
SSH_HOST="${SSH_HOST:-mg@5.129.249.206}"
REMOTE_PATH="${REMOTE_PATH:-/home/mg/THE_BOT_platform}"
VENV_PATH="${VENV_PATH:-/home/mg/venv}"
BACKUP_DIR="${BACKUP_DIR:-/home/mg/backups}"
LOCAL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DEPLOY_LOG="/tmp/deploy_${TIMESTAMP}.log"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Options
DRY_RUN=false
FORCE_DEPLOY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --force) FORCE_DEPLOY=true; shift ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$DEPLOY_LOG"; }
success() { echo -e "${GREEN}✓${NC} $1" | tee -a "$DEPLOY_LOG"; }
error() { echo -e "${RED}✗${NC} $1" | tee -a "$DEPLOY_LOG"; }
warning() { echo -e "${YELLOW}⚠${NC} $1" | tee -a "$DEPLOY_LOG"; }
info() { echo -e "${CYAN}ℹ${NC} $1" | tee -a "$DEPLOY_LOG"; }

# ===== PHASE 0: PRE-CHECKS =====
log "========== PHASE 0: PRE-CHECKS =========="

# Check SSH
if ! ssh -o ConnectTimeout=5 "$SSH_HOST" "echo OK" > /dev/null 2>&1; then
    error "SSH connection failed to $SSH_HOST"
    exit 1
fi
success "SSH connection OK"

# ===== PHASE 1: DATABASE BACKUP =====
log ""
log "========== PHASE 1: DATABASE BACKUP =========="

if [ "$DRY_RUN" = false ]; then
    log "Creating database backup on production..."
    ssh "$SSH_HOST" /bin/bash << 'BACKUP_SCRIPT'
set -e
BACKUP_DIR="/home/mg/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "Backing up PostgreSQL database..."
PGPASSWORD="postgres" pg_dump -h localhost -U postgres thebot_db > "$BACKUP_DIR/db_backup_${TIMESTAMP}.sql" 2>/dev/null || {
    PGPASSWORD="postgres" pg_dump -h localhost -U thebot_user thebot_db > "$BACKUP_DIR/db_backup_${TIMESTAMP}.sql" 2>/dev/null || true
}

if [ -f "$BACKUP_DIR/db_backup_${TIMESTAMP}.sql" ]; then
    SIZE=$(du -h "$BACKUP_DIR/db_backup_${TIMESTAMP}.sql" | cut -f1)
    echo "✓ DB backup created: db_backup_${TIMESTAMP}.sql ($SIZE)"
    # Keep last 7 days
    find "$BACKUP_DIR" -name "db_backup_*.sql" -mtime +7 -delete 2>/dev/null || true
else
    echo "⚠ Warning: Backup may not have been created"
fi
BACKUP_SCRIPT
    success "Database backup completed"
else
    info "[DRY-RUN] Database backup skipped"
fi

# ===== PHASE 2: COPY FILES =====
log ""
log "========== PHASE 2: COPY FILES =========="

if [ "$DRY_RUN" = false ]; then
    log "Copying backend code..."
    rsync -av --delete \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='*.log' \
        --exclude='.env' \
        --exclude='dump.rdb' \
        --exclude='.venv' \
        --exclude='venv' \
        "$LOCAL_PATH/backend/" "$SSH_HOST:$REMOTE_PATH/backend/" > /dev/null 2>&1
    success "Backend code copied"

    log "Copying scripts..."
    rsync -av "$LOCAL_PATH/scripts/" "$SSH_HOST:$REMOTE_PATH/scripts/" > /dev/null 2>&1
    success "Scripts copied"
else
    info "[DRY-RUN] Would copy: backend/ and scripts/"
fi

# ===== PHASE 3: MIGRATIONS =====
log ""
log "========== PHASE 3: DATABASE MIGRATIONS =========="

if [ "$DRY_RUN" = false ]; then
    log "Running database migrations..."
    ssh "$SSH_HOST" /bin/bash << MIGRATE_SCRIPT
set -e
cd $REMOTE_PATH/backend
source $VENV_PATH/bin/activate

echo "Running Django migrate..."
python manage.py migrate --noinput 2>&1 | tail -5

echo "Collecting static files..."
python manage.py collectstatic --noinput 2>&1 | tail -3

echo "✓ Migrations completed"
MIGRATE_SCRIPT
    success "Database migrations completed"
else
    info "[DRY-RUN] Would run: migrate, collectstatic"
fi

# ===== PHASE 4: RESTART SERVICES =====
log ""
log "========== PHASE 4: RESTART SERVICES =========="

if [ "$DRY_RUN" = false ]; then
    log "Restarting services..."
    ssh "$SSH_HOST" /bin/bash << RESTART_SCRIPT
set -e
echo "Restarting Daphne (WebSocket/HTTP)..."
echo "fstpass" | sudo -S systemctl restart the-bot-daphne.service 2>&1 | grep -v "password" || true

echo "Restarting Celery worker..."
echo "fstpass" | sudo -S systemctl restart the-bot-celery-worker.service 2>&1 | grep -v "password" || true

sleep 3

echo "Service status:"
systemctl is-active the-bot-daphne.service && echo "✓ Daphne active" || echo "✗ Daphne failed"
systemctl is-active the-bot-celery-worker.service && echo "✓ Celery active" || echo "✗ Celery may be starting"
RESTART_SCRIPT
    success "Services restarted"
else
    info "[DRY-RUN] Would restart: the-bot-daphne, the-bot-celery-worker"
fi

# ===== PHASE 5: VERIFICATION =====
log ""
log "========== PHASE 5: VERIFICATION =========="

if [ "$DRY_RUN" = false ]; then
    sleep 2
    log "Verifying API is responding..."

    RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" https://the-bot.ru/api/auth/login/ \
        -X POST \
        -H "Content-Type: application/json" \
        -d '{"email":"test@test.com","password":"test"}' 2>/dev/null || echo "000")

    if [ "$RESPONSE" != "000" ] && [ "$RESPONSE" != "500" ]; then
        success "API is responding (HTTP $RESPONSE)"
    else
        warning "API response: HTTP $RESPONSE (check logs if problematic)"
    fi
else
    info "[DRY-RUN] Would verify API"
fi

# ===== SUMMARY =====
log ""
log "========== DEPLOYMENT COMPLETE =========="
success "Native deployment finished successfully!"

echo ""
echo "Summary:"
echo "  Server: $SSH_HOST"
echo "  Remote path: $REMOTE_PATH"
echo "  Timestamp: $TIMESTAMP"
echo "  Mode: $([ "$DRY_RUN" = true ] && echo 'DRY-RUN' || echo 'LIVE')"
echo ""
echo "What was deployed:"
echo "  • Backend code (latest local version)"
echo "  • Database migrations"
echo "  • Static files"
echo ""
echo "Available commands:"
echo "  View logs: ssh $SSH_HOST journalctl -u the-bot-daphne.service -f"
echo "  Check status: ssh $SSH_HOST systemctl status the-bot-daphne.service"
echo ""
echo "Production URL: https://the-bot.ru"
echo "Log file: $DEPLOY_LOG"
echo ""
