#!/bin/bash

set -e

PROJECT_ROOT="/home/mego/Python Projects/THE_BOT_platform"
BACKEND_DIR="$PROJECT_ROOT/backend"

echo "=========================================="
echo "T5: Testing DATABASE URL Parsing"
echo "=========================================="

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0

# Test 1: Django check with DB_* variables (NO DATABASE_URL)
echo -e "\n${YELLOW}[TEST 1]${NC} Django check with DB_* variables (NO DATABASE_URL)"

cd "$BACKEND_DIR"

unset DATABASE_URL 2>/dev/null || true

export DB_ENGINE="postgresql"
export DB_HOST="localhost"
export DB_PORT="5432"
export DB_NAME="thebot_test"
export DB_USER="postgres"
export DB_PASSWORD="postgres"
export DB_SSLMODE="disable"
export ENVIRONMENT="test"
export DJANGO_SETTINGS_MODULE="config.settings"

if python manage.py check --database default > /tmp/django_check_1.log 2>&1; then
    echo -e "${GREEN}✓ PASS${NC}: Django settings loaded successfully"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}: Django check failed"
    cat /tmp/django_check_1.log
    ((TESTS_FAILED++))
fi

if ! grep -q "ValueError: Port could not be cast to integer" /tmp/django_check_1.log 2>/dev/null; then
    echo -e "${GREEN}✓ PASS${NC}: No port parsing ValueError detected"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}: Found the port parsing error!"
    cat /tmp/django_check_1.log
    ((TESTS_FAILED++))
fi

# Test 2: Python import test - verify _get_database_config works
echo -e "\n${YELLOW}[TEST 2]${NC} Python test - verify _get_database_config works"

python3 << 'PYEOF'
import os
import sys

sys.path.insert(0, '/home/mego/Python Projects/THE_BOT_platform/backend')

os.environ['DB_ENGINE'] = 'postgresql'
os.environ['DB_HOST'] = 'localhost'
os.environ['DB_PORT'] = '5432'
os.environ['DB_NAME'] = 'thebot_test'
os.environ['DB_USER'] = 'postgres'
os.environ['DB_PASSWORD'] = 'postgres'
os.environ['DB_SSLMODE'] = 'disable'
os.environ.pop('DATABASE_URL', None)

try:
    from config.settings import DATABASES
    db_config = DATABASES['default']

    print(f"DATABASE_URL: {os.environ.get('DATABASE_URL', '<NOT SET>')}")
    print(f"Config PORT: {db_config['PORT']} (type: {type(db_config['PORT']).__name__})")

    assert db_config['ENGINE'] == 'django.db.backends.postgresql'
    assert db_config['NAME'] == 'thebot_test'
    assert db_config['USER'] == 'postgres'
    assert db_config['HOST'] == 'localhost'
    assert db_config['PORT'] == '5432'
    assert db_config['PORT'] != 'None'

    print("All assertions passed!")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ PASS${NC}: _get_database_config works correctly"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}: _get_database_config failed"
    ((TESTS_FAILED++))
fi

# Test 3: Test DATABASE_URL parsing with URL-safe password
echo -e "\n${YELLOW}[TEST 3]${NC} DATABASE_URL parsing with URL-safe password"

python3 << 'PYEOF'
import os
import sys

sys.path.insert(0, '/home/mego/Python Projects/THE_BOT_platform/backend')

os.environ['DATABASE_URL'] = 'postgresql://postgres:test_password_123@localhost:5432/thebot_test'
os.environ.pop('DB_NAME', None)
os.environ.pop('DB_USER', None)
os.environ.pop('DB_PASSWORD', None)
os.environ.pop('DB_HOST', None)
os.environ.pop('DB_PORT', None)

try:
    from config.settings import _get_database_config
    db_config = _get_database_config()

    print(f"Database Config from URL: {db_config}")
    print(f"PORT: {db_config['PORT']} (type: {type(db_config['PORT']).__name__})")

    assert db_config['ENGINE'] == 'django.db.backends.postgresql'
    assert db_config['NAME'] == 'thebot_test'
    assert db_config['USER'] == 'postgres'
    assert db_config['PASSWORD'] == 'test_password_123'
    assert db_config['HOST'] == 'localhost'
    assert db_config['PORT'] == '5432'

    print("All DATABASE_URL assertions passed!")
    sys.exit(0)
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)
PYEOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ PASS${NC}: DATABASE_URL parsing works correctly"
    ((TESTS_PASSED++))
else
    echo -e "${RED}✗ FAIL${NC}: DATABASE_URL parsing failed"
    ((TESTS_FAILED++))
fi

# Summary
echo -e "\n=========================================="
echo "Test Summary"
echo "=========================================="
TOTAL=$((TESTS_PASSED + TESTS_FAILED))
echo -e "Total Tests: ${TOTAL}"
echo -e "${GREEN}Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Failed: ${TESTS_FAILED}${NC}"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}✗ Some tests failed${NC}"
    exit 1
fi
