# THE_BOT Platform - Logging & Monitoring Configuration

## What's New in This Update

### 1. Enhanced Logstash Pipelines

#### API Pipeline (pipelines/api-pipeline.conf)
- Specialized processing for API requests and responses
- Inputs: File logs and TCP streaming (port 5001)
- Key metrics: request_id, http_method, endpoint, http_status, response_time_ms, user_id, client_ip
- Performance categorization: fast (<50ms), moderate (50-500ms), slow (500-1000ms), very_slow (>1000ms)
- Output indices: thebot-api-*, thebot-api-performance-*, thebot-api-errors-*

#### Security Pipeline (pipelines/security-pipeline.conf)
- Threat detection and pattern analysis
- Detects: SQL injection, XSS, brute force, unauthorized access, credential exposure
- Inputs: File logs, TCP (port 5002), Syslog (port 5003)
- Severity levels: critical, high, medium, info
- Output indices: thebot-security-*, thebot-security-critical-*, thebot-auth-*

### 2. Kibana Dashboards

#### API Performance Dashboard
- Requests per minute (traffic volume)
- Response time percentiles (p50, p95, p99)
- HTTP status distribution
- Top slowest endpoints
- Error rate gauge (target < 2%)
- Success rate gauge (target > 95%)
- Response time heatmap
- Server errors (5xx) count
- Slow requests (p95 > 1s) count

#### Security Events Dashboard
- Security events timeline
- Critical/high/medium alerts count
- Failed login attempts by username
- Suspicious source IPs
- Threat type distribution
- Attack timeline (hourly)
- Injection attack count
- Blocked/rate limited IPs

### 3. Alert Rules (16 Total)

**Critical Alerts:**
- High API Error Rate (>5%)
- Server Errors (5xx)
- Brute Force Attack
- SQL Injection Attempt
- Credential Exposure

**High Priority:**
- Slow API Response (p95 > 1000ms)
- Failed Login Attempts (5+ in 5 min)
- XSS Attack
- Unauthorized Access
- Suspicious Data Export

**Medium Priority:**
- Rate Limit Exceeded
- Database Connection Pool (>80%)
- Elasticsearch Health
- Log Processing Lag
- Unusual API Behavior
- Geographic Anomaly

### 4. Index Lifecycle Management (ILM)

Automatic index management with phases:
- HOT (0-7 days): High indexing, full replicas, fast search
- WARM (7-30 days): Index shrinking, reduced replicas
- COLD (30-120 days): S3 snapshots, searchable snapshots
- DELETE (>120 days): Automatic removal

Retention: 30 days online, 90 days archived, 7 years for security logs

### 5. Notification Channels

- Email (SMTP configuration)
- Slack (webhook integration)
- PagerDuty (incident management)

## Configuration Files

```
logging/
├── logstash/
│   ├── pipelines/
│   │   ├── api-pipeline.conf       (NEW)
│   │   └── security-pipeline.conf  (NEW)
│   ├── pipelines.yml               (NEW)
│
├── kibana/
│   └── dashboards/
│       ├── api-dashboard.ndjson    (NEW)
│       └── security-dashboard.ndjson (NEW)
│
├── elasticsearch/
│   └── ilm-policy.json             (NEW)
│
├── alerts/
│   └── alert-rules.json            (NEW)
│
└── docs/
    └── LOGGING_MONITORING.md       (NEW)
```

## Quick Start

### 1. Start ELK Stack
```bash
cd logging
docker-compose up -d
```

### 2. Verify Health
```bash
curl http://localhost:9200/_cluster/health?pretty
curl http://localhost:9600
curl http://localhost:5601/api/status
```

### 3. Configure Django Logging
```python
from logging.python_logging_config import get_logging_config
LOGGING = get_logging_config(
    log_level='INFO',
    elasticsearch_host='localhost:9200',
    logstash_host='localhost:5000'
)
```

### 4. Import Dashboards
```bash
curl -X POST "localhost:5601/api/saved_objects/dashboard" \
  -H 'kbn-xsrf: true' \
  -d @logging/kibana/dashboards/api-dashboard.ndjson
```

### 5. Setup Alerts
```bash
cd logging/alerts
chmod +x setup-alerts.sh
./setup-alerts.sh
```

### 6. Configure Notifications
Edit .env with credentials:
```bash
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com

SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

PAGERDUTY_API_KEY=your-key
```

## API Log Format

```
[2025-12-27T10:30:45.123Z] [INFO] request_id=550e8400-e29b-41d4-a716-446655440000
endpoint=/api/v1/users/123 http_method=GET status=200 duration_ms=45.2
user_id=42 remote_ip=192.168.1.100 api_version=1.0
```

## Key Metrics to Monitor

### API Performance
- Error Rate: < 2% (alert at > 5%)
- p95 Response Time: < 1000ms
- p99 Response Time: < 2000ms
- Success Rate: > 95%
- 5xx Errors: 0

### Security
- Critical Alerts: 0 (investigate immediately)
- Failed Logins: < 5 per user per 5 min
- Injection Attempts: 0 (all blocked)
- Blocked IPs: Track active blocks
- Credential Exposures: 0

### Infrastructure
- Index Creation Rate: 1 per day
- Disk Usage: < 80%
- Processing Lag: < 1 minute
- Elasticsearch Health: Green

## Troubleshooting

### Logs Not Appearing
1. Check Logstash: `docker-compose logs logstash`
2. Verify input files exist
3. Check Elasticsearch: `curl http://localhost:9200/_cat/indices`
4. Review GROK patterns

### High Disk Usage
1. Check indices: `curl http://localhost:9200/_cat/indices?v&h=index,store.size`
2. Enable ILM
3. Reduce retention period
4. Archive old indices

### Dashboards Not Loading
1. Verify index patterns exist
2. Check for data in time range
3. Clear Kibana cache

### Alerts Not Firing
1. Verify condition data exists
2. Test alert manually
3. Check notification configuration

## Performance Tips

- Increase Logstash workers for throughput
- Enable index compression
- Use ILM for automatic management
- Pre-calculate metrics in Logstash
- Optimize Elasticsearch queries

## Next Steps

1. Monitor dashboards daily
2. Review alerts and respond to issues
3. Optimize thresholds based on baseline
4. Regular S3 backups
5. Keep runbooks updated

---

**Version**: 1.0.0
**Last Updated**: December 27, 2025
**Status**: Production Ready
