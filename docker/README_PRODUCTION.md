# THE_BOT Platform - Production Docker Setup

Complete production-grade Docker Compose configuration with all infrastructure components.

## Overview

This setup provides:

- **Nginx** - Reverse proxy, load balancer, TLS termination
- **Django Backend** - Daphne ASGI server with WebSocket support
- **React Frontend** - Built Vite app served via Nginx
- **PostgreSQL 15** - Production database with replication support
- **Redis 7** - Cache and message broker
- **Celery Workers** - Scalable background task processing
- **Celery Beat** - Scheduled task execution
- **Health Checks** - Automatic service monitoring
- **Network Isolation** - Internal and external networks
- **Resource Limits** - Memory and CPU constraints
- **Logging** - Centralized JSON-formatted logs
- **Security** - Non-root users, read-only filesystems, rate limiting

## Files

```
docker/
├── docker-compose.prod.yml          # Main production compose file
├── nginx.prod.conf                  # Nginx configuration
├── start-production.sh              # Automated startup script
├── test-production.sh               # Testing and validation
├── generate-ssl.sh                  # SSL certificate generation
├── PRODUCTION_DEPLOYMENT.md         # Detailed deployment guide
├── ssl/                             # SSL certificates (to be generated)
│   ├── cert.pem                     # TLS certificate
│   ├── key.pem                      # Private key
│   ├── chain.pem                    # Certificate chain
│   └── dhparam.pem                  # DH parameters
└── README_PRODUCTION.md             # This file

database/
├── init-scripts/
│   └── 01-init.sql                  # PostgreSQL initialization
└── backups/                         # Database backups

redis/
└── redis.conf                       # Redis configuration
```

## Quick Start

### 1. Prepare Environment

```bash
# Copy production environment template
cp .env.example .env.production

# Edit with your production settings
nano .env.production
```

Key variables to configure:

```env
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=<generate-50-char-random-string>
FRONTEND_URL=https://your-domain.com
ALLOWED_HOSTS=your-domain.com,www.your-domain.com
DB_PASSWORD=<strong-password>
REDIS_PASSWORD=<strong-password>
```

### 2. Generate SSL Certificates

For **testing/development**:

```bash
./docker/generate-ssl.sh
```

For **production** (Let's Encrypt):

```bash
# Install certbot
sudo apt-get install certbot

# Generate certificate
sudo certbot certonly --standalone -d your-domain.com

# Copy to Docker volume
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ./docker/ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ./docker/ssl/key.pem
sudo cp /etc/letsencrypt/live/your-domain.com/chain.pem ./docker/ssl/chain.pem

# Fix permissions
sudo chown $(id -u):$(id -g) ./docker/ssl/*
```

### 3. Start Services

**Automated**:

```bash
./docker/start-production.sh --build
```

**Manual**:

```bash
# Build images
docker-compose -f docker-compose.prod.yml build

# Start services
docker-compose -f docker-compose.prod.yml up -d

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Collect static files
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic --noinput
```

### 4. Verify Installation

```bash
# Check all services
docker-compose -f docker-compose.prod.yml ps

# Run tests
./docker/test-production.sh
```

## Service Details

### Nginx (Port 80/443)

**Features**:
- HTTP to HTTPS redirect
- TLS 1.2/1.3
- Load balancing
- Gzip compression
- Security headers
- Rate limiting
- Static file serving
- WebSocket support
- Caching

**Management**:

```bash
# Check config
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Reload config
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# View logs
docker-compose -f docker-compose.prod.yml logs -f nginx
```

### PostgreSQL (Port 5432)

**Features**:
- Replication-ready
- WAL archiving
- 200 max connections
- 512MB shared buffers
- Automatic vacuum
- Slow query logging

**Management**:

```bash
# Connect to database
docker-compose -f docker-compose.prod.yml exec postgres psql -U postgres -d thebot_db

# Backup
docker-compose -f docker-compose.prod.yml exec postgres \
    pg_dump -U postgres thebot_db > backup.sql

# Restore
docker-compose -f docker-compose.prod.yml exec -T postgres \
    psql -U postgres thebot_db < backup.sql
```

### Redis (Port 6379)

**Features**:
- AOF persistence
- 512MB max memory
- LRU eviction
- Replication support
- Keyspace notifications

**Management**:

```bash
# Connect to Redis
docker-compose -f docker-compose.prod.yml exec redis redis-cli -a redis

# Check memory
docker-compose -f docker-compose.prod.yml exec redis redis-cli INFO memory

# Monitor
docker-compose -f docker-compose.prod.yml exec redis redis-cli MONITOR
```

### Django Backend (Port 8000)

**Features**:
- Daphne ASGI
- WebSocket support
- Auto-migrations
- Static files
- Media uploads
- Health checks
- Gunicorn-compatible

**Management**:

```bash
# Access Django shell
docker-compose -f docker-compose.prod.yml exec backend python manage.py shell

# Run migrations
docker-compose -f docker-compose.prod.yml exec backend python manage.py migrate

# Create admin user
docker-compose -f docker-compose.prod.yml exec backend python manage.py createsuperuser

# Collect static
docker-compose -f docker-compose.prod.yml exec backend python manage.py collectstatic
```

### React Frontend (Port 3000)

**Features**:
- Vite build
- SPA routing
- Static optimization
- Cache busting

**Management**:

```bash
# Rebuild frontend
docker-compose -f docker-compose.prod.yml build frontend

# View logs
docker-compose -f docker-compose.prod.yml logs -f frontend
```

### Celery Workers

**Features**:
- Background task processing
- Scalable (add more workers with --scale)
- Concurrency: 4 per worker
- Task retry support
- Result backend (Redis)

**Management**:

```bash
# View worker logs
docker-compose -f docker-compose.prod.yml logs -f celery-worker

# Scale to 3 workers
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3

# Check active tasks
docker-compose -f docker-compose.prod.yml exec celery-worker \
    celery -A config inspect active

# Purge queue
docker-compose -f docker-compose.prod.yml exec celery-worker \
    celery -A config purge
```

### Celery Beat

**Features**:
- Scheduled task execution
- Database scheduler (django-celery-beat)
- Timezone-aware

**Management**:

```bash
# View scheduler logs
docker-compose -f docker-compose.prod.yml logs -f celery-beat

# Check scheduled tasks
docker-compose -f docker-compose.prod.yml exec celery-beat \
    celery -A config inspect scheduled
```

## Common Operations

### View Logs

```bash
# All services
docker-compose -f docker-compose.prod.yml logs -f

# Specific service
docker-compose -f docker-compose.prod.yml logs -f backend

# Last N lines
docker-compose -f docker-compose.prod.yml logs --tail=100 backend

# Follow specific pattern
docker-compose -f docker-compose.prod.yml logs | grep ERROR
```

### Monitor Resources

```bash
# Real-time stats
docker stats

# Specific container
docker stats thebot-backend-prod

# Memory usage
free -h
```

### Database Operations

```bash
# Backup database
docker-compose -f docker-compose.prod.yml exec postgres \
    pg_dump -U postgres thebot_db > backup-$(date +%Y%m%d).sql

# Restore database
docker-compose -f docker-compose.prod.yml exec -T postgres \
    psql -U postgres thebot_db < backup.sql

# List databases
docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U postgres -l

# Check connections
docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U postgres -d thebot_db -c "SELECT datname, numbackends FROM pg_stat_database;"
```

### Scale Services

```bash
# Scale Celery workers to 5
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=5

# Back to 1
docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=1
```

### Stop Services

```bash
# Stop all services (keep volumes)
docker-compose -f docker-compose.prod.yml down

# Remove volumes as well
docker-compose -f docker-compose.prod.yml down -v

# Remove all unused resources
docker system prune -a
```

## Testing

### Automated Tests

```bash
# All tests
./docker/test-production.sh

# Specific test type
./docker/test-production.sh health
./docker/test-production.sh connectivity
./docker/test-production.sh environment
./docker/test-production.sh performance
```

### Manual Tests

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Test PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres \
    psql -U postgres -d thebot_db -c "SELECT version();"

# Test Redis
docker-compose -f docker-compose.prod.yml exec redis \
    redis-cli ping

# Test Backend API
curl -X GET http://localhost:8000/api/system/health/

# Test Frontend
curl -X GET http://localhost/

# Test WebSocket
wscat -c ws://localhost:8000/ws/
```

## Troubleshooting

### Service Not Starting

```bash
# Check logs
docker-compose -f docker-compose.prod.yml logs backend

# Check resource availability
docker system df

# Restart single service
docker-compose -f docker-compose.prod.yml restart backend
```

### Database Connection Error

```bash
# Check PostgreSQL status
docker-compose -f docker-compose.prod.yml ps postgres

# Check connectivity
docker-compose -f docker-compose.prod.yml exec postgres pg_isready

# Check environment
docker-compose -f docker-compose.prod.yml exec backend env | grep DATABASE
```

### Redis Connection Error

```bash
# Check Redis status
docker-compose -f docker-compose.prod.yml ps redis

# Test connection
docker-compose -f docker-compose.prod.yml exec redis redis-cli ping

# Check password
docker-compose -f docker-compose.prod.yml exec redis \
    redis-cli -a redis ping
```

### Memory Issues

```bash
# Check memory usage
docker stats

# Increase memory limits in docker-compose.prod.yml
# Edit deploy.resources.limits.memory

# Restart services
docker-compose -f docker-compose.prod.yml restart
```

### SSL/TLS Issues

```bash
# Check certificate
openssl x509 -in ./docker/ssl/cert.pem -text -noout

# Check expiration
openssl x509 -in ./docker/ssl/cert.pem -noout -dates

# Verify configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Reload Nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Security Checklist

- [ ] Change all default passwords in `.env.production`
- [ ] Generate strong `SECRET_KEY` (min 50 characters)
- [ ] Set `DEBUG=False`
- [ ] Configure valid `ALLOWED_HOSTS`
- [ ] Use valid SSL certificates (not self-signed in production)
- [ ] Enable firewall rules
- [ ] Configure rate limiting
- [ ] Set up backups
- [ ] Monitor logs regularly
- [ ] Update images regularly
- [ ] Use strong Redis password
- [ ] Use strong database password
- [ ] Restrict admin panel access
- [ ] Enable HTTPS everywhere
- [ ] Monitor disk space
- [ ] Monitor CPU usage
- [ ] Monitor memory usage
- [ ] Set up alerting

## Performance Optimization

### Database

```sql
-- Check query performance
EXPLAIN ANALYZE SELECT ...;

-- Analyze table
ANALYZE table_name;

-- Reindex
REINDEX TABLE table_name;

-- Vacuum
VACUUM ANALYZE;
```

### Redis

```bash
# Monitor performance
redis-cli --stat

# Check slow log
redis-cli slowlog get 10

# Clear slow log
redis-cli slowlog reset
```

### Backend

- Increase worker concurrency
- Scale to multiple workers
- Use connection pooling
- Enable query caching
- Optimize static files
- Use CDN for assets

### Frontend

- Minimize bundle size
- Use code splitting
- Enable compression
- Use browser caching
- Optimize images
- Lazy load components

## Maintenance Tasks

### Daily

- Monitor logs
- Check disk space
- Monitor CPU/memory
- Verify services running

### Weekly

- Review slow queries
- Check Redis memory
- Monitor growth trends
- Test backups

### Monthly

- Database optimization
- Security updates
- Dependency updates
- Performance review

### Quarterly

- Full backup test
- Disaster recovery drill
- Security audit
- Capacity planning

## Backup & Recovery

### Automated Backup Script

```bash
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y%m%d-%H%M%S)"
mkdir -p "$BACKUP_DIR"

# PostgreSQL
docker-compose -f docker-compose.prod.yml exec postgres \
    pg_dump -U postgres thebot_db > "$BACKUP_DIR/database.sql"

# Redis
docker-compose -f docker-compose.prod.yml exec redis \
    redis-cli BGSAVE

docker cp thebot-redis-prod:/data/dump.rdb "$BACKUP_DIR/redis.rdb"

# Media
cp -r backend/media "$BACKUP_DIR/media"

# Config
cp .env.production "$BACKUP_DIR/.env"

echo "Backup complete: $BACKUP_DIR"
```

### Recovery

```bash
# Restore database
docker-compose -f docker-compose.prod.yml exec -T postgres \
    psql -U postgres < /backups/2024-01-01-120000/database.sql

# Restore media
cp -r /backups/2024-01-01-120000/media backend/

# Restart
docker-compose -f docker-compose.prod.yml up -d
```

## Support & Documentation

- **Deployment Guide**: `./PRODUCTION_DEPLOYMENT.md`
- **Docker Docs**: https://docs.docker.com/
- **Docker Compose Docs**: https://docs.docker.com/compose/
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Redis Docs**: https://redis.io/docs/
- **Django Docs**: https://docs.djangoproject.com/
- **Celery Docs**: https://docs.celeryproject.io/

## License

Same as THE_BOT platform.

## Version

**Docker Compose Version**: 3.9
**Status**: Production Ready
**Last Updated**: December 2025
