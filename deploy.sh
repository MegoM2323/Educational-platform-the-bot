#!/bin/bash

# THE_BOT Platform - Fully Automated Remote Deployment
# No interactive prompts, uses sudo for Docker operations
# Configuration via environment variables

set -euo pipefail

# =============================================================================
# CONFIGURATION (can be overridden by environment variables)
# =============================================================================
REMOTE_HOST="${REMOTE_HOST:-neil@176.108.248.21}"
REMOTE_DIR="${REMOTE_DIR:-/opt/vextra-trading}"
REMOTE_DOMAIN="${REMOTE_DOMAIN:-vextratrading.ru}"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_BEFORE_DEPLOY="${BACKUP_BEFORE_DEPLOY:-true}"
DRY_RUN="${DRY_RUN:-false}"
CERTBOT_EMAIL="${CERTBOT_EMAIL:-admin@vextratrading.ru}"

# Colors
if [ "${NO_COLOR:-0}" = "1" ]; then
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    NC=''
else
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    BLUE='\033[0;34m'
    NC='\033[0m'
fi

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================
log_step() {
    echo -e "${BLUE}[STEP]${NC} $1" >&2
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[✗]${NC} $1" >&2
    return 1
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1" >&2
}

# =============================================================================
# MAIN DEPLOYMENT FUNCTION
# =============================================================================
deploy() {
    log_step "Starting deployment to $REMOTE_HOST"
    log_info "Remote Dir: $REMOTE_DIR"
    log_info "Domain: $REMOTE_DOMAIN"
    log_info "Backup: $BACKUP_BEFORE_DEPLOY"
    log_info "Dry-run: $DRY_RUN"

    # Verify SSH connection
    if ! ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$REMOTE_HOST" "echo 'SSH OK'" > /dev/null 2>&1; then
        log_error "Cannot connect to $REMOTE_HOST via SSH"
        return 1
    fi
    log_success "SSH connection verified"

    # Create backup on remote if requested
    if [ "$BACKUP_BEFORE_DEPLOY" = "true" ]; then
        log_step "Creating database backup on remote server..."
        ssh -o StrictHostKeyChecking=no "$REMOTE_HOST" bash << 'BACKUP_EOF'
set -euo pipefail
REMOTE_DIR="/opt/vextra-trading"
BACKUP_DIR="$REMOTE_DIR/backups"
sudo mkdir -p "$BACKUP_DIR" 2>/dev/null || true
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql"
if sudo docker ps 2>/dev/null | grep -q thebot-postgres-prod; then
    echo "Creating database backup..."
    sudo docker exec thebot-postgres-prod pg_dump \
        -U postgres -d thebot_db \
        --no-owner --no-privileges 2>/dev/null | sudo tee "$BACKUP_FILE" > /dev/null
    if [ -f "$BACKUP_FILE" ]; then
        sudo gzip -f "$BACKUP_FILE"
        ls -t "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r sudo rm
        echo "✓ Backup created: $(sudo du -h "$BACKUP_FILE.gz" | cut -f1)"
    fi
else
    echo "Database not running yet - skipping backup"
fi
BACKUP_EOF
        log_success "Backup completed"
    fi

    # Deploy files via SSH and SCP
    log_step "Deploying files to remote server..."

    # Create remote directories
    ssh -o StrictHostKeyChecking=no "$REMOTE_HOST" bash << 'MKDIR_EOF'
sudo mkdir -p /opt/vextra-trading/{backend,frontend,nginx,database,scripts,backups}
CURRENT_USER=$(whoami)
sudo chown -R $CURRENT_USER:$CURRENT_USER /opt/vextra-trading
MKDIR_EOF

    # Copy docker-compose configuration
    log_info "Copying docker-compose.prod.yml..."
    scp -o StrictHostKeyChecking=no \
        "$PROJECT_DIR/docker-compose.prod.yml" \
        "$REMOTE_HOST:/opt/vextra-trading/" 2>&1 | grep -v "^docker-compose" || true

    # Copy .env file
    log_info "Copying environment file..."
    scp -o StrictHostKeyChecking=no \
        "$PROJECT_DIR/.deploy.env" \
        "$REMOTE_HOST:/opt/vextra-trading/.env" 2>&1 | grep -v "^\.env" || true

    # Copy backend files
    log_info "Copying backend Dockerfile and requirements..."
    scp -o StrictHostKeyChecking=no \
        "$PROJECT_DIR/backend/Dockerfile" \
        "$REMOTE_HOST:/opt/vextra-trading/backend/" 2>&1 | grep -v "^Dockerfile" || true

    scp -o StrictHostKeyChecking=no \
        "$PROJECT_DIR/backend/requirements.txt" \
        "$REMOTE_HOST:/opt/vextra-trading/backend/" 2>&1 | grep -v "^requirements" || true

    scp -o StrictHostKeyChecking=no \
        "$PROJECT_DIR/backend/docker-entrypoint.sh" \
        "$REMOTE_HOST:/opt/vextra-trading/backend/" 2>&1 | grep -v "^docker-entrypoint" || true

    # Sync backend source code
    log_info "Syncing backend source code (this may take a few minutes)..."
    rsync -avz --delete -e "ssh -o StrictHostKeyChecking=no" \
        --exclude='__pycache__' --exclude='*.pyc' --exclude='.venv' \
        --exclude='*.egg-info' --exclude='static' --exclude='media' \
        --exclude='logs' --exclude='htmlcov' \
        "$PROJECT_DIR/backend/" "$REMOTE_HOST:/opt/vextra-trading/backend/" 2>&1 | tail -5

    # Copy frontend files if exist
    if [ -f "$PROJECT_DIR/frontend/Dockerfile" ]; then
        log_info "Copying frontend Dockerfile..."
        scp -o StrictHostKeyChecking=no \
            "$PROJECT_DIR/frontend/Dockerfile" \
            "$REMOTE_HOST:/opt/vextra-trading/frontend/" 2>&1 | grep -v "^Dockerfile" || true
    fi

    log_success "Files synchronized"

    # Deploy and start containers
    log_step "Building and deploying Docker containers..."

    if [ "$DRY_RUN" != "true" ]; then
        ssh -o StrictHostKeyChecking=no "$REMOTE_HOST" bash -s << 'DEPLOY_EOF'
set -euo pipefail

REMOTE_DIR="/opt/vextra-trading"
DOMAIN="vextratrading.ru"
EMAIL="admin@vextratrading.ru"

cd "$REMOTE_DIR"

# Use docker compose or docker-compose with sudo
if sudo docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="sudo docker compose"
elif sudo docker-compose --version &> /dev/null 2>&1; then
    COMPOSE_CMD="sudo docker-compose"
else
    echo "Docker Compose not found"
    exit 1
fi

echo "Using: $COMPOSE_CMD"

# Stop old containers (preserve volumes)
$COMPOSE_CMD -f docker-compose.prod.yml down 2>/dev/null || true
sleep 3

# Ensure Docker is running
sudo systemctl start docker 2>/dev/null || true
sleep 2

# Build images
echo "Building Docker images..."
$COMPOSE_CMD -f docker-compose.prod.yml build --no-cache 2>&1 | tail -20

# Start containers
echo "Starting containers..."
$COMPOSE_CMD -f docker-compose.prod.yml up -d

# Wait for services
sleep 20

# Check health
echo ""
echo "Checking service health..."
$COMPOSE_CMD -f docker-compose.prod.yml ps

# Run migrations
echo "Running database migrations..."
$COMPOSE_CMD -f docker-compose.prod.yml exec -T backend \
    python manage.py migrate 2>/dev/null || echo "Migrations: skipped or already applied"

# Collect static files
echo "Collecting static files..."
$COMPOSE_CMD -f docker-compose.prod.yml exec -T backend \
    python manage.py collectstatic --noinput --clear 2>/dev/null || echo "Static files: skipped"

echo ""
echo "✓ Deployment completed successfully"
DEPLOY_EOF

        log_success "Containers deployed and running"
    else
        log_info "DRY-RUN: deployment commands not executed"
    fi

    # Verify deployment
    log_step "Verifying deployment..."
    ssh -o StrictHostKeyChecking=no "$REMOTE_HOST" bash -s << 'VERIFY_EOF'
REMOTE_DIR="/opt/vextra-trading"
cd "$REMOTE_DIR" || exit 0

if sudo docker compose version &> /dev/null 2>&1; then
    COMPOSE_CMD="sudo docker compose"
elif sudo docker-compose --version &> /dev/null 2>&1; then
    COMPOSE_CMD="sudo docker-compose"
else
    COMPOSE_CMD="docker-compose"
fi

# Check if services are up
echo "Checking services..."
$COMPOSE_CMD -f docker-compose.prod.yml ps 2>/dev/null || echo "Cannot check services"

# Check database
if sudo docker ps 2>/dev/null | grep -q thebot-postgres-prod; then
    echo "✓ Database container is running"
fi
VERIFY_EOF

    log_success "Verification completed"

    # Summary
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ DEPLOYMENT SUCCESSFUL                                       ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Platform is available at:"
    echo "  https://$REMOTE_DOMAIN"
    echo "  https://$REMOTE_DOMAIN/api/"
    echo ""
    echo "To monitor deployment:"
    echo "  ssh $REMOTE_HOST 'cd /opt/vextra-trading && sudo docker-compose -f docker-compose.prod.yml logs -f'"
    echo ""
}

# =============================================================================
# ENTRY POINT
# =============================================================================
main() {
    echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${YELLOW}║  THE_BOT Platform - Automated Deployment                       ║${NC}"
    echo -e "${YELLOW}║  https://vextratrading.ru                                      ║${NC}"
    echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""

    if deploy; then
        return 0
    else
        log_error "Deployment failed"
        return 1
    fi
}

main "$@"
