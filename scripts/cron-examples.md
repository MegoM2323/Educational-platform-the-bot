# Secret Rotation Cron Job Examples

## Overview

The rotate-secrets.sh script can be run automatically via cron for regular rotation.

## Rotation Strategies

### Strategy 1: Weekly (Recommended)

Rotate all secrets once per week at 2 AM Sunday:

```cron
0 2 * * 0 /opt/vault/scripts/rotate-secrets.sh >> /var/log/vault-rotation.log 2>&1
```

Pros: Balances security and operational overhead
Cons: 7-day gap if secret compromised

### Strategy 2: Monthly

Rotate all secrets on the 1st at 1 AM:

```cron
0 1 1 * * /opt/vault/scripts/rotate-secrets.sh >> /var/log/vault-rotation.log 2>&1
```

Pros: Minimal overhead
Cons: Slower response to compromised secrets

### Strategy 3: Quarterly

Rotate every 3 months:

```cron
0 1 1 */3 * /opt/vault/scripts/rotate-secrets.sh >> /var/log/vault-rotation.log 2>&1
```

### Strategy 4: Staggered

Different schedules for different secret types:

```cron
# Django weekly
0 2 * * 0 /opt/vault/scripts/rotate-secrets.sh django

# PostgreSQL monthly
0 2 1 * * /opt/vault/scripts/rotate-secrets.sh postgres

# Redis monthly
0 3 1 * * /opt/vault/scripts/rotate-secrets.sh redis

# API keys quarterly
0 2 1 */3 * /opt/vault/scripts/rotate-secrets.sh apis
```

### Strategy 5: Aggressive

Daily or bi-weekly for high-security environments:

```cron
# Daily Django rotation
0 3 * * * /opt/vault/scripts/rotate-secrets.sh django

# Bi-weekly API keys
0 2 * * 0,3 /opt/vault/scripts/rotate-secrets.sh apis

# Weekly full rotation
0 1 * * 0 /opt/vault/scripts/rotate-secrets.sh
```

## Complete Crontab Example

```cron
# Environment
VAULT_ADDR=https://vault.the-bot.ru:8200
VAULT_TOKEN=s.xxxxxxxxxx
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin

# Backup before rotation
45 1 * * 0 /opt/vault/scripts/rotate-secrets.sh --backup

# Weekly rotation
0 2 * * 0 /opt/vault/scripts/rotate-secrets.sh

# Verification
15 2 * * 0 /opt/vault/scripts/verify-rotation.sh

# Health check
0 9 * * * /opt/vault/scripts/check-rotation.sh

# Cleanup old backups
0 5 * * * find /opt/vault/backups -name "*.json" -mtime +30 -delete
```

## Monitoring & Alerts

Check rotation status:

```bash
# View logs
tail -f /var/log/vault-rotation.log

# Check last run
stat -c %y /var/log/vault-rotation.log

# Look for errors
grep -i error /var/log/vault-rotation.log
```

## Slack Notification

Add notification after rotation:

```cron
# After weekly rotation
0 3 * * 0 curl -X POST \
  -d '{"text":"Weekly Vault rotation completed"}' \
  $SLACK_WEBHOOK_URL
```

## Setup Instructions

```bash
# 1. Make script executable
chmod +x /opt/vault/scripts/rotate-secrets.sh

# 2. Test manually
/opt/vault/scripts/rotate-secrets.sh --dry-run

# 3. Edit crontab
crontab -e

# 4. Add one of the examples above

# 5. Verify cron job
crontab -l | grep rotate-secrets
```

---

Last Updated: December 27, 2025
