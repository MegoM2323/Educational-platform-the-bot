# Regression Test Report - Tutor Cabinet Final Test
**Test Name:** `tutor_cabinet_final_test_20260107`
**Date:** 2026-01-07
**Status:** FAILED (59.3% pass rate)

---

## Executive Summary

Regression testing revealed **8 critical/high regressions** affecting multiple API endpoints. The most severe issue is a **CRITICAL bug** preventing chat room creation (500 error - duplicate `created_by` parameter).

| Metric | Value |
|--------|-------|
| Total Tests | 27 |
| Passed | 16 |
| Failed | 11 |
| Pass Rate | 59.3% |
| Critical Issues | 1 |
| High Issues | 3 |
| Medium Issues | 3 |

---

## Regression Issues Summary

### CRITICAL - Must Fix Immediately

#### REG_001: Chat Room Creation Broken
- **Endpoint:** `POST /api/chat/rooms/`
- **Status Code:** 500 (Internal Server Error)
- **Error:** `TypeError: django.db.models.query.QuerySet.create() got multiple values for keyword argument 'created_by'`
- **Location:** `backend/chat/serializers.py:166`
- **Description:** The serializer receives `created_by` both from `perform_create()` and internally within `create()`
- **Impact:** Users cannot create chat rooms via API

**Root Cause Analysis:**
```python
# In views.py perform_create():
room = serializer.save(created_by=self.request.user)  # Passes created_by

# In serializers.py create():
room = ChatRoom.objects.create(created_by=self.context["request"].user, **validated_data)
# Tries to create with created_by again from context
```

**Fix Required:** Remove one of the duplicate `created_by` assignments

---

### HIGH - Urgent Investigation Required

#### REG_002: Student List Endpoint Permission Issue
- **Endpoint:** `GET /api/accounts/students/`
- **Status Code:** 403 (Forbidden) - Expected 200
- **Severity:** HIGH
- **Description:** Teacher role is blocked from accessing student list
- **Impact:** Teachers cannot view their student lists
- **Investigation:** Check `backend/accounts/views.py` permission classes

#### REG_003: Invoices Endpoints Not Found
- **Endpoints:** 
  - `GET /api/invoices/`
  - `POST /api/invoices/`
- **Status Code:** 404 (Not Found)
- **Severity:** HIGH
- **Description:** Payment/invoices functionality completely inaccessible
- **Impact:** Payments system is down
- **Investigation:** Verify `backend/invoices/urls.py` routing

#### REG_004: Assignments Create Broken
- **Endpoint:** `POST /api/assignments/`
- **Status Code:** 404 (Not Found) - Expected 201
- **Severity:** HIGH
- **Description:** Assignment creation endpoint not accessible
- **Impact:** Teachers cannot create assignments
- **Investigation:** Check `backend/assignments/views.py` and URL routing

---

### MEDIUM - Needs Investigation

#### REG_005-007: Accounts Endpoints Returning 404
- `GET /api/accounts/students/{id}/` → 404
- `PATCH /api/accounts/users/{id}/` → 404
- `GET /api/profile/tutor/` → 404

**Possible Causes:**
1. URL routing misconfiguration
2. ViewSet not properly registered
3. URL patterns not included in main urls.py

#### REG_008: HTTP Method Validation
- DELETE on list endpoint returns 200 instead of 405
- PUT method handling inconsistent

---

## Endpoint Status Matrix

### Working Endpoints (16)
```
CHAT:
✓ GET /api/chat/rooms/
✓ GET /api/chat/messages/
✓ POST /api/chat/messages/

SCHEDULING:
✓ GET /api/scheduling/lessons/
✓ POST /api/scheduling/lessons/
✓ GET /api/scheduling/schedule/

MATERIALS:
✓ GET /api/materials/subjects/
✓ POST /api/materials/subjects/
✓ GET /api/materials/materials/{id}/

ASSIGNMENTS:
✓ GET /api/assignments/
✓ GET /api/assignments/{id}/submissions/

REPORTS:
✓ GET /api/reports/

AUTH & PERMISSIONS:
✓ Authentication enforcement (401)
✓ Permission checks
✓ Teacher role access checks
✓ Performance (<2s response time)
```

### Broken Endpoints (8)
```
CHAT:
✗ POST /api/chat/rooms/                 [500] Duplicate created_by
✗ GET /api/chat/rooms/{id}/            [N/A] Not tested

ACCOUNTS:
✗ GET /api/accounts/students/          [403] Permission denied
✗ GET /api/accounts/students/{id}/    [404] Not found
✗ PATCH /api/accounts/users/{id}/     [404] Not found
✗ GET /api/profile/tutor/              [404] Not found

ASSIGNMENTS:
✗ POST /api/assignments/                [404] Not found

PAYMENTS:
✗ GET /api/invoices/                    [404] Not found
✗ POST /api/invoices/                   [404] Not found
```

---

## Detailed Issues by Category

### Chat Endpoints (4 tests: 3 PASS, 1 FAIL)
| Endpoint | Method | Status | Expected | Issue |
|----------|--------|--------|----------|-------|
| /api/chat/rooms/ | GET | 200 | 200 | OK |
| /api/chat/rooms/ | POST | 500 | 201 | Duplicate created_by |
| /api/chat/messages/ | GET | 200 | 200 | OK |
| /api/chat/messages/ | POST | 201 | 201 | OK |

### Accounts Endpoints (4 tests: 0 PASS, 4 FAIL)
| Endpoint | Method | Status | Expected | Issue |
|----------|--------|--------|----------|-------|
| /api/accounts/students/ | GET | 403 | 200 | Permission denied |
| /api/accounts/students/{id}/ | GET | 404 | 200 | Not found |
| /api/accounts/users/{id}/ | PATCH | 404 | 200 | Not found |
| /api/profile/tutor/ | GET | 404 | 200 | Not found |

### Scheduling Endpoints (3 tests: 3 PASS, 0 FAIL)
| Endpoint | Method | Status | Expected | Issue |
|----------|--------|--------|----------|-------|
| /api/scheduling/lessons/ | GET | 200 | 200 | OK |
| /api/scheduling/lessons/ | POST | 201 | 201 | OK |
| /api/scheduling/schedule/ | GET | 200 | 200 | OK |

### Materials Endpoints (3 tests: 3 PASS, 0 FAIL)
| Endpoint | Method | Status | Expected | Issue |
|----------|--------|--------|----------|-------|
| /api/materials/subjects/ | GET | 200 | 200 | OK |
| /api/materials/subjects/ | POST | 201 | 201 | OK |
| /api/materials/materials/{id}/ | GET | 200 | 200 | OK |

### Assignments Endpoints (3 tests: 2 PASS, 1 FAIL)
| Endpoint | Method | Status | Expected | Issue |
|----------|--------|--------|----------|-------|
| /api/assignments/ | GET | 200 | 200 | OK |
| /api/assignments/{id}/submissions/ | GET | 200 | 200 | OK |
| /api/assignments/ | POST | 404 | 201 | Not found |

### Payments Endpoints (2 tests: 0 PASS, 2 FAIL)
| Endpoint | Method | Status | Expected | Issue |
|----------|--------|--------|----------|-------|
| /api/invoices/ | GET | 404 | 200 | Not found |
| /api/invoices/ | POST | 404 | 201 | Not found |

### Reports Endpoints (1 test: 1 PASS, 0 FAIL)
| Endpoint | Method | Status | Expected | Issue |
|----------|--------|--------|----------|-------|
| /api/reports/ | GET | 200 | 200 | OK |

---

## Authentication & Permission Tests (3 PASS)
- Unauthenticated access properly denied (401)
- Student cannot access admin features
- Teacher can access scheduling endpoints

---

## Performance Test Results (1 PASS)
- Average response time: 45ms
- Maximum response time: 120ms
- All endpoints below 2s threshold
- Status: GOOD

---

## Root Cause Analysis

### Issue 1: Chat Room Creation (CRITICAL)
**File:** `backend/chat/serializers.py:166`

The `ChatRoomDetailSerializer.create()` method receives `created_by` from both:
1. The `perform_create()` method in `views.py`
2. The context within the serializer

**Solution:** Remove duplicate parameter passing. Choose one approach:
- Option A: Remove from `perform_create()`, get from context in serializer
- Option B: Remove from serializer, pass only from `perform_create()`

### Issue 2: Missing/404 Endpoints
**Possible Causes:**
1. ViewSet not registered in `urls.py`
2. URL patterns not included in main app's `urls.py`
3. Import error in router configuration
4. ViewSet class not properly defined

**Verification Steps:**
1. Check `backend/accounts/urls.py` - ensure all routers are registered
2. Check `backend/invoices/urls.py` - verify router existence
3. Check `backend/assignments/urls.py` - verify router existence
4. Verify all ViewSets are imported in URL configuration

### Issue 3: Permission Check Regression
**Endpoint:** `GET /api/accounts/students/`

Teacher should be able to access student list, but getting 403.

**Possible Causes:**
1. Permission class changed or added
2. Decorator override
3. Role-based permission logic changed

**Fix:**
1. Check `backend/accounts/views.py` - `StudentViewSet.permission_classes`
2. Verify teacher role has correct permissions
3. Check for any permission decorators that might override defaults

---

## Recommendations

### Priority: P0 - CRITICAL (Do Immediately)
1. **Fix Chat Room Creation**
   - File: `backend/chat/serializers.py:166`
   - Remove duplicate `created_by` parameter
   - Test with `pytest backend/chat/tests/ -k chat_rooms`

### Priority: P1 - HIGH (Today)
2. **Fix Missing Endpoints (404s)**
   - Verify URL routing for accounts, invoices, assignments
   - Check ViewSet registration
   - Test all 3 URL configurations

3. **Fix Permission Issue**
   - Debug student list endpoint permission
   - Verify teacher role permissions
   - Test with different user roles

### Priority: P2 - MEDIUM (This Week)
4. **Fix HTTP Method Validation**
   - Ensure proper 405 responses for unsupported methods
   - Add tests for method validation

5. **Add Endpoint Discovery Tests**
   - Create test that verifies all expected URLs are registered
   - Prevent future 404 regressions

---

## Test Files Generated

- **Test File:** `/home/mego/Python Projects/THE_BOT_platform/backend/tests/tutor_cabinet_final_test_20260107.py`
- **Report (JSON):** `/.playwright-mcp/tutor_cabinet_final_test_20260107.json`
- **Test Classes:** 10
- **Test Methods:** 27
- **Execution Time:** 10.24 seconds

---

## How to Reproduce

```bash
cd /home/mego/Python\ Projects/THE_BOT_platform

# Run regression tests
ENVIRONMENT=test python -m pytest backend/tests/tutor_cabinet_final_test_20260107.py -v

# Run specific test group
ENVIRONMENT=test python -m pytest backend/tests/tutor_cabinet_final_test_20260107.py::ChatEndpointsRegression -v

# Run with detailed output
ENVIRONMENT=test python -m pytest backend/tests/tutor_cabinet_final_test_20260107.py -v -s
```

---

## Next Steps

1. Assign P0 issue (Chat room creation) to coder
2. Investigate P1 issues (missing endpoints)
3. Fix permission regression
4. Re-run regression tests after each fix
5. Implement endpoint discovery test to prevent future regressions
