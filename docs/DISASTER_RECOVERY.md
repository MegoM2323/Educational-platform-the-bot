# Disaster Recovery Strategy - THE_BOT Platform

Complete disaster recovery documentation covering all failure scenarios, recovery procedures, and automated failover mechanisms.

**Version**: 1.0.0
**Last Updated**: December 27, 2025
**Status**: Production Ready

---

## Executive Summary

The THE_BOT Platform implements a comprehensive disaster recovery (DR) strategy with:

- **Recovery Time Objective (RTO)**: < 1 hour
- **Recovery Point Objective (RPO)**: < 15 minutes
- **Automated failover** for database and cache
- **Point-in-time recovery** (PITR) via WAL archiving
- **Multi-layer backup** strategy (full + incremental)
- **Automated verification** and recovery testing
- **Runbook-driven incident response** (JSON-based)

---

## Table of Contents

1. [Failure Scenarios](#failure-scenarios)
2. [Architecture & Components](#architecture--components)
3. [Backup Strategy](#backup-strategy)
4. [Recovery Procedures](#recovery-procedures)
5. [Failover Processes](#failover-processes)
6. [Verification & Testing](#verification--testing)
7. [RTO/RPO Analysis](#rto-rpo-analysis)
8. [Operational Procedures](#operational-procedures)
9. [Monitoring & Alerting](#monitoring--alerting)

---

## Failure Scenarios

### Scenario 1: Single Service Failure (RTO: 5-10 minutes)

**Affected Service**: Backend, Frontend, or Celery worker

**Root Causes**:
- Container crash or OOM kill
- Application error/uncaught exception
- Dependency failure (missing env var)
- Health check timeout

**Recovery Steps**:
1. **Automatic (via Docker Compose health checks)**:
   - Service automatically restarts (max 3 attempts)
   - Health check verifies service is responsive
   - If 3 attempts fail, alert is triggered

2. **Manual Recovery** (if auto-restart fails):
   ```bash
   # Restart service
   docker-compose -f docker-compose.prod.yml restart backend

   # Or redeploy
   docker-compose -f docker-compose.prod.yml up -d --force-recreate backend
   ```

3. **Verify**:
   - Health check: `curl http://backend:8000/api/system/health/`
   - Logs: `docker-compose logs -f backend`

---

### Scenario 2: Database Failure (RTO: 15-30 minutes)

**Affected Service**: PostgreSQL

**Root Causes**:
- Disk space exhausted
- Corrupted data files
- Connection pool exhaustion
- OOM killer terminating process

**Prevention**:
- Monitor disk usage (alert at 80%)
- Monitor connection pool (max 200)
- Regular integrity checks (pg_dump --schema-only)
- Max connections set to 200 (not unlimited)

**Recovery Steps**:

#### 2A. Service Still Running (Data Corruption)
```bash
# Use WAL archiving for point-in-time recovery
scripts/disaster-recovery/restore-database.sh --type pitr --until "2025-12-27 14:30:00"
```

#### 2B. Service Down (Crashed)
```bash
# 1. Restore from latest backup
scripts/disaster-recovery/restore-database.sh --type full --from latest

# 2. If that fails, perform PITR
scripts/disaster-recovery/restore-database.sh --type pitr --until "2025-12-27 14:00:00"
```

#### 2C. Disk Corruption
```bash
# 1. Remove corrupted container
docker-compose -f docker-compose.prod.yml rm -f postgres

# 2. Remove volume (WARNING: DATA LOSS)
docker volume rm thebot_postgres_data

# 3. Restore from backup
scripts/disaster-recovery/restore-database.sh --type full --from weekly

# 4. Restart
docker-compose -f docker-compose.prod.yml up -d postgres
```

---

### Scenario 3: Cache (Redis) Failure (RTO: 5 minutes)

**Affected Services**: Chat (WebSocket), Session storage, Celery tasks

**Root Causes**:
- Memory limit exceeded (512MB)
- Corrupted AOF file
- Disk space for persistence

**Prevention**:
- Monitor memory usage (alert at 80%)
- Enable AOF with fsync=everysec
- Regular AOF rewrite (every 2GB or 1 day)

**Recovery Steps**:

#### 3A. Service Running but Slow
```bash
# Check memory usage
docker-compose exec redis redis-cli info memory

# Evict old keys (if memory exhausted)
docker-compose exec redis redis-cli FLUSHDB

# Or restart service (loss of session data, acceptable for dev)
docker-compose -f docker-compose.prod.yml restart redis
```

#### 3B. Service Down / Corrupted AOF
```bash
# Restore from AOF backup
scripts/disaster-recovery/restore-redis.sh --type aof --from latest

# If AOF is corrupted, restore from full backup
scripts/disaster-recovery/restore-redis.sh --type rdb --from weekly

# Restart service
docker-compose -f docker-compose.prod.yml up -d redis
```

---

### Scenario 4: Complete Datacenter Failure (RTO: 1 hour, RPO: 15 min)

**Affected Services**: All

**Prerequisites**:
- AWS S3 backup of all data
- Documented infrastructure-as-code (Terraform)
- Secondary region/datacenter ready

**Recovery Steps**:

#### 4A. Failover to Secondary Datacenter
```bash
# 1. Verify secondary is ready
terraform apply -var-file=secondary.tfvars

# 2. Restore databases
scripts/disaster-recovery/restore-database.sh --type full --from s3

# 3. Restore cache (OK to start empty, will repopulate)
docker-compose -f docker-compose.prod.yml up -d redis

# 4. Update DNS to point to secondary
# (via Route 53 or equivalent)

# 5. Verify full system
scripts/disaster-recovery/verify-recovery.sh --full
```

#### 4B. Sync Data After Failover
```bash
# Once primary is recovered:
# 1. Promote secondary as new primary (if primary data is unrecoverable)
# 2. Restore primary from backup
# 3. Set up replication: primary -> new backup
```

---

### Scenario 5: Data Corruption (Partial, RTO: 30-60 minutes)

**Affected Data**: Specific tables/records

**Root Causes**:
- Bug in data migration
- Concurrent modification deadlock
- Silent disk corruption (RAID failure)

**Recovery Steps**:

#### 5A. Identify Corrupted Data
```bash
# Query for anomalies (e.g., null values that shouldn't be)
# Or use application-level verification

# Check integrity
docker-compose exec postgres pg_dump --schema-only thebot_db > /tmp/schema.sql
docker-compose exec postgres pg_dump -F custom thebot_db > /tmp/data.dump
```

#### 5B. Recover Using PITR
```bash
# Restore to point in time BEFORE corruption occurred
scripts/disaster-recovery/restore-database.sh --type pitr --until "2025-12-27 13:00:00"

# Verify data is correct
docker-compose exec postgres psql -U postgres -d thebot_db -c "SELECT COUNT(*) FROM users;"
```

#### 5C. Selective Recovery (if corruption is isolated)
```bash
# Export good data from secondary (if available)
# Or restore specific table from backup:

# 1. Restore to staging
docker-compose -f docker-compose.staging.yml up postgres
scripts/disaster-recovery/restore-database.sh --type pitr --until "2025-12-27 13:00:00" --target staging

# 2. Export good table
docker-compose -f docker-compose.staging.yml exec postgres pg_dump \
  -U postgres -d thebot_db \
  --table=users \
  --data-only > /tmp/users_data.sql

# 3. Import to production
docker-compose exec postgres psql -U postgres -d thebot_db < /tmp/users_data.sql
```

---

## Architecture & Components

### High-Availability Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   LOAD BALANCER                         │
│              (Nginx - container)                        │
└────────┬──────────────────────────────┬─────────────────┘
         │                              │
    ┌────▼────────┐            ┌────────▼─────┐
    │   Backend   │            │   Frontend    │
    │ (Container) │            │  (Container)  │
    └────┬────────┘            └───────────────┘
         │
    ┌────▼──────────────────┬──────────────────┐
    │                       │                  │
┌───▼────┐           ┌──────▼────┐      ┌──────▼─────┐
│ Primary│           │  Redis    │      │   Celery   │
│  Postgres          │ (Cache)   │      │  Workers   │
│  (Main DB)         │           │      │            │
└────────┘           └───────────┘      └────────────┘
```

### Backup Architecture

```
┌─────────────────────────────────────────────────────┐
│              BACKUP SYSTEM                          │
├─────────────────────────────────────────────────────┤
│ PostgreSQL                                          │
│ ├─ Daily backups (pg_dump custom format)           │
│ ├─ Weekly full backups                             │
│ ├─ Monthly full backups                            │
│ └─ WAL archiving (for PITR, 7-day retention)       │
│                                                     │
│ Redis                                              │
│ ├─ AOF persistence (appendonly.aof)                │
│ ├─ Daily snapshots (RDB format)                    │
│ └─ Weekly full backups                             │
│                                                     │
│ Storage Locations:                                 │
│ ├─ Local: /backups/ (7-day retention)              │
│ ├─ S3: s3://backup-bucket/ (30-day retention)      │
│ └─ WAL Archive: /wal-archive/ (7 days)             │
└─────────────────────────────────────────────────────┘
```

---

## Backup Strategy

### PostgreSQL Backups

**Backup Types**:
- **Full Backup**: `pg_dump --F custom` (weekly + monthly)
- **WAL Archiving**: Point-in-time recovery (every 5 minutes)
- **Differential**: Incremental based on WAL (implicit)

**Retention Policy**:
- Daily: 7 backups (7 days)
- Weekly: 4 backups (4 weeks)
- Monthly: 12 backups (1 year)
- WAL Files: 7 days (168 files at 16MB each)

**Storage**:
- Primary: `/home/mego/Python Projects/THE_BOT_platform/backups/`
- Secondary: AWS S3 (if configured)

**Backup Command**:
```bash
# Daily full backup
pg_dump -U postgres -d thebot_db -F custom > backup_20251227.dump

# With compression
pg_dump -U postgres -d thebot_db -F custom | gzip > backup_20251227.dump.gz

# WAL archiving (set in postgresql.conf)
archive_mode = on
archive_command = 'test ! -f /wal-archive/%f && cp %p /wal-archive/%f'
```

### Redis Backups

**Persistence Methods**:
- **AOF (Append-Only File)**: Every operation logged, fsync=everysec
- **RDB (Snapshot)**: Point-in-time snapshot, daily
- **Manual Backup**: `BGSAVE` for non-disruptive backups

**Retention Policy**:
- AOF files: Real-time (keep 2GB max, auto-rewrite)
- RDB snapshots: Daily (7 kept)
- Full backups: Weekly (4 kept)

**Storage**:
- Primary: `/var/lib/docker/volumes/thebot_redis_data/_data/`
- Secondary: AWS S3 (if configured)

**Backup Command**:
```bash
# Redis snapshot (non-blocking)
redis-cli BGSAVE

# AOF rewrite
redis-cli BGREWRITEAOF

# Export as dump
redis-cli --rdb /backups/redis_snapshot.rdb
```

### Combined Backup Verification

**Backup Metadata** (JSON):
```json
{
  "backup_id": "backup_20251227_010000",
  "type": "full",
  "service": "postgresql",
  "timestamp": "2025-12-27T01:00:00Z",
  "size_bytes": 536870912,
  "size_readable": "512MB",
  "duration_seconds": 1234,
  "files": ["backup_20251227_010000.dump.gz"],
  "checksum": "sha256:abc123...",
  "verified": true,
  "retention": "7_days",
  "restorability": "VERIFIED",
  "notes": "Daily backup, full database dump"
}
```

---

## Recovery Procedures

### Procedure 1: PostgreSQL Full Recovery (Fresh Install)

**Time**: 15-20 minutes
**Data Loss**: None (up to backup time)
**Prerequisites**: Backup file available, container stopped

**Steps**:

```bash
#!/bin/bash
# 1. Stop current service
docker-compose -f docker-compose.prod.yml stop postgres

# 2. Remove old data (WARNING: DESTRUCTIVE)
docker volume rm thebot_postgres_data || true
mkdir -p /backups/pre-restore-$(date +%Y%m%d_%H%M%S)

# 3. Start fresh container
docker-compose -f docker-compose.prod.yml up -d postgres
sleep 10  # Wait for PostgreSQL to initialize

# 4. Restore from backup
BACKUP_FILE="/backups/daily/backup_20251227_010000.dump.gz"
gunzip < "$BACKUP_FILE" | docker-compose exec -T postgres \
  pg_restore -U postgres -d thebot_db --exit-on-error

# 5. Verify
docker-compose exec postgres psql -U postgres -d thebot_db -c "SELECT COUNT(*) FROM users;"

# 6. Restart full system
docker-compose -f docker-compose.prod.yml up -d
```

### Procedure 2: PostgreSQL PITR (Point-in-Time Recovery)

**Time**: 20-30 minutes
**Data Loss**: None (recover to specific minute)
**Prerequisites**: WAL files available from target time to now

**Steps**:

```bash
#!/bin/bash
# 1. Stop services
docker-compose -f docker-compose.prod.yml stop

# 2. Create backup of current state
cp -r /var/lib/docker/volumes/thebot_postgres_data/_data \
  /backups/pre-restore-$(date +%Y%m%d_%H%M%S)

# 3. Remove current data
docker volume rm thebot_postgres_data
docker-compose -f docker-compose.prod.yml up -d postgres
sleep 10

# 4. Restore base backup
BACKUP_FILE="/backups/weekly/backup_2025W52_030000.dump.gz"
gunzip < "$BACKUP_FILE" | docker-compose exec -T postgres \
  pg_restore -U postgres -d thebot_db --exit-on-error

# 5. Apply WAL archiving for PITR
docker-compose exec postgres pg_ctl stop -D /var/lib/postgresql/data
docker-compose exec postgres pg_wal_replay_pause
docker-compose exec postgres pg_ctl start -D /var/lib/postgresql/data

# 6. Restore to specific time (e.g., 2025-12-27 14:30:00)
# Note: This requires recovery.conf setup (advanced)
cat > /tmp/recovery.conf << EOF
restore_command = 'test -f /wal-archive/%f && cp /wal-archive/%f %p'
recovery_target_timeline = 'latest'
recovery_target_time = '2025-12-27 14:30:00'
recovery_target_inclusive = false
EOF

# (Implementation varies by PostgreSQL version)
```

### Procedure 3: Redis Full Recovery

**Time**: 5-10 minutes
**Data Loss**: Acceptable (session data, cache)
**Prerequisites**: AOF backup or RDB snapshot available

**Steps**:

```bash
#!/bin/bash
# 1. Restore from AOF
BACKUP_FILE="/backups/daily/redis_aof_20251227.bak"
docker-compose -f docker-compose.prod.yml stop redis

# 2. Restore AOF file
docker volume rm thebot_redis_data || true
docker-compose -f docker-compose.prod.yml up -d redis
sleep 5

# 3. Copy AOF to container
docker cp "$BACKUP_FILE" thebot-redis-prod:/data/appendonly.aof

# 4. Restart Redis (it will replay AOF)
docker-compose -f docker-compose.prod.yml restart redis

# 5. Verify
docker-compose exec redis redis-cli -a ${REDIS_PASSWORD} DBSIZE
docker-compose exec redis redis-cli -a ${REDIS_PASSWORD} INFO server
```

### Procedure 4: Complete System Recovery (Datacenter Failure)

**Time**: 45-60 minutes
**Data Loss**: < 15 minutes (since last backup)
**Prerequisites**: Secondary datacenter/region prepared

**Steps**:

```bash
#!/bin/bash
# Phase 1: Prepare Infrastructure (15 min)
# ========================================
# In secondary region:
terraform init
terraform apply -var-file=production-secondary.tfvars -auto-approve
sleep 300  # Wait for infrastructure to be ready

# Phase 2: Restore Databases (20 min)
# ===================================
# Download from S3
aws s3 cp s3://backup-bucket/postgresql/latest.dump.gz /tmp/
aws s3 cp s3://backup-bucket/redis/latest.rdb /tmp/

# Restore PostgreSQL
gunzip < /tmp/latest.dump.gz | docker-compose exec -T postgres \
  pg_restore -U postgres -d thebot_db --exit-on-error

# Restore Redis
docker-compose exec redis redis-cli SHUTDOWN
cp /tmp/latest.rdb /var/lib/docker/volumes/secondary_redis_data/_data/dump.rdb
docker-compose up -d redis

# Phase 3: Verify System (10 min)
# ===============================
scripts/disaster-recovery/verify-recovery.sh --full

# Phase 4: Update DNS (5 min)
# ===========================
# Update Route 53 or equivalent to point to secondary
```

---

## Failover Processes

### Automated Database Failover (Replica Promotion)

**Prerequisites**: Read replica running in secondary

**Process** (automated):

```bash
#!/bin/bash
# Check if primary is down
if ! docker-compose exec postgres pg_isready; then
    echo "Primary database is down. Promoting replica..."

    # Promote read replica to primary
    docker-compose exec postgres_replica \
      pg_ctl promote -D /var/lib/postgresql/data

    # Wait for promotion to complete
    sleep 10

    # Update connection string to point to new primary
    export DATABASE_URL="postgresql://user:pass@postgres-replica:5432/thebot_db"

    # Restart backend
    docker-compose up -d backend
fi
```

**Implementation**:
- Replica is configured with `recovery_target_timeline = 'latest'`
- Monitoring script detects primary failure
- Automatic promotion via `pg_ctl promote`
- Connection string updated automatically
- Backend reconnects to new primary

### Redis Failover (Cluster or Sentinel)

**Prerequisites**: Redis Sentinel or Cluster configured

**Process** (automated):

```bash
#!/bin/bash
# Sentinel monitors Redis and auto-promotes replica
redis-sentinel /etc/redis/sentinel.conf

# On primary failure:
# 1. Sentinel detects primary is down (3 lost pings)
# 2. Sentinel promotes best replica to primary
# 3. Sentinel reconfigures other replicas to follow new primary
# 4. Application clients connect via sentinel DNS
```

---

## Verification & Testing

### Recovery Verification Script

The `verify-recovery.sh` script tests:

**Quick Check** (5 min):
```bash
scripts/disaster-recovery/verify-recovery.sh --quick

# Tests:
# 1. Backend health: /api/system/health/
# 2. Database connectivity
# 3. Redis connectivity
# 4. Celery worker status
```

**Full Check** (15 min):
```bash
scripts/disaster-recovery/verify-recovery.sh --full

# Tests (in addition to quick):
# 1. Database integrity (table counts, checksums)
# 2. Redis data integrity (key counts)
# 3. Sample API calls (auth, materials, chat)
# 4. Celery task execution
# 5. WebSocket connectivity
# 6. File uploads (chat attachments)
```

**Production Validation** (30 min):
```bash
scripts/disaster-recovery/verify-recovery.sh --full --smoke-test

# Full tests +
# Real-world user scenarios:
# 1. Student login → view materials
# 2. Teacher login → view students
# 3. Chat message exchange
# 4. Assignment submission
# 5. Payment flow (test mode)
# 6. Concurrent users (load test)
```

### Backup Verification

**Monthly Backup Test**:
```bash
#!/bin/bash
# 1st of each month:
# - Restore latest backup to staging
# - Run full verification
# - Document results

docker-compose -f docker-compose.staging.yml up -d postgres
scripts/disaster-recovery/restore-database.sh --type full --target staging
scripts/disaster-recovery/verify-recovery.sh --full --target staging
```

---

## RTO/RPO Analysis

### Service-Level Agreements

| Scenario | RTO | RPO | Automated | Notes |
|----------|-----|-----|-----------|-------|
| **Single service crash** | 5 min | 0 min | Yes (health check restart) | Container auto-restart |
| **Database failure (running)** | 15 min | 5 min | Yes (PITR with WAL) | Use latest WAL + backup |
| **Database failure (down)** | 20 min | 15 min | Yes (full restore) | Restore latest full backup |
| **Redis failure** | 5 min | 0 min | Partial (manual verify) | AOF or RDB restore |
| **Multi-service failure** | 30 min | 10 min | Yes (docker-compose up) | All services restart |
| **Datacenter failure** | 60 min | 15 min | Yes (failover script) | Secondary region ready |
| **Data corruption** | 45 min | 30 min | Manual (PITR required) | Restore to pre-corruption point |

### RTO Details by Scenario

#### RTO Breakdown for Database Failure

```
Scenario: Full PostgreSQL recovery
Total RTO: 20 minutes

1. Detect failure         : 1-2 min   (monitoring alert)
2. Prepare infrastructure : 3-5 min   (stop, remove volume)
3. Restore backup         : 10 min    (512MB restore)
4. Verify recovery        : 2-3 min   (health checks)
Total: ~20 minutes
```

#### RTO Breakdown for Datacenter Failure

```
Scenario: Full system failover to secondary
Total RTO: 60 minutes

1. Detect primary failure       : 1-2 min   (monitoring)
2. Prepare secondary infra      : 15 min    (terraform apply)
3. Download backups from S3     : 5-10 min  (512MB files)
4. Restore PostgreSQL           : 10-15 min (restore + verify)
5. Restore Redis               : 3-5 min   (snapshot)
6. Update application config   : 2-3 min   (env vars, restart)
7. Update DNS                  : 1-2 min   (Route 53)
8. Full system verification    : 5-10 min  (smoke tests)
Total: ~50-60 minutes
```

### RPO Details

#### RPO for PostgreSQL

```
Scenario: Database failure at 14:30
RPO Target: < 15 minutes

Backup Timeline:
- Last daily backup: 14:00 (30 min old) ❌
- WAL archiving: Every 5 minutes ✓
- Recovery: Restore 14:00 backup + WAL to 14:30 ✓

Actual RPO: 5 minutes (next WAL cycle)
```

#### RPO for Redis (Cache)

```
Scenario: Redis failure at 14:30
RPO Target: < 1 minute acceptable

Options:
1. Use latest AOF: < 1 sec loss
2. Use RDB snapshot: < 1 min loss (scheduled daily)
3. Start fresh: Acceptable (cache will repopulate)

Actual RPO: < 1 minute
```

---

## Operational Procedures

### Daily Operational Tasks

**Start of Day** (5 minutes):
```bash
# 1. Verify backup completion
./backup/database/monitor.sh check-last-backup

# 2. Check system health
curl http://localhost:8000/api/system/health/
curl http://localhost:8000/api/system/readiness/

# 3. Verify replication (if enabled)
docker-compose exec postgres psql -U postgres -d thebot_db \
  -c "SELECT slot_name, restart_lsn FROM pg_replication_slots;"
```

**Weekly** (30 minutes):
```bash
# 1. Test backup restoration (staging)
docker-compose -f docker-compose.staging.yml up -d postgres
scripts/disaster-recovery/restore-database.sh --type full --target staging
scripts/disaster-recovery/verify-recovery.sh --full --target staging

# 2. Review backup logs
tail -100 /backups/logs/backup_*.log | grep -E "ERROR|FAILED"

# 3. Check backup storage usage
du -sh /backups/*/
```

**Monthly** (1-2 hours):
```bash
# 1. Full disaster recovery drill
./scripts/disaster-recovery/failover.sh --simulate

# 2. Test failover procedures
# - Simulate primary down
# - Activate secondary
# - Run full verification
# - Return to normal

# 3. Review and update runbook
# - Document any issues found
# - Update contact information
# - Review RTO/RPO compliance
```

### Incident Response Workflow

**Automated Detection** (via monitoring):
```
Problem detected (e.g., health check fails)
    ↓
Alert sent (email, Slack, PagerDuty)
    ↓
Auto-recovery triggered (if applicable)
    ↓
Health check verifies recovery
    ↓
If failed: Escalate to on-call engineer
```

**Manual Response** (if auto-recovery fails):
```bash
# 1. Load incident runbook
cat /infrastructure/dr/dr-runbook.json | jq '.incidents[] | select(.type=="database_failure")'

# 2. Follow step-by-step procedure
scripts/disaster-recovery/failover.sh --incident database_failure

# 3. Verify recovery
scripts/disaster-recovery/verify-recovery.sh --full

# 4. Document incident
# - Time of failure
# - Root cause
# - Recovery time
# - Actions taken
# - Lessons learned
```

### Communication During Incident

**Immediate** (within 5 minutes):
- Alert on-call engineer
- Post incident channel notice
- Begin recovery procedure

**Ongoing** (every 15 minutes):
- Update status page
- Post progress update
- Adjust ETA if needed

**Resolution** (when recovered):
- Verify full system operational
- Update status page
- Post post-mortem notice

---

## Monitoring & Alerting

### Backup Monitoring

**Alerts** (sent to ops team):
- Backup failed: Within 30 minutes of scheduled time
- Backup oversized: > 20% increase from average
- Backup slow: > 2x normal duration
- Verification failed: Checksum mismatch
- Restore test failed: Staging restore unable to complete

**Dashboards** (in monitoring system):
```
Backup Health Dashboard:
├─ Last backup time (by type)
├─ Backup success rate (%)
├─ Storage usage (and trend)
├─ Restore test results
├─ WAL archiving status
└─ S3 sync status (if enabled)
```

### Service Health Monitoring

**Health Check Endpoints**:
- `GET /api/system/health/` - Service alive
- `GET /api/system/readiness/` - Ready for requests
- `GET /api/system/metrics/` - Performance metrics
- `GET /api/system/analytics/` - Business metrics

**Threshold-Based Alerts**:
- Backend response time > 500ms
- Database connections > 180/200 (90%)
- Redis memory > 460MB/512MB (90%)
- Celery task failure rate > 1%
- Queue depth > 10,000 tasks

### Capacity Monitoring

**Disk Usage**:
- Alert at 80% capacity
- Alert at 95% capacity
- Automatic cleanup of old WAL files (> 7 days)

**Memory Usage**:
- PostgreSQL: 256MB shared buffers (no alert needed, fixed)
- Redis: 512MB hard limit, evict LRU
- Backend: Per-container monitoring

**Network**:
- Monitor replication lag (if replica enabled)
- Monitor WebSocket connection count
- Monitor API request rate

---

## Advanced Topics

### Point-in-Time Recovery (PITR)

**How It Works**:
1. Full backup taken (e.g., 2025-12-27 01:00)
2. All write-ahead log (WAL) files archived
3. To recover to 2025-12-27 14:30:
   - Restore full backup (from 01:00)
   - Replay WAL files (01:00 → 14:30)
   - Stop before earliest WAL after 14:30

**Backup Timeline**:
```
Full Backup              WAL Files
(01:00)                 (01:00-14:30)
   ↓                        ↓
┌─────┐  ┌─────┬─────┬─────┬─────┐
│Full │→ │WAL1 │WAL2 │WAL3 │WAL4 │ → Recovery Point
│Dump │  │     │     │     │     │    (14:30)
└─────┘  └─────┴─────┴─────┴─────┘

Recovery to 14:30:
Restore dump + replay WAL1→WAL3 + stop before WAL4
```

**PostgreSQL Configuration**:
```
archive_mode = on
archive_command = 'test ! -f /wal-archive/%f && cp %p /wal-archive/%f'
wal_level = replica
max_wal_senders = 10
```

### High-Availability Setup (Optional)

**Master-Replica Replication**:
```
Primary (Master)              Secondary (Replica)
┌──────────────┐            ┌──────────────┐
│ PostgreSQL   │ WAL Stream │ PostgreSQL   │
│ (read+write) ├───────────→│ (read-only)  │
└──────────────┘            └──────────────┘
       ↓                            ↓
   (WAL files)              (continuous recovery)
       ↓
   Archived to /wal-archive/
```

**Failover Procedure**:
1. Primary fails
2. Replica promoted to primary: `pg_ctl promote`
3. Other replicas point to new primary
4. Application reconnected

### Distributed Backups (Multi-Region)

**Backup Replication**:
```
Local Backups             AWS S3 (Multi-region)
/backups/daily     ───→   s3://backup-bucket/daily/
/backups/weekly    ───→   s3://backup-bucket/weekly/
/backups/monthly   ───→   s3://backup-bucket/monthly/
/wal-archive/      ───→   s3://backup-bucket/wal-archive/
```

**S3 Configuration**:
- Versioning: Enabled (30-day retention)
- Cross-region replication: To secondary region
- Encryption: AES-256
- Lifecycle policies: Delete old versions after 30 days

---

## Emergency Contacts

**On-Call Engineer**: [PagerDuty URL]
**Incident Channel**: #incident (Slack)
**Status Page**: status.thebot.io

---

## Appendix: Command Reference

### Backup Commands
```bash
# Full backup
/backup/database/backup.sh full

# Weekly backup
/backup/database/backup.sh weekly

# Check last backup
/backup/database/monitor.sh check-last-backup

# List all backups
ls -lh /backups/*/backup_*.gz
```

### Recovery Commands
```bash
# Restore from latest
scripts/disaster-recovery/restore-database.sh --type full --from latest

# Restore from specific date
scripts/disaster-recovery/restore-database.sh --type full --from 20251226

# PITR restore
scripts/disaster-recovery/restore-database.sh --type pitr --until "2025-12-27 14:30:00"

# Verify recovery
scripts/disaster-recovery/verify-recovery.sh --full
```

### Monitoring Commands
```bash
# System health
curl http://localhost:8000/api/system/health/

# Database status
docker-compose exec postgres psql -U postgres -c "\list"

# Redis status
docker-compose exec redis redis-cli info server

# Backup status
cat /backups/.backup_status | jq
```

---

## Document History

| Date | Version | Author | Changes |
|------|---------|--------|---------|
| 2025-12-27 | 1.0.0 | DevOps Team | Initial comprehensive DR strategy |

---

**Last Updated**: December 27, 2025
**Next Review**: January 27, 2026
**Status**: Production Ready
