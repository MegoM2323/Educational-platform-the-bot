# SMS Notification Service Implementation

## Overview

The SMS Notification Service (T_NTF_003) provides a comprehensive solution for sending SMS notifications with queuing, retry logic, and rate limiting.

**Status**: COMPLETE
**Files Created**:
- `notifications/services/sms_service.py` (SMSNotificationService)
- `notifications/tasks.py` (4 new SMS Celery tasks)
- `notifications/services/test_sms_service.py` (comprehensive test suite)

## Architecture

### Core Components

#### 1. SMSNotificationService (`sms_service.py`)
High-level service for SMS notification management.

**Key Features**:
- Message validation with character limit handling (160 chars)
- Recipient validation (SMS preferences, phone number)
- Rate limiting (10 SMS/hour per user)
- Async queuing via Celery
- Delivery tracking and status monitoring
- Statistics and analytics

**Main Methods**:
```python
# Queue SMS for async delivery
queue_entry = service.queue_sms(notification, recipient)

# Send SMS asynchronously with Celery
result = service.send_sms_async(notification, recipient)

# Send SMS immediately with fallback to queue
result = service.send_sms_now(notification, recipient)

# Get delivery status
status = service.get_sms_delivery_status(queue_entry_id)

# Get user SMS statistics
stats = service.get_user_sms_stats(user)
```

#### 2. SMS Channel (`channels/sms.py`)
Provider abstraction layer for SMS delivery.

**Existing Implementation**:
- TwilioSMSProvider (main provider)
- MessageBirdSMSProvider (placeholder)
- Phone number validation and normalization
- Character limit handling

#### 3. Celery Tasks (`tasks.py`)
Asynchronous task processing for SMS delivery and maintenance.

**Tasks Implemented**:

1. **send_sms_task** - Delivers single SMS with retry logic
   - Auto-retry on provider errors
   - Exponential backoff: 300s × 2^attempts
   - Max 3 attempts before failure
   - Status tracking (pending → processing → sent/failed)

2. **process_pending_sms** - Process scheduled SMS notifications
   - Run every minute via Celery Beat
   - Finds SMS with status=pending and scheduled_at ≤ now
   - Enqueues send_sms_task for delivery
   - Limits to 100 SMS per run

3. **retry_failed_sms** - Retry stuck/failed SMS
   - Run periodically (e.g., every 10 minutes)
   - Reschedules SMS stuck in processing >5 minutes
   - Implements exponential backoff
   - Respects max_attempts limit

4. **cleanup_old_sms_queue** - Cleanup old queue entries
   - Run daily (e.g., 3 AM)
   - Removes sent/failed entries older than 30 days
   - Frees database space
   - Logs cleanup statistics

#### 4. Database Model (`models.py` - NotificationQueue)
Existing model for SMS queuing and delivery tracking.

**Fields**:
```python
- notification: ForeignKey to Notification
- channel: 'sms' (hardcoded)
- status: pending/processing/sent/failed/cancelled
- scheduled_at: datetime for scheduled delivery
- attempts: current attempt count
- max_attempts: max retries (default 3)
- error_message: last error details
- created_at: queue entry creation time
- processed_at: actual send/failure time
```

### Message Validation

SMS messages are validated for:
- Non-empty string
- Max length: 480 characters (3 × 160 char SMS)
- Auto-truncated to 160 chars during delivery if needed

### Character Limit Handling

**SMS Channel** (`channels/sms.py`):
```python
SMS_CHAR_LIMIT = 160  # Standard SMS character limit

def _truncate_sms(message: str) -> str:
    """Truncate SMS to 160 chars if needed."""
    if len(message) <= self.SMS_CHAR_LIMIT:
        return message
    return message[:self.SMS_CHAR_LIMIT - 3] + "..."
```

Message formatting includes recipient name:
```python
SMS_TEMPLATE = "{user_name}: {message}"
```

### Rate Limiting

**Per-User Rate Limiting**:
- Limit: 10 SMS per hour per user
- Window: Rolling 1-hour window
- Applies to: pending, processing, sent statuses
- Enforced in: `SMSNotificationService.check_rate_limit()`

**Implementation**:
```python
RATE_LIMIT_PER_HOUR = 10

def check_rate_limit(self, recipient: User) -> bool:
    one_hour_ago = timezone.now() - timedelta(hours=1)
    sms_count = NotificationQueue.objects.filter(
        notification__recipient=recipient,
        channel='sms',
        status__in=['sent', 'processing', 'pending'],
        created_at__gte=one_hour_ago
    ).count()
    return sms_count < self.RATE_LIMIT_PER_HOUR
```

### Retry Logic with Exponential Backoff

**Configuration**:
```python
MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 300  # 5 minutes
RETRY_BACKOFF_MULTIPLIER = 2
```

**Retry Delay Calculation**:
- Attempt 1: 300 × 2^1 = 600 seconds (10 minutes)
- Attempt 2: 300 × 2^2 = 1200 seconds (20 minutes)
- Attempt 3: 300 × 2^3 = 2400 seconds (40 minutes)
- After 3 attempts: marked as FAILED

**Retry Flow**:
```
Queue SMS (pending) → send_sms_task fails with SMSProviderError
  ↓
Increment attempts (1)
  ↓
If attempts < max_attempts:
  - Status: pending
  - Reschedule in 600s
  - Celery task.retry()
  ↓
Else:
  - Status: failed
  - processed_at = now
  - Return failure
```

### Delivery Tracking

**Status Transitions**:
```
PENDING
  ↓ (send_sms_task.delay)
PROCESSING
  ↓ (SMS sent successfully)
SENT → (end state)

OR

PROCESSING
  ↓ (Provider error)
PENDING (retry scheduled)
  ↓ (Max attempts exceeded)
FAILED → (end state)

OR

PENDING/PROCESSING/SENT
  ↓ (cancel operation)
CANCELLED → (end state)
```

**Status Tracking**:
- `created_at`: Queue entry creation
- `scheduled_at`: When to send (default: now)
- `processed_at`: When actually processed (sent or failed)
- `attempts`: Current attempt count
- `error_message`: Last error from provider

## Usage Examples

### Basic Async SMS Sending

```python
from notifications.services.sms_service import SMSNotificationService
from notifications.models import Notification

service = SMSNotificationService()

# Create notification
notification = Notification.objects.create(
    recipient=user,
    type=Notification.Type.MESSAGE_NEW,
    title='Test SMS',
    message='Your verification code: 123456'
)

# Queue for async delivery
result = service.send_sms_async(notification, user)
# Result: {'status': 'queued', 'queue_id': 123}
```

### Immediate SMS Sending

```python
# Send immediately with fallback to queue
result = service.send_sms_now(notification, user)
# Result: {'status': 'sent', 'message_length': 45, ...}
# OR: {'status': 'queued_fallback', 'queue_id': 123, 'reason': '...'}
```

### Scheduled SMS Delivery

```python
from datetime import timedelta
from django.utils import timezone

# Schedule for 1 hour from now
scheduled_time = timezone.now() + timedelta(hours=1)

result = service.send_sms_async(
    notification,
    user,
    scheduled_at=scheduled_time
)
```

### Get Delivery Status

```python
status = service.get_sms_delivery_status(queue_id=123)
# Result: {
#     'queue_id': 123,
#     'status': 'sent',
#     'attempts': 1,
#     'max_attempts': 3,
#     'scheduled_at': '2024-01-15T10:30:00Z',
#     'processed_at': '2024-01-15T10:30:05Z',
#     'error': None
# }
```

### Get User SMS Statistics

```python
stats = service.get_user_sms_stats(user)
# Result: {
#     'user_id': 123,
#     'sent_today': 3,
#     'sent_last_hour': 2,
#     'failed_today': 1,
#     'pending': 0,
#     'rate_limit_remaining': 8
# }
```

## Celery Configuration

### Celery Beat Scheduling

Add to `config/celery.py`:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # ... existing tasks ...

    'process-pending-sms': {
        'task': 'notifications.tasks.process_pending_sms',
        'schedule': crontab(minute='*'),  # Every minute
    },
    'retry-failed-sms': {
        'task': 'notifications.tasks.retry_failed_sms',
        'schedule': crontab(minute='*/10'),  # Every 10 minutes
    },
    'cleanup-old-sms-queue': {
        'task': 'notifications.tasks.cleanup_old_sms_queue',
        'schedule': crontab(hour=3, minute=0),  # Daily at 3 AM
    },
}
```

### Celery Configuration

```python
# config/settings.py

CELERY_TASK_ROUTING = {
    'notifications.tasks.send_sms_task': {'queue': 'sms'},
    'notifications.tasks.process_pending_sms': {'queue': 'notifications'},
    'notifications.tasks.retry_failed_sms': {'queue': 'notifications'},
    'notifications.tasks.cleanup_old_sms_queue': {'queue': 'maintenance'},
}

CELERY_TASK_TIME_LIMIT = 300  # 5 minutes
CELERY_TASK_SOFT_TIME_LIMIT = 240  # 4 minutes
```

## Twilio Configuration

### Environment Variables

```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
SMS_PROVIDER=twilio
```

### Django Settings

```python
# config/settings.py
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_FROM_NUMBER = os.getenv('TWILIO_FROM_NUMBER')
SMS_PROVIDER = os.getenv('SMS_PROVIDER', 'twilio')
```

## Error Handling

### Validation Errors

```python
from notifications.services.sms_service import SMSValidationError

try:
    service.send_sms_async(notification, user)
except SMSValidationError as e:
    # Handle: empty message, invalid recipient, SMS disabled, etc.
    logger.warning(f"SMS validation failed: {e}")
```

### Queue Errors

```python
from notifications.services.sms_service import SMSQueueError

try:
    service.queue_sms(notification, user)
except SMSQueueError as e:
    # Handle: database error, rate limit exceeded, etc.
    logger.error(f"SMS queuing failed: {e}")
```

### Provider Errors

Provider errors trigger automatic retry with exponential backoff:
- Network timeouts
- Invalid phone number
- Provider quota exceeded
- API errors

## Testing

### Test Suite

Tests located in `notifications/services/test_sms_service.py`:

**Test Coverage**:
- Message validation (empty, too long, etc.)
- Recipient validation (SMS enabled, phone number)
- Rate limiting (within limit, exceeded)
- SMS queuing (success, failures)
- Async delivery (successful, fallback)
- Sync delivery (success, fallback)
- Retry logic (backoff, max attempts)
- Delivery status tracking
- User statistics

**Running Tests**:

```bash
# All SMS service tests
ENVIRONMENT=test pytest backend/notifications/services/test_sms_service.py -v

# Specific test
ENVIRONMENT=test pytest backend/notifications/services/test_sms_service.py::TestSMSNotificationService::test_rate_limit_exceeded -v

# With coverage
ENVIRONMENT=test pytest backend/notifications/services/test_sms_service.py -v --cov=notifications.services.sms_service
```

## Performance Considerations

### Database Optimization

The `NotificationQueue` model includes indexes for SMS queries:
```python
indexes = [
    models.Index(fields=['notification', 'channel', 'status', 'scheduled_at']),
]
```

Query optimization:
- Limit to 100 SMS per process_pending_sms run
- Limit to 50 SMS per retry_failed_sms run
- Use select_related for notification.recipient
- Batch delete for cleanup (30+ days old)

### Celery Optimization

- Dedicated queue for SMS tasks: `'queue': 'sms'`
- Task time limit: 5 minutes (Twilio API calls typically < 1 second)
- Soft time limit: 4 minutes (allows cleanup before hard limit)
- Max retries per task: 3 (with exponential backoff)

### Rate Limiting Benefits

- Per-user rate limit prevents spam
- Rolling 1-hour window allows 10 SMS/hour
- Protects against accidental bulk sending
- SMS costs are typically per-message, so this saves money

## Monitoring & Logging

### Log Levels

- **INFO**: SMS queued, SMS sent, retry scheduled
- **WARNING**: Provider error, rate limit exceeded, SMS skipped
- **ERROR**: Max retries exceeded, database error, configuration missing

### Key Logs

```
SMS queued for notification {notification_id} to user {email} (queue_id={queue_id})
Sent SMS for notification {notification_id} to user {email}
SMS delivery failed for queue {queue_id}, retrying in {delay}s
Max retries exceeded for queue {queue_id}
Processed pending SMS: {processed} enqueued, {failed} failed
Retried {retried} failed SMS notifications
Cleaned up {deleted} old SMS queue entries
```

### Metrics

Monitor via SMS statistics endpoint:
```python
stats = service.get_user_sms_stats(user)
# Track: sent_today, sent_last_hour, failed_today, pending, rate_limit_remaining
```

## Integration Points

### With Notification System

SMS channel integrates with existing notification system:
- Uses `Notification` model for message content
- Works with `NotificationSettings` for user preferences
- Uses `NotificationQueue` for delivery tracking

### With Other Channels

SMS works alongside:
- **Email channel**: `channels/email.py`
- **Push channel**: `channels/firebase.py`
- **WebSocket/In-app**: `notification_service.py`

## Future Enhancements

1. **Multiple SMS Providers**
   - MessageBird provider implementation
   - Provider fallback (Twilio → MessageBird)
   - Cost optimization via provider selection

2. **Advanced Rate Limiting**
   - Per-user daily limit
   - Per-phone-number limit
   - Quiet hours respecting user timezone

3. **SMS Templates**
   - Template variables: `{user_name}`, `{code}`, `{link}`
   - Localization: Multi-language SMS
   - Campaign tracking: SMS campaign IDs

4. **Webhook Integration**
   - SMS delivery confirmation via Twilio webhooks
   - Real-time status updates
   - Bounce/failure handling

5. **Reporting**
   - Daily SMS delivery report
   - Cost analysis by user/type
   - Delivery rate SLA monitoring

## Troubleshooting

### SMS Not Sending

**Check 1**: Is Twilio configured?
```bash
# In Django shell
from django.conf import settings
print(settings.TWILIO_ACCOUNT_SID)  # Should not be None
```

**Check 2**: Does user have SMS enabled?
```python
from notifications.models import NotificationSettings
settings_obj = NotificationSettings.objects.get(user=user)
print(settings_obj.sms_notifications)  # Should be True
```

**Check 3**: Is Celery running?
```bash
# Check worker status
celery -A config inspect active

# Check queue
celery -A config inspect reserved
```

**Check 4**: Are there rate limit errors?
```python
service = SMSNotificationService()
if not service.check_rate_limit(user):
    print("Rate limit exceeded")
```

### High Failure Rate

**Check 1**: Provider quota exceeded
- Check Twilio account usage at twilio.com/console

**Check 2**: Invalid phone numbers
- Verify phone number format (E.164)
- Check NotificationSettings for valid phone

**Check 3**: Network timeouts
- Increase Celery task time limit
- Check server network connectivity

## Dependencies

- **Twilio**: SMS provider API
- **Celery**: Async task processing
- **Redis**: Celery broker and result backend
- **Django**: ORM and models

## References

- [Twilio Python SDK](https://www.twilio.com/docs/python/install)
- [Celery Documentation](https://docs.celeryproject.org/)
- [SMS Best Practices](https://www.twilio.com/docs/sms/best-practices)
