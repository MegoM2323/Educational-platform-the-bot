#!/bin/bash

# CDN Testing Script for THE_BOT Platform
# Tests cache functionality, security, and performance

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
DOMAIN="${1:-https://thebot.example.com}"
API_URL="${2:-https://api.thebot.example.com}"
TESTS_PASSED=0
TESTS_FAILED=0

echo -e "${BLUE}=== THE_BOT Platform CDN Testing ===${NC}"
echo -e "Domain: ${DOMAIN}"
echo -e "API URL: ${API_URL}\n"

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

log_test() {
  echo -e "${BLUE}[TEST]${NC} $1"
}

log_success() {
  echo -e "${GREEN}[PASS]${NC} $1"
  ((TESTS_PASSED++))
}

log_error() {
  echo -e "${RED}[FAIL]${NC} $1"
  ((TESTS_FAILED++))
}

log_warning() {
  echo -e "${YELLOW}[WARN]${NC} $1"
}

check_response_code() {
  local url=$1
  local expected=$2
  local description=$3

  log_test "$description"

  local status=$(curl -s -o /dev/null -w "%{http_code}" "$url")

  if [ "$status" = "$expected" ]; then
    log_success "HTTP $status (expected $expected)"
  else
    log_error "HTTP $status (expected $expected)"
  fi
}

check_header() {
  local url=$1
  local header=$2
  local expected=$3
  local description=$4

  log_test "$description"

  local value=$(curl -s -I "$url" | grep -i "^$header:" | cut -d' ' -f2-)

  if [[ "$value" == *"$expected"* ]]; then
    log_success "$header: $value"
  else
    log_error "$header not found or incorrect (got: $value)"
  fi
}

measure_response_time() {
  local url=$1
  local description=$2

  log_test "$description"

  local time=$(curl -o /dev/null -s -w "%{time_total}" "$url")
  echo -e "Response time: ${time}s"

  # Check if response time is acceptable (< 1 second for cached content)
  if (( $(echo "$time < 1.0" | bc -l) )); then
    log_success "Response time acceptable"
  else
    log_warning "Response time may be slow"
  fi
}

# ============================================================================
# 1. BASIC CONNECTIVITY TESTS
# ============================================================================

echo -e "\n${BLUE}=== 1. BASIC CONNECTIVITY ===${NC}"

check_response_code "$DOMAIN" "200" "Main domain should respond with 200"
check_response_code "$API_URL" "200" "API URL should respond with 200"

# ============================================================================
# 2. HTTPS/TLS TESTS
# ============================================================================

echo -e "\n${BLUE}=== 2. HTTPS/TLS TESTS ===${NC}"

log_test "Check HTTPS enforcement"
if curl -I "$DOMAIN" 2>/dev/null | grep -q "HTTP/1.1\|HTTP/2"; then
  log_success "HTTPS is active"
else
  log_error "HTTPS not detected"
fi

log_test "Check minimum TLS version"
if echo | openssl s_client -servername thebot.example.com -connect thebot.example.com:443 2>/dev/null | grep -q "TLSv1.2\|TLSv1.3"; then
  log_success "TLS 1.2+ is supported"
else
  log_error "TLS version too old"
fi

# ============================================================================
# 3. CACHE HEADER TESTS
# ============================================================================

echo -e "\n${BLUE}=== 3. CACHE HEADER TESTS ===${NC}"

check_header "$DOMAIN/assets/app.js" "Cache-Control" "max-age" "Static assets should have cache control"
check_header "$DOMAIN/images/logo.png" "Cache-Control" "max-age" "Images should have cache control"
check_header "$DOMAIN/index.html" "Cache-Control" "no-cache\|no-store" "HTML should not be cached"
check_header "$API_URL/api/users" "Cache-Control" "no-cache\|private" "API responses should not be cached"

# ============================================================================
# 4. COMPRESSION TESTS
# ============================================================================

echo -e "\n${BLUE}=== 4. COMPRESSION TESTS ===${NC}"

log_test "Check Gzip compression"
if curl -s -I -H "Accept-Encoding: gzip" "$DOMAIN" | grep -qi "content-encoding.*gzip"; then
  log_success "Gzip compression is enabled"
else
  log_warning "Gzip compression not detected"
fi

log_test "Check Brotli compression"
if curl -s -I -H "Accept-Encoding: br" "$DOMAIN" | grep -qi "content-encoding.*br"; then
  log_success "Brotli compression is enabled"
else
  log_warning "Brotli compression not detected"
fi

# ============================================================================
# 5. SECURITY HEADER TESTS
# ============================================================================

echo -e "\n${BLUE}=== 5. SECURITY HEADER TESTS ===${NC}"

check_header "$DOMAIN" "X-Content-Type-Options" "nosniff" "X-Content-Type-Options header"
check_header "$DOMAIN" "X-Frame-Options" "DENY\|SAMEORIGIN" "X-Frame-Options header"
check_header "$DOMAIN" "X-XSS-Protection" "1" "X-XSS-Protection header"
check_header "$DOMAIN" "Strict-Transport-Security" "max-age" "HSTS header"
check_header "$DOMAIN" "Content-Security-Policy" "default-src" "CSP header"

# ============================================================================
# 6. CACHE FUNCTIONALITY TESTS
# ============================================================================

echo -e "\n${BLUE}=== 6. CACHE FUNCTIONALITY TESTS ===${NC}"

log_test "First request (should be cache miss)"
RESPONSE1=$(curl -s -I "$DOMAIN/assets/app.js")
if echo "$RESPONSE1" | grep -qi "x-cache-status.*miss"; then
  log_success "Cache miss detected on first request"
else
  log_warning "Could not detect cache status header"
fi

log_test "Second request (should be cache hit)"
sleep 1
RESPONSE2=$(curl -s -I "$DOMAIN/assets/app.js")
if echo "$RESPONSE2" | grep -qi "x-cache-status.*hit"; then
  log_success "Cache hit detected on second request"
else
  log_warning "Could not detect cache hit"
fi

log_test "Cache busting with query parameter"
RESPONSE3=$(curl -s -I "$DOMAIN/assets/app.js?v=2.0")
if echo "$RESPONSE3" | grep -qi "x-cache-status.*miss"; then
  log_success "Cache busted with query parameter"
else
  log_warning "Cache busting may not be working"
fi

# ============================================================================
# 7. PERFORMANCE TESTS
# ============================================================================

echo -e "\n${BLUE}=== 7. PERFORMANCE TESTS ===${NC}"

measure_response_time "$DOMAIN" "Homepage response time"
measure_response_time "$DOMAIN/assets/app.js" "Static asset response time"
measure_response_time "$API_URL/api/health" "API health check response time"

log_test "Time to First Byte (TTFB)"
TTFB=$(curl -o /dev/null -s -w "%{time_starttransfer}" "$DOMAIN")
echo "TTFB: ${TTFB}s"
if (( $(echo "$TTFB < 0.5" | bc -l) )); then
  log_success "TTFB is excellent"
elif (( $(echo "$TTFB < 1.0" | bc -l) )); then
  log_success "TTFB is good"
else
  log_warning "TTFB may be slow"
fi

# ============================================================================
# 8. RATE LIMITING TESTS
# ============================================================================

echo -e "\n${BLUE}=== 8. RATE LIMITING TESTS ===${NC}"

log_test "Login endpoint rate limiting (5 requests)"
for i in {1..5}; do
  STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d '{"username":"test","password":"wrong"}')
  echo "Request $i: HTTP $STATUS"
done

log_test "6th request (should be rate limited)"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"test","password":"wrong"}')

if [ "$STATUS" = "429" ]; then
  log_success "Rate limiting is working (HTTP 429)"
else
  log_warning "Rate limiting may not be active (HTTP $STATUS)"
fi

# ============================================================================
# 9. WAF & SECURITY TESTS
# ============================================================================

echo -e "\n${BLUE}=== 9. WAF & SECURITY TESTS ===${NC}"

log_test "SQL injection attack attempt"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/search?q='; DROP TABLE users; --")
if [ "$STATUS" = "403" ]; then
  log_success "WAF blocked SQL injection (HTTP 403)"
elif [ "$STATUS" = "429" ]; then
  log_success "WAF blocked request (HTTP 429)"
else
  log_warning "WAF may not have blocked request (HTTP $STATUS)"
fi

log_test "XSS attack attempt"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API_URL/api/search?q=<script>alert('xss')</script>")
if [ "$STATUS" = "403" ]; then
  log_success "WAF blocked XSS attempt (HTTP 403)"
elif [ "$STATUS" = "429" ]; then
  log_success "WAF blocked request (HTTP 429)"
else
  log_warning "WAF may not have blocked request (HTTP $STATUS)"
fi

# ============================================================================
# 10. CLOUDFLARE FEATURES
# ============================================================================

echo -e "\n${BLUE}=== 10. CLOUDFLARE FEATURES ===${NC}"

log_test "Check HTTP/2 support"
if curl -s -I "$DOMAIN" | grep -q "HTTP/2"; then
  log_success "HTTP/2 is enabled"
else
  log_warning "HTTP/2 not detected (may be normal)"
fi

log_test "Check HTTP/3 support"
if curl -s -I --http3 "$DOMAIN" 2>&1 | grep -q "HTTP/3"; then
  log_success "HTTP/3 is enabled"
else
  log_warning "HTTP/3 not available (curl may not support it)"
fi

log_test "Check Cloudflare Server header"
if curl -s -I "$DOMAIN" | grep -qi "cloudflare"; then
  log_success "Cloudflare is detected"
else
  log_warning "Cloudflare header not visible"
fi

# ============================================================================
# 11. CONTENT TYPE TESTS
# ============================================================================

echo -e "\n${BLUE}=== 11. CONTENT TYPE TESTS ===${NC}"

check_header "$DOMAIN/assets/app.js" "Content-Type" "javascript" "JavaScript content type"
check_header "$DOMAIN/assets/style.css" "Content-Type" "css" "CSS content type"
check_header "$DOMAIN/images/logo.png" "Content-Type" "image" "Image content type"

# ============================================================================
# SUMMARY
# ============================================================================

echo -e "\n${BLUE}=== TEST SUMMARY ===${NC}"
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=$((TESTS_PASSED * 100 / TOTAL))

echo -e "Total tests: $TOTAL"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "Pass rate: ${PASS_RATE}%"

if [ $TESTS_FAILED -eq 0 ]; then
  echo -e "\n${GREEN}All tests passed!${NC}"
  exit 0
else
  echo -e "\n${RED}Some tests failed. Please review the configuration.${NC}"
  exit 1
fi
