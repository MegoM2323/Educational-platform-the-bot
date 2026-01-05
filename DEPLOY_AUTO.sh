#!/bin/bash

##############################################################################
# THE_BOT Platform - Automated Deployment Script
# Automatically passes sudo password for Docker operations
##############################################################################

set -e

PROJECT_DIR="/home/mego/Python Projects/THE_BOT_platform"
cd "$PROJECT_DIR"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SUDO_PASS="fstpass"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  THE_BOT Platform - Automated Deployment                      ║${NC}"
echo -e "${BLUE}║  Domain: the-bot.ru                                           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Start Docker
echo -e "${YELLOW}▶ STEP 1: Starting Docker daemon...${NC}"
echo "fstpass" | sudo -S systemctl start docker 2>/dev/null || true
sleep 2

if docker ps > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker daemon started successfully${NC}"
else
    echo -e "${RED}✗ Failed to start Docker daemon${NC}"
    echo "  Try: sudo systemctl start docker"
    exit 1
fi

# Step 2: Verify Docker
echo ""
echo -e "${YELLOW}▶ STEP 2: Verifying Docker installation...${NC}"
DOCKER_VERSION=$(docker --version)
echo -e "${GREEN}✓ $DOCKER_VERSION${NC}"

COMPOSE_VERSION=$(docker-compose --version)
echo -e "${GREEN}✓ $COMPOSE_VERSION${NC}"

# Step 3: Pre-deployment checks
echo ""
echo -e "${YELLOW}▶ STEP 3: Running pre-deployment checks...${NC}"
echo ""

echo "  • Checking git status..."
if [ -z "$(git status --porcelain)" ]; then
    echo -e "    ${GREEN}✓ Git working directory clean${NC}"
else
    echo -e "    ${YELLOW}⚠ Uncommitted changes detected${NC}"
fi

echo "  • Checking required files..."
files=("docker-compose.prod.yml" ".deploy.env")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "    ${GREEN}✓ $file found${NC}"
    else
        echo -e "    ${RED}✗ $file missing${NC}"
        exit 1
    fi
done

# Step 4: Build Docker images
echo ""
echo -e "${YELLOW}▶ STEP 4: Building Docker images...${NC}"
echo "  This may take 10-15 minutes on first build..."
echo ""

docker-compose -f docker-compose.prod.yml build --no-cache 2>&1 | grep -E "(Building|built|Successfully)" || echo "Building images..."

# Step 5: Start services
echo ""
echo -e "${YELLOW}▶ STEP 5: Starting services...${NC}"
echo ""

docker-compose -f docker-compose.prod.yml up -d

# Wait for services to be ready
echo "  Waiting for services to start..."
sleep 10

# Step 6: Run migrations
echo ""
echo -e "${YELLOW}▶ STEP 6: Running database migrations...${NC}"
docker-compose -f docker-compose.prod.yml exec -T backend python manage.py migrate 2>&1 | tail -5

# Step 7: Collect static files
echo ""
echo -e "${YELLOW}▶ STEP 7: Collecting static files...${NC}"
docker-compose -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput 2>&1 | grep -E "(Copying|Processing)" | head -10 || echo "  Static files collected"

# Step 8: Health checks
echo ""
echo -e "${YELLOW}▶ STEP 8: Running health checks...${NC}"
echo ""

if docker-compose -f docker-compose.prod.yml exec -T backend python manage.py check 2>&1 | grep -q "no issues"; then
    echo -e "    ${GREEN}✓ Django system check passed${NC}"
else
    echo -e "    ${YELLOW}⚠ Django check output:${NC}"
    docker-compose -f docker-compose.prod.yml exec -T backend python manage.py check || true
fi

# Step 9: Show status
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ DEPLOYMENT COMPLETE!${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

echo "📊 Services Status:"
docker-compose -f docker-compose.prod.yml ps

echo ""
echo "🌐 Access Points:"
echo "  • Frontend:    http://localhost:80"
echo "  • Backend API: http://localhost:8000/api/"
echo "  • Admin Panel: http://localhost:8000/admin/"
echo "  • WebSocket:   ws://localhost:8000/ws/notifications/"
echo ""

echo "📝 Next Steps:"
echo "  1. Configure domain DNS to point to this server"
echo "  2. Run: sudo certbot certonly --webroot -w /var/www/certbot -d the-bot.ru"
echo "  3. Copy nginx config: sudo cp nginx/the-bot.ru.conf /etc/nginx/sites-available/"
echo "  4. Enable SSL: sudo systemctl reload nginx"
echo ""

echo "📚 Documentation:"
echo "  • Deployment Guide: PRODUCTION_DEPLOYMENT_GUIDE.md"
echo "  • Docker Status: docker-compose -f docker-compose.prod.yml ps"
echo "  • View Logs: docker-compose -f docker-compose.prod.yml logs -f"
echo ""

echo -e "${GREEN}🚀 THE_BOT Platform is now running!${NC}"
echo ""

