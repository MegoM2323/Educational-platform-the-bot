#!/bin/bash

################################################################################
# CRON SETUP SCRIPT FOR MEDIA BACKUPS
#
# Configures automated daily/weekly media backups using cron
# Supports health monitoring and email notifications
#
# Usage:
#   ./setup-cron.sh                 # Interactive setup
#   ./setup-cron.sh --daily         # Setup daily backup at 2 AM
#   ./setup-cron.sh --weekly        # Setup weekly backup at 2 AM Sunday
#   ./setup-cron.sh --uninstall     # Remove all backup cron jobs
#   ./setup-cron.sh --test          # Test cron setup
#   ./setup-cron.sh --list          # List installed cron jobs
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups/media}"
LOG_DIR="${BACKUP_DIR}/logs"

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
    if ! command -v crontab &> /dev/null; then
        log ERROR "crontab command not found"
        return 1
    fi

    if ! [ -f "${SCRIPT_DIR}/backup.sh" ]; then
        log ERROR "backup.sh not found in ${SCRIPT_DIR}"
        return 1
    fi

    log INFO "All prerequisites met"
    return 0
}

################################################################################
# CRON JOB MANAGEMENT
################################################################################

install_daily_backup() {
    local hour="${1:-2}"
    local minute="${2:-0}"

    log INFO "Installing daily media backup cron job"
    log INFO "Schedule: Every day at ${hour}:${minute}"

    # Create cron entry
    local cron_entry="${minute} ${hour} * * * cd ${SCRIPT_DIR} && ./backup.sh daily >> ${LOG_DIR}/cron.log 2>&1"

    # Add to crontab
    if crontab -l 2>/dev/null | grep -q "backup.sh daily"; then
        log WARN "Daily backup cron job already exists"
        return 0
    fi

    # Create temporary file with current crontab + new entry
    local temp_crontab=$(mktemp)
    crontab -l 2>/dev/null > "${temp_crontab}" || true
    echo "${cron_entry}" >> "${temp_crontab}"

    # Install new crontab
    if crontab "${temp_crontab}"; then
        log SUCCESS "Daily backup cron job installed"
        rm -f "${temp_crontab}"
        return 0
    else
        log ERROR "Failed to install cron job"
        rm -f "${temp_crontab}"
        return 1
    fi
}

install_weekly_backup() {
    local hour="${1:-2}"
    local minute="${2:-0}"

    log INFO "Installing weekly media backup cron job"
    log INFO "Schedule: Every Sunday at ${hour}:${minute}"

    # Create cron entry
    local cron_entry="${minute} ${hour} * * 0 cd ${SCRIPT_DIR} && ./backup.sh full >> ${LOG_DIR}/cron.log 2>&1"

    # Add to crontab
    if crontab -l 2>/dev/null | grep -q "backup.sh full"; then
        log WARN "Weekly backup cron job already exists"
        return 0
    fi

    # Create temporary file with current crontab + new entry
    local temp_crontab=$(mktemp)
    crontab -l 2>/dev/null > "${temp_crontab}" || true
    echo "${cron_entry}" >> "${temp_crontab}"

    # Install new crontab
    if crontab "${temp_crontab}"; then
        log SUCCESS "Weekly backup cron job installed"
        rm -f "${temp_crontab}"
        return 0
    else
        log ERROR "Failed to install cron job"
        rm -f "${temp_crontab}"
        return 1
    fi
}

install_cleanup_job() {
    local day="${1:-1}"
    local hour="${2:-3}"

    log INFO "Installing cleanup cron job"
    log INFO "Schedule: Day ${day} of month at ${hour}:00"

    # Create cron entry
    local cron_entry="0 ${hour} ${day} * * cd ${SCRIPT_DIR} && ./backup.sh cleanup >> ${LOG_DIR}/cron.log 2>&1"

    # Add to crontab
    if crontab -l 2>/dev/null | grep -q "backup.sh cleanup"; then
        log WARN "Cleanup cron job already exists"
        return 0
    fi

    # Create temporary file with current crontab + new entry
    local temp_crontab=$(mktemp)
    crontab -l 2>/dev/null > "${temp_crontab}" || true
    echo "${cron_entry}" >> "${temp_crontab}"

    # Install new crontab
    if crontab "${temp_crontab}"; then
        log SUCCESS "Cleanup cron job installed"
        rm -f "${temp_crontab}"
        return 0
    else
        log ERROR "Failed to install cron job"
        rm -f "${temp_crontab}"
        return 1
    fi
}

list_backup_jobs() {
    log INFO "Installed backup cron jobs:"
    echo ""

    if crontab -l 2>/dev/null | grep -q "backup.sh"; then
        crontab -l | grep "backup.sh" || echo "No backup jobs found"
    else
        echo "No backup jobs found"
        return 1
    fi

    return 0
}

uninstall_backup_jobs() {
    log INFO "Removing all backup cron jobs..."

    if ! crontab -l 2>/dev/null | grep -q "backup.sh"; then
        log WARN "No backup cron jobs found"
        return 0
    fi

    # Create temporary file without backup jobs
    local temp_crontab=$(mktemp)
    crontab -l 2>/dev/null | grep -v "backup.sh" > "${temp_crontab}" || true

    # Install new crontab
    if crontab "${temp_crontab}"; then
        log SUCCESS "Backup cron jobs removed"
        rm -f "${temp_crontab}"
        return 0
    else
        log ERROR "Failed to remove cron jobs"
        rm -f "${temp_crontab}"
        return 1
    fi
}

################################################################################
# INTERACTIVE SETUP
################################################################################

interactive_setup() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Media Backup Cron Setup${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Daily backup option
    echo "1. Daily backup?"
    read -p "Install daily backup at 2:00 AM? (y/n): " -r answer
    if [ "${answer}" = "y" ] || [ "${answer}" = "Y" ]; then
        read -p "Backup hour (0-23) [2]: " -r hour
        hour="${hour:-2}"
        install_daily_backup "${hour}" "0"
    fi

    echo ""

    # Weekly backup option
    echo "2. Weekly full backup?"
    read -p "Install weekly full backup at 2:00 AM on Sundays? (y/n): " -r answer
    if [ "${answer}" = "y" ] || [ "${answer}" = "Y" ]; then
        read -p "Backup hour (0-23) [2]: " -r hour
        hour="${hour:-2}"
        install_weekly_backup "${hour}" "0"
    fi

    echo ""

    # Cleanup job option
    echo "3. Monthly cleanup?"
    read -p "Install monthly cleanup on the 1st at 3:00 AM? (y/n): " -r answer
    if [ "${answer}" = "y" ] || [ "${answer}" = "Y" ]; then
        read -p "Cleanup hour (0-23) [3]: " -r hour
        hour="${hour:-3}"
        install_cleanup_job "1" "${hour}"
    fi

    echo ""
    list_backup_jobs
}

################################################################################
# TEST EXECUTION
################################################################################

test_cron_setup() {
    log INFO "Testing cron setup..."
    echo ""

    # Check that backup script is executable
    if [ ! -x "${SCRIPT_DIR}/backup.sh" ]; then
        log WARN "Making backup.sh executable"
        chmod +x "${SCRIPT_DIR}/backup.sh"
    fi

    # Run a test backup
    log INFO "Running test backup..."
    if "${SCRIPT_DIR}/backup.sh" daily; then
        log SUCCESS "Test backup completed successfully"

        # Check backup directory
        if [ -d "${BACKUP_DIR}/full" ]; then
            local backup_count=$(find "${BACKUP_DIR}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)
            log INFO "Backups found: ${backup_count}"
        fi

        return 0
    else
        log ERROR "Test backup failed"
        return 1
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Cron Setup Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Initialize
    mkdir -p "${LOG_DIR}"

    if ! check_prerequisites; then
        exit 1
    fi

    # Make backup script executable
    chmod +x "${SCRIPT_DIR}/backup.sh"
    chmod +x "${SCRIPT_DIR}/restore.sh"

    local command="${1:-}"

    case "${command}" in
        --daily)
            install_daily_backup "${2:-2}" "${3:-0}"
            echo ""
            list_backup_jobs
            ;;
        --weekly)
            install_weekly_backup "${2:-2}" "${3:-0}"
            install_cleanup_job "1" "3"
            echo ""
            list_backup_jobs
            ;;
        --uninstall)
            uninstall_backup_jobs
            ;;
        --test)
            test_cron_setup
            ;;
        --list)
            list_backup_jobs
            ;;
        *)
            interactive_setup
            ;;
    esac

    echo ""
    log SUCCESS "Cron setup completed"
    exit 0
}

# Run main function
main "$@"
