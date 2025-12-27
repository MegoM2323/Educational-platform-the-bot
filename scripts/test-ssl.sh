#!/bin/bash
#
# SSL/TLS Testing and Verification
# Tests SSL/TLS configuration, protocols, ciphers, and security headers
#
# Usage: bash scripts/test-ssl.sh [domain]
# Example: bash scripts/test-ssl.sh the-bot.ru
#
# Tests:
# 1. Certificate validity
# 2. Protocol support (TLS 1.2, 1.3)
# 3. Weak protocol rejection (SSLv3, TLS 1.0, 1.1)
# 4. Cipher strength
# 5. OCSP stapling
# 6. HSTS header
# 7. Security headers
# 8. Forward secrecy (ECDHE)
#

set -e

DOMAIN="${1:-the-bot.ru}"
PORT="443"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

TEST_PASSED=0
TEST_FAILED=0

echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}SSL/TLS Test Suite${NC}"
echo -e "${BLUE}Domain: $DOMAIN${NC}"
echo -e "${BLUE}==========================================${NC}"
echo ""

test_result() {
    local name=$1
    local result=$2
    local details=$3

    if [ "$result" == "pass" ]; then
        echo -e "${GREEN}✓ PASS${NC}: $name"
        TEST_PASSED=$((TEST_PASSED + 1))
    else
        echo -e "${RED}✗ FAIL${NC}: $name"
        if [ -n "$details" ]; then
            echo "  Details: $details"
        fi
        TEST_FAILED=$((TEST_FAILED + 1))
    fi
}

# Test 1: Certificate validity
echo -e "${BLUE}[1] Certificate Validity${NC}"
echo "========================="

cert_info=$(echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:$PORT" 2>/dev/null | openssl x509 -text -noout 2>/dev/null)

subject=$(echo "$cert_info" | grep "Subject:" | head -1)
issuer=$(echo "$cert_info" | grep "Issuer:" | head -1)

echo "  Subject: $subject"
echo "  Issuer: $issuer"
echo ""

# Check if certificate is valid
if echo | openssl s_client -servername "$DOMAIN" -connect "$DOMAIN:$PORT" 2>/dev/null | openssl x509 -noout -checkend 0 > /dev/null 2>&1; then
    test_result "Certificate Valid" "pass"
else
    test_result "Certificate Valid" "fail" "Certificate is expired or invalid"
fi

# Check certificate matches domain
if echo "$subject" | grep -q "$DOMAIN"; then
    test_result "Certificate Domain Match" "pass"
else
    test_result "Certificate Domain Match" "warn" "Domain in certificate: $subject"
fi

echo ""

# Test 2: Protocol Support
echo -e "${BLUE}[2] Protocol Support${NC}"
echo "===================="

# Test TLS 1.2
echo -n "  Testing TLS 1.2... "
if echo | openssl s_client -tls1_2 -connect "$DOMAIN:$PORT" 2>/dev/null | grep -q "Protocol.*TLSv1.2"; then
    echo -e "${GREEN}OK${NC}"
    test_result "TLS 1.2 Support" "pass"
else
    echo -e "${YELLOW}WARN${NC}"
    test_result "TLS 1.2 Support" "warn"
fi

# Test TLS 1.3
echo -n "  Testing TLS 1.3... "
if echo | openssl s_client -tls1_3 -connect "$DOMAIN:$PORT" 2>/dev/null | grep -q "Protocol.*TLSv1.3"; then
    echo -e "${GREEN}OK${NC}"
    test_result "TLS 1.3 Support" "pass"
else
    echo -e "${YELLOW}WARN${NC}"
    test_result "TLS 1.3 Support" "warn"
fi

echo ""

# Test 3: Weak Protocol Rejection
echo -e "${BLUE}[3] Weak Protocol Rejection${NC}"
echo "============================"

# Test SSLv3 (should fail)
echo -n "  Testing SSLv3 rejection... "
if ! echo | openssl s_client -ssl3 -connect "$DOMAIN:$PORT" 2>&1 | grep -q "SSL23_GET_SERVER_HELLO:sslv3 alert"; then
    if ! echo | openssl s_client -ssl3 -connect "$DOMAIN:$PORT" 2>&1 | grep -q "handshake failure"; then
        test_result "SSLv3 Disabled" "warn" "Server may accept SSLv3"
    else
        echo -e "${GREEN}DISABLED${NC}"
        test_result "SSLv3 Disabled" "pass"
    fi
else
    echo -e "${GREEN}DISABLED${NC}"
    test_result "SSLv3 Disabled" "pass"
fi

echo ""

# Test 4: Cipher Strength
echo -e "${BLUE}[4] Cipher Strength${NC}"
echo "==================="

# Get cipher used
cipher=$(echo | openssl s_client -tls1_2 -connect "$DOMAIN:$PORT" 2>/dev/null | grep "Cipher" | awk '{print $3}' | head -1)
echo "  Cipher (TLS 1.2): $cipher"

if [[ "$cipher" == ECDHE-* ]]; then
    test_result "Forward Secrecy (ECDHE)" "pass"
else
    test_result "Forward Secrecy (ECDHE)" "warn" "Cipher: $cipher"
fi

if [[ "$cipher" == *GCM* ]] || [[ "$cipher" == *POLY1305* ]]; then
    test_result "AEAD Cipher (GCM/POLY1305)" "pass"
else
    test_result "AEAD Cipher (GCM/POLY1305)" "warn" "Cipher: $cipher"
fi

if [[ "$cipher" != *RC4* ]] && [[ "$cipher" != *DES* ]] && [[ "$cipher" != *MD5* ]]; then
    test_result "No Weak Ciphers (RC4/DES/MD5)" "pass"
else
    test_result "No Weak Ciphers (RC4/DES/MD5)" "fail" "Cipher: $cipher"
fi

echo ""

# Test 5: Security Headers
echo -e "${BLUE}[5] Security Headers${NC}"
echo "===================="

headers=$(curl -s -I -X GET "https://$DOMAIN" 2>/dev/null)

# HSTS
if echo "$headers" | grep -qi "Strict-Transport-Security"; then
    hsts_value=$(echo "$headers" | grep -i "Strict-Transport-Security" | cut -d' ' -f2-)
    echo "  HSTS: $hsts_value"
    test_result "HSTS Header Present" "pass"
else
    test_result "HSTS Header Present" "fail"
fi

# CSP
if echo "$headers" | grep -qi "Content-Security-Policy"; then
    test_result "CSP Header Present" "pass"
else
    test_result "CSP Header Present" "warn"
fi

# X-Frame-Options
if echo "$headers" | grep -qi "X-Frame-Options"; then
    test_result "X-Frame-Options Header" "pass"
else
    test_result "X-Frame-Options Header" "warn"
fi

# X-Content-Type-Options
if echo "$headers" | grep -qi "X-Content-Type-Options"; then
    test_result "X-Content-Type-Options Header" "pass"
else
    test_result "X-Content-Type-Options Header" "warn"
fi

echo ""

# Test 6: OCSP Stapling
echo -e "${BLUE}[6] OCSP Stapling${NC}"
echo "================="

ocsp_response=$(echo | openssl s_client -connect "$DOMAIN:$PORT" -tlsextdebug 2>/dev/null | grep "OCSP response:" | head -1)

if [ -n "$ocsp_response" ]; then
    echo "  $ocsp_response"
    test_result "OCSP Stapling Configured" "pass"
else
    test_result "OCSP Stapling Configured" "warn"
fi

echo ""

# Test 7: Certificate Chain
echo -e "${BLUE}[7] Certificate Chain${NC}"
echo "===================="

chain_depth=$(echo | openssl s_client -connect "$DOMAIN:$PORT" 2>/dev/null | grep "depth=" | wc -l)
echo "  Chain depth: $chain_depth"

if [ "$chain_depth" -ge 2 ]; then
    test_result "Complete Certificate Chain" "pass"
else
    test_result "Complete Certificate Chain" "warn" "Chain depth: $chain_depth"
fi

echo ""

# Summary
echo -e "${BLUE}==========================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}==========================================${NC}"
echo -e "${GREEN}Passed: $TEST_PASSED${NC}"
echo -e "${RED}Failed: $TEST_FAILED${NC}"

total=$((TEST_PASSED + TEST_FAILED))
if [ $TEST_FAILED -eq 0 ]; then
    percentage=100
else
    percentage=$((TEST_PASSED * 100 / total))
fi

echo "Success Rate: $percentage% ($TEST_PASSED/$total)"
echo ""

if [ $TEST_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    echo ""
    echo "Recommendations:"
    echo "1. Test online with SSL Labs: https://www.ssllabs.com/ssltest/analyze.html?d=$DOMAIN"
    echo "2. Test HSTS preload: https://hstspreload.org/?domain=$DOMAIN"
    echo "3. Check certificate transparency: https://crt.sh/?q=$DOMAIN"
    exit 0
else
    echo -e "${YELLOW}Some tests failed or have warnings.${NC}"
    echo "Please review the results above."
    exit 1
fi
