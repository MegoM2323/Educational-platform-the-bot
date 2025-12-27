# THE_BOT Platform - Capacity Planning Guide

**Version**: 1.0.0
**Last Updated**: December 27, 2025
**Review Frequency**: Quarterly

## Table of Contents

1. [Overview](#overview)
2. [Capacity Tiers](#capacity-tiers)
3. [Resource Baselines](#resource-baselines)
4. [Auto-Scaling Thresholds](#auto-scaling-thresholds)
5. [Scaling Procedures](#scaling-procedures)
6. [Cost Projections](#cost-projections)
7. [Resource Forecasting](#resource-forecasting)
8. [Monitoring & Alerts](#monitoring--alerts)
9. [Horizontal vs Vertical Scaling](#horizontal-vs-vertical-scaling)
10. [Disaster Recovery](#disaster-recovery)
11. [Runbooks](#runbooks)

---

## Overview

This document defines THE_BOT Platform's capacity planning framework, including:

- **Resource baselines** for 1K, 10K, and 100K concurrent users
- **Auto-scaling policies** with CPU and memory thresholds
- **Cost projections** for each capacity tier
- **Scaling procedures** for all infrastructure components
- **Resource forecasting** based on growth rates
- **Monitoring metrics** and alerting strategies

### Key Assumptions

| Parameter | Value | Description |
|-----------|-------|-------------|
| Concurrent User Ratio | 15% | Peak concurrent = 15% of registered users |
| Peak Hours | 17:00-21:00 UTC | 4-hour peak daily |
| Message Rate | 0.5/min/user | During active sessions |
| API Request Rate | 2/min/user | Background + foreground requests |
| DB Row Growth | 250 rows/user | Per new user registration |
| Monthly Growth | 15-25% | Declining over time |

---

## Capacity Tiers

### Tier 1: Starter (1K Concurrent Users)

**Target**: Early-stage deployment, pilot programs

#### Infrastructure

| Component | Specification |
|-----------|---------------|
| **Backend** | 2 instances (2 CPU, 4GB RAM each) |
| **Frontend** | 1 instance (1 CPU, 2GB RAM) |
| **Database** | PostgreSQL 15 single instance (4 CPU, 16GB RAM, 100GB storage) |
| **Redis** | 1 node (4GB) |
| **Celery** | 2 workers (4 concurrency each) |
| **Storage** | 50GB media + 100GB backups |
| **Load Balancer** | NGINX (single instance) |

#### Performance Targets

- API p50: 50ms | p95: 200ms | p99: 500ms
- WebSocket Latency: <100ms
- Database p95: <100ms
- Cache Hit Ratio: >85%
- Error Rate: <0.5%

#### Capacity Metrics

- **Registered Users**: 6,700
- **Concurrent Peak**: 1,000
- **Daily Active**: 2,000
- **API Requests/Month**: 18M
- **Messages/Month**: 450K

#### Monthly Cost

**$500 USD**

---

### Tier 2: Growth (10K Concurrent Users)

**Target**: Expanding user base, regional deployment

#### Infrastructure

| Component | Specification |
|-----------|---------------|
| **Backend** | 6 instances × 4 CPU, 8GB RAM (Kubernetes cluster) |
| **Frontend** | 2 instances × 2 CPU, 4GB RAM + CDN |
| **Database** | PostgreSQL 15 with replication (8 CPU primary, 32GB RAM + 2 replicas) |
| **Redis** | 3 nodes (8GB each) in Sentinel mode |
| **Celery** | 8 workers (8 concurrency each) |
| **Storage** | 500GB media + 1TB backups |
| **Load Balancer** | AWS ALB or NGINX Plus |

#### Performance Targets

- API p50: 40ms | p95: 150ms | p99: 400ms
- WebSocket Latency: <80ms
- Database p95: <80ms
- Cache Hit Ratio: >88%
- Error Rate: <0.2%

#### Capacity Metrics

- **Registered Users**: 67,000
- **Concurrent Peak**: 10,000
- **Daily Active**: 20,000
- **API Requests/Month**: 180M
- **Messages/Month**: 4.5M

#### Monthly Cost

**$3,500 USD**

---

### Tier 3: Enterprise (100K Concurrent Users)

**Target**: Production scale, multi-region deployment

#### Infrastructure

| Component | Specification |
|-----------|---------------|
| **Backend** | 30 instances × 8 CPU, 16GB RAM (multi-region K8s, auto-scaling 20-50) |
| **Frontend** | 5 instances × 4 CPU, 8GB RAM + CloudFront CDN |
| **Database** | AWS RDS Aurora PostgreSQL (16 CPU, 64GB RAM + 5 read replicas, multi-region) |
| **Redis** | 10 nodes (16GB each) in Cluster mode across 5 shards |
| **Celery** | 40 workers (16 concurrency each) with dedicated queues |
| **Storage** | 5TB media (S3) + 10TB backups (Glacier) |
| **Load Balancer** | AWS NLB or Google Cloud LB (multi-region) |

#### Performance Targets

- API p50: 30ms | p95: 120ms | p99: 300ms
- WebSocket Latency: <50ms
- Database p95: <60ms
- Cache Hit Ratio: >90%
- Error Rate: <0.1%

#### Capacity Metrics

- **Registered Users**: 670,000
- **Concurrent Peak**: 100,000
- **Daily Active**: 200,000
- **API Requests/Month**: 1.8B
- **Messages/Month**: 45M

#### Monthly Cost

**$25,000 USD**

---

## Resource Baselines

### Database Scaling

#### Tier 1K: Baseline Configuration

```
Instance Type:      PostgreSQL 15 (self-managed)
CPU Cores:          4
Memory:             16 GB
Storage:            100 GB
IOPS:               1,000
Connection Pool:    20
Replication:        None
Backup:             Daily snapshots (7 days)
```

#### Tier 10K: Scaling Phase

```
Instance Type:      PostgreSQL 15 (RDS Multi-AZ)
Primary CPU:        8
Primary Memory:     32 GB
Storage:            500 GB
IOPS:               5,000
Connection Pool:    100 (with pgBouncer)
Replication:        2 synchronous replicas
Backup:             Hourly snapshots (30 days)
Read Optimization:  2 read replicas
```

#### Tier 100K: Enterprise Configuration

```
Instance Type:      AWS Aurora PostgreSQL
CPU Cores:          16
Memory:             64 GB
Storage:            2 TB (auto-scaling)
IOPS:               20,000
Connection Pool:    500 (pgBouncer + connection pooling)
Replication:        5 read replicas + multi-region
Backup:             Continuous replication (90 days)
High Availability:  Multi-AZ + multi-region
Monitoring:         Enhanced Monitoring + Performance Insights
```

### Redis Scaling

#### Tier 1K: Single Node

```
Node Count:         1
Node Type:          redis:7-alpine
Memory per Node:    4 GB
Persistence:        RDB + AOF
Replication:        None
Cluster:            No
Eviction Policy:    allkeys-lru
```

#### Tier 10K: Sentinel Mode

```
Node Count:         3
Node Type:          cache.r6g.xlarge (8GB)
Memory per Node:    8 GB
Persistence:        RDB + AOF
Replication:        Master-Slave
Cluster:            No
Sentinel:           3 sentinels
Failover:           Automatic (30s)
```

#### Tier 100K: Cluster Mode

```
Node Count:         10
Node Type:          cache.r6g.2xlarge (16GB)
Memory per Node:    16 GB
Persistence:        RDB + AOF
Replication:        2x (cluster replication factor)
Cluster:            Yes (5 shards)
Sharding Strategy:  Hash-based on user_id
Failover:           Automatic
Multi-Region:       Yes
```

### Celery Task Queue Scaling

#### Tier 1K

```
Workers:                2
Concurrency/Worker:     4
Total Capacity:         8 concurrent tasks
Queue Depth Target:     <500
Task Timeout:           10 minutes (soft), 15 minutes (hard)
Priority Queues:        No
Dedicated Queues:       1 (default)
```

#### Tier 10K

```
Workers:                8
Concurrency/Worker:     8
Total Capacity:         64 concurrent tasks
Queue Depth Target:     <2000
Task Timeout:           10 minutes (soft), 15 minutes (hard)
Priority Queues:        3 (high, normal, low)
Dedicated Queues:       3 (notifications, analytics, background)
Retry Policy:           3 retries with exponential backoff
```

#### Tier 100K

```
Workers:                40
Concurrency/Worker:     16
Total Capacity:         640 concurrent tasks
Queue Depth Target:     <5000
Task Timeout:           10 minutes (soft), 15 minutes (hard)
Priority Queues:        4 (critical, high, normal, low)
Dedicated Queues:       8 (notifications, analytics, background, reporting, etc.)
Retry Policy:           5 retries with exponential backoff
Dead Letter Queue:      Yes (for failed tasks)
```

---

## Auto-Scaling Thresholds

### Backend API Scaling

#### Scale-Up Triggers

| Metric | Threshold | Duration | Action | Cooldown |
|--------|-----------|----------|--------|----------|
| CPU Utilization | ≥70% | 2 minutes | +2 instances | 5 min |
| Memory Utilization | ≥80% | 2 minutes | +1 instance | 5 min |
| Request Latency (p95) | ≥500ms | 3 minutes | +3 instances | 5 min |
| Active Connections | ≥1000 | 1 minute | +5 instances | 2 min |

#### Scale-Down Triggers

| Metric | Threshold | Duration | Action | Cooldown |
|--------|-----------|----------|--------|----------|
| CPU Utilization | ≤30% | 10 minutes | -1 instance | 10 min |
| Memory Utilization | ≤40% | 10 minutes | -1 instance | 10 min |

#### Constraints

```
Minimum Instances:     2
Maximum Instances:     50
Instance Type:         t3.2xlarge (8 CPU, 16GB RAM)
Allow Scale-Down:      No (during peak hours 17:00-21:00 UTC)
Predictive Scaling:    Yes (scale up 30 min before peaks)
```

### Database Scaling

#### Vertical Scaling (Instance Type Upgrade)

| Metric | Threshold | Action | Downtime |
|--------|-----------|--------|----------|
| CPU Utilization | ≥75% | Upgrade instance | <15 min |
| Memory Utilization | ≥85% | Upgrade instance | <15 min |
| Storage Used | ≥80% | Auto-expand (+100GB) | None |
| IOPS Utilization | ≥80% | Increase IOPS | None |

#### Horizontal Scaling (Read Replicas)

```
Trigger:        Read latency p95 >100ms
Action:         Add read replica
Max Replicas:   5
Region:         Same region initially, then multi-region
```

### Redis Scaling

#### Scale-Up Triggers

| Metric | Threshold | Action | Cooldown |
|--------|-----------|--------|----------|
| Memory Utilization | ≥85% | Add shard | 10 min |
| CPU Utilization | ≥75% | Increase node size | 5 min |
| Eviction Rate | >100 keys/sec | Critical alert + scale | 2 min |

#### Scale-Down Triggers

| Metric | Threshold | Duration | Action | Cooldown |
|--------|-----------|----------|--------|----------|
| Memory Utilization | ≤40% | 10 minutes | Remove shard | 30 min |

#### Constraints

```
Minimum Nodes:         1
Maximum Nodes:         20
Minimum Memory:        4 GB per node
Maximum Memory:        419 GB per node (r6g.16xlarge)
Replication Factor:    2 (cluster mode)
Allow Scale-Down:      No (peak hours 17:00-21:00 UTC)
Eviction Policy:       allkeys-lru (least recently used)
```

### Celery Scaling

#### Scale-Up Triggers

| Metric | Threshold | Duration | Action | Cooldown |
|--------|-----------|----------|--------|----------|
| Queue Depth | >1000 | 1 minute | +2 workers | 3 min |
| Worker CPU | >80% | 2 minutes | +1 worker | 5 min |
| Task Latency | >30 sec | 3 minutes | +3 workers | 5 min |

#### Scale-Down Triggers

| Metric | Threshold | Duration | Action | Cooldown |
|--------|-----------|----------|--------|----------|
| Queue Depth | <100 | 15 minutes | -1 worker | 15 min |

#### Constraints

```
Minimum Workers:       2
Maximum Workers:       40
Concurrency/Worker:    16
Task Timeout:          10 min (soft), 15 min (hard)
Allow Scale-Down:      Only during off-peak hours
```

### Frontend Scaling

#### Scale-Up Triggers

| Metric | Threshold | Duration | Action | Cooldown |
|--------|-----------|----------|--------|----------|
| CPU Utilization | ≥70% | 2 minutes | +1 instance | 5 min |
| Memory Utilization | ≥80% | 2 minutes | +1 instance | 5 min |
| Active Connections | >5000 | 1 minute | +2 instances | 2 min |

#### Scale-Down Triggers

| Metric | Threshold | Duration | Action | Cooldown |
|--------|-----------|----------|--------|----------|
| CPU Utilization | ≤30% | 10 minutes | -1 instance | 10 min |

---

## Scaling Procedures

### Scaling from Tier 1K to Tier 10K

**Trigger Condition**: Concurrent users reaching 3,000

**Duration**: 4 hours (zero-downtime)

#### Pre-scaling Checklist

- [ ] Verify current database health and backup status
- [ ] Schedule during low-traffic window (if possible)
- [ ] Notify team and stakeholders
- [ ] Prepare rollback plan
- [ ] Ensure all monitoring is active

#### Step 1: Database Preparation (30 minutes)

```bash
# Enable replication
ALTER SYSTEM SET wal_level = replica;
ALTER SYSTEM SET max_wal_senders = 10;

# Restart PostgreSQL
systemctl restart postgresql

# Create first read replica
# (for AWS RDS, use AWS Console)
aws rds create-db-instance-read-replica \
  --db-instance-identifier thebot-db-replica-1 \
  --source-db-instance-identifier thebot-db-primary

# Verify replication
SELECT slot_name, active FROM pg_replication_slots;
```

#### Step 2: Cache Layer Migration (45 minutes)

```bash
# Provision Redis cluster (3 nodes)
# Update docker-compose.yml or Kubernetes manifests
docker-compose up -d redis-node1 redis-node2 redis-node3

# Migrate existing cache
redis-cli --migrate <new-redis-host> 6379 0 0 0

# Update REDIS_URL in environment
export REDIS_URL=redis://redis-node1,redis-node2,redis-node3:6379/0

# Verify cluster
redis-cli cluster info
```

#### Step 3: Backend Scaling (60 minutes)

```bash
# Scale backend instances to 6
kubectl scale deployment backend --replicas=6

# Or with Docker Compose
docker-compose up --scale backend=6

# Wait for health checks
kubectl get pods -w
```

#### Step 4: Load Balancer Update (15 minutes)

```bash
# Configure load balancer for 6 backend instances
# Update NGINX upstream block or AWS ALB target group

# Test load balancing
for i in {1..100}; do curl http://api.thebot.com/api/health; done
```

#### Step 5: Monitoring & Verification (30 minutes)

```bash
# Monitor metrics
kubectl logs -f deployment/backend
tail -f /var/log/nginx/access.log

# Check performance targets
# - API p95 latency should be <150ms
# - Cache hit ratio >88%
# - Error rate <0.2%

# Run smoke tests
pytest tests/smoke_tests.py -v
```

#### Rollback Plan

If any step fails:

1. Revert DNS to old backend instances
2. Terminate new database replica
3. Reduce backend instances to 2
4. Clear Redis cache
5. Investigate issue and reschedule

---

### Scaling from Tier 10K to Tier 100K

**Trigger Condition**: Concurrent users reaching 30,000

**Duration**: 8 hours (zero-downtime, multi-region)

#### Pre-scaling Checklist

- [ ] Verify backup strategy and RPO/RTO
- [ ] Plan database migration to managed service
- [ ] Set up multi-region infrastructure
- [ ] Configure cross-region replication
- [ ] Plan DNS failover strategy
- [ ] Prepare comprehensive runbook

#### Phase 1: Database Migration to Managed Service (2 hours)

```bash
# 1. Create Aurora PostgreSQL cluster in primary region
aws rds create-db-cluster \
  --db-cluster-identifier thebot-aurora-primary \
  --engine aurora-postgresql \
  --engine-version 15.2 \
  --master-username admin \
  --master-user-password $DB_PASSWORD

# 2. Create instances in cluster
aws rds create-db-instance \
  --db-instance-identifier thebot-aurora-primary-1 \
  --db-instance-class db.r6i.2xlarge \
  --db-cluster-identifier thebot-aurora-primary

# 3. Create read replicas
aws rds create-db-instance \
  --db-instance-identifier thebot-aurora-replica-1 \
  --db-instance-class db.r6i.xlarge \
  --db-cluster-identifier thebot-aurora-primary

# 4. Migrate data using AWS DMS
# (parallel migration to avoid downtime)

# 5. Switch application to new database
export DATABASE_URL=postgresql://admin:password@aurora-cluster-endpoint:5432/thebot
```

#### Phase 2: Redis Cluster Setup (1.5 hours)

```bash
# Create Redis cluster across 5 shards
for i in {1..10}; do
  aws elasticache create-cache-cluster \
    --cache-cluster-id thebot-redis-cluster-$i \
    --cache-node-type cache.r6g.2xlarge \
    --engine redis \
    --num-cache-nodes 1
done

# Create cluster (all nodes to single cluster)
redis-cli --cluster create <node1>:6379 ... <node10>:6379

# Verify cluster
redis-cli cluster nodes
```

#### Phase 3: Multi-Region Backend Deployment (2 hours)

```bash
# Region 1 (Primary): 20 instances
kubectl scale deployment backend -n production --replicas=20

# Region 2: 5 instances (for failover)
kubectl apply -f k8s/backend-region2.yaml

# Region 3: 5 instances (for geographic distribution)
kubectl apply -f k8s/backend-region3.yaml

# Configure health checks
# Verify all regions are healthy
```

#### Phase 4: CDN & Load Balancer Setup (1.5 hours)

```bash
# Enable CloudFront CDN
aws cloudfront create-distribution \
  --distribution-config file://cloudfront-config.json

# Configure multi-region load balancer
aws globalaccelerator create-accelerator \
  --name thebot-global \
  --enabled

# Set origins for each region
# Primary region (80%)
# Secondary regions (20% - geographic failover)
```

#### Phase 5: Monitoring & Cutover (1.5 hours)

```bash
# Parallel run (old + new infrastructure)
# Monitor for 30 minutes to ensure stability

# Gradual traffic shift
# 10% → 25% → 50% → 75% → 100%
# Over 60 minutes

# Final cutover
# Update DNS to point to global accelerator
# Monitor error rates closely
```

---

## Cost Projections

### Monthly Costs by Tier

#### Tier 1K - Starter

| Component | Unit | Quantity | Unit Cost | Monthly Total |
|-----------|------|----------|-----------|---------------|
| Backend (2×2xlarge) | instance | 2 | $100 | $200 |
| Database (single) | instance | 1 | $150 | $150 |
| Redis (1 node) | node | 1 | $50 | $50 |
| Storage (50GB) | GB | 50 | $0.023 | $1.15 |
| Backup (100GB) | GB | 100 | $0.023 | $2.30 |
| Data Transfer | per GB | 100 | $0.10 | $10 |
| Monitoring | fixed | 1 | $50 | $50 |
| **Total** | | | | **$463.45** |
| **Recommended Budget** | | | | **$500** |

#### Tier 10K - Growth

| Component | Unit | Quantity | Unit Cost | Monthly Total |
|-----------|------|----------|-----------|---------------|
| Backend (6×4xlarge) | instance | 6 | $200 | $1,200 |
| Database Primary | instance | 1 | $400 | $400 |
| Database Replicas (2) | instance | 2 | $200 | $400 |
| Redis Nodes (3) | node | 3 | $200 | $600 |
| CDN | GB transferred | 1000 | $0.085 | $85 |
| Storage (500GB) | GB | 500 | $0.023 | $11.50 |
| Backup (1TB) | GB | 1024 | $0.023 | $23.55 |
| Load Balancer | fixed | 1 | $150 | $150 |
| Data Transfer | per GB | 500 | $0.10 | $50 |
| Monitoring | fixed | 1 | $100 | $100 |
| **Total** | | | | **$3,020.05** |
| **Recommended Budget** | | | | **$3,500** |

#### Tier 100K - Enterprise

| Component | Unit | Quantity | Unit Cost | Monthly Total |
|-----------|------|----------|-----------|---------------|
| Backend (30×8xlarge) | instance | 30 | $500 | $15,000 |
| Aurora Primary | instance | 1 | $1,500 | $1,500 |
| Aurora Replicas (5) | instance | 5 | $750 | $3,750 |
| Redis Cluster (10 nodes) | node | 10 | $400 | $4,000 |
| CDN | GB transferred | 10000 | $0.085 | $850 |
| S3 Storage (5TB) | GB | 5120 | $0.023 | $117.76 |
| Glacier Backup (10TB) | GB | 10240 | $0.004 | $40.96 |
| Global Load Balancer | fixed | 1 | $500 | $500 |
| Multi-region replication | per GB | 5000 | $0.02 | $100 |
| Data Transfer (cross-region) | per GB | 5000 | $0.02 | $100 |
| Monitoring & Logging | fixed | 1 | $300 | $300 |
| **Total** | | | | **$26,258.72** |
| **Recommended Budget** | | | | **$25,000-30,000** |

### Cost Optimization Strategies

#### Reserved Instances (40-60% savings)

```
Tier 1K:   $500/mo → $250/mo (3-year reserved)
Tier 10K:  $3,500/mo → $1,750/mo (3-year reserved)
Tier 100K: $25,000/mo → $10,000/mo (3-year reserved)
```

#### Spot Instances for Non-critical Workloads

```
Celery workers:    70% spot (saves $500-2000/mo)
Batch jobs:        100% spot (saves $200-1000/mo)
Dev/test:          100% spot (saves $300-1500/mo)
```

#### Data Transfer Optimization

```
Enable CDN:        Reduces data transfer by 60-70%
Enable compression: Reduces bandwidth by 40-50%
Regional buckets:  Reduces cross-region transfer costs
VPC endpoints:     Eliminates S3 data transfer costs
```

### 24-Month Cost Projection

#### Conservative Scenario (10% monthly growth)

| Month | Users | Monthly Cost | Cumulative |
|-------|-------|--------------|-----------|
| 1 | 10K | $600 | $600 |
| 6 | 20K | $1,000 | $4,800 |
| 12 | 40K | $2,500 | $16,500 |
| 18 | 80K | $10,000 | $48,000 |
| 24 | 160K | $20,000 | $180,000 |

**Total 24 Months: $180,000 USD**

#### Moderate Scenario (20% monthly growth)

| Month | Users | Monthly Cost | Cumulative |
|-------|-------|--------------|-----------|
| 1 | 10K | $600 | $600 |
| 6 | 43K | $1,500 | $5,500 |
| 12 | 106K | $5,000 | $28,000 |
| 18 | 217K | $15,000 | $96,000 |
| 24 | 405K | $25,000 | $272,000 |

**Total 24 Months: $272,000 USD**

#### Aggressive Scenario (25% monthly growth)

| Month | Users | Monthly Cost | Cumulative |
|-------|-------|--------------|-----------|
| 1 | 10K | $600 | $600 |
| 6 | 59K | $2,000 | $7,500 |
| 12 | 149K | $8,000 | $42,000 |
| 18 | 330K | $20,000 | $140,000 |
| 24 | 650K | $30,000 | $360,000 |

**Total 24 Months: $360,000 USD**

---

## Resource Forecasting

### Using the Forecasting Tool

The `resource-forecast.py` script predicts resource needs based on user growth.

#### Installation

```bash
cd infrastructure/capacity
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Basic Usage

```bash
# Moderate growth scenario (default)
python resource-forecast.py

# Conservative growth
python resource-forecast.py --scenario conservative --months 24

# Aggressive growth
python resource-forecast.py --scenario aggressive --initial-users 50000

# Export to CSV
python resource-forecast.py --export csv

# Export to JSON
python resource-forecast.py --export json
```

#### Output Example

```
================================================================================
THE_BOT PLATFORM - RESOURCE FORECASTING REPORT
Scenario: MODERATE | Period: 24 months
Initial Users: 10,000
================================================================================

Month  Users      Concurrent  DAU     Tier          Backend  DB CPU  DB Mem  Redis  Celery  Cost/mo   Storage
1      10,000     1,500       2,000   tier_1k       2        4       16      1      2       $600      50
3      18,900     2,835       3,780   tier_1k       2        4       16      1      2       $800      75
6      42,189     6,328       8,438   tier_10k      6        8       32      3      8       $1,500    150
9      73,430     11,015      14,686  tier_10k      6        8       32      3      8       $3,500    250
12     105,753    15,863      21,151  tier_100k     15       12      48      5      15      $5,000    350
18     217,189    32,579      43,438  tier_100k     25       14      56      8      25      $12,000   650
24     405,318    60,798      81,064  tier_100k     30       16      64      10     40      $20,000   1000
```

### Growth Rate Assumptions

#### Conservative

- Months 1-6: 10% monthly growth
- Months 7-12: 8% monthly growth
- Months 13-24: 5% monthly growth
- **24-month result**: 160K users

#### Moderate

- Months 1-6: 25% monthly growth
- Months 7-12: 20% monthly growth
- Months 13-24: 15% monthly growth
- **24-month result**: 405K users

#### Aggressive

- Months 1-6: 35% monthly growth
- Months 7-12: 30% monthly growth
- Months 13-24: 25% monthly growth
- **24-month result**: 900K users

---

## Monitoring & Alerts

### Critical Metrics

#### API Error Rate

| Level | Threshold | Action |
|-------|-----------|--------|
| ⚠️ Warning | >0.5% | Notify team |
| 🚨 Critical | >1.0% | Page on-call |
| 💀 Outage | >5.0% | War room |

```yaml
# Prometheus alert
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
  for: 5m
  annotations:
    summary: "High error rate on {{ $labels.instance }}"
    severity: critical
```

#### Database Connection Pool Exhaustion

| Level | Threshold | Action |
|-------|-----------|--------|
| ⚠️ Warning | >70% | Notify team |
| 🚨 Critical | >95% | Page on-call |

```yaml
- alert: DatabaseConnectionPoolExhausted
  expr: pg_stat_activity_count / pg_settings_max_connections > 0.95
  for: 2m
  annotations:
    summary: "Database connection pool exhausted"
    severity: critical
```

#### Redis Memory Exhaustion

| Level | Threshold | Action |
|-------|-----------|--------|
| ⚠️ Warning | >80% | Increase eviction |
| 🚨 Critical | >95% | Page on-call |

```yaml
- alert: RedisMemoryAlmostFull
  expr: redis_memory_used_bytes / redis_memory_max_bytes > 0.95
  for: 5m
  annotations:
    summary: "Redis memory almost full"
    severity: critical
```

#### WebSocket Connection Failures

| Level | Threshold | Action |
|-------|-----------|--------|
| ⚠️ Warning | >1% | Notify team |
| 🚨 Critical | >5% | Page on-call |

```yaml
- alert: WebSocketFailures
  expr: rate(websocket_connection_failures_total[5m]) > 0.05
  for: 2m
  annotations:
    summary: "High WebSocket failure rate"
    severity: critical
```

### Warning Metrics

| Metric | Threshold | Frequency | Action |
|--------|-----------|-----------|--------|
| CPU Utilization | >70% | 3 min | Page team |
| Memory Utilization | >80% | 3 min | Page team |
| Database Query p95 | >200ms | 5 min | Investigate |
| API Latency p95 | >500ms | 5 min | Scale backend |
| Queue Depth | >1000 | 1 min | Scale celery |

### Capacity Planning Metrics

| Metric | Tracking | Alert When | Action |
|--------|----------|-----------|--------|
| Storage Growth | Daily | 3 months remaining | Plan expansion |
| User Growth | Weekly | 70% of tier capacity | Plan tier migration |
| Cost | Monthly | >20% increase | Optimize costs |
| API Throughput | Hourly | Growing 50% mo/mo | Plan scaling |

### Dashboard Setup

#### Key Dashboards

1. **Overview Dashboard**
   - Current tier and capacity
   - Active users and concurrent peak
   - API throughput and error rate
   - Database and cache health

2. **Scaling Dashboard**
   - Auto-scaling history
   - Resource utilization trends
   - Cost projections
   - Tier migration readiness

3. **Performance Dashboard**
   - API latency (p50, p95, p99)
   - Database query performance
   - Cache hit ratios
   - WebSocket latency

---

## Horizontal vs Vertical Scaling

### Horizontal Scaling (Preferred)

**Add more instances/nodes of same size**

#### Advantages

- ✅ No downtime (can add instances gradually)
- ✅ Cost-effective (commodity hardware)
- ✅ Improved availability (redundancy)
- ✅ Better performance isolation
- ✅ Elastic (can scale down)

#### Disadvantages

- ❌ Increased complexity (load balancing, state management)
- ❌ Higher operational overhead
- ❌ Network latency between nodes

#### When to Use

- Backend API servers
- Frontend/CDN nodes
- Redis Cluster
- Celery workers
- Read replicas

#### Example Configuration

```yaml
# Backend auto-scaling
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
spec:
  replicas: 6
  template:
    spec:
      containers:
      - name: backend
        resources:
          requests:
            cpu: 4
            memory: 8Gi
          limits:
            cpu: 4
            memory: 8Gi
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: backend-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: backend
  minReplicas: 2
  maxReplicas: 50
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Vertical Scaling (Fallback)

**Upgrade to larger instance/node**

#### Advantages

- ✅ Simpler operations (no load balancing)
- ✅ Easier data management (single instance)
- ✅ Lower network latency
- ✅ Simpler backup/restore

#### Disadvantages

- ❌ Requires downtime (usually 10-30 min)
- ❌ Expensive (jump from 8GB to 16GB is 2×)
- ❌ Not elastic (can't scale down gracefully)
- ❌ Single point of failure (if not replicated)

#### When to Use

- Primary database (with replicas)
- Temporary spike handling
- Single-instance deployments

#### Example Configuration

```bash
# PostgreSQL vertical scaling (RDS)
aws rds modify-db-instance \
  --db-instance-identifier thebot-db \
  --db-instance-class db.r6i.2xlarge \
  --apply-immediately  # Or --preferred-maintenance-window

# Wait for completion
aws rds describe-db-instances \
  --query 'DBInstances[0].[DBInstanceIdentifier,DBInstanceStatus]'
```

### Decision Matrix

| Scenario | Horizontal | Vertical | Decision |
|----------|-----------|----------|----------|
| API backend traffic spike | ✅ | ❌ | Horizontal |
| Database query latency | ✅ | ✅ | Try horizontal (replicas) first, then vertical |
| Memory shortage | ✅ | ✅ | Horizontal for backend, vertical for database |
| Disk space | ❌ | ✅ | Vertical (expand storage) |
| Cache eviction | ✅ | ✅ | Horizontal (add shards) first |
| CPU bottleneck | ✅ | ✅ | Horizontal preferred, vertical fallback |

---

## Disaster Recovery

### Recovery Objectives

| Objective | Value | Tier 1K | Tier 10K | Tier 100K |
|-----------|-------|---------|----------|-----------|
| **RTO** | Recovery Time | 1 hour | 30 min | 15 min |
| **RPO** | Recovery Point | 24 hours | 1 hour | 15 min |

### Backup Strategy

#### Tier 1K - Daily Snapshots

```
Frequency:     Daily (02:00 UTC)
Retention:     7 days
Location:      Same region
Restore Time:  30-60 minutes
Data Loss:     Up to 24 hours
```

#### Tier 10K - Hourly Snapshots + Replicas

```
Database:
  Frequency:     Hourly snapshots
  Retention:     30 days
  Location:      Same region + cross-region replica
  Restore Time:  5-15 minutes
  Data Loss:     Up to 1 hour

Redis:
  Frequency:     Continuous (RDB every 6h + AOF)
  Retention:     7 days
  Location:      Replica nodes
  Restore Time:  1-5 minutes
  Data Loss:     <1 minute
```

#### Tier 100K - Continuous Replication

```
Database:
  Replication:   Continuous to replicas + multi-region
  Retention:     90 days
  Location:      5 read replicas + multi-region
  Restore Time:  <5 minutes (automatic failover)
  Data Loss:     <1 minute

Redis:
  Replication:   Cluster mode (2x replication factor)
  Retention:     Cross-region backup
  Restore Time:  <1 minute
  Data Loss:     0 (synchronous replication)

Application:
  Version:       Continuous deployment
  Rollback:      Instant (previous version ready)
```

### Failover Procedures

#### Database Failover (RDS)

```bash
# Automatic failover (if replica exists)
aws rds failover-db-instance \
  --db-instance-identifier thebot-db-primary

# Manual promotion of read replica
aws rds promote-read-replica \
  --db-instance-identifier thebot-db-replica-1

# Expected downtime: 30-60 seconds
```

#### Redis Failover

```bash
# Automatic failover in Sentinel mode
# (Sentinel automatically promotes replica)

# Manual promotion in Cluster mode
redis-cli --cluster failover <cluster-node>

# Expected downtime: <1 second
```

#### Application Failover

```bash
# DNS-based failover
aws route53 change-resource-record-sets \
  --hosted-zone-id <zone-id> \
  --change-batch file://failover.json

# Expected downtime: 1-5 minutes (DNS propagation)
```

### Regular Testing

```
Schedule:    Monthly failover tests
Procedure:
  1. Schedule test window (low traffic)
  2. Initiate failover (manual)
  3. Monitor metrics (errors, latency)
  4. Failback to primary
  5. Document results
  6. Post-mortem (if issues)
```

---

## Runbooks

### Runbook: Handling API Latency Spike

#### Symptoms
- API response time p95 > 500ms
- Error rate increasing
- Users reporting slowness

#### Steps

1. **Diagnose** (5 min)
   ```bash
   # Check backend utilization
   kubectl top pods | grep backend

   # Check database queries
   SELECT query, mean_exec_time FROM pg_stat_statements
   ORDER BY mean_exec_time DESC LIMIT 10;

   # Check Redis
   redis-cli info stats
   ```

2. **Immediate Actions** (5 min)
   ```bash
   # Scale backend up
   kubectl scale deployment backend --replicas=10

   # Clear Redis cache
   redis-cli FLUSHDB

   # Enable read-only mode (if critical)
   # (disable non-critical features)
   ```

3. **Investigation** (15 min)
   - Check slow query logs
   - Review recent deployments
   - Check for N+1 queries
   - Verify database connection pool usage

4. **Resolution**
   - Kill slow queries: `SELECT pg_terminate_backend(pid)`
   - Add missing database indexes
   - Optimize queries
   - Deploy fix

5. **Monitoring** (30 min)
   - Watch metrics every 5 min
   - Scale down if resolved
   - Post-incident review

### Runbook: Database Connection Pool Exhaustion

#### Symptoms
- "Cannot obtain a database connection" errors
- Requests timing out
- Background jobs failing

#### Steps

1. **Verify Issue**
   ```bash
   # Check current connections
   SELECT count(*) FROM pg_stat_activity;

   # Check max allowed
   SHOW max_connections;

   # Check per application
   SELECT usename, count(*) FROM pg_stat_activity
   GROUP BY usename;
   ```

2. **Immediate Relief** (5 min)
   ```bash
   # Kill idle connections
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE state = 'idle';

   # Kill connections from specific app
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE application_name = 'backend-old';
   ```

3. **Scale Connection Pool**
   ```bash
   # Update pgBouncer config
   max_client_conn = 2000  # was 1000
   default_pool_size = 50  # was 25

   # Reload
   pgbouncer -R /etc/pgbouncer.conf
   ```

4. **Long-term Fix**
   ```bash
   # Increase PostgreSQL max_connections
   ALTER SYSTEM SET max_connections = 500;
   systemctl restart postgresql

   # Monitor actual usage
   # Plan vertical scaling if consistently high
   ```

### Runbook: Redis Memory Exhaustion

#### Symptoms
- Redis eviction rate > 100 keys/sec
- Cache hit ratio dropping
- Memory usage at 95%+

#### Steps

1. **Check Memory Usage**
   ```bash
   redis-cli INFO memory

   # Check top keys
   redis-cli --bigkeys

   # Check eviction rate
   redis-cli INFO stats | grep evicted
   ```

2. **Immediate Actions**
   ```bash
   # Check and remove expired keys
   redis-cli --scan --pattern "*" | head -100

   # Clear specific keys
   redis-cli DEL cache:old:*

   # Adjust eviction policy
   CONFIG SET maxmemory-policy allkeys-lru
   ```

3. **Scaling**
   ```bash
   # Add new Redis node
   aws elasticache create-cache-cluster \
     --cache-cluster-id thebot-redis-new

   # Rebalance cluster
   redis-cli --cluster rebalance <cluster-node>
   ```

4. **Prevention**
   - Set TTL on cache keys
   - Monitor key growth
   - Plan cluster sizing before reaching 80%

---

## Appendix

### Configuration Files

- **capacity-plan.json**: Complete capacity baseline definitions
- **scaling-thresholds.json**: Auto-scaling trigger configurations
- **resource-forecast.py**: Growth forecasting script

### Related Documentation

- [DEPLOYMENT.md](DEPLOYMENT.md) - Production deployment guide
- [SECURITY.md](SECURITY.md) - Security best practices
- [PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md) - Pre-launch verification

### Tools & Integrations

- **Monitoring**: Prometheus + Grafana
- **Alerting**: PagerDuty or Opsgenie
- **Infrastructure**: Kubernetes, AWS, or GCP
- **Tracking**: Jira for capacity planning tasks

### Support

For capacity planning questions:
1. Review this documentation
2. Check capacity-plan.json configuration
3. Run resource-forecast.py for projections
4. Consult with DevOps team
5. File capacity planning task in Jira

---

**Last Updated**: December 27, 2025
**Next Review**: March 27, 2025 (quarterly)
