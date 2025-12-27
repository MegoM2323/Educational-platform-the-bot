#!/bin/bash

# THE BOT Platform - Production Server Startup Script
# Starts backend and frontend with production settings
# Requires: ENVIRONMENT=production in .env

set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend"

echo -e "${BLUE}THE BOT Platform - Production Server Startup${NC}"
echo ""

# Check .env file
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please create .env file from .env.example"
    exit 1
fi

# Load environment variables
export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)

# Verify production environment
if [ "$ENVIRONMENT" != "production" ]; then
    echo -e "${RED}Error: ENVIRONMENT must be set to 'production' in .env${NC}"
    echo "Current value: $ENVIRONMENT"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/.venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Creating...${NC}"
    cd "$PROJECT_ROOT"
    python -m venv .venv
fi

# Activate virtual environment
echo -e "${BLUE}Activating virtual environment...${NC}"
source "$PROJECT_ROOT/.venv/bin/activate"

# Install/update dependencies
echo -e "${BLUE}Installing backend dependencies...${NC}"
cd "$BACKEND_DIR"
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo -e "${BLUE}Building frontend...${NC}"
cd "$FRONTEND_DIR"
npm ci --silent > /dev/null 2>&1 || npm install --silent > /dev/null 2>&1
npm run build

# Kill any existing processes on the ports
echo -e "${BLUE}Cleaning up old processes...${NC}"
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
sleep 1

# Run migrations
echo -e "${BLUE}Running database migrations...${NC}"
cd "$BACKEND_DIR"
python manage.py migrate --noinput

# Collect static files
echo -e "${BLUE}Collecting static files...${NC}"
python manage.py collectstatic --noinput --clear

# Start backend server with gunicorn
echo -e "${GREEN}Starting Django backend server (port 8000)...${NC}"
cd "$BACKEND_DIR"

# Use gunicorn for production
gunicorn \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    config.asgi:application > "$PROJECT_ROOT/backend.log" 2>&1 &

BACKEND_PID=$!
echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"

# Wait for backend to be ready
echo -e "${BLUE}Waiting for backend to be ready...${NC}"
TIMEOUT=30
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s http://localhost:8000/api/health/ > /dev/null 2>&1; then
        echo -e "${GREEN}Backend is ready${NC}"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

if [ $ELAPSED -eq $TIMEOUT ]; then
    echo -e "${YELLOW}Backend startup timeout, continuing...${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Production server started successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Backend running at:${NC}"
echo -e "  API: http://localhost:8000/api"
echo -e "  Admin: http://localhost:8000/admin"
echo ""
echo -e "${BLUE}Frontend built:${NC}"
echo -e "  Location: $FRONTEND_DIR/dist"
echo ""
echo -e "${BLUE}Log file:${NC}"
echo -e "  $PROJECT_ROOT/backend.log"
echo ""
echo -e "${YELLOW}Setup nginx to serve frontend/dist as static files${NC}"
echo ""

# Wait for interrupt
wait $BACKEND_PID 2>/dev/null || true
