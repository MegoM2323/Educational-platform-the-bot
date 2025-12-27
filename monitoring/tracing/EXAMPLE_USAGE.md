# Distributed Tracing - Example Usage Guide

Practical examples of how to use OpenTelemetry and Jaeger in THE_BOT Platform.

## Table of Contents

1. [Basic Tracing](#basic-tracing)
2. [Chat System Tracing](#chat-system-tracing)
3. [Payment Processing Tracing](#payment-processing-tracing)
4. [Background Task Tracing](#background-task-tracing)
5. [Error Tracking](#error-tracking)
6. [Performance Analysis](#performance-analysis)
7. [Advanced Queries](#advanced-queries)

## Basic Tracing

### Automatically Traced Operations

These are automatically traced without any code changes:

```python
# 1. HTTP Requests are automatically traced
def chat_list_view(request):
    # Span created: GET /api/chat/rooms/
    # Automatically includes:
    # - Request method, path, query params
    # - Response status
    # - Execution time
    # - User ID (if authenticated)
    return Response(ChatRoom.objects.all().values())

# 2. Database queries are automatically traced
rooms = ChatRoom.objects.filter(members=request.user)
# Creates span: SELECT * FROM chat_chatroom WHERE ...
# Includes: Query time, result count

# 3. Redis cache operations traced
cache.get('user_messages')
# Creates span: REDIS GET user_messages
# Includes: Hit/miss, retrieval time

# 4. Celery tasks traced
send_notification.delay(user_id=1)
# Creates span: send_notification
# Includes: Task ID, arguments, execution time
```

### Manual Span Creation

Create custom spans for application logic:

```python
from config.tracing import get_tracer
from opentelemetry import trace

tracer = get_tracer(__name__)

def process_order(order_id: int):
    """Example of manual span creation."""

    # Method 1: Decorator style
    with tracer.start_as_current_span("process_order") as span:
        span.set_attribute("order.id", order_id)

        # Validate order
        span.add_event("validation_started")
        order = validate_order(order_id)
        span.add_event("validation_completed", {"is_valid": True})

        # Process payment
        with tracer.start_as_current_span("process_payment") as payment_span:
            payment_span.set_attribute("amount", order.total)
            result = charge_payment(order)
            payment_span.set_attribute("transaction_id", result['id'])

        # Update inventory
        with tracer.start_as_current_span("update_inventory") as inv_span:
            update_stock(order.items)
            inv_span.set_attribute("items_updated", len(order.items))

        return result

# Method 2: Function decorator style
@tracer.start_as_current_span("send_email")
def send_confirmation_email(order_id: int):
    """Decorator automatically creates span with function name."""
    email = get_order_email(order_id)
    send_mail(email)
    # Span duration includes entire function execution

# Method 3: Manual tracer
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("complex_calculation") as span:
    result = calculate_something()
    span.set_attribute("result", result)
```

## Chat System Tracing

### Room Creation

```python
from config.tracing import get_tracer, set_correlation_id
from opentelemetry import trace

tracer = get_tracer(__name__)

def create_chat_room(request):
    """Create chat room with full tracing."""

    # Set correlation ID for this request
    correlation_id = request.headers.get(
        'X-Correlation-ID',
        str(uuid.uuid4())
    )
    set_correlation_id(correlation_id)

    # Get current span (auto-created by Django instrumentation)
    current_span = trace.get_current_span()

    # Create room
    with tracer.start_as_current_span("create_chat_room") as span:
        span.set_attribute("room.type", request.data['type'])
        span.set_attribute("room.name", request.data['name'])
        span.set_attribute("user.id", request.user.id)
        span.set_attribute("members_count", len(request.data.get('members', [])))

        # Database operation (automatically traced)
        span.add_event("creating_room")
        room = ChatRoom.objects.create(
            name=request.data['name'],
            type=request.data['type'],
            created_by=request.user
        )
        span.set_attribute("room.id", room.id)
        span.add_event("room_created")

        # Add members (separate span)
        with tracer.start_as_current_span("add_members") as members_span:
            members_span.set_attribute("count", len(request.data.get('members', [])))
            for member_id in request.data.get('members', []):
                room.members.add(member_id)
            members_span.add_event("members_added")

        # Send notifications (async, traced separately)
        span.add_event("queueing_notifications")
        notify_room_created.delay(room.id)

        return Response(ChatRoomSerializer(room).data)

# View received trace in Jaeger:
# POST /api/chat/rooms/
# └─ create_chat_room
#   ├─ SELECT ... FROM chat_chatroom (auto)
#   ├─ INSERT INTO chat_chatroom (auto)
#   ├─ add_members
#   │ └─ INSERT INTO chat_chatroom_members (auto)
#   └─ send_notification (async)
```

### Message Sending

```python
@tracer.start_as_current_span("send_message")
def send_message(request):
    """Send chat message with real-time tracing."""
    span = trace.get_current_span()

    # Record attributes
    span.set_attribute("room.id", request.data['room_id'])
    span.set_attribute("message.length", len(request.data['content']))
    span.set_attribute("user.id", request.user.id)

    # Validate access (traced automatically)
    span.add_event("validating_access")
    room = ChatRoom.objects.get(id=request.data['room_id'])
    if request.user not in room.members.all():
        span.set_attribute("error", True)
        raise PermissionDenied()

    # Create message
    span.add_event("creating_message")
    message = Message.objects.create(
        room=room,
        sender=request.user,
        content=request.data['content']
    )
    span.set_attribute("message.id", message.id)

    # WebSocket broadcast (traced via signals)
    with tracer.start_as_current_span("broadcast_message") as broadcast_span:
        broadcast_span.set_attribute("room_members", room.members.count())
        broadcast_message(room, message)
        broadcast_span.add_event("broadcast_sent")

    # Queue offline delivery
    with tracer.start_as_current_span("queue_offline_delivery") as queue_span:
        offline_count = queue_offline_messages(room, message)
        queue_span.set_attribute("offline_recipients", offline_count)

    return Response(MessageSerializer(message).data)

# Generated trace:
# POST /api/chat/messages/
# └─ send_message
#   ├─ SELECT from chat_chatroom (auto)
#   ├─ INSERT into messages (auto)
#   ├─ broadcast_message
#   │ └─ WebSocket sends (if instrumented)
#   └─ queue_offline_delivery
#     └─ INSERT into pending_messages (auto)
```

## Payment Processing Tracing

### Payment Webhook

```python
@tracer.start_as_current_span("process_payment_webhook")
@csrf_exempt
def yookassa_webhook(request):
    """Process payment webhook with full tracing."""
    span = trace.get_current_span()

    # Always sampled (100%) due to criticality
    # Set correlation ID
    correlation_id = request.headers.get(
        'X-Correlation-ID',
        str(uuid.uuid4())
    )
    set_correlation_id(correlation_id)

    span.set_attribute("webhook.source", "yookassa")
    span.set_attribute("correlation_id", correlation_id)

    # Parse webhook data
    with tracer.start_as_current_span("parse_webhook") as parse_span:
        data = json.loads(request.body)
        parse_span.set_attribute("payment.id", data['id'])
        parse_span.set_attribute("payment.status", data['status'])

    # Verify signature (security)
    with tracer.start_as_current_span("verify_signature") as verify_span:
        if not verify_yookassa_signature(request):
            verify_span.set_attribute("valid", False)
            span.record_exception(ValueError("Invalid signature"))
            return Response({"error": "Invalid signature"}, status=400)
        verify_span.set_attribute("valid", True)

    # Update invoice
    with tracer.start_as_current_span("update_invoice") as update_span:
        invoice = Invoice.objects.get(external_id=data['id'])
        update_span.set_attribute("invoice.id", invoice.id)

        if data['status'] == 'succeeded':
            invoice.status = 'paid'
            update_span.set_attribute("new_status", "paid")

            # Unlock materials (separate span)
            with tracer.start_as_current_span("unlock_materials") as unlock_span:
                materials = invoice.enrollment.get_available_materials()
                unlock_span.set_attribute("materials_count", materials.count())
                for material in materials:
                    material.unlock_for_user(invoice.enrollment.user)
                unlock_span.add_event("materials_unlocked")

            # Send confirmation email
            with tracer.start_as_current_span("send_email") as email_span:
                send_payment_confirmation(invoice)
                email_span.add_event("confirmation_sent")

        invoice.save()
        update_span.set_attribute("saved", True)

    # Queue post-payment hooks
    with tracer.start_as_current_span("queue_hooks") as hooks_span:
        process_payment_hooks.delay(invoice.id)
        hooks_span.add_event("hooks_queued")

    return Response({"status": "ok"})

# Trace structure:
# POST /api/payments/webhook/ [100% sampled]
# └─ process_payment_webhook
#   ├─ parse_webhook
#   ├─ verify_signature
#   ├─ update_invoice
#   │ ├─ SELECT from invoices (auto)
#   │ ├─ unlock_materials
#   │ │ └─ UPDATE material_progress (auto)
#   │ ├─ send_email
#   │ │ └─ SMTP connection (auto)
#   │ └─ UPDATE invoices (auto)
#   └─ queue_hooks
#     └─ Celery task queued (auto)
```

## Background Task Tracing

### Celery Task

```python
from celery import shared_task
from config.tracing import get_tracer, set_correlation_id
import uuid

tracer = get_tracer(__name__)

@shared_task
@tracer.start_as_current_span("send_weekly_report")
def send_weekly_reports():
    """Send weekly reports to all teachers."""
    span = trace.get_current_span()

    # Generate correlation ID for task
    correlation_id = str(uuid.uuid4())
    set_correlation_id(correlation_id)
    span.set_attribute("correlation_id", correlation_id)

    # Get all teachers
    with tracer.start_as_current_span("fetch_teachers") as fetch_span:
        teachers = User.objects.filter(role='teacher')
        fetch_span.set_attribute("count", teachers.count())

    # Process each teacher
    with tracer.start_as_current_span("process_teachers") as process_span:
        for teacher in teachers:
            with tracer.start_as_current_span("generate_report") as report_span:
                report_span.set_attribute("teacher.id", teacher.id)
                report_span.set_attribute("teacher.email", teacher.email)

                # Generate report
                report_data = generate_report(teacher)
                report_span.set_attribute("report.size", len(report_data))

                # Send email
                with tracer.start_as_current_span("send_email") as email_span:
                    send_mail(
                        subject="Weekly Report",
                        body=report_data,
                        recipient=teacher.email
                    )
                    email_span.add_event("email_sent")

    span.add_event("all_reports_sent")

# Query in Jaeger:
# Task name: send_weekly_reports
# Shows:
# - Total execution time
# - Database queries per teacher
# - Email sending time
# - Correlation ID linking to webhook if triggered by one
```

## Error Tracking

### Exception Spans

```python
from opentelemetry import trace

def risky_operation(user_id: int):
    """Example of error tracking in spans."""
    span = trace.get_current_span()
    span.set_attribute("operation", "risky_operation")
    span.set_attribute("user.id", user_id)

    try:
        result = dangerous_api_call(user_id)
        span.set_attribute("success", True)
        return result

    except TimeoutError as e:
        # Record exception in span
        span.record_exception(e)
        span.set_attribute("error", True)
        span.set_attribute("error.type", "TimeoutError")
        span.set_attribute("error.message", str(e))

        # Raise for HTTP error response
        raise

    except ValueError as e:
        # Record validation error
        span.record_exception(e)
        span.set_attribute("error", True)
        span.set_attribute("error.type", "ValueError")

        # Return user-friendly response
        return {"error": "Invalid input"}

# Jaeger shows:
# - Red timeline indicating error
# - Exception details in span
# - Stack trace in logs section
# - Automatically sampled (100% for errors)
```

## Performance Analysis

### Finding Slow Operations

1. **In Jaeger UI**:
   - Open recent trace
   - Sort spans by duration
   - Identify longest-running spans

2. **Example trace showing bottleneck**:
   ```
   POST /api/chat/rooms/           350ms total
   ├─ GET /api/materials/   (200ms) ← Database slow
   ├─ CREATE room           (10ms)
   ├─ ADD members          (5ms)
   └─ NOTIFY users        (135ms)
   ```

### Database Query Optimization

```python
# Without tracing - hard to identify:
def get_user_materials(user):
    return Material.objects.filter(users=user)
    # Problem: N+1 query if accessing related objects

# With tracing - clearly shows:
span.set_attribute("query.count", 15)  # Shows N+1 problem
span.set_attribute("query.time_ms", 850)

# Solution with tracing:
def get_user_materials_optimized(user):
    with tracer.start_as_current_span("get_materials") as span:
        materials = Material.objects.filter(
            users=user
        ).select_related(
            'subject'  # Avoid N+1
        ).prefetch_related(
            'files'
        )
        span.set_attribute("count", materials.count())
        span.set_attribute("optimized", True)
        return materials

# Jacer shows:
# Original: 15 queries, 850ms
# Optimized: 3 queries, 50ms
```

## Advanced Queries

### Finding Issues

**All errors in last hour**:
1. In Jaeger UI: "error = true"
2. Select "Last 1h"
3. Find Traces

**Slow payment webhooks**:
1. Operation: "process_payment_webhook"
2. Min Duration: 5s
3. Find Traces

**Specific user activity**:
1. Tags: "user.id = 5"
2. All operations traced under this tag

### Performance Dashboard

Create Grafana dashboard using Prometheus metrics:

```promql
# Traces per second
rate(otelcol_receiver_accepted_spans_total[5m])

# Export success rate
rate(otelcol_exporter_sent_spans_total[5m]) /
rate(otelcol_receiver_accepted_spans_total[5m])

# Collector memory usage
process_resident_memory_bytes{job="otel-collector"}

# Jaeger storage latency
jaeger_storage_latency_ms
```

## Correlation Across Services

### Trace a Complete Request-Response Cycle

```
Client Request
│
├─ Header: X-Correlation-ID: abc-123
│
└─► API Gateway
    │
    ├─ Span: gateway_auth (uses correlation_id: abc-123)
    │
    └─► Django View
        │
        ├─ Span: POST /api/data (uses correlation_id: abc-123)
        ├─ Span: database_query
        │
        └─► External Service (HTTP call with headers)
            │
            ├─ Header: X-Correlation-ID: abc-123
            │
            └─ Response
                │
                └─► Jaeger shows complete trace
                    with correlation_id: abc-123
```

All spans in Jaeger UI are linked by correlation_id.

## Best Practices Summary

1. **Always set correlation_id** for requests
2. **Use automatic instrumentation** for HTTP, DB, cache
3. **Add custom spans** for business logic
4. **Record attributes** for filtering
5. **Add events** for important milestones
6. **Record exceptions** with span.record_exception()
7. **Monitor tracing system** with alerts
8. **Archive old traces** to save storage

## Next Steps

- Run examples in your code
- Generate traces with real traffic
- Analyze performance using Jaeger UI
- Set up alerts using tracing_rules.yml
- Share trace links with team for debugging
