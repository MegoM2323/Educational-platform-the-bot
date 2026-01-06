#!/bin/bash

# THE BOT Platform - Local Development Server Startup Script
# Starts all services locally: Django, Celery, Celery Beat, Redis, PostgreSQL

set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get project root directory
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${BLUE}THE BOT Platform - Starting Local Development Servers${NC}"
echo ""

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python 3 found${NC}"

# Check if virtual environment exists
if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo -e "${BLUE}Creating virtual environment...${NC}"
    cd "$PROJECT_ROOT"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
source "$PROJECT_ROOT/venv/bin/activate"
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Check if pip dependencies are installed
if [ ! -f "$PROJECT_ROOT/venv/bin/pip" ]; then
    echo -e "${RED}Error: pip not found in virtual environment${NC}"
    exit 1
fi

# Install dependencies if needed
if ! python3 -c "import django" 2>/dev/null; then
    echo -e "${BLUE}Installing Python dependencies...${NC}"
    pip install --upgrade pip setuptools wheel

    if [ -f "$PROJECT_ROOT/backend/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/backend/requirements.txt"
    elif [ -f "$PROJECT_ROOT/requirements.txt" ]; then
        pip install -r "$PROJECT_ROOT/requirements.txt"
    else
        echo -e "${RED}Error: requirements.txt not found${NC}"
        exit 1
    fi
    echo -e "${GREEN}✓ Dependencies installed${NC}"
fi

# Create .env file if it doesn't exist
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${BLUE}Creating .env file with defaults...${NC}"
    cat > "$PROJECT_ROOT/.env" << 'EOF'
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/thebot_db
DB_NAME=thebot_db
DB_USER=postgres
DB_PASSWORD=postgres
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Django
DEBUG=True
SECRET_KEY=your-secret-key-change-in-production
ALLOWED_HOSTS=localhost,127.0.0.1

# Logging
LOG_LEVEL=INFO
EOF
    echo -e "${GREEN}✓ .env file created${NC}"
fi

# Check PostgreSQL
echo -e "${BLUE}Checking PostgreSQL...${NC}"
if ! command -v psql &> /dev/null; then
    echo -e "${YELLOW}Warning: psql not found. Make sure PostgreSQL is running on localhost:5432${NC}"
fi

# Try to create database if it doesn't exist
if command -v psql &> /dev/null; then
    PGPASSWORD=postgres psql -h localhost -U postgres -tc "SELECT 1 FROM pg_database WHERE datname = 'thebot_db'" | grep -q 1 || \
    PGPASSWORD=postgres psql -h localhost -U postgres -c "CREATE DATABASE thebot_db;" 2>/dev/null || true
fi

# Run migrations
echo -e "${BLUE}Running database migrations...${NC}"
cd "$PROJECT_ROOT/backend"
python manage.py migrate --noinput
echo -e "${GREEN}✓ Migrations completed${NC}"

# Collect static files (optional for development)
echo -e "${BLUE}Skipping static files collection (development mode)...${NC}"
echo -e "${GREEN}✓ Development environment ready${NC}"

# Create necessary directories
mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/media"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ Initialization completed!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Starting services...${NC}"
echo ""

# Kill any existing processes on the ports
pkill -f "python manage.py runserver" 2>/dev/null || true
pkill -f "celery worker" 2>/dev/null || true
pkill -f "celery beat" 2>/dev/null || true

# Start Django development server in background
echo -e "${BLUE}Starting Django backend (port 8000)...${NC}"
cd "$PROJECT_ROOT/backend"
python manage.py runserver 0.0.0.0:8000 > "$PROJECT_ROOT/logs/django.log" 2>&1 &
DJANGO_PID=$!
sleep 2
echo -e "${GREEN}✓ Django started (PID: $DJANGO_PID)${NC}"

# Start Celery worker in background (optional for development)
echo -e "${BLUE}Starting Celery worker...${NC}"
python -m celery -A core.celery_config worker --loglevel=info > "$PROJECT_ROOT/logs/celery_worker.log" 2>&1 &
CELERY_WORKER_PID=$!
sleep 2
if kill -0 $CELERY_WORKER_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Celery worker started (PID: $CELERY_WORKER_PID)${NC}"
else
    echo -e "${YELLOW}⚠ Celery worker not available (optional in development mode)${NC}"
fi

# Start Celery beat in background (optional for development)
echo -e "${BLUE}Starting Celery beat (scheduler)...${NC}"
python -m celery -A core.celery_config beat --loglevel=info > "$PROJECT_ROOT/logs/celery_beat.log" 2>&1 &
CELERY_BEAT_PID=$!
sleep 2
if kill -0 $CELERY_BEAT_PID 2>/dev/null; then
    echo -e "${GREEN}✓ Celery beat started (PID: $CELERY_BEAT_PID)${NC}"
else
    echo -e "${YELLOW}⚠ Celery beat not available (optional in development mode)${NC}"
fi

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✓ All services started successfully!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
echo ""
echo -e "${BLUE}Available at:${NC}"
echo -e "  Backend API: ${YELLOW}http://localhost:8000/api${NC}"
echo -e "  Admin Panel: ${YELLOW}http://localhost:8000/admin${NC}"
echo ""
echo -e "${BLUE}Service PIDs:${NC}"
echo -e "  Django:        $DJANGO_PID"
echo -e "  Celery Worker: $CELERY_WORKER_PID"
echo -e "  Celery Beat:   $CELERY_BEAT_PID"
echo ""
echo -e "${BLUE}Log files:${NC}"
echo -e "  Django:        ${YELLOW}$PROJECT_ROOT/logs/django.log${NC}"
echo -e "  Celery Worker: ${YELLOW}$PROJECT_ROOT/logs/celery_worker.log${NC}"
echo -e "  Celery Beat:   ${YELLOW}$PROJECT_ROOT/logs/celery_beat.log${NC}"
echo ""
echo -e "${BLUE}Useful commands:${NC}"
echo -e "  View Django logs:      ${YELLOW}tail -f $PROJECT_ROOT/logs/django.log${NC}"
echo -e "  View Celery logs:      ${YELLOW}tail -f $PROJECT_ROOT/logs/celery_worker.log${NC}"
echo -e "  Stop all services:     ${YELLOW}pkill -f 'python manage.py runserver' && pkill -f 'celery'${NC}"
echo ""
echo -e "${YELLOW}Press Enter to view live logs (Ctrl+C to stop viewing, services continue running)${NC}"
read

# Show live logs
tail -f "$PROJECT_ROOT/logs/django.log" "$PROJECT_ROOT/logs/celery_worker.log" "$PROJECT_ROOT/logs/celery_beat.log"
