# PromQL Query Examples for THE_BOT Platform

Common PromQL queries for monitoring and alerting.

## HTTP Request Metrics

### Request Rate

```promql
# Total request rate (requests per second)
rate(django_request_total[5m])

# Request rate by method
sum(rate(django_request_total[5m])) by (method)

# Request rate by endpoint
sum(rate(django_request_total[5m])) by (endpoint)

# Request rate by status code
sum(rate(django_request_total[5m])) by (status)

# Request rate for specific status codes (5xx errors)
sum(rate(django_request_total{status=~"5.."}[5m]))
```

### Request Latency

```promql
# Average request latency
rate(django_request_latency_seconds_sum[5m]) / rate(django_request_latency_seconds_count[5m])

# 95th percentile latency
histogram_quantile(0.95, rate(django_request_latency_seconds_bucket[5m]))

# 99th percentile latency
histogram_quantile(0.99, rate(django_request_latency_seconds_bucket[5m]))

# 99.9th percentile latency
histogram_quantile(0.999, rate(django_request_latency_seconds_bucket[5m]))

# Latency by endpoint
histogram_quantile(0.95, rate(django_request_latency_seconds_bucket[5m])) by (endpoint)
```

### Error Metrics

```promql
# Error rate (percentage)
(sum(rate(django_request_total{status=~"5.."}[5m])) / sum(rate(django_request_total[5m]))) * 100

# 4xx error rate
(sum(rate(django_request_total{status=~"4.."}[5m])) / sum(rate(django_request_total[5m]))) * 100

# 5xx error rate
(sum(rate(django_request_total{status=~"5.."}[5m])) / sum(rate(django_request_total[5m]))) * 100

# Errors per second
sum(rate(django_request_total{status=~"5.."}[5m]))

# Errors by endpoint
sum(rate(django_request_total{status=~"5.."}[5m])) by (endpoint)
```

## Database Metrics

### Query Performance

```promql
# Average query execution time
rate(django_db_execute_time_seconds_sum[5m]) / rate(django_db_execute_time_seconds_count[5m])

# Queries per second
rate(django_db_execute_total[5m])

# Slow queries (>100ms)
rate(django_db_slow_query_total[5m])

# Query time distribution by percentile
histogram_quantile(0.95, rate(django_db_execute_time_seconds_bucket[5m]))

# Top slowest queries
topk(5, avg(django_db_execute_time_seconds_bucket) by (table))
```

### Connection Pool

```promql
# Active database connections
pg_active_transactions

# Available connections
pg_connections_available

# Connection pool utilization percentage
(pg_active_transactions / pg_connections_available) * 100

# Connection pool saturation alert
(pg_active_transactions / pg_connections_available) > 0.8
```

### Replication

```promql
# Replication lag in seconds
pg_replication_lag_seconds

# Replication lag alert (>10 seconds)
pg_replication_lag_seconds > 10
```

### Table Statistics

```promql
# Sequential scans per second
rate(pg_stat_user_tables_seq_scan[5m])

# Index scans per second
rate(pg_stat_user_tables_idx_scan[5m])

# Sequential to index scan ratio
rate(pg_stat_user_tables_seq_scan[5m]) / (rate(pg_stat_user_tables_seq_scan[5m]) + rate(pg_stat_user_tables_idx_scan[5m]))

# Live tuples in largest tables
topk(10, pg_stat_user_tables_live_tuples)
```

## Cache Metrics

### Hit Rate

```promql
# Cache hit rate (percentage)
(redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)) * 100

# Cache hit rate by cache
(redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)) * 100

# Django cache hit rate
(rate(django_cache_hits_total[5m]) / (rate(django_cache_hits_total[5m]) + rate(django_cache_misses_total[5m]))) * 100
```

### Memory Usage

```promql
# Redis memory usage
redis_used_memory

# Redis memory usage in GB
redis_used_memory / 1024 / 1024 / 1024

# Redis memory as percentage of peak
(redis_used_memory / redis_used_memory_peak) * 100

# Redis memory alert (>90% of peak)
(redis_used_memory / redis_used_memory_peak) > 0.9
```

### Operations

```promql
# Commands processed per second
rate(redis_commands_processed_total[5m])

# Evictions per second
rate(redis_evicted_keys_total[5m])

# Expirations per second
rate(redis_expired_keys_total[5m])

# Connected clients
redis_connected_clients
```

## System Metrics

### CPU Usage

```promql
# CPU usage percentage (0-100%)
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)

# CPU usage per core
100 - (rate(node_cpu_seconds_total{mode="idle"}[5m]) * 100)

# CPU usage by mode
sum(rate(node_cpu_seconds_total[5m])) by (mode)

# CPU alert (>80%)
(100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 80

# Critical CPU alert (>95%)
(100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 95
```

### Memory Usage

```promql
# Memory usage percentage
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100

# Memory usage in GB
(node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / 1024 / 1024 / 1024

# Memory alert (>80%)
((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100) > 80

# Critical memory alert (>95%)
((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100) > 95
```

### Disk Usage

```promql
# Disk usage percentage
node_filesystem_avail_bytes{mountpoint="/"} / node_filesystem_size_bytes{mountpoint="/"} * 100

# Disk I/O read rate
rate(node_disk_io_reads_completed_total[5m])

# Disk I/O write rate
rate(node_disk_io_writes_completed_total[5m])

# Total disk I/O
(rate(node_disk_io_reads_completed_total[5m]) + rate(node_disk_io_writes_completed_total[5m]))

# Disk I/O alert (>1000 ops/s)
(rate(node_disk_io_reads_completed_total[5m]) + rate(node_disk_io_writes_completed_total[5m])) > 1000
```

### Load Average

```promql
# 1-minute load average
node_load1

# 5-minute load average
node_load5

# 15-minute load average
node_load15

# Load relative to CPU count
node_load1 / count(count(node_cpu_seconds_total) by (cpu))

# High load alert (>80% of CPU count)
(node_load5 / count(count(node_cpu_seconds_total) by (cpu))) > 0.8
```

### Network

```promql
# Network receive rate (bytes/sec)
rate(node_network_receive_bytes_total[5m])

# Network transmit rate (bytes/sec)
rate(node_network_transmit_bytes_total[5m])

# Network receive rate in Mbps
(rate(node_network_receive_bytes_total[5m]) * 8) / 1024 / 1024

# Network transmit rate in Mbps
(rate(node_network_transmit_bytes_total[5m]) * 8) / 1024 / 1024

# Total network traffic
(rate(node_network_receive_bytes_total[5m]) + rate(node_network_transmit_bytes_total[5m]))
```

## Application Custom Metrics

### Chat System

```promql
# Chat messages per second
rate(django_messages_sent_total[5m])

# Messages by chat type
sum(rate(django_messages_sent_total[5m])) by (chat_type)

# Active WebSocket connections
django_websocket_connections

# Active WebSocket connections by type
django_websocket_connections{type="chat"}
```

### Assignments

```promql
# Submissions per second
rate(django_assignments_submitted_total[5m])

# Submissions by status
sum(rate(django_assignments_submitted_total[5m])) by (status)

# Submission rate over time
sum(rate(django_assignments_submitted_total[5m])) by (status)
```

### Payments

```promql
# Payments processed per second
rate(django_payments_processed_total[5m])

# Successful payments per second
rate(django_payments_processed_total{status="success"}[5m])

# Failed payments per second
rate(django_payments_processed_total{status="failed"}[5m])

# Payment failure rate
(rate(django_payments_processed_total{status="failed"}[5m]) / rate(django_payments_processed_total[5m])) * 100

# Payments by method
sum(rate(django_payments_processed_total[5m])) by (method)
```

### Celery Tasks

```promql
# Task executions per second
rate(django_celery_tasks_total[5m])

# Task success rate
(rate(django_celery_tasks_total{status="success"}[5m]) / rate(django_celery_tasks_total[5m])) * 100

# Task failure rate
(rate(django_celery_tasks_total{status="failure"}[5m]) / rate(django_celery_tasks_total[5m])) * 100

# Task execution time (average)
rate(django_celery_task_duration_seconds_sum[5m]) / rate(django_celery_task_duration_seconds_count[5m])

# Task execution time (p95)
histogram_quantile(0.95, rate(django_celery_task_duration_seconds_bucket[5m]))

# Slowest tasks
topk(5, avg(django_celery_task_duration_seconds_bucket) by (task_name))
```

## Composite Metrics

### API Health Score

```promql
# Health score (0-100, 100 = perfect)
100 - (
  (rate(django_request_total{status=~"5.."}[5m]) / rate(django_request_total[5m])) * 50 +
  (histogram_quantile(0.95, rate(django_request_latency_seconds_bucket[5m])) / 1) * 50
)
```

### System Health Score

```promql
# Combined system health (0-100)
(
  (100 - (100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) / 95) * 40 +
  (100 - ((1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100) / 95) * 40 +
  (100 - ((rate(django_request_total{status=~"5.."}[5m]) / rate(django_request_total[5m])) * 100) / 5) * 20
)
```

### Service Availability

```promql
# Django availability
up{job="django-backend"}

# Frontend availability
up{job="nodejs-frontend"}

# Database availability
up{job="postgres-exporter"}

# Redis availability
up{job="redis-exporter"}

# Overall service availability
count(up{job=~"django-backend|nodejs-frontend|postgres-exporter|redis-exporter"}) / 4 * 100
```

## Alerting Queries

### Critical Alerts

```promql
# API error rate critical (>10%)
(sum(rate(django_request_total{status=~"5.."}[5m])) / sum(rate(django_request_total[5m]))) * 100 > 10

# Service down
up{job="django-backend"} == 0

# Database down
up{job="postgres-exporter"} == 0

# Critical CPU usage (>95%)
(100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 95
```

### Warning Alerts

```promql
# API error rate warning (>5%)
(sum(rate(django_request_total{status=~"5.."}[5m])) / sum(rate(django_request_total[5m]))) * 100 > 5

# High latency (P95 >1s)
histogram_quantile(0.95, rate(django_request_latency_seconds_bucket[5m])) > 1

# High CPU usage (>80%)
(100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)) > 80

# High memory usage (>80%)
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100 > 80

# Low cache hit rate (<50%)
(redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)) * 100 < 50
```

## Tips and Best Practices

### 1. Use Recording Rules for Complex Queries

Instead of running complex queries in Grafana every time:

```yaml
# Use recording rules (in prometheus.yml)
- record: api_error_rate_5m
  expr: (sum(rate(django_request_total{status=~"5.."}[5m])) / sum(rate(django_request_total[5m]))) * 100
```

Then use in alerts:
```yaml
alert: HighErrorRate
expr: api_error_rate_5m > 5
```

### 2. Use `rate()` for Counters

```promql
# Good - measures increase rate
rate(django_request_total[5m])

# Bad - gives absolute value
django_request_total
```

### 3. Use `histogram_quantile()` for Percentiles

```promql
# Good - accurate percentile
histogram_quantile(0.95, rate(django_request_latency_seconds_bucket[5m]))

# Bad - inaccurate
topk(1, django_request_latency_seconds)
```

### 4. Use Labels for Dimensions

```promql
# Good - aggregates by endpoint
sum(rate(django_request_total[5m])) by (endpoint)

# Bad - creates too many series
{request_endpoint="users"}, {request_endpoint="posts"}, ...
```

### 5. Test Queries in Prometheus UI

1. Go to http://localhost:9090/graph
2. Enter your query
3. Click "Execute"
4. Check the "Graph" tab to visualize

---

**Last Updated**: December 27, 2025
