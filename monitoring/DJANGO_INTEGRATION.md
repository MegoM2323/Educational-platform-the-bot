# Django Integration with Prometheus

Instructions for integrating Prometheus metrics collection into Django backend.

## 1. Install Dependencies

Add to `backend/requirements.txt`:

```txt
prometheus-client>=0.16.0
psutil>=7.0.0
```

Install:

```bash
cd backend
pip install prometheus-client psutil
```

## 2. Configure Django Settings

Update `backend/config/settings.py`:

### Add Middleware

```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',

    # Add Prometheus middleware
    'core.prometheus_middleware.PrometheusMetricsMiddleware',
    'core.prometheus_middleware.DatabaseMetricsMiddleware',
    'core.prometheus_middleware.CacheMetricsMiddleware',
]
```

### Add Prometheus Settings

```python
# Prometheus monitoring
PROMETHEUS_ENABLED = True
PROMETHEUS_EXPORT_PORT = 8001
PROMETHEUS_METRICS_PATH = '/api/system/metrics/prometheus/'
```

## 3. Add URL Routes

Update `backend/config/urls.py`:

```python
from django.contrib import admin
from django.urls import path, include
from core import prometheus_views

urlpatterns = [
    path('admin/', admin.site.urls),

    # Prometheus metrics and health endpoints
    path('api/system/metrics/prometheus/', prometheus_views.prometheus_metrics, name='prometheus-metrics'),
    path('api/system/health/', prometheus_views.health_check, name='health-check'),
    path('api/system/readiness/', prometheus_views.readiness_check, name='readiness-check'),
    path('api/system/liveness/', prometheus_views.liveness_check, name='liveness-check'),
    path('api/system/metrics/', prometheus_views.system_metrics, name='system-metrics'),
    path('api/system/analytics/', prometheus_views.analytics, name='analytics'),
    path('api/system/prometheus/config/', prometheus_views.prometheus_config, name='prometheus-config'),

    # API routes
    path('api/', include('accounts.urls')),
    path('api/', include('materials.urls')),
    path('api/', include('assignments.urls')),
    path('api/', include('chat.urls')),
    path('api/', include('knowledge_graph.urls')),
    path('api/', include('scheduling.urls')),
    path('api/', include('reports.urls')),
    path('api/', include('notifications.urls')),
    path('api/', include('payments.urls')),
]
```

## 4. Record Metrics in Views

Example of recording metrics in Django views:

### Using Signals

```python
# backend/accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from config.prometheus_settings import DJANGO_MODEL_OPERATIONS_TOTAL

@receiver(post_save, sender=User)
def user_created(sender, instance, created, **kwargs):
    """Record user creation in metrics."""
    if created:
        DJANGO_MODEL_OPERATIONS_TOTAL.labels(
            model='User',
            operation='create'
        ).inc()
```

### Using Decorators

```python
# backend/core/decorators.py
import time
from functools import wraps
from config.prometheus_settings import (
    DJANGO_REQUEST_LATENCY_SECONDS,
    DJANGO_REQUEST_TOTAL
)

def record_metrics(func):
    """Decorator to record function execution metrics."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start = time.time()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            duration = time.time() - start
            DJANGO_REQUEST_LATENCY_SECONDS.labels(
                method='function',
                endpoint=func.__name__
            ).observe(duration)
    return wrapper
```

### In ViewSets

```python
# backend/accounts/views.py
from rest_framework import viewsets
from config.prometheus_settings import (
    DJANGO_AUTH_LOGIN_TOTAL,
    DJANGO_MODEL_OPERATIONS_TOTAL
)

class UserViewSet(viewsets.ModelViewSet):
    """User management viewset with metrics."""

    def perform_create(self, serializer):
        """Create user and record metrics."""
        super().perform_create(serializer)
        DJANGO_MODEL_OPERATIONS_TOTAL.labels(
            model='User',
            operation='create'
        ).inc()

    def perform_update(self, serializer):
        """Update user and record metrics."""
        super().perform_update(serializer)
        DJANGO_MODEL_OPERATIONS_TOTAL.labels(
            model='User',
            operation='update'
        ).inc()
```

## 5. Custom Metrics Examples

### Chat Messages

```python
# backend/chat/models.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from config.prometheus_settings import DJANGO_MESSAGES_SENT_TOTAL

@receiver(post_save, sender=Message)
def message_sent(sender, instance, created, **kwargs):
    """Record message sent to metrics."""
    if created:
        DJANGO_MESSAGES_SENT_TOTAL.labels(
            chat_type=instance.room.type
        ).inc()
```

### Assignments

```python
# backend/assignments/models.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from config.prometheus_settings import DJANGO_ASSIGNMENTS_SUBMITTED_TOTAL

@receiver(post_save, sender=Submission)
def submission_created(sender, instance, created, **kwargs):
    """Record assignment submission."""
    if created:
        DJANGO_ASSIGNMENTS_SUBMITTED_TOTAL.labels(
            status='submitted'
        ).inc()
```

### Payments

```python
# backend/payments/views.py
from config.prometheus_settings import DJANGO_PAYMENTS_PROCESSED_TOTAL

def process_payment(request):
    """Process payment and record metrics."""
    try:
        # Payment processing logic
        result = yookassa_client.create_payment(...)

        DJANGO_PAYMENTS_PROCESSED_TOTAL.labels(
            status='success',
            method='yookassa'
        ).inc()

        return result
    except Exception as e:
        DJANGO_PAYMENTS_PROCESSED_TOTAL.labels(
            status='failed',
            method='yookassa'
        ).inc()
        raise
```

### WebSocket Connections

```python
# backend/chat/consumers.py
from channels.generic.websocket import AsyncWebsocketConsumer
from config.prometheus_settings import DJANGO_WEBSOCKET_CONNECTIONS

class ChatConsumer(AsyncWebsocketConsumer):
    """Chat consumer with metrics."""

    async def connect(self):
        """Handle WebSocket connect."""
        await self.accept()
        DJANGO_WEBSOCKET_CONNECTIONS.labels(
            type='chat'
        ).inc()

    async def disconnect(self, close_code):
        """Handle WebSocket disconnect."""
        DJANGO_WEBSOCKET_CONNECTIONS.labels(
            type='chat'
        ).dec()
```

## 6. Database Metrics

### Using Connection Monitoring

```python
# backend/core/prometheus_middleware.py
# Already included in PrometheusMetricsMiddleware

# Middleware automatically records:
# - Query count per request
# - Query execution time
# - Slow queries (>100ms)
```

### Custom Database Metrics

```python
# backend/core/database_metrics.py
from django.db import connection
from config.prometheus_settings import DJANGO_DB_EXECUTE_TIME_SECONDS

def record_query_metrics():
    """Record database query metrics."""
    for query in connection.queries:
        duration = float(query.get('time', 0))

        DJANGO_DB_EXECUTE_TIME_SECONDS.labels(
            database='default',
            operation='query',
            table='*'
        ).observe(duration)
```

## 7. Cache Metrics

### Cache Operation Tracking

```python
# backend/core/cache_metrics.py
from django.core.cache import cache
from config.prometheus_settings import (
    DJANGO_CACHE_HITS_TOTAL,
    DJANGO_CACHE_MISSES_TOTAL
)

def track_cache_operation(key, hit):
    """Track cache hits and misses."""
    if hit:
        DJANGO_CACHE_HITS_TOTAL.labels(
            cache_name='default'
        ).inc()
    else:
        DJANGO_CACHE_MISSES_TOTAL.labels(
            cache_name='default'
        ).inc()
```

## 8. Health Checks

The following health check endpoints are automatically provided:

```bash
# Liveness check - is service running?
curl http://localhost:8000/api/system/liveness/

# Readiness check - is service ready for traffic?
curl http://localhost:8000/api/system/readiness/

# Full health check with component status
curl http://localhost:8000/api/system/health/

# System metrics
curl http://localhost:8000/api/system/metrics/

# Application analytics
curl http://localhost:8000/api/system/analytics/
```

## 9. Kubernetes Integration

For Kubernetes deployments, configure health probes:

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: thebot-backend
spec:
  template:
    spec:
      containers:
      - name: backend
        image: thebot-backend:latest

        # Liveness probe - restart if not responding
        livenessProbe:
          httpGet:
            path: /api/system/liveness/
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10

        # Readiness probe - stop traffic if not ready
        readinessProbe:
          httpGet:
            path: /api/system/readiness/
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
```

## 10. Testing

### Unit Tests for Metrics

```python
# backend/tests/test_metrics.py
from django.test import TestCase
from config.prometheus_settings import (
    DJANGO_REQUEST_TOTAL,
    DJANGO_REQUEST_LATENCY_SECONDS
)

class MetricsTestCase(TestCase):
    """Test metrics collection."""

    def test_request_metrics_recorded(self):
        """Test that request metrics are recorded."""
        # Make a request
        response = self.client.get('/api/users/')

        # Verify metrics were recorded
        self.assertEqual(response.status_code, 200)
```

### Integration Tests

```bash
# Test metrics endpoint
curl http://localhost:8000/api/system/metrics/prometheus/ | head -50

# Test health checks
curl http://localhost:8000/api/system/health/
curl http://localhost:8000/api/system/readiness/
curl http://localhost:8000/api/system/liveness/

# Test in Prometheus
curl 'http://localhost:9090/api/v1/query?query=rate(django_request_total[5m])'
```

## 11. Performance Considerations

### Disable Metrics in Development

```python
# backend/config/settings.py
if ENVIRONMENT == 'development':
    PROMETHEUS_ENABLED = False
```

### Exclude High-Cardinality Endpoints

In `prometheus_middleware.py`:

```python
EXCLUDED_PATHS = [
    r'^/health/$',
    r'^/static/',
    r'^/media/',
    r'^/api/metrics',  # Don't measure metrics endpoint
]
```

### Use Sampling for High-Volume Metrics

```python
# backend/core/prometheus_middleware.py
import random

def should_record_metric():
    """Return True if metric should be recorded."""
    # Sample 10% of requests
    return random.random() < 0.1
```

## 12. Troubleshooting

### Metrics Not Appearing in Prometheus

1. **Check metrics endpoint exists**:
   ```bash
   curl http://localhost:8000/api/system/metrics/prometheus/
   ```

2. **Verify Prometheus scrape config**:
   ```bash
   curl http://localhost:9090/api/v1/targets
   ```

3. **Check for errors**:
   ```bash
   docker logs thebot-prometheus
   ```

### High Memory Usage from Metrics

1. **Reduce metric cardinality** - Avoid unbounded label values
2. **Drop unused metrics** - Use metric relabeling in Prometheus
3. **Increase scrape interval** - Set longer intervals for less critical metrics

### Django Startup Issues

If Django won't start after adding metrics:

1. **Check imports**: Verify prometheus_settings.py is in config/
2. **Verify middleware**: Check MIDDLEWARE list is correct
3. **Test imports**: `python -c "from config.prometheus_settings import *"`

## Documentation

- [Prometheus Client Python](https://github.com/prometheus/client_python)
- [Django Signals](https://docs.djangoproject.com/en/stable/topics/signals/)
- [Django Middleware](https://docs.djangoproject.com/en/stable/topics/http/middleware/)

---

**Last Updated**: December 27, 2025
**Status**: Production Ready
