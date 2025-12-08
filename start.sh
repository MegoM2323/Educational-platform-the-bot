#!/bin/bash

# THE BOT Platform - Development Server Startup Script
# Starts both backend (Django) and frontend (React) servers for local development

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

echo -e "${BLUE}THE BOT Platform - Starting Development Servers${NC}"
echo ""

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
echo -e "${BLUE}Checking backend dependencies...${NC}"
cd "$BACKEND_DIR"
pip install -q --upgrade pip
pip install -q -r requirements.txt

echo -e "${BLUE}Checking frontend dependencies...${NC}"
cd "$FRONTEND_DIR"
npm ci --silent > /dev/null 2>&1 || npm install --silent > /dev/null 2>&1

# Kill any existing processes on the ports
echo -e "${BLUE}Cleaning up old processes...${NC}"
lsof -ti :8000 | xargs kill -9 2>/dev/null || true
lsof -ti :8080 | xargs kill -9 2>/dev/null || true
sleep 1

# Start backend server
echo -e "${GREEN}Starting Django backend server (port 8000)...${NC}"
cd "$BACKEND_DIR"
python manage.py migrate --noinput > /dev/null 2>&1 || true
daphne -b 0.0.0.0 -p 8000 config.asgi:application > "$PROJECT_ROOT/backend.log" 2>&1 &
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
    echo -e "${YELLOW}Backend startup may be slow, continuing...${NC}"
fi

# Start frontend server
echo -e "${GREEN}Starting React frontend server (port 8080)...${NC}"
cd "$FRONTEND_DIR"
npm run dev > "$PROJECT_ROOT/frontend.log" 2>&1 &
FRONTEND_PID=$!
echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"

# Wait for frontend to be ready
echo -e "${BLUE}Waiting for frontend to be ready...${NC}"
TIMEOUT=60
ELAPSED=0
while [ $ELAPSED -lt $TIMEOUT ]; do
    if curl -s http://localhost:8080 > /dev/null 2>&1; then
        echo -e "${GREEN}Frontend is ready${NC}"
        break
    fi
    sleep 1
    ELAPSED=$((ELAPSED + 1))
done

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ All servers started successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Available at:${NC}"
echo -e "  Backend API: ${YELLOW}http://localhost:8000/api${NC}"
echo -e "  Admin Panel: ${YELLOW}http://localhost:8000/admin${NC}"
echo -e "  Frontend:    ${YELLOW}http://localhost:8080${NC}"
echo ""
echo -e "${BLUE}WebSocket:${NC}"
echo -e "  ws://localhost:8000/ws${NC}"
echo ""
echo -e "${BLUE}Log files:${NC}"
echo -e "  Backend:  $PROJECT_ROOT/backend.log"
echo -e "  Frontend: $PROJECT_ROOT/frontend.log"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop all servers${NC}"
echo ""

# Wait for interrupt
wait $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
