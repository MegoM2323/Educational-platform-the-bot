#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Redis Cluster Test Suite${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}\n"

TESTS_TOTAL=0
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name=$1
    local test_cmd=$2
    
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
    echo -ne "${CYAN}Test $TESTS_TOTAL: $test_name... ${NC}"
    
    if eval "$test_cmd" > /dev/null 2>&1; then
        echo -e "${GREEN}PASSED${NC}"
        TESTS_PASSED=$((TESTS_PASSED + 1))
    else
        echo -e "${RED}FAILED${NC}"
        TESTS_FAILED=$((TESTS_FAILED + 1))
    fi
}

echo -e "${YELLOW}=== Connectivity Tests ===${NC}\n"
run_test "Master 1 (6379)" "timeout 2 redis-cli -h 127.0.0.1 -p 6379 ping"
run_test "Master 2 (6380)" "timeout 2 redis-cli -h 127.0.0.1 -p 6380 ping"
run_test "Master 3 (6381)" "timeout 2 redis-cli -h 127.0.0.1 -p 6381 ping"
run_test "Replica 1 (6382)" "timeout 2 redis-cli -h 127.0.0.1 -p 6382 ping"
run_test "Replica 2 (6383)" "timeout 2 redis-cli -h 127.0.0.1 -p 6383 ping"
run_test "Replica 3 (6384)" "timeout 2 redis-cli -h 127.0.0.1 -p 6384 ping"

echo ""
echo -e "${YELLOW}=== Cluster State Tests ===${NC}\n"
run_test "Cluster state OK" "[ \"ok\" = \"\$(redis-cli -h 127.0.0.1 -p 6379 CLUSTER INFO 2>/dev/null | grep 'cluster_state:' | cut -d: -f2 | tr -d '\\r')\" ]"
run_test "All slots assigned" "[ \"16384\" = \"\$(redis-cli -h 127.0.0.1 -p 6379 CLUSTER INFO 2>/dev/null | grep 'cluster_slots_assigned:' | cut -d: -f2 | tr -d '\\r')\" ]"

echo ""
echo -e "${YELLOW}=== Data Operation Tests ===${NC}\n"
run_test "SET key works" "redis-cli -h 127.0.0.1 -p 6379 SET test_key 'test_value'"
run_test "GET key works" "[ \"test_value\" = \"\$(redis-cli -h 127.0.0.1 -p 6379 GET test_key)\" ]"
run_test "DEL key works" "redis-cli -h 127.0.0.1 -p 6379 DEL test_key"
run_test "INCR works" "redis-cli -h 127.0.0.1 -p 6379 INCR counter"

echo ""
echo -e "${YELLOW}=== Latency Test ===${NC}\n"

local total_latency=0
local min_latency=999999
local max_latency=0

for i in {1..100}; do
    local start=$(date +%s%N)
    redis-cli -h 127.0.0.1 -p 6379 PING > /dev/null 2>&1
    local end=$(date +%s%N)
    local lat=$(( (end - start) / 1000000 ))
    
    if [ "$lat" -lt "$min_latency" ]; then
        min_latency=$lat
    fi
    if [ "$lat" -gt "$max_latency" ]; then
        max_latency=$lat
    fi
    
    total_latency=$((total_latency + lat))
done

local avg_latency=$((total_latency / 100))

echo -e "${CYAN}Average latency: ${avg_latency}ms${NC}"
echo -e "${CYAN}Min: ${min_latency}ms, Max: ${max_latency}ms${NC}"

if [ "$avg_latency" -lt 5 ]; then
    echo -e "${GREEN}✓ Latency test PASSED (<5ms)${NC}"
    TESTS_PASSED=$((TESTS_PASSED + 1))
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
else
    echo -e "${YELLOW}⚠ Latency: ${avg_latency}ms${NC}"
    TESTS_TOTAL=$((TESTS_TOTAL + 1))
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Test Summary${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${CYAN}Total: $TESTS_TOTAL | ${GREEN}Passed: $TESTS_PASSED${NC} | ${RED}Failed: $TESTS_FAILED${NC}"

local success_rate=$((TESTS_PASSED * 100 / TESTS_TOTAL))
echo -e "${CYAN}Success rate: ${success_rate}%${NC}"

if [ "$TESTS_FAILED" -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed${NC}"
    exit 1
fi
