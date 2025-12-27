# Grafana Dashboards - THE_BOT Platform

Comprehensive monitoring dashboards for THE_BOT Platform using Grafana and Prometheus.

## Dashboard Overview

### 1. System Overview (`system-overview.json`)

**Purpose**: High-level system health and performance metrics
**Default Time Range**: Last 1 hour
**Refresh Interval**: 30 seconds

**Metrics**:
- Services Health Status (up/down)
- API Error Rate
- Memory Usage
- CPU Usage
- API Request Rate
- Latency Percentiles (P50, P95, P99)
- Redis Cache Hit Rate
- Database Query Rate

**Use Case**: Quick status check, identifying system-wide issues

---

### 2. Backend Metrics (`backend-metrics.json`)

**Purpose**: Detailed Django backend performance metrics
**Default Time Range**: Last 1 hour
**Refresh Interval**: 30 seconds

**Key Metrics**:
- Requests per minute
- Error Rate (5xx errors)
- P95 Latency
- Exceptions per second
- Request Rate by HTTP Method
- Request Latency Percentiles (P50, P95, P99)
- Request Rate by Status Code
- Error Rate by Endpoint
- Request Status Distribution (pie chart)

**Panels**:
- 4 stat panels for quick KPIs
- 2 time series for trends
- 1 full-width status breakdown
- 1 error detail analysis
- 1 pie chart for status distribution

**Use Case**: Backend API troubleshooting, performance analysis

---

### 3. Database Metrics (`database-metrics.json`)

**Purpose**: PostgreSQL database health and performance
**Default Time Range**: Last 1 hour
**Refresh Interval**: 30 seconds

**Key Metrics**:
- Queries per second
- Average Query Time
- CPU Time Usage
- Available Connections
- Query Rate by Type
- Query Latency Percentiles
- I/O Operations (reads/writes)
- Database Size
- Active Connections by State

**Panels**:
- 4 stat panels for critical metrics
- Query performance analysis
- I/O performance tracking
- Database health status
- Connection pool monitoring

**Use Case**: Database troubleshooting, capacity planning

---

### 4. Redis Cache (`redis-cache.json`)

**Purpose**: Redis cache performance and memory usage
**Default Time Range**: Last 1 hour
**Refresh Interval**: 30 seconds

**Key Metrics**:
- Cache Hit Rate
- Memory Usage %
- Connected Clients
- Total Keys
- Cache Hit Rate Over Time
- Commands per Second
- Memory Usage Over Time
- Hits vs Misses (cumulative)
- Keys Distribution by Database

**Panels**:
- 4 stat panels for current values
- Hit rate trend
- Command throughput
- Memory trends
- Hit/miss comparison
- DB distribution pie chart

**Use Case**: Cache optimization, memory management

---

### 5. Frontend/Nginx (`frontend-nginx.json`)

**Purpose**: Frontend web server and reverse proxy metrics
**Default Time Range**: Last 1 hour
**Refresh Interval**: 30 seconds

**Key Metrics**:
- Requests per second
- Error Rate (5xx)
- Average Latency
- Throughput (bytes/sec)
- Request Rate by Method
- Request Rate by Status Code
- Latency Percentiles (P50, P95, P99)
- Throughput Trends
- Status Distribution

**Panels**:
- 4 stat panels for current performance
- Request volume tracking
- Status code analysis
- Latency monitoring
- Bandwidth usage
- Status distribution pie chart

**Use Case**: Frontend performance analysis, CDN/Nginx optimization

---

### 6. Celery Tasks (`celery-tasks.json`)

**Purpose**: Task queue monitoring and worker health
**Default Time Range**: Last 1 hour
**Refresh Interval**: 30 seconds

**Key Metrics**:
- Tasks per 5 minutes
- Success Rate %
- Queue Length
- Active Workers
- Task Rate by Status
- Task Execution Time (mean/max/min)
- Task Count by Type
- Queue Length Over Time
- Task Status Distribution (pie chart)

**Panels**:
- 4 stat panels for queue health
- Task processing rate
- Execution time analysis
- Queue depth tracking
- Per-task type breakdown
- Status distribution

**Use Case**: Async task monitoring, queue management

---

## Dashboard Features

### Common Features (All Dashboards)

1. **Time Series Graphs**
   - Line charts for trends
   - Stacked areas for aggregates
   - Multiple series with legend

2. **Gauge Charts**
   - Circular gauges for current values
   - Color-coded thresholds (green/yellow/red)
   - Percentage or absolute units

3. **Stat Panels**
   - Large text display for KPIs
   - Background color changes based on thresholds
   - Real-time values with trend indicators

4. **Pie Charts**
   - Distribution visualization
   - Status breakdown
   - Database/task type distribution

5. **Table Panels**
   - Detailed data views
   - Sortable columns
   - Multiple aggregation functions

### Templates and Variables

Each dashboard supports template variables for flexibility:

**System Overview**:
- Time Range: 15m, 30m, 1h, 4h, 24h

Future enhancements:
- Service filter
- Environment selection
- Custom date ranges

### Thresholds and Alerts

Color-coded thresholds for quick status identification:

| Metric | Green | Yellow | Red |
|--------|-------|--------|-----|
| Error Rate | < 0.5% | 0.5-2% | > 2% |
| CPU Usage | < 50% | 50-80% | > 80% |
| Memory | < 70% | 70-90% | > 90% |
| Latency P95 | < 500ms | 500ms-1s | > 1s |
| Cache Hit Rate | > 80% | 50-80% | < 50% |
| DB Connections | < 15 | 15-20 | > 20 |
| Task Queue | < 10 | 10-100 | > 100 |
| Success Rate | > 95% | 90-95% | < 90% |

---

## Dashboard Access

### Web UI

Access Grafana at:
```
http://localhost:3000
```

### Default Credentials

- **Username**: admin
- **Password**: admin

### Navigation

1. From Home Dashboard
2. Click "Dashboards" dropdown in toolbar
3. Select desired dashboard

---

## Metrics Collection

### Data Sources

All dashboards use **Prometheus** as the primary data source:
- **URL**: http://prometheus:9090
- **Scrape Interval**: 15 seconds
- **Evaluation Interval**: 15 seconds

### Metric Retention

Prometheus data retention:
- **Duration**: 15 days (default)
- **Size Limit**: 50GB (default)
- Adjust in: `monitoring/prometheus/prometheus.yml`

---

## Dashboard Configuration

### JSON Files Location

```
monitoring/grafana/dashboards/
├── system-overview.json
├── backend-metrics.json
├── database-metrics.json
├── redis-cache.json
├── frontend-nginx.json
├── celery-tasks.json
└── thebot-overview.json (legacy)
```

### Provisioning Configuration

**Datasources**: `monitoring/grafana/provisioning/datasources/prometheus.yml`
- Auto-configures Prometheus, Loki, AlertManager
- No manual setup required

**Dashboards**: `monitoring/grafana/provisioning/dashboards/dashboard-provider.yml`
- Auto-loads all JSON files from `/var/lib/grafana/dashboards`
- Update interval: 10 seconds

---

## Using Dashboards

### Viewing Metrics

1. **Select Time Range**
   - Click time picker in top-right
   - Choose preset (last hour, last day, etc.)
   - Or set custom date range

2. **Zoom Into Panel**
   - Click panel title or chart area
   - Dashboard drills down into details
   - Breadcrumb shows context

3. **Export Data**
   - Click panel menu (⋮)
   - Select "Inspect"
   - Export as CSV or JSON

4. **Share Dashboard**
   - Click "Share" button
   - Generate sharable link
   - Set expiration time

### Customization

**Edit Dashboard**:
1. Click "Edit" button (pencil icon)
2. Modify panels, queries, layout
3. Save changes
4. Changes auto-sync to JSON file

**Add New Panels**:
1. Click "Add Panel" button
2. Choose panel type
3. Enter PromQL query
4. Configure display options
5. Save dashboard

---

## Querying Metrics

### Common PromQL Queries

**Request Rate**:
```promql
rate(django_request_total[5m])
```

**Error Rate Percentage**:
```promql
(sum(rate(django_request_total{status=~"5.."}[5m])) / sum(rate(django_request_total[5m]))) * 100
```

**Latency Percentiles**:
```promql
histogram_quantile(0.95, rate(django_request_latency_seconds_bucket[5m]))
```

**Cache Hit Rate**:
```promql
(redis_keyspace_hits_total / (redis_keyspace_hits_total + redis_keyspace_misses_total)) * 100
```

**Database Connections**:
```promql
pg_stat_activity_count
```

**CPU Usage**:
```promql
100 - (avg(rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

**Memory Usage**:
```promql
(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100
```

---

## Troubleshooting

### Dashboard Not Loading

**Symptom**: "No Data" or empty panels

**Solutions**:
1. Check Prometheus connectivity:
   ```bash
   curl http://prometheus:9090/api/v1/targets
   ```

2. Verify metrics are being collected:
   ```bash
   curl http://localhost:8000/api/system/metrics/prometheus/
   ```

3. Check datasource configuration:
   - Settings → Data Sources → Prometheus
   - Click "Test" button

4. Verify time range:
   - Select longer time range (last 24 hours)
   - Metrics may not exist in selected range

### Slow Dashboard Loading

**Symptom**: Dashboard takes >5 seconds to load

**Solutions**:
1. Reduce time range (e.g., last 1 hour instead of 7 days)
2. Optimize PromQL queries:
   - Avoid wildcards in metric names
   - Use recording rules for complex queries
   - Add rate() for counters

3. Increase Prometheus resources:
   - More CPU for evaluation
   - More memory for retention

### Missing Metrics

**Symptom**: Some panels show "No Data"

**Check**:
1. Are exporters running?
   - node_exporter for system metrics
   - postgres_exporter for database
   - Django metrics endpoint for application

2. Is Prometheus scraping?
   - Visit http://localhost:9090/targets
   - Check "UP" status for each target

3. Are metrics exposed correctly?
   - Visit exporter endpoint: http://localhost:9100/metrics
   - Search for expected metric name

---

## Performance Tuning

### Dashboard Refresh Rate

Recommended settings by use case:

| Use Case | Refresh Rate | Time Range |
|----------|--------------|------------|
| Real-time monitoring | 5s | Last 1 hour |
| Production monitoring | 30s | Last 4 hours |
| Trend analysis | 1m | Last 24 hours |
| Capacity planning | 5m | Last 7 days |

### Query Performance

Optimize queries for faster loading:

1. **Use Recording Rules**
   ```yaml
   - record: django_request:rate5m
     expr: rate(django_request_total[5m])
   ```

2. **Aggregate at Query Time**
   ```promql
   sum(rate(django_request_total[5m])) by (status)
   ```

3. **Avoid Regular Expressions**
   ```promql
   # Bad
   django_request_total{endpoint=~".*api.*"}

   # Good
   django_request_total{endpoint="/api/users/"}
   ```

---

## Best Practices

### Dashboard Design

1. **Consistent Layout**
   - Place important metrics at top
   - Use consistent panel sizes
   - Group related metrics

2. **Readable Legends**
   - Use descriptive names
   - Format values with units (%, ms, bytes)
   - Show min/max/mean for trends

3. **Alert Visualization**
   - Color-code thresholds
   - Show alert status in panel title
   - Include runbook links

### Monitoring

1. **Alert on Symptoms, Not Causes**
   - Alert on error rate, not on 500 errors
   - Alert on latency, not on CPU

2. **Meaningful Thresholds**
   - Based on SLAs
   - Set at 80% of SLA limit
   - Review quarterly

3. **Documentation**
   - Add panel descriptions
   - Document metric meanings
   - Include troubleshooting guides

---

## Maintenance

### Regular Tasks

**Daily**:
- Monitor alert patterns
- Check error rates
- Review latency trends

**Weekly**:
- Analyze slow query logs
- Review resource usage
- Check disk space

**Monthly**:
- Analyze trends
- Review thresholds
- Update runbooks
- Capacity planning

### Backup Dashboards

Dashboards are stored as JSON files in Git:

```bash
# Dashboards
monitoring/grafana/dashboards/

# Version control
git add monitoring/grafana/dashboards/
git commit -m "Update dashboards"
git push
```

### Update Dashboards

1. Modify dashboard in UI
2. Save changes
3. Export as JSON:
   - Click share → export
   - Update file in repository
4. Commit and push

---

## Advanced Features

### Variables and Templating

Create dashboard variables for flexibility:

```json
{
  "name": "environment",
  "type": "query",
  "datasource": "Prometheus",
  "query": "label_values(up, env)"
}
```

Then use in queries:
```promql
django_request_total{env="$environment"}
```

### Annotations

Mark important events on charts:

1. Click graph to add annotation
2. Set time and description
3. Optional: link to alert or incident

### Cross-Dashboard Links

Link between dashboards:

1. Edit panel
2. "Links" section
3. Add dashboard link
4. Specify target dashboard

---

## Support and Documentation

- **Grafana Docs**: https://grafana.com/docs/
- **PromQL Guide**: https://prometheus.io/docs/prometheus/latest/querying/
- **Dashboard Gallery**: https://grafana.com/grafana/dashboards/
- **Community**: https://community.grafana.com/

---

## Dashboard Checklist

Before deploying new dashboards:

- [ ] All panels have meaningful titles
- [ ] Units are correctly formatted
- [ ] Thresholds are set appropriately
- [ ] Legend is readable
- [ ] Queries are optimized
- [ ] Refresh rate is appropriate
- [ ] Dashboard loads within 3 seconds
- [ ] No hardcoded IP addresses
- [ ] Documentation is complete
- [ ] Tested in production environment

---

**Last Updated**: December 27, 2025
**Status**: Production Ready
**Version**: 1.0.0
