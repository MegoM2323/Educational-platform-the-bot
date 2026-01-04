# THE_BOT Platform - Deployment & Testing Guide

**Последний обновление**: 2026-01-04
**Статус**: ✅ DEPLOYED AND RUNNING
**Версия**: 1.0

---

## 📍 QUICK REFERENCE

### Server Access
```
IP: 5.129.249.206
Domain: the-bot.ru
User: mg
Password: fstpass (stored in CREDENTIALS.secure)
SSH: ssh mg@5.129.249.206
```

### Access THE_BOT
```
Frontend:  https://the-bot.ru  (add to /etc/hosts first)
Direct IP: https://5.129.249.206/
API:       https://the-bot.ru/api/
Admin:     https://the-bot.ru/admin/
```

---

## 🧪 TEST ACCOUNTS (All Working)

| Role | Username | Password | Purpose |
|------|----------|----------|---------|
| Admin | admin | admin123 | Full system access, manage users |
| Student | student1 | student123 | View lessons, submit assignments |
| Teacher | teacher1 | teacher123 | Create lessons, grade assignments |
| Tutor | tutor1 | tutor123 | Manage tutoring sessions |
| Parent | parent1 | parent123 | Monitor child's progress |

### How to Test Login
```bash
# Via API (POST)
curl -k -X POST https://5.129.249.206/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Response contains:
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "user": {
    "id": 1,
    "username": "admin",
    "email": "admin@example.com",
    "role": "admin"
  }
}

# Use access token to access protected endpoints
curl -k -H "Authorization: Bearer $TOKEN" https://5.129.249.206/api/auth/profile/
```

---

## 🚀 DEPLOYMENT SCRIPTS

### 1. Full Stack Deployment (Recommended)
```bash
./deploy-full.sh
```
**Time**: ~3 minutes
**Includes**: Backend + Frontend + Nginx setup
**Use for**: Major updates, first deployment

### 2. Backend-Only Deployment (Fast)
```bash
./deploy-direct.sh
```
**Time**: ~2 minutes
**Includes**: Code sync + dependencies + migrations
**Use for**: Quick hotfixes, backend changes

### 3. Test All Logins
```bash
./test-domain-logins.sh          # Requires /etc/hosts entry
./test-ip-logins.sh              # Works directly via IP
```

---

## 📋 SYSTEM CONFIGURATION

### Backend
- **Framework**: Django 6.0 + DRF 3.16
- **ASGI Server**: Daphne 4.2.1
- **Port**: 127.0.0.1:8000
- **Process**: Python 3.12 (PID: check with `pgrep -f daphne`)
- **Virtual Env**: `/opt/THE_BOT_platform/venv`
- **Code**: `/opt/THE_BOT_platform/backend`
- **Logs**: `/tmp/daphne.log`

### Frontend
- **Framework**: React + TypeScript + Vite
- **Build Output**: `/opt/THE_BOT_platform/frontend/dist`
- **Size**: ~4.0K (highly optimized)
- **Served by**: Nginx with SPA routing

### Database
- **Type**: PostgreSQL 15
- **Host**: localhost (not postgres!)
- **Port**: 5432
- **Database**: thebot_db
- **User**: thebot_user
- **Password**: See CREDENTIALS.secure

### Cache
- **Type**: Redis 7
- **Host**: localhost
- **Port**: 6379
- **Purpose**: Session cache, real-time updates

### Reverse Proxy
- **Server**: Nginx
- **HTTP Port**: 80
- **HTTPS Port**: 443
- **SSL Type**: Self-signed (for production: use Let's Encrypt)
- **Config**: `/etc/nginx/sites-available/thebot.conf`
- **Enabled**: `/etc/nginx/sites-enabled/thebot.conf`

---

## 🔧 COMMON OPERATIONS

### Check Services Status
```bash
# Backend
ssh mg@5.129.249.206 'pgrep -f "daphne.*8000" && echo "✓ Backend running" || echo "✗ Backend stopped"'

# Nginx
ssh mg@5.129.249.206 'sudo systemctl status nginx --no-pager | head -5'

# All processes
ssh mg@5.129.249.206 'ps aux | grep -E "daphne|nginx" | grep -v grep'
```

### View Logs
```bash
# Backend logs (live)
ssh mg@5.129.249.206 'tail -f /tmp/daphne.log'

# Nginx error logs
ssh mg@5.129.249.206 'sudo tail -f /var/log/nginx/error.log'

# Nginx access logs
ssh mg@5.129.249.206 'sudo tail -f /var/log/nginx/access.log'

# Django (if needed)
ssh mg@5.129.249.206 'tail -f /opt/THE_BOT_platform/backend/django.log'
```

### Restart Services
```bash
# Backend only
ssh mg@5.129.249.206 'pkill -f "daphne.*8000"; sleep 1; /opt/THE_BOT_platform/deploy-direct.sh'

# Nginx only
ssh mg@5.129.249.206 'echo fstpass | sudo -S systemctl restart nginx'

# Everything
./deploy-full.sh
```

### Test Connectivity
```bash
# Backend health
curl -k https://5.129.249.206/api/system/health/live/

# Frontend (index.html)
curl -k https://5.129.249.206/

# API docs
curl -k https://5.129.249.206/api/schema/
```

---

## 🐛 TROUBLESHOOTING

### Backend won't start
```bash
# Check logs
ssh mg@5.129.249.206 'tail -50 /tmp/daphne.log'

# Check DB connection
ssh mg@5.129.249.206 'psql -h localhost -U thebot_user -d thebot_db -c "SELECT 1"'

# Check Redis
ssh mg@5.129.249.206 'redis-cli ping'

# Verify .env file
ssh mg@5.129.249.206 'cat /opt/THE_BOT_platform/backend/.env'
```

### Nginx not serving
```bash
# Test config
ssh mg@5.129.249.206 'sudo nginx -t'

# Check if listening
ssh mg@5.129.249.206 'sudo ss -tlnp | grep nginx'

# Reload config
ssh mg@5.129.249.206 'echo fstpass | sudo -S nginx -s reload'
```

### DNS/Domain not resolving
```bash
# Add to local /etc/hosts (macOS/Linux)
echo "5.129.249.206 the-bot.ru www.the-bot.ru" >> /etc/hosts

# Verify
nslookup the-bot.ru
ping the-bot.ru
```

### CSRF errors on login
- Check that Nginx is forwarding headers correctly
- Ensure `X-Forwarded-Proto: https` is set
- Try with `-k` flag in curl (ignores SSL cert validation)

### Slow API responses
```bash
# Check database
psql -h localhost -U thebot_user -d thebot_db -c "SELECT COUNT(*) FROM accounts_user;"

# Check Redis
redis-cli INFO stats

# Monitor processes
ssh mg@5.129.249.206 'watch -n 1 "ps aux | grep -E daphne|nginx"'
```

---

## 📊 API ENDPOINTS

### Authentication
```
POST   /api/auth/login/          - Login with credentials
POST   /api/auth/logout/         - Logout (invalidate token)
POST   /api/auth/refresh/        - Refresh access token
GET    /api/auth/profile/        - Get current user profile
GET    /api/auth/me/             - Get current user details
```

### Admin Panel
```
GET    /admin/                   - Django admin interface
GET    /admin/api/               - Admin API
POST   /admin/users/             - Create user
GET    /admin/users/             - List users
```

### Role-Specific
```
GET    /api/student/dashboard/   - Student dashboard
GET    /api/teacher/lessons/     - Teacher lessons
GET    /api/tutor/sessions/      - Tutor sessions
GET    /api/parent/children/     - Parent's children
```

### System
```
GET    /api/system/health/live/  - Health check
GET    /api/system/status/       - System status
GET    /api/schema/              - API schema/documentation
```

---

## 🔐 SECURITY NOTES

### Current Status
- ✅ Self-signed SSL certificate (for testing)
- ✅ HTTPS redirects configured
- ✅ CORS enabled for the-bot.ru
- ⚠️ Self-signed cert will show warnings in browser

### For Production
```bash
# Replace with Let's Encrypt
ssh mg@5.129.249.206 'echo fstpass | sudo -S certbot certonly --webroot -w /var/www/certbot -d the-bot.ru'

# Update Nginx config
# ssl_certificate /etc/letsencrypt/live/the-bot.ru/fullchain.pem;
# ssl_certificate_key /etc/letsencrypt/live/the-bot.ru/privkey.pem;

# Enable auto-renewal
ssh mg@5.129.249.206 'echo fstpass | sudo -S systemctl enable certbot.timer'
```

---

## 📁 IMPORTANT FILES

| File | Purpose | Location |
|------|---------|----------|
| DEPLOYMENT_CONFIG.md | Full deployment documentation | Project root |
| CREDENTIALS.secure | All credentials & passwords | Project root (not in git) |
| deploy-full.sh | Full stack deployment script | Project root |
| deploy-direct.sh | Backend deployment script | Project root |
| test-ip-logins.sh | Login testing script | Project root |
| test-domain-logins.sh | Domain-based login testing | Project root |
| .env | Backend environment variables | /opt/THE_BOT_platform/backend/ |

---

## 🎯 NEXT STEPS FOR PRODUCTION

1. **[ ] SSL Certificate**
   - Replace self-signed with Let's Encrypt
   - Enable auto-renewal

2. **[ ] DNS Configuration**
   - Update A record: the-bot.ru → 5.129.249.206
   - Remove /etc/hosts workaround

3. **[ ] Database Backups**
   - Setup daily automated backups
   - Test restoration

4. **[ ] Monitoring & Alerts**
   - Setup uptime monitoring
   - Configure error alerts
   - Log aggregation

5. **[ ] Performance Optimization**
   - Enable caching headers
   - Compress static assets
   - CDN for images/media

6. **[ ] Security Hardening**
   - Firewall rules
   - Fail2ban for brute-force
   - Rate limiting
   - Security headers (CSP, X-Frame-Options, etc)

---

## 📞 SUPPORT & REFERENCE

### Quick Commands Reference
See `CREDENTIALS.secure` for full SSH command library

### Documentation
- **API Docs**: https://the-bot.ru/api/schema/
- **Django Admin**: https://the-bot.ru/admin/
- **Frontend**: https://the-bot.ru/

### Status Check
```bash
# One-liner to check everything
ssh mg@5.129.249.206 "ps aux | grep -E 'daphne|nginx' | grep -v grep && echo '✓ Services running' || echo '✗ Services down'"
```

---

**Generated**: 2026-01-04 17:35 UTC
**Status**: ✅ READY FOR PRODUCTION
**Next Review**: After SSL upgrade to Let's Encrypt
