#!/bin/bash

################################################################################
# MEDIA BACKUP MONITORING SCRIPT
#
# Monitors backup health and sends alerts for failures
# Checks backup frequency, file integrity, disk space usage
#
# Usage:
#   ./monitor.sh                    # Check backup status
#   ./monitor.sh --health           # Detailed health check
#   ./monitor.sh --cleanup-test     # Simulate cleanup
#   ./monitor.sh --disk-usage       # Show disk usage
#
# Environment Variables:
#   BACKUP_DIR              Base backup directory
#   NOTIFICATION_EMAIL      Email for alerts
#   BACKUP_RETENTION_DAYS   Retention policy days
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups/media}"
LOG_DIR="${BACKUP_DIR}/logs"
NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-admin@example.com}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

# Health check thresholds
MAX_HOURS_WITHOUT_BACKUP=48
MIN_BACKUP_SIZE=1000000  # 1MB in bytes
MAX_DISK_USAGE_PERCENT=80

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global health status
HEALTH_STATUS="OK"
HEALTH_ISSUES=()

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    mkdir -p "${LOG_DIR}"
    echo "[${timestamp}] [${level}] ${message}" >> "${LOG_DIR}/monitor.log"

    case "${level}" in
        INFO)
            echo -e "${BLUE}[INFO]${NC} ${message}"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} ${message}"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} ${message}"
            HEALTH_STATUS="WARNING"
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${message}"
            HEALTH_STATUS="ERROR"
            ;;
    esac
}

add_issue() {
    HEALTH_ISSUES+=("$@")
}

load_env() {
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        set +u
        # shellcheck disable=SC1090
        source "${PROJECT_ROOT}/.env"
        set -u
    fi
}

################################################################################
# BACKUP FREQUENCY CHECK
################################################################################

check_backup_frequency() {
    log INFO "Checking backup frequency..."

    if [ ! -d "${BACKUP_DIR}/full" ]; then
        log ERROR "No full backups directory"
        add_issue "No full backups directory found"
        return 1
    fi

    local latest_backup=$(find "${BACKUP_DIR}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f -printf '%T@ %p\n' | sort -rn | head -1 | cut -d' ' -f2-)

    if [ -z "${latest_backup}" ]; then
        log ERROR "No backups found"
        add_issue "No backups found in full backup directory"
        return 1
    fi

    local backup_time=$(stat -c %Y "${latest_backup}")
    local current_time=$(date +%s)
    local hours_ago=$(( (current_time - backup_time) / 3600 ))

    log INFO "Latest backup: $(basename "${latest_backup}")"
    log INFO "Backup age: ${hours_ago} hours"

    if [ "${hours_ago}" -gt "${MAX_HOURS_WITHOUT_BACKUP}" ]; then
        log WARN "Last backup is ${hours_ago} hours old (max: ${MAX_HOURS_WITHOUT_BACKUP} hours)"
        add_issue "Last backup is ${hours_ago} hours old"
        return 1
    else
        log SUCCESS "Backup frequency is acceptable"
        return 0
    fi
}

################################################################################
# BACKUP INTEGRITY CHECK
################################################################################

check_backup_integrity() {
    log INFO "Checking backup integrity..."

    local check_count=0
    local failed_count=0

    find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.tar.gz" -type f | while read -r backup_file; do
        ((check_count++))

        # Skip if more than retention period
        if [ $(find "${backup_file}" -mtime +${BACKUP_RETENTION_DAYS} 2>/dev/null | wc -l) -gt 0 ]; then
            continue
        fi

        log INFO "Verifying: $(basename "${backup_file}")"

        # Check gzip integrity
        if ! gzip -t "${backup_file}" 2>/dev/null; then
            log WARN "Gzip integrity check failed: $(basename "${backup_file}")"
            ((failed_count++))
            add_issue "Backup corruption detected: $(basename "${backup_file}")"
            continue
        fi

        # Check file size
        local file_size=$(stat -c%s "${backup_file}")
        if [ "${file_size}" -lt "${MIN_BACKUP_SIZE}" ]; then
            log WARN "Backup size is suspiciously small: ${file_size} bytes"
            add_issue "Backup size is suspiciously small: $(basename "${backup_file}")"
            continue
        fi

        # Check checksum if metadata exists
        local metadata_file="${backup_file}.metadata"
        if [ -f "${metadata_file}" ]; then
            local expected_checksum=$(grep -o '"backup_checksum_sha256": "[^"]*' "${metadata_file}" | cut -d'"' -f4)
            local actual_checksum=$(sha256sum "${backup_file}" | awk '{print $1}')

            if [ "${expected_checksum}" != "${actual_checksum}" ]; then
                log WARN "Checksum mismatch: $(basename "${backup_file}")"
                ((failed_count++))
                add_issue "Checksum mismatch detected: $(basename "${backup_file}")"
            fi
        fi
    done

    log INFO "Integrity check complete: checked ${check_count} backups, ${failed_count} failed"

    if [ "${failed_count}" -gt 0 ]; then
        return 1
    else
        log SUCCESS "All backups passed integrity check"
        return 0
    fi
}

################################################################################
# DISK USAGE CHECK
################################################################################

check_disk_usage() {
    log INFO "Checking disk usage..."

    local backup_size=$(du -sb "${BACKUP_DIR}" 2>/dev/null | cut -f1)
    local backup_size_mb=$((backup_size / 1048576))
    local backup_size_gb=$((backup_size / 1073741824))

    log INFO "Backup directory size: ${backup_size_mb}MB (${backup_size_gb}GB)"

    # Check partition usage
    local partition=$(df "${BACKUP_DIR}" | tail -1 | awk '{print $1}')
    local usage_percent=$(df "${BACKUP_DIR}" | tail -1 | awk '{print $5}' | sed 's/%//')

    log INFO "Partition: ${partition}"
    log INFO "Disk usage: ${usage_percent}%"

    if [ "${usage_percent}" -gt "${MAX_DISK_USAGE_PERCENT}" ]; then
        log WARN "Disk usage is high: ${usage_percent}% (max: ${MAX_DISK_USAGE_PERCENT}%)"
        add_issue "Disk usage is high: ${usage_percent}%"
        return 1
    else
        log SUCCESS "Disk usage is acceptable"
        return 0
    fi
}

################################################################################
# BACKUP METADATA CHECK
################################################################################

check_backup_metadata() {
    log INFO "Checking backup metadata..."

    if [ ! -f "${BACKUP_DIR}/.backup_status" ]; then
        log WARN "No backup status file found"
        return 1
    fi

    log INFO "Backup status:"
    cat "${BACKUP_DIR}/.backup_status" | grep -o '"[^"]*": [^,}]*' | while read -r line; do
        log INFO "  ${line}"
    done

    # Check if last backup was successful
    local last_success=$(grep -o '"last_backup_success": [^,}]*' "${BACKUP_DIR}/.backup_status" | cut -d':' -f2 | tr -d ' ')

    if [ "${last_success}" != "true" ]; then
        log WARN "Last backup was not successful"
        add_issue "Last backup was not successful"
        return 1
    fi

    return 0
}

################################################################################
# RETENTION POLICY CHECK
################################################################################

check_retention_policy() {
    log INFO "Checking retention policy..."

    local old_backup_count=$(find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.tar.gz" -type f -mtime +${BACKUP_RETENTION_DAYS} | wc -l)

    if [ "${old_backup_count}" -gt 0 ]; then
        log WARN "Found ${old_backup_count} backups older than ${BACKUP_RETENTION_DAYS} days"
        add_issue "Retention policy not enforced - found ${old_backup_count} old backups"

        log INFO "Listing old backups:"
        find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.tar.gz" -type f -mtime +${BACKUP_RETENTION_DAYS} -ls

        return 1
    else
        log SUCCESS "Retention policy is enforced"
        return 0
    fi
}

################################################################################
# HEALTH REPORT
################################################################################

print_health_report() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Backup Health Report${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    echo "Status: ${HEALTH_STATUS}"
    echo "Timestamp: $(date)"
    echo "Backup Directory: ${BACKUP_DIR}"
    echo ""

    if [ ${#HEALTH_ISSUES[@]} -gt 0 ]; then
        echo "Issues Found:"
        for issue in "${HEALTH_ISSUES[@]}"; do
            echo "  - ${issue}"
        done
        echo ""
    fi

    # Backup count
    echo "Backup Count:"
    echo "  Full: $(find "${BACKUP_DIR}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)"
    echo "  Incremental: $(find "${BACKUP_DIR}/incremental" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)"
    echo ""

    # Storage usage
    echo "Storage Usage:"
    echo "  Total Size: $(du -sh "${BACKUP_DIR}" 2>/dev/null | cut -f1)"
    echo "  Disk Usage: $(df "${BACKUP_DIR}" | tail -1 | awk '{print $5}')"
    echo ""
}

send_health_alert() {
    if [ "${HEALTH_STATUS}" = "OK" ]; then
        return 0
    fi

    if [ -z "${NOTIFICATION_EMAIL}" ] || [ "${NOTIFICATION_EMAIL}" = "admin@example.com" ]; then
        log WARN "Notification email not configured"
        return 0
    fi

    log INFO "Would send health alert to ${NOTIFICATION_EMAIL}"
}

################################################################################
# CLEANUP TEST
################################################################################

simulate_cleanup() {
    log INFO "Simulating cleanup operation..."

    local old_backups_count=$(find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.tar.gz" -type f -mtime +${BACKUP_RETENTION_DAYS} | wc -l)

    if [ "${old_backups_count}" -eq 0 ]; then
        log INFO "No backups to clean - retention policy enforced"
        return 0
    fi

    echo ""
    echo "Backups that would be deleted:"

    find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.tar.gz" -type f -mtime +${BACKUP_RETENTION_DAYS} | while read -r backup_file; do
        local size=$(du -h "${backup_file}" | cut -f1)
        echo "  $(basename "${backup_file}") - ${size}"
    done

    echo ""
    log INFO "Total backups would be deleted: ${old_backups_count}"
}

################################################################################
# DISK USAGE DETAILED
################################################################################

show_disk_usage() {
    log INFO "Detailed disk usage analysis:"
    echo ""

    echo "By backup type:"
    du -sh "${BACKUP_DIR}"/* 2>/dev/null | while read -r size dir; do
        echo "  $(basename "${dir}"): ${size}"
    done
    echo ""

    echo "Largest backups:"
    find "${BACKUP_DIR}" -maxdepth 2 -name "backup_*.tar.gz" -type f -printf '%s %p\n' | sort -rn | head -10 | while read -r size file; do
        local size_mb=$((size / 1048576))
        echo "  $(basename "${file}"): ${size_mb}MB"
    done
    echo ""

    echo "Partition info:"
    df -h "${BACKUP_DIR}"
    echo ""

    echo "Directory structure:"
    du -sh "${BACKUP_DIR}"/*/. 2>/dev/null || echo "No subdirectories"
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Media Backup Monitor${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    mkdir -p "${LOG_DIR}"
    load_env

    local command="${1:-}"

    case "${command}" in
        --health)
            log INFO "Running full health check..."
            echo ""
            check_backup_frequency || true
            check_backup_integrity || true
            check_disk_usage || true
            check_backup_metadata || true
            check_retention_policy || true
            print_health_report
            send_health_alert
            ;;
        --cleanup-test)
            simulate_cleanup
            ;;
        --disk-usage)
            show_disk_usage
            ;;
        *)
            log INFO "Running backup status check..."
            echo ""
            check_backup_frequency || true
            check_disk_usage || true
            print_health_report
            ;;
    esac

    echo ""
    exit 0
}

# Run main function
main "$@"
