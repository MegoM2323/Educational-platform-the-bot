#!/bin/bash

# THE BOT Platform - Redis Health Check and Startup Script
# Usage: ./check_redis.sh

set -e

echo "================================================"
echo "THE BOT Platform - Redis Health Check"
echo "================================================"
echo ""

# Check if Redis is installed
if ! command -v redis-cli &> /dev/null; then
    echo "❌ Redis is not installed!"
    echo "Install Redis:"
    echo "  Ubuntu/Debian: sudo apt-get install redis-server"
    echo "  CentOS/RHEL: sudo yum install redis"
    exit 1
fi

echo "✓ Redis CLI found"

# Check if Redis service is running
if systemctl is-active --quiet redis-server; then
    echo "✓ Redis service is running"
else
    echo "⚠ Redis service is NOT running"
    echo "Starting Redis service..."
    sudo systemctl start redis-server

    if systemctl is-active --quiet redis-server; then
        echo "✓ Redis service started successfully"
    else
        echo "❌ Failed to start Redis service!"
        echo "Try to start manually: sudo systemctl start redis-server"
        exit 1
    fi
fi

# Test Redis connection
echo ""
echo "Testing Redis connection..."

REDIS_OUTPUT=$(redis-cli ping 2>&1 || echo "FAILED")

if [ "$REDIS_OUTPUT" = "PONG" ]; then
    echo "✓ Redis is responding correctly"
else
    echo "❌ Redis is not responding: $REDIS_OUTPUT"
    exit 1
fi

# Check Redis memory usage
MEMORY_USAGE=$(redis-cli info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')
echo "✓ Redis memory usage: $MEMORY_USAGE"

# Check connected clients
CLIENTS=$(redis-cli info clients | grep connected_clients | cut -d: -f2 | tr -d '\r')
echo "✓ Connected clients: $CLIENTS"

# Check keyspace
echo ""
echo "Keyspace info:"
redis-cli info keyspace | grep -v "^#" | head -10

# Enable Redis on boot
echo ""
echo "Configuring Redis to start on boot..."
sudo systemctl enable redis-server

if systemctl is-enabled --quiet redis-server; then
    echo "✓ Redis will start automatically on boot"
else
    echo "⚠ Could not enable Redis auto-start"
fi

echo ""
echo "================================================"
echo "Redis Health Check Completed ✓"
echo "================================================"
