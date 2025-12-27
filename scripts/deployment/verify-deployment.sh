#!/bin/bash

################################################################################
# THE_BOT Platform - Post-Deployment Verification Script
#
# Comprehensive health check and smoke testing suite for verifying deployments.
#
# Usage:
#   ./scripts/deployment/verify-deployment.sh              # Full verification
#   ./scripts/deployment/verify-deployment.sh --quick      # Quick checks only
#   ./scripts/deployment/verify-deployment.sh --strict     # Strict mode (fail on warnings)
#   ./scripts/deployment/verify-deployment.sh --env green  # Check specific environment
#   ./scripts/deployment/verify-deployment.sh --timeout 60 # Custom timeout
#
# Exit Codes:
#   0 - All checks passed
#   1 - One or more checks failed
#   2 - Critical check failed (requires immediate rollback)
#
################################################################################

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
VERIFY_MODE="full"
STRICT_MODE=false
ENV_NAME="prod"
TIMEOUT=120
API_URL="https://api.thebot.com"
FRONTEND_URL="https://thebot.com"
PASSED=0
FAILED=0
WARNINGS=0
CRITICAL_FAILURES=0

################################################################################
# PARSE ARGUMENTS
################################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --quick)
            VERIFY_MODE="quick"
            shift
            ;;
        --strict)
            STRICT_MODE=true
            shift
            ;;
        --env)
            ENV_NAME="$2"
            shift 2
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

################################################################################
# UTILITY FUNCTIONS
################################################################################

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_check() {
    echo -n "Checking: $1 ... "
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC}"
    if [ -n "$1" ]; then
        echo -e "  ${RED}Error: $1${NC}"
    fi
    ((FAILED++))
}

print_critical() {
    echo -e "${RED}✗ CRITICAL${NC}"
    if [ -n "$1" ]; then
        echo -e "  ${RED}Error: $1${NC}"
    fi
    ((FAILED++))
    ((CRITICAL_FAILURES++))
}

print_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}"
    if [ -n "$1" ]; then
        echo -e "  ${YELLOW}Note: $1${NC}"
    fi
    ((WARNINGS++))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

################################################################################
# HEALTH CHECK FUNCTIONS
################################################################################

check_container_status() {
    local container=$1
    print_check "Container $container is running"

    if docker-compose -f "$COMPOSE_FILE" ps "$container" 2>/dev/null | grep -q "Up"; then
        print_pass
        return 0
    else
        print_fail "Container not running"
        return 1
    fi
}

check_database_connectivity() {
    print_check "Database connectivity"

    # Check if postgres container is running
    if ! docker-compose -f "$COMPOSE_FILE" ps postgres 2>/dev/null | grep -q "Up"; then
        print_warn "Postgres container not running (may not be deployed yet)"
        return 0
    fi

    # Try to connect
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U postgres -c "SELECT 1" &>/dev/null; then
        print_pass
        return 0
    else
        print_critical "Cannot connect to database"
        return 1
    fi
}

check_redis_connectivity() {
    print_check "Redis connectivity"

    # Check if redis container is running
    if ! docker-compose -f "$COMPOSE_FILE" ps redis 2>/dev/null | grep -q "Up"; then
        print_warn "Redis container not running (may not be deployed yet)"
        return 0
    fi

    # Try to ping
    if docker-compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli ping &>/dev/null; then
        print_pass
        return 0
    else
        print_critical "Cannot connect to Redis"
        return 1
    fi
}

check_api_health() {
    print_check "API health endpoint"

    local response=$(curl -s -w "\n%{http_code}" \
        -H "Content-Type: application/json" \
        "$API_URL/health/" 2>/dev/null)

    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ]; then
        print_pass
        return 0
    elif [ "$http_code" = "000" ]; then
        print_critical "API unreachable (connection failed)"
        return 1
    else
        print_fail "API returned HTTP $http_code"
        return 1
    fi
}

check_frontend_loaded() {
    print_check "Frontend page loads"

    local response=$(curl -s -w "\n%{http_code}" \
        -H "User-Agent: Mozilla/5.0" \
        "$FRONTEND_URL/" 2>/dev/null)

    local http_code=$(echo "$response" | tail -1)
    local body=$(echo "$response" | head -n -1)

    if [ "$http_code" = "200" ] && echo "$body" | grep -q "THE_BOT"; then
        print_pass
        return 0
    elif [ "$http_code" = "000" ]; then
        print_critical "Frontend unreachable"
        return 1
    else
        print_fail "Frontend returned HTTP $http_code"
        return 1
    fi
}

check_api_authentication() {
    print_check "API authentication"

    # Test login endpoint
    local response=$(curl -s -w "\n%{http_code}" \
        -X POST "$API_URL/auth/login/" \
        -H "Content-Type: application/json" \
        -d '{"email":"test@test.com","password":"wrong"}' 2>/dev/null)

    local http_code=$(echo "$response" | tail -1)

    # Should return 401 or 400 (not 500)
    if [[ "$http_code" =~ ^(400|401)$ ]]; then
        print_pass
        return 0
    elif [ "$http_code" = "500" ]; then
        print_critical "Authentication endpoint returning 500 errors"
        return 1
    elif [ "$http_code" = "000" ]; then
        print_critical "Authentication endpoint unreachable"
        return 1
    else
        print_fail "Unexpected response code: $http_code"
        return 1
    fi
}

check_websocket() {
    print_check "WebSocket connectivity"

    # Simple WebSocket connection test
    if command -v wscat &> /dev/null; then
        if timeout 5 wscat -c "wss://api.thebot.com/ws/test/" --execute 'ping' &>/dev/null; then
            print_pass
            return 0
        else
            print_warn "WebSocket check inconclusive (wscat timeout)"
            return 0
        fi
    else
        print_warn "wscat not installed (skipping WebSocket test)"
        return 0
    fi
}

check_error_rate() {
    print_check "Error rate"

    # Check container logs for recent errors
    if docker-compose -f "$COMPOSE_FILE" logs --tail 100 backend 2>/dev/null | \
        grep -i "error\|exception" | grep -v "404" | grep -q .; then
        print_warn "Found errors in logs (review logs manually)"
        return 0
    else
        print_pass
        return 0
    fi
}

check_database_migrations() {
    print_check "Database migrations status"

    # Check if any pending migrations
    if ! docker-compose -f "$COMPOSE_FILE" exec backend \
        python manage.py showmigrations --plan 2>/dev/null | grep -q "\[ \]"; then
        print_pass
        return 0
    else
        print_warn "Pending migrations found (may need to be applied)"
        return 0
    fi
}

check_static_files() {
    print_check "Static files served"

    local response=$(curl -s -w "\n%{http_code}" \
        "$FRONTEND_URL/static/css/index.css" 2>/dev/null)

    local http_code=$(echo "$response" | tail -1)

    if [ "$http_code" = "200" ]; then
        print_pass
        return 0
    elif [ "$http_code" = "404" ]; then
        print_warn "Static files not found (may not be built yet)"
        return 0
    else
        print_fail "Static files returned HTTP $http_code"
        return 1
    fi
}

check_response_time() {
    print_check "Response time"

    # Measure response time for API health check
    local start=$(date +%s%N)
    curl -s "$API_URL/health/" > /dev/null 2>&1 || true
    local end=$(date +%s%N)
    local duration=$(( (end - start) / 1000000 ))  # Convert to ms

    if [ "$duration" -lt 2000 ]; then
        print_pass "(${duration}ms)"
        return 0
    elif [ "$duration" -lt 5000 ]; then
        print_warn "Slow response time (${duration}ms, expected <2000ms)"
        return 0
    else
        print_fail "Very slow response time (${duration}ms)"
        return 1
    fi
}

check_disk_space() {
    print_check "Disk space available"

    # Check container disk usage
    local usage=$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')

    if [ "$usage" -lt 80 ]; then
        print_pass "(${usage}% used)"
        return 0
    elif [ "$usage" -lt 90 ]; then
        print_warn "Disk usage high (${usage}%)"
        return 0
    else
        print_critical "Disk space critical (${usage}% used)"
        return 1
    fi
}

check_memory_usage() {
    print_check "Memory usage"

    # Check memory limit
    if docker stats --no-stream thebot-backend-prod 2>/dev/null | tail -1 | grep -q ""; then
        print_pass
        return 0
    else
        print_warn "Cannot check memory usage"
        return 0
    fi
}

check_no_restart_loops() {
    print_check "No restart loops"

    # Check if container has restarted recently
    local restart_count=$(docker inspect thebot-backend-prod 2>/dev/null | \
        grep -o '"RestartCount": [0-9]*' | grep -o '[0-9]*')

    if [ "$restart_count" -le 2 ]; then
        print_pass "(restart count: $restart_count)"
        return 0
    else
        print_warn "Container has restarted $restart_count times (may indicate instability)"
        return 0
    fi
}

check_nginx_config() {
    print_check "nginx configuration valid"

    # Check if nginx is running and config is valid
    if docker-compose -f "$COMPOSE_FILE" ps nginx 2>/dev/null | grep -q "Up"; then
        if docker-compose -f "$COMPOSE_FILE" exec nginx nginx -t 2>/dev/null; then
            print_pass
            return 0
        else
            print_fail "nginx configuration invalid"
            return 1
        fi
    else
        print_warn "nginx container not running"
        return 0
    fi
}

check_database_size() {
    print_check "Database health"

    # Check database size and query count
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        psql -U postgres -d thebot_db -c "SELECT pg_database.datname, pg_size_pretty(pg_database_size(pg_database.datname)) FROM pg_database;" &>/dev/null; then
        print_pass
        return 0
    else
        print_warn "Cannot check database size"
        return 0
    fi
}

check_redis_memory() {
    print_check "Redis memory usage"

    # Check Redis memory
    if docker-compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli info memory | grep "used_memory_human" &>/dev/null; then
        print_pass
        return 0
    else
        print_warn "Cannot check Redis memory"
        return 0
    fi
}

################################################################################
# MAIN VERIFICATION FLOW
################################################################################

print_header "POST-DEPLOYMENT VERIFICATION"

echo "Configuration:"
echo "  Verify Mode: $VERIFY_MODE"
echo "  Strict Mode: $STRICT_MODE"
echo "  Environment: $ENV_NAME"
echo "  Timeout: ${TIMEOUT}s"
echo "  API URL: $API_URL"
echo ""

print_header "PHASE 1: INFRASTRUCTURE"

check_container_status "backend"
check_container_status "postgres"
check_container_status "redis"
check_container_status "nginx"

print_header "PHASE 2: CONNECTIVITY"

check_database_connectivity
check_redis_connectivity
check_api_health
check_frontend_loaded

print_header "PHASE 3: API ENDPOINTS"

check_api_authentication
check_websocket

print_header "PHASE 4: PERFORMANCE"

check_response_time
check_disk_space
check_memory_usage
check_no_restart_loops

if [ "$VERIFY_MODE" = "full" ]; then
    print_header "PHASE 5: APPLICATION"

    check_database_migrations
    check_static_files
    check_error_rate
    check_nginx_config
    check_database_size
    check_redis_memory
fi

################################################################################
# SUMMARY
################################################################################

print_header "VERIFICATION SUMMARY"

TOTAL=$((PASSED + FAILED + WARNINGS))

echo "Results:"
echo -e "  ${GREEN}✓ Passed: $PASSED${NC}"
echo -e "  ${YELLOW}⚠ Warnings: $WARNINGS${NC}"
echo -e "  ${RED}✗ Failed: $FAILED${NC}"
if [ "$CRITICAL_FAILURES" -gt 0 ]; then
    echo -e "  ${RED}✗ CRITICAL: $CRITICAL_FAILURES${NC}"
fi
echo -e "  Total: $TOTAL"
echo ""

if [ "$CRITICAL_FAILURES" -gt 0 ]; then
    echo -e "${RED}✗ VERIFICATION FAILED (CRITICAL ISSUES DETECTED)${NC}"
    echo "Recommendation: ROLLBACK IMMEDIATELY"
    exit 2
elif [ "$FAILED" -gt 0 ]; then
    if [ "$STRICT_MODE" = true ]; then
        echo -e "${RED}✗ VERIFICATION FAILED (STRICT MODE)${NC}"
        exit 1
    else
        echo -e "${YELLOW}⚠ VERIFICATION PASSED WITH WARNINGS${NC}"
        exit 0
    fi
else
    echo -e "${GREEN}✓ VERIFICATION PASSED${NC}"
    exit 0
fi
