# THE_BOT Platform - Production Deployment Guide

Production-grade Docker Compose configuration with full infrastructure setup.

## Quick Start

```bash
# 1. Generate SSL certificates
./docker/generate-ssl.sh your-domain.com

# 2. Configure environment
cp .env.production .env.prod
# Edit .env.prod with your production settings

# 3. Start services
./docker/start-production.sh --build

# 4. Access the platform
# - Frontend:    https://your-domain.com
# - Backend API: https://your-domain.com/api
# - Admin Panel: https://your-domain.com/admin
```

## Architecture

```
┌──────────────────────────────────────────────────────────┐
│                    NGINX (Port 80/443)                  │
│              Reverse Proxy + Load Balancer               │
└──────────────────┬───────────────────────────────────────┘
                   │
        ┌──────────┼──────────┐
        │          │          │
        ▼          ▼          ▼
   ┌────────┐  ┌────────┐ ┌─────────┐
   │Backend │  │Frontend│ │  Static │
   │(8000)  │  │(3000)  │ │  Files  │
   └───┬────┘  └────────┘ └─────────┘
       │
   ┌───┴────────────────────────────┐
   │                                │
   ▼                                ▼
┌──────────────┐          ┌──────────────────┐
│ PostgreSQL   │          │     Redis        │
│  (5432)      │          │    (6379)        │
└──────────────┘          └────────┬─────────┘
                                   │
                          ┌────────┴────────┐
                          │                 │
                          ▼                 ▼
                      ┌─────────┐    ┌────────────┐
                      │ Celery  │    │ Celery     │
                      │ Workers │    │ Beat       │
                      └─────────┘    │ Scheduler  │
                                     └────────────┘
```

## Services Configuration

### 1. PostgreSQL 15 (postgres)

**Container**: `thebot-postgres-prod`

```bash
# Access PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d thebot_db

# Backup database
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U postgres thebot_db > backup.sql

# Restore database
docker-compose -f docker-compose.prod.yml exec -T postgres psql -U postgres thebot_db < backup.sql
```

**Features**:
- Replication-ready with WAL archiving
- Max connections: 200
- Shared buffers: 256MB
- Effective cache: 1GB
- Work memory: 16MB per connection
- Maintenance memory: 64MB
- AOF persistence
- Regular backups (mounted at `./database/backups`)

**Health Check**: Enabled (10s interval, 5 retries)

**Volumes**:
- `postgres_data`: Database files
- `./database/init-scripts`: Initialization SQL
- `./database/backups`: Backup directory

**Resource Limits**:
- CPU: 4 cores (limit) / 2 cores (reserved)
- Memory: 2GB (limit) / 1GB (reserved)

### 2. Redis 7 (redis)

**Container**: `thebot-redis-prod`

```bash
# Access Redis CLI
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a redis

# Check memory usage
docker-compose -f docker-compose.prod.yml exec redis redis-cli INFO memory

# Monitor commands
docker-compose -f docker-compose.prod.yml exec redis redis-cli MONITOR
```

**Features**:
- Append-Only File (AOF) persistence
- Max memory: 512MB with LRU eviction
- Replication-ready
- Keyspace notifications enabled
- Slow log monitoring
- TCP keepalive

**Health Check**: Enabled (10s interval, 5 retries)

**Volumes**:
- `redis_data`: AOF persistence file
- `./redis/redis.conf`: Configuration file

**Resource Limits**:
- CPU: 2 cores (limit) / 1 core (reserved)
- Memory: 1GB (limit) / 512MB (reserved)

### 3. Django Backend (backend)

**Container**: `thebot-backend-prod`

```bash
# Access Django shell
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic
```

**Features**:
- Daphne ASGI server (supports WebSocket)
- Running on port 8000
- Automatic migrations on startup
- Static files collection
- Health checks enabled
- Proper error handling

**Health Check**: Enabled (30s interval after 40s startup)

**Volumes**:
- `./backend`: Application code (read-only)
- `backend_static`: Collected static files
- `backend_media`: User-uploaded media
- `backend_logs`: Application logs

**Resource Limits**:
- CPU: 4 cores (limit) / 2 cores (reserved)
- Memory: 2GB (limit) / 1GB (reserved)

### 4. React Frontend (frontend)

**Container**: `thebot-frontend-prod`

```bash
# View frontend logs
docker-compose -f docker-compose.prod.yml logs -f frontend

# Rebuild frontend
docker-compose -f docker-compose.prod.yml build frontend
```

**Features**:
- Built with Vite
- Served via Nginx
- Port 3000
- SPA routing with fallback to index.html
- Automatic cache busting

**Health Check**: Enabled (30s interval after 10s startup)

**Volumes**:
- `./frontend/dist`: Built application
- `./frontend/nginx.conf`: Nginx config
- `frontend_logs`: Access logs

**Resource Limits**:
- CPU: 1 core (limit) / 0.5 cores (reserved)
- Memory: 512MB (limit) / 256MB (reserved)

### 5. Nginx Reverse Proxy (nginx)

**Container**: `thebot-nginx-prod`

```bash
# Check Nginx status
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Reload Nginx config
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# View Nginx logs
docker-compose -f docker-compose.prod.yml logs -f nginx
```

**Features**:
- HTTPS/HTTP gateway
- Load balancing to backend
- Static file serving
- WebSocket support
- Rate limiting
- Gzip compression
- Caching
- Security headers
- OCSP stapling
- TLS 1.2 & 1.3

**Configuration**: `./docker/nginx.prod.conf`

**Health Check**: Enabled (30s interval after 10s startup)

**Volumes**:
- `./docker/nginx.prod.conf`: Configuration
- `./docker/ssl`: SSL certificates
- `backend_static`: Backend static files
- `frontend_dist`: Frontend build
- `nginx_cache`: Cache directory
- `nginx_logs`: Access logs

**Resource Limits**:
- CPU: 2 cores (limit) / 1 core (reserved)
- Memory: 512MB (limit) / 256MB (reserved)

### 6. Celery Workers (celery-worker)

**Container**: `thebot-celery-worker-prod`

```bash
# View worker logs
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# Scale to 3 workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3

# Inspect worker status
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A config inspect active

# Purge tasks
docker-compose -f docker-compose.prod.yml exec celery-worker celery -A config purge
```

**Features**:
- Background task processing
- Concurrency: 4 workers
- Prefetch: 4 tasks
- Max tasks per child: 1000
- Automatic reconnection
- Task result backend via Redis
- Full logging

**Configuration**:
- Broker: Redis DB 1
- Results: Redis DB 2
- Concurrency: 4 (scalable)

**Resource Limits**:
- CPU: 2 cores (limit) / 1 core (reserved)
- Memory: 1GB (limit) / 512MB (reserved)

### 7. Celery Beat Scheduler (celery-beat)

**Container**: `thebot-celery-beat-prod`

```bash
# View scheduler logs
docker-compose -f docker-compose.prod.yml logs -f celery-beat

# Inspect scheduled tasks
docker-compose -f docker-compose.prod.yml exec celery-beat celery -A config inspect scheduled
```

**Features**:
- Scheduled task execution
- Database scheduler (django-celery-beat)
- Automatic task registration
- Timezone-aware scheduling

**Configuration**:
- Scheduler: DatabaseScheduler
- Broker: Redis DB 1
- Results: Redis DB 2

**Resource Limits**:
- CPU: 1 core (limit) / 0.5 cores (reserved)
- Memory: 512MB (limit) / 256MB (reserved)

## Environment Configuration

Create `.env.production`:

```bash
cp .env.production.example .env.production
```

Edit key variables:

```env
# Core
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=your-secret-key-min-50-chars

# Database (use separate DB_* variables instead of DATABASE_URL)
DB_HOST=db.example.com
DB_PORT=5432
DB_NAME=thebot_db
DB_USER=postgres
DB_PASSWORD=strong-password
DB_SSLMODE=require

# Redis
REDIS_PASSWORD=strong-password

# Frontend
FRONTEND_URL=https://your-domain.com
VITE_API_URL=https://your-domain.com/api
VITE_WS_URL=wss://your-domain.com/ws

# HTTPS & Security
ALLOWED_HOSTS=your-domain.com,www.your-domain.com

# Email
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Payment (YooKassa)
YOOKASSA_SHOP_ID=your-shop-id
YOOKASSA_SECRET_KEY=your-secret-key
YOOKASSA_WEBHOOK_URL=https://your-domain.com/api/webhooks/yookassa/

# API Keys
OPENROUTER_API_KEY=your-key
PACHCA_API_TOKEN=your-token
TELEGRAM_BOT_TOKEN=your-token
```

### Database Configuration Details

The platform uses individual `DB_*` environment variables instead of a single `DATABASE_URL`:

| Variable | Required | Example | Description |
|----------|----------|---------|-------------|
| `DB_HOST` | Yes | `db.example.com` | PostgreSQL hostname or IP |
| `DB_PORT` | No | `5432` | PostgreSQL port (default: 5432) |
| `DB_NAME` | Yes | `thebot_db` | Database name |
| `DB_USER` | Yes | `postgres` | Database user |
| `DB_PASSWORD` | Yes | `strong-password` | Database password |
| `DB_SSLMODE` | No | `require` | SSL mode (require/prefer/disable) |
| `DB_CONNECT_TIMEOUT` | No | `60` | Connection timeout in seconds (default: 60) |

#### Migration from DATABASE_URL

If you have existing deployments using `DATABASE_URL`:

1. **Remove DATABASE_URL** from your `.env` file:
   ```bash
   # REMOVE THIS LINE:
   DATABASE_URL=postgresql://user:pass@host:5432/dbname
   ```

2. **Add individual DB_* variables**:
   ```bash
   # ADD THESE INSTEAD:
   DB_HOST=host
   DB_PORT=5432
   DB_NAME=dbname
   DB_USER=user
   DB_PASSWORD=pass
   DB_SSLMODE=require
   ```

3. **Restart your containers**:
   ```bash
   docker-compose -f docker-compose.prod.yml restart backend
   ```

The application automatically detects which configuration to use based on available environment variables.

## SSL/TLS Setup

### Option 1: Self-Signed (Testing Only)

```bash
./docker/generate-ssl.sh your-domain.com
```

### Option 2: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy to Docker volume
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./docker/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./docker/ssl/key.pem
sudo cp /etc/letsencrypt/live/your-domain.com/chain.pem ./docker/ssl/chain.pem
sudo chown $(id -u):$(id -g) ./docker/ssl/*
```

### Option 3: Commercial Certificate

```bash
# Copy your certificate files
cp your-cert.pem ./docker/ssl/cert.pem
cp your-key.pem ./docker/ssl/key.pem
cp your-chain.pem ./docker/ssl/chain.pem
```

## Startup

### Automated Startup Script

```bash
# Basic startup
./docker/start-production.sh

# Build images and start
./docker/start-production.sh --build

# Scale Celery workers
./docker/start-production.sh --scale 3

# Skip database initialization
./docker/start-production.sh --no-init
```

### Manual Startup

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Create superuser
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Collect static
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

## Monitoring & Management

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f postgres
docker-compose -f docker-compose.prod.yml logs -f redis

# Last N lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend
```

### Service Status

```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Check specific service
docker ps | grep thebot
```

### Database Backup & Recovery

```bash
# Backup
docker-compose -f docker-compose.prod.yml exec postgres \
    pg_dump -U postgres thebot_db > backup-$(date +%Y%m%d-%H%M%S).sql

# Restore
docker-compose -f docker-compose.prod.yml exec -T postgres \
    psql -U postgres thebot_db < backup.sql

# List backups
ls -lh ./database/backups/
```

### Scale Celery Workers

```bash
# Scale to 3 workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3

# Scale to 5 workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=5

# Back to 1
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=1
```

### Performance Monitoring

```bash
# Check resource usage
docker stats

# PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U postgres -d thebot_db -c "SELECT datname, numbackends FROM pg_stat_database WHERE datname='thebot_db';"

# Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli INFO server

# Celery
docker-compose -f docker-compose.prod.yml exec celery-worker \
    celery -A config inspect active
```

## Troubleshooting

### Database Configuration Issues

#### "ValueError: Port could not be cast to integer"

This error occurs when using `DATABASE_URL` with special characters in passwords that break URL parsing.

**Solution**: Use individual `DB_*` environment variables instead:

```bash
# WRONG - will fail with special characters in password
DATABASE_URL=postgresql://user:p@ss%40word@host:5432/dbname

# CORRECT - use DB_* variables instead
DB_HOST=host
DB_PORT=5432
DB_NAME=dbname
DB_USER=user
DB_PASSWORD=p@ss%40word
DB_SSLMODE=require
```

#### ImproperlyConfigured: "Requires database configuration"

This error means Django could not find database configuration.

**Solution**: Ensure you have set either:
1. **Option A** - Individual `DB_*` variables (recommended):
   ```bash
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=thebot_db
   DB_USER=postgres
   DB_PASSWORD=password
   ```

2. **Option B** - `DATABASE_URL` (legacy support):
   ```bash
   DATABASE_URL=postgresql://postgres:password@localhost:5432/thebot_db
   ```

See **Database Configuration Details** section above for complete setup instructions.

### PostgreSQL Connection Issues

```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml ps postgres

# Check logs
docker-compose -f docker-compose.prod.yml logs postgres

# Verify connectivity
docker-compose -f docker-compose.prod.yml exec postgres \
    pg_isready -U postgres -d thebot_db
```

### Redis Connection Issues

```bash
# Check Redis status
docker-compose -f docker-compose.prod.yml ps redis

# Test connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Check logs
docker-compose -f docker-compose.prod.yml logs redis
```

### Backend Issues

```bash
# Check Django logs
docker-compose -f docker-compose.prod.yml logs backend

# Run migrations (if needed)
docker-compose -f docker-compose.prod.yml exec backend \
    python manage.py migrate

# Check static files
docker-compose -f docker-compose.prod.yml exec backend \
    python manage.py collectstatic --noinput

# Shell access
docker-compose -f docker-compose.prod.yml exec backend bash
```

### Nginx Issues

```bash
# Check configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# View logs
docker-compose -f docker-compose.prod.yml logs nginx

# Reload config
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Network Isolation

The deployment uses two networks:

1. **thebot-internal**: Database, cache, workers (isolated)
   - Subnet: 172.20.0.0/16
   - Services: postgres, redis, backend, celery-worker, celery-beat

2. **thebot-external**: Public services (exposed)
   - Subnet: 172.21.0.0/16
   - Services: nginx, frontend

This ensures:
- Database is not directly exposed
- Only nginx/frontend accessible from internet
- All services communicate through nginx

## Security Best Practices

1. **Secrets Management**:
   - Never commit `.env` files
   - Use strong passwords (min 20 chars)
   - Rotate keys regularly

2. **SSL/TLS**:
   - Always use HTTPS in production
   - Use valid certificates (Let's Encrypt)
   - Enable HSTS

3. **Database**:
   - Regular backups
   - Strong passwords
   - Limit connections
   - Monitor slow queries

4. **Access Control**:
   - Use authentication
   - Rate limiting enabled
   - Admin panel protected
   - API authentication required

5. **Updates**:
   - Keep Docker images updated
   - Monitor security advisories
   - Regular dependency updates

## Performance Optimization

### Database Tuning

The PostgreSQL container includes optimizations:

```sql
-- Check current settings
SHOW max_connections;
SHOW shared_buffers;
SHOW effective_cache_size;
SHOW work_mem;
```

### Redis Optimization

```bash
# Check memory usage
docker-compose -f docker-compose.prod.yml exec redis redis-cli INFO memory

# Check eviction policy
docker-compose -f docker-compose.prod.yml exec redis \
    redis-cli CONFIG GET maxmemory-policy
```

### Backend Scaling

Increase concurrency:

```bash
# Edit docker-compose.prod.yml celery-worker command
# Change --concurrency=4 to --concurrency=8

docker-compose -f docker-compose.prod.yml up -d
```

## Disaster Recovery

### Full System Backup

```bash
#!/bin/bash
DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="./backups/$DATE"

mkdir -p "$BACKUP_DIR"

# PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres \
    pg_dump -U postgres thebot_db > "$BACKUP_DIR/database.sql"

# Redis
docker-compose -f docker-compose.prod.yml exec redis \
    redis-cli BGSAVE && \
    docker cp thebot-redis-prod:/data/dump.rdb "$BACKUP_DIR/redis.rdb"

# Media
cp -r backend/media "$BACKUP_DIR/media"
cp -r backend_logs "$BACKUP_DIR/logs"

# Config
cp .env.production "$BACKUP_DIR/.env"
cp docker-compose.prod.yml "$BACKUP_DIR/"

echo "Backup complete: $BACKUP_DIR"
```

### System Recovery

```bash
# Stop services
docker-compose -f docker-compose.prod.yml down

# Restore database
docker-compose -f docker-compose.prod.yml exec -T postgres \
    psql -U postgres < backups/2024-01-01-120000/database.sql

# Restore media
cp -r backups/2024-01-01-120000/media backend/

# Restart
docker-compose -f docker-compose.prod.yml up -d
```

## Updating

### Update Docker Images

```bash
# Pull latest images
docker-compose -f docker-compose.prod.yml pull

# Rebuild if needed
docker-compose -f docker-compose.prod.yml build --pull

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

### Update Application Code

```bash
# Pull latest code
git pull origin main

# Rebuild backend
docker-compose -f docker-compose.prod.yml build backend

# Apply migrations
docker-compose -f docker-compose.prod.yml exec backend \
    python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend \
    python manage.py collectstatic --noinput

# Restart services
docker-compose -f docker-compose.prod.yml up -d
```

## Support

For issues or questions, check:

1. Logs: `docker-compose -f docker-compose.prod.yml logs`
2. Status: `docker-compose -f docker-compose.prod.yml ps`
3. Health: `docker ps --format "table {{.Names}}\t{{.Status}}"`

Contact the development team or open an issue on GitHub.
