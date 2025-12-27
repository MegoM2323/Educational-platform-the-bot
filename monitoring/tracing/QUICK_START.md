# Distributed Tracing Quick Start Guide

Get distributed tracing running in minutes.

## TL;DR - 5 Minute Setup

### 1. Install Dependencies

```bash
cd backend
pip install opentelemetry-api opentelemetry-sdk \
    opentelemetry-exporter-jaeger opentelemetry-exporter-prometheus \
    opentelemetry-instrumentation-django \
    opentelemetry-instrumentation-requests \
    opentelemetry-instrumentation-psycopg2 \
    opentelemetry-instrumentation-redis \
    opentelemetry-instrumentation-celery \
    opentelemetry-propagator-jaeger
```

### 2. Update Django Settings

In `backend/config/settings.py`, add to MIDDLEWARE list:

```python
MIDDLEWARE = [
    'config.middleware.correlation_id_middleware.CorrelationIDMiddleware',
    # ... rest of middleware
]

# Near the bottom of settings.py, add:
# Initialize tracing
try:
    from config.tracing import init_tracing, setup_metrics
    if ENVIRONMENT != 'test':
        init_tracing()
        setup_metrics()
except ImportError:
    pass
```

### 3. Start Services

```bash
# From project root
docker-compose -f docker-compose.yml -f docker-compose.tracing.yml up -d

# Verify
docker-compose -f docker-compose.tracing.yml logs -f otel-collector
```

### 4. Generate Traces

```bash
# Start Django
cd backend
python manage.py runserver

# Make requests (in another terminal)
curl http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "student@test.com", "password": "TestPass123!"}'
```

### 5. View Traces

Open browser: **http://localhost:16686**

- Service: "thebot-platform"
- Search for recent traces
- Click on any trace to view details

## Common Tasks

### View All Traces

1. Go to http://localhost:16686
2. Select service "thebot-platform"
3. Click "Find Traces"

### Search by Operation

1. In Jaeger UI, use dropdown: "Operation Name"
2. Select operation like "POST /api/auth/login"
3. Click "Find Traces"

### Search by Tag

```
# Example searches in Jaeger UI
http.status_code = 200
error = true
user.id = 5
```

### View Trace Details

1. Click any trace in results
2. See timeline of all operations
3. Click any span to view:
   - Span name
   - Start time and duration
   - All attributes
   - Events
   - Logs

### Monitor Collector Health

```bash
# Check collector status
curl http://localhost:13133/healthz

# View collector metrics
curl http://localhost:8889/metrics | grep otel

# Key metrics:
# - otelcol_receiver_accepted_spans_total
# - otelcol_exporter_sent_spans_total
# - otelcol_exporter_queue_size
```

## Custom Instrumentation

### Create a Span in Views

```python
from config.tracing import get_tracer, set_correlation_id
import uuid

tracer = get_tracer(__name__)

def my_view(request):
    # Set correlation ID
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)

    # Create custom span
    with tracer.start_as_current_span("process_payment") as span:
        # Add attributes
        span.set_attribute("user.id", request.user.id)
        span.set_attribute("amount", 100.0)

        # Add event
        span.add_event("processing_started")

        # Your logic
        result = process_payment(request.user.id, 100.0)

        # Record result
        span.set_attribute("success", True)

        return Response({"status": "ok"})
```

### Trace a Function

```python
from config.tracing import get_tracer

tracer = get_tracer(__name__)

@tracer.start_as_current_span("calculate_report")
def calculate_report(user_id):
    """Function automatically traced."""
    # Span created automatically with function name
    # Execution time recorded automatically
    return expensive_calculation(user_id)
```

### Manual Span Creation

```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("my_operation") as span:
    span.set_attribute("key", "value")
    span.add_event("something happened")
    # Do work
    pass
```

## Troubleshooting

### No Traces Showing

Check Jaeger is running:
```bash
docker-compose -f docker-compose.tracing.yml ps

# Should see: jaeger, otel-collector, elasticsearch all healthy
```

Check collector is receiving traces:
```bash
docker-compose -f docker-compose.tracing.yml logs otel-collector | head -20
# Should see: "Received 1 spans"
```

### High Memory Usage

Reduce sampling rate:
```bash
export TRACING_SAMPLE_PERCENTAGE=5
docker-compose -f docker-compose.tracing.yml restart
```

### Elasticsearch Errors

Check disk space:
```bash
docker exec thebot-elasticsearch df -h /usr/share/elasticsearch/data
```

Restart Elasticsearch:
```bash
docker-compose -f docker-compose.tracing.yml restart elasticsearch
```

## Docker Compose Commands

```bash
# Start
docker-compose -f docker-compose.yml -f docker-compose.tracing.yml up -d

# Stop
docker-compose -f docker-compose.yml -f docker-compose.tracing.yml down

# View logs
docker-compose -f docker-compose.yml -f docker-compose.tracing.yml logs -f

# Restart specific service
docker-compose -f docker-compose.tracing.yml restart jaeger

# Clean everything (WARNING: deletes all traces)
docker-compose -f docker-compose.tracing.yml down -v
```

## Environment Variables

```bash
# Sampling rate (0-100)
TRACING_SAMPLE_PERCENTAGE=10  # Default 10%

# Jaeger endpoint
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
JAEGER_COLLECTOR_ENDPOINT=http://localhost:14250

# OTEL Collector
OTEL_EXPORTER_OTLP_ENDPOINT=localhost:4317

# Environment
ENVIRONMENT=development  # development, staging, production
```

## Access Points Summary

| Service | URL | Purpose |
|---------|-----|---------|
| **Jaeger UI** | http://localhost:16686 | View traces |
| **Jaeger API** | http://localhost:14268 | Query traces |
| **Collector Health** | http://localhost:13133/healthz | Collector status |
| **Collector Metrics** | http://localhost:8889/metrics | OTEL metrics |
| **Elasticsearch** | http://localhost:9200 | Trace storage |
| **Prometheus** | http://localhost:9091 | Collector metrics (Prometheus) |

## Key Sampling Rates

- POST /api/auth/login: 100%
- POST /api/payments/*: 100%
- POST /api/chat/messages: 50%
- GET /api/materials: 10%
- Errors: 100% (always sampled)
- Others: Based on environment

## Next Steps

1. Read [SETUP_AND_INTEGRATION.md](SETUP_AND_INTEGRATION.md) for detailed setup
2. Check [JAEGER_QUERIES.md](JAEGER_QUERIES.md) for advanced queries
3. Review examples in `backend/config/tracing.py`
4. Add custom instrumentation to your code
5. Configure alerts in `tracing_rules.yml`

## Support

For issues, check logs:

```bash
# Collector logs
docker-compose -f docker-compose.tracing.yml logs otel-collector

# Jaeger logs
docker-compose -f docker-compose.tracing.yml logs jaeger

# Elasticsearch logs
docker-compose -f docker-compose.tracing.yml logs elasticsearch

# View last 50 lines
docker-compose -f docker-compose.tracing.yml logs --tail=50
```
