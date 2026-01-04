#!/bin/bash

# Integration Test Suite for the-bot.ru Production Deployment
# Remote execution via SSH
# Test Environment: Server 5.129.249.206, Domain: the-bot.ru

# Configuration
SERVER_IP="5.129.249.206"
DOMAIN="the-bot.ru"
BACKEND_PORT=8000
FRONTEND_PORT=3000
HTTP_PORT=80
HTTPS_PORT=443
DB_PORT=5432
REDIS_PORT=6379
SSH_USER="mg"
PROJECT_PATH="/opt/THE_BOT_platform"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
REPORT_FILE="/home/mego/Python Projects/THE_BOT_platform/INTEGRATION_TEST_REPORT.md"

# Counters
TESTS_PASSED=0
TESTS_FAILED=0
FAILED_TESTS=()

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    TESTS_PASSED=$((TESTS_PASSED + 1))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    TESTS_FAILED=$((TESTS_FAILED + 1))
    FAILED_TESTS+=("$1")
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Initialize report
cat > "$REPORT_FILE" << EOF
# Integration Test Report - the-bot.ru Production Deployment

**Test Execution Timestamp**: $TIMESTAMP

**Server**: $SERVER_IP
**Domain**: $DOMAIN
**Project Path**: $PROJECT_PATH

---

EOF

echo ""
echo "=========================================="
echo "   INTEGRATION TEST SUITE EXECUTION"
echo "=========================================="
echo ""

# ==================== TEST 1: DNS RESOLUTION ====================
echo ""
echo "========== TEST 1: DNS RESOLUTION =========="
echo ""

echo "## Test 1: DNS Resolution" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_test "DNS Resolution - Standard (nslookup)"
if nslookup "$DOMAIN" > /tmp/dns_standard.txt 2>&1; then
    if grep -q "$SERVER_IP" /tmp/dns_standard.txt; then
        log_pass "DNS resolves to $SERVER_IP"
        echo "### Standard nslookup:" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        cat /tmp/dns_standard.txt >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
    else
        log_fail "DNS does not resolve to correct IP"
    fi
else
    log_fail "DNS query failed"
fi

log_test "DNS Resolution - Detailed (dig)"
if dig "$DOMAIN" > /tmp/dns_dig.txt 2>&1; then
    if grep -q "$SERVER_IP" /tmp/dns_dig.txt; then
        log_pass "Dig confirms resolution to $SERVER_IP"
        echo "" >> "$REPORT_FILE"
        echo "### Detailed dig result:" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        cat /tmp/dns_dig.txt >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
    else
        log_fail "Dig does not show correct IP"
    fi
else
    log_fail "Dig query failed"
fi

log_test "DNS Resolution - Google DNS Validation"
if nslookup "$DOMAIN" 8.8.8.8 > /tmp/dns_google.txt 2>&1; then
    if grep -q "$SERVER_IP" /tmp/dns_google.txt; then
        log_pass "Google DNS validates correct resolution"
        echo "" >> "$REPORT_FILE"
        echo "### Google DNS validation (8.8.8.8):" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        cat /tmp/dns_google.txt >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
    else
        log_fail "Google DNS validation failed"
    fi
else
    log_fail "Google DNS query failed"
fi

# ==================== TEST 2: REMOTE PORT ACCESSIBILITY ====================
echo ""
echo "========== TEST 2: REMOTE PORT ACCESSIBILITY =========="
echo ""

echo "" >> "$REPORT_FILE"
echo "## Test 2: Port Accessibility" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

check_remote_port() {
    local port=$1
    local name=$2

    log_test "Port $port ($name) accessibility"

    if ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "timeout 3 bash -c 'echo >/dev/tcp/localhost/$port'" > /dev/null 2>&1; then
        log_pass "Port $port ($name) is accessible"
        echo "- Port $port ($name): **OPEN**" >> "$REPORT_FILE"
        return 0
    else
        log_fail "Port $port ($name) is not accessible"
        echo "- Port $port ($name): **CLOSED/TIMEOUT**" >> "$REPORT_FILE"
        return 1
    fi
}

check_remote_port "$BACKEND_PORT" "Backend API"
check_remote_port "$FRONTEND_PORT" "Frontend Dev"
check_remote_port "$HTTP_PORT" "HTTP"
check_remote_port "$HTTPS_PORT" "HTTPS"
check_remote_port "$DB_PORT" "PostgreSQL"
check_remote_port "$REDIS_PORT" "Redis"

# ==================== TEST 3: HTTP CONNECTIVITY ====================
echo ""
echo "========== TEST 3: HTTP CONNECTIVITY =========="
echo ""

echo "" >> "$REPORT_FILE"
echo "## Test 3: HTTP Connectivity" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

test_http() {
    local url=$1
    local name=$2

    log_test "HTTP connectivity to $name"

    response=$(curl -s -w "\n%{http_code}" -m 5 "$url" 2>&1)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [[ "$http_code" =~ ^[123][0-9]{2}$ ]]; then
        log_pass "$name returned HTTP $http_code"
        echo "### $name" >> "$REPORT_FILE"
        echo "- URL: $url" >> "$REPORT_FILE"
        echo "- HTTP Code: **$http_code**" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    else
        log_fail "$name returned HTTP $http_code (timeout or error)"
        echo "### $name" >> "$REPORT_FILE"
        echo "- URL: $url" >> "$REPORT_FILE"
        echo "- HTTP Code: **$http_code (ERROR)**" >> "$REPORT_FILE"
        echo "" >> "$REPORT_FILE"
    fi
}

test_http "http://$SERVER_IP:$BACKEND_PORT/api/" "Backend API Root"
test_http "http://$SERVER_IP:$FRONTEND_PORT/" "Frontend Dev Server"
test_http "http://$SERVER_IP:$HTTP_PORT/" "HTTP Port 80"

# ==================== TEST 4: BACKEND API HEALTH ====================
echo ""
echo "========== TEST 4: BACKEND API HEALTH =========="
echo ""

echo "" >> "$REPORT_FILE"
echo "## Test 4: Backend API Health" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

test_health_endpoint() {
    local url=$1
    local name=$2

    log_test "Health endpoint: $name"

    response=$(curl -s -w "\n%{http_code}" -m 5 "$url" 2>&1)
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    echo "### $name" >> "$REPORT_FILE"
    echo "- Endpoint: $url" >> "$REPORT_FILE"
    echo "- HTTP Code: $http_code" >> "$REPORT_FILE"

    if [[ "$http_code" == "200" ]]; then
        log_pass "$name returned 200"
        echo "- Status: **HEALTHY**" >> "$REPORT_FILE"
        echo '```json' >> "$REPORT_FILE"
        echo "$body" | head -n 50 >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
    else
        log_fail "$name returned $http_code"
        echo "- Status: **UNHEALTHY (HTTP $http_code)**" >> "$REPORT_FILE"
    fi
    echo "" >> "$REPORT_FILE"
}

test_health_endpoint "http://$SERVER_IP:$BACKEND_PORT/api/system/health/live/" "Liveness Probe"
test_health_endpoint "http://$SERVER_IP:$BACKEND_PORT/api/system/health/ready/" "Readiness Probe"
test_health_endpoint "http://$SERVER_IP:$BACKEND_PORT/admin/" "Admin Panel"

# ==================== TEST 5: FRONTEND ASSET LOADING ====================
echo ""
echo "========== TEST 5: FRONTEND ASSET LOADING =========="
echo ""

echo "" >> "$REPORT_FILE"
echo "## Test 5: Frontend Asset Loading" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_test "Frontend index.html loading (Port 3000)"
if curl -s -I "http://$SERVER_IP:$FRONTEND_PORT/" > /tmp/frontend_3000_headers.txt 2>&1; then
    http_code=$(grep "HTTP" /tmp/frontend_3000_headers.txt | awk '{print $2}' | head -1)
    if [[ "$http_code" =~ ^[123][0-9]{2}$ ]] && ! grep -q "403" /tmp/frontend_3000_headers.txt; then
        log_pass "Frontend (port 3000) loaded successfully, HTTP $http_code"
        echo "### Frontend Port 3000" >> "$REPORT_FILE"
        echo "- HTTP Code: **$http_code**" >> "$REPORT_FILE"
        echo "- 403 Forbidden: **NO**" >> "$REPORT_FILE"
    else
        log_fail "Frontend (port 3000) returned $http_code or 403"
        echo "### Frontend Port 3000" >> "$REPORT_FILE"
        echo "- Status: **ERROR - HTTP $http_code**" >> "$REPORT_FILE"
    fi
else
    log_fail "Could not connect to frontend (port 3000)"
fi
echo "" >> "$REPORT_FILE"

log_test "Frontend index.html loading (Port 80)"
if curl -s -I "http://$SERVER_IP:$HTTP_PORT/" > /tmp/frontend_80_headers.txt 2>&1; then
    http_code=$(grep "HTTP" /tmp/frontend_80_headers.txt | awk '{print $2}' | head -1)
    if [[ "$http_code" =~ ^[123][0-9]{2}$ ]]; then
        log_pass "Frontend (port 80) loaded successfully, HTTP $http_code"
        echo "### Frontend Port 80" >> "$REPORT_FILE"
        echo "- HTTP Code: **$http_code**" >> "$REPORT_FILE"
    else
        log_fail "Frontend (port 80) returned $http_code"
        echo "### Frontend Port 80" >> "$REPORT_FILE"
        echo "- Status: **ERROR - HTTP $http_code**" >> "$REPORT_FILE"
    fi
else
    log_fail "Could not connect to frontend (port 80)"
fi
echo "" >> "$REPORT_FILE"

# ==================== TEST 6: DATABASE CONNECTIVITY ====================
echo ""
echo "========== TEST 6: DATABASE CONNECTIVITY =========="
echo ""

echo "" >> "$REPORT_FILE"
echo "## Test 6: Database Connectivity" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_test "PostgreSQL connectivity (via Docker)"
if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" \
    "cd $PROJECT_PATH && docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres -d thebot_db -c 'SELECT 1;'" > /tmp/db_test.txt 2>&1; then
    if grep -q "1" /tmp/db_test.txt; then
        log_pass "PostgreSQL is accessible and responding"
        echo "- Status: **CONNECTED**" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        cat /tmp/db_test.txt >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
    else
        log_fail "PostgreSQL did not return expected response"
        echo "- Status: **NO RESPONSE**" >> "$REPORT_FILE"
    fi
else
    log_fail "PostgreSQL connection failed"
    echo "- Status: **CONNECTION FAILED**" >> "$REPORT_FILE"
    cat /tmp/db_test.txt 2>/dev/null >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# ==================== TEST 7: REDIS CONNECTIVITY ====================
echo ""
echo "========== TEST 7: REDIS CONNECTIVITY =========="
echo ""

echo "" >> "$REPORT_FILE"
echo "## Test 7: Redis Connectivity" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_test "Redis connectivity (via Docker)"
if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" \
    "cd $PROJECT_PATH && docker-compose -f docker-compose.prod.yml exec -T redis redis-cli PING" > /tmp/redis_test.txt 2>&1; then
    if grep -q "PONG" /tmp/redis_test.txt; then
        log_pass "Redis is accessible and responding with PONG"
        echo "- Status: **CONNECTED**" >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
        cat /tmp/redis_test.txt >> "$REPORT_FILE"
        echo '```' >> "$REPORT_FILE"
    else
        log_fail "Redis did not return PONG"
        echo "- Status: **NO PONG RESPONSE**" >> "$REPORT_FILE"
        cat /tmp/redis_test.txt >> "$REPORT_FILE"
    fi
else
    log_fail "Redis connection failed"
    echo "- Status: **CONNECTION FAILED**" >> "$REPORT_FILE"
    cat /tmp/redis_test.txt 2>/dev/null >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# ==================== TEST 8: DOCKER CONTAINER HEALTH ====================
echo ""
echo "========== TEST 8: DOCKER CONTAINER HEALTH =========="
echo ""

echo "" >> "$REPORT_FILE"
echo "## Test 8: Docker Container Status" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_test "Docker container status (via SSH)"
if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" \
    "cd $PROJECT_PATH && docker-compose -f docker-compose.prod.yml ps" > /tmp/docker_status.txt 2>&1; then
    log_pass "Retrieved container status"
    echo '```' >> "$REPORT_FILE"
    cat /tmp/docker_status.txt >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"

    running=$(grep -c "Up" /tmp/docker_status.txt || echo "0")
    log_info "Running containers: $running"
else
    log_fail "Could not retrieve container status"
    echo "- Status: **UNABLE TO RETRIEVE**" >> "$REPORT_FILE"
fi
echo "" >> "$REPORT_FILE"

# ==================== TEST 9: LOGS CHECK ====================
echo ""
echo "========== TEST 9: APPLICATION LOGS =========="
echo ""

echo "" >> "$REPORT_FILE"
echo "## Test 9: Application Logs" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

log_test "Backend application logs"
if ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" \
    "cd $PROJECT_PATH && docker-compose -f docker-compose.prod.yml logs --tail=20 backend" > /tmp/backend_logs.txt 2>&1; then
    log_pass "Retrieved backend logs"
    echo "### Backend Logs (last 20 lines):" >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"
    tail -20 /tmp/backend_logs.txt >> "$REPORT_FILE"
    echo '```' >> "$REPORT_FILE"

    if grep -q "ERROR" /tmp/backend_logs.txt; then
        log_fail "Backend logs contain ERROR messages"
        echo "- **WARNING**: Error messages found in backend logs" >> "$REPORT_FILE"
    else
        log_pass "No ERROR messages in backend logs"
    fi
else
    log_fail "Could not retrieve backend logs"
fi
echo "" >> "$REPORT_FILE"

# ==================== SUMMARY ====================
echo ""
echo "=========================================="
echo "   TEST EXECUTION SUMMARY"
echo "=========================================="
echo ""
echo -e "${GREEN}TESTS PASSED: $TESTS_PASSED${NC}"
echo -e "${RED}TESTS FAILED: $TESTS_FAILED${NC}"
echo ""

# Add summary to report
echo "" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "| Metric | Result |" >> "$REPORT_FILE"
echo "|--------|--------|" >> "$REPORT_FILE"
echo "| Total Tests | $((TESTS_PASSED + TESTS_FAILED)) |" >> "$REPORT_FILE"
echo "| Passed | $TESTS_PASSED |" >> "$REPORT_FILE"
echo "| Failed | $TESTS_FAILED |" >> "$REPORT_FILE"
echo "| Success Rate | $((TESTS_PASSED * 100 / (TESTS_PASSED + TESTS_FAILED)))% |" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

if [ $TESTS_FAILED -gt 0 ]; then
    echo "### Failed Tests:" >> "$REPORT_FILE"
    for test in "${FAILED_TESTS[@]}"; do
        echo "- $test" >> "$REPORT_FILE"
    done
    echo "" >> "$REPORT_FILE"
fi

echo "### Test Execution Details" >> "$REPORT_FILE"
echo "- Timestamp: $TIMESTAMP" >> "$REPORT_FILE"
echo "- Server: $SERVER_IP" >> "$REPORT_FILE"
echo "- Domain: $DOMAIN" >> "$REPORT_FILE"
echo "- Project Path: $PROJECT_PATH" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Acceptance criteria check
echo "" >> "$REPORT_FILE"
echo "## Acceptance Criteria Checklist" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

DNS_OK=$(grep -q "$SERVER_IP" /tmp/dns_standard.txt 2>/dev/null && echo "✓ PASS" || echo "✗ FAIL")
echo "- DNS resolves correctly: **$DNS_OK**" >> "$REPORT_FILE"

FRONTEND_OK=$(grep -q "200\|301\|302" /tmp/frontend_80_headers.txt 2>/dev/null && ! grep -q "403" /tmp/frontend_80_headers.txt 2>/dev/null && echo "✓ PASS" || echo "✗ FAIL")
echo "- Frontend loads without 403: **$FRONTEND_OK**" >> "$REPORT_FILE"

BACKEND_HEALTH=$(curl -s -o /dev/null -w "%{http_code}" "http://$SERVER_IP:$BACKEND_PORT/api/system/health/live/" 2>/dev/null)
if [[ "$BACKEND_HEALTH" == "200" ]]; then
    echo "- Backend API responds: **✓ PASS**" >> "$REPORT_FILE"
else
    echo "- Backend API responds: **✗ FAIL (HTTP $BACKEND_HEALTH)**" >> "$REPORT_FILE"
fi

DB_STATUS=$(grep -q "1" /tmp/db_test.txt 2>/dev/null && echo "✓ PASS" || echo "✗ FAIL")
echo "- Database operational: **$DB_STATUS**" >> "$REPORT_FILE"

REDIS_STATUS=$(grep -q "PONG" /tmp/redis_test.txt 2>/dev/null && echo "✓ PASS" || echo "✗ FAIL")
echo "- Redis operational: **$REDIS_STATUS**" >> "$REPORT_FILE"

CONTAINERS=$(grep -c "Up" /tmp/docker_status.txt 2>/dev/null || echo "0")
echo "- Container status: **$CONTAINERS containers running**" >> "$REPORT_FILE"

echo "" >> "$REPORT_FILE"

echo ""
echo "Report saved to: $REPORT_FILE"
echo ""
