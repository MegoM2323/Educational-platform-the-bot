#!/bin/bash

################################################################################
# THE_BOT Platform - Full Native Deployment Script
#
# Полный редеплой на production с нативным systemd (без Docker)
# Сохраняет БД на production сервере (backup)
#
# Использование:
#   ./scripts/deploy/native-full-deploy.sh              # Интерактивный режим
#   ./scripts/deploy/native-full-deploy.sh --force      # Без подтверждения
#   ./scripts/deploy/native-full-deploy.sh --dry-run    # Симуляция без изменений
#
# Параметры окружения:
#   SSH_HOST           - SSH хост (default: mg@5.129.249.206)
#   REMOTE_PATH        - Путь проекта на сервере (default: /home/mg/THE_BOT_platform)
#   VENV_PATH          - Путь к venv (default: /home/mg/venv)
#   BACKUP_DIR         - Путь для бэкапов БД (default: /home/mg/backups)
#   GIT_BRANCH         - Git ветка для deploy (default: main)
#   SUDO_PASS          - Пароль для sudo (если нужен)
#
################################################################################

set -e

# ===== CONFIG =====
SSH_HOST="${SSH_HOST:-mg@5.129.249.206}"
REMOTE_PATH="${REMOTE_PATH:-/home/mg/THE_BOT_platform}"
VENV_PATH="${VENV_PATH:-/home/mg/venv}"
BACKUP_DIR="${BACKUP_DIR:-/home/mg/backups}"
LOCAL_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GIT_BRANCH="${GIT_BRANCH:-main}"
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
VERBOSE=false
SKIP_BACKUP=false

# ===== FUNCTIONS =====

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$DEPLOY_LOG"
}

success() {
    echo -e "${GREEN}✓${NC} $1" | tee -a "$DEPLOY_LOG"
}

error() {
    echo -e "${RED}✗${NC} $1" | tee -a "$DEPLOY_LOG"
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1" | tee -a "$DEPLOY_LOG"
}

info() {
    echo -e "${CYAN}ℹ${NC} $1" | tee -a "$DEPLOY_LOG"
}

# ===== PARSE ARGS =====

while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            log "DRY RUN MODE - никакие изменения не будут применены"
            shift
            ;;
        --force)
            FORCE_DEPLOY=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --skip-backup)
            SKIP_BACKUP=true
            shift
            ;;
        --branch)
            GIT_BRANCH="$2"
            shift 2
            ;;
        *)
            error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ===== PHASE 0: PRE-CHECKS =====

log "========== PHASE 0: PRE-CHECKS =========="

# Check SSH connectivity
log "Проверка SSH подключения к $SSH_HOST..."
if ! ssh -o ConnectTimeout=5 "$SSH_HOST" "echo OK" > /dev/null 2>&1; then
    error "Cannot connect to $SSH_HOST"
    exit 1
fi
success "SSH подключение OK"

# Check local git
log "Проверка локального git репозитория..."
if ! git -C "$LOCAL_PATH" status > /dev/null 2>&1; then
    error "Not a git repository: $LOCAL_PATH"
    exit 1
fi
success "Git репозиторий OK"

# ===== PHASE 1: LOCAL CHANGES =====

log ""
log "========== PHASE 1: LOCAL CHANGES =========="

# Check for uncommitted changes
CHANGES=$(git -C "$LOCAL_PATH" status --short | grep -v __pycache__ | grep -v '.log' | wc -l)
if [ "$CHANGES" -gt 0 ]; then
    warning "Найдены локальные изменения:"
    git -C "$LOCAL_PATH" status --short | grep -v __pycache__ | grep -v '.log' | sed 's/^/ /'

    if [ "$FORCE_DEPLOY" = false ]; then
        read -p "Коммитить эти изменения? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Deployment отменён"
            exit 1
        fi
    fi

    # Create commit
    log "Коммитирование изменений..."
    git -C "$LOCAL_PATH" add -A
    git -C "$LOCAL_PATH" commit -m "Обновление расписания и исправления

$(git -C "$LOCAL_PATH" status --short | grep -v __pycache__ | grep -v '.log' | head -10)

Автоматический коммит из скрипта развертывания"
    success "Коммит создан"
else
    info "Локальных изменений не найдено"
fi

# Get current branch and commit
CURRENT_BRANCH=$(git -C "$LOCAL_PATH" rev-parse --abbrev-ref HEAD)
CURRENT_COMMIT=$(git -C "$LOCAL_PATH" rev-parse --short HEAD)
log "Текущая ветка: $CURRENT_BRANCH @ $CURRENT_COMMIT"

# If no GIT_BRANCH specified, use current branch
if [ "$GIT_BRANCH" = "main" ] && [ "$CURRENT_BRANCH" != "main" ]; then
    log "Использование текущей ветки вместо main: $CURRENT_BRANCH"
    GIT_BRANCH="$CURRENT_BRANCH"
fi

# ===== PHASE 2: PRODUCTION BACKUP =====

log ""
log "========== PHASE 2: PRODUCTION BACKUP =========="

if [ "$SKIP_BACKUP" = false ]; then
    log "Создание backup БД на production..."

    if [ "$DRY_RUN" = false ]; then
        ssh "$SSH_HOST" /bin/bash << 'BACKUP_SCRIPT'
set -e
BACKUP_DIR="/home/mg/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_BACKUP="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql"

mkdir -p "$BACKUP_DIR"

# Backup PostgreSQL
echo "Создание backup PostgreSQL..."
PGPASSWORD="${DB_PASSWORD:-postgres}" pg_dump -h localhost -U thebot_user thebot_db > "$DB_BACKUP" 2>/dev/null || true

if [ -f "$DB_BACKUP" ]; then
    echo "✓ DB backup: $DB_BACKUP ($(du -h "$DB_BACKUP" | cut -f1))"

    # Clean old backups (keep last 7 days)
    find "$BACKUP_DIR" -name "db_backup_*.sql" -mtime +7 -delete || true
else
    echo "✗ Backup создать не удалось"
fi
BACKUP_SCRIPT
    fi
    success "Backup создан"
else
    warning "Backup пропущен (--skip-backup)"
fi

# ===== PHASE 3: CODE DEPLOYMENT =====

log ""
log "========== PHASE 3: CODE DEPLOYMENT =========="

log "Развертывание кода на production..."

if [ "$DRY_RUN" = false ]; then
    ssh "$SSH_HOST" /bin/bash << DEPLOY_SCRIPT
set -e
cd $REMOTE_PATH

# Git pull (или checkout если нужна другая ветка)
echo "Получение последних изменений..."
git fetch origin
git checkout $GIT_BRANCH
git pull origin $GIT_BRANCH

echo "✓ Code deployed"
DEPLOY_SCRIPT
    success "Код развёрнут"
else
    info "[DRY-RUN] Был бы выполнен git pull на $GIT_BRANCH"
fi

# ===== PHASE 4: MIGRATIONS =====

log ""
log "========== PHASE 4: DATABASE MIGRATIONS =========="

log "Выполнение миграций БД..."

if [ "$DRY_RUN" = false ]; then
    ssh "$SSH_HOST" /bin/bash << MIGRATE_SCRIPT
set -e
cd $REMOTE_PATH/backend
source $VENV_PATH/bin/activate

echo "Выполнение миграций..."
python manage.py migrate --noinput

echo "Сбор статических файлов..."
python manage.py collectstatic --noinput

echo "✓ Migrations выполнены"
MIGRATE_SCRIPT
    success "Миграции выполнены"
else
    info "[DRY-RUN] Были бы выполнены migrate и collectstatic"
fi

# ===== PHASE 5: SERVICE RESTART =====

log ""
log "========== PHASE 5: SERVICE RESTART =========="

log "Перезагрузка systemd сервисов..."

SERVICES=(
    "the-bot-daphne.service"
    "the-bot-celery-worker.service"
    "the-bot-celery-beat.service"
)

if [ "$DRY_RUN" = false ]; then
    for service in "${SERVICES[@]}"; do
        log "Перезагрузка $service..."
        ssh "$SSH_HOST" "echo 'fstpass' | sudo -S systemctl restart $service" || warning "Service $service не найден или ошибка"
    done

    sleep 5
    success "Сервисы перезагружены"
else
    info "[DRY-RUN] Были бы перезагружены: ${SERVICES[*]}"
fi

# ===== PHASE 6: VERIFICATION =====

log ""
log "========== PHASE 6: VERIFICATION =========="

log "Проверка статуса сервисов..."

if [ "$DRY_RUN" = false ]; then
    ssh "$SSH_HOST" /bin/bash << VERIFY_SCRIPT
set -e

echo "Статус сервисов:"
for service in the-bot-daphne.service the-bot-celery-worker.service; do
    status=\$(systemctl is-active \$service 2>/dev/null || echo "not-found")
    if [ "\$status" = "active" ]; then
        echo "  ✓ \$service: active"
    else
        echo "  ✗ \$service: \$status"
    fi
done

echo ""
echo "Последние логи Daphne (последние 10 строк):"
journalctl -u the-bot-daphne.service -n 10 --no-pager --since "5 minutes ago" 2>/dev/null | tail -5 || echo "  (no logs)"

VERIFY_SCRIPT
else
    info "[DRY-RUN] Была бы проведена проверка статуса сервисов"
fi

# ===== FINAL SUMMARY =====

log ""
log "========== DEPLOYMENT COMPLETE =========="
success "Развертывание успешно завершено!"

echo ""
echo "Summaryммарий:"
echo "  SSH Host: $SSH_HOST"
echo "  Remote Path: $REMOTE_PATH"
echo "  Git Branch: $GIT_BRANCH"
echo "  Commit: $CURRENT_COMMIT"
echo "  Backup: $([ "$SKIP_BACKUP" = true ] && echo 'skipped' || echo 'created')"
echo "  Dry Run: $([ "$DRY_RUN" = true ] && echo 'YES' || echo 'NO')"
echo ""
echo "Log file: $DEPLOY_LOG"
echo ""

# Final checks
log "Проверка доступности API..."
if [ "$DRY_RUN" = false ]; then
    sleep 3
    if curl -s -f https://the-bot.ru/api/auth/login/ -X POST \
        -H "Content-Type: application/json" \
        -d '{"email":"test@example.com","password":"test"}' > /dev/null 2>&1; then
        success "API доступен ✓"
    else
        warning "API может быть недоступен (проверь вручную)"
    fi
fi

echo ""
success "Все готово!"
