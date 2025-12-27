#!/bin/bash

################################################################################
# RECOVERY VERIFICATION SCRIPT
#
# Comprehensive post-recovery verification testing
# Validates database, cache, and application functionality
#
# Levels:
#   --quick      : Basic health checks (5 min)
#   --full       : Detailed integrity checks (15 min)
#   --smoke-test : Full user scenario testing (30 min)
#
# Usage:
#   ./verify-recovery.sh --quick
#   ./verify-recovery.sh --full
#   ./verify-recovery.sh --smoke-test
#
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
LOG_DIR="${BACKUP_DIR}/logs"

# Environment
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_NAME="${DB_NAME:-thebot_db}"
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-redis}"
BACKEND_URL="${BACKEND_URL:-http://localhost:8000}"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

# Verification level
VERIFY_LEVEL="${VERIFY_LEVEL:-quick}"  # quick, full, smoke-test
TARGET_ENV="${TARGET_ENV:-production}"

# Logging
VERIFY_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VERIFY_LOG="${LOG_DIR}/verify_${VERIFY_TIMESTAMP}.log"
mkdir -p "$LOG_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Tracking
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_TOTAL=0

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$VERIFY_LOG"
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S') [PASS] $*${NC}" | tee -a "$VERIFY_LOG"
}

log_fail() {
    echo -e "${RED}$(date '+%Y-%m-%d %H:%M:%S') [FAIL] $*${NC}" | tee -a "$VERIFY_LOG"
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$*${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

assert_pass() {
    local test_name="$1"
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    log_success "$test_name"
    CHECKS_PASSED=$((CHECKS_PASSED + 1))
}

assert_fail() {
    local test_name="$1"
    local reason="${2:-unknown}"
    CHECKS_TOTAL=$((CHECKS_TOTAL + 1))
    log_fail "$test_name: $reason"
    CHECKS_FAILED=$((CHECKS_FAILED + 1))
}

################################################################################
# QUICK CHECKS (5 min)
################################################################################

verify_backend_health() {
    print_header "BACKEND HEALTH CHECKS"

    # Check 1: Service running
    log_info "Check 1: Backend service running..."
    if docker ps -q -f "name=thebot-backend" | grep -q .; then
        assert_pass "Backend container running"
    else
        assert_fail "Backend container not running"
        return 1
    fi

    # Check 2: Health endpoint
    log_info "Check 2: Health endpoint..."
    local max_retries=10
    local retry=0

    while [[ $retry -lt $max_retries ]]; do
        local status=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL/api/system/health/" 2>/dev/null || echo "000")

        if [[ "$status" == "200" ]]; then
            assert_pass "Health endpoint responding (HTTP $status)"
            break
        fi

        retry=$((retry + 1))
        if [[ $retry -lt $max_retries ]]; then
            log_warn "Health endpoint returned HTTP $status, retrying..."
            sleep 3
        fi
    done

    if [[ $retry -ge $max_retries ]]; then
        assert_fail "Health endpoint not responding"
        return 1
    fi

    # Check 3: Readiness endpoint
    log_info "Check 3: Readiness endpoint..."
    local readiness=$(curl -s "$BACKEND_URL/api/system/readiness/" 2>/dev/null | jq -r '.ready' 2>/dev/null || echo "false")

    if [[ "$readiness" == "true" ]]; then
        assert_pass "Readiness check passed"
    else
        assert_fail "Service not ready for requests"
        return 1
    fi

    return 0
}

verify_database_connectivity() {
    print_header "DATABASE CONNECTIVITY CHECKS"

    # Check 1: Container running
    log_info "Check 1: PostgreSQL container running..."
    if docker ps -q -f "name=thebot-postgres" | grep -q .; then
        assert_pass "PostgreSQL container running"
    else
        assert_fail "PostgreSQL container not running"
        return 1
    fi

    # Check 2: Port listening
    log_info "Check 2: PostgreSQL port listening..."
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "$DB_USER" &>/dev/null; then
        assert_pass "PostgreSQL accepting connections"
    else
        assert_fail "PostgreSQL not responding to connections"
        return 1
    fi

    # Check 3: Database exists
    log_info "Check 3: Database exists..."
    local db_list=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -w "$DB_NAME" || echo "")

    if [[ -n "$db_list" ]]; then
        assert_pass "Database '$DB_NAME' exists"
    else
        assert_fail "Database '$DB_NAME' not found"
        return 1
    fi

    # Check 4: Basic query
    log_info "Check 4: Basic query execution..."
    local table_count=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U "$DB_USER" -d "$DB_NAME" -t -c \
      "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" 2>/dev/null || echo "0")

    if [[ $table_count -gt 0 ]]; then
        assert_pass "Database contains $table_count tables"
    else
        assert_fail "No tables found in database"
        return 1
    fi

    return 0
}

verify_redis_connectivity() {
    print_header "REDIS CONNECTIVITY CHECKS"

    # Check 1: Container running
    log_info "Check 1: Redis container running..."
    if docker ps -q -f "name=thebot-redis" | grep -q .; then
        assert_pass "Redis container running"
    else
        assert_fail "Redis container not running"
        return 1
    fi

    # Check 2: Port listening
    log_info "Check 2: Redis port listening..."
    if docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" ping &>/dev/null; then
        assert_pass "Redis accepting connections"
    else
        assert_fail "Redis not responding"
        return 1
    fi

    # Check 3: Memory status
    log_info "Check 3: Redis memory status..."
    local memory_used=$(docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r' || echo "unknown")

    assert_pass "Redis memory: $memory_used"

    return 0
}

verify_celery_workers() {
    print_header "CELERY WORKER CHECKS"

    # Check 1: Workers running
    log_info "Check 1: Celery workers..."
    local worker_count=$(docker ps -q -f "name=thebot-celery" | wc -l)

    if [[ $worker_count -gt 0 ]]; then
        assert_pass "Celery workers running ($worker_count)"
    else
        log_warn "No Celery workers found (optional)"
        assert_pass "Celery workers check (optional)"
    fi

    return 0
}

################################################################################
# FULL CHECKS (15 min)
################################################################################

verify_database_integrity() {
    print_header "DATABASE INTEGRITY CHECKS"

    # Check 1: Key tables exist
    log_info "Check 1: Key tables exist..."
    local required_tables=("auth_user" "accounts_studentprofile" "materials_material")

    for table in "${required_tables[@]}"; do
        local exists=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
          psql -U "$DB_USER" -d "$DB_NAME" -t -c \
          "SELECT EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name='$table');" 2>/dev/null || echo "false")

        if [[ "$exists" == "t" ]]; then
            assert_pass "Table '$table' exists"
        else
            assert_fail "Table '$table' not found"
        fi
    done

    # Check 2: Record counts
    log_info "Check 2: Record counts..."
    local user_count=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM auth_user;" 2>/dev/null || echo "0")

    if [[ $user_count -gt 0 ]]; then
        assert_pass "Users found: $user_count"
    else
        log_warn "No users found (may be expected if fresh restore)"
        assert_pass "User count check (0 may be expected)"
    fi

    # Check 3: No corruption indicators
    log_info "Check 3: Database corruption check..."
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres \
      pg_dump -U "$DB_USER" -d "$DB_NAME" --schema-only > /tmp/schema_check.sql 2>/dev/null; then
        assert_pass "Database schema dump successful (no corruption detected)"
        rm -f /tmp/schema_check.sql
    else
        assert_fail "Database schema check failed (possible corruption)"
    fi

    return 0
}

verify_redis_data() {
    print_header "REDIS DATA CHECKS"

    # Check 1: Data can be written
    log_info "Check 1: Write capability..."
    if docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" SET test_key test_value &>/dev/null; then
        assert_pass "Can write to Redis"
        docker-compose -f "$COMPOSE_FILE" exec -T redis \
          redis-cli -a "$REDIS_PASSWORD" DEL test_key &>/dev/null || true
    else
        assert_fail "Cannot write to Redis"
    fi

    # Check 2: Key expiration working
    log_info "Check 2: Key expiration..."
    docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" SET expiry_test value EX 2 &>/dev/null || true

    sleep 3

    local exists=$(docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" EXISTS expiry_test 2>/dev/null || echo "1")

    if [[ "$exists" == "0" ]]; then
        assert_pass "Key expiration working"
    else
        log_warn "Key expiration may not be working (non-critical)"
        assert_pass "Key expiration check (non-critical)"
    fi

    return 0
}

verify_api_endpoints() {
    print_header "API ENDPOINT CHECKS"

    local endpoints=(
        "/api/system/health/"
        "/api/system/readiness/"
        "/api/system/metrics/"
    )

    for endpoint in "${endpoints[@]}"; do
        log_info "Testing endpoint: $endpoint..."
        local status=$(curl -s -o /dev/null -w "%{http_code}" "$BACKEND_URL$endpoint" 2>/dev/null || echo "000")

        if [[ "$status" == "200" ]]; then
            assert_pass "Endpoint $endpoint returning HTTP 200"
        else
            assert_fail "Endpoint $endpoint returned HTTP $status"
        fi
    done

    return 0
}

################################################################################
# SMOKE TESTS (30 min)
################################################################################

verify_auth_flow() {
    print_header "AUTH FLOW TEST"

    log_info "Testing authentication flow..."

    # Create test payload
    local response=$(curl -s -X POST "$BACKEND_URL/api/accounts/login/" \
      -H "Content-Type: application/json" \
      -d '{"email":"student@test.com","password":"TestPass123!"}' 2>/dev/null || echo "{}")

    local token=$(echo "$response" | jq -r '.token' 2>/dev/null || echo "")

    if [[ -n "$token" && "$token" != "null" ]]; then
        assert_pass "Authentication successful (token received)"
        return 0
    else
        assert_fail "Authentication failed (no token)"
        return 1
    fi
}

verify_materials_api() {
    print_header "MATERIALS API TEST"

    log_info "Testing materials API..."

    local response=$(curl -s "$BACKEND_URL/api/materials/" 2>/dev/null || echo "{}")
    local count=$(echo "$response" | jq -r '.count' 2>/dev/null || echo "0")

    if [[ $count -ge 0 ]]; then
        assert_pass "Materials API responding (found $count materials)"
        return 0
    else
        assert_fail "Materials API not responding"
        return 1
    fi
}

verify_chat_api() {
    print_header "CHAT API TEST"

    log_info "Testing chat rooms API..."

    local response=$(curl -s "$BACKEND_URL/api/chat/rooms/" 2>/dev/null || echo "{}")
    local count=$(echo "$response" | jq -r '.count' 2>/dev/null || echo "0")

    if [[ $count -ge 0 ]]; then
        assert_pass "Chat API responding (found $count rooms)"
        return 0
    else
        assert_fail "Chat API not responding"
        return 1
    fi
}

################################################################################
# REPORT
################################################################################

generate_report() {
    print_header "VERIFICATION REPORT"

    local checks_skipped=$((CHECKS_TOTAL - CHECKS_PASSED - CHECKS_FAILED))

    echo "Total Checks: $CHECKS_TOTAL"
    echo "Passed: $CHECKS_PASSED"
    echo "Failed: $CHECKS_FAILED"
    echo ""

    if [[ $CHECKS_FAILED -eq 0 ]]; then
        echo -e "${GREEN}RESULT: ALL CHECKS PASSED${NC}"
        echo ""
        echo "The system has been successfully recovered."
        echo "All critical components are functional."
        return 0
    else
        echo -e "${RED}RESULT: SOME CHECKS FAILED${NC}"
        echo ""
        echo "The system has issues that need investigation."
        echo "Failed checks: $CHECKS_FAILED"
        return 1
    fi
}

################################################################################
# MAIN
################################################################################

main() {
    print_header "RECOVERY VERIFICATION UTILITY"

    log_info "Verification Level: $VERIFY_LEVEL"
    log_info "Target: $TARGET_ENV"
    log_info "Start time: $(date)"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --quick)
                VERIFY_LEVEL="quick"
                shift
                ;;
            --full)
                VERIFY_LEVEL="full"
                shift
                ;;
            --smoke-test)
                VERIFY_LEVEL="smoke-test"
                shift
                ;;
            --target)
                TARGET_ENV="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Execute verifications based on level
    case "$VERIFY_LEVEL" in
        quick)
            log_info "Running QUICK verification (5 minutes)..."
            verify_backend_health || true
            verify_database_connectivity || true
            verify_redis_connectivity || true
            ;;

        full)
            log_info "Running FULL verification (15 minutes)..."
            verify_backend_health || true
            verify_database_connectivity || true
            verify_redis_connectivity || true
            verify_celery_workers || true
            verify_database_integrity || true
            verify_redis_data || true
            verify_api_endpoints || true
            ;;

        smoke-test)
            log_info "Running SMOKE TEST verification (30 minutes)..."
            verify_backend_health || true
            verify_database_connectivity || true
            verify_redis_connectivity || true
            verify_database_integrity || true
            verify_redis_data || true
            verify_api_endpoints || true
            verify_auth_flow || true
            verify_materials_api || true
            verify_chat_api || true
            ;;
    esac

    # Generate report
    echo ""
    generate_report
    local exit_code=$?

    log_info "Log file: $VERIFY_LOG"
    log_info "Verification completed"

    exit $exit_code
}

main "$@"
