# Distributed Tracing Setup with OpenTelemetry and Jaeger

Complete guide to setting up and integrating distributed tracing in THE_BOT Platform using OpenTelemetry and Jaeger.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Requirements](#requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [Django Integration](#django-integration)
7. [Usage](#usage)
8. [Access Points](#access-points)
9. [Sampling Strategy](#sampling-strategy)
10. [Troubleshooting](#troubleshooting)
11. [Best Practices](#best-practices)

## Overview

This setup provides comprehensive distributed tracing across the entire THE_BOT Platform:

- **OpenTelemetry Collector**: Receives traces from applications
- **Jaeger Backend**: Stores traces in Elasticsearch and provides query UI
- **Custom Instrumentation**: Django, database, cache, Celery, external services
- **Correlation ID Propagation**: Track requests across services
- **Environment-Based Sampling**: Different rates per environment

### Key Features

- Automatic Django instrumentation
- Database query tracing (psycopg2)
- Redis cache tracing
- Celery task tracing
- HTTP request tracing (outgoing)
- WebSocket connection tracking
- Custom span creation support
- Error and exception tracking
- Performance bottleneck identification

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    THE_BOT Applications                      │
│  (Django, Celery, WebSocket handlers)                        │
└──────────────┬──────────────────────────────────────────────┘
               │
               │ OTLP gRPC (port 4317)
               │
┌──────────────▼──────────────────────────────────────────────┐
│          OpenTelemetry Collector (OTEL)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐         │
│  │ OTLP        │  │ Prometheus  │  │ Logging      │         │
│  │ Receiver    │  │ Receiver    │  │ Exporter     │         │
│  └─────┬───────┘  └─────┬───────┘  └──────┬───────┘         │
│        │                │                 │                  │
│        └────────────────┼─────────────────┘                  │
│                         │                                    │
│  Processing:           Batch, Sampling, Resource            │
│                                                              │
│        ┌────────────────┼─────────────────┐                 │
│        │                │                 │                 │
│  ┌─────▼──────┐  ┌─────▼──────┐  ┌──────▼──────┐           │
│  │ Jaeger     │  │ Prometheus │  │ Logging     │           │
│  │ Exporter   │  │ Exporter   │  │ Output      │           │
│  └─────┬──────┘  └─────┬──────┘  └─────────────┘           │
└────────┼───────────────┼─────────────────────────────────────┘
         │               │
         │ gRPC (port    │ Metrics (port 8889)
         │ 14250)        │
         │               │
    ┌────▼──────────┬────▼──────────┐
    │               │               │
┌───▼────┐    ┌────▼─────┐    ┌──────────┐
│ Jaeger │    │Prometheus │    │ Grafana  │
│Backend │    │ Tracing   │    │(optional)│
└────┬───┘    └───────────┘    └──────────┘
     │
┌────▼──────────────────┐
│  Elasticsearch        │
│  (Trace Storage)      │
└───────────────────────┘
     │
     │ Jaeger UI
     └──► http://localhost:16686
```

## Requirements

### Python Packages

```bash
# Core OpenTelemetry packages
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0

# Exporters
opentelemetry-exporter-jaeger>=1.20.0
opentelemetry-exporter-otlp>=0.41b0

# Instrumentation
opentelemetry-instrumentation>=0.41b0
opentelemetry-instrumentation-django>=0.41b0
opentelemetry-instrumentation-requests>=0.41b0
opentelemetry-instrumentation-psycopg2>=0.41b0
opentelemetry-instrumentation-redis>=0.41b0
opentelemetry-instrumentation-celery>=0.41b0
opentelemetry-instrumentation-httpx>=0.41b0
opentelemetry-instrumentation-wsgi>=0.41b0

# Propagators
opentelemetry-propagator-jaeger>=1.20.0
opentelemetry-propagator-b3>=1.20.0

# Prometheus exporter for metrics
opentelemetry-exporter-prometheus>=0.41b0
```

### Docker Services

- OpenTelemetry Collector (version 0.97.0+)
- Jaeger (version 1.50.0+)
- Elasticsearch (version 8.x+, for trace storage)
- Prometheus (optional, for collector metrics)

### System Requirements

- RAM: 2GB minimum (4GB recommended)
  - Elasticsearch: 512MB
  - Jaeger: 512MB
  - Collector: 256MB
  - Prometheus: 256MB

- Disk: 10GB for 7-day trace retention

## Installation

### Step 1: Install Python Dependencies

```bash
cd /path/to/backend

# Add to requirements.txt
cat >> requirements.txt << 'EOF'
# OpenTelemetry - Distributed Tracing
opentelemetry-api>=1.20.0
opentelemetry-sdk>=1.20.0
opentelemetry-exporter-jaeger>=1.20.0
opentelemetry-exporter-otlp>=0.41b0
opentelemetry-exporter-prometheus>=0.41b0
opentelemetry-instrumentation>=0.41b0
opentelemetry-instrumentation-django>=0.41b0
opentelemetry-instrumentation-requests>=0.41b0
opentelemetry-instrumentation-psycopg2>=0.41b0
opentelemetry-instrumentation-redis>=0.41b0
opentelemetry-instrumentation-celery>=0.41b0
opentelemetry-instrumentation-httpx>=0.41b0
opentelemetry-instrumentation-wsgi>=0.41b0
opentelemetry-propagator-jaeger>=1.20.0
opentelemetry-propagator-b3>=1.20.0
EOF

# Install packages
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Add to `.env` file:

```bash
# Tracing Configuration
TRACING_ENABLED=True
TRACING_SAMPLE_PERCENTAGE=10  # 10% for production, 100% for development

# Jaeger Configuration
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
JAEGER_COLLECTOR_ENDPOINT=http://localhost:14250

# OTLP Configuration (if using collector)
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317

# Environment
ENVIRONMENT=development  # development, staging, production
```

### Step 3: Start Tracing Stack

```bash
# From project root
docker-compose -f docker-compose.yml -f docker-compose.tracing.yml up -d

# Verify services are running
docker-compose -f docker-compose.yml -f docker-compose.tracing.yml ps

# Check collector health
curl http://localhost:13133/healthz

# Check Jaeger health
curl http://localhost:16686/health
```

### Step 4: Initialize Django Integration

Add to `backend/config/settings.py`:

```python
# At the top of settings file, after imports
from config.tracing import init_tracing, setup_metrics

# Initialize tracing during Django startup
if not DEBUG or ENVIRONMENT == 'test':
    OTEL_TRACER = init_tracing(
        enabled=True,
        service_name="thebot-platform",
        jaeger_enabled=True,
        sample_rate=None,  # Uses environment-based rate
    )

    # Initialize metrics collection
    OTEL_METER = setup_metrics()
```

Or use lazy initialization in Django signals:

```python
# In config/apps.py
from django.apps import AppConfig
from config.tracing import init_tracing, setup_metrics

class ConfigAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'config'

    def ready(self):
        """Initialize tracing when Django is ready."""
        # Avoid running during management commands
        import sys
        if 'migrate' not in sys.argv and 'createsuperuser' not in sys.argv:
            try:
                init_tracing()
                setup_metrics()
            except Exception as e:
                import logging
                logging.error(f"Failed to initialize tracing: {e}")
```

## Configuration

### Sampling Configuration

Sampling rates are automatically set based on environment:

```
Development:  100% (sample all requests)
Staging:       50% (sample half of requests)
Production:    10% (sample 10% of requests)
```

To override, set `TRACING_SAMPLE_PERCENTAGE` in environment:

```bash
# 50% sampling
export TRACING_SAMPLE_PERCENTAGE=50

# 100% sampling (not recommended for production)
export TRACING_SAMPLE_PERCENTAGE=100
```

**Critical paths are always sampled (100%)**:
- POST /api/auth/login
- POST /api/auth/logout
- POST /api/payments/webhook
- POST /api/chat/rooms
- GET /admin/*

### Span Processors

The setup includes:

1. **BatchSpanProcessor**: Batches spans before export
   - Batch size: 512 spans
   - Timeout: 5 seconds
   - Max queue: 2048 spans

2. **Memory Limiter**: Prevents OOM
   - Limit: 512MB
   - Spike threshold: 128MB

3. **Custom Sampler**: Environment-based with error tracking
   - Always samples errors
   - Always samples critical paths
   - Respects operation-specific rates

### Storage Configuration

Jaeger uses Elasticsearch for storage:

**Retention Policy**: 7 days
- Daily indices with date separator
- Automatic index cleanup after 7 days
- Configurable in docker-compose.tracing.yml

**Storage Limits**:
- No hard limit (configure in Elasticsearch if needed)
- Recommended: 10GB per day

## Django Integration

### Automatic Instrumentation

The following are automatically instrumented:

1. **HTTP Requests**
   - Request method, path, query parameters
   - Response status code
   - Request/response size
   - Execution time

2. **Database Queries**
   - Query text (parameterized)
   - Execution time
   - Database name
   - Operation type (SELECT, INSERT, UPDATE, DELETE)

3. **Redis Cache**
   - Operation (GET, SET, DEL)
   - Key name
   - Response time
   - Hit/miss tracking

4. **Celery Tasks**
   - Task name
   - Arguments (when safe)
   - Result (when available)
   - Execution time
   - Task status

5. **External HTTP Requests**
   - Outgoing requests via requests/httpx
   - URL, method, status code
   - Response time

### Custom Spans

Create custom spans for application logic:

```python
from config.tracing import get_tracer, set_correlation_id

tracer = get_tracer(__name__)

@tracer.start_as_current_span("process_payment")
def process_payment(user_id: int, amount: float):
    """Process payment for user."""
    span = trace.get_current_span()

    # Add custom attributes
    span.set_attribute("user.id", user_id)
    span.set_attribute("payment.amount", amount)
    span.set_attribute("payment.currency", "RUB")

    # Your payment logic
    result = payment_gateway.charge(user_id, amount)

    # Record event
    span.add_event("payment_processing_completed")

    return result

# In views
from opentelemetry import trace

def payment_view(request):
    # Set correlation ID for this request
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)

    # Process payment
    result = process_payment(request.user.id, request.data['amount'])

    return Response({"status": "success"})
```

### Correlation ID Propagation

Correlation IDs are automatically propagated across services:

```python
from config.tracing import set_correlation_id
import uuid

# In middleware or view
correlation_id = request.META.get('HTTP_X_CORRELATION_ID', str(uuid.uuid4()))
set_correlation_id(correlation_id)

# Send to external services
external_response = requests.get(
    "http://external-service/api/data",
    headers={'X-Correlation-ID': correlation_id}
)
```

The following headers propagate correlation IDs:

- `X-Trace-ID` (Jaeger)
- `X-Span-ID` (Jaeger)
- `X-B3-Trace-ID` (B3)
- `Baggage` (W3C)

## Usage

### Starting Traces

```bash
# Start services
cd /path/to/project
docker-compose -f docker-compose.yml -f docker-compose.tracing.yml up -d

# Check status
docker-compose -f docker-compose.yml -f docker-compose.tracing.yml logs -f otel-collector

# Start Django application
cd backend
python manage.py runserver
```

### Generating Traces

Perform any action in the application:

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "student@test.com", "password": "TestPass123!"}'

# Create chat
curl -X POST http://localhost:8000/api/chat/rooms/ \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Room", "type": "direct", "members": [2]}'

# Send message
curl -X POST http://localhost:8000/api/chat/messages/ \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{"room_id": 1, "content": "Hello, World!"}'
```

## Access Points

### Jaeger UI

- **URL**: http://localhost:16686
- **Services**: thebot-platform
- **Features**:
  - Trace search
  - Service map
  - Dependency graph
  - Trace detail view
  - Service comparison

### OpenTelemetry Collector

- **Health Check**: http://localhost:13133/healthz
- **Metrics Endpoint**: http://localhost:8889/metrics
- **zPages**: http://localhost:55679/debug

### Prometheus (Tracing)

- **URL**: http://localhost:9091
- **Scrapes**: OTEL Collector, Jaeger
- **Metrics**: tracing:spans_per_second, tracing:export_success_rate

### Elasticsearch

- **API**: http://localhost:9200
- **Index Prefix**: jaeger-*
- **Query example**:

```bash
# List indices
curl http://localhost:9200/_cat/indices/jaeger*

# Search traces by service
curl http://localhost:9200/jaeger-*/_search \
  -H "Content-Type: application/json" \
  -d '{"query": {"match": {"serviceName": "thebot-platform"}}}'
```

## Sampling Strategy

### Default Sampling Rates

| Operation | Sample Rate | Reason |
|-----------|-------------|--------|
| POST /api/auth/login | 100% | Authentication is critical |
| POST /api/auth/logout | 100% | Session management |
| POST /api/payments/* | 100% | Financial transactions |
| POST /api/payments/webhook | 100% | Payment webhooks |
| POST /api/chat/messages | 50% | High volume |
| POST /api/chat/rooms | 100% | Resource creation |
| GET /admin/* | 100% | Admin operations |
| Errors | 100% | All errors |
| Other | 10%-100% | Environment-dependent |

### Custom Sampling Rules

Override sampling in `jaeger-sampling-strategies.json`:

```json
{
  "service_strategies": [
    {
      "service": "thebot-platform",
      "operation_strategies": [
        {
          "operation": "GET /api/materials/*",
          "type": "probabilistic",
          "param": 0.05  // 5% sampling
        }
      ]
    }
  ]
}
```

Then restart Jaeger:

```bash
docker-compose -f docker-compose.tracing.yml restart jaeger
```

### Error Sampling

Errors are always sampled at 100% regardless of configuration. This ensures:
- All exceptions are traced
- Performance bottlenecks are visible
- Security issues are tracked

## Troubleshooting

### No Traces Appearing in Jaeger

1. Check collector is receiving traces:
   ```bash
   docker-compose logs otel-collector | grep "received"
   ```

2. Check Django instrumentation is enabled:
   ```bash
   python manage.py shell
   >>> from config.tracing import get_tracer
   >>> tracer = get_tracer()
   >>> tracer  # Should return valid tracer instance
   ```

3. Verify environment variables:
   ```bash
   docker-compose -f docker-compose.tracing.yml logs jaeger | head -20
   ```

### High Memory Usage

1. Reduce sampling rate:
   ```bash
   export TRACING_SAMPLE_PERCENTAGE=5
   docker-compose restart
   ```

2. Reduce batch size in `otel-config.yml`:
   ```yaml
   batch:
     send_batch_size: 256  # From 512
     timeout: 10s  # Increase timeout
   ```

3. Lower Elasticsearch memory:
   ```yaml
   environment:
     - "ES_JAVA_OPTS=-Xms256m -Xmx256m"  # From 512m
   ```

### Elasticsearch Connection Errors

1. Check Elasticsearch is running:
   ```bash
   docker-compose logs elasticsearch | tail -20
   ```

2. Check Jaeger can connect:
   ```bash
   docker exec thebot-jaeger curl -f http://elasticsearch:9200/_cluster/health
   ```

3. Check disk space:
   ```bash
   docker exec thebot-elasticsearch df -h /usr/share/elasticsearch/data
   ```

### Collector High Resource Usage

1. Check queue depth:
   ```bash
   curl http://localhost:8889/metrics | grep otel_exporter_queue
   ```

2. If queue is full, increase batch size and timeout:
   ```yaml
   batch:
     send_batch_size: 1024
     timeout: 10s
   ```

3. Check for network issues to Jaeger:
   ```bash
   docker exec thebot-otel-collector nc -zv jaeger 14250
   ```

## Best Practices

### 1. Correlation IDs

Always set correlation IDs for request tracing:

```python
import uuid

def correlation_id_middleware(request):
    correlation_id = request.META.get(
        'HTTP_X_CORRELATION_ID',
        str(uuid.uuid4())
    )
    request.correlation_id = correlation_id
    set_correlation_id(correlation_id)
```

### 2. Custom Span Attributes

Add business context to spans:

```python
span = trace.get_current_span()
span.set_attribute("user.id", user.id)
span.set_attribute("user.role", user.role)
span.set_attribute("organization.id", organization.id)
span.set_attribute("resource.id", resource.id)
span.set_attribute("resource.type", "document")
```

### 3. Span Events

Use events for important milestones:

```python
span.add_event("validation_started")
# ... validation logic ...
span.add_event("validation_completed", {"errors": 0})

span.add_event("database_query", {
    "table": "users",
    "count": result_count
})
```

### 4. Error Recording

Always record exceptions in spans:

```python
try:
    result = risky_operation()
except Exception as e:
    span.record_exception(e)
    span.set_attribute("error", True)
    raise
```

### 5. Sampling Consistency

Use same sampling strategy across all services for consistent traces.

### 6. Index Management

Clean up old indices to save storage:

```bash
# List old indices
curl http://localhost:9200/_cat/indices/jaeger*

# Delete indices older than 7 days manually
curl -X DELETE http://localhost:9200/jaeger-2024-01-01

# Or configure in Elasticsearch curator (advanced)
```

### 7. Performance Tuning

For high-traffic environments:

```yaml
# In otel-config.yml
batch:
  send_batch_size: 1024
  timeout: 10s
  send_batch_max_size: 4096

# In docker-compose.tracing.yml
elasticsearch:
  environment:
    - "ES_JAVA_OPTS=-Xms1g -Xmx1g"
```

### 8. Monitoring Tracing Infrastructure

Monitor the tracing system itself:

```bash
# Check OTEL collector metrics
curl http://localhost:8889/metrics

# Key metrics to watch:
# - otelcol_receiver_accepted_spans_total
# - otelcol_exporter_sent_spans_total
# - otelcol_exporter_queue_size
# - process_resident_memory_bytes
```

## Integration with Existing Monitoring

This tracing setup integrates with existing monitoring:

- **Prometheus** (port 8889): Collects OTEL collector metrics
- **Grafana** (port 3000): Visualize tracing metrics alongside other metrics
- **AlertManager**: Alerts for tracing system issues (rules in tracing_rules.yml)

## Security Considerations

### Development

- Credentials are logged (use test data only)
- Sampling rate: 100%
- Storage: SQLite or in-memory

### Staging

- Sensitive data redacted
- Sampling rate: 50%
- Storage: 7-day retention

### Production

- PII redacted from spans
- Sampling rate: 10% (adjust as needed)
- Secure Elasticsearch connection (TLS)
- Network isolation (VPN/private network)
- Access control for Jaeger UI

## Cleaning Up

To stop tracing stack:

```bash
# Stop services
docker-compose -f docker-compose.tracing.yml down

# Remove volumes (WARNING: deletes all traces)
docker-compose -f docker-compose.tracing.yml down -v

# Restart with fresh data
docker-compose -f docker-compose.tracing.yml up -d
```

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [Django Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/django/django.html)
- [OpenTelemetry Collector](https://opentelemetry.io/docs/collector/)
