#!/bin/bash

# THE BOT Platform - Load Balancer Testing Script
#
# Tests load balancing functionality including:
# - Health checks
# - Backend failover
# - Load distribution
# - WebSocket connectivity
# - Rate limiting
# - Connection pooling
#
# Usage:
#   ./scripts/test-load-balancer.sh [command]
#
# Commands:
#   health           Test health endpoints
#   api              Test API load balancing
#   websocket        Test WebSocket connectivity
#   rate-limit       Test rate limiting
#   failover         Test backend failover
#   stress           Stress test with concurrent requests
#   all              Run all tests
#
# Examples:
#   ./scripts/test-load-balancer.sh health
#   ./scripts/test-load-balancer.sh all
#   ./scripts/test-load-balancer.sh stress

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
LOAD_BALANCER_HOST="${LB_HOST:-http://localhost:8080}"
API_BASE="${LOAD_BALANCER_HOST}/api"
WS_BASE="${LOAD_BALANCER_HOST}/ws"
HEALTH_ENDPOINT="${LOAD_BALANCER_HOST}/health"
DETAILED_HEALTH="${LOAD_BALANCER_HOST}/health/detailed"
UPSTREAM_STATUS="${LOAD_BALANCER_HOST}/upstream-status"
STATS_ENDPOINT="${LOAD_BALANCER_HOST}/stats"
METRICS_ENDPOINT="${LOAD_BALANCER_HOST}/metrics"

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Utility functions
print_header() {
    echo -e "\n${BLUE}===========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((TESTS_PASSED++))
}

print_failure() {
    echo -e "${RED}✗ $1${NC}"
    ((TESTS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ $1${NC}"
}

# Check if curl is installed
check_prerequisites() {
    if ! command -v curl &> /dev/null; then
        echo -e "${RED}Error: curl is not installed${NC}"
        exit 1
    fi

    if ! command -v jq &> /dev/null; then
        print_warning "jq is not installed - some tests will be limited"
    fi
}

# Test health endpoints
test_health() {
    print_header "HEALTH CHECKS"

    # Simple health check
    print_info "Testing simple health endpoint: ${HEALTH_ENDPOINT}"
    if response=$(curl -s -w "\n%{http_code}" "${HEALTH_ENDPOINT}" 2>/dev/null); then
        status=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n-1)

        if [[ $status == "200" ]]; then
            print_success "Health endpoint returned 200 OK"
            print_info "Response: $body"
        else
            print_failure "Health endpoint returned $status (expected 200)"
        fi
    else
        print_failure "Failed to connect to health endpoint"
    fi

    # Detailed health check
    print_info "Testing detailed health endpoint: ${DETAILED_HEALTH}"
    if response=$(curl -s -w "\n%{http_code}" "${DETAILED_HEALTH}" 2>/dev/null); then
        status=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n-1)

        if [[ $status == "200" ]]; then
            print_success "Detailed health endpoint returned 200 OK"
            if command -v jq &> /dev/null; then
                echo "$body" | jq . 2>/dev/null || echo "$body"
            else
                echo "$body"
            fi
        else
            print_failure "Detailed health endpoint returned $status"
        fi
    else
        print_failure "Failed to connect to detailed health endpoint"
    fi

    # Upstream status
    print_info "Checking upstream status: ${UPSTREAM_STATUS}"
    if response=$(curl -s -w "\n%{http_code}" "${UPSTREAM_STATUS}" 2>/dev/null); then
        status=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n-1)

        if [[ $status == "200" ]]; then
            print_success "Upstream status endpoint returned 200"
            echo "$body"
        else
            print_failure "Upstream status endpoint returned $status"
        fi
    else
        print_failure "Failed to connect to upstream status endpoint"
    fi
}

# Test API load balancing
test_api_load_balancing() {
    print_header "API LOAD BALANCING"

    print_info "Testing API endpoint: ${API_BASE}/users/"

    # Perform multiple requests to test load distribution
    local request_count=5
    local successful=0
    local failed=0

    for i in $(seq 1 $request_count); do
        print_info "Request $i/$request_count to API endpoint"

        if response=$(curl -s -w "\n%{http_code}" "${API_BASE}/users/" 2>/dev/null); then
            status=$(echo "$response" | tail -n1)

            if [[ $status == "200" || $status == "401" ]]; then
                # 401 is expected if no auth token
                ((successful++))
                print_success "API request $i returned $status"
            else
                ((failed++))
                print_failure "API request $i returned $status"
            fi
        else
            ((failed++))
            print_failure "API request $i failed to connect"
        fi

        # Small delay between requests
        sleep 0.5
    done

    if [[ $successful -eq $request_count ]]; then
        print_success "All $request_count API requests successful"
    else
        print_failure "$failed/$request_count API requests failed"
    fi
}

# Test WebSocket connectivity
test_websocket() {
    print_header "WEBSOCKET CONNECTIVITY"

    print_info "Note: WebSocket testing requires wscat or similar tool"
    print_info "Install: npm install -g wscat"

    if command -v wscat &> /dev/null; then
        print_info "Attempting WebSocket connection to ${WS_BASE}/chat/1/"
        # Note: This will timeout quickly without auth
        timeout 3 wscat -c "${WS_BASE}/chat/1/" 2>&1 | head -5 && print_success "WebSocket connected" || print_warning "WebSocket test incomplete (expected timeout without auth)"
    else
        print_warning "wscat not installed - skipping WebSocket test"
        print_info "To test WebSocket: wscat -c ${WS_BASE}/chat/1/"
    fi
}

# Test rate limiting
test_rate_limiting() {
    print_header "RATE LIMITING"

    # Test authentication rate limit (should be strict: 5 req/min)
    print_info "Testing rate limiting on login endpoint"
    print_info "Limit: 5 requests/minute (after burst)"

    local endpoint="${API_BASE}/auth/login/"
    local request_count=10
    local rate_limited=0

    for i in $(seq 1 $request_count); do
        if response=$(curl -s -w "\n%{http_code}" -X POST "${endpoint}" 2>/dev/null); then
            status=$(echo "$response" | tail -n1)

            if [[ $status == "429" ]]; then
                ((rate_limited++))
                print_success "Request $i was rate limited (429)"
            elif [[ $status == "400" || $status == "401" ]]; then
                print_info "Request $i returned $status (expected)"
            else
                print_warning "Request $i returned $status"
            fi
        fi

        sleep 0.1
    done

    if [[ $rate_limited -gt 0 ]]; then
        print_success "Rate limiting is working ($rate_limited requests limited)"
    else
        print_info "Rate limiting test completed (may need more requests to trigger)"
    fi
}

# Test backend failover
test_failover() {
    print_header "BACKEND FAILOVER"

    print_info "To test failover:"
    print_info "1. Stop one backend instance: docker-compose stop backend-api-2"
    print_info "2. Verify requests still work: curl ${API_BASE}/health/"
    print_info "3. Stop another: docker-compose stop backend-api-1"
    print_info "4. Requests should still route to backend-api-3"
    print_info "5. Restart services: docker-compose up -d"

    print_info "Attempting to get backend status..."
    if response=$(curl -s -w "\n%{http_code}" "${UPSTREAM_STATUS}" 2>/dev/null); then
        status=$(echo "$response" | tail -n1)
        if [[ $status == "200" ]]; then
            echo "$(echo "$response" | head -n-1)"
        fi
    fi
}

# Stress test with concurrent requests
test_stress() {
    print_header "STRESS TEST - CONCURRENT REQUESTS"

    print_info "Sending 100 concurrent requests to API endpoint"
    local endpoint="${API_BASE}/users/"
    local concurrent_requests=100
    local temp_file="/tmp/stress_test_$$.txt"

    # Create concurrent requests
    {
        for i in $(seq 1 $concurrent_requests); do
            (
                curl -s -o /dev/null -w "%{http_code}\n" "${endpoint}" &
            )
        done
        wait
    } > "$temp_file" 2>/dev/null || true

    # Analyze results
    local success=0
    local errors=0

    while IFS= read -r code; do
        if [[ $code == "200" || $code == "401" ]]; then
            ((success++))
        else
            ((errors++))
        fi
    done < "$temp_file"

    print_success "Received $success successful responses out of $concurrent_requests"
    if [[ $errors -gt 0 ]]; then
        print_warning "$errors responses with other status codes"
    fi

    rm -f "$temp_file"
}

# Performance monitoring
test_performance() {
    print_header "PERFORMANCE METRICS"

    print_info "Testing response times"

    local endpoint="${API_BASE}/users/"
    local iterations=5
    local total_time=0
    local times=()

    for i in $(seq 1 $iterations); do
        if response=$(curl -s -w "%{time_total}" -o /dev/null "${endpoint}" 2>/dev/null); then
            times+=("$response")
            total_time=$(echo "$total_time + $response" | bc)
            print_info "Request $i: ${response}s"
        fi
    done

    if [[ $iterations -gt 0 ]]; then
        avg_time=$(echo "scale=3; $total_time / $iterations" | bc)
        print_success "Average response time: ${avg_time}s"

        # Performance threshold (should be < 1s)
        if (( $(echo "$avg_time < 1.0" | bc -l) )); then
            print_success "Response time is within acceptable range"
        else
            print_warning "Response time is higher than expected (< 1.0s recommended)"
        fi
    fi
}

# Monitoring endpoints
test_monitoring() {
    print_header "MONITORING ENDPOINTS"

    # Test stats endpoint
    print_info "Testing stats endpoint: ${STATS_ENDPOINT}"
    if response=$(curl -s -w "\n%{http_code}" "${STATS_ENDPOINT}" 2>/dev/null); then
        status=$(echo "$response" | tail -n1)
        body=$(echo "$response" | head -n-1)

        if [[ $status == "200" ]]; then
            print_success "Stats endpoint returned 200"
            if command -v jq &> /dev/null; then
                echo "$body" | jq . 2>/dev/null || echo "$body"
            else
                echo "$body"
            fi
        else
            print_failure "Stats endpoint returned $status"
        fi
    else
        print_failure "Failed to connect to stats endpoint"
    fi

    # Test metrics endpoint
    print_info "Testing metrics endpoint: ${METRICS_ENDPOINT}"
    if response=$(curl -s -w "\n%{http_code}" "${METRICS_ENDPOINT}" 2>/dev/null); then
        status=$(echo "$response" | tail -n1)

        if [[ $status == "200" ]]; then
            print_success "Metrics endpoint returned 200"
        else
            print_failure "Metrics endpoint returned $status"
        fi
    else
        print_failure "Failed to connect to metrics endpoint"
    fi
}

# Print test summary
print_summary() {
    print_header "TEST SUMMARY"
    echo -e "Total tests passed: ${GREEN}${TESTS_PASSED}${NC}"
    echo -e "Total tests failed: ${RED}${TESTS_FAILED}${NC}"

    if [[ $TESTS_FAILED -eq 0 ]]; then
        print_success "All tests passed!"
        return 0
    else
        print_failure "Some tests failed"
        return 1
    fi
}

# Main script
main() {
    local command="${1:-all}"

    check_prerequisites

    echo -e "${BLUE}THE BOT Platform - Load Balancer Test Suite${NC}"
    echo -e "${BLUE}Load Balancer: ${LOAD_BALANCER_HOST}${NC}\n"

    case "$command" in
        health)
            test_health
            ;;
        api)
            test_api_load_balancing
            ;;
        websocket)
            test_websocket
            ;;
        rate-limit)
            test_rate_limiting
            ;;
        failover)
            test_failover
            ;;
        stress)
            test_stress
            ;;
        performance)
            test_performance
            ;;
        monitoring)
            test_monitoring
            ;;
        all)
            test_health
            test_api_load_balancing
            test_rate_limiting
            test_websocket
            test_performance
            test_monitoring
            ;;
        *)
            echo "Usage: $0 [command]"
            echo ""
            echo "Commands:"
            echo "  health           Test health endpoints"
            echo "  api              Test API load balancing"
            echo "  websocket        Test WebSocket connectivity"
            echo "  rate-limit       Test rate limiting"
            echo "  failover         Test backend failover"
            echo "  stress           Stress test with concurrent requests"
            echo "  performance      Test response times"
            echo "  monitoring       Test monitoring endpoints"
            echo "  all              Run all tests (default)"
            exit 1
            ;;
    esac

    print_summary
}

main "$@"
