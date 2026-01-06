#!/bin/bash

# THE_BOT Platform - Production Startup Script
# ============================================================================
# Initializes and starts all production services
#
# Usage:
#   ./docker/start-production.sh              # Normal start
#   ./docker/start-production.sh --build      # Build images first
#   ./docker/start-production.sh --scale 3    # Scale to 3 workers
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
# Use .env.production.native first, then .env as fallback
ENV_FILE="$PROJECT_DIR/.env.production.native"
if [ ! -f "$ENV_FILE" ]; then
    ENV_FILE="$PROJECT_DIR/.env"
fi
WORKERS=1

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCTIONS
# ============================================================================

print_header() {
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}========================================${NC}"
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# ============================================================================
# CHECKS
# ============================================================================

check_environment() {
    print_header "Checking Environment"

    # Check if env file exists
    if [ ! -f "$ENV_FILE" ]; then
        print_error "Environment file not found!"
        echo "Please ensure .env.production.native or .env exists"
        exit 1
    fi
    print_info "Environment file found: $ENV_FILE"

    # Check if docker-compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_error "docker-compose.prod.yml not found!"
        exit 1
    fi
    print_info "docker-compose.prod.yml found"

    # Check Docker installation
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_info "Docker found: $(docker --version)"

    # Check Docker Compose installation
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_info "Docker Compose found: $(docker-compose --version)"

    # Check if Docker daemon is running
    if ! docker ps &> /dev/null; then
        print_error "Docker daemon is not running"
        exit 1
    fi
    print_success "Docker daemon is running"
}

check_ssl() {
    print_header "Checking SSL Certificates"

    SSL_DIR="$SCRIPT_DIR/ssl"

    if [ ! -f "$SSL_DIR/cert.pem" ] || [ ! -f "$SSL_DIR/key.pem" ]; then
        print_info "SSL certificates not found"
        read -p "Generate self-signed certificates? (y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            print_info "Generating SSL certificates..."
            chmod +x "$SCRIPT_DIR/generate-ssl.sh"
            "$SCRIPT_DIR/generate-ssl.sh"
            print_success "SSL certificates generated"
        else
            print_error "SSL certificates are required for HTTPS"
            exit 1
        fi
    else
        print_success "SSL certificates found"
    fi
}

# ============================================================================
# BUILD
# ============================================================================

build_images() {
    print_header "Building Docker Images"

    print_info "Building backend image..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build backend

    print_info "Building frontend image..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build frontend

    print_success "Images built successfully"
}

# ============================================================================
# STARTUP
# ============================================================================

start_services() {
    print_header "Starting Services"

    # Remove old containers if any
    print_info "Cleaning up old containers..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down 2>/dev/null || true

    # Start services
    print_info "Starting all services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d

    print_success "Services started"
}

scale_workers() {
    print_header "Scaling Celery Workers"

    print_info "Scaling to $WORKERS worker(s)..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --scale celery-worker="$WORKERS"

    print_success "Celery workers scaled to $WORKERS"
}

# ============================================================================
# INITIALIZATION
# ============================================================================

init_database() {
    print_header "Initializing Database"

    print_info "Waiting for PostgreSQL to be ready..."
    sleep 10

    print_info "Running migrations..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
        python manage.py migrate

    print_info "Creating superuser..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
        python manage.py createsuperuser --noinput \
        --username admin \
        --email admin@example.com || true

    print_info "Collecting static files..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
        python manage.py collectstatic --noinput

    print_success "Database initialized"
}

# ============================================================================
# HEALTH CHECKS
# ============================================================================

wait_for_service() {
    local container=$1
    local max_attempts=30
    local attempt=0

    print_info "Waiting for $container to be healthy..."

    while [ $attempt -lt $max_attempts ]; do
        if docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null | grep -q "healthy"; then
            return 0
        fi
        sleep 1
        ((attempt++))
    done

    return 1
}

health_checks() {
    print_header "Running Health Checks"

    local healthy=true

    # PostgreSQL
    print_info "Checking PostgreSQL..."
    if wait_for_service "thebot-postgres-prod"; then
        print_success "PostgreSQL is healthy"
    else
        print_error "PostgreSQL failed health check"
        healthy=false
    fi

    # Redis
    print_info "Checking Redis..."
    if wait_for_service "thebot-redis-prod"; then
        print_success "Redis is healthy"
    else
        print_error "Redis failed health check"
        healthy=false
    fi

    # Backend
    print_info "Checking Backend..."
    if wait_for_service "thebot-backend-prod"; then
        print_success "Backend is healthy"
    else
        print_error "Backend failed health check"
        healthy=false
    fi

    # Frontend
    print_info "Checking Frontend..."
    if wait_for_service "thebot-frontend-prod"; then
        print_success "Frontend is healthy"
    else
        print_error "Frontend failed health check"
        healthy=false
    fi

    if [ "$healthy" = false ]; then
        print_error "Some services failed health checks"
        echo "Run 'docker-compose logs' for more details"
        exit 1
    fi

    print_success "All health checks passed"
}

# ============================================================================
# SUMMARY
# ============================================================================

print_summary() {
    print_header "Startup Complete"

    local host="${ALLOWED_HOSTS:-localhost}"

    echo ""
    echo "Services are running:"
    echo "  - Frontend:    https://$host"
    echo "  - Backend API: https://$host/api"
    echo "  - Admin Panel: https://$host/admin"
    echo "  - WebSocket:   wss://$host/ws"
    echo ""
    echo "Database:"
    echo "  - PostgreSQL: localhost:5432"
    echo "  - Database: $(grep DB_NAME "$ENV_FILE" | cut -d= -f2)"
    echo ""
    echo "Cache:"
    echo "  - Redis: localhost:6379"
    echo ""
    echo "Useful commands:"
    echo "  - View logs:     docker-compose -f docker-compose.prod.yml logs -f"
    echo "  - Stop services: docker-compose -f docker-compose.prod.yml down"
    echo "  - Shell access:  docker-compose -f docker-compose.prod.yml exec backend bash"
    echo "  - Scale workers: docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3"
    echo ""
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    print_header "THE_BOT Production Startup"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --build)
                BUILD=true
                shift
                ;;
            --scale)
                WORKERS="$2"
                shift 2
                ;;
            --no-init)
                NO_INIT=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo ""
                echo "Options:"
                echo "  --build       Build Docker images before starting"
                echo "  --scale N     Scale to N Celery workers"
                echo "  --no-init     Skip database initialization"
                echo "  --help        Show this help message"
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Run checks
    check_environment
    check_ssl

    # Build images if requested
    if [ "$BUILD" = true ]; then
        build_images
    fi

    # Start services
    start_services
    health_checks

    # Initialize database if not skipped
    if [ "$NO_INIT" != true ]; then
        init_database
    fi

    # Scale workers
    if [ "$WORKERS" -gt 1 ]; then
        scale_workers
    fi

    # Print summary
    print_summary
}

# Run main function
main "$@"
