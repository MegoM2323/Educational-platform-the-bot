#!/bin/bash

# THE_BOT Platform - Safe Deployment with Database Preservation
# Automatically deploys with sudo password caching
# Usage: ./deploy-with-db-safe.sh [--no-backup]

set -euo pipefail

# Configuration
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKUP_BEFORE_DEPLOY=true
SUDO_PASSWORD=""

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
        *)
            ;;
    esac
done

echo -e "${YELLOW}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${YELLOW}║  THE_BOT Platform - Safe Deployment with DB Preservation      ║${NC}"
echo -e "${YELLOW}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Backup before deploy: $BACKUP_BEFORE_DEPLOY"
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

# Create helper script for SUDO_ASKPASS
create_askpass_helper() {
    ASKPASS_SCRIPT="/tmp/sudoaskpass_$$.sh"
    cat > "$ASKPASS_SCRIPT" << 'EOF'
#!/bin/bash
echo "$SUDO_PASSWORD"
EOF
    chmod 755 "$ASKPASS_SCRIPT"
    echo "$ASKPASS_SCRIPT"
}

# Request sudo password once
request_sudo_password() {
    # Try to use password from stdin first (for automated deployment)
    if [ -t 0 ]; then
        # Interactive terminal - ask for password
        log_step "Requesting sudo access (password required for Docker)..."
        read -sp "Enter sudo password: " SUDO_PASSWORD
        echo ""
    else
        # Non-interactive - read from stdin
        log_step "Reading sudo password from stdin..."
        read SUDO_PASSWORD
    fi

    export SUDO_PASSWORD
    export SUDO_ASKPASS=$(create_askpass_helper)
    export SUDO_ASKPASS_FORCE=1

    log_success "Sudo password configured"

    # Cleanup on exit
    trap "rm -f $SUDO_ASKPASS 2>/dev/null || true" EXIT
}

# Run command with cached sudo
run_sudo() {
    sudo -A "$@"
}

# Pre-deployment checks
check_prerequisites() {
    log_step "Checking prerequisites..."

    # Check required files
    if [ ! -f "$PROJECT_DIR/docker-compose.prod.yml" ]; then
        log_error "docker-compose.prod.yml not found"
        exit 1
    fi
    log_success "docker-compose.prod.yml found"

    if [ ! -f "$PROJECT_DIR/.deploy.env" ]; then
        log_error ".deploy.env not found"
        exit 1
    fi
    log_success ".deploy.env found"

    # Check Docker installation
    if ! command -v docker &> /dev/null; then
        log_error "Docker not installed"
        exit 1
    fi
    log_success "Docker installed"

    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose not installed"
        exit 1
    fi
    log_success "Docker Compose installed"

    # Check if Docker daemon is running
    log_info "Checking if Docker daemon is running..."
    if ! docker ps &>/dev/null; then
        log_info "Docker daemon not running, starting it..."
        run_sudo systemctl start docker
        sleep 2

        if ! docker ps &>/dev/null; then
            log_error "Failed to start Docker daemon"
            exit 1
        fi
    fi
    log_success "Docker daemon is running"
}

# Create pre-deployment backup
backup_database() {
    log_step "Creating backup of database..."

    BACKUP_DIR="$PROJECT_DIR/backups"
    mkdir -p "$BACKUP_DIR"

    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    BACKUP_FILE="$BACKUP_DIR/db_backup_${TIMESTAMP}.sql"

    # Check if PostgreSQL container is running
    if docker ps 2>/dev/null | grep -q thebot-postgres-prod; then
        log_info "Dumping PostgreSQL database..."
        docker exec thebot-postgres-prod pg_dump \
            -U postgres \
            -d thebot_db \
            --no-owner \
            --no-privileges \
            > "$BACKUP_FILE" 2>/dev/null || {
            log_error "Database backup failed"
            exit 1
        }

        # Compress backup
        gzip -f "$BACKUP_FILE"
        log_success "Database backup created: $BACKUP_FILE.gz"

        # Keep only last 5 backups
        ls -t "$BACKUP_DIR"/db_backup_*.sql.gz 2>/dev/null | tail -n +6 | xargs -r rm
    else
        log_info "Database container not running yet (first deployment)"
    fi
}

# Deploy with Docker (preserving database)
deploy_docker_safe() {
    log_step "Starting Docker deployment (with database preservation)..."

    cd "$PROJECT_DIR"

    log_info "Copying environment file..."
    if [ ! -f ".env.prod" ]; then
        cp ".deploy.env" ".env.prod"
    fi

    log_info "Stopping services (preserving database volumes)..."
    # CRITICAL: Use 'down' without --volumes to preserve data
    docker-compose -f docker-compose.prod.yml down 2>/dev/null || true

    sleep 2
    log_success "Containers stopped, database volume preserved"

    log_info "Building Docker images (no cache)..."
    docker-compose -f docker-compose.prod.yml build --no-cache

    log_info "Starting containers (using existing database if available)..."
    docker-compose -f docker-compose.prod.yml up -d

    log_info "Waiting for services to start..."
    sleep 15

    log_success "Docker deployment completed"
}

# Run database migrations
run_migrations() {
    log_step "Running database migrations..."

    cd "$PROJECT_DIR"

    # Check if database is ready
    for i in {1..30}; do
        if docker-compose -f docker-compose.prod.yml exec -T backend \
            python manage.py dbshell -c "SELECT 1" &>/dev/null; then
            break
        fi
        if [ $i -eq 30 ]; then
            log_error "Database not ready after 60 seconds"
            exit 1
        fi
        sleep 2
    done

    log_info "Applying migrations..."
    docker-compose -f docker-compose.prod.yml exec -T backend \
        python manage.py migrate || {
        log_error "Migrations failed"
        exit 1
    }

    log_info "Collecting static files..."
    docker-compose -f docker-compose.prod.yml exec -T backend \
        python manage.py collectstatic --noinput --clear

    log_success "Migrations and static files completed"
}

# Post-deployment verification
verify_deployment() {
    log_step "Verifying deployment..."

    cd "$PROJECT_DIR"

    echo ""
    echo "Container status:"
    docker-compose -f docker-compose.prod.yml ps

    echo ""
    log_info "Running health checks..."

    # Check Django
    if docker-compose -f docker-compose.prod.yml exec -T backend \
        python manage.py check &>/dev/null; then
        log_success "Django health check passed"
    else
        log_error "Django health check failed"
        exit 1
    fi

    # Check API endpoint
    log_info "Testing API endpoint..."
    for i in {1..10}; do
        if curl -s http://localhost/api/health/ > /dev/null 2>&1; then
            log_success "API is responding"
            break
        fi
        if [ $i -eq 10 ]; then
            log_error "API endpoint not responding"
            exit 1
        fi
        sleep 2
    done

    # Check database volume
    if docker volume inspect thebot_postgres_data &>/dev/null; then
        log_success "Database volume exists and is healthy"
    else
        log_error "Database volume missing"
        exit 1
    fi

    log_success "All verifications passed"
}

# Main flow
main() {
    request_sudo_password

    check_prerequisites

    if [ "$BACKUP_BEFORE_DEPLOY" = true ]; then
        backup_database
    else
        log_info "Skipping database backup (--no-backup flag used)"
    fi

    deploy_docker_safe

    run_migrations

    verify_deployment

    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║  ✓ DEPLOYMENT SUCCESSFUL                                      ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo "Summary:"
    echo "  ✓ Database preserved from previous deployment"
    echo "  ✓ Containers rebuilt and restarted"
    echo "  ✓ Migrations applied successfully"
    echo "  ✓ Services verified and healthy"
    echo ""
    echo "Platform available at:"
    echo "  Frontend:  http://localhost"
    echo "  Backend:   http://localhost:8000/api/"
    echo "  Admin:     http://localhost:8000/admin/"
    echo ""
    echo "Next steps:"
    echo "  1. Configure domain DNS to point to server IP"
    echo "  2. Run: sudo certbot certonly -w /var/www/certbot -d the-bot.ru"
    echo "  3. Configure Nginx for SSL"
    echo ""
}

main "$@"
