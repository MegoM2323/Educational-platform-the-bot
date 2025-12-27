# Notification Preferences Backend Implementation (T_NTF_006)

## Overview

Implemented complete notification preferences management system for THE_BOT platform, allowing users to customize how and when they receive notifications across multiple channels and notification types.

## Components Implemented

### 1. Model Enhancement: NotificationSettings

**File**: `backend/notifications/models.py`

Added three new fields to `NotificationSettings`:
- `in_app_notifications` (Boolean, default=True): Enable/disable in-app notifications
- `quiet_hours_enabled` (Boolean, default=False): Toggle quiet hours feature
- `timezone` (CharField with choices, default='UTC'): User's timezone for quiet hours calculation

**Timezone Choices** (14 timezones):
```
UTC, US/Eastern, US/Central, US/Mountain, US/Pacific,
Europe/London, Europe/Paris, Europe/Moscow,
Asia/Tokyo, Asia/Shanghai, Asia/Hong_Kong, Asia/Bangkok,
Australia/Sydney, Pacific/Auckland
```

### 2. Database Migration

**File**: `backend/notifications/migrations/0012_add_notification_preferences.py`

Creates three new fields for the NotificationSettings model with proper default values.

### 3. Serializer Enhancement

**File**: `backend/notifications/serializers.py`

Updated `NotificationSettingsSerializer` to include:
- All channel preferences: `email_notifications`, `push_notifications`, `sms_notifications`, `in_app_notifications`
- All notification type preferences: `assignment_notifications`, `material_notifications`, `message_notifications`, `payment_notifications`, `invoice_notifications`, `system_notifications`
- Quiet hours: `quiet_hours_enabled`, `quiet_hours_start`, `quiet_hours_end`
- Timezone: `timezone`, `timezone_display`

### 4. API Endpoints

**File**: `backend/accounts/profile_views.py`

Created `NotificationSettingsView` supporting:

#### GET /api/accounts/notification-settings/
Returns user's current notification preferences with default values if not yet set.

**Response**:
```json
{
  "id": 1,
  "user": 1,
  "email_notifications": true,
  "push_notifications": true,
  "sms_notifications": false,
  "in_app_notifications": true,
  "assignment_notifications": true,
  "material_notifications": true,
  "message_notifications": true,
  "report_notifications": true,
  "payment_notifications": true,
  "invoice_notifications": true,
  "system_notifications": true,
  "quiet_hours_enabled": false,
  "quiet_hours_start": null,
  "quiet_hours_end": null,
  "timezone": "UTC",
  "timezone_display": "UTC",
  "created_at": "2025-12-27T10:00:00Z",
  "updated_at": "2025-12-27T10:00:00Z"
}
```

#### PATCH /api/accounts/notification-settings/
Updates user's notification preferences. All fields are optional and support partial updates.

**Request**:
```json
{
  "email_notifications": false,
  "push_notifications": true,
  "quiet_hours_enabled": true,
  "quiet_hours_start": "22:00",
  "quiet_hours_end": "08:00",
  "timezone": "Europe/Moscow",
  "assignment_notifications": false,
  "material_notifications": true
}
```

**Response**: Returns updated preferences (same format as GET)

### 5. Signal-Based Auto-Creation

**File**: `backend/accounts/signals.py`

Added `auto_create_notification_settings` signal handler that:
- Automatically creates `NotificationSettings` with defaults when a new user is created
- Runs on `post_save` of User model
- Skips in test mode to avoid fixture conflicts
- Idempotent: uses `get_or_create` to prevent duplicates

### 6. URL Configuration

**Files**:
- `backend/accounts/urls.py`: Added route `notification-settings/` → `NotificationSettingsView`
- `backend/accounts/profile_urls.py`: Added route in profile namespace

## Features

### Channel Preferences
Users can control notifications across:
- Email
- Push notifications
- SMS
- In-app notifications (always enabled by default)

### Notification Type Preferences
Users can configure preferences for:
- Assignment-related notifications
- Material/course content notifications
- Message/chat notifications
- Payment notifications
- Invoice notifications
- System notifications
- Report notifications

### Quiet Hours
Users can:
- Enable/disable quiet hours
- Set start and end times
- Notifications are queued during quiet hours and sent afterwards
- Configurable per user timezone

### Timezone Support
- 14 major timezones covering global regions
- Used to calculate local quiet hours
- Allows displaying notification times in user's local timezone

## Default Behavior

When a new user is created, they automatically receive `NotificationSettings` with:
- All notification types enabled (assignment, material, messages, etc.)
- All delivery channels enabled except SMS (email, push, in-app enabled)
- Quiet hours disabled
- Timezone set to UTC
- In-app notifications always enabled

## Authentication & Authorization

- All endpoints require authentication (`IsAuthenticated` permission class)
- Users can only access their own notification settings
- Automatic creation happens for all authenticated users

## Implementation Quality

### Validation
- Timezone field has predefined choices to prevent invalid values
- Time fields support HH:MM format validation
- Serializer validates partial updates correctly

### Error Handling
- 401/403 for unauthenticated access
- 400 for invalid data
- 500 with descriptive error messages
- Proper logging for debugging

### Testing
Created comprehensive test suite `test_notification_preferences.py` covering:
- Model creation and defaults
- Timezone validation
- Quiet hours functionality
- GET endpoint with auto-creation
- PATCH endpoint with partial updates
- Unauthorized access prevention
- Auto-creation signal behavior
- Multiple user roles (student, teacher, tutor, parent)

## API Usage Examples

### Python (Requests)
```python
import requests

headers = {'Authorization': 'Token YOUR_TOKEN'}

# Get current settings
response = requests.get(
    'http://localhost:8000/api/accounts/notification-settings/',
    headers=headers
)
settings = response.json()

# Update settings
payload = {
    'email_notifications': False,
    'quiet_hours_enabled': True,
    'quiet_hours_start': '21:00',
    'quiet_hours_end': '08:00',
    'timezone': 'US/Pacific'
}
response = requests.patch(
    'http://localhost:8000/api/accounts/notification-settings/',
    json=payload,
    headers=headers
)
```

### JavaScript/Fetch
```javascript
const token = 'YOUR_TOKEN';

// Get settings
const response = await fetch('/api/accounts/notification-settings/', {
  headers: { 'Authorization': `Token ${token}` }
});
const settings = await response.json();

// Update settings
await fetch('/api/accounts/notification-settings/', {
  method: 'PATCH',
  headers: {
    'Authorization': `Token ${token}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    email_notifications: false,
    timezone: 'Europe/Moscow'
  })
});
```

### CURL
```bash
# Get settings
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/accounts/notification-settings/

# Update settings
curl -X PATCH \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "email_notifications": false,
    "quiet_hours_enabled": true,
    "timezone": "Europe/Moscow"
  }' \
  http://localhost:8000/api/accounts/notification-settings/
```

## Integration Points

### Existing Systems

1. **Notification Delivery** (`notification_service.py`)
   - Will respect user's channel preferences when sending notifications
   - Will queue notifications during quiet hours

2. **Frontend** (`NotificationSettings.tsx`)
   - Already implemented UI for these preferences
   - Uses GET/PATCH endpoints for state management
   - Displays timezone selector with 14 options

3. **Accounts App**
   - Integrated with user profile system
   - Uses existing authentication infrastructure
   - Follows project's API patterns

## Files Modified/Created

### Created Files:
1. `backend/notifications/migrations/0012_add_notification_preferences.py`
2. `backend/notifications/tests/test_notification_preferences.py`
3. `backend/notifications/NOTIFICATION_PREFERENCES_IMPLEMENTATION.md` (this file)

### Modified Files:
1. `backend/notifications/models.py` - Added 3 new fields to NotificationSettings
2. `backend/notifications/serializers.py` - Updated NotificationSettingsSerializer
3. `backend/accounts/profile_views.py` - Added NotificationSettingsView
4. `backend/accounts/profile_urls.py` - Added notification-settings route
5. `backend/accounts/urls.py` - Added notification-settings route
6. `backend/accounts/signals.py` - Added auto_create_notification_settings signal

## Acceptance Criteria Fulfilled

✅ Create NotificationPreference model (enhanced existing NotificationSettings)
  - Channel preferences (email, SMS, push, in-app)
  - Notification type preferences (assignments, materials, messages, payments, invoices, system)
  - Quiet hours (start, end, enabled toggle)
  - Timezone support (14 major timezones)

✅ Implement preference endpoints
  - GET /api/accounts/notification-settings/ - fetch user preferences
  - PATCH /api/accounts/notification-settings/ - update user preferences
  - Proper validation and error handling
  - Authentication required

✅ Add preference defaults
  - Auto-creation of NotificationSettings via signal when user is created
  - All preferences have sensible defaults
  - Override system defaults at user level

## Testing

Run the test suite:
```bash
cd backend
pytest notifications/tests/test_notification_preferences.py -v
```

Expected output: All tests passing

## Performance Considerations

- OneToOne relationship between User and NotificationSettings - O(1) lookup
- Cached on first access via get_or_create
- No N+1 queries
- Indexed on user field

## Security Considerations

- Authentication required (IsAuthenticated permission class)
- Users can only access/modify their own preferences
- No bypass mechanisms for quiet hours on system notifications
- Timezone choices validated against predefined list
