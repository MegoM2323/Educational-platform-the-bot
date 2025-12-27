#!/bin/bash

################################################################################
# INTEGRATED DISASTER RECOVERY TEST ORCHESTRATOR
#
# Coordinates and orchestrates all disaster recovery tests
# Generates comprehensive reports with RTO/RPO compliance validation
#
# Usage:
#   ./integrated-dr-test.sh [--dry-run] [--full-report] [--parallel]
#   ./integrated-dr-test.sh --quick                    # Fast sanity check
#   ./integrated-dr-test.sh --full                     # Complete test suite
#   ./integrated-dr-test.sh --validate-compliance      # Check RTO/RPO targets
#
# Features:
#  - Orchestrates multiple test suites
#  - Collects and aggregates metrics
#  - Generates HTML and JSON reports
#  - Validates RTO/RPO compliance
#  - Tracks test history
#  - Provides summary dashboard
#
################################################################################

set -euo pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
LOGS_DIR="${PROJECT_ROOT}/logs/dr-integration-tests"
METRICS_DIR="${PROJECT_ROOT}/metrics"
REPORTS_DIR="${PROJECT_ROOT}/metrics/dr-reports"

mkdir -p "$LOGS_DIR" "$METRICS_DIR" "$REPORTS_DIR"

# Test parameters
DRY_RUN="${DRY_RUN:-false}"
RUN_PARALLEL="${RUN_PARALLEL:-false}"
GENERATE_FULL_REPORT="${GENERATE_FULL_REPORT:-false}"
VERBOSE="${VERBOSE:-true}"

# RTO/RPO targets
TARGET_RTO=900        # 15 minutes
TARGET_RPO=300        # 5 minutes

# Logging
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
INTEGRATION_LOG="${LOGS_DIR}/integrated-test_${TIMESTAMP}.log"
INTEGRATION_REPORT="${REPORTS_DIR}/dr-report_${TIMESTAMP}.json"
SUMMARY_REPORT="${REPORTS_DIR}/dr-summary_${TIMESTAMP}.html"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m'

# Test results tracking
TESTS_EXECUTED=()
TESTS_RESULTS=()
TESTS_METRICS=()
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# ============================================================================
# LOGGING FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*" | tee -a "$INTEGRATION_LOG"
}

log_success() {
    echo -e "${GREEN}[✓]${NC} $*" | tee -a "$INTEGRATION_LOG"
}

log_error() {
    echo -e "${RED}[✗]${NC} $*" | tee -a "$INTEGRATION_LOG"
}

log_warning() {
    echo -e "${YELLOW}[!]${NC} $*" | tee -a "$INTEGRATION_LOG"
}

log_metric() {
    echo -e "${CYAN}[METRIC]${NC} $*" | tee -a "$INTEGRATION_LOG"
}

log_section() {
    echo -e "\n${MAGENTA}═══════════════════════════════════════════════════════════${NC}" | tee -a "$INTEGRATION_LOG"
    echo -e "${MAGENTA}$1${NC}" | tee -a "$INTEGRATION_LOG"
    echo -e "${MAGENTA}═══════════════════════════════════════════════════════════${NC}\n" | tee -a "$INTEGRATION_LOG"
}

print_header() {
    echo -e "\n${CYAN}════════════════════════════════════════════════════════${NC}" | tee -a "$INTEGRATION_LOG"
    echo -e "${CYAN}$1${NC}" | tee -a "$INTEGRATION_LOG"
    echo -e "${CYAN}════════════════════════════════════════════════════════${NC}\n" | tee -a "$INTEGRATION_LOG"
}

# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

init_integration_report() {
    cat > "$INTEGRATION_REPORT" << 'EOF'
{
  "integration_test": {
    "timestamp": "",
    "duration_seconds": 0,
    "dry_run": false,
    "test_environment": "production",
    "tests": [],
    "summary": {
      "total_tests": 0,
      "passed": 0,
      "failed": 0,
      "rto_compliant": false,
      "rpo_compliant": false,
      "overall_status": "pending"
    },
    "metrics": {
      "failover_rto_seconds": 0,
      "restore_rpo_seconds": 0,
      "recovery_rto_seconds": 0,
      "backup_age_minutes": 0,
      "data_integrity_verified": false
    },
    "compliance": {
      "rto_target_seconds": 900,
      "rpo_target_seconds": 300,
      "rto_actual_seconds": 0,
      "rpo_actual_seconds": 0,
      "rto_margin_percent": 0,
      "rpo_margin_percent": 0
    },
    "notes": ""
  }
}
EOF
}

add_test_result() {
    local test_name="$1"
    local status="$2"
    local duration="$3"
    local metrics="$4"

    jq ".integration_test.tests += [{
        \"name\": \"$test_name\",
        \"status\": \"$status\",
        \"duration_seconds\": $duration,
        \"metrics\": $metrics
    }]" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
    mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

    if [[ "$status" == "passed" ]]; then
        ((PASSED_TESTS++))
    else
        ((FAILED_TESTS++))
    fi
}

# ============================================================================
# QUICK SANITY CHECK
# ============================================================================

run_quick_check() {
    print_header "QUICK SANITY CHECK (5 minutes)"

    local start_time=$(date +%s)

    # Check 1: Services running
    log_info "Check 1: Verifying services are running..."
    if docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" ps | grep -q "running"; then
        log_success "Services are running"
    else
        log_warning "Some services may not be running"
    fi

    # Check 2: Database connectivity
    log_info "Check 2: Testing database connectivity..."
    if docker-compose -f "$PROJECT_ROOT/docker-compose.prod.yml" exec -T postgres pg_isready &>/dev/null; then
        log_success "Database is accessible"
    else
        log_error "Database is not accessible"
        return 1
    fi

    # Check 3: API health
    log_info "Check 3: Checking API health..."
    local health_status=$(curl -s -w "%{http_code}" -o /dev/null http://localhost:8000/api/system/health/ 2>/dev/null || echo "000")
    if [[ "$health_status" == "200" ]]; then
        log_success "API is healthy (HTTP $health_status)"
    else
        log_warning "API returned HTTP $health_status"
    fi

    # Check 4: Backup availability
    log_info "Check 4: Checking backup availability..."
    if [[ -d "${PROJECT_ROOT}/backups" ]] && ls "${PROJECT_ROOT}"/backups/*.sql &>/dev/null; then
        local latest_backup=$(ls -t "${PROJECT_ROOT}"/backups/*.sql 2>/dev/null | head -1)
        log_success "Latest backup found: $(basename "$latest_backup")"
    else
        log_warning "No backups found in ${PROJECT_ROOT}/backups"
    fi

    local end_time=$(date +%s)
    local duration=$((end_time - start_time))

    log_metric "Quick check completed in ${duration}s"
    add_test_result "QuickCheck" "passed" "$duration" "{}"

    ((TOTAL_TESTS++))

    return 0
}

# ============================================================================
# FAILOVER TEST
# ============================================================================

run_failover_test() {
    print_header "RUNNING FAILOVER TEST (10 minutes)"

    local start_time=$(date +%s)
    local test_script="${SCRIPT_DIR}/failover-test.sh"

    if [[ ! -f "$test_script" ]]; then
        log_error "Failover test script not found: $test_script"
        add_test_result "FailoverTest" "failed" "0" "{\"error\": \"script_not_found\"}"
        ((TOTAL_TESTS++))
        return 1
    fi

    # Run failover test with dry-run if requested
    local test_cmd="bash '$test_script'"
    if [[ "$DRY_RUN" == "true" ]]; then
        test_cmd="$test_cmd --dry-run"
    fi

    log_info "Executing: $test_cmd"

    if eval "$test_cmd" >> "$INTEGRATION_LOG" 2>&1; then
        log_success "Failover test passed"

        # Extract metrics
        if [[ -f "${METRICS_DIR}/failover-metrics_"*.json ]]; then
            local latest_metric=$(ls -t "${METRICS_DIR}"/failover-metrics_*.json 2>/dev/null | head -1)
            local rto_actual=$(jq -r '.metrics.total_rto_seconds // 0' "$latest_metric")
            log_metric "Failover RTO: ${rto_actual}s"

            add_test_result "FailoverTest" "passed" "$(($(date +%s) - start_time))" \
                "{\"rto_seconds\": $rto_actual}"
        else
            add_test_result "FailoverTest" "passed" "$(($(date +%s) - start_time))" "{}"
        fi

        ((PASSED_TESTS++))
    else
        log_error "Failover test failed"
        add_test_result "FailoverTest" "failed" "$(($(date +%s) - start_time))" "{\"error\": \"test_failed\"}"
        ((FAILED_TESTS++))
    fi

    ((TOTAL_TESTS++))
}

# ============================================================================
# RESTORE TEST
# ============================================================================

run_restore_test() {
    print_header "RUNNING RESTORE TEST (10 minutes)"

    local start_time=$(date +%s)
    local test_script="${SCRIPT_DIR}/restore-test.sh"

    if [[ ! -f "$test_script" ]]; then
        log_error "Restore test script not found: $test_script"
        add_test_result "RestoreTest" "failed" "0" "{\"error\": \"script_not_found\"}"
        ((TOTAL_TESTS++))
        return 1
    fi

    # Run restore test with verify-only if needed
    local test_cmd="bash '$test_script' --verify-backup"
    if [[ "$DRY_RUN" != "true" ]]; then
        test_cmd="bash '$test_script'"
    fi

    log_info "Executing: $test_cmd"

    if eval "$test_cmd" >> "$INTEGRATION_LOG" 2>&1; then
        log_success "Restore test passed"

        # Extract metrics
        if [[ -f "${METRICS_DIR}/restore-metrics_"*.json ]]; then
            local latest_metric=$(ls -t "${METRICS_DIR}"/restore-metrics_*.json 2>/dev/null | head -1)
            local rpo_actual=$(jq -r '.metrics.total_rpo_seconds // 0' "$latest_metric")
            log_metric "Restore RPO: ${rpo_actual}s"

            add_test_result "RestoreTest" "passed" "$(($(date +%s) - start_time))" \
                "{\"rpo_seconds\": $rpo_actual}"
        else
            add_test_result "RestoreTest" "passed" "$(($(date +%s) - start_time))" "{}"
        fi

        ((PASSED_TESTS++))
    else
        log_error "Restore test failed"
        add_test_result "RestoreTest" "failed" "$(($(date +%s) - start_time))" "{\"error\": \"test_failed\"}"
        ((FAILED_TESTS++))
    fi

    ((TOTAL_TESTS++))
}

# ============================================================================
# COMPLIANCE VALIDATION
# ============================================================================

validate_rto_compliance() {
    print_header "RTO COMPLIANCE VALIDATION"

    log_info "Checking RTO compliance (target: ${TARGET_RTO}s = 15 minutes)..."

    # Collect RTO metrics from failover test
    if [[ -f "${METRICS_DIR}/failover-metrics_"*.json ]]; then
        local latest_metric=$(ls -t "${METRICS_DIR}"/failover-metrics_*.json 2>/dev/null | head -1)
        local failover_rto=$(jq -r '.metrics.total_rto_seconds // 0' "$latest_metric")

        log_metric "Failover RTO: ${failover_rto}s"

        if [[ $failover_rto -lt $TARGET_RTO ]]; then
            log_success "RTO COMPLIANT: ${failover_rto}s < ${TARGET_RTO}s"
            jq ".integration_test.compliance.rto_actual_seconds = $failover_rto" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
            mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

            local margin=$(((TARGET_RTO - failover_rto) * 100 / TARGET_RTO))
            jq ".integration_test.compliance.rto_margin_percent = $margin" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
            mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

            jq ".integration_test.summary.rto_compliant = true" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
            mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

            return 0
        else
            log_error "RTO NON-COMPLIANT: ${failover_rto}s >= ${TARGET_RTO}s"
            return 1
        fi
    else
        log_warning "No failover metrics found"
        return 1
    fi
}

validate_rpo_compliance() {
    print_header "RPO COMPLIANCE VALIDATION"

    log_info "Checking RPO compliance (target: ${TARGET_RPO}s = 5 minutes)..."

    # Collect RPO metrics from restore test
    if [[ -f "${METRICS_DIR}/restore-metrics_"*.json ]]; then
        local latest_metric=$(ls -t "${METRICS_DIR}"/restore-metrics_*.json 2>/dev/null | head -1)
        local restore_rpo=$(jq -r '.metrics.total_rpo_seconds // 0' "$latest_metric")

        log_metric "Restore RPO: ${restore_rpo}s"

        if [[ $restore_rpo -lt $TARGET_RPO ]]; then
            log_success "RPO COMPLIANT: ${restore_rpo}s < ${TARGET_RPO}s"
            jq ".integration_test.compliance.rpo_actual_seconds = $restore_rpo" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
            mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

            local margin=$(((TARGET_RPO - restore_rpo) * 100 / TARGET_RPO))
            jq ".integration_test.compliance.rpo_margin_percent = $margin" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
            mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

            jq ".integration_test.summary.rpo_compliant = true" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
            mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

            return 0
        else
            log_error "RPO NON-COMPLIANT: ${restore_rpo}s >= ${TARGET_RPO}s"
            return 1
        fi
    else
        log_warning "No restore metrics found"
        return 1
    fi
}

# ============================================================================
# REPORTING
# ============================================================================

generate_html_report() {
    print_header "Generating HTML Report"

    local total_tests=$((PASSED_TESTS + FAILED_TESTS))
    local pass_rate=0
    if [[ $total_tests -gt 0 ]]; then
        pass_rate=$((PASSED_TESTS * 100 / total_tests))
    fi

    # Determine compliance status
    local rto_status="NON-COMPLIANT"
    local rpo_status="NON-COMPLIANT"
    if jq -e '.integration_test.summary.rto_compliant' "$INTEGRATION_REPORT" &>/dev/null; then
        rto_status=$(jq -r '.integration_test.summary.rto_compliant' "$INTEGRATION_REPORT")
        [[ "$rto_status" == "true" ]] && rto_status="COMPLIANT" || rto_status="NON-COMPLIANT"
    fi
    if jq -e '.integration_test.summary.rpo_compliant' "$INTEGRATION_REPORT" &>/dev/null; then
        rpo_status=$(jq -r '.integration_test.summary.rpo_compliant' "$INTEGRATION_REPORT")
        [[ "$rpo_status" == "true" ]] && rpo_status="COMPLIANT" || rpo_status="NON-COMPLIANT"
    fi

    cat > "$SUMMARY_REPORT" << 'REPORT_HTML'
<!DOCTYPE html>
<html>
<head>
    <title>Disaster Recovery Test Report</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 40px;
            border-radius: 8px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .header h1 { font-size: 2.5em; margin-bottom: 10px; }
        .header p { font-size: 1.1em; opacity: 0.9; }
        .section {
            background: white;
            padding: 25px;
            margin-bottom: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .section h2 {
            color: #667eea;
            margin-bottom: 15px;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .metric-card {
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #667eea;
        }
        .metric-card.success { border-left-color: #10b981; background: linear-gradient(135deg, #d4fc79 0%, #96e6a1 100%); }
        .metric-card.failed { border-left-color: #ef4444; background: linear-gradient(135deg, #fca5a5 0%, #f87171 100%); }
        .metric-card.warning { border-left-color: #f59e0b; background: linear-gradient(135deg, #fcd34d 0%, #fbbf24 100%); }
        .metric-label { font-size: 0.9em; color: #666; margin-bottom: 5px; }
        .metric-value { font-size: 1.8em; font-weight: bold; color: #333; }
        .metric-unit { font-size: 0.9em; color: #666; }
        .status-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            margin: 5px 5px 5px 0;
        }
        .status-badge.compliant { background: #d1fae5; color: #065f46; }
        .status-badge.non-compliant { background: #fee2e2; color: #7f1d1d; }
        .status-badge.passed { background: #d1fae5; color: #065f46; }
        .status-badge.failed { background: #fee2e2; color: #7f1d1d; }
        table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 15px;
        }
        th {
            background: #f3f4f6;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            border-bottom: 2px solid #e5e7eb;
        }
        td {
            padding: 12px;
            border-bottom: 1px solid #e5e7eb;
        }
        tr:hover { background: #f9fafb; }
        .progress-bar {
            width: 100%;
            height: 24px;
            background: #e5e7eb;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #10b981, #34d399);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 0.9em;
        }
        .footer {
            text-align: center;
            color: #999;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Disaster Recovery Test Report</h1>
            <p>Comprehensive RTO/RPO Compliance Validation</p>
            <p id="timestamp"></p>
        </div>

        <div class="section">
            <h2>Executive Summary</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">Tests Executed</div>
                    <div class="metric-value" id="total-tests">0</div>
                </div>
                <div class="metric-card success" id="passed-card">
                    <div class="metric-label">Tests Passed</div>
                    <div class="metric-value" id="passed-tests">0</div>
                </div>
                <div class="metric-card failed" id="failed-card">
                    <div class="metric-label">Tests Failed</div>
                    <div class="metric-value" id="failed-tests">0</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">Pass Rate</div>
                    <div class="metric-value" id="pass-rate">0%</div>
                </div>
            </div>
            <div class="progress-bar">
                <div class="progress-fill" id="progress-fill" style="width: PASS_RATE%">
                    PASS_RATE% Pass
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Compliance Status</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-label">RTO Target</div>
                    <div class="metric-value">15</div>
                    <div class="metric-unit">minutes</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">RTO Actual</div>
                    <div class="metric-value" id="rto-actual">-</div>
                    <div class="metric-unit">seconds</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">RTO Status</div>
                    <div id="rto-status" class="status-badge">PENDING</div>
                </div>
            </div>
            <div class="metrics-grid" style="margin-top: 20px;">
                <div class="metric-card">
                    <div class="metric-label">RPO Target</div>
                    <div class="metric-value">5</div>
                    <div class="metric-unit">minutes</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">RPO Actual</div>
                    <div class="metric-value" id="rpo-actual">-</div>
                    <div class="metric-unit">seconds</div>
                </div>
                <div class="metric-card">
                    <div class="metric-label">RPO Status</div>
                    <div id="rpo-status" class="status-badge">PENDING</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Test Results</h2>
            <table>
                <thead>
                    <tr>
                        <th>Test Name</th>
                        <th>Status</th>
                        <th>Duration</th>
                        <th>Details</th>
                    </tr>
                </thead>
                <tbody id="test-results">
                </tbody>
            </table>
        </div>

        <div class="footer">
            <p>Report generated: <span id="generated-at"></span></p>
            <p>THE_BOT Platform - Disaster Recovery Testing</p>
        </div>
    </div>

    <script>
        // Update report with actual data
        document.getElementById('timestamp').textContent = 'Generated: ' + new Date().toLocaleString();
        document.getElementById('total-tests').textContent = 'TOTAL_TESTS';
        document.getElementById('passed-tests').textContent = 'PASSED_TESTS';
        document.getElementById('failed-tests').textContent = 'FAILED_TESTS';
        document.getElementById('pass-rate').textContent = 'PASS_RATE%';
        document.getElementById('rto-actual').textContent = 'RTO_ACTUAL';
        document.getElementById('rpo-actual').textContent = 'RPO_ACTUAL';
        document.getElementById('generated-at').textContent = new Date().toLocaleString();

        // Set compliance badges
        var rtoStatus = 'RTO_COMPLIANT' === 'true' ? 'compliant' : 'non-compliant';
        var rpoStatus = 'RPO_COMPLIANT' === 'true' ? 'compliant' : 'non-compliant';

        document.getElementById('rto-status').textContent = rtoStatus.toUpperCase();
        document.getElementById('rto-status').className = 'status-badge ' + rtoStatus;

        document.getElementById('rpo-status').textContent = rpoStatus.toUpperCase();
        document.getElementById('rpo-status').className = 'status-badge ' + rpoStatus;

        // Update progress bar
        var progressPercent = PASS_RATE;
        document.getElementById('progress-fill').style.width = progressPercent + '%';
        document.getElementById('progress-fill').textContent = progressPercent + '% Pass';
    </script>
</body>
</html>
REPORT_HTML

    # Replace placeholders with actual values
    sed -i "s/TOTAL_TESTS/$total_tests/g" "$SUMMARY_REPORT"
    sed -i "s/PASSED_TESTS/$PASSED_TESTS/g" "$SUMMARY_REPORT"
    sed -i "s/FAILED_TESTS/$FAILED_TESTS/g" "$SUMMARY_REPORT"
    sed -i "s/PASS_RATE/$pass_rate/g" "$SUMMARY_REPORT"

    # Get compliance values
    local rto_status=$(jq -r '.integration_test.summary.rto_compliant // false' "$INTEGRATION_REPORT")
    local rpo_status=$(jq -r '.integration_test.summary.rpo_compliant // false' "$INTEGRATION_REPORT")
    local rto_actual=$(jq -r '.integration_test.compliance.rto_actual_seconds // "N/A"' "$INTEGRATION_REPORT")
    local rpo_actual=$(jq -r '.integration_test.compliance.rpo_actual_seconds // "N/A"' "$INTEGRATION_REPORT")

    sed -i "s/RTO_COMPLIANT/$rto_status/g" "$SUMMARY_REPORT"
    sed -i "s/RPO_COMPLIANT/$rpo_status/g" "$SUMMARY_REPORT"
    sed -i "s/RTO_ACTUAL/$rto_actual/g" "$SUMMARY_REPORT"
    sed -i "s/RPO_ACTUAL/$rpo_actual/g" "$SUMMARY_REPORT"

    log_success "HTML report generated: $SUMMARY_REPORT"
}

# ============================================================================
# SHOW HELP
# ============================================================================

show_help() {
    cat << 'HELP_EOF'
INTEGRATED DISASTER RECOVERY TEST ORCHESTRATOR

Usage: ./integrated-dr-test.sh [OPTIONS]

Options:
  --quick                Run quick sanity check only
  --full                 Run full test suite (all tests)
  --failover             Run only failover test
  --restore              Run only restore test
  --dry-run              Simulate without actual changes
  --parallel             Run tests in parallel (experimental)
  --full-report          Generate comprehensive HTML report
  --validate             Validate RTO/RPO compliance only
  --help                 Show this help message

Examples:
  # Quick sanity check
  ./integrated-dr-test.sh --quick

  # Full test suite with reports
  ./integrated-dr-test.sh --full --full-report

  # Dry-run with reports
  ./integrated-dr-test.sh --full --dry-run --full-report

  # Validate compliance
  ./integrated-dr-test.sh --validate

RTO/RPO Targets:
  RTO (Recovery Time Objective): < 15 minutes
  RPO (Recovery Point Objective): < 5 minutes

Output Files:
  - Integration Log: logs/dr-integration-tests/integrated-test_*.log
  - JSON Report: metrics/dr-reports/dr-report_*.json
  - HTML Summary: metrics/dr-reports/dr-summary_*.html

HELP_EOF
}

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

main() {
    local test_type="quick"
    local run_validate=false

    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --quick)
                test_type="quick"
                shift
                ;;
            --full)
                test_type="full"
                shift
                ;;
            --failover)
                test_type="failover"
                shift
                ;;
            --restore)
                test_type="restore"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --full-report)
                GENERATE_FULL_REPORT="true"
                shift
                ;;
            --parallel)
                RUN_PARALLEL="true"
                shift
                ;;
            --validate)
                run_validate=true
                shift
                ;;
            --help)
                show_help
                exit 0
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done

    # Initialize report
    init_integration_report
    jq ".integration_test.timestamp = \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
    mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"
    jq ".integration_test.dry_run = $([ "$DRY_RUN" = "true" ] && echo "true" || echo "false")" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
    mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

    log_section "INTEGRATED DISASTER RECOVERY TEST ORCHESTRATOR"
    log_info "Test Type: $test_type"
    log_info "Dry Run: $DRY_RUN"
    log_info "Parallel: $RUN_PARALLEL"
    log_info "Timestamp: $(date)"

    # Handle validate-only mode
    if [[ "$run_validate" == "true" ]]; then
        validate_rto_compliance
        validate_rpo_compliance

        local rto_status=$(jq -r '.integration_test.summary.rto_compliant // false' "$INTEGRATION_REPORT")
        local rpo_status=$(jq -r '.integration_test.summary.rpo_compliant // false' "$INTEGRATION_REPORT")

        if [[ "$rto_status" == "true" ]] && [[ "$rpo_status" == "true" ]]; then
            log_success "COMPLIANCE: RTO and RPO both COMPLIANT"
            exit 0
        else
            log_error "COMPLIANCE: One or more targets NON-COMPLIANT"
            exit 1
        fi
    fi

    # Run tests based on type
    case "$test_type" in
        quick)
            run_quick_check
            ;;
        failover)
            run_failover_test
            ;;
        restore)
            run_restore_test
            ;;
        full)
            run_quick_check
            run_failover_test
            run_restore_test
            ;;
        *)
            log_error "Unknown test type: $test_type"
            show_help
            exit 1
            ;;
    esac

    # Validate compliance
    print_header "VALIDATING COMPLIANCE TARGETS"
    local rto_pass=false
    local rpo_pass=false

    if validate_rto_compliance; then
        rto_pass=true
    fi

    if validate_rpo_compliance; then
        rpo_pass=true
    fi

    # Update summary
    jq ".integration_test.summary.total_tests = $TOTAL_TESTS" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
    mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

    jq ".integration_test.summary.passed = $PASSED_TESTS" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
    mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

    jq ".integration_test.summary.failed = $FAILED_TESTS" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
    mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"

    if [[ "$rto_pass" == "true" ]] && [[ "$rpo_pass" == "true" ]]; then
        jq ".integration_test.summary.overall_status = \"COMPLIANT\"" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
        mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"
    else
        jq ".integration_test.summary.overall_status = \"NON-COMPLIANT\"" "$INTEGRATION_REPORT" > "${INTEGRATION_REPORT}.tmp"
        mv "${INTEGRATION_REPORT}.tmp" "$INTEGRATION_REPORT"
    fi

    # Generate reports
    print_header "GENERATING REPORTS"

    log_info "JSON Report: $INTEGRATION_REPORT"
    log_info "Log File: $INTEGRATION_LOG"

    if [[ "$GENERATE_FULL_REPORT" == "true" ]]; then
        generate_html_report
        log_success "HTML Report: $SUMMARY_REPORT"
    fi

    # Print summary
    print_header "INTEGRATION TEST SUMMARY"

    echo -e "Tests Executed: $TOTAL_TESTS"
    echo -e "  ${GREEN}Passed: $PASSED_TESTS${NC}"
    echo -e "  ${RED}Failed: $FAILED_TESTS${NC}"
    echo ""
    echo -e "Compliance Status:"
    if [[ "$rto_pass" == "true" ]]; then
        echo -e "  RTO: ${GREEN}COMPLIANT${NC}"
    else
        echo -e "  RTO: ${RED}NON-COMPLIANT${NC}"
    fi
    if [[ "$rpo_pass" == "true" ]]; then
        echo -e "  RPO: ${GREEN}COMPLIANT${NC}"
    else
        echo -e "  RPO: ${RED}NON-COMPLIANT${NC}"
    fi
    echo ""

    # Display metrics
    echo -e "Metrics:"
    jq '.integration_test' "$INTEGRATION_REPORT" 2>/dev/null | head -50

    # Exit status
    if [[ "$rto_pass" == "true" ]] && [[ "$rpo_pass" == "true" ]]; then
        exit 0
    else
        exit 1
    fi
}

# Run main orchestrator
main "$@"
