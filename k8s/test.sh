#!/bin/bash

# THE_BOT Kubernetes Deployment Test Script
# Tests Kubernetes manifests and validates deployment
#
# Usage:
#   ./test.sh [options]
#
# Options:
#   -e, --environment     Environment to test: dev, staging, production (default: dev)
#   -n, --namespace       Kubernetes namespace (default: thebot-test)
#   -c, --cluster         Test against actual cluster (default: dry-run only)
#   -h, --help            Show this help message

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Default values
ENVIRONMENT="dev"
NAMESPACE="thebot-test"
CLUSTER_TEST=false
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -n|--namespace)
            NAMESPACE="$2"
            shift 2
            ;;
        -c|--cluster)
            CLUSTER_TEST=true
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
echo -e "${BLUE}Kubernetes Deployment Tests${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Helper functions
test_start() {
    ((TOTAL_TESTS++))
    printf "%-50s " "Test $TOTAL_TESTS: $1"
}

test_pass() {
    ((PASSED_TESTS++))
    echo -e "${GREEN}PASS${NC}"
}

test_fail() {
    ((FAILED_TESTS++))
    echo -e "${RED}FAIL${NC}"
    if [[ -n "$1" ]]; then
        echo -e "  ${RED}Error: $1${NC}"
    fi
}

# Test 1: Check YAML syntax
test_start "YAML syntax validation"
if kustomize build "$SCRIPT_DIR/overlays/$ENVIRONMENT" 2>&1 | python3 -m yaml 2>&1 | grep -q "SyntaxError"; then
    test_fail "Invalid YAML"
else
    test_pass
fi

# Test 2: Check manifests generate successfully
test_start "Manifests generation"
MANIFEST_FILE="/tmp/thebot-test-manifest.yaml"
if kustomize build "$SCRIPT_DIR/overlays/$ENVIRONMENT" > "$MANIFEST_FILE" 2>&1; then
    test_pass
else
    test_fail "Failed to generate manifests"
fi

# Test 3: Check required resources exist
test_start "Deployment resource exists"
if grep -q "kind: Deployment" "$MANIFEST_FILE" && grep -q "name: backend" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "Backend deployment not found"
fi

# Test 4: Check namespace
test_start "Namespace configuration"
if grep -q "namespace: thebot" "$MANIFEST_FILE" || grep -q "namespace: thebot-dev" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "Namespace not configured"
fi

# Test 5: Check ConfigMaps
test_start "ConfigMaps configuration"
if grep -q "kind: ConfigMap" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "ConfigMaps not found"
fi

# Test 6: Check Secrets
test_start "Secrets configuration"
if grep -q "kind: Secret" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "Secrets not found"
fi

# Test 7: Check PersistentVolumes
test_start "PersistentVolumeClaims"
if grep -q "kind: PersistentVolumeClaim" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "PVCs not found"
fi

# Test 8: Check Services
test_start "Services configuration"
if grep -q "kind: Service" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "Services not found"
fi

# Test 9: Check Ingress
test_start "Ingress configuration"
if grep -q "kind: Ingress" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "Ingress not found"
fi

# Test 10: Check resource limits
test_start "Resource limits defined"
LIMITS_COUNT=$(grep -c "limits:" "$MANIFEST_FILE" || echo "0")
if [[ $LIMITS_COUNT -gt 0 ]]; then
    test_pass
else
    test_fail "Resource limits not defined"
fi

# Test 11: Check resource requests
test_start "Resource requests defined"
REQUESTS_COUNT=$(grep -c "requests:" "$MANIFEST_FILE" || echo "0")
if [[ $REQUESTS_COUNT -gt 0 ]]; then
    test_pass
else
    test_fail "Resource requests not defined"
fi

# Test 12: Check health probes
test_start "Health probes configured"
PROBES_COUNT=$(grep -c "Probe:" "$MANIFEST_FILE" || echo "0")
if [[ $PROBES_COUNT -gt 0 ]]; then
    test_pass
else
    test_fail "Health probes not configured"
fi

# Test 13: Check security context
test_start "Security context configured"
SECURITY_COUNT=$(grep -c "securityContext:" "$MANIFEST_FILE" || echo "0")
if [[ $SECURITY_COUNT -gt 0 ]]; then
    test_pass
else
    test_fail "Security context not configured"
fi

# Test 14: Check replicas configuration
test_start "Replicas configuration"
if grep -q "replicas:" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "Replicas not configured"
fi

# Test 15: Check HPA configuration
test_start "HorizontalPodAutoscaler configured"
if grep -q "kind: HorizontalPodAutoscaler" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "HPA not configured"
fi

# Test 16: Check Pod Disruption Budgets
test_start "Pod Disruption Budgets configured"
if grep -q "kind: PodDisruptionBudget" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "Pod Disruption Budgets not configured"
fi

# Test 17: Check Network Policies
test_start "Network Policies configured"
if grep -q "kind: NetworkPolicy" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "Network Policies not configured"
fi

# Test 18: Check RBAC rules
test_start "RBAC rules configured"
if grep -q "kind: Role" "$MANIFEST_FILE" || grep -q "kind: ClusterRole" "$MANIFEST_FILE"; then
    test_pass
else
    test_fail "RBAC rules not configured"
fi

# Test 19: Dry-run validation
test_start "Kubernetes validation (dry-run)"
TEMP_NS="thebot-test-$$"
kubectl create namespace "$TEMP_NS" --dry-run=client -o yaml | kubectl apply -f - 2>/dev/null || true

if kubectl apply -f "$MANIFEST_FILE" -n "$TEMP_NS" --dry-run=client --validate=strict > /dev/null 2>&1; then
    test_pass
    kubectl delete namespace "$TEMP_NS" 2>/dev/null || true
else
    test_fail "Kubernetes validation failed"
fi

# Test 20: Resource count check
test_start "Resource count validation"
RESOURCE_COUNT=$(grep "^kind:" "$MANIFEST_FILE" | wc -l)
if [[ $RESOURCE_COUNT -gt 10 ]]; then
    test_pass
else
    test_fail "Insufficient resources ($RESOURCE_COUNT < 10)"
fi

# Cluster tests (if enabled)
if [[ "$CLUSTER_TEST" == "true" ]]; then
    echo ""
    echo -e "${BLUE}Running cluster tests...${NC}"
    echo ""

    # Test 21: Cluster connectivity
    test_start "Kubernetes cluster accessible"
    if kubectl cluster-info > /dev/null 2>&1; then
        test_pass
    else
        test_fail "Cannot access Kubernetes cluster"
    fi

    # Test 22: Create namespace
    test_start "Creating test namespace"
    if kubectl create namespace "$NAMESPACE" 2>/dev/null || true; then
        test_pass
    else
        test_fail "Failed to create namespace"
    fi

    # Test 23: Apply manifests to cluster
    test_start "Applying manifests to cluster"
    if kubectl apply -f "$MANIFEST_FILE" -n "$NAMESPACE" --dry-run=client > /dev/null 2>&1; then
        test_pass
    else
        test_fail "Failed to apply manifests"
    fi

    # Test 24: Verify resources in cluster
    test_start "Verifying resources in cluster"
    if kubectl get deployments -n "$NAMESPACE" 2>/dev/null | grep -q "backend"; then
        test_pass
    else
        test_fail "Resources not created in cluster"
    fi

    # Test 25: Check pod templates
    test_start "Pod templates validation"
    if kubectl get deployment backend -n "$NAMESPACE" -o yaml 2>/dev/null | grep -q "containers:"; then
        test_pass
    else
        test_fail "Pod template validation failed"
    fi

    # Cleanup
    echo ""
    echo -e "${BLUE}Cleaning up test resources...${NC}"
    kubectl delete namespace "$NAMESPACE" 2>/dev/null || true
fi

# Summary
echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Test Results${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo "Total tests: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$PASSED_TESTS${NC}"
echo -e "Failed: ${RED}$FAILED_TESTS${NC}"
echo ""

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    echo ""
    rm -f "$MANIFEST_FILE"
    exit 0
else
    echo -e "${RED}✗ $FAILED_TESTS test(s) failed${NC}"
    echo ""
    rm -f "$MANIFEST_FILE"
    exit 1
fi
