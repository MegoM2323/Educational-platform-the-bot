# Report Scheduling Implementation - T_RPT_006

## Overview

Complete implementation of automatic recurring report generation and email delivery system for THE_BOT platform. The system allows teachers, tutors, and admins to create scheduled report deliveries with customizable frequencies (daily, weekly, monthly) and automatic email sending to multiple recipients.

## Components Implemented

### 1. Database Models

All models are implemented in `reports/models.py`:

#### ReportSchedule Model (lines 623-738)
Stores schedule configuration for automatic report delivery:

**Fields:**
- `report_type`: Choice field (STUDENT_REPORT, TUTOR_WEEKLY_REPORT, TEACHER_WEEKLY_REPORT)
- `frequency`: Choice field (DAILY, WEEKLY, MONTHLY)
- `day_of_week`: For weekly schedules (1=Monday, 7=Sunday)
- `day_of_month`: For monthly schedules (1-31)
- `time`: TimeField for delivery time (HH:MM format)
- `export_format`: Choice field (CSV, XLSX, PDF)
- `created_by`: ForeignKey to User
- `is_active`: Boolean flag to enable/disable schedule
- `name`: Display name for the schedule
- `last_sent`: Timestamp of last delivery
- `last_generated`: Timestamp of last generation
- `next_scheduled`: Calculated next execution time

**Indexes:**
- `(is_active, next_scheduled)` - For scheduler queries
- `(created_by, is_active)` - For user's schedules

#### ReportScheduleRecipient Model (lines 1025-1078)
Tracks recipients and their subscription status:

**Fields:**
- `schedule`: ForeignKey to ReportSchedule
- `recipient`: ForeignKey to User
- `is_subscribed`: Boolean (default: True)
- `unsubscribe_token`: Unique token for unsubscribe links
- `added_at`: Auto timestamp
- `unsubscribed_at`: When recipient unsubscribed

**Constraints:**
- Unique constraint: `(schedule, recipient)`

#### ReportScheduleExecution Model (lines 1081-1137)
Tracks execution history for monitoring and debugging:

**Fields:**
- `schedule`: ForeignKey to ReportSchedule
- `status`: Choice field (STARTED, COMPLETED, FAILED, PARTIAL)
- `total_recipients`: Count of recipients for this run
- `successful_sends`: Count of successful deliveries
- `failed_sends`: Count of failed deliveries
- `error_message`: Error details if failed
- `started_at`: Auto timestamp
- `completed_at`: When execution finished

**Properties:**
- `duration`: Property returning execution time in seconds
- `success_rate`: Property returning success percentage

### 2. Celery Tasks

All tasks in `reports/tasks.py`:

#### execute_scheduled_reports (lines 424-541)
Main periodic task that:
1. Finds all active schedules needing execution
2. Checks frequency and timing constraints
3. Prevents duplicate runs (1-hour minimum between executions)
4. Creates execution records
5. Queues send_scheduled_report tasks for each recipient
6. Updates next_scheduled timestamp

**Schedule:** Every hour (via Celery Beat)
**Return:** Execution summary with counts

#### send_scheduled_report (lines 248-421)
Individual task for sending report to one recipient:
1. Validates schedule and recipient are active
2. Generates report data based on report_type
3. Checks recipient subscription status
4. Sends email with EmailReportService
5. Implements retry logic (max 3 retries)

**Input:** schedule_id, recipient_id
**Retry:** Max 3 times with exponential backoff
**Return:** Success/failure status

#### test_email_report (lines 582-635)
Sends test email for schedule configuration:
1. Creates dummy report data
2. Renders email template
3. Sends to specified test email address
4. Logs result

**Input:** schedule_id, recipient_email
**Return:** Test status and message

#### refresh_materialized_views (lines 27-83)
Refreshes data warehouse materialized views:
- Concurrently refreshes all 4 views
- Invalidates related caches
- Logs execution times

**Schedule:** Daily at 2:00 AM UTC

#### warm_analytics_cache (lines 86-127)
Pre-populates cache before business hours:
- Caches engagement metrics
- Caches top/bottom performers
- Reduces initial load times

**Schedule:** Daily at 7:00 AM UTC

### 3. REST API Endpoints

Enhanced ViewSet in `reports/views.py` (lines 761-1027):

#### List & CRUD Operations
- `GET /api/reports/schedules/` - List user's schedules (paginated)
- `POST /api/reports/schedules/` - Create new schedule
- `GET /api/reports/schedules/{id}/` - Get schedule details with recipients
- `PATCH /api/reports/schedules/{id}/` - Update schedule
- `DELETE /api/reports/schedules/{id}/` - Delete schedule

#### Recipient Management
- `POST /api/reports/schedules/{id}/recipients/` - Add recipient
  ```json
  {"recipient_id": 123}
  ```
- `DELETE /api/reports/schedules/{id}/remove_recipient/?recipient_id=123` - Remove recipient

#### Email Management
- `POST /api/reports/schedules/{id}/test_email/` - Send test email
  ```json
  {"recipient_email": "test@example.com"}
  ```
  Returns: Task ID and acceptance status (202)

#### Monitoring
- `GET /api/reports/schedules/{id}/executions/?limit=10` - Get execution history
  ```json
  {
    "count": 25,
    "results": [
      {
        "id": 1,
        "status": "completed",
        "total_recipients": 5,
        "successful_sends": 5,
        "failed_sends": 0,
        "duration_seconds": 12,
        "success_rate_percent": 100.0
      }
    ]
  }
  ```

#### Subscription Management
- `GET /api/reports/schedules/my_subscriptions/` - Get schedules user is subscribed to
- `POST /api/reports/schedules/unsubscribe/` - Unsubscribe using token
  ```json
  {"unsubscribe_token": "abc123..."}
  ```

### 4. API Serializers

In `reports/serializers.py`:

#### ReportScheduleSerializer (lines 239-252)
Basic list/update serializer with:
- Schedule metadata
- Last execution times
- Frequency and timing info

#### ReportScheduleDetailSerializer (lines 677-704)
Enhanced retrieve serializer with:
- All schedule details
- Recipients list with subscription status
- Recent execution history (last 5)
- Active recipients count

#### ReportScheduleCreateUpdateSerializer (lines 707-739)
Create/update serializer with:
- Field validation
- Frequency-based field validation
- Weekly: requires day_of_week
- Monthly: requires day_of_month

#### ReportScheduleRecipientSerializer (lines 640-651)
Recipient tracking with:
- Recipient details (email, name)
- Subscription status
- Unsubscribe token
- Timestamps

#### ReportScheduleExecutionSerializer (lines 654-674)
Execution history tracking with:
- Schedule reference
- Status and counts
- Calculated metrics (duration, success_rate)
- Error messages

### 5. Email Integration

EmailReportService in `reports/services/email_report.py`:

**Methods:**
- `send_report_email()` - Main email sending method
- `render_email_template()` - HTML template rendering
- `export_to_csv()` - CSV generation
- `export_to_excel()` - Excel generation
- `get_report_summary()` - HTML summary for email body
- `generate_*_report_data()` - Report-specific data generation

**Features:**
- CSV/Excel file attachment
- HTML email template with styling
- Unsubscribe link in footer
- Error handling and logging

**Email Template:** `templates/emails/report_schedule_email.html`
- Professional styling with gradient header
- Report summary section
- Attachment info notice
- Unsubscribe link
- Footer with copyright

### 6. Celery Beat Configuration

Updated `core/celery_config.py` with new schedules:

```python
'execute-scheduled-reports': {
    'task': 'reports.tasks.execute_scheduled_reports',
    'schedule': crontab(minute=0),  # Every hour
}

'refresh-materialized-views': {
    'task': 'reports.tasks.refresh_materialized_views',
    'schedule': crontab(hour=2, minute=0),  # 2 AM daily
}

'warm-analytics-cache': {
    'task': 'reports.tasks.warm_analytics_cache',
    'schedule': crontab(hour=7, minute=0),  # 7 AM daily
}
```

### 7. Admin Interface

Enhanced admin in `reports/admin.py` (lines 200-242):

**Features:**
- Color-coded frequency badges (daily=green, weekly=blue, monthly=purple)
- Status badges (active=green, inactive=red)
- Filtering by frequency and status
- Search by schedule name
- Readonly fields for timestamps

## Acceptance Criteria Fulfillment

### 1. ReportSchedule Model ✅
- [x] Report type choices (STUDENT_REPORT, TUTOR_WEEKLY_REPORT, TEACHER_WEEKLY_REPORT)
- [x] Frequency choices (daily, weekly, monthly)
- [x] Recipients list (via ReportScheduleRecipient)
- [x] Next execution time field
- [x] Enabled/disabled flag (is_active)
- [x] Database indexes for performance

### 2. Celery Beat Tasks ✅
- [x] execute_scheduled_reports - Main scheduler task
- [x] send_scheduled_report - Per-recipient sending
- [x] test_email_report - Configuration testing
- [x] Periodic execution (every hour)
- [x] Check next execution time
- [x] Update next execution after delivery
- [x] Retry logic with exponential backoff

### 3. Schedule Management Endpoints ✅
- [x] POST /api/reports/schedules/ - Create schedule
- [x] GET /api/reports/schedules/ - List schedules
- [x] PATCH /api/reports/schedules/{id}/ - Update schedule
- [x] DELETE /api/reports/schedules/{id}/ - Delete schedule
- [x] POST /api/reports/schedules/{id}/recipients/ - Add recipient
- [x] DELETE /api/reports/schedules/{id}/remove_recipient/ - Remove recipient
- [x] POST /api/reports/schedules/{id}/test_email/ - Send test email
- [x] GET /api/reports/schedules/{id}/executions/ - View history

### 4. Email Integration ✅
- [x] Send report to recipients
- [x] Include download links (file attachments)
- [x] HTML template with formatting
- [x] Unsubscribe functionality
- [x] Error handling and logging
- [x] Multiple export formats (CSV, XLSX)

## File Changes Summary

### Modified Files:
1. `backend/core/celery_config.py` - Added 3 new Celery Beat tasks
2. `backend/reports/views.py` - Enhanced ReportScheduleViewSet with 6 new endpoints

### Existing Complete Files:
- `backend/reports/models.py` - All models implemented
- `backend/reports/tasks.py` - All Celery tasks implemented
- `backend/reports/serializers.py` - All serializers implemented
- `backend/reports/admin.py` - Admin configuration complete
- `backend/reports/services/email_report.py` - Email service complete
- `backend/templates/emails/report_schedule_email.html` - Template complete
- `backend/reports/test_scheduled_reports.py` - Test suite ready

## Usage Examples

### Create a Daily Schedule
```bash
curl -X POST http://localhost:8000/api/reports/schedules/ \
  -H "Authorization: Token abc123" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Daily Student Reports",
    "report_type": "student_report",
    "frequency": "daily",
    "time": "09:00",
    "export_format": "csv",
    "is_active": true
  }'
```

### Add Recipients
```bash
curl -X POST http://localhost:8000/api/reports/schedules/1/recipients/ \
  -H "Authorization: Token abc123" \
  -H "Content-Type: application/json" \
  -d '{"recipient_id": 5}'
```

### Send Test Email
```bash
curl -X POST http://localhost:8000/api/reports/schedules/1/test_email/ \
  -H "Authorization: Token abc123" \
  -H "Content-Type: application/json" \
  -d '{"recipient_email": "teacher@example.com"}'
```

### View Execution History
```bash
curl http://localhost:8000/api/reports/schedules/1/executions/?limit=5 \
  -H "Authorization: Token abc123"
```

## Architecture

### Flow Diagram
```
Celery Beat (hourly)
    ↓
execute_scheduled_reports
    ↓
For each active schedule at execution time:
    ├─ Create ReportScheduleExecution
    ├─ Get subscribed recipients
    └─ Queue send_scheduled_report for each
        ↓
    send_scheduled_report (with retry)
        ├─ Validate schedule/recipient
        ├─ Generate report data
        └─ EmailReportService.send_report_email()
            ├─ Export to CSV/Excel
            ├─ Render HTML template
            └─ Send via Django Email
```

### Data Flow
```
Teacher creates schedule
    ↓
AddReportScheduleRecipient entries
    ↓
Celery Beat triggers execute_scheduled_reports hourly
    ↓
If schedule.next_scheduled <= now:
    ├─ Create ReportScheduleExecution
    ├─ Generate reports
    ├─ Send emails with attachments
    ├─ Update schedule.last_sent and next_scheduled
    └─ Log results in ReportScheduleExecution

Recipients receive email with:
    ├─ HTML summary
    ├─ File attachment (CSV/Excel)
    └─ Unsubscribe link
```

## Testing

Test suite in `reports/test_scheduled_reports.py`:

**Test Classes:**
- ReportScheduleModelTests - Model creation and validation
- ReportScheduleRecipientTests - Recipient management
- ReportScheduleExecutionTests - Execution tracking
- ReportScheduleAPITests - API endpoints
- ScheduleValidationTests - Validation logic

**Run Tests:**
```bash
cd backend
ENVIRONMENT=test python manage.py test reports.test_scheduled_reports -v 2
```

## Performance Considerations

1. **Database Queries:**
   - Indexes on (is_active, next_scheduled) for scheduler
   - Prefetch_related for recipients to avoid N+1
   - Select_related for foreign keys

2. **Task Queue:**
   - Async execution via Celery
   - Retry logic with exponential backoff
   - Max 3 retries before failure

3. **Email Delivery:**
   - Configurable export formats
   - File attachment size limits
   - Batch unsubscribe token generation

4. **Caching:**
   - Analytics cache warmed at 7 AM
   - Materialized views refreshed at 2 AM
   - Redis for session storage

## Security Features

1. **Authentication:**
   - Token-based API authentication
   - User role-based access control

2. **Data Protection:**
   - Unique unsubscribe tokens (secrets.token_urlsafe)
   - HTTPS email links
   - SQL injection protection via ORM

3. **Rate Limiting:**
   - Hourly schedule checks (prevents duplicate runs)
   - 1-hour minimum between executions

## Deployment

### Prerequisites
1. Celery Beat scheduler running
2. Redis for task queue and caching
3. Email backend configured in Django settings
4. Database migrations applied

### Start Services
```bash
# Celery Worker
celery -A core.celery worker -l info

# Celery Beat
celery -A core.celery beat -l info

# Django with Gunicorn
gunicorn config.wsgi:application
```

### Environment Variables
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=noreply@platform.com
EMAIL_HOST_PASSWORD=xxxxx

CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Monitoring

### Via Django Admin
- View active schedules
- Check execution history
- Monitor recipient statuses
- Verify next scheduled times

### Via API
- GET /api/reports/schedules/ - List all schedules
- GET /api/reports/schedules/{id}/executions/ - View execution history

### Logs
- Check Celery worker logs for task execution
- Check Django logs for email sending
- Review ReportScheduleExecution for detailed status

## Future Enhancements

1. **Additional Report Types:**
   - Custom report building
   - Class-wide analytics
   - Parent-child progress reports

2. **Advanced Scheduling:**
   - Cron expression support
   - Timezone-aware scheduling
   - Business day only option

3. **Delivery Options:**
   - SMS delivery
   - In-platform notifications
   - Slack/Teams integration

4. **Analytics:**
   - Email open tracking
   - Click tracking on links
   - Delivery success metrics

## References

- Django Documentation: https://docs.djangoproject.com/
- Django REST Framework: https://www.django-rest-framework.org/
- Celery: https://docs.celeryproject.org/
- Django Signals: https://docs.djangoproject.com/en/stable/topics/signals/

## Status

**Completed:** December 27, 2025
**Version:** 1.0.0
**Status:** Production Ready

All requirements from T_RPT_006 are fully implemented and tested.
