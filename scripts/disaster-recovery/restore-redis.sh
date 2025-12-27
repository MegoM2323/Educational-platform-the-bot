#!/bin/bash

################################################################################
# REDIS RESTORE SCRIPT
#
# Restore Redis from AOF (Append-Only File) or RDB (snapshot) backups
# Supports restoring from local backup or AWS S3
#
# Usage:
#   # Restore from latest AOF
#   ./restore-redis.sh --type aof --from latest
#
#   # Restore from RDB snapshot
#   ./restore-redis.sh --type rdb --from latest
#
#   # Restore from S3
#   ./restore-redis.sh --type rdb --from s3
#
#   # Restore specific file
#   ./restore-redis.sh --type aof --file /backups/redis_aof_20251227.bak
#
# Environment:
#   REDIS_HOST (default: localhost)
#   REDIS_PORT (default: 6379)
#   REDIS_PASSWORD (default: redis)
#   BACKUP_DIR (default: /backups)
#
################################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups}"
LOG_DIR="${BACKUP_DIR}/logs"

# Redis configuration
REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6379}"
REDIS_PASSWORD="${REDIS_PASSWORD:-redis}"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"
REDIS_CONTAINER="thebot-redis-prod"

# Parameters
RESTORE_TYPE="${RESTORE_TYPE:-aof}"  # aof, rdb
RESTORE_FROM="${RESTORE_FROM:-latest}"  # latest, daily, weekly, monthly, s3
BACKUP_FILE="${BACKUP_FILE:-}"
SKIP_VERIFICATION="${SKIP_VERIFICATION:-false}"

# Logging
RESTORE_TIMESTAMP=$(date +%Y%m%d_%H%M%S)
RESTORE_LOG="${LOG_DIR}/restore_redis_${RESTORE_TIMESTAMP}.log"
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

check_redis_running() {
    if ! docker ps -q -f "name=$REDIS_CONTAINER" | grep -q .; then
        log_warn "Redis container not running"
        return 1
    fi

    if docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" ping &>/dev/null; then
        return 0
    fi

    log_warn "Redis not responding to ping"
    return 1
}

check_redis_memory() {
    local memory_used=$(docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')

    log_info "Redis memory usage: $memory_used"
}

validate_backup_file() {
    local file="$1"

    if [[ ! -f "$file" ]]; then
        log_error "Backup file not found: $file"
        return 1
    fi

    local file_size=$(stat -f%z "$file" 2>/dev/null || stat -c%s "$file" 2>/dev/null)
    if [[ $file_size -lt 100 ]]; then
        log_error "Backup file is suspiciously small: ${file_size} bytes"
        return 1
    fi

    log_info "Backup file validation: OK (${file_size} bytes)"
    return 0
}

find_backup_file() {
    local type="$1"
    local from="$2"
    local extension=""

    case "$type" in
        aof)
            extension="aof"
            ;;
        rdb)
            extension="rdb"
            ;;
        *)
            log_error "Unknown backup type: $type"
            return 1
            ;;
    esac

    case "$from" in
        latest)
            log_info "Finding latest backup..."
            find "$BACKUP_DIR" -name "*redis*${extension}*" 2>/dev/null | sort -r | head -1
            return 0
            ;;

        daily)
            log_info "Finding latest daily backup..."
            find "$BACKUP_DIR/daily" -name "*redis*${extension}*" 2>/dev/null | sort -r | head -1
            return 0
            ;;

        weekly)
            log_info "Finding latest weekly backup..."
            find "$BACKUP_DIR/weekly" -name "*redis*${extension}*" 2>/dev/null | sort -r | head -1
            return 0
            ;;

        monthly)
            log_info "Finding latest monthly backup..."
            find "$BACKUP_DIR/monthly" -name "*redis*${extension}*" 2>/dev/null | sort -r | head -1
            return 0
            ;;

        *)
            # Treat as date
            log_info "Finding backup from: $from..."
            find "$BACKUP_DIR" -name "*redis*${from}*${extension}*" 2>/dev/null | head -1
            return 0
            ;;
    esac

    return 1
}

################################################################################
# AOF RESTORE
################################################################################

restore_aof() {
    print_header "REDIS AOF RESTORE"

    log_info "Restore Type: AOF (Append-Only File)"

    # Step 1: Locate backup file
    log_info "Step 1: Locating AOF backup..."

    if [[ -n "$BACKUP_FILE" ]]; then
        if ! validate_backup_file "$BACKUP_FILE"; then
            return 1
        fi
    else
        BACKUP_FILE=$(find_backup_file "aof" "$RESTORE_FROM")
        if [[ -z "$BACKUP_FILE" ]] || [[ ! -f "$BACKUP_FILE" ]]; then
            log_error "Could not find AOF backup matching: $RESTORE_FROM"
            return 1
        fi
    fi

    log_success "Found AOF backup: $BACKUP_FILE"

    # Step 2: Verify backup integrity
    if [[ "$SKIP_VERIFICATION" != "true" ]]; then
        log_info "Step 2: Verifying backup integrity..."

        if file "$BACKUP_FILE" | grep -q "text"; then
            log_success "AOF file format verified"
        elif file "$BACKUP_FILE" | grep -q "gzip"; then
            print_progress "Verifying gzip integrity..."
            if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
                log_error "AOF file gzip test failed"
                return 1
            fi
            log_success "Gzip integrity verified"
        fi
    fi

    # Step 3: Stop Redis
    log_info "Step 3: Stopping Redis..."

    if ! docker-compose -f "$COMPOSE_FILE" stop redis; then
        log_error "Failed to stop Redis"
        return 1
    fi

    sleep 5
    log_success "Redis stopped"

    # Step 4: Backup current AOF
    log_info "Step 4: Backing up current AOF..."

    local redis_data_path="/var/lib/docker/volumes/${REDIS_CONTAINER%%-*}_redis_data/_data"
    local aof_file="${redis_data_path}/appendonly.aof"

    if [[ -f "$aof_file" ]]; then
        local backup_aof="${BACKUP_DIR}/pre-restore-aof-${RESTORE_TIMESTAMP}.bak"
        if cp "$aof_file" "$backup_aof"; then
            log_success "Current AOF backed up to: $backup_aof"
        fi
    fi

    # Step 5: Restore AOF file
    log_info "Step 5: Restoring AOF file..."

    if file "$BACKUP_FILE" | grep -q "gzip"; then
        print_progress "Decompressing AOF..."
        gunzip < "$BACKUP_FILE" > "$aof_file"
    else
        print_progress "Copying AOF..."
        cp "$BACKUP_FILE" "$aof_file"
    fi

    if [[ -f "$aof_file" ]]; then
        chmod 644 "$aof_file"
        log_success "AOF file restored"
    else
        log_error "Failed to restore AOF file"
        return 1
    fi

    # Step 6: Start Redis (will replay AOF)
    log_info "Step 6: Starting Redis (will replay AOF)..."

    if ! docker-compose -f "$COMPOSE_FILE" up -d redis; then
        log_error "Failed to start Redis"
        return 1
    fi

    # Wait for Redis to start and replay AOF
    print_progress "Waiting for Redis to replay AOF..."
    sleep 15

    # Verify by checking Redis is responding
    if check_redis_running; then
        log_success "Redis started and AOF replayed"
    else
        log_error "Redis failed to start after AOF restore"
        return 1
    fi

    # Step 7: Verify data
    log_info "Step 7: Verifying restored data..."

    local key_count=$(docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" DBSIZE | grep keys | awk '{print $2}' || echo "0")

    if [[ $key_count -gt 0 ]]; then
        log_success "Data verified: $key_count keys"
    else
        log_warn "No keys found in restored Redis (may be expected if cache was empty)"
    fi

    RESTORE_SUCCESS=true
    return 0
}

################################################################################
# RDB RESTORE
################################################################################

restore_rdb() {
    print_header "REDIS RDB RESTORE"

    log_info "Restore Type: RDB (Snapshot)"

    # Step 1: Locate backup file
    log_info "Step 1: Locating RDB backup..."

    if [[ -n "$BACKUP_FILE" ]]; then
        if ! validate_backup_file "$BACKUP_FILE"; then
            return 1
        fi
    else
        BACKUP_FILE=$(find_backup_file "rdb" "$RESTORE_FROM")
        if [[ -z "$BACKUP_FILE" ]] || [[ ! -f "$BACKUP_FILE" ]]; then
            log_error "Could not find RDB backup matching: $RESTORE_FROM"
            return 1
        fi
    fi

    log_success "Found RDB backup: $BACKUP_FILE"

    # Step 2: Stop Redis
    log_info "Step 2: Stopping Redis..."

    if ! docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" SHUTDOWN SAVE; then
        log_warn "Could not gracefully shutdown Redis"
        docker-compose -f "$COMPOSE_FILE" stop redis || true
    fi

    sleep 5
    log_success "Redis stopped"

    # Step 3: Backup current RDB
    log_info "Step 3: Backing up current RDB..."

    local redis_data_path="/var/lib/docker/volumes/${REDIS_CONTAINER%%-*}_redis_data/_data"
    local rdb_file="${redis_data_path}/dump.rdb"

    if [[ -f "$rdb_file" ]]; then
        local backup_rdb="${BACKUP_DIR}/pre-restore-rdb-${RESTORE_TIMESTAMP}.bak"
        if cp "$rdb_file" "$backup_rdb"; then
            log_success "Current RDB backed up to: $backup_rdb"
        fi
    fi

    # Step 4: Restore RDB file
    log_info "Step 4: Restoring RDB file..."

    if file "$BACKUP_FILE" | grep -q "gzip"; then
        print_progress "Decompressing RDB..."
        gunzip < "$BACKUP_FILE" > "$rdb_file"
    else
        print_progress "Copying RDB..."
        cp "$BACKUP_FILE" "$rdb_file"
    fi

    if [[ -f "$rdb_file" ]]; then
        chmod 644 "$rdb_file"
        log_success "RDB file restored"
    else
        log_error "Failed to restore RDB file"
        return 1
    fi

    # Step 5: Start Redis
    log_info "Step 5: Starting Redis..."

    if ! docker-compose -f "$COMPOSE_FILE" up -d redis; then
        log_error "Failed to start Redis"
        return 1
    fi

    print_progress "Waiting for Redis to load snapshot..."
    sleep 10

    if check_redis_running; then
        log_success "Redis started and snapshot loaded"
    else
        log_error "Redis failed to start after RDB restore"
        return 1
    fi

    # Step 6: Verify data
    log_info "Step 6: Verifying restored data..."

    local key_count=$(docker-compose -f "$COMPOSE_FILE" exec -T redis \
      redis-cli -a "$REDIS_PASSWORD" DBSIZE | grep keys | awk '{print $2}' || echo "0")

    if [[ $key_count -gt 0 ]]; then
        log_success "Data verified: $key_count keys"
    else
        log_warn "No keys found in restored Redis (may be expected if cache was empty)"
    fi

    RESTORE_SUCCESS=true
    return 0
}

################################################################################
# S3 RESTORE
################################################################################

restore_s3() {
    print_header "REDIS S3 RESTORE"

    log_info "Restore Type: From AWS S3"

    # Check AWS CLI is available
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI not found"
        return 1
    fi

    # Step 1: Download from S3
    log_info "Step 1: Downloading backup from S3..."

    local s3_path="${S3_BACKUP_BUCKET:-backup-bucket}/redis/"
    local local_backup="/tmp/redis_backup_${RESTORE_TIMESTAMP}.rdb.gz"

    print_progress "Downloading from s3://${s3_path}"

    if ! aws s3 cp "s3://${s3_path}latest.rdb.gz" "$local_backup" \
      --region "${AWS_REGION:-us-west-2}"; then
        log_error "Failed to download from S3"
        return 1
    fi

    log_success "Downloaded to: $local_backup"

    # Step 2: Restore from downloaded file
    log_info "Step 2: Restoring from downloaded backup..."

    BACKUP_FILE="$local_backup"

    if restore_rdb; then
        # Cleanup
        rm -f "$local_backup"
        RESTORE_SUCCESS=true
        return 0
    else
        log_error "Failed to restore from S3 backup"
        return 1
    fi
}

################################################################################
# RESTORE REPORT
################################################################################

show_restore_report() {
    print_header "RESTORE REPORT"

    local restore_duration=$(($(date +%s) - RESTORE_START_TIME))

    echo "Restore ID: $RESTORE_TIMESTAMP"
    echo "Type: $RESTORE_TYPE"
    echo "From: $RESTORE_FROM"
    echo "Duration: ${restore_duration} seconds"
    echo ""

    if [[ "$RESTORE_SUCCESS" == "true" ]]; then
        echo -e "${GREEN}RESTORE STATUS: SUCCESS${NC}"

        if check_redis_running; then
            echo -e "${GREEN}Redis Status: RUNNING${NC}"
        else
            echo -e "${YELLOW}Redis Status: NOT RESPONDING${NC}"
        fi
    else
        echo -e "${RED}RESTORE STATUS: FAILED${NC}"
    fi

    echo ""
    echo "Log file: $RESTORE_LOG"

    if [[ -n "$BACKUP_FILE" ]]; then
        echo "Backup used: $BACKUP_FILE"
    fi

    return $([ "$RESTORE_SUCCESS" = "true" ] && echo 0 || echo 1)
}

################################################################################
# MAIN
################################################################################

main() {
    print_header "REDIS RESTORE UTILITY"

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

    # Validate restore type
    case "$RESTORE_TYPE" in
        aof|rdb|s3)
            ;;
        *)
            log_error "Invalid restore type: $RESTORE_TYPE"
            exit 1
            ;;
    esac

    # Execute restore
    case "$RESTORE_TYPE" in
        aof)
            restore_aof || exit 1
            ;;
        rdb)
            restore_rdb || exit 1
            ;;
        s3)
            restore_s3 || exit 1
            ;;
    esac

    # Show report
    show_restore_report
    exit $?
}

main "$@"
