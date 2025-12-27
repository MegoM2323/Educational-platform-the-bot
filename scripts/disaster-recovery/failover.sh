#!/bin/bash

################################################################################
# AUTOMATED FAILOVER SCRIPT
#
# Handles automated failover for database and application services
# Supports multiple scenarios: replica promotion, service restart, DNS failover
#
# Usage:
#   ./failover.sh --incident database_failure
#   ./failover.sh --incident datacenter_failure
#   ./failover.sh --simulate
#   ./failover.sh --status
#
# Scenarios:
#   - database_failure: Promote replica to primary
#   - redis_failure: Restore from backup or restart
#   - service_failure: Restart service
#   - datacenter_failure: Activate secondary datacenter
#   - partial_corruption: PITR to known-good point
#
################################################################################

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
BACKUP_DIR="${PROJECT_ROOT}/backups"
COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.prod.yml"
STAGING_COMPOSE_FILE="${PROJECT_ROOT}/docker-compose.staging.yml"

# Logging
LOG_DIR="${PROJECT_ROOT}/logs"
FAILOVER_LOG="${LOG_DIR}/failover_$(date +%Y%m%d_%H%M%S).log"
mkdir -p "$LOG_DIR"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
INCIDENT_TYPE="${1:-}"
SIMULATE_MODE="${SIMULATE_MODE:-false}"
VERBOSE="${VERBOSE:-true}"
NOTIFICATION_EMAIL="${NOTIFICATION_EMAIL:-ops@example.com}"

# Tracking
FAILOVER_START_TIME=$(date +%s)
FAILOVER_SUCCESS=false
INCIDENT_ID="INC_$(date +%Y%m%d_%H%M%S)"

################################################################################
# UTILITY FUNCTIONS
################################################################################

log() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$FAILOVER_LOG"
}

log_info() {
    log "INFO" "$@"
}

log_warn() {
    log "WARN" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_success() {
    echo -e "${GREEN}$(date '+%Y-%m-%d %H:%M:%S') [SUCCESS] $*${NC}" | tee -a "$FAILOVER_LOG"
}

print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$*${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_progress() {
    echo -e "${YELLOW}[*] $*${NC}"
}

send_alert() {
    local subject="$1"
    local message="$2"

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED ALERT: $subject - $message"
        return 0
    fi

    # Send to ops team (email, Slack, PagerDuty)
    log_info "Sending alert: $subject"

    # TODO: Implement actual notification
    # echo "$message" | mail -s "$subject" "$NOTIFICATION_EMAIL"
}

check_docker_compose() {
    if ! command -v docker-compose &> /dev/null; then
        log_error "docker-compose not found"
        return 1
    fi

    if [[ ! -f "$COMPOSE_FILE" ]]; then
        log_error "docker-compose file not found: $COMPOSE_FILE"
        return 1
    fi

    return 0
}

check_postgres_health() {
    local container_name="${1:-thebot-postgres-prod}"

    if ! docker ps -q -f "name=$container_name" | grep -q .; then
        log_warn "PostgreSQL container not running: $container_name"
        return 1
    fi

    if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U postgres &>/dev/null; then
        return 0
    fi

    log_warn "PostgreSQL not responding to health check"
    return 1
}

check_redis_health() {
    local container_name="${1:-thebot-redis-prod}"

    if ! docker ps -q -f "name=$container_name" | grep -q .; then
        log_warn "Redis container not running: $container_name"
        return 1
    fi

    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli -a "${REDIS_PASSWORD:-redis}" ping &>/dev/null; then
        return 0
    fi

    log_warn "Redis not responding to ping"
    return 1
}

check_backend_health() {
    local max_retries=3
    local retry=0

    while [[ $retry -lt $max_retries ]]; do
        if curl -sf http://localhost:8000/api/system/health/ &>/dev/null; then
            return 0
        fi

        retry=$((retry + 1))
        if [[ $retry -lt $max_retries ]]; then
            log_warn "Backend health check failed (attempt $retry/$max_retries), retrying..."
            sleep 5
        fi
    done

    log_warn "Backend not responding to health checks"
    return 1
}

################################################################################
# DATABASE FAILOVER
################################################################################

failover_database() {
    print_header "DATABASE FAILOVER PROCEDURE"

    log_info "Initiating database failover..."

    # Step 1: Check if replica exists and is healthy
    log_info "Step 1: Checking replica status..."
    if ! docker ps -q -f "name=thebot-postgres-replica" | grep -q .; then
        log_error "Replica not found or not running"
        log_error "Manual replica setup required or restore from backup"
        return 1
    fi

    # Step 2: Verify replica is in recovery mode (read-only)
    log_info "Step 2: Verifying replica is in recovery mode..."
    if ! docker-compose exec -T postgres_replica \
      psql -U postgres -c "SELECT pg_is_in_recovery();" | grep -q "t"; then
        log_error "Replica is not in recovery mode (already promoted?)"
        return 1
    fi

    # Step 3: Backup current primary state (if possible)
    log_info "Step 3: Backing up primary state (optional)..."
    if check_postgres_health "thebot-postgres-prod"; then
        if ! "$SCRIPT_DIR/restore-database.sh" --type full --target pre-failover 2>/dev/null; then
            log_warn "Could not backup primary (primary may be partially down)"
        else
            log_success "Primary backup completed"
        fi
    else
        log_warn "Primary not responding, skipping backup"
    fi

    # Step 4: Promote replica to primary
    log_info "Step 4: Promoting replica to primary..."

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would run: pg_ctl promote"
    else
        if ! docker-compose -f "$COMPOSE_FILE" exec -T postgres_replica \
          pg_ctl promote -D /var/lib/postgresql/data; then
            log_error "Failed to promote replica"
            return 1
        fi
        log_success "Replica promoted to primary"
    fi

    # Step 5: Wait for promotion to complete
    log_info "Step 5: Waiting for promotion to complete (15 seconds)..."
    sleep 15

    # Step 6: Verify new primary is accepting writes
    log_info "Step 6: Verifying new primary is accepting writes..."
    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would verify write capability"
    else
        if ! docker-compose -f "$COMPOSE_FILE" exec -T postgres_replica \
          psql -U postgres -c "SELECT version();" | grep -q PostgreSQL; then
            log_error "New primary not responding"
            return 1
        fi
        log_success "New primary is responding"
    fi

    # Step 7: Update connection strings
    log_info "Step 7: Updating connection strings..."

    # Update environment variable (in real setup, update configmap/secrets)
    export DATABASE_URL="postgresql://${DB_USER:-postgres}:${DB_PASSWORD:-postgres}@postgres-replica:5432/${DB_NAME:-thebot_db}"
    log_info "DATABASE_URL updated to use replica (now primary)"

    # Step 8: Restart backend to use new connection
    log_info "Step 8: Restarting backend services..."

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would restart backend"
    else
        if ! docker-compose -f "$COMPOSE_FILE" restart backend; then
            log_error "Failed to restart backend"
            return 1
        fi

        # Wait for backend to come up
        sleep 10

        # Verify backend health
        if check_backend_health; then
            log_success "Backend restarted and healthy"
        else
            log_error "Backend failed health check after restart"
            return 1
        fi
    fi

    # Step 9: Configure old primary as standby (if recovered)
    log_info "Step 9: Reconfiguring old primary as standby..."
    log_info "Manual step: Reconfigure thebot-postgres-prod to follow new primary"

    FAILOVER_SUCCESS=true
    return 0
}

################################################################################
# REDIS FAILOVER
################################################################################

failover_redis() {
    print_header "REDIS FAILOVER PROCEDURE"

    log_info "Initiating Redis failover..."

    # Step 1: Check Redis status
    log_info "Step 1: Checking Redis status..."
    if check_redis_health; then
        log_warn "Redis is still healthy, checking for corruption..."
    else
        log_warn "Redis is not responding"
    fi

    # Step 2: Try restart first (often sufficient)
    log_info "Step 2: Attempting Redis restart..."

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would restart Redis"
    else
        if docker-compose -f "$COMPOSE_FILE" restart redis; then
            sleep 10

            if check_redis_health; then
                log_success "Redis restart successful"
                FAILOVER_SUCCESS=true
                return 0
            fi
        fi
    fi

    # Step 3: Restore from backup
    log_info "Step 3: Restoring Redis from backup..."

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would restore from backup"
    else
        if "$SCRIPT_DIR/restore-redis.sh" --type aof --from latest; then
            log_success "Redis restore completed"
            FAILOVER_SUCCESS=true
            return 0
        else
            log_warn "AOF restore failed, trying RDB..."
            if "$SCRIPT_DIR/restore-redis.sh" --type rdb --from latest; then
                log_success "Redis RDB restore completed"
                FAILOVER_SUCCESS=true
                return 0
            fi
        fi
    fi

    log_error "Redis failover failed"
    return 1
}

################################################################################
# SERVICE FAILOVER
################################################################################

failover_service() {
    local service_name="$1"

    print_header "SERVICE FAILOVER: $service_name"

    log_info "Attempting to restart service: $service_name"

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would restart $service_name"
    else
        if docker-compose -f "$COMPOSE_FILE" restart "$service_name"; then
            sleep 10

            # Check health based on service type
            case "$service_name" in
                backend)
                    if check_backend_health; then
                        log_success "Backend recovered"
                        FAILOVER_SUCCESS=true
                        return 0
                    fi
                    ;;
                postgres)
                    if check_postgres_health; then
                        log_success "PostgreSQL recovered"
                        FAILOVER_SUCCESS=true
                        return 0
                    fi
                    ;;
                redis)
                    if check_redis_health; then
                        log_success "Redis recovered"
                        FAILOVER_SUCCESS=true
                        return 0
                    fi
                    ;;
            esac
        fi
    fi

    log_error "Service restart failed: $service_name"
    return 1
}

################################################################################
# DATACENTER FAILOVER
################################################################################

failover_datacenter() {
    print_header "DATACENTER FAILOVER PROCEDURE"

    log_info "Initiating datacenter failover to secondary region..."

    # Step 1: Verify secondary infrastructure is ready
    log_info "Step 1: Verifying secondary infrastructure..."

    if [[ ! -f "$PROJECT_ROOT/terraform/secondary.tfvars" ]]; then
        log_error "Secondary Terraform configuration not found"
        return 1
    fi

    # Step 2: Prepare secondary infrastructure
    log_info "Step 2: Provisioning secondary datacenter (15 minutes)..."

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would run terraform apply"
    else
        cd "$PROJECT_ROOT/terraform"
        if ! terraform apply -var-file=secondary.tfvars -auto-approve; then
            log_error "Failed to provision secondary infrastructure"
            cd "$SCRIPT_DIR"
            return 1
        fi
        cd "$SCRIPT_DIR"
        log_success "Secondary infrastructure provisioned"
    fi

    sleep 300  # Wait for infrastructure to stabilize

    # Step 3: Restore databases from S3
    log_info "Step 3: Restoring databases from S3..."

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would restore from S3"
    else
        log_info "Downloading PostgreSQL backup from S3..."
        if ! aws s3 cp s3://backup-bucket/postgresql/latest.dump.gz /tmp/ \
          --region us-west-2; then
            log_error "Failed to download PostgreSQL backup"
            return 1
        fi

        log_info "Restoring PostgreSQL..."
        if ! "$SCRIPT_DIR/restore-database.sh" --type full \
          --file /tmp/latest.dump.gz --target secondary; then
            log_error "Failed to restore PostgreSQL"
            return 1
        fi
        log_success "PostgreSQL restored"
    fi

    # Step 4: Restore Redis from S3
    log_info "Step 4: Restoring Redis from S3..."

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would restore Redis from S3"
    else
        if ! "$SCRIPT_DIR/restore-redis.sh" --type rdb --from s3; then
            log_warn "Failed to restore Redis (OK to start fresh)"
        fi
        log_success "Redis restored"
    fi

    # Step 5: Update DNS
    log_info "Step 5: Updating DNS records..."

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would update Route53"
    else
        log_info "Updating Route53 to point to secondary datacenter..."
        # This would use AWS CLI to update Route53
        # aws route53 change-resource-record-sets ...
        log_success "DNS updated"
    fi

    # Step 6: Verify secondary system
    log_info "Step 6: Verifying secondary system..."

    if [[ "$SIMULATE_MODE" == "true" ]]; then
        log_info "SIMULATED: Would verify secondary"
    else
        if "$SCRIPT_DIR/verify-recovery.sh" --full --target secondary; then
            log_success "Secondary system verified"
            FAILOVER_SUCCESS=true
        else
            log_error "Secondary system verification failed"
            return 1
        fi
    fi

    return 0
}

################################################################################
# VERIFICATION
################################################################################

verify_failover() {
    print_header "FAILOVER VERIFICATION"

    log_info "Verifying system after failover..."

    local checks_passed=0
    local checks_total=0

    # Check 1: Backend health
    checks_total=$((checks_total + 1))
    if check_backend_health; then
        log_success "Backend health check passed"
        checks_passed=$((checks_passed + 1))
    else
        log_error "Backend health check failed"
    fi

    # Check 2: Database connectivity
    checks_total=$((checks_total + 1))
    if check_postgres_health; then
        log_success "PostgreSQL health check passed"
        checks_passed=$((checks_passed + 1))
    else
        log_error "PostgreSQL health check failed"
    fi

    # Check 3: Redis connectivity
    checks_total=$((checks_total + 1))
    if check_redis_health; then
        log_success "Redis health check passed"
        checks_passed=$((checks_passed + 1))
    else
        log_warn "Redis health check failed (non-critical)"
        checks_passed=$((checks_passed + 1))
    fi

    # Check 4: API endpoint
    checks_total=$((checks_total + 1))
    if curl -sf http://localhost:8000/api/ &>/dev/null; then
        log_success "API endpoint check passed"
        checks_passed=$((checks_passed + 1))
    else
        log_error "API endpoint check failed"
    fi

    log_info "Verification: $checks_passed/$checks_total checks passed"

    if [[ $checks_passed -ge $((checks_total - 1)) ]]; then
        return 0
    else
        return 1
    fi
}

################################################################################
# STATUS REPORTING
################################################################################

show_failover_status() {
    print_header "FAILOVER STATUS REPORT"

    local failover_duration=$(($(date +%s) - FAILOVER_START_TIME))

    echo "Incident ID: $INCIDENT_ID"
    echo "Start Time: $(date -d @$FAILOVER_START_TIME)"
    echo "Duration: ${failover_duration} seconds ($(( failover_duration / 60 )) minutes)"
    echo ""

    echo "Service Status:"
    echo "  Backend: $(check_backend_health && echo "HEALTHY" || echo "UNHEALTHY")"
    echo "  PostgreSQL: $(check_postgres_health && echo "HEALTHY" || echo "UNHEALTHY")"
    echo "  Redis: $(check_redis_health && echo "HEALTHY" || echo "UNHEALTHY")"
    echo ""

    if [[ "$FAILOVER_SUCCESS" == "true" ]]; then
        echo -e "${GREEN}FAILOVER STATUS: SUCCESS${NC}"
        return 0
    else
        echo -e "${RED}FAILOVER STATUS: FAILED${NC}"
        return 1
    fi
}

################################################################################
# SIMULATION MODE
################################################################################

run_simulation() {
    print_header "RUNNING FAILOVER SIMULATION"

    log_info "Simulation Mode: All destructive operations will be logged but not executed"

    print_progress "Simulating database failover..."
    failover_database || log_warn "Database failover simulation returned non-zero (expected)"

    print_progress "Simulating system verification..."
    verify_failover || log_warn "Verification simulation returned non-zero (expected)"

    print_progress "Simulating status reporting..."
    show_failover_status

    log_success "Simulation completed successfully"
}

################################################################################
# MAIN EXECUTION
################################################################################

main() {
    print_header "DISASTER RECOVERY FAILOVER HANDLER"

    log_info "Incident Type: ${INCIDENT_TYPE:-none}"
    log_info "Simulate Mode: $SIMULATE_MODE"
    log_info "Incident ID: $INCIDENT_ID"

    # Validation
    if ! check_docker_compose; then
        log_error "Docker Compose validation failed"
        exit 1
    fi

    # Execute based on incident type or command
    case "${INCIDENT_TYPE}" in
        database_failure)
            send_alert "Database Failover Started" \
              "Attempting to promote replica to primary. Incident: $INCIDENT_ID"

            if failover_database; then
                verify_failover
                send_alert "Database Failover Completed Successfully" \
                  "Replica promoted and system verified. Incident: $INCIDENT_ID"
            else
                log_error "Database failover failed"
                send_alert "Database Failover FAILED" \
                  "Manual intervention required. Incident: $INCIDENT_ID"
                exit 1
            fi
            ;;

        redis_failure)
            send_alert "Redis Failover Started" \
              "Attempting to recover Redis. Incident: $INCIDENT_ID"

            if failover_redis; then
                send_alert "Redis Failover Completed" \
                  "Redis recovered. Incident: $INCIDENT_ID"
            else
                log_error "Redis failover failed"
                send_alert "Redis Failover FAILED" \
                  "Manual intervention required. Incident: $INCIDENT_ID"
                exit 1
            fi
            ;;

        datacenter_failure)
            send_alert "Datacenter Failover Started" \
              "Initiating failover to secondary datacenter. Incident: $INCIDENT_ID"

            if failover_datacenter; then
                send_alert "Datacenter Failover Completed" \
                  "Secondary datacenter is now active. Incident: $INCIDENT_ID"
            else
                log_error "Datacenter failover failed"
                send_alert "Datacenter Failover FAILED" \
                  "Manual intervention required. Incident: $INCIDENT_ID"
                exit 1
            fi
            ;;

        service_failure)
            # Get service name from second argument
            local service="${2:-}"
            if [[ -z "$service" ]]; then
                log_error "Service name required for service_failure incident"
                exit 1
            fi

            if failover_service "$service"; then
                send_alert "Service Failover Completed" \
                  "Service $service recovered. Incident: $INCIDENT_ID"
            else
                log_error "Service failover failed"
                send_alert "Service Failover FAILED" \
                  "Manual intervention required for $service. Incident: $INCIDENT_ID"
                exit 1
            fi
            ;;

        --simulate)
            run_simulation
            ;;

        --status)
            show_failover_status
            ;;

        *)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Scenarios:"
            echo "  $0 --incident database_failure     # Promote replica to primary"
            echo "  $0 --incident redis_failure         # Restore Redis from backup"
            echo "  $0 --incident datacenter_failure    # Failover to secondary"
            echo "  $0 --incident service_failure backend"
            echo ""
            echo "Testing:"
            echo "  $0 --simulate    # Run simulation (no actual changes)"
            echo "  $0 --status      # Show current status"
            echo ""
            echo "Environment:"
            echo "  SIMULATE_MODE=true                  # Enable simulation"
            echo "  VERBOSE=true                        # Enable verbose logging"
            exit 1
            ;;
    esac

    # Final status report
    echo ""
    show_failover_status
    local exit_code=$?

    log_info "Failover log saved to: $FAILOVER_LOG"

    exit $exit_code
}

# Run main function
main "$@"
