# Critical Test Failures - THE_BOT_platform

**Generated:** 2026-01-02 19:45 UTC
**Status:** Blocking test execution

---

## Issue #1: ImportError - Model Class Renamed

**Severity:** CRITICAL
**Type:** Model Import Error
**Count:** ~4000+ test failures

### Problem
Tests reference old model class names that no longer exist or were renamed.

### Affected Modules

| Import Statement | Issue | Current Name | File |
|-----------------|-------|--------------|------|
| `from chat.models import ChatMessage` | Class renamed | `Message` | test_chat_post_endpoints.py |
| `from materials.models import Enrollment` | Class not found | `SubjectEnrollment`? | test_payments_post_endpoints.py |
| `from applications.models import Subject` | Class not found | Check materials? | test_performance_suite.py |
| `from accounts.serializers import UserMinimalSerializer` | Serializer not exported | Check export list | test_auditlog_serializer.py |

### Fixed Issues
- [x] `test_chat_post_endpoints.py` - Updated ChatMessage → Message
- [ ] `test_payments_post_endpoints.py` - Needs Enrollment resolution
- [ ] `test_performance_suite.py` - Needs Subject resolution
- [ ] `test_auditlog_serializer.py` - Needs UserMinimalSerializer export

### How to Fix
1. Find current class name: `grep -n "^class.*Name" <module>/models.py`
2. Update test import
3. Update all usages in test file
4. Run: `pytest tests/api/test_chat_post_endpoints.py -v`

---

## Issue #2: Cache Not Initialized

**Severity:** HIGH
**Type:** Configuration Error
**Count:** 14 test failures
**Error:** `NameError: name 'cache' is not defined`

### Affected Tests
```
tests/unit/config/test_throttling.py (14 failures)
- test_throttle_by_ip_address
- test_cache_key_includes_ip_for_anonymous
- test_headers_include_remaining_count
- test_headers_show_reset_time
```

### Root Cause
Test cache backend not initialized in conftest.py. Tests expect `django.core.cache.cache` to be available.

### How to Fix
Add to `backend/conftest.py`:

```python
import django.core.cache
from django.core.cache import cache

@pytest.fixture(autouse=True)
def reset_cache():
    """Reset cache before each test"""
    cache.clear()
    yield
    cache.clear()
```

Or mock in test:
```python
from unittest.mock import MagicMock
from django.core import cache

@pytest.fixture
def mock_cache():
    cache.cache = MagicMock()
    yield
```

---

## Issue #3: Pytest Markers Not Registered

**Severity:** MEDIUM
**Type:** Configuration Warning
**Count:** 4 errors
**Error:** `PytestUnknownMarkWarning: Unknown pytest.mark.cache`

### Affected Tests
```
tests/unit/advanced/test_*.py
- test_caching.py
- test_error_handling.py
- test_management_commands.py
- test_signals.py
- test_validation.py
```

### Root Cause
Custom pytest markers used but not registered in conftest.py.

### How to Fix
Add to `backend/conftest.py`:

```python
def pytest_configure(config):
    """Register custom pytest markers"""
    config.addinivalue_line(
        "markers", "cache: marks tests involving caching"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    # ... add all custom markers used in tests
```

---

## Issue #4: Django Model Constraint Syntax

**Severity:** HIGH
**Type:** Model Configuration Error
**Count:** 1 (but blocks all model loading)
**Status:** FIXED

### Problem
Django 4.2+ changed CheckConstraint API from `condition=` to `check=`.

### File
`backend/invoices/models.py:157-172`

### Fix Applied
```python
# BEFORE
models.CheckConstraint(
    condition=Q(sent_at__isnull=True) | Q(sent_at__gte=F("created_at")),
    name="check_invoice_sent_after_created",
)

# AFTER
models.CheckConstraint(
    check=Q(sent_at__isnull=True) | Q(sent_at__gte=F("created_at")),
    name="check_invoice_sent_after_created",
)
```

### Status
COMPLETED - All 3 constraints fixed in invoices/models.py

---

## Issue #5: Missing Module

**Severity:** MEDIUM
**Type:** Module Not Found
**Count:** 1 error
**Error:** `ModuleNotFoundError: No module named 'backend.tests.unit.notifications.template'`

### Affected Test
`tests/unit/notifications/test_template_service.py:6`

### Root Cause
Test tries to import local module that doesn't exist or wrong path.

### How to Check
```bash
ls -la backend/tests/unit/notifications/
# Check if template.py exists
find . -name "template*"
```

---

## Test Files Requiring Fixes

### Priority 1 (Blocking - Import Errors)

| File | Issue | Est. Fix Time |
|------|-------|---------------|
| test_chat_post_endpoints.py | ChatMessage → Message | 5 min |
| test_payments_post_endpoints.py | Enrollment not found | 10 min |
| test_scheduling_update_endpoints.py | Import errors | 10 min |
| test_performance_suite.py | Subject not found | 10 min |
| test_comprehensive_security.py | ChatMessage → Message | 5 min |
| test_auditlog_serializer.py | UserMinimalSerializer missing | 10 min |
| test_template_service.py | Module not found | 15 min |

### Priority 2 (Config Errors)

| File | Issue | Est. Fix Time |
|------|-------|---------------|
| conftest.py | Add cache fixture | 15 min |
| conftest.py | Register markers | 10 min |
| test_throttling.py | Mock cache | 20 min |

---

## Quick Fix Checklist

```
[ ] 1. Check materials/models.py exports for SubjectEnrollment
[ ] 2. Check applications/models.py for Subject class
[ ] 3. Check accounts/serializers.py for UserMinimalSerializer
[ ] 4. Add cache fixture to conftest.py
[ ] 5. Register pytest markers in conftest.py
[ ] 6. Update test_chat_post_endpoints.py imports
[ ] 7. Update test_payments_post_endpoints.py imports
[ ] 8. Update test_comprehensive_security.py imports
[ ] 9. Run pytest collection to verify: pytest --collect-only
[ ] 10. Run full test suite: pytest tests/ -v
```

---

## Verification Commands

After fixing issues, run:

```bash
# Check imports are correct
python -c "from chat.models import Message; print('OK')"

# Run single test file
pytest tests/api/test_chat_post_endpoints.py -v

# Count test errors
pytest tests/ --collect-only 2>&1 | grep "error\|ERROR" | wc -l

# Full test run
pytest tests/ -v --tb=short -x
```

---

## Model/Serializer Inventory

Need to verify these exports exist:

```python
# materials/models.py
- Subject
- Enrollment (or SubjectEnrollment?)
- Material
- ...

# applications/models.py
- Subject (or elsewhere?)

# accounts/serializers.py
- UserMinimalSerializer (or different name?)

# chat/models.py
- Message (CONFIRMED)
- ChatRoom (CONFIRMED)
```

---

**Last Updated:** 2026-01-02 19:45 UTC
**Reporter:** Claude Code QA Suite
**Next Action:** Fix Priority 1 issues (Est. 1 hour)
