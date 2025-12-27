# Media Backup System Guide

Complete backup solution for media files in THE_BOT platform, including avatars, course materials, submissions, chat media, and reports.

## Overview

The media backup system provides:
- **Daily snapshots** of all media files
- **Incremental backups** for changed files only
- **S3 storage** for off-site backup and disaster recovery
- **Compression** with tar.gz for efficiency
- **Integrity verification** using SHA256 checksums
- **Retention policies** to manage storage (30 days default)
- **Automated cron jobs** for scheduled backups
- **Health monitoring** with alerts

## Quick Start

### 1. View Available Backups

```bash
cd backup/media
./restore.sh --list
```

Output:
```
FULL BACKUPS:
  backup_20251227_020000.tar.gz       1.2M  2025-12-27 02:00  abc12345...
  backup_20251226_020000.tar.gz       1.1M  2025-12-26 02:00  def67890...

INCREMENTAL BACKUPS:
  backup_20251227_103000.tar.gz      100K  2025-12-27 10:30  ghi13579...
```

### 2. Run Manual Backup

```bash
# Full backup
./backup.sh full

# Or daily backup
./backup.sh daily

# Incremental backup (changed files only)
./backup.sh incremental
```

### 3. Restore from Backup

```bash
# Restore from local backup
./restore.sh backup/full/backup_20251227_020000.tar.gz

# Or restore from S3
./restore.sh --s3 media-backups/full/backup_20251227_020000.tar.gz

# Test restore without extraction
./restore.sh --test backup/full/backup_20251227_020000.tar.gz

# Verify backup integrity
./restore.sh --verify backup/full/backup_20251227_020000.tar.gz
```

### 4. Check Backup Health

```bash
./monitor.sh --health
```

## Scripts Overview

### backup.sh - Create Backups

**Usage:**
```bash
./backup.sh [TYPE]
```

**Types:**
- `daily` - Daily full backup (default)
- `full` - Full backup of all media
- `incremental` - Incremental backup (changed files only)
- `cleanup` - Cleanup old backups per retention policy
- `status` - Show backup status

**Examples:**
```bash
# Daily backup at 2 AM
./backup.sh daily

# Full backup on Sundays
./backup.sh full

# Incremental backup (after full backup)
./backup.sh incremental

# Remove old backups (keep 30 days)
./backup.sh cleanup

# Show current backup status
./backup.sh status
```

**Backup Locations:**
- Full backups: `backups/media/full/`
- Incremental backups: `backups/media/incremental/`
- Logs: `backups/media/logs/`

### restore.sh - Restore Backups

**Usage:**
```bash
./restore.sh [COMMAND]
```

**Commands:**
- `<backup_file>` - Restore from backup file
- `--list` - List available local backups
- `--list-s3` - List backups on S3
- `--s3 <key>` - Restore from S3
- `--verify <backup>` - Verify backup integrity
- `--test <backup>` - Test restore without extraction

**Examples:**
```bash
# Restore specific backup
./restore.sh backups/media/full/backup_20251227_020000.tar.gz

# Test restore (dry-run)
./restore.sh --test backups/media/full/backup_20251227_020000.tar.gz

# Verify integrity
./restore.sh --verify backups/media/full/backup_20251227_020000.tar.gz

# List S3 backups
./restore.sh --list-s3

# Restore from S3
./restore.sh --s3 media-backups/full/backup_20251227_020000.tar.gz
```

**Restore Process:**
1. Verifies backup integrity
2. Backs up current media directory (if it exists)
3. Extracts files from backup
4. Tests sample files
5. Creates restore metadata

**Automatic Rollback:**
If restore fails, automatically restores from backup of previous media directory.

### setup-cron.sh - Schedule Automated Backups

**Usage:**
```bash
./setup-cron.sh [COMMAND]
```

**Commands:**
- (interactive) - Interactive setup
- `--daily` - Setup daily backup at 2:00 AM
- `--weekly` - Setup weekly backup at 2:00 AM Sundays
- `--uninstall` - Remove all backup cron jobs
- `--test` - Test cron setup with manual backup
- `--list` - Show installed cron jobs

**Examples:**
```bash
# Interactive setup
./setup-cron.sh

# Setup daily backup
./setup-cron.sh --daily

# Setup daily + weekly backups
./setup-cron.sh --daily
./setup-cron.sh --weekly

# Show installed cron jobs
./setup-cron.sh --list

# Remove all backup cron jobs
./setup-cron.sh --uninstall

# Test cron setup
./setup-cron.sh --test
```

**Cron Schedules:**
```cron
# Daily backup at 2:00 AM
0 2 * * * cd /path/to/backup/media && ./backup.sh daily

# Weekly full backup on Sundays at 2:00 AM
0 2 * * 0 cd /path/to/backup/media && ./backup.sh full

# Monthly cleanup on 1st at 3:00 AM
0 3 1 * * cd /path/to/backup/media && ./backup.sh cleanup
```

### monitor.sh - Monitor Backup Health

**Usage:**
```bash
./monitor.sh [COMMAND]
```

**Commands:**
- (default) - Quick status check
- `--health` - Detailed health check with alerts
- `--cleanup-test` - Simulate cleanup operation
- `--disk-usage` - Show detailed disk usage

**Examples:**
```bash
# Quick status
./monitor.sh

# Detailed health check
./monitor.sh --health

# Check disk usage
./monitor.sh --disk-usage

# Simulate cleanup (show what would be deleted)
./monitor.sh --cleanup-test
```

**Health Checks:**
- ✓ Backup frequency (max 48 hours without backup)
- ✓ Backup integrity (gzip validation)
- ✓ File count verification
- ✓ Disk space (max 80% usage)
- ✓ Retention policy enforcement

### test_backup.sh - Test Backup System

**Usage:**
```bash
./test_backup.sh [TESTS]
```

**Tests:**
- `all` - Run all tests (default)
- `--unit` - Unit tests only
- `--integration` - Integration tests
- `--s3` - S3 tests (requires AWS config)
- `--cleanup` - Clean up test environment

**Examples:**
```bash
# Run all tests
./test_backup.sh

# Unit tests only
./test_backup.sh --unit

# Integration tests
./test_backup.sh --integration

# S3 tests
./test_backup.sh --s3

# Cleanup test environment
./test_backup.sh --cleanup
```

**Test Coverage:**
- Backup script existence and executability
- Directory creation
- Manifest generation
- Checksum calculation
- Full backup creation
- Incremental backup creation
- Backup verification
- Backup integrity checking
- Restore functionality
- Metadata generation
- Backup listing
- Cleanup operations
- S3 upload (if configured)

## Configuration

### Environment Variables

```bash
# Directories
BACKUP_DIR=./backups/media          # Backup storage location
MEDIA_DIR=../backend/media          # Media directory to backup

# Retention
BACKUP_RETENTION_DAYS=30            # Keep backups for 30 days

# S3 Configuration
ENABLE_S3_UPLOAD=false              # Enable S3 upload
AWS_S3_BUCKET=my-backups            # S3 bucket name
AWS_REGION=us-east-1                # AWS region

# Notifications
ENABLE_NOTIFICATIONS=false           # Enable email alerts
NOTIFICATION_EMAIL=admin@example.com # Alert recipient email
```

### .env File

Add to `.env` in project root:

```bash
# Media Backup Configuration
BACKUP_RETENTION_DAYS=30
ENABLE_S3_UPLOAD=true
AWS_S3_BUCKET=thebot-backups
AWS_REGION=us-east-1
ENABLE_NOTIFICATIONS=true
NOTIFICATION_EMAIL=admin@example.com
```

### S3 Setup

Configure AWS CLI:

```bash
aws configure
```

Or set environment variables:

```bash
export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
export AWS_DEFAULT_REGION=us-east-1
```

Create S3 bucket:

```bash
aws s3 mb s3://thebot-backups --region us-east-1
```

## Backup Strategy

### Daily Backups
- Run every day at 2:00 AM
- Full snapshot of all media files
- Compressed with gzip (typically 80-90% reduction)
- Retention: 30 days

### Incremental Backups (Optional)
- After full backup, capture changes only
- Much smaller than full backups
- Good for frequent intermediate backups
- Useful for frequent changes

### Weekly Full Backups
- Run every Sunday at 2:00 AM
- Ensures consistent weekly snapshots
- Good for monthly archival

### Monthly Cleanup
- Runs on 1st of month at 3:00 AM
- Removes backups older than 30 days
- Updates storage statistics

## Media Files Covered

```
backend/media/
├── avatars/              # User profile pictures
├── materials/            # Course PDFs, videos
├── submissions/          # Student assignment submissions
├── chat/                 # Chat images and attachments
└── reports/              # Generated Excel/PDF reports
```

## Backup Verification

### Automatic Verification

Every backup includes:
1. **Gzip integrity check** - Validates compression
2. **SHA256 checksum** - Detects corruption
3. **File count** - Ensures all files backed up
4. **Metadata** - Timestamps and statistics

### Manual Verification

```bash
# Verify backup integrity
./restore.sh --verify backup_file.tar.gz

# List contents without extracting
tar -tzf backup_file.tar.gz | head -20

# Check backup size
ls -lh backup_file.tar.gz

# Calculate checksum
sha256sum backup_file.tar.gz
```

## Restore Procedures

### Standard Restore

```bash
# List available backups
./restore.sh --list

# Restore specific backup
./restore.sh backups/media/full/backup_20251227_020000.tar.gz
```

**What happens:**
1. Verifies backup integrity
2. Backs up current media directory
3. Extracts all files
4. Tests sample files
5. Creates restore metadata

### Test Restore (Dry-run)

```bash
# Test without extraction
./restore.sh --test backup_file.tar.gz

# Lists what would be restored
# Doesn't modify media directory
```

### From S3

```bash
# List S3 backups
./restore.sh --list-s3

# Restore from S3
./restore.sh --s3 media-backups/full/backup_20251227_020000.tar.gz

# Automatically downloads from S3
# Then restores locally
```

### Recovery from Failure

If restore fails:
1. Current media directory is automatically backed up
2. You can restore from `media_backup_20251227_103000/`
3. Or restore again from a different backup

## Monitoring and Alerts

### Health Check

```bash
./monitor.sh --health
```

Checks:
- Last backup age (max 48 hours)
- Backup integrity (all files valid)
- Disk usage (max 80%)
- Retention policy (old backups deleted)
- File count and sizes

### Email Alerts

If configured, alerts sent for:
- Backup failures
- High disk usage (>80%)
- Corrupted backups
- Missing backups (>48 hours)

### View Logs

```bash
# Daily backup logs
tail -f backups/media/logs/backup_20251227.log

# Monitor logs
tail -f backups/media/logs/monitor.log

# Cron logs
tail -f backups/media/logs/cron.log
```

## Disk Usage Management

### View Usage

```bash
# Quick usage check
./monitor.sh --disk-usage

# Detailed breakdown
du -sh backups/media/*

# Largest backups
du -sh backups/media/full/* | sort -h | tail -10
```

### Reduce Usage

1. **Decrease retention period:**
   ```bash
   BACKUP_RETENTION_DAYS=14 ./backup.sh cleanup
   ```

2. **Remove old incremental backups:**
   ```bash
   find backups/media/incremental -mtime +7 -delete
   ```

3. **Archive to S3:**
   ```bash
   ENABLE_S3_UPLOAD=true ./backup.sh daily
   # Then delete local: rm -rf backups/media/full/*
   ```

## Performance Characteristics

### Backup Performance
- **Full backup:** ~10-30 seconds (typical media size ~500MB)
- **Incremental:** ~5-10 seconds (changed files only)
- **Compression ratio:** 80-90% size reduction

### Restore Performance
- **Restore:** ~15-30 seconds for full restoration
- **Test restore:** <1 second (reads metadata only)

### S3 Performance
- **Upload:** Depends on file size and network
  - Small backup (100MB): ~30-60 seconds
  - Large backup (500MB): ~2-5 minutes
- **Download:** Similar timing

## Troubleshooting

### Backup Creation Failed

```bash
# Check permissions
ls -la backend/media/

# Check disk space
df -h backups/media/

# Check logs
tail -50 backups/media/logs/backup_*.log

# Verify backup.sh is executable
ls -la backup/media/backup.sh
```

### Restore Failed

```bash
# Verify backup integrity first
./restore.sh --verify backup_file.tar.gz

# Check backup contents
tar -tzf backup_file.tar.gz | head -20

# Check media directory permissions
ls -la backend/media/

# Check disk space
df -h backend/media/

# Try test restore
./restore.sh --test backup_file.tar.gz
```

### S3 Upload Failed

```bash
# Check AWS credentials
aws s3 ls

# Check bucket name
aws s3 ls s3://your-bucket-name

# Verify AWS CLI is installed
which aws

# Test upload
aws s3 cp test_file.txt s3://your-bucket/test.txt
```

### Cron Jobs Not Running

```bash
# List installed cron jobs
crontab -l

# Check cron logs
sudo tail -f /var/log/syslog | grep CRON

# Verify backup script is executable
ls -la backup/media/backup.sh

# Test manual backup
cd backup/media && ./backup.sh daily

# Reinstall cron jobs
./setup-cron.sh --daily
```

## Best Practices

1. **Regular Testing**
   - Test restore monthly: `./restore.sh --test <backup>`
   - Verify data integrity: `./restore.sh --verify <backup>`

2. **Multiple Backup Copies**
   - Keep local backups (30 days)
   - Upload to S3 for off-site storage
   - Consider archiving monthly backups

3. **Monitoring**
   - Run health check weekly: `./monitor.sh --health`
   - Check logs regularly: `tail backups/media/logs/*`
   - Set up email alerts for failures

4. **Documentation**
   - Document S3 bucket details
   - Keep list of important backups
   - Document recovery procedures

5. **Access Control**
   - Restrict backup directory permissions
   - Use IAM roles for AWS access
   - Rotate access keys regularly

6. **Retention Policies**
   - Keep at least 30 days of backups
   - Monthly archive to S3 Glacier for cost savings
   - Delete test/temp files regularly

## Disaster Recovery

### Scenario: Media Directory Corrupted

```bash
# 1. Verify latest backup
./restore.sh --list | head -1

# 2. Test restore
./restore.sh --test backup_20251227_020000.tar.gz

# 3. Perform restore
./restore.sh backup_20251227_020000.tar.gz

# 4. Verify restoration
./monitor.sh --health
```

### Scenario: Server Crash

```bash
# 1. Setup new media directory
mkdir -p backend/media

# 2. If local backups available:
./restore.sh backup_from_local_disk.tar.gz

# 3. If local backups lost, restore from S3:
./restore.sh --s3 media-backups/full/backup_20251227_020000.tar.gz

# 4. Verify restoration
./monitor.sh --health
```

### Scenario: Complete Data Loss

```bash
# 1. Download from S3
aws s3 cp s3://thebot-backups/media-backups/full/backup_20251227_020000.tar.gz .

# 2. Restore
./restore.sh backup_20251227_020000.tar.gz

# 3. Verify all files
find backend/media -type f | wc -l
./monitor.sh --health
```

## Support and Logs

### Log Files

- **Backup logs:** `backups/media/logs/backup_YYYYMMDD.log`
- **Monitor logs:** `backups/media/logs/monitor.log`
- **Cron logs:** `backups/media/logs/cron.log`
- **Restore logs:** `backups/media/logs/restore_YYYYMMDD.log`

### View Current Status

```bash
cat backups/media/.backup_status
```

Output:
```json
{
  "last_backup": "2025-12-27T02:00:00Z",
  "last_backup_type": "daily",
  "last_backup_file": "backup_20251227_020000.tar.gz",
  "last_backup_size": "1.2M",
  "last_backup_success": true,
  "full_backup_count": 30,
  "incremental_backup_count": 5,
  "total_backup_size": "36G"
}
```

## Advanced Usage

### Custom Retention Policy

```bash
# Keep only 14 days of backups
BACKUP_RETENTION_DAYS=14 ./backup.sh cleanup

# Keep 60 days
BACKUP_RETENTION_DAYS=60 ./backup.sh cleanup
```

### Custom Backup Directory

```bash
# Backup to external drive
BACKUP_DIR=/mnt/external_drive/backups ./backup.sh daily
```

### S3 with Different Region

```bash
# Backup to US-West
AWS_REGION=us-west-2 AWS_S3_BUCKET=backup-west ./backup.sh daily
```

### Manual Incremental Strategy

```bash
# Full backup on Sunday
0 2 * * 0 /path/to/backup.sh full

# Incremental backup daily (Mon-Sat)
0 2 * * 1-6 /path/to/backup.sh incremental
```

## Version Information

- Script Version: 1.0.0
- Created: December 27, 2025
- Compatible with: THE_BOT platform v1.0.0+

## License

Part of THE_BOT educational platform. See LICENSE in project root.
