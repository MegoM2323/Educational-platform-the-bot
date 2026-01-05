#!/bin/bash

# THE_BOT Platform - Deployment Utilities
# Contains common functions for deployment scripts

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Check if command exists
check_command() {
    if command -v "$1" &> /dev/null; then
        log_success "Command found: $1"
        return 0
    else
        log_error "Command not found: $1"
        return 1
    fi
}

# Check Docker installation
check_docker() {
    log_info "Checking Docker installation..."
    if ! check_command docker; then
        return 1
    fi

    # Check Docker version
    DOCKER_VERSION=$(docker --version | awk '{print $3}' | cut -d',' -f1)
    log_info "Docker version: $DOCKER_VERSION"

    # Check if Docker daemon is running
    if docker ps > /dev/null 2>&1; then
        log_success "Docker daemon is running"
        return 0
    else
        log_error "Docker daemon is not running"
        return 1
    fi
}

# Check Docker Compose installation
check_docker_compose() {
    log_info "Checking Docker Compose installation..."

    # Try docker compose (v2) first
    if docker compose version > /dev/null 2>&1; then
        COMPOSE_VERSION=$(docker compose version | grep -oP '\d+\.\d+\.\d+' | head -1)
        log_success "Docker Compose v2 found: $COMPOSE_VERSION"
        echo "docker compose"
        return 0
    fi

    # Fallback to docker-compose (v1)
    if check_command docker-compose; then
        COMPOSE_VERSION=$(docker-compose --version | grep -oP '\d+\.\d+\.\d+' | head -1)
        log_success "Docker Compose v1 found: $COMPOSE_VERSION"
        echo "docker-compose"
        return 0
    fi

    log_error "Docker Compose not found"
    return 1
}

# Check disk space
check_disk_space() {
    local required_gb=${1:-5}
    log_info "Checking disk space (required: ${required_gb}GB)..."

    local available_kb=$(df / | awk 'NR==2 {print $4}')
    local available_gb=$((available_kb / 1024 / 1024))

    if [ "$available_gb" -ge "$required_gb" ]; then
        log_success "Disk space OK: ${available_gb}GB available"
        return 0
    else
        log_error "Insufficient disk space: ${available_gb}GB available, ${required_gb}GB required"
        return 1
    fi
}

# Check memory
check_memory() {
    local required_mb=${1:-512}
    log_info "Checking memory (required: ${required_mb}MB)..."

    local available_mb=$(free -m | awk 'NR==2 {print $7}')

    if [ "$available_mb" -ge "$required_mb" ]; then
        log_success "Memory OK: ${available_mb}MB available"
        return 0
    else
        log_error "Insufficient memory: ${available_mb}MB available, ${required_mb}MB required"
        return 1
    fi
}

# Execute remote command via SSH
execute_remote_command() {
    local remote_user=$1
    local remote_host=$2
    local command=$3

    log_info "Executing remote command on $remote_user@$remote_host"

    ssh -o ConnectTimeout=10 -o StrictHostKeyChecking=accept-new \
        "$remote_user@$remote_host" "bash -c '$command'" 2>&1

    return $?
}

# Wait for service to be ready
wait_for_service() {
    local service=$1
    local timeout=${2:-30}
    local elapsed=0

    log_info "Waiting for service $service (timeout: ${timeout}s)..."

    while [ $elapsed -lt $timeout ]; do
        if docker-compose ps "$service" | grep -q "healthy\|Up"; then
            log_success "Service $service is ready"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    log_error "Service $service failed to start within ${timeout}s"
    return 1
}

# Check HTTP endpoint
check_http_endpoint() {
    local url=$1
    local expected_status=${2:-200}
    local retries=${3:-3}
    local attempt=1

    log_info "Checking HTTP endpoint: $url (expected: $expected_status)"

    while [ $attempt -le $retries ]; do
        status=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null)

        if [ "$status" = "$expected_status" ]; then
            log_success "HTTP endpoint OK: $url ($status)"
            return 0
        fi

        log_warn "Attempt $attempt/$retries: got $status, expected $expected_status"
        attempt=$((attempt + 1))
        sleep 2
    done

    log_error "HTTP endpoint failed: $url (got $status, expected $expected_status)"
    return 1
}

# Validate environment file
validate_env_file() {
    local env_file=$1
    local required_vars=("${@:2}")

    log_info "Validating environment file: $env_file"

    if [ ! -f "$env_file" ]; then
        log_error "Environment file not found: $env_file"
        return 1
    fi

    for var in "${required_vars[@]}"; do
        if grep -q "^$var=" "$env_file"; then
            log_success "Found required variable: $var"
        else
            log_error "Missing required variable: $var"
            return 1
        fi
    done

    return 0
}

# Get current timestamp
get_timestamp() {
    date '+%Y%m%d_%H%M%S'
}

# Create backup directory
create_backup_dir() {
    local backup_dir=$1
    log_info "Creating backup directory: $backup_dir"

    mkdir -p "$backup_dir" || {
        log_error "Failed to create backup directory"
        return 1
    }

    log_success "Backup directory created"
    return 0
}

# Archive directory
archive_directory() {
    local source_dir=$1
    local archive_name=$2

    log_info "Archiving directory: $source_dir → $archive_name"

    tar -czf "$archive_name" -C "$(dirname "$source_dir")" "$(basename "$source_dir")" 2>/dev/null || {
        log_error "Failed to create archive"
        return 1
    }

    log_success "Archive created: $archive_name"
    return 0
}

export -f log_info log_success log_warn log_error
export -f check_command check_docker check_docker_compose
export -f check_disk_space check_memory
export -f execute_remote_command wait_for_service check_http_endpoint
export -f validate_env_file get_timestamp create_backup_dir archive_directory
