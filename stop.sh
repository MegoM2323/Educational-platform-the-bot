#!/bin/bash

# ============================================================================
# Stop All Services: Django/Daphne, React, Celery Worker & Beat
# ============================================================================

# ANSI color codes (matching start.sh)
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo -e "${BLUE}======================================================================"
echo -e "🛑 THE BOT Platform - Stopping All Services"
echo -e "======================================================================${NC}"
echo ""

# Function to kill processes on port
kill_port_processes() {
    local port=$1
    local service_name=$2

    echo -e "${YELLOW}🔍 Checking port $port ($service_name)...${NC}"

    # Find processes on port
    local pids=$(lsof -ti:$port 2>/dev/null)

    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}⚠️  Found processes on port $port: $pids${NC}"
        echo -e "${RED}🛑 Killing processes on port $port...${NC}"

        # Kill processes
        for pid in $pids; do
            echo "   Killing process $pid..."
            kill -9 $pid 2>/dev/null || true
        done

        # Wait a moment
        sleep 1

        # Verify processes are killed
        local remaining_pids=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$remaining_pids" ]; then
            echo -e "${RED}❌ Failed to kill all processes on port $port${NC}"
            echo "   Remaining processes: $remaining_pids"
            return 1
        else
            echo -e "${GREEN}✅ Port $port freed${NC}"
            return 0
        fi
    else
        echo -e "${GREEN}✅ Port $port is not in use${NC}"
        return 0
    fi
}

# Function to kill celery processes by pattern
kill_celery_processes() {
    local pattern=$1
    local service_name=$2

    echo -e "${YELLOW}🔍 Looking for $service_name processes...${NC}"

    local pids=$(pgrep -f "$pattern" 2>/dev/null)

    if [ ! -z "$pids" ]; then
        echo -e "${YELLOW}⚠️  Found $service_name processes: $pids${NC}"
        echo -e "${RED}🛑 Killing $service_name...${NC}"

        for pid in $pids; do
            echo "   Killing process $pid..."
            kill -9 $pid 2>/dev/null || true
        done

        sleep 1

        # Verify processes are killed
        local remaining_pids=$(pgrep -f "$pattern" 2>/dev/null)
        if [ ! -z "$remaining_pids" ]; then
            echo -e "${RED}❌ Failed to kill all $service_name processes${NC}"
            echo "   Remaining processes: $remaining_pids"
            return 1
        else
            echo -e "${GREEN}✅ $service_name stopped${NC}"
            return 0
        fi
    else
        echo -e "${GREEN}✅ No $service_name processes found${NC}"
        return 0
    fi
}

# Stop services in order
echo -e "${BLUE}========== Stopping Services ==========${NC}"
echo ""

# Stop Django/Daphne on port 8000
kill_port_processes 8000 "Django Backend (Daphne)"
DJANGO_SUCCESS=$?
echo ""

# Stop React dev server on port 8080
kill_port_processes 8080 "React Frontend"
FRONTEND_SUCCESS=$?
echo ""

# Stop Celery worker
kill_celery_processes "celery worker" "Celery Worker"
CELERY_WORKER_SUCCESS=$?
echo ""

# Stop Celery beat
kill_celery_processes "celery beat" "Celery Beat"
CELERY_BEAT_SUCCESS=$?
echo ""

# Additional cleanup: kill any remaining celery processes
pkill -9 -f "celery" 2>/dev/null || true
sleep 1

# Summary
echo -e "${BLUE}========== Shutdown Summary ==========${NC}"
echo ""

if [ $DJANGO_SUCCESS -eq 0 ]; then
    echo -e "🌐 Django Backend: ${GREEN}✅ Stopped${NC}"
else
    echo -e "🌐 Django Backend: ${RED}❌ Failed${NC}"
fi

if [ $FRONTEND_SUCCESS -eq 0 ]; then
    echo -e "🎨 React Frontend: ${GREEN}✅ Stopped${NC}"
else
    echo -e "🎨 React Frontend: ${RED}❌ Failed${NC}"
fi

if [ $CELERY_WORKER_SUCCESS -eq 0 ]; then
    echo -e "⚙️  Celery Worker: ${GREEN}✅ Stopped${NC}"
else
    echo -e "⚙️  Celery Worker: ${RED}❌ Failed${NC}"
fi

if [ $CELERY_BEAT_SUCCESS -eq 0 ]; then
    echo -e "⏰ Celery Beat: ${GREEN}✅ Stopped${NC}"
else
    echo -e "⏰ Celery Beat: ${RED}❌ Failed${NC}"
fi

echo ""
echo -e "${GREEN}======================================================================"
echo -e "✅ All services stopped successfully!"
echo -e "======================================================================${NC}"
echo ""
echo -e "${YELLOW}To start services again, run: ./start.sh${NC}"
echo ""
