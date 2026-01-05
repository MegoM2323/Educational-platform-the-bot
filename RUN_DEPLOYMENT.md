# 🚀 THE_BOT Platform - Manual Deployment Instructions

**For:** the-bot.ru domain deployment  
**Status:** ✅ Ready to deploy  
**Date:** 2026-01-05

---

## ⚠️ IMPORTANT: TTY Access Required

Docker startup requires interactive terminal for sudo password entry. 

**This means you need to run these commands in your terminal (not via script):**

---

## 🔧 STEP-BY-STEP DEPLOYMENT

### Step 1️⃣: Open Terminal and Navigate to Project

```bash
cd "/home/mego/Python Projects/THE_BOT_platform"
```

### Step 2️⃣: Start Docker Daemon (requires password)

```bash
sudo systemctl start docker
```

**When prompted:**
```
[sudo] password for mego: fstpass
```

**Expected output:**
```
✓ (no output = success, or "Warning: ..." = daemon already running)
```

Verify Docker is running:
```bash
docker ps
```

Should show:
```
CONTAINER ID   IMAGE   COMMAND   CREATED   STATUS   PORTS   NAMES
(empty table if no containers yet)
```

### Step 3️⃣: Build Docker Images

```bash
docker-compose -f docker-compose.prod.yml build --no-cache
```

**This takes 10-15 minutes. You'll see:**
```
Building backend
Building postgres
Building redis
...
Successfully built...
```

### Step 4️⃣: Start All Services

```bash
docker-compose -f docker-compose.prod.yml up -d
```

**Expected output:**
```
Creating thebot-postgres-prod ... done
Creating thebot-redis-prod    ... done
Creating thebot-backend-prod  ... done
Creating thebot-celery-worker-prod ... done
Creating thebot-celery-beat-prod   ... done
Creating thebot-nginx-prod    ... done
```

### Step 5️⃣: Wait for Services to Start

```bash
sleep 15
```

### Step 6️⃣: Run Database Migrations

```bash
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py migrate
```

**Expected output:**
```
Operations to perform:
  Apply all migrations: ...
Running migrations:
  Applying accounts.0001_initial ... OK
  Applying accounts.0002_alter_user_password ... OK
  ...
```

### Step 7️⃣: Collect Static Files

```bash
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py collectstatic --noinput
```

**Expected output:**
```
123 static files copied to '/app/staticfiles', 45 post-processed.
```

### Step 8️⃣: Create Admin User

```bash
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py createsuperuser
```

**When prompted, enter:**
```
Username: admin
Email: admin@the-bot.ru
Password: (your secure password)
Password (again): (confirm)
```

### Step 9️⃣: Check Service Status

```bash
docker-compose -f docker-compose.prod.yml ps
```

**Expected output - ALL should be "Up":**
```
NAME                              STATUS
thebot-postgres-prod              Up 2 minutes (healthy)
thebot-redis-prod                 Up 2 minutes
thebot-backend-prod               Up 2 minutes (healthy)
thebot-celery-worker-prod         Up 2 minutes
thebot-celery-beat-prod           Up 2 minutes
thebot-nginx-prod                 Up 2 minutes
```

### Step 🔟: Run Health Checks

```bash
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py check
```

**Expected output:**
```
System check identified no issues (0 silenced).
```

### Step 1️⃣1️⃣: Verify API Response

```bash
curl http://localhost/api/health/
```

**Expected output:**
```json
{"status": "ok", "version": "1.0.0"}
```

### Step 1️⃣2️⃣: View Logs

```bash
# See all logs
docker-compose -f docker-compose.prod.yml logs

# Follow logs (Ctrl+C to stop)
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs backend
```

---

## ✅ VERIFICATION CHECKLIST

After completing all steps, verify everything works:

### ✓ Frontend Access
```bash
# Should return HTML (frontend)
curl http://localhost/

# Or open in browser:
# http://localhost:80
```

### ✓ API Access
```bash
# Health check
curl http://localhost:8000/api/health/

# Expected: {"status": "ok", ...}
```

### ✓ Login Test
```bash
# Login with admin credentials
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "username": "admin",
    "password": "YOUR_PASSWORD"
  }'

# Expected: {"access": "JWT_TOKEN", "refresh": "..."}
```

### ✓ Database Check
```bash
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d thebot_db -c "SELECT COUNT(*) FROM accounts_user;"

# Expected: count
# -------
#     5
# (or more if you added users)
```

### ✓ Redis Check
```bash
docker-compose -f docker-compose.prod.yml exec redis \
  redis-cli PING

# Expected: PONG
```

### ✓ Celery Check
```bash
docker-compose -f docker-compose.prod.yml exec backend \
  celery -A config inspect active

# Expected: lists active Celery tasks
```

---

## 🌐 ACCESSING THE PLATFORM

### Local Access (for testing)
```
Frontend:  http://localhost
Backend:   http://localhost:8000/api/
Admin:     http://localhost:8000/admin/
```

### Domain Access (after DNS/SSL setup)
```
Frontend:  https://the-bot.ru
Backend:   https://the-bot.ru/api/
Admin:     https://the-bot.ru/admin/
```

---

## 🔒 SSL/TLS Setup (Domain)

When ready to use the-bot.ru domain:

### Step A: DNS Configuration
```
Domain: the-bot.ru
Points to: YOUR_SERVER_IP

Wait 5-15 minutes for DNS to propagate
```

### Step B: Get SSL Certificate
```bash
sudo apt-get install certbot python3-certbot-nginx

sudo certbot certonly --webroot \
  -w /var/www/certbot \
  -d the-bot.ru \
  -d www.the-bot.ru \
  --agree-tos \
  --email your-email@example.com
```

### Step C: Configure Nginx
```bash
sudo cp nginx/the-bot.ru.conf /etc/nginx/sites-available/the-bot.ru

sudo ln -s /etc/nginx/sites-available/the-bot.ru \
  /etc/nginx/sites-enabled/

sudo nginx -t

sudo systemctl reload nginx
```

### Step D: Verify HTTPS
```bash
curl https://the-bot.ru/

# Check certificate
openssl s_client -connect the-bot.ru:443
```

---

## 🐛 TROUBLESHOOTING

### Problem: Docker daemon won't start
```bash
# Check status
sudo systemctl status docker

# View logs
sudo journalctl -u docker -n 50

# Try again
sudo systemctl start docker
```

### Problem: Build fails
```bash
# Clean images
docker system prune -a

# Try build again
docker-compose -f docker-compose.prod.yml build --no-cache
```

### Problem: Services won't start
```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs

# Restart
docker-compose -f docker-compose.prod.yml restart

# Or rebuild from scratch
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
```

### Problem: Database connection error
```bash
# Check PostgreSQL
docker-compose -f docker-compose.prod.yml logs postgres

# Reset database
docker-compose -f docker-compose.prod.yml down -v
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml exec backend \
  python manage.py migrate
```

### Problem: Port already in use
```bash
# Kill process on port 80
sudo lsof -i :80
sudo kill -9 PID

# Or change port in docker-compose.prod.yml:
#   ports:
#     - "8080:80"  (instead of "80:80")
```

---

## 📊 MONITORING

### Check Container Status
```bash
docker ps
docker stats
```

### View Logs
```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs backend -f

# Last 100 lines
docker-compose -f docker-compose.prod.yml logs --tail=100
```

### Database Operations
```bash
# Connect to database
docker-compose -f docker-compose.prod.yml exec postgres \
  psql -U postgres -d thebot_db

# Common queries:
# \dt                     - list tables
# SELECT * FROM accounts_user;  - list users
# \q                      - quit
```

### Performance Monitoring
```bash
# CPU and memory usage
docker stats

# Disk usage
docker system df

# Network status
docker-compose -f docker-compose.prod.yml logs nginx
```

---

## 🎯 QUICK REFERENCE

### Start/Stop Services
```bash
# Start all
docker-compose -f docker-compose.prod.yml up -d

# Stop all
docker-compose -f docker-compose.prod.yml stop

# Restart
docker-compose -f docker-compose.prod.yml restart

# Down (removes containers, keeps volumes)
docker-compose -f docker-compose.prod.yml down

# Down with volume deletion (WARNING: loses data)
docker-compose -f docker-compose.prod.yml down -v
```

### Useful Commands
```bash
# View running services
docker-compose -f docker-compose.prod.yml ps

# Execute command in container
docker-compose -f docker-compose.prod.yml exec backend bash

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Rebuild images
docker-compose -f docker-compose.prod.yml build --no-cache

# Scale Celery workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3
```

---

## 📞 HELP & SUPPORT

**If deployment fails:**

1. ✅ Check Docker is running: `docker ps`
2. ✅ Check logs: `docker-compose -f docker-compose.prod.yml logs`
3. ✅ Verify files exist: `ls docker-compose.prod.yml .deploy.env`
4. ✅ Check disk space: `df -h`
5. ✅ Check memory: `free -h`

**Still having issues?**

- Review: `PRODUCTION_DEPLOYMENT_GUIDE.md`
- Check logs: `tail -f deployment-run.log`
- Restart everything: `docker-compose -f docker-compose.prod.yml restart`

---

## ✨ SUCCESS!

When you see:
```
✅ All containers UP and HEALTHY
✅ curl http://localhost returns 200 OK
✅ Admin panel accessible
✅ Login works with credentials
✅ Dashboard displays correctly
```

**Then THE_BOT Platform is successfully deployed!** 🎉

---

**Next Steps:**
1. Set up domain DNS (point to server IP)
2. Configure SSL with Let's Encrypt
3. Create real users and content
4. Set up monitoring/alerting
5. Configure automated backups

**Generated:** 2026-01-05  
**Platform:** THE_BOT Educational Platform

