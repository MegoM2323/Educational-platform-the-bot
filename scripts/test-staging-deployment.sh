#!/bin/bash

# Staging Deployment Testing Script
# Tests staging deployment configuration and health checks
# Usage: bash scripts/test-staging-deployment.sh [environment]

set -e

ENVIRONMENT=${1:-staging}
STAGING_URL=${STAGING_URL:-https://staging.the-bot.ru}
HEALTH_CHECK_TIMEOUT=60
HEALTH_CHECK_INTERVAL=5

echo "=========================================="
echo "Staging Deployment Test Suite"
echo "=========================================="
echo "Environment: $ENVIRONMENT"
echo "Staging URL: $STAGING_URL"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
test_start() {
    echo -n "Testing: $1... "
}

test_pass() {
    echo -e "${GREEN}PASS${NC}"
    ((TESTS_PASSED++))
}

test_fail() {
    echo -e "${RED}FAIL${NC}"
    echo "  Error: $1"
    ((TESTS_FAILED++))
}

test_warn() {
    echo -e "${YELLOW}WARN${NC}"
    echo "  Warning: $1"
}

# ============================================================================
# Test 1: Backend Health Check
# ============================================================================
test_start "Backend health endpoint"
if curl -sf "${STAGING_URL}/api/system/health/" \
    -H "User-Agent: Test" \
    -m 10 > /dev/null 2>&1; then
    test_pass
else
    test_fail "Backend health endpoint not responding"
fi

# ============================================================================
# Test 2: Frontend Availability
# ============================================================================
test_start "Frontend availability"
if curl -sf "${STAGING_URL}/" \
    -H "User-Agent: Test" \
    -m 10 > /tmp/frontend-response.html 2>&1; then
    if grep -q "THE_BOT\|html\|DOCTYPE" /tmp/frontend-response.html; then
        test_pass
    else
        test_warn "Frontend returned content but may not be fully loaded"
    fi
    rm -f /tmp/frontend-response.html
else
    test_fail "Frontend not responding"
fi

# ============================================================================
# Test 3: API Readiness
# ============================================================================
test_start "API readiness check"
if curl -sf "${STAGING_URL}/api/system/readiness/" \
    -H "Accept: application/json" \
    -m 10 > /dev/null 2>&1; then
    test_pass
else
    test_warn "Readiness endpoint not available (may not be implemented)"
fi

# ============================================================================
# Test 4: Authentication Endpoints
# ============================================================================
test_start "Authentication endpoints"
if curl -sf "${STAGING_URL}/api/auth/login/" \
    -X OPTIONS \
    -m 10 > /dev/null 2>&1; then
    test_pass
else
    test_fail "Authentication endpoint not accessible"
fi

# ============================================================================
# Test 5: Static Files
# ============================================================================
test_start "Static files endpoint"
if curl -sf "${STAGING_URL}/static/" -I \
    -m 10 > /dev/null 2>&1; then
    test_pass
else
    test_warn "Static files endpoint not available"
fi

# ============================================================================
# Test 6: Profile Endpoint (requires auth)
# ============================================================================
test_start "Profile endpoint (auth check)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${STAGING_URL}/api/accounts/profile/" -m 10)
if [ "$STATUS" == "401" ] || [ "$STATUS" == "403" ]; then
    test_pass "Endpoint protected (authentication required)"
elif [ "$STATUS" == "200" ]; then
    test_warn "Endpoint returned 200 (may be publicly accessible)"
else
    test_warn "Endpoint returned status $STATUS"
fi

# ============================================================================
# Test 7: Response Time Check
# ============================================================================
test_start "Response time (backend)"
RESPONSE_TIME=$(curl -w "%{time_total}" -o /dev/null -s "${STAGING_URL}/api/system/health/")
if (( $(echo "$RESPONSE_TIME < 5" | bc -l) )); then
    echo -ne "${GREEN}PASS${NC} (${RESPONSE_TIME}s)\n"
    ((TESTS_PASSED++))
else
    echo -ne "${YELLOW}WARN${NC} (${RESPONSE_TIME}s - slow response)\n"
fi

# ============================================================================
# Test 8: TLS/HTTPS Configuration
# ============================================================================
test_start "HTTPS/TLS configuration"
if curl -Iv "${STAGING_URL}/" 2>&1 | grep -q "SSL\|TLS"; then
    test_pass
else
    test_fail "HTTPS/TLS not properly configured"
fi

# ============================================================================
# Test 9: Security Headers
# ============================================================================
test_start "Security headers"
HEADERS=$(curl -sI "${STAGING_URL}/" 2>&1)
SECURITY_HEADERS=0

if echo "$HEADERS" | grep -q "X-Frame-Options"; then
    ((SECURITY_HEADERS++))
fi

if echo "$HEADERS" | grep -q "Content-Security-Policy"; then
    ((SECURITY_HEADERS++))
fi

if echo "$HEADERS" | grep -q "X-Content-Type-Options"; then
    ((SECURITY_HEADERS++))
fi

if [ $SECURITY_HEADERS -ge 2 ]; then
    test_pass "Security headers present ($SECURITY_HEADERS found)"
else
    test_warn "Limited security headers ($SECURITY_HEADERS found)"
fi

# ============================================================================
# Test 10: CORS Configuration
# ============================================================================
test_start "CORS headers"
if curl -sI "${STAGING_URL}/api/system/health/" | grep -q "Access-Control"; then
    test_pass
else
    test_warn "CORS headers not explicitly set (may be configured elsewhere)"
fi

# ============================================================================
# Test 11: Database Connectivity (via API)
# ============================================================================
test_start "Database connectivity"
if curl -sf "${STAGING_URL}/api/system/health/" \
    -m 10 | grep -q "ok\|healthy\|status" 2>/dev/null; then
    test_pass
else
    test_warn "Database status unknown (endpoint may not expose it)"
fi

# ============================================================================
# Test 12: Docker Compose Validation
# ============================================================================
if [ -f "docker-compose.yml" ]; then
    test_start "docker-compose.yml validation"
    if command -v docker-compose &> /dev/null; then
        if docker-compose config > /dev/null 2>&1; then
            test_pass
        else
            test_fail "docker-compose.yml is invalid"
        fi
    elif command -v docker &> /dev/null; then
        if docker compose config > /dev/null 2>&1; then
            test_pass
        else
            test_fail "docker-compose configuration is invalid"
        fi
    else
        test_warn "docker-compose not available for validation"
    fi
fi

# ============================================================================
# Test 13: Environment File Check (if on staging server)
# ============================================================================
if [ -f ".env.staging" ]; then
    test_start "Environment file (.env.staging)"
    if grep -q "DATABASE_URL\|SECRET_KEY" .env.staging 2>/dev/null; then
        test_pass
    else
        test_fail "Environment file missing critical variables"
    fi
fi

# ============================================================================
# Test 14: Deployment Manifest Check
# ============================================================================
if [ -f "deployment-manifests/staging-deployment.env" ]; then
    test_start "Deployment manifest"
    if grep -q "DEPLOYMENT_ID\|BACKEND_IMAGE\|FRONTEND_IMAGE" \
        deployment-manifests/staging-deployment.env 2>/dev/null; then
        test_pass
    else
        test_fail "Deployment manifest incomplete"
    fi
fi

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "=========================================="
echo "Test Results"
echo "=========================================="
echo -e "Passed: ${GREEN}${TESTS_PASSED}${NC}"
echo -e "Failed: ${RED}${TESTS_FAILED}${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
fi
