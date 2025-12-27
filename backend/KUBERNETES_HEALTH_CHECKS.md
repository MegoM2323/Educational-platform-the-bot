# Kubernetes Health Check Endpoints

Kubernetes-ready health check endpoints for monitoring and managing containerized deployments.

## Overview

The THE_BOT platform provides three health check endpoints optimized for Kubernetes probe configurations:

1. **Liveness Probe** - Checks if pod should be restarted
2. **Readiness Probe** - Checks if pod is ready to handle traffic
3. **Detailed Health** - Full system diagnostics and metrics

## Endpoint Specification

### 1. Liveness Endpoint

**Path:** `GET /api/health/live/`

**Purpose:** Check if service is running (alive)

**Authentication:** Not required (AllowAny)

**Response Time:** <100ms (instant)

**HTTP Status Codes:**
- `200 OK` - Service is alive

**Response Format:**
```json
{
  "status": "alive",
  "timestamp": "2025-12-27T10:00:00Z"
}
```

**Use Case:**
```yaml
# Kubernetes Pod Configuration
livenessProbe:
  httpGet:
    path: /api/health/live/
    port: 8000
    scheme: HTTP
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

**Behavior:**
- No heavy checks performed
- Always returns 200 (process is running)
- Use for Kubernetes restart decisions
- If this fails, Kubernetes will restart the pod

---

### 2. Readiness Endpoint

**Path:** `GET /api/health/ready/`

**Purpose:** Check if service is ready to handle requests

**Authentication:** Not required (AllowAny)

**Response Time:** 50-200ms (typical)

**HTTP Status Codes:**
- `200 OK` - Service is ready
- `503 Service Unavailable` - Service not ready

**Response Format (Ready):**
```json
{
  "status": "ready",
  "timestamp": "2025-12-27T10:00:00Z",
  "checks": {
    "database": {
      "status": "ok",
      "response_time_ms": 5
    },
    "redis": {
      "status": "ok",
      "response_time_ms": 2
    },
    "celery": {
      "status": "ok",
      "response_time_ms": 1,
      "pending_tasks": 10
    }
  }
}
```

**Response Format (Not Ready):**
```json
{
  "status": "not_ready",
  "timestamp": "2025-12-27T10:00:00Z",
  "checks": {
    "database": {
      "status": "error",
      "response_time_ms": 0
    },
    "redis": {
      "status": "ok",
      "response_time_ms": 2
    },
    "celery": {
      "status": "ok",
      "response_time_ms": 1,
      "pending_tasks": 0
    }
  }
}
```

**Checks Performed:**
1. **Database** - SELECT 1 query
2. **Redis** - PING and SET operation
3. **Celery** - Task queue inspection

**Use Case:**
```yaml
# Kubernetes Pod Configuration
readinessProbe:
  httpGet:
    path: /api/health/ready/
    port: 8000
    scheme: HTTP
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  successThreshold: 1
  failureThreshold: 3
```

**Behavior:**
- Checks all critical dependencies
- Returns 200 only if ALL checks pass
- Returns 503 if ANY check fails
- Use for traffic routing decisions
- Kubernetes will not send traffic until this returns 200

---

### 3. Detailed Health Endpoint

**Path:** `GET /api/health/detailed/`

**Purpose:** Full system diagnostics and metrics

**Authentication:** Not required (AllowAny)

**Response Time:** 100-300ms (typical)

**HTTP Status Codes:**
- `200 OK` - Always returns 200 (diagnostic endpoint)

**Response Format:**
```json
{
  "status": "healthy",
  "timestamp": "2025-12-27T10:00:00Z",
  "checks": {
    "database": {
      "status": "ok",
      "response_time_ms": 5
    },
    "redis": {
      "status": "ok",
      "response_time_ms": 2
    },
    "celery": {
      "status": "ok",
      "response_time_ms": 1,
      "pending_tasks": 10
    },
    "cpu": {
      "status": "ok",
      "percent": 25.5,
      "count": 4
    },
    "memory": {
      "status": "ok",
      "percent": 60.2,
      "available_mb": 2048,
      "total_mb": 8192
    },
    "disk": {
      "status": "ok",
      "percent": 45.8,
      "free_mb": 50000,
      "total_mb": 100000
    },
    "connections": {
      "status": "ok",
      "active_connections": 42
    }
  }
}
```

**Status Values:**
- `healthy` - All checks OK, no warnings
- `degraded` - Some warnings but functional
- `unhealthy` - Critical issues detected

**Warning Thresholds:**
- CPU: > 90% = warning
- Memory: > 85% = warning
- Disk: > 80% = warning

**Use Case:**
```bash
# Manual health check
curl http://localhost:8000/api/health/detailed/

# Monitor in admin dashboard
# Navigate to: /admin/monitoring/

# Prometheus scraping
# Endpoint: /api/health/detailed/
```

---

## Implementation Details

### Architecture

```
core/
├── health.py              # HealthChecker class
├── views.py              # API endpoint views
├── urls.py               # URL routing
└── tests/
    ├── test_health_checks.py         # Full integration tests
    └── test_health_checks_simple.py  # Unit tests
```

### HealthChecker Class

**File:** `backend/core/health.py`

**Key Methods:**
```python
class HealthChecker:
    def check_liveness(self) -> bool
    def check_database(self) -> Tuple[str, int]
    def check_redis(self) -> Tuple[str, int]
    def check_celery(self) -> Tuple[str, int, int]

    def get_cpu_metrics(self) -> Dict[str, Any]
    def get_memory_metrics(self) -> Dict[str, Any]
    def get_disk_metrics(self) -> Dict[str, Any]
    def get_connections_metrics(self) -> Dict[str, Any]

    def get_liveness_response(self) -> Dict[str, Any]
    def get_readiness_response(self) -> Tuple[Dict[str, Any], int]
    def get_detailed_response(self) -> Dict[str, Any]
```

### Dependencies

All dependencies are already installed:
- `django` - Web framework
- `djangorestframework` - REST API
- `psutil` - System metrics
- `redis` - Redis cache
- `celery` - Task queue

---

## Kubernetes Configuration

### Pod Spec Example

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: thebot-backend
spec:
  containers:
  - name: backend
    image: thebot:latest
    ports:
    - containerPort: 8000

    # Liveness Probe - Restart if dead
    livenessProbe:
      httpGet:
        path: /api/health/live/
        port: 8000
        scheme: HTTP
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3

    # Readiness Probe - Remove from load balancer if not ready
    readinessProbe:
      httpGet:
        path: /api/health/ready/
        port: 8000
        scheme: HTTP
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
      successThreshold: 1
      failureThreshold: 3
```

### Deployment with Health Checks

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: thebot-backend
  labels:
    app: thebot-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: thebot-backend
  template:
    metadata:
      labels:
        app: thebot-backend
    spec:
      containers:
      - name: backend
        image: thebot:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /api/health/live/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health/ready/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

---

## Testing

### Unit Tests

```bash
# Run all health check tests
cd backend
ENVIRONMENT=test python -m pytest tests/unit/core/test_health_checks_simple.py -v

# Run specific test class
ENVIRONMENT=test python -m pytest tests/unit/core/test_health_checks_simple.py::TestHealthCheckerBasics -v

# Run with coverage
ENVIRONMENT=test python -m pytest tests/unit/core/test_health_checks_simple.py --cov=core.health
```

### Manual Testing

```bash
# Start backend
cd backend
python manage.py runserver

# In another terminal, test endpoints
python tests/manual_health_check_test.py
```

### Curl Examples

```bash
# Liveness check
curl -i http://localhost:8000/api/health/live/

# Readiness check
curl -i http://localhost:8000/api/health/ready/

# Detailed health check
curl -i http://localhost:8000/api/health/detailed/

# With pretty JSON output
curl http://localhost:8000/api/health/detailed/ | python -m json.tool
```

---

## Performance Characteristics

| Endpoint | Response Time | Heavy Operations |
|----------|---------------|------------------|
| Liveness | <100ms | None |
| Readiness | 50-200ms | DB query, Redis ping, Celery inspect |
| Detailed | 100-300ms | All readiness checks + psutil metrics |

**Recommended Probe Intervals:**
- Liveness: 10-30 seconds
- Readiness: 5-10 seconds
- Detailed: 30-60 seconds (manual/monitoring only)

---

## Troubleshooting

### Readiness Always Returns 503

**Cause:** One or more critical dependencies is down

**Solution:**
1. Check database connectivity
2. Check Redis connectivity
3. Check Celery worker status
4. Review detailed endpoint response for specific failures

```bash
curl http://localhost:8000/api/health/detailed/ | python -m json.tool
```

### High Response Times

**Cause:** Slow database/Redis/Celery responses

**Solution:**
1. Check database performance (indexes, query plans)
2. Check Redis memory usage
3. Monitor Celery task queue backlog
4. Review system metrics (CPU, memory, disk)

### Pod Keeps Restarting

**Cause:** Liveness probe failing

**Solution:**
1. Increase initialDelaySeconds (pods need time to start)
2. Check application logs
3. Verify all dependencies are running
4. Check resource limits (memory, CPU)

---

## Monitoring

### Prometheus Integration

```yaml
# Prometheus scrape config
scrape_configs:
  - job_name: 'thebot-backend'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/health/detailed/'
```

### Grafana Dashboard

Create dashboard with:
1. Liveness probe success rate
2. Readiness probe success rate
3. Response time trends
4. CPU/Memory/Disk usage over time
5. Database/Redis/Celery check status

### Alerting Rules

```yaml
# AlertManager rules
groups:
  - name: thebot-health
    rules:
      - alert: ReadinessProbeFailure
        expr: |
          increase(http_requests_total{endpoint="/api/health/ready/", status="503"}[5m]) > 0
        for: 2m
        annotations:
          summary: "Backend not ready"

      - alert: HighCPUUsage
        expr: |
          http_request_duration_seconds_bucket{endpoint="/api/health/detailed/",
          le="+Inf"} > 0.5
        for: 5m
        annotations:
          summary: "High CPU usage detected"
```

---

## Best Practices

1. **Liveness Probes**
   - Set high failureThreshold (3-5)
   - Use longer periodSeconds (10-30)
   - High initialDelaySeconds for slow startups

2. **Readiness Probes**
   - Stricter thresholds (1-2 failures)
   - Shorter periodSeconds (5-10)
   - Lower initialDelaySeconds (5-10)

3. **Monitoring**
   - Always monitor health endpoints
   - Set up alerts for failures
   - Track response time trends

4. **Resource Allocation**
   - Ensure adequate CPU for database queries
   - Monitor memory for metrics collection
   - Track disk space (diagnostic data)

---

## Migration Guide

### From Old Health Check

Old endpoint: `GET /api/health-check/`
New endpoints:
- Use `/api/health/live/` for liveness
- Use `/api/health/ready/` for readiness
- Use `/api/health/detailed/` for diagnostics

Old endpoint still available for backward compatibility.

---

## Testing Status

✅ 31 unit tests - All passing
✅ Liveness endpoint - 200 OK
✅ Readiness endpoint - 200/503 based on dependencies
✅ Detailed health endpoint - 200 OK with full metrics
✅ Performance - <300ms response time
✅ Error handling - Graceful degradation

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-12-27 | Initial implementation |
| - | - | Kubernetes-ready health checks |
| - | - | Liveness, readiness, detailed endpoints |
| - | - | System metrics (CPU, memory, disk) |
| - | - | Dependency checks (DB, Redis, Celery) |
| - | - | 31 unit tests |

---

## Support

For issues or questions about health checks:
1. Review detailed endpoint response: `/api/health/detailed/`
2. Check application logs
3. Review database/Redis/Celery logs
4. Check system resources (CPU, memory, disk)

---

## Related Documentation

- [Kubernetes Documentation](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)
- [THE_BOT Platform Documentation](./CLAUDE.md)
- [API Documentation](./docs/API_ENDPOINTS.md)
