#!/bin/bash

# Test Production Docker Compose Configuration
# ============================================================================
# Validates all services and checks communication
#
# Usage:
#   ./docker/test-production.sh
#   ./docker/test-production.sh [health|connectivity|performance]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.prod.yml"
ENV_FILE="$PROJECT_DIR/.env.production"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# ============================================================================
# UTILITIES
# ============================================================================

print_header() {
    echo -e "${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} $1"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
}

print_test() {
    echo -e "${YELLOW}[TEST]${NC} $1"
}

print_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

print_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

# ============================================================================
# HEALTH CHECKS
# ============================================================================

test_health() {
    print_header "Service Health Checks"

    local services=(
        "thebot-postgres-prod:postgres"
        "thebot-redis-prod:redis"
        "thebot-backend-prod:backend"
        "thebot-frontend-prod:frontend"
        "thebot-nginx-prod:nginx"
        "thebot-celery-worker-prod:celery-worker"
        "thebot-celery-beat-prod:celery-beat"
    )

    for service in "${services[@]}"; do
        local container="${service%:*}"
        local name="${service#*:}"

        print_test "Checking $name..."

        if docker ps --filter "name=$container" --format "{{.Names}}" | grep -q "$container"; then
            print_pass "$name is running"
        else
            print_fail "$name is not running"
            continue
        fi

        # Check health status if health check is configured
        local health=$(docker inspect --format='{{.State.Health.Status}}' "$container" 2>/dev/null || echo "none")

        if [ "$health" = "healthy" ]; then
            print_pass "$name is healthy"
        elif [ "$health" = "none" ]; then
            print_info "$name has no health check configured"
        else
            print_fail "$name is $health"
        fi
    done
}

# ============================================================================
# CONNECTIVITY TESTS
# ============================================================================

test_connectivity() {
    print_header "Service Connectivity Tests"

    # PostgreSQL
    print_test "Testing PostgreSQL connectivity..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
        pg_isready -U postgres -d thebot_db &>/dev/null; then
        print_pass "PostgreSQL is accessible"
    else
        print_fail "PostgreSQL connection failed"
    fi

    # Redis
    print_test "Testing Redis connectivity..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T redis \
        redis-cli -a redis ping &>/dev/null; then
        print_pass "Redis is accessible"
    else
        print_fail "Redis connection failed"
    fi

    # Backend health endpoint
    print_test "Testing Backend health endpoint..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
        curl -s http://localhost:8000/api/system/health/ >/dev/null; then
        print_pass "Backend health endpoint is working"
    else
        print_fail "Backend health endpoint failed"
    fi

    # Nginx health endpoint
    print_test "Testing Nginx health endpoint..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T nginx \
        curl -s http://localhost/health >/dev/null; then
        print_pass "Nginx health endpoint is working"
    else
        print_fail "Nginx health endpoint failed"
    fi
}

# ============================================================================
# ENVIRONMENT CONFIGURATION TESTS
# ============================================================================

test_environment() {
    print_header "Environment Configuration Tests"

    # Check required environment variables
    local required_vars=(
        "SECRET_KEY"
        "DB_NAME"
        "DB_USER"
        "DB_PASSWORD"
        "REDIS_PASSWORD"
        "FRONTEND_URL"
    )

    for var in "${required_vars[@]}"; do
        print_test "Checking $var..."

        if grep -q "^$var=" "$ENV_FILE"; then
            print_pass "$var is configured"
        else
            print_fail "$var is not configured"
        fi
    done

    # Check SSL certificates
    print_test "Checking SSL certificates..."
    if [ -f "$SCRIPT_DIR/ssl/cert.pem" ] && [ -f "$SCRIPT_DIR/ssl/key.pem" ]; then
        print_pass "SSL certificates are present"

        # Check certificate validity
        local expiry=$(openssl x509 -in "$SCRIPT_DIR/ssl/cert.pem" -noout -enddate 2>/dev/null || echo "error")
        if [[ "$expiry" != "error" ]]; then
            print_info "  $expiry"
            print_pass "SSL certificate is valid"
        fi
    else
        print_fail "SSL certificates are missing"
    fi
}

# ============================================================================
# VOLUME & PERSISTENCE TESTS
# ============================================================================

test_volumes() {
    print_header "Volume & Persistence Tests"

    local volumes=(
        "postgres_data"
        "redis_data"
        "backend_static"
        "backend_media"
        "backend_logs"
    )

    for volume in "${volumes[@]}"; do
        print_test "Checking volume $volume..."

        if docker volume ls | grep -q "$volume"; then
            print_pass "Volume $volume exists"
        else
            print_fail "Volume $volume is missing"
        fi
    done

    # Test write permissions
    print_test "Testing write permissions..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
        touch /app/logs/test.txt 2>/dev/null && \
       docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
        rm /app/logs/test.txt 2>/dev/null; then
        print_pass "Write permissions are correct"
    else
        print_fail "Write permissions issue detected"
    fi
}

# ============================================================================
# RESOURCE LIMITS TESTS
# ============================================================================

test_resources() {
    print_header "Resource Limits Tests"

    local containers=(
        "thebot-backend-prod"
        "thebot-frontend-prod"
        "thebot-nginx-prod"
        "thebot-postgres-prod"
        "thebot-redis-prod"
        "thebot-celery-worker-prod"
        "thebot-celery-beat-prod"
    )

    print_test "Checking resource limits..."

    for container in "${containers[@]}"; do
        if docker ps --filter "name=$container" --format "{{.Names}}" | grep -q "$container"; then
            local limits=$(docker inspect "$container" --format='{{.HostConfig.Memory}}')
            if [ "$limits" != "0" ] && [ "$limits" != "0" ]; then
                print_pass "$container has memory limits set"
            else
                print_fail "$container does not have memory limits"
            fi
        fi
    done
}

# ============================================================================
# SECURITY TESTS
# ============================================================================

test_security() {
    print_header "Security Tests"

    # Check non-root users
    print_test "Checking for non-root containers..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
        whoami 2>/dev/null | grep -q "appuser"; then
        print_pass "Backend running as non-root user"
    else
        print_fail "Backend not running as non-root user"
    fi

    # Check read-only filesystems
    print_test "Checking read-only filesystem configuration..."
    if grep -q "read_only_root_filesystem: true" "$COMPOSE_FILE"; then
        print_pass "Read-only filesystem configured for static services"
    else
        print_fail "Read-only filesystem not configured"
    fi

    # Check security opts
    print_test "Checking security options..."
    if grep -q "no-new-privileges:true" "$COMPOSE_FILE"; then
        print_pass "no-new-privileges security option enabled"
    else
        print_fail "Security options not properly configured"
    fi

    # Check network isolation
    print_test "Checking network isolation..."
    if grep -q "thebot-internal" "$COMPOSE_FILE" && grep -q "thebot-external" "$COMPOSE_FILE"; then
        print_pass "Network isolation configured"
    else
        print_fail "Network isolation not configured"
    fi
}

# ============================================================================
# PERFORMANCE TESTS
# ============================================================================

test_performance() {
    print_header "Performance Tests"

    # API response time
    print_test "Testing API response time..."
    local start=$(date +%s%N)

    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T backend \
        curl -s http://localhost:8000/api/system/health/ >/dev/null 2>&1; then
        local end=$(date +%s%N)
        local duration=$(( (end - start) / 1000000 ))
        echo "  Response time: ${duration}ms"

        if [ "$duration" -lt 500 ]; then
            print_pass "API response time is acceptable (<500ms)"
        else
            print_fail "API response time is too slow (${duration}ms)"
        fi
    fi

    # Database connection time
    print_test "Testing database connection..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T postgres \
        psql -U postgres -d thebot_db -c "SELECT 1" >/dev/null 2>&1; then
        print_pass "Database connection is working"
    else
        print_fail "Database connection failed"
    fi

    # Redis connection time
    print_test "Testing Redis connection..."
    if docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" exec -T redis \
        redis-cli -a redis ping >/dev/null 2>&1; then
        print_pass "Redis connection is working"
    else
        print_fail "Redis connection failed"
    fi

    # Check container resource usage
    print_test "Checking resource usage..."
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" | head -8
}

# ============================================================================
# MAIN
# ============================================================================

main() {
    local test_type="${1:-all}"

    print_header "THE_BOT Production Docker Compose Tests"

    # Verify files exist
    if [ ! -f "$COMPOSE_FILE" ]; then
        print_fail "docker-compose.prod.yml not found"
        exit 1
    fi

    if [ ! -f "$ENV_FILE" ]; then
        print_fail ".env.production not found"
        exit 1
    fi

    # Run tests
    case $test_type in
        health)
            test_health
            ;;
        connectivity)
            test_connectivity
            ;;
        environment)
            test_environment
            ;;
        volumes)
            test_volumes
            ;;
        resources)
            test_resources
            ;;
        security)
            test_security
            ;;
        performance)
            test_performance
            ;;
        all)
            test_health
            test_connectivity
            test_environment
            test_volumes
            test_resources
            test_security
            test_performance
            ;;
        *)
            echo "Usage: $0 [health|connectivity|environment|volumes|resources|security|performance|all]"
            exit 1
            ;;
    esac

    # Summary
    echo ""
    print_header "Test Summary"
    echo -e "${GREEN}Passed: $TESTS_PASSED${NC}"
    echo -e "${RED}Failed: $TESTS_FAILED${NC}"

    if [ $TESTS_FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ All tests passed!${NC}"
        exit 0
    else
        echo -e "${RED}✗ Some tests failed${NC}"
        exit 1
    fi
}

# Run main function
main "$@"
