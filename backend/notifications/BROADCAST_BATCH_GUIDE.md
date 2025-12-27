# Broadcast Batch Processing Service

Comprehensive guide for the optimized broadcast notification system with batch operations support.

## Overview

The Broadcast Notification Service provides a robust, scalable system for sending notifications to multiple user groups with:
- Batch processing for optimized database operations
- Progress tracking and monitoring
- Automatic retry mechanisms
- Support for multiple targeting strategies
- Comprehensive error handling

## Models

### Broadcast Model
```
Fields:
- created_by (ForeignKey): User who created the broadcast
- target_group (CharField): ALL_STUDENTS, ALL_TEACHERS, ALL_TUTORS, ALL_PARENTS, BY_SUBJECT, BY_TUTOR, BY_TEACHER, CUSTOM
- target_filter (JSONField): Additional filters (subject_id, tutor_id, teacher_id, user_ids)
- message (TextField): Broadcast message (max 1000 chars)
- recipient_count (IntegerField): Total number of recipients
- sent_count (IntegerField): Successfully sent count
- failed_count (IntegerField): Failed count
- error_log (JSONField): Array of errors with timestamps
- status (CharField): DRAFT, SCHEDULED, SENDING, SENT, COMPLETED, FAILED, CANCELLED
- scheduled_at (DateTimeField): Optional scheduled time
- sent_at (DateTimeField): When sending started
- completed_at (DateTimeField): When sending completed
```

### BroadcastRecipient Model
```
Fields:
- broadcast (ForeignKey): Reference to Broadcast
- recipient (ForeignKey): Reference to User
- telegram_sent (BooleanField): Whether sent to Telegram
- telegram_message_id (CharField): Message ID in Telegram
- telegram_error (TextField): Error message if failed
- sent_at (DateTimeField): When sent
```

## API Endpoints

### Broadcast ViewSet

#### List Broadcasts
```
GET /api/admin/broadcasts/
Query params:
- status: draft|sending|sent|failed|cancelled
- date_from: YYYY-MM-DD
- date_to: YYYY-MM-DD
- search: text search in message
- page: page number
- page_size: results per page

Response:
{
  "count": 100,
  "next": 2,
  "previous": null,
  "results": [...],
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

#### Create Broadcast
```
POST /api/admin/broadcasts/
{
  "target_group": "all_students",
  "target_filter": {"subject_id": 5},  // optional
  "message": "Important notification",
  "send_immediately": false  // optional
}

Response:
{
  "success": true,
  "data": {Broadcast object},
  "message": "Рассылка успешно создана"
}
```

#### Get Broadcast Details
```
GET /api/admin/broadcasts/{id}/

Response:
{
  "success": true,
  "data": {
    "id": 1,
    "created_by": 1,
    "created_by_name": "Admin User",
    "target_group": "all_students",
    "target_group_display": "Все студенты",
    "message": "...",
    "status": "sending",
    "status_display": "Отправляется",
    "recipient_count": 100,
    "sent_count": 45,
    "failed_count": 5,
    "recipients": [
      {
        "id": 1,
        "user_id": 123,
        "user_name": "John Doe",
        "email": "john@test.com",
        "telegram_id": "123456789",
        "telegram_sent": true,
        "error_message": null,
        "sent_at": "2024-01-01T12:00:00Z"
      }
    ],
    "created_at": "2024-01-01T11:00:00Z",
    "sent_at": "2024-01-01T12:00:00Z"
  }
}
```

#### Get Progress
```
GET /api/admin/broadcasts/{id}/progress/

Response:
{
  "success": true,
  "data": {
    "id": 1,
    "status": "sending",
    "total_recipients": 100,
    "sent_count": 45,
    "failed_count": 5,
    "pending_count": 50,
    "progress_pct": 50,
    "error_summary": "5 failed: network error",
    "created_at": "2024-01-01T11:00:00Z",
    "sent_at": "2024-01-01T12:00:00Z",
    "completed_at": null
  }
}
```

#### Cancel Broadcast
```
POST /api/admin/broadcasts/{id}/cancel/

Response:
{
  "success": true,
  "data": {
    "message": "Рассылка успешно отменена",
    "broadcast_id": 1,
    "cancelled_at": "2024-01-01T12:30:00Z"
  }
}
```

#### Retry Failed
```
POST /api/admin/broadcasts/{id}/retry/

Response:
{
  "success": true,
  "data": {
    "message": "Повторная отправка запущена для 50 получателей",
    "retried_count": 50,
    "broadcast_id": 1,
    "task_id": "celery-task-id"
  }
}
```

#### Get Recipients
```
GET /api/admin/broadcasts/{id}/recipients/
Query params:
- status: sent|failed|pending
- page: page number
- page_size: results per page

Response:
{
  "count": 100,
  "next": 2,
  "previous": null,
  "results": [...],
  "page": 1,
  "page_size": 20,
  "total_pages": 5
}
```

## Service Layer

### BroadcastService

Main service for broadcast operations.

#### Methods

##### get_progress(broadcast_id: int) -> Dict
Get progress information for a broadcast.

```python
from notifications.services.broadcast import BroadcastService

progress = BroadcastService.get_progress(broadcast_id=1)
# Returns:
# {
#   'id': 1,
#   'status': 'sending',
#   'total_recipients': 100,
#   'sent_count': 50,
#   'failed_count': 10,
#   'pending_count': 40,
#   'progress_pct': 60,
#   'error_summary': '10 failed: ...',
#   ...
# }
```

##### cancel_broadcast(broadcast_id: int) -> Dict
Cancel a broadcast and stop sending.

```python
result = BroadcastService.cancel_broadcast(broadcast_id=1)
# Returns: {'success': True, 'message': '...', 'broadcast_id': 1, 'cancelled_at': '...'}
```

##### retry_failed(broadcast_id: int, max_retries: int = 3) -> Dict
Queue failed recipients for retry.

```python
result = BroadcastService.retry_failed(broadcast_id=1)
# Returns: {'success': True, 'message': '...', 'retried_count': 50, 'task_id': '...'}
```

##### update_progress(broadcast_id: int, sent_count: int, failed_count: int) -> None
Update broadcast progress (internal).

### BroadcastBatchProcessor

Optimized batch processing for broadcasts.

#### Methods

##### create_broadcast_recipients_batch(broadcast_id: int, recipient_ids: List[int], batch_size: int = 1000) -> Dict
Create BroadcastRecipient records in optimized batches.

```python
from notifications.broadcast_batch import BroadcastBatchProcessor

result = BroadcastBatchProcessor.create_broadcast_recipients_batch(
    broadcast_id=1,
    recipient_ids=[1, 2, 3, 4, 5],
    batch_size=2
)
# Returns:
# {
#   'success': True,
#   'created_count': 5,
#   'total_count': 5,
#   'batches_processed': 3,
#   'errors': []
# }
```

##### send_to_group_batch(broadcast_id: int, target_group: str, target_filter: Dict = None, batch_size: int = 100) -> Dict
Send broadcast to a target group using batch processing.

```python
result = BroadcastBatchProcessor.send_to_group_batch(
    broadcast_id=1,
    target_group='all_students',
    batch_size=100
)

result = BroadcastBatchProcessor.send_to_group_batch(
    broadcast_id=1,
    target_group='by_subject',
    target_filter={'subject_id': 5}
)
```

##### send_to_role_batch(broadcast_id: int, role: str, batch_size: int = 100) -> Dict
Send to all users of a specific role.

```python
result = BroadcastBatchProcessor.send_to_role_batch(
    broadcast_id=1,
    role='student',  # or 'teacher', 'tutor', 'parent'
    batch_size=100
)
```

##### send_to_custom_list_batch(broadcast_id: int, user_ids: List[int], batch_size: int = 100) -> Dict
Send to a custom list of users.

```python
result = BroadcastBatchProcessor.send_to_custom_list_batch(
    broadcast_id=1,
    user_ids=[1, 2, 3, 4, 5],
    batch_size=100
)
```

##### retry_failed_batch(broadcast_id: int, max_retries: int = 3, batch_size: int = 100) -> Dict
Retry failed sends in batches.

```python
result = BroadcastBatchProcessor.retry_failed_batch(
    broadcast_id=1,
    max_retries=3,
    batch_size=100
)
```

##### get_batch_status(broadcast_id: int) -> Dict
Get detailed batch processing status.

```python
status = BroadcastBatchProcessor.get_batch_status(broadcast_id=1)
# Returns:
# {
#   'broadcast_id': 1,
#   'status': 'sending',
#   'total_recipients': 100,
#   'sent_count': 50,
#   'failed_count': 10,
#   'pending_count': 40,
#   'progress_pct': 60,
#   ...
# }
```

## Target Groups

### Supported Target Groups

1. **ALL_STUDENTS** - All active students
   ```json
   {
     "target_group": "all_students"
   }
   ```

2. **ALL_TEACHERS** - All active teachers
   ```json
   {
     "target_group": "all_teachers"
   }
   ```

3. **ALL_TUTORS** - All active tutors
   ```json
   {
     "target_group": "all_tutors"
   }
   ```

4. **ALL_PARENTS** - All active parents
   ```json
   {
     "target_group": "all_parents"
   }
   ```

5. **BY_SUBJECT** - Students and teachers of a specific subject
   ```json
   {
     "target_group": "by_subject",
     "target_filter": {
       "subject_id": 5
     }
   }
   ```

6. **BY_TUTOR** - Students assigned to a specific tutor
   ```json
   {
     "target_group": "by_tutor",
     "target_filter": {
       "tutor_id": 3
     }
   }
   ```

7. **BY_TEACHER** - Students assigned to a specific teacher
   ```json
   {
     "target_group": "by_teacher",
     "target_filter": {
       "teacher_id": 2
     }
   }
   ```

8. **CUSTOM** - Custom list of specific users
   ```json
   {
     "target_group": "custom",
     "target_filter": {
       "user_ids": [1, 2, 3, 4, 5]
     }
   }
   ```

## Celery Tasks

### Async Tasks for Long-Running Operations

#### send_broadcast_async(broadcast_id: int, only_failed: bool = False) -> Dict
Send broadcast asynchronously with retries.

```python
from notifications.services.broadcast import send_broadcast_async

task = send_broadcast_async.delay(broadcast_id=1)
# Returns Celery task object with task.id
```

#### process_scheduled_broadcasts() -> Dict
Process all scheduled broadcasts (runs periodically via Celery Beat).

```python
from notifications.services.broadcast import process_scheduled_broadcasts

task = process_scheduled_broadcasts.delay()
```

#### process_broadcast_batch_async(broadcast_id: int, target_group: str, target_filter: Dict = None) -> Dict
Process broadcast with batch optimization asynchronously.

```python
from notifications.broadcast_batch import process_broadcast_batch_async

task = process_broadcast_batch_async.delay(
    broadcast_id=1,
    target_group='all_students',
    target_filter=None
)
```

## Configuration

### Batch Processor Configuration

```python
# In BroadcastBatchProcessor class
BATCH_SIZE = 1000              # Size for bulk_create operations
SEND_BATCH_SIZE = 100          # Size for send operations
MAX_RETRIES = 3                # Max retry attempts
RETRY_DELAYS = [10, 60, 300]   # Retry delays in seconds (10s, 1m, 5m)
```

Customize by subclassing:

```python
class CustomBroadcastProcessor(BroadcastBatchProcessor):
    BATCH_SIZE = 5000
    SEND_BATCH_SIZE = 500
    MAX_RETRIES = 5
```

## Examples

### Example 1: Send Broadcast to All Students

```python
from notifications.models import Broadcast
from notifications.services.broadcast import BroadcastService

# Create broadcast
broadcast = Broadcast.objects.create(
    created_by=admin_user,
    target_group='all_students',
    message='Important announcement for all students',
    recipient_count=0,  # Will be updated
    status='draft'
)

# Send immediately
from notifications.broadcast_views import _get_recipients_by_group, _create_broadcast_recipients
recipients = _get_recipients_by_group('all_students')
broadcast.recipient_count = len(recipients)
broadcast.save()

_create_broadcast_recipients(broadcast, recipients)

# Queue for sending
from notifications.broadcast_batch import process_broadcast_batch_async
task = process_broadcast_batch_async.delay(
    broadcast_id=broadcast.id,
    target_group='all_students'
)

# Track progress
progress = BroadcastService.get_progress(broadcast.id)
print(f"Progress: {progress['progress_pct']}%")
```

### Example 2: Send to Specific Subject

```python
from notifications.models import Broadcast
from notifications.services.broadcast import BroadcastService

broadcast = Broadcast.objects.create(
    created_by=admin_user,
    target_group='by_subject',
    target_filter={'subject_id': 5},
    message='New materials for Mathematics',
    status='draft'
)

# Use batch service
result = BroadcastService.send_to_group_batch(
    broadcast_id=broadcast.id,
    target_group='by_subject',
    target_filter={'subject_id': 5}
)

if result['success']:
    print(f"Sent to {result['sent_count']} recipients")
```

### Example 3: Retry Failed Sends

```python
from notifications.services.broadcast import BroadcastService

# Get progress
progress = BroadcastService.get_progress(broadcast_id=1)
if progress['failed_count'] > 0:
    # Retry
    result = BroadcastService.retry_failed(broadcast_id=1)
    print(f"Retrying {result['retried_count']} recipients")
    # Check progress again
    progress = BroadcastService.get_progress(broadcast_id=1)
```

## Error Handling

### Common Errors and Solutions

#### Broadcast Not Found
```python
from notifications.services.broadcast import BroadcastService

try:
    progress = BroadcastService.get_progress(broadcast_id=99999)
except ValueError as e:
    print(f"Error: {e}")  # "Broadcast 99999 not found"
```

#### Cannot Cancel Completed Broadcast
```python
try:
    BroadcastService.cancel_broadcast(broadcast_id=1)
except ValueError as e:
    print(f"Error: {e}")  # "Cannot cancel broadcast with status ..."
```

#### No Recipients Found
```json
{
  "success": false,
  "error": "No recipients found for group ...",
  "code": "NO_RECIPIENTS"
}
```

## Performance Considerations

1. **Batch Size**: Adjust `BATCH_SIZE` based on your database:
   - Large databases (100k+ users): Use 1000-5000
   - Medium databases: Use 500-1000
   - Small databases: Use 100-500

2. **Async Processing**: Always use async tasks for broadcasts > 100 recipients

3. **Indexing**: Ensure indexes on:
   - `Broadcast.status`, `Broadcast.scheduled_at`
   - `BroadcastRecipient.telegram_sent`, `BroadcastRecipient.broadcast`

4. **Database Connections**: Monitor active connections during bulk operations

## Testing

### Run Tests

```bash
# All broadcast tests
cd backend && python manage.py test notifications.test_broadcast_batch

# Specific test class
python manage.py test notifications.test_broadcast_batch.BroadcastBatchProcessorTestCase

# With pytest
pytest notifications/test_broadcast_batch.py -v
```

### Test Coverage

- Batch creation with various sizes
- Batch sending to different target groups
- Error handling and recovery
- Progress tracking
- Retry mechanisms
- Duplicate handling
- Performance with large datasets

## Monitoring

### Health Checks

Monitor these metrics:

1. **Broadcast Status Distribution**
   ```python
   from django.db.models import Count
   from notifications.models import Broadcast

   stats = Broadcast.objects.values('status').annotate(count=Count('id'))
   ```

2. **Failed Send Rate**
   ```python
   from notifications.models import BroadcastRecipient

   total = BroadcastRecipient.objects.count()
   failed = BroadcastRecipient.objects.filter(telegram_sent=False).count()
   failed_rate = (failed / total * 100) if total > 0 else 0
   ```

3. **Processing Time**
   ```python
   from django.db.models import F
   from notifications.models import Broadcast

   completed = Broadcast.objects.filter(
       status='completed'
   ).annotate(
       processing_time=F('completed_at') - F('sent_at')
   )
   ```

## Troubleshooting

### Broadcasts Stuck in "SENDING" Status
- Check Celery worker status
- Review error logs in `Broadcast.error_log`
- Manually cancel and retry

### High Memory Usage During Batch Operations
- Reduce `BATCH_SIZE`
- Add pagination to recipient queries
- Use `select_related()` and `prefetch_related()`

### Slow Batch Processing
- Add database indexes
- Increase `BATCH_SIZE` if database is fast
- Check network latency for Telegram API calls
