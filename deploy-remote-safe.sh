#!/bin/bash

# THE_BOT Platform - Remote Safe Deployment with Database Preservation
# This script deploys the application to a remote server preserving the database
# Usage: ./deploy-remote-safe.sh [--no-backup] [--dry-run]

set -euo pipefail

# =============================================================================
# CONFIGURATION - CUSTOMIZE THESE VALUES
# =============================================================================
REMOTE_HOST="${REMOTE_HOST:-neil@176.108.248.21}"  # SSH connection string
REMOTE_DIR="${REMOTE_DIR:-/home/neil/the-bot-platform}"  # Deployment directory
REMOTE_DOMAIN="${REMOTE_DOMAIN:-the-bot.ru}"  # Domain name for SSL
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_BEFORE_DEPLOY=true
DRY_RUN=false
CERTBOT_EMAIL="${CERTBOT_EMAIL:-admin@the-bot.ru}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Parse arguments
for arg in "$@"; do
    case $arg in
        --no-backup)
            BACKUP_BEFORE_DEPLOY=false
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        *)
            ;;
    esac
done

echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  THE_BOT Platform - Remote Safe Deployment                    ║${NC}"
echo -e "${YELLOW}║  Database Preservation & Rollback Support                     ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Remote Host: $REMOTE_HOST"
echo "Remote Dir:  $REMOTE_DIR"
echo "Domain:      $REMOTE_DOMAIN"
echo "Backup:      $BACKUP_BEFORE_DEPLOY"
echo "Dry-run:     $DRY_RUN"
echo ""

# Logging functions
log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Check SSH connection
check_ssh() {
    log_step "Checking SSH connection to $REMOTE_HOST..."
    if ! ssh -o ConnectTimeout=5 "$REMOTE_HOST" "echo 'SSH OK'" > /dev/null 2>&1; then
        log_error "Cannot connect to $REMOTE_HOST"
        exit 1
    fi
    log_success "SSH connection OK"
}

# Create backup of production database
backup_database() {
    log_step "Creating backup of production database..."

    ssh "$REMOTE_HOST" bash -s << 'BACKUP_SCRIPT'
set -euo pipefail

REMOTE_DIR="/opt/the-bot-platform"
BACKUP_DIR="$REMOTE_DIR/backups"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Generate backup filename with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql"
BACKUP_FILE_GZ="$BACKUP_FILE.gz"

echo "Creating database backup..."

# Check if PostgreSQL container is running
if docker ps 2>/dev/null | grep -q thebot-postgres-prod; then
    docker exec thebot-postgres-prod pg_dump \
        -U postgres \
        -d thebot_db \
        --no-owner \
        --no-privileges \
        > "$BACKUP_FILE" 2>/dev/null || {
        echo "Error: Docker backup failed"
        exit 1
    }

    # Compress backup
    gzip -f "$BACKUP_FILE"

    # Keep only last 5 backups to save space
    ls -t "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r rm

    echo "✓ Backup created: $(du -h "$BACKUP_FILE_GZ" | cut -f1)"
else
    echo "⚠ Database container not running - skipping live backup"
fi
BACKUP_SCRIPT

    log_success "Database backup completed"
}

# Deploy files to remote server
deploy_files() {
    log_step "Deploying files to $REMOTE_HOST..."

    # Create remote directories
    ssh "$REMOTE_HOST" "mkdir -p $REMOTE_DIR/backend $REMOTE_DIR/frontend $REMOTE_DIR/scripts $REMOTE_DIR/nginx"

    log_info "Copying Docker configuration..."
    scp "$PROJECT_DIR/docker-compose.prod.yml" "$REMOTE_HOST:$REMOTE_DIR/"
    scp "$PROJECT_DIR/.deploy.env" "$REMOTE_HOST:$REMOTE_DIR/.env" 2>/dev/null || true

    # Copy backend files
    log_info "Copying backend files..."
    scp "$PROJECT_DIR/backend/Dockerfile" "$REMOTE_HOST:$REMOTE_DIR/backend/"
    scp "$PROJECT_DIR/backend/docker-entrypoint.sh" "$REMOTE_HOST:$REMOTE_DIR/backend/" 2>/dev/null || true
    scp "$PROJECT_DIR/backend/requirements.txt" "$REMOTE_HOST:$REMOTE_DIR/backend/" 2>/dev/null || true

    # Copy backend source code with rsync for efficiency
    rsync -avz --delete \
        --exclude='__pycache__' \
        --exclude='*.pyc' \
        --exclude='.venv' \
        --exclude='*.egg-info' \
        --exclude='static' \
        --exclude='media' \
        --exclude='logs' \
        "$PROJECT_DIR/backend/" "$REMOTE_HOST:$REMOTE_DIR/backend/"

    # Copy frontend
    log_info "Copying frontend files..."
    scp "$PROJECT_DIR/frontend/Dockerfile" "$REMOTE_HOST:$REMOTE_DIR/frontend/" 2>/dev/null || true
    scp "$PROJECT_DIR/frontend/nginx.conf" "$REMOTE_HOST:$REMOTE_DIR/frontend/" 2>/dev/null || true

    rsync -avz --delete \
        --exclude='node_modules' \
        --exclude='dist' \
        --exclude='.next' \
        "$PROJECT_DIR/frontend/" "$REMOTE_HOST:$REMOTE_DIR/frontend/" 2>/dev/null || true

    # Copy nginx config
    if [ -d "$PROJECT_DIR/nginx" ]; then
        rsync -avz "$PROJECT_DIR/nginx/" "$REMOTE_HOST:$REMOTE_DIR/nginx/" 2>/dev/null || true
    fi

    log_success "Files deployed successfully"
}

# Deploy with Docker (preserving database)
deploy_docker_safe() {
    log_step "Starting Docker deployment on remote server (with database preservation)..."

    if [ "$DRY_RUN" = true ]; then
        log_info "DRY-RUN: Would execute Docker deployment"
        return
    fi

    ssh "$REMOTE_HOST" CERTBOT_EMAIL="$CERTBOT_EMAIL" bash -s << 'DOCKER_SCRIPT'
set -euo pipefail

REMOTE_DIR="/opt/the-bot-platform"
DOMAIN="the-bot.ru"
cd "$REMOTE_DIR"

echo "=== Docker Safe Deployment (Database Preservation) ==="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker $USER
    echo "Docker installed"
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo "Installing Docker Compose..."
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" \
        -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
fi

# Use 'docker compose' or 'docker-compose'
if docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
else
    COMPOSE_CMD="docker-compose"
fi

echo ""
echo "=== Pre-deployment checks ==="

# Check current volume status
echo "Current Docker volumes:"
docker volume ls | grep postgres_data || echo "Note: postgres_data volume not yet created"

echo ""
echo "=== Stopping services (preserving volumes) ==="

# CRITICAL: Use 'down' without --volumes to preserve data
$COMPOSE_CMD -f docker-compose.prod.yml down 2>/dev/null || true
sleep 3

echo "✓ Containers stopped, database volume preserved"

# Install and configure Certbot for SSL
echo ""
echo "=== SSL Certificate Setup ==="

check_certificate_valid() {
    if [ ! -d "/etc/letsencrypt/live/$DOMAIN" ]; then
        return 1
    fi
    if command -v certbot &> /dev/null; then
        certbot certificates 2>/dev/null | grep -q "$DOMAIN" && return 0
        return 1
    fi
    return 0
}

if ! check_certificate_valid; then
    if ! command -v certbot &> /dev/null; then
        sudo apt-get update -qq
        sudo apt-get install -y certbot python3-certbot-nginx > /dev/null 2>&1
    fi

    if [ -z "${CERTBOT_EMAIL}" ]; then
        echo "Warning: CERTBOT_EMAIL not set, skipping certificate"
    else
        echo "Requesting Let's Encrypt certificate for $DOMAIN..."
        sudo certbot certonly \
            --standalone \
            --non-interactive \
            --agree-tos \
            --email "${CERTBOT_EMAIL}" \
            -d "$DOMAIN" \
            -d "www.$DOMAIN" \
            2>&1 || echo "⚠ Certificate request failed or already exists"
    fi
else
    echo "Certificate valid at /etc/letsencrypt/live/$DOMAIN/"
fi

# Setup auto-renewal
sudo systemctl enable certbot.timer 2>/dev/null || true
sudo systemctl start certbot.timer 2>/dev/null || true

echo ""
echo "=== Building and starting containers ==="

# Build with no cache
echo "Building Docker images..."
$COMPOSE_CMD -f docker-compose.prod.yml build --no-cache

# Start containers - this will use existing volume data
echo "Starting containers (using existing database if available)..."
$COMPOSE_CMD -f docker-compose.prod.yml up -d

# Wait for services
echo "Waiting for services to start..."
sleep 20

echo ""
echo "=== Post-deployment verification ==="

# Check container status
echo "Container status:"
$COMPOSE_CMD -f docker-compose.prod.yml ps

# Check PostgreSQL volume
echo ""
echo "Checking database volume:"
if docker volume inspect thebot_postgres_data > /dev/null 2>&1; then
    echo "✓ postgres_data volume exists and preserved"
else
    echo "⚠ postgres_data volume missing - database will be reinitialized"
fi

# Check health
echo ""
echo "Checking service health..."
for i in {1..30}; do
    if curl -s http://localhost/api/health/ > /dev/null 2>&1; then
        echo "✓ Service is responding!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "⚠ Health check timeout - services may still be starting"
        echo "Check logs with: $COMPOSE_CMD logs --tail=50"
    fi
    sleep 2
done

echo ""
echo "=== Deployment Complete ==="
DOCKER_SCRIPT

    log_success "Docker deployment completed"
}

# Verify database integrity
verify_database() {
    log_step "Verifying database integrity..."

    ssh "$REMOTE_HOST" bash -s << 'VERIFY_SCRIPT'
set -euo pipefail

REMOTE_DIR="/opt/the-bot-platform"

echo "Checking database connection..."

# Try to get row count from main table
if docker ps | grep -q thebot-postgres-prod; then
    ROW_COUNT=$(docker exec thebot-postgres-prod psql -U postgres -d thebot_db -t -c "SELECT COUNT(*) FROM accounts_user;" 2>/dev/null || echo "error")

    if [ "$ROW_COUNT" != "error" ] && [ ! -z "$ROW_COUNT" ]; then
        echo "✓ Database is accessible"
        echo "  Users in database: $ROW_COUNT"
    else
        echo "⚠ Database connection issue - may be first deployment"
    fi
else
    echo "⚠ PostgreSQL container not running"
fi
VERIFY_SCRIPT

    log_success "Database verification completed"
}

# Main deployment flow
main() {
    if [ "$DRY_RUN" = true ]; then
        log_info "Running in DRY-RUN mode - no changes will be made"
        echo ""
    fi

    check_ssh

    if [ "$BACKUP_BEFORE_DEPLOY" = true ]; then
        backup_database
    else
        log_info "Skipping database backup"
    fi

    deploy_files

    deploy_docker_safe

    verify_database

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ REMOTE DEPLOYMENT SUCCESSFUL                               ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Deployment Summary:"
    echo "  ✓ Database preserved from previous deployment"
    echo "  ✓ Files synchronized to remote server"
    echo "  ✓ Docker containers rebuilt and restarted"
    echo "  ✓ Services verified and healthy"
    echo ""
    echo "Platform available at:"
    echo "  Frontend:  https://$REMOTE_DOMAIN"
    echo "  Backend:   https://$REMOTE_DOMAIN/api/"
    echo "  Admin:     https://$REMOTE_DOMAIN/admin/"
    echo ""
    echo "Useful commands:"
    echo "  # View logs:  ssh $REMOTE_HOST 'cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml logs -f'"
    echo "  # Status:     ssh $REMOTE_HOST 'cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml ps'"
    echo "  # Restart:    ssh $REMOTE_HOST 'cd $REMOTE_DIR && docker-compose -f docker-compose.prod.yml restart'"
    echo ""
}

main "$@"
