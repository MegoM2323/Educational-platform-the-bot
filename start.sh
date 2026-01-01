#!/bin/bash

# THE BOT Platform - Docker Development Server Startup Script
# Starts both backend (Django) and frontend (React) servers via Docker Compose

set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"

echo -e "${BLUE}THE BOT Platform - Starting Development Servers (Docker)${NC}"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Please install Docker: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Use 'docker compose' (v2) if available, otherwise 'docker-compose' (v1)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

# Check if docker-compose.yml exists
if [ ! -f "$COMPOSE_FILE" ]; then
    echo -e "${RED}Error: docker-compose.yml not found at $COMPOSE_FILE${NC}"
    exit 1
fi

# Stop and remove existing containers
echo -e "${BLUE}Cleaning up existing containers...${NC}"
cd "$PROJECT_ROOT"
$DOCKER_COMPOSE down 2>/dev/null || true

# Build images (if needed)
echo -e "${BLUE}Building Docker images...${NC}"
$DOCKER_COMPOSE build --no-cache

# Start services
echo -e "${GREEN}Starting services...${NC}"
$DOCKER_COMPOSE up -d

# Wait for services to be ready
echo -e "${BLUE}Waiting for services to be ready...${NC}"

# Wait for backend
TIMEOUT=60
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s http://localhost:8000/api/ > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is ready${NC}"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo -n "."
done
echo ""

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo -e "${YELLOW}Backend startup timeout, checking logs...${NC}"
    $DOCKER_COMPOSE logs backend | tail -20
fi

# Wait for frontend (if port 3000 is used, adjust if needed)
FRONTEND_PORT=${FRONTEND_PORT:-3000}
TIMEOUT=60
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        echo -e "${GREEN}Frontend is ready${NC}"
        break
    fi
    sleep 2
    ELAPSED=$((ELAPSED + 2))
    echo -n "."
done
echo ""

if [ $ELAPSED -ge $TIMEOUT ]; then
    echo -e "${YELLOW}Frontend startup timeout, checking logs...${NC}"
    $DOCKER_COMPOSE logs frontend | tail -20
fi

# Show status
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Available at:${NC}"
echo -e "  Backend API: ${YELLOW}http://localhost:8000/api${NC}"
echo -e "  Admin Panel: ${YELLOW}http://localhost:8000/admin${NC}"
echo -e "  Frontend:    ${YELLOW}http://localhost:$FRONTEND_PORT${NC}"
echo ""
echo -e "${BLUE}WebSocket:${NC}"
echo -e "  ws://localhost:8000/ws${NC}"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  View logs:     ${YELLOW}$DOCKER_COMPOSE logs -f${NC}"
echo -e "  Stop services: ${YELLOW}$DOCKER_COMPOSE down${NC}"
echo -e "  Restart:       ${YELLOW}$DOCKER_COMPOSE restart${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to view logs (services will continue running)${NC}"
echo -e "${YELLOW}To stop all services, run: $DOCKER_COMPOSE down${NC}"
echo ""

# Show logs
$DOCKER_COMPOSE logs -f
