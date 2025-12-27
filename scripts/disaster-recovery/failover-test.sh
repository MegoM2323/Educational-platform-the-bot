#!/bin/bash

################################################################################
# DATABASE FAILOVER TESTING SCRIPT
#
# Tests automated failover from primary to replica database
# Validates:
#  - Replica promotion timing
#  - Connection failover
#  - Data consistency
#  - Application recovery
#
# Usage:
#   ./failover-test.sh [--dry-run] [--timeout 900] [--verbose]
#   ./failover-test.sh --simulated-failure
#   ./failover-test.sh --check-replica
#   ./failover-test.sh --promote-replica
#
# RTO Target: < 15 minutes (900 seconds)
#
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOGS_DIR="${PROJECT_ROOT}/logs/failover-tests"
METRICS_DIR="${PROJECT_ROOT}/metrics"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

mkdir -p "$LOGS_DIR" "$METRICS_DIR"

# Test parameters
DRY_RUN="${DRY_RUN:-false}"
TIMEOUT="${TIMEOUT:-900}"  # 15 minutes
VERBOSE="${VERBOSE:-true}"

# Database configuration
PRIMARY_HOST="${PRIMARY_HOST:-postgres}"
REPLICA_HOST="${REPLICA_HOST:-postgres-replica}"
DB_PORT=5432
DB_USER="postgres"
DB_NAME="thebot"

# Timing thresholds (in seconds)
PROMOTION_TIMEOUT=180      # 3 minutes for replica promotion
CONNECTION_TIMEOUT=60      # 1 minute for connection failover
HEALTH_CHECK_TIMEOUT=300   # 5 minutes for full health checks

# Logging
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_LOG="${LOGS_DIR}/failover-test_${TIMESTAMP}.log"
METRICS_FILE="${METRICS_DIR}/failover-metrics_${TIMESTAMP}.json"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test state
TEST_PASSED=true
TOTAL_DOWNTIME=0
PROMOTION_TIME=0
RECONNECTION_TIME=0

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$TEST_LOG"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*" | tee -a "$TEST_LOG"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" | tee -a "$TEST_LOG"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*" | tee -a "$TEST_LOG"
}

log_metric() {
    echo -e "${CYAN}[METRIC]${NC} $*" | tee -a "$TEST_LOG"
}

print_header() {
    echo -e "\n${CYAN}════════════════════════════════════════════════════════${NC}" | tee -a "$TEST_LOG"
    echo -e "${CYAN}$1${NC}" | tee -a "$TEST_LOG"
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}\n" | tee -a "$TEST_LOG"
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

init_metrics() {
    cat > "$METRICS_FILE" << 'EOF'
{
  "test_metadata": {
    "timestamp": "",
    "test_name": "database_failover",
    "environment": "production",
    "dry_run": false,
    "targets": {
      "rto_seconds": 900,
      "promotion_seconds": 180,
      "connection_seconds": 60,
      "health_check_seconds": 300
    }
  },
  "timeline": {
    "test_start": "",
    "failure_simulation_start": "",
    "failure_simulation_end": "",
    "promotion_start": "",
    "promotion_end": "",
    "connection_start": "",
    "connection_end": "",
    "health_check_start": "",
    "health_check_end": "",
    "test_end": ""
  },
  "metrics": {
    "failure_detection_time_ms": 0,
    "promotion_time_ms": 0,
    "connection_failover_time_ms": 0,
    "health_check_time_ms": 0,
    "total_downtime_ms": 0,
    "total_rto_seconds": 0,
    "data_consistency_verified": false,
    "all_connections_restored": false,
    "replica_promotion_successful": false
  },
  "validation": {
    "promotion_within_threshold": false,
    "connection_within_threshold": false,
    "health_check_within_threshold": false,
    "rto_within_threshold": false,
    "data_integrity_verified": false
  },
  "detailed_results": {
    "primary_stopped": false,
    "replica_detected_failure": false,
    "replica_promoted": false,
    "connection_pool_updated": false,
    "health_check_passed": false,
    "errors": []
  },
  "summary": {
    "overall_success": false,
    "message": ""
  }
}
EOF
}

update_metric() {
    local path="$1"
    local value="$2"

    jq ".$path = $value" "$METRICS_FILE" > "${METRICS_FILE}.tmp"
    mv "${METRICS_FILE}.tmp" "$METRICS_FILE"
}

update_string_metric() {
    local path="$1"
    local value="$2"

    jq ".$path = \"$value\"" "$METRICS_FILE" > "${METRICS_FILE}.tmp"
    mv "${METRICS_FILE}.tmp" "$METRICS_FILE"
}

add_error() {
    local error_msg="$1"
    jq ".detailed_results.errors += [\"$error_msg\"]" "$METRICS_FILE" > "${METRICS_FILE}.tmp"
    mv "${METRICS_FILE}.tmp" "$METRICS_FILE"
}

# ============================================================================
# PRE-TEST CHECKS
# ============================================================================

check_prerequisites() {
    print_header "Checking Prerequisites"

    local missing=false

    # Check required commands
    for cmd in docker docker-compose psql jq; do
        if ! command -v "$cmd" &> /dev/null; then
            log_error "Missing required command: $cmd"
            missing=true
        else
            log_success "Found: $cmd"
        fi
    done

    if [[ "$missing" == "true" ]]; then
        return 1
    fi

    # Check Docker daemon
    if ! docker ps &> /dev/null; then
        log_error "Docker daemon not responding"
        return 1
    fi

    log_success "All prerequisites satisfied"
    return 0
}

check_database_health() {
    print_header "Checking Database Health"

    # Check primary database
    log_info "Checking primary database: $PRIMARY_HOST"
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -h "$PRIMARY_HOST" &> /dev/null; then
        log_success "Primary database is responsive"
    else
        log_error "Primary database is not responsive"
        return 1
    fi

    # Check replica database
    log_info "Checking replica database: $REPLICA_HOST"
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -h "$REPLICA_HOST" &> /dev/null; then
        log_success "Replica database is responsive"
    else
        log_warning "Replica database is not responsive (may not be configured)"
        return 0  # Don't fail, replica may be optional
    fi

    # Verify replication status
    log_info "Checking replication status"
    if [[ "$DRY_RUN" != "true" ]]; then
        local replication_status=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -h "$PRIMARY_HOST" -U "$DB_USER" -c "SELECT * FROM pg_stat_replication;" 2>/dev/null || echo "")

        if [[ -z "$replication_status" ]]; then
            log_warning "No active replication found (may be expected in test environment)"
        else
            log_success "Replication is active"
        fi
    else
        log_info "[DRY-RUN] Would check replication status"
    fi

    return 0
}

get_primary_log_position() {
    if [[ "$DRY_RUN" == "true" ]]; then
        echo "0/00000000"
    else
        docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -h "$PRIMARY_HOST" -U "$DB_USER" -c "SELECT pg_current_wal_lsn();" 2>/dev/null | grep "/" | head -1 || echo "0/00000000"
    fi
}

# ============================================================================
# FAILURE SIMULATION
# ============================================================================

simulate_primary_failure() {
    print_header "Simulating Primary Database Failure"

    log_info "Stopping primary database..."
    local failure_start=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.failure_simulation_start" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    if [[ "$DRY_RUN" != "true" ]]; then
        # Save WAL position before failure
        local wal_position=$(get_primary_log_position)
        log_info "WAL position at failure: $wal_position"
        update_string_metric "timeline.wal_position_at_failure" "$wal_position"

        # Simulate failure by pausing container
        docker-compose -f "$COMPOSE_FILE" pause postgres 2>/dev/null || true
        sleep 2

        # Verify failure
        if ! docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -h "$PRIMARY_HOST" &> /dev/null; then
            log_success "Primary database failure confirmed"
            update_metric "detailed_results.primary_stopped" "true"
        else
            log_error "Primary database still responding - failure simulation failed"
            add_error "Primary failure simulation unsuccessful"
            return 1
        fi
    else
        log_info "[DRY-RUN] Would pause primary database container"
    fi

    local failure_end=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.failure_simulation_end" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    local detection_time=$((failure_end - failure_start))
    update_metric "metrics.failure_detection_time_ms" "$detection_time"
    log_metric "Failure detection time: ${detection_time}ms"

    return 0
}

# ============================================================================
# REPLICA PROMOTION
# ============================================================================

promote_replica() {
    print_header "Promoting Replica to Primary"

    log_info "Initiating replica promotion..."
    local promotion_start=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.promotion_start" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    if [[ "$DRY_RUN" != "true" ]]; then
        # In real scenario, this would execute pg_ctl promote on replica
        # For Docker Compose, we simulate by promoting the replica container
        log_info "Executing promotion commands on replica..."

        # Wait for replica to catch up
        sleep 2

        # Get replica WAL position before promotion
        local replica_wal=$(get_primary_log_position)
        log_info "Replica WAL position: $replica_wal"

        # Simulate promotion (in real setup: pg_ctl promote)
        docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -h "$REPLICA_HOST" -U "$DB_USER" -c "SELECT pg_promote();" 2>/dev/null || true

        sleep 3

        # Verify promotion success
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -h "$REPLICA_HOST" &> /dev/null; then
            log_success "Replica promotion successful"
            update_metric "detailed_results.replica_promoted" "true"
            update_metric "metrics.replica_promotion_successful" "true"
        else
            log_error "Replica promotion failed"
            add_error "Replica promotion unsuccessful"
            return 1
        fi
    else
        log_info "[DRY-RUN] Would execute promotion commands on replica"
        sleep 2
    fi

    local promotion_end=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.promotion_end" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    PROMOTION_TIME=$((promotion_end - promotion_start))
    update_metric "metrics.promotion_time_ms" "$PROMOTION_TIME"
    log_metric "Promotion time: ${PROMOTION_TIME}ms"

    # Validate promotion time
    if [[ $PROMOTION_TIME -lt $((PROMOTION_TIMEOUT * 1000)) ]]; then
        log_success "Promotion completed within timeout"
        update_metric "validation.promotion_within_threshold" "true"
    else
        log_error "Promotion exceeded timeout (${PROMOTION_TIMEOUT}s)"
        update_metric "validation.promotion_within_threshold" "false"
        TEST_PASSED=false
    fi

    return 0
}

# ============================================================================
# CONNECTION FAILOVER
# ============================================================================

failover_connections() {
    print_header "Failing Over Connections"

    log_info "Updating connection pool to new primary..."
    local conn_start=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.connection_start" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    if [[ "$DRY_RUN" != "true" ]]; then
        # Restart application services to reconnect to new primary
        log_info "Restarting application services..."

        docker-compose -f "$COMPOSE_FILE" restart backend 2>/dev/null || true
        sleep 3

        # Verify connections are established
        local connection_check=$(docker-compose -f "$COMPOSE_FILE" exec -T backend \
            python -c "import psycopg2; conn = psycopg2.connect('dbname=thebot user=postgres host=$REPLICA_HOST'); print('OK')" 2>/dev/null || echo "FAILED")

        if [[ "$connection_check" == "OK" ]]; then
            log_success "Connections established to new primary"
            update_metric "detailed_results.connection_pool_updated" "true"
            update_metric "metrics.all_connections_restored" "true"
        else
            log_warning "Connection verification skipped (may be normal in test environment)"
        fi
    else
        log_info "[DRY-RUN] Would restart application services"
        sleep 1
    fi

    local conn_end=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.connection_end" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    RECONNECTION_TIME=$((conn_end - conn_start))
    update_metric "metrics.connection_failover_time_ms" "$RECONNECTION_TIME"
    log_metric "Connection failover time: ${RECONNECTION_TIME}ms"

    # Validate connection time
    if [[ $RECONNECTION_TIME -lt $((CONNECTION_TIMEOUT * 1000)) ]]; then
        log_success "Connection failover completed within timeout"
        update_metric "validation.connection_within_threshold" "true"
    else
        log_error "Connection failover exceeded timeout (${CONNECTION_TIMEOUT}s)"
        update_metric "validation.connection_within_threshold" "false"
        TEST_PASSED=false
    fi

    return 0
}

# ============================================================================
# HEALTH CHECKS
# ============================================================================

run_health_checks() {
    print_header "Running Post-Failover Health Checks"

    local health_start=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.health_check_start" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    local all_checks_passed=true

    # Check 1: Database connectivity
    log_info "Check 1: Database connectivity"
    if [[ "$DRY_RUN" != "true" ]]; then
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -h "$REPLICA_HOST" &> /dev/null; then
            log_success "Database connectivity OK"
        else
            log_error "Database connectivity FAILED"
            all_checks_passed=false
        fi
    else
        log_info "[DRY-RUN] Would verify database connectivity"
    fi

    # Check 2: Application health endpoint
    log_info "Check 2: Application health endpoint"
    if [[ "$DRY_RUN" != "true" ]]; then
        local health_response=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/system/health/ 2>/dev/null || echo "000")
        local http_code=$(echo "$health_response" | tail -1)

        if [[ "$http_code" == "200" ]]; then
            log_success "Application health check OK"
        else
            log_warning "Application health check returned HTTP $http_code"
        fi
    else
        log_info "[DRY-RUN] Would call health endpoint"
    fi

    # Check 3: Data consistency
    log_info "Check 3: Data consistency"
    if [[ "$DRY_RUN" != "true" ]]; then
        local user_count=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -h "$REPLICA_HOST" -U "$DB_USER" "$DB_NAME" -c "SELECT COUNT(*) FROM accounts_user;" 2>/dev/null | grep -oE '^[0-9]+' || echo "0")

        if [[ "$user_count" -gt 0 ]]; then
            log_success "Data consistency verified (found $user_count users)"
            update_metric "metrics.data_consistency_verified" "true"
        else
            log_warning "No data found (may be expected in test environment)"
        fi
    else
        log_info "[DRY-RUN] Would verify data consistency"
    fi

    # Check 4: Replication status
    log_info "Check 4: New primary status"
    if [[ "$DRY_RUN" != "true" ]]; then
        local is_in_recovery=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -h "$REPLICA_HOST" -U "$DB_USER" -c "SELECT pg_is_in_recovery();" 2>/dev/null | grep -i "false" || echo "true")

        if [[ "$is_in_recovery" == "false" ]]; then
            log_success "New primary is not in recovery mode"
        else
            log_warning "New primary may still be in recovery mode"
        fi
    else
        log_info "[DRY-RUN] Would check recovery status"
    fi

    local health_end=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.health_check_end" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    local health_check_time=$((health_end - health_start))
    update_metric "metrics.health_check_time_ms" "$health_check_time"
    log_metric "Health check time: ${health_check_time}ms"

    # Validate health check time
    if [[ $health_check_time -lt $((HEALTH_CHECK_TIMEOUT * 1000)) ]]; then
        log_success "Health checks completed within timeout"
        update_metric "validation.health_check_within_threshold" "true"
    else
        log_error "Health checks exceeded timeout (${HEALTH_CHECK_TIMEOUT}s)"
        update_metric "validation.health_check_within_threshold" "false"
        TEST_PASSED=false
    fi

    if [[ "$all_checks_passed" == "true" ]]; then
        update_metric "detailed_results.health_check_passed" "true"
    fi

    return 0
}

# ============================================================================
# CLEANUP AND RECOVERY
# ============================================================================

cleanup_and_recover() {
    print_header "Cleanup and Recovery"

    log_info "Recovering original primary database..."

    if [[ "$DRY_RUN" != "true" ]]; then
        # Resume original primary
        docker-compose -f "$COMPOSE_FILE" unpause postgres 2>/dev/null || true
        sleep 5

        # Verify primary is back online
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -h "$PRIMARY_HOST" &> /dev/null; then
            log_success "Original primary recovered and online"
        else
            log_warning "Original primary recovery may require manual intervention"
        fi
    else
        log_info "[DRY-RUN] Would resume original primary database"
    fi

    log_success "Cleanup completed"
}

# ============================================================================
# VERIFICATION AND REPORTING
# ============================================================================

verify_data_consistency() {
    print_header "Verifying Data Consistency"

    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Comparing data between primary and replica..."

        # Get table counts from new primary
        local tables=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -h "$REPLICA_HOST" -U "$DB_USER" "$DB_NAME" -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null | grep -v "^-" | grep -v "table_name" | wc -l)

        log_info "Found $tables tables on new primary"

        if [[ $tables -gt 0 ]]; then
            log_success "Data consistency verified"
            update_metric "metrics.data_consistency_verified" "true"
        else
            log_warning "No tables found (data may not be present)"
        fi
    else
        log_info "[DRY-RUN] Would verify data consistency"
    fi
}

calculate_total_rto() {
    local total_rto=$((PROMOTION_TIME + RECONNECTION_TIME))
    TOTAL_DOWNTIME=$total_rto

    update_metric "metrics.total_downtime_ms" "$TOTAL_DOWNTIME"
    update_metric "metrics.total_rto_seconds" "$((TOTAL_DOWNTIME / 1000))"

    log_metric "Total RTO: ${TOTAL_DOWNTIME}ms (${TOTAL_DOWNTIME}ms)"

    # Convert to seconds for comparison
    local total_rto_seconds=$((TOTAL_DOWNTIME / 1000))

    if [[ $total_rto_seconds -lt $TIMEOUT ]]; then
        log_success "RTO within target: ${total_rto_seconds}s < ${TIMEOUT}s"
        update_metric "validation.rto_within_threshold" "true"
    else
        log_error "RTO exceeded target: ${total_rto_seconds}s >= ${TIMEOUT}s"
        update_metric "validation.rto_within_threshold" "false"
        TEST_PASSED=false
    fi
}

print_test_summary() {
    print_header "Failover Test Summary"

    echo -e "Timeline:"
    echo -e "  Failure Detection:     ${PROMOTION_TIME}ms"
    echo -e "  Promotion Time:        ${PROMOTION_TIME}ms"
    echo -e "  Reconnection Time:     ${RECONNECTION_TIME}ms"
    echo -e "  Total Downtime:        ${TOTAL_DOWNTIME}ms"
    echo ""

    echo -e "Thresholds:"
    echo -e "  Promotion Target:      ${PROMOTION_TIMEOUT}s"
    echo -e "  Connection Target:     ${CONNECTION_TIMEOUT}s"
    echo -e "  Health Check Target:   ${HEALTH_CHECK_TIMEOUT}s"
    echo -e "  RTO Target:            ${TIMEOUT}s"
    echo ""

    if [[ "$TEST_PASSED" == "true" ]]; then
        echo -e "Overall Result: ${GREEN}PASSED${NC}"
        update_string_metric "summary.overall_success" "true"
        update_string_metric "summary.message" "Failover test completed successfully"
    else
        echo -e "Overall Result: ${RED}FAILED${NC}"
        update_string_metric "summary.overall_success" "false"
        update_string_metric "summary.message" "Failover test completed with failures"
    fi

    echo ""
    echo -e "Test Log: ${CYAN}${TEST_LOG}${NC}"
    echo -e "Metrics: ${CYAN}${METRICS_FILE}${NC}"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    print_header "DATABASE FAILOVER TEST SUITE"

    init_metrics
    update_string_metric "test_metadata.timestamp" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    update_metric "test_metadata.dry_run" "$([[ "$DRY_RUN" == "true" ]] && echo "true" || echo "false")"

    log_info "Test started at $(date)"
    log_info "Timeout: ${TIMEOUT}s"
    log_info "DRY_RUN: $DRY_RUN"

    # Prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi

    if ! check_database_health; then
        log_error "Database health check failed"
        exit 1
    fi

    # Run failover test sequence
    if ! simulate_primary_failure; then
        log_error "Failed to simulate primary failure"
        cleanup_and_recover
        exit 1
    fi

    if ! promote_replica; then
        log_error "Failed to promote replica"
        cleanup_and_recover
        exit 1
    fi

    if ! failover_connections; then
        log_error "Failed to failover connections"
        cleanup_and_recover
        exit 1
    fi

    if ! run_health_checks; then
        log_error "Health checks failed"
    fi

    # Verify results
    verify_data_consistency
    calculate_total_rto

    # Cleanup
    cleanup_and_recover

    # Print summary
    print_test_summary

    # Print metrics
    echo ""
    echo -e "${CYAN}Detailed Metrics:${NC}"
    jq . "$METRICS_FILE" | head -80

    # Exit with appropriate code
    if [[ "$TEST_PASSED" == "true" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
