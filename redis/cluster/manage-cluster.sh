#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

show_help() {
    cat << EOF
${BLUE}Redis Cluster Management Tool${NC}

Usage: ./manage-cluster.sh [command]

Commands:
  ${GREEN}start${NC}     - Start cluster
  ${GREEN}stop${NC}      - Stop cluster
  ${GREEN}init${NC}      - Initialize cluster
  ${GREEN}status${NC}    - Show status
  ${GREEN}monitor${NC}   - Monitor cluster
  ${GREEN}test${NC}      - Run tests
  ${GREEN}failover${NC}  - Test failover
  ${GREEN}help${NC}      - Show this help

EOF
}

start_cluster() {
    echo -e "${BLUE}Starting Redis Cluster...${NC}\n"
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" up -d
    echo -e "${CYAN}Waiting for nodes to start...${NC}"
    sleep 30
    echo -e "${GREEN}Cluster started. Next: ./manage-cluster.sh init${NC}"
}

stop_cluster() {
    echo -e "${BLUE}Stopping Redis Cluster...${NC}\n"
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" down
    echo -e "${GREEN}Cluster stopped${NC}"
}

init_cluster() {
    echo -e "${BLUE}Initializing cluster...${NC}\n"
    bash "$SCRIPT_DIR/init-cluster.sh"
}

show_status() {
    echo -e "${BLUE}Redis Cluster Status${NC}\n"
    docker-compose -f "$SCRIPT_DIR/docker-compose.yml" ps
    echo ""
    redis-cli -h 127.0.0.1 -p 6379 CLUSTER INFO 2>/dev/null | grep -E "cluster_state|cluster_slots"
}

monitor_cluster() {
    bash "$SCRIPT_DIR/monitor-cluster.sh"
}

test_cluster() {
    bash "$SCRIPT_DIR/test-cluster.sh"
}

test_failover() {
    bash "$SCRIPT_DIR/failover-test.sh"
}

main() {
    local command=$1
    
    case "$command" in
        start) start_cluster ;;
        stop) stop_cluster ;;
        init) init_cluster ;;
        status) show_status ;;
        monitor) monitor_cluster ;;
        test) test_cluster ;;
        failover) test_failover ;;
        help|--help|-h|"") show_help ;;
        *) echo -e "${RED}Unknown command: $command${NC}"; show_help; exit 1 ;;
    esac
}

main "$@"
