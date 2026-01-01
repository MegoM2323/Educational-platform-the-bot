# Disaster Recovery Procedures Runbook

**Version**: 1.0.0
**Last Updated**: December 27, 2025
**Severity**: CRITICAL
**RTO Target**: < 15 minutes
**RPO Target**: < 5 minutes

---

## Table of Contents

1. [Overview](#overview)
2. [RTO/RPO Definitions](#rtorpo-definitions)
3. [Recovery Scenarios](#recovery-scenarios)
4. [Pre-Disaster Preparation](#pre-disaster-preparation)
5. [Database Failover](#database-failover)
6. [Backup Restoration](#backup-restoration)
7. [Service Recovery](#service-recovery)
8. [Communication & Escalation](#communication--escalation)
9. [Testing & Validation](#testing--validation)
10. [Post-Recovery Steps](#post-recovery-steps)
11. [Checklists](#checklists)

---

## Overview

This runbook provides step-by-step procedures for recovering THE_BOT platform from various disaster scenarios. All procedures are designed to meet Recovery Time Objective (RTO) and Recovery Point Objective (RPO) targets.

### Supported Scenarios

| Scenario | Severity | RTO | RPO | Procedure |
|----------|----------|-----|-----|-----------|
| Primary DB failure | CRITICAL | 15 min | 5 min | Database Failover |
| Replica DB failure | HIGH | 30 min | N/A | Rebuild Replica |
| Data corruption | CRITICAL | 20 min | 5 min | Point-in-Time Restore |
| Service crash | HIGH | 5 min | 0 min | Auto-Restart |
| Datacenter failure | CRITICAL | 30 min | 5 min | Full Failover |
| Ransomware attack | CRITICAL | 2 hours | 1 hour | Complete Restore |

### Key Contacts

| Role | Name | Phone | Email | On-Call |
|------|------|-------|-------|---------|
| Database Admin | [NAME] | [PHONE] | [EMAIL] | Yes/No |
| DevOps Lead | [NAME] | [PHONE] | [EMAIL] | Yes/No |
| Infrastructure Lead | [NAME] | [PHONE] | [EMAIL] | Yes/No |
| CTO | [NAME] | [PHONE] | [EMAIL] | Yes/No |

---

## RTO/RPO Definitions

### Recovery Time Objective (RTO)

**Definition**: Maximum time allowed to restore system functionality after failure

**THE_BOT RTO Targets**:
- Database failover: **15 minutes**
- Service recovery: **5 minutes**
- Full system restore: **30 minutes**
- Data restoration: **30 minutes**

### Recovery Point Objective (RPO)

**Definition**: Maximum amount of data loss acceptable (time since last backup)

**THE_BOT RPO Targets**:
- Database: **5 minutes** (continuous streaming replication)
- Application data: **5 minutes** (via scheduled backups)
- Configuration: **24 hours** (versioned in Git)

### Current Infrastructure Status

- **Primary Database**: PostgreSQL 15 (production)
- **Replica Database**: PostgreSQL 15 (streaming replication)
- **Backup Strategy**:
  - Hourly full backups to S3
  - Point-in-time recovery (PITR) enabled
  - WAL archiving to S3
- **Failover Mechanism**: Automatic promotion via Patroni/etcd
- **Backup Retention**: 30 days

---

## Recovery Scenarios

### Scenario 1: Primary Database Failure (RTO: 15 min, RPO: 5 min)

**Triggers**:
- Primary database server unresponsive
- Database service crashed
- Connection timeout errors in application logs
- Health check failures for 2+ minutes

**Recovery Window**: 15 minutes from failure detection

**Procedure**: See [Database Failover](#database-failover) section

---

### Scenario 2: Data Corruption (RTO: 20 min, RPO: 5 min)

**Triggers**:
- Corrupted records detected
- Constraint violations
- Invalid data integrity checks
- Users reporting missing/incorrect data

**Recovery Window**: 20 minutes from corruption detection

**Procedure**: See [Point-in-Time Restore](#point-in-time-restore) section

---

### Scenario 3: Service Crash (RTO: 5 min, RPO: 0 min)

**Triggers**:
- Backend service crash
- Frontend service unavailable
- Container exit with non-zero code
- Health check failures

**Recovery Window**: 5 minutes from detection

**Procedure**: See [Service Recovery](#service-recovery) section

---

### Scenario 4: Datacenter Failure (RTO: 30 min, RPO: 5 min)

**Triggers**:
- Entire datacenter/region down
- Network partition
- Multiple simultaneous service failures
- Cannot reach infrastructure

**Recovery Window**: 30 minutes to switch regions

**Procedure**: See [Multi-Region Failover](#multi-region-failover) section

---

## Pre-Disaster Preparation

### 1. Regular Testing

**Monthly DR Drills** (Last run: [DATE])

```bash
# Run full DR test
./scripts/disaster-recovery/dr-test.sh --test all --dry-run

# Validate RTO compliance
./scripts/disaster-recovery/dr-test.sh --validate-rto

# Validate RPO compliance
./scripts/disaster-recovery/dr-test.sh --validate-rpo
```

**Expected Duration**: 30-45 minutes
**Success Criteria**:
- ✓ All tests pass
- ✓ RTO < 15 minutes
- ✓ RPO < 5 minutes
- ✓ Data integrity verified

### 2. Backup Validation

**Weekly Backup Verification** (Schedule: Every Monday)

```bash
# Verify latest backup integrity
./scripts/disaster-recovery/restore-test.sh --verify-backup

# Test restoration without data loss
./scripts/disaster-recovery/restore-test.sh --dry-run
```

**Success Criteria**:
- ✓ Backup checksum valid
- ✓ Backup file accessible
- ✓ Backup age < 24 hours
- ✓ S3 connectivity verified

### 3. Documentation Updates

**Quarterly Runbook Review** (Schedule: Every Q)

- [ ] Update contact information
- [ ] Review RTO/RPO targets
- [ ] Update server addresses/IPs
- [ ] Verify backup retention policy
- [ ] Check S3 bucket configuration
- [ ] Review failover mechanisms
- [ ] Update DNS failover procedures

### 4. Infrastructure Readiness

**Pre-Disaster Checklist**:

- [ ] Replica database is configured and syncing
- [ ] Backups are scheduled and running
- [ ] S3 bucket has sufficient space
- [ ] WAL archiving is enabled
- [ ] Monitoring alerts are configured
- [ ] Health checks are active
- [ ] Failover scripts are deployed
- [ ] Team has access to runbook
- [ ] VPN/SSH access tested
- [ ] Escalation procedures documented

---

## Database Failover

### Step-by-Step Procedure (15 minutes target)

#### Phase 1: Detect Failure (1-2 minutes)

**1.1 Verify Primary Failure**

```bash
# SSH to monitoring server
ssh monitoring@prod-monitor.example.com

# Check primary database status
curl -s http://primary-db.example.com:5432/ 2>&1 | head -5

# Expected output: Connection refused or timeout
```

**1.2 Confirm in Monitoring Dashboard**

- Open [Monitoring URL](https://monitoring.example.com)
- Check PostgreSQL dashboard
- Verify "Primary: DOWN" status
- Note: failure start time from metrics

**1.3 Check Application Error Logs**

```bash
# View recent application logs
kubectl logs -n production deployment/backend --tail=50 | grep -i "database\|connection"
# Or for Docker Compose:
docker-compose -f docker-compose.prod.yml logs backend | tail -50
```

**Success Indicator**: Multiple sources confirm primary is down

**⏱️ Duration: 1-2 minutes**

---

#### Phase 2: Verify Replica is Ready (1-2 minutes)

**2.1 Check Replica Database Status**

```bash
# SSH to replica server
ssh postgres@replica-db.example.com

# Check replica status
sudo su - postgres
pg_ctl status -D /var/lib/postgresql/15/main/

# Expected: "pg_ctl: server is running"
```

**2.2 Verify Replication State**

```bash
# Check if replica is in recovery mode
psql -U postgres -c "SELECT pg_is_in_recovery();"

# Expected output: t (true) - replica is still in recovery

# Check last received WAL
psql -U postgres -c "SELECT now(), pg_last_xact_replay_timestamp();"

# Expected: timestamps are close (< 1 second apart)
```

**2.3 Check Standby Lag**

```bash
# Monitor WAL lag
watch -n 1 'psql -U postgres -c "SELECT
    EXTRACT(EPOCH FROM (now() - pg_last_xact_replay_timestamp())) as replication_lag_seconds;"'

# Expected: < 5 seconds lag
```

**Success Indicator**:
- ✓ Replica is running
- ✓ In recovery mode
- ✓ Lag < 5 seconds

**⏱️ Duration: 1-2 minutes**

---

#### Phase 3: Promote Replica (2-3 minutes)

**3.1 Execute Promotion Command**

```bash
# SSH to replica server
ssh postgres@replica-db.example.com

# Become postgres user
sudo su - postgres

# Promote replica to primary
pg_ctl promote -D /var/lib/postgresql/15/main/

# Output: "waiting for server to promote... done"
```

**3.2 Verify Promotion Success**

```bash
# Check new primary status
psql -U postgres -c "SELECT pg_is_in_recovery();"

# Expected output: f (false) - no longer in recovery

# Check WAL archiving is active
psql -U postgres -c "SHOW wal_level;"

# Expected: replica or higher
```

**3.3 Verify Database Accessibility**

```bash
# Test connections from application server
psql -h replica-db.example.com -U postgres -c "SELECT version();" | head -3

# Expected: PostgreSQL version info
```

**Success Indicator**:
- ✓ Promotion command succeeded
- ✓ Not in recovery mode
- ✓ Database accepts connections

**⏱️ Duration: 2-3 minutes**

---

#### Phase 4: Update Application Connections (1-2 minutes)

**4.1 Update Connection String**

```bash
# Edit environment configuration
# Option 1: If using load balancer (preferred)
# Update DNS record: primary-db.example.com -> replica-db IP

# Option 2: Update application config directly
kubectl set env deployment/backend -n production \
    DATABASE_HOST=replica-db.example.com

# Or for Docker Compose:
# Edit .env or docker-compose.prod.yml
# DATABASE_URL=postgresql://user:pass@replica-db:5432/thebot

# Verify change:
echo $DATABASE_URL
```

**4.2 Restart Application Services**

```bash
# Kubernetes
kubectl rollout restart deployment/backend -n production
kubectl rollout status deployment/backend -n production

# Or Docker Compose
docker-compose -f docker-compose.prod.yml restart backend
docker-compose -f docker-compose.prod.yml restart frontend
```

**4.3 Verify Connections Established**

```bash
# Check application logs
kubectl logs -n production deployment/backend --tail=20 | grep -i "connected\|database"

# Expected: "Successfully connected to database" or similar

# Test API health
curl -s http://api.example.com/api/system/health/ | jq '.database.status'

# Expected: "healthy" or "connected"
```

**Success Indicator**:
- ✓ Connection string updated
- ✓ Services restarted
- ✓ API responds with 200
- ✓ Health check passes

**⏱️ Duration: 1-2 minutes**

---

#### Phase 5: Run Validation Tests (2-3 minutes)

**5.1 Test Database Operations**

```bash
# Test read operations
psql -h replica-db.example.com -U thebot_user -d thebot -c \
    "SELECT COUNT(*) FROM accounts_user;"

# Expected: returns row count (> 0)
```

**5.2 Test Write Operations**

```bash
# Test basic insert (optional, can skip if read-only acceptable)
psql -h replica-db.example.com -U thebot_user -d thebot -c \
    "INSERT INTO audit_log (action, timestamp) VALUES ('failover_test', now());"

# Expected: "INSERT 0 1"

# Verify write
psql -h replica-db.example.com -U thebot_user -d thebot -c \
    "SELECT COUNT(*) FROM audit_log WHERE action='failover_test';"
```

**5.3 Run Automated Tests**

```bash
# Run DR test suite
./scripts/disaster-recovery/failover-test.sh

# Expected: All tests pass, RTO < 15 minutes
```

**Success Indicator**:
- ✓ Data queries successful
- ✓ Writes are working
- ✓ DR tests pass

**⏱️ Duration: 2-3 minutes**

---

### Failover Timeline Summary

| Phase | Duration | Cumulative | Status |
|-------|----------|-----------|--------|
| Detection | 1-2 min | 1-2 min | ⏳ |
| Verify Replica | 1-2 min | 2-4 min | ⏳ |
| Promote | 2-3 min | 4-7 min | ⏳ |
| Update Connections | 1-2 min | 5-9 min | ⏳ |
| Validation | 2-3 min | 7-12 min | ⏳ |
| **Total** | **7-12 min** | **7-12 min** | ✅ |

**RTO Status**: ✅ WITHIN TARGET (target: 15 min, actual: 7-12 min)

---

## Backup Restoration

### Point-in-Time Restore (PITR)

**Use Case**: Data corruption, accidental deletion, malicious changes

**RTO**: 20 minutes
**RPO**: 5 minutes (time since last WAL segment)

#### Step 1: Detect Corruption (1-2 minutes)

```bash
# Check application error logs
docker-compose logs backend | grep -i "integrity\|constraint\|corrupt"

# Query suspicious data
psql -U postgres thebot -c \
    "SELECT * FROM accounts_user WHERE created_at > '2024-01-27' LIMIT 5;"

# Check for NULL anomalies
psql -U postgres thebot -c \
    "SELECT COUNT(*) FROM accounts_user WHERE email IS NULL;"
```

#### Step 2: Determine Recovery Point (2-3 minutes)

```bash
# List available WAL segments
aws s3api list-objects-v2 \
    --bucket thebot-backups \
    --prefix wal-archives/ \
    --query 'Contents[?LastModified>=`2024-01-27T14:00:00Z`].Key' \
    | jq -r '.[]'

# Find closest valid backup
aws s3api list-objects-v2 \
    --bucket thebot-backups \
    --prefix "backups/full/" \
    --query 'sort_by(Contents, &LastModified)[-1]'

# Example: backup from 14:00, want restore to 14:03
```

#### Step 3: Prepare Recovery Database (3-5 minutes)

```bash
# Create recovery database
psql -U postgres -c "CREATE DATABASE thebot_recovery;"

# Download full backup
aws s3 cp s3://thebot-backups/backups/full/backup_2024-01-27_1400.sql \
    /tmp/backup_recovery.sql

# Restore full backup
psql -U postgres thebot_recovery < /tmp/backup_recovery.sql
```

#### Step 4: Recover to Point in Time (5-7 minutes)

```bash
# Download WAL segments from 14:00 to 14:03
aws s3 sync \
    s3://thebot-backups/wal-archives/ \
    /tmp/wal-recovery/ \
    --exclude "*" \
    --include "2024-01-27*140*"

# Configure recovery target
cat >> /tmp/recovery.conf << EOF
restore_command = 'cp /tmp/wal-recovery/%f %p'
recovery_target_time = '2024-01-27 14:03:00'
recovery_target_inclusive = true
pause_at_recovery_target = true
EOF

# Apply WAL recovery
pg_wal_replay /tmp/recovery.conf
```

#### Step 5: Validate Recovery (2-3 minutes)

```bash
# Check data at recovery point
psql -U postgres thebot_recovery -c \
    "SELECT * FROM accounts_user WHERE created_at > '2024-01-27' LIMIT 5;"

# Verify no corruption
psql -U postgres thebot_recovery -c \
    "SELECT COUNT(*) FROM accounts_user WHERE email IS NULL;"

# Compare record counts
psql -U postgres -d thebot_recovery -c \
    "SELECT COUNT(*) FROM accounts_user;"
```

#### Step 6: Promote Recovery Database (2-3 minutes)

```bash
# Rename corrupted database
psql -U postgres -c "ALTER DATABASE thebot RENAME TO thebot_corrupted;"

# Rename recovery database
psql -U postgres -c "ALTER DATABASE thebot_recovery RENAME TO thebot;"

# Restart application
docker-compose -f docker-compose.prod.yml restart backend
```

#### Step 7: Verify and Cleanup (1-2 minutes)

```bash
# Test application
curl -s http://localhost:8000/api/system/health/ | jq '.database.status'

# Expected: "healthy"

# Cleanup
psql -U postgres -c "DROP DATABASE IF EXISTS thebot_corrupted;"
rm -f /tmp/backup_recovery.sql /tmp/recovery.conf
rm -rf /tmp/wal-recovery/
```

---

## Service Recovery

### Automatic Service Restart

**Use Case**: Service crash, unexpected termination
**RTO**: 5 minutes
**RPO**: 0 minutes (no data loss)

#### For Kubernetes

```bash
# Kubernetes automatically restarts failed pods
# Monitor restart status
kubectl get pods -n production -w

# Check restart count
kubectl describe pod <pod-name> -n production | grep Restart

# View restart logs
kubectl logs <pod-name> --previous -n production | tail -50

# Manual restart if needed
kubectl rollout restart deployment/backend -n production
kubectl rollout status deployment/backend -n production
```

#### For Docker Compose

```bash
# Check container status
docker-compose -f docker-compose.prod.yml ps

# Restart failed service
docker-compose -f docker-compose.prod.yml restart backend

# Verify restart
docker-compose -f docker-compose.prod.yml logs -f backend | grep "Starting\|Started"

# Full reset if needed
docker-compose -f docker-compose.prod.yml up -d backend
```

#### Verification

```bash
# Check health endpoint
curl -s http://localhost:8000/api/system/health/ | jq '.overall_status'

# Expected: "healthy"

# Check application logs
docker-compose logs backend | tail -20

# Monitor for errors
docker-compose logs -f backend | grep -i error
```

---

## Communication & Escalation

### During Disaster

**Immediate Actions (First 5 minutes)**:

1. **Declare Incident**
   ```bash
   # Send alert to team
   # Email: ops@example.com
   # Subject: [INCIDENT] Database failure - PRIMARY DATABASE DOWN
   ```

2. **Activate War Room**
   - Launch video conference: [ZOOM LINK]
   - Invite: Database Admin, DevOps Lead, CTO
   - Document incident ID and start time

3. **Notify Stakeholders**
   - Product team
   - Customer support
   - Executive team

**Ongoing Communication**:
- Update war room every 2-3 minutes
- Post status to Slack #incidents channel
- Prepare customer communication template

**Status Examples**:

```
[12:00 UTC] PRIMARY DATABASE DOWN
- Detection: 12:00 UTC
- Status: Promoting replica to primary
- ETA Recovery: 12:10 UTC
- Impact: Platform unavailable

[12:05 UTC] REPLICA PROMOTION IN PROGRESS
- Replica promotion started: 12:03 UTC
- Expected promotion complete: 12:06 UTC
- Application restart in progress
- ETA: 12:10 UTC

[12:10 UTC] RECOVERY COMPLETE
- Failover completed: 12:10 UTC
- Total downtime: 10 minutes
- Services restored: 100%
- Data integrity: Verified
- Status: RESOLVED
```

### Post-Recovery Communication

```
# Customer notification template
Subject: Service Recovery Complete - Incident Post-Mortem

We experienced a database failure on January 27 from 12:00-12:10 UTC.
Service has been fully restored.

Impact:
- Duration: 10 minutes
- Services affected: API, Web platform
- Data integrity: No loss verified

Recovery:
- Primary database failed
- Replica automatically promoted
- All services restarted and validated
- Full status: Healthy

Next Steps:
- Post-mortem analysis underway
- Report will be published within 24 hours
- Infrastructure improvements planned

Thank you for your patience.
```

---

## Testing & Validation

### Running DR Tests

#### Test 1: Full DR Simulation (Monthly)

```bash
cd /home/mego/Python\ Projects/THE_BOT_platform

# Run complete test with dry-run first
./scripts/disaster-recovery/dr-test.sh --test all --dry-run --metrics

# Review dry-run output
cat logs/dr-tests/dr-test_*.log | tail -50

# Run actual test
./scripts/disaster-recovery/dr-test.sh --test all --metrics

# Check results
jq '.summary' metrics/dr-metrics_*.json
```

**Expected Results**:
- ✅ All tests pass
- ✅ RTO < 900 seconds (15 min)
- ✅ RPO < 300 seconds (5 min)
- ✅ Data integrity verified

#### Test 2: Failover Test Only

```bash
# Test database failover in isolation
./scripts/disaster-recovery/failover-test.sh --dry-run

# Run actual failover test
./scripts/disaster-recovery/failover-test.sh

# Check failover metrics
jq '.metrics' metrics/failover-metrics_*.json
```

**Validation Criteria**:
- Promotion time < 180 seconds
- Connection failover < 60 seconds
- Health checks < 300 seconds
- Total RTO < 900 seconds

#### Test 3: Restore Test Only

```bash
# Verify backup restoration
./scripts/disaster-recovery/restore-test.sh --verify-backup

# Run full restore test
./scripts/disaster-recovery/restore-test.sh --dry-run

# Execute actual restore
./scripts/disaster-recovery/restore-test.sh

# Check restore metrics
jq '.metrics' metrics/restore-metrics_*.json
```

**Validation Criteria**:
- Backup integrity verified
- Download time < 300 seconds
- Restore time < 600 seconds
- Data integrity verified
- Total RPO < 300 seconds

#### Test 4: RTO/RPO Compliance Check

```bash
# Validate RTO compliance
./scripts/disaster-recovery/dr-test.sh --validate-rto

# Output: COMPLIANT or FAILED

# Validate RPO compliance
./scripts/disaster-recovery/dr-test.sh --validate-rpo

# Output: COMPLIANT or FAILED
```

### Test Schedule

| Test | Frequency | Duration | Owner |
|------|-----------|----------|-------|
| Full DR simulation | Monthly | 1 hour | DevOps |
| Failover test | Bi-weekly | 30 min | DBA |
| Restore test | Weekly | 30 min | DBA |
| RTO/RPO validation | Monthly | 15 min | DevOps |
| Backup verification | Weekly | 15 min | DBA |
| Runbook review | Quarterly | 1 hour | DevOps Lead |

---

## Post-Recovery Steps

### Immediate Recovery Actions (0-30 minutes)

1. **Verify System Health**
   ```bash
   # Run comprehensive health check
   curl -s http://api.example.com/api/system/health/ | jq .

   # Expected: All components "healthy"
   ```

2. **Check Monitoring**
   - Verify all alerting systems active
   - Check dashboard shows green status
   - Confirm no new alerts triggered

3. **Database Verification**
   ```bash
   # Connect to new primary
   psql -h primary-db.example.com -U postgres -c \
       "SELECT COUNT(*) FROM accounts_user,
               COUNT(*) FROM materials_material,
               COUNT(*) FROM chat_message;"
   ```

4. **Application Testing**
   - Manual smoke test of key features
   - User login test
   - Data retrieval test
   - Data write test

5. **Notify Stakeholders**
   - Send "RESOLVED" notification
   - Include recovery time metrics
   - Confirm data integrity

### Short-Term Actions (30-120 minutes)

1. **Rebuild Failed Primary**
   ```bash
   # SSH to old primary
   ssh postgres@primary-db.example.com

   # Reset replica configuration
   sudo systemctl stop postgresql
   sudo rm -rf /var/lib/postgresql/15/main/*

   # Set up as new replica
   pg_basebackup -h replica-db.example.com -U postgres \
       -D /var/lib/postgresql/15/main/ -Fp -Xs -P

   # Start as standby
   sudo systemctl start postgresql
   ```

2. **Verify Replication**
   ```bash
   # On new primary
   psql -U postgres -c "SELECT * FROM pg_stat_replication;"

   # Expected: Shows new replica in replication state
   ```

3. **Update DNS Records** (if manual)
   ```bash
   # Point failover DNS back to original primary
   # (or leave on current if no changes needed)
   ```

4. **Run Diagnostics**
   ```bash
   # Analyze what caused failure
   grep -i "error\|fail" /var/log/postgresql/postgresql.log | tail -50
   ```

### Long-Term Actions (24-48 hours)

1. **Root Cause Analysis**
   - Review all logs
   - Identify failure trigger
   - Document findings

2. **Infrastructure Updates**
   - Apply fixes/patches
   - Update configurations
   - Improve monitoring thresholds

3. **Team Debrief**
   - Conduct post-mortem meeting
   - Discuss what went well
   - Identify improvement areas
   - Plan preventive measures

4. **Documentation Updates**
   - Update runbook with lessons learned
   - Improve automation
   - Update contact information
   - Refresh team training

5. **Announce Resolution**
   - Publish full incident report
   - Share lessons learned
   - Announce infrastructure improvements

---

## Checklists

### Pre-Disaster Checklist

#### Monthly Verification (First Monday of month)

- [ ] Run full DR test: `./dr-test.sh --test all --dry-run`
- [ ] Validate RTO: `./dr-test.sh --validate-rto`
- [ ] Validate RPO: `./dr-test.sh --validate-rpo`
- [ ] Review contact list - all numbers current?
- [ ] Verify backup S3 bucket accessible
- [ ] Check backup retention policy
- [ ] Review monitoring alerts configured
- [ ] Verify health checks responding

#### Weekly Tasks

- [ ] Test backup restoration: `./restore-test.sh --verify-backup`
- [ ] Check replication lag < 5 seconds
- [ ] Review error logs for warnings
- [ ] Verify backup jobs completing
- [ ] Check disk space on backup storage
- [ ] Monitor PostgreSQL logs

#### Quarterly Tasks

- [ ] Update runbook with current information
- [ ] Verify server addresses/IPs current
- [ ] Review and update recovery procedures
- [ ] Test failover scripts deploy correctly
- [ ] Review team training material
- [ ] Audit backup encryption status

---

### Active Disaster Checklist

#### Phase 1: Detection (First 2 minutes)

- [ ] Confirm primary database is actually down
- [ ] Check application error logs
- [ ] Verify monitoring dashboard shows failure
- [ ] Note exact failure start time

#### Phase 2: Preparation (Minutes 2-4)

- [ ] Declare incident to team
- [ ] Activate war room/video conference
- [ ] Notify stakeholders
- [ ] Verify replica is ready
- [ ] Check replica replication lag

#### Phase 3: Promotion (Minutes 4-7)

- [ ] Execute replica promotion: `pg_ctl promote`
- [ ] Verify promotion successful
- [ ] Update connection strings/DNS
- [ ] Restart application services

#### Phase 4: Validation (Minutes 7-12)

- [ ] Confirm API responding
- [ ] Run health checks
- [ ] Verify data accessibility
- [ ] Run DR test suite
- [ ] Validate RTO < 15 minutes

#### Phase 5: Communication (Minutes 12+)

- [ ] Notify all stakeholders recovery complete
- [ ] Provide recovery time metrics
- [ ] Explain what happened
- [ ] Schedule post-mortem

---

### Post-Recovery Checklist

#### Immediate (0-30 minutes)

- [ ] Verify all systems healthy
- [ ] Confirm data integrity
- [ ] Run smoke tests on key features
- [ ] Notify customer support
- [ ] Update status page

#### Short-Term (30 minutes - 2 hours)

- [ ] Rebuild failed primary server
- [ ] Re-establish replica replication
- [ ] Verify replication working
- [ ] Analyze failure root cause
- [ ] Update documentation

#### Long-Term (24-48 hours)

- [ ] Conduct post-mortem meeting
- [ ] Complete root cause analysis
- [ ] Plan infrastructure improvements
- [ ] Update runbook
- [ ] Publish incident report

---

## Additional Resources

### Tools and Scripts

```bash
# DR Testing Scripts
./scripts/disaster-recovery/dr-test.sh           # Full DR test suite
./scripts/disaster-recovery/failover-test.sh     # Database failover test
./scripts/disaster-recovery/restore-test.sh      # Backup restore test

# Health Check
curl http://api.example.com/api/system/health/    # Application health
curl http://api.example.com/api/system/readiness/ # Readiness check
curl http://api.example.com/api/system/metrics/   # System metrics

# Database Access
psql -h <host> -U postgres -d thebot             # PostgreSQL CLI
```

### Reference Documentation

- [Database Configuration](../DATABASE_CONFIG.md)
- [Backup Procedures](../BACKUP_PROCEDURES.md)
- [Monitoring Setup](../MONITORING.md)
- [Deployment Guide](../DEPLOYMENT.md)

### External Resources

- PostgreSQL Documentation: https://www.postgresql.org/docs/15/
- Patroni Documentation: https://patroni.readthedocs.io/
- AWS S3 Documentation: https://docs.aws.amazon.com/s3/
- Recovery Concepts: https://www.postgresql.org/docs/15/warm-standby.html

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0.0 | 2025-12-27 | DevOps Team | Initial version |
| | | | - Database failover procedures |
| | | | - Point-in-time restore |
| | | | - Service recovery |
| | | | - RTO/RPO validation |
| | | | - Testing framework |

---

## Document Control

**Document Type**: Operational Runbook
**Classification**: INTERNAL
**Distribution**: DevOps, Database, Infrastructure Teams
**Last Review**: 2025-12-27
**Next Review**: 2026-03-27 (quarterly)
**Owner**: DevOps Lead
**Approved By**: CTO

---

## Acknowledgments

This runbook was created based on industry best practices and THE_BOT platform's specific infrastructure and RTO/RPO targets. Regular testing and team training are essential for successful disaster recovery.

For questions or improvements, contact the DevOps team.
