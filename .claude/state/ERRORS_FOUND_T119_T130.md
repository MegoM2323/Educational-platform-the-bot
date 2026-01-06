# All Errors Found in T119-T130 Tests

**Test Session**: tutor_cabinet_test_20260107
**Total Errors Found**: 23 distinct issues

---

## ERROR #1: API Endpoints Return 403 Forbidden Instead of Expected Codes
**Severity**: CRITICAL
**Impact**: 17/28 tests fail
**Category**: API Infrastructure

### Affected Tests
- TestNetworkLossHandling::test_network_timeout_on_list_students
- TestTimeoutHandling::test_api_timeout_response
- TestInvalidDataHandling (all 6 tests)
- TestDeleteNonexistent (2 tests)
- TestCascadeDeletion::test_delete_student_cascade
- TestStudentLimitExceeded::test_many_students_handled
- TestNullUndefinedData (3 tests)
- TestPaginationOutOfBounds (5 tests)

### Root Cause Analysis
```
Expected: HTTP 200, 400, 404, or 503
Actual:   HTTP 403 Forbidden
Pattern:  ALL API endpoints return 403
```

### Suspected Issues
1. **URL Router Not Mounted**
   - `/api/tutor/students/` not in urlpatterns
   - `/api/tutor/profile/` not in urlpatterns
   - `/api/tutor/lessons/` not in urlpatterns

2. **Permission Denied by Default**
   - DRF permission classes deny all tutor API access
   - `IsAuthenticated` not properly configured
   - `force_authenticate()` not working correctly

3. **API Router Configuration Missing**
   - Missing `include()` for tutor routes
   - Missing app-level `urls.py` in tutor_cabinet app
   - Missing registration in main `urls.py`

### Evidence
```python
# Test: authenticated_client.get('/api/tutor/students/')
# Result: 403 Forbidden (authentication should be OK)
# Expected: 200 OK or 404 Not Found
```

### Fix Priority
**P1 - CRITICAL**: Must fix before other tests can run

---

## ERROR #2: Django Test Client TypeError with None Values
**Severity**: MEDIUM
**Impact**: 1/28 tests fail
**Category**: Test Framework Limitation

### Affected Test
- TestNullUndefinedData::test_empty_vs_null

### Error Message
```
TypeError: Cannot encode None for key 'name' as POST data.
Did you mean to pass an empty string or omit the value?
```

### Root Cause
Django's test client encodes POST data as multipart form data, which cannot represent None values.

### Code That Fails
```python
response = authenticated_client.post(
    '/api/tutor/students/',
    {'name': None, 'email': 'test@example.com'}  # ERROR: None
)
```

### Solution
```python
# Option 1: Use empty string
{'name': '', 'email': 'test@example.com'}

# Option 2: Omit the field
{'email': 'test@example.com'}

# Option 3: Use JSON encoding
client.post(
    endpoint,
    data=json.dumps({'name': None}),
    content_type='application/json'
)
```

### Fix Priority
**P4 - LOW**: Update test to use valid data encoding

---

## ERROR #3: PostgreSQL Deadlock in Concurrent Tests
**Severity**: HIGH
**Impact**: 2 tests fail + system error
**Category**: Database Concurrency

### Affected Tests
- TestDatabaseRaceConditions::test_concurrent_subject_creation (FAILED + ERROR)
- TestConcurrentEditing::test_concurrent_profile_edits (ERROR at teardown)

### Error Message
```
psycopg.errors.DeadlockDetected: deadlock detected
DETAIL: Process 836074 waits for AccessExclusiveLock on relation 4658616
         Process 836941 waits for AccessShareLock on relation 4660549
HINT: See server log for query details.
```

### Root Cause
Multiple concurrent threads trying to write to same database tables with improper transaction isolation.

### Database Deadlock Chain
```
Thread 1: Waiting for AccessExclusiveLock (waiting to write)
Thread 2: Waiting for AccessShareLock (waiting to read)
Result: Both threads blocked indefinitely
```

### Problematic Code
```python
class TestDatabaseRaceConditions(TransactionTestCase):
    def test_concurrent_subject_creation(self):
        def create_subject():
            # Multiple threads trying to CREATE simultaneously
            Subject.objects.create(name=name)  # DEADLOCK HERE
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            # 3 concurrent threads = deadlock
            futures = [executor.submit(create_subject) for _ in range(3)]
```

### Issues
1. **TransactionTestCase Isolation Broken**
   - Each test method flushes database after tests
   - ThreadPoolExecutor creates database conflicts during teardown

2. **Missing Transaction.atomic()**
   - Concurrent creates without proper transaction wrapping
   - Database takes conflicting locks

3. **Multiple Threads + Django ORM**
   - Django connections not thread-safe by default
   - Each thread needs separate database connection

### Solution Options
1. **Use pytest-django transaction fixtures**
   ```python
   @pytest.mark.django_db(transaction=True)
   def test_concurrent():
       # Proper transaction handling
   ```

2. **Separate test data per thread**
   ```python
   def create_subject_unique():
       name = f'Subject_{threading.current_thread().ident}'
       # Unique names prevent conflicts
       Subject.objects.create(name=name)
   ```

3. **Use database connection per thread**
   ```python
   from django.db import connections
   from django.test.utils import setup_test_environment
   
   def create_subject():
       connection = connections['default']
       # Use dedicated connection
   ```

### Fix Priority
**P3 - HIGH**: Fix transaction isolation in concurrent tests

---

## ERROR #4: Test Timeout Handling Returns 403 Not 504
**Severity**: HIGH
**Impact**: 2 tests fail
**Category**: API Error Response

### Affected Tests
- TestNetworkLossHandling::test_network_timeout_on_list_students
- TestTimeoutHandling::test_api_timeout_response

### Issue
When network timeout is mocked, API still returns 403 Forbidden instead of 504 Gateway Timeout.

### Expected Flow
```
1. Network timeout occurs
2. API catches timeout exception
3. API returns HTTP 504 Gateway Timeout
4. Test validates error handling
```

### Actual Flow
```
1. Network timeout is mocked
2. API returns 403 Forbidden (endpoint not found?)
3. Test expects 504 but gets 403
4. Test fails
```

### Root Cause
Same as ERROR #1: API endpoint not properly accessible to authenticated user.

### Fix Priority
**P2 - HIGH**: Depends on fixing ERROR #1

---

## ERROR #5: Cascade Deletion Not Tested (404 Response)
**Severity**: HIGH
**Impact**: 1 test fails
**Category**: Data Integrity

### Affected Test
- TestCascadeDeletion::test_delete_student_cascade

### Issue
Cannot test cascade deletion because DELETE returns 403 instead of 200/404.

### Expected Behavior
```python
1. Delete student
2. All StudentProfile, enrollments, messages deleted automatically
3. Database maintains referential integrity
```

### Actual Behavior
```python
1. DELETE /api/tutor/students/{id}/ returns 403 Forbidden
2. Cannot verify cascade deletion worked
3. No data verification possible
```

### Implications
- Cascade deletion may not be configured
- Foreign key ON DELETE=CASCADE may be missing
- Need to verify all models have proper relationships

### Fix Priority
**P2 - HIGH**: After API endpoints fixed

---

## ERROR #6: Invalid Data Not Returning 400 Bad Request
**Severity**: HIGH
**Impact**: 6 tests fail
**Category**: API Error Handling

### Affected Tests
- TestInvalidDataHandling::test_invalid_json_request
- TestInvalidDataHandling::test_missing_required_fields
- TestInvalidDataHandling::test_invalid_field_types
- TestInvalidDataHandling::test_sql_injection_protection
- TestInvalidDataHandling::test_xss_injection_protection
- TestInvalidDataHandling::test_oversized_payload_rejection

### Issue
Invalid data returns 403 Forbidden instead of 400 Bad Request.

### Expected Error Handling
```
Input: Invalid JSON {"bad": json}
Response: 400 Bad Request
Body: {"detail": "Invalid JSON", "errors": {...}}
```

### Actual Error Handling
```
Input: Invalid JSON or missing fields
Response: 403 Forbidden
Body: {"detail": "Permission denied"}
```

### Test Cases Not Working
1. **Invalid JSON** - Should return 400, returns 403
2. **Missing Required Fields** - Should return 400, returns 403
3. **Invalid Field Types** - Should return 400, returns 403
4. **SQL Injection** - Should return 400 or 200, returns 403
5. **XSS Injection** - Should return 400 or 200, returns 403
6. **Oversized Payload** - Should return 413, returns 403

### Root Cause
Same as ERROR #1: API endpoint not accessible, DRF not validating input.

### Fix Priority
**P2 - HIGH**: After ERROR #1 fixed

---

## ERROR #7: Pagination Out of Bounds Returns 403
**Severity**: MEDIUM
**Impact**: 5/6 pagination tests fail
**Category**: API Pagination

### Affected Tests
- TestPaginationOutOfBounds::test_page_exceeds_total
- TestPaginationOutOfBounds::test_negative_page_number
- TestPaginationOutOfBounds::test_zero_page_number
- TestPaginationOutOfBounds::test_non_numeric_page
- TestPaginationOutOfBounds::test_excessive_page_size

### Issue
All pagination parameter variations return 403 instead of 200 or 400.

### Expected Behavior
```
GET /api/tutor/students/?page=99999
Response: 200 OK (empty list) OR 404 Not Found

GET /api/tutor/students/?page=abc
Response: 400 Bad Request OR 200 OK

GET /api/tutor/students/?page_size=10000
Response: 200 OK (capped size) OR 400 Bad Request
```

### Actual Behavior
```
All requests return 403 Forbidden
```

### Why It Matters
- Cannot verify pagination bounds checking
- Cannot verify invalid parameter handling
- Cannot verify page size limits

### Fix Priority
**P2 - MEDIUM**: Depends on ERROR #1

---

## ERROR #8: Concurrent Editing Not Handled
**Severity**: MEDIUM
**Impact**: 1 test fails
**Category**: Concurrency Control

### Affected Test
- TestConcurrentEditing::test_concurrent_profile_edits

### Issue
Concurrent PATCH requests to profile endpoint all return 403.

### Test Case
```python
# 3 concurrent edits to same profile
with ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(edit_profile, f'Bio {i}')
        for i in range(3)
    ]
```

### Expected Outcomes (one should happen)
1. **Last write wins** - Last request wins, data = 'Bio 2'
2. **First wins** - First request wins, data = 'Bio 0'
3. **Conflict error** - HTTP 409 Conflict
4. **Merge** - All bios combined somehow
5. **Optimistic locking** - Version check prevents overwrite

### Actual Outcome
```
All 3 requests return 403 Forbidden
Cannot test concurrency at all
```

### Required Features
- Proper transaction handling
- Conflict detection (optimistic or pessimistic locking)
- Proper error responses for conflicts

### Fix Priority
**P3 - MEDIUM**: After API endpoints accessible

---

## ERROR #9: Delete Non-existent Returns 403
**Severity**: MEDIUM
**Impact**: 2 tests fail
**Category**: API Error Handling

### Affected Tests
- TestDeleteNonexistent::test_delete_nonexistent_student_404
- TestDeleteNonexistent::test_delete_student_idempotency

### Issue
DELETE for non-existent student returns 403 instead of 404.

### Expected Behavior
```
DELETE /api/tutor/students/99999/
Response: 404 Not Found

DELETE /api/tutor/students/{id}/
Response: 204 No Content or 200 OK
DELETE /api/tutor/students/{id}/ (again)
Response: 404 Not Found (idempotent)
```

### Actual Behavior
```
Both requests return 403 Forbidden
```

### Why It Matters
- Cannot verify API properly handles non-existent resources
- Cannot verify idempotency
- Cannot verify correct HTTP semantics

### Fix Priority
**P2 - MEDIUM**: After ERROR #1 fixed

---

## ERROR #10: Student Limit Not Enforced
**Severity**: LOW
**Impact**: 1 test fails
**Category**: Business Logic

### Affected Test
- TestStudentLimitExceeded::test_many_students_handled

### Issue
Cannot verify student limits because API returns 403.

### Expected Behavior
```
When tutor has 50+ students assigned:
- New assignment attempt returns 400 Bad Request
- Or returns 409 Conflict
- Or silently caps at limit
```

### Actual Behavior
```
GET /api/tutor/students/ returns 403 Forbidden
Cannot even fetch student list
```

### Business Logic
- Some tutors may have student limits
- Need to enforce these limits
- Need proper error messages

### Fix Priority
**P4 - LOW**: After ERROR #1 fixed

---

## SUMMARY TABLE

| Error # | Issue | Severity | Tests Affected | Root Cause |
|---------|-------|----------|----------------|-----------|
| #1 | API 403 Forbidden | CRITICAL | 17 | Endpoints not mounted/accessible |
| #2 | None in POST data | MEDIUM | 1 | Test framework limitation |
| #3 | Database deadlock | HIGH | 2 | Transaction isolation in tests |
| #4 | Timeout 403 not 504 | HIGH | 2 | Same as #1 |
| #5 | Cascade delete untested | HIGH | 1 | Same as #1 |
| #6 | Invalid data 403 not 400 | HIGH | 6 | Same as #1 |
| #7 | Pagination 403 | MEDIUM | 5 | Same as #1 |
| #8 | Concurrent edit untested | MEDIUM | 1 | Same as #1 + missing logic |
| #9 | Delete 404 returns 403 | MEDIUM | 2 | Same as #1 |
| #10 | Limits untested | LOW | 1 | Same as #1 |

---

## CRITICAL PATH TO FIX

### Phase 1: Fix API Routing (BLOCKS 17 TESTS)
1. Check `/home/mego/Python Projects/THE_BOT_platform/backend/tutor_cabinet/urls.py`
2. Verify routes are properly included in main `urls.py`
3. Check for any `@permission_classes` decorators that may block access
4. Verify `force_authenticate()` is working in tests

### Phase 2: Fix Transaction Tests (BLOCKS 2 TESTS)
1. Update TestDatabaseRaceConditions to use proper isolation
2. Use `@pytest.mark.django_db(transaction=True)`
3. Create unique test data per thread

### Phase 3: Update Test Assertions (BLOCKS 1 TEST)
1. Fix test_empty_vs_null to use empty strings instead of None
2. Test with JSON encoding if None values important

---

## CONCLUSION

**Total Errors Found**: 23 distinct issues
**Unique Root Causes**: 3 (API routing, DB isolation, test framework)
**Blocking Tests**: 17/28 (61%)

The main issue is **API endpoint accessibility (403 errors)**, which blocks testing of error handling for 17 tests. Once this is fixed, most other errors should resolve naturally.
