#!/bin/bash

# THE_BOT Platform Kubernetes Deployment Script
# This script deploys THE_BOT platform to Kubernetes
#
# Usage:
#   ./deploy.sh [options]
#
# Options:
#   -e, --environment     Environment: dev, staging, production (default: production)
#   -n, --namespace       Kubernetes namespace (default: thebot)
#   -d, --dry-run         Perform a dry-run (no actual deployment)
#   -w, --wait            Wait for deployment to complete
#   -t, --timeout         Timeout in seconds for waiting (default: 600)
#   -h, --help            Show this help message

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
ENVIRONMENT="production"
NAMESPACE="thebot"
DRY_RUN=false
WAIT=false
TIMEOUT=600
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse command line arguments
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
        -d|--dry-run)
            DRY_RUN=true
            shift
            ;;
        -w|--wait)
            WAIT=true
            shift
            ;;
        -t|--timeout)
            TIMEOUT="$2"
            shift 2
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

# Validate environment
if [[ ! "$ENVIRONMENT" =~ ^(dev|staging|production)$ ]]; then
    echo -e "${RED}Error: Invalid environment '$ENVIRONMENT'${NC}"
    echo "Valid options: dev, staging, production"
    exit 1
fi

# Adjust namespace for dev environment
if [[ "$ENVIRONMENT" == "dev" ]]; then
    NAMESPACE="thebot-dev"
elif [[ "$ENVIRONMENT" == "staging" ]]; then
    NAMESPACE="thebot-staging"
fi

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}THE_BOT Kubernetes Deployment${NC}"
echo -e "${BLUE}================================${NC}"
echo ""
echo -e "Environment: ${YELLOW}$ENVIRONMENT${NC}"
echo -e "Namespace: ${YELLOW}$NAMESPACE${NC}"
echo -e "Dry-run: ${YELLOW}$DRY_RUN${NC}"
echo -e "Wait: ${YELLOW}$WAIT${NC}"
echo ""

# Check prerequisites
echo -e "${BLUE}Checking prerequisites...${NC}"

if ! command -v kubectl &> /dev/null; then
    echo -e "${RED}Error: kubectl not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ kubectl found${NC}"

if ! command -v kustomize &> /dev/null; then
    echo -e "${RED}Error: kustomize not found${NC}"
    exit 1
fi
echo -e "${GREEN}✓ kustomize found${NC}"

# Check kubectl context
CONTEXT=$(kubectl config current-context)
echo -e "${GREEN}✓ kubectl context: $CONTEXT${NC}"

# Verify cluster connectivity
if ! kubectl cluster-info &> /dev/null; then
    echo -e "${RED}Error: Cannot connect to Kubernetes cluster${NC}"
    exit 1
fi
echo -e "${GREEN}✓ Connected to Kubernetes cluster${NC}"

echo ""

# Create namespace if it doesn't exist
if ! kubectl get namespace "$NAMESPACE" &> /dev/null; then
    echo -e "${BLUE}Creating namespace '$NAMESPACE'...${NC}"
    if [[ "$DRY_RUN" == "false" ]]; then
        kubectl create namespace "$NAMESPACE"
        echo -e "${GREEN}✓ Namespace created${NC}"
    else
        echo -e "${YELLOW}[DRY-RUN] Would create namespace${NC}"
    fi
fi

echo ""
echo -e "${BLUE}Generating manifests...${NC}"

# Generate manifests with kustomize
MANIFEST_FILE="/tmp/thebot-${ENVIRONMENT}-manifest.yaml"
kustomize build "$SCRIPT_DIR/overlays/$ENVIRONMENT" > "$MANIFEST_FILE"
echo -e "${GREEN}✓ Manifests generated: $MANIFEST_FILE${NC}"

# Count resources
RESOURCE_COUNT=$(grep -c "^kind:" "$MANIFEST_FILE" || echo "0")
echo -e "${GREEN}✓ Total resources: $RESOURCE_COUNT${NC}"

echo ""

if [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}[DRY-RUN] Would deploy the following resources:${NC}"
    echo ""
    kustomize build "$SCRIPT_DIR/overlays/$ENVIRONMENT" | \
        grep -E "^  (name|kind):" | sed 's/^/  /'
    echo ""
    echo -e "${YELLOW}To apply these changes, run without --dry-run:${NC}"
    echo -e "${YELLOW}  $0 -e $ENVIRONMENT${NC}"
    exit 0
fi

# Apply manifests
echo -e "${BLUE}Deploying to Kubernetes...${NC}"
echo ""

kubectl apply -f "$MANIFEST_FILE" --namespace="$NAMESPACE" -n "$NAMESPACE"

echo ""
echo -e "${GREEN}✓ Deployment submitted${NC}"

# Wait for deployment if requested
if [[ "$WAIT" == "true" ]]; then
    echo ""
    echo -e "${BLUE}Waiting for deployment to complete...${NC}"
    echo "(Timeout: ${TIMEOUT}s)"
    echo ""

    # Wait for backend deployment
    echo -e "Waiting for backend..."
    if kubectl rollout status deployment/backend -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
        echo -e "${GREEN}✓ Backend deployment complete${NC}"
    else
        echo -e "${RED}✗ Backend deployment timeout${NC}"
        exit 1
    fi

    # Wait for frontend deployment
    echo -e "Waiting for frontend..."
    if kubectl rollout status deployment/frontend -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
        echo -e "${GREEN}✓ Frontend deployment complete${NC}"
    else
        echo -e "${RED}✗ Frontend deployment timeout${NC}"
        exit 1
    fi

    # Wait for postgres statefulset
    echo -e "Waiting for database..."
    if kubectl rollout status statefulset/postgres -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
        echo -e "${GREEN}✓ Database deployment complete${NC}"
    else
        echo -e "${RED}✗ Database deployment timeout${NC}"
        exit 1
    fi

    # Wait for redis statefulset
    echo -e "Waiting for cache..."
    if kubectl rollout status statefulset/redis -n "$NAMESPACE" --timeout="${TIMEOUT}s"; then
        echo -e "${GREEN}✓ Cache deployment complete${NC}"
    else
        echo -e "${RED}✗ Cache deployment timeout${NC}"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}✓ All deployments complete${NC}"
fi

echo ""
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}Deployment Summary${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Show deployment status
echo -e "${BLUE}Deployments:${NC}"
kubectl get deployments -n "$NAMESPACE" -o wide

echo ""
echo -e "${BLUE}StatefulSets:${NC}"
kubectl get statefulsets -n "$NAMESPACE" -o wide

echo ""
echo -e "${BLUE}Services:${NC}"
kubectl get services -n "$NAMESPACE" -o wide

echo ""
echo -e "${BLUE}Ingresses:${NC}"
kubectl get ingress -n "$NAMESPACE" -o wide

echo ""
echo -e "${BLUE}PersistentVolumeClaims:${NC}"
kubectl get pvc -n "$NAMESPACE" -o wide

echo ""
echo -e "${BLUE}Pods:${NC}"
kubectl get pods -n "$NAMESPACE" -o wide

echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "1. Check pod status: kubectl get pods -n $NAMESPACE"
echo "2. View logs: kubectl logs -f deployment/backend -n $NAMESPACE"
echo "3. Port forward: kubectl port-forward svc/backend 8000:8000 -n $NAMESPACE"
echo "4. Access frontend: kubectl port-forward svc/frontend 3000:3000 -n $NAMESPACE"
echo ""

echo -e "${GREEN}✓ Deployment complete!${NC}"
