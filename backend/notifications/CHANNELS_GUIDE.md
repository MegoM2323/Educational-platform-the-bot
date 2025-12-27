# Notification Channels Guide

This document describes the notification delivery channels system for THE_BOT platform.

## Overview

The notification channels system provides an abstraction layer for sending notifications through different delivery methods (push notifications, SMS, email, etc.). Each channel implements a common interface while handling provider-specific details.

## Architecture

### Channel Registry

The `get_channel()` factory function returns channel instances by type:

```python
from notifications.channels import get_channel

# Get a channel
push_channel = get_channel('push')
sms_channel = get_channel('sms')
```

Registered channels:
- `'push'` - Firebase Cloud Messaging (FCM) push notifications
- `'sms'` - SMS notifications via Twilio/MessageBird
- `'email'` - (Future) Email notifications

### Base Channel Class

All channels inherit from `AbstractChannel` and must implement:

```python
class AbstractChannel(ABC):
    @abstractmethod
    def send(self, notification, recipient) -> Dict[str, Any]:
        """Send notification through this channel."""
        pass

    @abstractmethod
    def validate_recipient(self, recipient) -> bool:
        """Check if recipient can receive via this channel."""
        pass

    @abstractmethod
    def get_channel_name(self) -> str:
        """Return channel type name."""
        pass
```

## Push Notifications (Firebase)

### Configuration

Add to `.env`:

```bash
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_SERVICE_ACCOUNT_KEY='{"type":"service_account","project_id":"...","...":"..."}'
```

Or set in `settings.py`:

```python
FIREBASE_PROJECT_ID = os.getenv('FIREBASE_PROJECT_ID')
FIREBASE_SERVICE_ACCOUNT_KEY = os.getenv('FIREBASE_SERVICE_ACCOUNT_KEY')
```

### Requirements

- Firebase project with Cloud Messaging enabled
- Service account key with Firebase Messaging permissions

### Device Token Management

Device tokens are stored in the `DeviceToken` model:

```python
from notifications.channels.models import DeviceToken

# Create a device token
DeviceToken.objects.create(
    user=user,
    token='firebase_device_token_here',
    device_type='ios',  # or 'android', 'web'
    device_name='iPhone 12',
    is_active=True,
)

# List active tokens
tokens = DeviceToken.objects.filter(user=user, is_active=True)
```

### Usage

```python
from notifications.channels import get_channel
from notifications.models import Notification

# Create notification
notification = Notification.objects.create(
    recipient=user,
    title='New Message',
    message='You have a new message',
    type=Notification.Type.MESSAGE_NEW,
)

# Send via push
channel = get_channel('push')
result = channel.send(notification, user)

# Result:
# {
#     'status': 'sent',
#     'sent_count': 1,
#     'failed_count': 0,
# }
```

### Error Handling

The Firebase channel handles several error types:

- **Transient errors** (INTERNAL, UNAVAILABLE, DEADLINE_EXCEEDED):
  - Can be retried automatically
  - Logged as recoverable errors

- **Permanent errors** (INVALID_ARGUMENT, FAILED_PRECONDITION, NOT_FOUND):
  - Cannot be retried
  - Token should be deactivated
  - Logged as fatal errors

### Payload Format

FCM messages are sent with the following structure:

```json
{
  "message": {
    "token": "device_token_here",
    "notification": {
      "title": "Message title (max 100 chars)",
      "body": "Message body (max 240 chars)",
      "click_action": "OPEN_APP"
    },
    "data": {
      "notification_id": "123",
      "action_type": "message_new",
      "priority": "normal",
      "extra_*": "additional data fields"
    }
  }
}
```

## SMS Notifications

### Configuration

#### Twilio (Default)

Add to `.env`:

```bash
SMS_PROVIDER=twilio
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890
```

### Requirements

- Twilio account with SMS capability
- Account credentials and verified sender phone number

### Phone Number Management

Phone numbers are stored in the `UserPhoneNumber` model:

```python
from notifications.channels.models import UserPhoneNumber

# Create phone number record
phone_record = UserPhoneNumber.objects.create(
    user=user,
    phone_number='+79876543210',  # E.164 format
    status='verified',
)
```

### Phone Validation

The SMS channel validates phone numbers:

```python
from notifications.channels import SMSChannel

sms = SMSChannel()

# Validate format
is_valid = sms.provider.validate_phone('+79876543210')
# Returns: True

# Normalize number
normalized = sms.provider._normalize_phone('9876543210')
# Returns: '+79876543210'
```

### Usage

```python
from notifications.channels import get_channel

# Create notification
notification = Notification.objects.create(
    recipient=user,
    title='Verification',
    message='Your verification code is 123456',
    type=Notification.Type.SYSTEM,
)

# Send via SMS
channel = get_channel('sms')
result = channel.send(notification, user)

# Result:
# {
#     'status': 'sent',
#     'message_length': 45,
#     'provider': 'twilio',
#     'provider_message_id': 'SM_abc123...',
# }
```

### Message Formatting

SMS messages are formatted and truncated to fit the 160 character limit:

```
Template: "{user_name}: {message}"
Example: "John Doe: Your verification code is 123456"
```

If the message exceeds 160 characters, it's truncated with "..." suffix:

```python
message = "x" * 200
sms = SMSChannel()
truncated = sms._truncate_sms(message)
# Returns: "xxx...xxx" (160 chars total)
```

### Supported Providers

Currently implemented:
- **Twilio** (fully functional)
  - Phone number validation with regex
  - E.164 format normalization
  - Russian number support (+7 country code)

Planned:
- **MessageBird**
- **AWS SNS**

## Error Handling

### Channel Validation Errors

Raised when recipient cannot receive via channel:

```python
from notifications.channels.base import ChannelValidationError

try:
    channel.send(notification, user)
except ChannelValidationError as e:
    print(f"Recipient validation failed: {e}")
```

### Channel Delivery Errors

Raised when delivery attempt fails:

```python
from notifications.channels.base import ChannelDeliveryError

try:
    channel.send(notification, user)
except ChannelDeliveryError as e:
    print(f"Delivery failed: {e}")
```

### Provider Errors

SMS provider-specific errors:

```python
from notifications.channels.sms import SMSProviderError

try:
    result = provider.send_sms(phone_number, message)
except SMSProviderError as e:
    print(f"SMS provider error: {e}")
```

## Integration with Notification Queue

The channels integrate with the notification queue system:

```python
from notifications.models import NotificationQueue, Notification

# Create notification
notification = Notification.objects.create(
    recipient=user,
    title='Test',
    message='Test message',
    type=Notification.Type.SYSTEM,
)

# Create queue entry for SMS delivery
queue_entry = NotificationQueue.objects.create(
    notification=notification,
    channel='sms',
    status=NotificationQueue.Status.PENDING,
)

# Process queue (in Celery task or management command)
from notifications.channels import get_channel

channel = get_channel(queue_entry.channel)
try:
    result = channel.send(notification, user)
    queue_entry.status = NotificationQueue.Status.SENT
except Exception as e:
    queue_entry.status = NotificationQueue.Status.FAILED
    queue_entry.error_message = str(e)
finally:
    queue_entry.save()
```

## Models

### DeviceToken

Stores Firebase device tokens for push notifications:

```python
class DeviceToken(models.Model):
    user = models.ForeignKey(User, ...)
    token = models.TextField(unique=True)  # FCM token
    device_type = models.CharField(choices=['ios', 'android', 'web'])
    device_name = models.CharField(max_length=255)  # e.g., "iPhone 12"
    is_active = models.BooleanField(default=True)
    last_used_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### UserPhoneNumber

Stores verified phone numbers for SMS:

```python
class UserPhoneNumber(models.Model):
    user = models.OneToOneField(User, ...)
    phone_number = models.CharField(max_length=20)  # E.164 format
    status = models.CharField(choices=['pending', 'verified', 'invalid'])
    verification_code = models.CharField(max_length=6)
    verification_attempts = models.PositiveIntegerField(default=0)
    verified_at = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

## Logging

Channels log all delivery attempts:

```
INFO: Channel=push, Recipient=user@example.com, Status=sent
ERROR: Channel=sms, Recipient=user@example.com, Status=failed, Error=Invalid phone number
```

Set logging level in settings:

```python
LOGGING = {
    'loggers': {
        'notifications.channels': {
            'level': 'INFO',
            'handlers': ['console', 'file'],
        },
    },
}
```

## Testing

Run channel tests:

```bash
# All channel tests
ENVIRONMENT=test python manage.py test notifications.test_channels

# Specific test class
ENVIRONMENT=test python manage.py test notifications.test_channels.TestTwilioSMSProvider

# With coverage
ENVIRONMENT=test pytest backend/notifications/test_channels.py -v --cov
```

## Admin Interface

Manage channels in Django admin:

- `/admin/notifications/devicetoken/` - View/manage device tokens
- `/admin/notifications/userphonenumber/` - View/manage phone numbers

## Best Practices

### 1. Use Channel Validation

Always validate recipient before sending:

```python
channel = get_channel('push')
if channel.validate_recipient(user):
    result = channel.send(notification, user)
else:
    print("User cannot receive push notifications")
```

### 2. Handle Provider Configuration

Check if provider is configured:

```python
sms = SMSChannel()
if not sms.provider:
    print("SMS provider not configured")
    return
```

### 3. Implement Retry Logic

Use the notification queue for retry handling:

```python
# Automatic retries with exponential backoff
queue_entry = NotificationQueue.objects.create(
    notification=notification,
    channel='sms',
    status=NotificationQueue.Status.PENDING,
    max_attempts=3,  # Retry up to 3 times
)
```

### 4. Monitor Delivery Status

Track delivery status in the queue:

```python
# Get failed deliveries
failed = NotificationQueue.objects.filter(
    status=NotificationQueue.Status.FAILED
)

# Analyze by channel
sms_failures = failed.filter(channel='sms')
push_failures = failed.filter(channel='push')
```

## Future Enhancements

- [ ] Email channel with template support
- [ ] Webhook integration for delivery status
- [ ] Message deduplication
- [ ] Rate limiting per user/channel
- [ ] A/B testing support
- [ ] Batch sending optimization
- [ ] Analytics dashboard
