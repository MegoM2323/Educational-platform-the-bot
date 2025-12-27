# Configuration Management - Practical Examples

## Table of Contents
1. [Service Layer Usage](#service-layer-usage)
2. [REST API Usage](#rest-api-usage)
3. [Admin Panel Usage](#admin-panel-usage)
4. [Integration Examples](#integration-examples)
5. [Common Scenarios](#common-scenarios)

## Service Layer Usage

### Getting Configuration Values

```python
from core.config import ConfigurationService

# Get a single configuration
assignments_enabled = ConfigurationService.get('feature_flags.assignments_enabled')
# Returns: True (default) or False (if custom value set)

# Get with custom default (if key doesn't exist)
custom_value = ConfigurationService.get('nonexistent.key', default='my_default')
# Returns: 'my_default' if key not found

# Get all configurations
all_configs = ConfigurationService.get_all()
# Returns: dict with all keys and their current values
# Example: {
#     'feature_flags.assignments_enabled': True,
#     'feature_flags.payments_enabled': True,
#     'rate_limit.api_requests_per_minute': 60,
#     ...
# }

# Get configurations by group
feature_flags = ConfigurationService.get_group('feature_flags')
# Returns: {
#     'feature_flags.assignments_enabled': True,
#     'feature_flags.payments_enabled': True,
#     'feature_flags.notifications_enabled': True,
#     'feature_flags.chat_enabled': True,
#     'feature_flags.knowledge_graph_enabled': True,
# }
```

### Setting Configuration Values

```python
# Simple set
ConfigurationService.set('feature_flags.assignments_enabled', False, user=request.user)
# Stores value, invalidates cache, logs to audit

# Type validation happens automatically
try:
    ConfigurationService.set(
        'feature_flags.assignments_enabled',
        'false'  # Wrong type - should be boolean
    )
except ValueError as e:
    print(f"Error: {e}")  # "Error: Expected boolean, got str"

# Set multiple configurations at once
configs = {
    'feature_flags.assignments_enabled': False,
    'feature_flags.payments_enabled': False,
    'rate_limit.api_requests_per_minute': 100,
}
ConfigurationService.set_multiple(configs, user=request.user)
# All set atomically (same transaction)
# All changes audited together
```

### Validation

```python
# Validate without saving
try:
    ConfigurationService.validate('feature_flags.assignments_enabled', True)
    # No exception - validation passed
except ValueError as e:
    # Validation failed
    print(f"Invalid: {e}")

# Check if key exists
from core.config import DEFAULT_CONFIGURATIONS
if 'my.config.key' in DEFAULT_CONFIGURATIONS:
    # Key exists
    pass
else:
    # Key doesn't exist
    pass
```

### Reset Operations

```python
# Reset all configurations to defaults
ConfigurationService.reset(user=request.user)

# Reset a specific group
ConfigurationService.reset_key('feature_flags.assignments_enabled', user=request.user)

# Reset multiple keys
for key in ['feature_flags.assignments_enabled', 'feature_flags.payments_enabled']:
    ConfigurationService.reset_key(key, user=request.user)
```

### Getting Schema

```python
# Get configuration schema
schema = ConfigurationService.get_schema()

# Each schema item includes:
schema_item = {
    'type': 'boolean',
    'description': 'Enable/disable assignment feature',
    'group': 'feature_flags',
    'default': True,
    'current': False,  # Current value (may be different from default)
}

# Access specific config schema
assignments_schema = ConfigurationService.get_schema()['feature_flags.assignments_enabled']
print(f"Type: {assignments_schema['type']}")
print(f"Default: {assignments_schema['default']}")
print(f"Current: {assignments_schema['current']}")
print(f"Description: {assignments_schema['description']}")
```

## REST API Usage

### List All Configurations

```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/admin/config/
```

Response:
```json
{
  "count": 28,
  "results": [
    {
      "key": "email.from_address",
      "value": "noreply@thebot.com",
      "value_type": "string",
      "description": "Email from address",
      "group": "email",
      "default": "noreply@thebot.com"
    },
    {
      "key": "email.smtp_host",
      "value": "smtp.gmail.com",
      "value_type": "string",
      "description": "SMTP server hostname",
      "group": "email",
      "default": "smtp.gmail.com"
    },
    ...
  ]
}
```

### Get Single Configuration

```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/admin/config/rate_limit.api_requests_per_minute/
```

Response:
```json
{
  "key": "rate_limit.api_requests_per_minute",
  "value": 60,
  "value_type": "integer",
  "description": "Maximum API requests per minute",
  "group": "rate_limit",
  "default": 60
}
```

### Update Single Configuration

```bash
curl -X PUT \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": 100}' \
  http://localhost:8000/api/admin/config/rate_limit.api_requests_per_minute/
```

Response:
```json
{
  "key": "rate_limit.api_requests_per_minute",
  "value": 100,
  "message": "Configuration updated successfully"
}
```

### Bulk Update Multiple Configurations

```bash
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configurations": {
      "feature_flags.assignments_enabled": false,
      "feature_flags.payments_enabled": false,
      "rate_limit.api_requests_per_minute": 100,
      "email.smtp_port": 465
    }
  }' \
  http://localhost:8000/api/admin/config/bulk_update/
```

Response:
```json
{
  "count": 4,
  "message": "Configurations updated successfully",
  "updated": [
    "feature_flags.assignments_enabled",
    "feature_flags.payments_enabled",
    "rate_limit.api_requests_per_minute",
    "email.smtp_port"
  ]
}
```

### Reset All Configurations

```bash
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reset_type": "all"}' \
  http://localhost:8000/api/admin/config/reset/
```

Response:
```json
{
  "message": "All configurations reset to defaults",
  "reset_type": "all"
}
```

### Reset Specific Group

```bash
curl -X POST \
  -H "Authorization: Token YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "reset_type": "group",
    "group": "feature_flags"
  }' \
  http://localhost:8000/api/admin/config/reset/
```

Response:
```json
{
  "message": "Group \"feature_flags\" reset to defaults",
  "reset_type": "group"
}
```

### Get Configuration Schema

```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  http://localhost:8000/api/admin/config/schema/
```

Response:
```json
{
  "total": 28,
  "groups": {
    "feature_flags": [
      {
        "key": "feature_flags.assignments_enabled",
        "type": "boolean",
        "description": "Enable/disable assignment feature",
        "group": "feature_flags",
        "default": true,
        "current": true
      },
      ...
    ],
    "rate_limit": [...],
    "email": [...],
    ...
  },
  "schema": {
    "feature_flags.assignments_enabled": {...},
    "rate_limit.api_requests_per_minute": {...},
    ...
  }
}
```

### Get Configurations by Group

```bash
curl -H "Authorization: Token YOUR_TOKEN" \
  "http://localhost:8000/api/admin/config/group/?group=security"
```

Response:
```json
{
  "group": "security",
  "count": 7,
  "results": [
    {
      "key": "security.enforce_https",
      "value": false,
      "value_type": "boolean",
      "description": "Enforce HTTPS connections",
      "group": "security",
      "default": false
    },
    {
      "key": "security.password_min_length",
      "value": 12,
      "value_type": "integer",
      "description": "Minimum password length",
      "group": "security",
      "default": 12
    },
    ...
  ]
}
```

## Admin Panel Usage

### Access Configuration Admin

1. Go to: http://localhost:8000/admin/
2. Login with admin credentials
3. Navigate to: **Core → Configurations**

### List Configurations

The configuration list shows:
- **Key**: Configuration identifier (e.g., "feature_flags.assignments_enabled")
- **Value**: Current value (truncated if long)
- **Type**: Color-coded type badge (boolean, integer, string, etc.)
- **Group**: Configuration group (feature_flags, rate_limit, etc.)
- **Updated By**: User who last changed it
- **Updated At**: When it was last changed

### Filter Configurations

Click **Filters** on the right to filter by:
- **Group**: Select group (feature_flags, rate_limit, email, etc.)
- **Type**: Select type (string, integer, boolean, list, JSON)
- **Updated At**: Date range
- **Updated By**: User who made changes

### Search Configurations

Use the search box at the top to search for:
- Configuration key
- Description
- Group name

Example searches:
- "assignments" → finds `feature_flags.assignments_enabled`
- "email" → finds all email configurations
- "password" → finds all security configurations

### Edit Configuration

1. Click on a configuration key in the list
2. The detail page shows:
   - **Key** (read-only)
   - **Group** (read-only)
   - **Description** (read-only)
   - **Value** (formatted, read-only in view mode)
   - **Type** (read-only)
   - **Created At** (read-only)
   - **Updated At** (read-only)
   - **Updated By** (read-only)

3. Click **Edit** button
4. Change the value
5. Click **Save**

**Note:** Changes are automatically audited with the admin user and timestamp

### Delete Configuration

1. Select configuration checkbox(es)
2. Select "Delete selected configurations" from actions dropdown
3. Click **Go**
4. Confirm deletion

**Note:** Only superusers can delete configurations

## Integration Examples

### Feature Toggle in Views

```python
from django.http import JsonResponse
from core.config import ConfigurationService

def get_assignments(request):
    # Check if assignments are enabled
    if not ConfigurationService.get('feature_flags.assignments_enabled'):
        return JsonResponse({'error': 'Assignments feature is disabled'}, status=403)

    # Get assignments...
    assignments = Assignment.objects.all()
    return JsonResponse({'assignments': [...]})
```

### API Rate Limiting

```python
from rest_framework import viewsets
from core.config import ConfigurationService

class MyViewSet(viewsets.ViewSet):
    def list(self, request):
        # Get rate limit from configuration
        rate_limit = ConfigurationService.get('rate_limit.api_requests_per_minute')

        # Apply rate limiting logic
        # (your rate limiting implementation here)

        return Response({...})
```

### Email Configuration

```python
from django.core.mail import send_mail
from core.config import ConfigurationService

def send_email(to_email, subject, message):
    if not ConfigurationService.get('notification.email_enabled'):
        print("Email notifications disabled")
        return False

    # Use configured SMTP settings
    smtp_host = ConfigurationService.get('email.smtp_host')
    smtp_port = ConfigurationService.get('email.smtp_port')
    from_address = ConfigurationService.get('email.from_address')

    # Send email with configured settings
    # (your email sending implementation here)

    return True
```

### Payment Processing

```python
from core.config import ConfigurationService

def process_payment(request, invoice):
    if not ConfigurationService.get('feature_flags.payments_enabled'):
        return Response({'error': 'Payments disabled'}, status=403)

    if not ConfigurationService.get('payment.yookassa_enabled'):
        return Response({'error': 'YooKassa not configured'}, status=400)

    shop_id = ConfigurationService.get('payment.yookassa_shop_id')

    # Process payment with YooKassa
    # (your payment processing here)
```

### UI Customization

```python
from core.config import ConfigurationService

def get_ui_config(request):
    return Response({
        'company_name': ConfigurationService.get('ui.company_name'),
        'logo_url': ConfigurationService.get('ui.logo_url'),
        'primary_color': ConfigurationService.get('ui.primary_color'),
        'theme': ConfigurationService.get('ui.theme'),
    })
```

## Common Scenarios

### Scenario 1: Disable Feature During Maintenance

```python
from core.config import ConfigurationService
from django.contrib.auth.models import User

admin_user = User.objects.filter(is_superuser=True).first()

# Disable assignments
ConfigurationService.set(
    'feature_flags.assignments_enabled',
    False,
    user=admin_user
)

# Disable payments
ConfigurationService.set(
    'feature_flags.payments_enabled',
    False,
    user=admin_user
)

print("Features disabled for maintenance")
```

### Scenario 2: Adjust Rate Limits for Load Testing

```bash
curl -X POST \
  -H "Authorization: Token ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "configurations": {
      "rate_limit.api_requests_per_minute": 1000,
      "rate_limit.login_attempts_per_minute": 50
    }
  }' \
  http://localhost:8000/api/admin/config/bulk_update/
```

### Scenario 3: Update Email Configuration

```bash
curl -X PUT \
  -H "Authorization: Token ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "smtp.sendgrid.net"}' \
  http://localhost:8000/api/admin/config/email.smtp_host/

curl -X PUT \
  -H "Authorization: Token ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": 587}' \
  http://localhost:8000/api/admin/config/email.smtp_port/

curl -X PUT \
  -H "Authorization: Token ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"value": "noreply@sendgrid.com"}' \
  http://localhost:8000/api/admin/config/email.from_address/
```

### Scenario 4: Check Current Configuration

```python
from core.config import ConfigurationService

# Print all current settings
schema = ConfigurationService.get_schema()
for group in ['feature_flags', 'rate_limit', 'security']:
    print(f"\n=== {group.upper()} ===")
    for key, config in schema.items():
        if config['group'] == group:
            print(f"{key}: {config['current']} (default: {config['default']})")
```

Output:
```
=== FEATURE_FLAGS ===
feature_flags.assignments_enabled: False (default: True)
feature_flags.payments_enabled: True (default: True)
feature_flags.notifications_enabled: True (default: True)
feature_flags.chat_enabled: True (default: True)
feature_flags.knowledge_graph_enabled: True (default: True)

=== RATE_LIMIT ===
rate_limit.api_requests_per_minute: 100 (default: 60)
rate_limit.login_attempts_per_minute: 5 (default: 5)
rate_limit.brute_force_lockout_minutes: 30 (default: 30)

=== SECURITY ===
security.password_min_length: 12 (default: 12)
security.password_require_uppercase: True (default: True)
...
```

### Scenario 5: Audit Trail Analysis

```python
from core.models import AuditLog

# Get all configuration changes
config_changes = AuditLog.objects.filter(
    target_type='configuration'
).order_by('-timestamp')

# Print recent changes
for log in config_changes[:10]:
    metadata = log.metadata
    print(f"{log.timestamp}: {log.user} changed {metadata['key']}")
    print(f"  Old: {metadata['old_value']}")
    print(f"  New: {metadata['new_value']}")
    print()
```

## Tips & Tricks

### Caching Performance

```python
# This is cached - very fast (sub-millisecond)
value = ConfigurationService.get('feature_flags.assignments_enabled')

# All configurations cached together - fast bulk operation
all_configs = ConfigurationService.get_all()

# Group retrieval is not cached but fast
group_configs = ConfigurationService.get_group('feature_flags')
```

### Type Hints

```python
from typing import Any, Dict
from core.config import ConfigurationService

def get_feature_flag(key: str) -> bool:
    """Get boolean feature flag."""
    value = ConfigurationService.get(key, default=False)
    return bool(value)

def get_rate_limit(key: str) -> int:
    """Get integer rate limit."""
    value = ConfigurationService.get(key, default=60)
    return int(value)
```

### Error Handling

```python
from core.config import ConfigurationService

def safe_get_config(key: str, default: Any = None) -> Any:
    """Safely get configuration with error handling."""
    try:
        return ConfigurationService.get(key, default=default)
    except Exception as e:
        logger.error(f"Error getting configuration {key}: {e}")
        return default

# Usage
api_limit = safe_get_config('rate_limit.api_requests_per_minute', 60)
```
