# Media Backup System

Production-ready backup solution for media files in THE_BOT platform.

## Quick Start

```bash
# Make scripts executable
chmod +x *.sh

# Run daily backup
./backup.sh

# List available backups
./restore.sh --list

# Setup automated daily backups
./setup-cron.sh --daily

# Monitor backup health
./monitor.sh --health

# Test backup system
./test_backup.sh
```

## Scripts

| Script | Purpose | Usage |
|--------|---------|-------|
| `backup.sh` | Create backups (full/incremental) | `./backup.sh [daily\|full\|incremental]` |
| `restore.sh` | Restore from backups | `./restore.sh <backup_file>` |
| `setup-cron.sh` | Schedule automated backups | `./setup-cron.sh [--daily\|--weekly]` |
| `monitor.sh` | Monitor backup health | `./monitor.sh [--health\|--disk-usage]` |
| `test_backup.sh` | Test backup system | `./test_backup.sh [all\|--unit\|--integration]` |

## Features

- ✓ **Full and incremental backups**
- ✓ **Compression (gzip)** - 80-90% size reduction
- ✓ **SHA256 checksums** - Integrity verification
- ✓ **S3 storage** - Off-site backup support
- ✓ **Retention policies** - Automatic cleanup
- ✓ **Health monitoring** - Automated checks
- ✓ **Email notifications** - Failure alerts
- ✓ **Cron scheduling** - Automated backups
- ✓ **Comprehensive tests** - Unit + integration

## Files Backed Up

```
backend/media/
├── avatars/           # User profile pictures
├── materials/         # Course materials (PDF, video)
├── submissions/       # Student submissions
├── chat/              # Chat media (images, files)
└── reports/           # Generated reports
```

## Configuration

### Environment Variables (.env)

```bash
BACKUP_DIR=./backups/media
MEDIA_DIR=../backend/media
BACKUP_RETENTION_DAYS=30

# S3 Configuration
ENABLE_S3_UPLOAD=true
AWS_S3_BUCKET=my-backups
AWS_REGION=us-east-1

# Notifications
ENABLE_NOTIFICATIONS=true
NOTIFICATION_EMAIL=admin@example.com
```

## Common Commands

### Backup Operations

```bash
# Full backup now
./backup.sh full

# Daily backup
./backup.sh daily

# Incremental backup
./backup.sh incremental

# Cleanup old backups
./backup.sh cleanup

# Show status
./backup.sh status
```

### Restore Operations

```bash
# List local backups
./restore.sh --list

# List S3 backups
./restore.sh --list-s3

# Restore from file
./restore.sh backup_20251227_020000.tar.gz

# Restore from S3
./restore.sh --s3 media-backups/full/backup_20251227_020000.tar.gz

# Test restore (dry-run)
./restore.sh --test backup_20251227_020000.tar.gz

# Verify backup
./restore.sh --verify backup_20251227_020000.tar.gz
```

### Setup Cron

```bash
# Interactive setup
./setup-cron.sh

# Daily backup
./setup-cron.sh --daily

# Weekly backup
./setup-cron.sh --weekly

# List installed jobs
./setup-cron.sh --list

# Remove all jobs
./setup-cron.sh --uninstall

# Test setup
./setup-cron.sh --test
```

### Monitoring

```bash
# Quick status
./monitor.sh

# Detailed health check
./monitor.sh --health

# Disk usage
./monitor.sh --disk-usage

# Simulate cleanup
./monitor.sh --cleanup-test
```

### Testing

```bash
# Run all tests
./test_backup.sh

# Unit tests only
./test_backup.sh --unit

# Integration tests
./test_backup.sh --integration

# S3 tests
./test_backup.sh --s3

# Clean test environment
./test_backup.sh --cleanup
```

## Backup Storage

### Directory Structure

```
backups/media/
├── full/               # Full backups (daily)
├── incremental/        # Incremental backups
├── logs/               # Backup logs
│   ├── backup_*.log
│   ├── restore_*.log
│   ├── monitor.log
│   └── cron.log
├── .backup_status      # Current status JSON
└── .last_manifest      # Latest file manifest
```

### Retention Policy

- **Daily backups:** Keep 30 days
- **Old backups:** Automatically deleted after 30 days
- **Total size:** Typically 30-50 GB for 30 days

## Monitoring & Alerts

### Health Checks

```bash
./monitor.sh --health
```

Verifies:
- Last backup age (max 48 hours)
- Backup integrity (gzip/checksums)
- Disk usage (max 80%)
- Retention policy enforcement
- File count and sizes

### Email Notifications

When configured, alerts sent for:
- Backup failures
- High disk usage
- Corrupted backups
- Missing backups

### View Logs

```bash
# Latest backup log
tail -f backups/media/logs/backup_*.log

# Monitor log
tail -f backups/media/logs/monitor.log

# Restore log
tail -f backups/media/logs/restore_*.log

# Current status
cat backups/media/.backup_status
```

## Testing

### Run Tests

```bash
# All tests
./test_backup.sh

# Unit tests (scripts, tools)
./test_backup.sh --unit

# Integration tests (backup/restore)
./test_backup.sh --integration

# S3 tests (requires AWS config)
./test_backup.sh --s3
```

### Test Coverage

- ✓ Scripts exist and are executable
- ✓ Directory structure creation
- ✓ Manifest generation
- ✓ Checksum calculation
- ✓ Full backup creation
- ✓ Incremental backup creation
- ✓ Backup verification
- ✓ Backup integrity checking
- ✓ Restore functionality
- ✓ Metadata generation
- ✓ Backup listing
- ✓ Cleanup operations
- ✓ S3 upload (if configured)

## Disaster Recovery

### Media Directory Corrupted

```bash
# 1. List available backups
./restore.sh --list

# 2. Restore latest
./restore.sh backups/media/full/backup_20251227_020000.tar.gz

# 3. Verify
./monitor.sh --health
```

### Local Backups Lost (Restore from S3)

```bash
# 1. List S3 backups
./restore.sh --list-s3

# 2. Restore from S3
./restore.sh --s3 media-backups/full/backup_20251227_020000.tar.gz

# 3. Verify
./monitor.sh --health
```

## Performance

| Operation | Duration | Notes |
|-----------|----------|-------|
| Full backup | 10-30s | Typical 500MB media |
| Incremental backup | 5-10s | Changed files only |
| Restore | 15-30s | Full restoration |
| Test restore | <1s | Metadata read only |
| S3 upload | 30s-5m | Depends on file size |

## S3 Setup

### Configure AWS

```bash
aws configure
# Or set environment:
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_DEFAULT_REGION=us-east-1
```

### Create Bucket

```bash
aws s3 mb s3://thebot-backups --region us-east-1
```

### Enable S3 Upload

```bash
export ENABLE_S3_UPLOAD=true
export AWS_S3_BUCKET=thebot-backups
./backup.sh daily
```

## Troubleshooting

### Backup Failed

```bash
# Check logs
tail -50 backups/media/logs/backup_*.log

# Check permissions
ls -la backend/media/

# Check disk space
df -h backups/media/

# Run test
./test_backup.sh --unit
```

### Restore Failed

```bash
# Verify backup integrity
./restore.sh --verify backup_file.tar.gz

# Check backup contents
tar -tzf backup_file.tar.gz | head -20

# Check permissions
ls -la backend/media/

# Try test restore
./restore.sh --test backup_file.tar.gz
```

### Cron Not Running

```bash
# List installed jobs
crontab -l

# Test manually
./backup.sh daily

# Reinstall
./setup-cron.sh --daily

# Check system logs
sudo journalctl -u cron --follow
```

## Best Practices

1. **Regular Testing**
   - Test restore monthly
   - Verify integrity regularly
   - Run health checks weekly

2. **Multiple Copies**
   - Keep local backups (30 days)
   - Upload to S3 (off-site)
   - Archive monthly backups

3. **Monitoring**
   - Enable email notifications
   - Check logs regularly
   - Monitor disk usage

4. **Documentation**
   - Document S3 bucket details
   - Record recovery procedures
   - Keep backup schedule documented

5. **Access Control**
   - Restrict backup directory
   - Protect AWS credentials
   - Use IAM roles

## Documentation

See [MEDIA_BACKUP_GUIDE.md](../MEDIA_BACKUP_GUIDE.md) for complete documentation including:
- Detailed configuration
- Advanced usage
- Recovery procedures
- Performance optimization
- Troubleshooting guide

## Support

For issues or questions:
1. Check logs: `tail backups/media/logs/*.log`
2. Run health check: `./monitor.sh --health`
3. Test system: `./test_backup.sh`
4. Review documentation: [MEDIA_BACKUP_GUIDE.md](../MEDIA_BACKUP_GUIDE.md)

## Version

- Version: 1.0.0
- Created: December 27, 2025
- Status: Production Ready

## Related Tasks

- **T_DEV_014**: Database Backups (Completed)
- **T_DEV_015**: Media Backups (This Task)
