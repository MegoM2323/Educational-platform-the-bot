#!/bin/bash

#############################################################################
# Security Headers Testing Script
# Tests all security headers configured in nginx.conf
#############################################################################

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test domain (change to your actual domain)
DOMAIN="${1:-localhost:8080}"
PROTOCOL="${2:-http}"
TEST_URL="${PROTOCOL}://${DOMAIN}"

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Security Headers Verification Test${NC}"
echo -e "${BLUE}Testing: ${TEST_URL}${NC}"
echo -e "${BLUE}========================================${NC}"
echo ""

# Function to test header presence and value
test_header() {
    local header_name=$1
    local expected_pattern=$2
    local description=$3

    echo -ne "${YELLOW}Testing ${header_name}...${NC} "

    local response=$(curl -s -I "${TEST_URL}" 2>/dev/null)
    local header_value=$(echo "$response" | grep -i "^${header_name}:" | cut -d' ' -f2-)

    if [ -z "$header_value" ]; then
        echo -e "${RED}MISSING${NC}"
        echo "  Description: ${description}"
        echo "  Expected: ${expected_pattern}"
        return 1
    elif [[ "$header_value" == *"$expected_pattern"* ]]; then
        echo -e "${GREEN}PRESENT${NC}"
        echo "  Value: ${header_value}"
        return 0
    else
        echo -e "${YELLOW}MISMATCH${NC}"
        echo "  Expected pattern: ${expected_pattern}"
        echo "  Actual value: ${header_value}"
        return 2
    fi
}

# Track results
PASSED=0
FAILED=0
WARNINGS=0

# Test all security headers
echo -e "${BLUE}1. HTTPS/TLS Headers${NC}"
test_header "Strict-Transport-Security" "max-age=31536000" "HSTS - Force HTTPS for 1 year"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
echo -e "${BLUE}2. Content Security Headers${NC}"
test_header "Content-Security-Policy" "default-src" "CSP - Prevent XSS attacks"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
test_header "X-Content-Type-Options" "nosniff" "Prevent MIME type sniffing"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
test_header "X-Frame-Options" "SAMEORIGIN" "Prevent clickjacking"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
test_header "X-XSS-Protection" "1" "Legacy XSS protection"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
echo -e "${BLUE}3. Privacy & Policy Headers${NC}"
test_header "Referrer-Policy" "strict-origin-when-cross-origin" "Control referrer information"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
test_header "Permissions-Policy" "geolocation=" "Disable unnecessary APIs"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
echo -e "${BLUE}4. Cross-Origin Headers${NC}"
test_header "Cross-Origin-Opener-Policy" "same-origin" "COOP - Prevent cross-origin attacks"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
test_header "Cross-Origin-Embedder-Policy" "require-corp" "COEP - Isolate context"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
test_header "Cross-Origin-Resource-Policy" "same-origin" "CORP - Restrict cross-origin requests"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
echo -e "${BLUE}5. Additional Security Headers${NC}"
test_header "X-Permitted-Cross-Domain-Policies" "none" "Flash/PDF policy"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
echo -e "${BLUE}6. Cache Control Headers${NC}"
test_header "Cache-Control" "no-cache" "Cache-Control for index.html"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
test_header "Expires" "0" "Expires header"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
echo -e "${BLUE}7. Compression Headers${NC}"
test_header "Content-Encoding" "gzip" "Gzip compression"
if [ $? -eq 0 ]; then ((PASSED++)); else ((FAILED++)); fi

echo ""
echo -e "${BLUE}8. HTTP Status & Server Info${NC}"
STATUS_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${TEST_URL}")
echo -ne "${YELLOW}HTTP Status Code...${NC} "
if [ "$STATUS_CODE" == "200" ] || [ "$STATUS_CODE" == "304" ]; then
    echo -e "${GREEN}$STATUS_CODE${NC}"
    ((PASSED++))
else
    echo -e "${RED}$STATUS_CODE (Expected 200/304)${NC}"
    ((FAILED++))
fi

echo ""
echo -ne "${YELLOW}Server Header (should be minimal)...${NC} "
SERVER_HEADER=$(curl -s -I "${TEST_URL}" 2>/dev/null | grep -i "^Server:" | cut -d' ' -f2-)
if [ -z "$SERVER_HEADER" ]; then
    echo -e "${GREEN}Not exposed${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}$SERVER_HEADER (Consider hiding version)${NC}"
    ((WARNINGS++))
fi

# Summary
echo ""
echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo -e "${YELLOW}Warnings: ${WARNINGS}${NC}"
echo ""

# Overall result
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All security headers are properly configured!${NC}"
    exit 0
else
    echo -e "${RED}Some security headers are missing or misconfigured!${NC}"
    exit 1
fi
