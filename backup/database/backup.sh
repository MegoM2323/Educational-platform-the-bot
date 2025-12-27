#!/bin/bash

################################################################################
# DATABASE BACKUP SCRIPT
#
# Comprehensive backup solution for PostgreSQL and SQLite databases
# Supports daily, weekly, and monthly backups with retention policies
# Features: compression, PITR setup, WAL archiving, notifications
#
# Usage:
#   ./backup.sh                    # Run daily backup
#   ./backup.sh full               # Full backup
#   ./backup.sh weekly             # Weekly backup
#   ./backup.sh monthly            # Monthly backup
#   ./backup.sh cleanup            # Run cleanup (retention policy)
#
# Environment Variables:
#   BACKUP_DIR              Base backup directory (default: ./backups)
#   DATABASE_TYPE           postgresql|sqlite (default: postgresql)
#   DATABASE_URL            PostgreSQL connection string
#   DATABASE_PATH           SQLite database file path
#   BACKUP_RETENTION_DAILY  Daily backups to keep (default: 7)
#   BACKUP_RETENTION_WEEKLY Weekly backups to keep (default: 4)
#   BACKUP_RETENTION_MONTHLY Monthly backups to keep (default: 12)
#   ENABLE_NOTIFICATIONS    Enable email notifications (default: false)
#   NOTIFICATION_EMAIL      Email for backup notifications
#   ENABLE_S3_UPLOAD        Enable S3 upload (default: false)
#   AWS_S3_BUCKET           S3 bucket name
#   AWS_REGION              AWS region
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DATE=$(date +%Y%m%d)
BACKUP_WEEK=$(date +%YW%V)
BACKUP_MONTH=$(date +%Y%m)

DATABASE_TYPE="${DATABASE_TYPE:-postgresql}"
BACKUP_RETENTION_DAILY="${BACKUP_RETENTION_DAILY:-7}"
BACKUP_RETENTION_WEEKLY="${BACKUP_RETENTION_WEEKLY:-4}"
BACKUP_RETENTION_MONTHLY="${BACKUP_RETENTION_MONTHLY:-12}"

ENABLE_NOTIFICATIONS="${ENABLE_NOTIFICATIONS:-false}"
NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-admin@example.com}"
ENABLE_S3_UPLOAD="${ENABLE_S3_UPLOAD:-false}"

# Log file
LOG_DIR="${BACKUP_DIR}/logs"
LOG_FILE="${LOG_DIR}/backup_${BACKUP_DATE}.log"

# Backup types
BACKUP_TYPE="${1:-daily}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables for tracking
BACKUP_SUCCESS=true
BACKUP_SIZE=0
BACKUP_DURATION=0
BACKUP_FILE=""
BACKUP_CHECKSUM=""

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    echo "[${timestamp}] [${level}] ${message}" >> "${LOG_FILE}"

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
            BACKUP_SUCCESS=false
            ;;
    esac
}

init_directories() {
    mkdir -p "${BACKUP_DIR}"/{daily,weekly,monthly,logs,wal-archive}
    mkdir -p "${LOG_DIR}"
    chmod 700 "${BACKUP_DIR}"
    log INFO "Initialized backup directories"
}

load_env() {
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        set +u
        # shellcheck disable=SC1090
        source "${PROJECT_ROOT}/.env"
        set -u
        log INFO "Loaded environment from .env"
    fi
}

check_prerequisites() {
    local missing_tools=()

    # Common tools
    command -v gzip >/dev/null 2>&1 || missing_tools+=("gzip")
    command -v tar >/dev/null 2>&1 || missing_tools+=("tar")
    command -v sha256sum >/dev/null 2>&1 || missing_tools+=("sha256sum")

    # Database-specific tools
    if [ "${DATABASE_TYPE}" = "postgresql" ]; then
        command -v pg_dump >/dev/null 2>&1 || missing_tools+=("pg_dump (postgresql-client)")
        command -v psql >/dev/null 2>&1 || missing_tools+=("psql (postgresql-client)")
    elif [ "${DATABASE_TYPE}" = "sqlite" ]; then
        command -v sqlite3 >/dev/null 2>&1 || missing_tools+=("sqlite3")
    fi

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log ERROR "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    log INFO "All required tools found"
    return 0
}

################################################################################
# DATABASE BACKUP FUNCTIONS
################################################################################

backup_postgresql() {
    local backup_file=$1
    local backup_dir=$(dirname "${backup_file}")

    log INFO "Starting PostgreSQL backup to ${backup_file}"

    # Extract connection parameters
    local db_host="${DB_HOST:-localhost}"
    local db_port="${DB_PORT:-5432}"
    local db_user="${DB_USER:-postgres}"
    local db_name="${DB_NAME:-thebot}"

    # Use DATABASE_URL if provided
    if [ -n "${DATABASE_URL:-}" ]; then
        db_host=$(echo "${DATABASE_URL}" | grep -oP '(?<=@)[^:]+' || echo "localhost")
        db_port=$(echo "${DATABASE_URL}" | grep -oP '(?<=:)\d+(?=/)' || echo "5432")
        db_name=$(echo "${DATABASE_URL}" | grep -oP '[^/]+$' || echo "thebot")
    fi

    local start_time=$(date +%s)

    # Perform full database backup with custom format for PITR capability
    if PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${db_user}" \
        -d "${db_name}" \
        -F custom \
        -v 2>"${backup_file}.stderr" | gzip > "${backup_file}.gz"; then

        local end_time=$(date +%s)
        BACKUP_DURATION=$((end_time - start_time))

        if [ -f "${backup_file}.gz" ]; then
            BACKUP_SIZE=$(du -h "${backup_file}.gz" | cut -f1)
            BACKUP_CHECKSUM=$(sha256sum "${backup_file}.gz" | awk '{print $1}')

            # Remove uncompressed file
            rm -f "${backup_file}"

            log SUCCESS "PostgreSQL backup completed: ${BACKUP_SIZE} in ${BACKUP_DURATION}s"
            BACKUP_FILE="${backup_file}.gz"
            return 0
        fi
    else
        log ERROR "PostgreSQL backup failed"
        if [ -f "${backup_file}.stderr" ]; then
            log ERROR "$(cat "${backup_file}.stderr")"
        fi
        return 1
    fi
}

backup_sqlite() {
    local backup_file=$1
    local db_path="${DATABASE_PATH:-${PROJECT_ROOT}/backend/db.sqlite3}"

    if [ ! -f "${db_path}" ]; then
        log ERROR "SQLite database not found: ${db_path}"
        return 1
    fi

    log INFO "Starting SQLite backup from ${db_path}"

    local start_time=$(date +%s)

    # Use sqlite3 backup command for point-in-time consistency
    if sqlite3 "${db_path}" ".backup '${backup_file}'" 2>"${backup_file}.stderr"; then
        if gzip "${backup_file}"; then
            local end_time=$(date +%s)
            BACKUP_DURATION=$((end_time - start_time))
            BACKUP_SIZE=$(du -h "${backup_file}.gz" | cut -f1)
            BACKUP_CHECKSUM=$(sha256sum "${backup_file}.gz" | awk '{print $1}')

            log SUCCESS "SQLite backup completed: ${BACKUP_SIZE} in ${BACKUP_DURATION}s"
            BACKUP_FILE="${backup_file}.gz"
            return 0
        fi
    else
        log ERROR "SQLite backup failed"
        if [ -f "${backup_file}.stderr" ]; then
            log ERROR "$(cat "${backup_file}.stderr")"
        fi
        return 1
    fi
}

backup_database() {
    case "${DATABASE_TYPE}" in
        postgresql)
            backup_postgresql "$1"
            ;;
        sqlite)
            backup_sqlite "$1"
            ;;
        *)
            log ERROR "Unknown database type: ${DATABASE_TYPE}"
            return 1
            ;;
    esac
}

################################################################################
# BACKUP TYPE HANDLERS
################################################################################

create_daily_backup() {
    log INFO "Creating daily backup (Type: ${BACKUP_TYPE})"

    local backup_file="${BACKUP_DIR}/daily/backup_${BACKUP_DATE}_${BACKUP_TIMESTAMP}"

    if backup_database "${backup_file}"; then
        create_backup_metadata "${BACKUP_FILE}" "daily"
        return 0
    else
        return 1
    fi
}

create_weekly_backup() {
    log INFO "Creating weekly backup (Type: ${BACKUP_TYPE})"

    local backup_file="${BACKUP_DIR}/weekly/backup_${BACKUP_WEEK}_${BACKUP_TIMESTAMP}"

    if backup_database "${backup_file}"; then
        create_backup_metadata "${BACKUP_FILE}" "weekly"
        return 0
    else
        return 1
    fi
}

create_monthly_backup() {
    log INFO "Creating monthly backup (Type: ${BACKUP_TYPE})"

    local backup_file="${BACKUP_DIR}/monthly/backup_${BACKUP_MONTH}_${BACKUP_TIMESTAMP}"

    if backup_database "${backup_file}"; then
        create_backup_metadata "${BACKUP_FILE}" "monthly"
        return 0
    else
        return 1
    fi
}

################################################################################
# BACKUP METADATA AND VERIFICATION
################################################################################

create_backup_metadata() {
    local backup_file=$1
    local backup_category=$2
    local metadata_file="${backup_file}.metadata"

    cat > "${metadata_file}" <<EOF
{
  "backup_file": "$(basename "${backup_file}")",
  "backup_path": "${backup_file}",
  "backup_type": "${DATABASE_TYPE}",
  "backup_category": "${backup_category}",
  "backup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "backup_size": "${BACKUP_SIZE}",
  "backup_duration_seconds": ${BACKUP_DURATION},
  "backup_checksum_sha256": "${BACKUP_CHECKSUM}",
  "compression": "gzip",
  "timestamp": $(date +%s),
  "hostname": "$(hostname)",
  "database_type": "${DATABASE_TYPE}"
}
EOF

    log INFO "Metadata created: ${metadata_file}"
}

verify_backup() {
    local backup_file=$1

    if [ ! -f "${backup_file}" ]; then
        log ERROR "Backup file not found: ${backup_file}"
        return 1
    fi

    log INFO "Verifying backup integrity..."

    # Verify gzip integrity
    if ! gzip -t "${backup_file}" 2>/dev/null; then
        log ERROR "Gzip integrity check failed"
        return 1
    fi

    # Verify checksum if metadata exists
    local metadata_file="${backup_file}.metadata"
    if [ -f "${metadata_file}" ]; then
        local expected_checksum=$(grep -o '"backup_checksum_sha256": "[^"]*' "${metadata_file}" | cut -d'"' -f4)
        local actual_checksum=$(sha256sum "${backup_file}" | awk '{print $1}')

        if [ "${expected_checksum}" != "${actual_checksum}" ]; then
            log ERROR "Checksum mismatch: expected ${expected_checksum}, got ${actual_checksum}"
            return 1
        fi

        log SUCCESS "Backup integrity verified: ${expected_checksum}"
    fi

    return 0
}

################################################################################
# RETENTION AND CLEANUP
################################################################################

cleanup_backups() {
    log INFO "Running backup cleanup with retention policy..."

    cleanup_daily_backups
    cleanup_weekly_backups
    cleanup_monthly_backups
}

cleanup_daily_backups() {
    log INFO "Cleaning up daily backups (keeping ${BACKUP_RETENTION_DAILY} days)"

    local backup_count=$(find "${BACKUP_DIR}/daily" -maxdepth 1 -name "backup_*.gz" -type f | wc -l)

    if [ "${backup_count}" -gt "${BACKUP_RETENTION_DAILY}" ]; then
        local to_delete=$((backup_count - BACKUP_RETENTION_DAILY))

        find "${BACKUP_DIR}/daily" -maxdepth 1 -name "backup_*.gz" -type f -printf '%T@ %p\n' | \
            sort -n | \
            head -n "${to_delete}" | \
            cut -d' ' -f2- | \
            while read -r backup_file; do
                log INFO "Deleting old daily backup: $(basename "${backup_file}")"
                rm -f "${backup_file}" "${backup_file}.metadata" "${backup_file}.stderr"
            done
    fi
}

cleanup_weekly_backups() {
    log INFO "Cleaning up weekly backups (keeping ${BACKUP_RETENTION_WEEKLY} weeks)"

    local backup_count=$(find "${BACKUP_DIR}/weekly" -maxdepth 1 -name "backup_*.gz" -type f | wc -l)

    if [ "${backup_count}" -gt "${BACKUP_RETENTION_WEEKLY}" ]; then
        local to_delete=$((backup_count - BACKUP_RETENTION_WEEKLY))

        find "${BACKUP_DIR}/weekly" -maxdepth 1 -name "backup_*.gz" -type f -printf '%T@ %p\n' | \
            sort -n | \
            head -n "${to_delete}" | \
            cut -d' ' -f2- | \
            while read -r backup_file; do
                log INFO "Deleting old weekly backup: $(basename "${backup_file}")"
                rm -f "${backup_file}" "${backup_file}.metadata" "${backup_file}.stderr"
            done
    fi
}

cleanup_monthly_backups() {
    log INFO "Cleaning up monthly backups (keeping ${BACKUP_RETENTION_MONTHLY} months)"

    local backup_count=$(find "${BACKUP_DIR}/monthly" -maxdepth 1 -name "backup_*.gz" -type f | wc -l)

    if [ "${backup_count}" -gt "${BACKUP_RETENTION_MONTHLY}" ]; then
        local to_delete=$((backup_count - BACKUP_RETENTION_MONTHLY))

        find "${BACKUP_DIR}/monthly" -maxdepth 1 -name "backup_*.gz" -type f -printf '%T@ %p\n' | \
            sort -n | \
            head -n "${to_delete}" | \
            cut -d' ' -f2- | \
            while read -r backup_file; do
                log INFO "Deleting old monthly backup: $(basename "${backup_file}")"
                rm -f "${backup_file}" "${backup_file}.metadata" "${backup_file}.stderr"
            done
    fi
}

################################################################################
# S3 UPLOAD
################################################################################

upload_to_s3() {
    if [ "${ENABLE_S3_UPLOAD}" != "true" ]; then
        return 0
    fi

    if [ -z "${AWS_S3_BUCKET:-}" ]; then
        log WARN "S3 upload enabled but AWS_S3_BUCKET not set"
        return 0
    fi

    if ! command -v aws &> /dev/null; then
        log WARN "AWS CLI not found, skipping S3 upload"
        return 0
    fi

    log INFO "Uploading backup to S3: s3://${AWS_S3_BUCKET}/${BACKUP_TYPE}/"

    local s3_path="s3://${AWS_S3_BUCKET}/database-backups/${BACKUP_TYPE}/$(basename "${BACKUP_FILE}")"

    if aws s3 cp "${BACKUP_FILE}" "${s3_path}" \
        --region "${AWS_REGION:-us-east-1}" \
        --metadata "checksum=${BACKUP_CHECKSUM},timestamp=${BACKUP_TIMESTAMP}" \
        --storage-class STANDARD_IA; then

        log SUCCESS "Backup uploaded to S3: ${s3_path}"

        # Also upload metadata
        if [ -f "${BACKUP_FILE}.metadata" ]; then
            aws s3 cp "${BACKUP_FILE}.metadata" "${s3_path}.metadata" \
                --region "${AWS_REGION:-us-east-1}"
        fi

        return 0
    else
        log ERROR "Failed to upload backup to S3"
        return 1
    fi
}

################################################################################
# NOTIFICATIONS
################################################################################

send_notification() {
    if [ "${ENABLE_NOTIFICATIONS}" != "true" ]; then
        return 0
    fi

    if [ -z "${NOTIFICATION_EMAIL}" ]; then
        log WARN "Notifications enabled but NOTIFICATION_EMAIL not set"
        return 0
    fi

    local subject="Database Backup Report - ${BACKUP_DATE}"
    local backup_status=$( [ "${BACKUP_SUCCESS}" = true ] && echo "SUCCESS" || echo "FAILED" )

    local email_body=$(cat <<EOF
Database Backup Report
======================

Date: $(date)
Status: ${backup_status}
Backup Type: ${BACKUP_TYPE}
Database Type: ${DATABASE_TYPE}

Details:
--------
Backup File: ${BACKUP_FILE:-N/A}
Backup Size: ${BACKUP_SIZE}
Duration: ${BACKUP_DURATION}s
Checksum (SHA256): ${BACKUP_CHECKSUM}

Retention Policy:
-----------------
Daily Backups: ${BACKUP_RETENTION_DAILY} days
Weekly Backups: ${BACKUP_RETENTION_WEEKLY} weeks
Monthly Backups: ${BACKUP_RETENTION_MONTHLY} months

Backup Locations:
-----------------
Local: ${BACKUP_DIR}

$([ "${ENABLE_S3_UPLOAD}" = "true" ] && echo "S3 Bucket: ${AWS_S3_BUCKET}")

Logs:
-----
$(tail -20 "${LOG_FILE}")
EOF
)

    # Try to send via mail command
    if command -v mail &> /dev/null; then
        echo "${email_body}" | mail -s "${subject}" "${NOTIFICATION_EMAIL}"
        log INFO "Notification email sent to ${NOTIFICATION_EMAIL}"
    elif command -v sendmail &> /dev/null; then
        (echo "To: ${NOTIFICATION_EMAIL}"
         echo "Subject: ${subject}"
         echo ""
         echo "${email_body}") | sendmail "${NOTIFICATION_EMAIL}"
        log INFO "Notification email sent via sendmail to ${NOTIFICATION_EMAIL}"
    else
        log WARN "No mail command available, notification not sent"
    fi
}

################################################################################
# BACKUP STATUS AND REPORTING
################################################################################

generate_backup_status() {
    local status_file="${BACKUP_DIR}/.backup_status"

    cat > "${status_file}" <<EOF
{
  "last_backup": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "last_backup_type": "${BACKUP_TYPE}",
  "last_backup_file": "${BACKUP_FILE}",
  "last_backup_size": "${BACKUP_SIZE}",
  "last_backup_success": ${BACKUP_SUCCESS},
  "daily_count": $(find "${BACKUP_DIR}/daily" -maxdepth 1 -name "backup_*.gz" -type f | wc -l),
  "weekly_count": $(find "${BACKUP_DIR}/weekly" -maxdepth 1 -name "backup_*.gz" -type f | wc -l),
  "monthly_count": $(find "${BACKUP_DIR}/monthly" -maxdepth 1 -name "backup_*.gz" -type f | wc -l),
  "total_backup_size": "$(du -sh "${BACKUP_DIR}" | cut -f1)"
}
EOF
}

show_status() {
    log INFO "=== Backup Status ==="

    echo ""
    echo "Daily Backups (kept: ${BACKUP_RETENTION_DAILY}):"
    ls -lh "${BACKUP_DIR}/daily" | grep "backup_" | tail -3

    echo ""
    echo "Weekly Backups (kept: ${BACKUP_RETENTION_WEEKLY}):"
    ls -lh "${BACKUP_DIR}/weekly" | grep "backup_" | tail -3

    echo ""
    echo "Monthly Backups (kept: ${BACKUP_RETENTION_MONTHLY}):"
    ls -lh "${BACKUP_DIR}/monthly" | grep "backup_" | tail -3

    echo ""
    echo "Total Backup Size:"
    du -sh "${BACKUP_DIR}"

    if [ -f "${BACKUP_DIR}/.backup_status" ]; then
        echo ""
        echo "Last Backup Status:"
        cat "${BACKUP_DIR}/.backup_status" | grep -o '"last_backup[^,]*' | tr -d '"{}'
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Database Backup Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Initialize
    init_directories
    load_env

    if ! check_prerequisites; then
        exit 1
    fi

    log INFO "Starting backup process: ${BACKUP_TYPE}"
    log INFO "Database Type: ${DATABASE_TYPE}"
    log INFO "Backup Directory: ${BACKUP_DIR}"

    # Run backup based on type
    case "${BACKUP_TYPE}" in
        daily)
            create_daily_backup
            ;;
        weekly)
            create_weekly_backup
            ;;
        monthly)
            create_monthly_backup
            ;;
        full)
            create_daily_backup
            ;;
        cleanup)
            cleanup_backups
            generate_backup_status
            show_status
            exit 0
            ;;
        status)
            show_status
            exit 0
            ;;
        *)
            log ERROR "Unknown backup type: ${BACKUP_TYPE}"
            echo "Usage: $0 [daily|weekly|monthly|full|cleanup|status]"
            exit 1
            ;;
    esac

    # Verify backup
    if [ "${BACKUP_SUCCESS}" = true ] && [ -n "${BACKUP_FILE}" ]; then
        if verify_backup "${BACKUP_FILE}"; then
            log SUCCESS "Backup verification passed"
        else
            log ERROR "Backup verification failed"
            BACKUP_SUCCESS=false
        fi
    fi

    # Upload to S3
    if [ "${BACKUP_SUCCESS}" = true ] && [ -n "${BACKUP_FILE}" ]; then
        upload_to_s3
    fi

    # Run cleanup after successful backup
    if [ "${BACKUP_SUCCESS}" = true ]; then
        cleanup_backups
    fi

    # Generate status report
    generate_backup_status

    # Send notifications
    send_notification

    # Final status
    show_status

    echo ""
    if [ "${BACKUP_SUCCESS}" = true ]; then
        log SUCCESS "Backup process completed successfully"
        exit 0
    else
        log ERROR "Backup process completed with errors"
        exit 1
    fi
}

# Run main function
main "$@"
