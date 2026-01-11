# THE_BOT Platform Deployment System

Complete native systemd deployment for production.

## Overview

Single entry point deployment: `./deploy.sh` from project root.

Uses RSYNC for fast code sync + automatic backup/rollback + service management.

## Quick Reference

| Command | Purpose |
|---------|---------|
| `./deploy.sh` | Full deployment (interactive) |
| `./deploy.sh --dry-run` | Preview mode |
| `./deploy.sh --skip-migrations --force` | Hotfix (fast) |

## Configuration

**File**: `deploy/.env`

See `deploy/.env.template` for all available options.

Key variables:
- `PROD_USER=mg`
- `PROD_SERVER=5.129.249.206`
- `PROD_HOME=/home/mg/THE_BOT_platform`

## Modules

### deploy/lib/shared.sh
Shared functions for all modules:
- Color output functions (log, success, error, warning, info)
- SSH execution helpers
- Service management utilities
- File/path validation

### deploy/backup.sh
Creates backups before deployment:
- Backend code tar.gz (excludes .git, .venv, etc.)
- Frontend dist tar.gz (if exists)
- PostgreSQL database dump

Returns: `BACKUP_TIMESTAMP` for rollback

### deploy/sync.sh
Synchronizes code to production:
- Frontend build (npm install + npm run build)
- Backend rsync (21 exclusion rules)
- Frontend dist rsync

Supports: `--dry-run` for preview

### deploy/migrate.sh
Database operations:
- Pre-migration check
- Django migrate (if not --skip-migrations)
- Collect static files

### deploy/services.sh
Systemd service management:
- Restart thebot-daphne.service
- Restart thebot-celery-worker.service
- Restart thebot-celery-beat.service
- Verify services are active

### deploy/health.sh
Post-deployment verification:
- Service health checks (with retry)
- API endpoint checks
- Disk usage monitoring

Retry logic: 10 attempts, 2 sec interval

### deploy/rollback.sh
Automatic error recovery:
- Stops services
- Restores code from backup
- Restores database
- Restarts services
- Verifies health

## Deployment Flow

```
1. Parse arguments + load config
2. Pre-checks (SSH, disk, services)
3. Backup (code + DB)
4. Sync (rsync backend + frontend)
5. Migrate (Django migrations + collectstatic)
6. Restart services
7. Health checks
8. Report (✅ success or ❌ error)

On error at any step → auto-rollback to backup
```

## Log Files

Deployment logs: `${PROD_HOME}/logs/deploy_${TIMESTAMP}.log`

Example: `/home/mg/THE_BOT_platform/logs/deploy_20250111_143022.log`

## Troubleshooting

### Services won't restart
```bash
ssh mg@5.129.249.206
systemctl status thebot-daphne.service
journalctl -u thebot-daphne.service -n 50
```

### Rollback failed
Logs at: `/home/mg/backups/BACKUP_REFERENCE_*.txt`

### Check deployment status
```bash
tail -f /home/mg/THE_BOT_platform/logs/deploy_*.log
```

## Performance

- Full deployment: 5-10 minutes
- Hotfix (--skip-migrations): 2-3 minutes
- Dry-run: 1-2 minutes

## Security

- No secrets in code
- SSH key-based authentication only
- Backup retention: 7 days
- Disk space validation before backup
