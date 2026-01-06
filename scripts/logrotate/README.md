# Log Rotation Configuration

## Overview
Logrotate configuration for THE_BOT platform ensures persistent storage of logs in `/var/log/thebot/` with automatic rotation.

## Installation

### Manual Installation
```bash
# Copy logrotate configuration
sudo cp scripts/logrotate/thebot /etc/logrotate.d/thebot

# Verify installation
ls -la /etc/logrotate.d/thebot
```

### Automated Installation (via deploy script)
The deployment script automatically creates `/var/log/thebot/` directory with proper permissions during PHASE 0.

## Configuration Details

**Location**: `/etc/logrotate.d/thebot`

**Logs rotated**:
- `/var/log/thebot/audit.log`
- `/var/log/thebot/admin.log`
- `/var/log/thebot/celery.log`
- `/var/log/thebot/error.log`

**Rotation policy**:
- **Frequency**: Daily
- **Retention**: 7 days (7 rotated files kept)
- **Compression**: gzip (after 1 day delay)
- **Permissions**: 0640 (owner read/write, group read)
- **Owner**: www-data:www-data

**Post-rotation action**:
- Reloads Nginx configuration (non-blocking)

## Directory Structure

```
/var/log/thebot/
├── audit.log              # Audit trail (INFO level)
├── admin.log              # Admin actions (INFO level)
├── celery.log             # Celery task logs (INFO level)
├── error.log              # Error logs (ERROR level)
├── audit.log.1.gz         # Previous day (compressed)
├── audit.log.2.gz         # 2 days ago (compressed)
└── ...
```

## Logging Configuration (Django)

Django logging handlers are configured in `backend/config/settings.py`:

```python
"handlers": {
    "audit_file": {
        "class": "logging.handlers.RotatingFileHandler",
        "filename": "/var/log/thebot/audit.log",
        "maxBytes": 10485760,  # 10MB per file
        "backupCount": 10,     # Keep 10 backup files
        "level": "INFO",
        "formatter": "audit",
    },
    # ... other handlers
}
```

## Systemd Service Integration

All systemd service files automatically create `/var/log/thebot/` directory before starting:

```bash
ExecStartPre=/bin/mkdir -p /var/log/thebot
ExecStartPre=/bin/chown mg:mg /var/log/thebot
ExecStartPre=/bin/chmod 755 /var/log/thebot
```

## Verification

### Check logrotate is working
```bash
# Test logrotate configuration
sudo logrotate -d /etc/logrotate.d/thebot

# View logrotate status
sudo logrotate -v /etc/logrotate.d/thebot
```

### Check log files
```bash
# List current logs
ls -lh /var/log/thebot/

# View recent entries
tail -f /var/log/thebot/error.log

# Check rotation schedule
stat /var/log/thebot/audit.log
```

### Monitor disk usage
```bash
du -sh /var/log/thebot/
du -sh /var/log/thebot/*.gz
```

## Troubleshooting

### Logs not rotating
```bash
# Check logrotate runs daily via cron
sudo ls -la /etc/cron.daily/
grep logrotate /etc/cron.daily/*

# Run manually for testing
sudo logrotate -f /etc/logrotate.d/thebot
```

### Permission denied errors
```bash
# Fix ownership
sudo chown -R mg:mg /var/log/thebot
sudo chmod 755 /var/log/thebot
sudo chmod 640 /var/log/thebot/*.log
```

### Directory doesn't exist
```bash
# Create and set permissions
sudo mkdir -p /var/log/thebot
sudo chown mg:mg /var/log/thebot
sudo chmod 755 /var/log/thebot

# Restart services
sudo systemctl restart thebot-backend thebot-celery-worker thebot-celery-beat
```

## Related Files
- Django logging config: `backend/config/settings.py` (lines 1045-1076)
- Backend service: `scripts/deployment/thebot-backend.service`
- Celery worker service: `scripts/deployment/thebot-celery-worker.service`
- Celery beat service: `scripts/deployment/thebot-celery-beat.service`
- Universal deploy script: `scripts/deployment/universal-deploy.sh`
