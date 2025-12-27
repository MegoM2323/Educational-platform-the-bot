#!/bin/bash

################################################################################
# CRON JOB SETUP SCRIPT
#
# Configure automatic database backups using cron jobs
# Creates scheduled tasks for daily, weekly, and monthly backups
#
# Usage:
#   ./setup-cron.sh install        Install cron jobs
#   ./setup-cron.sh uninstall      Remove cron jobs
#   ./setup-cron.sh status         Show cron job status
#   ./setup-cron.sh list           List installed cron jobs
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_SCRIPT="${SCRIPT_DIR}/backup.sh"
CRON_IDENTIFIER="THE_BOT_DATABASE_BACKUP"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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
            ;;
        ERROR)
            echo -e "${RED}[ERROR]${NC} ${message}"
            ;;
    esac
}

check_prerequisites() {
    if [ ! -f "${BACKUP_SCRIPT}" ]; then
        log ERROR "Backup script not found: ${BACKUP_SCRIPT}"
        return 1
    fi

    if ! command -v crontab &> /dev/null; then
        log ERROR "crontab command not found"
        return 1
    fi

    chmod +x "${BACKUP_SCRIPT}"
    log INFO "Backup script executable"

    return 0
}

################################################################################
# CRON JOB FUNCTIONS
################################################################################

install_cron_jobs() {
    log INFO "Installing cron jobs for database backups..."

    # Get current crontab or create empty
    local current_cron=""
    if crontab -l >/dev/null 2>&1; then
        current_cron=$(crontab -l 2>/dev/null || echo "")
    fi

    # Check if already installed
    if echo "${current_cron}" | grep -q "${CRON_IDENTIFIER}"; then
        log WARN "Cron jobs already installed"
        return 0
    fi

    # Create new crontab with existing entries + new backup jobs
    local new_cron=$(cat <<'EOF'
# ================================================================
# THE_BOT PLATFORM - DATABASE BACKUP JOBS
# ================================================================

# Daily backup at 1 AM
0 1 * * * cd /home/mego/Python\ Projects/THE_BOT_platform && /home/mego/Python\ Projects/THE_BOT_platform/backup/database/backup.sh daily >> /home/mego/Python\ Projects/THE_BOT_platform/backups/logs/cron.log 2>&1 # THE_BOT_DATABASE_BACKUP

# Weekly backup every Sunday at 3 AM
0 3 * * 0 cd /home/mego/Python\ Projects/THE_BOT_platform && /home/mego/Python\ Projects/THE_BOT_platform/backup/database/backup.sh weekly >> /home/mego/Python\ Projects/THE_BOT_platform/backups/logs/cron.log 2>&1 # THE_BOT_DATABASE_BACKUP

# Monthly backup on 1st of month at 5 AM
0 5 1 * * cd /home/mego/Python\ Projects/THE_BOT_platform && /home/mego/Python\ Projects/THE_BOT_platform/backup/database/backup.sh monthly >> /home/mego/Python\ Projects/THE_BOT_platform/backups/logs/cron.log 2>&1 # THE_BOT_DATABASE_BACKUP

# Weekly cleanup and retention policy check (Saturday at 2 AM)
0 2 * * 6 cd /home/mego/Python\ Projects/THE_BOT_platform && /home/mego/Python\ Projects/THE_BOT_platform/backup/database/backup.sh cleanup >> /home/mego/Python\ Projects/THE_BOT_platform/backups/logs/cron.log 2>&1 # THE_BOT_DATABASE_BACKUP

# Daily backup health check (runs before daily backup)
30 0 * * * cd /home/mego/Python\ Projects/THE_BOT_platform && /home/mego/Python\ Projects/THE_BOT_platform/backup/database/backup.sh status >> /home/mego/Python\ Projects/THE_BOT_platform/backups/logs/cron.log 2>&1 # THE_BOT_DATABASE_BACKUP

EOF
)

    # Add existing cron entries (exclude our old jobs if any)
    if [ -n "${current_cron}" ]; then
        new_cron="${current_cron}"$'\n'"${new_cron}"
    fi

    # Install new crontab
    if echo "${new_cron}" | crontab - 2>/dev/null; then
        log SUCCESS "Cron jobs installed successfully"
        log INFO "Cron jobs:"
        log INFO "  - Daily backup: 1:00 AM"
        log INFO "  - Weekly backup: 3:00 AM (Sunday)"
        log INFO "  - Monthly backup: 5:00 AM (1st of month)"
        log INFO "  - Weekly cleanup: 2:00 AM (Saturday)"
        log INFO "  - Health check: 12:30 AM (Daily)"
        return 0
    else
        log ERROR "Failed to install cron jobs"
        return 1
    fi
}

uninstall_cron_jobs() {
    log INFO "Uninstalling cron jobs for database backups..."

    local current_cron=""
    if crontab -l >/dev/null 2>&1; then
        current_cron=$(crontab -l 2>/dev/null || echo "")
    fi

    if ! echo "${current_cron}" | grep -q "${CRON_IDENTIFIER}"; then
        log WARN "Cron jobs not found, nothing to uninstall"
        return 0
    fi

    # Remove backup-related entries
    local new_cron=$(echo "${current_cron}" | grep -v "${CRON_IDENTIFIER}" || echo "")

    # Remove the backup jobs section if it's empty
    if [ -z "${new_cron}" ]; then
        crontab -r 2>/dev/null || true
        log SUCCESS "All cron jobs removed"
    else
        echo "${new_cron}" | crontab -
        log SUCCESS "Cron jobs removed"
    fi

    return 0
}

list_cron_jobs() {
    if ! crontab -l >/dev/null 2>&1; then
        log INFO "No crontab installed for current user"
        return 0
    fi

    local backup_jobs=$(crontab -l 2>/dev/null | grep "${CRON_IDENTIFIER}" || echo "")

    if [ -z "${backup_jobs}" ]; then
        log INFO "No backup cron jobs found"
        return 0
    fi

    log INFO "Installed backup cron jobs:"
    echo ""
    echo "${backup_jobs}" | while read -r line; do
        # Skip comments and empty lines
        if [[ "${line}" =~ ^# ]] || [ -z "${line}" ]; then
            continue
        fi

        # Extract time and command
        local time=$(echo "${line}" | awk '{print $1, $2, $3, $4, $5}')
        local command=$(echo "${line}" | awk '{for(i=7;i<=NF;i++) if ($i !~ /^#/) printf "%s ", $i; else break}')
        local type=$(echo "${command}" | grep -oE 'backup\.sh \w+' | awk '{print $2}' || echo "unknown")

        # Convert cron time to readable format
        local readable_time=$(convert_cron_time "${time}")

        echo "  [${type}] ${readable_time}"
        echo "      ${command}"
        echo ""
    done

    return 0
}

convert_cron_time() {
    local minute=$1
    local hour=$2
    local day=$3
    local month=$4
    local weekday=$5

    local readable=""

    # Day of week
    case "${weekday}" in
        0) readable="Sunday" ;;
        1) readable="Monday" ;;
        2) readable="Tuesday" ;;
        3) readable="Wednesday" ;;
        4) readable="Thursday" ;;
        5) readable="Friday" ;;
        6) readable="Saturday" ;;
        *) readable="every day" ;;
    esac

    # Day of month
    if [ "${day}" != "*" ]; then
        readable="on day ${day} of every month"
    fi

    echo "${readable} at ${hour}:$(printf '%02d' ${minute})"
}

show_cron_status() {
    log INFO "=== Database Backup Cron Status ==="
    echo ""

    if ! crontab -l >/dev/null 2>&1; then
        log INFO "No crontab installed"
        return 0
    fi

    local backup_jobs=$(crontab -l 2>/dev/null | grep -c "${CRON_IDENTIFIER}" || echo "0")

    if [ "${backup_jobs}" -eq 0 ]; then
        log INFO "No backup cron jobs installed"
        echo ""
        log INFO "Run './setup-cron.sh install' to enable automatic backups"
    else
        log SUCCESS "Backup cron jobs are installed: ${backup_jobs} job(s)"
        echo ""
        list_cron_jobs
    fi

    # Show last backup logs
    local log_file="/home/mego/Python Projects/THE_BOT_platform/backups/logs/cron.log"
    if [ -f "${log_file}" ]; then
        echo ""
        echo -e "${BLUE}Last backup logs:${NC}"
        tail -20 "${log_file}" | while read -r line; do
            if [[ "${line}" =~ "ERROR" ]]; then
                echo -e "${RED}${line}${NC}"
            elif [[ "${line}" =~ "SUCCESS" ]]; then
                echo -e "${GREEN}${line}${NC}"
            else
                echo "${line}"
            fi
        done
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

show_usage() {
    cat <<EOF
Cron Job Setup Script

Usage:
  ./setup-cron.sh install      Install automatic backup cron jobs
  ./setup-cron.sh uninstall    Remove backup cron jobs
  ./setup-cron.sh status       Show cron job status and logs
  ./setup-cron.sh list         List installed cron jobs

Examples:
  # Install automated backups
  ./setup-cron.sh install

  # Check status
  ./setup-cron.sh status

  # Remove automated backups
  ./setup-cron.sh uninstall

Cron Schedule:
  - Daily backup:      1:00 AM (every day)
  - Weekly backup:     3:00 AM (Sundays)
  - Monthly backup:    5:00 AM (1st of month)
  - Weekly cleanup:    2:00 AM (Saturdays)
  - Health check:      12:30 AM (every day)

Logs:
  All backup logs are written to: ${PROJECT_ROOT}/backups/logs/cron.log
EOF
}

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Cron Job Setup${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    if ! check_prerequisites; then
        exit 1
    fi

    local action="${1:-}"

    case "${action}" in
        install)
            install_cron_jobs
            exit $?
            ;;
        uninstall)
            uninstall_cron_jobs
            exit $?
            ;;
        status)
            show_cron_status
            exit 0
            ;;
        list)
            list_cron_jobs
            exit 0
            ;;
        *)
            show_usage
            exit 1
            ;;
    esac
}

main "$@"
