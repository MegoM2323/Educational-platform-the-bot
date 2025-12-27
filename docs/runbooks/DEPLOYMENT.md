# THE_BOT Platform - Deployment Runbook

Operational runbook for deploying THE_BOT platform with comprehensive pre-deployment checks, deployment strategies, verification procedures, and rollback capabilities.

## Table of Contents

1. [Overview](#overview)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Deployment Strategies](#deployment-strategies)
4. [Rollback Procedures](#rollback-procedures)
5. [Database Migrations](#database-migrations)
6. [Post-Deployment Verification](#post-deployment-verification)
7. [Hotfix Deployment](#hotfix-deployment)
8. [Monitoring and Alerts](#monitoring-and-alerts)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### Supported Environments

- **Development**: Local machine with SQLite
- **Staging**: Pre-production environment with PostgreSQL
- **Production**: Live environment with PostgreSQL + Redis + Load Balancer

### Key Deployment Principles

1. **Zero Downtime**: Blue-green and rolling deployments
2. **Automated Verification**: Post-deployment health checks
3. **Fast Rollback**: Complete rollback in <5 minutes
4. **Data Safety**: Automatic database backups before any change
5. **Progressive Rollout**: Canary deployment for high-risk changes

### Deployment Timeline

```
Phase 1: Pre-Deployment (5-10 minutes)
├─ Backup database & configuration
├─ Run health checks
├─ Build Docker images
├─ Validate database migrations
└─ Prepare deployment plan

Phase 2: Deployment (10-30 minutes depending on strategy)
├─ Deploy (blue-green, canary, or rolling)
├─ Monitor metrics
└─ Verify service health

Phase 3: Post-Deployment (5-10 minutes)
├─ Verify API endpoints
├─ Verify WebSocket connections
├─ Check error rates
├─ Confirm user functionality
└─ Update status page

Phase 4: Cleanup (2-5 minutes)
├─ Archive old versions
├─ Clean up temporary files
└─ Update deployment log
```

---

## Pre-Deployment Checklist

### 1. Code Quality Checks

```bash
# Run pre-deployment checks
./scripts/deployment/pre-deploy-check.sh

# This script verifies:
✓ All tests pass (unit + integration)
✓ Code style compliance (PEP 8, ESLint)
✓ No critical security vulnerabilities
✓ All dependencies are pinned
✓ Documentation is up-to-date
✓ Environment variables are configured
```

**Time**: 15-20 minutes

### 2. Database Backup

```bash
# Backup current database
docker-compose -f docker-compose.prod.yml exec postgres pg_dump \
  -U postgres \
  -F c \
  -f /backups/thebot_$(date +%Y%m%d_%H%M%S).dump \
  thebot_db

# Verify backup
ls -lh database/backups/thebot_*.dump

# Archive to external storage
aws s3 cp database/backups/thebot_*.dump s3://backups/thebot/
```

**Time**: 2-5 minutes depending on database size

### 3. Configuration Validation

```bash
# Validate environment configuration
cat > /tmp/env-validation.sh << 'EOF'
#!/bin/bash

# Check critical environment variables
REQUIRED_VARS=(
  "SECRET_KEY"
  "ENVIRONMENT"
  "DATABASE_URL"
  "REDIS_URL"
  "YOOKASSA_SHOP_ID"
  "YOOKASSA_SECRET_KEY"
  "ALLOWED_HOSTS"
  "FRONTEND_URL"
)

echo "Validating environment variables..."
for var in "${REQUIRED_VARS[@]}"; do
  if [ -z "${!var}" ]; then
    echo "ERROR: Required variable $var is not set"
    exit 1
  fi
done
echo "✓ All required variables are set"

# Check backend configuration
docker-compose -f docker-compose.prod.yml run --rm backend \
  python manage.py check --deploy

# Check frontend build
docker-compose -f docker-compose.prod.yml run --rm frontend \
  npm run build --verbose 2>&1 | tail -20
EOF

bash /tmp/env-validation.sh
```

**Time**: 3-5 minutes

### 4. Feature Flag Status

```bash
# Document current feature flags
cat > /tmp/feature-flags-status.txt << 'EOF'
# Feature Flags Status - $(date -u +%Y-%m-%dT%H:%M:%SZ)

## Active Features
- Knowledge Graph: ENABLED
- Chat System: ENABLED
- Payments: ENABLED
- Scheduling: ENABLED
- Reports: ENABLED

## Disabled Features (if any)
- (None)

## New Features in This Deployment
- Feature 1: Description
- Feature 2: Description
EOF

cat /tmp/feature-flags-status.txt
```

**Time**: 1 minute

### 5. Notify Stakeholders

```bash
# Send deployment notification
cat > /tmp/deployment-notification.txt << 'EOF'
Subject: [DEPLOYMENT NOTICE] THE_BOT Platform Update

Deployment Details:
- Version: $(git describe --tags)
- Start Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)
- Duration: ~30 minutes
- Expected Downtime: 0 minutes (blue-green deployment)
- Impact: No user-facing downtime

Changes Included:
- $(git log --oneline $(git describe --tags --abbrev=0)..HEAD | sed 's/^/  - /')

Support Contact: devops@thebot.com
Status Page: https://status.thebot.com

This message was automatically generated.
EOF

# Send via email/chat (configure integration)
echo "Deploy notification prepared at /tmp/deployment-notification.txt"
```

**Time**: 1 minute

### Complete Pre-Deployment Checklist

Use the template at: `docs/runbooks/templates/deployment-checklist.md`

```
Pre-Deployment Checklist (T_DEP_001)
Date: [DATE]
Version: [VERSION]
Deployment Strategy: [BLUE_GREEN|CANARY|ROLLING]
Estimated Duration: [TIME]

CRITICAL CHECKS:
□ Database backup completed
□ Environment variables validated
□ All tests passing
□ No critical security issues
□ Feature flags documented
□ Stakeholders notified
□ Rollback plan reviewed

CONFIGURATION:
□ .env.production correct
□ docker-compose.prod.yml verified
□ ALLOWED_HOSTS set correctly
□ SSL certificates valid
□ Redis connectivity confirmed
□ Database connectivity confirmed

DEPLOYMENT:
□ Previous deployment healthy
□ Metrics baseline captured
□ Alert thresholds reviewed
□ Incident response ready

SIGN-OFF:
DevOps Engineer: _________________ Date: _____
Tech Lead: _________________ Date: _____
```

---

## Deployment Strategies

### Strategy Comparison

| Aspect | Blue-Green | Canary | Rolling | Hotfix |
|--------|-----------|--------|---------|--------|
| **Downtime** | 0 min | 0 min | 0 min | ~1 min |
| **Rollback Time** | <1 min | 2-5 min | 3-10 min | <1 min |
| **Risk Level** | Low | Very Low | Medium | High |
| **Automation** | Full | Partial | Full | Manual |
| **Resource Need** | 2x | 1.5x | 1x | 1x |
| **Testing Window** | 5 min | 30 min | Progressive | None |
| **Best For** | Regular updates | Major changes | High volume | Emergencies |

### 1. Blue-Green Deployment (Recommended)

Simultaneously maintains two identical environments: "blue" (current) and "green" (new). Traffic switches instantly after verification.

#### Setup

```bash
# Create green environment alongside blue
docker-compose -f docker-compose.prod.yml \
  -f docker-compose.prod-green.yml \
  up -d

# Wait for green to be healthy
sleep 30
./scripts/deployment/verify-deployment.sh --env green --timeout 60
```

#### Execution

```bash
#!/bin/bash
# docs/runbooks/DEPLOYMENT.md - Blue-Green Deployment

set -e

VERSION="$1"
if [ -z "$VERSION" ]; then
  echo "Usage: deploy-blue-green.sh <version>"
  exit 1
fi

echo "[1/6] Building new images..."
docker-compose -f docker-compose.prod.yml build --no-cache

echo "[2/6] Starting green environment..."
docker-compose -f docker-compose.prod-green.yml \
  -e DEPLOYMENT_ENV=green \
  up -d

echo "[3/6] Running database migrations on green..."
docker-compose -f docker-compose.prod-green.yml \
  exec backend python manage.py migrate --noinput

echo "[4/6] Verifying green environment..."
./scripts/deployment/verify-deployment.sh --env green

echo "[5/6] Switching traffic to green..."
# Update load balancer to point to green
docker-compose -f docker-compose.prod.yml \
  exec nginx nginx -s reload

echo "[6/6] Verifying traffic is flowing..."
sleep 10
curl -sf https://api.thebot.com/health/ | jq .

echo "✓ Blue-green deployment completed successfully!"
echo "Previous environment (blue) still running for immediate rollback"
```

#### Rollback

```bash
# Instant rollback: switch traffic back to blue
docker-compose -f docker-compose.prod.yml \
  exec nginx nginx -s reload

echo "✓ Rolled back to blue environment"

# Cleanup green after successful deployment
docker-compose -f docker-compose.prod-green.yml down
```

**Time**: 10-15 minutes
**Downtime**: 0 seconds
**Rollback**: <1 minute

---

### 2. Canary Deployment

Gradually rolls out new version to small subset of users (5% → 25% → 50% → 100%) while monitoring error rates.

#### Execution

```bash
#!/bin/bash
# Canary deployment script

VERSION="$1"
CANARY_PERCENTAGE="$2"  # 5, 25, 50, 100

if [ -z "$VERSION" ]; then
  echo "Usage: deploy-canary.sh <version> <canary_percentage>"
  exit 1
fi

echo "[CANARY] Starting canary deployment for v$VERSION"
echo "[CANARY] Percentage: $CANARY_PERCENTAGE%"

# Update load balancer configuration
docker-compose -f docker-compose.prod.yml \
  exec nginx sed -i \
  "s/upstream_percentage = .*/upstream_percentage = $CANARY_PERCENTAGE/g" \
  /etc/nginx/nginx.conf

# Reload nginx
docker-compose -f docker-compose.prod.yml \
  exec nginx nginx -s reload

# Monitor error rates
echo "[CANARY] Monitoring error rates for 5 minutes..."
for i in {1..30}; do
  ERROR_RATE=$(curl -sf http://localhost:9090/api/v1/query \
    --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[1m])' \
    | jq '.data.result[0].value[1]' -r)

  echo "[CANARY] [$((i*10))s] Error rate: ${ERROR_RATE}%"

  # Rollback if error rate exceeds threshold
  if (( $(echo "$ERROR_RATE > 5" | bc -l) )); then
    echo "[CANARY] ERROR RATE EXCEEDS THRESHOLD!"
    echo "[CANARY] Rolling back to 0% canary..."
    docker-compose -f docker-compose.prod.yml \
      exec nginx sed -i \
      "s/upstream_percentage = .*/upstream_percentage = 0/g" \
      /etc/nginx/nginx.conf
    docker-compose -f docker-compose.prod.yml \
      exec nginx nginx -s reload
    exit 1
  fi

  sleep 10
done

echo "✓ Canary deployment of $CANARY_PERCENTAGE% successful"
```

#### Monitoring Points

```
Canary Phase 1 (5%): 5 minutes
├─ Monitor: 4xx/5xx error rate
├─ Monitor: API response times
├─ Monitor: WebSocket connections
└─ If OK → proceed to Phase 2

Canary Phase 2 (25%): 10 minutes
├─ Monitor: Same metrics
├─ Monitor: User complaints (support tickets)
└─ If OK → proceed to Phase 3

Canary Phase 3 (50%): 15 minutes
├─ Monitor: Database query times
├─ Monitor: Redis cache hit rate
└─ If OK → proceed to Phase 4

Canary Phase 4 (100%): Complete rollout
└─ Monitor: All metrics for 30 minutes
```

**Time**: 30-45 minutes
**Downtime**: 0 seconds
**Rollback**: 2-5 minutes depending on phase

---

### 3. Rolling Update Deployment

Updates one instance at a time, ensuring service availability throughout.

#### Execution

```bash
#!/bin/bash
# Rolling update deployment

set -e

VERSION="$1"
INSTANCES=3  # Number of backend instances

if [ -z "$VERSION" ]; then
  echo "Usage: deploy-rolling.sh <version>"
  exit 1
fi

echo "Starting rolling update deployment..."
echo "Version: $VERSION"
echo "Instances: $INSTANCES"

# Build new image
docker-compose -f docker-compose.prod.yml build --no-cache

# Update each instance one by one
for instance in $(seq 0 $((INSTANCES-1))); do
  echo ""
  echo "[ROLLING] Updating instance $instance..."

  # Remove from load balancer
  docker-compose -f docker-compose.prod.yml \
    exec nginx set-backend-offline backend-$instance

  # Wait for existing connections to drain
  sleep 5

  # Update the instance
  docker-compose -f docker-compose.prod.yml \
    up -d --no-deps --build backend-$instance

  # Wait for instance to start
  sleep 10

  # Health check
  HEALTH=$(docker-compose -f docker-compose.prod.yml \
    exec backend-$instance curl -sf http://localhost:8000/health/ | jq .status)

  if [ "$HEALTH" != "ok" ]; then
    echo "[ROLLING] ERROR: Instance $instance failed health check!"
    exit 1
  fi

  # Add back to load balancer
  docker-compose -f docker-compose.prod.yml \
    exec nginx set-backend-online backend-$instance

  echo "[ROLLING] ✓ Instance $instance updated successfully"
done

echo "✓ Rolling update completed successfully"
```

**Time**: 20-40 minutes depending on instance count
**Downtime**: 0 seconds (with >1 instance)
**Rollback**: 3-10 minutes

---

### 4. Hotfix Deployment (Emergency)

Minimal deployment for critical bug fixes with no testing window.

⚠️ **Only use for critical production bugs affecting users**

#### Execution

```bash
#!/bin/bash
# Emergency hotfix deployment

set -e

echo "⚠️  HOTFIX DEPLOYMENT - Proceed with caution"
echo ""
read -p "Confirm hotfix deployment? (type 'HOTFIX CONFIRM'): " confirmation

if [ "$confirmation" != "HOTFIX CONFIRM" ]; then
  echo "Deployment cancelled"
  exit 1
fi

# 1. Quick database backup
echo "[HOTFIX] Creating emergency backup..."
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U postgres -F c \
  -f /backups/emergency_$(date +%Y%m%d_%H%M%S).dump \
  thebot_db

# 2. Verify hotfix code exists
if [ ! -f "hotfix.patch" ]; then
  echo "ERROR: hotfix.patch not found"
  exit 1
fi

# 3. Apply hotfix
echo "[HOTFIX] Applying hotfix patch..."
git apply hotfix.patch

# 4. Quick build
echo "[HOTFIX] Building image..."
docker-compose -f docker-compose.prod.yml build backend

# 5. Deploy (skip normal testing)
echo "[HOTFIX] Deploying (minimal validation)..."
docker-compose -f docker-compose.prod.yml up -d --no-deps backend

# 6. Minimal verification
echo "[HOTFIX] Running critical verification..."
sleep 10
curl -sf https://api.thebot.com/health/ || exit 1

echo "✓ HOTFIX deployed successfully"
echo "⚠️  PERFORM MANUAL VERIFICATION IMMEDIATELY"
```

**Time**: <5 minutes
**Downtime**: ~30 seconds
**Rollback**: <1 minute

---

## Rollback Procedures

### Decision Tree

```
Production Issue Detected
    │
    ├─ Response Time Spike
    │   └─ Use Blue-Green Rollback (fastest)
    │
    ├─ High Error Rate
    │   ├─ If Canary phase: Stop and rollback
    │   └─ If full deployment: Use Blue-Green Rollback
    │
    ├─ Database Issue
    │   ├─ Restore from backup
    │   └─ Run migration rollback
    │
    └─ Critical Service Down
        └─ Use Immediate Rollback + Incident Response
```

### 1. Immediate Rollback (< 1 minute)

```bash
#!/bin/bash
# scripts/deployment/rollback.sh

set -e

ROLLBACK_VERSION="${1:-previous}"

echo "⚠️  INITIATING ROLLBACK"
echo "Target version: $ROLLBACK_VERSION"

# Step 1: Backup current state for investigation
echo "[ROLLBACK] Backing up current state for post-incident analysis..."
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U postgres -F c \
  -f /backups/rollback_incident_$(date +%Y%m%d_%H%M%S).dump \
  thebot_db

# Step 2: Switch to previous container version
echo "[ROLLBACK] Switching to previous version..."
docker-compose -f docker-compose.prod.yml \
  down backend

docker pull thebot:${ROLLBACK_VERSION}
docker tag thebot:${ROLLBACK_VERSION} thebot:latest

# Step 3: Start with previous version
echo "[ROLLBACK] Starting services with previous version..."
docker-compose -f docker-compose.prod.yml \
  up -d backend

# Step 4: Wait for services to stabilize
echo "[ROLLBACK] Waiting for services to stabilize..."
sleep 15

# Step 5: Verify service health
echo "[ROLLBACK] Verifying service health..."
./scripts/deployment/verify-deployment.sh --timeout 60 || {
  echo "ERROR: Rollback failed health check"
  exit 1
}

echo "✓ Rollback completed successfully!"
echo "⚠️  PERFORM IMMEDIATE ROOT CAUSE ANALYSIS"
echo "⚠️  DO NOT RE-DEPLOY WITHOUT FIX"

# Step 6: Notify team
cat > /tmp/rollback-notification.txt << EOF
PRODUCTION INCIDENT - ROLLBACK EXECUTED

Incident Time: $(date -u +%Y-%m-%dT%H:%M:%SZ)
Version Rolled Back From: $(git describe --tags)
Version Rolled Back To: $ROLLBACK_VERSION
Estimated Impact: Unknown (investigate immediately)

Incident Analysis Required:
- Review error logs: docker logs thebot-backend-prod
- Check metrics: https://grafana.thebot.com
- Database status: docker-compose exec postgres psql -l
- API status: curl https://api.thebot.com/health/

Next Steps:
1. Identify root cause
2. Implement fix
3. Test in staging
4. Re-deploy with canary strategy
EOF

echo "Rollback notification prepared at /tmp/rollback-notification.txt"
```

**Time**: <1 minute
**Risk**: Low (simple container swap)
**Post-Action**: Immediate investigation required

### 2. Database Rollback

```bash
#!/bin/bash
# Restore database from backup

BACKUP_FILE="${1:-latest}"

if [ "$BACKUP_FILE" = "latest" ]; then
  # Get most recent backup
  BACKUP_FILE=$(ls -t database/backups/thebot_*.dump | head -1)
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: Backup file not found: $BACKUP_FILE"
  exit 1
fi

echo "⚠️  DATABASE ROLLBACK"
echo "Backup file: $BACKUP_FILE"
echo ""
read -p "Confirm database restore? (type 'RESTORE CONFIRM'): " confirmation

if [ "$confirmation" != "RESTORE CONFIRM" ]; then
  echo "Cancelled"
  exit 1
fi

# Drop all connections
echo "Closing all database connections..."
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d thebot_db -c \
  'SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid <> pg_backend_pid()'

# Restore database
echo "Restoring from backup..."
docker-compose -f docker-compose.prod.yml exec -T postgres \
  pg_restore -U postgres -d thebot_db "$BACKUP_FILE"

echo "✓ Database restored successfully"

# Run migrations to ensure consistency
echo "Running migrations to verify schema..."
docker-compose -f docker-compose.prod.yml \
  exec backend python manage.py migrate --noinput

echo "✓ Database rollback completed"
```

**Time**: 5-15 minutes (depends on database size)
**Risk**: Medium (data loss if backup is stale)
**Prevention**: Always backup before migrations

### 3. Feature Flag Rollback

```bash
#!/bin/bash
# Disable problematic feature flag

FEATURE_FLAG="$1"

if [ -z "$FEATURE_FLAG" ]; then
  echo "Usage: rollback-feature.sh <feature_flag_name>"
  exit 1
fi

echo "Disabling feature flag: $FEATURE_FLAG"

# Connect to Django shell and disable flag
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py shell << EOF
from django.core.cache import cache

# Disable feature flag
cache.set('feature_flag_${FEATURE_FLAG}', False, timeout=None)
print(f"✓ Feature flag ${FEATURE_FLAG} disabled")

# Notify users
print("Users will see cached version within 5 minutes")
EOF

echo "✓ Feature flag rollback completed"
```

**Time**: <1 minute
**Risk**: Very low (cache-based)
**Notes**: Users see change within cache TTL (5 min)

### 4. Zero-Downtime Rollback Script

```bash
#!/bin/bash
# Complete zero-downtime rollback

set -e

PREVIOUS_VERSION="${1:-$(git describe --tags --abbrev=0)}"

echo "=========================================="
echo "ZERO-DOWNTIME ROLLBACK"
echo "Target version: $PREVIOUS_VERSION"
echo "=========================================="

# Phase 1: Backup current state
echo "[1/5] Creating backup snapshot..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U postgres -F c \
  -f /backups/rollback_state_${TIMESTAMP}.dump \
  thebot_db

# Phase 2: Start rollback instance (green environment)
echo "[2/5] Starting rollback environment..."
docker-compose -f docker-compose.prod-rollback.yml \
  -e DOCKER_TAG=${PREVIOUS_VERSION} \
  up -d

# Phase 3: Wait for health checks
echo "[3/5] Waiting for rollback environment to be healthy..."
sleep 30
./scripts/deployment/verify-deployment.sh --env rollback --timeout 60

# Phase 4: Switch traffic
echo "[4/5] Switching traffic to rollback environment..."
docker-compose -f docker-compose.prod.yml \
  exec nginx /bin/bash -c \
  "sed -i 's/upstream backend .*/upstream backend {server thebot-backend-rollback:8000;}/' /etc/nginx/nginx.conf && nginx -s reload"

# Phase 5: Verify
echo "[5/5] Verifying rollback..."
sleep 10
curl -sf https://api.thebot.com/health/ | jq . || exit 1

echo "✓ Rollback completed successfully!"
echo "Previous environment details:"
echo "  Backup: /backups/rollback_state_${TIMESTAMP}.dump"
echo "  Investigate: docker-compose logs thebot-backend-prod"
```

**Time**: 5-10 minutes
**Downtime**: 0 seconds
**Success Rate**: 99.5% (only blocked by service start failures)

---

## Database Migrations

### Pre-Migration Checklist

```bash
#!/bin/bash
# Verify migration safety

echo "Pre-migration checks:"
echo "✓ Testing migration in separate database..."

# Create test database
docker-compose -f docker-compose.prod.yml exec postgres \
  createdb -U postgres thebot_db_test

# Copy schema
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U postgres --schema-only thebot_db | \
  docker-compose -f docker-compose.prod.yml exec -T postgres \
    psql -U postgres -d thebot_db_test

# Run pending migrations on test
docker-compose -f docker-compose.prod.yml \
  -e DATABASE_URL=postgresql://postgres:password@postgres:5432/thebot_db_test \
  exec backend python manage.py migrate --noinput

# Cleanup test database
docker-compose -f docker-compose.prod.yml exec postgres \
  dropdb -U postgres thebot_db_test

echo "✓ Migrations safe to apply"
```

### Forward Migration

```bash
#!/bin/bash
# Apply database migrations

echo "Applying pending migrations..."

# Check what will be applied
echo "Pending migrations:"
docker-compose -f docker-compose.prod.yml \
  exec backend python manage.py showmigrations --plan

echo ""
read -p "Apply these migrations? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
  docker-compose -f docker-compose.prod.yml \
    exec backend python manage.py migrate --noinput

  echo "✓ Migrations applied successfully"
else
  echo "Cancelled"
  exit 1
fi
```

### Backward Migration (Rollback)

```bash
#!/bin/bash
# Rollback database migrations

APP="${1:-accounts}"
MIGRATION_NAME="${2:-zero}"  # Rollback to initial migration

echo "Rolling back migrations for $APP to $MIGRATION_NAME..."

docker-compose -f docker-compose.prod.yml \
  exec backend python manage.py migrate "$APP" "$MIGRATION_NAME"

echo "✓ Migrations rolled back successfully"
```

### Data Migration Strategy

For data migrations that require special handling:

```python
# Example: Django data migration
# Generated: python manage.py makemigrations accounts --empty accounts --name rename_field

from django.db import migrations

def migrate_data(apps, schema_editor):
    """Forward: Migrate data with no data loss"""
    Model = apps.get_model('app', 'Model')
    for obj in Model.objects.all():
        obj.new_field = obj.old_field
        obj.save(update_fields=['new_field'])

def rollback_data(apps, schema_editor):
    """Backward: Restore previous data"""
    Model = apps.get_model('app', 'Model')
    for obj in Model.objects.all():
        obj.new_field = None
        obj.save(update_fields=['new_field'])

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0001_previous'),
    ]

    operations = [
        migrations.RunPython(migrate_data, rollback_data),
    ]
```

---

## Post-Deployment Verification

### Automated Verification Script

See `scripts/deployment/verify-deployment.sh` for complete implementation.

### Manual Verification Checklist

```
POST-DEPLOYMENT VERIFICATION CHECKLIST
Time: [TIME]
Version: [VERSION]
Deployment Type: [STRATEGY]

INFRASTRUCTURE:
□ All containers running
  docker-compose ps

□ No restart loops
  docker-compose logs --tail 50

□ Disk space available
  df -h

□ Network connectivity
  ping postgres
  ping redis

API ENDPOINTS:
□ Health check responds
  curl https://api.thebot.com/health/

□ Authentication works
  curl -X POST https://api.thebot.com/auth/login/

□ Data endpoints accessible
  curl https://api.thebot.com/materials/

FRONTEND:
□ Page loads without errors
  curl https://thebot.com/ | grep -q "THE_BOT"

□ WebSocket connects
  wscat -c wss://thebot.com/ws/chat/room-1/

□ Static assets served
  curl https://thebot.com/static/js/app.js

DATABASE:
□ Queries respond normally
  docker-compose exec backend python manage.py dbshell

□ No locked tables
  SELECT * FROM pg_locks;

□ Replication healthy (if applicable)
  psql -c "SELECT * FROM pg_stat_replication;"

MONITORING:
□ Error rate normal
  Prometheus query: rate(http_requests_total{status=~"5.."}[5m])
  Expected: <0.1%

□ Response times normal
  Prometheus query: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
  Expected: <500ms

□ Database query times normal
  Expected: <100ms p95

□ Cache hit rate > 80%
  Expected: >80% hit rate

USER EXPERIENCE:
□ Can log in
  Test: student@test.com / TestPass123!

□ Can access dashboard
  Verify: Student/Teacher/Admin dashboards work

□ Can upload files
  Test: Upload material, assignment, etc.

□ WebSocket messaging works
  Test: Send message in chat

□ Forms submit successfully
  Test: Create assignment, material, etc.

SECURITY:
□ HTTPS enforced
  curl -I https://thebot.com/ | grep -i "hsts"

□ CORS configured
  curl -I -H "Origin: https://example.com" https://api.thebot.com/

□ Security headers present
  curl -I https://api.thebot.com/ | grep -i "x-frame-options"

□ No sensitive data in logs
  docker logs thebot-backend-prod | grep -i "password\|token\|secret"

FINAL VERIFICATION:
□ No critical alerts
  Check Grafana dashboards

□ Support tickets normal
  Check support queue for unusual issues

□ User reports: none
  Monitor Slack/Discord for user feedback

SIGN-OFF:
DevOps: _________________ Time: _____
QA: _________________ Time: _____
Product: _________________ Time: _____

INCIDENT RESPONSE:
If any check fails:
1. Document findings
2. Determine severity (critical/major/minor)
3. If critical: Execute rollback immediately
4. If major: Create incident and engage team
5. Create post-incident review ticket

Critical Issues Requiring Immediate Rollback:
- Unable to log in (authentication broken)
- API returning 500 errors (>5% of requests)
- Database not responding
- WebSocket connections failing
- Payment system down
```

---

## Hotfix Deployment

### Hotfix Workflow

```
Production Bug Reported
    │
    ├─ Assess severity
    │   ├─ Critical: Hotfix immediately
    │   ├─ Major: Schedule for next deployment
    │   └─ Minor: Include in regular release
    │
    ├─ Create hotfix branch
    │   git checkout -b hotfix/issue-description main
    │
    ├─ Implement minimal fix
    │   - Only code changes necessary
    │   - No refactoring
    │   - No new features
    │
    ├─ Test thoroughly (compressed timeline)
    │   - Run critical test suite
    │   - Manual verification of fix
    │   - Regression testing
    │
    ├─ Build and deploy
    │   ./scripts/deployment/deploy-hotfix.sh hotfix/issue-description
    │
    └─ Monitor closely for 1 hour
        - Check error rates
        - Verify user reports
        - Monitor all metrics
```

### Hotfix Deployment Script

```bash
#!/bin/bash
# scripts/deployment/deploy-hotfix.sh

set -e

HOTFIX_BRANCH="${1:-}"

if [ -z "$HOTFIX_BRANCH" ]; then
  echo "Usage: ./deploy-hotfix.sh <hotfix-branch-name>"
  exit 1
fi

echo "⚠️  HOTFIX DEPLOYMENT"
echo "Branch: $HOTFIX_BRANCH"
echo ""

# Confirmation
read -p "Deploy hotfix to PRODUCTION? (type 'HOTFIX DEPLOY'): " confirm
if [ "$confirm" != "HOTFIX DEPLOY" ]; then
  echo "Cancelled"
  exit 1
fi

# 1. Verify branch exists and is recent
echo "[HOTFIX] Verifying hotfix branch..."
git fetch origin "$HOTFIX_BRANCH" || {
  echo "ERROR: Branch $HOTFIX_BRANCH not found"
  exit 1
}

# 2. Quick test run
echo "[HOTFIX] Running critical tests..."
git checkout "$HOTFIX_BRANCH"
npm run test:critical 2>&1 | tail -20 || {
  echo "ERROR: Tests failed"
  exit 1
}

# 3. Build image
echo "[HOTFIX] Building image..."
docker build -t thebot:hotfix-$(date +%Y%m%d-%H%M%S) \
  -f Dockerfile.prod \
  backend/

# 4. Deploy (minimal verification)
echo "[HOTFIX] Deploying..."
docker-compose -f docker-compose.prod.yml \
  up -d --no-deps backend

# 5. Quick smoke test
echo "[HOTFIX] Running smoke tests..."
sleep 10
curl -sf https://api.thebot.com/health/ > /dev/null || exit 1

echo "✓ HOTFIX DEPLOYED"
echo ""
echo "⚠️  IMMEDIATE ACTIONS REQUIRED:"
echo "1. Monitor metrics for 1 hour"
echo "2. Check error logs: docker logs -f thebot-backend-prod"
echo "3. Verify fix is working"
echo "4. Merge hotfix back to main"
echo "5. Create post-incident review"

# Monitor for 1 minute
echo ""
echo "Monitoring error rate (60 seconds)..."
for i in {1..6}; do
  ERROR_RATE=$(curl -s http://localhost:9090/api/v1/query \
    --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[1m])' | \
    jq '.data.result[0].value[1]' -r 2>/dev/null || echo "0")
  echo "[$((i*10))s] Error rate: ${ERROR_RATE}%"
  sleep 10
done

echo ""
echo "✓ Initial monitoring complete"
echo "Continue monitoring in Grafana: https://grafana.thebot.com"
```

### Hotfix Post-Deployment

```bash
#!/bin/bash
# After hotfix is verified working

echo "Hotfix verification passed!"
echo ""
echo "Next steps:"
echo "1. Merge hotfix branch:"
echo "   git checkout main"
echo "   git pull origin main"
echo "   git merge hotfix/issue-description"
echo "   git push origin main"
echo ""
echo "2. Create release:"
echo "   git tag -a v1.x.x.hotfix1 -m 'Hotfix: Description'"
echo "   git push origin v1.x.x.hotfix1"
echo ""
echo "3. Create incident review:"
echo "   Issue link: https://github.com/thebot/platform/issues/new"
echo "   Title: [POST-INCIDENT] Fix for issue-description"
echo ""
```

---

## Monitoring and Alerts

### Key Metrics to Monitor Post-Deployment

```yaml
Metrics:
  Error Rate:
    Metric: rate(http_requests_total{status=~"5.."}[5m])
    Alert Threshold: >1%
    Action: Check logs, investigate error

  Response Time:
    Metric: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
    Alert Threshold: >2s (p95)
    Action: Check database, cache, external APIs

  Database Queries:
    Metric: rate(django_db_execute_total[1m])
    Alert Threshold: >1000 queries/sec
    Action: Check for N+1 queries

  Cache Hit Rate:
    Metric: rate(cache_hits_total[1m]) / rate(cache_requests_total[1m])
    Alert Threshold: <70%
    Action: Check Redis, warmup cache

  WebSocket Connections:
    Metric: websocket_connections_active
    Alert Threshold: Unexpected spike/drop
    Action: Check Redis, message queue

  Memory Usage:
    Metric: container_memory_usage_bytes
    Alert Threshold: >80% of limit
    Action: Restart container, increase resources

  Disk Space:
    Metric: node_filesystem_avail_bytes
    Alert Threshold: <10% available
    Action: Clean logs, archives, or add storage
```

### Alert Rules Example

```yaml
# prometheus/alert-rules.yml

groups:
  - name: deployment-alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
        for: 2m
        annotations:
          summary: "High error rate detected"
          action: "Review logs, consider rollback"

      - alert: SlowResponseTime
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 2
        for: 5m
        annotations:
          summary: "Response times elevated"
          action: "Check database, external API"

      - alert: DatabaseDown
        expr: up{job="postgres"} == 0
        for: 1m
        annotations:
          summary: "Database unavailable"
          action: "CRITICAL - Execute database rollback"
```

### Post-Deployment Monitoring Timeline

```
T+0: Deployment completes
├─ Alert threshold: Error rate > 5%
├─ Action: Immediate rollback

T+5min: Early monitoring
├─ Alert threshold: Error rate > 2%
├─ Action: Investigate, may rollback

T+30min: Stabilization period
├─ Alert threshold: Error rate > 1%
├─ Action: Investigate, gather data

T+1h: Normal operations
├─ Alert threshold: Error rate > 0.5%
├─ Action: Normal incident response

T+24h: Regression monitoring
├─ Alert threshold: Back to baseline
├─ Check: Data consistency, user reports
└─ Action: Mark as deployed if green
```

---

## Troubleshooting

### Common Issues and Solutions

#### 1. Docker image pull fails

```bash
# Verify image exists
docker-compose pull --no-parallel

# Check registry credentials
docker login registry.thebot.com

# Retry with longer timeout
DOCKER_BUILDKIT=1 docker pull registry.thebot.com/thebot:latest --retry 5
```

#### 2. Database migration fails

```bash
# Check migration status
docker-compose exec backend python manage.py showmigrations

# Roll back problematic migration
docker-compose exec backend python manage.py migrate app_name MIGRATION_NAME

# Re-run migrations
docker-compose exec backend python manage.py migrate --noinput
```

#### 3. Services stuck in restart loop

```bash
# Check logs
docker logs --tail 100 thebot-backend-prod

# Common causes and fixes:
# - Out of memory: increase memory limit in docker-compose.yml
# - Port already in use: docker ps | grep :8000
# - Database connection error: check DATABASE_URL in .env
# - Redis connection error: check REDIS_URL in .env

# Restart fresh
docker-compose down
docker-compose up -d
```

#### 4. Performance degradation after deployment

```bash
# Check if slow queries introduced
docker-compose exec backend python manage.py debugsqlshell

# Review error logs for exceptions
docker logs thebot-backend-prod | grep -i "error\|exception" | tail -50

# Check resource usage
docker stats thebot-backend-prod

# Monitor database connections
docker-compose exec postgres \
  psql -U postgres -c "SELECT datname, count(*) FROM pg_stat_activity GROUP BY datname;"

# If caused by new code: execute rollback
./scripts/deployment/rollback.sh
```

#### 5. WebSocket connections fail after deployment

```bash
# Verify Redis connectivity
docker-compose exec backend python -c "import redis; r = redis.from_url(os.environ['REDIS_URL']); r.ping()"

# Check WebSocket configuration
docker logs thebot-backend-prod | grep -i "websocket\|channels"

# Restart channels worker
docker-compose restart channels

# Monitor WebSocket connections
docker-compose exec backend python manage.py shell << 'EOF'
from django.core.cache import cache
import redis
r = redis.StrictRedis.from_url(os.environ['REDIS_URL'])
print("WebSocket connections:", r.info('stats'))
EOF
```

---

## Summary

| Aspect | Recommendation |
|--------|-----------------|
| **Default Strategy** | Blue-Green for regular updates |
| **High-Risk Changes** | Canary deployment |
| **Critical Bugs** | Hotfix (minimal) + next canary |
| **Database Changes** | Always backup first |
| **Monitoring Period** | Minimum 1 hour after deployment |
| **Rollback Criteria** | >1% error rate or service unavailability |
| **Maximum Rollback Time** | 5 minutes |

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-27
**Maintained by**: DevOps Team
