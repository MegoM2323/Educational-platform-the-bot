#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "=================================================="
echo "Redis Cluster Initialization"
echo "=================================================="
echo ""

NODES=(
    "127.0.0.1:6379"
    "127.0.0.1:6380"
    "127.0.0.1:6381"
    "127.0.0.1:6382"
    "127.0.0.1:6383"
    "127.0.0.1:6384"
)

echo -e "${YELLOW}[1/5] Checking Redis CLI availability...${NC}"
if ! command -v redis-cli &> /dev/null; then
    echo -e "${RED}❌ redis-cli not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ redis-cli found${NC}\n"

echo -e "${YELLOW}[2/5] Checking node connectivity...${NC}"
for node in "${NODES[@]}"; do
    IFS=':' read -r host port <<< "$node"
    if timeout 2 redis-cli -h "$host" -p "$port" ping > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Node $node reachable${NC}"
    else
        echo -e "${RED}❌ Node $node not reachable${NC}"
        exit 1
    fi
done
echo ""

echo -e "${YELLOW}[3/5] Flushing existing data...${NC}"
echo -e "${RED}⚠️  WARNING: This will delete all existing data!${NC}"
echo "Type 'yes' to continue:"
read -r confirmation
if [ "$confirmation" != "yes" ]; then
    echo "Aborted."
    exit 0
fi

for node in "${NODES[@]}"; do
    IFS=':' read -r host port <<< "$node"
    redis-cli -h "$host" -p "$port" FLUSHDB > /dev/null 2>&1
    echo -e "${GREEN}✓ Flushed node $node${NC}"
done
echo ""

echo -e "${YELLOW}[4/5] Creating Redis cluster...${NC}"
NODE_LIST=""
for node in "${NODES[@]}"; do
    NODE_LIST="$NODE_LIST $node"
done

if timeout 30 redis-cli --cluster create $NODE_LIST --cluster-replicas 1 --cluster-yes 2>/dev/null; then
    echo -e "${GREEN}✓ Cluster created successfully${NC}"
else
    echo -e "${RED}❌ Failed to create cluster${NC}"
    exit 1
fi
echo ""

echo -e "${YELLOW}[5/5] Verifying cluster configuration...${NC}\n"

echo -e "${YELLOW}Cluster Info:${NC}"
redis-cli -h 127.0.0.1 -p 6379 CLUSTER INFO 2>/dev/null | grep -E "cluster_state|cluster_slots"

echo ""
echo -e "${YELLOW}Cluster Nodes:${NC}"
redis-cli -h 127.0.0.1 -p 6379 CLUSTER NODES 2>/dev/null | head -10

echo ""
echo -e "${GREEN}=================================================${NC}"
echo -e "${GREEN}Redis Cluster initialized successfully!${NC}"
echo -e "${GREEN}=================================================${NC}"
