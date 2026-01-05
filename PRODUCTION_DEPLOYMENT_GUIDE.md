# 🚀 THE_BOT Platform - Production Deployment Guide

**Status:** ✅ Ready for deployment  
**Domain:** the-bot.ru  
**Date:** 2026-01-05

---

## 📋 TABLE OF CONTENTS

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checks](#pre-deployment-checks)
3. [Automated Deployment](#automated-deployment)
4. [Manual Steps](#manual-steps)
5. [SSL/TLS Setup](#ssltls-setup)
6. [Verification](#verification)
7. [Troubleshooting](#troubleshooting)
8. [Rollback](#rollback)

---

## ✅ PREREQUISITES

### System Requirements
```
- OS: Ubuntu 20.04 LTS or newer
- CPU: 4 cores minimum (8+ recommended)
- RAM: 8GB minimum (16GB recommended)
- Disk: 50GB SSD minimum
- Network: 100 Mbps upload/download
```

### Software Requirements
```
✅ Docker 20.10+
✅ Docker Compose v2+
✅ Git
✅ OpenSSL (for certificate management)
✅ Nginx (or use Docker version)
```

### Installation Command
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker-compose --version
```

---

## 🔍 PRE-DEPLOYMENT CHECKS

### 1. Clone Repository
```bash
cd /home/mego/Python\ Projects
git clone <repo-url> THE_BOT_platform || cd THE_BOT_platform
git checkout main
git pull origin main
```

### 2. Verify Configuration
```bash
cd /home/mego/Python\ Projects/THE_BOT_platform

# Check required files
ls -la docker-compose.prod.yml
ls -la .deploy.env
ls -la backend/
ls -la frontend/

# Verify git status
git status
git log --oneline -5
```

### 3. Check Environment Variables
```bash
# Create .env.prod if not exists
cp .deploy.env .env.prod

# Required variables:
echo "Checking required env vars..."
grep -E "^(ENVIRONMENT|DEBUG|DATABASE|REDIS|SECRET)" .env.prod
```

### 4. Verify Database Connection
```bash
# Test PostgreSQL (if external)
psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -c "\dt"

# Or use Docker's built-in PostgreSQL
# (will be created automatically)
```

---

## 🤖 AUTOMATED DEPLOYMENT

### Option 1: Interactive Deployment (Recommended)

```bash
cd /home/mego/Python\ Projects/THE_BOT_platform

# Make script executable
chmod +x DEPLOY_INTERACTIVE.sh

# Run interactive deployment
# You will be prompted for:
# - Sudo password: fstpass
# - Confirmation before starting real deployment
./DEPLOY_INTERACTIVE.sh
```

**What this does:**
1. ✅ Starts Docker daemon
2. ✅ Verifies Docker installation
3. ✅ Runs pre-deployment checks
4. ✅ Builds Docker images
5. ✅ Starts all services
6. ✅ Runs database migrations
7. ✅ Collects static files
8. ✅ Runs health checks

### Option 2: Docker Compose Direct

```bash
cd /home/mego/Python\ Projects/THE_BOT_platform

# Build images
docker-compose -f docker-compose.prod.yml build --no-cache

# Start services
docker-compose -f docker-compose.prod.yml up -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check status
docker-compose -f docker-compose.prod.yml ps
```

---

## 🔧 MANUAL STEPS

### Step 1: Build Docker Images
```bash
docker-compose -f docker-compose.prod.yml build

# With specific version
docker-compose -f docker-compose.prod.yml build --tag thebot:20260105
```

### Step 2: Start Services
```bash
# Start all services in background
docker-compose -f docker-compose.prod.yml up -d

# Or run in foreground for debugging
docker-compose -f docker-compose.prod.yml up
```

### Step 3: Run Database Migrations
```bash
# Apply migrations
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py migrate

# Check migration status
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py showmigrations
```

### Step 4: Collect Static Files
```bash
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py collectstatic --noinput --clear
```

### Step 5: Create Superuser (Optional)
```bash
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py createsuperuser
```

### Step 6: Verify Services
```bash
# Check all containers running
docker-compose -f docker-compose.prod.yml ps

# Check logs for errors
docker-compose -f docker-compose.prod.yml logs

# Test API
curl http://localhost:8000/api/health/
curl http://localhost:80/

# Test WebSocket (should work)
wscat -c ws://localhost:8000/ws/notifications/
```

---

## 🔒 SSL/TLS SETUP

### Step 1: Install Certbot
```bash
sudo apt-get update
sudo apt-get install certbot python3-certbot-nginx
```

### Step 2: Request SSL Certificate
```bash
# For the-bot.ru domain
sudo certbot certonly --webroot \
  -w /var/www/certbot \
  -d the-bot.ru \
  -d www.the-bot.ru \
  --agree-tos \
  --email your-email@example.com \
  -n

# Certificate will be at:
# /etc/letsencrypt/live/the-bot.ru/
```

### Step 3: Configure Nginx
```bash
# Copy nginx config
sudo cp nginx/the-bot.ru.conf /etc/nginx/sites-available/the-bot.ru

# Enable site
sudo ln -s /etc/nginx/sites-available/the-bot.ru /etc/nginx/sites-enabled/

# Test nginx config
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### Step 4: Auto-Renewal Setup
```bash
# Enable certbot auto-renewal
sudo systemctl enable certbot.timer

# Test renewal (dry-run)
sudo certbot renew --dry-run

# Check renewal status
sudo certbot certificates
```

### Step 5: Verify HTTPS
```bash
curl https://the-bot.ru/

# Check SSL certificate
openssl s_client -connect the-bot.ru:443

# Check certificate expiration
curl https://the-bot.ru/ | grep -i certificate
```

---

## ✅ VERIFICATION

### Health Checks
```bash
# Check all containers healthy
docker-compose -f docker-compose.prod.yml ps

# Expected output:
# STATUS: Up X minutes (health: healthy)

# Run Django checks
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py check

# Expected output:
# System check identified no issues (0 silenced).

# Check database
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py dbshell -c "\dt"

# Check Redis
docker-compose -f docker-compose.prod.yml exec redis \
  redis-cli PING
# Expected: PONG

# Check Celery
docker-compose -f docker-compose.prod.yml exec backend \
  celery -A config inspect active
```

### API Endpoints
```bash
# Health endpoint
curl https://the-bot.ru/api/health/
# Expected: 200 OK

# Authentication
curl -X POST https://the-bot.ru/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"..."}'
# Expected: 200 OK with JWT token

# Dashboard
curl -H "Authorization: Bearer TOKEN" \
  https://the-bot.ru/api/student/dashboard/
# Expected: 200 OK with dashboard data

# Admin panel
curl https://the-bot.ru/admin/
# Expected: 200 OK (Django admin)
```

### Frontend
```bash
# Test frontend at root
curl https://the-bot.ru/
# Expected: 200 OK, HTML content

# Test static files
curl https://the-bot.ru/static/main.js
curl https://the-bot.ru/static/main.css
# Expected: 200 OK

# Test in browser
# Go to https://the-bot.ru
# Should see: THE_BOT Platform login page
```

---

## 🐛 TROUBLESHOOTING

### Docker Daemon Not Running
```bash
# Start Docker
sudo systemctl start docker

# Enable auto-start
sudo systemctl enable docker

# Check status
sudo systemctl status docker

# If error: need password
# Ensure your user is in docker group:
sudo usermod -aG docker $USER
newgrp docker
```

### Database Connection Error
```bash
# Check PostgreSQL container
docker-compose -f docker-compose.prod.yml logs postgres

# Test connection
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d thebot_db -c "SELECT 1"

# Reset database (WARNING: loses data)
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py migrate
```

### API Not Responding
```bash
# Check Django logs
docker-compose -f docker-compose.prod.yml logs backend

# Check Nginx logs
docker-compose -f docker-compose.prod.yml logs nginx

# Restart services
docker-compose -f docker-compose.prod.yml restart backend nginx
```

### SSL Certificate Issues
```bash
# Check certificate validity
openssl x509 -in /etc/letsencrypt/live/the-bot.ru/fullchain.pem -text -noout

# Renew manually
sudo certbot renew --force-renewal

# Check renewal logs
sudo journalctl -u certbot.timer -n 20

# Fix permissions
sudo chmod -R 755 /etc/letsencrypt/live/
sudo chmod -R 755 /etc/letsencrypt/archive/
```

### WebSocket Connection Issues
```bash
# Check WebSocket logs
docker-compose -f docker-compose.prod.yml logs backend

# Test WebSocket connection
# Install wscat:
npm install -g wscat

# Connect:
wscat -c ws://the-bot.ru/ws/notifications/YOUR_USER_ID/

# Expected: {"type": "message", "message": "connected"}
```

---

## 🔄 ROLLBACK

### Rollback to Previous Version
```bash
# View backup timestamps
ls -la backups/

# Find latest backup
BACKUP_DATE="20260104_150000"

# Stop current services
docker-compose -f docker-compose.prod.yml down

# Restore database
pg_restore -U postgres -d thebot_db \
  backups/db_backup_${BACKUP_DATE}.sql

# Restore code (if needed)
git checkout $(git log --oneline | head -1 | awk '{print $1}')

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

### Quick Rollback Script
```bash
# Create file: rollback.sh
#!/bin/bash

BACKUP="${1:?Specify backup timestamp: YYYYMMDD_HHMMSS}"
PROJECT_DIR="/home/mego/Python Projects/THE_BOT_platform"

cd "$PROJECT_DIR"

echo "⚠ Rolling back to $BACKUP..."

# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore database
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_restore -U postgres -d thebot_db \
  /backups/db_backup_${BACKUP}.sql || echo "Restore failed"

# Restart
docker-compose -f docker-compose.prod.yml up -d

echo "✓ Rollback complete"

# Usage:
# bash rollback.sh 20260104_150000
```

---

## 📊 MONITORING & LOGS

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last N lines
docker-compose -f docker-compose.prod.yml logs --tail=100 nginx

# With timestamps
docker-compose -f docker-compose.prod.yml logs --timestamps
```

### Container Resources
```bash
# Monitor CPU and memory
docker stats

# Disk usage
docker system df

# Clean up unused images/containers
docker system prune

# Deep clean (WARNING: removes all unused)
docker system prune -a
```

### Performance Metrics
```bash
# Django debug toolbar (if enabled)
# Go to: https://the-bot.ru/?debug=1

# Database query logging
docker-compose -f docker-compose.prod.yml exec backend \
  tail -f logs/queries.log

# Slow query log
docker-compose -f docker-compose.prod.yml exec postgres \
  tail -f /var/log/postgresql/postgresql.log | grep "duration"

# Celery monitoring
docker-compose -f docker-compose.prod.yml exec backend \
  celery -A config events
```

---

## 📞 SUPPORT

### Critical Issues Contact
```
Email: devops@the-bot.ru
Slack: #production-alerts
On-call: Check Slack pinned message
```

### Useful Commands Summary
```bash
# Status check
docker-compose -f docker-compose.prod.yml ps

# Restart services
docker-compose -f docker-compose.prod.yml restart

# Stop all
docker-compose -f docker-compose.prod.yml down

# Full restart
docker-compose -f docker-compose.prod.yml down -v && \
docker-compose -f docker-compose.prod.yml up -d

# Backup database
docker-compose -f docker-compose.prod.yml exec postgres \
  pg_dump -U postgres thebot_db > backup_$(date +%s).sql

# Check logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

---

## ✨ SUMMARY

### Deployment Checklist
- [ ] Prerequisites installed (Docker, Docker Compose)
- [ ] Repository cloned and on main branch
- [ ] Configuration files present (.deploy.env, docker-compose.prod.yml)
- [ ] Disk space verified (>50GB)
- [ ] Database backup created (if existing)
- [ ] Interactive deployment script run successfully
- [ ] All health checks passed
- [ ] SSL certificate installed
- [ ] Domain DNS pointing to server
- [ ] HTTPS working (test at https://the-bot.ru/)
- [ ] Admin user created
- [ ] Monitoring configured
- [ ] Backup automated

### Success Indicators
```
✅ docker-compose ps shows all containers UP
✅ curl https://the-bot.ru/ returns 200 OK
✅ curl https://the-bot.ru/api/health/ returns 200 OK
✅ Browser access at https://the-bot.ru shows login page
✅ Login works with test/admin credentials
✅ Dashboard displays correctly
✅ Static files served (CSS, JS, images)
✅ Nginx reverse proxy working
✅ SSL certificate valid (check in browser)
✅ All services healthy
```

---

**Generated:** 2026-01-05  
**Platform:** THE_BOT Educational Platform  
**Environment:** Production on the-bot.ru

