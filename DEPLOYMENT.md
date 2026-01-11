# THE_BOT Platform - Deployment Guide

## Overview

Main deployment orchestrator script for THE_BOT platform. Coordinates all deployment phases through modular shell scripts.

## Quick Start

```bash
# Full interactive deployment
./deploy.sh

# Dry-run mode (preview without making changes)
./deploy.sh --dry-run

# Force deployment without confirmation
./deploy.sh --force

# Hotfix deployment (skip migrations)
./deploy.sh --skip-migrations --force

# Verbose logging for debugging
./deploy.sh --verbose
```

## Architecture

```
deploy.sh (Main Orchestrator)
    │
    ├── deploy/pre-checks.sh      (Phase 0: Pre-flight checks)
    ├── deploy/backup.sh          (Phase 1: Database & config backup)
    ├── deploy/sync.sh            (Phase 2: Code synchronization via rsync)
    ├── deploy/migrate.sh         (Phase 3: Django migrations & static files)
    ├── deploy/services.sh        (Phase 4: Service restart)
    ├── deploy/health.sh          (Phase 5: Health checks)
    ├── deploy/rollback.sh        (On error: Automatic rollback)
    │
    ├── deploy/.env               (Configuration file)
    └── deploy/lib/shared.sh      (Shared library with common functions)
```

## Configuration

Edit `deploy/.env` to customize deployment settings:

```bash
# Production Server
PROD_SERVER=mg@5.129.249.206
PROD_HOME=/home/mg/THE_BOT_platform

# Python & Backup
VENV_PATH=/home/mg/venv
BACKUP_DIR=/home/mg/backups

# Services
SERVICES="thebot-daphne.service thebot-celery-worker.service thebot-celery-beat.service"

# Health Checks
HEALTH_CHECK_URL=http://localhost:8001/api/health/
HEALTH_CHECK_TIMEOUT=30
HEALTH_CHECK_RETRIES=3
```

## Deployment Phases

### Phase 0: Pre-Checks
- SSH connectivity verification
- Disk space validation
- System services check
- Git status verification

### Phase 1: Backup
- Database dump creation
- Configuration backup
- .env credentials preservation
- Backup compression and retention

### Phase 2: Sync
- Backend code synchronization (rsync)
- Frontend code synchronization
- Scripts synchronization
- Smart exclusions (cache, venv, etc.)

### Phase 3: Migrate
- Django database migrations
- Static files collection
- Cache clearing

### Phase 4: Services
- systemd service restart
- Service health verification
- Gradual startup monitoring

### Phase 5: Health Checks
- Service status verification
- API health endpoint testing
- Disk space final check

### Rollback (on error)
- Automatic rollback if any phase fails
- Service restart from last stable state
- Credentials restoration

## Usage Examples

### Standard Deployment
```bash
cd /home/mego/Python\ Projects/THE_BOT_platform
./deploy.sh
```

### Preview Changes
```bash
./deploy.sh --dry-run
```

### Quick Hotfix
```bash
./deploy.sh --skip-migrations --force --verbose
```

### Skip Frontend Build
```bash
./deploy.sh --skip-frontend --force
```

## Error Handling

- **Pre-checks fail**: Deployment aborts, no changes made
- **Sync fails**: Services not restarted, previous version active
- **Migration fails**: Rollback triggered automatically
- **Service restart fails**: Rollback triggered, old services restarted

## Logs

Deployment logs are stored in:
```
./logs/deploy_YYYYMMDD_HHMMSS.log
```

## Debugging

Enable verbose logging to see detailed execution:
```bash
./deploy.sh --verbose
```

This will show:
- All SSH commands executed
- Detailed phase information
- Full command output

## SSH Configuration

Ensure SSH connection to production server works:
```bash
ssh mg@5.129.249.206 "echo OK"
```

### Known Issues & Solutions

**"SSH connection failed"**
- Check network connectivity
- Verify SSH key is configured
- Ensure key has correct permissions

**"Disk usage critical"**
- SSH to production and clean up old files
- Remove old backups: `rm -f /home/mg/backups/db_backup_*.sql.gz`

**"Service failed to restart"**
- Check service status: `systemctl status thebot-daphne.service`
- Review logs: `journalctl -u thebot-daphne.service -n 50`

## Environment Variables (Export Before Running)

```bash
export VERBOSE=true           # Enable verbose logging
export DRY_RUN=true          # Preview mode
export FORCE_DEPLOY=true     # Skip confirmations
```

## Post-Deployment Verification

After successful deployment:
```bash
# Check service status
ssh mg@5.129.249.206 "systemctl status thebot-daphne.service"

# View application logs
ssh mg@5.129.249.206 "journalctl -u thebot-daphne.service -f"

# Check API health
ssh mg@5.129.249.206 "curl -s http://localhost:8001/api/health/"
```

## Support

For issues or questions, check:
- Main log file in `./logs/`
- Production service logs via SSH
- System disk space and resources
