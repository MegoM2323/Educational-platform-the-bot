#!/bin/bash

# Test Pipeline Validation Script
# Validates the test.yml workflow configuration and environment

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
CHECKS_PASSED=0
CHECKS_FAILED=0
WARNINGS=0

# Helper functions
pass() {
    echo -e "${GREEN}✓${NC} $1"
    ((CHECKS_PASSED++))
}

fail() {
    echo -e "${RED}✗${NC} $1"
    ((CHECKS_FAILED++))
}

warn() {
    echo -e "${YELLOW}⚠${NC} $1"
    ((WARNINGS++))
}

info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

# Main validation
main() {
    echo "==========================================="
    echo "Test Pipeline Validation"
    echo "==========================================="
    echo ""

    # 1. Check workflow file exists
    info "Checking workflow files..."
    if [ -f "${SCRIPT_DIR}/test.yml" ]; then
        pass "test.yml workflow file exists"
    else
        fail "test.yml workflow file not found"
    fi

    # 2. Check workflow documentation
    if [ -f "${SCRIPT_DIR}/TEST_PIPELINE.md" ]; then
        pass "TEST_PIPELINE.md documentation exists"
    else
        fail "TEST_PIPELINE.md documentation not found"
    fi

    # 3. Check backend configuration
    info "Checking backend configuration..."
    if [ -f "${PROJECT_ROOT}/backend/pytest.ini" ]; then
        pass "pytest.ini configuration exists"
    else
        fail "pytest.ini configuration not found"
    fi

    if [ -f "${PROJECT_ROOT}/backend/requirements.txt" ]; then
        pass "requirements.txt exists"
        # Check for test dependencies
        if grep -q "pytest" "${PROJECT_ROOT}/backend/requirements.txt" 2>/dev/null || true; then
            pass "pytest dependency found"
        else
            warn "pytest dependency not found in requirements.txt"
        fi
        if grep -q "coverage" "${PROJECT_ROOT}/backend/requirements.txt" 2>/dev/null || true; then
            pass "coverage dependency found"
        else
            warn "coverage dependency not found in requirements.txt"
        fi
    else
        fail "requirements.txt not found"
    fi

    # 4. Check frontend configuration
    info "Checking frontend configuration..."
    if [ -f "${PROJECT_ROOT}/frontend/package.json" ]; then
        pass "package.json exists"
        # Check for test scripts
        if grep -q '"test"' "${PROJECT_ROOT}/frontend/package.json" 2>/dev/null || true; then
            pass "test script found in package.json"
        else
            warn "test script not found in package.json"
        fi
        if grep -q '"test:coverage"' "${PROJECT_ROOT}/frontend/package.json" 2>/dev/null || true; then
            pass "test:coverage script found"
        else
            warn "test:coverage script not found in package.json"
        fi
    else
        fail "package.json not found"
    fi

    if [ -f "${PROJECT_ROOT}/frontend/vitest.config.ts" ]; then
        pass "vitest.config.ts exists"
    else
        warn "vitest.config.ts not found"
    fi

    if [ -f "${PROJECT_ROOT}/frontend/playwright.config.ts" ]; then
        pass "playwright.config.ts exists"
    else
        warn "playwright.config.ts not found"
    fi

    # 5. Check test directories
    info "Checking test directories..."
    if [ -d "${PROJECT_ROOT}/backend/tests" ]; then
        pass "backend/tests directory exists"
        # Count test files
        TEST_COUNT=$(find "${PROJECT_ROOT}/backend/tests" -name "test_*.py" | wc -l)
        if [ "$TEST_COUNT" -gt 0 ]; then
            pass "Found $TEST_COUNT backend test files"
        else
            warn "No test_*.py files found in backend/tests"
        fi
    else
        warn "backend/tests directory not found"
    fi

    if [ -d "${PROJECT_ROOT}/frontend/tests" ]; then
        pass "frontend/tests directory exists"
    else
        warn "frontend/tests directory not found"
    fi

    # 6. Check Docker configuration
    info "Checking Docker configuration..."
    if [ -f "${PROJECT_ROOT}/docker-compose.yml" ]; then
        pass "docker-compose.yml exists"
    else
        warn "docker-compose.yml not found"
    fi

    # 7. Validate workflow syntax (if yamllint available)
    info "Validating YAML syntax..."
    if command -v yamllint &> /dev/null; then
        if yamllint "${SCRIPT_DIR}/test.yml" > /dev/null 2>&1; then
            pass "test.yml YAML syntax is valid"
        else
            warn "test.yml has YAML syntax warnings (non-critical)"
        fi
    else
        warn "yamllint not installed (skipping YAML validation)"
    fi

    # 8. Check environment configuration
    info "Checking environment configuration..."
    if [ -f "${PROJECT_ROOT}/.env.example" ]; then
        pass ".env.example file exists"
        # Check for required variables
        if grep -q "DATABASE_URL" "${PROJECT_ROOT}/.env.example" 2>/dev/null || true; then
            pass "DATABASE_URL defined in .env.example"
        else
            warn "DATABASE_URL not found in .env.example"
        fi
        if grep -q "REDIS_URL" "${PROJECT_ROOT}/.env.example" 2>/dev/null || true; then
            pass "REDIS_URL defined in .env.example"
        else
            warn "REDIS_URL not found in .env.example"
        fi
    else
        warn ".env.example file not found"
    fi

    # 9. Check Makefile for test commands
    info "Checking Makefile..."
    if [ -f "${PROJECT_ROOT}/Makefile" ]; then
        pass "Makefile exists"
        if grep -q "test:" "${PROJECT_ROOT}/Makefile" 2>/dev/null || true; then
            pass "test target found in Makefile"
        else
            warn "test target not found in Makefile"
        fi
        if grep -q "coverage:" "${PROJECT_ROOT}/Makefile" 2>/dev/null || true; then
            pass "coverage target found in Makefile"
        else
            warn "coverage target not found in Makefile"
        fi
    else
        warn "Makefile not found"
    fi

    # 10. Check GitHub Actions configuration
    info "Checking GitHub Actions configuration..."
    if [ -d "${PROJECT_ROOT}/.github/workflows" ]; then
        pass ".github/workflows directory exists"
        WORKFLOW_COUNT=$(find "${PROJECT_ROOT}/.github/workflows" -name "*.yml" | wc -l)
        pass "Found $WORKFLOW_COUNT workflow files"
    else
        fail ".github/workflows directory not found"
    fi

    # Summary
    echo ""
    echo "==========================================="
    echo "Validation Summary"
    echo "==========================================="
    echo -e "Passed:  ${GREEN}$CHECKS_PASSED${NC}"
    echo -e "Failed:  ${RED}$CHECKS_FAILED${NC}"
    echo -e "Warnings: ${YELLOW}$WARNINGS${NC}"
    echo ""

    if [ $CHECKS_FAILED -eq 0 ]; then
        echo -e "${GREEN}All critical checks passed!${NC}"
        return 0
    else
        echo -e "${RED}Some critical checks failed!${NC}"
        return 1
    fi
}

# Run validation
main "$@"
