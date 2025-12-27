#!/bin/bash
#
# Security scanning script for local testing
# Usage: ./scripts/security-scan.sh [backend|frontend|all]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo -e "\n${BLUE}================================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

scan_backend() {
    print_header "Backend Security Scanning"

    cd "$PROJECT_DIR/backend"

    # Check if Python is available
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 not found"
        return 1
    fi

    # Install tools
    print_header "Installing security tools"
    python3 -m pip install --quiet --upgrade pip
    python3 -m pip install --quiet safety bandit pip-audit

    # Safety scan
    print_header "Running Safety scan (dependency vulnerabilities)"
    if python3 -m safety check --file=requirements.txt --json > safety-report.json 2>/dev/null || true; then
        if grep -q "vulnerabilities" safety-report.json 2>/dev/null; then
            print_warning "Safety found issues - check safety-report.json"
        else
            print_success "Safety scan completed"
        fi
    fi

    # pip-audit scan
    print_header "Running pip-audit scan"
    if python3 -m pip_audit --requirements requirements.txt > pip-audit-report.txt 2>&1 || true; then
        if grep -q "has known security vulnerabilities" pip-audit-report.txt; then
            print_warning "pip-audit found issues - check pip-audit-report.txt"
        else
            print_success "pip-audit scan completed"
        fi
    fi

    # Bandit scan
    print_header "Running Bandit SAST scan"
    if bandit -r . \
        --exclude tests,migrations,venv \
        -f json -o bandit-report.json \
        -f txt > bandit-report.txt 2>&1 || true; then
        if grep -q "Issue\|Severity" bandit-report.txt; then
            print_warning "Bandit found issues - check bandit-report.txt"
            cat bandit-report.txt
        else
            print_success "Bandit scan completed"
        fi
    fi

    cd "$PROJECT_DIR"
}

scan_frontend() {
    print_header "Frontend Security Scanning"

    cd "$PROJECT_DIR/frontend"

    # Check if npm is available
    if ! command -v npm &> /dev/null; then
        print_error "npm not found"
        return 1
    fi

    # npm audit
    print_header "Running npm audit"
    if npm audit --json > npm-audit-report.json 2>/dev/null || true; then
        VULN_COUNT=$(jq '.metadata.vulnerabilities.total // 0' npm-audit-report.json 2>/dev/null || echo 0)
        if [ "$VULN_COUNT" -gt 0 ]; then
            print_warning "npm audit found $VULN_COUNT vulnerabilities"
            jq '.vulnerabilities | keys[]' npm-audit-report.json 2>/dev/null || true
        else
            print_success "npm audit completed - no vulnerabilities found"
        fi
    fi

    # npm audit fix suggestions
    print_header "Checking npm audit fix suggestions"
    npm audit fix --dry-run > npm-audit-fix-suggestions.txt 2>&1 || true

    # ESLint security checks
    print_header "Running ESLint security checks"
    if npx eslint . --format json --output-file eslint-report.json 2>/dev/null || true; then
        ERROR_COUNT=$(jq 'length' eslint-report.json 2>/dev/null || echo 0)
        if [ "$ERROR_COUNT" -gt 0 ]; then
            print_warning "ESLint found $ERROR_COUNT issues"
        else
            print_success "ESLint security checks completed"
        fi
    fi

    cd "$PROJECT_DIR"
}

scan_secrets() {
    print_header "Secret Detection Scanning"

    cd "$PROJECT_DIR"

    # Check if gitleaks is available
    if ! command -v gitleaks &> /dev/null; then
        print_warning "gitleaks not found - skipping secret detection"
        print_warning "To install: https://github.com/gitleaks/gitleaks"
        return 0
    fi

    # gitleaks scan
    print_header "Running gitleaks secret detection"
    if gitleaks detect --source . --format json --report-path gitleaks-report.json 2>/dev/null || true; then
        if [ -f gitleaks-report.json ] && [ -s gitleaks-report.json ]; then
            SECRET_COUNT=$(jq 'length' gitleaks-report.json 2>/dev/null || echo 0)
            if [ "$SECRET_COUNT" -gt 0 ]; then
                print_error "gitleaks found $SECRET_COUNT potential secrets!"
                jq '.[].RuleID' gitleaks-report.json 2>/dev/null || true
            fi
        else
            print_success "No secrets detected"
        fi
    fi

    cd "$PROJECT_DIR"
}

generate_report() {
    print_header "Security Scan Report Summary"

    cd "$PROJECT_DIR"

    python3 << 'EOF'
import json
import os
from pathlib import Path
from datetime import datetime

summary = {
    "timestamp": datetime.now().isoformat(),
    "scans": {},
    "findings": {
        "critical": 0,
        "high": 0,
        "medium": 0,
        "low": 0,
        "info": 0
    }
}

# Check backend reports
backend_dir = Path("backend")
if (backend_dir / "safety-report.json").exists():
    try:
        with open(backend_dir / "safety-report.json") as f:
            data = json.load(f)
        summary["scans"]["backend_safety"] = f"completed ({len(data)} findings)"
    except:
        pass

if (backend_dir / "bandit-report.json").exists():
    try:
        with open(backend_dir / "bandit-report.json") as f:
            data = json.load(f)
        if "results" in data:
            summary["scans"]["backend_bandit"] = f"completed ({len(data['results'])} findings)"
    except:
        pass

# Check frontend reports
frontend_dir = Path("frontend")
if (frontend_dir / "npm-audit-report.json").exists():
    try:
        with open(frontend_dir / "npm-audit-report.json") as f:
            data = json.load(f)
        vulns = data.get("vulnerabilities", {})
        summary["scans"]["frontend_npm"] = f"completed ({len(vulns)} findings)"
    except:
        pass

if (frontend_dir / "eslint-report.json").exists():
    try:
        with open(frontend_dir / "eslint-report.json") as f:
            data = json.load(f)
        summary["scans"]["frontend_eslint"] = f"completed ({len(data)} findings)"
    except:
        pass

# Check secret scan
if Path("gitleaks-report.json").exists():
    try:
        with open("gitleaks-report.json") as f:
            data = json.load(f)
        summary["scans"]["secrets"] = f"completed ({len(data) if data else 0} findings)"
    except:
        pass

# Print summary
print("Security Scan Summary")
print("=" * 80)
print(json.dumps(summary, indent=2))

# Save summary
with open("security-scan-summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print("\n" + "=" * 80)
print("Reports saved to:")
print("  - backend/safety-report.json")
print("  - backend/bandit-report.json")
print("  - frontend/npm-audit-report.json")
print("  - frontend/eslint-report.json")
print("  - gitleaks-report.json")
print("  - security-scan-summary.json")

EOF
}

# Main
SCAN_TYPE="${1:-all}"

case "$SCAN_TYPE" in
    backend)
        scan_backend
        ;;
    frontend)
        scan_frontend
        ;;
    secrets)
        scan_secrets
        ;;
    all)
        scan_backend
        scan_frontend
        scan_secrets
        generate_report
        ;;
    *)
        print_error "Unknown scan type: $SCAN_TYPE"
        echo "Usage: $0 [backend|frontend|secrets|all]"
        exit 1
        ;;
esac

print_success "Security scanning completed!"
