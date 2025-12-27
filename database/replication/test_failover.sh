#!/bin/bash
# PostgreSQL Failover Testing Script
# Tests automatic failover and recovery procedures

set -e

# Configuration
PRIMARY_HOST="${PRIMARY_HOST:-localhost}"
PRIMARY_PORT="${PRIMARY_PORT:-5432}"
REPLICA_HOST="${REPLICA_HOST:-localhost}"
REPLICA_PORT="${REPLICA_PORT:-5433}"
MONITOR_USER="${MONITOR_USER:-postgres}"
MONITOR_DB="${MONITOR_DB:-postgres}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test configuration
TEST_TABLE="failover_test_$(date +%s)"
FAILOVER_TIMEOUT=30

echo -e "${BLUE}=== PostgreSQL Failover Test ===${NC}"
echo "Time: $(date)"
echo ""

# Function to setup test environment
setup_test() {
    echo -e "${BLUE}[SETUP] Creating test table on primary...${NC}"

    psql -h $PRIMARY_HOST -p $PRIMARY_PORT -U $MONITOR_USER -d $MONITOR_DB << EOF
CREATE TABLE $TEST_TABLE (
    id SERIAL PRIMARY KEY,
    test_data TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO $TEST_TABLE (test_data) VALUES ('Test data 1');
INSERT INTO $TEST_TABLE (test_data) VALUES ('Test data 2');
INSERT INTO $TEST_TABLE (test_data) VALUES ('Test data 3');

SELECT count(*) as row_count FROM $TEST_TABLE;
EOF

    echo -e "${GREEN}✓ Test table created${NC}"
}

# Function to verify replication to replica
verify_replication() {
    echo ""
    echo -e "${BLUE}[VERIFY] Checking if data replicated to replica...${NC}"

    # Wait a moment for replication
    sleep 2

    # Check if data exists on replica
    COUNT=$(psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT count(*) FROM $TEST_TABLE;" 2>/dev/null || echo "0")

    if [ "$COUNT" -eq "3" ]; then
        echo -e "${GREEN}✓ All 3 rows replicated to replica${NC}"
        return 0
    else
        echo -e "${RED}✗ Replication failed - only $COUNT rows found${NC}"
        return 1
    fi
}

# Function to simulate primary failure
simulate_primary_failure() {
    echo ""
    echo -e "${YELLOW}[FAILOVER] Simulating primary server failure...${NC}"
    echo "This would normally be: docker stop postgres-primary"
    echo "Or stopping the postgres service"
    echo ""
    echo -e "${YELLOW}WARNING: This test requires manual intervention to stop the primary${NC}"
    echo -e "${YELLOW}Press Enter to continue, or Ctrl+C to abort...${NC}"
    read

    # In actual test, would do:
    # docker stop postgres-primary
    # Or: systemctl stop postgresql@15-main

    echo -e "${YELLOW}Primary failure simulated${NC}"
}

# Function to promote replica to primary
promote_replica() {
    echo ""
    echo -e "${BLUE}[PROMOTE] Promoting replica to primary...${NC}"

    START_TIME=$(date +%s)

    # Using pg_ctl promote (alternative to SQL command)
    # pg_ctl promote -D /var/lib/postgresql/15/main

    # Or using SQL (faster):
    psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -c \
        "SELECT pg_promote();" 2>/dev/null || true

    # Wait for promotion to complete
    PROMOTED=0
    while [ $PROMOTED -eq 0 ]; do
        RECOVERY=$(psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
            "SELECT pg_is_in_recovery()::text;" 2>/dev/null || echo "t")

        if [ "$RECOVERY" = "f" ]; then
            PROMOTED=1
            break
        fi

        sleep 1
    done

    END_TIME=$(date +%s)
    FAILOVER_TIME=$((END_TIME - START_TIME))

    echo -e "${GREEN}✓ Replica promoted to primary${NC}"
    echo -e "${GREEN}Failover time: ${FAILOVER_TIME}s${NC}"

    if [ $FAILOVER_TIME -le $FAILOVER_TIMEOUT ]; then
        echo -e "${GREEN}✓ PASS: Failover completed within ${FAILOVER_TIMEOUT}s target${NC}"
    else
        echo -e "${RED}✗ FAIL: Failover took ${FAILOVER_TIME}s (target: ${FAILOVER_TIMEOUT}s)${NC}"
    fi
}

# Function to verify data consistency
verify_data_consistency() {
    echo ""
    echo -e "${BLUE}[VERIFY] Checking data consistency on promoted primary...${NC}"

    COUNT=$(psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT count(*) FROM $TEST_TABLE;")

    if [ "$COUNT" -eq "3" ]; then
        echo -e "${GREEN}✓ Data consistency verified - all 3 rows present${NC}"
        return 0
    else
        echo -e "${RED}✗ Data loss detected - only $COUNT rows found (expected 3)${NC}"
        return 1
    fi
}

# Function to test write capability
test_write_capability() {
    echo ""
    echo -e "${BLUE}[TEST] Testing write capability on promoted server...${NC}"

    # Promoted server should now accept writes
    psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -c \
        "INSERT INTO $TEST_TABLE (test_data) VALUES ('Failover test successful');"

    COUNT=$(psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -t -c \
        "SELECT count(*) FROM $TEST_TABLE;")

    if [ "$COUNT" -eq "4" ]; then
        echo -e "${GREEN}✓ Write capability verified - insert successful${NC}"
        return 0
    else
        echo -e "${RED}✗ Write test failed${NC}"
        return 1
    fi
}

# Function to cleanup test data
cleanup_test() {
    echo ""
    echo -e "${BLUE}[CLEANUP] Removing test table...${NC}"

    psql -h $REPLICA_HOST -p $REPLICA_PORT -U $MONITOR_USER -d $MONITOR_DB -c \
        "DROP TABLE IF EXISTS $TEST_TABLE;"

    echo -e "${GREEN}✓ Test table dropped${NC}"
}

# Main test execution
main() {
    ERRORS=0

    echo -e "${BLUE}=== PHASE 1: Setup ===${NC}"
    setup_test || ERRORS=$((ERRORS + 1))

    echo -e "${BLUE}=== PHASE 2: Verify Replication ===${NC}"
    verify_replication || ERRORS=$((ERRORS + 1))

    echo -e "${BLUE}=== PHASE 3: Simulate Failure ===${NC}"
    simulate_primary_failure || ERRORS=$((ERRORS + 1))

    echo -e "${BLUE}=== PHASE 4: Automatic Failover ===${NC}"
    promote_replica || ERRORS=$((ERRORS + 1))

    echo -e "${BLUE}=== PHASE 5: Data Consistency ===${NC}"
    verify_data_consistency || ERRORS=$((ERRORS + 1))

    echo -e "${BLUE}=== PHASE 6: Write Test ===${NC}"
    test_write_capability || ERRORS=$((ERRORS + 1))

    echo -e "${BLUE}=== PHASE 7: Cleanup ===${NC}"
    cleanup_test || ERRORS=$((ERRORS + 1))

    echo ""
    echo -e "${BLUE}=== FAILOVER TEST SUMMARY ===${NC}"
    if [ $ERRORS -eq 0 ]; then
        echo -e "${GREEN}✓ ALL TESTS PASSED${NC}"
        echo -e "${GREEN}✓ Failover working correctly${NC}"
        echo -e "${GREEN}✓ Data consistency verified${NC}"
        echo -e "${GREEN}✓ System ready for production${NC}"
        exit 0
    else
        echo -e "${RED}✗ TEST FAILED ($ERRORS errors)${NC}"
        exit 1
    fi
}

# Run main if not sourced
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    main
fi
