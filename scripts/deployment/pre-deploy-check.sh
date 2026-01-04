#!/bin/bash

################################################################################
# THE_BOT Platform - Pre-Deployment Checks (22 checks in 5 categories)
#
# Performs comprehensive pre-deployment verification:
# - 6 System checks (SSH, disk, memory, Docker, Docker Compose, network)
# - 4 Git checks (repo, uncommitted, branch, remote)
# - 5 Code checks (Dockerfile, docker-compose, .env, Python, Node.js)
# - 4 Services checks (PostgreSQL, Redis, Nginx, volume paths)
# - 3 Application checks (migrations, static files, Celery)
#
# Usage:
#   ./scripts/deployment/pre-deploy-check.sh
#   ./scripts/deployment/pre-deploy-check.sh --verbose
#   ./scripts/deployment/pre-deploy-check.sh --json
#   ./scripts/deployment/pre-deploy-check.sh --only-category system
#   ./scripts/deployment/pre-deploy-check.sh --remote
#   ./scripts/deployment/pre-deploy-check.sh --dry-run
#
# Exit Codes:
#   0 = all checks passed
#   1 = one or more checks failed
#   2 = critical checks failed (blocking deployment)
#   3 = configuration error
#
################################################################################

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
DEPLOY_ENV="${PROJECT_DIR}/.deploy.env"
UTILS_FILE="${SCRIPT_DIR}/deployment-utils.sh"

if [[ ! -f "$UTILS_FILE" ]]; then
    echo "ERROR: deployment-utils.sh not found at $UTILS_FILE"
    exit 3
fi

source "$UTILS_FILE" || {
    echo "ERROR: Failed to source deployment-utils.sh"
    exit 3
}

trap - EXIT ERR

LOG_DIR="${LOG_DIR:-deployment-logs}"
mkdir -p "$LOG_DIR" 2>/dev/null || true

CHECK_LOG="${LOG_DIR}/pre-deploy-check_$(get_timestamp).log"
touch "$CHECK_LOG" 2>/dev/null || true

VERBOSE=false
JSON_OUTPUT=false
STOP_ON_ERROR=false
ONLY_CATEGORY=""
REMOTE_MODE=false
DRY_RUN=false

TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0
CRITICAL_CHECKS=0

declare -a CHECK_RESULTS=()
declare -a FAILED_DETAILS=()
declare -a WARNING_DETAILS=()

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --verbose)
                VERBOSE=true
                shift
                ;;
            --json)
                JSON_OUTPUT=true
                shift
                ;;
            --stop-on-error)
                STOP_ON_ERROR=true
                shift
                ;;
            --only-category)
                ONLY_CATEGORY="$2"
                shift 2
                ;;
            --remote)
                REMOTE_MODE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                print_error "Unknown option: $1"
                exit 3
                ;;
        esac
    done
}

show_help() {
    cat << 'EOF'
THE_BOT Platform - Pre-Deployment Checks

Usage:
  ./pre-deploy-check.sh [OPTIONS]

Options:
  --verbose              Show detailed output for each check
  --json                 Output results in JSON format
  --stop-on-error        Exit after first failure
  --only-category CAT    Run only specific category (system|git|code|services|app)
  --remote               Run checks on remote server via SSH
  --dry-run              Show checks without executing them
  --help                 Display this help message

Exit Codes:
  0 = All checks passed
  1 = One or more checks failed
  2 = Critical checks failed (blocking deployment)
  3 = Configuration error

Examples:
  ./pre-deploy-check.sh --verbose
  ./pre-deploy-check.sh --json | jq '.'
  ./pre-deploy-check.sh --only-category system
  ./pre-deploy-check.sh --remote --verbose
  ./pre-deploy-check.sh --dry-run --json
EOF
}

log_check() {
    local check_name="$1"
    local status="$2"
    local duration="$3"
    local error_msg="${4:-}"

    if [[ "$DRY_RUN" == true ]]; then
        status="dry-run"
    fi

    local log_line="[${status}] ${check_name} (${duration}ms)"
    [[ -n "$error_msg" ]] && log_line="${log_line} - ${error_msg}"

    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ${log_line}" >> "$CHECK_LOG" 2>/dev/null || true

    CHECK_RESULTS+=("${check_name}|${status}|${duration}|${error_msg}")
}

record_check() {
    local name="$1"
    local status="$2"
    local duration="${3:-0}"
    local detail="${4:-}"

    TOTAL_CHECKS=$((TOTAL_CHECKS + 1))

    if [[ "$status" == "pass" ]]; then
        PASSED_CHECKS=$((PASSED_CHECKS + 1))
        print_success "✓ PASS: $name (${duration}ms)"
    elif [[ "$status" == "fail" ]]; then
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        print_error "✗ FAIL: $name"
        [[ -n "$detail" ]] && print_error "  Reason: $detail"
        FAILED_DETAILS+=("$name: $detail")

        if [[ "$STOP_ON_ERROR" == true ]]; then
            exit 1
        fi
    elif [[ "$status" == "warn" ]]; then
        WARNING_CHECKS=$((WARNING_CHECKS + 1))
        print_warning "⚠ WARN: $name"
        [[ -n "$detail" ]] && print_warning "  Note: $detail"
        WARNING_DETAILS+=("$name: $detail")
    elif [[ "$status" == "critical" ]]; then
        CRITICAL_CHECKS=$((CRITICAL_CHECKS + 1))
        FAILED_CHECKS=$((FAILED_CHECKS + 1))
        print_error "✗✗ CRITICAL: $name - BLOCKS DEPLOYMENT"
        [[ -n "$detail" ]] && print_error "  Reason: $detail"
        FAILED_DETAILS+=("CRITICAL - $name: $detail")
    fi

    log_check "$name" "$status" "$duration" "$detail"
}

load_config() {
    if [[ -f "$DEPLOY_ENV" ]]; then
        source "$DEPLOY_ENV"
        print_info "Loaded configuration from .deploy.env"
        log "Configuration loaded from $DEPLOY_ENV"
    else
        print_warning "No .deploy.env found, using defaults"
        SSH_USER="${SSH_USER:-}"
        SSH_HOST="${SSH_HOST:-}"
        SSH_PORT="${SSH_PORT:-22}"
        REMOTE_PATH="${REMOTE_PATH:-}"
    fi
}

should_skip_category() {
    local category="$1"
    if [[ -n "$ONLY_CATEGORY" ]] && [[ "$ONLY_CATEGORY" != "$category" ]]; then
        return 0
    fi
    return 1
}

category_header() {
    local category="$1"
    print_header "CHECKS: $category"
}

check_duration() {
    local start_time=$1
    echo $(( ($(date +%s%N) - start_time) / 1000000 ))
}

check_ssh_connection() {
    [[ "$(should_skip_category system)" == "true" ]] && return

    local ssh_host="${SSH_HOST:-}"
    local ssh_user="${SSH_USER:-}"
    local ssh_port="${SSH_PORT:-22}"

    [[ -z "$ssh_host" ]] && {
        record_check "SSH connection" "fail" 0 "SSH_HOST not configured"
        return
    }
    [[ -z "$ssh_user" ]] && {
        record_check "SSH connection" "fail" 0 "SSH_USER not configured"
        return
    }

    local start_time=$(date +%s%N)

    if [[ "$REMOTE_MODE" == true ]]; then
        if timeout 10 ssh_check "$ssh_user" "$ssh_host" 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "SSH connection to $ssh_host" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "SSH connection to $ssh_host" "critical" "$duration" "Cannot SSH to $ssh_user@$ssh_host:$ssh_port"
        fi
    else
        local duration=$(check_duration $start_time)
        record_check "SSH connection" "warn" "$duration" "Run with --remote to verify SSH connectivity"
    fi
}

check_disk_space() {
    [[ "$(should_skip_category system)" == "true" ]] && return

    local start_time=$(date +%s%N)
    local min_space=5242880

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        local available=$(ssh_exec "df ${REMOTE_PATH:-/home} | tail -1 | awk '{print \$4}'" "$SSH_USER" "$SSH_HOST" 2>/dev/null || echo "0")
        if [[ "$available" -gt "$min_space" ]]; then
            local duration=$(check_duration $start_time)
            record_check "Disk space >= 5GB" "pass" "$duration" "Available: $(human_readable_size $((available * 1024)))"
        else
            local duration=$(check_duration $start_time)
            record_check "Disk space >= 5GB" "critical" "$duration" "Only $(human_readable_size $((available * 1024))) available"
        fi
    else
        local duration=$(check_duration $start_time)
        record_check "Disk space >= 5GB" "warn" "$duration" "Run with --remote to verify on server"
    fi
}

check_memory() {
    [[ "$(should_skip_category system)" == "true" ]] && return

    local start_time=$(date +%s%N)
    local min_memory=524288

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        local available=$(ssh_exec "free | grep Mem | awk '{print \$7}'" "$SSH_USER" "$SSH_HOST" 2>/dev/null || echo "0")
        if [[ "$available" -gt "$min_memory" ]]; then
            local duration=$(check_duration $start_time)
            record_check "Memory >= 512MB available" "pass" "$duration" "Available: $(human_readable_size $((available * 1024)))"
        else
            local duration=$(check_duration $start_time)
            record_check "Memory >= 512MB available" "warn" "$duration" "Only $(human_readable_size $((available * 1024))) available"
        fi
    else
        local duration=$(check_duration $start_time)
        record_check "Memory >= 512MB available" "warn" "$duration" "Run with --remote to verify"
    fi
}

check_docker_version() {
    [[ "$(should_skip_category system)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        local docker_version=$(ssh_exec "docker --version 2>/dev/null | awk '{print \$3}' | sed 's/,//'" "$SSH_USER" "$SSH_HOST" 2>/dev/null || echo "")
        if [[ -n "$docker_version" ]]; then
            local major=$(echo "$docker_version" | cut -d. -f1)
            if [[ "$major" -ge 20 ]]; then
                local duration=$(check_duration $start_time)
                record_check "Docker version >= 20.10" "pass" "$duration" "Version: $docker_version"
            else
                local duration=$(check_duration $start_time)
                record_check "Docker version >= 20.10" "fail" "$duration" "Found: $docker_version"
            fi
        else
            local duration=$(check_duration $start_time)
            record_check "Docker version >= 20.10" "critical" "$duration" "Docker not installed or not accessible"
        fi
    else
        if command -v docker &>/dev/null; then
            local docker_version=$(docker --version 2>/dev/null | awk '{print $3}' | sed 's/,//')
            local start_time=$(date +%s%N)
            local major=$(echo "$docker_version" | cut -d. -f1)
            if [[ "$major" -ge 20 ]]; then
                local duration=$(check_duration $start_time)
                record_check "Docker version >= 20.10" "pass" "$duration" "Version: $docker_version"
            else
                local duration=$(check_duration $start_time)
                record_check "Docker version >= 20.10" "fail" "$duration" "Found: $docker_version"
            fi
        else
            local duration=$(check_duration $start_time)
            record_check "Docker version >= 20.10" "critical" "$duration" "Docker not installed"
        fi
    fi
}

check_docker_compose() {
    [[ "$(should_skip_category system)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        local dc_version=$(ssh_exec "docker-compose --version 2>/dev/null | awk '{print \$NF}' | sed 's/v//'" "$SSH_USER" "$SSH_HOST" 2>/dev/null || echo "")
        if [[ -n "$dc_version" ]]; then
            local major=$(echo "$dc_version" | cut -d. -f1)
            if [[ "$major" -ge 2 ]]; then
                local duration=$(check_duration $start_time)
                record_check "Docker Compose v2+" "pass" "$duration" "Version: v$dc_version"
            else
                local duration=$(check_duration $start_time)
                record_check "Docker Compose v2+" "fail" "$duration" "Found v$dc_version, need v2+"
            fi
        else
            local duration=$(check_duration $start_time)
            record_check "Docker Compose v2+" "critical" "$duration" "Not installed or not accessible"
        fi
    else
        if command -v docker-compose &>/dev/null; then
            local dc_version=$(docker-compose --version 2>/dev/null | awk '{print $NF}' | sed 's/v//')
            local major=$(echo "$dc_version" | cut -d. -f1)
            if [[ "$major" -ge 2 ]]; then
                local duration=$(check_duration $start_time)
                record_check "Docker Compose v2+" "pass" "$duration" "Version: v$dc_version"
            else
                local duration=$(check_duration $start_time)
                record_check "Docker Compose v2+" "fail" "$duration" "Found v$dc_version, need v2+"
            fi
        else
            local duration=$(check_duration $start_time)
            record_check "Docker Compose v2+" "critical" "$duration" "Not installed"
        fi
    fi
}

check_network_connectivity() {
    [[ "$(should_skip_category system)" == "true" ]] && return

    local start_time=$(date +%s%N)
    local ssh_host="${SSH_HOST:-}"

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$ssh_host" ]]; then
        if timeout 5 ssh_exec "ping -c 1 8.8.8.8 > /dev/null 2>&1" "$SSH_USER" "$ssh_host" 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "Network connectivity to external services" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Network connectivity to external services" "warn" "$duration" "Cannot reach 8.8.8.8 (may be blocked)"
        fi
    else
        if timeout 5 ping -c 1 8.8.8.8 > /dev/null 2>&1; then
            local duration=$(check_duration $start_time)
            record_check "Network connectivity to external services" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Network connectivity to external services" "warn" "$duration" "Cannot reach 8.8.8.8"
        fi
    fi
}

check_git_repo() {
    [[ "$(should_skip_category git)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if [[ -d "${PROJECT_DIR}/.git" ]]; then
        local duration=$(check_duration $start_time)
        record_check ".git directory exists" "pass" "$duration"
    else
        local duration=$(check_duration $start_time)
        record_check ".git directory exists" "critical" "$duration" "Not a git repository"
    fi
}

check_uncommitted_changes() {
    [[ "$(should_skip_category git)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if git -C "$PROJECT_DIR" diff-index --quiet HEAD -- 2>/dev/null; then
        local duration=$(check_duration $start_time)
        record_check "No uncommitted changes" "pass" "$duration"
    else
        local duration=$(check_duration $start_time)
        record_check "No uncommitted changes" "fail" "$duration" "Uncommitted changes found in working directory"
        if [[ "$VERBOSE" == true ]]; then
            print_info "Changed files:"
            git -C "$PROJECT_DIR" status --short
        fi
    fi
}

check_git_branch() {
    [[ "$(should_skip_category git)" == "true" ]] && return

    local start_time=$(date +%s%N)
    local current_branch=$(git -C "$PROJECT_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
    local expected_branch="${GIT_BRANCH:-main}"

    local duration=$(check_duration $start_time)
    if [[ "$current_branch" == "$expected_branch" ]]; then
        record_check "Current branch is $expected_branch" "pass" "$duration" "Branch: $current_branch"
    else
        record_check "Current branch is $expected_branch" "warn" "$duration" "Current: $current_branch, Expected: $expected_branch"
    fi
}

check_git_remote() {
    [[ "$(should_skip_category git)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if git -C "$PROJECT_DIR" remote -v 2>/dev/null | grep -q "origin"; then
        if git -C "$PROJECT_DIR" ls-remote origin HEAD > /dev/null 2>&1; then
            local duration=$(check_duration $start_time)
            record_check "Remote origin is accessible" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Remote origin is accessible" "fail" "$duration" "Cannot reach origin"
        fi
    else
        local duration=$(check_duration $start_time)
        record_check "Remote origin is accessible" "fail" "$duration" "No origin remote configured"
    fi
}

check_dockerfile() {
    [[ "$(should_skip_category code)" == "true" ]] && return

    local start_time=$(date +%s%N)

    local dockerfile="${PROJECT_DIR}/backend/Dockerfile"
    if [[ -f "$dockerfile" ]]; then
        if grep -q "^FROM\|^RUN\|^CMD" "$dockerfile" 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "Dockerfile exists and has valid syntax" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Dockerfile exists and has valid syntax" "fail" "$duration" "Dockerfile syntax invalid"
        fi
    else
        local duration=$(check_duration $start_time)
        record_check "Dockerfile exists and has valid syntax" "critical" "$duration" "Dockerfile not found"
    fi
}

check_docker_compose_file() {
    [[ "$(should_skip_category code)" == "true" ]] && return

    local start_time=$(date +%s%N)

    local compose_file="${PROJECT_DIR}/docker-compose.prod.yml"
    if [[ ! -f "$compose_file" ]]; then
        local duration=$(check_duration $start_time)
        record_check "docker-compose.prod.yml exists and is valid YAML" "critical" "$duration" "File not found"
        return
    fi

    if command -v yamllint &>/dev/null; then
        if yamllint -d relaxed "$compose_file" > /dev/null 2>&1; then
            local duration=$(check_duration $start_time)
            record_check "docker-compose.prod.yml exists and is valid YAML" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "docker-compose.prod.yml exists and is valid YAML" "fail" "$duration" "Invalid YAML syntax"
        fi
    else
        if python3 -c "import yaml; yaml.safe_load(open('$compose_file'))" 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "docker-compose.prod.yml exists and is valid YAML" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "docker-compose.prod.yml exists and is valid YAML" "warn" "$duration" "Cannot validate YAML (yamllint not installed)"
        fi
    fi
}

check_env_file() {
    [[ "$(should_skip_category code)" == "true" ]] && return

    local start_time=$(date +%s%N)

    local env_file="${PROJECT_DIR}/.env.production"
    if [[ ! -f "$env_file" ]]; then
        local duration=$(check_duration $start_time)
        record_check ".env file exists and has required variables" "critical" "$duration" ".env.production not found"
        return
    fi

    source "$env_file" 2>/dev/null || true

    local required_vars=("SECRET_KEY" "DATABASE_URL" "REDIS_URL" "ALLOWED_HOSTS")
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [[ -z "${!var:-}" ]]; then
            missing_vars+=("$var")
        fi
    done

    local duration=$(check_duration $start_time)
    if [[ ${#missing_vars[@]} -eq 0 ]]; then
        record_check ".env file exists and has required variables" "pass" "$duration"
    else
        record_check ".env file exists and has required variables" "fail" "$duration" "Missing: ${missing_vars[*]}"
    fi
}

check_python_version() {
    [[ "$(should_skip_category code)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        local python_version=$(ssh_exec "python3 --version 2>/dev/null | awk '{print \$2}'" "$SSH_USER" "$SSH_HOST" 2>/dev/null || echo "")
        if [[ -n "$python_version" ]]; then
            local major=$(echo "$python_version" | cut -d. -f1)
            local minor=$(echo "$python_version" | cut -d. -f2)
            if [[ "$major" -eq 3 ]] && [[ "$minor" -ge 10 ]]; then
                local duration=$(check_duration $start_time)
                record_check "Python 3.10+ installed" "pass" "$duration" "Version: $python_version"
            else
                local duration=$(check_duration $start_time)
                record_check "Python 3.10+ installed" "fail" "$duration" "Found: $python_version, need 3.10+"
            fi
        else
            local duration=$(check_duration $start_time)
            record_check "Python 3.10+ installed" "critical" "$duration" "Python3 not found"
        fi
    else
        if command -v python3 &>/dev/null; then
            local python_version=$(python3 --version 2>&1 | awk '{print $2}')
            local major=$(echo "$python_version" | cut -d. -f1)
            local minor=$(echo "$python_version" | cut -d. -f2)
            if [[ "$major" -eq 3 ]] && [[ "$minor" -ge 10 ]]; then
                local duration=$(check_duration $start_time)
                record_check "Python 3.10+ installed" "pass" "$duration" "Version: $python_version"
            else
                local duration=$(check_duration $start_time)
                record_check "Python 3.10+ installed" "fail" "$duration" "Found: $python_version"
            fi
        else
            local duration=$(check_duration $start_time)
            record_check "Python 3.10+ installed" "critical" "$duration" "Not found"
        fi
    fi
}

check_nodejs_version() {
    [[ "$(should_skip_category code)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        local node_version=$(ssh_exec "node --version 2>/dev/null | sed 's/v//'" "$SSH_USER" "$SSH_HOST" 2>/dev/null || echo "")
        if [[ -n "$node_version" ]]; then
            local major=$(echo "$node_version" | cut -d. -f1)
            if [[ "$major" -ge 18 ]]; then
                local duration=$(check_duration $start_time)
                record_check "Node.js 18+ installed" "pass" "$duration" "Version: $node_version"
            else
                local duration=$(check_duration $start_time)
                record_check "Node.js 18+ installed" "warn" "$duration" "Found: $node_version"
            fi
        else
            local duration=$(check_duration $start_time)
            record_check "Node.js 18+ installed" "warn" "$duration" "Not found (optional)"
        fi
    else
        if command -v node &>/dev/null; then
            local node_version=$(node --version 2>&1 | sed 's/v//')
            local major=$(echo "$node_version" | cut -d. -f1)
            if [[ "$major" -ge 18 ]]; then
                local duration=$(check_duration $start_time)
                record_check "Node.js 18+ installed" "pass" "$duration" "Version: $node_version"
            else
                local duration=$(check_duration $start_time)
                record_check "Node.js 18+ installed" "warn" "$duration" "Found: $node_version"
            fi
        else
            local duration=$(check_duration $start_time)
            record_check "Node.js 18+ installed" "warn" "$duration" "Not found (optional)"
        fi
    fi
}

check_postgresql_port() {
    [[ "$(should_skip_category services)" == "true" ]] && return

    local start_time=$(date +%s%N)
    local db_port="${DB_PORT:-5432}"

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        if ! ssh_exec "lsof -i :$db_port > /dev/null 2>&1" "$SSH_USER" "$SSH_HOST" 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "PostgreSQL port ($db_port) not in use" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "PostgreSQL port ($db_port) not in use" "warn" "$duration" "Port already in use"
        fi
    else
        if ! lsof -i ":$db_port" > /dev/null 2>&1; then
            local duration=$(check_duration $start_time)
            record_check "PostgreSQL port ($db_port) not in use" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "PostgreSQL port ($db_port) not in use" "warn" "$duration" "Port already in use"
        fi
    fi
}

check_redis_port() {
    [[ "$(should_skip_category services)" == "true" ]] && return

    local start_time=$(date +%s%N)
    local redis_port="${REDIS_PORT:-6379}"

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        if ! ssh_exec "lsof -i :$redis_port > /dev/null 2>&1" "$SSH_USER" "$SSH_HOST" 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "Redis port ($redis_port) not in use" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Redis port ($redis_port) not in use" "warn" "$duration" "Port already in use"
        fi
    else
        if ! lsof -i ":$redis_port" > /dev/null 2>&1; then
            local duration=$(check_duration $start_time)
            record_check "Redis port ($redis_port) not in use" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Redis port ($redis_port) not in use" "warn" "$duration" "Port already in use"
        fi
    fi
}

check_nginx_port() {
    [[ "$(should_skip_category services)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        if ! ssh_exec "lsof -i :80 > /dev/null 2>&1 || lsof -i :443 > /dev/null 2>&1" "$SSH_USER" "$SSH_HOST" 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "Nginx ports (80/443) not in use" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Nginx ports (80/443) not in use" "warn" "$duration" "Ports already in use"
        fi
    else
        if ! (lsof -i :80 > /dev/null 2>&1 || lsof -i :443 > /dev/null 2>&1); then
            local duration=$(check_duration $start_time)
            record_check "Nginx ports (80/443) not in use" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Nginx ports (80/443) not in use" "warn" "$duration" "Ports already in use"
        fi
    fi
}

check_volume_mounts() {
    [[ "$(should_skip_category services)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        local db_backup_path="${DB_BACKUP_PATH:-/home/neil/backups/db}"
        if ssh_exec "test -d '$db_backup_path' && test -w '$db_backup_path'" "$SSH_USER" "$SSH_HOST" 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "Required volume mount paths exist and accessible" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Required volume mount paths exist and accessible" "fail" "$duration" "Backup path not accessible: $db_backup_path"
        fi
    else
        local duration=$(check_duration $start_time)
        record_check "Required volume mount paths exist and accessible" "warn" "$duration" "Run with --remote to verify"
    fi
}

check_pending_migrations() {
    [[ "$(should_skip_category app)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        local pending=$(ssh_exec "cd $REMOTE_PATH && python manage.py showmigrations --check 2>/dev/null || echo 'check'" "$SSH_USER" "$SSH_HOST" 2>/dev/null)
        if [[ "$pending" == "ok" ]]; then
            local duration=$(check_duration $start_time)
            record_check "No pending database migrations" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "No pending database migrations" "warn" "$duration" "Pending migrations will be applied during deployment"
        fi
    else
        if cd "$PROJECT_DIR/backend" && python manage.py showmigrations --check 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "No pending database migrations" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "No pending database migrations" "warn" "$duration" "Pending migrations will be applied during deployment"
        fi
    fi
}

check_static_files() {
    [[ "$(should_skip_category app)" == "true" ]] && return

    local start_time=$(date +%s%N)

    local static_path="${PROJECT_DIR}/backend/staticfiles"
    if [[ -d "$static_path" ]] && [[ -w "$static_path" ]]; then
        local duration=$(check_duration $start_time)
        record_check "Static files directory exists and writable" "pass" "$duration"
    else
        local duration=$(check_duration $start_time)
        record_check "Static files directory exists and writable" "warn" "$duration" "Will be created during deployment (COLLECT_STATIC=true)"
    fi
}

check_celery_queue() {
    [[ "$(should_skip_category app)" == "true" ]] && return

    local start_time=$(date +%s%N)

    if [[ "$REMOTE_MODE" == true ]] && [[ -n "$SSH_HOST" ]]; then
        if ssh_exec "redis-cli -h redis ping > /dev/null 2>&1" "$SSH_USER" "$SSH_HOST" 2>/dev/null; then
            local duration=$(check_duration $start_time)
            record_check "Celery queue accessible and responding" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Celery queue accessible and responding" "warn" "$duration" "Redis not accessible (will start during deployment)"
        fi
    else
        if command -v redis-cli &>/dev/null && redis-cli ping > /dev/null 2>&1; then
            local duration=$(check_duration $start_time)
            record_check "Celery queue accessible and responding" "pass" "$duration"
        else
            local duration=$(check_duration $start_time)
            record_check "Celery queue accessible and responding" "warn" "$duration" "Redis not accessible locally (check remote server)"
        fi
    fi
}

output_summary() {
    if [[ "$JSON_OUTPUT" == true ]]; then
        output_json_summary
    else
        output_text_summary
    fi
}

output_text_summary() {
    print_header "DEPLOYMENT READINESS SUMMARY"

    echo "Checks Summary:"
    echo "  Passed:   $PASSED_CHECKS"
    echo "  Warnings: $WARNING_CHECKS"
    echo "  Failed:   $FAILED_CHECKS"
    echo "  Critical: $CRITICAL_CHECKS"
    echo "  Total:    $TOTAL_CHECKS"
    echo ""

    if [[ ${#FAILED_DETAILS[@]} -gt 0 ]]; then
        echo "Failed Checks:"
        for detail in "${FAILED_DETAILS[@]}"; do
            echo "  - $detail"
        done
        echo ""
    fi

    if [[ ${#WARNING_DETAILS[@]} -gt 0 ]]; then
        echo "Warnings:"
        for detail in "${WARNING_DETAILS[@]}"; do
            echo "  - $detail"
        done
        echo ""
    fi

    if [[ "$CRITICAL_CHECKS" -gt 0 ]]; then
        print_error "DEPLOYMENT BLOCKED - Critical failures detected"
        exit 2
    elif [[ "$FAILED_CHECKS" -gt 0 ]]; then
        print_error "DEPLOYMENT BLOCKED - Failures detected"
        exit 1
    elif [[ "$WARNING_CHECKS" -gt 0 ]]; then
        print_warning "DEPLOYMENT ALLOWED WITH CAUTION - Review $WARNING_CHECKS warnings"
        exit 0
    else
        print_success "DEPLOYMENT READY - All checks passed"
        exit 0
    fi
}

output_json_summary() {
    local check_id="pre-deploy-check-$(get_timestamp)"
    local timestamp=$(date -u '+%Y-%m-%dT%H:%M:%SZ')

    cat > "${LOG_DIR}/${check_id}.json" << JSONEOF
{
  "check_id": "$check_id",
  "timestamp": "$timestamp",
  "total_checks": $TOTAL_CHECKS,
  "passed": $PASSED_CHECKS,
  "failed": $FAILED_CHECKS,
  "warnings": $WARNING_CHECKS,
  "critical": $CRITICAL_CHECKS,
  "categories": {
    "system": {"total": 6, "passed": $([[ "$(should_skip_category system)" == true ]] && echo 0 || echo "$PASSED_CHECKS"), "failed": 0},
    "git": {"total": 4, "passed": $([[ "$(should_skip_category git)" == true ]] && echo 0 || echo "$PASSED_CHECKS"), "failed": 0},
    "code": {"total": 5, "passed": $([[ "$(should_skip_category code)" == true ]] && echo 0 || echo "$PASSED_CHECKS"), "failed": 0},
    "services": {"total": 4, "passed": $([[ "$(should_skip_category services)" == true ]] && echo 0 || echo "$PASSED_CHECKS"), "failed": 0},
    "app": {"total": 3, "passed": $([[ "$(should_skip_category app)" == true ]] && echo 0 || echo "$PASSED_CHECKS"), "failed": 0}
  },
  "checks": [
JSONEOF

    for result in "${CHECK_RESULTS[@]}"; do
        IFS='|' read -r name status duration error <<< "$result"
        cat >> "${LOG_DIR}/${check_id}.json" << JSONEOF
    {"name": "$name", "status": "$status", "duration_ms": $duration, "error": "$error"},
JSONEOF
    done

    sed -i '$ s/,$//' "${LOG_DIR}/${check_id}.json"

    cat >> "${LOG_DIR}/${check_id}.json" << JSONEOF
  ]
}
JSONEOF

    cat "${LOG_DIR}/${check_id}.json"
    echo ""
    print_success "JSON report saved to ${LOG_DIR}/${check_id}.json"
}

main() {
    parse_arguments "$@"

    load_config

    if [[ "$DRY_RUN" == true ]]; then
        print_info "Running in DRY-RUN mode - no changes will be made"
    fi

    if [[ "$ONLY_CATEGORY" != "" ]]; then
        print_info "Running only category: $ONLY_CATEGORY"
    fi

    print_header "THE_BOT PLATFORM - PRE-DEPLOYMENT CHECKS"

    if ! should_skip_category system; then
        category_header "SYSTEM (6 checks)"
        check_ssh_connection
        check_disk_space
        check_memory
        check_docker_version
        check_docker_compose
        check_network_connectivity
    fi

    if ! should_skip_category git; then
        category_header "GIT (4 checks)"
        check_git_repo
        check_uncommitted_changes
        check_git_branch
        check_git_remote
    fi

    if ! should_skip_category code; then
        category_header "CODE (5 checks)"
        check_dockerfile
        check_docker_compose_file
        check_env_file
        check_python_version
        check_nodejs_version
    fi

    if ! should_skip_category services; then
        category_header "SERVICES (4 checks)"
        check_postgresql_port
        check_redis_port
        check_nginx_port
        check_volume_mounts
    fi

    if ! should_skip_category app; then
        category_header "APPLICATION (3 checks)"
        check_pending_migrations
        check_static_files
        check_celery_queue
    fi

    output_summary
}

main "$@"
