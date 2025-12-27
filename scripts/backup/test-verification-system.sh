#!/bin/bash

################################################################################
# BACKUP VERIFICATION SYSTEM TEST
#
# Quick test of backup verification system components
#
# Usage:
#   ./test-verification-system.sh
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

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

################################################################################
# TEST FUNCTIONS
################################################################################

test_case() {
    local name=$1
    echo -e "\n${BLUE}Testing: ${name}${NC}"
}

test_pass() {
    local message=$1
    echo -e "${GREEN}✓ PASSED${NC}: ${message}"
    ((TESTS_PASSED++)) || true
}

test_fail() {
    local message=$1
    echo -e "${RED}✗ FAILED${NC}: ${message}"
    ((TESTS_FAILED++)) || true
}

################################################################################
# TEST SUITE
################################################################################

test_scripts_exist() {
    test_case "Backup scripts existence"

    local scripts=(
        "verify-backup.sh"
        "restore-test.sh"
        "setup-cron.sh"
    )

    for script in "${scripts[@]}"; do
        local script_path="${SCRIPT_DIR}/${script}"

        if [ -f "${script_path}" ] && [ -x "${script_path}" ]; then
            test_pass "Script exists and is executable: ${script}"
        else
            test_fail "Script missing or not executable: ${script}"
        fi
    done
}

test_script_syntax() {
    test_case "Bash script syntax validation"

    local scripts=(
        "verify-backup.sh"
        "restore-test.sh"
        "setup-cron.sh"
    )

    for script in "${scripts[@]}"; do
        local script_path="${SCRIPT_DIR}/${script}"

        if bash -n "${script_path}" 2>/dev/null; then
            test_pass "Syntax valid: ${script}"
        else
            test_fail "Syntax error in: ${script}"
        fi
    done
}

test_django_command() {
    test_case "Django management command existence"

    local command_file="${PROJECT_ROOT}/backend/core/management/commands/verify_backup.py"

    if [ -f "${command_file}" ]; then
        test_pass "Management command file exists"
    else
        test_fail "Management command file not found"
        return
    fi

    # Check Python syntax
    if python -m py_compile "${command_file}" 2>/dev/null; then
        test_pass "Management command syntax valid"
    else
        test_fail "Management command has syntax errors"
    fi
}

test_test_files() {
    test_case "Test files existence"

    local test_files=(
        "tests/backup/test_backup_verification.py"
        "tests/backup/test_backup_integration.py"
        "tests/backup/__init__.py"
    )

    for test_file in "${test_files[@]}"; do
        local file_path="${PROJECT_ROOT}/${test_file}"

        if [ -f "${file_path}" ]; then
            test_pass "Test file exists: ${test_file}"
        else
            test_fail "Test file not found: ${test_file}"
        fi
    done
}

test_test_syntax() {
    test_case "Test files syntax validation"

    local test_files=(
        "tests/backup/test_backup_verification.py"
        "tests/backup/test_backup_integration.py"
    )

    for test_file in "${test_files[@]}"; do
        local file_path="${PROJECT_ROOT}/${test_file}"

        if python -m py_compile "${file_path}" 2>/dev/null; then
            test_pass "Syntax valid: ${test_file}"
        else
            test_fail "Syntax error in: ${test_file}"
        fi
    done
}

test_documentation() {
    test_case "Documentation existence"

    local doc_file="${PROJECT_ROOT}/docs/BACKUP_VERIFICATION.md"

    if [ -f "${doc_file}" ]; then
        test_pass "Documentation file exists"

        # Check for key sections
        local sections=(
            "Overview"
            "Installation"
            "Usage"
            "Scheduling"
            "Troubleshooting"
        )

        for section in "${sections[@]}"; do
            if grep -q "^## ${section}" "${doc_file}"; then
                test_pass "Documentation section found: ${section}"
            else
                test_fail "Documentation section missing: ${section}"
            fi
        done
    else
        test_fail "Documentation file not found"
    fi
}

test_directory_structure() {
    test_case "Directory structure"

    local dirs=(
        "scripts/backup"
        "backend/core/management/commands"
        "tests/backup"
        "docs"
    )

    for dir in "${dirs[@]}"; do
        local dir_path="${PROJECT_ROOT}/${dir}"

        if [ -d "${dir_path}" ]; then
            test_pass "Directory exists: ${dir}"
        else
            test_fail "Directory not found: ${dir}"
        fi
    done
}

test_environment_configuration() {
    test_case "Environment configuration"

    # Check if .env exists
    if [ -f "${PROJECT_ROOT}/.env" ]; then
        test_pass "Environment file exists: .env"

        # Check for backup-related variables (optional)
        if grep -q "BACKUP_DIR\|DATABASE_TYPE" "${PROJECT_ROOT}/.env"; then
            test_pass "Backup configuration found in .env"
        fi
    else
        test_fail "Environment file not found: .env"
    fi
}

test_integration() {
    test_case "Integration test - backup verifier imports"

    # Try to import the verifier class
    if python -c "
import sys
sys.path.insert(0, '${PROJECT_ROOT}/backend')
try:
    from core.management.commands.verify_backup import BackupVerifier
    print('Import successful')
    verifier = BackupVerifier()
    print('Instance created')
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
" 2>/dev/null | grep -q "Import successful"; then
        test_pass "Backup verifier can be imported"
    else
        test_fail "Failed to import backup verifier"
    fi
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}Backup Verification System Test${NC}"
    echo -e "${BLUE}================================${NC}"

    # Run all tests
    test_scripts_exist
    test_script_syntax
    test_django_command
    test_test_files
    test_test_syntax
    test_documentation
    test_directory_structure
    test_environment_configuration
    test_integration

    # Print summary
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}Test Summary${NC}"
    echo -e "${BLUE}================================${NC}"

    local total=$((TESTS_PASSED + TESTS_FAILED))
    local pass_rate=$((TESTS_PASSED * 100 / (total > 0 ? total : 1)))

    echo -e "Total Tests: ${total}"
    echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
    echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"
    echo -e "Pass Rate: ${pass_rate}%"
    echo ""

    if [ ${TESTS_FAILED} -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        echo ""
        echo "Next steps:"
        echo "1. Configure .env with backup settings"
        echo "2. Run: ./scripts/backup/setup-cron.sh"
        echo "3. Test: ./scripts/backup/verify-backup.sh --all"
        exit 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
