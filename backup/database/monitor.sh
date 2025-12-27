#!/bin/bash

################################################################################
# BACKUP MONITORING SCRIPT
#
# Monitor backup health, detect failures, and send alerts
# Verifies backup integrity and checks retention policy
#
# Usage:
#   ./monitor.sh                       Run health check
#   ./monitor.sh alert                 Check and send alerts
#   ./monitor.sh verify                Verify all recent backups
#   ./monitor.sh report                Generate detailed report
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
LOG_DIR="${BACKUP_DIR}/logs"
ALERT_THRESHOLD_HOURS="${ALERT_THRESHOLD_HOURS:-24}"
ALERT_EMAIL="${ALERT_EMAIL:-admin@example.com}"
ENABLE_ALERTS="${ENABLE_ALERTS:-false}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Status tracking
BACKUP_HEALTH="HEALTHY"
ISSUES=()

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level=$1
    shift
    local message="$@"

    case "${level}" in
        INFO)
            echo -e "${BLUE}[INFO]${NC} ${message}"
            ;;
        SUCCESS)
            echo -e "${GREEN}[SUCCESS]${NC} ${message}"
            ;;
        WARN)
            echo -e "${YELLOW}[WARN]${NC} ${message}"
            if [ "${level}" = "WARN" ]; then
                BACKUP_HEALTH="WARNING"
                ISSUES+=("${message}")
            fi
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${message}"
            BACKUP_HEALTH="UNHEALTHY"
            ISSUES+=("${message}")
            ;;
    esac
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
# BACKUP DISCOVERY
################################################################################

get_latest_backup() {
    local category=$1
    if [ -d "${BACKUP_DIR}/${category}" ]; then
        find "${BACKUP_DIR}/${category}" -maxdepth 1 -name "backup_*.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-
    fi
}

get_backup_age_hours() {
    local backup_file=$1
    if [ ! -f "${backup_file}" ]; then
        echo "99999"
        return
    fi

    local backup_time=$(stat -c %Y "${backup_file}")
    local current_time=$(date +%s)
    local age_seconds=$((current_time - backup_time))
    echo $((age_seconds / 3600))
}

format_backup_time() {
    local backup_file=$1
    if [ ! -f "${backup_file}" ]; then
        echo "N/A"
        return
    fi
    stat -c %y "${backup_file}" | cut -d'.' -f1
}

################################################################################
# HEALTH CHECKS
################################################################################

check_backup_freshness() {
    log INFO "Checking backup freshness..."

    local daily_backup=$(get_latest_backup "daily")
    if [ -n "${daily_backup}" ] && [ -f "${daily_backup}" ]; then
        local age=$(get_backup_age_hours "${daily_backup}")
        log SUCCESS "Latest daily backup: $(basename "${daily_backup}") (${age}h old)"

        if [ "${age}" -gt "${ALERT_THRESHOLD_HOURS}" ]; then
            log WARN "Daily backup is older than ${ALERT_THRESHOLD_HOURS} hours"
        fi
    else
        log ERROR "No daily backups found"
    fi

    local weekly_backup=$(get_latest_backup "weekly")
    if [ -n "${weekly_backup}" ] && [ -f "${weekly_backup}" ]; then
        local age=$(get_backup_age_hours "${weekly_backup}")
        log SUCCESS "Latest weekly backup: $(basename "${weekly_backup}") (${age}h old)"
    else
        log WARN "No weekly backups found"
    fi

    local monthly_backup=$(get_latest_backup "monthly")
    if [ -n "${monthly_backup}" ] && [ -f "${monthly_backup}" ]; then
        local age=$(get_backup_age_hours "${monthly_backup}")
        log SUCCESS "Latest monthly backup: $(basename "${monthly_backup}") (${age}h old)"
    else
        log WARN "No monthly backups found"
    fi
}

check_backup_integrity() {
    log INFO "Checking backup integrity..."

    local backup_count=0
    local corrupted_count=0

    for backup_file in "${BACKUP_DIR}"/**/backup_*.gz; do
        if [ ! -f "${backup_file}" ]; then
            continue
        fi

        ((backup_count++))

        if ! gzip -t "${backup_file}" 2>/dev/null; then
            log ERROR "Corrupted backup: $(basename "${backup_file}")"
            ((corrupted_count++))
        fi
    done

    if [ "${corrupted_count}" -eq 0 ]; then
        log SUCCESS "All ${backup_count} backups are intact"
    else
        log ERROR "${corrupted_count}/${backup_count} backups are corrupted"
    fi
}

check_backup_storage() {
    log INFO "Checking backup storage..."

    local total_size=$(du -sh "${BACKUP_DIR}" 2>/dev/null | awk '{print $1}')
    log SUCCESS "Total backup storage: ${total_size}"

    # Check disk space on backup partition
    local backup_disk=$(df "${BACKUP_DIR}" | tail -1)
    local disk_percent=$(echo "${backup_disk}" | awk '{print $5}' | sed 's/%//')
    local disk_available=$(echo "${backup_disk}" | awk '{print $4}')

    log INFO "Disk usage: ${disk_percent}% ($(echo "${backup_disk}" | awk '{print $4}') available)"

    if [ "${disk_percent}" -gt 80 ]; then
        log WARN "Disk usage is above 80%"
    fi

    if [ "${disk_percent}" -gt 95 ]; then
        log ERROR "Disk usage is above 95%, backup space critical"
    fi
}

check_retention_policy() {
    log INFO "Checking retention policy..."

    local daily_count=$(find "${BACKUP_DIR}/daily" -maxdepth 1 -name "backup_*.gz" -type f 2>/dev/null | wc -l)
    local weekly_count=$(find "${BACKUP_DIR}/weekly" -maxdepth 1 -name "backup_*.gz" -type f 2>/dev/null | wc -l)
    local monthly_count=$(find "${BACKUP_DIR}/monthly" -maxdepth 1 -name "backup_*.gz" -type f 2>/dev/null | wc -l)

    log INFO "Daily backups: ${daily_count}"
    log INFO "Weekly backups: ${weekly_count}"
    log INFO "Monthly backups: ${monthly_count}"

    # Check retention configured correctly
    if [ -f "${BACKUP_DIR}/.backup_status" ]; then
        log SUCCESS "Backup status file exists"
    else
        log WARN "Backup status file not found"
    fi
}

check_log_files() {
    log INFO "Checking backup logs..."

    if [ ! -f "${LOG_DIR}/backup_"*.log ]; then
        log WARN "No backup logs found"
        return
    fi

    local latest_log=$(ls -t "${LOG_DIR}"/backup_*.log 2>/dev/null | head -1)
    if [ -n "${latest_log}" ]; then
        local log_age=$(get_backup_age_hours "${latest_log}")
        log INFO "Latest log: $(basename "${latest_log}") (${log_age}h old)"

        # Check for errors in recent logs
        local error_count=$(grep -c "ERROR" "${latest_log}" 2>/dev/null || echo "0")
        if [ "${error_count}" -gt 0 ]; then
            log ERROR "Found ${error_count} errors in latest log"
        else
            log SUCCESS "No errors in latest backup log"
        fi
    fi
}

################################################################################
# VERIFICATION TESTS
################################################################################

verify_all_backups() {
    log INFO "Verifying all backups..."

    local verify_count=0
    local success_count=0
    local fail_count=0

    for backup_file in "${BACKUP_DIR}"/**/backup_*.gz; do
        if [ ! -f "${backup_file}" ]; then
            continue
        fi

        ((verify_count++))

        echo -n "  $(basename "${backup_file}"): "

        if gzip -t "${backup_file}" 2>/dev/null; then
            echo -e "${GREEN}OK${NC}"
            ((success_count++))
        else
            echo -e "${RED}FAILED${NC}"
            ((fail_count++))
        fi

        # Only check last 10 backups to save time
        if [ "${verify_count}" -ge 10 ]; then
            log INFO "Verification limited to last 10 backups"
            break
        fi
    done

    log INFO "Verification complete: ${success_count}/${verify_count} passed"

    if [ "${fail_count}" -gt 0 ]; then
        log ERROR "${fail_count} backup(s) failed verification"
        return 1
    fi

    return 0
}

################################################################################
# REPORTING
################################################################################

generate_health_report() {
    log INFO "=== Database Backup Health Report ==="
    echo ""

    echo "Generated: $(date)"
    echo "Status: ${BACKUP_HEALTH}"
    echo "Backup Directory: ${BACKUP_DIR}"
    echo ""

    # Backup counts
    echo -e "${BLUE}Backup Counts:${NC}"
    echo "  Daily:   $(find "${BACKUP_DIR}/daily" -maxdepth 1 -name "backup_*.gz" -type f 2>/dev/null | wc -l)"
    echo "  Weekly:  $(find "${BACKUP_DIR}/weekly" -maxdepth 1 -name "backup_*.gz" -type f 2>/dev/null | wc -l)"
    echo "  Monthly: $(find "${BACKUP_DIR}/monthly" -maxdepth 1 -name "backup_*.gz" -type f 2>/dev/null | wc -l)"
    echo ""

    # Latest backups
    echo -e "${BLUE}Latest Backups:${NC}"
    local daily_backup=$(get_latest_backup "daily")
    if [ -n "${daily_backup}" ] && [ -f "${daily_backup}" ]; then
        echo "  Daily:   $(basename "${daily_backup}") - $(format_backup_time "${daily_backup}")"
    else
        echo "  Daily:   None"
    fi

    local weekly_backup=$(get_latest_backup "weekly")
    if [ -n "${weekly_backup}" ] && [ -f "${weekly_backup}" ]; then
        echo "  Weekly:  $(basename "${weekly_backup}") - $(format_backup_time "${weekly_backup}")"
    else
        echo "  Weekly:  None"
    fi

    local monthly_backup=$(get_latest_backup "monthly")
    if [ -n "${monthly_backup}" ] && [ -f "${monthly_backup}" ]; then
        echo "  Monthly: $(basename "${monthly_backup}") - $(format_backup_time "${monthly_backup}")"
    else
        echo "  Monthly: None"
    fi
    echo ""

    # Storage info
    echo -e "${BLUE}Storage Information:${NC}"
    echo "  Total Size:  $(du -sh "${BACKUP_DIR}" 2>/dev/null | awk '{print $1}')"
    local backup_disk=$(df "${BACKUP_DIR}" | tail -1)
    echo "  Disk Usage:  $(echo "${backup_disk}" | awk '{print $5}')"
    echo "  Available:   $(echo "${backup_disk}" | awk '{print $4}')"
    echo ""

    # Issues
    if [ ${#ISSUES[@]} -eq 0 ]; then
        echo -e "${GREEN}Issues: None${NC}"
    else
        echo -e "${YELLOW}Issues Found:${NC}"
        for issue in "${ISSUES[@]}"; do
            echo "  - ${issue}"
        done
    fi

    echo ""
}

send_alert() {
    if [ "${ENABLE_ALERTS}" != "true" ]; then
        return 0
    fi

    if [ -z "${ALERT_EMAIL}" ]; then
        return 0
    fi

    local subject="Backup Health Alert: ${BACKUP_HEALTH}"
    local report_file="/tmp/backup_health_report_$$.txt"

    generate_health_report > "${report_file}"

    if command -v mail &> /dev/null; then
        cat "${report_file}" | mail -s "${subject}" "${ALERT_EMAIL}"
        log SUCCESS "Alert email sent to ${ALERT_EMAIL}"
    fi

    rm -f "${report_file}"
}

################################################################################
# MAIN EXECUTION
################################################################################

show_usage() {
    cat <<EOF
Backup Monitoring Script

Usage:
  ./monitor.sh                Run health check
  ./monitor.sh alert          Run health check and send alerts
  ./monitor.sh verify         Verify all recent backups
  ./monitor.sh report         Generate detailed report

Environment Variables:
  ALERT_THRESHOLD_HOURS      Hours before alerting on old backups (default: 24)
  ALERT_EMAIL                Email for alerts (default: admin@example.com)
  ENABLE_ALERTS              Enable email alerts (default: false)

Examples:
  # Run quick health check
  ./monitor.sh

  # Run health check and send alerts
  ./monitor.sh alert

  # Verify all backups
  ./monitor.sh verify

  # Generate detailed report
  ./monitor.sh report
EOF
}

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Backup Monitoring${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    load_env

    # Initialize log directory
    mkdir -p "${LOG_DIR}"

    local action="${1:-health}"

    case "${action}" in
        health|"")
            check_backup_freshness
            echo ""
            check_backup_integrity
            echo ""
            check_backup_storage
            echo ""
            check_retention_policy
            echo ""
            check_log_files
            echo ""
            generate_health_report
            exit 0
            ;;
        alert)
            check_backup_freshness > /dev/null
            check_backup_integrity > /dev/null
            check_backup_storage > /dev/null
            check_retention_policy > /dev/null
            check_log_files > /dev/null

            generate_health_report
            echo ""

            if [ "${BACKUP_HEALTH}" != "HEALTHY" ]; then
                send_alert
            fi
            exit 0
            ;;
        verify)
            verify_all_backups
            exit $?
            ;;
        report)
            check_backup_freshness
            echo ""
            check_backup_integrity
            echo ""
            check_backup_storage
            echo ""
            check_retention_policy
            echo ""
            check_log_files
            echo ""
            generate_health_report
            exit 0
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
