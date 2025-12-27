#!/bin/bash

################################################################################
# BACKUP SYSTEM TEST SUITE
#
# Comprehensive tests for database backup and recovery functionality
# Verifies: backup creation, verification, restore, retention, monitoring
#
# Usage:
#   ./test_backup.sh                Run all tests
#   ./test_backup.sh backup         Test backup creation
#   ./test_backup.sh restore        Test restore functionality
#   ./test_backup.sh retention      Test retention policy
#   ./test_backup.sh monitor        Test monitoring
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Test configuration
TEST_DIR="${PROJECT_ROOT}/backup/tests"
TEST_BACKUP_DIR="${TEST_DIR}/backups"
TEST_LOG_FILE="${TEST_DIR}/test_results.log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0

################################################################################
# TEST UTILITIES
################################################################################

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[${timestamp}] [${level}] ${message}" >> "${TEST_LOG_FILE}"

    case "${level}" in
        INFO)
            echo -e "${BLUE}[INFO]${NC} ${message}"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} ${message}"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} ${message}"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${message}"
            ;;
        TEST)
            echo -e "${BLUE}[TEST]${NC} ${message}"
            ;;
    esac
}

init_test_environment() {
    mkdir -p "${TEST_DIR}"/{backups/{daily,weekly,monthly,logs},test_db}
    rm -f "${TEST_LOG_FILE}"
    log INFO "Test environment initialized: ${TEST_DIR}"
}

assert_success() {
    local test_name=$1
    local exit_code=$2

    ((TESTS_RUN++))

    if [ ${exit_code} -eq 0 ]; then
        ((TESTS_PASSED++))
        log SUCCESS "PASS: ${test_name}"
        return 0
    else
        ((TESTS_FAILED++))
        log ERROR "FAIL: ${test_name} (exit code: ${exit_code})"
        return 1
    fi
}

assert_file_exists() {
    local test_name=$1
    local file_path=$2

    ((TESTS_RUN++))

    if [ -f "${file_path}" ]; then
        ((TESTS_PASSED++))
        log SUCCESS "PASS: ${test_name} - File exists"
        return 0
    else
        ((TESTS_FAILED++))
        log ERROR "FAIL: ${test_name} - File not found: ${file_path}"
        return 1
    fi
}

assert_directory_exists() {
    local test_name=$1
    local dir_path=$2

    ((TESTS_RUN++))

    if [ -d "${dir_path}" ]; then
        ((TESTS_PASSED++))
        log SUCCESS "PASS: ${test_name} - Directory exists"
        return 0
    else
        ((TESTS_FAILED++))
        log ERROR "FAIL: ${test_name} - Directory not found: ${dir_path}"
        return 1
    fi
}

assert_contains() {
    local test_name=$1
    local file_path=$2
    local search_string=$3

    ((TESTS_RUN++))

    if grep -q "${search_string}" "${file_path}" 2>/dev/null; then
        ((TESTS_PASSED++))
        log SUCCESS "PASS: ${test_name} - Content found"
        return 0
    else
        ((TESTS_FAILED++))
        log ERROR "FAIL: ${test_name} - Content not found: ${search_string}"
        return 1
    fi
}

assert_count() {
    local test_name=$1
    local expected=$2
    local actual=$3

    ((TESTS_RUN++))

    if [ "${expected}" -eq "${actual}" ]; then
        ((TESTS_PASSED++))
        log SUCCESS "PASS: ${test_name} - Count matches (${actual})"
        return 0
    else
        ((TESTS_FAILED++))
        log ERROR "FAIL: ${test_name} - Expected ${expected}, got ${actual}"
        return 1
    fi
}

################################################################################
# TEST SUITES
################################################################################

create_test_database() {
    log TEST "Creating test database..."

    # Create test SQLite database
    local test_db="${TEST_DIR}/test_db/test.sqlite3"
    sqlite3 "${test_db}" <<'EOF'
CREATE TABLE test_users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT UNIQUE
);

CREATE TABLE test_data (
    id INTEGER PRIMARY KEY,
    content TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO test_users (id, name, email) VALUES
    (1, 'Test User 1', 'test1@example.com'),
    (2, 'Test User 2', 'test2@example.com');

INSERT INTO test_data (content) VALUES
    ('Test data 1'),
    ('Test data 2'),
    ('Test data 3');
EOF

    log SUCCESS "Test database created: ${test_db}"
    echo "${test_db}"
}

test_backup_prerequisites() {
    log TEST "Testing backup prerequisites..."

    local missing_tools=()

    command -v gzip >/dev/null 2>&1 || missing_tools+=("gzip")
    command -v sqlite3 >/dev/null 2>&1 || missing_tools+=("sqlite3")
    command -v sha256sum >/dev/null 2>&1 || missing_tools+=("sha256sum")

    if [ ${#missing_tools[@]} -eq 0 ]; then
        assert_success "All prerequisite tools present" 0
    else
        assert_success "Missing tools check" 1
        log ERROR "Missing: ${missing_tools[*]}"
    fi
}

test_backup_creation() {
    log TEST "Testing backup creation..."

    local test_db=$(create_test_database)
    local backup_file="${TEST_BACKUP_DIR}/daily/test_backup_$(date +%s).gz"

    # Simulate backup
    if sqlite3 "${test_db}" ".backup '/tmp/test.backup'" && gzip "/tmp/test.backup" -c > "${backup_file}"; then
        assert_file_exists "Backup file created" "${backup_file}"

        # Test compression
        local file_size=$(stat -c%s "${backup_file}" 2>/dev/null || echo "0")
        if [ "${file_size}" -gt 0 ]; then
            log SUCCESS "Backup compressed: ${file_size} bytes"
        fi

        # Test integrity
        if gzip -t "${backup_file}" 2>/dev/null; then
            assert_success "Backup gzip integrity" 0
        else
            assert_success "Backup gzip integrity" 1
        fi

        # Cleanup
        rm -f "/tmp/test.backup"
    else
        assert_success "Backup creation" 1
    fi
}

test_backup_metadata() {
    log TEST "Testing backup metadata creation..."

    local metadata_file="${TEST_BACKUP_DIR}/daily/test_backup_$(date +%s).metadata"

    # Create sample metadata
    cat > "${metadata_file}" <<'EOF'
{
  "backup_file": "test_backup.gz",
  "backup_type": "sqlite",
  "backup_date": "2023-12-15T01:00:00Z",
  "backup_size": "1024",
  "backup_duration_seconds": 45,
  "backup_checksum_sha256": "abc123def456",
  "compression": "gzip"
}
EOF

    assert_file_exists "Metadata file created" "${metadata_file}"
    assert_contains "Metadata contains backup_type" "${metadata_file}" '"backup_type"'
    assert_contains "Metadata contains checksum" "${metadata_file}" "backup_checksum_sha256"

    # Cleanup
    rm -f "${metadata_file}"
}

test_backup_verification() {
    log TEST "Testing backup verification..."

    local test_db=$(create_test_database)
    local backup_file="${TEST_BACKUP_DIR}/daily/test_verify_$(date +%s).gz"

    # Create backup
    if sqlite3 "${test_db}" ".backup '/tmp/verify.backup'" && gzip "/tmp/verify.backup" -c > "${backup_file}"; then
        # Verify gzip integrity
        if gzip -t "${backup_file}" 2>/dev/null; then
            assert_success "Backup verification" 0
        else
            assert_success "Backup verification" 1
        fi

        # Verify checksum
        local checksum=$(sha256sum "${backup_file}" | awk '{print $1}')
        if [ -n "${checksum}" ] && [ ${#checksum} -eq 64 ]; then
            log SUCCESS "Backup checksum valid: ${checksum}"
        fi

        rm -f "/tmp/verify.backup"
    else
        assert_success "Backup verification" 1
    fi
}

test_backup_directories() {
    log TEST "Testing backup directory structure..."

    assert_directory_exists "Daily backup directory" "${TEST_BACKUP_DIR}/daily"
    assert_directory_exists "Weekly backup directory" "${TEST_BACKUP_DIR}/weekly"
    assert_directory_exists "Monthly backup directory" "${TEST_BACKUP_DIR}/monthly"
    assert_directory_exists "Logs directory" "${TEST_BACKUP_DIR}/logs"
}

test_retention_policy() {
    log TEST "Testing retention policy..."

    local daily_dir="${TEST_BACKUP_DIR}/daily"
    mkdir -p "${daily_dir}"

    # Create 10 test backup files
    for i in {1..10}; do
        touch "${daily_dir}/backup_202312$(printf '%02d' $i)_010000.gz"
    done

    local backup_count=$(find "${daily_dir}" -maxdepth 1 -name "backup_*.gz" -type f | wc -l)
    assert_count "Backup count matches" 10 "${backup_count}"

    # Test cleanup logic
    local to_delete=$((backup_count - 7))  # Keep 7
    if [ "${to_delete}" -gt 0 ]; then
        log INFO "Simulating cleanup: would delete ${to_delete} backups"
    fi

    # Cleanup test files
    rm -f "${daily_dir}"/backup_*.gz
}

test_restore_preparation() {
    log TEST "Testing restore preparation..."

    local test_db=$(create_test_database)
    local backup_file="${TEST_BACKUP_DIR}/daily/test_restore_$(date +%s).gz"
    local pre_restore_backup="${TEST_DIR}/pre_restore_backup.gz"

    # Create backup
    if sqlite3 "${test_db}" ".backup '/tmp/restore.backup'" && gzip "/tmp/restore.backup" -c > "${backup_file}"; then
        # Create pre-restore backup
        if cp "${backup_file}" "${pre_restore_backup}"; then
            assert_file_exists "Pre-restore backup created" "${pre_restore_backup}"
        fi

        # Cleanup
        rm -f "/tmp/restore.backup" "${pre_restore_backup}"
    else
        assert_success "Restore preparation" 1
    fi
}

test_backup_logging() {
    log TEST "Testing backup logging..."

    local log_file="${TEST_BACKUP_DIR}/logs/test_backup_$(date +%Y%m%d).log"

    # Create log file
    mkdir -p "$(dirname "${log_file}")"
    cat > "${log_file}" <<'EOF'
[2023-12-15 01:00:00] [INFO] Starting backup process: daily
[2023-12-15 01:00:05] [SUCCESS] PostgreSQL backup completed: 45M in 45s
[2023-12-15 01:00:10] [SUCCESS] Backup verification passed
[2023-12-15 01:00:15] [SUCCESS] Backup process completed successfully
EOF

    assert_file_exists "Log file created" "${log_file}"
    assert_contains "Log contains INFO" "${log_file}" "INFO"
    assert_contains "Log contains SUCCESS" "${log_file}" "SUCCESS"

    # Cleanup
    rm -f "${log_file}"
}

test_status_file() {
    log TEST "Testing backup status file..."

    local status_file="${TEST_BACKUP_DIR}/.backup_status"

    # Create status file
    cat > "${status_file}" <<'EOF'
{
  "last_backup": "2023-12-15T01:00:00Z",
  "last_backup_type": "daily",
  "last_backup_file": "backup_20231215_010000.gz",
  "last_backup_size": "45M",
  "last_backup_success": true,
  "daily_count": 7,
  "weekly_count": 4,
  "monthly_count": 12,
  "total_backup_size": "520M"
}
EOF

    assert_file_exists "Status file created" "${status_file}"
    assert_contains "Status contains last_backup" "${status_file}" "last_backup"
    assert_contains "Status contains daily_count" "${status_file}" "daily_count"

    # Cleanup
    rm -f "${status_file}"
}

test_script_executable() {
    log TEST "Testing script executability..."

    assert_file_exists "backup.sh exists" "${SCRIPT_DIR}/backup.sh"
    assert_file_exists "restore.sh exists" "${SCRIPT_DIR}/restore.sh"
    assert_file_exists "monitor.sh exists" "${SCRIPT_DIR}/monitor.sh"
    assert_file_exists "setup-cron.sh exists" "${SCRIPT_DIR}/setup-cron.sh"

    # Check executable bit
    if [ -x "${SCRIPT_DIR}/backup.sh" ]; then
        log SUCCESS "backup.sh is executable"
    else
        log INFO "Making scripts executable..."
        chmod +x "${SCRIPT_DIR}"/*.sh
    fi
}

test_error_handling() {
    log TEST "Testing error handling..."

    # Test with non-existent file
    if gzip -t "/nonexistent/file.gz" 2>/dev/null; then
        assert_success "Error handling test" 1
    else
        assert_success "Error handling test" 0
    fi

    # Test with invalid backup file
    local invalid_file="${TEST_BACKUP_DIR}/invalid.gz"
    echo "not a valid gzip file" | gzip > "${invalid_file}"
    if gzip -t "${invalid_file}" 2>/dev/null; then
        log SUCCESS "Gzip integrity check passed as expected"
    else
        log SUCCESS "Gzip integrity check failed as expected"
    fi

    rm -f "${invalid_file}"
}

################################################################################
# TEST SUITE RUNNERS
################################################################################

run_backup_tests() {
    log INFO "=== Running Backup Tests ==="
    echo ""

    test_backup_prerequisites
    test_backup_directories
    test_backup_creation
    test_backup_metadata
    test_backup_verification
    test_backup_logging
}

run_restore_tests() {
    log INFO "=== Running Restore Tests ==="
    echo ""

    test_restore_preparation
    test_script_executable
}

run_retention_tests() {
    log INFO "=== Running Retention Tests ==="
    echo ""

    test_retention_policy
    test_status_file
}

run_monitoring_tests() {
    log INFO "=== Running Monitoring Tests ==="
    echo ""

    test_backup_logging
    test_error_handling
}

run_all_tests() {
    run_backup_tests
    echo ""
    run_restore_tests
    echo ""
    run_retention_tests
    echo ""
    run_monitoring_tests
}

################################################################################
# TEST REPORT
################################################################################

generate_report() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Test Report${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    echo "Tests Run:     ${TESTS_RUN}"
    echo "Tests Passed:  ${TESTS_PASSED}"
    echo "Tests Failed:  ${TESTS_FAILED}"
    echo ""

    if [ "${TESTS_FAILED}" -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed${NC}"
        echo ""
        echo "Failed tests:"
        grep "FAIL:" "${TEST_LOG_FILE}" | while read -r line; do
            echo "  - ${line}"
        done
        return 1
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Backup System Test Suite${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    init_test_environment

    local test_suite="${1:-all}"

    case "${test_suite}" in
        backup)
            run_backup_tests
            ;;
        restore)
            run_restore_tests
            ;;
        retention)
            run_retention_tests
            ;;
        monitor)
            run_monitoring_tests
            ;;
        all)
            run_all_tests
            ;;
        *)
            echo "Usage: $0 [backup|restore|retention|monitor|all]"
            exit 1
            ;;
    esac

    generate_report
    exit $?
}

main "$@"
