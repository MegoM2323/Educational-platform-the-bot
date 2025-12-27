#!/bin/bash

################################################################################
# SETUP CRON JOBS FOR BACKUP VERIFICATION
#
# Sets up automated cron jobs for:
# - Daily backup verification
# - Weekly restore tests
# - Email alerts on failures
#
# Usage:
#   ./setup-cron.sh              # Install all cron jobs
#   ./setup-cron.sh --remove     # Remove all cron jobs
#   ./setup-cron.sh --list       # List installed cron jobs
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
CRON_IDENTIFIER="THEBOT_BACKUP_VERIFICATION"
BACKUP_DIR="${PROJECT_ROOT}/backups"
LOG_DIR="${BACKUP_DIR}/verification_logs"

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
    if ! command -v crontab &>/dev/null; then
        log ERROR "crontab command not found"
        return 1
    fi

    if ! command -v python &>/dev/null && ! command -v python3 &>/dev/null; then
        log ERROR "Python not found"
        return 1
    fi

    if [ ! -f "${PROJECT_ROOT}/backend/manage.py" ]; then
        log ERROR "Django manage.py not found at ${PROJECT_ROOT}/backend/"
        return 1
    fi

    log SUCCESS "All prerequisites found"
    return 0
}

################################################################################
# CRON JOB MANAGEMENT
################################################################################

install_cron_jobs() {
    log INFO "Installing cron jobs..."

    # Create log directory
    mkdir -p "${LOG_DIR}"
    chmod 700 "${LOG_DIR}"

    # Get Python executable
    local python_cmd="python3"
    if ! command -v python3 &>/dev/null; then
        python_cmd="python"
    fi

    # Get current crontab
    local current_crontab=""
    if crontab -l 2>/dev/null; then
        current_crontab=$(crontab -l 2>/dev/null)
    fi

    # Build new crontab with jobs
    local new_crontab="${current_crontab}"

    # Add header
    if ! echo "${current_crontab}" | grep -q "${CRON_IDENTIFIER}"; then
        new_crontab="${new_crontab}
# ============================================
# ${CRON_IDENTIFIER}
# ============================================"
    fi

    # Daily backup verification at 2 AM
    if ! echo "${current_crontab}" | grep -q "verify_backup --all"; then
        new_crontab="${new_crontab}
0 2 * * * cd ${PROJECT_ROOT} && ${python_cmd} backend/manage.py verify_backup --all --report >> ${LOG_DIR}/daily_verification.log 2>&1"
        log SUCCESS "Added daily backup verification (2 AM)"
    else
        log WARN "Daily backup verification already exists"
    fi

    # Email alerts on failures at 3 AM
    if ! echo "${current_crontab}" | grep -q "verify_backup --alert"; then
        new_crontab="${new_crontab}
0 3 * * * cd ${PROJECT_ROOT} && ${python_cmd} backend/manage.py verify_backup --all --alert >> ${LOG_DIR}/alerts.log 2>&1"
        log SUCCESS "Added email alert job (3 AM)"
    else
        log WARN "Email alert job already exists"
    fi

    # Weekly restore test on Sunday at 4 AM
    if ! echo "${current_crontab}" | grep -q "restore-test.sh.*--weekly"; then
        new_crontab="${new_crontab}
0 4 * * 0 cd ${PROJECT_ROOT}/scripts/backup && ./restore-test.sh --weekly >> ${LOG_DIR}/weekly_restore_test.log 2>&1"
        log SUCCESS "Added weekly restore test (Sunday 4 AM)"
    else
        log WARN "Weekly restore test already exists"
    fi

    # Database integrity check on Wednesday at 1 AM
    if ! echo "${current_crontab}" | grep -q "verify_backup --database-check"; then
        new_crontab="${new_crontab}
0 1 * * 3 cd ${PROJECT_ROOT} && ${python_cmd} backend/manage.py verify_backup --database-check >> ${LOG_DIR}/db_integrity.log 2>&1"
        log SUCCESS "Added database integrity check (Wednesday 1 AM)"
    else
        log WARN "Database integrity check already exists"
    fi

    # Install new crontab
    if echo "${new_crontab}" | crontab -; then
        log SUCCESS "Cron jobs installed successfully"
        return 0
    else
        log ERROR "Failed to install cron jobs"
        return 1
    fi
}

remove_cron_jobs() {
    log INFO "Removing cron jobs..."

    # Get current crontab
    if ! crontab -l 2>/dev/null | grep -q "${CRON_IDENTIFIER}"; then
        log WARN "No backup verification cron jobs found"
        return 0
    fi

    # Remove jobs
    local new_crontab=$(crontab -l 2>/dev/null | grep -v "${CRON_IDENTIFIER}" | \
        grep -v "verify_backup" | \
        grep -v "restore-test.sh" | \
        sed '/^$/d')

    if echo "${new_crontab}" | crontab -; then
        log SUCCESS "Cron jobs removed successfully"
        return 0
    else
        log ERROR "Failed to remove cron jobs"
        return 1
    fi
}

list_cron_jobs() {
    log INFO "Listing backup verification cron jobs..."

    if crontab -l 2>/dev/null | grep -q "${CRON_IDENTIFIER}"; then
        echo ""
        crontab -l 2>/dev/null | grep -A 10 "${CRON_IDENTIFIER}"
        echo ""
    else
        log WARN "No backup verification cron jobs found"
        return 1
    fi
}

show_schedule() {
    log INFO "Backup verification schedule:"
    echo ""
    echo "  2:00 AM (Daily)      - Verify all backups"
    echo "  3:00 AM (Daily)      - Send email alerts on failures"
    echo "  1:00 AM (Wednesday)  - Check database integrity"
    echo "  4:00 AM (Sunday)     - Test restore from backup"
    echo ""
    echo "Logs are stored in: ${LOG_DIR}/"
    echo ""
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Backup Verification Cron Setup${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    if ! check_prerequisites; then
        exit 1
    fi

    # Parse arguments
    local action="${1:-install}"

    case "${action}" in
        install)
            if install_cron_jobs; then
                show_schedule
                echo -e "${GREEN}✓ Cron jobs installed${NC}"
                exit 0
            else
                exit 1
            fi
            ;;
        remove|--remove)
            if remove_cron_jobs; then
                echo -e "${GREEN}✓ Cron jobs removed${NC}"
                exit 0
            else
                exit 1
            fi
            ;;
        list|--list)
            if list_cron_jobs; then
                exit 0
            else
                exit 1
            fi
            ;;
        schedule|--schedule)
            show_schedule
            exit 0
            ;;
        *)
            echo "Usage: $0 [install|remove|list|schedule]"
            echo ""
            echo "Actions:"
            echo "  install   - Install cron jobs for backup verification"
            echo "  remove    - Remove all backup verification cron jobs"
            echo "  list      - List installed cron jobs"
            echo "  schedule  - Show backup verification schedule"
            echo ""
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
