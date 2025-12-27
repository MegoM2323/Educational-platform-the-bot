#!/bin/bash

################################################################################
# Automated Blocklist Update Script
#
# Назначение:
# - Ежедневное обновление списков блокировок IP
# - Интеграция с AbuseIPDB и Spamhaus
# - Автоматическое обновление WAF правил AWS
# - Логирование и мониторинг
#
# Установка Cron:
# 0 2 * * * /path/to/update-blocklist.sh >> /var/log/firewall-update.log 2>&1
# (Запускается каждый день в 2:00 AM)
#
# Требуемые переменные окружения:
# - ABUSEIPDB_API_KEY: API ключ AbuseIPDB
# - AWS_REGION: Регион AWS
# - PROJECT_NAME: Имя проекта в WAF
# - SLACK_WEBHOOK_URL: (опционально) Webhook для уведомлений
#
################################################################################

set -e  # Выход при ошибке

# ============================================================
# CONFIGURATION
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
INFRASTRUCTURE_DIR="${SCRIPT_DIR}/infrastructure"
SECURITY_DIR="${INFRASTRUCTURE_DIR}/security"
DATA_DIR="${SECURITY_DIR}/ip-reputation-data"
LOG_DIR="${SCRIPT_DIR}/logs"
LOG_FILE="${LOG_DIR}/blocklist-update.log"

# Ensure directories exist
mkdir -p "${DATA_DIR}" "${LOG_DIR}"

# Configuration from environment or defaults
ABUSEIPDB_API_KEY="${ABUSEIPDB_API_KEY:=}"
AWS_REGION="${AWS_REGION:=us-east-1}"
PROJECT_NAME="${PROJECT_NAME:=thebot}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:=}"
PYTHON_SCRIPT="${SECURITY_DIR}/ip-reputation.py"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================================
# LOGGING FUNCTIONS
# ============================================================

log() {
    echo "[${TIMESTAMP}] INFO: $*" | tee -a "${LOG_FILE}"
}

log_error() {
    echo "[${TIMESTAMP}] ERROR: $*" | tee -a "${LOG_FILE}" >&2
}

log_warning() {
    echo "[${TIMESTAMP}] WARNING: $*" | tee -a "${LOG_FILE}"
}

log_success() {
    echo "[${TIMESTAMP}] SUCCESS: $*" | tee -a "${LOG_FILE}"
}

# ============================================================
# NOTIFICATION FUNCTIONS
# ============================================================

notify_slack() {
    local message="$1"
    local level="${2:=info}"  # info, warning, error, success

    if [[ -z "${SLACK_WEBHOOK_URL}" ]]; then
        return
    fi

    local color="good"
    case "${level}" in
        warning) color="warning" ;;
        error) color="danger" ;;
        success) color="good" ;;
    esac

    local payload=$(cat <<EOF
{
    "attachments": [
        {
            "color": "${color}",
            "title": "Blocklist Update - ${level}",
            "text": "${message}",
            "footer": "THE_BOT Security System",
            "ts": $(date +%s)
        }
    ]
}
EOF
)

    curl -X POST -H 'Content-type: application/json' \
        --data "${payload}" \
        "${SLACK_WEBHOOK_URL}" \
        2>/dev/null || true
}

# ============================================================
# VALIDATION FUNCTIONS
# ============================================================

validate_requirements() {
    log "Validating requirements..."

    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is not installed"
        return 1
    fi

    # Check AWS CLI
    if ! command -v aws &> /dev/null; then
        log_error "AWS CLI is not installed"
        return 1
    fi

    # Check curl
    if ! command -v curl &> /dev/null; then
        log_error "curl is not installed"
        return 1
    fi

    # Check Python script exists
    if [[ ! -f "${PYTHON_SCRIPT}" ]]; then
        log_error "Python script not found: ${PYTHON_SCRIPT}"
        return 1
    fi

    # Check API key
    if [[ -z "${ABUSEIPDB_API_KEY}" ]]; then
        log_warning "ABUSEIPDB_API_KEY is not set - AbuseIPDB checks will be skipped"
    fi

    log_success "All requirements validated"
    return 0
}

# ============================================================
# BACKUP FUNCTIONS
# ============================================================

backup_current_lists() {
    log "Backing up current blocklists..."

    local backup_timestamp=$(date '+%Y%m%d_%H%M%S')
    local backup_dir="${DATA_DIR}/backups/${backup_timestamp}"

    mkdir -p "${backup_dir}"

    # Backup JSON files
    for file in "${DATA_DIR}"/*.json; do
        if [[ -f "${file}" ]]; then
            cp "${file}" "${backup_dir}/" || true
        fi
    done

    log_success "Backup created: ${backup_dir}"

    # Keep only last 7 days of backups
    find "${DATA_DIR}/backups" -mindepth 1 -maxdepth 1 -type d -mtime +7 -exec rm -rf {} + || true

    return 0
}

# ============================================================
# UPDATE FUNCTIONS
# ============================================================

update_blocklists() {
    log "Starting blocklist update..."

    local start_time=$(date +%s)

    # Export environment for Python script
    export ABUSEIPDB_API_KEY
    export AWS_REGION
    export PYTHONPATH="${INFRASTRUCTURE_DIR}:${PYTHONPATH}"

    # Run Python update script
    if python3 "${PYTHON_SCRIPT}" --update --project "${PROJECT_NAME}"; then
        local end_time=$(date +%s)
        local duration=$((end_time - start_time))

        log_success "Blocklist update completed in ${duration}s"
        return 0
    else
        log_error "Blocklist update failed"
        return 1
    fi
}

# ============================================================
# VERIFICATION FUNCTIONS
# ============================================================

verify_blocklist_updates() {
    log "Verifying blocklist updates..."

    local abuseipdb_file="${DATA_DIR}/abuseipdb.json"
    local spamhaus_file="${DATA_DIR}/spamhaus.json"
    local combined_file="${DATA_DIR}/combined-blocklist.json"

    # Check if files were updated in last hour
    local current_time=$(date +%s)
    local one_hour_ago=$((current_time - 3600))

    for file in "${abuseipdb_file}" "${spamhaus_file}" "${combined_file}"; do
        if [[ -f "${file}" ]]; then
            local file_time=$(stat -f%m "${file}" 2>/dev/null || stat -c%Y "${file}")

            if [[ ${file_time} -gt ${one_hour_ago} ]]; then
                local count=$(jq '.count // (.total_ips // 0)' "${file}" 2>/dev/null || echo "0")
                log_success "$(basename ${file}): ${count} entries"
            else
                log_warning "$(basename ${file}) was not updated recently"
            fi
        else
            log_warning "$(basename ${file}) not found"
        fi
    done

    return 0
}

# ============================================================
# WAF UPDATE VERIFICATION
# ============================================================

verify_waf_updates() {
    log "Verifying WAF IP set updates..."

    local ip_sets=(
        "${PROJECT_NAME}-abuseipdb-ips"
        "${PROJECT_NAME}-spamhaus-ips"
        "${PROJECT_NAME}-custom-blocked-ips"
    )

    for ip_set_name in "${ip_sets[@]}"; do
        # Get IP set info
        local result=$(aws wafv2 list-ip-sets \
            --scope REGIONAL \
            --region "${AWS_REGION}" \
            --output json 2>/dev/null || echo '{}')

        local ip_set=$(echo "${result}" | jq -r ".IPSets[] | select(.Name==\"${ip_set_name}\") | .Id" 2>/dev/null)

        if [[ -n "${ip_set}" ]]; then
            local ip_set_details=$(aws wafv2 get-ip-set \
                --scope REGIONAL \
                --region "${AWS_REGION}" \
                --name "${ip_set_name}" \
                --id "${ip_set}" \
                --output json 2>/dev/null || echo '{}')

            local count=$(echo "${ip_set_details}" | jq '.IPSet.Addresses | length' 2>/dev/null || echo "0")
            log_success "WAF IP set ${ip_set_name}: ${count} addresses"
        else
            log_warning "WAF IP set ${ip_set_name} not found"
        fi
    done

    return 0
}

# ============================================================
# STATISTICS COLLECTION
# ============================================================

collect_statistics() {
    log "Collecting update statistics..."

    local combined_file="${DATA_DIR}/combined-blocklist.json"

    if [[ -f "${combined_file}" ]]; then
        local stats=$(jq '.' "${combined_file}" 2>/dev/null || echo '{}')

        local total_ips=$(echo "${stats}" | jq '.total_ips // 0' 2>/dev/null)
        local abuseipdb=$(echo "${stats}" | jq '.abuseipdb_count // 0' 2>/dev/null)
        local spamhaus=$(echo "${stats}" | jq '.spamhaus_count // 0' 2>/dev/null)

        log "=== UPDATE STATISTICS ==="
        log "Total IPs blocked: ${total_ips}"
        log "AbuseIPDB entries: ${abuseipdb}"
        log "Spamhaus entries: ${spamhaus}"

        # Send Slack notification if webhook configured
        if [[ -n "${SLACK_WEBHOOK_URL}" ]]; then
            notify_slack "Blocklist update completed\n- Total IPs: ${total_ips}\n- AbuseIPDB: ${abuseipdb}\n- Spamhaus: ${spamhaus}" "success"
        fi
    fi

    return 0
}

# ============================================================
# CLEANUP FUNCTIONS
# ============================================================

cleanup_old_data() {
    log "Cleaning up old data..."

    # Remove JSON files older than 30 days
    find "${DATA_DIR}" -maxdepth 1 -name "*.json" -mtime +30 -delete || true

    # Keep only last 14 days of logs
    find "${LOG_DIR}" -maxdepth 1 -name "*.log" -mtime +14 -delete || true

    log_success "Cleanup completed"
    return 0
}

# ============================================================
# ERROR HANDLING
# ============================================================

on_error() {
    local line_number=$1
    log_error "Script failed at line ${line_number}"
    notify_slack "Blocklist update failed at line ${line_number}" "error"
    cleanup_on_exit
    exit 1
}

cleanup_on_exit() {
    # Any cleanup tasks
    true
}

trap 'on_error $LINENO' ERR
trap cleanup_on_exit EXIT

# ============================================================
# MAIN EXECUTION
# ============================================================

main() {
    log "=========================================="
    log "Starting Automated Blocklist Update"
    log "=========================================="

    # Step 1: Validate requirements
    if ! validate_requirements; then
        log_error "Validation failed"
        notify_slack "Blocklist update failed: validation error" "error"
        return 1
    fi

    # Step 2: Backup current lists
    if ! backup_current_lists; then
        log_warning "Backup failed, continuing anyway"
    fi

    # Step 3: Update blocklists
    if ! update_blocklists; then
        log_error "Blocklist update failed"
        notify_slack "Blocklist update failed" "error"
        return 1
    fi

    # Step 4: Verify updates
    if ! verify_blocklist_updates; then
        log_warning "Verification failed, but updates may still be successful"
    fi

    # Step 5: Verify WAF updates
    if ! verify_waf_updates; then
        log_warning "WAF verification failed"
    fi

    # Step 6: Collect statistics
    if ! collect_statistics; then
        log_warning "Statistics collection failed"
    fi

    # Step 7: Cleanup old data
    if ! cleanup_old_data; then
        log_warning "Cleanup failed"
    fi

    log "=========================================="
    log_success "Blocklist update completed successfully"
    log "=========================================="

    return 0
}

# Run main function
main
exit $?
