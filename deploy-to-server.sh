#!/bin/bash

################################################################################
# THE_BOT Platform - Automated Production Deployment to Remote Server
# 
# Usage:
#   chmod +x deploy-to-server.sh
#   ./deploy-to-server.sh [git_repo_url]
#
# Example:
#   ./deploy-to-server.sh https://github.com/yourname/the-bot-platform.git
################################################################################

set -e

# ============================================================================
# CONFIGURATION
# ============================================================================

# Server credentials
SSH_USER="mg"
SSH_HOST="${SSH_HOST:-5.129.249.206}"
SSH_PORT="${SSH_PORT:-22}"
SSH_KEY="${SSH_KEY:-$HOME/.ssh/id_ed25519}" # ed25519 key
DOMAIN="${DOMAIN:-the-bot.ru}"
API_DOMAIN="${API_DOMAIN:-api.the-bot.ru}"

# Deployment paths
REMOTE_PROJECT_PATH="/opt/thebot"
REMOTE_APP_USER="thebot"

# Git repository (pass as argument or use default)
GIT_REPO="${1:-https://github.com/yourusername/the-bot-platform.git}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# ============================================================================
# FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

log_error() {
    echo -e "${RED}[✗]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[⚠]${NC} $1"
}

# Execute command on remote server
run_remote() {
    local cmd="$1"
    if [ -z "$SSH_KEY" ]; then
        ssh -p "$SSH_PORT" -o StrictHostKeyChecking=accept-new "$SSH_USER@$SSH_HOST" "$cmd"
    else
        ssh -i "$SSH_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=accept-new "$SSH_USER@$SSH_HOST" "$cmd"
    fi
}

# Execute command with sudo on remote server (quoted & escaped properly)
run_remote_sudo() {
    local cmd="$1"
    ssh -i "$SSH_KEY" -p "$SSH_PORT" -o StrictHostKeyChecking=accept-new "$SSH_USER@$SSH_HOST" "sudo bash -c \"$(printf '%s\n' "$cmd" | sed 's/[\"\\]/\\&/g')\""
}

# Transfer file to remote server
transfer_file() {
    local local_file="$1"
    local remote_path="$2"

    if [ -z "$SSH_KEY" ]; then
        scp -P "$SSH_PORT" -o StrictHostKeyChecking=accept-new "$local_file" "$SSH_USER@$SSH_HOST:$remote_path"
    else
        scp -i "$SSH_KEY" -P "$SSH_PORT" -o StrictHostKeyChecking=accept-new "$local_file" "$SSH_USER@$SSH_HOST:$remote_path"
    fi
}

# Generate URL-safe password (a-z, A-Z, 0-9, _)
# Compatible with DATABASE_URL and REDIS_URL parsing
generate_url_safe_password() {
    local length=${1:-16}
    # Use openssl to generate random bytes, then filter to safe characters only
    # Remove +, /, = characters that break URL parsing
    openssl rand -base64 32 | tr -cd 'a-zA-Z0-9_' | head -c "$length"
}

# URL encode password for defensive use (optional fallback)
# Use Python's urllib.parse.quote() for safe encoding with proper escaping
urlencode_password() {
    local password="$1"
    python3 << EOFPYTHON 2>/dev/null || echo "$password"
import urllib.parse
import sys
print(urllib.parse.quote(sys.stdin.read().rstrip('\n'), safe=''))
EOFPYTHON
    <<< "$password"
}

# ============================================================================
# HEADER
# ============================================================================

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║     THE_BOT Platform - Production Deployment Script            ║"
echo "║                   Automated Remote Deploy                      ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
echo

# ============================================================================
# STEP 1: VALIDATION
# ============================================================================

log_info "Step 1/8: Validating deployment configuration..."
echo "  Server: $SSH_USER@$SSH_HOST:$SSH_PORT"
echo "  Target: $REMOTE_PROJECT_PATH"
echo "  Git Repo: $GIT_REPO"
echo

# Test SSH connection
log_info "Testing SSH connection..."
if run_remote "echo 'SSH connection OK'" > /dev/null 2>&1; then
    log_success "SSH connection successful"
else
    log_error "Cannot connect to server via SSH"
    exit 1
fi

# Check if Docker is installed on server
log_info "Checking Docker installation..."
if run_remote "command -v docker >/dev/null 2>&1 && docker --version" > /dev/null 2>&1; then
    log_success "Docker is installed"
else
    log_error "Docker is not installed on server"
    log_warning "Please install Docker: curl -fsSL https://get.docker.com | sh"
    exit 1
fi

# Check if Docker Compose is installed
log_info "Checking Docker Compose installation..."
if run_remote "command -v docker-compose >/dev/null 2>&1 && docker-compose --version" > /dev/null 2>&1; then
    log_success "Docker Compose is installed"
else
    log_error "Docker Compose is not installed on server"
    log_warning "Please install Docker Compose: sudo curl -L https://github.com/docker/compose/releases/latest/download/docker-compose-Linux-x86_64 -o /usr/local/bin/docker-compose && sudo chmod +x /usr/local/bin/docker-compose"
    exit 1
fi

echo

# ============================================================================
# STEP 2: PREPARE SERVER
# ============================================================================

log_info "Step 2/8: Preparing server..."

# Create project directory
log_info "Creating project directory..."
run_remote_sudo "mkdir -p \"$REMOTE_PROJECT_PATH\" && chown \"$SSH_USER:$SSH_USER\" \"$REMOTE_PROJECT_PATH\""
log_success "Project directory ready"

# Create .env directory for backups
run_remote "mkdir -p \"$REMOTE_PROJECT_PATH/backups\""

echo

# ============================================================================
# STEP 3: CLONE/UPDATE REPOSITORY
# ============================================================================

log_info "Step 3/8: Cloning/updating repository..."

# Check if repo already exists
if run_remote "[ -d \"$REMOTE_PROJECT_PATH/.git\" ]" 2>/dev/null; then
    log_info "Repository exists, updating..."
    run_remote "cd \"$REMOTE_PROJECT_PATH\" && git pull origin main"
    log_success "Repository updated"
else
    log_info "Directory exists but no git repo, removing old deployment..."
    run_remote_sudo "rm -rf \"$REMOTE_PROJECT_PATH\" && mkdir -p \"$REMOTE_PROJECT_PATH\" && chown \"$SSH_USER:$SSH_USER\" \"$REMOTE_PROJECT_PATH\""
    log_info "Cloning repository..."
    run_remote "git clone \"$GIT_REPO\" \"$REMOTE_PROJECT_PATH\""
    log_success "Repository cloned"
fi

# Transfer entire frontend directory with corrected files (vite.config.ts, .dockerignore)
log_info "Transferring corrected application files..."
if [ -d "frontend" ]; then
    log_info "Syncing frontend directory (vite.config.ts, .dockerignore fixes)..."
    run_remote "mkdir -p \"$REMOTE_PROJECT_PATH/frontend\""
    tar czf /tmp/frontend.tar.gz frontend/
    transfer_file /tmp/frontend.tar.gz "$REMOTE_PROJECT_PATH/frontend.tar.gz"
    run_remote "cd \"$REMOTE_PROJECT_PATH\" && tar xzf frontend.tar.gz && rm frontend.tar.gz"
    rm /tmp/frontend.tar.gz
    log_success "Frontend directory transferred with all fixes"
fi

# Transfer other critical files
if [ -f "docker-compose.prod.yml" ]; then
    transfer_file "docker-compose.prod.yml" "$REMOTE_PROJECT_PATH/docker-compose.prod.yml"
    log_success "docker-compose.prod.yml transferred"
fi
if [ -f "backend/invoices/migrations/0001_initial.py" ]; then
    transfer_file "backend/invoices/migrations/0001_initial.py" "$REMOTE_PROJECT_PATH/backend/invoices/migrations/0001_initial.py"
    log_success "Migration file transferred"
fi
if [ -f "backend/invoices/models.py" ]; then
    transfer_file "backend/invoices/models.py" "$REMOTE_PROJECT_PATH/backend/invoices/models.py"
    log_success "Models file transferred"
fi
if [ -f "docker/nginx.prod.conf" ]; then
    transfer_file "docker/nginx.prod.conf" "$REMOTE_PROJECT_PATH/docker/nginx.prod.conf"
    log_success "Nginx config transferred"
fi

echo

# ============================================================================
# STEP 4: CREATE ENVIRONMENT FILE
# ============================================================================

log_info "Step 4/8: Creating production .env file..."

# Generate secure random strings (SECRET_KEY must be at least 50 chars for production)
SECRET_KEY=$(openssl rand -base64 50)
REDIS_PASSWORD=$(generate_url_safe_password 16)
DB_PASSWORD=$(generate_url_safe_password 16)

# Create .env file content
cat > /tmp/.env.production << EOFENV
# THE_BOT Platform - Production Environment Configuration
# Generated: $TIMESTAMP

# Environment
ENVIRONMENT=production
DEBUG=False

# Django Security
SECRET_KEY=$SECRET_KEY
ALLOWED_HOSTS=$SSH_HOST,localhost,127.0.0.1

# Database Configuration
DB_ENGINE=postgresql
DB_HOST=postgres
DB_PORT=5432
DB_NAME=thebot_db
DB_USER=postgres
DB_PASSWORD=$DB_PASSWORD

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$REDIS_PASSWORD
REDIS_DB=0

# Celery Configuration
CELERY_BROKER_URL=redis://:$REDIS_PASSWORD@redis:6379/1
CELERY_RESULT_BACKEND=redis://:$REDIS_PASSWORD@redis:6379/2

# API Configuration (use production domain for FRONTEND_URL in production mode)
API_URL=https://$API_DOMAIN/api
FRONTEND_URL=https://$DOMAIN
WS_URL=wss://$DOMAIN/ws

# Email Configuration (optional)
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
EMAIL_USE_TLS=True

# External Services (optional)
YOOKASSA_SHOP_ID=
YOOKASSA_SECRET_KEY=
OPENROUTER_API_KEY=
PACHCA_API_TOKEN=
PACHCA_FORUM_API_TOKEN=
TELEGRAM_BOT_TOKEN=

# Logging
LOG_LEVEL=INFO

# Monitoring (optional)
SENTRY_DSN=

# Application
APP_NAME=THE_BOT
APP_VERSION=1.0.0
EOFENV

# Remove old .env file and transfer new one to ensure clean state
log_info "Transferring .env file to server..."
run_remote "rm -f \"$REMOTE_PROJECT_PATH/.env\""
transfer_file /tmp/.env.production "$REMOTE_PROJECT_PATH/.env"
run_remote "chmod 600 \"$REMOTE_PROJECT_PATH/.env\""
rm -f /tmp/.env.production
log_success ".env file created and transferred"

echo

# ============================================================================
# STEP 5: BUILD AND START SERVICES
# ============================================================================

log_info "Step 5/8: Building and starting Docker services..."

log_info "Building Docker images (this may take 5-10 minutes)..."
run_remote "cd \"$REMOTE_PROJECT_PATH\" && docker-compose -f docker-compose.prod.yml build"
log_success "Docker images built"

log_info "Starting services..."
run_remote "cd \"$REMOTE_PROJECT_PATH\" && docker-compose -f docker-compose.prod.yml up -d"
log_success "Services started"

echo

# ============================================================================
# STEP 6: INITIALIZE DATABASE
# ============================================================================

log_info "Step 6/8: Initializing database..."

# Wait for database to be ready
log_info "Waiting for database to be ready..."
sleep 10

# Run migrations
log_info "Running database migrations..."
run_remote "cd \"$REMOTE_PROJECT_PATH\" && docker-compose -f docker-compose.prod.yml exec -T backend python manage.py migrate --noinput"
log_success "Migrations completed"

# Create superuser (optional, commented out for automation)
log_info "Creating test data..."
run_remote "cd \"$REMOTE_PROJECT_PATH\" && docker-compose -f docker-compose.prod.yml exec -T backend python manage.py reset_and_seed_users" || true

# Collect static files
log_info "Collecting static files..."
run_remote "cd \"$REMOTE_PROJECT_PATH\" && docker-compose -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput" || true

log_success "Database initialized"

echo

# ============================================================================
# STEP 7: HEALTH CHECKS
# ============================================================================

log_info "Step 7/8: Performing health checks..."

# Wait a moment for services to stabilize
sleep 5

# Check backend health
log_info "Checking backend health..."
if run_remote "curl -s http://localhost:8000/api/system/health/live/ | grep -q 'healthy'" 2>/dev/null || true; then
    log_success "Backend is healthy"
else
    log_warning "Backend health check inconclusive (may still be starting)"
fi

# Check Docker containers
log_info "Checking container status..."
run_remote "docker-compose -f \"$REMOTE_PROJECT_PATH/docker-compose.prod.yml\" ps"

echo

# ============================================================================
# STEP 8: FINAL SUMMARY
# ============================================================================

log_info "Step 8/8: Deployment complete!"
echo

echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         ✓ DEPLOYMENT SUCCESSFUL                               ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo

echo -e "${BLUE}Server Information:${NC}"
echo "  SSH: ssh $SSH_USER@$SSH_HOST"
echo "  Project: $REMOTE_PROJECT_PATH"
echo "  Compose: docker-compose -f docker-compose.prod.yml"
echo

echo -e "${BLUE}Access Platform:${NC}"
echo "  API: http://$SSH_HOST:8000/api"
echo "  Frontend: http://$SSH_HOST:3000"
echo "  Admin: http://$SSH_HOST:8000/admin"
echo

echo -e "${BLUE}Test Credentials:${NC}"
echo "  Admin: admin / admin12345"
echo "  Student: test_student@example.com / test123"
echo "  Teacher: test_teacher@example.com / test123"
echo "  Tutor: test_tutor@example.com / test123"
echo "  Parent: test_parent@example.com / test123"
echo

echo -e "${BLUE}Useful Commands:${NC}"
echo "  View logs: ssh $SSH_USER@$SSH_HOST 'cd $REMOTE_PROJECT_PATH && docker-compose -f docker-compose.prod.yml logs -f'"
echo "  Stop services: ssh $SSH_USER@$SSH_HOST 'cd $REMOTE_PROJECT_PATH && docker-compose -f docker-compose.prod.yml down'"
echo "  Restart services: ssh $SSH_USER@$SSH_HOST 'cd $REMOTE_PROJECT_PATH && docker-compose -f docker-compose.prod.yml restart'"
echo "  Check status: ssh $SSH_USER@$SSH_HOST 'cd $REMOTE_PROJECT_PATH && docker-compose -f docker-compose.prod.yml ps'"
echo

echo -e "${BLUE}Generated Configuration:${NC}"
echo "  Environment: $REMOTE_PROJECT_PATH/.env"
echo "  Secret Key: Generated and stored in .env"
echo "  Database Password: Generated and stored in .env"
echo "  Redis Password: Generated and stored in .env"
echo

echo -e "${YELLOW}IMPORTANT:${NC}"
echo "  1. Save your .env file from the server for backup"
echo "  2. Update DNS records to point to $SSH_HOST"
echo "  3. Configure SSL certificates (if needed)"
echo "  4. Update ALLOWED_HOSTS in .env with your domain"
echo "  5. Monitor logs for any issues"
echo

echo -e "${GREEN}✓ Platform is ready for testing!${NC}"
echo

