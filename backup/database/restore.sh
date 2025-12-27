#!/bin/bash

################################################################################
# DATABASE RESTORE SCRIPT
#
# Restore database from backup files with point-in-time recovery support
# Supports PostgreSQL and SQLite databases
#
# Usage:
#   ./restore.sh backup_file                    # Restore from specific backup
#   ./restore.sh latest                         # Restore from latest backup
#   ./restore.sh latest daily                   # Restore from latest daily backup
#   ./restore.sh list                           # List available backups
#   ./restore.sh verify backup_file             # Verify backup before restore
#   ./restore.sh --dry-run backup_file          # Test restore without applying
#
# Environment Variables:
#   BACKUP_DIR              Base backup directory (default: ./backups)
#   DATABASE_TYPE           postgresql|sqlite (default: postgresql)
#   DATABASE_URL            PostgreSQL connection string
#   DATABASE_PATH           SQLite database file path
#   DB_HOST, DB_PORT, etc.  Database connection parameters
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
DATABASE_TYPE="${DATABASE_TYPE:-postgresql}"
BACKUP_CATEGORY="${BACKUP_CATEGORY:-daily}"
DRY_RUN="${DRY_RUN:-false}"

# Log file
LOG_DIR="${BACKUP_DIR}/logs"
LOG_FILE="${LOG_DIR}/restore_$(date +%Y%m%d_%H%M%S).log"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global state
RESTORE_SUCCESS=false
RESTORE_START_TIME=""
RESTORE_END_TIME=""

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
            ;;
    esac
}

init_directories() {
    mkdir -p "${LOG_DIR}"
    log INFO "Initialized log directory: ${LOG_DIR}"
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
    command -v gunzip >/dev/null 2>&1 || missing_tools+=("gunzip")
    command -v tar >/dev/null 2>&1 || missing_tools+=("tar")
    command -v sha256sum >/dev/null 2>&1 || missing_tools+=("sha256sum")

    # Database-specific tools
    if [ "${DATABASE_TYPE}" = "postgresql" ]; then
        command -v pg_restore >/dev/null 2>&1 || missing_tools+=("pg_restore (postgresql-client)")
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
# BACKUP DISCOVERY AND LISTING
################################################################################

list_backups() {
    log INFO "Available backups:"
    echo ""

    echo -e "${BLUE}Daily Backups:${NC}"
    if [ -d "${BACKUP_DIR}/daily" ]; then
        ls -lh "${BACKUP_DIR}/daily"/backup_*.gz 2>/dev/null | awk '{print $9, "(" $5 ")"}' | tail -10 || echo "  No daily backups found"
    else
        echo "  Directory not found"
    fi

    echo ""
    echo -e "${BLUE}Weekly Backups:${NC}"
    if [ -d "${BACKUP_DIR}/weekly" ]; then
        ls -lh "${BACKUP_DIR}/weekly"/backup_*.gz 2>/dev/null | awk '{print $9, "(" $5 ")"}' | tail -10 || echo "  No weekly backups found"
    else
        echo "  Directory not found"
    fi

    echo ""
    echo -e "${BLUE}Monthly Backups:${NC}"
    if [ -d "${BACKUP_DIR}/monthly" ]; then
        ls -lh "${BACKUP_DIR}/monthly"/backup_*.gz 2>/dev/null | awk '{print $9, "(" $5 ")"}' | tail -10 || echo "  No monthly backups found"
    else
        echo "  Directory not found"
    fi
}

find_latest_backup() {
    local category="${1:-daily}"

    if [ ! -d "${BACKUP_DIR}/${category}" ]; then
        log ERROR "Backup directory not found: ${BACKUP_DIR}/${category}"
        return 1
    fi

    # Find the most recent backup in the category
    local latest=$(find "${BACKUP_DIR}/${category}" -maxdepth 1 -name "backup_*.gz" -type f -printf '%T@ %p\n' 2>/dev/null | sort -rn | head -1 | cut -d' ' -f2-)

    if [ -z "${latest}" ]; then
        log ERROR "No backups found in category: ${category}"
        return 1
    fi

    echo "${latest}"
}

################################################################################
# BACKUP VERIFICATION
################################################################################

verify_backup_file() {
    local backup_file=$1

    if [ ! -f "${backup_file}" ]; then
        log ERROR "Backup file not found: ${backup_file}"
        return 1
    fi

    log INFO "Verifying backup integrity..."

    # Check gzip integrity
    if ! gzip -t "${backup_file}" 2>/dev/null; then
        log ERROR "Gzip integrity check failed"
        return 1
    fi

    log SUCCESS "Gzip integrity check passed"

    # Verify checksum if metadata exists
    local metadata_file="${backup_file}.metadata"
    if [ -f "${metadata_file}" ]; then
        log INFO "Verifying checksum from metadata..."

        local expected_checksum=$(grep -o '"backup_checksum_sha256": "[^"]*' "${metadata_file}" 2>/dev/null | cut -d'"' -f4)

        if [ -z "${expected_checksum}" ]; then
            log WARN "Checksum not found in metadata, skipping verification"
            return 0
        fi

        local actual_checksum=$(sha256sum "${backup_file}" | awk '{print $1}')

        if [ "${expected_checksum}" != "${actual_checksum}" ]; then
            log ERROR "Checksum mismatch: expected ${expected_checksum}, got ${actual_checksum}"
            return 1
        fi

        log SUCCESS "Checksum verified: ${expected_checksum}"
    else
        log WARN "Metadata file not found, skipping checksum verification"
    fi

    return 0
}

get_backup_size() {
    local backup_file=$1
    du -h "${backup_file}" | awk '{print $1}'
}

################################################################################
# DATABASE RESTORE FUNCTIONS
################################################################################

restore_postgresql() {
    local backup_file=$1

    log INFO "Preparing PostgreSQL restore from ${backup_file}"

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

    log INFO "Target: ${db_user}@${db_host}:${db_port}/${db_name}"

    # Test connection
    if ! PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${db_user}" \
        -d "${db_name}" \
        -c "SELECT 1" >/dev/null 2>&1; then
        log ERROR "Cannot connect to database: ${db_host}:${db_port}/${db_name}"
        return 1
    fi

    log INFO "Database connection verified"

    if [ "${DRY_RUN}" = "true" ]; then
        log INFO "[DRY RUN] Would restore from: ${backup_file}"
        return 0
    fi

    # Create backup of current database before restore
    log INFO "Creating backup of current database..."
    local backup_timestamp=$(date +%Y%m%d_%H%M%S)
    local pre_restore_backup="${BACKUP_DIR}/pre-restore-${backup_timestamp}.sql.gz"

    if PGPASSWORD="${DB_PASSWORD:-}" pg_dump \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${db_user}" \
        -d "${db_name}" \
        -F custom | gzip > "${pre_restore_backup}"; then
        log SUCCESS "Pre-restore backup created: ${pre_restore_backup}"
    else
        log WARN "Failed to create pre-restore backup"
    fi

    # Drop existing database (dangerous - requires confirmation)
    log INFO "Dropping existing database: ${db_name}"
    if ! PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${db_user}" \
        -d "postgres" \
        -c "DROP DATABASE IF EXISTS ${db_name} WITH (FORCE);" 2>"${LOG_FILE}.err"; then
        log ERROR "Failed to drop database"
        cat "${LOG_FILE}.err" >> "${LOG_FILE}"
        return 1
    fi

    # Create empty database
    log INFO "Creating new database: ${db_name}"
    if ! PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${db_user}" \
        -d "postgres" \
        -c "CREATE DATABASE ${db_name};" 2>"${LOG_FILE}.err"; then
        log ERROR "Failed to create database"
        cat "${LOG_FILE}.err" >> "${LOG_FILE}"
        return 1
    fi

    RESTORE_START_TIME=$(date +%s)

    # Restore from backup
    log INFO "Restoring database from backup (this may take a few minutes)..."

    if ! gunzip -c "${backup_file}" | PGPASSWORD="${DB_PASSWORD:-}" pg_restore \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${db_user}" \
        -d "${db_name}" \
        --exit-on-error \
        -v 2>"${LOG_FILE}.restore.err" | head -50 >> "${LOG_FILE}"; then
        log ERROR "Database restore failed"
        if [ -f "${LOG_FILE}.restore.err" ]; then
            log ERROR "$(head -20 "${LOG_FILE}.restore.err")"
        fi
        return 1
    fi

    RESTORE_END_TIME=$(date +%s)
    local duration=$((RESTORE_END_TIME - RESTORE_START_TIME))

    log SUCCESS "PostgreSQL restore completed in ${duration}s"
    return 0
}

restore_sqlite() {
    local backup_file=$1
    local db_path="${DATABASE_PATH:-${PROJECT_ROOT}/backend/db.sqlite3}"
    local db_backup="${db_path}.pre-restore.$(date +%Y%m%d_%H%M%S)"

    log INFO "Preparing SQLite restore from ${backup_file}"
    log INFO "Target: ${db_path}"

    if [ ! -f "${db_path}" ]; then
        log WARN "Database file does not exist, will be created"
    fi

    if [ "${DRY_RUN}" = "true" ]; then
        log INFO "[DRY RUN] Would restore from: ${backup_file}"
        return 0
    fi

    # Backup current database
    if [ -f "${db_path}" ]; then
        log INFO "Creating backup of current database..."
        cp "${db_path}" "${db_backup}"
        log SUCCESS "Pre-restore backup created: ${db_backup}"
    fi

    RESTORE_START_TIME=$(date +%s)

    # Restore from backup
    log INFO "Restoring database from backup..."

    if ! gunzip -c "${backup_file}" > "${db_path}" 2>"${LOG_FILE}.err"; then
        log ERROR "Failed to restore database"
        cat "${LOG_FILE}.err" >> "${LOG_FILE}"

        # Restore from pre-restore backup
        if [ -f "${db_backup}" ]; then
            log INFO "Restoring from pre-restore backup..."
            cp "${db_backup}" "${db_path}"
        fi

        return 1
    fi

    # Verify SQLite database integrity
    if ! sqlite3 "${db_path}" "PRAGMA integrity_check;" > /dev/null 2>&1; then
        log ERROR "Database integrity check failed"

        # Restore from pre-restore backup
        if [ -f "${db_backup}" ]; then
            log INFO "Restoring from pre-restore backup..."
            cp "${db_backup}" "${db_path}"
        fi

        return 1
    fi

    RESTORE_END_TIME=$(date +%s)
    local duration=$((RESTORE_END_TIME - RESTORE_START_TIME))

    log SUCCESS "SQLite restore completed in ${duration}s"
    return 0
}

restore_database() {
    case "${DATABASE_TYPE}" in
        postgresql)
            restore_postgresql "$1"
            ;;
        sqlite)
            restore_sqlite "$1"
            ;;
        *)
            log ERROR "Unknown database type: ${DATABASE_TYPE}"
            return 1
            ;;
    esac
}

################################################################################
# POST-RESTORE VERIFICATION
################################################################################

verify_restore() {
    log INFO "Verifying restored database..."

    case "${DATABASE_TYPE}" in
        postgresql)
            verify_restore_postgresql
            ;;
        sqlite)
            verify_restore_sqlite
            ;;
    esac
}

verify_restore_postgresql() {
    local db_host="${DB_HOST:-localhost}"
    local db_port="${DB_PORT:-5432}"
    local db_user="${DB_USER:-postgres}"
    local db_name="${DB_NAME:-thebot}"

    # Test connection
    if ! PGPASSWORD="${DB_PASSWORD:-}" psql \
        -h "${db_host}" \
        -p "${db_port}" \
        -U "${db_user}" \
        -d "${db_name}" \
        -c "SELECT COUNT(*) as tables FROM information_schema.tables WHERE table_schema='public';" > /tmp/table_count.txt 2>&1; then
        log ERROR "Cannot connect to restored database"
        return 1
    fi

    local table_count=$(grep -o '[0-9]\+' /tmp/table_count.txt | head -1)
    log SUCCESS "Restored database has ${table_count} tables"

    if [ "${table_count}" -eq 0 ]; then
        log WARN "No tables found in restored database"
        return 1
    fi

    return 0
}

verify_restore_sqlite() {
    local db_path="${DATABASE_PATH:-${PROJECT_ROOT}/backend/db.sqlite3}"

    if ! sqlite3 "${db_path}" ".tables" > /tmp/tables.txt 2>&1; then
        log ERROR "Cannot verify restored database"
        return 1
    fi

    local table_count=$(wc -w < /tmp/tables.txt)
    log SUCCESS "Restored database has ${table_count} tables"

    if [ "${table_count}" -eq 0 ]; then
        log WARN "No tables found in restored database"
        return 1
    fi

    return 0
}

################################################################################
# MAIN EXECUTION
################################################################################

show_usage() {
    cat <<EOF
Database Restore Script

Usage:
  ./restore.sh <backup_file>           Restore from specific backup file
  ./restore.sh latest [category]       Restore from latest backup (category: daily|weekly|monthly)
  ./restore.sh list                    List available backups
  ./restore.sh verify <backup_file>    Verify backup before restore
  ./restore.sh --dry-run <backup_file> Test restore without applying

Options:
  --dry-run                Run restore without actually modifying the database

Environment Variables:
  DATABASE_TYPE            postgresql|sqlite (default: postgresql)
  BACKUP_DIR               Base backup directory (default: ./backups)
  DATABASE_URL             PostgreSQL connection string
  DATABASE_PATH            SQLite database file path

Examples:
  # List available backups
  ./restore.sh list

  # Restore from latest daily backup
  ./restore.sh latest daily

  # Verify a specific backup
  ./restore.sh verify ./backups/daily/backup_20231215_120000.gz

  # Test restore without making changes
  ./restore.sh --dry-run ./backups/daily/backup_20231215_120000.gz

  # Actually restore
  ./restore.sh ./backups/daily/backup_20231215_120000.gz
EOF
}

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Database Restore Script${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Initialize
    init_directories
    load_env

    if ! check_prerequisites; then
        exit 1
    fi

    # Parse arguments
    local action="${1:-}"

    # Handle --dry-run flag
    if [ "${action}" = "--dry-run" ]; then
        DRY_RUN=true
        action="${2:-}"
        shift 2 || true
    else
        shift || true
    fi

    case "${action}" in
        list)
            list_backups
            exit 0
            ;;
        verify)
            local backup_file="${1:-}"
            if [ -z "${backup_file}" ]; then
                log ERROR "Backup file required for verify action"
                show_usage
                exit 1
            fi
            if verify_backup_file "${backup_file}"; then
                log SUCCESS "Backup verification passed"
                exit 0
            else
                exit 1
            fi
            ;;
        latest)
            local category="${1:-daily}"
            local backup_file=""
            if ! backup_file=$(find_latest_backup "${category}"); then
                log ERROR "Failed to find latest backup in category: ${category}"
                exit 1
            fi
            log INFO "Found latest backup: ${backup_file}"
            ;;
        *)
            if [ -z "${action}" ]; then
                show_usage
                exit 1
            fi
            backup_file="${action}"
            ;;
    esac

    # Verify backup file exists
    if [ ! -f "${backup_file}" ]; then
        log ERROR "Backup file not found: ${backup_file}"
        exit 1
    fi

    # Show restore details
    echo ""
    log INFO "=== Restore Details ==="
    log INFO "Backup File: $(basename "${backup_file}")"
    log INFO "Backup Size: $(get_backup_size "${backup_file}")"
    log INFO "Database Type: ${DATABASE_TYPE}"
    log INFO "Dry Run: ${DRY_RUN}"
    echo ""

    # Verify backup before restore
    if ! verify_backup_file "${backup_file}"; then
        log ERROR "Backup verification failed, aborting restore"
        exit 1
    fi

    echo ""
    if [ "${DRY_RUN}" != "true" ]; then
        echo -e "${YELLOW}WARNING: This will restore the database from backup!${NC}"
        echo "All data in the current database will be replaced."
        echo ""
        read -p "Are you sure you want to continue? (yes/no) " -r response
        if [ "${response}" != "yes" ]; then
            log INFO "Restore cancelled by user"
            exit 0
        fi
        echo ""
    else
        log INFO "DRY RUN MODE - No changes will be made"
        echo ""
    fi

    # Perform restore
    if restore_database "${backup_file}"; then
        RESTORE_SUCCESS=true

        # Verify restored database
        if verify_restore; then
            log SUCCESS "Restore completed successfully"
            echo ""
            log INFO "Duration: $((RESTORE_END_TIME - RESTORE_START_TIME))s"
            exit 0
        else
            log WARN "Restore completed but verification failed"
            exit 1
        fi
    else
        log ERROR "Restore failed"
        exit 1
    fi
}

# Run main function
main "$@"
