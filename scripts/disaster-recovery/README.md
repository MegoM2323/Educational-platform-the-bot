# Disaster Recovery System

Comprehensive disaster recovery framework for THE_BOT Platform with automated failover, backup management, and recovery procedures.

## Overview

This directory contains automated scripts and runbooks for disaster recovery scenarios including:

- **Service Failures**: Automatic restart and recovery
- **Database Failures**: Full restore or point-in-time recovery
- **Cache Failures**: AOF or RDB restore
- **Datacenter Failures**: Complete system failover
- **Data Corruption**: Selective or full recovery

**Key Metrics**:
- RTO (Recovery Time Objective): < 1 hour
- RPO (Recovery Point Objective): < 15 minutes

## Quick Start

### View Disaster Recovery Plan
```bash
# Read comprehensive plan
cat ../../../docs/DISASTER_RECOVERY.md

# View incident runbook
cat ../../infrastructure/dr/dr-runbook.json | jq
```

### Run Recovery Verification
```bash
# Quick health check (5 minutes)
./verify-recovery.sh --quick

# Full system check (15 minutes)
./verify-recovery.sh --full

# Production smoke test (30 minutes)
./verify-recovery.sh --smoke-test
```

### Emergency Procedures

#### Service Crashed
```bash
# Auto-restart and verify
./failover.sh --incident service_failure backend
```

#### Database Down
```bash
# Restore from latest backup
./restore-database.sh --type full --from latest

# Or point-in-time recovery
./restore-database.sh --type pitr --until "2025-12-27 14:30:00"
```

#### Redis Down
```bash
# Restore from AOF
./restore-redis.sh --type aof --from latest

# Or from RDB snapshot
./restore-redis.sh --type rdb --from latest
```

#### Complete Datacenter Failure
```bash
# Failover to secondary
./failover.sh --incident datacenter_failure
```

## Scripts

### 1. failover.sh - Automated Failover Handler

Orchestrates failover for different incident types.

**Usage**:
```bash
./failover.sh --incident [TYPE]
./failover.sh --simulate
./failover.sh --status
```

**Incident Types**:
- `database_failure` - Promote replica to primary
- `redis_failure` - Restore or restart Redis
- `service_failure [SERVICE]` - Restart specific service
- `datacenter_failure` - Failover to secondary region

**Example**:
```bash
# Database failover (with replica)
./failover.sh --incident database_failure

# Service restart
./failover.sh --incident service_failure backend

# Simulation mode (no actual changes)
./failover.sh --simulate

# Check current failover status
./failover.sh --status
```

**Features**:
- Automatic health checks
- Pre-failover backups
- Replica promotion for database
- Connection string updates
- Service restart and verification
- Detailed logging
- Alert notifications (email, Slack)

### 2. restore-database.sh - PostgreSQL Recovery

Restores PostgreSQL from full backups or performs point-in-time recovery.

**Usage**:
```bash
# Restore from latest backup
./restore-database.sh --type full --from latest

# Restore from specific date
./restore-database.sh --type full --from 20251226

# Point-in-time recovery
./restore-database.sh --type pitr --until "2025-12-27 14:30:00"

# Restore to staging environment
./restore-database.sh --type full --from latest --target staging

# Restore from specific file
./restore-database.sh --type full --file /backups/database/backup_20251227.dump.gz
```

**Options**:
- `--type` - `full` or `pitr`
- `--from` - `latest`, `daily`, `weekly`, `monthly`, or date (YYYYMMDD)
- `--file` - Specific backup file path
- `--until` - Target time for PITR (format: "YYYY-MM-DD HH:MM:SS")
- `--target` - `production` or `staging`
- `--skip-verify` - Skip backup integrity check

**Features**:
- Automatic backup file discovery
- Backup integrity verification
- Pre-restore backups (production)
- Database recreation
- Restore progress tracking
- Post-restore verification
- Support for full and PITR recoveries

### 3. restore-redis.sh - Redis Recovery

Restores Redis from AOF or RDB backups.

**Usage**:
```bash
# Restore from AOF
./restore-redis.sh --type aof --from latest

# Restore from RDB snapshot
./restore-redis.sh --type rdb --from latest

# Restore from S3
./restore-redis.sh --type rdb --from s3

# Restore from specific file
./restore-redis.sh --type aof --file /backups/redis_aof_20251227.bak
```

**Options**:
- `--type` - `aof`, `rdb`, or `s3`
- `--from` - `latest`, `daily`, `weekly`, `monthly`
- `--file` - Specific backup file
- `--skip-verify` - Skip backup integrity check

**Features**:
- AOF replay recovery
- RDB snapshot restore
- S3 download and restore
- Pre-restore backups
- Service restart verification
- Data integrity checks

### 4. verify-recovery.sh - Verification Testing

Comprehensive post-recovery system verification.

**Usage**:
```bash
# Quick checks (5 minutes)
./verify-recovery.sh --quick

# Full checks (15 minutes)
./verify-recovery.sh --full

# Smoke tests (30 minutes)
./verify-recovery.sh --smoke-test
```

**Quick Checks**:
- Backend health endpoint
- Database connectivity
- Redis connectivity
- Celery workers

**Full Checks**:
- All quick checks +
- Database integrity (tables, records)
- Redis data verification
- API endpoint testing
- Database schema validation

**Smoke Tests**:
- All full checks +
- User authentication flow
- Materials API
- Chat API
- Real-world scenarios

**Sample Output**:
```
Total Checks: 12
Passed: 11
Failed: 1

[PASS] Backend container running
[PASS] Health endpoint responding (HTTP 200)
[PASS] PostgreSQL accepting connections
[PASS] Database 'thebot_db' exists
[FAIL] Chat API not responding (HTTP 500)
...

RESULT: SOME CHECKS FAILED
```

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
