# THE_BOT Platform - Deployment Configuration & Memory

## Server Configuration
- **IP**: 5.129.249.206
- **Domain**: the-bot.ru
- **User**: mg
- **Sudo Password**: fstpass
- **OS**: Ubuntu 24.04.3 LTS
- **Deployment Method**: Native (without Docker)

## Deployment Time
- **Direct (backend only)**: 2 minutes
- **Full (backend + frontend + nginx)**: 3 minutes
- **Docker (old method)**: 20+ minutes ❌
- **Improvement**: 6-7x faster ⚡

## Services Configuration

### Backend (Django + Daphne)
```
Port: 127.0.0.1:8000
ASGI Server: Daphne 4.2.1
Framework: Django 6.0
Database: PostgreSQL (localhost:5432)
Cache: Redis (localhost:6379)
Python: 3.12
Virtual Env: /opt/THE_BOT_platform/venv
Code: /opt/THE_BOT_platform/backend
Logs: /tmp/daphne.log
```

### Frontend (React + Vite)
```
Framework: React + TypeScript
Build Tool: Vite
Package Manager: npm (or bun)
Built Output: /opt/THE_BOT_platform/frontend/dist
Size: ~4.0K (highly optimized)
Node: 18+ required
```

### Reverse Proxy (Nginx)
```
Config: /etc/nginx/sites-available/thebot.conf
Enabled: /etc/nginx/sites-enabled/thebot.conf
HTTP Port: 80
HTTPS Port: 443
SSL Cert: /etc/nginx/ssl/cert.pem
SSL Key: /etc/nginx/ssl/key.pem
Log Error: /var/log/nginx/error.log
Log Access: /var/log/nginx/access.log
```

### SSL Certificate
```
Type: Self-signed (for testing)
Created: 2026-01-04
Expires: 2027-01-04 (365 days)
CN: the-bot.ru
Issuer: Self-signed
For Production: Use Let's Encrypt
```

## Database Configuration
```
Engine: PostgreSQL 15
Host: localhost
Port: 5432
Database: thebot_db
User: thebot_user
Password: thebot_secure_password_change_in_production
SSL Mode: disable (for development)
```

## Redis Cache Configuration
```
Host: localhost
Port: 6379
DB: 0 (default)
Password: none (local)
```

## Deployment Scripts

### 1. deploy-direct.sh (Backend Only)
**Usage**: `./deploy-direct.sh`
**Time**: ~2 minutes
**What it does**:
- Syncs backend code (rsync)
- Installs Python dependencies
- Sets up .env file
- Applies database migrations
- Starts Daphne ASGI server

### 2. deploy-full.sh (Complete Stack)
**Usage**: `./deploy-full.sh`
**Time**: ~3 minutes
**What it does**:
- Syncs backend + frontend
- Installs all dependencies
- Builds frontend (Vite)
- Configures Nginx
- Starts all services
- Verifies deployment

### 3. test-login-all-roles.sh (Login Tests)
**Usage**: `./test-login-all-roles.sh`
**Tests**: All 5 user roles
**Output**: Color-coded status report

## Test Accounts (DO NOT DELETE)

```
Role        Username    Password
─────────────────────────────────
Admin       admin       admin123
Student     student1    student123
Teacher     teacher1    teacher123
Tutor       tutor1      tutor123
Parent      parent1     parent123
```

## Common Commands

### SSH to Server
```bash
ssh mg@5.129.249.206
```

### Check Backend Status
```bash
ssh mg@5.129.249.206 'pgrep -f "daphne.*8000"'
ssh mg@5.129.249.206 'tail -f /tmp/daphne.log'
```

### Check Nginx Status
```bash
ssh mg@5.129.249.206 'sudo systemctl status nginx'
ssh mg@5.129.249.206 'sudo tail -f /var/log/nginx/error.log'
```

### Restart Services
```bash
# Backend
ssh mg@5.129.249.206 'pkill -f "daphne.*8000" && sleep 1 && cd /opt/THE_BOT_platform/backend && . /opt/THE_BOT_platform/venv/bin/activate && nohup daphne -b 127.0.0.1 -p 8000 -v 1 config.asgi:application &> /tmp/daphne.log &'

# Nginx (requires sudo)
ssh mg@5.129.249.206 'echo fstpass | sudo -S systemctl restart nginx'

# All
ssh mg@5.129.249.206 'echo fstpass | sudo -S systemctl restart nginx && pkill -f daphne; sleep 1; cd /opt/THE_BOT_platform/backend && . /opt/THE_BOT_platform/venv/bin/activate && nohup daphne -b 127.0.0.1 -p 8000 config.asgi:application &> /tmp/daphne.log &'
```

### Deploy Updates
```bash
# Quick (code changes only)
./deploy-direct.sh

# Full (with frontend rebuild)
./deploy-full.sh
```

## Local Machine Configuration

### Add to /etc/hosts
```bash
# macOS/Linux
echo "5.129.249.206 the-bot.ru www.the-bot.ru" >> /etc/hosts

# Windows (admin cmd)
echo 5.129.249.206 the-bot.ru www.the-bot.ru >> C:\Windows\System32\drivers\etc\hosts
```

### Access URLs
```
Frontend SPA:     https://the-bot.ru
API Endpoints:    https://the-bot.ru/api/
Admin Panel:      https://the-bot.ru/admin/
API Schema:       https://the-bot.ru/api/schema/
Health Check:     https://the-bot.ru/api/system/health/live/
```

## Nginx Configuration Structure
```
# Main upstream
upstream backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

# HTTP → HTTPS redirect
server { listen 80; ... }

# HTTPS secure server
server {
    listen 443 ssl http2;

    # Frontend SPA (try_files for routing)
    location / { root /opt/THE_BOT_platform/frontend; try_files $uri $uri/ /index.html; }

    # API endpoints (proxy to backend)
    location /api/ { proxy_pass http://backend; }

    # Admin panel (proxy to backend)
    location /admin/ { proxy_pass http://backend; }

    # Static files (Django admin, etc)
    location /static/ { alias /opt/THE_BOT_platform/backend/staticfiles/; }

    # Media files (uploads)
    location /media/ { alias /opt/THE_BOT_platform/backend/media/; }
}
```

## Django Migration History
- **Fixed**: CheckConstraint syntax (Django 5.0 compatibility)
  - Changed: `check=` → `condition=` parameter
  - Files: `invoices/migrations/0001_initial.py`, `0006_invoice_enrollment_and_more.py`
- **DB Host**: Changed from `postgres` (docker) to `localhost` (native)
- **WORKDIR**: Fixed Docker entrypoint path from `/app/backend` to `/app`

## Troubleshooting Guide

### Backend not starting
```bash
# Check logs
ssh mg@5.129.249.206 'tail -100 /tmp/daphne.log'

# Verify database connection
ssh mg@5.129.249.206 'psql -h localhost -U thebot_user -d thebot_db -c "SELECT 1"'

# Check Redis
ssh mg@5.129.249.206 'redis-cli ping'

# Restart manually
ssh mg@5.129.249.206 'pkill -9 daphne; sleep 1; ./deploy-direct.sh'
```

### Nginx not proxying correctly
```bash
# Test config
ssh mg@5.129.249.206 'sudo nginx -t'

# Check error log
ssh mg@5.129.249.206 'sudo tail -50 /var/log/nginx/error.log'

# Verify upstream is reachable
ssh mg@5.129.249.206 'curl http://127.0.0.1:8000/'

# Reload config
ssh mg@5.129.249.206 'echo fstpass | sudo -S nginx -s reload'
```

### Frontend not loading
```bash
# Check if built
ssh mg@5.129.249.206 'ls -la /opt/THE_BOT_platform/frontend/dist/'

# Rebuild
ssh mg@5.129.249.206 'cd /opt/THE_BOT_platform/frontend && npm run build'

# Check Nginx can serve it
ssh mg@5.129.249.206 'curl http://127.0.0.1/index.html'
```

### SSL certificate expired (future)
```bash
# Renew self-signed
ssh mg@5.129.249.206 'echo fstpass | sudo -S openssl req -x509 -newkey rsa:2048 -keyout /etc/nginx/ssl/key.pem -out /etc/nginx/ssl/cert.pem -days 365 -nodes -subj "/C=RU/CN=the-bot.ru"'

# Or use Let's Encrypt (recommended for production)
ssh mg@5.129.249.206 'echo fstpass | sudo -S certbot certonly --webroot -w /var/www/certbot -d the-bot.ru'
```

## Production Checklist

- [ ] Replace self-signed SSL with Let's Encrypt
- [ ] Configure proper DNS (A record pointing to 5.129.249.206)
- [ ] Remove /etc/hosts workaround
- [ ] Setup PostgreSQL daily backups
- [ ] Configure monitoring/alerting
- [ ] Setup log rotation
- [ ] Configure firewall rules
- [ ] Setup fail2ban for brute-force protection
- [ ] Enable HSTS header in Nginx
- [ ] Configure CORS properly
- [ ] Setup uptime monitoring
- [ ] Configure CDN for static assets

## Useful Links & References
- Django Docs: https://docs.djangoproject.com/
- Daphne: https://github.com/django/daphne
- React: https://react.dev
- Vite: https://vitejs.dev
- Nginx: https://nginx.org/en/docs/
- PostgreSQL: https://www.postgresql.org/docs/

---
**Last Updated**: 2026-01-04
**Status**: ✅ DEPLOYED AND RUNNING
**Maintainer Notes**: Keep this file updated when deployment configs change
