# Deployment Strategies Guide

Detailed guide for implementing different deployment strategies with step-by-step examples.

## Table of Contents

1. [Blue-Green Deployment](#blue-green-deployment)
2. [Canary Deployment](#canary-deployment)
3. [Rolling Update](#rolling-update)
4. [Feature Flag Deployment](#feature-flag-deployment)
5. [Database Migration Strategies](#database-migration-strategies)
6. [Strategy Comparison](#strategy-comparison)

---

## Blue-Green Deployment

### Overview

Maintains two identical production environments: **Blue** (current) and **Green** (new). Traffic switches completely to Green after verification, allowing instant rollback if issues occur.

### Best For

- Regular feature releases
- Non-breaking API changes
- Database schema changes (backward compatible)
- Full regression testing available

### Advantages

- Instant rollback (<1 second)
- Complete testing before traffic switch
- Zero downtime
- Easy to understand

### Disadvantages

- Requires 2x resources
- Database migrations must be backward compatible
- Data synchronization complexity

### Implementation Steps

#### 1. Pre-Deployment (Blue Environment Active)

```bash
# Verify blue environment is healthy
curl https://api.thebot.com/health/ | jq .

# Baseline metrics
BASELINE_ERROR_RATE=$(curl -s http://localhost:9090/api/v1/query \
  --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[5m])' \
  | jq '.data.result[0].value[1]' -r)
echo "Baseline error rate: $BASELINE_ERROR_RATE%"

# Backup current state
./scripts/deployment/pre-deploy-check.sh
```

#### 2. Build Green Environment

```bash
# Build new images
docker-compose -f docker-compose.prod.yml build --no-cache

# Create docker-compose override for green environment
cat > docker-compose.prod-green.yml << 'EOF'
version: '3.8'

services:
  backend:
    container_name: thebot-backend-green
    environment:
      - DEPLOYMENT_ENV=green

  frontend:
    container_name: thebot-frontend-green

  nginx:
    container_name: thebot-nginx-green
    ports:
      - "8081:80"      # Green environment on 8081
      - "8443:443"
EOF

# Start green environment
docker-compose -f docker-compose.prod.yml \
  -f docker-compose.prod-green.yml \
  up -d

echo "Green environment started on port 8081"
```

#### 3. Verify Green Environment

```bash
# Wait for services to stabilize
sleep 30

# Run health checks on green
curl http://localhost:8081/api/health/ | jq .

# Run smoke tests against green
for endpoint in \
  "http://localhost:8081/api/health/" \
  "http://localhost:8081/api/auth/login/" \
  "http://localhost:8081/api/materials/"; do
  echo "Testing: $endpoint"
  curl -sf "$endpoint" > /dev/null && echo "✓ PASS" || echo "✗ FAIL"
done

# Run comprehensive verification
./scripts/deployment/verify-deployment.sh --env green

# Monitor error rates for 5 minutes
for i in {1..30}; do
  ERROR_RATE=$(curl -s http://localhost:9090/api/v1/query \
    --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[1m])' \
    | jq '.data.result[0].value[1]' -r)
  echo "[$((i*10))s] Green error rate: ${ERROR_RATE}%"

  if (( $(echo "$ERROR_RATE > 5" | bc -l) )); then
    echo "ERROR: Error rate exceeded threshold!"
    # Keep blue running and stop green
    docker-compose -f docker-compose.prod-green.yml down
    exit 1
  fi

  sleep 10
done
```

#### 4. Switch Traffic

```bash
# Update nginx to point to green
cat > nginx.conf.green << 'EOF'
upstream backend {
  server thebot-backend-green:8000;
}

upstream frontend {
  server thebot-frontend-green:3000;
}
EOF

# Reload nginx configuration
docker-compose -f docker-compose.prod.yml \
  exec nginx nginx -s reload

echo "✓ Traffic switched to green environment"

# Verify traffic is flowing
sleep 5
curl https://api.thebot.com/health/ | jq .
```

#### 5. Monitor Green Environment

```bash
# Continuous monitoring for 15 minutes
for i in {1..15}; do
  echo "Minute $i of 15..."

  # Check error rate
  ERROR_RATE=$(curl -s http://localhost:9090/api/v1/query \
    --data-urlencode 'query=rate(http_requests_total{status=~"5.."}[1m])' \
    | jq '.data.result[0].value[1]' -r)

  # Check response time
  RESPONSE_TIME=$(curl -s http://localhost:9090/api/v1/query \
    --data-urlencode 'query=histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))' \
    | jq '.data.result[0].value[1]' -r)

  echo "  Error rate: ${ERROR_RATE}%"
  echo "  Response time (p95): ${RESPONSE_TIME}s"

  # Alert if threshold exceeded
  if (( $(echo "$ERROR_RATE > 1" | bc -l) )); then
    echo "⚠️  ERROR RATE ELEVATED"
    # Rollback if critical
    if (( $(echo "$ERROR_RATE > 5" | bc -l) )); then
      echo "Rolling back..."
      docker-compose -f docker-compose.prod.yml \
        exec nginx nginx -s reload
      exit 1
    fi
  fi

  sleep 60
done

echo "✓ Monitoring period complete - green environment stable"
```

#### 6. Cleanup Blue Environment

```bash
# After successful deployment, keep blue for quick rollback
# Keep for at least 1 hour before cleanup

# To keep blue environment:
# - Blue environment remains stopped but images are available
# - Rollback just requires: docker-compose up -d blue && nginx reload

# After 1 hour, can remove old images
docker image rm thebot-backend:$(git describe --tags --abbrev=0 HEAD~1)

echo "Blue environment cleanup complete"
```

#### 7. Rollback Procedure (if needed)

```bash
#!/bin/bash
# Emergency rollback from green to blue

echo "🔄 ROLLING BACK FROM GREEN TO BLUE"

# Stop green
docker-compose -f docker-compose.prod-green.yml down

# Switch nginx back to blue
cat > nginx.conf.blue << 'EOF'
upstream backend {
  server thebot-backend:8000;
}

upstream frontend {
  server thebot-frontend:3000;
}
EOF

docker-compose -f docker-compose.prod.yml \
  exec nginx nginx -s reload

# Verify blue is responding
sleep 5
curl https://api.thebot.com/health/ | jq .

echo "✓ Rollback complete"
```

---

## Canary Deployment

### Overview

Gradually rolls out to increasing percentages of users while monitoring for issues:
- Phase 1: 5% of traffic
- Phase 2: 25% of traffic
- Phase 3: 50% of traffic
- Phase 4: 100% of traffic

### Best For

- Major feature changes
- Database schema changes (requiring careful monitoring)
- New third-party integrations
- Performance-critical changes

### Advantages

- Detects issues early with limited user impact
- Gradual rollout allows monitoring at each stage
- Can halt deployment at any phase
- Real user metrics inform decisions

### Disadvantages

- Slower deployment (30-45 minutes)
- Requires sophisticated load balancer
- Monitoring setup complexity
- Potential user experience inconsistency

### Implementation

#### 1. Build Canary Image

```bash
# Build new image
docker build -t thebot:canary-v1.2.3 -f Dockerfile.prod backend/
docker push registry.thebot.com/thebot:canary-v1.2.3

# Verify image is available
docker pull registry.thebot.com/thebot:canary-v1.2.3
echo "✓ Canary image built and pushed"
```

#### 2. Canary Phase 1 (5% Traffic)

```bash
#!/bin/bash

# Start canary instances (5% of total)
docker-compose -f docker-compose.prod.yml up -d backend-canary-1

# Configure load balancer for 5% traffic
# using weighted upstream in nginx
cat > nginx-canary-5.conf << 'EOF'
upstream backend {
  server thebot-backend:8000 weight=95;
  server thebot-backend-canary-1:8000 weight=5;
}
EOF

docker cp nginx-canary-5.conf thebot-nginx-prod:/etc/nginx/conf.d/backend.conf
docker exec thebot-nginx-prod nginx -s reload

echo "Canary Phase 1 started: 5% traffic"

# Monitor for 10 minutes
for i in {1..10}; do
  echo "Minute $i: Monitoring canary instances..."

  # Error rate specifically from canary
  CANARY_ERRORS=$(curl -s http://localhost:9090/api/v1/query \
    --data-urlencode 'query=rate(http_requests_total{pod=~".*canary.*",status=~"5.."}[1m])' \
    | jq '.data.result[0].value[1]' -r)

  echo "  Canary error rate: ${CANARY_ERRORS}%"

  # Check for exceptions in canary logs
  CANARY_EXCEPTIONS=$(docker logs --tail 100 thebot-backend-canary-1 | \
    grep -i "error\|exception" | wc -l)

  echo "  Exceptions in logs: $CANARY_EXCEPTIONS"

  # Abort if canary error rate > 5%
  if (( $(echo "$CANARY_ERRORS > 5" | bc -l) )); then
    echo "⚠️  CANARY ERROR RATE EXCEEDED"
    docker stop thebot-backend-canary-1
    docker rm thebot-backend-canary-1

    # Restore 0% canary traffic
    cat > nginx-no-canary.conf << 'EOF'
upstream backend {
  server thebot-backend:8000;
}
EOF
    docker cp nginx-no-canary.conf thebot-nginx-prod:/etc/nginx/conf.d/backend.conf
    docker exec thebot-nginx-prod nginx -s reload

    exit 1
  fi

  sleep 60
done

echo "✓ Canary Phase 1 successful"
```

#### 3. Canary Phase 2 (25% Traffic)

```bash
# Increase to 25% traffic
cat > nginx-canary-25.conf << 'EOF'
upstream backend {
  server thebot-backend:8000 weight=75;
  server thebot-backend-canary-1:8000 weight=12;
  server thebot-backend-canary-2:8000 weight=13;
}
EOF

# Start additional canary instance
docker-compose -f docker-compose.prod.yml up -d backend-canary-2

docker cp nginx-canary-25.conf thebot-nginx-prod:/etc/nginx/conf.d/backend.conf
docker exec thebot-nginx-prod nginx -s reload

echo "Canary Phase 2 started: 25% traffic"

# Continue monitoring for 15 minutes
# (same monitoring logic as Phase 1)
```

#### 4. Canary Phase 3 (50% Traffic)

```bash
# Increase to 50% traffic
cat > nginx-canary-50.conf << 'EOF'
upstream backend {
  server thebot-backend:8000 weight=50;
  server thebot-backend-canary-1:8000 weight=25;
  server thebot-backend-canary-2:8000 weight=25;
}
EOF

docker cp nginx-canary-50.conf thebot-nginx-prod:/etc/nginx/conf.d/backend.conf
docker exec thebot-nginx-prod nginx -s reload

echo "Canary Phase 3 started: 50% traffic"

# Monitor for 15 minutes
```

#### 5. Canary Phase 4 (100% Traffic)

```bash
# Full rollout
cat > nginx-full.conf << 'EOF'
upstream backend {
  server thebot-backend-canary-1:8000;
  server thebot-backend-canary-2:8000;
}
EOF

# Stop old instances
docker stop thebot-backend

docker cp nginx-full.conf thebot-nginx-prod:/etc/nginx/conf.d/backend.conf
docker exec thebot-nginx-prod nginx -s reload

echo "Canary Phase 4 complete: 100% traffic"

# Monitor for extended period (1 hour)
for i in {1..60}; do
  echo "Post-deployment monitoring minute $i..."
  # Monitoring logic
  sleep 60
done
```

---

## Rolling Update

### Overview

Updates one or a few instances at a time, ensuring service stays available throughout.

### Best For

- Microservice deployments
- Multiple instance setups
- Updates that don't require database changes
- Applications with good load distribution

### Implementation

```bash
#!/bin/bash
# Rolling update with 1-instance-at-a-time strategy

TOTAL_INSTANCES=3
BATCH_SIZE=1

echo "Rolling update deployment"
echo "Total instances: $TOTAL_INSTANCES"
echo "Batch size: $BATCH_SIZE"

for ((i=1; i<=TOTAL_INSTANCES; i+=BATCH_SIZE)); do
  END=$((i + BATCH_SIZE - 1))
  if [ $END -gt $TOTAL_INSTANCES ]; then
    END=$TOTAL_INSTANCES
  fi

  for instance in $(seq $i $END); do
    echo ""
    echo "Updating instance $instance..."

    # Remove from load balancer
    echo "  1. Removing from load balancer"
    curl -X POST http://load-balancer:8080/remove_backend \
      -d "backend=instance-$instance"

    # Drain existing connections (timeout for graceful shutdown)
    echo "  2. Draining connections"
    sleep 10

    # Kill old container
    echo "  3. Stopping old instance"
    docker-compose -f docker-compose.prod.yml \
      stop backend-$instance

    # Pull new image
    echo "  4. Pulling new image"
    docker-compose -f docker-compose.prod.yml \
      pull backend-$instance

    # Start new instance
    echo "  5. Starting new instance"
    docker-compose -f docker-compose.prod.yml \
      up -d --no-deps backend-$instance

    # Wait for health check
    echo "  6. Waiting for health check"
    HEALTH_RETRIES=30
    while [ $HEALTH_RETRIES -gt 0 ]; do
      if curl -sf http://instance-$instance:8000/health/ &>/dev/null; then
        break
      fi
      HEALTH_RETRIES=$((HEALTH_RETRIES - 1))
      sleep 1
    done

    if [ $HEALTH_RETRIES -eq 0 ]; then
      echo "  ✗ Health check failed"
      exit 1
    fi

    # Add back to load balancer
    echo "  7. Adding back to load balancer"
    curl -X POST http://load-balancer:8080/add_backend \
      -d "backend=instance-$instance"

    echo "  ✓ Instance $instance updated"
  done

  # Verify batch is healthy before continuing
  echo ""
  echo "Verifying batch..."
  ./scripts/deployment/verify-deployment.sh || exit 1
done

echo ""
echo "✓ Rolling update complete"
```

---

## Feature Flag Deployment

### Overview

Use feature flags to enable/disable new features independently of code deployment.

### Implementation

```bash
#!/bin/bash
# Deploy with feature flags

# 1. Deploy code with feature disabled
docker-compose -f docker-compose.prod.yml up -d backend

# 2. Enable feature flag progressively
echo "Enabling feature flag: new_payment_system"

# Phase 1: 10% of users
curl -X POST http://localhost:8000/admin/feature-flags/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "flag": "new_payment_system",
    "enabled_for": "10%",
    "config": {"payment_provider": "new_system"}
  }'

# Monitor
sleep 300

# Phase 2: 50% of users
curl -X POST http://localhost:8000/admin/feature-flags/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "flag": "new_payment_system",
    "enabled_for": "50%"
  }'

# Monitor
sleep 300

# Phase 3: 100% of users
curl -X POST http://localhost:8000/admin/feature-flags/ \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{
    "flag": "new_payment_system",
    "enabled_for": "100%"
  }'

echo "✓ Feature flag fully enabled"
```

---

## Database Migration Strategies

### Zero-Downtime Migration Pattern

```python
# migration: 0002_add_new_field.py

from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0001_initial'),
    ]

    operations = [
        # Step 1: Add field with default (doesn't lock table long)
        migrations.AddField(
            model_name='model',
            name='new_field',
            field=models.CharField(max_length=100, default=''),
            preserve_default=False,
        ),

        # Step 2: Create index in background
        migrations.RunSQL(
            sql="""
            CREATE INDEX CONCURRENTLY idx_new_field
            ON app_model(new_field);
            """,
            reverse_sql="DROP INDEX IF EXISTS idx_new_field;",
        ),
    ]
```

### Large Table Migration

For tables with millions of rows:

```bash
#!/bin/bash
# Migrate large table in batches

BATCH_SIZE=10000
TOTAL_ROWS=$(docker-compose exec -T postgres \
  psql -U postgres -d thebot_db -c \
  "SELECT COUNT(*) FROM large_table" | tail -1 | xargs)

echo "Migrating $TOTAL_ROWS rows in batches of $BATCH_SIZE"

for ((i=0; i<TOTAL_ROWS; i+=BATCH_SIZE)); do
  echo "Migrating rows $i to $((i+BATCH_SIZE))..."

  docker-compose exec backend python manage.py shell << EOF
from app.models import LargeModel
from django.db import connection

# Migrate batch
batch = LargeModel.objects.all()[${i}:$((i+BATCH_SIZE))]
for obj in batch:
    obj.new_field = process(obj.old_field)
    obj.save(update_fields=['new_field'])

connection.close()
EOF
done

echo "✓ Large table migration complete"
```

---

## Strategy Comparison

| Factor | Blue-Green | Canary | Rolling | Feature Flag |
|--------|-----------|--------|---------|--------------|
| **Deployment Time** | 15 min | 40 min | 30 min | 5 min |
| **Rollback Time** | <1 min | 5 min | 10 min | <1 min |
| **Resource Usage** | 2x | 1.5x | 1x | 1x |
| **Risk Level** | Low | Very Low | Medium | Very Low |
| **Testing Window** | Yes (5 min) | Yes (per phase) | No | Yes (gradual) |
| **User Impact** | All or nothing | Gradual | Gradual | None |
| **Complexity** | Medium | High | Medium | Medium |
| **Best For** | Regular releases | Major changes | Simple updates | Feature toggles |
| **Database Changes** | Backward compatible | With caution | Not recommended | N/A |

---

## Decision Tree

```
Choose deployment strategy:

Is this a hotfix for production bug?
├─ YES → Use Hotfix (manual, minimal testing)
└─ NO ↓

Are there database schema changes?
├─ YES (breaking) → Cannot deploy without downtime
├─ YES (backward compatible) → Blue-Green or Canary
└─ NO ↓

Is this a major feature change?
├─ YES → Canary deployment
└─ NO ↓

Is this a regular update?
├─ YES → Blue-Green deployment
└─ NO → Use Feature Flags

Can we use feature flags?
├─ YES → Feature flag deployment (lowest risk)
└─ NO ↓

Do we have multiple instances?
├─ YES → Rolling update
└─ NO → Blue-green deployment
```

---

**Document Version**: 1.0.0
**Last Updated**: 2025-12-27
