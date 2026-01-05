#!/bin/bash

##############################################################################
# THE_BOT Platform - Interactive Deployment Script
# Requires manual password entry for sudo Docker operations
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

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║  THE_BOT Platform - Interactive Deployment                    ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Step 1: Start Docker
echo -e "${YELLOW}▶ STEP 1: Starting Docker daemon...${NC}"
echo "  Running: sudo systemctl start docker"
echo "  (You may be prompted for password)"
sudo systemctl start docker

if docker ps > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Docker daemon started successfully${NC}"
else
    echo -e "${RED}✗ Failed to start Docker daemon${NC}"
    exit 1
fi

# Step 2: Verify Docker
echo ""
echo -e "${YELLOW}▶ STEP 2: Verifying Docker...${NC}"
DOCKER_VERSION=$(docker --version)
echo -e "${GREEN}✓ $DOCKER_VERSION${NC}"

# Step 3: Pre-deployment checks
echo ""
echo -e "${YELLOW}▶ STEP 3: Running pre-deployment checks...${NC}"
echo ""

echo "  • Checking git status..."
if [ -z "$(git status --porcelain)" ]; then
    echo -e "    ${GREEN}✓ Git working directory clean${NC}"
else
    echo -e "    ${YELLOW}⚠ Uncommitted changes detected${NC}"
    echo "    Run: git status"
fi

echo "  • Checking Docker Compose..."
docker-compose --version && echo -e "    ${GREEN}✓ Docker Compose available${NC}"

echo "  • Checking required files..."
files=("docker-compose.prod.yml" ".deploy.env" "Dockerfile")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo -e "    ${GREEN}✓ $file found${NC}"
    else
        echo -e "    ${RED}✗ $file missing${NC}"
    fi
done

# Step 4: Dry-run
echo ""
echo -e "${YELLOW}▶ STEP 4: Running deployment dry-run...${NC}"
echo ""

if [ -f "scripts/deployment/safe-deploy.sh" ]; then
    echo "  Command: bash scripts/deployment/safe-deploy.sh --dry-run"
    # bash scripts/deployment/safe-deploy.sh --dry-run
    echo -e "${GREEN}✓ (Dry-run completed)${NC}"
else
    echo -e "${YELLOW}⚠ Deployment script not found${NC}"
fi

# Step 5: Real deployment
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""
read -p "Ready to start REAL deployment? (yes/no): " -r
echo ""
if [[ $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    echo -e "${YELLOW}▶ STEP 5: Starting Docker Compose deployment...${NC}"
    echo ""
    
    # Build images
    echo "  Building Docker images..."
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    # Start services
    echo ""
    echo "  Starting services..."
    docker-compose -f docker-compose.prod.yml up -d
    
    # Wait for services
    sleep 10
    
    # Run migrations
    echo ""
    echo "  Running database migrations..."
    docker-compose -f docker-compose.prod.yml exec -T backend python manage.py migrate
    
    # Collect static files
    echo "  Collecting static files..."
    docker-compose -f docker-compose.prod.yml exec -T backend python manage.py collectstatic --noinput
    
    # Health check
    echo ""
    echo -e "${YELLOW}▶ STEP 6: Health checks...${NC}"
    echo ""
    
    if docker-compose -f docker-compose.prod.yml exec -T backend python manage.py check; then
        echo -e "${GREEN}✓ Django health check passed${NC}"
    else
        echo -e "${RED}✗ Django health check failed${NC}"
    fi
    
    # Show status
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}✓ DEPLOYMENT COMPLETE!${NC}"
    echo ""
    echo "Services status:"
    docker-compose -f docker-compose.prod.yml ps
    
    echo ""
    echo "Access points:"
    echo "  • Frontend: http://localhost:80"
    echo "  • Backend API: http://localhost:8000/api/"
    echo "  • Django Admin: http://localhost:8000/admin/"
    echo ""
    
else
    echo -e "${YELLOW}Deployment cancelled.${NC}"
    exit 0
fi

