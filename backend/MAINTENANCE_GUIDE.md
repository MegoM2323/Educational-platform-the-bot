# Database Maintenance Guide

## Overview

The database maintenance command provides automated tools for optimizing and maintaining PostgreSQL and SQLite databases. It includes operations for vacuuming, reindexing, cleanup, and monitoring.

## Installation

The maintenance command is automatically installed as part of the Django management commands:

```bash
cd backend
python manage.py maintenance --help
```

## Usage

### Basic Syntax

```bash
python manage.py maintenance [OPTIONS]
```

### Available Operations

| Operation | Description | Time | Database |
|-----------|-------------|------|----------|
| **vacuum** | VACUUM ANALYZE - reclaim disk space, update statistics | 10-30 min | PostgreSQL |
| **reindex** | REINDEX DATABASE - rebuild all indexes | 5-15 min | PostgreSQL |
| **cleanup** | Archive/delete old soft-deleted records | 5-10 min | Both |
| **logs** | Clean up old audit and task logs | 2-5 min | Both |
| **sessions** | Remove expired Django sessions | <1 min | Both |
| **views** | Refresh materialized views (non-blocking) | <1 min | PostgreSQL |
| **stats** | Generate database statistics | <1 min | Both |
| **bloat** | Check for bloated tables | <1 min | PostgreSQL |
| **backup** | Create database backup before maintenance | 5-30 min | PostgreSQL |

## Examples

### Run All Maintenance Operations (Safe Preview)

```bash
python manage.py maintenance --all --dry-run
```

Output:
```
============================================================
DATABASE MAINTENANCE REPORT
============================================================

VACUUM
  Status: simulated
  Message: VACUUM ANALYZE would run on all tables

REINDEX
  Status: simulated
  Message: REINDEX DATABASE would run concurrently

...

============================================================
Duration: 0.25s
Timestamp: 2025-12-27T02:00:00Z
Database: thebot
```

### Run Specific Operation

```bash
# Clean up old logs
python manage.py maintenance --operation logs

# Check for table bloat
python manage.py maintenance --operation bloat --dry-run

# Create backup
python manage.py maintenance --operation backup

# Vacuum database
python manage.py maintenance --operation vacuum
```

### Dry-Run Mode (Recommended for First Time)

```bash
python manage.py maintenance --operation cleanup --dry-run
```

Output shows what would be deleted without actually deleting:

```
DATABASE MAINTENANCE REPORT
============================================================

CLEANUP
  Status: simulated
  Operation: cleanup
  Message: Would delete 1523 FailedTask records older than 730 days

...
```

### JSON Output Format

```bash
python manage.py maintenance --operation stats --output json
```

Output:
```json
{
  "stats": {
    "status": "completed",
    "operation": "stats",
    "top_tables": [
      {
        "schema": "public",
        "table": "core_audit_log",
        "size": "245 MB"
      },
      {
        "schema": "public",
        "table": "chat_message",
        "size": "185 MB"
      }
    ]
  },
  "metadata": {
    "timestamp": "2025-12-27T02:00:00Z",
    "duration_seconds": 1.23,
    "dry_run": false,
    "database": "thebot"
  }
}
```

## Options

### --all

Run all maintenance operations sequentially:

```bash
python manage.py maintenance --all
```

Operations run in order:
1. backup
2. vacuum
3. reindex
4. cleanup
5. logs
6. sessions
7. stats
8. bloat

### --operation {operation}

Run a specific operation:

```bash
python manage.py maintenance --operation logs
```

### --dry-run

Preview what would be done without making changes:

```bash
python manage.py maintenance --operation cleanup --dry-run
```

Perfect for testing before running in production!

### --output {text|json}

Choose output format:

```bash
# Text format (default)
python manage.py maintenance --operation stats --output text

# JSON format (for scripting)
python manage.py maintenance --operation stats --output json
```

### --schedule {daily|weekly|monthly}

Add to Celery Beat scheduler (requires celery-beat):

```bash
python manage.py maintenance --all --schedule daily
```

Scheduling:
- `daily`: 2 AM (light maintenance)
- `weekly`: Sunday 3 AM (full vacuum)
- `monthly`: First Sunday 4 AM (reindex)

## Detailed Operation Guide

### VACUUM & ANALYZE (PostgreSQL only)

Reclaims disk space and updates table statistics for query planning.

```bash
python manage.py maintenance --operation vacuum --dry-run
python manage.py maintenance --operation vacuum
```

**What it does:**
- Removes dead tuples from tables
- Updates ANALYZE statistics
- Rebuilds indexes
- Optimizes query planning

**Time:** 10-30 minutes (depends on database size)

**Best practices:**
- Run during low-traffic periods
- Run weekly on production
- Monitor disk space before/after

### REINDEX (PostgreSQL only)

Rebuilds all database indexes without locking tables.

```bash
python manage.py maintenance --operation reindex
```

**What it does:**
- Rebuilds all indexes using CONCURRENTLY flag
- Removes bloated indexes
- Improves query performance
- Non-blocking (allows concurrent access)

**Time:** 5-15 minutes

**Best practices:**
- Safe to run during business hours
- Run monthly on production
- Can run on heavily-used tables

### CLEANUP

Archives and removes old soft-deleted records.

```bash
python manage.py maintenance --operation cleanup --dry-run
python manage.py maintenance --operation cleanup
```

**What it cleans:**
- FailedTask records > 365 days old (archived to 730 days)
- Processes in batches of 1000 to avoid locking

**Time:** 5-10 minutes

**Retention policy:**
- Archive after: 365 days
- Delete after: 730 days

### CLEANUP LOGS

Removes old audit and task execution logs.

```bash
python manage.py maintenance --operation logs --dry-run
python manage.py maintenance --operation logs
```

**What it cleans:**
- AuditLog: older than 90 days
- TaskExecutionLog: older than 30 days
- Processes in batches of 10000

**Time:** 2-5 minutes

**Retention policy:**
- Audit logs: 90 days
- Task logs: 30 days
- System logs: 30 days

**Example output:**
```
Cleanup logs
  Status: completed
  Details:
    Audit Logs:
      deleted: 5234
      days: 90
    Task Logs:
      deleted: 1823
      days: 30
```

### CLEANUP SESSIONS

Removes expired Django sessions.

```bash
python manage.py maintenance --operation sessions
```

**What it does:**
- Removes sessions past expiration date
- Safe to run frequently
- No data loss (expired sessions are invalid anyway)

**Time:** <1 minute

### UPDATE VIEWS (PostgreSQL only)

Refreshes materialized views non-blocking.

```bash
python manage.py maintenance --operation views
```

**What it does:**
- Refreshes cached data in materialized views
- Uses CONCURRENT flag (non-blocking)
- Updates statistics for reporting

**Time:** <1 minute

### GENERATE STATISTICS

Analyzes database structure and generates stats.

```bash
python manage.py maintenance --operation stats
python manage.py maintenance --operation stats --output json
```

**What it shows:**
- Top 20 largest tables
- Schema breakdown
- Size trends

**Example:**
```json
{
  "stats": {
    "status": "completed",
    "top_tables": [
      {
        "schema": "public",
        "table": "core_audit_log",
        "size": "245 MB"
      }
    ]
  }
}
```

### CHECK BLOAT (PostgreSQL only)

Identifies tables with significant bloat (wasted space).

```bash
python manage.py maintenance --operation bloat
python manage.py maintenance --operation bloat --dry-run
```

**What it reports:**
- Tables with >10% wasted space
- Recommended candidates for VACUUM FULL
- Size of wasted space

**Example:**
```
BLOAT
  Status: completed
  Bloated tables:
    - schema: public
      table: old_logs
      waste_percent: 35
      waste_size: 125 MB
```

**Action if bloat found:**
1. Schedule VACUUM for off-peak hours
2. Consider archiving old data
3. Run reindex after vacuum

### CREATE BACKUP

Creates a backup of the database before maintenance.

```bash
python manage.py maintenance --operation backup
```

**Backup location:** `/tmp/backup_{database}_{timestamp}.sql`

**Restore from backup:**
```bash
psql -U username database < /tmp/backup_thebot_20251227_020000.sql
```

**Note:** Requires `pg_dump` installed on the system.

## Scheduling Maintenance

### Using Celery Beat

Add to `celery_config.py`:

```python
from celery.schedules import crontab

app.conf.beat_schedule = {
    'maintenance-daily': {
        'task': 'core.tasks.run_maintenance',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'args': ('all', '--dry-run=False')
    },
    'maintenance-weekly-full': {
        'task': 'core.tasks.run_maintenance',
        'schedule': crontab(day_of_week=0, hour=3, minute=0),  # Sunday 3 AM
        'args': ('all', '--dry-run=False')
    },
}
```

### Using Cron

Add to crontab:

```bash
# Daily light maintenance (2 AM)
0 2 * * * cd /app && python manage.py maintenance --operation logs --operation sessions

# Weekly full maintenance (Sunday 3 AM)
0 3 * * 0 cd /app && python manage.py maintenance --all

# Monthly reindex (First Sunday 4 AM)
0 4 * * 0 [ "$(date +%d)" -le 07 ] && cd /app && python manage.py maintenance --operation reindex
```

## Monitoring and Alerts

### Check Execution Logs

```python
from core.models import TaskExecutionLog

logs = TaskExecutionLog.objects.filter(
    task_name='database_maintenance'
).order_by('-started_at')[:10]

for log in logs:
    print(f"{log.started_at}: {log.status} ({log.duration_seconds}s)")
```

### Email Notifications

Maintenance logs are automatically sent to configured email addresses:

```python
# In settings.py
ADMINS = [
    ('Admin Name', 'admin@example.com'),
]
```

## Performance Metrics

### Before & After Maintenance

Track improvements:

```bash
# Before
python manage.py maintenance --operation stats

# Run maintenance
python manage.py maintenance --all

# After
python manage.py maintenance --operation stats
```

### Expected Improvements

- Query performance: 10-30% faster
- Disk space: 10-50% reduction
- Table bloat: <10% remaining
- Index efficiency: 90%+ scan efficiency

## Troubleshooting

### Issue: Maintenance Hangs or Locks

**Symptoms:**
- Command doesn't complete
- Queries time out
- Database is unresponsive

**Solution:**
1. Check long-running queries:
   ```python
   from core.maintenance_utils import MaintenanceUtils
   queries = MaintenanceUtils.get_long_running_queries(minutes=5)
   ```

2. Kill long-running transaction:
   ```sql
   SELECT pg_terminate_backend(pid)
   FROM pg_stat_activity
   WHERE duration > '1 hour';
   ```

3. Run in off-peak hours

### Issue: "PostgreSQL required" error

**Cause:** Running on SQLite database

**Solution:** Use PostgreSQL for production

```bash
# Check database type
python manage.py maintenance --operation stats
```

### Issue: Disk space not freed after VACUUM

**Cause:** Database file not truncated

**Solution:**
1. Run VACUUM FULL (with table lock):
   ```sql
   VACUUM FULL;
   ```

2. Or restart PostgreSQL:
   ```bash
   systemctl restart postgresql
   ```

### Issue: Reindex fails with "index already exists"

**Cause:** Duplicate or corrupted index

**Solution:**
1. Drop corrupted index:
   ```sql
   DROP INDEX IF EXISTS index_name CASCADE;
   ```

2. Run reindex again

## Best Practices

### Scheduling
- ✅ Run during low-traffic periods (2-4 AM)
- ✅ Never run during peak hours
- ✅ Schedule weekly on production
- ❌ Don't run multiple operations simultaneously

### Testing
- ✅ Always use `--dry-run` first
- ✅ Test on staging environment
- ✅ Review output before running on production
- ❌ Don't run without dry-run on production

### Monitoring
- ✅ Set up alerts for failed maintenance
- ✅ Monitor disk space before/after
- ✅ Track execution time trends
- ✅ Review logs weekly

### Maintenance Windows
- ✅ Schedule during maintenance window
- ✅ Notify users of downtime
- ✅ Have rollback plan ready
- ✅ Monitor system during execution

## Command Reference

```bash
# Show help
python manage.py maintenance --help

# Run all operations (safe preview)
python manage.py maintenance --all --dry-run

# Run all operations (actually execute)
python manage.py maintenance --all

# Run specific operation
python manage.py maintenance --operation vacuum
python manage.py maintenance --operation reindex
python manage.py maintenance --operation cleanup --dry-run
python manage.py maintenance --operation logs
python manage.py maintenance --operation sessions
python manage.py maintenance --operation views
python manage.py maintenance --operation stats
python manage.py maintenance --operation stats --output json
python manage.py maintenance --operation bloat
python manage.py maintenance --operation backup

# Schedule maintenance (requires Celery Beat)
python manage.py maintenance --all --schedule daily
python manage.py maintenance --all --schedule weekly
python manage.py maintenance --all --schedule monthly
```

## Additional Resources

- [PostgreSQL VACUUM Documentation](https://www.postgresql.org/docs/current/sql-vacuum.html)
- [PostgreSQL REINDEX Documentation](https://www.postgresql.org/docs/current/sql-reindex.html)
- [Django Management Commands](https://docs.djangoproject.com/en/stable/ref/django-admin/)
- [Celery Beat Scheduler](https://docs.celeryproject.io/en/stable/userguide/periodic-tasks.html)

## Support

For issues or questions:

1. Check this guide for solutions
2. Review maintenance logs:
   ```python
   from core.models import TaskExecutionLog
   TaskExecutionLog.objects.filter(task_name='database_maintenance').latest('started_at')
   ```
3. Check database health:
   ```bash
   python manage.py system_health --json
   ```
4. Open issue with:
   - Command used
   - Output/error messages
   - Database size
   - Last successful run date
