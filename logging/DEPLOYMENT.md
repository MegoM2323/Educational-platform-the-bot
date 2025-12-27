# ELK Stack Deployment Guide

Production deployment guide for THE_BOT platform logging infrastructure.

## Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 4GB+ RAM
- 20GB+ disk space for logs
- Network connectivity between services

## Development Environment

### 1. Start Services

```bash
cd logging
docker-compose up -d
```

### 2. Verify Services

```bash
# Check container status
docker-compose ps

# Expected output:
# NAME                    STATUS
# thebot-elasticsearch    Up (healthy)
# thebot-logstash         Up
# thebot-kibana           Up
# thebot-filebeat         Up
```

### 3. Run Tests

```bash
python test_elk_stack.py
```

### 4. Access Interfaces

- Elasticsearch: http://localhost:9200
- Kibana: http://localhost:5601
- Logstash API: http://localhost:9600

## Production Environment

### 1. Infrastructure Setup

```bash
# Create logging directory
mkdir -p /opt/thebot-logging
cd /opt/thebot-logging

# Copy configuration files
cp -r ./logging/* .

# Create persistent volumes
mkdir -p data/elasticsearch
mkdir -p data/kibana
mkdir -p logs

# Set permissions
chmod -R 755 data/
chmod -R 755 logs/
```

### 2. Environment Configuration

Create `.env` file:

```env
# Elasticsearch
ES_JAVA_OPTS=-Xms2g -Xmx2g
ELASTICSEARCH_HOST=elasticsearch
ELASTICSEARCH_PORT=9200

# Logstash
LS_JAVA_OPTS=-Xmx1g -Xms1g
LOGSTASH_HOST=logstash
LOGSTASH_PORT=5000

# Kibana
KIBANA_HOST=0.0.0.0
KIBANA_PORT=5601
ELASTICSEARCH_HOSTS=http://elasticsearch:9200

# Application
ENVIRONMENT=production
LOG_LEVEL=INFO
LOG_RETENTION_DAYS=30
```

### 3. Update docker-compose.yml

For production:

```yaml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    container_name: thebot-elasticsearch
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=true
      - xpack.security.authc.realms.file.file1.order=0
      - ELASTIC_PASSWORD=${ELASTIC_PASSWORD}
      - ES_JAVA_OPTS=${ES_JAVA_OPTS:-Xms2g -Xmx2g}
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
      - ./elasticsearch/elasticsearch.yml:/usr/share/elasticsearch/config/elasticsearch.yml:ro
      - ./elasticsearch/backups:/usr/share/elasticsearch/backups
    ports:
      - "127.0.0.1:9200:9200"  # Only local access
    networks:
      - logging-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "curl -s -u elastic:${ELASTIC_PASSWORD} http://localhost:9200 >/dev/null || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5

  # Logstash configuration
  logstash:
    build:
      context: ./logstash
      dockerfile: Dockerfile
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=elastic
      - ELASTICSEARCH_PASSWORD=${ELASTIC_PASSWORD}
      - LS_JAVA_OPTS=${LS_JAVA_OPTS:-Xmx1g -Xms1g}
    volumes:
      - ../backend/logs:/var/log/thebot:ro
    ports:
      - "127.0.0.1:5000:5000"
    depends_on:
      - elasticsearch
    networks:
      - logging-network
    restart: unless-stopped

  # Kibana
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
      - ELASTICSEARCH_USERNAME=elastic
      - ELASTICSEARCH_PASSWORD=${ELASTIC_PASSWORD}
      - xpack.security.enabled=true
    ports:
      - "127.0.0.1:5601:5601"
    volumes:
      - kibana_data:/usr/share/kibana/data
      - ./kibana/kibana.yml:/usr/share/kibana/config/kibana.yml:ro
    depends_on:
      - elasticsearch
    networks:
      - logging-network
    restart: unless-stopped

volumes:
  elasticsearch_data:
  kibana_data:

networks:
  logging-network:
    driver: bridge
```

### 4. Security Configuration

#### Enable Authentication

Edit `elasticsearch/elasticsearch.yml`:

```yaml
xpack.security.enabled: true
xpack.security.enrollment.enabled: true
xpack.security.authc.realms.file.file1.order: 0
xpack.security.authc.realms.file.file1.users_file: users
xpack.security.authc.realms.file.file1.users_roles_file: users_roles
```

#### Create Users

```bash
docker-compose exec elasticsearch \
  elasticsearch-setup-passwords auto \
  -b -u elastic
```

Save the generated passwords securely.

#### Enable TLS

```bash
# Generate certificates
docker-compose exec elasticsearch \
  elasticsearch-certutil ca -silent -pass "" \
  -out /usr/share/elasticsearch/elastic-stack-ca.p12

docker-compose exec elasticsearch \
  elasticsearch-certutil cert \
  -silent -pass "" \
  -ca /usr/share/elasticsearch/elastic-stack-ca.p12 \
  -name elasticsearch \
  -out /usr/share/elasticsearch/elasticsearch.p12
```

Update `elasticsearch.yml`:

```yaml
xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.keystore.path: elasticsearch.p12
xpack.security.http.ssl.keystore.password: ""
xpack.security.http.ssl.truststore.path: elasticsearch.p12
xpack.security.http.ssl.truststore.password: ""
```

### 5. Network Configuration

#### Nginx Reverse Proxy

```nginx
upstream kibana {
    server localhost:5601;
}

upstream elasticsearch {
    server localhost:9200;
}

server {
    listen 443 ssl;
    server_name logs.thebot.local;

    ssl_certificate /etc/ssl/certs/kibana.crt;
    ssl_certificate_key /etc/ssl/private/kibana.key;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    location / {
        proxy_pass http://kibana;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Elasticsearch API (restricted)
    location /elasticsearch/ {
        auth_basic "Elasticsearch Admin";
        auth_basic_user_file /etc/nginx/.htpasswd;

        rewrite ^/elasticsearch/(.*)$ /$1 break;
        proxy_pass http://elasticsearch;
    }
}
```

### 6. Resource Limits

#### Elasticsearch JVM Heap

```yaml
environment:
  - ES_JAVA_OPTS=-Xms4g -Xmx4g
```

Set to 50% of available RAM, max 32GB.

#### Logstash JVM Heap

```yaml
environment:
  - LS_JAVA_OPTS=-Xms1g -Xmx2g
```

#### Memory Limits (docker-compose)

```yaml
elasticsearch:
  deploy:
    resources:
      limits:
        memory: 8G
      reservations:
        memory: 4G

logstash:
  deploy:
    resources:
      limits:
        memory: 2G
      reservations:
        memory: 1G
```

### 7. Backup Strategy

#### Automated Backups

Create backup script:

```bash
#!/bin/bash
# backup_elasticsearch.sh

BACKUP_DIR="/mnt/backups"
DATE=$(date +%Y%m%d_%H%M%S)
SNAPSHOT="logs-backup-$DATE"

# Create snapshot
curl -X PUT "elasticsearch:9200/_snapshot/backup/$SNAPSHOT" \
  -H 'Content-Type: application/json' \
  -d '{
    "indices": "thebot-*",
    "ignore_unavailable": true,
    "include_global_state": false
  }'

# Wait for completion
sleep 30

# Compress snapshot
cd $BACKUP_DIR
tar -czf "$SNAPSHOT.tar.gz" "$SNAPSHOT"

# Cleanup old backups (keep last 7 days)
find . -name "logs-backup-*.tar.gz" -mtime +7 -delete
```

Schedule with cron:

```bash
0 2 * * * /usr/local/bin/backup_elasticsearch.sh >> /var/log/elasticsearch-backup.log 2>&1
```

#### Restore from Backup

```bash
# List snapshots
curl http://elasticsearch:9200/_snapshot/backup/_all

# Restore snapshot
curl -X POST "elasticsearch:9200/_snapshot/backup/logs-backup-YYYYMMDD/_restore" \
  -H 'Content-Type: application/json' \
  -d '{
    "indices": "thebot-logs-*",
    "ignore_unavailable": true,
    "include_global_state": false
  }'
```

### 8. Monitoring

#### Prometheus Integration

Create `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: elasticsearch
    static_configs:
      - targets: ['localhost:9200']
    metrics_path: '/_prometheus/metrics'

  - job_name: logstash
    static_configs:
      - targets: ['localhost:9600']
    metrics_path: '/_prometheus/metrics'
```

#### Health Checks

```bash
#!/bin/bash
# health_check.sh

check_service() {
    local url=$1
    local name=$2

    response=$(curl -s -o /dev/null -w "%{http_code}" "$url")

    if [ "$response" = "200" ] || [ "$response" = "401" ]; then
        echo "✓ $name is healthy"
        return 0
    else
        echo "✗ $name is unhealthy (HTTP $response)"
        return 1
    fi
}

check_service "http://localhost:9200/_cluster/health" "Elasticsearch"
check_service "http://localhost:5601/api/status" "Kibana"
check_service "http://localhost:9600/" "Logstash"
```

### 9. Maintenance

#### Log Rotation

Configure in `elasticsearch.yml`:

```yaml
# Delete indices older than 30 days
index.lifecycle.max_age: 30d

# Delete when size exceeds 50GB
index.lifecycle.max_primary_shard_size: 50GB
```

#### Index Cleanup

```bash
#!/bin/bash
# cleanup_old_indices.sh

# Delete indices older than 60 days
curl -X DELETE "localhost:9200/thebot-logs-$(date -d '60 days ago' +%Y.%m.%d)"
```

#### Reindex Operations

```bash
curl -X POST "localhost:9200/_reindex" \
  -H 'Content-Type: application/json' \
  -d '{
    "source": {
      "index": "thebot-logs-old"
    },
    "dest": {
      "index": "thebot-logs-new"
    }
  }'
```

### 10. Upgrade Procedure

#### Version Upgrade

```bash
# Check current version
curl http://localhost:9200/

# Backup before upgrade
docker-compose exec elasticsearch \
  curl -X PUT "localhost:9200/_snapshot/backup/pre-upgrade-backup"

# Stop services
docker-compose down

# Update docker-compose.yml with new version
# Update configuration files if needed

# Start services
docker-compose up -d

# Verify cluster health
curl http://localhost:9200/_cluster/health
```

## Performance Tuning

### Query Optimization

```
# Use filter context (faster, cacheable)
{
  "query": {
    "bool": {
      "filter": [
        { "term": { "status": "active" } },
        { "range": { "@timestamp": { "gte": "now-1d" } } }
      ]
    }
  }
}
```

### Index Settings

```bash
# Update shard count for large indices
curl -X PUT "localhost:9200/thebot-logs/_settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "number_of_shards": 5,
    "number_of_replicas": 1
  }'
```

### Logstash Tuning

```conf
# Increase workers for parallel processing
filter {
  # ... filters ...
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    workers => 4
    bulk_max_size => 4096
  }
}
```

## Troubleshooting

### Out of Disk Space

```bash
# Check disk usage
curl "localhost:9200/_cat/allocation?v"

# Delete old indices
curl -X DELETE "localhost:9200/thebot-logs-2024.01.01"

# Force merge to reclaim space
curl -X POST "localhost:9200/thebot-logs-*/_forcemerge"
```

### High Memory Usage

```bash
# Reduce heap size
docker-compose down
# Edit .env to reduce ES_JAVA_OPTS
docker-compose up -d

# Reduce refresh interval
curl -X PUT "localhost:9200/thebot-logs/_settings" \
  -H 'Content-Type: application/json' \
  -d '{"index.refresh_interval": "60s"}'
```

### Slow Queries

```bash
# Enable slow query logging
curl -X PUT "localhost:9200/_cluster/settings" \
  -H 'Content-Type: application/json' \
  -d '{
    "transient": {
      "index.search.slowlog.threshold.query.warn": "10s"
    }
  }'

# Check slow log
curl "localhost:9200/thebot-logs/_search?q=elasticsearch*slowlog"
```

## Compliance & Retention

### GDPR Data Deletion

```bash
# Delete user data
curl -X POST "localhost:9200/thebot-logs/_delete_by_query" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "term": {
        "user_id": "user-123"
      }
    }
  }'
```

### Audit Trail Retention

Ensure `thebot-audit-*` indices are retained for 2 years:

```yaml
index.lifecycle.max_age: 730d
```

## Support & Documentation

- [Elasticsearch Production Checklist](https://www.elastic.co/guide/en/elasticsearch/reference/current/setup-xpack.html)
- [Kibana Best Practices](https://www.elastic.co/guide/en/kibana/current/production.html)
- [Logstash Performance Tuning](https://www.elastic.co/guide/en/logstash/current/performance-tuning.html)

