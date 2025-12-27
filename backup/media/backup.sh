#!/bin/bash

################################################################################
# MEDIA FILES BACKUP SCRIPT
#
# Comprehensive backup solution for media files stored in the platform
# Supports daily snapshots, S3 storage, compression, and retention policies
# Features: incremental backups, checksums, verification, notifications
#
# Usage:
#   ./backup.sh                    # Run daily backup
#   ./backup.sh full               # Full backup
#   ./backup.sh incremental        # Incremental backup (changed files only)
#   ./backup.sh cleanup            # Run cleanup (retention policy)
#   ./backup.sh status             # Show backup status
#
# Environment Variables:
#   BACKUP_DIR              Base backup directory (default: ./backups)
#   MEDIA_DIR               Media directory to backup (default: ../../../backend/media)
#   BACKUP_RETENTION_DAYS   Days to keep backups (default: 30)
#   ENABLE_S3_UPLOAD        Enable S3 upload (default: false)
#   AWS_S3_BUCKET           S3 bucket name
#   AWS_REGION              AWS region (default: us-east-1)
#   ENABLE_NOTIFICATIONS    Enable email notifications (default: false)
#   NOTIFICATION_EMAIL      Email for notifications
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups/media}"
MEDIA_DIR="${MEDIA_DIR:-${PROJECT_ROOT}/backend/media}"
BACKUP_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_DATE=$(date +%Y%m%d)

BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"
ENABLE_S3_UPLOAD="${ENABLE_S3_UPLOAD:-false}"
ENABLE_NOTIFICATIONS="${ENABLE_NOTIFICATIONS:-false}"
NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-admin@example.com}"

# Log file
LOG_DIR="${BACKUP_DIR}/logs"
LOG_FILE="${LOG_DIR}/backup_${BACKUP_DATE}.log"

# Backup type
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
FILES_BACKED_UP=0
FILES_CHANGED=0
PREVIOUS_MANIFEST=""

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
    mkdir -p "${BACKUP_DIR}"/{full,incremental,logs}
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

    # Check required tools
    command -v tar >/dev/null 2>&1 || missing_tools+=("tar")
    command -v gzip >/dev/null 2>&1 || missing_tools+=("gzip")
    command -v sha256sum >/dev/null 2>&1 || missing_tools+=("sha256sum")
    command -v find >/dev/null 2>&1 || missing_tools+=("find")

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log ERROR "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    # Check media directory exists
    if [ ! -d "${MEDIA_DIR}" ]; then
        log WARN "Media directory not found: ${MEDIA_DIR}, creating empty backup"
        mkdir -p "${MEDIA_DIR}"
    fi

    log INFO "All required tools found"
    return 0
}

################################################################################
# MEDIA BACKUP FUNCTIONS
################################################################################

create_manifest() {
    local manifest_file=$1
    local media_path=$2

    log INFO "Creating file manifest: ${manifest_file}"

    if [ ! -d "${media_path}" ] || [ -z "$(find "${media_path}" -type f 2>/dev/null)" ]; then
        # Create empty manifest if no files
        echo "# Empty manifest - no media files" > "${manifest_file}"
        log WARN "Media directory is empty or does not exist"
        return 0
    fi

    # Create manifest with file paths and checksums
    find "${media_path}" -type f -exec sha256sum {} \; | sort > "${manifest_file}"
    log INFO "Manifest created with $(wc -l < "${manifest_file}") files"
}

detect_changed_files() {
    local current_manifest=$1
    local previous_manifest=$2
    local changed_files_list=$3

    if [ ! -f "${previous_manifest}" ]; then
        log INFO "No previous manifest found, treating as full backup"
        cp "${current_manifest}" "${changed_files_list}"
        FILES_CHANGED=$(wc -l < "${changed_files_list}")
        return 0
    fi

    # Find differences between manifests
    comm -13 <(sort "${previous_manifest}") <(sort "${current_manifest}") > "${changed_files_list}" || true

    FILES_CHANGED=$(wc -l < "${changed_files_list}")
    log INFO "Detected ${FILES_CHANGED} changed files"
}

backup_media_full() {
    local backup_file=$1
    local start_time=$(date +%s)

    log INFO "Starting full media backup to ${backup_file}"

    if [ ! -d "${MEDIA_DIR}" ]; then
        mkdir -p "${MEDIA_DIR}"
    fi

    # Create tar.gz archive of entire media directory
    if tar -czf "${backup_file}" -C "${MEDIA_DIR%/*}" "$(basename "${MEDIA_DIR}")" 2>"${backup_file}.stderr"; then
        local end_time=$(date +%s)
        BACKUP_DURATION=$((end_time - start_time))
        BACKUP_SIZE=$(du -h "${backup_file}" | cut -f1)
        BACKUP_CHECKSUM=$(sha256sum "${backup_file}" | awk '{print $1}')
        FILES_BACKED_UP=$(find "${MEDIA_DIR}" -type f | wc -l)

        log SUCCESS "Full media backup completed: ${BACKUP_SIZE} (${FILES_BACKED_UP} files) in ${BACKUP_DURATION}s"
        BACKUP_FILE="${backup_file}"
        return 0
    else
        log ERROR "Media backup failed"
        if [ -f "${backup_file}.stderr" ]; then
            log ERROR "$(cat "${backup_file}.stderr")"
        fi
        return 1
    fi
}

backup_media_incremental() {
    local backup_file=$1
    local manifest_file="${backup_file}.manifest"
    local previous_manifest="${BACKUP_DIR}/full/.last_manifest"
    local changed_files_list="${backup_file}.changed"
    local start_time=$(date +%s)

    log INFO "Starting incremental media backup to ${backup_file}"

    # Create current manifest
    create_manifest "${manifest_file}" "${MEDIA_DIR}"

    # Detect changed files
    detect_changed_files "${manifest_file}" "${previous_manifest}" "${changed_files_list}"

    if [ ! -s "${changed_files_list}" ]; then
        log INFO "No changes detected, skipping backup"
        BACKUP_FILE=""
        return 0
    fi

    # Create tar.gz archive with only changed files
    if [ -s "${changed_files_list}" ]; then
        # Extract file paths from changed_files_list (remove checksums)
        cut -d' ' -f3- "${changed_files_list}" > "${backup_file}.filelist"

        tar -czf "${backup_file}" \
            -C "${MEDIA_DIR}" \
            -T "${backup_file}.filelist" 2>"${backup_file}.stderr" || true

        if [ -f "${backup_file}" ] && [ -s "${backup_file}" ]; then
            local end_time=$(date +%s)
            BACKUP_DURATION=$((end_time - start_time))
            BACKUP_SIZE=$(du -h "${backup_file}" | cut -f1)
            BACKUP_CHECKSUM=$(sha256sum "${backup_file}" | awk '{print $1}')

            log SUCCESS "Incremental backup completed: ${BACKUP_SIZE} (${FILES_CHANGED} changed files) in ${BACKUP_DURATION}s"
            BACKUP_FILE="${backup_file}"

            # Save current manifest as previous for next incremental backup
            cp "${manifest_file}" "${previous_manifest}"
            return 0
        else
            log WARN "Backup file is empty"
            return 1
        fi
    fi

    return 1
}

################################################################################
# BACKUP TYPE HANDLERS
################################################################################

create_daily_backup() {
    log INFO "Creating daily backup (Type: full)"

    local backup_file="${BACKUP_DIR}/full/backup_${BACKUP_DATE}_${BACKUP_TIMESTAMP}.tar.gz"

    if backup_media_full "${backup_file}"; then
        create_backup_metadata "${BACKUP_FILE}" "daily"
        return 0
    else
        return 1
    fi
}

create_full_backup() {
    log INFO "Creating full backup"

    local backup_file="${BACKUP_DIR}/full/backup_${BACKUP_DATE}_${BACKUP_TIMESTAMP}.tar.gz"

    if backup_media_full "${backup_file}"; then
        create_backup_metadata "${BACKUP_FILE}" "full"
        # Save manifest for incremental backups
        create_manifest "${BACKUP_DIR}/full/.last_manifest" "${MEDIA_DIR}"
        return 0
    else
        return 1
    fi
}

create_incremental_backup() {
    log INFO "Creating incremental backup"

    local backup_file="${BACKUP_DIR}/incremental/backup_${BACKUP_DATE}_${BACKUP_TIMESTAMP}.tar.gz"

    if backup_media_incremental "${backup_file}"; then
        [ -n "${BACKUP_FILE}" ] && create_backup_metadata "${BACKUP_FILE}" "incremental"
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
  "backup_type": "media",
  "backup_category": "${backup_category}",
  "backup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "backup_size": "${BACKUP_SIZE}",
  "backup_duration_seconds": ${BACKUP_DURATION},
  "files_backed_up": ${FILES_BACKED_UP},
  "files_changed": ${FILES_CHANGED},
  "backup_checksum_sha256": "${BACKUP_CHECKSUM}",
  "compression": "gzip",
  "timestamp": $(date +%s),
  "hostname": "$(hostname)",
  "media_directory": "${MEDIA_DIR}"
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
    log INFO "Running backup cleanup with ${BACKUP_RETENTION_DAYS}-day retention policy..."

    # Clean full backups
    local full_backup_count=$(find "${BACKUP_DIR}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)
    if [ "${full_backup_count}" -gt 0 ]; then
        find "${BACKUP_DIR}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f -mtime "+${BACKUP_RETENTION_DAYS}" -delete -print | while read -r file; do
            log INFO "Deleted old backup: $(basename "${file}")"
            rm -f "${file}.metadata" "${file}.manifest" "${file}.stderr"
        done
    fi

    # Clean incremental backups
    local incr_backup_count=$(find "${BACKUP_DIR}/incremental" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)
    if [ "${incr_backup_count}" -gt 0 ]; then
        find "${BACKUP_DIR}/incremental" -maxdepth 1 -name "backup_*.tar.gz" -type f -mtime "+${BACKUP_RETENTION_DAYS}" -delete -print | while read -r file; do
            log INFO "Deleted old backup: $(basename "${file}")"
            rm -f "${file}.metadata" "${file}.manifest" "${file}.stderr" "${file}.filelist" "${file}.changed"
        done
    fi

    log SUCCESS "Cleanup completed"
}

################################################################################
# S3 UPLOAD
################################################################################

upload_to_s3() {
    if [ "${ENABLE_S3_UPLOAD}" != "true" ]; then
        return 0
    fi

    if [ -z "${BACKUP_FILE}" ] || [ ! -f "${BACKUP_FILE}" ]; then
        log WARN "No backup file to upload to S3"
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

    log INFO "Uploading backup to S3: s3://${AWS_S3_BUCKET}/media-backups/"

    local s3_path="s3://${AWS_S3_BUCKET}/media-backups/${BACKUP_TYPE}/$(basename "${BACKUP_FILE}")"

    if aws s3 cp "${BACKUP_FILE}" "${s3_path}" \
        --region "${AWS_REGION:-us-east-1}" \
        --metadata "checksum=${BACKUP_CHECKSUM},timestamp=${BACKUP_TIMESTAMP},files=${FILES_BACKED_UP}" \
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

    local subject="Media Backup Report - ${BACKUP_DATE}"
    local backup_status=$( [ "${BACKUP_SUCCESS}" = true ] && echo "SUCCESS" || echo "FAILED" )

    local email_body=$(cat <<EOF
Media Backup Report
===================

Date: $(date)
Status: ${backup_status}
Backup Type: ${BACKUP_TYPE}

Details:
--------
Backup File: ${BACKUP_FILE:-N/A}
Backup Size: ${BACKUP_SIZE}
Duration: ${BACKUP_DURATION}s
Files Backed Up: ${FILES_BACKED_UP}
Files Changed: ${FILES_CHANGED}
Checksum (SHA256): ${BACKUP_CHECKSUM}

Retention Policy:
-----------------
Retention Days: ${BACKUP_RETENTION_DAYS}

Backup Location:
----------------
Local: ${BACKUP_DIR}
$([ "${ENABLE_S3_UPLOAD}" = "true" ] && echo "S3 Bucket: s3://${AWS_S3_BUCKET}/media-backups/")

Media Directory:
----------------
${MEDIA_DIR}

Logs:
-----
$(tail -20 "${LOG_FILE}" 2>/dev/null || echo "No logs available")
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
  "full_backup_count": $(find "${BACKUP_DIR}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l),
  "incremental_backup_count": $(find "${BACKUP_DIR}/incremental" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l),
  "total_backup_size": "$(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)"
}
EOF
}

show_status() {
    log INFO "=== Backup Status ==="

    echo ""
    echo "Full Backups:"
    ls -lh "${BACKUP_DIR}/full" 2>/dev/null | grep "backup_" | tail -5 || echo "No full backups found"

    echo ""
    echo "Incremental Backups:"
    ls -lh "${BACKUP_DIR}/incremental" 2>/dev/null | grep "backup_" | tail -5 || echo "No incremental backups found"

    echo ""
    echo "Total Backup Size:"
    du -sh "${BACKUP_DIR}" 2>/dev/null || echo "0"

    echo ""
    echo "Retention Policy: ${BACKUP_RETENTION_DAYS} days"

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
    echo -e "${BLUE}Media Backup Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Initialize
    init_directories
    load_env

    if ! check_prerequisites; then
        exit 1
    fi

    log INFO "Starting backup process: ${BACKUP_TYPE}"
    log INFO "Media Directory: ${MEDIA_DIR}"
    log INFO "Backup Directory: ${BACKUP_DIR}"

    # Run backup based on type
    case "${BACKUP_TYPE}" in
        daily|full)
            create_full_backup
            ;;
        incremental)
            create_incremental_backup
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
            echo "Usage: $0 [daily|full|incremental|cleanup|status]"
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
