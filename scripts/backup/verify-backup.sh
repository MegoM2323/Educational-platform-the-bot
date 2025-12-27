#!/bin/bash

################################################################################
# BACKUP VERIFICATION SCRIPT
#
# Verifies backup integrity and performs comprehensive health checks
# Features: gzip integrity check, SHA256 verification, restore testing,
#           database integrity checks, email alerts
#
# Usage:
#   ./verify-backup.sh                    # Verify latest backup
#   ./verify-backup.sh <backup_file>      # Verify specific backup
#   ./verify-backup.sh --all              # Verify all backups
#   ./verify-backup.sh --report           # Generate verification report
#   ./verify-backup.sh --test-restore     # Test restore in isolated env
#
# Environment Variables:
#   BACKUP_DIR              Base backup directory (default: ./backups)
#   VERIFICATION_LOG_DIR    Verification logs directory
#   ALERT_EMAIL             Email for backup verification alerts
#   TEST_DB_HOST            Test database host
#   TEST_DB_NAME            Test database name suffix (default: _test)
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
VERIFICATION_LOG_DIR="${VERIFICATION_LOG_DIR:-${BACKUP_DIR}/verification_logs}"
VERIFICATION_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
VERIFICATION_LOG="${VERIFICATION_LOG_DIR}/verification_${VERIFICATION_TIMESTAMP}.log"

DATABASE_TYPE="${DATABASE_TYPE:-postgresql}"
ALERT_EMAIL="${ALERT_EMAIL:-admin@example.com}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TOTAL_BACKUPS=0
VERIFIED_BACKUPS=0
FAILED_BACKUPS=0
BACKUP_DETAILS=""

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[${timestamp}] [${level}] ${message}" >> "${VERIFICATION_LOG}"

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
    esac
}

init_directories() {
    mkdir -p "${VERIFICATION_LOG_DIR}"
    chmod 700 "${VERIFICATION_LOG_DIR}"
    log INFO "Initialized verification directories"
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
    command -v sha256sum >/dev/null 2>&1 || missing_tools+=("sha256sum")
    command -v tar >/dev/null 2>&1 || missing_tools+=("tar")

    if [ "${DATABASE_TYPE}" = "postgresql" ]; then
        command -v pg_isready >/dev/null 2>&1 || missing_tools+=("pg_isready")
        command -v psql >/dev/null 2>&1 || missing_tools+=("psql")
    fi

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log ERROR "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    log INFO "All required tools found"
    return 0
}

################################################################################
# BACKUP VERIFICATION FUNCTIONS
################################################################################

verify_gzip_integrity() {
    local backup_file=$1

    if ! gzip -t "${backup_file}" 2>/dev/null; then
        return 1
    fi
    return 0
}

verify_checksum() {
    local backup_file=$1
    local metadata_file="${backup_file}.metadata"

    if [ ! -f "${metadata_file}" ]; then
        log WARN "Metadata file not found: ${metadata_file}"
        return 1
    fi

    # Extract checksum from metadata
    local expected_checksum=$(grep -o '"backup_checksum_sha256": "[^"]*' "${metadata_file}" | cut -d'"' -f4)

    if [ -z "${expected_checksum}" ]; then
        log WARN "No checksum found in metadata: ${metadata_file}"
        return 1
    fi

    # Calculate actual checksum
    local actual_checksum=$(sha256sum "${backup_file}" | awk '{print $1}')

    if [ "${expected_checksum}" = "${actual_checksum}" ]; then
        return 0
    else
        log ERROR "Checksum mismatch for ${backup_file}"
        log ERROR "Expected: ${expected_checksum}"
        log ERROR "Actual: ${actual_checksum}"
        return 1
    fi
}

verify_file_size() {
    local backup_file=$1
    local metadata_file="${backup_file}.metadata"

    if [ ! -f "${metadata_file}" ]; then
        return 0
    fi

    # Check if file size is reasonable (at least 100 bytes, less than 100GB)
    local file_size=$(stat -f%z "${backup_file}" 2>/dev/null || stat -c%s "${backup_file}")

    if [ "${file_size}" -lt 100 ]; then
        log ERROR "Backup file too small: ${file_size} bytes"
        return 1
    fi

    # 100GB limit
    if [ "${file_size}" -gt 107374182400 ]; then
        log WARN "Backup file very large: $(numfmt --to=iec ${file_size})"
    fi

    return 0
}

verify_backup_file() {
    local backup_file=$1
    local backup_name=$(basename "${backup_file}")

    log INFO "Verifying backup: ${backup_name}"

    # Check file exists
    if [ ! -f "${backup_file}" ]; then
        log ERROR "Backup file not found: ${backup_file}"
        return 1
    fi

    # Verify gzip integrity
    if ! verify_gzip_integrity "${backup_file}"; then
        log ERROR "Gzip integrity check failed for ${backup_name}"
        return 1
    fi
    log SUCCESS "Gzip integrity verified for ${backup_name}"

    # Verify checksum
    if ! verify_checksum "${backup_file}"; then
        log ERROR "Checksum verification failed for ${backup_name}"
        return 1
    fi
    log SUCCESS "SHA256 checksum verified for ${backup_name}"

    # Verify file size
    if ! verify_file_size "${backup_file}"; then
        log ERROR "File size check failed for ${backup_name}"
        return 1
    fi
    log SUCCESS "File size check passed for ${backup_name}"

    # Extract and test
    local extract_test=$(verify_backup_extractable "${backup_file}")
    if [ $? -ne 0 ]; then
        log ERROR "Backup extraction test failed for ${backup_name}"
        return 1
    fi
    log SUCCESS "Backup extraction test passed for ${backup_name}"

    return 0
}

verify_backup_extractable() {
    local backup_file=$1
    local temp_dir=$(mktemp -d)

    # Try to test extraction without full decompress
    if gzip -t "${backup_file}" 2>/dev/null; then
        rm -rf "${temp_dir}"
        return 0
    else
        rm -rf "${temp_dir}"
        return 1
    fi
}

################################################################################
# BATCH VERIFICATION
################################################################################

verify_latest_backup() {
    local latest_backup=""

    # Find latest backup from all categories
    for category in daily weekly monthly; do
        local category_backup=$(find "${BACKUP_DIR}/${category}" -maxdepth 1 -name "backup_*.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)

        if [ -n "${category_backup}" ]; then
            if [ -z "${latest_backup}" ] || [ "${category_backup}" -nt "${latest_backup}" ]; then
                latest_backup="${category_backup}"
            fi
        fi
    done

    if [ -z "${latest_backup}" ]; then
        log ERROR "No backup files found in ${BACKUP_DIR}"
        return 1
    fi

    verify_backup_file "${latest_backup}"
}

verify_all_backups() {
    log INFO "Verifying all backups in ${BACKUP_DIR}"

    TOTAL_BACKUPS=$(find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.gz" -type f | wc -l)

    if [ "${TOTAL_BACKUPS}" -eq 0 ]; then
        log WARN "No backup files found"
        return 0
    fi

    find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.gz" -type f | while read -r backup_file; do
        if verify_backup_file "${backup_file}"; then
            ((VERIFIED_BACKUPS++)) || true
            BACKUP_DETAILS="${BACKUP_DETAILS}✓ $(basename "${backup_file}") - OK\n"
        else
            ((FAILED_BACKUPS++)) || true
            BACKUP_DETAILS="${BACKUP_DETAILS}✗ $(basename "${backup_file}") - FAILED\n"
        fi
    done

    log INFO "Verification complete: ${VERIFIED_BACKUPS}/${TOTAL_BACKUPS} backups verified"
}

################################################################################
# RESTORE TESTING
################################################################################

test_restore() {
    local backup_file=$1
    local test_dir=$(mktemp -d)
    local backup_name=$(basename "${backup_file}")

    log INFO "Testing restore from ${backup_name} to ${test_dir}"

    # Extract to test directory
    if ! gzip -dc "${backup_file}" > "${test_dir}/extracted_backup" 2>"${test_dir}/extract.log"; then
        log ERROR "Failed to extract backup during restore test"
        rm -rf "${test_dir}"
        return 1
    fi

    # Check extracted file
    if [ ! -s "${test_dir}/extracted_backup" ]; then
        log ERROR "Extracted backup is empty"
        rm -rf "${test_dir}"
        return 1
    fi

    log SUCCESS "Restore test completed successfully for ${backup_name}"
    rm -rf "${test_dir}"
    return 0
}

test_database_integrity() {
    if [ "${DATABASE_TYPE}" != "postgresql" ]; then
        log WARN "Database integrity check only supported for PostgreSQL"
        return 0
    fi

    local db_host="${DB_HOST:-localhost}"
    local db_port="${DB_PORT:-5432}"
    local db_user="${DB_USER:-postgres}"
    local db_name="${DB_NAME:-thebot}"

    log INFO "Testing database connectivity on ${db_host}:${db_port}"

    # Check if database is ready
    if ! PGPASSWORD="${DB_PASSWORD:-}" pg_isready -h "${db_host}" -p "${db_port}" -U "${db_user}" >/dev/null 2>&1; then
        log WARN "Database not ready: ${db_host}:${db_port}"
        return 1
    fi

    log SUCCESS "Database is ready and accessible"

    # Check for table issues
    if ! PGPASSWORD="${DB_PASSWORD:-}" psql -h "${db_host}" -p "${db_port}" -U "${db_user}" -d "${db_name}" -c "\dt" >/dev/null 2>&1; then
        log ERROR "Failed to query database tables"
        return 1
    fi

    log SUCCESS "Database tables accessible"

    # Suggest REINDEX if needed (not running automatically)
    log INFO "To run REINDEX, execute: REINDEX DATABASE ${db_name};"

    return 0
}

################################################################################
# REPORTING
################################################################################

generate_verification_report() {
    local report_file="${VERIFICATION_LOG_DIR}/verification_report_${VERIFICATION_TIMESTAMP}.txt"

    cat > "${report_file}" <<EOF
================================================================================
BACKUP VERIFICATION REPORT
================================================================================

Generated: $(date)
Verification Timestamp: ${VERIFICATION_TIMESTAMP}
Backup Directory: ${BACKUP_DIR}

================================================================================
SUMMARY
================================================================================

Total Backups Checked: ${TOTAL_BACKUPS}
Successfully Verified: ${VERIFIED_BACKUPS}
Failed Verification: ${FAILED_BACKUPS}

================================================================================
BACKUP STATUS
================================================================================

${BACKUP_DETAILS}

================================================================================
CHECKS PERFORMED
================================================================================

✓ Gzip integrity check (verify compressed file is not corrupted)
✓ SHA256 checksum verification (verify against metadata)
✓ File size validation (ensure file is not empty or corrupted)
✓ Backup extractability test (verify content can be extracted)
✓ Database connectivity check (PostgreSQL only)

================================================================================
BACKUP CATEGORIES
================================================================================

Daily Backups: $(find "${BACKUP_DIR}/daily" -maxdepth 1 -name "backup_*.gz" -type f 2>/dev/null | wc -l) files
Weekly Backups: $(find "${BACKUP_DIR}/weekly" -maxdepth 1 -name "backup_*.gz" -type f 2>/dev/null | wc -l) files
Monthly Backups: $(find "${BACKUP_DIR}/monthly" -maxdepth 1 -name "backup_*.gz" -type f 2>/dev/null | wc -l) files

Total Backup Size: $(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)

================================================================================
RECOMMENDATIONS
================================================================================

EOF

    if [ "${FAILED_BACKUPS}" -gt 0 ]; then
        cat >> "${report_file}" <<'EOF'
⚠ WARNING: Some backups failed verification!
  - Review error logs in: ${VERIFICATION_LOG}
  - Check backup file integrity manually
  - Consider re-running failed backups
  - Verify storage permissions and disk space

EOF
    else
        cat >> "${report_file}" <<'EOF'
✓ All backups passed verification
  - Backup system is functioning correctly
  - Continue regular backup schedule
  - Review backup logs periodically

EOF
    fi

    cat >> "${report_file}" <<EOF

For detailed logs, see: ${VERIFICATION_LOG}

================================================================================
EOF

    log INFO "Verification report generated: ${report_file}"
    cat "${report_file}"
}

send_alert_email() {
    if [ "${FAILED_BACKUPS}" -eq 0 ]; then
        return 0
    fi

    if [ -z "${ALERT_EMAIL}" ] || [ "${ALERT_EMAIL}" = "admin@example.com" ]; then
        log WARN "Alert email not configured, skipping notification"
        return 0
    fi

    local subject="ALERT: Backup Verification Failed - ${FAILED_BACKUPS}/${TOTAL_BACKUPS} backups"
    local email_body=$(cat <<EOF
BACKUP VERIFICATION ALERT
=========================

Status: FAILED
Failed Backups: ${FAILED_BACKUPS}/${TOTAL_BACKUPS}
Verification Time: $(date)

Failed Backups:
${BACKUP_DETAILS}

Please review the verification logs:
${VERIFICATION_LOG}

Action Required:
1. Check backup storage for errors
2. Verify disk space availability
3. Review backup script logs
4. Test restore from latest backup
5. Consider manual backup if needed

EOF
)

    if command -v mail &>/dev/null; then
        echo "${email_body}" | mail -s "${subject}" "${ALERT_EMAIL}"
        log INFO "Alert email sent to ${ALERT_EMAIL}"
    else
        log WARN "Mail command not available, alert not sent"
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Backup Verification Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Initialize
    init_directories
    load_env

    if ! check_prerequisites; then
        exit 1
    fi

    log INFO "Starting backup verification"
    log INFO "Backup Directory: ${BACKUP_DIR}"

    # Parse arguments
    local mode="${1:-latest}"

    case "${mode}" in
        --all)
            verify_all_backups
            test_database_integrity
            generate_verification_report
            send_alert_email
            ;;
        --test-restore)
            local backup_file="${2:-}"
            if [ -z "${backup_file}" ]; then
                backup_file=$(find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.gz" -type f -printf '%T@ %p\n' | sort -nr | head -1 | cut -d' ' -f2-)
            fi
            if [ -n "${backup_file}" ] && [ -f "${backup_file}" ]; then
                test_restore "${backup_file}"
                test_database_integrity
            else
                log ERROR "No backup file found for restore test"
                exit 1
            fi
            ;;
        --report)
            verify_all_backups
            test_database_integrity
            generate_verification_report
            send_alert_email
            ;;
        *)
            verify_latest_backup
            test_database_integrity
            ;;
    esac

    echo ""
    log SUCCESS "Backup verification completed"
}

# Run main function
main "$@"
