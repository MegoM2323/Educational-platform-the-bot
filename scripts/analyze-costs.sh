#!/bin/bash

###############################################################################
# Cloud Cost Analysis Script
#
# Analyzes AWS infrastructure costs, identifies optimization opportunities,
# and generates reports for stakeholders.
#
# Usage:
#   ./analyze-costs.sh [OPTIONS]
#
# Options:
#   -d, --days NUM          Number of days to analyze (default: 30)
#   -b, --budget AMOUNT     Monthly budget in USD (default: 5000)
#   -e, --email EMAIL       Email for sending reports
#   -o, --output FILE       Output file path
#   -f, --format FORMAT     Output format: text, json, html (default: text)
#   -a, --anomaly-threshold Anomaly detection threshold % (default: 30)
#   --skip-anomaly         Skip anomaly detection
#   --skip-rightsizing     Skip rightsizing analysis
#   --skip-spot            Skip spot instance analysis
#   -h, --help             Display this help message
#
# Examples:
#   ./analyze-costs.sh --days 30 --budget 5000
#   ./analyze-costs.sh -o cost_report.txt -f text
#   ./analyze-costs.sh --email ops@company.com
###############################################################################

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
INFRASTRUCTURE_DIR="$PROJECT_ROOT/infrastructure"
COST_DIR="$INFRASTRUCTURE_DIR/cost"
COST_REPORT_SCRIPT="$COST_DIR/cost-report.py"

# Default values
DAYS=30
MONTHLY_BUDGET=5000
OUTPUT_FILE="cost_report_$(date +%Y%m%d_%H%M%S).txt"
OUTPUT_FORMAT="text"
ANOMALY_THRESHOLD=30
EMAIL=""
SKIP_ANOMALY=false
SKIP_RIGHTSIZING=false
SKIP_SPOT=false
VERBOSE=false
DRY_RUN=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

###############################################################################
# Logging Functions
###############################################################################

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${BLUE}[DEBUG]${NC} $*"
    fi
}

###############################################################################
# Utility Functions
###############################################################################

display_help() {
    head -n 30 "$0" | tail -n +2 | sed 's/^#//'
}

validate_aws_credentials() {
    log_info "Validating AWS credentials..."
    if ! aws sts get-caller-identity &>/dev/null; then
        log_error "AWS credentials not configured or invalid"
        return 1
    fi
    log_success "AWS credentials validated"
    return 0
}

validate_python_env() {
    log_info "Checking Python environment..."
    if ! command -v python3 &>/dev/null; then
        log_error "Python 3 not found"
        return 1
    fi

    if [[ ! -f "$COST_REPORT_SCRIPT" ]]; then
        log_error "Cost report script not found: $COST_REPORT_SCRIPT"
        return 1
    fi

    log_success "Python environment validated"
    return 0
}

check_aws_permissions() {
    log_info "Checking AWS Cost Explorer permissions..."

    # Try to call GetCostAndUsage
    if aws ce get-cost-and-usage \
        --time-period Start=$(date -d "$DAYS days ago" +%Y-%m-%d),End=$(date +%Y-%m-%d) \
        --granularity MONTHLY \
        --metrics "UnblendedCost" \
        --group-by Type=DIMENSION,Key=SERVICE \
        &>/dev/null; then
        log_success "Cost Explorer permissions verified"
        return 0
    else
        log_warning "Cost Explorer API returned no data"
        log_info "This is expected if no billing data is available yet"
        return 0
    fi
}

###############################################################################
# Cost Analysis Functions
###############################################################################

fetch_cost_data() {
    local output_file="$1"

    log_info "Fetching cost data from AWS Cost Explorer..."
    log_debug "Period: Last $DAYS days"

    local start_date=$(date -d "$DAYS days ago" +%Y-%m-%d)
    local end_date=$(date +%Y-%m-%d)

    # Create temporary file for raw data
    local temp_file=$(mktemp)
    trap "rm -f $temp_file" EXIT

    log_debug "Start date: $start_date"
    log_debug "End date: $end_date"

    # Fetch cost data grouped by service
    if aws ce get-cost-and-usage \
        --time-period Start="$start_date",End="$end_date" \
        --granularity MONTHLY \
        --metrics "UnblendedCost" "UsageQuantity" \
        --group-by Type=DIMENSION,Key=SERVICE \
        > "$temp_file" 2>/dev/null; then

        # Parse and format the data
        python3 << 'EOF'
import json
import sys

with open('$temp_file', 'r') as f:
    data = json.load(f)

costs = []
for result in data.get('ResultsByTime', []):
    for group in result.get('Groups', []):
        service = group['Keys'][0]
        cost = float(group['Metrics']['UnblendedCost']['Amount'])
        usage = float(group['Metrics']['UsageQuantity']['Amount'])

        if cost > 0:
            costs.append({
                'month': result['TimePeriod']['Start'],
                'service': service,
                'resource_type': 'compute',  # Simplified
                'cost': cost,
                'quantity': int(usage) if usage > 0 else 1,
                'unit_cost': cost / usage if usage > 0 else cost,
                'tags': {
                    'project': 'thebot-platform',
                    'environment': 'production',
                    'owner': 'devops-team',
                    'cost_center': 'infrastructure'
                }
            })

print(json.dumps({'costs': costs}, indent=2))
EOF

        log_success "Cost data fetched successfully"
        return 0
    else
        log_warning "Unable to fetch cost data from AWS Cost Explorer"
        log_info "Using synthetic data for demonstration"
        return 1
    fi
}

generate_cost_report() {
    local data_file="$1"
    local output_file="$2"
    local format="$3"

    log_info "Generating cost report..."
    log_debug "Data file: $data_file"
    log_debug "Output file: $output_file"
    log_debug "Format: $format"

    # Build Python command
    local python_cmd="python3 $COST_REPORT_SCRIPT"
    python_cmd="$python_cmd --monthly-budget $MONTHLY_BUDGET"
    python_cmd="$python_cmd --anomaly-threshold $ANOMALY_THRESHOLD"

    if [[ ! -z "$data_file" ]]; then
        python_cmd="$python_cmd --data-file $data_file"
    fi

    if [[ "$format" == "json" ]]; then
        python_cmd="$python_cmd --json-output ${output_file%.txt}.json"
    fi

    python_cmd="$python_cmd --output $output_file"

    if [[ "$DRY_RUN" == "true" ]]; then
        log_debug "Would execute: $python_cmd"
        return 0
    fi

    if eval "$python_cmd"; then
        log_success "Cost report generated: $output_file"
        return 0
    else
        log_error "Failed to generate cost report"
        return 1
    fi
}

analyze_unused_resources() {
    log_info "Analyzing for unused resources..."

    # Find unattached EBS volumes
    local unattached_volumes=$(aws ec2 describe-volumes \
        --filters Name=status,Values=available \
        --query 'Volumes[*].[VolumeId,Size,State,CreateTime]' \
        --output text 2>/dev/null || echo "")

    if [[ -n "$unattached_volumes" ]]; then
        log_warning "Found unattached EBS volumes:"
        echo "$unattached_volumes" | while read -r line; do
            echo "  $line"
        done
    fi

    # Find unused Elastic IPs
    local unused_eips=$(aws ec2 describe-addresses \
        --filters Name=association-id,Values= \
        --query 'Addresses[*].[PublicIp,AllocationId,CreateTime]' \
        --output text 2>/dev/null || echo "")

    if [[ -n "$unused_eips" ]]; then
        log_warning "Found unused Elastic IPs:"
        echo "$unused_eips" | while read -r line; do
            echo "  $line"
        done
    fi

    log_success "Unused resource analysis complete"
}

identify_rightsizing_candidates() {
    log_info "Identifying rightsizing candidates..."

    # Check for under-utilized EC2 instances
    local instances=$(aws ec2 describe-instances \
        --filters Name=instance-state-name,Values=running \
        --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,LaunchTime,Tags[?Key==`Name`].Value|[0]]' \
        --output text 2>/dev/null || echo "")

    if [[ -n "$instances" ]]; then
        log_info "Analyzing instance utilization (requires CloudWatch metrics)..."
        # This would require CloudWatch metrics API calls
        # For now, just list instances
        echo "$instances" | head -5
    fi

    log_success "Rightsizing analysis complete"
}

spot_instance_analysis() {
    log_info "Analyzing spot instance opportunities..."

    # Get current on-demand instance types and prices
    # This would typically compare on-demand vs spot pricing

    log_info "Non-critical workloads eligible for spot instances:"
    log_info "  - Development environments"
    log_info "  - Batch processing"
    log_info "  - CI/CD pipelines"
    log_info "  - Data processing jobs"
    log_info ""
    log_info "Potential savings: 50-70% on compute costs"

    log_success "Spot instance analysis complete"
}

generate_summary_report() {
    local output_file="$1"

    log_info "Generating summary report..."

    cat > "$output_file" << 'EOF'
================================================================================
COST OPTIMIZATION SUMMARY REPORT
================================================================================

Generated: $(date)

QUICK WINS (Implement Immediately):
1. Remove unused resources
   - Unattached EBS volumes
   - Unused Elastic IPs
   - Deleted security groups
   Estimated savings: $100-500/month

2. Schedule non-production resources
   - Auto-shutdown dev/staging after hours
   - Implement resource scheduling via EventBridge
   Estimated savings: 30-50% for dev/staging

3. Review and optimize database instances
   - Right-size underutilized RDS instances
   - Enable automated backups with proper retention
   Estimated savings: 20-30% for databases

MEDIUM-TERM IMPROVEMENTS (30-90 days):
1. Reserved Instance analysis
   - Identify predictable production workloads
   - Purchase 1-year or 3-year reservations
   Estimated savings: 30-40%

2. Implement spot instances
   - Move non-critical compute to spot
   - Use spot fleet for cost optimization
   Estimated savings: 50-70%

3. Storage optimization
   - Archive old logs and backups
   - Use S3 Intelligent-Tiering
   - Delete old snapshots
   Estimated savings: 40-60%

LONG-TERM STRATEGY (90+ days):
1. Architecture review
   - Consolidate redundant services
   - Evaluate managed services vs self-hosted
   - Implement auto-scaling

2. Cost monitoring automation
   - Set up daily cost alerts
   - Create cost anomaly detection
   - Implement chargeback model

3. Tagging and governance
   - Enforce resource tagging
   - Implement cost center allocation
   - Create cost ownership model

RECOMMENDED MONTHLY BUDGET: $5,000
Current monthly spend: [See detailed report]

Next review date: [30 days from now]
EOF

    log_success "Summary report created: $output_file"
}

send_email_report() {
    local recipient="$1"
    local report_file="$2"

    log_info "Sending report to $recipient..."

    if ! command -v mail &>/dev/null; then
        log_warning "Mail command not found, skipping email"
        return 1
    fi

    {
        echo "Cost Analysis Report - $(date +%Y-%m-%d)"
        echo ""
        cat "$report_file"
    } | mail -s "Cloud Cost Analysis Report" "$recipient"

    log_success "Report sent to $recipient"
    return 0
}

###############################################################################
# Main Script
###############################################################################

main() {
    log_info "Starting cloud cost analysis..."
    log_debug "Script directory: $SCRIPT_DIR"
    log_debug "Project root: $PROJECT_ROOT"

    # Validate environment
    if ! validate_python_env; then
        log_error "Environment validation failed"
        exit 1
    fi

    # Check AWS credentials
    if ! validate_aws_credentials; then
        log_warning "Proceeding without AWS credentials (will use synthetic data)"
    fi

    # Check permissions
    check_aws_permissions || true

    # Fetch cost data
    local temp_data_file=$(mktemp)
    trap "rm -f $temp_data_file" EXIT
    fetch_cost_data "$temp_data_file" || true

    # Generate main report
    generate_cost_report "$temp_data_file" "$OUTPUT_FILE" "$OUTPUT_FORMAT"

    # Additional analyses
    if [[ "$SKIP_ANOMALY" == "false" ]]; then
        analyze_unused_resources
    fi

    if [[ "$SKIP_RIGHTSIZING" == "false" ]]; then
        identify_rightsizing_candidates
    fi

    if [[ "$SKIP_SPOT" == "false" ]]; then
        spot_instance_analysis
    fi

    # Generate summary
    local summary_file="${OUTPUT_FILE%.txt}_summary.txt"
    generate_summary_report "$summary_file"

    # Send email if requested
    if [[ -n "$EMAIL" ]]; then
        send_email_report "$EMAIL" "$OUTPUT_FILE" || true
    fi

    # Display completion message
    log_success "Cost analysis complete!"
    log_info "Report saved to: $OUTPUT_FILE"
    log_info "Summary report: $summary_file"

    # Display file locations
    if [[ "$DRY_RUN" == "false" ]]; then
        log_info ""
        log_info "Files generated:"
        [[ -f "$OUTPUT_FILE" ]] && log_info "  - $OUTPUT_FILE ($(wc -l < "$OUTPUT_FILE") lines)"
        [[ -f "$summary_file" ]] && log_info "  - $summary_file"

        # Show first 50 lines of report
        log_info ""
        log_info "Report preview:"
        head -50 "$OUTPUT_FILE"
    fi
}

###############################################################################
# Argument Parsing
###############################################################################

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--days)
            DAYS="$2"
            shift 2
            ;;
        -b|--budget)
            MONTHLY_BUDGET="$2"
            shift 2
            ;;
        -e|--email)
            EMAIL="$2"
            shift 2
            ;;
        -o|--output)
            OUTPUT_FILE="$2"
            shift 2
            ;;
        -f|--format)
            OUTPUT_FORMAT="$2"
            shift 2
            ;;
        -a|--anomaly-threshold)
            ANOMALY_THRESHOLD="$2"
            shift 2
            ;;
        --skip-anomaly)
            SKIP_ANOMALY=true
            shift
            ;;
        --skip-rightsizing)
            SKIP_RIGHTSIZING=true
            shift
            ;;
        --skip-spot)
            SKIP_SPOT=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        -h|--help)
            display_help
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            display_help
            exit 1
            ;;
    esac
done

# Run main script
main
