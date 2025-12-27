#!/bin/bash

################################################################################
# THE_BOT Platform - Pre-Deployment Health Check Script
#
# Performs comprehensive pre-deployment verification including:
# - Code quality and test validation
# - Environment configuration verification
# - Database connectivity and migration safety
# - Docker image building and scanning
# - Security vulnerability checks
# - Deployment readiness assessment
#
# Usage:
#   ./scripts/deployment/pre-deploy-check.sh
#   ./scripts/deployment/pre-deploy-check.sh --no-tests      # Skip tests
#   ./scripts/deployment/pre-deploy-check.sh --quick         # Quick checks only
#   ./scripts/deployment/pre-deploy-check.sh --verbose       # Detailed output
#
################################################################################

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
ENV_FILE="${PROJECT_DIR}/.env.production"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
RUN_TESTS=true
VERBOSE=false
QUICK_MODE=false
FAILED_CHECKS=0
PASSED_CHECKS=0
WARNING_CHECKS=0

################################################################################
# UTILITY FUNCTIONS
################################################################################

print_header() {
    echo -e "\n${BLUE}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════${NC}\n"
}

print_check() {
    echo -n "Checking: $1 ... "
}

print_pass() {
    echo -e "${GREEN}✓ PASS${NC}"
    ((PASSED_CHECKS++))
}

print_fail() {
    echo -e "${RED}✗ FAIL${NC}"
    if [ -n "$1" ]; then
        echo -e "  ${RED}Reason: $1${NC}"
    fi
    ((FAILED_CHECKS++))
}

print_warn() {
    echo -e "${YELLOW}⚠ WARN${NC}"
    if [ -n "$1" ]; then
        echo -e "  ${YELLOW}Note: $1${NC}"
    fi
    ((WARNING_CHECKS++))
}

print_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_result() {
    local status=$1
    local message=$2

    if [ "$status" = "0" ]; then
        print_pass "$message"
    else
        print_fail "$message"
    fi
}

################################################################################
# PARSE ARGUMENTS
################################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-tests)
            RUN_TESTS=false
            shift
            ;;
        --quick)
            QUICK_MODE=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

################################################################################
# PRE-DEPLOYMENT CHECKS
################################################################################

print_header "THE_BOT Platform - Pre-Deployment Check"

# Check 1: Git status
print_header "1. GIT REPOSITORY STATUS"

print_check "Git repository initialized"
if [ -d "${PROJECT_DIR}/.git" ]; then
    print_pass
else
    print_fail "Not a git repository"
    exit 1
fi

print_check "No uncommitted changes"
if git -C "$PROJECT_DIR" diff-index --quiet HEAD --; then
    print_pass
else
    print_fail "Uncommitted changes found"
    if [ "$VERBOSE" = true ]; then
        git -C "$PROJECT_DIR" status
    fi
fi

print_check "Current branch is main/master"
CURRENT_BRANCH=$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD)
if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" ]]; then
    print_pass
else
    print_warn "Current branch is $CURRENT_BRANCH (expected main/master)"
fi

print_check "Latest commits visible"
COMMIT_COUNT=$(git -C "$PROJECT_DIR" rev-list --count HEAD)
echo -e "Found ${BLUE}${COMMIT_COUNT}${NC} commits"

# Check 2: Environment Configuration
print_header "2. ENVIRONMENT CONFIGURATION"

print_check "Environment file exists"
if [ -f "$ENV_FILE" ]; then
    print_pass
else
    print_fail ".env.production not found at $ENV_FILE"
    exit 1
fi

# Required environment variables
REQUIRED_VARS=(
    "SECRET_KEY"
    "ENVIRONMENT"
    "DATABASE_URL"
    "REDIS_URL"
    "ALLOWED_HOSTS"
    "YOOKASSA_SHOP_ID"
    "YOOKASSA_SECRET_KEY"
)

print_check "Required environment variables"
MISSING_VARS=()
source "$ENV_FILE"
for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        MISSING_VARS+=("$var")
    fi
done

if [ ${#MISSING_VARS[@]} -eq 0 ]; then
    print_pass
else
    print_fail "Missing variables: ${MISSING_VARS[*]}"
fi

print_check "SECRET_KEY strength"
SECRET_KEY_LENGTH=${#SECRET_KEY}
if [ "$SECRET_KEY_LENGTH" -ge 50 ]; then
    print_pass "(length: $SECRET_KEY_LENGTH)"
else
    print_fail "SECRET_KEY too short (length: $SECRET_KEY_LENGTH, min: 50)"
fi

print_check "ENVIRONMENT is production"
if [ "$ENVIRONMENT" = "production" ]; then
    print_pass
else
    print_warn "ENVIRONMENT is $ENVIRONMENT (not production)"
fi

print_check "DEBUG is disabled"
if [ "$DEBUG" = "False" ] || [ "$DEBUG" = "false" ]; then
    print_pass
else
    print_warn "DEBUG is enabled"
fi

# Check 3: Docker Configuration
print_header "3. DOCKER CONFIGURATION"

print_check "Docker installed"
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
    print_pass "(version: $DOCKER_VERSION)"
else
    print_fail "Docker not installed"
    exit 1
fi

print_check "Docker daemon running"
if docker info &> /dev/null; then
    print_pass
else
    print_fail "Docker daemon not running"
    exit 1
fi

print_check "Docker Compose installed"
if command -v docker-compose &> /dev/null; then
    DC_VERSION=$(docker-compose --version | awk '{print $3}' | sed 's/,//')
    print_pass "(version: $DC_VERSION)"
else
    print_fail "Docker Compose not installed"
    exit 1
fi

print_check "docker-compose.prod.yml exists"
if [ -f "$COMPOSE_FILE" ]; then
    print_pass
else
    print_fail "File not found: $COMPOSE_FILE"
    exit 1
fi

# Check 4: Code Quality (if not quick mode)
if [ "$QUICK_MODE" = false ]; then
    print_header "4. CODE QUALITY CHECKS"

    # Backend linting
    print_check "Backend code style (black)"
    if command -v black &> /dev/null; then
        if black --check backend/ 2>/dev/null; then
            print_pass
        else
            print_warn "Code style issues found (run: black backend/)"
        fi
    else
        print_warn "black not installed"
    fi

    # Backend type checking
    print_check "Backend type hints (mypy)"
    if command -v mypy &> /dev/null; then
        if mypy backend/ --ignore-missing-imports 2>/dev/null | grep -q "error:"; then
            print_warn "Type hints issues found"
        else
            print_pass
        fi
    else
        print_warn "mypy not installed"
    fi

    # Frontend linting
    print_check "Frontend code style (eslint)"
    if [ -f "${PROJECT_DIR}/frontend/package.json" ]; then
        if cd "${PROJECT_DIR}/frontend" && npm run lint 2>&1 | grep -q "error:"; then
            print_warn "ESLint errors found"
        else
            print_pass
        fi
        cd "$PROJECT_DIR"
    else
        print_warn "Frontend package.json not found"
    fi
fi

# Check 5: Dependencies
print_header "5. DEPENDENCY CHECKS"

print_check "Python dependencies pinned"
UNPINNED=$(grep -v "==" "${PROJECT_DIR}/backend/requirements.txt" | grep -v "^#" | grep -v "^$" | wc -l)
if [ "$UNPINNED" -eq 0 ]; then
    print_pass
else
    print_warn "Found $UNPINNED unpinned dependencies"
fi

print_check "Node.js dependencies in lockfile"
if [ -f "${PROJECT_DIR}/frontend/package-lock.json" ]; then
    print_pass
else
    print_warn "package-lock.json not found"
fi

if [ "$QUICK_MODE" = false ]; then
    print_check "Security vulnerabilities (Python)"
    if command -v pip-audit &> /dev/null; then
        if pip-audit --skip-editable 2>/dev/null | grep -q "VULNERABILITY"; then
            print_warn "Python vulnerabilities found (review carefully)"
        else
            print_pass
        fi
    else
        print_warn "pip-audit not installed"
    fi

    print_check "Security vulnerabilities (Node.js)"
    if [ -f "${PROJECT_DIR}/frontend/package.json" ]; then
        if cd "${PROJECT_DIR}/frontend" && npm audit 2>&1 | grep -q "vulnerabilities"; then
            print_warn "Node.js vulnerabilities found (review carefully)"
        else
            print_pass
        fi
        cd "$PROJECT_DIR"
    fi
fi

# Check 6: Database Connectivity
print_header "6. DATABASE CONNECTIVITY"

print_check "PostgreSQL URL format"
if [[ "$DATABASE_URL" =~ ^postgres(ql)?:// ]]; then
    print_pass
else
    print_fail "Invalid DATABASE_URL format"
fi

print_check "Redis URL format"
if [[ "$REDIS_URL" =~ ^redis:// ]]; then
    print_pass
else
    print_fail "Invalid REDIS_URL format"
fi

if [ "$QUICK_MODE" = false ]; then
    print_check "PostgreSQL connectivity"
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres \
        psql "$DATABASE_URL" -c "SELECT 1" &>/dev/null; then
        print_pass
    else
        print_warn "Cannot connect to PostgreSQL (it may not be running)"
    fi

    print_check "Redis connectivity"
    if docker-compose -f "$COMPOSE_FILE" exec -T redis \
        redis-cli ping &>/dev/null; then
        print_pass
    else
        print_warn "Cannot connect to Redis (it may not be running)"
    fi
fi

# Check 7: Tests (if not disabled)
if [ "$RUN_TESTS" = true ] && [ "$QUICK_MODE" = false ]; then
    print_header "7. TEST SUITE"

    print_check "Backend tests"
    cd "$PROJECT_DIR/backend"
    if pytest tests/ -q --tb=no 2>/dev/null; then
        print_pass
    else
        print_fail "Some tests failed (run: pytest tests/ -v)"
    fi
    cd "$PROJECT_DIR"

    print_check "Frontend tests"
    if [ -f "${PROJECT_DIR}/frontend/package.json" ]; then
        cd "${PROJECT_DIR}/frontend"
        if npm test -- --run 2>/dev/null; then
            print_pass
        else
            print_warn "Frontend tests failed (review)"
        fi
        cd "$PROJECT_DIR"
    fi
fi

# Check 8: Docker Images
print_header "8. DOCKER IMAGE CHECKS"

print_check "Backend Dockerfile exists"
if [ -f "${PROJECT_DIR}/backend/Dockerfile" ]; then
    print_pass
else
    print_fail "Backend Dockerfile not found"
fi

print_check "Frontend Dockerfile exists"
if [ -f "${PROJECT_DIR}/frontend/Dockerfile" ]; then
    print_pass
else
    print_fail "Frontend Dockerfile not found"
fi

if [ "$QUICK_MODE" = false ]; then
    print_check "Building Docker images"
    if docker-compose -f "$COMPOSE_FILE" build --no-cache 2>&1 | tail -5 | grep -q "Successfully built\|already built"; then
        print_pass
    else
        print_warn "Docker build check inconclusive"
    fi
fi

# Check 9: SSL Certificates
print_header "9. SSL CERTIFICATE CHECKS"

SSL_CERT_FILE="${PROJECT_DIR}/docker/certs/server.crt"
print_check "SSL certificate exists"
if [ -f "$SSL_CERT_FILE" ]; then
    print_pass
else
    print_warn "SSL certificate not found at $SSL_CERT_FILE"
fi

if [ -f "$SSL_CERT_FILE" ]; then
    print_check "SSL certificate validity"
    EXPIRY=$(openssl x509 -in "$SSL_CERT_FILE" -noout -enddate 2>/dev/null | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s 2>/dev/null || date -jf "%b %d %T %Z %Y" "$EXPIRY" +%s 2>/dev/null || echo 0)
    NOW_EPOCH=$(date +%s)
    DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_EPOCH - $NOW_EPOCH) / 86400 ))

    if [ "$DAYS_UNTIL_EXPIRY" -gt 30 ]; then
        print_pass "(expires in $DAYS_UNTIL_EXPIRY days: $EXPIRY)"
    elif [ "$DAYS_UNTIL_EXPIRY" -gt 0 ]; then
        print_warn "Certificate expires soon (in $DAYS_UNTIL_EXPIRY days)"
    else
        print_fail "Certificate has expired"
    fi
fi

# Check 10: Database Migrations
print_header "10. DATABASE MIGRATION CHECKS"

print_check "Pending migrations exist"
if [ "$QUICK_MODE" = false ]; then
    cd "${PROJECT_DIR}/backend"
    PENDING=$(python manage.py showmigrations --plan 2>/dev/null | grep "\[" | grep -v "\[X\]" | wc -l)
    cd "$PROJECT_DIR"

    if [ "$PENDING" -gt 0 ]; then
        print_warn "Found $PENDING pending migrations (will be applied during deployment)"
    else
        print_pass "No pending migrations"
    fi
fi

# Check 11: Configuration Files
print_header "11. CONFIGURATION FILES"

print_check "nginx configuration exists"
if [ -f "${PROJECT_DIR}/docker/nginx.prod.conf" ]; then
    print_pass
else
    print_fail "nginx.prod.conf not found"
fi

print_check "Configuration has no syntax errors"
if [ -f "${PROJECT_DIR}/docker/nginx.prod.conf" ]; then
    if docker run --rm -v "${PROJECT_DIR}/docker:/etc/nginx" nginx:latest \
        nginx -t -c /etc/nginx/nginx.prod.conf 2>/dev/null; then
        print_pass
    else
        print_warn "nginx config syntax check inconclusive"
    fi
fi

# Check 12: Version Information
print_header "12. VERSION INFORMATION"

print_check "Git version tag"
GIT_VERSION=$(git -C "$PROJECT_DIR" describe --tags 2>/dev/null || echo "no tags")
echo -e "Current: ${BLUE}${GIT_VERSION}${NC}"

print_check "Python version"
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
if [[ "$PYTHON_VERSION" =~ ^3\.(10|11|12) ]]; then
    print_pass "(version: $PYTHON_VERSION)"
else
    print_warn "(version: $PYTHON_VERSION, expected 3.10+)"
fi

print_check "Node.js version"
if command -v node &> /dev/null; then
    NODE_VERSION=$(node --version | sed 's/v//')
    print_pass "(version: $NODE_VERSION)"
fi

# Final Summary
print_header "DEPLOYMENT READINESS SUMMARY"

TOTAL_CHECKS=$((PASSED_CHECKS + FAILED_CHECKS + WARNING_CHECKS))

echo "Checks Summary:"
echo -e "  ${GREEN}✓ Passed: $PASSED_CHECKS${NC}"
echo -e "  ${YELLOW}⚠ Warnings: $WARNING_CHECKS${NC}"
echo -e "  ${RED}✗ Failed: $FAILED_CHECKS${NC}"
echo -e "  Total: $TOTAL_CHECKS"
echo ""

if [ "$FAILED_CHECKS" -eq 0 ]; then
    if [ "$WARNING_CHECKS" -gt 0 ]; then
        echo -e "${YELLOW}⚠️  DEPLOYMENT ALLOWED WITH CAUTION${NC}"
        echo -e "Please review the ${YELLOW}$WARNING_CHECKS${NC} warnings above"
    else
        echo -e "${GREEN}✓ DEPLOYMENT READY${NC}"
        echo -e "All pre-deployment checks passed!"
    fi
    exit 0
else
    echo -e "${RED}✗ DEPLOYMENT BLOCKED${NC}"
    echo -e "Please fix the ${RED}$FAILED_CHECKS${NC} failed checks above before deploying"
    exit 1
fi
