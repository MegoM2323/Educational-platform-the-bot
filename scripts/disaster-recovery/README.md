# Disaster Recovery Testing Framework

Comprehensive disaster recovery testing and validation framework for THE_BOT platform with automated RTO/RPO compliance monitoring.

**Version**: 1.0.0
**Status**: Production Ready
**Last Updated**: December 27, 2025

## Overview

This directory contains complete disaster recovery infrastructure:

- **Automated Testing**: Complete DR test suites for failover, backup restoration, and service recovery
- **RTO/RPO Validation**: Automated compliance checking against targets (RTO < 15 min, RPO < 5 min)
- **Dry-Run Mode**: Safe testing without affecting production
- **Comprehensive Metrics**: Detailed timing and performance metrics collection
- **Report Generation**: JSON and HTML reports for analysis and compliance documentation
- **Runbook Support**: Step-by-step procedures for manual recovery if needed

**Key Metrics**:
- RTO (Recovery Time Objective): **< 15 minutes** (900 seconds)
- RPO (Recovery Point Objective): **< 5 minutes** (300 seconds)

## Quick Start

### 1. Verify Prerequisites

```bash
# Check all required tools are installed
./dr-test.sh --help

# System requirements:
# - Docker & Docker Compose
# - PostgreSQL client tools (psql)
# - AWS CLI (for S3 operations)
# - jq (for JSON processing)
```

### 2. Run Quick Sanity Check

```bash
# Fast 5-minute sanity check
./integrated-dr-test.sh --quick

# Output shows:
# ✓ Services running
# ✓ Database accessible
# ✓ API healthy
# ✓ Backups available
```

### 3. Run Full DR Test (First Time with Dry-Run)

```bash
# Dry-run to verify scripts work correctly
./integrated-dr-test.sh --full --dry-run --full-report

# Expected: All operations logged, no production impact
```

### 4. Run Actual DR Test

```bash
# Full test with reporting (10-15 minutes)
./integrated-dr-test.sh --full --full-report

# Monitor progress:
tail -f logs/dr-integration-tests/integrated-test_*.log
```

### 5. Validate Compliance

```bash
# Check RTO/RPO compliance
./integrated-dr-test.sh --validate

# Output shows:
# ✓ RTO COMPLIANT: 450s < 900s
# ✓ RPO COMPLIANT: 280s < 300s
```

### Emergency Recovery Procedures

For step-by-step manual procedures, see:
- [DR_PROCEDURES.md](../../docs/runbooks/DR_PROCEDURES.md) - Complete runbook

## Scripts

### 1. `dr-test.sh` - Master Test Suite

Comprehensive DR testing with multiple test scenarios.

**Usage**:
```bash
./dr-test.sh --test all [--dry-run] [--metrics]
./dr-test.sh --test failover [--dry-run]
./dr-test.sh --test restore [--dry-run]
./dr-test.sh --test recovery [--dry-run]
./dr-test.sh --validate-rto
./dr-test.sh --validate-rpo
```

**Examples**:
```bash
# Test all components with dry-run
./dr-test.sh --test all --dry-run --metrics

# Test failover only
./dr-test.sh --test failover --metrics

# Validate RTO compliance
./dr-test.sh --validate-rto
```

**Output**:
- Log: `logs/dr-tests/dr-test_YYYYMMDD_HHMMSS.log`
- Metrics: `metrics/dr-metrics_YYYYMMDD_HHMMSS.json`

---

### 2. `failover-test.sh` - Database Failover Testing

Tests automated failover from primary to replica database.

**Usage**:
```bash
./failover-test.sh [--dry-run] [--timeout 900]
```

**What It Tests**:
1. Primary database failure simulation
2. Replica promotion (< 3 minutes target)
3. Connection failover (< 1 minute target)
4. Health checks (< 5 minutes target)
5. Data consistency verification
6. Full RTO validation (< 15 minutes target)

**Example**:
```bash
# Test with dry-run first
./failover-test.sh --dry-run

# Run actual test
./failover-test.sh
```

**Output**:
- Log: `logs/failover-tests/failover-test_YYYYMMDD_HHMMSS.log`
- Metrics: `metrics/failover-metrics_YYYYMMDD_HHMMSS.json`

---

### 3. `restore-test.sh` - Backup Restoration Testing

Tests backup restoration from S3 and verifies data integrity.

**Usage**:
```bash
./restore-test.sh [--dry-run] [--verify]
./restore-test.sh --verify-backup
./restore-test.sh --full-restore
```

**What It Tests**:
1. Backup discovery and validation
2. Backup integrity verification (checksums)
3. Download from S3 (if applicable)
4. Database restoration from backup
5. Table structure verification
6. Data integrity checks
7. Full RPO validation (< 5 minutes target)

**Example**:
```bash
# Verify backup integrity only
./restore-test.sh --verify-backup

# Test full restore (with dry-run)
./restore-test.sh --dry-run

# Run actual restoration test
./restore-test.sh
```

**Output**:
- Log: `logs/restore-tests/restore-test_YYYYMMDD_HHMMSS.log`
- Metrics: `metrics/restore-metrics_YYYYMMDD_HHMMSS.json`

---

### 4. `integrated-dr-test.sh` - Orchestrated Testing

Coordinates all DR tests with reporting and compliance validation.

**Usage**:
```bash
./integrated-dr-test.sh [--quick] [--full] [--dry-run] [--full-report]
./integrated-dr-test.sh --failover
./integrated-dr-test.sh --restore
./integrated-dr-test.sh --validate
```

**Examples**:
```bash
# Quick sanity check (5 minutes)
./integrated-dr-test.sh --quick

# Full test with HTML report (15 minutes)
./integrated-dr-test.sh --full --full-report

# Dry-run without affecting production
./integrated-dr-test.sh --full --dry-run --full-report

# Validate compliance only
./integrated-dr-test.sh --validate
```

**Output**:
- Integration Log: `logs/dr-integration-tests/integrated-test_YYYYMMDD_HHMMSS.log`
- JSON Report: `metrics/dr-reports/dr-report_YYYYMMDD_HHMMSS.json`
- HTML Summary: `metrics/dr-reports/dr-summary_YYYYMMDD_HHMMSS.html`

## Backup Structure

### Location
```
/home/mego/Python Projects/THE_BOT_platform/backups/
├── daily/                  # Daily backups (7 kept)
│   ├── backup_20251227_010000.dump.gz
│   └── backup_20251227_010000.metadata
├── weekly/                 # Weekly backups (4 kept)
├── monthly/                # Monthly backups (12 kept)
├── wal-archive/           # WAL files for PITR (7 days)
├── logs/                  # Backup/restore logs
└── pre-restore-*/         # Pre-restore backups
```

### File Naming
- **PostgreSQL**: `backup_YYYYMMDD_HHMMSS.dump.gz`
- **Redis**: `redis_aof_YYYYMMDD_HHMMSS.bak` or `redis_rdb_YYYYMMDD_HHMMSS.rdb`
- **Metadata**: `.metadata` files with JSON info

### Metadata Format
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
  "restorability": "VERIFIED"
}
```

## Runbook

The JSON runbook (`infrastructure/dr/dr-runbook.json`) contains detailed step-by-step procedures for each incident type.

### View Specific Incident
```bash
# View database failure procedure
cat ../../infrastructure/dr/dr-runbook.json | jq '.incidents[] | select(.id=="INC-003")'

# View escalation contacts
cat ../../infrastructure/dr/dr-runbook.json | jq '.escalation_matrix'

# View backup retention policy
cat ../../infrastructure/dr/dr-runbook.json | jq '.backup_retention_policy'
```

### Incident Types in Runbook

1. **INC-001**: Backend Service Failure (RTO: 5 min)
2. **INC-002**: Database Failure - Running (RTO: 30 min)
3. **INC-003**: Database Failure - Down (RTO: 20 min)
4. **INC-004**: Redis Failure (RTO: 5 min)
5. **INC-005**: Datacenter Failure (RTO: 60 min)
6. **INC-006**: Partial Data Corruption (RTO: 45 min)

## Common Operations

### Daily Operations
```bash
# Check last backup
cat /backups/.backup_status | jq

# View backup logs
tail -50 /backups/logs/backup_*.log

# Check system health
./verify-recovery.sh --quick
```

### Weekly Operations
```bash
# Test backup restoration (to staging)
./restore-database.sh --type full --from latest --target staging

# Run full verification
./verify-recovery.sh --full

# Review backup logs for errors
grep -E "ERROR|FAILED" /backups/logs/backup_*.log
```

### Monthly Operations
```bash
# Run DR drill (simulation)
./failover.sh --simulate

# Run full smoke tests
./verify-recovery.sh --smoke-test

# Review and update runbook
# Edit infrastructure/dr/dr-runbook.json

# Schedule postmortem meeting if issues found
```

## Environment Variables

### Database
```bash
DB_HOST=localhost              # PostgreSQL host
DB_PORT=5432                   # PostgreSQL port
DB_USER=postgres               # PostgreSQL user
DB_PASSWORD=postgres           # PostgreSQL password
DB_NAME=thebot_db             # Database name
```

### Redis
```bash
REDIS_HOST=localhost           # Redis host
REDIS_PORT=6379               # Redis port
REDIS_PASSWORD=redis          # Redis password
```

### Backup
```bash
BACKUP_DIR=/backups           # Backup directory
SKIP_VERIFICATION=false       # Skip backup integrity checks
```

### Notifications
```bash
NOTIFICATION_EMAIL=ops@example.com
SLACK_WEBHOOK_URL=https://...
```

### AWS S3 (for datacenter failure)
```bash
AWS_REGION=us-west-2
S3_BACKUP_BUCKET=backup-bucket
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
```

## Logs

All operations create detailed logs:

```bash
# Failover logs
/backups/logs/failover_YYYYMMDD_HHMMSS.log

# Database restore logs
/backups/logs/restore_YYYYMMDD_HHMMSS.log

# Verification logs
/backups/logs/verify_YYYYMMDD_HHMMSS.log

# View latest log
tail -100 /backups/logs/failover_*.log

# Search for errors
grep ERROR /backups/logs/*.log
```

## Testing

### Run Simulation (No Changes)
```bash
# Simulate database failover
SIMULATE_MODE=true ./failover.sh --incident database_failure

# All operations will be logged but not executed
```

### Monthly Backup Test
```bash
# First of month:
# 1. Restore latest backup to staging
./restore-database.sh --type full --from latest --target staging

# 2. Run full verification
./verify-recovery.sh --full --target staging

# 3. Document results
# Results saved to /backups/logs/verify_*.log
```

### DR Drill (Quarterly)
```bash
# Simulate complete failover
./failover.sh --simulate

# Review procedures and timing
# Identify any issues
# Update runbook if needed
```

## Troubleshooting

### Backup Not Found
```bash
# Check available backups
find /backups -name "backup_*.dump.gz" -ls

# Check backup directory permissions
ls -la /backups/

# List by date
ls -la /backups/daily/ | sort -k6,7
```

### Restore Fails: "Backup file corrupted"
```bash
# Verify backup integrity
gzip -t /backups/daily/backup_20251227_010000.dump.gz

# Check file size
ls -lh /backups/daily/backup_20251227_010000.dump.gz

# Try restore with skip-verify
./restore-database.sh --type full --from latest --skip-verify
```

### Database won't start after restore
```bash
# Check PostgreSQL logs
docker logs thebot-postgres | tail -50

# Check disk space
df -h /var/lib/docker/volumes/

# Verify database file permissions
docker exec thebot-postgres ls -la /var/lib/postgresql/data/
```

### Redis restore fails: "AOF corrupted"
```bash
# Check Redis logs
docker logs thebot-redis

# Try RDB restore instead
./restore-redis.sh --type rdb --from latest

# Or flush and restart
docker-compose exec redis redis-cli FLUSHALL
docker-compose restart redis
```

### Verification shows failed checks
```bash
# Re-run with full details
./verify-recovery.sh --full

# Check individual service logs
docker logs thebot-backend
docker logs thebot-postgres
docker logs thebot-redis

# Run specific health check
curl -v http://localhost:8000/api/system/health/
```

## Performance Characteristics

### Restore Times
- **Database (512MB)**: 10-15 minutes
- **Redis (100MB)**: 2-3 minutes
- **PITR (with WAL replay)**: 15-20 minutes
- **Complete datacenter failover**: 45-60 minutes

### Backup Times
- **Daily database**: 3-5 minutes
- **Weekly database**: 3-5 minutes (with compression)
- **Redis snapshot**: < 1 minute
- **WAL archiving**: Automatic, <100ms per file

### Storage Usage
- **Daily backups**: ~500MB × 7 = 3.5GB
- **Weekly backups**: ~500MB × 4 = 2GB
- **Monthly backups**: ~500MB × 12 = 6GB
- **WAL archive**: ~16MB × 168 = 2.7GB
- **Total**: ~14GB (7-day retention)

## Maintenance

### Update Runbook
When incident procedures change:
```bash
# Edit the runbook
nano ../../infrastructure/dr/dr-runbook.json

# Validate JSON
cat ../../infrastructure/dr/dr-runbook.json | jq .

# Test new procedures
./failover.sh --simulate
```

### Update Contact Information
```bash
# Edit runbook escalation_matrix
vim ../../infrastructure/dr/dr-runbook.json

# Update email addresses, phone numbers
# Ensure team has access to runbook
```

### Periodic Review
- **Monthly**: Review backup sizes and growth trends
- **Quarterly**: Run DR drill and update procedures
- **Annually**: Complete audit of recovery procedures

## Support

For questions or issues with disaster recovery:

1. **Check logs**: `/backups/logs/`
2. **Review runbook**: `infrastructure/dr/dr-runbook.json`
3. **Read guide**: `docs/DISASTER_RECOVERY.md`
4. **Run verification**: `./verify-recovery.sh --full`
5. **Contact DBA team**: `dba@thebot.io`

---

**Last Updated**: December 27, 2025
**Status**: Production Ready
**Version**: 1.0.0

For complete documentation, see [DISASTER_RECOVERY.md](../../docs/DISASTER_RECOVERY.md)
