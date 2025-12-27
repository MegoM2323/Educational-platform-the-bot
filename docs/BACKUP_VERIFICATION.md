# Backup Verification System

Complete automated backup verification and restore testing system for THE_BOT educational platform.

## Overview

The backup verification system provides comprehensive tools to:
- Verify backup integrity (gzip, checksums, file size)
- Test restore procedures in isolated environments
- Check database integrity after restore
- Generate verification reports
- Send email alerts on failures

## Features

### Backup Verification
- **Gzip Integrity Check**: Verifies compressed files are not corrupted
- **SHA256 Checksum Verification**: Validates checksums against metadata
- **File Size Validation**: Ensures files are not empty or corrupted (100B - 100GB)
- **Metadata Validation**: Checks for required metadata fields
- **Extractability Test**: Verifies backup content can be extracted

### Restore Testing
- **Isolated Test Database**: Creates temporary test database on separate port
- **Automated Restore**: Extracts and restores backup to test database
- **Database Integrity Checks**: Runs REINDEX and ANALYZE
- **Data Consistency Verification**: Checks referential integrity
- **Automatic Cleanup**: Removes test databases older than 7 days

### Reporting & Alerts
- **Detailed Reports**: HTML/text reports with pass/fail status
- **Email Notifications**: Alerts on verification failures
- **Audit Trail**: Complete verification logs
- **Metrics**: Backup size, count, pass rate

## Installation

### 1. Make Scripts Executable

```bash
chmod +x /home/mego/Python\ Projects/THE_BOT_platform/scripts/backup/verify-backup.sh
chmod +x /home/mego/Python\ Projects/THE_BOT_platform/scripts/backup/restore-test.sh
```

### 2. Configure Environment Variables

Add to `.env`:

```bash
# Backup Configuration
BACKUP_DIR=/path/to/backups                    # Default: ${PROJECT_ROOT}/backups
VERIFICATION_LOG_DIR=/path/to/logs             # Default: ${BACKUP_DIR}/verification_logs

# Alert Email
ALERT_EMAIL=admin@example.com                  # Required for email alerts
ADMIN_EMAIL=admin@example.com                  # For Django management command

# Test Database (for restore testing)
TEST_DB_HOST=localhost
TEST_DB_PORT=5433                              # Different from main DB port
TEST_DB_USER=postgres
TEST_DB_PASSWORD=your_password
TEST_DB_RETENTION_DAYS=7                       # Keep test DBs for 7 days

# Database Configuration (for verification)
DATABASE_TYPE=postgresql                       # postgresql or sqlite
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres
DB_PASSWORD=your_password
DB_NAME=thebot
```

## Usage

### Verify Latest Backup

```bash
# Using bash script
./scripts/backup/verify-backup.sh

# Using Django management command
python backend/manage.py verify_backup
```

Output:
```
[INFO] Verifying backup: backup_20251227_120000.gz
[SUCCESS] Gzip integrity verified
[SUCCESS] SHA256 checksum verified
[SUCCESS] File size check passed
[SUCCESS] Backup extraction test passed
[SUCCESS] Backup verification completed
```

### Verify All Backups

```bash
# Bash script
./scripts/backup/verify-backup.sh --all

# Django command
python backend/manage.py verify_backup --all
```

### Generate Verification Report

```bash
# Bash script
./scripts/backup/verify-backup.sh --report

# Django command
python backend/manage.py verify_backup --report
```

Report includes:
- Summary (total, verified, failed counts)
- Backup categories (daily, weekly, monthly)
- Checks performed
- Recommendations
- Email alerts if failures detected

### Test Restore from Backup

```bash
# Test from latest backup
./scripts/backup/restore-test.sh

# Test from specific backup
./scripts/backup/restore-test.sh /path/to/backup.gz

# Weekly automated test
./scripts/backup/restore-test.sh --weekly

# Verify data only (don't clean up test DB)
./scripts/backup/restore-test.sh --verify-only
```

Restore test includes:
- Test database creation on separate port
- Backup extraction and restoration
- Database REINDEX and ANALYZE
- Table count and structure verification
- Referential integrity checks
- Data consistency validation

### Check Database Integrity

```bash
# Bash script
./scripts/backup/verify-backup.sh --test-restore

# Django command
python backend/manage.py verify_backup --database-check
```

Checks include:
- Users without profiles
- Blocked table locks
- Database connectivity
- Table existence

### Verify Specific Backup File

```bash
# Bash script
./scripts/backup/verify-backup.sh /path/to/backup_20251227_120000.gz

# Django command
python backend/manage.py verify_backup --backup-file /path/to/backup_20251227_120000.gz
```

### Send Email Alerts

```bash
# Automatically sent on failures
python backend/manage.py verify_backup --all --alert
```

## Scheduling

### Daily Verification (using cron)

```bash
# Edit crontab
crontab -e

# Add for daily backup verification at 2 AM
0 2 * * * cd /home/mego/Python\ Projects/THE_BOT_platform && \
           ./scripts/backup/verify-backup.sh --all --report >> \
           backups/verification_logs/cron.log 2>&1

# Add for email alerts on failures at 3 AM
0 3 * * * cd /home/mego/Python\ Projects/THE_BOT_platform && \
           python backend/manage.py verify_backup --all --alert >> \
           backups/verification_logs/alerts.log 2>&1
```

### Weekly Restore Test (using cron)

```bash
# Add for weekly restore test on Sunday at 4 AM
0 4 * * 0 cd /home/mego/Python\ Projects/THE_BOT_platform && \
          ./scripts/backup/restore-test.sh --weekly >> \
          backups/restore_test_logs/cron.log 2>&1

# Cleanup old test databases on Sunday at 5 AM
0 5 * * 0 cd /home/mego/Python\ Projects/THE_BOT_platform && \
          psql -h localhost -p 5433 -U postgres -tc \
          "SELECT datname FROM pg_database WHERE datname LIKE 'thebot_test_%'" | \
          while read db; do dropdb -h localhost -p 5433 -U postgres "$db"; done >> \
          backups/restore_test_logs/cleanup.log 2>&1
```

### Setup with Script

```bash
cd /home/mego/Python\ Projects/THE_BOT_platform/scripts/backup

# Create cron jobs
./setup-cron.sh
```

## Log Files

### Verification Logs

Location: `backups/verification_logs/verification_YYYYMMDD_HHMMSS.log`

Sample:
```
[2025-12-27 12:00:00] [INFO] Starting backup verification
[2025-12-27 12:00:01] [SUCCESS] Gzip integrity verified
[2025-12-27 12:00:02] [SUCCESS] SHA256 checksum verified
[2025-12-27 12:00:03] [SUCCESS] File size check passed
[2025-12-27 12:00:04] [SUCCESS] Backup extraction test passed
```

### Restore Test Logs

Location: `backups/restore_test_logs/restore_test_YYYYMMDD_HHMMSS.log`

Sample:
```
[2025-12-27 04:00:00] [INFO] Setting up test database: thebot_test_20251227_040000
[2025-12-27 04:00:01] [SUCCESS] Test database created
[2025-12-27 04:00:05] [SUCCESS] Backup restored successfully
[2025-12-27 04:00:06] [INFO] Verifying database integrity
[2025-12-27 04:00:07] [SUCCESS] Database REINDEX completed
```

### Reports

Location: `backups/verification_logs/verification_report_YYYYMMDD_HHMMSS.txt`

Sample:
```
================================================================================
BACKUP VERIFICATION REPORT
================================================================================

Generated: 2025-12-27 12:00:00
Backup Directory: /home/mego/Python Projects/THE_BOT_platform/backups

================================================================================
SUMMARY
================================================================================

Total Backups: 21
Verified: 21
Failed: 0
Pass Rate: 21/21 = 100.0%
```

## Verification Checks

### 1. Gzip Integrity Check

Verifies the gzip file is not corrupted:
- Tests file can be decompressed
- Checks CRC32 checksum
- Ensures file is readable

**Failure causes**:
- File corrupted during storage
- Incomplete write to disk
- Storage device errors

**Action**: Re-run backup, check disk space and I/O

### 2. SHA256 Checksum Verification

Validates checksum against metadata:
- Calculates SHA256 of entire file
- Compares against metadata checksum
- Detects any file modifications

**Failure causes**:
- File corrupted after backup
- Metadata mismatch
- File copy errors

**Action**: Verify backup file integrity, check storage

### 3. File Size Validation

Ensures file size is reasonable:
- Minimum: 100 bytes
- Maximum: 100 GB
- Detects truncated files

**Failure causes**:
- Disk full during backup
- Backup process interrupted
- Storage corruption

**Action**: Check disk space, verify backup logs

### 4. Metadata Validation

Checks metadata completeness:
- Required fields present
- Valid JSON format
- Timestamp format valid

**Failure causes**:
- Metadata file corrupted
- Missing metadata file
- Incomplete backup process

**Action**: Check metadata files, re-run backup

### 5. Backup Extractability Test

Verifies content can be extracted:
- Tests decompression
- Reads first 1MB of content
- Validates gzip headers

**Failure causes**:
- Corrupted compressed data
- Invalid gzip format
- Truncated file

**Action**: Check gzip integrity, re-run backup

### 6. Database Integrity Check

Validates restored database:
- Checks table count (minimum 10)
- Verifies key tables exist
- Runs REINDEX for index validation
- Runs ANALYZE for statistics

**Failure causes**:
- Incomplete backup restore
- Database schema issues
- Missing tables

**Action**: Check restore logs, verify backup content

### 7. Referential Integrity Check

Validates data relationships:
- Checks for orphaned users
- Verifies foreign key constraints
- Validates parent-child relationships

**Failure causes**:
- Data inconsistency in backup
- Partial restore
- Constraint violations

**Action**: Review restore logs, check backup content

### 8. Data Consistency Verification

Validates data integrity:
- Checks user profile completeness
- Verifies required associations
- Detects missing relationships

**Failure causes**:
- Incomplete backup
- Data corruption
- Consistency issues in source

**Action**: Check data integrity in source database

## Troubleshooting

### Backup Verification Fails

```bash
# Check individual components
./scripts/backup/verify-backup.sh --backup-file /path/to/backup.gz

# Review detailed logs
tail -f backups/verification_logs/verification_*.log

# Test gzip directly
gzip -t /path/to/backup.gz

# Calculate checksum
sha256sum /path/to/backup.gz

# Check file size
ls -lh /path/to/backup.gz
```

### Restore Test Fails

```bash
# Check test database connectivity
pg_isready -h localhost -p 5433 -U postgres

# Review restore logs
tail -f backups/restore_test_logs/restore_test_*.log

# Check test database existence
psql -h localhost -p 5433 -U postgres -l | grep thebot_test

# Manual cleanup of test database
dropdb -h localhost -p 5433 -U postgres thebot_test_20251227_040000
```

### Email Alerts Not Sending

```bash
# Check email configuration in .env
cat .env | grep EMAIL

# Test mail delivery
echo "Test" | mail -s "Test Subject" admin@example.com

# Check mail logs (Ubuntu/Debian)
tail -f /var/log/mail.log

# Verify Django settings
python backend/manage.py shell -c "from django.conf import settings; print(settings.EMAIL_BACKEND)"
```

### Test Database Issues

```bash
# Check test database port is available
netstat -an | grep 5433

# List test databases
psql -h localhost -p 5433 -U postgres -l | grep thebot_test

# Check test database size
psql -h localhost -p 5433 -U postgres -c "SELECT datname, pg_size_pretty(pg_database_size(datname)) FROM pg_database WHERE datname LIKE 'thebot_test_%'"
```

## Performance Considerations

### Backup Size Impact

- **Small database** (<100MB): Verification takes <30 seconds
- **Medium database** (100MB-1GB): Verification takes <2 minutes
- **Large database** (>1GB): Verification takes 5-10 minutes

### Restore Test Performance

- **Small database**: Restore + verification takes <1 minute
- **Medium database**: Restore + verification takes 5-10 minutes
- **Large database**: Restore + verification takes 30+ minutes

### Disk Space Requirements

- **For daily verification**: 10% of backup size
- **For weekly restore test**: 200% of backup size (test DB + temp files)
- **For logs**: 1-5MB per verification

## Security Considerations

### Backup Verification Security

1. **File Permissions**: Verification logs contain no sensitive data
2. **Checksum Verification**: Detects unauthorized file modifications
3. **Extraction Testing**: Ensures backups cannot be tampered with
4. **Email Alerts**: Sent via secure SMTP with TLS

### Test Database Security

1. **Separate Port**: Test database runs on different port (5433)
2. **Automatic Cleanup**: Test databases cleaned up after 7 days
3. **No Production Data**: Only test data in verification environment
4. **Connection Password**: Test DB uses separate credentials

### Access Control

1. **Script Permissions**: Scripts are executable only (700)
2. **Log Directory**: Verification logs in restricted directory (700)
3. **Environment Variables**: Database credentials in .env (600)

## Maintenance

### Regular Maintenance Tasks

1. **Weekly**: Review verification reports
2. **Monthly**: Clean old test databases manually
3. **Quarterly**: Verify email alerts are working
4. **Yearly**: Full system backup/restore drill

### Archive Old Logs

```bash
# Archive logs older than 30 days
find backups/verification_logs -name "*.log" -mtime +30 -exec gzip {} \;

# Remove archives older than 90 days
find backups/verification_logs -name "*.log.gz" -mtime +90 -delete
```

### Monitor Log Size

```bash
# Check verification logs size
du -sh backups/verification_logs/

# Limit log size (max 1GB)
find backups/verification_logs -name "*.log" -type f -printf '%s\n' | \
    awk '{s+=$1} END {if (s > 1073741824) print "Archive old logs"}'
```

## Integration with CI/CD

### GitHub Actions Example

```yaml
name: Backup Verification

on:
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  verify-backup:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Load environment variables
        run: cat .env.production >> $GITHUB_ENV

      - name: Verify backup integrity
        run: |
          ./scripts/backup/verify-backup.sh --all

      - name: Test restore
        run: |
          ./scripts/backup/restore-test.sh --weekly

      - name: Upload verification report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: backup-verification-report
          path: backups/verification_logs/
```

## API Integration

### Django Management Commands

```bash
# In your application code
from django.core.management import call_command

# Verify all backups
call_command('verify_backup', all=True, alert=True)

# Check database integrity
call_command('verify_backup', database_check=True)

# Verify specific backup
call_command('verify_backup', backup_file='/path/to/backup.gz')
```

### Python Integration

```python
from pathlib import Path
from core.management.commands.verify_backup import BackupVerifier

# Create verifier instance
verifier = BackupVerifier()

# Verify specific backup
result = verifier.verify_backup_file(Path('/path/to/backup.gz'))

print(f"Status: {result['overall_status']}")
for check_name, check_result in result['checks'].items():
    print(f"  {check_name}: {check_result['status']}")

# Generate report
report = verifier.generate_verification_report()
print(report)
```

## Best Practices

1. **Run verification after every backup**
   - Ensures backup quality immediately
   - Catches issues early

2. **Test restore weekly**
   - Validates entire backup/restore process
   - Ensures system can recover

3. **Review reports regularly**
   - Monitor trends
   - Identify patterns

4. **Keep 7+ days of backups**
   - Daily: 7 days
   - Weekly: 4 weeks
   - Monthly: 12 months

5. **Document restore procedures**
   - Keep runbook updated
   - Test procedures regularly

6. **Monitor email alerts**
   - Set up email filters
   - Review failures immediately

7. **Archive old logs**
   - Keep 90+ days of logs
   - Compress old logs
   - Monitor disk space

## Conclusion

The backup verification system provides comprehensive protection for your data through automated integrity checks and restore testing. Regular verification ensures backups are reliable and restorable when needed.

For issues or questions, check logs and troubleshooting section above.
