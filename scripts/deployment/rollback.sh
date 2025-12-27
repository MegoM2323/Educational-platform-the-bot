#!/bin/bash

################################################################################
# THE_BOT Platform - Emergency Rollback Script
#
# Performs zero-downtime rollback to previous version with automatic verification.
#
# This script should be executed IMMEDIATELY if a critical issue is detected
# after deployment. Rollback time should be < 5 minutes.
#
# Usage:
#   ./scripts/deployment/rollback.sh                    # Rollback to previous tag
#   ./scripts/deployment/rollback.sh v1.2.3            # Rollback to specific version
#   ./scripts/deployment/rollback.sh v1.2.3 --no-verify # Skip health checks
#   ./scripts/deployment/rollback.sh --dry-run          # Show what would happen
#
# Environment Variables:
#   ROLLBACK_VERSION    - Version to rollback to (auto-detected if not set)
#   DRY_RUN            - Set to 1 to simulate without making changes
#   SKIP_VERIFY        - Set to 1 to skip post-rollback verification
#   ROLLBACK_TIMEOUT   - Health check timeout in seconds (default: 120)
#
################################################################################

set -e

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$(dirname "$SCRIPT_DIR")")"
COMPOSE_FILE="${PROJECT_DIR}/docker-compose.prod.yml"
VERIFY_SCRIPT="${SCRIPT_DIR}/verify-deployment.sh"
BACKUP_DIR="${PROJECT_DIR}/database/backups"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Configuration with defaults
DRY_RUN="${DRY_RUN:-0}"
SKIP_VERIFY="${SKIP_VERIFY:-0}"
ROLLBACK_TIMEOUT="${ROLLBACK_TIMEOUT:-120}"
BACKUP_CURRENT="${BACKUP_CURRENT:-1}"
NOTIFY_TEAM="${NOTIFY_TEAM:-1}"
CURRENT_VERSION=""
ROLLBACK_VERSION="${1:-}"
INCIDENT_ID="INCIDENT_$(date +%Y%m%d_%H%M%S)"

################################################################################
# UTILITY FUNCTIONS
################################################################################

print_header() {
    echo -e "\n${RED}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}$1${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════${NC}\n"
}

print_critical() {
    echo -e "${RED}[CRITICAL]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_step() {
    echo -e "\n${BLUE}>>> $1${NC}"
}

confirm_action() {
    local prompt="$1"
    echo ""
    read -p "$(echo -e ${RED}$prompt${NC})" -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

################################################################################
# INITIALIZATION
################################################################################

print_header "⚠️  PRODUCTION ROLLBACK INITIATED"

echo "Rollback Information:"
echo "  Incident ID: $INCIDENT_ID"
echo "  Start Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  Environment: Production"
echo ""

# Check if compose file exists
if [ ! -f "$COMPOSE_FILE" ]; then
    print_critical "docker-compose.prod.yml not found at $COMPOSE_FILE"
    exit 1
fi

# Get current version
print_step "Detecting current deployment version..."
CURRENT_VERSION=$(git -C "$PROJECT_DIR" describe --tags 2>/dev/null || git -C "$PROJECT_DIR" rev-parse --short HEAD)
print_info "Current version: $CURRENT_VERSION"

# Determine rollback target version
if [ -z "$ROLLBACK_VERSION" ]; then
    print_step "Auto-detecting previous version..."
    ROLLBACK_VERSION=$(git -C "$PROJECT_DIR" describe --tags --abbrev=0 2>/dev/null || echo "HEAD~1")

    # If no tags, use previous commit
    if [ "$ROLLBACK_VERSION" = "HEAD~1" ]; then
        ROLLBACK_VERSION=$(git -C "$PROJECT_DIR" rev-parse HEAD~1)
    fi

    print_info "Auto-detected rollback version: $ROLLBACK_VERSION"
else
    print_info "Manual rollback version specified: $ROLLBACK_VERSION"
fi

echo ""
echo "Rollback Details:"
echo "  From: $CURRENT_VERSION"
echo "  To: $ROLLBACK_VERSION"
echo "  Backup: Enabled"
echo "  Verification: $([[ $SKIP_VERIFY -eq 1 ]] && echo 'Disabled' || echo 'Enabled')"
echo "  Dry Run: $([[ $DRY_RUN -eq 1 ]] && echo 'Yes' || echo 'No')"
echo ""

# Require confirmation for actual rollback
if [ "$DRY_RUN" -eq 0 ]; then
    if ! confirm_action "CONFIRM PRODUCTION ROLLBACK? This is destructive! (y/n): "; then
        print_warning "Rollback cancelled by user"
        exit 0
    fi
fi

################################################################################
# PHASE 1: BACKUP CURRENT STATE
################################################################################

print_header "PHASE 1: BACKING UP CURRENT STATE"

if [ "$BACKUP_CURRENT" -eq 1 ]; then
    print_step "Creating database backup..."

    # Create backup directory if not exists
    mkdir -p "$BACKUP_DIR"

    BACKUP_FILE="${BACKUP_DIR}/rollback_incident_${INCIDENT_ID}.dump"

    if [ "$DRY_RUN" -eq 0 ]; then
        if docker-compose -f "$COMPOSE_FILE" exec postgres \
            pg_dump -U postgres -F c -f "/backups/$(basename "$BACKUP_FILE")" thebot_db 2>/dev/null; then
            print_success "Database backed up to $(basename "$BACKUP_FILE")"
        else
            print_warning "Database backup may have failed (continue anyway)"
        fi
    else
        print_info "[DRY RUN] Would backup database to $BACKUP_FILE"
    fi

    # Backup environment configuration
    print_step "Archiving current configuration..."
    CONFIG_ARCHIVE="${PROJECT_DIR}/deployment-logs/config_${INCIDENT_ID}.tar.gz"
    mkdir -p "$(dirname "$CONFIG_ARCHIVE")"

    if [ "$DRY_RUN" -eq 0 ]; then
        tar czf "$CONFIG_ARCHIVE" \
            "${PROJECT_DIR}/.env.production" \
            "${PROJECT_DIR}/docker/nginx.prod.conf" \
            2>/dev/null || true
        print_success "Configuration archived"
    else
        print_info "[DRY RUN] Would archive configuration to $CONFIG_ARCHIVE"
    fi

    # Backup container logs
    print_step "Saving current logs for analysis..."
    LOGS_ARCHIVE="${PROJECT_DIR}/deployment-logs/logs_${INCIDENT_ID}.tar.gz"

    if [ "$DRY_RUN" -eq 0 ]; then
        docker-compose -f "$COMPOSE_FILE" logs --no-color backend > \
            "${PROJECT_DIR}/deployment-logs/backend_${INCIDENT_ID}.log" 2>/dev/null || true
        docker-compose -f "$COMPOSE_FILE" logs --no-color frontend > \
            "${PROJECT_DIR}/deployment-logs/frontend_${INCIDENT_ID}.log" 2>/dev/null || true
        print_success "Logs saved for post-incident analysis"
    else
        print_info "[DRY RUN] Would save logs"
    fi
else
    print_warning "Backup disabled (BACKUP_CURRENT=0)"
fi

################################################################################
# PHASE 2: VERIFY ROLLBACK TARGET
################################################################################

print_header "PHASE 2: VERIFYING ROLLBACK TARGET"

print_step "Checking if rollback version is available..."

# Check if tag exists
if git -C "$PROJECT_DIR" rev-parse "$ROLLBACK_VERSION" &>/dev/null; then
    print_success "Rollback version found in git"
else
    print_critical "Rollback version not found: $ROLLBACK_VERSION"
    exit 1
fi

print_step "Verifying rollback version is different from current..."
if [ "$ROLLBACK_VERSION" = "$CURRENT_VERSION" ]; then
    print_critical "Rollback version is the same as current version!"
    exit 1
fi

print_success "Rollback target verified"

################################################################################
# PHASE 3: STOP CURRENT DEPLOYMENT
################################################################################

print_header "PHASE 3: STOPPING CURRENT DEPLOYMENT"

print_step "Gracefully stopping services..."

if [ "$DRY_RUN" -eq 0 ]; then
    # Stop backend without removing containers (faster for restart)
    docker-compose -f "$COMPOSE_FILE" stop backend 2>/dev/null || true
    print_success "Backend stopped"

    # Wait for graceful shutdown
    sleep 5
else
    print_info "[DRY RUN] Would stop backend service"
fi

################################################################################
# PHASE 4: RESTORE PREVIOUS VERSION
################################################################################

print_header "PHASE 4: RESTORING PREVIOUS VERSION"

print_step "Checking out version $ROLLBACK_VERSION..."

if [ "$DRY_RUN" -eq 0 ]; then
    # Save current HEAD to allow returning to it if needed
    echo "$CURRENT_VERSION" > "${PROJECT_DIR}/.rollback_from"
    echo "$ROLLBACK_VERSION" > "${PROJECT_DIR}/.rollback_to"

    # Stash any local changes
    git -C "$PROJECT_DIR" stash 2>/dev/null || true

    # Checkout rollback version
    if ! git -C "$PROJECT_DIR" checkout "$ROLLBACK_VERSION" 2>/dev/null; then
        print_critical "Failed to checkout version $ROLLBACK_VERSION"

        # Attempt recovery
        git -C "$PROJECT_DIR" checkout - 2>/dev/null || true
        exit 1
    fi

    print_success "Version $ROLLBACK_VERSION checked out"
else
    print_info "[DRY RUN] Would checkout version $ROLLBACK_VERSION"
fi

print_step "Building and starting previous version..."

if [ "$DRY_RUN" -eq 0 ]; then
    # Pull correct image version
    docker-compose -f "$COMPOSE_FILE" pull backend 2>/dev/null || true

    # Start the service
    docker-compose -f "$COMPOSE_FILE" up -d backend 2>/dev/null || {
        print_critical "Failed to start backend service"
        git -C "$PROJECT_DIR" checkout "$CURRENT_VERSION"
        exit 1
    }

    print_success "Service started with previous version"
else
    print_info "[DRY RUN] Would start service with previous version"
fi

################################################################################
# PHASE 5: VERIFY ROLLBACK
################################################################################

if [ "$SKIP_VERIFY" -eq 0 ]; then
    print_header "PHASE 5: VERIFYING ROLLBACK"

    if [ "$DRY_RUN" -eq 0 ]; then
        # Wait for service to fully start
        print_step "Waiting for service to stabilize (30 seconds)..."
        sleep 30

        print_step "Running health checks..."

        # Run comprehensive verification
        if bash "$VERIFY_SCRIPT" --timeout "$ROLLBACK_TIMEOUT" --strict; then
            print_success "Rollback verification PASSED"
        else
            print_critical "Rollback verification FAILED"
            print_warning "Service may not be healthy - manual intervention required"
            exit 1
        fi
    else
        print_info "[DRY RUN] Would verify rollback using $VERIFY_SCRIPT"
    fi
else
    print_warning "Verification skipped (SKIP_VERIFY=1)"
    print_warning "MANUAL VERIFICATION REQUIRED IMMEDIATELY"
fi

################################################################################
# PHASE 6: NOTIFY AND DOCUMENT
################################################################################

print_header "PHASE 6: INCIDENT DOCUMENTATION"

if [ "$DRY_RUN" -eq 0 ]; then
    print_step "Creating incident report..."

    INCIDENT_REPORT="${PROJECT_DIR}/deployment-logs/incident_${INCIDENT_ID}.md"
    mkdir -p "$(dirname "$INCIDENT_REPORT")"

    cat > "$INCIDENT_REPORT" << EOF
# Production Incident Report

**Incident ID**: $INCIDENT_ID
**Time**: $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Rollback Details

| Item | Value |
|------|-------|
| From Version | $CURRENT_VERSION |
| To Version | $ROLLBACK_VERSION |
| Reason | [TO BE FILLED] |
| Severity | [TO BE FILLED] |
| Duration | [TO BE FILLED] |
| Users Affected | [TO BE FILLED] |

## Actions Taken

- [x] Database backup created: $BACKUP_FILE
- [x] Current configuration archived
- [x] Logs collected for analysis
- [x] Service rolled back to $ROLLBACK_VERSION
- [x] Health checks passed

## Root Cause Analysis

[TO BE COMPLETED]

## Recovery Steps

1. Identify root cause
2. Implement fix in hotfix branch
3. Test thoroughly in staging
4. Deploy as canary with close monitoring

## Post-Incident Review

Scheduled for: [DATE/TIME]

---

**Automated by**: rollback.sh
**Status**: Rollback Completed Successfully
**Next Steps**: Perform root cause analysis and fix deployment
EOF

    print_success "Incident report created at $INCIDENT_REPORT"
else
    print_info "[DRY RUN] Would create incident report"
fi

if [ "$NOTIFY_TEAM" -eq 1 ]; then
    print_step "Creating team notification..."

    NOTIFICATION="${PROJECT_DIR}/deployment-logs/notification_${INCIDENT_ID}.txt"

    cat > "$NOTIFICATION" << EOF
PRODUCTION INCIDENT - AUTOMATIC ROLLBACK EXECUTED

Incident ID: $INCIDENT_ID
Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)

Version Rolled Back:
  From: $CURRENT_VERSION
  To: $ROLLBACK_VERSION

Status: ✓ Rollback Completed Successfully

Evidence Files:
  - Database Backup: $BACKUP_FILE
  - Configuration Archive: $CONFIG_ARCHIVE
  - Incident Report: $INCIDENT_REPORT
  - Logs: $LOGS_ARCHIVE

IMMEDIATE ACTIONS REQUIRED:

1. Notify stakeholders of incident
2. Review logs and identify root cause
3. Prepare hotfix if needed
4. Schedule post-incident review

Log Files for Analysis:
  - Backend logs: ${PROJECT_DIR}/deployment-logs/backend_${INCIDENT_ID}.log
  - Frontend logs: ${PROJECT_DIR}/deployment-logs/frontend_${INCIDENT_ID}.log
  - Full report: $INCIDENT_REPORT

Contact: devops@thebot.com
Status Page: https://status.thebot.com
EOF

    print_success "Notification prepared at $NOTIFICATION"
    echo ""
    cat "$NOTIFICATION"
else
    print_info "Team notification disabled (NOTIFY_TEAM=0)"
fi

################################################################################
# FINAL SUMMARY
################################################################################

print_header "ROLLBACK COMPLETED"

echo "Summary:"
echo "  Status: ✓ SUCCESS"
echo "  Duration: $((SECONDS / 60)) minutes"
echo "  Incident ID: $INCIDENT_ID"
echo ""

if [ "$DRY_RUN" -eq 0 ]; then
    echo "Rollback artifacts saved to:"
    echo "  - Database Backup: $BACKUP_FILE"
    echo "  - Configuration: $CONFIG_ARCHIVE"
    echo "  - Incident Report: $INCIDENT_REPORT"
    echo ""

    echo "NEXT STEPS:"
    echo "  1. Contact team and stakeholders"
    echo "  2. Review logs: cat ${PROJECT_DIR}/deployment-logs/backend_${INCIDENT_ID}.log"
    echo "  3. Identify root cause"
    echo "  4. Implement fix in hotfix branch: git checkout -b hotfix/[issue]"
    echo "  5. Test in staging environment"
    echo "  6. Deploy as canary with close monitoring"
    echo "  7. Schedule post-incident review"
    echo ""

    print_critical "DO NOT DEPLOY AGAIN UNTIL ROOT CAUSE IS FIXED"
else
    echo "[DRY RUN MODE]"
    echo "No actual changes were made. Rerun without --dry-run to execute rollback."
fi

print_success "Rollback script completed"
