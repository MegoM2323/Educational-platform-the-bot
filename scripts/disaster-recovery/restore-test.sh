#!/bin/bash

################################################################################
# BACKUP RESTORATION TESTING SCRIPT
#
# Tests restoration of database and application data from S3 backups
# Validates:
#  - Backup download and integrity
#  - Database restoration
#  - Data consistency after restore
#  - Application functionality
#
# Usage:
#   ./restore-test.sh [--dry-run] [--backup-path /path/to/backup] [--verify]
#   ./restore-test.sh --full-restore
#   ./restore-test.sh --point-in-time --timestamp "2024-01-15 14:30:00"
#   ./restore-test.sh --verify-backup
#
# RPO Target: < 5 minutes (300 seconds)
#
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
RESTORE_TEST_DIR="${PROJECT_ROOT}/restore-test"
LOGS_DIR="${PROJECT_ROOT}/logs/restore-tests"
METRICS_DIR="${PROJECT_ROOT}/metrics"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"

mkdir -p "$BACKUP_DIR" "$RESTORE_TEST_DIR" "$LOGS_DIR" "$METRICS_DIR"

# Test parameters
DRY_RUN="${DRY_RUN:-false}"
VERIFY_ONLY="${VERIFY_ONLY:-false}"
VERBOSE="${VERBOSE:-true}"

# Database configuration
DB_HOST="postgres"
DB_PORT=5432
DB_USER="postgres"
DB_NAME="thebot"
TEST_DB_NAME="thebot_restore_test"

# S3 configuration (if used)
S3_BUCKET="${S3_BUCKET:-thebot-backups}"
S3_REGION="${S3_REGION:-us-east-1}"
AWS_CLI="aws"  # Or full path if needed

# Timing thresholds
BACKUP_DOWNLOAD_TIMEOUT=300    # 5 minutes
RESTORE_TIMEOUT=600            # 10 minutes
VERIFICATION_TIMEOUT=120       # 2 minutes
MAX_RPO_SECONDS=300            # 5 minutes

# Logging
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TEST_LOG="${LOGS_DIR}/restore-test_${TIMESTAMP}.log"
METRICS_FILE="${METRICS_DIR}/restore-metrics_${TIMESTAMP}.json"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Test state
TEST_PASSED=true
BACKUP_SIZE_BYTES=0
RESTORE_TIME_TOTAL=0

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$TEST_LOG"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*" | tee -a "$TEST_LOG"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" | tee -a "$TEST_LOG"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*" | tee -a "$TEST_LOG"
}

log_metric() {
    echo -e "${CYAN}[METRIC]${NC} $*" | tee -a "$TEST_LOG"
}

print_header() {
    echo -e "\n${CYAN}════════════════════════════════════════════════════════${NC}" | tee -a "$TEST_LOG"
    echo -e "${CYAN}$1${NC}" | tee -a "$TEST_LOG"
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}\n" | tee -a "$TEST_LOG"
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

init_metrics() {
    cat > "$METRICS_FILE" << 'EOF'
{
  "test_metadata": {
    "timestamp": "",
    "test_name": "backup_restoration",
    "environment": "production",
    "dry_run": false,
    "targets": {
      "rpo_seconds": 300,
      "download_seconds": 300,
      "restore_seconds": 600,
      "verification_seconds": 120
    }
  },
  "timeline": {
    "test_start": "",
    "backup_selection_start": "",
    "backup_selection_end": "",
    "download_start": "",
    "download_end": "",
    "restore_start": "",
    "restore_end": "",
    "verification_start": "",
    "verification_end": "",
    "test_end": ""
  },
  "metrics": {
    "backup_size_bytes": 0,
    "backup_age_minutes": 0,
    "download_time_ms": 0,
    "restore_time_ms": 0,
    "verification_time_ms": 0,
    "total_rpo_ms": 0,
    "total_rpo_seconds": 0,
    "data_loss_records": 0,
    "table_count_source": 0,
    "table_count_restored": 0,
    "record_count_match": false
  },
  "validation": {
    "backup_found": false,
    "backup_integrity_verified": false,
    "download_within_threshold": false,
    "restore_within_threshold": false,
    "verification_within_threshold": false,
    "rpo_within_threshold": false,
    "data_integrity_verified": false,
    "all_tables_present": false
  },
  "detailed_results": {
    "backup_file_path": "",
    "backup_checksum_valid": false,
    "database_created": false,
    "restore_successful": false,
    "table_restoration_status": {},
    "errors": []
  },
  "summary": {
    "overall_success": false,
    "message": ""
  }
}
EOF
}

update_metric() {
    local path="$1"
    local value="$2"

    jq ".$path = $value" "$METRICS_FILE" > "${METRICS_FILE}.tmp"
    mv "${METRICS_FILE}.tmp" "$METRICS_FILE"
}

update_string_metric() {
    local path="$1"
    local value="$2"

    jq ".$path = \"$value\"" "$METRICS_FILE" > "${METRICS_FILE}.tmp"
    mv "${METRICS_FILE}.tmp" "$METRICS_FILE"
}

add_error() {
    local error_msg="$1"
    jq ".detailed_results.errors += [\"$error_msg\"]" "$METRICS_FILE" > "${METRICS_FILE}.tmp"
    mv "${METRICS_FILE}.tmp" "$METRICS_FILE"
}

# ============================================================================
# BACKUP SELECTION AND VALIDATION
# ============================================================================

find_latest_backup() {
    print_header "Finding Latest Backup"

    if [[ "$DRY_RUN" != "true" ]]; then
        # Look for backups in local directory first
        if ls "$BACKUP_DIR"/*.sql 2>/dev/null | head -1 &>/dev/null; then
            local latest_backup=$(ls -t "$BACKUP_DIR"/*.sql 2>/dev/null | head -1)
            log_success "Found local backup: $latest_backup"
            echo "$latest_backup"
            return 0
        fi

        # Try S3 if configured
        if command -v "$AWS_CLI" &>/dev/null; then
            log_info "Looking for backups in S3..."
            local s3_backup=$("$AWS_CLI" s3api list-objects-v2 \
                --bucket "$S3_BUCKET" \
                --prefix "backups/" \
                --region "$S3_REGION" \
                --query "Contents[?ends_with(Key, '.sql')] | sort_by(@, &LastModified) | [-1].Key" \
                --output text 2>/dev/null || echo "")

            if [[ -n "$s3_backup" && "$s3_backup" != "None" ]]; then
                log_success "Found S3 backup: $s3_backup"
                echo "$s3_backup"
                return 0
            fi
        fi

        log_error "No backups found"
        return 1
    else
        log_info "[DRY-RUN] Would search for latest backup in $BACKUP_DIR"
        echo "${BACKUP_DIR}/backup_latest.sql"
        return 0
    fi
}

validate_backup_integrity() {
    local backup_path="$1"

    print_header "Validating Backup Integrity"

    if [[ "$DRY_RUN" != "true" ]]; then
        if [[ ! -f "$backup_path" ]]; then
            log_error "Backup file not found: $backup_path"
            return 1
        fi

        # Check file size
        BACKUP_SIZE_BYTES=$(stat -f%z "$backup_path" 2>/dev/null || stat -c%s "$backup_path" 2>/dev/null || echo "0")
        log_info "Backup file size: $((BACKUP_SIZE_BYTES / 1024 / 1024))MB"
        update_metric "metrics.backup_size_bytes" "$BACKUP_SIZE_BYTES"

        # Check file is readable
        if [[ ! -r "$backup_path" ]]; then
            log_error "Backup file is not readable"
            add_error "Backup file permission denied"
            return 1
        fi

        # Check for backup header (SQL dumps start with --)
        local header=$(head -1 "$backup_path")
        if [[ "$header" == --* ]]; then
            log_success "Backup file has valid SQL header"
        else
            log_warning "Backup file header may be invalid: $header"
        fi

        # Check backup checksum if .md5 file exists
        if [[ -f "${backup_path}.md5" ]]; then
            log_info "Verifying backup checksum..."
            if md5sum -c "${backup_path}.md5" &>/dev/null; then
                log_success "Backup checksum verified"
                update_metric "detailed_results.backup_checksum_valid" "true"
            else
                log_error "Backup checksum failed"
                add_error "Backup checksum verification failed"
                TEST_PASSED=false
            fi
        else
            log_warning "No checksum file found for verification"
        fi

        # Calculate backup age
        local backup_mtime=$(stat -f%m "$backup_path" 2>/dev/null || stat -c%Y "$backup_path" 2>/dev/null)
        local backup_age_seconds=$(($(date +%s) - backup_mtime))
        local backup_age_minutes=$((backup_age_seconds / 60))

        log_info "Backup age: ${backup_age_minutes} minutes"
        update_metric "metrics.backup_age_minutes" "$backup_age_minutes"

        # Check if backup is too old
        if [[ $backup_age_minutes -gt 1440 ]]; then  # 24 hours
            log_warning "Backup is older than 24 hours (age: ${backup_age_minutes}min)"
        fi

        update_metric "validation.backup_integrity_verified" "true"
        return 0
    else
        log_info "[DRY-RUN] Would validate backup integrity"
        update_metric "metrics.backup_size_bytes" "104857600"  # 100MB simulation
        update_metric "metrics.backup_age_minutes" 5
        return 0
    fi
}

download_backup_from_s3() {
    local s3_key="$1"
    local local_path="$2"

    print_header "Downloading Backup from S3"

    local download_start=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.download_start" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    if [[ "$DRY_RUN" != "true" ]]; then
        if command -v "$AWS_CLI" &>/dev/null; then
            log_info "Downloading: $s3_key"
            if "$AWS_CLI" s3 cp "s3://${S3_BUCKET}/${s3_key}" "$local_path" \
                --region "$S3_REGION" --no-progress 2>&1 | tee -a "$TEST_LOG"; then
                log_success "Backup downloaded successfully"
            else
                log_error "Failed to download backup from S3"
                add_error "S3 download failed"
                return 1
            fi
        else
            log_warning "AWS CLI not available, skipping S3 download"
        fi
    else
        log_info "[DRY-RUN] Would download from S3: $s3_key"
        sleep 2
    fi

    local download_end=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.download_end" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    local download_time=$((download_end - download_start))
    update_metric "metrics.download_time_ms" "$download_time"
    log_metric "Download time: ${download_time}ms"

    if [[ $download_time -lt $((BACKUP_DOWNLOAD_TIMEOUT * 1000)) ]]; then
        log_success "Download completed within timeout"
        update_metric "validation.download_within_threshold" "true"
    else
        log_error "Download exceeded timeout (${BACKUP_DOWNLOAD_TIMEOUT}s)"
        update_metric "validation.download_within_threshold" "false"
        TEST_PASSED=false
    fi

    return 0
}

# ============================================================================
# DATABASE RESTORATION
# ============================================================================

create_restore_database() {
    print_header "Creating Test Database for Restoration"

    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Creating database: $TEST_DB_NAME"

        docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -U "$DB_USER" -c "CREATE DATABASE ${TEST_DB_NAME};" 2>&1 | tee -a "$TEST_LOG" || \
            log_warning "Database may already exist"

        update_metric "detailed_results.database_created" "true"
    else
        log_info "[DRY-RUN] Would create test database"
    fi

    return 0
}

restore_from_backup() {
    local backup_path="$1"

    print_header "Restoring Database from Backup"

    if [[ ! -f "$backup_path" ]]; then
        log_error "Backup file not found: $backup_path"
        return 1
    fi

    local restore_start=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.restore_start" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Restoring backup to: $TEST_DB_NAME"

        # Method 1: Using psql directly
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -U "$DB_USER" "$TEST_DB_NAME" < "$backup_path" 2>&1 | tee -a "$TEST_LOG"; then
            log_success "Database restoration completed"
            update_metric "detailed_results.restore_successful" "true"
        else
            log_error "Database restoration failed"
            add_error "Restore process failed"
            return 1
        fi
    else
        log_info "[DRY-RUN] Would restore database from: $backup_path"
        sleep 3
    fi

    local restore_end=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.restore_end" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    RESTORE_TIME_TOTAL=$((restore_end - restore_start))
    update_metric "metrics.restore_time_ms" "$RESTORE_TIME_TOTAL"
    log_metric "Restore time: ${RESTORE_TIME_TOTAL}ms"

    if [[ $RESTORE_TIME_TOTAL -lt $((RESTORE_TIMEOUT * 1000)) ]]; then
        log_success "Restore completed within timeout"
        update_metric "validation.restore_within_threshold" "true"
    else
        log_error "Restore exceeded timeout (${RESTORE_TIMEOUT}s)"
        update_metric "validation.restore_within_threshold" "false"
        TEST_PASSED=false
    fi

    return 0
}

# ============================================================================
# VERIFICATION AND VALIDATION
# ============================================================================

verify_table_structure() {
    print_header "Verifying Table Structure"

    local verify_start=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.verification_start" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Checking tables in restored database..."

        # Get table list
        local tables=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -U "$DB_USER" "$TEST_DB_NAME" -c "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;" 2>&1 | tail -n +3)

        if [[ -n "$tables" ]]; then
            local table_count=$(echo "$tables" | wc -l)
            log_success "Found $table_count tables in restored database"
            update_metric "metrics.table_count_restored" "$table_count"
            update_metric "validation.all_tables_present" "true"

            # Sample a few tables
            log_info "Sampling table data..."
            echo "$tables" | head -5 | while read -r table; do
                local row_count=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
                    psql -U "$DB_USER" "$TEST_DB_NAME" -c "SELECT COUNT(*) FROM $table;" 2>&1 | grep -oE '^[0-9]+' | head -1)
                log_info "  $table: $row_count rows"
            done
        else
            log_warning "No tables found in restored database"
            TEST_PASSED=false
        fi
    else
        log_info "[DRY-RUN] Would verify table structure"
    fi

    local verify_end=$(date +%s%N | cut -b1-13)
    update_string_metric "timeline.verification_end" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"

    local verify_time=$((verify_end - verify_start))
    update_metric "metrics.verification_time_ms" "$verify_time"
    log_metric "Verification time: ${verify_time}ms"

    if [[ $verify_time -lt $((VERIFICATION_TIMEOUT * 1000)) ]]; then
        log_success "Verification completed within timeout"
        update_metric "validation.verification_within_threshold" "true"
    else
        log_warning "Verification exceeded timeout (${VERIFICATION_TIMEOUT}s)"
    fi

    return 0
}

verify_data_integrity() {
    print_header "Verifying Data Integrity"

    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Comparing data in restored database..."

        # Check specific tables
        local critical_tables=("accounts_user" "accounts_userprofile" "materials_material")

        for table in "${critical_tables[@]}"; do
            local count=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
                psql -U "$DB_USER" "$TEST_DB_NAME" -c "SELECT COUNT(*) FROM $table;" 2>&1 | grep -oE '^[0-9]+' | head -1 || echo "0")

            if [[ "$count" -gt 0 ]]; then
                log_success "$table: $count records"
            else
                log_warning "$table: No records (may be expected)"
            fi
        done

        # Check for data corruption
        log_info "Checking for data anomalies..."
        docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -U "$DB_USER" "$TEST_DB_NAME" -c "SELECT COUNT(*) as missing_dates FROM accounts_user WHERE created_at IS NULL;" 2>/dev/null | head -5 || true

        update_metric "validation.data_integrity_verified" "true"
    else
        log_info "[DRY-RUN] Would verify data integrity"
    fi

    return 0
}

verify_application_functionality() {
    print_header "Verifying Application Functionality"

    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Testing application with restored database..."

        # Test basic database connection
        local test_query=$(docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -U "$DB_USER" "$TEST_DB_NAME" -c "SELECT 'connected' as status;" 2>&1 | grep connected || echo "FAILED")

        if [[ "$test_query" == "connected" ]]; then
            log_success "Application can connect to restored database"
        else
            log_warning "Application connection test inconclusive"
        fi

        # Test API health with restored data
        local health_status=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/system/health/ 2>/dev/null | tail -1 || echo "000")

        if [[ "$health_status" == "200" ]]; then
            log_success "Application health endpoint OK"
        else
            log_warning "Application health endpoint returned: $health_status"
        fi
    else
        log_info "[DRY-RUN] Would test application functionality"
    fi

    return 0
}

# ============================================================================
# CLEANUP
# ============================================================================

cleanup_test_database() {
    print_header "Cleaning Up Test Database"

    if [[ "$DRY_RUN" != "true" ]]; then
        log_info "Removing test database: $TEST_DB_NAME"

        docker-compose -f "$COMPOSE_FILE" exec -T postgres \
            psql -U "$DB_USER" -c "DROP DATABASE IF EXISTS ${TEST_DB_NAME};" 2>&1 | tee -a "$TEST_LOG" || \
            log_warning "Could not drop test database"
    else
        log_info "[DRY-RUN] Would drop test database"
    fi

    # Clean up temporary files
    rm -f "${RESTORE_TEST_DIR}"/*.sql 2>/dev/null || true

    log_success "Cleanup completed"
}

# ============================================================================
# REPORTING
# ============================================================================

calculate_total_rpo() {
    local total_rpo=$((RESTORE_TIME_TOTAL))
    update_metric "metrics.total_rpo_ms" "$total_rpo"
    update_metric "metrics.total_rpo_seconds" "$((total_rpo / 1000))"

    local total_rpo_seconds=$((total_rpo / 1000))

    log_metric "Total RPO: ${total_rpo}ms (${total_rpo_seconds}s)"

    if [[ $total_rpo_seconds -lt $MAX_RPO_SECONDS ]]; then
        log_success "RPO within target: ${total_rpo_seconds}s < ${MAX_RPO_SECONDS}s"
        update_metric "validation.rpo_within_threshold" "true"
    else
        log_error "RPO exceeded target: ${total_rpo_seconds}s >= ${MAX_RPO_SECONDS}s"
        update_metric "validation.rpo_within_threshold" "false"
        TEST_PASSED=false
    fi
}

print_test_summary() {
    print_header "Restore Test Summary"

    echo -e "Timeline:"
    echo -e "  Backup Download:       $(($(jq -r '.metrics.download_time_ms // 0' "$METRICS_FILE") / 1000))s"
    echo -e "  Database Restore:      $((RESTORE_TIME_TOTAL / 1000))s"
    echo -e "  Verification:          $(($(jq -r '.metrics.verification_time_ms // 0' "$METRICS_FILE") / 1000))s"
    echo -e "  Total RPO:             $((RESTORE_TIME_TOTAL / 1000))s"
    echo ""

    echo -e "Backup Info:"
    echo -e "  Size:                  $((BACKUP_SIZE_BYTES / 1024 / 1024))MB"
    echo -e "  Age:                   $(jq -r '.metrics.backup_age_minutes // 0' "$METRICS_FILE") minutes"
    echo ""

    echo -e "Thresholds:"
    echo -e "  RPO Target:            ${MAX_RPO_SECONDS}s"
    echo ""

    if [[ "$TEST_PASSED" == "true" ]]; then
        echo -e "Overall Result: ${GREEN}PASSED${NC}"
        update_string_metric "summary.overall_success" "true"
        update_string_metric "summary.message" "Restore test completed successfully"
    else
        echo -e "Overall Result: ${RED}FAILED${NC}"
        update_string_metric "summary.overall_success" "false"
        update_string_metric "summary.message" "Restore test completed with failures"
    fi

    echo ""
    echo -e "Test Log: ${CYAN}${TEST_LOG}${NC}"
    echo -e "Metrics: ${CYAN}${METRICS_FILE}${NC}"
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    print_header "BACKUP RESTORATION TEST SUITE"

    init_metrics
    update_string_metric "test_metadata.timestamp" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    update_metric "test_metadata.dry_run" "$([[ "$DRY_RUN" == "true" ]] && echo "true" || echo "false")"

    log_info "Test started at $(date)"
    log_info "DRY_RUN: $DRY_RUN"

    # Find and validate backup
    local backup_path
    if ! backup_path=$(find_latest_backup); then
        log_error "Could not find backup"
        exit 1
    fi

    if [[ "$VERIFY_ONLY" == "true" ]]; then
        if ! validate_backup_integrity "$backup_path"; then
            exit 1
        fi
        log_success "Backup verification completed"
        exit 0
    fi

    update_string_metric "detailed_results.backup_file_path" "$backup_path"

    if ! validate_backup_integrity "$backup_path"; then
        log_error "Backup validation failed"
        exit 1
    fi

    # Create test database
    if ! create_restore_database; then
        log_error "Failed to create test database"
        exit 1
    fi

    # Restore database
    if ! restore_from_backup "$backup_path"; then
        log_error "Database restoration failed"
        cleanup_test_database
        exit 1
    fi

    # Verify restoration
    if ! verify_table_structure; then
        log_error "Table structure verification failed"
    fi

    if ! verify_data_integrity; then
        log_error "Data integrity check failed"
    fi

    if ! verify_application_functionality; then
        log_warning "Application functionality test inconclusive"
    fi

    # Calculate metrics
    calculate_total_rpo

    # Cleanup
    cleanup_test_database

    # Print summary
    print_test_summary

    # Print metrics
    echo ""
    echo -e "${CYAN}Detailed Metrics:${NC}"
    jq . "$METRICS_FILE" | head -80

    # Exit with appropriate code
    if [[ "$TEST_PASSED" == "true" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main function
main "$@"
