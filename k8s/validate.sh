#!/bin/bash

# THE_BOT Kubernetes Manifests Validation Script
# Validates all Kubernetes manifests for syntax and best practices
#
# Usage:
#   ./validate.sh [options]
#
# Options:
#   -e, --environment     Environment to validate: dev, staging, production (default: all)
#   -s, --strict          Enable strict validation mode
#   -h, --help            Show this help message

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT=""
STRICT=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ERRORS=0
WARNINGS=0

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -s|--strict)
            STRICT=true
            shift
            ;;
        -h|--help)
            grep "^#" "$0" | head -20
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Kubernetes Manifests Validator${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found${NC}"
    exit 1
fi

if ! command -v kustomize &> /dev/null; then
    echo -e "${RED}Error: kustomize not found${NC}"
    exit 1
fi

if ! command -v yamllint &> /dev/null; then
    echo -e "${YELLOW}Warning: yamllint not found (syntax validation disabled)${NC}"
    YAMLLINT=false
else
    YAMLLINT=true
fi

if ! command -v kubeval &> /dev/null; then
    echo -e "${YELLOW}Warning: kubeval not found (schema validation disabled)${NC}"
    KUBEVAL=false
else
    KUBEVAL=true
fi

echo -e "${GREEN}✓ Prerequisites checked${NC}"
echo ""

# Function to validate a directory
validate_environment() {
    local env=$1
    local overlay_path="$SCRIPT_DIR/overlays/$env"

    if [[ ! -d "$overlay_path" ]]; then
        echo -e "${RED}Error: Environment directory not found: $overlay_path${NC}"
        return 1
    fi

    echo -e "${BLUE}Validating $env environment...${NC}"
    echo ""

    # Generate manifests
    local manifest_file="/tmp/thebot-${env}-validation.yaml"
    echo -e "Generating manifests..."

    if ! kustomize build "$overlay_path" > "$manifest_file" 2>&1; then
        echo -e "${RED}✗ Kustomize build failed${NC}"
        ((ERRORS++))
        return 1
    fi

    echo -e "${GREEN}✓ Manifests generated${NC}"

    # YAML syntax validation
    if [[ "$YAMLLINT" == "true" ]]; then
        echo -e "Validating YAML syntax..."
        if yamllint -c relaxed "$manifest_file" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ YAML syntax valid${NC}"
        else
            echo -e "${RED}✗ YAML syntax errors:${NC}"
            yamllint -c relaxed "$manifest_file" || true
            ((WARNINGS++))
        fi
    fi

    # Kubernetes schema validation
    if [[ "$KUBEVAL" == "true" ]]; then
        echo -e "Validating Kubernetes schema..."
        if kubeval --strict "$manifest_file" > /dev/null 2>&1; then
            echo -e "${GREEN}✓ Kubernetes schema valid${NC}"
        else
            echo -e "${RED}✗ Schema validation errors:${NC}"
            kubeval --strict "$manifest_file" || true
            ((WARNINGS++))
        fi
    fi

    # Dry-run validation
    echo -e "Performing dry-run validation..."

    # Create temporary namespace
    local temp_ns="thebot-validation-$$"
    kubectl create namespace "$temp_ns" --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true

    if kubectl apply -f "$manifest_file" -n "$temp_ns" --dry-run=client --validate=strict > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Dry-run validation passed${NC}"
    else
        echo -e "${RED}✗ Dry-run validation failed:${NC}"
        kubectl apply -f "$manifest_file" -n "$temp_ns" --dry-run=client --validate=strict || true
        ((ERRORS++))
    fi

    # Clean up
    kubectl delete namespace "$temp_ns" --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true

    # Check for common issues
    echo -e "Checking for common issues..."
    local issues_found=false

    # Check for latest image tags
    if grep -q "image:.*:latest" "$manifest_file"; then
        echo -e "${YELLOW}! Using 'latest' image tag (not recommended for production)${NC}"
        ((WARNINGS++))
        issues_found=true
    fi

    # Check for resource limits
    if ! grep -q "requests:" "$manifest_file"; then
        echo -e "${YELLOW}! Some containers missing resource requests${NC}"
        ((WARNINGS++))
        issues_found=true
    fi

    # Check for health probes
    if ! grep -q "livenessProbe:" "$manifest_file"; then
        echo -e "${YELLOW}! Some containers missing liveness probes${NC}"
        ((WARNINGS++))
        issues_found=true
    fi

    # Check for security context
    if ! grep -q "securityContext:" "$manifest_file"; then
        echo -e "${YELLOW}! Some containers missing security context${NC}"
        ((WARNINGS++))
        issues_found=true
    fi

    if [[ "$issues_found" == "false" ]]; then
        echo -e "${GREEN}✓ No common issues found${NC}"
    fi

    # Count resources
    echo -e "Counting resources..."
    local kind_count=$(grep "^kind:" "$manifest_file" | wc -l)
    echo -e "${GREEN}✓ Total resources: $kind_count${NC}"

    # List resource types
    echo -e "Resource types:"
    grep "^kind:" "$manifest_file" | sort | uniq -c | sed 's/^/  /'

    # Cleanup
    rm -f "$manifest_file"

    echo ""
    return 0
}

# Validate environments
if [[ -z "$ENVIRONMENT" ]]; then
    # Validate all environments
    for env in dev staging production; do
        validate_environment "$env" || true
        echo ""
    done
else
    # Validate specific environment
    validate_environment "$ENVIRONMENT" || exit 1
fi

# Summary
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Validation Summary${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

if [[ $ERRORS -eq 0 && $WARNINGS -eq 0 ]]; then
    echo -e "${GREEN}✓ All validations passed!${NC}"
    exit 0
elif [[ $ERRORS -eq 0 ]]; then
    echo -e "${YELLOW}⚠ Validation complete with $WARNINGS warning(s)${NC}"
    if [[ "$STRICT" == "true" ]]; then
        exit 1
    fi
    exit 0
else
    echo -e "${RED}✗ Validation failed with $ERRORS error(s) and $WARNINGS warning(s)${NC}"
    exit 1
fi
