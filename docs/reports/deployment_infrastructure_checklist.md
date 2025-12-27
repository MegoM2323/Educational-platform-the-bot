# Deployment Infrastructure Checklist

**Date**: December 27, 2025
**Platform**: THE_BOT Educational Platform v1.0.0
**Status**: Ready for Deployment

---

## Pre-Deployment Environment Setup

### 1. Secret & Configuration Management

#### 1.1 Generate Production SECRET_KEY

- [ ] Run Django secret key generator
  ```bash
  python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
  ```
- [ ] Store in secure vault (not in version control)
- [ ] Update .env file: `SECRET_KEY=<generated-key>`
- [ ] Minimum length: 50 characters (verified)
- [ ] Rotation policy: Every 90 days

**Expected**: 50+ character random string

---

#### 1.2 Database Configuration

- [ ] Provision PostgreSQL instance (Supabase or self-managed)
  - [ ] Version: 15+ (recommended)
  - [ ] Create database: `thebot_prod`
  - [ ] Create user with appropriate permissions
  - [ ] Enable SSL/TLS connections
  - [ ] Configure backup schedule

- [ ] Set environment variables:
  ```
  DATABASE_URL=postgresql://user:password@host:5432/db
  DB_CONNECT_TIMEOUT=60
  DB_SSLMODE=require
  ```

**Verification**:
```bash
psql $DATABASE_URL -c "SELECT version();"
```

---

#### 1.3 Redis/Cache Configuration

- [ ] Provision Redis instance
  - [ ] Version: 7+ (recommended)
  - [ ] Memory: 512MB minimum
  - [ ] Persistence: Enabled (appendonly)
  - [ ] Password: Strong authentication
  - [ ] Replication: Configure for HA (optional)

- [ ] Set environment variables:
  ```
  REDIS_URL=redis://:password@host:6379/0
  REDIS_PASSWORD=<strong-password>
  USE_REDIS_CACHE=True
  ```

**Verification**:
```bash
redis-cli -u $REDIS_URL ping
```

---

#### 1.4 Web Server Configuration (ALLOWED_HOSTS)

- [ ] Set ALLOWED_HOSTS environment variable
  ```
  ALLOWED_HOSTS=thebot.example.com,www.thebot.example.com,api.thebot.example.com
  ```

- [ ] Update FRONTEND_URL
  ```
  FRONTEND_URL=https://thebot.example.com
  ```

- [ ] Update API endpoints
  ```
  API_URL=https://api.thebot.example.com
  WS_URL=wss://api.thebot.example.com/ws
  ```

---

#### 1.5 CORS Configuration

- [ ] Set CORS_ALLOWED_ORIGINS
  ```
  CORS_ALLOWED_ORIGINS=https://thebot.example.com,https://www.thebot.example.com
  ```

**Verification**: Only frontend domain(s) should be listed

---

### 2. SSL/TLS Certificate Setup

#### 2.1 Obtain Certificates

- [ ] Option 1: Let's Encrypt (Free)
  ```bash
  certbot certonly --standalone -d thebot.example.com -d www.thebot.example.com
  ```

- [ ] Option 2: Purchased certificates
  - [ ] Store certificate files securely
  - [ ] Verify certificate validity
  - [ ] Check certificate chain

**Certificate Locations** (typical):
- Private key: `/etc/letsencrypt/live/thebot.example.com/privkey.pem`
- Certificate: `/etc/letsencrypt/live/thebot.example.com/fullchain.pem`

---

#### 2.2 Configure Auto-Renewal

- [ ] Setup certbot auto-renewal
  ```bash
  certbot renew --dry-run
  ```

- [ ] Add to crontab (daily check)
  ```bash
  0 3 * * * certbot renew --quiet
  ```

- [ ] Verify renewal works
  ```bash
  systemctl start certbot.timer
  systemctl enable certbot.timer
  ```

---

#### 2.3 Test HTTPS Configuration

- [ ] Test SSL configuration
  ```bash
  openssl s_client -connect thebot.example.com:443
  ```

- [ ] Verify SSL Labs rating (target: A+)
  - Visit: https://www.ssllabs.com/ssltest/

---

### 3. Reverse Proxy Setup (Nginx)

#### 3.1 Install & Configure Nginx

- [ ] Install Nginx
  ```bash
  sudo apt-get install nginx
  ```

- [ ] Configure main site block
  ```nginx
  server {
      listen 443 ssl http2;
      server_name thebot.example.com;

      ssl_certificate /path/to/cert.pem;
      ssl_certificate_key /path/to/key.pem;

      # Django backend
      location /api/ {
          proxy_pass http://backend:8000;
          proxy_set_header Host $host;
          proxy_set_header X-Real-IP $remote_addr;
          proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
          proxy_set_header X-Forwarded-Proto $scheme;
      }

      # WebSocket
      location /ws/ {
          proxy_pass http://backend:8000;
          proxy_http_version 1.1;
          proxy_set_header Upgrade $http_upgrade;
          proxy_set_header Connection "upgrade";
      }

      # Frontend
      location / {
          proxy_pass http://frontend:3000;
      }
  }

  # Redirect HTTP to HTTPS
  server {
      listen 80;
      server_name _;
      return 301 https://$host$request_uri;
  }
  ```

- [ ] Test configuration
  ```bash
  sudo nginx -t
  ```

- [ ] Enable and start Nginx
  ```bash
  sudo systemctl enable nginx
  sudo systemctl start nginx
  ```

---

### 4. Environment File Setup

#### 4.1 Create Production .env

```bash
# Core
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generated-key>
ADMIN_SECRET_URL=<custom-admin-url>

# Database
DATABASE_URL=postgresql://user:pass@host:5432/db
DB_CONNECT_TIMEOUT=60
DB_SSLMODE=require

# Redis
REDIS_URL=redis://:password@host:6379/0
USE_REDIS_CACHE=True

# Web Server
FRONTEND_URL=https://thebot.example.com
ALLOWED_HOSTS=thebot.example.com,www.thebot.example.com
API_URL=https://api.thebot.example.com
WS_URL=wss://api.thebot.example.com/ws

# CORS
CORS_ALLOWED_ORIGINS=https://thebot.example.com,https://www.thebot.example.com

# External Services
YOOKASSA_SHOP_ID=<actual-shop-id>
YOOKASSA_SECRET_KEY=<actual-secret>
OPENROUTER_API_KEY=<actual-key>
PACHCA_FORUM_API_TOKEN=<actual-token>
TELEGRAM_BOT_TOKEN=<actual-token>

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=<app-password>

# Monitoring
SENTRY_DSN=<actual-dsn>
LOG_LEVEL=INFO
```

- [ ] Store .env file securely (not in version control)
- [ ] Use secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- [ ] Restrict file permissions: `chmod 600 .env`

---

## Docker & Container Setup

### 5. Docker Image Preparation

#### 5.1 Build Docker Images

- [ ] Build backend image
  ```bash
  docker build -f backend/Dockerfile -t thebot-backend:1.0.0 ./backend
  ```

- [ ] Build frontend image
  ```bash
  docker build -f frontend/Dockerfile -t thebot-frontend:1.0.0 ./frontend
  ```

- [ ] Tag for registry
  ```bash
  docker tag thebot-backend:1.0.0 registry.example.com/thebot-backend:1.0.0
  docker tag thebot-frontend:1.0.0 registry.example.com/thebot-frontend:1.0.0
  ```

- [ ] Push to container registry
  ```bash
  docker push registry.example.com/thebot-backend:1.0.0
  docker push registry.example.com/thebot-frontend:1.0.0
  ```

---

#### 5.2 Verify Image Security

- [ ] Scan images for vulnerabilities
  ```bash
  trivy image registry.example.com/thebot-backend:1.0.0
  ```

- [ ] Check image size (should be optimized)
  - Backend: <400MB
  - Frontend: <100MB

- [ ] Verify non-root user in images
  ```bash
  docker inspect registry.example.com/thebot-backend:1.0.0 | grep -i user
  ```

---

### 6. Docker Compose Deployment

#### 6.1 Update Docker Compose File

- [ ] Set environment variables in docker-compose.yml or .env file
- [ ] Update image tags to production versions
- [ ] Configure volume mounts for logs and data
- [ ] Set resource limits appropriately

#### 6.2 Deploy Services

- [ ] Start services in correct order
  ```bash
  docker-compose up -d postgres redis
  sleep 30
  docker-compose up -d backend frontend
  ```

- [ ] Verify services are running
  ```bash
  docker-compose ps
  ```

- [ ] Check logs for errors
  ```bash
  docker-compose logs -f backend
  ```

---

## Database Initialization

### 7. Database Setup

#### 7.1 Run Migrations

- [ ] Apply all migrations
  ```bash
  docker exec thebot-backend python manage.py migrate
  ```

- [ ] Verify migrations applied
  ```bash
  docker exec thebot-backend python manage.py showmigrations --list
  ```

#### 7.2 Create Admin User

- [ ] Create superuser
  ```bash
  docker exec -it thebot-backend python manage.py createsuperuser
  ```

  Answer prompts:
  - Username: admin
  - Email: admin@example.com
  - Password: <strong-password>

#### 7.3 Load Test Data (Optional)

- [ ] Create test users
  ```bash
  docker exec thebot-backend python ../create_test_users.py
  ```

#### 7.4 Collect Static Files

- [ ] Collect static files
  ```bash
  docker exec thebot-backend python manage.py collectstatic --noinput
  ```

---

## Monitoring & Observability Setup

### 8. Logging Configuration

#### 8.1 Configure Log Aggregation

- [ ] Option 1: ELK Stack (Elasticsearch, Logstash, Kibana)
  - Deploy Elasticsearch
  - Deploy Logstash
  - Deploy Kibana
  - Configure Filebeat on host

- [ ] Option 2: Loki + Grafana
  - Deploy Loki
  - Deploy Grafana
  - Configure Promtail

- [ ] Option 3: SaaS Solution (Datadog, Splunk, etc.)
  - Sign up for service
  - Install agent
  - Configure log shipping

#### 8.2 Verify Logs Are Being Collected

- [ ] Check log files are being written
  ```bash
  tail -f backend_logs/audit.log
  tail -f backend_logs/admin.log
  tail -f backend_logs/celery.log
  ```

- [ ] Verify logs appear in aggregation service

---

### 9. Metrics & Monitoring

#### 9.1 Setup Prometheus

- [ ] Deploy Prometheus
  ```yaml
  # prometheus.yml
  global:
    scrape_interval: 15s

  scrape_configs:
    - job_name: 'thebot-backend'
      static_configs:
        - targets: ['localhost:8000']
      metrics_path: '/api/system/metrics/prometheus/'
  ```

- [ ] Verify metrics collection
  ```bash
  curl http://localhost:9090/api/v1/query?query=up
  ```

#### 9.2 Setup Grafana

- [ ] Deploy Grafana
- [ ] Add Prometheus data source
- [ ] Import dashboards
- [ ] Create alerts

#### 9.3 Setup Sentry (Error Tracking)

- [ ] Sign up for Sentry account
- [ ] Create project
- [ ] Note DSN value
- [ ] Set SENTRY_DSN environment variable
- [ ] Test error reporting
  ```bash
  curl http://localhost:8000/api/test-sentry-error/
  ```

---

### 10. Uptime Monitoring

#### 10.1 Configure External Uptime Monitoring

- [ ] Option 1: Pingdom
  - Create uptime check
  - Monitor /api/system/health/live/

- [ ] Option 2: Uptime.com
  - Create monitoring service
  - Configure alerts

- [ ] Option 3: Synthetic monitoring
  - Deploy synthetic monitoring
  - Create test scenarios

#### 10.2 Verify Health Check Endpoints

- [ ] Test liveness endpoint
  ```bash
  curl -w "\nHTTP Status: %{http_code}\n" https://api.thebot.example.com/api/system/health/live/
  ```

- [ ] Test readiness endpoint
  ```bash
  curl -w "\nHTTP Status: %{http_code}\n" https://api.thebot.example.com/api/system/readiness/
  ```

- [ ] Test full health endpoint
  ```bash
  curl -w "\nHTTP Status: %{http_code}\n" https://api.thebot.example.com/api/system/health/
  ```

---

## Security Hardening

### 11. Production Security

#### 11.1 Firewall Configuration

- [ ] Configure firewall rules
  - Allow HTTP (80) → redirect to HTTPS
  - Allow HTTPS (443)
  - Allow SSH (22) - restricted IP
  - Deny all other ports

- [ ] Example (UFW):
  ```bash
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw allow 22/tcp
  sudo ufw enable
  ```

#### 11.2 Database Security

- [ ] Configure database access controls
  - [ ] Only backend service can connect
  - [ ] VPC/network isolation
  - [ ] SSL/TLS enforcement
  - [ ] Daily automated backups

- [ ] Change default passwords
  - [ ] PostgreSQL admin user
  - [ ] Redis password

#### 11.3 API Key Management

- [ ] Rotate API keys
  - [ ] YOOKASSA_SECRET_KEY
  - [ ] OPENROUTER_API_KEY
  - [ ] PACHCA_FORUM_API_TOKEN
  - [ ] TELEGRAM_BOT_TOKEN

- [ ] Store in secrets manager (not in .env)

#### 11.4 SSH Key Management

- [ ] Generate SSH keys for server access
  ```bash
  ssh-keygen -t ed25519 -f thebot_deploy
  ```

- [ ] Add public key to server authorized_keys
- [ ] Store private key securely
- [ ] Disable password SSH login
  ```bash
  PermitRootLogin no
  PasswordAuthentication no
  ```

---

## Backup & Disaster Recovery

### 12. Backup Configuration

#### 12.1 Database Backups

- [ ] Configure automated backups
  ```bash
  # Daily backup at 3 AM UTC
  0 3 * * * pg_dump $DATABASE_URL | gzip > /backups/db-$(date +%Y%m%d).sql.gz
  ```

- [ ] Store backups off-site
  - [ ] S3 bucket
  - [ ] Google Cloud Storage
  - [ ] Azure Blob Storage
  - [ ] Local backup server

- [ ] Verify backup integrity
  ```bash
  gunzip -t /backups/db-*.sql.gz
  ```

#### 12.2 Full System Backup

- [ ] Backup volumes
  ```bash
  docker run --rm -v postgres_data:/data -v /backups:/backups \
    alpine tar czf /backups/postgres-data-$(date +%Y%m%d).tar.gz -C /data .
  ```

- [ ] Backup configuration files
  - .env file (encrypted)
  - nginx configuration
  - SSL certificates

#### 12.3 Test Restore Procedure

- [ ] Document restore procedure
- [ ] Test restore to staging environment
- [ ] Verify data integrity after restore
- [ ] Document recovery time objective (RTO)

---

## Testing & Validation

### 13. Pre-Production Testing

#### 13.1 Smoke Tests

- [ ] Test basic functionality
  - [ ] Frontend loads
  - [ ] API responds
  - [ ] Database is accessible
  - [ ] Redis is accessible
  - [ ] WebSocket connects

#### 13.2 Load Testing

- [ ] Tool: Apache JMeter, Locust, or similar
  ```bash
  locust -f locustfile.py -u 1000 -r 100 --run-time 10m
  ```

- [ ] Test scenarios:
  - [ ] 100 concurrent users
  - [ ] 500 concurrent users
  - [ ] 1000 concurrent users

- [ ] Verify performance metrics:
  - [ ] Response time < 500ms (p95)
  - [ ] Error rate < 0.1%
  - [ ] CPU usage < 80%
  - [ ] Memory usage < 80%

#### 13.3 Security Testing

- [ ] OWASP Top 10 validation
  - [ ] SQL injection tests
  - [ ] XSS tests
  - [ ] CSRF tests
  - [ ] Authentication bypass tests

- [ ] SSL/TLS testing
  ```bash
  nmap --script ssl-enum-ciphers -p 443 thebot.example.com
  ```

#### 13.4 API Testing

- [ ] Test all endpoints with valid data
- [ ] Test all endpoints with invalid data
- [ ] Test rate limiting
- [ ] Test authentication failures
- [ ] Test CORS enforcement

---

### 14. User Acceptance Testing

#### 14.1 Create UAT Plan

- [ ] Test script for each major feature
- [ ] Test data preparation
- [ ] User roles to test (Student, Teacher, Tutor, Parent, Admin)

#### 14.2 Execute UAT

- [ ] Student workflows
  - [ ] Login and view materials
  - [ ] Submit assignments
  - [ ] View progress
  - [ ] Participate in chat

- [ ] Teacher workflows
  - [ ] Create materials
  - [ ] View student progress
  - [ ] Grade assignments
  - [ ] Create chat room

- [ ] Admin workflows
  - [ ] User management
  - [ ] System monitoring
  - [ ] Generate reports

#### 14.3 Document Issues & Fixes

- [ ] Create issue log
- [ ] Prioritize and fix critical issues
- [ ] Re-test after fixes
- [ ] Get sign-off from stakeholders

---

## Post-Deployment Validation

### 15. Production Sign-Off Checklist

#### 15.1 Core Services

- [ ] Backend API responding (HTTP 200)
- [ ] Frontend accessible (loads without errors)
- [ ] Database connected and queryable
- [ ] Redis cache working
- [ ] WebSocket connections active

#### 15.2 Health Checks

- [ ] Liveness check: `/api/system/health/live/` → HTTP 200
- [ ] Readiness check: `/api/system/readiness/` → HTTP 200
- [ ] System health: `/api/system/health/` → all components ok
- [ ] Metrics: `/api/system/metrics/` → data available

#### 15.3 Functionality

- [ ] User login/logout working
- [ ] Data persistence verified
- [ ] File uploads working
- [ ] Real-time chat functional
- [ ] Reports generation working
- [ ] Payment processing working

#### 15.4 Monitoring & Alerts

- [ ] Error logs being captured
- [ ] Metrics being collected
- [ ] Alerts configured and testing
- [ ] PagerDuty/SMS notifications working

#### 15.5 Backup System

- [ ] Daily backups running
- [ ] Backup verification passing
- [ ] Restore procedure tested
- [ ] Off-site backup verified

#### 15.6 Security

- [ ] HTTPS working and enforced
- [ ] Security headers present
- [ ] SSL Labs score: A or A+
- [ ] No hardcoded secrets in logs
- [ ] API rate limiting working

---

### 16. Post-Deployment Monitoring (Week 1)

#### 16.1 Daily Checks

- [ ] Error rate < 0.1%
- [ ] API response time < 500ms
- [ ] CPU usage < 70% average
- [ ] Memory usage < 80% average
- [ ] Disk usage < 80%
- [ ] Zero failed health checks

#### 16.2 Weekly Review

- [ ] Review error logs
- [ ] Review performance metrics
- [ ] Review user feedback
- [ ] Verify backup success
- [ ] Check for security issues

#### 16.3 Ongoing Maintenance

- [ ] Monthly security updates
- [ ] Monthly backup restore test
- [ ] Quarterly performance review
- [ ] Annual security audit

---

## Documentation & Handover

### 17. Documentation

#### 17.1 Required Documentation

- [ ] Deployment guide (this checklist)
- [ ] Operational runbook
  - [ ] Common issues and solutions
  - [ ] Emergency procedures
  - [ ] Troubleshooting guide

- [ ] Architecture documentation
  - [ ] System diagram
  - [ ] Network topology
  - [ ] Data flow diagrams

- [ ] API documentation
  - [ ] Endpoint reference
  - [ ] Authentication guide
  - [ ] Error codes

#### 17.2 Handover Materials

- [ ] Credentials package (secured)
  - [ ] Admin accounts
  - [ ] SSH keys
  - [ ] API keys
  - [ ] Database passwords

- [ ] Support contact information
  - [ ] On-call rotation
  - [ ] Escalation path
  - [ ] Support hours

---

## Rollback Plan

### 18. Rollback Procedure

#### 18.1 Quick Rollback (if critical issue)

```bash
# Stop current deployment
docker-compose down

# Restore from backup
docker-compose up -d postgres
# ... restore database from backup

# Start with previous version
docker-compose up -d
```

#### 18.2 Communication

- [ ] Notify all stakeholders
- [ ] Set up status page notification
- [ ] Document issue and cause
- [ ] Create post-mortem

---

## Sign-Off

- [ ] DevOps Engineer: _________________ Date: _______
- [ ] System Administrator: __________ Date: _______
- [ ] Product Manager: ________________ Date: _______
- [ ] Security Officer: ________________ Date: _______

---

**Deployment Checklist Version**: 1.0
**Last Updated**: December 27, 2025
**Status**: READY FOR DEPLOYMENT
