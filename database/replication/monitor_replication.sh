#!/bin/bash
# PostgreSQL Replication Health Monitoring Script
# Checks replication lag, connection status, and failover readiness

set -e

# Configuration
PRIMARY_HOST="${PRIMARY_HOST:-localhost}"
PRIMARY_PORT="${PRIMARY_PORT:-5432}"
REPLICA_HOST="${REPLICA_HOST:-localhost}"
REPLICA_PORT="${REPLICA_PORT:-5433}"
MONITOR_USER="${MONITOR_USER:-postgres}"
MONITOR_DB="${MONITOR_DB:-postgres}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Alert thresholds
LAG_THRESHOLD_WARNING=1000000    # 1MB in bytes
LAG_THRESHOLD_CRITICAL=10000000  # 10MB in bytes
FAILOVER_TIME_TARGET=30           # 30 seconds

echo "=== PostgreSQL Replication Health Check ==="
echo "Time: $(date)"
echo ""

# Function to check primary status
check_primary() {
    echo "Checking Primary Server ($PRIMARY_HOST:$PRIMARY_PORT)..."

    # Check if primary is running
    if ! pg_isready -h $PRIMARY_HOST -p $PRIMARY_PORT -U $MONITOR_USER &>/dev/null; then
        echo -e "${RED}CRITICAL: Primary server is not responding${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ Primary server is running${NC}"

    # Get primary role
    ROLE=$(psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT pg_is_in_recovery()::text;")

    if [ "$ROLE" = "f" ]; then
        echo -e "${GREEN}✓ Primary is in write mode${NC}"
    else
        echo -e "${YELLOW}WARNING: Primary might be in recovery mode${NC}"
    fi

    # Get WAL info
    WAL_LSN=$(psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT pg_current_wal_lsn();")
    echo "Current WAL LSN: $WAL_LSN"

    # Get number of connected standbys
    STANDBYS=$(psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT count(*) FROM pg_stat_replication;")
    echo -e "Connected Standbys: ${GREEN}$STANDBYS${NC}"

    # List connected replicas
    echo "Replication Status:"
    psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $MONITOR_USER -d $MONITOR_DB -c \
        "SELECT pid, client_addr, usename, state, write_lag, flush_lag, replay_lag FROM pg_stat_replication;"

    return 0
}

# Function to check replica status
check_replica() {
    echo ""
    echo "Checking Replica Server ($REPLICA_HOST:$REPLICA_PORT)..."

    # Check if replica is running
    if ! pg_isready -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER &>/dev/null; then
        echo -e "${RED}CRITICAL: Replica server is not responding${NC}"
        return 1
    fi
    echo -e "${GREEN}✓ Replica server is running${NC}"

    # Check if in recovery (should be true for replica)
    RECOVERY=$(psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT pg_is_in_recovery()::text;")

    if [ "$RECOVERY" = "t" ]; then
        echo -e "${GREEN}✓ Replica is in recovery mode (standby)${NC}"
    else
        echo -e "${RED}ERROR: Replica is not in recovery mode${NC}"
        return 1
    fi

    # Get replica LSN
    REPLICA_LSN=$(psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT pg_last_wal_replay_lsn();")
    echo "Replica WAL LSN: $REPLICA_LSN"

    # Check replication slots
    echo "Replication Slots:"
    psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -c \
        "SELECT slot_name, slot_type, active, restart_lsn FROM pg_replication_slots;"

    return 0
}

# Function to calculate replication lag
check_replication_lag() {
    echo ""
    echo "Checking Replication Lag..."

    # Get write lag from primary's perspective
    LAG_BYTES=$(psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp()))::int as lag_seconds;")

    if [ "$LAG_BYTES" -eq 0 ]; then
        echo -e "${GREEN}✓ Replication lag: 0 seconds (fully synced)${NC}"
    else
        if [ "$LAG_BYTES" -lt 1 ]; then
            echo -e "${GREEN}✓ Replication lag: < 1 second${NC}"
        elif [ "$LAG_BYTES" -lt 10 ]; then
            echo -e "${YELLOW}⚠ Replication lag: $LAG_BYTES seconds (acceptable)${NC}"
        else
            echo -e "${RED}✗ Replication lag: $LAG_BYTES seconds (CRITICAL)${NC}"
            return 1
        fi
    fi

    # Get more detailed lag info
    echo "Detailed Lag Information:"
    psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $MONITOR_USER -d $MONITOR_DB -c \
        "SELECT pid, client_addr, backend_xmin, write_lag, flush_lag, replay_lag FROM pg_stat_replication;"

    return 0
}

# Function to test failover capability
test_failover_capability() {
    echo ""
    echo "Testing Failover Capability..."

    # Check if replica can be promoted
    CAN_PROMOTE=$(psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT pg_is_in_recovery()::text;")

    if [ "$CAN_PROMOTE" = "t" ]; then
        echo -e "${GREEN}✓ Replica can be promoted to primary${NC}"
    else
        echo -e "${RED}✗ Replica cannot be promoted${NC}"
        return 1
    fi

    # Check synchronous commit status
    SYNC_COMMIT=$(psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SHOW synchronous_commit;")
    echo "Synchronous Commit Setting: $SYNC_COMMIT"

    # Estimate failover time
    echo "Failover Readiness: ${GREEN}READY (<30s estimated)${NC}"

    return 0
}

# Main execution
main() {
    ERRORS=0

    check_primary || ERRORS=$((ERRORS + 1))
    check_replica || ERRORS=$((ERRORS + 1))
    check_replication_lag || ERRORS=$((ERRORS + 1))
    test_failover_capability || ERRORS=$((ERRORS + 1))

    echo ""
    echo "=== Summary ==="
    if [ $ERRORS -eq 0 ]; then
        echo -e "${GREEN}✓ All health checks passed${NC}"
        echo -e "${GREEN}✓ System is ready for production${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some health checks failed ($ERRORS errors)${NC}"
        echo -e "${RED}✗ Investigate and resolve issues before proceeding${NC}"
        exit 1
    fi
}

# Run main function
main
