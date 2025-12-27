#!/bin/bash

# Docker Build and Optimization Script
# This script builds optimized Docker images and performs security scanning
#
# Usage:
#   ./build-docker.sh [--scan] [--push] [--registry REGISTRY] [--tag TAG]
#
# Options:
#   --scan        Scan images with Trivy after building
#   --push        Push images to registry
#   --registry    Registry URL (default: localhost:5000)
#   --tag         Image tag (default: latest)
#   --help        Show this help message

set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
SCAN=false
PUSH=false
REGISTRY="localhost:5000"
TAG="latest"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --scan)
            SCAN=true
            shift
            ;;
        --push)
            PUSH=true
            shift
            ;;
        --registry)
            REGISTRY="$2"
            shift 2
            ;;
        --tag)
            TAG="$2"
            shift 2
            ;;
        --help)
            grep "^#" "$0" | head -20
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            exit 1
            ;;
    esac
done

# Functions
print_header() {
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}========================================${NC}\n"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    print_header "Checking Prerequisites"

    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed"
        exit 1
    fi
    print_success "Docker is installed"

    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed"
        exit 1
    fi
    print_success "Docker Compose is installed"

    if [ "$SCAN" = true ]; then
        if ! command -v trivy &> /dev/null; then
            print_warning "Trivy not found - skipping vulnerability scans"
            SCAN=false
        else
            print_success "Trivy is installed"
        fi
    fi
}

# Get image sizes
get_image_size() {
    docker inspect "$1" -f '{{.Size}}' | numfmt --to=iec-i --suffix=B 2>/dev/null || echo "N/A"
}

# Build images
build_images() {
    print_header "Building Docker Images"

    echo "Building backend image..."
    docker build \
        --tag "thebot-backend:${TAG}" \
        --tag "${REGISTRY}/thebot-backend:${TAG}" \
        --progress=plain \
        --build-arg ENVIRONMENT=production \
        "$SCRIPT_DIR/backend"

    if [ $? -eq 0 ]; then
        BACKEND_SIZE=$(get_image_size "thebot-backend:${TAG}")
        print_success "Backend image built: thebot-backend:${TAG} (Size: ${BACKEND_SIZE})"
    else
        print_error "Failed to build backend image"
        exit 1
    fi

    echo ""
    echo "Building frontend image..."
    docker build \
        --tag "thebot-frontend:${TAG}" \
        --tag "${REGISTRY}/thebot-frontend:${TAG}" \
        --progress=plain \
        "$SCRIPT_DIR/frontend"

    if [ $? -eq 0 ]; then
        FRONTEND_SIZE=$(get_image_size "thebot-frontend:${TAG}")
        print_success "Frontend image built: thebot-frontend:${TAG} (Size: ${FRONTEND_SIZE})"
    else
        print_error "Failed to build frontend image"
        exit 1
    fi
}

# Scan images for vulnerabilities
scan_images() {
    if [ "$SCAN" = false ]; then
        return
    fi

    print_header "Scanning Images for Vulnerabilities"

    echo "Scanning backend image..."
    trivy image --exit-code 0 --severity HIGH,CRITICAL "thebot-backend:${TAG}"
    print_success "Backend scan complete"

    echo ""
    echo "Scanning frontend image..."
    trivy image --exit-code 0 --severity HIGH,CRITICAL "thebot-frontend:${TAG}"
    print_success "Frontend scan complete"
}

# Display image information
show_image_info() {
    print_header "Image Information"

    echo -e "${YELLOW}Backend Image:${NC}"
    docker images "thebot-backend:${TAG}" --format "{{.Repository}}\t{{.Size}}\t{{.Created}}"

    echo -e "\n${YELLOW}Frontend Image:${NC}"
    docker images "thebot-frontend:${TAG}" --format "{{.Repository}}\t{{.Size}}\t{{.Created}}"

    echo -e "\n${YELLOW}Image Layers (Backend):${NC}"
    docker history "thebot-backend:${TAG}" --human --no-trunc | head -10

    echo -e "\n${YELLOW}Image Layers (Frontend):${NC}"
    docker history "thebot-frontend:${TAG}" --human --no-trunc | head -10
}

# Verify images can run
verify_images() {
    print_header "Verifying Images"

    echo "Testing backend image..."
    docker run --rm "thebot-backend:${TAG}" python --version
    print_success "Backend image verification passed"

    echo ""
    echo "Testing frontend image..."
    docker run --rm --entrypoint nginx "thebot-frontend:${TAG}" -v
    print_success "Frontend image verification passed"
}

# Push images to registry
push_images() {
    if [ "$PUSH" = false ]; then
        return
    fi

    print_header "Pushing Images to Registry"

    echo "Pushing backend image to ${REGISTRY}..."
    docker push "${REGISTRY}/thebot-backend:${TAG}"
    print_success "Backend image pushed"

    echo ""
    echo "Pushing frontend image to ${REGISTRY}..."
    docker push "${REGISTRY}/thebot-frontend:${TAG}"
    print_success "Frontend image pushed"
}

# Generate report
generate_report() {
    print_header "Build Summary Report"

    BACKEND_SIZE=$(get_image_size "thebot-backend:${TAG}")
    FRONTEND_SIZE=$(get_image_size "thebot-frontend:${TAG}")

    echo "Timestamp: $(date)"
    echo "Tag: ${TAG}"
    echo ""
    echo "Backend Image: thebot-backend:${TAG}"
    echo "  Size: ${BACKEND_SIZE}"
    echo "  Base: python:3.13-alpine3.21"
    echo "  Build Type: Multi-stage (builder + runtime)"
    echo "  User: appuser (UID 1001)"
    echo ""
    echo "Frontend Image: thebot-frontend:${TAG}"
    echo "  Size: ${FRONTEND_SIZE}"
    echo "  Base: nginx:1.27-alpine"
    echo "  Build Type: Multi-stage (builder + runtime)"
    echo "  User: www-data (UID 1001)"
    echo ""
    echo "Security Features:"
    echo "  ✓ Multi-stage builds (excludes build dependencies)"
    echo "  ✓ Non-root user execution"
    echo "  ✓ Pinned base image versions"
    echo "  ✓ Health checks configured"
    echo "  ✓ Read-only filesystem (frontend)"
    echo "  ✓ Security headers (nginx)"
    echo ""
    echo "Total Size: ~$(echo "$BACKEND_SIZE $FRONTEND_SIZE" | awk '{print $1 + $2}')"
}

# Main execution
main() {
    echo -e "${BLUE}"
    echo " ________          ______     ___________"
    echo "|__    __|        |  __  \\    |_____   _|"
    echo "   |  |   ____    | |  | |          | |"
    echo "   |  |  |  _ \\   | |__| |          | |"
    echo "   |  |  | (_) |  |  _  <           | |"
    echo "   |__|  |____/   |_| \\_|           |_|"
    echo "Docker Build & Optimization Script"
    echo -e "${NC}\n"

    check_prerequisites
    build_images
    verify_images
    show_image_info
    scan_images
    generate_report
    push_images

    print_header "Build Complete!"
    echo -e "${GREEN}All images built successfully!${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. Run services: docker-compose up -d"
    echo "  2. Check status: docker-compose ps"
    echo "  3. View logs: docker-compose logs -f"
    echo "  4. Access frontend: http://localhost:3000"
    echo "  5. Access backend: http://localhost:8000/api/"
}

# Run main function
main
