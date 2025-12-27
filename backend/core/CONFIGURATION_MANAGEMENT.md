# Configuration Management System (T_ADM_005)

## Overview

The Configuration Management System provides dynamic system configuration management without requiring application restart. It supports feature flags, rate limits, email settings, payment settings, and UI customization.

## Features

### 1. Dynamic Configuration Management
- Get/set configurations at runtime
- Automatic cache invalidation (Redis, 1-hour TTL)
- Default values for all configuration keys
- Type validation (string, integer, boolean, list, JSON)
- Audit logging for all changes

### 2. Configuration Groups
- **feature_flags**: Enable/disable features
- **rate_limit**: API throttling and login protection
- **email**: SMTP settings
- **payment**: Payment processing configuration
- **notification**: Email, SMS, push notifications
- **ui**: Application branding (colors, logo, company name)
- **security**: Password policy, session timeout

### 3. In-Memory Caching
- Redis-backed caching with 1-hour TTL
- Automatic cache invalidation on updates
- Lazy loading from defaults if not in database

### 4. Admin Panel Integration
- View/edit configurations in Django admin
- Color-coded type badges
- Formatted value display
- Audit trail (who changed what and when)
- Bulk operations

### 5. REST API
- GET /api/admin/config/ - List all configurations
- GET /api/admin/config/{key}/ - Get single configuration
- PUT /api/admin/config/{key}/ - Update configuration
- POST /api/admin/config/bulk_update/ - Update multiple
- POST /api/admin/config/reset/ - Reset to defaults
- GET /api/admin/config/schema/ - Get available keys and types
- GET /api/admin/config/group/?group=feature_flags - Get group

## Usage

### In Code

```python
from core.config import ConfigurationService

# Get configuration (cached, falls back to default)
assignments_enabled = ConfigurationService.get('feature_flags.assignments_enabled')

# Get all configurations
all_configs = ConfigurationService.get_all()

# Get configurations by group
feature_flags = ConfigurationService.get_group('feature_flags')

# Set configuration (invalidates cache, logs change)
ConfigurationService.set(
    'feature_flags.assignments_enabled',
    False,
    user=request.user
)

# Set multiple
ConfigurationService.set_multiple({
    'feature_flags.assignments_enabled': False,
    'rate_limit.api_requests_per_minute': 100,
}, user=request.user)

# Reset to defaults
ConfigurationService.reset(user=request.user)

# Reset specific key
ConfigurationService.reset_key('feature_flags.assignments_enabled', user=request.user)

# Validate without saving
ConfigurationService.validate('feature_flags.assignments_enabled', True)

# Get schema
schema = ConfigurationService.get_schema()
```

### REST API

**Get all configurations**
```bash
curl -H "Authorization: Token xxx" \
  http://localhost:8000/api/admin/config/
```

Response:
```json
{
  "count": 32,
  "results": [
    {
      "key": "feature_flags.assignments_enabled",
      "value": true,
      "value_type": "boolean",
      "description": "Enable/disable assignment feature",
      "group": "feature_flags",
      "default": true
    }
  ]
}
```

**Get single configuration**
```bash
curl -H "Authorization: Token xxx" \
  http://localhost:8000/api/admin/config/feature_flags.assignments_enabled/
```

**Update configuration**
```bash
curl -X PUT \
  -H "Authorization: Token xxx" \
  -H "Content-Type: application/json" \
  -d '{"value": false}' \
  http://localhost:8000/api/admin/config/feature_flags.assignments_enabled/
```

**Bulk update**
```bash
curl -X POST \
  -H "Authorization: Token xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "configurations": {
      "feature_flags.assignments_enabled": false,
      "rate_limit.api_requests_per_minute": 100
    }
  }' \
  http://localhost:8000/api/admin/config/bulk_update/
```

**Reset to defaults**
```bash
curl -X POST \
  -H "Authorization: Token xxx" \
  -H "Content-Type: application/json" \
  -d '{"reset_type": "all"}' \
  http://localhost:8000/api/admin/config/reset/
```

**Reset group**
```bash
curl -X POST \
  -H "Authorization: Token xxx" \
  -H "Content-Type: application/json" \
  -d '{
    "reset_type": "group",
    "group": "feature_flags"
  }' \
  http://localhost:8000/api/admin/config/reset/
```

**Get schema**
```bash
curl -H "Authorization: Token xxx" \
  http://localhost:8000/api/admin/config/schema/
```

**Get group**
```bash
curl -H "Authorization: Token xxx" \
  "http://localhost:8000/api/admin/config/group/?group=feature_flags"
```

## Default Configurations

### Feature Flags
- `feature_flags.assignments_enabled` (boolean, default: true)
- `feature_flags.payments_enabled` (boolean, default: true)
- `feature_flags.notifications_enabled` (boolean, default: true)
- `feature_flags.chat_enabled` (boolean, default: true)
- `feature_flags.knowledge_graph_enabled` (boolean, default: true)

### Rate Limits
- `rate_limit.api_requests_per_minute` (integer, default: 60)
- `rate_limit.login_attempts_per_minute` (integer, default: 5)
- `rate_limit.brute_force_lockout_minutes` (integer, default: 30)

### Email Settings
- `email.smtp_host` (string, default: smtp.gmail.com)
- `email.smtp_port` (integer, default: 587)
- `email.from_address` (string, default: noreply@thebot.com)
- `email.use_tls` (boolean, default: true)

### Payment Settings
- `payment.yookassa_shop_id` (string, default: "")
- `payment.yookassa_enabled` (boolean, default: false)

### Notification Settings
- `notification.email_enabled` (boolean, default: true)
- `notification.sms_enabled` (boolean, default: false)
- `notification.push_enabled` (boolean, default: false)

### UI Settings
- `ui.company_name` (string, default: "THE_BOT")
- `ui.logo_url` (string, default: "/static/logo.png")
- `ui.primary_color` (string, default: "#007bff")
- `ui.theme` (string, default: "light")

### Security Settings
- `security.password_min_length` (integer, default: 12)
- `security.password_require_uppercase` (boolean, default: true)
- `security.password_require_lowercase` (boolean, default: true)
- `security.password_require_numbers` (boolean, default: true)
- `security.password_require_special` (boolean, default: true)
- `security.session_timeout_minutes` (integer, default: 30)
- `security.enforce_https` (boolean, default: false)

## Database Model

### Configuration Model

```python
class Configuration(models.Model):
    key = CharField(unique=True)  # e.g., "feature_flags.assignments_enabled"
    value = JSONField()           # Actual value
    value_type = CharField(choices=['string', 'integer', 'boolean', 'list', 'json'])
    description = TextField()     # Human-readable description
    group = CharField(db_index=True)  # e.g., "feature_flags"
    updated_by = ForeignKey(User)  # Who made the change
    created_at = DateTimeField(auto_now_add=True)
    updated_at = DateTimeField(auto_now=True, db_index=True)
```

### Indexes
- `(group, key)` - Fast lookups by group
- `(updated_at)` - Fast queries by update time

## Caching Strategy

### Cache Keys
- `config:{key}` - Individual configuration
- `config:all` - All configurations dictionary

### TTL
- 3600 seconds (1 hour)
- Automatically invalidated on update

### Cache Fallback
1. Check Redis cache
2. Check database
3. Use default value
4. Return provided default or None

## Audit Logging

All configuration changes are logged to `AuditLog` with:
- User who made the change
- Timestamp
- Old and new values
- Configuration key
- Target type: "configuration"

### Example Audit Log Entry
```json
{
  "action": "admin_action",
  "user": "admin@test.com",
  "target_type": "configuration",
  "timestamp": "2025-12-27T10:00:00Z",
  "metadata": {
    "action": "configuration_update",
    "key": "feature_flags.assignments_enabled",
    "old_value": true,
    "new_value": false
  }
}
```

## Permissions

All configuration API endpoints require:
- Authentication (must be logged in)
- Admin permission (is_staff=True or is_superuser=True)

Returns:
- 401 Unauthorized if not authenticated
- 403 Forbidden if not admin
- 404 Not Found if key doesn't exist
- 400 Bad Request if validation fails

## Type Validation

Each configuration has a declared type. Setting an invalid type raises `ValueError`:

```python
# Valid
ConfigurationService.set('feature_flags.assignments_enabled', True)

# Invalid - raises ValueError
ConfigurationService.set('feature_flags.assignments_enabled', 'true')  # Should be bool
ConfigurationService.set('rate_limit.api_requests_per_minute', '100')  # Should be int
```

## Testing

Comprehensive tests are included in `test_configuration.py`:

```bash
# Run all configuration tests
pytest core/test_configuration.py -v

# Run specific test class
pytest core/test_configuration.py::ConfigurationServiceTests -v

# Run specific test
pytest core/test_configuration.py::ConfigurationServiceTests::test_get_default_value -v
```

### Test Coverage
- Configuration CRUD operations
- Caching and cache invalidation
- Type validation
- Default value fallback
- Audit logging
- Permissions (admin-only)
- Configuration groups
- Bulk operations
- Reset operations
- REST API endpoints

## Admin Panel

Access configurations in Django admin:
1. Login to /admin/
2. Navigate to "Core" → "Configurations"
3. View, edit, or filter configurations
4. Changes are automatically audited

### Admin Features
- Search by key, description, or group
- Filter by group, type, or updated date
- Color-coded type badges
- Formatted value display (JSON/list pretty-printed)
- Quick actions
- Bulk delete (superuser only)

## Best Practices

### 1. Always Use ConfigurationService
```python
# Good
from core.config import ConfigurationService
value = ConfigurationService.get('feature_flags.assignments_enabled')

# Avoid direct database queries
from core.models import Configuration
config = Configuration.objects.get(key='...')  # Misses caching
```

### 2. Check Cached Values
```python
# This is cached and fast
assignments_enabled = ConfigurationService.get('feature_flags.assignments_enabled')

# Use in views
if assignments_enabled:
    # Show assignments feature
```

### 3. Log All Changes
```python
# Always pass user for audit logging
ConfigurationService.set(key, value, user=request.user)

# Check audit log later
audit_logs = AuditLog.objects.filter(target_type='configuration')
```

### 4. Validate Before Setting
```python
# Validate first
try:
    ConfigurationService.validate(key, value)
except ValueError as e:
    return Response({'error': str(e)}, status=400)

# Then set
ConfigurationService.set(key, value, user=request.user)
```

### 5. Use Defaults Carefully
```python
# Falls back to default if not set
value = ConfigurationService.get('some.key')

# Use custom default
value = ConfigurationService.get('some.key', default='my_default')
```

## Performance Considerations

### Caching Impact
- Reduces database queries by ~90%
- 1-hour cache invalidation on update
- Sub-millisecond retrieval from cache

### Database Impact
- Minimal - only read on first access
- Index on (group, key) for fast lookups
- Index on updated_at for time-based queries

### Audit Log Impact
- Separate table to avoid blocking configuration updates
- Indexed by user, timestamp, target_type for fast queries
- Consider archiving old logs monthly

## Troubleshooting

### Configuration Not Updating
1. Check permissions - user must be admin
2. Verify key exists in DEFAULT_CONFIGURATIONS
3. Check cache - may be stale (TTL: 1 hour)
4. Check audit log for errors

### Cache Issues
```python
# Manually clear cache
from django.core.cache import cache
cache.clear()

# Or specific key
from core.config import ConfigurationService
cache.delete(ConfigurationService._get_cache_key('feature_flags.assignments_enabled'))
```

### Type Validation Errors
```python
# Check expected type
from core.config import DEFAULT_CONFIGURATIONS
config_info = DEFAULT_CONFIGURATIONS['feature_flags.assignments_enabled']
print(config_info['type'])  # Output: 'boolean'

# Ensure value matches type
value = True  # Correct
value = 'true'  # Wrong - would raise ValueError
```

## Future Enhancements

- [ ] Configuration versioning (rollback support)
- [ ] Configuration diff/history view
- [ ] Configuration templates/presets
- [ ] Conditional configurations
- [ ] Configuration validation rules
- [ ] Real-time WebSocket updates
- [ ] Configuration encryption for sensitive values
- [ ] Scheduled configuration changes (at specific time)
