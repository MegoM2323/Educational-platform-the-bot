#!/bin/bash

################################################################################
# Deploy Script Unit Tests
#
# Tests deploy.sh functionality including:
# - Argument parsing
# - Configuration loading
# - Phase execution (dry-run mode)
# - Error handling
# - Exit codes
################################################################################

set -euo pipefail

# Test framework setup
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOY_ROOT="$PROJECT_ROOT/deploy"
DEPLOY_SCRIPT="$PROJECT_ROOT/deploy.sh"
LIB_DIR="$DEPLOY_ROOT/lib"

# Colors for test output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Test counters
TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

# Source shared library
source "$LIB_DIR/shared.sh" 2>/dev/null || {
    echo "ERROR: Shared library not found: $LIB_DIR/shared.sh"
    exit 1
}

# ===== TEST ASSERTION FUNCTIONS =====

# Global test result file
TEST_RESULTS_FILE="${TEST_RESULTS_FILE:-/tmp/test_results.log}"

test_pass() {
    local test_name="$1"
    echo "PASS: $test_name" | tee -a "$TEST_RESULTS_FILE"
}

test_fail() {
    local test_name="$1"
    echo "FAIL: $test_name" | tee -a "$TEST_RESULTS_FILE" >&2
}

test_skip() {
    local test_name="$1"
    echo "SKIP: $test_name" | tee -a "$TEST_RESULTS_FILE"
}

# ===== HELPER FUNCTIONS =====

assert_exit_code() {
    local expected="$1"
    local actual="$2"
    local test_name="$3"

    if [ "$actual" -eq "$expected" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name: expected exit code $expected, got $actual"
    fi
}

assert_file_exists() {
    local file="$1"
    local test_name="$2"

    if [ -f "$file" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name: file not found: $file"
    fi
}

assert_contains() {
    local haystack="$1"
    local needle="$2"
    local test_name="$3"

    if echo "$haystack" | grep -qF "$needle" 2>/dev/null; then
        test_pass "$test_name"
    else
        test_fail "$test_name: expected to find '$needle'"
    fi
}

assert_not_contains() {
    local haystack="$1"
    local needle="$2"
    local test_name="$3"

    if ! echo "$haystack" | grep -qF "$needle" 2>/dev/null; then
        test_pass "$test_name"
    else
        test_fail "$test_name: should not contain '$needle'"
    fi
}

# ===== TEST FUNCTIONS =====

test_deploy_script_exists() {
    local test_name="test_deploy_script_exists"
    TESTS_RUN=$((TESTS_RUN + 1))

    if [ -f "$DEPLOY_SCRIPT" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name"
    fi
}

test_deploy_script_executable() {
    local test_name="test_deploy_script_executable"
    TESTS_RUN=$((TESTS_RUN + 1))

    if [ -x "$DEPLOY_SCRIPT" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name"
    fi
}

test_config_file_exists() {
    local test_name="test_config_file_exists"
    TESTS_RUN=$((TESTS_RUN + 1))

    local config="$DEPLOY_ROOT/.env"
    assert_file_exists "$config" "$test_name"
}

test_shared_library_exists() {
    local test_name="test_shared_library_exists"
    TESTS_RUN=$((TESTS_RUN + 1))

    local lib="$LIB_DIR/shared.sh"
    assert_file_exists "$lib" "$test_name"
}

test_all_phase_scripts_exist() {
    local test_name="test_all_phase_scripts_exist"
    TESTS_RUN=$((TESTS_RUN + 1))

    local phases=("pre-checks" "backup" "sync" "migrate" "services" "health")
    local all_exist=true

    for phase in "${phases[@]}"; do
        if [ ! -f "$DEPLOY_ROOT/${phase}.sh" ]; then
            all_exist=false
            break
        fi
    done

    if [ "$all_exist" = true ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name: missing phase scripts"
    fi
}

test_deploy_help_flag() {
    local test_name="test_deploy_help_flag"
    TESTS_RUN=$((TESTS_RUN + 1))

    # Test help flag parsing in deploy.sh directly
    if grep -q "show_help()" "$DEPLOY_SCRIPT"; then
        test_pass "$test_name (show_help function)"
    else
        test_fail "$test_name (show_help function)"
    fi

    if grep -q "\-\-help" "$DEPLOY_SCRIPT"; then
        test_pass "$test_name (--help flag)"
    else
        test_fail "$test_name (--help flag)"
    fi
}

test_deploy_dry_run_creates_log() {
    local test_name="test_deploy_dry_run_creates_log"
    TESTS_RUN=$((TESTS_RUN + 1))

    # Create temporary logs directory if needed
    mkdir -p "$PROJECT_ROOT/logs"

    # Run deploy with --dry-run (skip if SSH fails)
    if timeout 5 ssh -o ConnectTimeout=2 mg@5.129.249.206 "echo OK" > /dev/null 2>&1; then
        $DEPLOY_SCRIPT --dry-run --force > /tmp/deploy_test.log 2>&1 || true

        # Check if log file was created
        local log_file=$(find "$PROJECT_ROOT/logs" -name "deploy_*.log" -type f 2>/dev/null | tail -1)
        if [ -n "$log_file" ] && [ -f "$log_file" ]; then
            test_pass "$test_name"
        else
            test_fail "$test_name: no log file created"
        fi
    else
        test_skip "$test_name: SSH connection unavailable"
    fi
}

test_deploy_logs_directory_created() {
    local test_name="test_deploy_logs_directory_created"
    TESTS_RUN=$((TESTS_RUN + 1))

    if [ -d "$PROJECT_ROOT/logs" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name: logs directory not created"
    fi
}

test_config_contains_required_vars() {
    local test_name="test_config_contains_required_vars"
    TESTS_RUN=$((TESTS_RUN + 1))

    local config="$DEPLOY_ROOT/.env"
    local required_vars=("PROD_SERVER" "PROD_HOME" "VENV_PATH" "BACKUP_DIR")
    local missing=false

    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$config"; then
            missing=true
            break
        fi
    done

    if [ "$missing" = false ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name: missing required variables"
    fi
}

test_phase_script_is_executable() {
    local test_name="test_phase_script_is_executable"
    TESTS_RUN=$((TESTS_RUN + 1))

    local phases=("pre-checks" "backup" "sync" "migrate" "services" "health")
    local all_executable=true

    for phase in "${phases[@]}"; do
        if [ ! -x "$DEPLOY_ROOT/${phase}.sh" ]; then
            all_executable=false
            break
        fi
    done

    if [ "$all_executable" = true ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name: not all phase scripts are executable"
    fi
}

test_check_ssh_function() {
    local test_name="test_check_ssh_function"
    TESTS_RUN=$((TESTS_RUN + 1))

    if grep -q "check_ssh_connection()" "$LIB_DIR/shared.sh"; then
        test_pass "$test_name"
    else
        test_fail "$test_name: check_ssh_connection function not found"
    fi
}

test_log_functions_exported() {
    local test_name="test_log_functions_exported"
    TESTS_RUN=$((TESTS_RUN + 1))

    local functions=("log_info" "log_success" "log_error" "log_warning" "log_section")
    local all_found=true

    for func in "${functions[@]}"; do
        if ! grep -q "export -f.*$func" "$LIB_DIR/shared.sh"; then
            all_found=false
            break
        fi
    done

    if [ "$all_found" = true ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name: log functions not exported"
    fi
}

test_dry_run_flag_parsed() {
    local test_name="test_dry_run_flag_parsed"
    TESTS_RUN=$((TESTS_RUN + 1))

    if grep -q "DRY_RUN=true" "$DEPLOY_SCRIPT"; then
        test_pass "$test_name"
    else
        test_fail "$test_name: --dry-run flag parsing not found"
    fi
}

test_force_flag_parsed() {
    local test_name="test_force_flag_parsed"
    TESTS_RUN=$((TESTS_RUN + 1))

    if grep -q "FORCE_DEPLOY=true" "$DEPLOY_SCRIPT"; then
        test_pass "$test_name"
    else
        test_fail "$test_name: --force flag parsing not found"
    fi
}

test_skip_migrations_flag() {
    local test_name="test_skip_migrations_flag"
    TESTS_RUN=$((TESTS_RUN + 1))

    if grep -q "SKIP_MIGRATIONS=true" "$DEPLOY_SCRIPT"; then
        test_pass "$test_name"
    else
        test_fail "$test_name: --skip-migrations flag not found"
    fi
}

test_error_handler_defined() {
    local test_name="test_error_handler_defined"
    TESTS_RUN=$((TESTS_RUN + 1))

    if grep -q "error_handler()" "$DEPLOY_SCRIPT"; then
        test_pass "$test_name"
    else
        test_fail "$test_name: error_handler function not defined"
    fi
}

test_error_trap_set() {
    local test_name="test_error_trap_set"
    TESTS_RUN=$((TESTS_RUN + 1))

    if grep -q "trap 'error_handler" "$DEPLOY_SCRIPT"; then
        test_pass "$test_name"
    else
        test_fail "$test_name: error trap not set"
    fi
}

test_rollback_phase_exists() {
    local test_name="test_rollback_phase_exists"
    TESTS_RUN=$((TESTS_RUN + 1))

    if [ -f "$DEPLOY_ROOT/rollback.sh" ]; then
        test_pass "$test_name"
    else
        test_fail "$test_name: rollback.sh not found"
    fi
}

test_services_list_defined() {
    local test_name="test_services_list_defined"
    TESTS_RUN=$((TESTS_RUN + 1))

    if grep -q 'SERVICES=(' "$DEPLOY_SCRIPT"; then
        test_pass "$test_name"
    else
        test_fail "$test_name: SERVICES list not defined"
    fi
}

# ===== MAIN TEST EXECUTION =====

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Deploy Script Test Suite${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Basic structure tests
test_deploy_script_exists
test_deploy_script_executable
test_config_file_exists
test_shared_library_exists
test_all_phase_scripts_exist

echo ""
echo -e "${BLUE}--- Configuration Tests ---${NC}"
test_config_contains_required_vars

echo ""
echo -e "${BLUE}--- Executable Tests ---${NC}"
test_phase_script_is_executable

echo ""
echo -e "${BLUE}--- Help and Flags Tests ---${NC}"
test_deploy_help_flag
test_dry_run_flag_parsed
test_force_flag_parsed
test_skip_migrations_flag

echo ""
echo -e "${BLUE}--- Logging Tests ---${NC}"
test_check_ssh_function
test_log_functions_exported

echo ""
echo -e "${BLUE}--- Error Handling Tests ---${NC}"
test_error_handler_defined
test_error_trap_set

echo ""
echo -e "${BLUE}--- Services Tests ---${NC}"
test_services_list_defined
test_rollback_phase_exists

echo ""
echo -e "${BLUE}--- Runtime Tests ---${NC}"
test_deploy_logs_directory_created
test_deploy_dry_run_creates_log

# ===== TEST SUMMARY =====
echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Test Summary${NC}"
echo -e "${BLUE}================================${NC}"

TESTS_PASSED=$(grep -c "^PASS:" "$TEST_RESULTS_FILE" 2>/dev/null) || TESTS_PASSED=0
TESTS_FAILED=$(grep -c "^FAIL:" "$TEST_RESULTS_FILE" 2>/dev/null) || TESTS_FAILED=0
TESTS_SKIPPED=$(grep -c "^SKIP:" "$TEST_RESULTS_FILE" 2>/dev/null) || TESTS_SKIPPED=0

echo -e "Total Tests: ${BLUE}$TESTS_RUN${NC}"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo -e "Skipped: ${YELLOW}$TESTS_SKIPPED${NC}"

if [ "${TESTS_FAILED:-0}" -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed${NC}"
    exit 1
fi
