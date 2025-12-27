#!/bin/bash

################################################################################
# MEDIA FILES RESTORE SCRIPT
#
# Restore media files from backup archives
# Supports verification, integrity checking, and incremental restoration
#
# Usage:
#   ./restore.sh <backup_file>           # Restore from local backup
#   ./restore.sh --list                  # List available backups
#   ./restore.sh --list-s3               # List backups on S3
#   ./restore.sh --s3 <backup_key>       # Restore from S3
#   ./restore.sh --verify <backup_file>  # Verify backup integrity
#   ./restore.sh --test <backup_file>    # Test restore (dry-run)
#
# Environment Variables:
#   BACKUP_DIR              Base backup directory (default: ./backups)
#   MEDIA_DIR               Media directory to restore to (default: ../../../backend/media)
#   AWS_S3_BUCKET           S3 bucket name
#   AWS_REGION              AWS region (default: us-east-1)
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups/media}"
MEDIA_DIR="${MEDIA_DIR:-${PROJECT_ROOT}/backend/media}"

# Log file
LOG_DIR="${BACKUP_DIR}/logs"
LOG_FILE="${LOG_DIR}/restore_$(date +%Y%m%d).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
RESTORE_SUCCESS=true
RESTORE_FILE=""
FILES_RESTORED=0

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    mkdir -p "${LOG_DIR}"
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
            RESTORE_SUCCESS=false
            ;;
    esac
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

    if [ ${#missing_tools[@]} -gt 0 ]; then
        log ERROR "Missing required tools: ${missing_tools[*]}"
        return 1
    fi

    log INFO "All required tools found"
    return 0
}

################################################################################
# BACKUP LISTING AND DISCOVERY
################################################################################

list_local_backups() {
    log INFO "Available local backups:"
    echo ""

    if [ ! -d "${BACKUP_DIR}" ]; then
        echo "No backup directory found"
        return 1
    fi

    local backup_count=0

    # List full backups
    if [ -d "${BACKUP_DIR}/full" ]; then
        echo "FULL BACKUPS:"
        find "${BACKUP_DIR}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | while read -r backup_file; do
            local size=$(ls -lh "${backup_file}" | awk '{print $5}')
            local date=$(stat -c %y "${backup_file}" | cut -d' ' -f1,2)
            local checksum=""
            if [ -f "${backup_file}.metadata" ]; then
                checksum=$(grep -o '"backup_checksum_sha256": "[^"]*' "${backup_file}.metadata" | cut -d'"' -f4 | cut -c1-8)
            fi
            printf "  %-50s %10s  %19s  %s\n" "$(basename "${backup_file}")" "${size}" "${date}" "${checksum}..."
            ((backup_count++))
        done
        echo ""
    fi

    # List incremental backups
    if [ -d "${BACKUP_DIR}/incremental" ]; then
        echo "INCREMENTAL BACKUPS:"
        find "${BACKUP_DIR}/incremental" -maxdepth 1 -name "backup_*.tar.gz" -type f | while read -r backup_file; do
            local size=$(ls -lh "${backup_file}" | awk '{print $5}')
            local date=$(stat -c %y "${backup_file}" | cut -d' ' -f1,2)
            local checksum=""
            if [ -f "${backup_file}.metadata" ]; then
                checksum=$(grep -o '"backup_checksum_sha256": "[^"]*' "${backup_file}.metadata" | cut -d'"' -f4 | cut -c1-8)
            fi
            printf "  %-50s %10s  %19s  %s\n" "$(basename "${backup_file}")" "${size}" "${date}" "${checksum}..."
            ((backup_count++))
        done
        echo ""
    fi

    if [ "${backup_count}" -eq 0 ]; then
        echo "No backups found"
        return 1
    fi

    echo "Total: ${backup_count} backup(s)"
    return 0
}

list_s3_backups() {
    if [ -z "${AWS_S3_BUCKET:-}" ]; then
        log ERROR "AWS_S3_BUCKET not set"
        return 1
    fi

    if ! command -v aws &> /dev/null; then
        log ERROR "AWS CLI not found"
        return 1
    fi

    log INFO "Available backups on S3:"
    echo ""

    aws s3 ls "s3://${AWS_S3_BUCKET}/media-backups/" --recursive \
        --region "${AWS_REGION:-us-east-1}" | \
        grep -E "\.tar\.gz$|\.metadata$" | \
        awk '{print $1, $2, $3, $4}' | \
        column -t

    return 0
}

################################################################################
# RESTORE FUNCTIONS
################################################################################

verify_backup_file() {
    local backup_file=$1

    if [ ! -f "${backup_file}" ]; then
        log ERROR "Backup file not found: ${backup_file}"
        return 1
    fi

    log INFO "Verifying backup file: ${backup_file}"

    # Check gzip integrity
    if ! gzip -t "${backup_file}" 2>/dev/null; then
        log ERROR "Gzip integrity check failed"
        return 1
    fi

    # Check checksum if metadata exists
    local metadata_file="${backup_file}.metadata"
    if [ -f "${metadata_file}" ]; then
        local expected_checksum=$(grep -o '"backup_checksum_sha256": "[^"]*' "${metadata_file}" | cut -d'"' -f4)
        local actual_checksum=$(sha256sum "${backup_file}" | awk '{print $1}')

        if [ "${expected_checksum}" != "${actual_checksum}" ]; then
            log ERROR "Checksum mismatch: expected ${expected_checksum}, got ${actual_checksum}"
            return 1
        fi

        log SUCCESS "Checksum verified: ${expected_checksum}"
    fi

    log SUCCESS "Backup verification passed"
    return 0
}

download_from_s3() {
    local s3_key=$1
    local local_file="${BACKUP_DIR}/temp_$(basename "${s3_key}")"

    if [ -z "${AWS_S3_BUCKET:-}" ]; then
        log ERROR "AWS_S3_BUCKET not set"
        return 1
    fi

    if ! command -v aws &> /dev/null; then
        log ERROR "AWS CLI not found"
        return 1
    fi

    log INFO "Downloading backup from S3: ${s3_key}"

    if aws s3 cp "s3://${AWS_S3_BUCKET}/${s3_key}" "${local_file}" \
        --region "${AWS_REGION:-us-east-1}"; then

        RESTORE_FILE="${local_file}"
        log SUCCESS "Downloaded: ${local_file}"
        return 0
    else
        log ERROR "Failed to download from S3"
        return 1
    fi
}

restore_from_backup() {
    local backup_file=$1
    local test_mode=${2:-false}

    if [ ! -f "${backup_file}" ]; then
        log ERROR "Backup file not found: ${backup_file}"
        return 1
    fi

    log INFO "Starting restore from: $(basename "${backup_file}")"

    # Create media directory if it doesn't exist
    mkdir -p "${MEDIA_DIR}"

    # Get file count from backup
    local file_count=$(tar -tzf "${backup_file}" | grep -v "/$" | wc -l)
    log INFO "Backup contains ${file_count} files"

    if [ "${test_mode}" = "true" ]; then
        log INFO "Running restore in TEST mode (dry-run)"
        # List contents without extracting
        if tar -tzf "${backup_file}" | head -20; then
            log SUCCESS "Test restore passed - backup is readable"
            FILES_RESTORED="${file_count}"
            return 0
        else
            log ERROR "Test restore failed - cannot read backup"
            return 1
        fi
    fi

    # Backup current media directory
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local media_backup="${MEDIA_DIR}_backup_${backup_timestamp}"

    if [ -d "${MEDIA_DIR}" ] && [ -n "$(find "${MEDIA_DIR}" -type f 2>/dev/null)" ]; then
        log INFO "Creating backup of current media directory: ${media_backup}"
        cp -r "${MEDIA_DIR}" "${media_backup}"
    fi

    # Extract backup
    if tar -xzf "${backup_file}" -C "${MEDIA_DIR%/*}" 2>"${backup_file}.restore_stderr"; then
        FILES_RESTORED="${file_count}"
        log SUCCESS "Restore completed: ${FILES_RESTORED} files extracted"
        return 0
    else
        log ERROR "Restore failed"
        if [ -f "${backup_file}.restore_stderr" ]; then
            log ERROR "$(cat "${backup_file}.restore_stderr")"
        fi

        # Restore from backup if extraction failed
        if [ -d "${media_backup}" ]; then
            log INFO "Restoring from backup due to failure"
            rm -rf "${MEDIA_DIR}"
            mv "${media_backup}" "${MEDIA_DIR}"
        fi

        return 1
    fi
}

################################################################################
# SAMPLE FILE VERIFICATION
################################################################################

test_sample_files() {
    log INFO "Testing sample files from restore..."

    if [ ! -d "${MEDIA_DIR}" ]; then
        log ERROR "Media directory not found after restore"
        return 1
    fi

    # Find sample files
    local sample_files=$(find "${MEDIA_DIR}" -type f | head -5)

    if [ -z "${sample_files}" ]; then
        log WARN "No files to test"
        return 0
    fi

    local files_ok=0
    local files_total=0

    echo "${sample_files}" | while read -r file; do
        if [ -f "${file}" ]; then
            local size=$(stat -c%s "${file}")
            if [ "${size}" -gt 0 ]; then
                log INFO "Sample file OK: ${file} (${size} bytes)"
                ((files_ok++))
            else
                log WARN "Sample file is empty: ${file}"
            fi
        fi
        ((files_total++))
    done

    log INFO "Sample verification: ${files_ok}/${files_total} files OK"
    return 0
}

################################################################################
# RESTORE METADATA
################################################################################

create_restore_metadata() {
    local restore_file=$1
    local metadata_file="${restore_file}.restore_metadata"

    cat > "${metadata_file}" <<EOF
{
  "restore_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "source_backup": "${RESTORE_FILE}",
  "target_directory": "${MEDIA_DIR}",
  "files_restored": ${FILES_RESTORED},
  "restore_success": ${RESTORE_SUCCESS},
  "hostname": "$(hostname)",
  "timestamp": $(date +%s)
}
EOF

    log INFO "Restore metadata created: ${metadata_file}"
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Media Restore Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Initialize
    mkdir -p "${LOG_DIR}"
    load_env

    if ! check_prerequisites; then
        exit 1
    fi

    local command="${1:-}"

    # Handle different commands
    case "${command}" in
        --list)
            list_local_backups
            exit $?
            ;;
        --list-s3)
            list_s3_backups
            exit $?
            ;;
        --verify)
            if [ -z "${2:-}" ]; then
                log ERROR "Please specify backup file to verify"
                exit 1
            fi
            verify_backup_file "$2"
            exit $?
            ;;
        --test)
            if [ -z "${2:-}" ]; then
                log ERROR "Please specify backup file to test"
                exit 1
            fi
            restore_from_backup "$2" true
            exit $?
            ;;
        --s3)
            if [ -z "${2:-}" ]; then
                log ERROR "Please specify S3 backup key"
                exit 1
            fi
            download_from_s3 "$2" || exit 1
            verify_backup_file "${RESTORE_FILE}" || exit 1
            restore_from_backup "${RESTORE_FILE}" || exit 1
            ;;
        *)
            if [ -z "${command}" ]; then
                log ERROR "Please specify backup file or command"
                echo ""
                echo "Usage:"
                echo "  $0 <backup_file>           # Restore from backup"
                echo "  $0 --list                  # List local backups"
                echo "  $0 --list-s3               # List S3 backups"
                echo "  $0 --s3 <backup_key>       # Restore from S3"
                echo "  $0 --verify <backup_file>  # Verify backup"
                echo "  $0 --test <backup_file>    # Test restore (dry-run)"
                exit 1
            fi

            RESTORE_FILE="${command}"

            # Verify backup
            if ! verify_backup_file "${RESTORE_FILE}"; then
                exit 1
            fi

            # Restore from backup
            if ! restore_from_backup "${RESTORE_FILE}"; then
                exit 1
            fi

            # Test sample files
            if ! test_sample_files; then
                RESTORE_SUCCESS=false
            fi
            ;;
    esac

    # Create restore metadata
    if [ -n "${RESTORE_FILE}" ]; then
        create_restore_metadata "${RESTORE_FILE}"
    fi

    echo ""
    if [ "${RESTORE_SUCCESS}" = true ]; then
        log SUCCESS "Restore process completed successfully"
        exit 0
    else
        log ERROR "Restore process completed with errors"
        exit 1
    fi
}

# Run main function
main "$@"
