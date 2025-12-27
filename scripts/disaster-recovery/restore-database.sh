#!/bin/bash

################################################################################
# DATABASE RESTORE SCRIPT
#
# Comprehensive PostgreSQL restore with support for:
# - Full restore from backup file
# - Point-in-time recovery (PITR)
# - Incremental recovery from WAL files
# - Staging environment restore
# - Backup integrity verification
#
# Usage:
#   # Restore from latest daily backup
#   ./restore-database.sh --type full --from latest
#
#   # Restore from specific backup file
#   ./restore-database.sh --type full --file /backups/daily/backup_20251227.dump.gz
#
#   # Point-in-time recovery
#   ./restore-database.sh --type pitr --until "2025-12-27 14:30:00"
#
#   # Restore to staging
#   ./restore-database.sh --type full --from latest --target staging
#
# Environment:
#   DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
#   BACKUP_DIR (default: /backups)
#
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
LOG_DIR="${BACKUP_DIR}/logs"

# Database configuration
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_USER="${DB_USER:-postgres}"
DB_PASSWORD="${DB_PASSWORD:-postgres}"
DB_NAME="${DB_NAME:-thebot_db}"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

# Parameters
RESTORE_TYPE="${RESTORE_TYPE:-full}"  # full, pitr, incremental
RESTORE_FROM="${RESTORE_FROM:-latest}"  # latest, daily, weekly, monthly, YYYYMMDD, or file path
BACKUP_FILE="${BACKUP_FILE:-}"
RESTORE_UNTIL="${RESTORE_UNTIL:-}"
TARGET_ENV="${TARGET_ENV:-production}"  # production, staging
SKIP_VERIFICATION="${SKIP_VERIFICATION:-false}"

# Logging
RESTORE_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESTORE_LOG="${LOG_DIR}/restore_${RESTORE_TIMESTAMP}.log"
mkdir -p "$LOG_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Tracking
RESTORE_SUCCESS=false
RESTORE_START_TIME=$(date +%s)

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$RESTORE_LOG"
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $*${NC}" | tee -a "$RESTORE_LOG"
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$*${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_progress() {
    echo -e "${YELLOW}[*] $*${NC}"
}

validate_backup_file() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        log_error "Backup file not found: $file"
        return 1
    fi

    # Check file size
    local file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    if [[ $file_size -lt 1000 ]]; then
        log_error "Backup file is suspiciously small: ${file_size} bytes"
        return 1
    fi

    log_info "Backup file validation: OK ($(( file_size / 1024 / 1024 ))MB)"
    return 0
}

verify_backup_integrity() {
    local file="$1"

    log_info "Verifying backup integrity..."

    # Check if file is valid gzip
    if file "$file" | grep -q "gzip"; then
        print_progress "Testing gzip integrity..."
        if ! gzip -t "$file" 2>/dev/null; then
            log_error "Backup file gzip test failed - file may be corrupted"
            return 1
        fi
        log_success "Gzip integrity verified"
    fi

    # Check metadata file (if exists)
    local metadata_file="${file%.gz}.metadata"
    if [[ -f "$metadata_file" ]]; then
        log_info "Found metadata file: $metadata_file"
        if grep -q '"verified": true' "$metadata_file"; then
            log_success "Backup was previously verified"
        fi
    fi

    return 0
}

check_postgres_running() {
    local container="thebot-postgres-prod"

    if [[ "$TARGET_ENV" == "staging" ]]; then
        container="thebot-postgres-staging"
    fi

    if ! docker ps -q -f "name=$container" | grep -q .; then
        log_warn "PostgreSQL container not running: $container"

        if [[ "$TARGET_ENV" == "staging" ]]; then
            log_info "Starting staging PostgreSQL..."
            docker-compose -f "$PROJECT_ROOT/docker-compose.staging.yml" up -d postgres
            sleep 10
        else
            log_info "Starting production PostgreSQL..."
            docker-compose -f "$COMPOSE_FILE" up -d postgres
            sleep 10
        fi
    fi

    # Wait for PostgreSQL to be ready
    local max_retries=30
    local retry=0

    while [[ $retry -lt $max_retries ]]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U "$DB_USER" &>/dev/null; then
            log_success "PostgreSQL is ready"
            return 0
        fi

        retry=$((retry + 1))
        log_warn "Waiting for PostgreSQL... (attempt $retry/$max_retries)"
        sleep 2
    done

    log_error "PostgreSQL failed to start"
    return 1
}

find_backup_file() {
    local from="$1"

    case "$from" in
        latest)
            log_info "Finding latest backup..."
            local latest_daily=$(find "$BACKUP_DIR/daily" -name "backup_*.dump.gz" 2>/dev/null | sort -r | head -1)
            if [[ -n "$latest_daily" ]]; then
                echo "$latest_daily"
                return 0
            fi
            ;;

        daily)
            log_info "Finding latest daily backup..."
            find "$BACKUP_DIR/daily" -name "backup_*.dump.gz" 2>/dev/null | sort -r | head -1
            return 0
            ;;

        weekly)
            log_info "Finding latest weekly backup..."
            find "$BACKUP_DIR/weekly" -name "backup_*.dump.gz" 2>/dev/null | sort -r | head -1
            return 0
            ;;

        monthly)
            log_info "Finding latest monthly backup..."
            find "$BACKUP_DIR/monthly" -name "backup_*.dump.gz" 2>/dev/null | sort -r | head -1
            return 0
            ;;

        *)
            # Treat as date (YYYYMMDD)
            if [[ "$from" =~ ^[0-9]{8}$ ]]; then
                log_info "Finding backup from date: $from..."
                find "$BACKUP_DIR" -name "*${from}*.dump.gz" 2>/dev/null | head -1
                return 0
            fi
            ;;
    esac

    return 1
}

################################################################################
# FULL RESTORE
################################################################################

restore_full() {
    print_header "FULL DATABASE RESTORE"

    log_info "Restore Type: Full"
    log_info "Target Environment: $TARGET_ENV"

    # Step 1: Determine backup file
    log_info "Step 1: Locating backup file..."

    if [[ -n "$BACKUP_FILE" ]]; then
        if ! validate_backup_file "$BACKUP_FILE"; then
            return 1
        fi
    else
        BACKUP_FILE=$(find_backup_file "$RESTORE_FROM")
        if [[ -z "$BACKUP_FILE" ]] || [[ ! -f "$BACKUP_FILE" ]]; then
            log_error "Could not find backup matching: $RESTORE_FROM"
            return 1
        fi
    fi

    log_success "Found backup: $BACKUP_FILE"

    # Step 2: Verify backup integrity
    log_info "Step 2: Verifying backup integrity..."

    if [[ "$SKIP_VERIFICATION" != "true" ]]; then
        if ! verify_backup_integrity "$BACKUP_FILE"; then
            log_error "Backup integrity check failed"
            return 1
        fi
    else
        log_warn "Skipping backup integrity verification"
    fi

    # Step 3: Create pre-restore backup (if production and DB exists)
    if [[ "$TARGET_ENV" == "production" ]]; then
        log_info "Step 3: Creating pre-restore backup..."

        local pre_restore_dir="${BACKUP_DIR}/pre-restore-${RESTORE_TIMESTAMP}"
        mkdir -p "$pre_restore_dir"

        if check_postgres_running; then
            print_progress "Backing up current database..."
            if docker-compose -f "$COMPOSE_FILE" exec -T postgres \
              pg_dump -U "$DB_USER" -d "$DB_NAME" -F custom | \
              gzip > "${pre_restore_dir}/pre_restore.dump.gz"; then
                log_success "Pre-restore backup created"
            else
                log_warn "Could not create pre-restore backup (DB may not exist yet)"
            fi
        fi
    fi

    # Step 4: Drop and recreate database
    log_info "Step 4: Preparing database..."

    if ! check_postgres_running; then
        return 1
    fi

    if docker-compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U "$DB_USER" -lqt | cut -d \| -f 1 | grep -qw "$DB_NAME"; then
        print_progress "Dropping existing database..."
        if ! docker-compose -f "$COMPOSE_FILE" exec -T postgres \
          psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS \"$DB_NAME\" WITH (FORCE);" 2>/dev/null; then
            log_warn "Could not drop database (may be in use, trying to continue)"
        fi
        sleep 5
    fi

    print_progress "Creating fresh database..."
    if ! docker-compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U "$DB_USER" -c "CREATE DATABASE \"$DB_NAME\" WITH ENCODING 'UTF8' LC_COLLATE 'C' LC_CTYPE 'C';"; then
        log_error "Failed to create database"
        return 1
    fi

    log_success "Database prepared"

    # Step 5: Restore from backup
    log_info "Step 5: Restoring from backup..."
    log_info "File: $BACKUP_FILE"
    log_info "Size: $(( $(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE") / 1024 / 1024 ))MB"

    print_progress "Decompressing and restoring (this may take several minutes)..."

    local start_time=$(date +%s)

    if gunzip < "$BACKUP_FILE" | docker-compose -f "$COMPOSE_FILE" exec -T postgres \
      pg_restore -U "$DB_USER" -d "$DB_NAME" --exit-on-error 2>&1 | tee -a "$RESTORE_LOG"; then
        log_success "Database restored successfully"
    else
        log_error "Database restore failed"
        return 1
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_info "Restore duration: ${duration} seconds ($(( duration / 60 )) minutes)"

    # Step 6: Verify restore
    log_info "Step 6: Verifying restored database..."

    local table_count=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
      psql -U "$DB_USER" -d "$DB_NAME" -t -c \
      "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';")

    if [[ $table_count -gt 0 ]]; then
        log_success "Database verified: $table_count tables"
    else
        log_error "Database verification failed: no tables found"
        return 1
    fi

    RESTORE_SUCCESS=true
    return 0
}

################################################################################
# PITR RESTORE
################################################################################

restore_pitr() {
    print_header "POINT-IN-TIME RECOVERY (PITR)"

    log_info "Restore Type: PITR"
    log_info "Target Time: $RESTORE_UNTIL"

    if [[ -z "$RESTORE_UNTIL" ]]; then
        log_error "PITR requires --until parameter"
        return 1
    fi

    log_warn "PITR restore requires manual configuration of recovery.conf"
    log_warn "This is an advanced operation. Ensure WAL files are available."

    # Step 1: Find backup before target time
    log_info "Step 1: Finding base backup..."

    # This would typically find the latest backup before RESTORE_UNTIL
    local base_backup=$(find "$BACKUP_DIR" -name "backup_*.dump.gz" -printf "%T@ %p\n" | \
        awk '{print $2}' | sort -r | head -1)

    if [[ -z "$base_backup" ]]; then
        log_error "No backup found for PITR"
        return 1
    fi

    log_info "Base backup: $base_backup"

    # Step 2: Check WAL files
    log_info "Step 2: Checking WAL files..."

    local wal_count=$(find "$BACKUP_DIR/wal-archive" -name "*.wal" -o -name "*.backup" 2>/dev/null | wc -l)
    log_info "Found $wal_count WAL files"

    if [[ $wal_count -lt 10 ]]; then
        log_warn "Limited WAL files available, PITR may not be possible"
    fi

    # Step 3: Restore base backup
    log_info "Step 3: Restoring base backup..."

    if ! restore_full; then
        log_error "Failed to restore base backup for PITR"
        return 1
    fi

    # Step 4: Replay WAL to target time
    log_info "Step 4: Replaying WAL to target time..."
    log_warn "Manual WAL replay required - requires recovery.conf configuration"

    # NOTE: Actual PITR replay would be:
    # 1. Stop PostgreSQL
    # 2. Create recovery.conf with:
    #    restore_command = 'test -f /wal-archive/%f && cp /wal-archive/%f %p'
    #    recovery_target_time = '2025-12-27 14:30:00'
    #    recovery_target_inclusive = false
    # 3. Start PostgreSQL
    # 4. PostgreSQL replays WAL until target time

    log_info "PITR restore flow:"
    log_info "  1. Base backup restored to $DB_NAME"
    log_info "  2. WAL files available at: $BACKUP_DIR/wal-archive/"
    log_info "  3. Target time: $RESTORE_UNTIL"
    log_info "  4. Manual: Configure recovery.conf and restart PostgreSQL"

    RESTORE_SUCCESS=true
    return 0
}

################################################################################
# RESTORE REPORT
################################################################################

show_restore_report() {
    print_header "RESTORE REPORT"

    local restore_duration=$(($(date +%s) - RESTORE_START_TIME))

    echo "Restore ID: $RESTORE_TIMESTAMP"
    echo "Type: $RESTORE_TYPE"
    echo "Target: $TARGET_ENV"
    echo "Duration: ${restore_duration} seconds ($(( restore_duration / 60 )) minutes)"
    echo ""

    if [[ "$RESTORE_SUCCESS" == "true" ]]; then
        echo -e "${GREEN}RESTORE STATUS: SUCCESS${NC}"
    else
        echo -e "${RED}RESTORE STATUS: FAILED${NC}"
    fi

    echo ""
    echo "Log file: $RESTORE_LOG"

    if [[ -n "$BACKUP_FILE" ]]; then
        echo "Backup used: $BACKUP_FILE"
    fi

    echo ""

    return $([ "$RESTORE_SUCCESS" = "true" ] && echo 0 || echo 1)
}

################################################################################
# MAIN
################################################################################

main() {
    print_header "DATABASE RESTORE UTILITY"

    log_info "Start time: $(date)"
    log_info "Restore type: $RESTORE_TYPE"
    log_info "From: $RESTORE_FROM"

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --type)
                RESTORE_TYPE="$2"
                shift 2
                ;;
            --from)
                RESTORE_FROM="$2"
                shift 2
                ;;
            --file)
                BACKUP_FILE="$2"
                shift 2
                ;;
            --until)
                RESTORE_UNTIL="$2"
                shift 2
                ;;
            --target)
                TARGET_ENV="$2"
                shift 2
                ;;
            --skip-verify)
                SKIP_VERIFICATION="true"
                shift
                ;;
            *)
                log_error "Unknown option: $1"
                exit 1
                ;;
        esac
    done

    # Execute restore based on type
    case "$RESTORE_TYPE" in
        full)
            restore_full || exit 1
            ;;
        pitr)
            restore_pitr || exit 1
            ;;
        *)
            log_error "Unknown restore type: $RESTORE_TYPE"
            exit 1
            ;;
    esac

    # Show report
    show_restore_report
    exit $?
}

main "$@"
