#!/bin/bash

# Incident Diagnostics Collection Script
# Collects system, application, and service information for incident analysis

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="/tmp/incident-diagnostics-${TIMESTAMP}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

# Create output directory
mkdir -p "${OUTPUT_DIR}"
log_info "Creating diagnostics in: ${OUTPUT_DIR}"

# System Information
mkdir -p "${OUTPUT_DIR}/system"
log_info "Collecting system information..."
uname -a > "${OUTPUT_DIR}/system/uname.txt" 2>&1 || true
date -u > "${OUTPUT_DIR}/system/date.txt" 2>&1 || true
uptime > "${OUTPUT_DIR}/system/uptime.txt" 2>&1 || true
free -h > "${OUTPUT_DIR}/system/memory.txt" 2>&1 || true
df -h > "${OUTPUT_DIR}/system/disk.txt" 2>&1 || true

# Docker
mkdir -p "${OUTPUT_DIR}/docker"
log_info "Collecting docker information..."
docker ps --all > "${OUTPUT_DIR}/docker/ps.txt" 2>&1 || true
docker stats --no-stream --all > "${OUTPUT_DIR}/docker/stats.txt" 2>&1 || true
docker logs thebot-backend --tail=1000 > "${OUTPUT_DIR}/docker/backend_logs.txt" 2>&1 || true
docker logs thebot-postgres --tail=500 > "${OUTPUT_DIR}/docker/postgres_logs.txt" 2>&1 || true
docker logs thebot-redis --tail=500 > "${OUTPUT_DIR}/docker/redis_logs.txt" 2>&1 || true

# Database
mkdir -p "${OUTPUT_DIR}/database"
log_info "Collecting database information..."
pg_isready -h localhost -p 5432 > "${OUTPUT_DIR}/database/connection_test.txt" 2>&1 || true
psql $DATABASE_URL -c "SELECT count(*) FROM pg_stat_activity;" > "${OUTPUT_DIR}/database/connection_count.txt" 2>&1 || true
psql $DATABASE_URL -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database;" > "${OUTPUT_DIR}/database/sizes.txt" 2>&1 || true

# Redis
mkdir -p "${OUTPUT_DIR}/redis"
log_info "Collecting redis information..."
redis-cli ping > "${OUTPUT_DIR}/redis/ping.txt" 2>&1 || true
redis-cli INFO > "${OUTPUT_DIR}/redis/info.txt" 2>&1 || true
redis-cli DBSIZE > "${OUTPUT_DIR}/redis/dbsize.txt" 2>&1 || true

# API Health
mkdir -p "${OUTPUT_DIR}/api"
log_info "Collecting API health..."
curl -s http://localhost:8000/api/health/ > "${OUTPUT_DIR}/api/health.txt" 2>&1 || true
curl -s http://localhost:8000/api/system/metrics/ > "${OUTPUT_DIR}/api/metrics.txt" 2>&1 || true

# Git info
mkdir -p "${OUTPUT_DIR}/git"
if [ -d ".git" ]; then
    git status > "${OUTPUT_DIR}/git/status.txt" 2>&1 || true
    git log --oneline -20 > "${OUTPUT_DIR}/git/log.txt" 2>&1 || true
fi

# Create archive
log_info "Creating compressed archive..."
cd /tmp
tar -czf "incident-diagnostics-${TIMESTAMP}.tar.gz" "incident-diagnostics-${TIMESTAMP}/" 2>/dev/null || true

log_info "Diagnostics collection complete!"
log_info "Output: ${OUTPUT_DIR}"
log_info "Archive: /tmp/incident-diagnostics-${TIMESTAMP}.tar.gz"
echo ""
echo "To review:"
echo "  cat ${OUTPUT_DIR}/system/uname.txt"
echo "  cat ${OUTPUT_DIR}/docker/backend_logs.txt"
echo "  cat ${OUTPUT_DIR}/database/connection_count.txt"
echo ""

exit 0
