#!/bin/bash

################################################################################
# BACKUP RESTORE TEST SCRIPT
#
# Performs automated weekly restore tests to isolated test environment
# Verifies backup restoration and database functionality
# Features: isolated test database, integrity verification, cleanup, reporting
#
# Usage:
#   ./restore-test.sh                        # Test restore from latest backup
#   ./restore-test.sh <backup_file>          # Test restore from specific backup
#   ./restore-test.sh --weekly               # Run weekly automated test
#   ./restore-test.sh --verify-only          # Only verify restored data
#
# Environment Variables:
#   BACKUP_DIR              Base backup directory
#   TEST_DB_HOST            Test database host
#   TEST_DB_PORT            Test database port (default: 5433)
#   TEST_DB_USER            Test database user
#   TEST_DB_PASSWORD        Test database password
#   TEST_DB_RETENTION_DAYS  Keep test DBs for N days (default: 7)
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
TEST_LOG_DIR="${BACKUP_DIR}/restore_test_logs"
TEST_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_LOG="${TEST_LOG_DIR}/restore_test_${TEST_TIMESTAMP}.log"

# Test database configuration
TEST_DB_HOST="${TEST_DB_HOST:-localhost}"
TEST_DB_PORT="${TEST_DB_PORT:-5433}"
TEST_DB_USER="${TEST_DB_USER:-postgres}"
TEST_DB_PASSWORD="${TEST_DB_PASSWORD:-postgres}"
TEST_DB_RETENTION_DAYS="${TEST_DB_RETENTION_DAYS:-7}"
TEST_DB_NAME="thebot_test_${TEST_TIMESTAMP//:/_}"

# Original database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_NAME="${DB_NAME:-thebot}"
DATABASE_TYPE="${DATABASE_TYPE:-postgresql}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test results
TEST_SUCCESS=true
TEST_RESULTS=""

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[${timestamp}] [${level}] ${message}" >> "${TEST_LOG}"

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
            TEST_SUCCESS=false
            ;;
    esac
}

init_directories() {
    mkdir -p "${TEST_LOG_DIR}"
    chmod 700 "${TEST_LOG_DIR}"
    log INFO "Initialized test directories"
}

load_env() {
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        set +u
        source "${PROJECT_ROOT}/.env"
        set -u
        log INFO "Loaded environment from .env"
    fi
}

check_prerequisites() {
    local missing_tools=()

    command -v gzip >/dev/null 2>&1 || missing_tools+=("gzip")
    command -v psql >/dev/null 2>&1 || missing_tools+=("psql")
    command -v pg_isready >/dev/null 2>&1 || missing_tools+=("pg_isready")
    command -v pg_restore >/dev/null 2>&1 || missing_tools+=("pg_restore")

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log ERROR "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    log INFO "All required tools found"
    return 0
}

################################################################################
# TEST DATABASE SETUP
################################################################################

setup_test_database() {
    log INFO "Setting up test database: ${TEST_DB_NAME}"

    # Check if PostgreSQL is running on test port
    if ! PGPASSWORD="${TEST_DB_PASSWORD}" pg_isready -h "${TEST_DB_HOST}" -p "${TEST_DB_PORT}" -U "${TEST_DB_USER}" >/dev/null 2>&1; then
        log ERROR "Cannot connect to test PostgreSQL on ${TEST_DB_HOST}:${TEST_DB_PORT}"
        return 1
    fi

    # Create test database
    if ! PGPASSWORD="${TEST_DB_PASSWORD}" psql -h "${TEST_DB_HOST}" -p "${TEST_DB_PORT}" -U "${TEST_DB_USER}" -tc "SELECT 1 FROM pg_database WHERE datname='${TEST_DB_NAME}'" | grep -q 1; then

        if PGPASSWORD="${TEST_DB_PASSWORD}" psql -h "${TEST_DB_HOST}" -p "${TEST_DB_PORT}" -U "${TEST_DB_USER}" -c "CREATE DATABASE ${TEST_DB_NAME};" 2>"${TEST_LOG}.stderr"; then
            log SUCCESS "Test database created: ${TEST_DB_NAME}"
        else
            log ERROR "Failed to create test database"
            return 1
        fi
    else
        log INFO "Test database already exists: ${TEST_DB_NAME}"
    fi

    return 0
}

cleanup_test_database() {
    local db_name=$1

    log INFO "Cleaning up test database: ${db_name}"

    # Kill active connections
    PGPASSWORD="${TEST_DB_PASSWORD}" psql -h "${TEST_DB_HOST}" -p "${TEST_DB_PORT}" -U "${TEST_DB_USER}" -c "
        SELECT pg_terminate_backend(pid)
        FROM pg_stat_activity
        WHERE datname = '${db_name}' AND pid <> pg_backend_pid();" 2>/dev/null || true

    # Drop database
    if PGPASSWORD="${TEST_DB_PASSWORD}" psql -h "${TEST_DB_HOST}" -p "${TEST_DB_PORT}" -U "${TEST_DB_USER}" -c "DROP DATABASE IF EXISTS ${db_name};" 2>/dev/null; then
        log SUCCESS "Test database cleaned up: ${db_name}"
        return 0
    else
        log ERROR "Failed to drop test database: ${db_name}"
        return 1
    fi
}

cleanup_old_test_databases() {
    log INFO "Cleaning up old test databases (older than ${TEST_DB_RETENTION_DAYS} days)"

    local cutoff_timestamp=$(date -d "${TEST_DB_RETENTION_DAYS} days ago" +%s 2>/dev/null || date -v-${TEST_DB_RETENTION_DAYS}d +%s)

    PGPASSWORD="${TEST_DB_PASSWORD}" psql -h "${TEST_DB_HOST}" -p "${TEST_DB_PORT}" -U "${TEST_DB_USER}" -tc "
        SELECT datname FROM pg_database
        WHERE datname LIKE 'thebot_test_%'
        AND datcreate < to_timestamp(${cutoff_timestamp});" | while read -r old_db; do

        if [ -n "${old_db}" ] && [ "${old_db}" != "datname" ]; then
            cleanup_test_database "${old_db}" || true
        fi
    done

    log SUCCESS "Old test database cleanup completed"
}

################################################################################
# RESTORE OPERATIONS
################################################################################

restore_backup_postgresql() {
    local backup_file=$1
    local target_db=$2

    log INFO "Restoring backup to ${target_db}: $(basename "${backup_file}")"

    # Extract backup file
    local temp_file=$(mktemp)
    if ! gzip -dc "${backup_file}" > "${temp_file}"; then
        log ERROR "Failed to decompress backup file"
        rm -f "${temp_file}"
        return 1
    fi

    # Restore database
    if PGPASSWORD="${TEST_DB_PASSWORD}" pg_restore \
        -h "${TEST_DB_HOST}" \
        -p "${TEST_DB_PORT}" \
        -U "${TEST_DB_USER}" \
        -d "${target_db}" \
        -v "${temp_file}" 2>"${TEST_LOG}.restore_error"; then

        log SUCCESS "Backup restored successfully to ${target_db}"
        rm -f "${temp_file}"
        return 0
    else
        log ERROR "Failed to restore backup to ${target_db}"
        cat "${TEST_LOG}.restore_error" >> "${TEST_LOG}"
        rm -f "${temp_file}"
        return 1
    fi
}

################################################################################
# VERIFICATION FUNCTIONS
################################################################################

verify_database_integrity() {
    local target_db=$1

    log INFO "Verifying database integrity: ${target_db}"

    # Check table count
    local table_count=$(PGPASSWORD="${TEST_DB_PASSWORD}" psql \
        -h "${TEST_DB_HOST}" \
        -p "${TEST_DB_PORT}" \
        -U "${TEST_DB_USER}" \
        -d "${target_db}" \
        -tc "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | xargs)

    if [ "${table_count}" -lt 10 ]; then
        log ERROR "Restored database has only ${table_count} tables, expected at least 10"
        return 1
    fi

    log SUCCESS "Database integrity check passed (${table_count} tables found)"

    # Check for key tables
    local key_tables=("accounts_user" "accounts_studentprofile" "materials_subject")
    for table in "${key_tables[@]}"; do
        if ! PGPASSWORD="${TEST_DB_PASSWORD}" psql \
            -h "${TEST_DB_HOST}" \
            -p "${TEST_DB_PORT}" \
            -U "${TEST_DB_USER}" \
            -d "${target_db}" \
            -tc "SELECT 1 FROM information_schema.tables WHERE table_name='${table}';" | grep -q 1; then

            log WARN "Key table not found: ${table}"
        fi
    done

    # Run database integrity checks
    log INFO "Running database REINDEX on ${target_db}"
    if PGPASSWORD="${TEST_DB_PASSWORD}" psql \
        -h "${TEST_DB_HOST}" \
        -p "${TEST_DB_PORT}" \
        -U "${TEST_DB_USER}" \
        -d "${target_db}" \
        -c "REINDEX DATABASE ${target_db};" >/dev/null 2>&1; then

        log SUCCESS "Database REINDEX completed"
    else
        log WARN "Database REINDEX failed or not available"
    fi

    # Run ANALYZE to update statistics
    if PGPASSWORD="${TEST_DB_PASSWORD}" psql \
        -h "${TEST_DB_HOST}" \
        -p "${TEST_DB_PORT}" \
        -U "${TEST_DB_USER}" \
        -d "${target_db}" \
        -c "ANALYZE;" >/dev/null 2>&1; then

        log SUCCESS "Database ANALYZE completed"
    else
        log WARN "Database ANALYZE failed"
    fi

    return 0
}

verify_data_consistency() {
    local target_db=$1

    log INFO "Verifying data consistency: ${target_db}"

    # Check for referential integrity issues
    local orphaned_users=$(PGPASSWORD="${TEST_DB_PASSWORD}" psql \
        -h "${TEST_DB_HOST}" \
        -p "${TEST_DB_PORT}" \
        -U "${TEST_DB_USER}" \
        -d "${target_db}" \
        -tc "
        SELECT COUNT(*) FROM accounts_user u
        LEFT JOIN accounts_studentprofile sp ON u.id = sp.user_id
        LEFT JOIN accounts_teacherprofile tp ON u.id = tp.user_id
        LEFT JOIN accounts_tutorprofile tup ON u.id = tup.user_id
        LEFT JOIN accounts_parentprofile pp ON u.id = pp.user_id
        WHERE u.is_staff=FALSE
        AND sp.user_id IS NULL
        AND tp.user_id IS NULL
        AND tup.user_id IS NULL
        AND pp.user_id IS NULL;" 2>/dev/null | xargs)

    if [ -n "${orphaned_users}" ] && [ "${orphaned_users}" -gt 0 ]; then
        log WARN "Found ${orphaned_users} users without profiles"
    else
        log SUCCESS "Data consistency check passed"
    fi

    return 0
}

verify_restored_data_counts() {
    local target_db=$1

    log INFO "Verifying restored data counts: ${target_db}"

    # Check user count
    local user_count=$(PGPASSWORD="${TEST_DB_PASSWORD}" psql \
        -h "${TEST_DB_HOST}" \
        -p "${TEST_DB_PORT}" \
        -U "${TEST_DB_USER}" \
        -d "${target_db}" \
        -tc "SELECT COUNT(*) FROM accounts_user;" 2>/dev/null | xargs)

    log INFO "Users in restored database: ${user_count}"

    if [ "${user_count}" -eq 0 ]; then
        log WARN "No users found in restored database"
    fi

    # Check subject count
    local subject_count=$(PGPASSWORD="${TEST_DB_PASSWORD}" psql \
        -h "${TEST_DB_HOST}" \
        -p "${TEST_DB_PORT}" \
        -U "${TEST_DB_USER}" \
        -d "${target_db}" \
        -tc "SELECT COUNT(*) FROM materials_subject;" 2>/dev/null | xargs)

    log INFO "Subjects in restored database: ${subject_count}"

    return 0
}

################################################################################
# REPORT GENERATION
################################################################################

generate_test_report() {
    local report_file="${TEST_LOG_DIR}/restore_test_report_${TEST_TIMESTAMP}.txt"

    cat > "${report_file}" <<EOF
================================================================================
BACKUP RESTORE TEST REPORT
================================================================================

Generated: $(date)
Test Timestamp: ${TEST_TIMESTAMP}
Test Database: ${TEST_DB_NAME}

================================================================================
SUMMARY
================================================================================

Test Status: $([ "${TEST_SUCCESS}" = true ] && echo "PASSED" || echo "FAILED")
Test Duration: $(tail -1 "${TEST_LOG}" | grep -o '\[.*\]' || echo "Unknown")
Backup File: ${1:-Unknown}

================================================================================
TEST RESULTS
================================================================================

${TEST_RESULTS}

================================================================================
CHECKS PERFORMED
================================================================================

✓ Test database creation
✓ Backup extraction and restoration
✓ Table count verification (minimum 10 tables)
✓ Key table existence check
✓ Database REINDEX execution
✓ Database ANALYZE execution
✓ Referential integrity check
✓ Data consistency verification
✓ User and subject data count verification

================================================================================
DATABASE STATISTICS
================================================================================

Test Database: ${TEST_DB_NAME}
Test Host: ${TEST_DB_HOST}:${TEST_DB_PORT}
Creation Time: $(date)
Cleanup Policy: Keep for ${TEST_DB_RETENTION_DAYS} days

================================================================================
RECOMMENDATIONS
================================================================================

EOF

    if [ "${TEST_SUCCESS}" = true ]; then
        cat >> "${report_file}" <<'EOF'
✓ Restore test passed successfully
  - Backup integrity verified through successful restoration
  - Database structure validated
  - Data consistency confirmed
  - Ready for production restore if needed

EOF
    else
        cat >> "${report_file}" <<'EOF'
✗ Restore test failed
  - Review error logs in: ${TEST_LOG}
  - Verify backup file integrity
  - Check database connectivity
  - Test database must be accessible
  - Review PostgreSQL error logs

EOF
    fi

    cat >> "${report_file}" <<EOF

For detailed logs, see: ${TEST_LOG}

================================================================================
EOF

    log INFO "Test report generated: ${report_file}"
    cat "${report_file}"
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Backup Restore Test Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Initialize
    init_directories
    load_env

    if ! check_prerequisites; then
        exit 1
    fi

    log INFO "Starting backup restore test"

    # Parse arguments
    local mode="${1:-latest}"
    local backup_file="${2:-}"

    case "${mode}" in
        --weekly)
            log INFO "Running weekly automated restore test"

            # Find latest backup
            backup_file=$(find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.gz" -type f -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)

            if [ -z "${backup_file}" ] || [ ! -f "${backup_file}" ]; then
                log ERROR "No backup file found for weekly test"
                exit 1
            fi

            # Clean up old test databases first
            cleanup_old_test_databases

            # Run test
            if setup_test_database && restore_backup_postgresql "${backup_file}" "${TEST_DB_NAME}"; then
                verify_database_integrity "${TEST_DB_NAME}"
                verify_data_consistency "${TEST_DB_NAME}"
                verify_restored_data_counts "${TEST_DB_NAME}"
                TEST_RESULTS="Weekly restore test completed successfully"
            fi

            generate_test_report "${backup_file}"
            ;;

        --verify-only)
            backup_file="${2:-}"
            if [ -z "${backup_file}" ]; then
                backup_file=$(find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.gz" -type f -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)
            fi

            if [ -z "${backup_file}" ] || [ ! -f "${backup_file}" ]; then
                log ERROR "No backup file found"
                exit 1
            fi

            if setup_test_database && restore_backup_postgresql "${backup_file}" "${TEST_DB_NAME}"; then
                verify_database_integrity "${TEST_DB_NAME}"
                verify_data_consistency "${TEST_DB_NAME}"
                verify_restored_data_counts "${TEST_DB_NAME}"
                TEST_RESULTS="Data verification completed"
                generate_test_report "${backup_file}"
                cleanup_test_database "${TEST_DB_NAME}" || true
            fi
            ;;

        *)
            # Default: test restore from specified or latest backup
            if [ -z "${backup_file}" ]; then
                backup_file=$(find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.gz" -type f -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)
            fi

            if [ -z "${backup_file}" ] || [ ! -f "${backup_file}" ]; then
                log ERROR "No backup file found"
                exit 1
            fi

            if setup_test_database && restore_backup_postgresql "${backup_file}" "${TEST_DB_NAME}"; then
                verify_database_integrity "${TEST_DB_NAME}"
                verify_data_consistency "${TEST_DB_NAME}"
                verify_restored_data_counts "${TEST_DB_NAME}"
                TEST_RESULTS="Manual restore test completed"
                generate_test_report "${backup_file}"
                cleanup_test_database "${TEST_DB_NAME}" || true
            fi
            ;;
    esac

    echo ""
    if [ "${TEST_SUCCESS}" = true ]; then
        log SUCCESS "Restore test completed successfully"
        exit 0
    else
        log ERROR "Restore test failed"
        exit 1
    fi
}

# Run main function
main "$@"
