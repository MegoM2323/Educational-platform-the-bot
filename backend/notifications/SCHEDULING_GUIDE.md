# Notification Scheduling Guide

This guide covers the Celery-based notification scheduling system for THE_BOT platform.

## Overview

The notification scheduling system allows you to:
- Schedule notifications to be sent at a specific time in the future
- Cancel scheduled notifications before they're sent
- Retry failed notifications with exponential backoff
- Monitor the status of scheduled notifications
- Automatically clean up old cancelled notifications

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ API Layer                                                       │
│ POST /api/notifications/schedule/                               │
│ DELETE /api/notifications/{id}/cancel_scheduled/                │
│ GET /api/notifications/{id}/schedule_status/                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│ NotificationScheduler Service                                   │
│ - schedule_notification()                                        │
│ - cancel_scheduled()                                             │
│ - send_scheduled_notification()                                  │
│ - get_pending_notifications()                                    │
│ - get_schedule_status()                                          │
│ - retry_failed_notification()                                    │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│ Celery Tasks                                                    │
│ - send_notification_task()           (async sender)              │
│ - process_scheduled_notifications()  (every 1 minute)            │
│ - retry_failed_notifications()       (every 5 minutes)           │
│ - cleanup_cancelled_notifications()  (daily at 3:00 AM)          │
└─────────────────────┬───────────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────────┐
│ Database (Notification Model)                                   │
│ Fields:                                                         │
│ - scheduled_at (DateTime): When to send                          │
│ - scheduled_status (CharField): pending/sent/cancelled           │
│ - is_sent (BooleanField): Sent flag                              │
│ - sent_at (DateTime): When it was sent                           │
└─────────────────────────────────────────────────────────────────┘
```

## API Endpoints

### 1. Schedule Notifications

Schedule notifications for future delivery.

**Endpoint**: `POST /api/notifications/schedule/`

**Authentication**: Required (authenticated user)

**Request Body**:
```json
{
  "recipients": [1, 2, 3],
  "title": "Meeting Reminder",
  "message": "You have a meeting in 30 minutes",
  "scheduled_at": "2025-12-28T10:00:00Z",
  "type": "reminder",
  "priority": "high",
  "related_object_type": "meeting",
  "related_object_id": 123,
  "data": {
    "meeting_id": 123,
    "duration": "30 minutes"
  }
}
```

**Required Fields**:
- `recipients`: List of user IDs
- `title`: Notification title (max 200 chars)
- `message`: Notification message (required)
- `scheduled_at`: ISO 8601 datetime string (must be in future)

**Optional Fields**:
- `type`: Notification type (default: 'system')
- `priority`: Priority level (default: 'normal')
- `related_object_type`: Type of related object
- `related_object_id`: ID of related object
- `data`: Additional JSON data

**Response** (201 Created):
```json
{
  "notification_ids": [1, 2, 3],
  "count": 3,
  "scheduled_at": "2025-12-28T10:00:00Z"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid scheduled_at (past) or empty recipients
- `404 Not Found`: User IDs don't exist

**Example with curl**:
```bash
curl -X POST http://localhost:8000/api/notifications/schedule/ \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": [1, 2],
    "title": "Test",
    "message": "Test message",
    "scheduled_at": "2025-12-28T10:00:00Z"
  }'
```

### 2. Cancel Scheduled Notification

Cancel a scheduled notification before it's sent.

**Endpoint**: `DELETE /api/notifications/{id}/cancel_scheduled/`

**Authentication**: Required (notification recipient or admin)

**Response** (200 OK):
```json
{
  "message": "Notification cancelled successfully",
  "notification_id": 1
}
```

**Error Responses**:
- `400 Bad Request`: Notification not in pending state
- `404 Not Found`: Notification doesn't exist

**Example with curl**:
```bash
curl -X DELETE http://localhost:8000/api/notifications/1/cancel_scheduled/ \
  -H "Authorization: Token YOUR_TOKEN"
```

### 3. Get Schedule Status

Get the scheduling status of a notification.

**Endpoint**: `GET /api/notifications/{id}/schedule_status/`

**Authentication**: Required (notification recipient or admin)

**Response** (200 OK):
```json
{
  "id": 1,
  "title": "Meeting Reminder",
  "scheduled_at": "2025-12-28T10:00:00Z",
  "scheduled_status": "pending",
  "is_sent": false,
  "sent_at": null,
  "created_at": "2025-12-27T09:00:00Z"
}
```

**Status Values**:
- `pending`: Waiting to be sent
- `sent`: Successfully sent
- `cancelled`: Cancelled by user

## Database Model

### Notification Model Fields

```python
class Notification(models.Model):
    # Scheduling fields
    scheduled_at = models.DateTimeField(null=True, blank=True)
    scheduled_status = models.CharField(
        choices=[
            ('pending', 'Pending'),
            ('sent', 'Sent'),
            ('cancelled', 'Cancelled'),
        ],
        default='pending'
    )

    # Existing fields
    recipient = ForeignKey(User)
    title = CharField(max_length=200)
    message = TextField()
    type = CharField(max_length=30)
    priority = CharField(max_length=10)
    is_sent = BooleanField(default=False)
    is_read = BooleanField(default=False)
    sent_at = DateTimeField(null=True, blank=True)
    created_at = DateTimeField(auto_now_add=True)
    # ... more fields
```

### Indexes

```python
indexes = [
    Index(fields=['scheduled_at', 'scheduled_status']),
    Index(fields=['recipient', 'scheduled_status']),
]
```

## Celery Tasks

### 1. process_scheduled_notifications()

**Schedule**: Every minute (via Celery Beat)

**Function**: Processes all pending notifications that are due to be sent.

**Logic**:
1. Query: `Notification.objects.filter(scheduled_at <= now, scheduled_status='pending')`
2. For each notification: enqueue `send_notification_task`
3. Log statistics

**Returns**:
```python
{
    'processed': 5,
    'failed': 0,
    'timestamp': '2025-12-27T10:00:00Z'
}
```

### 2. send_notification_task(notification_id)

**Schedule**: On-demand (enqueued by process_scheduled_notifications)

**Function**: Sends a single notification asynchronously.

**Retry Logic**:
- Max retries: 3
- Exponential backoff: 5min, 10min, 20min

**Logic**:
1. Get notification
2. Send via WebSocket to recipient
3. Update status to 'sent'
4. Log result

**Returns**:
```python
{
    'success': True,
    'notification_id': 1,
    'message': 'Notification sent successfully'
}
```

### 3. retry_failed_notifications()

**Schedule**: Every 5 minutes (via Celery Beat)

**Function**: Finds and retries stuck notifications.

**Logic**:
1. Query: notifications with `scheduled_at < (now - 5 min)` and `scheduled_status='pending'`
2. For each: reschedule with 10-minute delay
3. Process up to 100 per run

**Returns**:
```python
{
    'retried': 5,
    'timestamp': '2025-12-27T10:00:00Z'
}
```

### 4. cleanup_cancelled_notifications(days_old=30)

**Schedule**: Daily at 3:00 AM (via Celery Beat)

**Function**: Cleans up old cancelled notifications.

**Logic**:
1. Query: notifications with `scheduled_at < (now - 30 days)` and `scheduled_status='cancelled'`
2. Delete from database
3. Log cleanup stats

**Returns**:
```python
{
    'deleted': 10,
    'before_cutoff': 15,
    'cutoff_date': '2025-11-27T00:00:00Z',
    'timestamp': '2025-12-27T03:00:00Z'
}
```

## Python API (NotificationScheduler)

Use the `NotificationScheduler` service for programmatic access:

```python
from notifications.scheduler import NotificationScheduler

scheduler = NotificationScheduler()

# Schedule notifications
notification_ids = scheduler.schedule_notification(
    recipients=[1, 2, 3],
    title='Test',
    message='Test message',
    scheduled_at='2025-12-28T10:00:00Z',
    notif_type='system',
    priority='high',
    data={'key': 'value'}
)

# Cancel notification
success = scheduler.cancel_scheduled(notification_id=1)

# Get pending notifications
pending = scheduler.get_pending_notifications()

# Send a notification
success = scheduler.send_scheduled_notification(notification_id=1)

# Get status
status = scheduler.get_schedule_status(notification_id=1)

# Retry failed notification
success = scheduler.retry_failed_notification(
    notification_id=1,
    retry_delay_minutes=10
)
```

## Configuration

### Environment Variables

```bash
# Celery broker (Redis)
CELERY_BROKER_URL=redis://localhost:6379/0

# Celery result backend
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# Redis URL (fallback for both)
REDIS_URL=redis://localhost:6379/0
```

### Settings

Edit `backend/core/settings.py`:

```python
# Celery configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://127.0.0.1:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://127.0.0.1:6379/0')
CELERY_ACCEPT_CONTENT = ['application/json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes
```

### Beat Schedule

Edit `backend/core/celery_config.py`:

```python
CELERY_BEAT_SCHEDULE = {
    'process-scheduled-notifications': {
        'task': 'notifications.tasks.process_scheduled_notifications',
        'schedule': crontab(minute='*'),  # Every minute
    },
    'retry-failed-notifications': {
        'task': 'notifications.tasks.retry_failed_notifications',
        'schedule': crontab(minute='*/5'),  # Every 5 minutes
    },
    'cleanup-cancelled-notifications': {
        'task': 'notifications.tasks.cleanup_cancelled_notifications',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3:00 AM
    },
}
```

## Running the System

### Start Celery Worker

```bash
cd backend
celery -A core worker -l info
```

### Start Celery Beat (Scheduler)

```bash
cd backend
celery -A core beat -l info
```

### Both in One (Development)

```bash
cd backend
celery -A core worker -l info --beat
```

## Usage Examples

### Python Example

```python
from datetime import datetime, timedelta
from django.utils import timezone
from notifications.scheduler import NotificationScheduler
from django.contrib.auth import get_user_model

User = get_user_model()

scheduler = NotificationScheduler()

# Schedule for tomorrow at 10:00 AM
tomorrow_10am = (
    timezone.now()
    .replace(hour=10, minute=0, second=0, microsecond=0)
    + timedelta(days=1)
)

# Get all students
students = User.objects.filter(role='student')

# Schedule notification
notification_ids = scheduler.schedule_notification(
    recipients=[u.id for u in students],
    title='Daily Quiz Available',
    message='A new quiz is available in your subject',
    scheduled_at=tomorrow_10am,
    notif_type='assignment_new',
    priority='normal',
    data={
        'quiz_id': 123,
        'subject': 'Mathematics'
    }
)

print(f"Scheduled {len(notification_ids)} notifications")
```

### API Example (cURL)

```bash
# Schedule
curl -X POST http://localhost:8000/api/notifications/schedule/ \
  -H "Authorization: Token abc123def456" \
  -H "Content-Type: application/json" \
  -d '{
    "recipients": [1, 2, 3, 4, 5],
    "title": "System Maintenance",
    "message": "System maintenance on 2025-12-28 from 10:00 to 11:00 UTC",
    "scheduled_at": "2025-12-28T09:30:00Z",
    "type": "system",
    "priority": "urgent"
  }'

# Get status
curl http://localhost:8000/api/notifications/1/schedule_status/ \
  -H "Authorization: Token abc123def456"

# Cancel
curl -X DELETE http://localhost:8000/api/notifications/1/cancel_scheduled/ \
  -H "Authorization: Token abc123def456"
```

### API Example (Python)

```python
import requests
from datetime import datetime, timedelta
from django.utils import timezone

BASE_URL = 'http://localhost:8000/api'
TOKEN = 'your-auth-token'

headers = {
    'Authorization': f'Token {TOKEN}',
    'Content-Type': 'application/json'
}

# Schedule
scheduled_at = (timezone.now() + timedelta(hours=1)).isoformat()

payload = {
    'recipients': [1, 2, 3],
    'title': 'Test Notification',
    'message': 'This is a test',
    'scheduled_at': scheduled_at,
    'type': 'system',
    'priority': 'normal'
}

response = requests.post(
    f'{BASE_URL}/notifications/schedule/',
    json=payload,
    headers=headers
)

data = response.json()
notification_ids = data['notification_ids']
print(f"Created {len(notification_ids)} notifications: {notification_ids}")

# Check status
notif_id = notification_ids[0]
response = requests.get(
    f'{BASE_URL}/notifications/{notif_id}/schedule_status/',
    headers=headers
)
print(response.json())

# Cancel
response = requests.delete(
    f'{BASE_URL}/notifications/{notif_id}/cancel_scheduled/',
    headers=headers
)
print(response.json())
```

## Testing

Run tests:

```bash
cd backend
pytest notifications/test_scheduling.py -v
```

Run specific test:

```bash
pytest notifications/test_scheduling.py::NotificationSchedulerTestCase::test_schedule_notification_single_recipient -v
```

Test coverage:

```bash
pytest notifications/test_scheduling.py --cov=notifications.scheduler --cov-report=html
```

## Monitoring

### Check Celery Tasks

```bash
# List all tasks
celery -A core inspect active

# Get stats
celery -A core inspect stats

# See registered tasks
celery -A core inspect registered
```

### Log Monitoring

Check `/var/log/celery/` or journalctl:

```bash
journalctl -u celery-worker -f
journalctl -u celery-beat -f
```

### Database Monitoring

```python
from notifications.models import Notification
from django.utils import timezone
from datetime import timedelta

# Count pending notifications
pending_count = Notification.objects.filter(
    scheduled_status='pending'
).count()

# Get due notifications
now = timezone.now()
due = Notification.objects.filter(
    scheduled_at__lte=now,
    scheduled_status='pending'
).count()

# Failed notifications (stuck in pending for >5 minutes)
five_min_ago = now - timedelta(minutes=5)
stuck = Notification.objects.filter(
    scheduled_at__lt=five_min_ago,
    scheduled_status='pending'
).count()

print(f"Pending: {pending_count}, Due: {due}, Stuck: {stuck}")
```

## Troubleshooting

### Notifications Not Sending

1. Check Celery worker is running: `celery -A core inspect active`
2. Check Beat scheduler is running: `celery -A core inspect registered`
3. Check Redis connection: `redis-cli ping`
4. Check logs for errors

### High Memory Usage

- Reduce batch size in `retry_failed_notifications()` (currently 100)
- Increase cleanup frequency: change `days_old=30` to `days_old=14`
- Monitor pending notifications: `Notification.objects.filter(scheduled_status='pending').count()`

### Timezone Issues

Always use `django.utils.timezone.now()` and timezone-aware datetime objects.

```python
from django.utils import timezone

# Correct
scheduled_at = timezone.now() + timedelta(hours=1)

# Wrong
import datetime
scheduled_at = datetime.datetime.now() + timedelta(hours=1)  # Not timezone aware!
```

## Performance Considerations

- **Database**: Scheduled notifications use indexed queries on `scheduled_at` and `scheduled_status`
- **Redis**: All task state stored in Redis (configure Redis memory limits)
- **Celery**: Configure worker concurrency: `celery -A core worker -c 4` (4 concurrent tasks)
- **Batch Processing**: Processes up to 100 stuck notifications per run (configurable)

## Security

1. **Authentication**: All API endpoints require authentication
2. **Authorization**: Users can only view/cancel their own notifications
3. **Input Validation**: Scheduled time must be in future, recipients must exist
4. **SQL Injection**: Using Django ORM (parameterized queries)
5. **Rate Limiting**: Configure DRF throttling for `/schedule/` endpoint

## Future Enhancements

- [ ] WebSocket delivery (already integrated)
- [ ] Email delivery integration
- [ ] SMS delivery integration
- [ ] Recurring scheduled notifications
- [ ] Schedule templates
- [ ] Delivery analytics
- [ ] Advanced retry policies
- [ ] Notification batching
