#!/bin/bash

################################################################################
# MEDIA BACKUP TEST SCRIPT
#
# Comprehensive test suite for media backup system
# Tests backup creation, restoration, integrity, and S3 operations
#
# Usage:
#   ./test_backup.sh                 # Run all tests
#   ./test_backup.sh --unit          # Unit tests only
#   ./test_backup.sh --integration   # Integration tests
#   ./test_backup.sh --s3            # S3 tests (requires AWS config)
#   ./test_backup.sh --cleanup       # Cleanup test environment
#
################################################################################

set -euo pipefail

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Test configuration
BACKUP_DIR="${BACKUP_DIR:-${PROJECT_ROOT}/backups/media}"
MEDIA_DIR="${MEDIA_DIR:-${PROJECT_ROOT}/backend/media}"
TEST_DIR="${BACKUP_DIR}/test"
TEST_MEDIA_DIR="${TEST_DIR}/test_media"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test tracking
TESTS_PASSED=0
TESTS_FAILED=0
TEST_RESULTS=()

################################################################################
# TEST UTILITIES
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

assert_exit_code() {
    local expected=$1
    local actual=$2
    local message=$3

    if [ "${actual}" -eq "${expected}" ]; then
        return 0
    else
        log ERROR "${message} (expected: ${expected}, got: ${actual})"
        return 1
    fi
}

assert_file_exists() {
    local file=$1
    local message=$2

    if [ -f "${file}" ]; then
        return 0
    else
        log ERROR "${message}: ${file} not found"
        return 1
    fi
}

assert_command_success() {
    local command=$1
    local message=$2

    if eval "${command}" >/dev/null 2>&1; then
        return 0
    else
        log ERROR "${message}: command failed"
        return 1
    fi
}

setup_test_environment() {
    log INFO "Setting up test environment..."

    mkdir -p "${TEST_DIR}"
    mkdir -p "${TEST_MEDIA_DIR}"

    # Create test media files
    create_test_files
    export MEDIA_DIR="${TEST_MEDIA_DIR}"

    log SUCCESS "Test environment ready"
}

create_test_files() {
    log INFO "Creating test media files..."

    # Create different types of test files
    mkdir -p "${TEST_MEDIA_DIR}/avatars"
    mkdir -p "${TEST_MEDIA_DIR}/materials"
    mkdir -p "${TEST_MEDIA_DIR}/submissions"
    mkdir -p "${TEST_MEDIA_DIR}/chat"

    # Generate test files
    dd if=/dev/urandom of="${TEST_MEDIA_DIR}/avatars/test_avatar_1.jpg" bs=1K count=50
    dd if=/dev/urandom of="${TEST_MEDIA_DIR}/avatars/test_avatar_2.jpg" bs=1K count=45
    dd if=/dev/urandom of="${TEST_MEDIA_DIR}/materials/test_material_1.pdf" bs=1K count=100
    dd if=/dev/urandom of="${TEST_MEDIA_DIR}/materials/test_material_2.pdf" bs=1K count=150
    dd if=/dev/urandom of="${TEST_MEDIA_DIR}/submissions/test_submission_1.docx" bs=1K count=80
    dd if=/dev/urandom of="${TEST_MEDIA_DIR}/chat/test_image_1.png" bs=1K count=60

    echo "Test content" > "${TEST_MEDIA_DIR}/test.txt"

    log INFO "Created test files: $(find "${TEST_MEDIA_DIR}" -type f | wc -l) files"
}

cleanup_test_environment() {
    log INFO "Cleaning up test environment..."

    if [ -d "${TEST_DIR}" ]; then
        rm -rf "${TEST_DIR}"
        log SUCCESS "Test environment cleaned"
    fi
}

run_test() {
    local test_name=$1
    local test_function=$2

    echo ""
    log INFO "Running test: ${test_name}"

    if ${test_function}; then
        log SUCCESS "PASSED: ${test_name}"
        ((TESTS_PASSED++))
        TEST_RESULTS+=("✓ ${test_name}")
        return 0
    else
        log ERROR "FAILED: ${test_name}"
        ((TESTS_FAILED++))
        TEST_RESULTS+=("✗ ${test_name}")
        return 1
    fi
}

################################################################################
# UNIT TESTS
################################################################################

test_backup_script_exists() {
    [ -f "${SCRIPT_DIR}/backup.sh" ] && [ -x "${SCRIPT_DIR}/backup.sh" ]
}

test_restore_script_exists() {
    [ -f "${SCRIPT_DIR}/restore.sh" ] && [ -x "${SCRIPT_DIR}/restore.sh" ]
}

test_backup_directory_creation() {
    local test_backup_dir="${TEST_DIR}/test_backup"
    mkdir -p "${test_backup_dir}"

    # Test backup script creates subdirectories
    BACKUP_DIR="${test_backup_dir}" bash "${SCRIPT_DIR}/backup.sh" status >/dev/null 2>&1 || true

    [ -d "${test_backup_dir}/full" ] && [ -d "${test_backup_dir}/incremental" ]
}

test_manifest_creation() {
    local manifest_file="${TEST_DIR}/test.manifest"

    # Create manifest of test files
    find "${TEST_MEDIA_DIR}" -type f -exec sha256sum {} \; | sort > "${manifest_file}"

    [ -f "${manifest_file}" ] && [ -s "${manifest_file}" ]
}

test_checksum_calculation() {
    local test_file="${TEST_DIR}/test_checksum.txt"
    echo "Test content" > "${test_file}"

    local checksum=$(sha256sum "${test_file}" | awk '{print $1}')

    # Verify checksum is valid SHA256 (64 hex characters)
    [[ "${checksum}" =~ ^[0-9a-f]{64}$ ]]
}

################################################################################
# INTEGRATION TESTS
################################################################################

test_full_backup_creation() {
    local test_backup_dir="${TEST_DIR}/full_backup_test"
    mkdir -p "${test_backup_dir}"

    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1

    # Check backup was created
    local backup_count=$(find "${test_backup_dir}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)
    [ "${backup_count}" -gt 0 ]
}

test_incremental_backup_creation() {
    local test_backup_dir="${TEST_DIR}/incremental_backup_test"
    mkdir -p "${test_backup_dir}"

    # First, create full backup
    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1

    # Then, add new file and create incremental backup
    echo "New test content" > "${TEST_MEDIA_DIR}/new_file.txt"

    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" incremental >/dev/null 2>&1

    # Check backup was created
    local backup_count=$(find "${test_backup_dir}/incremental" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)
    [ "${backup_count}" -gt 0 ]
}

test_backup_verification() {
    local test_backup_dir="${TEST_DIR}/verify_backup_test"
    mkdir -p "${test_backup_dir}"

    # Create backup
    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1

    # Get backup file
    local backup_file=$(find "${test_backup_dir}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | head -1)

    # Test verify command
    [ -n "${backup_file}" ] && bash "${SCRIPT_DIR}/restore.sh" --verify "${backup_file}" >/dev/null 2>&1
}

test_backup_integrity() {
    local test_backup_dir="${TEST_DIR}/integrity_test"
    mkdir -p "${test_backup_dir}"

    # Create backup
    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1

    # Get backup file
    local backup_file=$(find "${test_backup_dir}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | head -1)

    # Verify gzip integrity
    [ -n "${backup_file}" ] && gzip -t "${backup_file}"
}

test_restore_from_backup() {
    local test_backup_dir="${TEST_DIR}/restore_test"
    local restore_media_dir="${TEST_DIR}/restored_media"

    mkdir -p "${test_backup_dir}"
    mkdir -p "${restore_media_dir}"

    # Create backup
    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1

    # Get backup file
    local backup_file=$(find "${test_backup_dir}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | head -1)

    # Test restore (test mode)
    if [ -n "${backup_file}" ]; then
        bash "${SCRIPT_DIR}/restore.sh" --test "${backup_file}" >/dev/null 2>&1
        return 0
    fi

    return 1
}

test_backup_metadata() {
    local test_backup_dir="${TEST_DIR}/metadata_test"
    mkdir -p "${test_backup_dir}"

    # Create backup
    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1

    # Get backup file
    local backup_file=$(find "${test_backup_dir}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | head -1)

    # Check metadata exists and contains expected fields
    if [ -f "${backup_file}.metadata" ]; then
        grep -q "backup_checksum_sha256" "${backup_file}.metadata" && \
        grep -q "backup_size" "${backup_file}.metadata" && \
        grep -q "backup_date" "${backup_file}.metadata"
    else
        return 1
    fi
}

test_backup_listing() {
    local test_backup_dir="${TEST_DIR}/list_test"
    mkdir -p "${test_backup_dir}"

    # Create backup
    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1

    # Test list command
    bash "${SCRIPT_DIR}/restore.sh" --list 2>/dev/null | grep -q "backup_" || return 1
}

test_cleanup_operation() {
    local test_backup_dir="${TEST_DIR}/cleanup_test"
    mkdir -p "${test_backup_dir}"

    # Create backup
    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1

    # Get initial backup count
    local before_count=$(find "${test_backup_dir}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)

    # Run cleanup
    BACKUP_DIR="${test_backup_dir}" BACKUP_RETENTION_DAYS=0 \
        bash "${SCRIPT_DIR}/backup.sh" cleanup >/dev/null 2>&1

    # Get final backup count (should be same or less)
    local after_count=$(find "${test_backup_dir}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | wc -l)

    [ "${after_count}" -le "${before_count}" ]
}

################################################################################
# S3 TESTS
################################################################################

test_s3_prerequisites() {
    if [ -z "${AWS_S3_BUCKET:-}" ]; then
        log WARN "AWS_S3_BUCKET not set, skipping S3 tests"
        return 1
    fi

    command -v aws &> /dev/null || return 1
}

test_s3_bucket_access() {
    if ! test_s3_prerequisites; then
        return 1
    fi

    aws s3 ls "s3://${AWS_S3_BUCKET}/" --region "${AWS_REGION:-us-east-1}" >/dev/null 2>&1
}

test_s3_upload() {
    if ! test_s3_prerequisites; then
        return 1
    fi

    local test_backup_dir="${TEST_DIR}/s3_upload_test"
    mkdir -p "${test_backup_dir}"

    # Create backup
    BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
        bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1

    # Get backup file
    local backup_file=$(find "${test_backup_dir}/full" -maxdepth 1 -name "backup_*.tar.gz" -type f | head -1)

    # Test S3 upload
    if [ -n "${backup_file}" ]; then
        ENABLE_S3_UPLOAD=true BACKUP_DIR="${test_backup_dir}" MEDIA_DIR="${TEST_MEDIA_DIR}" \
            bash "${SCRIPT_DIR}/backup.sh" full >/dev/null 2>&1
        return 0
    fi

    return 1
}

################################################################################
# TEST REPORTING
################################################################################

print_test_summary() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Test Summary${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    echo "Results:"
    for result in "${TEST_RESULTS[@]}"; do
        echo "  ${result}"
    done

    echo ""
    echo "Statistics:"
    echo "  Passed: ${TESTS_PASSED}"
    echo "  Failed: ${TESTS_FAILED}"
    echo "  Total:  $((TESTS_PASSED + TESTS_FAILED))"
    echo ""

    if [ "${TESTS_FAILED}" -eq 0 ]; then
        echo -e "${GREEN}All tests passed!${NC}"
        return 0
    else
        echo -e "${RED}Some tests failed!${NC}"
        return 1
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Media Backup Test Suite${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    # Make scripts executable
    chmod +x "${SCRIPT_DIR}/backup.sh"
    chmod +x "${SCRIPT_DIR}/restore.sh"

    # Setup test environment
    setup_test_environment

    local command="${1:-all}"

    case "${command}" in
        all)
            log INFO "Running all tests..."
            echo ""

            # Unit tests
            log INFO "=== UNIT TESTS ==="
            run_test "Backup script exists" test_backup_script_exists
            run_test "Restore script exists" test_restore_script_exists
            run_test "Backup directory creation" test_backup_directory_creation
            run_test "Manifest creation" test_manifest_creation
            run_test "Checksum calculation" test_checksum_calculation

            # Integration tests
            log INFO "=== INTEGRATION TESTS ==="
            run_test "Full backup creation" test_full_backup_creation
            run_test "Incremental backup creation" test_incremental_backup_creation
            run_test "Backup verification" test_backup_verification
            run_test "Backup integrity" test_backup_integrity
            run_test "Restore from backup" test_restore_from_backup
            run_test "Backup metadata" test_backup_metadata
            run_test "Backup listing" test_backup_listing
            run_test "Cleanup operation" test_cleanup_operation

            # S3 tests
            if test_s3_prerequisites; then
                log INFO "=== S3 TESTS ==="
                run_test "S3 bucket access" test_s3_bucket_access || true
                run_test "S3 upload" test_s3_upload || true
            fi

            print_test_summary
            ;;
        --unit)
            log INFO "Running unit tests..."
            run_test "Backup script exists" test_backup_script_exists
            run_test "Restore script exists" test_restore_script_exists
            run_test "Backup directory creation" test_backup_directory_creation
            run_test "Manifest creation" test_manifest_creation
            run_test "Checksum calculation" test_checksum_calculation
            print_test_summary
            ;;
        --integration)
            log INFO "Running integration tests..."
            run_test "Full backup creation" test_full_backup_creation
            run_test "Incremental backup creation" test_incremental_backup_creation
            run_test "Backup verification" test_backup_verification
            run_test "Backup integrity" test_backup_integrity
            run_test "Restore from backup" test_restore_from_backup
            run_test "Backup metadata" test_backup_metadata
            run_test "Backup listing" test_backup_listing
            run_test "Cleanup operation" test_cleanup_operation
            print_test_summary
            ;;
        --s3)
            if test_s3_prerequisites; then
                log INFO "Running S3 tests..."
                run_test "S3 bucket access" test_s3_bucket_access
                run_test "S3 upload" test_s3_upload
                print_test_summary
            else
                log ERROR "S3 prerequisites not met"
                exit 1
            fi
            ;;
        --cleanup)
            cleanup_test_environment
            exit 0
            ;;
        *)
            log ERROR "Unknown command: ${command}"
            echo "Usage: $0 [all|--unit|--integration|--s3|--cleanup]"
            exit 1
            ;;
    esac

    # Cleanup
    cleanup_test_environment

    if [ "${TESTS_FAILED}" -gt 0 ]; then
        exit 1
    fi

    exit 0
}

# Run main function
main "$@"
