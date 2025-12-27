# Email Notification Service

Complete email notification system with SMTP support, HTML templates, async delivery via Celery, and delivery tracking.

## Features

### Core Email Sending
- **SMTP Integration**: Full support for Django's email configuration
- **HTML + Plain Text**: Automatic HTML to plain text conversion for email clients
- **Custom Headers**: Notification ID tracking and email tags
- **Responsive Design**: Professional HTML email templates with mobile support
- **CC/BCC Support**: Send to multiple recipients

### Template System
- **Base Template**: Responsive email layout with branding
- **Notification-Specific Templates**: Pre-built templates for all notification types
  - `assignment_new.html` - New assignment notification
  - `invoice_sent.html` - Invoice payment request
  - `material_new.html` - New learning material
  - `message_new.html` - New message notification
  - `payment_success.html` - Payment confirmation
- **Template Variables**: Context-aware variables for dynamic content
- **Django Template Engine**: Full Jinja2 template support

### Async Email Delivery
- **Celery Integration**: Background task processing
- **Queuing System**: NotificationQueue model for tracking
- **Retry Logic**: Exponential backoff on failures (max 3 retries)
- **Status Tracking**: Pending → Processing → Sent/Failed
- **Batch Processing**: Send to multiple users efficiently

### Delivery Management
- **Bounce Handling**: Automatic disable of email for bounced addresses
- **User Preferences**: Respect per-user email notification settings
- **Queue Processing**: Periodic Celery tasks to process pending emails
- **Delivery Status**: Full history of delivery attempts and errors

## Usage

### Basic Email Sending

```python
from notifications.email_service import EmailNotificationService

service = EmailNotificationService()

# Send simple email
success = service.send_email(
    to_email='user@example.com',
    subject='Hello',
    html_content='<p>This is a test email</p>'
)

# With plain text fallback
success = service.send_email(
    to_email='user@example.com',
    subject='Hello',
    html_content='<p>HTML content</p>',
    plain_text='Plain text version'
)
```

### Templated Notification Emails

```python
from django.contrib.auth import get_user_model
from notifications.email_service import EmailNotificationService

User = get_user_model()
user = User.objects.get(id=1)
service = EmailNotificationService()

# Send notification email using template
context = {
    'assignment_title': 'Math Assignment',
    'subject_name': 'Mathematics',
    'teacher_name': 'John Doe',
    'due_date': '2024-01-15',
    'points': 100,
    'assignment_url': 'https://platform.com/assignments/123'
}

success = service.send_notification_email(
    recipient=user,
    notification_type='assignment_new',
    context=context,
    # Optional overrides:
    # template_name='notifications/custom_template.html',
    # subject='Custom Subject'
)
```

### Batch Email Sending

```python
from django.contrib.auth import get_user_model

User = get_user_model()
users = User.objects.filter(role='student')

service = EmailNotificationService()
results = service.send_batch_email(
    recipients=users,
    subject='Important Announcement',
    html_content='<p>All students please review...</p>',
    filter_settings=True  # Respects user notification preferences
)

print(f"Sent: {results['sent']}, Failed: {results['failed']}")
```

### Queue Notification for Async Delivery

```python
from notifications.models import Notification

notification = Notification.objects.create(
    recipient=user,
    type=Notification.Type.ASSIGNMENT_NEW,
    title='New Assignment',
    message='An assignment has been posted'
)

service = EmailNotificationService()
queue_entry = service.queue_notification_email(
    notification=notification,
    template_name='notifications/assignment_new.html',
    subject='New Assignment Posted',
    context={'assignment_title': 'Math 101'}
)

# Later, Celery tasks will process the queue
```

### Handle Email Bounces

```python
service = EmailNotificationService()

# Disable email for bounced address
service.handle_bounce(
    email='invalid@example.com',
    bounce_type='permanent',
    reason='Invalid email address'
)

# Temporary bounces (network issues, mailbox full)
service.handle_bounce(
    email='temp@example.com',
    bounce_type='temporary',
    reason='Mailbox temporarily full'
)
```

## Celery Tasks

### Available Tasks

#### `send_notification_email`
```python
from notifications.email_tasks import send_notification_email

# Queue email for async sending
send_notification_email.delay(
    notification_id=123,
    template_name='notifications/assignment_new.html',
    subject='New Assignment',
    context={'key': 'value'}
)
```

**Retry Policy**: Max 3 retries with exponential backoff (5min, 10min, 20min)

#### `send_batch_notification_emails`
```python
from notifications.email_tasks import send_batch_notification_emails

# Queue multiple emails
send_batch_notification_emails.delay(
    notification_ids=[1, 2, 3, 4, 5],
    template_name='notifications/assignment_new.html'
)
```

#### `process_email_queue`
```python
from notifications.email_tasks import process_email_queue

# Process pending email queue (run periodically)
result = process_email_queue.delay(batch_size=50)
```

#### `retry_failed_emails`
```python
from notifications.email_tasks import retry_failed_emails

# Retry failed emails
result = retry_failed_emails.delay(max_retries=3)
```

#### `cleanup_old_email_queue`
```python
from notifications.email_tasks import cleanup_old_email_queue

# Clean up old queue entries
result = cleanup_old_email_queue.delay(days_old=30)
```

## Celery Beat Schedule

Configure periodic tasks in `config/celery_config.py`:

```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Process email queue every 2 minutes
    'process-email-queue': {
        'task': 'notifications.process_email_queue',
        'schedule': 120.0,
        'args': (50,)  # batch size
    },

    # Retry failed emails every 10 minutes
    'retry-failed-emails': {
        'task': 'notifications.retry_failed_emails',
        'schedule': 600.0,
    },

    # Clean up old queue entries daily at 3 AM
    'cleanup-old-email-queue': {
        'task': 'notifications.cleanup_old_email_queue',
        'schedule': crontab(hour=3, minute=0),
        'args': (30,)  # days old
    },
}
```

## Configuration

### Django Settings

```python
# Email backend (production: use SMTP)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'
EMAIL_HOST_PASSWORD = 'your-app-password'
DEFAULT_FROM_EMAIL = 'noreply@thebot.platform'

# In-memory backend for testing
# EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
```

### Email Service Settings

```python
# No additional configuration needed - uses Django settings
# EmailNotificationService reads from:
# - DEFAULT_FROM_EMAIL
# - EMAIL_USE_TLS
# - EMAIL_BACKEND
```

## Models

### NotificationQueue
Tracks email delivery status for async sending.

```python
class NotificationQueue(models.Model):
    notification = ForeignKey(Notification)
    channel = CharField(choices=[...])  # 'email'
    status = CharField(choices=[
        'pending',      # Waiting to be processed
        'processing',   # Currently sending
        'sent',         # Successfully sent
        'failed',       # Failed after max retries
        'retry',        # Failed, will retry
        'cancelled'     # Cancelled
    ])
    attempts = IntegerField(default=0)
    max_attempts = IntegerField(default=3)
    error_message = TextField(blank=True)
    created_at = DateTimeField(auto_now_add=True)
    processed_at = DateTimeField(null=True, blank=True)
```

### Notification
Extended with email delivery fields.

```python
class Notification(models.Model):
    # Existing fields...
    is_sent = BooleanField(default=False)
    sent_at = DateTimeField(null=True, blank=True)
    data = JSONField()  # Stores: {
                        #   'email_template': '...',
                        #   'email_subject': '...',
                        #   'email_context': {...}
                        # }
```

### NotificationSettings
User preferences for notifications.

```python
class NotificationSettings(models.Model):
    user = OneToOneField(User)
    email_notifications = BooleanField(default=True)
    # Other notification channels...
```

## Template Structure

### Base Email Template (`base_email.html`)
- Responsive layout (mobile-optimized)
- Professional styling with CSS
- Brand colors and typography
- Footer with unsubscribe link
- Support for text and HTML

### Extending Templates
```html
{% extends "notifications/base_email.html" %}

{% block header %}Assignment Due{% endblock %}

{% block content %}
<div class="email-section">
    <p>Hello {{ recipient_name }},</p>
    <p>Your assignment is due soon.</p>
</div>

<div class="email-info-box">
    <strong>Details</strong>
    <p><strong>Due:</strong> {{ due_date }}</p>
</div>

<div class="email-button-group">
    <a href="{{ assignment_url }}" class="email-button">View Assignment</a>
</div>
{% endblock %}
```

## Testing

### Run Email Service Tests
```bash
ENVIRONMENT=test pytest backend/notifications/test_email_simple.py -v
```

### Test Email Templates
```python
from django.test import override_settings
from django.template.loader import render_to_string

@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
def test_email_template():
    context = {
        'recipient_name': 'John',
        'assignment_title': 'Math'
    }
    html = render_to_string('notifications/assignment_new.html', context)
    assert 'John' in html
```

### Manual Testing with In-Memory Backend
```python
from django.core import mail
from notifications.email_service import EmailNotificationService

# Configure Django to use locmem backend
# settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

service = EmailNotificationService()
service.send_email(
    to_email='test@example.com',
    subject='Test',
    html_content='<p>Test</p>'
)

# Check sent emails
print(len(mail.outbox))
print(mail.outbox[0].subject)
```

## HTML to Plain Text Conversion

Automatic conversion for email clients without HTML support:

```python
service = EmailNotificationService()
plain = service._strip_html('<p>Hello <strong>World</strong></p>')
# Result: "Hello World"
```

## Email Delivery Status

### Status Flow

```
┌─────────────┐
│   PENDING   │  Initial state, waiting to be processed
└──────┬──────┘
       │
       v
┌─────────────┐
│ PROCESSING  │  Currently sending email
└──────┬──────┘
       │
   ┌───┴───┐
   v       v
┌──────┐  ┌──────┐
│ SENT │  │RETRY │  Failed, will retry
└──────┘  └──────┘
          │
          v
       ┌──────┐
       │FAILED│  Max retries exceeded
       └──────┘
```

### Tracking Delivery

```python
from notifications.models import NotificationQueue

# Get delivery status
queue_entry = NotificationQueue.objects.get(notification_id=123)
print(f"Status: {queue_entry.status}")
print(f"Attempts: {queue_entry.attempts}/{queue_entry.max_attempts}")
print(f"Error: {queue_entry.error_message}")
print(f"Sent at: {queue_entry.processed_at}")
```

## Performance

### Optimization Tips

1. **Use Batch Sending**: Send to multiple users in one task
2. **Configure Queue Size**: Adjust batch_size in process_email_queue
3. **Cache Templates**: Django template caching enabled by default
4. **Connection Pooling**: SMTP connections reused across tasks
5. **Database Indexes**: Indexed on (channel, status) for fast lookups

### Metrics

- **Send Time**: ~100-500ms per email (depending on SMTP provider)
- **Queue Processing**: 50 emails per task cycle
- **Retry Attempts**: Max 3 attempts with exponential backoff
- **Storage**: ~2KB per queue entry

## Troubleshooting

### Email Not Sending

1. **Check Settings**
   ```python
   from django.conf import settings
   print(settings.EMAIL_BACKEND)
   print(settings.EMAIL_HOST)
   ```

2. **Check Queue Status**
   ```python
   from notifications.models import NotificationQueue
   failed = NotificationQueue.objects.filter(status='failed')
   for entry in failed:
       print(entry.error_message)
   ```

3. **Check User Settings**
   ```python
   user.notification_settings.email_notifications  # Should be True
   ```

4. **Verify Celery**
   ```bash
   celery -A config worker -l info  # Check for task execution
   ```

### SMTP Authentication Error

```python
# Test SMTP connection
from django.core.mail import send_mail
send_mail('Test', 'Message', 'from@example.com', ['to@example.com'])
```

### Template Not Found

```
TemplateDoesNotExist: notifications/assignment_new.html
```

Solution: Ensure template file exists in `backend/notifications/templates/notifications/`

## Migration

If adding new email notification types:

1. Create template: `notifications/your_type.html`
2. Add to Notification.Type choices
3. Add to service._get_default_subject()
4. Create test cases
5. Deploy and start using

## Future Enhancements

- [ ] Email template editor in admin panel
- [ ] A/B testing for subject lines
- [ ] Open rate tracking with pixel tracking
- [ ] Link click tracking
- [ ] Unsubscribe link implementation
- [ ] DKIM/SPF/DMARC configuration
- [ ] Email list segmentation
- [ ] Automated digest emails
- [ ] Reply-to email handling

## Support

For issues or questions:
1. Check Django email configuration
2. Review Celery task logs
3. Check NotificationQueue.error_message
4. Verify email template syntax
5. Test with in-memory backend first

## Related Documentation

- [Notification System](notification_service.py)
- [Celery Configuration](../config/celery_config.py)
- [Django Email Documentation](https://docs.djangoproject.com/en/5.2/topics/email/)
