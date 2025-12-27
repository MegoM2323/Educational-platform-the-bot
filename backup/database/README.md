# Database Backup & Recovery System

Complete automated backup solution for THE_BOT platform with point-in-time recovery, retention policies, and comprehensive monitoring.

## Overview

This system provides:
- **Automated daily, weekly, and monthly backups** with configurable retention
- **Point-in-time recovery (PITR)** for PostgreSQL using custom format dumps
- **Compression & checksums** for data integrity verification
- **S3 upload** for off-site backup storage
- **Cron automation** with health monitoring and alerts
- **Full restore procedures** with pre-restore backups
- **Comprehensive logging** for audit trails

## Quick Start

### 1. Install Automated Backups

```bash
cd /home/mego/Python\ Projects/THE_BOT_platform/backup/database

# Make scripts executable
chmod +x *.sh

# Install cron jobs
./setup-cron.sh install

# Verify installation
./setup-cron.sh status
```

### 2. Create First Backup

```bash
# Manual daily backup
./backup.sh daily

# Or specific types
./backup.sh weekly
./backup.sh monthly

# Check backup status
./backup.sh status
```

### 3. Restore from Backup

```bash
# List available backups
./restore.sh list

# Restore from latest daily backup
./restore.sh latest daily

# Restore from specific backup
./restore.sh /path/to/backup_file.gz

# Test restore without making changes
./restore.sh --dry-run /path/to/backup_file.gz
```

## Configuration

### Environment Variables

Set in `.env` file:

```bash
# Database configuration
DATABASE_TYPE=postgresql          # or 'sqlite'
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=thebot
DATABASE_URL=postgresql://user:password@host:5432/dbname

# SQLite (if using)
DATABASE_PATH=/path/to/db.sqlite3

# Backup retention
BACKUP_RETENTION_DAILY=7          # Keep 7 daily backups
BACKUP_RETENTION_WEEKLY=4         # Keep 4 weekly backups
BACKUP_RETENTION_MONTHLY=12       # Keep 12 monthly backups

# Backup directory
BACKUP_DIR=/path/to/backups

# Email notifications
ENABLE_NOTIFICATIONS=true
NOTIFICATION_EMAIL=admin@example.com

# S3 upload (optional)
ENABLE_S3_UPLOAD=false
AWS_S3_BUCKET=my-backup-bucket
AWS_REGION=us-east-1

# Monitoring
ENABLE_ALERTS=true
ALERT_THRESHOLD_HOURS=24          # Alert if backup older than 24 hours
```

## Scripts

### backup.sh - Create Backups

Complete backup tool with compression, verification, and notifications.

**Usage:**
```bash
./backup.sh [daily|weekly|monthly|full|cleanup|status]
```

**Examples:**
```bash
# Daily backup
./backup.sh daily

# Weekly backup
./backup.sh weekly

# Monthly backup
./backup.sh monthly

# Cleanup old backups according to retention policy
./backup.sh cleanup

# Show current backup status
./backup.sh status
```

**Features:**
- Automatic compression with gzip
- SHA256 checksums for integrity verification
- Metadata file with backup information
- Automatic cleanup based on retention policy
- S3 upload capability
- Email notifications on success/failure
- Detailed logging

**Output:**
- Backup files: `backups/{daily,weekly,monthly}/backup_YYYYMMDD_HHMMSS.gz`
- Metadata: `backup_file.metadata` (JSON)
- Logs: `backups/logs/backup_YYYYMMDD.log`

### restore.sh - Restore Database

Restore from backup with verification and rollback capabilities.

**Usage:**
```bash
./restore.sh <backup_file|latest|list|verify>
./restore.sh --dry-run <backup_file>
```

**Examples:**
```bash
# List available backups
./restore.sh list

# Restore from latest daily backup
./restore.sh latest daily

# Restore from specific file (interactive confirmation)
./restore.sh backups/daily/backup_20231215_010000.gz

# Verify backup integrity before restore
./restore.sh verify backups/daily/backup_20231215_010000.gz

# Test restore without making changes
./restore.sh --dry-run backups/daily/backup_20231215_010000.gz
```

**Safety Features:**
- Pre-restore backup created automatically
- Gzip and checksum verification
- Interactive confirmation before destructive operations
- Detailed logging of restore process
- Database integrity checks after restore

### setup-cron.sh - Automation Setup

Configure automatic scheduled backups.

**Usage:**
```bash
./setup-cron.sh [install|uninstall|status|list]
```

**Examples:**
```bash
# Install automated backups
./setup-cron.sh install

# Check status
./setup-cron.sh status

# List installed jobs
./setup-cron.sh list

# Remove automation
./setup-cron.sh uninstall
```

**Default Schedule:**
- **Daily backup**: 1:00 AM (every day)
- **Weekly backup**: 3:00 AM (Sundays)
- **Monthly backup**: 5:00 AM (1st of month)
- **Weekly cleanup**: 2:00 AM (Saturdays)
- **Health check**: 12:30 AM (every day)

### monitor.sh - Health Monitoring

Monitor backup system health and detect issues.

**Usage:**
```bash
./monitor.sh [health|alert|verify|report]
```

**Examples:**
```bash
# Quick health check
./monitor.sh

# Health check and send alerts
./monitor.sh alert

# Verify all recent backups
./monitor.sh verify

# Generate detailed report
./monitor.sh report
```

**Checks Performed:**
- Backup freshness (age of latest backups)
- Backup integrity (gzip validation)
- Disk space available
- Retention policy compliance
- Log file status
- Error detection in logs

## Backup Storage

```
backups/
├── daily/                 # Daily backups (7 kept by default)
│   ├── backup_20231215_010000.gz
│   ├── backup_20231215_010000.metadata
│   └── ...
├── weekly/                # Weekly backups (4 kept by default)
│   ├── backup_2023W50_030000.gz
│   └── ...
├── monthly/               # Monthly backups (12 kept by default)
│   ├── backup_202312_050000.gz
│   └── ...
├── logs/                  # Backup logs
│   ├── backup_20231215.log
│   ├── restore_20231215_143000.log
│   └── cron.log
├── wal-archive/          # WAL files (PostgreSQL PITR)
├── pre-restore-*/        # Pre-restore backups (automatic)
└── .backup_status        # Current status (JSON)
```

## Point-in-Time Recovery (PITR)

### PostgreSQL PITR Setup

For production PostgreSQL databases, enable WAL archiving:

```sql
-- PostgreSQL configuration (postgresql.conf)
wal_level = archive           # or 'replica' for better features
archive_mode = on
archive_command = 'cp %p /var/lib/postgresql/wal-archive/%f'
archive_timeout = 300

-- Create WAL archive directory
mkdir -p /var/lib/postgresql/wal-archive
chmod 700 /var/lib/postgresql/wal-archive
chown postgres:postgres /var/lib/postgresql/wal-archive
```

Restore to specific point in time:

```bash
# Restore database from backup
./restore.sh backups/daily/backup_20231215_010000.gz

# Then restore WAL files up to specific timestamp
# psql -d thebot -f recovery.sql
# ALTER DATABASE thebot SET recovery_target_timeline TO latest;
# SELECT pg_wal_replay_resume();
```

## Retention Policy

The system automatically manages backups according to configured retention:

### Default Policy
- **7 daily backups**: Latest 7 days of daily backups kept
- **4 weekly backups**: Latest 4 weeks of backups kept
- **12 monthly backups**: Latest 12 months of backups kept

### Customization

Set environment variables:

```bash
export BACKUP_RETENTION_DAILY=10      # Keep 10 daily backups
export BACKUP_RETENTION_WEEKLY=8      # Keep 8 weekly backups
export BACKUP_RETENTION_MONTHLY=24    # Keep 24 monthly backups

./backup.sh cleanup
```

### Automatic Cleanup

- Cleanup runs automatically after successful backups
- Manual cleanup: `./backup.sh cleanup`
- Old backups deleted based on creation time
- Related metadata and log files also removed

## S3 Off-site Backup

### Setup

1. Install AWS CLI:
```bash
pip install awscli
```

2. Configure AWS credentials:
```bash
aws configure
# Enter: AWS Access Key ID
# Enter: AWS Secret Access Key
# Enter: Default region
# Enter: Default output format
```

3. Create S3 bucket:
```bash
aws s3 mb s3://my-backup-bucket --region us-east-1
```

4. Enable S3 upload in `.env`:
```bash
ENABLE_S3_UPLOAD=true
AWS_S3_BUCKET=my-backup-bucket
AWS_REGION=us-east-1
```

### Backup Naming

Backups uploaded to S3 with structure:
```
s3://my-backup-bucket/database-backups/
├── daily/
│   ├── backup_20231215_010000.gz
│   └── backup_20231215_010000.gz.metadata
├── weekly/
│   └── ...
└── monthly/
    └── ...
```

### S3 Lifecycle Policy

Create lifecycle rule to auto-archive old backups:

```bash
# Create lifecycle policy file
cat > lifecycle.json <<'EOF'
{
  "Rules": [
    {
      "Id": "Archive old backups",
      "Filter": {"Prefix": "database-backups/"},
      "Status": "Enabled",
      "Transitions": [
        {
          "Days": 30,
          "StorageClass": "GLACIER"
        }
      ],
      "Expiration": {
        "Days": 365
      }
    }
  ]
}
EOF

# Apply policy
aws s3api put-bucket-lifecycle-configuration \
  --bucket my-backup-bucket \
  --lifecycle-configuration file://lifecycle.json
```

## Email Notifications

### Setup

1. Configure SMTP in `.env`:
```bash
ENABLE_NOTIFICATIONS=true
NOTIFICATION_EMAIL=admin@example.com
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
```

2. Enable for backup script:
```bash
# Edit backup.sh and uncomment mail configuration
```

### Notification Content

Emails include:
- Backup status (success/failed)
- Backup file name and size
- Duration and checksum
- Retention policy summary
- Recent log entries

## Monitoring & Alerts

### Health Check

Regular monitoring via cron:

```bash
# Runs automatically via cron (12:30 AM daily)
./monitor.sh
```

### Manual Health Check

```bash
# Quick status
./monitor.sh

# Detailed report
./monitor.sh report

# Verify backups
./monitor.sh verify

# Health check with alerts
./monitor.sh alert
```

### Alert Conditions

Alerts triggered for:
- No daily backup in last 24 hours
- Corrupted backups detected
- Disk usage > 80%
- Disk usage > 95% (critical)
- Retention policy violations
- Errors in backup logs

### Email Alerts

Enable in `.env`:

```bash
ENABLE_ALERTS=true
ALERT_EMAIL=admin@example.com
ALERT_THRESHOLD_HOURS=24
```

## Disaster Recovery Procedures

### Complete Database Loss

```bash
# 1. List available backups
./restore.sh list

# 2. Choose appropriate backup (e.g., latest daily)
./restore.sh backups/daily/backup_20231215_010000.gz

# 3. System will prompt for confirmation
# 4. Pre-restore backup created automatically
# 5. Database restored and verified
# 6. Application can reconnect
```

### Partial Data Corruption

```bash
# 1. If recent backup available, restore it
./restore.sh latest daily

# 2. Or test restore first (dry-run)
./restore.sh --dry-run backups/daily/backup_20231215_010000.gz

# 3. Then perform actual restore
./restore.sh backups/daily/backup_20231215_010000.gz
```

### Point-in-Time Recovery (PostgreSQL)

```bash
# For PostgreSQL with WAL archiving enabled:
# 1. Restore full backup
./restore.sh backups/daily/backup_20231215_010000.gz

# 2. Configure recovery_target_timeline in recovery.conf
# 3. Apply WAL files up to desired point in time
# 4. Complete recovery with pg_wal_replay_resume()
```

### Testing Restore Procedure

Regular restore testing (weekly recommended):

```bash
# 1. Test latest backup without making changes
./restore.sh --dry-run backups/daily/backup_$(date +%Y%m%d)_*.gz

# 2. If test passes, actual restore can be performed
# 3. Log results for compliance
```

## Performance Metrics

### Typical Backup Times

- **SQLite database**: 30-60 seconds (10-50 MB)
- **PostgreSQL (small)**: 60-120 seconds (50-500 MB)
- **PostgreSQL (large)**: 5-30 minutes (500 MB - 5 GB)
- **Compression**: 2-10x size reduction

### Typical Restore Times

- **SQLite database**: 30-60 seconds
- **PostgreSQL (small)**: 60-120 seconds
- **PostgreSQL (large)**: 5-30 minutes
- **Verification**: 10-60 seconds

### Storage Requirements

Backup size approximately 20-30% of database size after compression.

Examples:
- 100 MB database → 20-30 MB backup
- 1 GB database → 200-300 MB backup
- 10 GB database → 2-3 GB backup

## Troubleshooting

### Backup Fails

**Issue**: `ERROR PostgreSQL backup failed`

**Solution**:
1. Check database connection: `psql -c "SELECT 1"`
2. Verify credentials in `.env`
3. Ensure pg_dump is installed: `pg_dump --version`
4. Check disk space: `df -h`
5. Review log file: `backups/logs/backup_*.log`

### Restore Fails

**Issue**: `ERROR Cannot connect to database`

**Solution**:
1. Verify database is running
2. Check connection parameters
3. Ensure sufficient permissions
4. Check pre-restore backup exists
5. Review restore log for details

### Corrupted Backup

**Issue**: `ERROR Gzip integrity check failed`

**Solution**:
1. Backup is corrupted and cannot be restored
2. Try older backup: `./restore.sh list`
3. Check S3 backup if available
4. Verify disk/network during backup
5. Enable more frequent backups

### Disk Space Full

**Issue**: `ERROR Failed to create backup`

**Solution**:
1. Check backup size: `du -sh backups/`
2. Run cleanup manually: `./backup.sh cleanup`
3. Archive old backups to S3 or external storage
4. Increase retention threshold if needed
5. Reduce backup frequency if necessary

## Compliance & Audit

### Audit Log

All backup operations logged in:
- `backups/logs/backup_*.log` - Detailed backup logs
- `backups/logs/restore_*.log` - Restore operations
- `backups/logs/cron.log` - Cron job execution

### Verification Reports

Generate compliance report:

```bash
# Generate status report
./backup.sh status

# Generate health report
./monitor.sh report

# List backup inventory
./restore.sh list
```

### Data Retention Certificate

```bash
# Show last backup timestamp
cat backups/.backup_status

# Example output:
# {
#   "last_backup": "2023-12-15T01:00:00Z",
#   "last_backup_file": "backup_20231215_010000.gz",
#   "daily_count": 7,
#   "weekly_count": 4,
#   "monthly_count": 12
# }
```

## Best Practices

1. **Regular Backups**: Enable daily automated backups via cron
2. **Multiple Strategies**: Combine daily (frequent), weekly (medium), and monthly (long-term)
3. **Off-site Storage**: Upload critical backups to S3 or external location
4. **Regular Testing**: Test restore procedures weekly
5. **Monitoring**: Check backup health daily
6. **Documentation**: Keep restore procedures documented
7. **Notification**: Set up email alerts for backup failures
8. **Retention**: Keep 7 daily, 4 weekly, 12 monthly at minimum
9. **Verification**: Verify backup checksums after creation
10. **Disaster Plan**: Have documented recovery procedures

## API Reference

### Backup Script Exit Codes

- `0`: Backup successful
- `1`: Backup failed
- `1`: Prerequisites not met
- `1`: Unknown backup type

### Restore Script Exit Codes

- `0`: Restore successful
- `0`: List operation successful
- `1`: Backup file not found
- `1`: Restore failed
- `1`: Pre-restore backup failed

### Status File Format

`backups/.backup_status` (JSON):

```json
{
  "last_backup": "2023-12-15T01:00:00Z",
  "last_backup_type": "daily",
  "last_backup_file": "backup_20231215_010000.gz",
  "last_backup_size": "45M",
  "last_backup_success": true,
  "daily_count": 7,
  "weekly_count": 4,
  "monthly_count": 12,
  "total_backup_size": "520M"
}
```

### Metadata File Format

`backup_file.metadata` (JSON):

```json
{
  "backup_file": "backup_20231215_010000.gz",
  "backup_path": "/path/to/backup_20231215_010000.gz",
  "backup_type": "postgresql",
  "backup_category": "daily",
  "backup_date": "2023-12-15T01:00:00Z",
  "backup_size": "45M",
  "backup_duration_seconds": 45,
  "backup_checksum_sha256": "abc123def456...",
  "compression": "gzip",
  "timestamp": 1702597200,
  "hostname": "production-server",
  "database_type": "postgresql"
}
```

## Support & Documentation

- Backup logs: `backups/logs/backup_*.log`
- Restore logs: `backups/logs/restore_*.log`
- Status: `backups/.backup_status`
- This README: `backup/database/README.md`

## License

Part of THE_BOT Platform. See main project LICENSE file.
