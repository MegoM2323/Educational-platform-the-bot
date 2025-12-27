# THE_BOT Platform - ELK Stack Logging

Comprehensive logging infrastructure using Elasticsearch, Logstash, Kibana (ELK Stack) for centralized log collection, processing, and analysis.

## Overview

The ELK Stack provides:

- **Elasticsearch**: Distributed search and analytics engine for log storage and indexing
- **Logstash**: Log processing pipeline for parsing, filtering, and enriching logs
- **Kibana**: Web UI for log visualization, search, and dashboards
- **Filebeat**: Lightweight log shipper for file collection
- **Metricbeat**: Metrics collection for system and service monitoring

## Architecture

```
┌─────────────────────────────────────────────────────┐
│         Log Sources                                 │
│  ├─ Django Application Logs                         │
│  ├─ Celery Task Logs                                │
│  ├─ Nginx Web Server                                │
│  ├─ PostgreSQL Database                             │
│  ├─ Redis Cache                                     │
│  ├─ System Logs                                     │
│  └─ Docker Containers                               │
└────────────┬────────────────────────────────────────┘
             │
      ┌──────▼──────┐
      │   Filebeat  │
      │   Beats)    │
      └──────┬──────┘
             │
      ┌──────▼──────────────┐
      │    Logstash         │
      │  (Processing)       │
      │  ├─ Parse logs      │
      │  ├─ Extract fields  │
      │  ├─ Filter events   │
      │  └─ Transform data  │
      └──────┬──────────────┘
             │
      ┌──────▼────────────────────┐
      │  Elasticsearch            │
      │  (Storage & Indexing)     │
      │  ├─ thebot-logs-*         │
      │  ├─ thebot-errors-*       │
      │  ├─ metrics-*             │
      │  └─ Full-text search      │
      └──────┬────────────────────┘
             │
      ┌──────▼────────────────┐
      │    Kibana             │
      │  (Visualization)      │
      │  ├─ Discover          │
      │  ├─ Dashboards        │
      │  ├─ Alerts            │
      │  └─ Analytics         │
      └───────────────────────┘
```

## Quick Start

### 1. Start ELK Stack

```bash
cd logging
docker-compose up -d
```

Services:
- Elasticsearch: http://localhost:9200
- Kibana: http://localhost:5601
- Logstash: localhost:5000 (TCP/UDP)

### 2. Verify Setup

```bash
python test_elk_stack.py
```

### 3. View Logs

Open Kibana: http://localhost:5601

1. Create Index Pattern:
   - Go to "Stack Management" → "Index Patterns"
   - Create pattern: `thebot-logs-*`
   - Time field: `@timestamp`

2. View Logs:
   - Go to "Discover"
   - Select index pattern
   - Browse logs in real-time

## Configuration Files

### Docker Compose
- `docker-compose.yml` - Complete ELK Stack orchestration

### Service Configurations
- `elasticsearch/elasticsearch.yml` - Elasticsearch settings
- `logstash/logstash.conf` - Log processing pipeline
- `logstash/patterns/thebot` - Custom grok patterns
- `kibana/kibana.yml` - Kibana settings
- `filebeat/filebeat.yml` - Log collection
- `metricbeat/metricbeat.yml` - Metrics collection

### Application Integration
- `python_logging_config.py` - Django logging configuration

## Log Sources

### Django Application Logs
- All application logs
- Request/response logging
- Error traces
- Database queries (debug mode)

**File**: `/backend/logs/django.log`

### Celery Task Logs
- Async task execution
- Task failures and retries
- Execution times

**File**: `/backend/logs/celery.log`

### Audit Logs
- User actions
- Security events
- Data changes

**File**: `/backend/logs/audit.log`

### Request Logs
- HTTP requests
- Response times
- Status codes

**File**: `/backend/logs/requests.log`

### System Logs
- OS events
- Service status
- Resource usage

**Files**: `/var/log/syslog`, `/var/log/messages`

## Log Processing Pipeline

### Parse Logs
Logstash uses grok patterns to parse:
- Timestamps
- Log levels (DEBUG, INFO, WARNING, ERROR, CRITICAL)
- Logger names
- HTTP methods and paths
- Status codes
- Exception types

### Extract Fields
- `@timestamp` - Timestamp for sorting
- `log_level` - Severity level
- `service` - Source service
- `request_id` - Request tracking
- `user_id` - User identification
- `duration_ms` - Response time

### Filter Events
- Remove debug messages in production
- Separate errors to dedicated index
- Drop low-importance events

### Enrich Data
- Add hostname
- Add environment tag
- Add platform version
- Add Docker metadata
- Add Kubernetes metadata (if applicable)

## Elasticsearch Indices

### Log Indices
- `thebot-logs-YYYY.MM.dd` - All application logs
- `thebot-errors-YYYY.MM.dd` - Errors and critical issues
- `filebeat-VERSION-YYYY.MM.dd` - Filebeat logs
- `metrics-VERSION-YYYY.MM.dd` - System metrics

### Index Templates
- Automatic creation based on naming pattern
- Date-based rollover
- Field mappings for optimal search
- Settings for performance

### Index Lifecycle Policy (ILM)
- Hot: Active index (0-7 days)
- Warm: Read-only (7-30 days)
- Cold: Archive (30+ days)
- Delete: After retention period

## Kibana Features

### Discover
- Full-text search across all logs
- Filter by service, level, user, etc.
- View field values
- Export search results

### Dashboards
Pre-built dashboards for:
- System health (CPU, memory, disk)
- Application metrics (requests, errors)
- Database performance
- Security events
- User activities

### Alerts
Trigger notifications for:
- Error rate > threshold
- Request time > threshold
- Service failures
- Failed logins
- Suspicious activities

### Canvas
Create custom visualizations:
- Timeline charts
- Distribution histograms
- Top users/endpoints
- Error rates by service

## Searching Logs

### Basic Search
```
message: "error"
```

### Field Search
```
log_level: ERROR
service: django-backend
user_id: 123
request_id: "abc-123"
```

### Range Query
```
response_time: [100 TO 500]
@timestamp: [now-1h TO now]
```

### Regex Search
```
message: /^ERROR: .*/
```

### Complex Queries
```
(log_level: ERROR OR log_level: CRITICAL) AND service: django-backend
```

## Integration with Django

### 1. Install Dependencies

```bash
pip install python-json-logger python-logstash-async
```

### 2. Configure Logging

In `backend/config/settings.py`:

```python
from logging_config import LOGGING

LOGGING = LOGGING
```

### 3. Environment Variables

```bash
export LOG_PATH=/var/log/thebot
export LOGSTASH_HOST=localhost
export LOGSTASH_PORT=5000
export LOG_LEVEL=INFO
export ENVIRONMENT=development
```

### 4. Log in Code

```python
import logging

logger = logging.getLogger('django')
logger.info('Application started')
logger.error('Database connection failed', extra={
    'request_id': request.id,
    'user_id': request.user.id,
    'duration_ms': response_time
})
```

## Performance Optimization

### Elasticsearch
- `indices.memory.index_buffer_size: 40%` - Memory for buffering
- `index.codec: best_compression` - Compression for storage
- `index.refresh_interval: 30s` - Less frequent refreshes
- Connection pooling enabled

### Logstash
- `thread_pool.write.queue_size: 1000` - Buffer writes
- `bulk_max_size: 2048` - Batch size
- Multiple workers for processing

### Filebeat
- Queue memory: 3200 events
- Bulk size: 2048
- Compression enabled

## Retention Policies

### Default Retention (30 days)

```
Hot (0-7 days):
  - Active index
  - Full resolution data

Warm (7-30 days):
  - Read-only
  - Optimized for search

Delete (30+ days):
  - Automatic deletion
```

### Configure Retention

Edit `elasticsearch/elasticsearch.yml`:

```yaml
index.lifecycle.name: thebot-log-policy
index.lifecycle.rollover_alias: thebot-logs
```

## Backup and Recovery

### Manual Backup

```bash
# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup?pretty" -H 'Content-Type: application/json' -d'
{
  "type": "fs",
  "settings": {
    "location": "/mnt/backup"
  }
}'

# Create snapshot
curl -X PUT "localhost:9200/_snapshot/backup/logs-backup?pretty"
```

### Restore from Backup

```bash
curl -X POST "localhost:9200/_snapshot/backup/logs-backup/_restore?pretty"
```

## Troubleshooting

### No Logs Appearing

1. Check log files exist:
   ```bash
   ls -la /backend/logs/
   ```

2. Verify Filebeat is running:
   ```bash
   docker-compose logs filebeat
   ```

3. Check Logstash pipeline:
   ```bash
   curl http://localhost:9600/_node/stats/pipelines
   ```

4. Verify Elasticsearch is accepting data:
   ```bash
   curl http://localhost:9200/_cat/indices
   ```

### High CPU Usage

1. Reduce refresh interval:
   ```yaml
   index.refresh_interval: 60s  # Increase from 30s
   ```

2. Reduce bulk batch size in Logstash:
   ```
   bulk_max_size: 1024  # Decrease from 2048
   ```

3. Increase Elasticsearch heap:
   ```yaml
   ES_JAVA_OPTS: "-Xms1g -Xmx1g"  # Increase memory
   ```

### Disk Space Issues

1. Check index sizes:
   ```bash
   curl "localhost:9200/_cat/indices?v&s=store.size:desc"
   ```

2. Delete old indices:
   ```bash
   curl -X DELETE "localhost:9200/thebot-logs-2024.01.01"
   ```

3. Enable compression:
   ```yaml
   index.codec: best_compression
   ```

### Logstash Backpressure

1. Increase queue size:
   ```yaml
   queue.mem.events: 5000
   ```

2. Increase workers:
   ```
   worker: 8
   ```

3. Optimize filters in `logstash.conf`

## Monitoring

### Health Checks

```bash
# Elasticsearch
curl http://localhost:9200/_cluster/health

# Kibana
curl http://localhost:5601/api/status

# Logstash
curl http://localhost:9600/
```

### Metrics

- Document count: `curl http://localhost:9200/_cat/indices`
- Cluster status: `curl http://localhost:9200/_cluster/health`
- Node stats: `curl http://localhost:9200/_nodes/stats`

### Disk Usage

```bash
# By index
curl "localhost:9200/_cat/indices?v&s=store.size:desc"

# By node
curl "localhost:9200/_cat/allocation?v"
```

## Scaling

### Multi-Node Elasticsearch

```yaml
# In docker-compose.yml
elasticsearch-2:
  image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
  environment:
    - discovery.seed_hosts=elasticsearch,elasticsearch-2
    - cluster.initial_master_nodes=elasticsearch,elasticsearch-2
```

### Logstash Cluster

Run multiple Logstash instances with load balancing:

```bash
docker-compose up -d --scale logstash=3
```

### Horizontal Scaling

1. Add more Filebeat instances
2. Add more Logstash workers
3. Add more Elasticsearch nodes
4. Use load balancer for Kibana

## Security

### Authentication

Uncomment in `elasticsearch/elasticsearch.yml`:

```yaml
xpack.security.enabled: true
xpack.security.authc.realms.file.file1.order: 0
```

### HTTPS

In `elasticsearch/elasticsearch.yml`:

```yaml
xpack.security.http.ssl.enabled: true
xpack.security.http.ssl.keystore.path: certs/elasticsearch.p12
xpack.security.http.ssl.truststore.path: certs/elasticsearch.p12
```

### Network Isolation

Only expose Kibana to trusted networks:

```yaml
# docker-compose.yml
kibana:
  ports:
    - "127.0.0.1:5601:5601"  # localhost only
```

## Best Practices

1. **Use Index Templates**: Ensure consistent field mappings
2. **Set Retention**: Delete old logs after 30 days
3. **Monitor Resources**: Watch CPU, memory, disk usage
4. **Optimize Queries**: Use filters instead of queries
5. **Archive Data**: Move old logs to cold storage
6. **Test Recovery**: Regular backup and restore tests
7. **Log Rotation**: Use log rotation to prevent disk full
8. **Alert Thresholds**: Set reasonable alert thresholds

## Resources

- [Elasticsearch Documentation](https://www.elastic.co/guide/en/elasticsearch/reference/current/index.html)
- [Kibana Documentation](https://www.elastic.co/guide/en/kibana/current/index.html)
- [Logstash Documentation](https://www.elastic.co/guide/en/logstash/current/index.html)
- [Beats Documentation](https://www.elastic.co/guide/en/beats/libbeat/current/index.html)

## Support

For issues or questions:
1. Check logs: `docker-compose logs [service]`
2. Run tests: `python test_elk_stack.py`
3. Review configuration files
4. Check Elasticsearch status: `curl http://localhost:9200/_cluster/health`

## License

Same as THE_BOT platform
