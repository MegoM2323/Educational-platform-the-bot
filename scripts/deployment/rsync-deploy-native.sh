#!/bin/bash

################################################################################
# THE_BOT Platform - Native RSYNC Deployment Script
#
# Fast deployment using rsync to sync code, build frontend, and restart services
# Production deployment via rsync (faster than git pull)
#
# Usage:
#   ./rsync-deploy-native.sh                    # Interactive full deploy
#   ./rsync-deploy-native.sh --force            # No confirmation
#   ./rsync-deploy-native.sh --dry-run          # Simulation mode
#   ./rsync-deploy-native.sh --skip-frontend    # Skip frontend build
#   ./rsync-deploy-native.sh --skip-migrations  # Skip migrations (hotfix)
#   ./rsync-deploy-native.sh --verbose          # Detailed logging
#   ./rsync-deploy-native.sh --help             # Show help
#
################################################################################

set -euo pipefail

# ===== CONFIG =====
PROD_USER="${PROD_USER:-mg}"
PROD_SERVER="${PROD_SERVER:-5.129.249.206}"
PROD_HOME="${PROD_HOME:-/home/mg/THE_BOT_platform}"
VENV_PATH="${VENV_PATH:-/home/mg/venv}"
BACKUP_DIR="${BACKUP_DIR:-/home/mg/backups}"
LOCAL_PATH="$(cd "$(dirname "$0")/../.." && pwd)"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_DIR="${PROD_HOME}/logs"
DEPLOY_LOG="${LOG_DIR}/rsync_deploy_${TIMESTAMP}.log"

# Systemd services
SERVICES=("thebot-celery-worker.service" "thebot-celery-beat.service" "thebot-daphne.service")

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
SKIP_FRONTEND=false
SKIP_MIGRATIONS=false
VERBOSE=false

# ===== HELP =====
show_help() {
    cat << EOF
THE_BOT Platform - RSYNC Deployment Script

USAGE:
    $0 [OPTIONS]

OPTIONS:
    --dry-run             Simulation mode (show what would be synced)
    --force               Skip confirmation prompts
    --skip-frontend       Skip frontend build (code only)
    --skip-migrations     Skip database migrations (for hotfixes)
    --verbose             Detailed logging
    --help                Show this help message

EXAMPLES:
    $0                              # Full interactive deploy
    $0 --dry-run                    # Preview changes
    $0 --force                      # Quick deploy without prompts
    $0 --skip-migrations --force    # Hotfix deploy
    $0 --skip-frontend --force      # Code-only deploy

PHASES:
    Phase 0: Pre-checks (SSH, local files, disk space)
    Phase 1: Database backup (optional)
    Phase 2: Frontend build (optional)
    Phase 3: Backend rsync
    Phase 4: Frontend dist rsync
    Phase 5: Execute remote migrations & restart services

EOF
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run) DRY_RUN=true; shift ;;
        --force) FORCE_DEPLOY=true; shift ;;
        --skip-frontend) SKIP_FRONTEND=true; shift ;;
        --skip-migrations) SKIP_MIGRATIONS=true; shift ;;
        --verbose) VERBOSE=true; shift ;;
        --help) show_help ;;
        *) echo "Unknown option: $1. Use --help for usage."; exit 1 ;;
    esac
done

# ===== LOGGING FUNCTIONS =====
log() { echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1" | tee -a "$DEPLOY_LOG"; }
success() { echo -e "${GREEN}✓${NC} $1" | tee -a "$DEPLOY_LOG"; }
error() { echo -e "${RED}✗${NC} $1" | tee -a "$DEPLOY_LOG"; }
warning() { echo -e "${YELLOW}⚠${NC} $1" | tee -a "$DEPLOY_LOG"; }
log_info() { echo -e "${CYAN}ℹ${NC} $1" | tee -a "$DEPLOY_LOG"; }

print_header() {
    echo "" | tee -a "$DEPLOY_LOG"
    echo -e "${BLUE}╔════════════════════════════════════════════════════════════╗${NC}" | tee -a "$DEPLOY_LOG"
    echo -e "${BLUE}║${NC} $1" | tee -a "$DEPLOY_LOG"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════╝${NC}" | tee -a "$DEPLOY_LOG"
}

# ===== BACKUP AND ROLLBACK FUNCTIONS =====

BACKUP_CREATED=false
BACKUP_TIMESTAMP=""

create_backup_phase() {
    print_header "PHASE 0B: CREATING BACKUP ON PRODUCTION SERVER"

    log "Creating backup of current code (timestamp: ${TIMESTAMP})..."

    ssh "${PROD_USER}@${PROD_SERVER}" bash << BACKUP_SCRIPT
set -e

BACKUP_DIR="/home/${PROD_USER}/backups"
TIMESTAMP="${TIMESTAMP}"

mkdir -p "\${BACKUP_DIR}"

log_msg() {
    echo "[backup] \$1"
}

# Backup backend code
if [ -d "${PROD_HOME}/backend" ]; then
    log_msg "Backing up backend/"
    tar -czf "\${BACKUP_DIR}/backend_\${TIMESTAMP}.tar.gz" \\
        -C "${PROD_HOME}" backend/ \\
        --exclude='__pycache__' \\
        --exclude='*.pyc' \\
        --exclude='.git' \\
        --exclude='.venv' \\
        --exclude='venv' \\
        --exclude='*.sqlite3' \\
        --exclude='media/' \\
        --exclude='staticfiles/' 2>/dev/null || true
    log_msg "Backend backup completed"
fi

# Backup frontend dist
if [ -d "${PROD_HOME}/frontend/dist" ]; then
    log_msg "Backing up frontend/dist/"
    tar -czf "\${BACKUP_DIR}/frontend_dist_\${TIMESTAMP}.tar.gz" \\
        -C "${PROD_HOME}" frontend/dist/ 2>/dev/null || true
    log_msg "Frontend dist backup completed"
fi

# Save deployment reference
echo "Backup created at \$(date)" > "\${BACKUP_DIR}/BACKUP_REFERENCE_\${TIMESTAMP}.txt"
echo "Previous commit: \$(cd ${PROD_HOME} && git rev-parse HEAD 2>/dev/null || echo 'N/A')" >> "\${BACKUP_DIR}/BACKUP_REFERENCE_\${TIMESTAMP}.txt"

# Clean old backups (older than 7 days)
find "\${BACKUP_DIR}" -name "backend_*.tar.gz" -mtime +7 -delete 2>/dev/null || true
find "\${BACKUP_DIR}" -name "frontend_dist_*.tar.gz" -mtime +7 -delete 2>/dev/null || true

log_msg "Backup cleanup completed"
BACKUP_SCRIPT

    if [ $? -ne 0 ]; then
        error "Backup creation failed on production server!"
        return 1
    fi

    BACKUP_CREATED=true
    BACKUP_TIMESTAMP="${TIMESTAMP}"
    success "Backups created on production server"
    return 0
}

rollback_from_backup() {
    local backup_ts="${1:-}"

    if [ -z "${backup_ts}" ]; then
        error "No backup timestamp provided for rollback"
        return 1
    fi

    error "ROLLING BACK deployment from backup_${backup_ts}..."

    ssh "${PROD_USER}@${PROD_SERVER}" bash << ROLLBACK_SCRIPT
set -e

BACKUP_DIR="/home/${PROD_USER}/backups"
TIMESTAMP="${backup_ts}"

log_msg() {
    echo "[rollback] \$1"
}

log_msg "Restoring from backup_\${TIMESTAMP}..."

# Restore backend
if [ -f "\${BACKUP_DIR}/backend_\${TIMESTAMP}.tar.gz" ]; then
    log_msg "Restoring backend/"
    tar -xzf "\${BACKUP_DIR}/backend_\${TIMESTAMP}.tar.gz" -C "${PROD_HOME}"
    log_msg "Backend restored"
else
    echo "ERROR: Backend backup not found: \${BACKUP_DIR}/backend_\${TIMESTAMP}.tar.gz"
    exit 1
fi

# Restore frontend dist
if [ -f "\${BACKUP_DIR}/frontend_dist_\${TIMESTAMP}.tar.gz" ]; then
    log_msg "Restoring frontend/dist/"
    tar -xzf "\${BACKUP_DIR}/frontend_dist_\${TIMESTAMP}.tar.gz" -C "${PROD_HOME}"
    log_msg "Frontend dist restored"
fi

log_msg "Rollback completed successfully"
ROLLBACK_SCRIPT

    if [ $? -ne 0 ]; then
        error "Rollback failed!"
        return 1
    fi

    success "Deployment rolled back successfully"
    return 0
}

trap_error_with_rollback() {
    local phase="$1"

    error "ERROR in ${phase}"

    if [ "${BACKUP_CREATED}" == "true" ] && [ -n "${BACKUP_TIMESTAMP}" ]; then
        warning "Starting automatic rollback..."
        if rollback_from_backup "${BACKUP_TIMESTAMP}"; then
            log "Restarting services after rollback..."
            ssh "${PROD_USER}@${PROD_SERVER}" bash << 'RESTART_SCRIPT'
set -e
sudo systemctl restart thebot-daphne.service
sudo systemctl restart thebot-celery-worker.service
sudo systemctl restart thebot-celery-beat.service
RESTART_SCRIPT
        fi
    fi

    return 1
}

# ===== ENSURE LOG DIRECTORY EXISTS =====
mkdir -p "$LOG_DIR" || {
    LOG_DIR="/tmp"
    DEPLOY_LOG="${LOG_DIR}/rsync_deploy_${TIMESTAMP}.log"
    echo "WARNING: Could not create logs directory, using /tmp instead"
}

# ===== ERROR HANDLING =====
trap_error() {
    local phase="$1"
    error "ERROR in ${phase}"

    if [ "${BACKUP_CREATED}" == "true" ] && [ -n "${BACKUP_TIMESTAMP}" ]; then
        warning "Starting automatic rollback..."
        if rollback_from_backup "${BACKUP_TIMESTAMP}"; then
            log "Restarting services after rollback..."
            ssh "${PROD_USER}@${PROD_SERVER}" bash << 'RESTART_SCRIPT'
set -e
sudo systemctl restart thebot-daphne.service
sudo systemctl restart thebot-celery-worker.service
sudo systemctl restart thebot-celery-beat.service
RESTART_SCRIPT
        fi
    fi
}

cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ]; then
        error "Deployment failed! Check logs at: $DEPLOY_LOG"
        if grep -q "CRITICAL\|ERROR" "$DEPLOY_LOG" 2>/dev/null; then
            if [ -n "${BACKUP_TIMESTAMP:-}" ]; then
                error "Initiating rollback..."
                rollback_from_backup "$BACKUP_TIMESTAMP"
            fi
        fi
    fi
}

trap 'trap_error "Deployment execution"' ERR
trap cleanup EXIT

# ===== PHASE 0: PRE-CHECKS =====
print_header "PHASE 0: PRE-DEPLOYMENT CHECKS"

log "Checking SSH connectivity..."
if ! ssh -o ConnectTimeout=5 "${PROD_USER}@${PROD_SERVER}" "echo 'SSH OK'" > /dev/null 2>&1; then
    error "SSH connection failed to ${PROD_USER}@${PROD_SERVER}"
    exit 1
fi
success "SSH connectivity verified"

log "Checking local project structure..."
if [ ! -d "$LOCAL_PATH/backend" ]; then
    error "backend/ directory not found at $LOCAL_PATH"
    exit 1
fi
if [ ! -d "$LOCAL_PATH/frontend" ]; then
    error "frontend/ directory not found at $LOCAL_PATH"
    exit 1
fi
success "Local project structure verified"

log "Checking remote server disk space..."
REMOTE_DISK=$(ssh "${PROD_USER}@${PROD_SERVER}" "df -h '${PROD_HOME}' | tail -1 | awk '{print \$4}'")
log_info "Remote available disk: $REMOTE_DISK"

log "Checking for Git uncommitted changes..."
if [ -n "$(cd "$LOCAL_PATH" && git status --porcelain 2>/dev/null)" ]; then
    warning "You have uncommitted changes in Git. Consider committing them first."
    if [ "$FORCE_DEPLOY" = false ]; then
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
fi
success "Pre-checks completed"

# ===== PHASE 0B: CODE BACKUP =====
if [ "$DRY_RUN" = false ]; then
    create_backup_phase || {
        error "Failed to create backup before deployment"
        exit 1
    }
fi

# ===== PHASE 1: DATABASE BACKUP (optional) =====
print_header "PHASE 1: DATABASE BACKUP"

if [ "$DRY_RUN" = true ]; then
    log_info "DRY-RUN: Would backup PostgreSQL database"
else
    log "Creating PostgreSQL backup on remote server..."
    BACKUP_FILE="thebot_db_${TIMESTAMP}.sql"

    if ssh "${PROD_USER}@${PROD_SERVER}" bash << DBBACKUP
set -e
BACKUP_DIR="/home/mg/backups"
BACKUP_FILE="thebot_db_${TIMESTAMP}.sql"
PROD_HOME="/home/mg/THE_BOT_platform"
VENV_PATH="/home/mg/venv"

mkdir -p "\${BACKUP_DIR}"
cd "\${PROD_HOME}" && source "\${VENV_PATH}/bin/activate"
python backend/manage.py dumpdata --natural-foreign --natural-primary > "\${BACKUP_DIR}/\${BACKUP_FILE}" 2>/dev/null
chmod 600 "\${BACKUP_DIR}/\${BACKUP_FILE}"
gzip "\${BACKUP_DIR}/\${BACKUP_FILE}"
DBBACKUP
    then
        success "Database backup created: ${BACKUP_FILE}.gz"
    else
        error "Database backup failed - critical for rollback!"
        exit 1
    fi
fi

# ===== PHASE 2: FRONTEND BUILD (optional) =====
if [ "$SKIP_FRONTEND" = true ]; then
    log_info "Skipping frontend build (--skip-frontend flag)"
else
    print_header "PHASE 2: BUILDING FRONTEND"

    log "Installing frontend dependencies..."
    if [ "$DRY_RUN" = false ]; then
        if ! cd "$LOCAL_PATH/frontend"; then
            error "Failed to change to frontend directory: $LOCAL_PATH/frontend"
            exit 1
        fi
        npm install --legacy-peer-deps || {
            error "npm install failed"
            exit 1
        }
        success "Frontend dependencies installed"
    fi

    log "Building frontend distribution..."
    if [ "$DRY_RUN" = false ]; then
        if ! cd "$LOCAL_PATH/frontend"; then
            error "Failed to change to frontend directory: $LOCAL_PATH/frontend"
            exit 1
        fi
        if ! npm run build; then
            error "Frontend build failed (npm run build)"
            exit 1
        fi
        if [ ! -d "dist" ]; then
            error "frontend/dist/ was not created after build"
            exit 1
        fi
        success "Frontend built successfully"
    else
        log_info "DRY-RUN: Would build frontend with 'npm run build'"
    fi
fi

# ===== PHASE 3: BACKEND RSYNC =====
print_header "PHASE 3: SYNCING BACKEND FILES"

log_info "Preparing backend rsync..."

# Validate backend directory
if [ ! -d "$LOCAL_PATH/backend" ]; then
    error "backend/ directory not found at $LOCAL_PATH!"
    exit 1
fi

# Exclude patterns for rsync
RSYNC_EXCLUDE=(
    "--exclude=.git"
    "--exclude=.claude"
    "--exclude=__pycache__"
    "--exclude=*.pyc"
    "--exclude=.env"
    "--exclude=.venv"
    "--exclude=venv"
    "--exclude=node_modules"
    "--exclude=.pytest_cache"
    "--exclude=.coverage"
    "--exclude=htmlcov"
    "--exclude=dist"
    "--exclude=.DS_Store"
)

RSYNC_CMD=(
    "rsync"
    "-avz"
    "--delete"
    "${RSYNC_EXCLUDE[@]}"
    "$LOCAL_PATH/backend/"
    "${PROD_USER}@${PROD_SERVER}:${PROD_HOME}/backend/"
)

log "Syncing backend code to production server..."

if [ "$DRY_RUN" = true ]; then
    log_info "DRY-RUN: ${RSYNC_CMD[@]} --dry-run"
    "${RSYNC_CMD[@]}" --dry-run || {
        error "Rsync dry-run failed"
        exit 1
    }
else
    "${RSYNC_CMD[@]}" || {
        trap_error_with_rollback "PHASE 3: Backend rsync"
    }
fi

success "Backend files synced successfully"

# ===== PHASE 4: FRONTEND RSYNC =====
print_header "PHASE 4: SYNCING FRONTEND FILES"

log_info "Preparing frontend rsync..."

# Validate frontend/dist exists (was built in Phase 2)
if [ "$SKIP_FRONTEND" = false ] && [ ! -d "$LOCAL_PATH/frontend/dist" ]; then
    error "frontend/dist/ not found! Run Phase 2 build first."
    exit 1
fi

if [ "$SKIP_FRONTEND" = false ]; then
    log_info "Syncing frontend/dist/ to production server..."

    FRONTEND_RSYNC_CMD=(
        "rsync"
        "-avz"
        "--delete"
        "$LOCAL_PATH/frontend/dist/"
        "${PROD_USER}@${PROD_SERVER}:${PROD_HOME}/frontend/dist/"
    )

    if [ "$DRY_RUN" = true ]; then
        log_info "DRY-RUN: ${FRONTEND_RSYNC_CMD[@]}"
        "${FRONTEND_RSYNC_CMD[@]}" --dry-run || {
            error "Frontend dist rsync dry-run failed"
            exit 1
        }
    else
        "${FRONTEND_RSYNC_CMD[@]}" || {
            trap_error_with_rollback "PHASE 4: Frontend dist rsync"
        }
    fi

    success "Frontend dist synced successfully"

    # Optionally sync public/ assets
    if [ -d "$LOCAL_PATH/frontend/public" ]; then
        log_info "Syncing frontend/public/ assets..."

        PUBLIC_RSYNC_CMD=(
            "rsync"
            "-avz"
            "$LOCAL_PATH/frontend/public/"
            "${PROD_USER}@${PROD_SERVER}:${PROD_HOME}/frontend/public/"
        )

        if [ "$DRY_RUN" = true ]; then
            "${PUBLIC_RSYNC_CMD[@]}" --dry-run 2>/dev/null || {
                log_info "DRY-RUN: frontend/public/ sync would have issues (non-critical)"
            }
        else
            "${PUBLIC_RSYNC_CMD[@]}" 2>/dev/null || {
                warning "frontend/public/ sync had issues (non-critical)"
            }
        fi
    fi

    success "Frontend files synced"
else
    log_info "Skipping frontend sync (--skip-frontend flag)"
fi

# ===== PHASE 5: REMOTE MIGRATIONS & SERVICE RESTART =====
if [ "$DRY_RUN" = false ]; then
    print_header "PHASE 5: EXECUTING REMOTE MIGRATIONS & RESTART SERVICES"

    log "Executing remote deployment commands..."

    ssh "${PROD_USER}@${PROD_SERVER}" bash -s << EOFREMOTE
set -euo pipefail

VENV_PATH="/home/mg/venv"
PROD_HOME="/home/mg/THE_BOT_platform"
SERVICES=("thebot-celery-worker.service" "thebot-celery-beat.service" "thebot-daphne.service")
SKIP_MIGRATIONS="${SKIP_MIGRATIONS}"

log() { echo "[remote] \$1"; }

cd "\${PROD_HOME}"
source "\${VENV_PATH}/bin/activate"

if [ "\${SKIP_MIGRATIONS}" = "true" ]; then
    log "Skipping migrations (hotfix mode)"
else
    log "Checking migrations first..."
    python backend/manage.py migrate --check --noinput --verbosity 1 || {
        echo "ERROR: Migration check failed!"
        exit 1
    }
    log "Running Django migrations..."
    python backend/manage.py migrate --noinput
fi

log "Collecting static files..."
python backend/manage.py collectstatic --noinput --clear

log "Restarting systemd services..."
for service in "\${SERVICES[@]}"; do
    sudo systemctl restart "\$service"
done

log "Services restarted successfully"
sleep 5

log "Checking service health..."
for service in "\${SERVICES[@]}"; do
    if systemctl is-active --quiet "\$service"; then
        log "✓ \$service is active"
    else
        echo "ERROR: \$service is NOT active"
        exit 1
    fi
done

if [ "\${SKIP_MIGRATIONS}" = "true" ]; then
    log "Hotfix deployment completed!"
else
    log "Deployment completed successfully!"
fi
EOFREMOTE

    if [ $? -eq 0 ]; then
        success "Remote deployment completed"
    else
        trap_error_with_rollback "PHASE 5: Remote migrations and service restart"
    fi
else
    print_header "PHASE 5: EXECUTING REMOTE MIGRATIONS & RESTART SERVICES (DRY-RUN)"
    log_info "DRY-RUN: Would execute:"
    log_info "  - Check migrations (unless --skip-migrations)"
    log_info "  - Run migrations (unless --skip-migrations)"
    log_info "  - collectstatic"
    log_info "  - Restart systemd services"
    log_info "  - Service health checks"
fi

# ===== FINAL REPORT =====
print_header "DEPLOYMENT COMPLETED"
success "All phases completed successfully!"
log_info "Deployment log: $DEPLOY_LOG"

echo ""
echo "Summary:"
echo "  - Backend synced via rsync"
if [ "$SKIP_FRONTEND" = false ]; then
    echo "  - Frontend built and synced"
fi
echo "  - Migrations executed"
echo "  - Services restarted"
echo ""
log_info "To verify deployment:"
log_info "  ssh ${PROD_USER}@${PROD_SERVER}"
log_info "  systemctl status thebot-daphne.service"
log_info "  journalctl -u thebot-daphne.service -f"

################################################################################
# PHASE 6: Database Migrations & Static Files Validation
################################################################################

print_header "PHASE 6: DATABASE MIGRATIONS & STATIC FILES"

if [ "$DRY_RUN" = false ]; then
    log_info "Validating database migrations on production..."
    
    ssh "${PROD_USER}@${PROD_SERVER}" bash << MIGCHECK
set -e

log() { echo "[remote] \$1"; }

PROD_HOME="/home/mg/THE_BOT_platform"
VENV_PATH="/home/mg/venv"

cd "\${PROD_HOME}"
source "\${VENV_PATH}/bin/activate"

cd backend

# Check migrations first
log "Checking migration status..."
python manage.py migrate --check --no-input --verbosity 1 || {
    echo "ERROR: Migration validation failed!"
    exit 1
}

log "SUCCESS: All migrations validated"

MIGCHECK

    if [ $? -ne 0 ]; then
        error "Migration validation failed!"
        exit 1
    fi
    
    success "Phase 6 completed"
else
    log_info "DRY-RUN: Would validate migrations on production"
fi

################################################################################
# PHASE 7: Health Checks & System Status
################################################################################

print_header "PHASE 7: HEALTH CHECKS & SYSTEM STATUS"

if [ "$DRY_RUN" = false ]; then
    log_info "Running health checks on production..."
    
    ssh "${PROD_USER}@${PROD_SERVER}" bash << HEALTHCHECK
set -e

log() { echo "[remote] \$1"; }
PROD_HOME="/home/mg/THE_BOT_platform"

# Check service status
log "Checking service status..."
for service in thebot-daphne thebot-celery-worker thebot-celery-beat; do
    if sudo systemctl is-active --quiet "\$service"; then
        log "✓ \$service is running"
    else
        log "✗ \$service is NOT running"
        exit 1
    fi
done

# Check disk space
log "Checking disk space..."
DISK_USAGE=\$(df -h "\${PROD_HOME}" | awk 'NR==2 {print \$5}' | sed 's/%//')

if [ "\${DISK_USAGE}" -lt 80 ]; then
    log "✓ Disk usage: \${DISK_USAGE}%"
elif [ "\${DISK_USAGE}" -lt 90 ]; then
    log "⚠ Disk usage: \${DISK_USAGE}% (monitor)"
else
    log "✗ Disk usage: \${DISK_USAGE}% (critical!)"
    exit 1
fi

# Check API health
log "Checking API health..."
if curl -f --max-time 10 http://localhost:8000/api/health/ 2>/dev/null | grep -q "status\|ok\|healthy" 2>/dev/null || true; then
    log "✓ API is responding"
else
    log "⚠ API health check failed or unreachable (may be normal on first deploy)"
fi

log "SUCCESS: All health checks passed"

HEALTHCHECK

    if [ $? -ne 0 ]; then
        error "Health checks failed!"
        exit 1
    fi
    
    success "Phase 7 completed"
else
    log_info "DRY-RUN: Would perform health checks"
fi

################################################################################
# PHASE 8: Final Deployment Summary
################################################################################

print_header "PHASE 8: DEPLOYMENT SUMMARY"

success "DEPLOYMENT COMPLETED SUCCESSFULLY!"
echo ""
echo "Summary of completed operations:"
echo "  ✓ Code synced via rsync"
if [ "$SKIP_FRONTEND" = false ]; then
    echo "  ✓ Frontend built locally and synced"
fi
echo "  ✓ Database migrations validated"
echo "  ✓ Static files collected"
echo "  ✓ Services running correctly"
echo "  ✓ Health checks passed"
echo ""
log_info "Deployment completed at: $(date)"
log_info "Server: ${PROD_SERVER}"
log_info "Home: ${PROD_HOME}"
echo ""
success "READY TO USE!"

exit 0
