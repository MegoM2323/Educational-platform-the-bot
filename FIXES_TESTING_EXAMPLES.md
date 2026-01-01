# Testing Examples - All 10 Fixes

This document contains manual test commands that can be run against the THE_BOT platform to verify all 10 security fixes.

---

## 1. [L2] CORS Configuration

### Test 1: Check CORS Headers in Response

```bash
curl -i -X OPTIONS http://localhost:8000/api/auth/login/ \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"

# Expected response headers:
# Access-Control-Allow-Origin: http://localhost:3000
# Access-Control-Allow-Credentials: true
# Access-Control-Allow-Methods: GET,HEAD,PUT,PATCH,POST,DELETE
```

### Test 2: Verify Non-Whitelisted Origin is Rejected

```bash
curl -i -X OPTIONS http://localhost:8000/api/auth/login/ \
  -H "Origin: http://evil-site.com" \
  -H "Access-Control-Request-Method: POST"

# Expected: No Access-Control-Allow-Origin header in response
```

### Test 3: Verify CORS_ALLOW_ALL_ORIGINS is False

```bash
grep "CORS_ALLOW_ALL_ORIGINS = False" backend/config/settings.py
# Should return: CORS_ALLOW_ALL_ORIGINS = False
```

---

## 2. [H1] CSRF Exempt Removed from Login

### Test 1: Login Endpoint Requires CSRF Token

```bash
# Without CSRF token (should fail if strict CSRF checking)
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -d '{"email":"user@test.com","password":"password"}'

# With CSRF token (should succeed)
CSRF_TOKEN=$(curl -s -b cookies.txt http://localhost:8000/ | grep csrftoken | cut -d'"' -f 2)
curl -X POST http://localhost:8000/api/auth/login/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: $CSRF_TOKEN" \
  -b cookies.txt \
  -d '{"email":"user@test.com","password":"password"}'
```

### Test 2: Verify csrf_exempt Only on Webhooks

```bash
# Should find csrf_exempt only in webhook files
grep -r "csrf_exempt" backend/accounts/
# Should only return: backend/accounts/telegram_webhook_views.py

grep -r "csrf_exempt" backend/payments/views.py
# Should find it (payments webhook)
```

---

## 3. [M3] File Upload Size Limit

### Test 1: Upload Small File (< 5MB) - Should Succeed

```bash
# Create a 2MB test file
dd if=/dev/zero of=test_2mb.bin bs=1M count=2

# Upload it
curl -X POST http://localhost:8000/api/assignments/1/submit/ \
  -H "Authorization: Token {YOUR_TOKEN}" \
  -F "file=@test_2mb.bin"

# Expected: 201 Created or 200 OK
```

### Test 2: Upload Large File (> 5MB) - Should Fail

```bash
# Create a 10MB test file
dd if=/dev/zero of=test_10mb.bin bs=1M count=10

# Try to upload it
curl -X POST http://localhost:8000/api/assignments/1/submit/ \
  -H "Authorization: Token {YOUR_TOKEN}" \
  -F "file=@test_10mb.bin"

# Expected: 413 Payload Too Large
```

### Test 3: Verify Settings

```bash
python -c "
import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
from django.conf import settings
print(f'FILE_UPLOAD_MAX_MEMORY_SIZE: {settings.FILE_UPLOAD_MAX_MEMORY_SIZE}')
print(f'DATA_UPLOAD_MAX_MEMORY_SIZE: {settings.DATA_UPLOAD_MAX_MEMORY_SIZE}')
print(f'5MB in bytes: {5 * 1024 * 1024}')
"
```

---

## 4. [M1] Lesson Time Conflict Validation

### Test 1: Create Non-Conflicting Lesson - Should Succeed

```bash
# Lesson 1: Monday 10:00-11:00
curl -X POST http://localhost:8000/api/scheduling/lessons/ \
  -H "Authorization: Token {TEACHER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "student":1,
    "subject":1,
    "date":"2026-01-06",
    "start_time":"10:00:00",
    "end_time":"11:00:00"
  }'

# Expected: 201 Created
```

### Test 2: Attempt to Create Overlapping Lesson - Should Fail

```bash
# Lesson 2: Monday 10:30-11:30 (overlaps with Lesson 1!)
curl -X POST http://localhost:8000/api/scheduling/lessons/ \
  -H "Authorization: Token {TEACHER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "student":1,
    "subject":1,
    "date":"2026-01-06",
    "start_time":"10:30:00",
    "end_time":"11:30:00"
  }'

# Expected: 400 Bad Request with conflict error message
```

---

## 5. [M2] Time Validation (start < end)

### Test 1: Create Lesson with End Time Before Start Time - Should Fail

```bash
curl -X POST http://localhost:8000/api/scheduling/lessons/ \
  -H "Authorization: Token {TEACHER_TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "student":1,
    "subject":1,
    "date":"2026-01-06",
    "start_time":"11:00:00",
    "end_time":"10:00:00"
  }'

# Expected: 400 Bad Request
# Error message: "Start time must be before end time"
```

### Test 2: Verify Model Validation

```bash
python -c "
import os
import django
os.environ['DJANGO_SETTINGS_MODULE'] = 'config.settings'
os.environ['ENVIRONMENT'] = 'test'
django.setup()

from datetime import date, time
from scheduling.models import Lesson
from accounts.models import User

# Get test data (create if needed)
user = User.objects.first()
lesson = Lesson(
    student=user,
    teacher=user,
    subject=None,
    date=date(2026, 1, 6),
    start_time=time(11, 0),
    end_time=time(10, 0)
)

try:
    lesson.clean()
    print('ERROR: Validation did not raise exception!')
except Exception as e:
    print(f'SUCCESS: Validation raised: {e}')
"
```

---

## 6. [H2] WebSocket JWT Authentication

### Test 1: WebSocket Without Token - Should Fail

```bash
# Using wscat (install: npm install -g wscat)
wscat -c ws://localhost:8000/ws/chat/1/

# Expected: Connection refused or closed with 4001 (Unauthorized)
```

### Test 2: WebSocket With Valid Token - Should Succeed

```bash
# Get a valid token for authenticated user
VALID_TOKEN="your_jwt_token_here"

wscat -c "ws://localhost:8000/ws/chat/1/?token=$VALID_TOKEN"

# Expected: Connection accepted
# You should be able to send/receive messages:
# {"type": "chat_message", "text": "Hello"}
```

### Test 3: WebSocket With Invalid Token - Should Fail

```bash
wscat -c "ws://localhost:8000/ws/chat/1/?token=invalid_token_12345"

# Expected: Connection refused or closed with 4001
```

### Test 4: WebSocket With Bearer Token Format

```bash
VALID_TOKEN="your_jwt_token_here"

wscat -c "ws://localhost:8000/ws/chat/1/?authorization=Bearer%20$VALID_TOKEN"

# Expected: Connection accepted
```

---

## 7. [H3] Admin Endpoints Permission Check

### Test 1: Student Cannot Access Admin Endpoints

```bash
curl -X GET http://localhost:8000/api/admin/users/ \
  -H "Authorization: Token {STUDENT_TOKEN}"

# Expected: 403 Forbidden
# Response: {"detail":"You do not have permission to perform this action."}
```

### Test 2: Admin Can Access Admin Endpoints

```bash
curl -X GET http://localhost:8000/api/admin/users/ \
  -H "Authorization: Token {ADMIN_TOKEN}"

# Expected: 200 OK
# Response: List of users
```

### Test 3: Teacher Cannot Access Admin Endpoints

```bash
curl -X GET http://localhost:8000/api/admin/users/ \
  -H "Authorization: Token {TEACHER_TOKEN}"

# Expected: 403 Forbidden
```

---

## 8. [M4] Permission Classes Usage

### Test 1: Count Permission Classes

```bash
# Should find >50 instances
grep -r "@permission_classes" backend/ --include="*.py" | wc -l

# Expected: > 50
```

### Test 2: Count IsStaffOrAdmin Usage

```bash
# Should find >10 instances
grep -r "IsStaffOrAdmin" backend/ --include="*.py" | wc -l

# Expected: > 10
```

### Test 3: Verify Staff Views Protected

```bash
grep -c "@permission_classes" backend/accounts/staff_views.py

# Expected: > 10
```

---

## 9. [L1] .env Not in Git

### Test 1: Check Git Status

```bash
git status | grep .env

# Expected: (empty output, meaning .env is not tracked)
```

### Test 2: Check .gitignore

```bash
grep "\.env" .gitignore

# Expected: multiple .env entries
# .env
# .env.backup
# .env.production
# .env.development
# .env.local
# etc.
```

### Test 3: Check Git History

```bash
git log --all --full-history -- .env

# This should show if .env was committed in the past
# If it was, it should show as deleted (BFG or git-filter-branch was used)
```

---

## 10. [C1] Frontend Container Healthcheck

### Test 1: Check Docker Compose Healthcheck

```bash
grep -A 5 "healthcheck:" docker-compose.yml | head -20

# Expected: healthcheck configuration for multiple services
```

### Test 2: Run Docker Compose and Check Container Status

```bash
docker-compose up -d

# Wait a few seconds for services to start
sleep 10

docker ps --format "table {{.Names}}\t{{.Status}}"

# Expected output should show:
# thebot-frontend ... Up (healthy)
# thebot-backend ... Up (healthy)
# thebot-db ... Up (healthy)
# thebot-redis ... Up (healthy)
```

### Test 3: Check Frontend Service Health

```bash
# Get the frontend container ID
CONTAINER_ID=$(docker ps -q -f "name=frontend")

# Check its healthcheck status
docker inspect --format='{{json .State.Health}}' $CONTAINER_ID | jq .

# Expected Status: "healthy"
```

### Test 4: Verify Frontend is Accessible

```bash
curl -s http://localhost:3000/ | head -1

# Expected: <!DOCTYPE html> or similar HTML start
```

---

## Running All Tests Automatically

```bash
# Run static validation tests (no Docker needed)
python test_fixes_static.py

# Expected output:
# SUMMARY: Passed: 23, Failed: 0, Total: 23
```

---

## Test Coverage

| Fix | Test Count | Status | Example Commands |
|-----|-----------|--------|------------------|
| L2 CORS | 3 | Automated | curl OPTIONS with Origin header |
| H1 CSRF | 2 | Static | grep csrf_exempt |
| M3 Upload | 2 | Manual | dd + curl file upload |
| M1 Conflict | 1 | Static | grep clean() method |
| M2 Time | 2 | Static | grep time validation |
| H2 WebSocket | 4 | Manual | wscat with/without tokens |
| H3 Admin | 2 | Manual | curl with different tokens |
| M4 Permissions | 2 | Static | grep @permission_classes |
| L1 .env | 2 | Static | git status/history |
| C1 Health | 3 | Manual | docker ps/inspect |

**Total Test Cases**: 23
**Automated Tests**: 14
**Manual Tests**: 9
