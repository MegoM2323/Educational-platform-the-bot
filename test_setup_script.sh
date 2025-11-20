#!/usr/bin/env bash

# Тестовый скрипт для проверки setup_test_environment.sh
# Запускает набор тестов для валидации работы скрипта

set -e

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SETUP_SCRIPT="$SCRIPT_DIR/setup_test_environment.sh"

# Цвета
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

print_test() {
    echo -e "\n${YELLOW}TEST:${NC} $1"
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}: $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC}: $1"
    ((TESTS_FAILED++))
}

echo "========================================"
echo "Testing setup_test_environment.sh"
echo "========================================"

# Test 1: Скрипт существует и исполняемый
print_test "Checking script exists and is executable"
if [ -f "$SETUP_SCRIPT" ] && [ -x "$SETUP_SCRIPT" ]; then
    print_pass "Script is executable"
else
    print_fail "Script not found or not executable"
fi

# Test 2: Синтаксис bash корректен
print_test "Checking bash syntax"
if bash -n "$SETUP_SCRIPT" 2>/dev/null; then
    print_pass "Bash syntax is valid"
else
    print_fail "Bash syntax errors found"
fi

# Test 3: --help работает
print_test "Testing --help flag"
if "$SETUP_SCRIPT" --help > /dev/null 2>&1; then
    print_pass "--help flag works"
else
    print_fail "--help flag failed"
fi

# Test 4: --help содержит все основные опции
print_test "Checking help content"
HELP_OUTPUT=$("$SETUP_SCRIPT" --help 2>&1)
REQUIRED_FLAGS=("--full-reset" "--clean-only" "--seed-only" "--preview" "--with-e2e" "--force")
ALL_FOUND=true

for flag in "${REQUIRED_FLAGS[@]}"; do
    if ! echo "$HELP_OUTPUT" | grep -q "$flag"; then
        print_fail "Help missing flag: $flag"
        ALL_FOUND=false
    fi
done

if [ "$ALL_FOUND" = true ]; then
    print_pass "All required flags documented in help"
fi

# Test 5: Неизвестная опция отклоняется
print_test "Testing invalid option handling"
if "$SETUP_SCRIPT" --invalid-option 2>&1 | grep -q "Неизвестная опция"; then
    print_pass "Invalid options are rejected"
else
    print_fail "Invalid option handling not working"
fi

# Test 6: Конфликтующие опции
print_test "Testing conflicting options"
if "$SETUP_SCRIPT" --clean-only --seed-only 2>&1 | grep -q "не могут использоваться вместе"; then
    print_pass "Conflicting options detected"
else
    print_fail "Conflicting options not detected"
fi

# Test 7: Проверка необходимых функций
print_test "Checking required functions exist"
REQUIRED_FUNCTIONS=(
    "print_banner"
    "check_prerequisites"
    "cleanup_database"
    "create_test_users"
    "create_test_subjects"
    "create_full_dataset"
    "verify_data"
    "show_statistics"
    "run_e2e_tests"
    "main"
)

ALL_FUNCTIONS_FOUND=true
for func in "${REQUIRED_FUNCTIONS[@]}"; do
    if ! grep -q "^${func}()" "$SETUP_SCRIPT"; then
        print_fail "Function missing: $func"
        ALL_FUNCTIONS_FOUND=false
    fi
done

if [ "$ALL_FUNCTIONS_FOUND" = true ]; then
    print_pass "All required functions exist"
fi

# Test 8: Проверка наличия цветов в выводе
print_test "Checking colored output support"
if grep -q "readonly GREEN=" "$SETUP_SCRIPT" && \
   grep -q "readonly RED=" "$SETUP_SCRIPT" && \
   grep -q "readonly CYAN=" "$SETUP_SCRIPT"; then
    print_pass "Color support implemented"
else
    print_fail "Color support missing"
fi

# Test 9: Проверка обработки ошибок
print_test "Checking error handling"
if grep -q "trap.*ERR" "$SETUP_SCRIPT"; then
    print_pass "Error trap implemented"
else
    print_fail "Error trap missing"
fi

# Test 10: Проверка логирования
print_test "Checking logging functionality"
if grep -q "LOG_FILE=" "$SETUP_SCRIPT" && \
   grep -q "log()" "$SETUP_SCRIPT"; then
    print_pass "Logging functionality implemented"
else
    print_fail "Logging functionality missing"
fi

# Итоги
echo ""
echo "========================================"
echo "Test Results"
echo "========================================"
echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
echo -e "${RED}Failed: $TESTS_FAILED${NC}"
echo "========================================"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi
