#!/bin/bash

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

MASTER_HOST="127.0.0.1"
MASTER_PORT="6379"

print_header() {
    echo -e "\n${BLUE}════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}════════════════════════════════════════════════${NC}\n"
}

check_cluster_health() {
    print_header "Cluster Health Status"
    
    local state=$(redis-cli -h "$MASTER_HOST" -p "$MASTER_PORT" CLUSTER INFO 2>/dev/null | grep "cluster_state:" | cut -d: -f2 | tr -d '\r')
    local slots=$(redis-cli -h "$MASTER_HOST" -p "$MASTER_PORT" CLUSTER INFO 2>/dev/null | grep "cluster_slots_assigned:" | cut -d: -f2 | tr -d '\r')
    
    if [ "$state" = "ok" ]; then
        echo -e "${GREEN}✓ Cluster State: OK${NC}"
    else
        echo -e "${RED}❌ Cluster State: $state${NC}"
    fi
    
    echo -e "${GREEN}✓ Slots Assigned: $slots/16384${NC}"
}

list_cluster_nodes() {
    print_header "Cluster Nodes"
    redis-cli -h "$MASTER_HOST" -p "$MASTER_PORT" CLUSTER NODES 2>/dev/null | while read -r line; do
        node_id=$(echo "$line" | awk '{print substr($1, 1, 8)}')
        node_addr=$(echo "$line" | awk '{print $2}')
        node_flags=$(echo "$line" | awk '{print $3}')
        
        if [[ "$node_flags" == *"master"* ]]; then
            echo -e "${GREEN}$node_id | $node_addr | MASTER${NC}"
        elif [[ "$node_flags" == *"slave"* ]]; then
            echo -e "${YELLOW}$node_id | $node_addr | REPLICA${NC}"
        fi
    done
}

show_memory_usage() {
    print_header "Memory Usage"
    local ports=(6379 6380 6381 6382 6383 6384)
    
    for port in "${ports[@]}"; do
        local used=$(redis-cli -h 127.0.0.1 -p "$port" INFO memory 2>/dev/null | grep "used_memory_human:" | cut -d: -f2 | tr -d '\r')
        [ -n "$used" ] && echo -e "${CYAN}Port $port:${NC} $used"
    done
}

show_cache_stats() {
    print_header "Cache Hit Rate"
    local port=6379
    local stats=$(redis-cli -h 127.0.0.1 -p "$port" INFO stats 2>/dev/null)
    
    if [ -n "$stats" ]; then
        local hits=$(echo "$stats" | grep "keyspace_hits:" | cut -d: -f2 | tr -d '\r')
        local misses=$(echo "$stats" | grep "keyspace_misses:" | cut -d: -f2 | tr -d '\r')
        
        if [ -n "$hits" ] && [ -n "$misses" ]; then
            local total=$((hits + misses))
            if [ "$total" -gt 0 ]; then
                local rate=$((hits * 100 / total))
                if [ "$rate" -ge 95 ]; then
                    echo -e "${GREEN}Hit Rate: ${rate}%${NC}"
                else
                    echo -e "${YELLOW}Hit Rate: ${rate}%${NC}"
                fi
            fi
        fi
    fi
}

show_latency() {
    print_header "Command Latency Test"
    
    local total=0
    local count=10
    
    for i in $(seq 1 $count); do
        local start=$(date +%s%N)
        redis-cli -h 127.0.0.1 -p 6379 PING > /dev/null 2>&1
        local end=$(date +%s%N)
        local lat=$(( (end - start) / 1000000 ))
        total=$((total + lat))
    done
    
    local avg=$((total / count))
    if [ "$avg" -lt 5 ]; then
        echo -e "${GREEN}Average latency: ${avg}ms (Excellent)${NC}"
    else
        echo -e "${YELLOW}Average latency: ${avg}ms${NC}"
    fi
}

main() {
    echo -e "${GREEN}════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}Redis Cluster Monitor${NC}"
    echo -e "${GREEN}════════════════════════════════════════════════${NC}\n"
    
    while true; do
        clear
        check_cluster_health
        list_cluster_nodes
        show_memory_usage
        show_cache_stats
        show_latency
        
        echo ""
        echo -e "${YELLOW}Refreshing in 5 seconds (Ctrl+C to exit)${NC}"
        sleep 5
    done
}

main
