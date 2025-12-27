#!/bin/bash

################################################################################
# ELK Stack Monitoring & Alerting Script
# Monitors Elasticsearch cluster health and generates alerts
################################################################################

set -e

# Configuration
ELASTICSEARCH_URL=${ELASTICSEARCH_URL:-"http://localhost:9200"}
KIBANA_URL=${KIBANA_URL:-"http://localhost:5601"}
LOGSTASH_URL=${LOGSTASH_URL:-"http://localhost:9600"}
LOG_FILE=${LOG_FILE:-"/var/log/thebot-elk-monitor.log"}
ALERT_EMAIL=${ALERT_EMAIL:-""}
ALERT_THRESHOLD_DISK=${ALERT_THRESHOLD_DISK:-80}  # 80% disk usage
ALERT_THRESHOLD_ERRORS=${ALERT_THRESHOLD_ERRORS:-100}  # 100 errors per minute

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] [$level] $message" | tee -a "$LOG_FILE"
}

# Health check functions
check_elasticsearch() {
    log_message "INFO" "Checking Elasticsearch health..."

    # Check connectivity
    if ! curl -s "$ELASTICSEARCH_URL/_cluster/health" > /dev/null 2>&1; then
        log_message "ERROR" "Cannot connect to Elasticsearch at $ELASTICSEARCH_URL"
        return 1
    fi

    # Get cluster health
    local health=$(curl -s "$ELASTICSEARCH_URL/_cluster/health")
    local status=$(echo "$health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    local active_shards=$(echo "$health" | grep -o '"active_shards":[0-9]*' | cut -d':' -f2)
    local unassigned_shards=$(echo "$health" | grep -o '"unassigned_shards":[0-9]*' | cut -d':' -f2)

    if [ "$status" = "red" ]; then
        log_message "ERROR" "Elasticsearch cluster status is RED"
        echo "  Active shards: $active_shards"
        echo "  Unassigned shards: $unassigned_shards"
        send_alert "Elasticsearch Cluster RED" "Status: $status, Unassigned: $unassigned_shards"
        return 1
    elif [ "$status" = "yellow" ]; then
        log_message "WARN" "Elasticsearch cluster status is YELLOW"
        echo "  Unassigned shards: $unassigned_shards"
    else
        log_message "INFO" "Elasticsearch cluster status is GREEN ✓"
    fi

    return 0
}

check_disk_usage() {
    log_message "INFO" "Checking disk usage..."

    local disk_info=$(curl -s "$ELASTICSEARCH_URL/_cat/allocation?format=json")
    local max_usage=0

    # Parse disk usage
    echo "$disk_info" | grep -o '"disk.percent":[0-9]*' | cut -d':' -f2 | while read usage; do
        if [ "$usage" -gt "$ALERT_THRESHOLD_DISK" ]; then
            log_message "WARN" "Disk usage at ${usage}% (threshold: ${ALERT_THRESHOLD_DISK}%)"
            send_alert "High Disk Usage" "Elasticsearch disk usage: ${usage}%"
        fi
    done
}

check_error_rate() {
    log_message "INFO" "Checking error rate..."

    # Count errors in last minute
    local error_count=$(curl -s "$(ELASTICSEARCH_URL)/thebot-errors-*/_count" \
        -H 'Content-Type: application/json' \
        -d '{
            "query": {
                "range": {
                    "@timestamp": {
                        "gte": "now-1m"
                    }
                }
            }
        }' 2>/dev/null | grep -o '"count":[0-9]*' | cut -d':' -f2 || echo "0")

    if [ "$error_count" -gt "$ALERT_THRESHOLD_ERRORS" ]; then
        log_message "WARN" "High error rate: $error_count errors in last minute"
        send_alert "High Error Rate" "Errors in last minute: $error_count"
    else
        log_message "INFO" "Error rate normal: $error_count errors in last minute"
    fi
}

check_index_count() {
    log_message "INFO" "Checking index count..."

    local indices=$(curl -s "$ELASTICSEARCH_URL/_cat/indices?format=json")
    local count=$(echo "$indices" | grep -o '"index"' | wc -l)

    log_message "INFO" "Total indices: $count"

    # Warn if too many indices
    if [ "$count" -gt 500 ]; then
        log_message "WARN" "High number of indices: $count"
        send_alert "High Index Count" "Total indices: $count"
    fi
}

check_logstash_pipeline() {
    log_message "INFO" "Checking Logstash pipeline..."

    if ! curl -s "$LOGSTASH_URL/" > /dev/null 2>&1; then
        log_message "ERROR" "Cannot connect to Logstash at $LOGSTASH_URL"
        send_alert "Logstash Unavailable" "Logstash is not responding"
        return 1
    fi

    local pipeline_info=$(curl -s "$LOGSTASH_URL/_node/stats/pipelines")
    # Check for pipeline errors
    if echo "$pipeline_info" | grep -q '"errors"'; then
        log_message "WARN" "Logstash pipeline has errors"
    else
        log_message "INFO" "Logstash pipeline healthy ✓"
    fi
}

check_kibana() {
    log_message "INFO" "Checking Kibana..."

    if ! curl -s "$KIBANA_URL/api/status" > /dev/null 2>&1; then
        log_message "ERROR" "Cannot connect to Kibana at $KIBANA_URL"
        send_alert "Kibana Unavailable" "Kibana is not responding"
        return 1
    fi

    log_message "INFO" "Kibana is operational ✓"
}

check_memory_usage() {
    log_message "INFO" "Checking memory usage..."

    local nodes_stats=$(curl -s "$ELASTICSEARCH_URL/_nodes/stats/jvm")
    local max_memory=$(echo "$nodes_stats" | grep -o '"heap_max_in_bytes":[0-9]*' | head -1 | cut -d':' -f2)
    local used_memory=$(echo "$nodes_stats" | grep -o '"heap_used_in_bytes":[0-9]*' | head -1 | cut -d':' -f2)

    if [ -n "$max_memory" ] && [ "$max_memory" -gt 0 ]; then
        local usage_percent=$((used_memory * 100 / max_memory))
        log_message "INFO" "Heap memory usage: ${usage_percent}%"

        if [ "$usage_percent" -gt 85 ]; then
            log_message "WARN" "High memory usage: ${usage_percent}%"
            send_alert "High Memory Usage" "JVM heap usage: ${usage_percent}%"
        fi
    fi
}

check_slow_queries() {
    log_message "INFO" "Checking for slow queries..."

    # Look for slow queries in logs
    local slow_count=$(curl -s "$(ELASTICSEARCH_URL)/.logs-*/_count" \
        -H 'Content-Type: application/json' \
        -d '{
            "query": {
                "match": {
                    "message": "slow query"
                }
            }
        }' 2>/dev/null | grep -o '"count":[0-9]*' | cut -d':' -f2 || echo "0")

    if [ "$slow_count" -gt 10 ]; then
        log_message "WARN" "Detected $slow_count slow queries"
        send_alert "Slow Queries Detected" "Count: $slow_count"
    fi
}

# Alert function
send_alert() {
    local title=$1
    local message=$2

    log_message "ALERT" "$title: $message"

    # Send email if configured
    if [ -n "$ALERT_EMAIL" ]; then
        local subject="ELK Alert: $title"
        echo "$message" | mail -s "$subject" "$ALERT_EMAIL" || true
    fi

    # Log to alerts file
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $title: $message" >> "/var/log/thebot-elk-alerts.log"
}

# Main monitoring loop
run_checks() {
    log_message "INFO" "Starting ELK Stack monitoring checks..."

    check_elasticsearch
    check_kibana
    check_logstash_pipeline
    check_disk_usage
    check_error_rate
    check_index_count
    check_memory_usage
    check_slow_queries

    log_message "INFO" "Monitoring checks completed"
}

# Generate health report
generate_report() {
    log_message "INFO" "Generating health report..."

    echo ""
    echo "====================================="
    echo "ELK Stack Health Report"
    echo "====================================="
    echo "Timestamp: $(date)"
    echo ""

    echo "Elasticsearch Cluster:"
    curl -s "$ELASTICSEARCH_URL/_cluster/health" | python3 -m json.tool 2>/dev/null | head -20 || echo "Unable to fetch cluster health"
    echo ""

    echo "Top 5 Largest Indices:"
    curl -s "$ELASTICSEARCH_URL/_cat/indices?v&s=store.size:desc&h=index,docs.count,store.size" 2>/dev/null | head -6 || echo "Unable to fetch indices"
    echo ""

    echo "Node Status:"
    curl -s "$ELASTICSEARCH_URL/_cat/nodes?v&h=name,ip,heap.percent,ram.percent,disk.avail" 2>/dev/null | head -10 || echo "Unable to fetch nodes"
    echo ""
}

# Show help
show_help() {
    cat << EOF
ELK Stack Monitoring Script

Usage: $0 [OPTION]

Options:
    -c, --check          Run health checks once
    -m, --monitor        Run continuous monitoring (interval: 5 minutes)
    -r, --report         Generate health report
    -h, --help           Show this help message

Examples:
    $0 --check           # Run checks once
    $0 --monitor         # Run continuous monitoring
    $0 --report          # Generate report

Environment Variables:
    ELASTICSEARCH_URL    Elasticsearch URL (default: http://localhost:9200)
    KIBANA_URL          Kibana URL (default: http://localhost:5601)
    LOGSTASH_URL        Logstash URL (default: http://localhost:9600)
    ALERT_EMAIL         Email for alerts (optional)
    ALERT_THRESHOLD_DISK Disk usage alert threshold % (default: 80)
    ALERT_THRESHOLD_ERRORS Error rate alert threshold (default: 100/min)

EOF
}

# Main entry point
main() {
    # Create log directory if needed
    mkdir -p "$(dirname "$LOG_FILE")"

    # Parse arguments
    case "${1:-}" in
        -c|--check)
            run_checks
            ;;
        -m|--monitor)
            log_message "INFO" "Starting continuous monitoring..."
            while true; do
                run_checks
                log_message "INFO" "Next check in 5 minutes..."
                sleep 300
            done
            ;;
        -r|--report)
            generate_report
            ;;
        -h|--help)
            show_help
            ;;
        *)
            run_checks
            ;;
    esac
}

# Run main function
main "$@"
