# Pachca Token Validation - Usage Guide

## Overview

Validates Pachca API tokens by making a test request to `/users/me` endpoint.

## Files Created/Modified

### 1. Service Method
**File**: `backend/chat/services/pachca_service.py`

Added `validate_token()` method:
- Makes GET request to `/users/me` endpoint
- Returns `True` if token is valid (200 OK)
- Returns `False` for any error (401, 403, 500, network errors)
- Logs user ID on success
- Logs errors with status codes

### 2. Management Command
**File**: `backend/chat/management/commands/test_pachca.py`

Django management command for testing Pachca connection:
```bash
python manage.py test_pachca
```

**Note**: This command has a Twisted/OpenSSL compatibility issue with Python 3.13.
Use the standalone script instead (see below).

### 3. Standalone Test Script
**File**: `backend/test_pachca_standalone.py`

Standalone script that works without Django's full setup:
```bash
cd backend
python test_pachca_standalone.py
```

### 4. Unit Tests
**File**: `backend/tests/unit/chat/test_pachca_forum_service.py`

Added `TestPachcaServiceTokenValidation` class with 8 tests:
- `test_validate_token_success` - Valid token (200 OK)
- `test_validate_token_failure_401` - Invalid token (401 Unauthorized)
- `test_validate_token_failure_403` - Forbidden (403)
- `test_validate_token_failure_500` - Server error (500)
- `test_validate_token_network_error` - Network errors
- `test_validate_token_timeout` - Timeout errors
- `test_validate_token_not_configured` - Missing credentials
- `test_validate_token_logs_user_id` - Logging verification

## Usage Examples

### 1. Standalone Script (Recommended)

```bash
cd backend

# Without Pachca configured (expected)
python test_pachca_standalone.py
# Output:
# API Token: NOT SET
# Channel ID: NOT SET
# ⚠️ WARNING: Pachca not configured

# With test credentials (will fail validation)
PACHCA_FORUM_API_TOKEN="test_token" PACHCA_FORUM_CHANNEL_ID="999" python test_pachca_standalone.py
# Output:
# API Token: ***oken
# Channel ID: 999
# ❌ FAILED: Pachca token validation failed
# Error: 401 - {"error":"invalid_token"}

# With valid credentials (will succeed)
PACHCA_FORUM_API_TOKEN="your_real_token" PACHCA_FORUM_CHANNEL_ID="123456" python test_pachca_standalone.py
# Output:
# API Token: ***oken
# Channel ID: 123456
# ✅ SUCCESS: Pachca token is valid!
# Pachca token valid. User ID: user-12345
```

### 2. Python API Usage

```python
from chat.services.pachca_service import PachcaService

# Initialize service
service = PachcaService()

# Check if configured
if not service.is_configured():
    print("Pachca not configured")
else:
    # Validate token
    if service.validate_token():
        print("Token is valid!")
    else:
        print("Token validation failed")
```

### 3. Unit Tests

```bash
cd backend

# Run all Pachca tests
ENVIRONMENT=test python -m pytest tests/unit/chat/test_pachca_forum_service.py -v

# Run only validation tests
ENVIRONMENT=test python -m pytest tests/unit/chat/test_pachca_forum_service.py::TestPachcaServiceTokenValidation -v
```

## Environment Variables

Required for Pachca forum notifications:

```bash
PACHCA_FORUM_API_TOKEN=your_api_token_here
PACHCA_FORUM_CHANNEL_ID=123456
PACHCA_FORUM_BASE_URL=https://api.pachca.com/api/shared/v1  # Optional
```

See `.env.example` for full configuration.

## API Endpoint Used

**GET** `https://api.pachca.com/api/shared/v1/users/me`

**Headers**:
```
Authorization: Bearer {api_token}
Content-Type: application/json
```

**Response** (200 OK):
```json
{
  "data": {
    "id": "user-12345",
    "name": "Test User",
    "email": "user@example.com"
  }
}
```

**Response** (401 Unauthorized):
```json
{
  "error": "invalid_token",
  "error_description": "Access token is missing or invalid"
}
```

## Error Handling

The `validate_token()` method handles all errors gracefully:

1. **Not Configured** (no token/channel) → Returns `False`, logs warning
2. **401/403** (invalid/forbidden) → Returns `False`, logs error with status
3. **500** (server error) → Returns `False`, logs error
4. **Network errors** (timeout, connection refused) → Returns `False`, logs exception
5. **200 OK** → Returns `True`, logs user ID

All errors are logged but never raise exceptions.

## Test Results

All 8 validation tests pass:
```
tests/unit/chat/test_pachca_forum_service.py::TestPachcaServiceTokenValidation::test_validate_token_success PASSED
tests/unit/chat/test_pachca_forum_service.py::TestPachcaServiceTokenValidation::test_validate_token_failure_401 PASSED
tests/unit/chat/test_pachca_forum_service.py::TestPachcaServiceTokenValidation::test_validate_token_failure_403 PASSED
tests/unit/chat/test_pachca_forum_service.py::TestPachcaServiceTokenValidation::test_validate_token_failure_500 PASSED
tests/unit/chat/test_pachca_forum_service.py::TestPachcaServiceTokenValidation::test_validate_token_network_error PASSED
tests/unit/chat/test_pachca_forum_service.py::TestPachcaServiceTokenValidation::test_validate_token_timeout PASSED
tests/unit/chat/test_pachca_forum_service.py::TestPachcaServiceTokenValidation::test_validate_token_not_configured PASSED
tests/unit/chat/test_pachca_forum_service.py::TestPachcaServiceTokenValidation::test_validate_token_logs_user_id PASSED
```

Total test suite: 44/44 tests pass (including 8 new validation tests)

## Troubleshooting

### Management Command Error (Twisted/OpenSSL)

If `python manage.py test_pachca` fails with:
```
AttributeError: module 'lib' has no attribute 'SSL_MODE_ACCEPT_MOVING_WRITE_BUFFER'
```

**Solution**: Use the standalone script instead:
```bash
python test_pachca_standalone.py
```

This is a known compatibility issue between Twisted and Python 3.13.

### Token Validation Fails

1. Check environment variables are set correctly
2. Verify token is not expired
3. Check network connectivity
4. Review logs for specific error messages

### Missing Environment Variables

If you see `NOT SET` for token/channel:
1. Check `.env` file exists
2. Verify variables are uncommented
3. Restart application after changes
