#!/bin/bash

# CloudFront Cache Invalidation Script
# Invalidates CloudFront cache for deployed assets and media files
#
# Usage:
#   ./invalidate-cache.sh [--distribution-id ID] [--paths "path1" "path2"] [--all]
#
# Examples:
#   # Invalidate all paths (full distribution)
#   ./invalidate-cache.sh --all
#
#   # Invalidate specific paths
#   ./invalidate-cache.sh --paths "/index.html" "/js/*" "/css/*"
#
#   # Invalidate after static file deployment
#   ./invalidate-cache.sh --paths "/static/*" "/assets/*"
#
#   # Invalidate media files
#   ./invalidate-cache.sh --paths "/media/*"

set -euo pipefail

# Color output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default variables
DISTRIBUTION_ID="${CLOUDFRONT_DISTRIBUTION_ID:-}"
INVALIDATE_ALL=false
PATHS=()
DRY_RUN=false
BATCH_SIZE=3000  # AWS CloudFront limit per invalidation request
AWS_REGION="${AWS_REGION:-us-east-1}"

# Helper functions
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
Usage: $(basename "$0") [OPTIONS]

Options:
  -d, --distribution-id ID    CloudFront distribution ID (or set CLOUDFRONT_DISTRIBUTION_ID env var)
  -p, --paths PATH1 PATH2     Space-separated list of paths to invalidate
  -a, --all                   Invalidate all paths (/*)
  --dry-run                   Show what would be invalidated without actually invalidating
  -h, --help                  Show this help message

Examples:
  # Invalidate all
  $(basename "$0") --distribution-id E123ABC456 --all

  # Invalidate specific paths
  $(basename "$0") --distribution-id E123ABC456 --paths "/index.html" "/js/*" "/css/*"

  # Invalidate static assets
  $(basename "$0") --distribution-id E123ABC456 --paths "/static/*" "/assets/*"

  # Test without actually invalidating
  $(basename "$0") --distribution-id E123ABC456 --all --dry-run

Environment Variables:
  CLOUDFRONT_DISTRIBUTION_ID    CloudFront distribution ID
  AWS_REGION                     AWS region (default: us-east-1)

EOF
}

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    -d|--distribution-id)
      DISTRIBUTION_ID="$2"
      shift 2
      ;;
    -p|--paths)
      shift
      while [[ $# -gt 0 ]] && [[ ! "$1" =~ ^- ]]; do
        PATHS+=("$1")
        shift
      done
      ;;
    -a|--all)
      INVALIDATE_ALL=true
      shift
      ;;
    --dry-run)
      DRY_RUN=true
      shift
      ;;
    -h|--help)
      show_usage
      exit 0
      ;;
    *)
      print_error "Unknown option: $1"
      show_usage
      exit 1
      ;;
  esac
done

# Validate inputs
if [[ -z "$DISTRIBUTION_ID" ]]; then
  print_error "Distribution ID not provided"
  print_info "Set CLOUDFRONT_DISTRIBUTION_ID environment variable or use --distribution-id"
  show_usage
  exit 1
fi

# Check AWS CLI is installed
if ! command -v aws &> /dev/null; then
  print_error "AWS CLI is not installed"
  exit 1
fi

# Validate AWS credentials
if ! aws sts get-caller-identity &> /dev/null; then
  print_error "AWS credentials not configured or invalid"
  exit 1
fi

# Determine paths to invalidate
if [[ "$INVALIDATE_ALL" == true ]]; then
  PATHS=("/*")
  print_warning "Invalidating ALL paths - this will be more expensive"
elif [[ ${#PATHS[@]} -eq 0 ]]; then
  print_error "No paths specified"
  print_info "Use --all to invalidate all paths, or --paths to specify paths"
  show_usage
  exit 1
fi

print_info "CloudFront Cache Invalidation"
print_info "Distribution ID: $DISTRIBUTION_ID"
print_info "Region: $AWS_REGION"
print_info "Number of paths: ${#PATHS[@]}"
print_info "Paths to invalidate:"
for path in "${PATHS[@]}"; do
  echo "  - $path"
done

# Check path count against AWS limit
if [[ ${#PATHS[@]} -gt $BATCH_SIZE ]]; then
  print_warning "Path count (${#PATHS[@]}) exceeds AWS limit per request ($BATCH_SIZE)"
  print_info "Will batch invalidations into multiple requests"
fi

# Show cost estimate
ESTIMATED_PATHS=${#PATHS[@]}
if [[ ${#PATHS[@]} -gt $BATCH_SIZE ]]; then
  NUM_REQUESTS=$(( (ESTIMATED_PATHS + BATCH_SIZE - 1) / BATCH_SIZE ))
  ESTIMATED_COST=$(echo "scale=2; $NUM_REQUESTS * 0.005" | bc)
  print_warning "Estimated cost: \$$ESTIMATED_COST (${NUM_REQUESTS} requests @ \$0.005/path)"
else
  ESTIMATED_COST=$(echo "scale=4; $ESTIMATED_PATHS * 0.005" | bc)
  print_info "Estimated cost: \$$ESTIMATED_COST"
fi

if [[ "$DRY_RUN" == true ]]; then
  print_warning "DRY RUN MODE - No actual invalidation will occur"
  exit 0
fi

# Confirm before proceeding
read -p "Proceed with cache invalidation? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy][Ee][Ss]$ ]]; then
  print_info "Cancelled"
  exit 0
fi

# Perform invalidation(s)
print_info "Starting cache invalidation..."

# Batch paths if necessary
BATCH_NUMBER=1
TOTAL_BATCHES=$(( (${#PATHS[@]} + BATCH_SIZE - 1) / BATCH_SIZE ))
INVALIDATION_IDS=()

for ((i=0; i<${#PATHS[@]}; i+=BATCH_SIZE)); do
  BATCH=("${PATHS[@]:$i:$BATCH_SIZE}")
  BATCH_LENGTH=${#BATCH[@]}

  print_info "Batch $BATCH_NUMBER/$TOTAL_BATCHES ($BATCH_LENGTH paths)"

  # Create invalidation request JSON
  ITEMS_JSON=$(printf '"%s",' "${BATCH[@]}" | sed 's/,$//')

  INVALIDATION_JSON=$(cat <<EOF
{
  "DistributionId": "$DISTRIBUTION_ID",
  "InvalidationBatch": {
    "Paths": {
      "Quantity": $BATCH_LENGTH,
      "Items": [$ITEMS_JSON]
    },
    "CallerReference": "$(date +%s)-batch-$BATCH_NUMBER"
  }
}
EOF
)

  # Submit invalidation request
  RESPONSE=$(aws cloudfront create-invalidation \
    --cli-input-json "$INVALIDATION_JSON" \
    --region "$AWS_REGION" \
    --output json)

  INVALIDATION_ID=$(echo "$RESPONSE" | jq -r '.Invalidation.Id')
  STATUS=$(echo "$RESPONSE" | jq -r '.Invalidation.Status')

  if [[ -z "$INVALIDATION_ID" ]] || [[ "$INVALIDATION_ID" == "null" ]]; then
    print_error "Failed to create invalidation batch $BATCH_NUMBER"
    echo "$RESPONSE" | jq .
    exit 1
  fi

  INVALIDATION_IDS+=("$INVALIDATION_ID")
  print_success "Batch $BATCH_NUMBER submitted with ID: $INVALIDATION_ID (Status: $STATUS)"

  BATCH_NUMBER=$((BATCH_NUMBER + 1))

  # Rate limiting between batches
  if [[ $BATCH_NUMBER -le $TOTAL_BATCHES ]]; then
    sleep 2
  fi
done

print_success "All invalidation requests submitted"
print_info ""
print_info "Invalidation IDs:"
for id in "${INVALIDATION_IDS[@]}"; do
  echo "  - $id"
done

# Monitor invalidation progress
print_info ""
print_info "Monitoring invalidation progress..."

COMPLETED=0
FAILED=0
TIMEOUT=0
START_TIME=$(date +%s)
MAX_WAIT_SECONDS=$((15 * 60))  # 15 minutes max wait

while [[ $COMPLETED -lt ${#INVALIDATION_IDS[@]} ]]; do
  CURRENT_TIME=$(date +%s)
  ELAPSED=$((CURRENT_TIME - START_TIME))

  if [[ $ELAPSED -gt $MAX_WAIT_SECONDS ]]; then
    print_warning "Timeout waiting for invalidation to complete"
    TIMEOUT=1
    break
  fi

  for id in "${INVALIDATION_IDS[@]}"; do
    STATUS=$(aws cloudfront get-invalidation \
      --distribution-id "$DISTRIBUTION_ID" \
      --id "$id" \
      --region "$AWS_REGION" \
      --query 'Invalidation.Status' \
      --output text)

    if [[ "$STATUS" == "Completed" ]]; then
      print_success "Invalidation $id completed"
      COMPLETED=$((COMPLETED + 1))
    elif [[ "$STATUS" == "Failed" ]]; then
      print_error "Invalidation $id failed"
      FAILED=$((FAILED + 1))
    fi
  done

  if [[ $COMPLETED -lt ${#INVALIDATION_IDS[@]} ]]; then
    echo -ne "\rProgress: $COMPLETED/${#INVALIDATION_IDS[@]} invalidations completed... (${ELAPSED}s)"
    sleep 5
  fi
done

echo ""

# Final status
print_info "Invalidation Summary:"
print_success "Completed: $COMPLETED/${#INVALIDATION_IDS[@]}"
if [[ $FAILED -gt 0 ]]; then
  print_error "Failed: $FAILED"
fi
if [[ $TIMEOUT -eq 1 ]]; then
  print_warning "Timeout occurred - invalidations may still be processing"
fi

# Calculate total cost
TOTAL_PATHS=0
for ((i=0; i<${#PATHS[@]}; i+=BATCH_SIZE)); do
  TOTAL_PATHS=$((TOTAL_PATHS + 1))
done

TOTAL_COST=$(echo "scale=2; $TOTAL_PATHS * 0.005" | bc)
print_info "Total cost: \$$TOTAL_COST"

# Exit with appropriate code
if [[ $FAILED -gt 0 ]] || [[ $TIMEOUT -eq 1 ]]; then
  exit 1
else
  exit 0
fi
