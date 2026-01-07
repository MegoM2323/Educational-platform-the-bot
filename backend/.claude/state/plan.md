# 401 Unauthorized Production Login Fix

## Objective
Fix authentication failures on production by supporting multiple password hashing algorithms, email-based authentication, and extending password field limits.

## Parallel Group 1 (Independent changes)

### Task 1: Extend password field in User model
- **File:** `backend/accounts/models.py`
- **Change:** Increase `password` field from `max_length=128` to `max_length=256`
- **Reason:** Support all Django password hashing algorithms (PBKDF2, Argon2, bcrypt, scrypt produce hashes up to 256 chars)
- **Migration:** Django will auto-create migration
- **Agent:** coder

### Task 2: Add PASSWORD_HASHERS to settings
- **File:** `backend/config/settings.py`
- **Change:** Add PASSWORD_HASHERS list with all supported algorithms
- **Include:** PBKDF2_SHA256 (default), Argon2, bcrypt, scrypt
- **Reason:** Ensure backward compatibility with existing password hashes while supporting new algorithms
- **Agent:** coder

### Task 3: Create email authentication backend
- **File:** `backend/accounts/backends.py` (NEW)
- **Create:** `EmailBackend` class that authenticates by email instead of username
- **Change in settings:** Add to AUTHENTICATION_BACKENDS
- **Agent:** coder

## Parallel Group 2 (Depends on Group 1)

### Task 4: Update login_view to support email/username auth
- **File:** `backend/accounts/views.py`
- **Change:** Modify login_view to detect email vs username and authenticate accordingly
- **Add:** Debug logging for auth issues
- **Depends on:** Task 3 (email backend must exist first)
- **Agent:** coder

## Sequential (Testing)

### Task 5: Test email/username authentication
- **File:** `backend/accounts/tests/test_auth.py`
- **Agent:** tester
- **Scope:** 
  - Login with email
  - Login with username
  - Login with invalid credentials
  - Password hash verification

---

## Implementation Status
- [x] Task 1: Extend password field (DONE)
- [x] Task 2: Add PASSWORD_HASHERS (DONE)
- [x] Task 3: Create email backend (DONE)
- [x] Task 4: Update login_view (DONE)
- [x] Task 5: Test authentication (VERIFIED)

