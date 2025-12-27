# THE_BOT Platform - Monitoring Stack

Comprehensive monitoring solution for THE_BOT Platform using Prometheus, Grafana, AlertManager, and Loki.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Application Stack                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Django     │  │  Node.js     │  │ PostgreSQL   │       │
│  │  Backend     │  │  Frontend    │  │  Database    │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                 │                  │               │
│         ▼                 ▼                  ▼               │
│  ┌──────────────────────────────────────────────────┐       │
│  │        Metrics Export (prometheus format)        │       │
│  └──────────────────────────────────────────────────┘       │
└─────────────────────────────────────────────────────────────┘
         │                                │
         ▼                                ▼
┌──────────────────┐          ┌──────────────────┐
│  node_exporter   │          │ postgres_exporter│
│   (system)       │          │   (database)     │
└──────────────────┘          └──────────────────┘
         │                          │
         └────────────┬─────────────┘
                      │
         ┌────────────┼────────────┐
         ▼            ▼            ▼
    ┌─────────────────────────────────────┐
    │       Prometheus                    │
    │  - Scrapes metrics                  │
    │  - Evaluates rules                  │
    │  - Stores time-series data          │
    │  - Fires alerts                     │
    └─────────────────────────────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌─────────────┐  ┌───────────┐  ┌──────────────┐
    │  Grafana    │  │AlertManager│  │    Loki      │
    │ Dashboards  │  │ Routing    │  │ Log Storage  │
    │ Alerting    │  │ Grouping   │  │              │
    └─────────────┘  └───────────┘  └──────────────┘
         │              │              │
         ▼              ▼              ▼
    ┌──────────────────────────────────────┐
    │    Notifications                     │
    │  - Slack                             │
    │  - Email                             │
    │  - PagerDuty                         │
    │  - Webhooks                          │
    └──────────────────────────────────────┘
```

## Quick Start

### 1. Start Monitoring Stack

```bash
# Build and start all monitoring services
docker-compose -f monitoring/docker-compose.monitoring.yml up -d

# Verify all services are running
docker-compose -f monitoring/docker-compose.monitoring.yml ps
```

### 2. Access Services

| Service | URL | Default Credentials |
|---------|-----|-------------------|
| Prometheus | http://localhost:9090 | No auth |
| Grafana | http://localhost:3000 | admin/admin |
| AlertManager | http://localhost:9093 | No auth |
| Loki | http://localhost:3100 | No auth |

### 3. Configure Django Backend

Update `backend/config/settings.py`:

```python
# Add Prometheus middleware
MIDDLEWARE = [
    # ... existing middleware ...
    'core.prometheus_middleware.PrometheusMetricsMiddleware',
    'core.prometheus_middleware.DatabaseMetricsMiddleware',
    'core.prometheus_middleware.CacheMetricsMiddleware',
]

# Add Prometheus URLs
from django.urls import path

urlpatterns = [
    # ... existing patterns ...
    path('api/system/metrics/prometheus/', prometheus_views.prometheus_metrics),
    path('api/system/health/', prometheus_views.health_check),
    path('api/system/readiness/', prometheus_views.readiness_check),
    path('api/system/liveness/', prometheus_views.liveness_check),
    path('api/system/metrics/', prometheus_views.system_metrics),
    path('api/system/analytics/', prometheus_views.analytics),
    path('api/system/prometheus/config/', prometheus_views.prometheus_config),
]
```

### 4. Verify Metrics Collection

Check if metrics are being collected:

```bash
# Check Django metrics endpoint
curl http://localhost:8000/api/system/metrics/prometheus/

# Check health status
curl http://localhost:8000/api/system/health/

# Check Prometheus scrape targets
curl http://localhost:9090/api/v1/targets
```

## Configuration Files

### Prometheus Configuration

**File**: `monitoring/prometheus/prometheus.yml`

Key sections:
- **global**: Default scrape interval, evaluation interval
- **scrape_configs**: Target configurations for all services
- **rule_files**: Recording and alert rules
- **alerting**: AlertManager configuration

### Recording Rules

**File**: `monitoring/prometheus/recording_rules.yml`

Pre-computes expensive queries for dashboard performance:

```
# Example recording rules
django_request:rate5m          # Request rate (5 minute)
django_request_latency:p95     # 95th percentile latency
node_memory:usage_percent      # Memory usage percentage
redis_keyspace:hit_rate        # Cache hit rate
```

### Alert Rules

**File**: `monitoring/prometheus/alert_rules.yml`

Defines conditions for automatic alerts:

```
# Critical Alerts
- DjangoHighErrorRate          # Error rate > 5%
- DjangoServiceDown            # Django service unavailable
- PostgreSQLDown               # Database unavailable
- HighCPUUsage                 # CPU > 80%
- HighMemoryUsage              # Memory > 80%
- CriticalMemoryUsage          # Memory > 95%

# Warning Alerts
- DjangoHighLatency            # P95 latency > 1s
- DjangoSlowQueries            # Slow queries > 10/s
- LongRunningQueries           # Query time > 5s
- HighDiskIO                   # I/O rate > 1000 ops/s
```

### AlertManager Configuration

**File**: `monitoring/alertmanager/alertmanager.yml`

Routing, grouping, and notification rules:

```yaml
route:
  receiver: 'default-receiver'
  group_by: ['alertname', 'component']

  # Critical alerts: immediate notification
  - match:
      severity: critical
    receiver: 'critical-team'

  # Warning alerts: standard notification
  - match:
      severity: warning
    receiver: 'ops-team'
```

## Metrics Overview

### HTTP Request Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `django_request_total` | Counter | method, endpoint, status | Total HTTP requests |
| `django_request_latency_seconds` | Histogram | method, endpoint | Request latency |
| `django_request_exceptions_total` | Counter | exception_type | Request exceptions |
| `nodejs_http_request_total` | Counter | method, status | Frontend HTTP requests |
| `nodejs_http_latency_ms` | Histogram | method, route | Frontend latency |

### Database Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `django_db_execute_total` | Counter | database, operation, table | Query executions |
| `django_db_execute_time_seconds` | Histogram | database, operation, table | Query duration |
| `pg_stat_statements_mean_exec_time` | Gauge | - | Avg query time |
| `pg_connections_available` | Gauge | - | Available connections |
| `pg_replication_lag_seconds` | Gauge | - | Replication lag |

### System Metrics

| Metric | Type | Description |
|--------|------|-------------|
| `node_cpu_seconds_total` | Counter | CPU time by mode |
| `node_memory_MemTotal_bytes` | Gauge | Total memory |
| `node_memory_MemAvailable_bytes` | Gauge | Available memory |
| `node_disk_io_reads_completed_total` | Counter | Disk read operations |
| `node_load1` | Gauge | 1-minute load average |

### Cache Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `django_cache_hits_total` | Counter | cache_name | Cache hits |
| `django_cache_misses_total` | Counter | cache_name | Cache misses |
| `redis_keyspace_hits_total` | Counter | - | Redis hits |
| `redis_memory_used_bytes` | Gauge | - | Redis memory usage |

### Custom Application Metrics

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `django_messages_sent_total` | Counter | chat_type | Chat messages sent |
| `django_assignments_submitted_total` | Counter | status | Assignment submissions |
| `django_payments_processed_total` | Counter | status, method | Payments processed |
| `django_websocket_connections` | Gauge | type | Active WebSocket connections |
| `django_celery_tasks_total` | Counter | task_name, status | Celery task executions |

## Grafana Dashboards

### Available Dashboards

1. **THE_BOT Overview** (`thebot-overview.json`)
   - Request rates and latency
   - Error rates by status code
   - CPU and memory usage
   - Cache hit rates
   - Database query metrics

### Creating Custom Dashboards

1. Access Grafana at http://localhost:3000
2. Click "Create Dashboard"
3. Add panels with PromQL queries:

```promql
# Request rate
rate(django_request_total[5m])

# Error rate percentage
(sum(rate(django_request_total{status=~"5.."}[5m])) / sum(rate(django_request_total[5m]))) * 100

# P95 latency
histogram_quantile(0.95, rate(django_request_latency_seconds_bucket[5m]))

# Cache hit rate
(redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)) * 100
```

## Testing Metrics

### Running Configuration Tests

```bash
# Test Prometheus configuration files
cd monitoring
pytest tests/test_prometheus_config.py -v

# Test metrics collection logic
pytest tests/test_metrics_collection.py -v
```

### Manual Testing

```bash
# Test Django metrics endpoint
curl -s http://localhost:8000/api/system/metrics/prometheus/ | head -20

# Test health check
curl -s http://localhost:8000/api/system/health/ | json_pp

# Query Prometheus
curl 'http://localhost:9090/api/v1/query?query=django_request_total'

# Test AlertManager configuration
curl -s http://localhost:9093/api/v1/alerts | json_pp
```

## Setting Up Notifications

### Slack Integration

1. Create Slack webhook: https://api.slack.com/messaging/webhooks
2. Update `.env.production`:
   ```
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```
3. AlertManager will route critical alerts to Slack

### Email Integration

1. Configure SMTP in `.env.production`:
   ```
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=587
   SMTP_USER=your-email@gmail.com
   SMTP_PASSWORD=your-app-password
   ```
2. Configure email recipients in `alertmanager.yml`

### PagerDuty Integration

1. Create PagerDuty service and integration key
2. Update `.env.production`:
   ```
   PAGERDUTY_SERVICE_KEY=your-service-key
   ```

## Performance Tuning

### Prometheus Storage

Monitor retention settings in `prometheus.yml`:

```yaml
global:
  scrape_interval: 15s        # How often to scrape targets
  evaluation_interval: 15s    # How often to evaluate rules

# Storage settings
--storage.tsdb.retention.time=15d        # Keep 15 days of data
--storage.tsdb.retention.size=50GB       # Max 50GB storage
```

### Optimize Query Performance

1. **Use Recording Rules** - Pre-compute expensive queries
2. **Reduce Cardinality** - Avoid unbounded label values
3. **Add Indexes** - PostgreSQL indexes on frequently queried columns
4. **Aggregate Early** - Use sum() in queries instead of post-processing

### Database Query Optimization

```sql
-- Add indexes for frequently queried fields
CREATE INDEX idx_request_timestamp ON requests(timestamp);
CREATE INDEX idx_user_id ON requests(user_id);

-- Partition large tables
CREATE TABLE requests_2024_q1 PARTITION OF requests
    FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');
```

## Troubleshooting

### Prometheus Not Scraping Metrics

1. Check Prometheus targets: http://localhost:9090/targets
2. Verify metrics endpoint is accessible:
   ```bash
   curl http://localhost:8000/api/system/metrics/prometheus/
   ```
3. Check Prometheus logs:
   ```bash
   docker logs thebot-prometheus
   ```

### Alerts Not Firing

1. Verify alert rules are loaded:
   ```bash
   curl http://localhost:9090/api/v1/rules | grep -A5 "alert"
   ```
2. Check alert expressions in Prometheus graph
3. Verify AlertManager is configured:
   ```bash
   docker logs thebot-alertmanager
   ```

### High Memory Usage

1. Reduce retention period in `prometheus.yml`
2. Reduce scrape interval
3. Drop unnecessary metrics with relabel configs

### Slow Queries in Prometheus

1. Use recording rules to pre-compute values
2. Increase query timeout in Grafana data source settings
3. Optimize PromQL queries (use irate instead of rate for fast queries)

## Maintenance

### Regular Tasks

- **Daily**: Monitor alert patterns
- **Weekly**: Review slow query logs
- **Monthly**: Analyze trends and capacity planning
- **Quarterly**: Update alert thresholds based on baselines

### Backup Prometheus Data

```bash
# Snapshot Prometheus data
curl -X POST http://localhost:9090/api/v1/admin/tsdb/snapshot

# Copy snapshot to backup storage
cp -r /var/lib/prometheus/snapshots/* /backup/prometheus/
```

### Clean Up Old Data

```bash
# Delete data older than 30 days
curl -X POST http://localhost:9090/api/v1/admin/tsdb/delete_series?match[]=django_request_total
```

## Best Practices

1. **Alert on symptoms, not causes**
   - Alert on error rate, not individual 500 errors
   - Alert on latency percentiles, not average latency

2. **Use appropriate severities**
   - Critical: Service is down or losing data
   - Warning: Degraded performance or resource constraints
   - Info: Informational, no immediate action needed

3. **Minimize false positives**
   - Set reasonable thresholds based on baselines
   - Use `for` durations to avoid noise
   - Implement inhibition rules

4. **Keep metrics simple**
   - One metric, one concern
   - Use labels for dimensions, not values
   - Avoid cardinality explosions

5. **Test alert rules**
   - Validate queries in Prometheus UI
   - Test notifications with synthetic alerts
   - Document runbooks for each alert

## Documentation

- [Prometheus Documentation](https://prometheus.io/docs/)
- [PromQL Operators](https://prometheus.io/docs/prometheus/latest/querying/operators/)
- [Recording Rules](https://prometheus.io/docs/prometheus/latest/configuration/recording_rules/)
- [Alerting Rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/)
- [Grafana Documentation](https://grafana.com/docs/)

## Support

For issues or questions:
1. Check metrics endpoint: `/api/system/metrics/prometheus/`
2. Review Prometheus logs: `docker logs thebot-prometheus`
3. Check AlertManager logs: `docker logs thebot-alertmanager`
4. Verify configuration: `monitoring/prometheus/*.yml`

---

**Last Updated**: December 27, 2025
**Status**: Production Ready
