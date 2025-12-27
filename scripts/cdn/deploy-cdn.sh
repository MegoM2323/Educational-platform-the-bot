#!/bin/bash

# CloudFront CDN Deployment Script
# Deploys CloudFront distribution and configures backend/frontend for CDN
#
# Usage:
#   ./deploy-cdn.sh [environment] [action]
#
# Examples:
#   ./deploy-cdn.sh staging plan     # Plan staging deployment
#   ./deploy-cdn.sh staging apply    # Apply staging deployment
#   ./deploy-cdn.sh production apply # Deploy to production

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
TERRAFORM_DIR="$PROJECT_ROOT/infrastructure/terraform"
CDN_CONFIG_DIR="$PROJECT_ROOT/infrastructure/cdn"

ENVIRONMENT="${1:-staging}"
ACTION="${2:-plan}"

print_info() {
  echo -e "${BLUE}INFO${NC}: $1"
}

print_success() {
  echo -e "${GREEN}SUCCESS${NC}: $1"
}

print_warning() {
  echo -e "${YELLOW}WARNING${NC}: $1"
}

print_error() {
  echo -e "${RED}ERROR${NC}: $1"
}

show_usage() {
  cat << EOF
Usage: $(basename "$0") [ENVIRONMENT] [ACTION]

Arguments:
  ENVIRONMENT     Environment name (development, staging, production)
                  Default: staging
  ACTION          Terraform action (plan, apply, destroy)
                  Default: plan

Examples:
  # Plan staging deployment
  $(basename "$0") staging plan

  # Apply staging deployment
  $(basename "$0") staging apply

  # Plan production deployment
  $(basename "$0") production plan

  # Destroy staging (careful!)
  $(basename "$0") staging destroy

Prerequisites:
  - Terraform >= 1.0
  - AWS CLI configured with appropriate credentials
  - Docker (for infrastructure validation)
  - jq (for JSON parsing)

Required Files:
  - infrastructure/terraform/cloudfront.tf
  - infrastructure/terraform/functions/*.js
  - infrastructure/cdn/.env.example
  - scripts/cdn/invalidate-cache.sh

EOF
}

# Validate environment
validate_environment() {
  print_info "Validating environment..."

  # Check required tools
  for tool in terraform aws jq; do
    if ! command -v "$tool" &> /dev/null; then
      print_error "$tool is not installed"
      exit 1
    fi
  done

  # Check AWS credentials
  if ! aws sts get-caller-identity &> /dev/null; then
    print_error "AWS credentials not configured or invalid"
    exit 1
  fi

  # Check terraform files
  if [[ ! -f "$TERRAFORM_DIR/cloudfront.tf" ]]; then
    print_error "cloudfront.tf not found in $TERRAFORM_DIR"
    exit 1
  fi

  # Check terraform functions
  for fn in add-cache-headers add-cors-headers validate-signed-urls; do
    if [[ ! -f "$TERRAFORM_DIR/functions/$fn.js" ]]; then
      print_error "Function $fn.js not found"
      exit 1
    fi
  done

  print_success "Environment validation passed"
}

# Load or create terraform variables
setup_terraform_variables() {
  print_info "Setting up Terraform variables for $ENVIRONMENT..."

  local tfvars_file="$TERRAFORM_DIR/terraform-$ENVIRONMENT.tfvars"

  if [[ -f "$tfvars_file" ]]; then
    print_info "Using existing $tfvars_file"
    return
  fi

  print_warning "Creating new $tfvars_file"

  # Generate origin verify token
  local token=$(openssl rand -base64 32)

  # Get backend domain from environment or user
  local backend_domain="${BACKEND_DOMAIN:-api-$ENVIRONMENT.thebot.com}"

  cat > "$tfvars_file" << EOF
# CloudFront CDN Configuration for $ENVIRONMENT

environment              = "$ENVIRONMENT"
project_name             = "thebot-platform"
origin_domain_name       = "$backend_domain"
origin_custom_header_value = "$token"

enable_geo_restrictions = false
# geo_restriction_type   = "whitelist"
# geo_restriction_locations = ["US", "CA", "GB"]

tags = {
  Project     = "thebot-platform"
  Environment = "$ENVIRONMENT"
  Managed     = "terraform"
  CreatedAt   = "$(date -u +%Y-%m-%d)"
  CreatedBy   = "$(whoami)"
}
EOF

  print_success "Created $tfvars_file"
  print_info "Edit the file to customize settings:"
  echo "  $tfvars_file"
}

# Initialize terraform
terraform_init() {
  print_info "Initializing Terraform..."

  cd "$TERRAFORM_DIR"
  terraform init
  print_success "Terraform initialized"
}

# Validate terraform
terraform_validate() {
  print_info "Validating Terraform configuration..."

  cd "$TERRAFORM_DIR"
  terraform validate
  print_success "Terraform configuration valid"
}

# Plan terraform deployment
terraform_plan() {
  print_info "Planning Terraform deployment for $ENVIRONMENT..."

  cd "$TERRAFORM_DIR"

  local tfvars_file="terraform-$ENVIRONMENT.tfvars"

  if [[ ! -f "$tfvars_file" ]]; then
    print_error "Variables file not found: $tfvars_file"
    print_info "Run setup_terraform_variables first"
    exit 1
  fi

  terraform plan \
    -var-file="$tfvars_file" \
    -out="tfplan-$ENVIRONMENT"

  print_success "Plan created: tfplan-$ENVIRONMENT"
  print_info "Review plan with: terraform show tfplan-$ENVIRONMENT"
}

# Apply terraform deployment
terraform_apply() {
  print_info "Applying Terraform deployment for $ENVIRONMENT..."

  cd "$TERRAFORM_DIR"

  local tfplan_file="tfplan-$ENVIRONMENT"

  if [[ ! -f "$tfplan_file" ]]; then
    print_warning "Plan file not found, creating new plan..."
    terraform_plan
  fi

  # Confirm before applying
  read -p "Are you sure you want to apply this plan? (yes/no): " -r
  if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
    print_info "Cancelled"
    return
  fi

  terraform apply "$tfplan_file"

  print_success "Terraform deployment completed"
  capture_outputs
}

# Capture terraform outputs
capture_outputs() {
  print_info "Capturing CloudFront outputs..."

  cd "$TERRAFORM_DIR"

  local outputs_file="$PROJECT_ROOT/.cdn-outputs-$ENVIRONMENT.json"

  # Extract outputs
  terraform output -json > "$outputs_file"

  # Extract key values
  local domain=$(jq -r '.cloudfront_domain_name.value' "$outputs_file")
  local dist_id=$(jq -r '.cloudfront_distribution_id.value' "$outputs_file")
  local key_group=$(jq -r '.cloudfront_key_group_id.value' "$outputs_file")
  local pub_key=$(jq -r '.cloudfront_public_key_id.value' "$outputs_file")
  local logs_bucket=$(jq -r '.s3_logs_bucket.value' "$outputs_file")

  cat > "$PROJECT_ROOT/.env.cdn-$ENVIRONMENT" << EOF
# CloudFront CDN Configuration - Auto-generated from Terraform
# Generated: $(date)

CLOUDFRONT_DOMAIN=$domain
CLOUDFRONT_DISTRIBUTION_ID=$dist_id
CLOUDFRONT_KEY_GROUP_ID=$key_group
CLOUDFRONT_PUBLIC_KEY_ID=$pub_key
CDN_LOGS_BUCKET=$logs_bucket

# Set this in your main .env file
STATIC_URL_CDN=https://$domain/static/
MEDIA_URL_CDN=https://$domain/media/
VITE_CDN_DOMAIN=$domain
EOF

  print_success "Outputs saved to .env.cdn-$ENVIRONMENT"
  print_info ""
  print_info "CloudFront Outputs:"
  echo "  Domain: $domain"
  echo "  Distribution ID: $dist_id"
  echo "  Key Group ID: $key_group"
  echo "  Public Key ID: $pub_key"
  echo "  Logs Bucket: $logs_bucket"
  echo ""
  print_info "To use, add to your .env:"
  cat "$PROJECT_ROOT/.env.cdn-$ENVIRONMENT" | grep -v "^#"
}

# Destroy terraform deployment
terraform_destroy() {
  print_warning "This will destroy the CloudFront distribution for $ENVIRONMENT!"
  read -p "Are you absolutely sure? Type environment name to confirm: " -r

  if [[ "$REPLY" != "$ENVIRONMENT" ]]; then
    print_info "Cancelled"
    return
  fi

  cd "$TERRAFORM_DIR"

  local tfvars_file="terraform-$ENVIRONMENT.tfvars"

  if [[ ! -f "$tfvars_file" ]]; then
    print_error "Variables file not found: $tfvars_file"
    exit 1
  fi

  terraform destroy \
    -var-file="$tfvars_file" \
    -auto-approve

  print_success "CloudFront distribution destroyed"
}

# Show status
show_status() {
  print_info "CloudFront Distribution Status for $ENVIRONMENT"

  cd "$TERRAFORM_DIR"

  if [[ ! -f "terraform-$ENVIRONMENT.tfvars" ]]; then
    print_info "No deployment for $ENVIRONMENT"
    return
  fi

  terraform show -json | jq '.values.root_module.resources[] | {type, address, values}'
}

# Main flow
main() {
  print_info "CloudFront CDN Deployment"
  print_info "Environment: $ENVIRONMENT"
  print_info "Action: $ACTION"
  echo ""

  # Validate prerequisites
  validate_environment

  # Setup terraform variables
  setup_terraform_variables

  # Initialize terraform
  terraform_init

  # Validate configuration
  terraform_validate

  # Execute action
  case "$ACTION" in
    plan)
      terraform_plan
      ;;
    apply)
      terraform_plan
      terraform_apply
      ;;
    destroy)
      terraform_destroy
      ;;
    status)
      show_status
      ;;
    *)
      print_error "Unknown action: $ACTION"
      echo "Valid actions: plan, apply, destroy, status"
      exit 1
      ;;
  esac

  print_success "Deployment script completed"
}

# Show help if requested
if [[ "${1:-}" == "-h" ]] || [[ "${1:-}" == "--help" ]]; then
  show_usage
  exit 0
fi

# Run main
main
