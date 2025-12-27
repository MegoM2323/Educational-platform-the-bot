# Grafana Setup Guide - THE_BOT Platform

Complete setup and configuration guide for Grafana monitoring dashboards.

## Quick Start

### 1. Start Grafana Service

```bash
# Start monitoring stack with Grafana
docker-compose -f monitoring/docker-compose.monitoring.yml up -d grafana

# Verify Grafana is running
docker-compose -f monitoring/docker-compose.monitoring.yml ps grafana
```

### 2. Access Grafana UI

Open browser and navigate to:
```
http://localhost:3000
```

**Default Credentials**:
- Username: `admin`
- Password: `admin`

**First Login**:
1. Enter default credentials
2. Change password (recommended for production)
3. Accept any setup prompts

### 3. Verify Datasources

1. Click Settings icon (⚙️) in left sidebar
2. Select "Data Sources"
3. Verify these are configured:
   - **Prometheus** (http://prometheus:9090) - Default
   - **Loki** (http://loki:3100)
   - **Alertmanager** (http://alertmanager:9093)

4. Click on Prometheus and test connection:
   - Click "Test" button
   - Should show "Data source is working"

### 4. View Dashboards

1. Click Dashboards icon (squares) in left sidebar
2. Click "Browse"
3. You should see all 6 dashboards:
   - System Overview
   - Backend Metrics
   - Database Metrics
   - Redis Cache
   - Frontend/Nginx
   - Celery Tasks

Click any dashboard to view metrics.

---

## Docker Setup

### Environment Variables

Set these in `docker-compose.monitoring.yml`:

```yaml
services:
  grafana:
    environment:
      # Admin credentials
      GF_SECURITY_ADMIN_USER: admin
      GF_SECURITY_ADMIN_PASSWORD: admin  # Change in production!

      # Database
      GF_DATABASE_TYPE: sqlite3

      # Server
      GF_SERVER_ROOT_URL: http://localhost:3000
      GF_SERVER_HTTP_PORT: 3000

      # Logging
      GF_LOG_LEVEL: info

      # Anonymous access (optional)
      GF_AUTH_ANONYMOUS_ENABLED: "false"
```

### Docker Compose Configuration

Required services:

```yaml
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-storage:/prometheus

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    volumes:
      - grafana-storage:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    depends_on:
      - prometheus

  loki:
    image: grafana/loki:latest
    ports:
      - "3100:3100"
    volumes:
      - ./loki/loki-config.yml:/etc/loki/local-config.yml

  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager/alertmanager.yml:/etc/alertmanager/alertmanager.yml

volumes:
  grafana-storage:
  prometheus-storage:
```

---

## Provisioning System

Grafana uses provisioning to auto-configure dashboards and datasources.

### How It Works

1. **Datasource Provisioning**
   - File: `monitoring/grafana/provisioning/datasources/prometheus.yml`
   - Automatically configures Prometheus, Loki, AlertManager
   - Changes detected every 10 seconds

2. **Dashboard Provisioning**
   - File: `monitoring/grafana/provisioning/dashboards/dashboard-provider.yml`
   - Auto-loads all JSON files from `/var/lib/grafana/dashboards`
   - Changes detected every 10 seconds

### Provisioning Directory Structure

```
monitoring/grafana/
├── dashboards/
│   ├── system-overview.json
│   ├── backend-metrics.json
│   ├── database-metrics.json
│   ├── redis-cache.json
│   ├── frontend-nginx.json
│   ├── celery-tasks.json
│   └── thebot-overview.json
└── provisioning/
    ├── dashboards/
    │   └── dashboard-provider.yml
    ├── datasources/
    │   └── prometheus.yml
    └── notifiers/
        └── slack.yml
```

### Modifying Provisioned Dashboards

1. **Via UI (Recommended)**
   - Edit dashboard in UI
   - Save changes
   - Changes are persisted to JSON file

2. **Via JSON File**
   - Edit JSON file directly
   - Grafana reloads within 10 seconds
   - No restart required

### Adding New Datasources

1. Create YAML in `provisioning/datasources/`
2. Add to `provisioning/datasources/prometheus.yml`:
   ```yaml
   datasources:
     - name: MyDataSource
       type: prometheus
       access: proxy
       url: http://my-service:9090
   ```
3. Restart Grafana or wait 10 seconds for auto-reload

---

## Dashboard Management

### Creating Custom Dashboards

1. Click "+" icon → "Dashboard"
2. Add panels with PromQL queries
3. Configure visualization (line chart, gauge, etc.)
4. Save dashboard:
   - Give it a name (e.g., "My Custom Dashboard")
   - Save to folder (default is "General")
   - JSON is auto-generated

### Exporting Dashboards

1. Click dashboard title → "Share" → "Export"
2. Copy JSON
3. Save to `monitoring/grafana/dashboards/my-dashboard.json`
4. Commit to Git

### Importing Dashboards

1. Click "+" icon → "Import"
2. Paste JSON or enter Grafana ID
3. Select datasource (Prometheus)
4. Click "Import"

### Dashboard Folder Organization

Create folders to organize dashboards:

1. Click Settings (⚙️) → Folders
2. Create new folder
3. Move dashboards to folder
4. Organize by service/team

---

## Alerting Configuration

### Setting Up Alerts

1. **Create Alert Rule**
   - Edit panel → "Alert" tab
   - Set condition (e.g., error rate > 5%)
   - Set evaluation period (e.g., 5 minutes)
   - Set pause duration (e.g., 5 minutes to prevent spam)

2. **Configure Notification Channel**
   - Settings → Notification channels
   - Add channel (Slack, Email, PagerDuty, etc.)
   - Test notification

3. **Attach to Alert Rule**
   - Edit alert rule
   - Select notification channel
   - Save dashboard

### Alert Rule Best Practices

```
Condition:
  metric > threshold

For: 5m
  Prevents noisy alerts from temporary spikes

Pause for: 5m
  Reduces alert fatigue if already firing
```

### Common Alert Queries

**API Error Rate**:
```promql
(sum(rate(django_request_total{status=~"5.."}[5m])) / sum(rate(django_request_total[5m]))) * 100 > 5
```

**High Latency**:
```promql
histogram_quantile(0.95, rate(django_request_latency_seconds_bucket[5m])) > 1
```

**Database Slow Queries**:
```promql
pg_stat_statements_mean_exec_time > 5000
```

---

## Authentication & Security

### Enable Auth

1. Go to Settings (⚙️)
2. Select "Server"
3. Configure auth provider (Google, GitHub, LDAP, etc.)

### User Management

1. Settings → Users
2. Add new user
3. Assign role:
   - **Viewer**: Read-only access
   - **Editor**: Can edit dashboards
   - **Admin**: Full access

### Security Settings

1. Go to Settings (⚙️) → Security
2. Enable:
   - OAuth
   - SSL/TLS
   - Security headers
3. Set password policy:
   - Minimum length
   - Require uppercase/numbers/special chars

### HTTPS/SSL Setup

1. Generate SSL certificate:
   ```bash
   openssl req -x509 -nodes -days 365 \
     -newkey rsa:2048 \
     -keyout /etc/grafana/certs/grafana.key \
     -out /etc/grafana/certs/grafana.crt
   ```

2. Update `docker-compose.yml`:
   ```yaml
   grafana:
     environment:
       GF_SERVER_PROTOCOL: https
       GF_SERVER_CERT_FILE: /etc/grafana/certs/grafana.crt
       GF_SERVER_CERT_KEY: /etc/grafana/certs/grafana.key
   ```

---

## Performance Optimization

### Dashboard Performance

**Optimize Panel Queries**:
1. Avoid long time ranges (use max 30 days)
2. Use recording rules for complex queries
3. Aggregate data in query (use `sum()`, `avg()`)
4. Reduce graph resolution (1m interval instead of 15s)

**Refresh Rates**:
| Use Case | Refresh | Time Range |
|----------|---------|-----------|
| Real-time | 5s | 1h |
| Standard | 30s | 4h |
| Analytics | 1m | 24h |
| Capacity | 5m | 7d |

### Grafana Server Performance

**Memory Settings**:
```yaml
grafana:
  environment:
    GF_INSTALL_PLUGINS: grafana-piechart-panel
  resources:
    limits:
      memory: 512Mi
    requests:
      memory: 256Mi
```

**Database Optimization**:
- Use PostgreSQL instead of SQLite for production
- Enable connection pooling
- Regular vacuuming of database

### Prometheus Performance

**Retention Tuning**:
```yaml
prometheus:
  command:
    - '--storage.tsdb.retention.time=15d'
    - '--storage.tsdb.retention.size=50GB'
```

---

## Troubleshooting

### Dashboard Not Loading

**Symptom**: Empty panels, "No Data"

**Steps**:
1. Check Prometheus is running:
   ```bash
   docker logs thebot-prometheus
   ```

2. Test Prometheus endpoint:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

3. Check datasource in Grafana:
   - Settings → Data Sources → Prometheus
   - Click "Test" button
   - Check error message

4. Verify metrics are being scraped:
   ```bash
   curl http://localhost:9090/api/v1/query?query=up
   ```

### Slow Dashboard Loading

**Symptom**: Takes >5 seconds to load

**Solutions**:
1. Reduce time range in dashboard
2. Optimize queries (remove wildcards)
3. Enable query caching
4. Increase Prometheus resources

### Missing Metrics

**Check**:
1. Is exporter running? `docker ps | grep exporter`
2. Is Prometheus scraping? Visit http://localhost:9090/targets
3. Is metric exported correctly? Visit exporter endpoint
4. Check metric exists: `curl http://localhost:9090/api/v1/query?query=metric_name`

### Authentication Issues

**Can't Login**:
1. Reset admin password:
   ```bash
   docker exec -it thebot-grafana grafana-cli admin reset-admin-password newpassword
   ```

2. Check logs:
   ```bash
   docker logs thebot-grafana
   ```

---

## Maintenance

### Regular Tasks

**Daily**:
- Monitor alert patterns
- Check for failed scrapes
- Review error rates

**Weekly**:
- Review slow queries
- Check storage usage
- Analyze trends

**Monthly**:
- Update thresholds
- Review alert rules
- Capacity planning
- Backup dashboards

### Backup Dashboards

```bash
# Export all dashboards as JSON
cd monitoring/grafana/dashboards/
for dashboard in *.json; do
  git add "$dashboard"
done
git commit -m "Backup dashboards"
git push
```

### Update Grafana

```bash
# Check current version
docker exec thebot-grafana grafana-cli -version

# Update image in docker-compose.yml
# image: grafana/grafana:latest

# Restart service
docker-compose -f monitoring/docker-compose.monitoring.yml up -d grafana --no-deps
```

### Monitor Grafana Health

```bash
# Check service is running
curl -s http://localhost:3000/api/health

# Check database status
docker logs thebot-grafana | grep database

# Monitor resource usage
docker stats thebot-grafana
```

---

## Advanced Configuration

### Using PostgreSQL Database

For production, use PostgreSQL instead of SQLite:

```yaml
grafana:
  environment:
    GF_DATABASE_TYPE: postgres
    GF_DATABASE_HOST: postgres:5432
    GF_DATABASE_NAME: grafana
    GF_DATABASE_USER: grafana
    GF_DATABASE_PASSWORD: grafana_password
  depends_on:
    - postgres

postgres:
  image: postgres:15
  environment:
    POSTGRES_DB: grafana
    POSTGRES_USER: grafana
    POSTGRES_PASSWORD: grafana_password
  volumes:
    - postgres-storage:/var/lib/postgresql/data
```

### LDAP Authentication

```yaml
grafana:
  environment:
    GF_AUTH_LDAP_ENABLED: "true"
  volumes:
    - ./grafana/ldap.toml:/etc/grafana/ldap.toml
```

### OAuth/SAML

```yaml
grafana:
  environment:
    GF_AUTH_GOOGLE_ENABLED: "true"
    GF_AUTH_GOOGLE_CLIENT_ID: your-client-id
    GF_AUTH_GOOGLE_CLIENT_SECRET: your-client-secret
```

---

## Testing

### Run Dashboard Tests

```bash
# Test dashboard structure
pytest monitoring/tests/test_grafana_dashboards.py -v

# Test specific dashboard
pytest monitoring/tests/test_grafana_dashboards.py::TestDashboardStructure -v
```

### Manual Testing Checklist

- [ ] Grafana loads without errors
- [ ] All dashboards visible
- [ ] Can select time range
- [ ] Metrics display correctly
- [ ] Can export data
- [ ] Can create new dashboard
- [ ] Can edit existing dashboard
- [ ] Alerts work correctly
- [ ] Notifications send (Slack, email, etc.)
- [ ] User management works

---

## Support

- **Grafana Documentation**: https://grafana.com/docs/grafana/
- **Community Forum**: https://community.grafana.com/
- **Issues/Bugs**: https://github.com/grafana/grafana/issues

---

**Last Updated**: December 27, 2025
**Status**: Production Ready
**Version**: 1.0.0
