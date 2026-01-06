#!/bin/bash

set -e

echo "=========================================="
echo "Phase 2 E2E Testing - Message Sending"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Check if servers are running
echo "Checking prerequisites..."

# Check if frontend dev server is running
if ! curl -s http://localhost:8080 > /dev/null 2>&1; then
    echo -e "${RED}Error: Frontend dev server not running on http://localhost:8080${NC}"
    echo "Start it with: npm run dev (in frontend directory)"
    exit 1
fi
echo -e "${GREEN}✓${NC} Frontend dev server running"

# Check if backend dev server is running
if ! curl -s http://localhost:8000 > /dev/null 2>&1; then
    echo -e "${RED}Error: Backend dev server not running on http://localhost:8000${NC}"
    echo "Start it with: python manage.py runserver (in backend directory)"
    exit 1
fi
echo -e "${GREEN}✓${NC} Backend dev server running"

# Create output directory
mkdir -p e2e-results
echo -e "${GREEN}✓${NC} Output directory ready: e2e-results/"

echo ""
echo "=========================================="
echo "Running E2E Tests..."
echo "=========================================="
echo ""

cd frontend

# Default test to run
TEST_FILE="e2e/messaging.phase2.spec.ts"
BROWSER_TYPE="${1:-all}"  # all, chromium, firefox, mobile

case "$BROWSER_TYPE" in
    all)
        echo "Running tests on all browsers (Chromium, Firefox, Mobile Chrome)..."
        npx playwright test "$TEST_FILE" --config=../frontend/e2e.playwright.config.ts
        ;;
    chromium)
        echo "Running tests on Chromium browser..."
        npx playwright test "$TEST_FILE" --project=chromium --config=../frontend/e2e.playwright.config.ts
        ;;
    firefox)
        echo "Running tests on Firefox browser..."
        npx playwright test "$TEST_FILE" --project=firefox --config=../frontend/e2e.playwright.config.ts
        ;;
    mobile)
        echo "Running tests on Mobile Chrome..."
        npx playwright test "$TEST_FILE" --project="Mobile Chrome" --config=../frontend/e2e.playwright.config.ts
        ;;
    debug)
        echo "Running tests in debug mode..."
        npx playwright test "$TEST_FILE" --debug --config=../frontend/e2e.playwright.config.ts
        ;;
    headed)
        echo "Running tests in headed mode (see browser)..."
        npx playwright test "$TEST_FILE" --headed --config=../frontend/e2e.playwright.config.ts
        ;;
    *)
        echo "Usage: $0 [all|chromium|firefox|mobile|debug|headed]"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Test Results"
echo "=========================================="
echo ""

if [ -f "../e2e-results/results.json" ]; then
    # Parse JSON results
    PASSED=$(grep -o '"ok": true' ../e2e-results/results.json | wc -l)
    FAILED=$(grep -o '"ok": false' ../e2e-results/results.json | wc -l)

    if [ "$FAILED" -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed (${PASSED} tests)${NC}"
    else
        echo -e "${RED}✗ Some tests failed (${PASSED} passed, ${FAILED} failed)${NC}"
    fi

    echo ""
    echo "HTML Report: ../e2e-results/html/index.html"
    echo "JSON Results: ../e2e-results/results.json"
fi

echo ""
echo "=========================================="
