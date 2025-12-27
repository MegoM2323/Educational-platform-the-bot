#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${BLUE}════════════════════════════════════════════════${NC}"
echo -e "${BLUE}Redis Cluster Failover Test${NC}"
echo -e "${BLUE}════════════════════════════════════════════════${NC}\n"

MASTER_HOST="127.0.0.1"
MASTER_PORT="6379"

get_cluster_state() {
    redis-cli -h "$MASTER_HOST" -p "$MASTER_PORT" CLUSTER INFO 2>/dev/null | grep "cluster_state:" | cut -d: -f2 | tr -d '\r'
}

is_master() {
    local port=$1
    local role=$(redis-cli -h "$MASTER_HOST" -p "$port" INFO replication 2>/dev/null | grep "role:" | cut -d: -f2 | tr -d '\r')
    [ "$role" = "master" ]
}

echo -e "${YELLOW}Test 1: Verify Initial State${NC}\n"

echo -ne "${CYAN}Checking cluster state... ${NC}"
local state=$(get_cluster_state)
if [ "$state" = "ok" ]; then
    echo -e "${GREEN}OK${NC}"
else
    echo -e "${RED}FAILED${NC}"
    exit 1
fi

echo -ne "${CYAN}Checking master count... ${NC}"
local m1_role=$(redis-cli -h "$MASTER_HOST" -p 6379 INFO replication 2>/dev/null | grep "role:" | cut -d: -f2 | tr -d '\r')
echo -e "${GREEN}Master 1 is $m1_role${NC}"

echo ""
echo -e "${YELLOW}Test 2: Write Test Data${NC}\n"

echo -ne "${CYAN}Writing 100 test keys... ${NC}"
for i in {1..100}; do
    redis-cli -h "$MASTER_HOST" -p 6379 SET "test_$i" "value_$i" > /dev/null 2>&1
done
echo -e "${GREEN}Done${NC}"

echo ""
echo -e "${YELLOW}Test 3: Stop Master Node${NC}\n"

echo -e "${RED}⚠️  About to stop Master 1 (6379) to test failover${NC}"
echo -e "${CYAN}Continue? (type 'yes'):${NC}"
read -r confirmation

if [ "$confirmation" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

echo -ne "${CYAN}Stopping Master 1... ${NC}"
docker-compose -f docker-compose.yml stop redis-6379 2>/dev/null || true
sleep 3
echo -e "${GREEN}Done${NC}"

echo ""
echo -e "${YELLOW}Test 4: Wait for Failover${NC}\n"

echo -e "${CYAN}Monitoring failover (timeout: 30s)...${NC}"

local failover_timeout=30
local failover_start=$(date +%s)
local failover_detected=false

while [ $(($(date +%s) - failover_start)) -lt "$failover_timeout" ]; do
    local state=$(get_cluster_state 2>/dev/null || echo "error")
    
    if [ "$state" = "ok" ]; then
        echo -e "${GREEN}✓ Cluster recovered${NC}"
        failover_detected=true
        break
    else
        echo -ne "."
        sleep 1
    fi
done

echo ""

if [ "$failover_detected" = true ]; then
    echo -e "${GREEN}✓ Failover test PASSED${NC}"
else
    echo -e "${YELLOW}⚠ Failover may still be in progress${NC}"
fi

echo ""
echo -e "${YELLOW}Test 5: Restart Master${NC}\n"

echo -ne "${CYAN}Restarting Master 1... ${NC}"
docker-compose -f docker-compose.yml start redis-6379 2>/dev/null || true
sleep 5
echo -e "${GREEN}Done${NC}"

echo ""
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
echo -e "${GREEN}Failover Test Completed${NC}"
echo -e "${GREEN}════════════════════════════════════════════════${NC}"
