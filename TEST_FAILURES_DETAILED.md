# Detailed Test Failures - THE BOT Platform Backend

Generated: December 6, 2025
Total Failures: 65

---

## Critical Failures (Must Fix Before Merge)

### Group 1: Authentication Endpoint 500 Errors (5 tests)

**File**: `tests/integration/test_wave2_critical_endpoints.py`

```
FAILED test_wave2_critical_endpoints.py::TestT005TeacherAuthentication::test_teacher_login
FAILED test_wave2_critical_endpoints.py::TestAllRolesAuthentication::test_student_login
FAILED test_wave2_critical_endpoints.py::TestAllRolesAuthentication::test_teacher_login
FAILED test_wave2_critical_endpoints.py::TestAllRolesAuthentication::test_tutor_login
FAILED test_wave2_critical_endpoints.py::TestAllRolesAuthentication::test_parent_login
```

**Error**:
```
assert 500 == 200
where 500 = <Response status_code=500, "application/json">.status_code
and 200 = status.HTTP_200_OK

Endpoint: /api/auth/login/
```

**Root Cause**: Supabase client initialization failing in test environment

**Log Message**:
```
[ERROR] 2025-12-06 04:24:42 django.request log_response:253 - Internal Server Error: /api/auth/login/
INFO accounts.supabase_service:supabase_service.py:50 - Supabase клиент успешно инициализирован
```

**Fix**:
1. Mock Supabase client in test environment
2. OR provide valid test credentials in ENVIRONMENT=test
3. OR use fallback authentication method for tests

**File to Fix**: `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/views.py`

---

### Group 2: Profile Endpoint URLs Incorrect (18 tests)

**File**: `tests/integration/test_profile_integration.py`

```
FAILED test_profile_integration.py::TestStudentProfileIntegration::test_student_can_update_own_profile
FAILED test_profile_integration.py::TestStudentProfileIntegration::test_student_cannot_get_profile_without_auth
FAILED test_profile_integration.py::TestStudentProfileIntegration::test_student_profile_requires_auth
FAILED test_profile_integration.py::TestStudentProfileIntegration::test_student_profile_partial_update
FAILED test_profile_integration.py::TestTeacherProfileIntegration::test_teacher_can_update_own_profile
FAILED test_profile_integration.py::TestTeacherProfileIntegration::test_teacher_profile_requires_auth
FAILED test_profile_integration.py::TestTeacherProfileIntegration::test_teacher_partial_update
FAILED test_profile_integration.py::TestTutorProfileIntegration::test_tutor_can_update_own_profile
FAILED test_profile_integration.py::TestTutorProfileIntegration::test_tutor_profile_requires_auth
FAILED test_profile_integration.py::TestParentProfileIntegration::test_parent_can_update_own_profile
FAILED test_profile_integration.py::TestParentProfileIntegration::test_parent_profile_requires_auth
FAILED test_profile_integration.py::TestProfileErrorHandling::test_invalid_token_returns_error
FAILED test_profile_integration.py::TestProfileErrorHandling::test_missing_auth_header_returns_error
FAILED test_profile_integration.py::TestProfileCrossRoles::test_multiple_roles_isolation
FAILED test_profile_integration.py::TestProfileCrossRoles::test_tutor_and_parent_isolation
FAILED test_profile_integration.py::TestProfileDataValidation::test_student_progress_validation
FAILED test_profile_integration.py::TestProfileDataValidation::test_teacher_experience_validation
FAILED test_profile_integration.py::TestProfileConcurrency::test_sequential_updates
```

**Error**:
```
assert 404 in [200, 201]
where 404 = <HttpResponseNotFound status_code=404, "text/html; charset=utf-8">.status_code
```

**Issue**: Tests use `/api/auth/profile/{role}/me/` but actual endpoints are `/api/auth/profile/{role}/`

**Example**:
```python
# WRONG (in test):
response = api_client.patch('/api/auth/profile/student/me/', data)

# CORRECT (actual endpoint):
# path('profile/student/', StudentProfileView.as_view(), ...)
```

**Fix**: Remove `/me/` from all profile endpoint URLs in test file

**Lines to Change**:
- Line 108: `/api/auth/profile/student/me/`
- Line 117: `/api/auth/profile/student/me/`
- Line 122: `/api/auth/profile/student/me/`
- Line 133: `/api/auth/profile/student/me/`
- (and all similar lines for teacher, tutor, parent)

**File to Fix**: `/home/mego/Python Projects/THE_BOT_platform/backend/tests/integration/test_profile_integration.py`

---

## High Priority Failures (Blocks Multiple Tests)

### Group 3: Missing Database Decorators (1 confirmed, likely more)

**File**: `tests/integration/scheduling/test_lesson_views.py`

```
FAILED test_lesson_views.py::TestLessonListEndpoint::test_list_returns_empty_for_no_access
  RuntimeError: Database access not allowed, use the "django_db" mark,
  or the "db" or "transactional_db" fixtures to enable it.
```

**Root Cause**: Test function missing `@pytest.mark.django_db` decorator

**Code**:
```python
class TestLessonListEndpoint:
    # WRONG - no decorator:
    def test_list_returns_empty_for_no_access(self, api_client):
        from accounts.models import User, TeacherProfile
        teacher = User.objects.create_user(...)  # ERROR HERE
        TeacherProfile.objects.create(...)
```

**Fix**: Add decorator to test class:
```python
@pytest.mark.django_db
class TestLessonListEndpoint:
    ...
```

**Affected Classes** (likely):
- `TestLessonListEndpoint` - line 280+
- `TestLessonMyScheduleEndpoint` - likely
- `TestLessonCreateEndpoint` - likely
- Other lesson test classes

**File to Fix**: `/home/mego/Python Projects/THE_BOT_platform/backend/tests/integration/scheduling/test_lesson_views.py`

---

### Group 4: Lesson Endpoint 404 Errors (11 tests)

**File**: `tests/integration/scheduling/test_lesson_views.py`

```
FAILED test_lesson_views.py::TestLessonListEndpoint::test_teacher_sees_own_lessons
FAILED test_lesson_views.py::TestLessonListEndpoint::test_student_sees_own_lessons
FAILED test_lesson_views.py::TestLessonListEndpoint::test_tutor_sees_students_lessons
FAILED test_lesson_views.py::TestLessonMyScheduleEndpoint::test_teacher_gets_own_schedule
FAILED test_lesson_views.py::TestLessonMyScheduleEndpoint::test_student_gets_own_schedule
FAILED test_lesson_views.py::TestLessonMyScheduleEndpoint::test_my_schedule_with_subject_filter
FAILED test_lesson_views.py::TestLessonMyScheduleEndpoint::test_my_schedule_with_date_filter
FAILED test_lesson_views.py::TestLessonUpdateEndpoint::test_teacher_cannot_update_other_lesson
FAILED test_lesson_views.py::TestLessonHistoryEndpoint::test_history_ordered_by_timestamp
FAILED test_lesson_views.py::TestLessonCreateEndpoint::test_unauthenticated_cannot_create
```

**Error**:
```
assert 404 in [expected_codes]
Expected: 200, 401, or other valid code
Actual: 404 Not Found
```

**Root Cause**: Likely combination of:
1. Missing `@pytest.mark.django_db` (database doesn't exist)
2. Wrong endpoint URLs
3. Missing test data

**Recommendation**: First add `@pytest.mark.django_db` to class, then re-run to identify remaining issues

**File to Fix**: `/home/mego/Python Projects/THE_BOT_platform/backend/tests/integration/scheduling/test_lesson_views.py`

---

### Group 5: Lesson Creation Flow Issues (4 tests)

**File**: `tests/integration/scheduling/test_lesson_creation_flow.py`

```
FAILED test_lesson_creation_flow.py::TestLessonCreationIntegration::test_teacher_create_lesson_full_flow
FAILED test_lesson_creation_flow.py::TestLessonCreationIntegration::test_lesson_creation_creates_history_record
FAILED test_lesson_creation_flow.py::TestLessonListingFiltering::test_teacher_sees_only_their_lessons
FAILED test_lesson_creation_flow.py::TestLessonListingFiltering::test_student_sees_only_their_lessons
```

**Root Cause**: Same as Group 4 - missing `@pytest.mark.django_db`

**Fix**: Add decorator to test classes:
```python
@pytest.mark.django_db
class TestLessonCreationIntegration:
    ...

@pytest.mark.django_db
class TestLessonListingFiltering:
    ...
```

**File to Fix**: `/home/mego/Python Projects/THE_BOT_platform/backend/tests/integration/scheduling/test_lesson_creation_flow.py`

---

## Medium Priority Failures (Performance/Coverage)

### Group 6: N+1 Query Optimization (1 test)

**File**: `tests/integration/accounts/test_teacher_profile_api.py`

```
FAILED test_teacher_profile_api.py::TestTeacherProfileGetEndpoint::test_profile_no_n_plus_one_queries
  Failed: Expected to perform 2 queries but 4 were done

Queries:
1. SAVEPOINT "s139781390277568_x2"
2. SELECT "accounts_teacherprofile".* FROM "accounts_teacherprofile"
   INNER JOIN "accounts_user" ON ...
   WHERE "accounts_teacherprofile"."user_id" = 1
3. SELECT "materials_teachersubject".* FROM "materials_teachersubject"
   INNER JOIN "materials_subject" ON ...
   WHERE "materials_teachersubject"."teacher_id" = 1
4. RELEASE SAVEPOINT "s139781390277568_x2"
```

**Root Cause**: View not using `select_related()` or `prefetch_related()` to fetch teacher subjects

**Fix**: In `TeacherProfileView`, use:
```python
# Option 1: select_related (if one-to-one)
profile = TeacherProfile.objects.select_related('user').get(user=user)

# Option 2: prefetch_related (for reverse relations)
.prefetch_related('teachersubject_set__subject')
```

**File to Fix**: `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/profile_views.py`

---

### Group 7: Forum System Integration Issues (8 tests)

**File**: `tests/integration/chat/test_forum_system_integration.py`

```
FAILED test_forum_system_integration.py::TestForumMessageSending::test_teacher_can_send_message_to_student
FAILED test_forum_system_integration.py::TestForumMessageSending::test_student_can_send_message_to_teacher
FAILED test_forum_system_integration.py::TestForumMessageSending::test_pachca_notification_signal_triggered
FAILED test_forum_system_integration.py::TestForumChatVisibility::test_tutor_sees_only_their_student_chats
FAILED test_forum_system_integration.py::TestForumChatVisibility::test_teacher_sees_only_their_student_chats
FAILED test_forum_system_integration.py::TestForumChatVisibility::test_teacher_cannot_see_tutor_chats
FAILED test_forum_system_integration.py::TestForumChatVisibility::test_student_sees_only_their_teacher_and_tutor_chats
FAILED test_forum_system_integration.py::TestForumChatSignalCreation::test_enrollment_chat_idempotency
```

**Error**: Varies - mostly 404s or missing data

**Root Cause**: Likely incorrect endpoint URLs or missing database decorators

**Fix**:
1. Add `@pytest.mark.django_db` to test classes if not present
2. Verify endpoint URLs match actual routes
3. Check test data setup in conftest fixtures

**File to Fix**: `/home/mego/Python Projects/THE_BOT_platform/backend/tests/integration/chat/test_forum_system_integration.py`

---

## Lower Priority Failures (Ambiguous/Need Investigation)

### Group 8: Tutor Students API Issues (12 tests)

**File**: `tests/integration/materials/test_tutor_students_api.py`

```
FAILED test_tutor_students_api.py::TestTutorStudentsListEndpoint::test_tutor_only_sees_their_students
FAILED test_tutor_students_api.py::TestTutorStudentsListEndpoint::test_tutor_can_list_their_students
FAILED test_tutor_students_api.py::TestTutorStudentsListEndpoint::test_students_list_no_n_plus_one
FAILED test_tutor_students_api.py::TestTutorStudentsListEndpoint::test_student_list_includes_full_name_field
FAILED test_tutor_students_api.py::TestTutorStudentsListEndpoint::test_student_list_includes_avatar_url
FAILED test_tutor_students_api.py::TestTutorStudentScheduleEndpoint::test_unauthenticated_cannot_get_schedule
FAILED test_tutor_students_api.py::TestTutorStudentScheduleEndpoint::test_tutor_cannot_access_other_tutors_students
FAILED test_tutor_students_api.py::TestTutorStudentScheduleEndpoint::test_tutor_can_get_student_schedule
FAILED test_tutor_students_api.py::TestTutorStudentScheduleEndpoint::test_student_without_lessons_returns_empty_array
FAILED test_tutor_students_api.py::TestTutorStudentScheduleEndpoint::test_schedule_only_includes_future_lessons
FAILED test_tutor_students_api.py::TestTutorStudentScheduleEndpoint::test_schedule_no_n_plus_one_queries
FAILED test_tutor_students_api.py::TestTutorStudentScheduleEndpoint::test_schedule_includes_lesson_details
```

**Root Cause**: Likely missing `@pytest.mark.django_db` + incorrect endpoint URLs

**Fix**:
1. Add `@pytest.mark.django_db` to test class
2. Verify endpoint URLs match actual routes
3. May need query optimization

**File to Fix**: `/home/mego/Python Projects/THE_BOT_platform/backend/tests/integration/materials/test_tutor_students_api.py`

---

### Group 9: Admin User Creation Issues (6 tests)

**File**: `tests/integration/test_admin_user_creation.py`

```
FAILED test_admin_user_creation.py::TestAdminStudentCreation::test_create_student_minimal_data
FAILED test_admin_user_creation.py::TestAdminStudentCreation::test_create_student_with_optional_data
FAILED test_admin_user_creation.py::TestAdminParentCreation::test_create_parent_minimal_data
FAILED test_admin_user_creation.py::TestAdminParentCreation::test_create_parent_with_phone
FAILED test_admin_user_creation.py::TestAdminParentCreation::test_create_parent_duplicate_email
FAILED test_admin_user_creation.py::TestAdminWorkflowIntegration::test_complete_workflow
```

**Error**: 404 on admin endpoints

**Root Cause**: Endpoint URLs don't match actual routes in `accounts/urls.py`

**Fix**:
1. Verify admin endpoint URLs in test match `accounts/urls.py`
2. Add `@pytest.mark.django_db` if not present
3. Check test data setup

**File to Fix**: `/home/mego/Python Projects/THE_BOT_platform/backend/tests/integration/test_admin_user_creation.py`

---

## Summary Table

| Issue Type | Count | Files | Priority | Estimated Time |
|-----------|-------|-------|----------|-----------------|
| Login 500 errors | 5 | 1 | CRITICAL | 2-4 hours |
| Profile URL wrong | 18 | 1 | HIGH | 30 minutes |
| Missing @django_db | 1+ | 4+ | HIGH | 1 hour |
| Lesson endpoint 404s | 11 | 2 | HIGH | 2 hours |
| Forum integration 404s | 8 | 1 | MEDIUM | 2 hours |
| Tutor API 404s | 12 | 1 | MEDIUM | 2 hours |
| Admin endpoint 404s | 6 | 1 | MEDIUM | 1 hour |
| N+1 query | 1 | 1 | LOW | 30 minutes |
| **TOTAL** | **65** | **6+** | | **8-12 hours** |

---

## Files Requiring Changes

### Tests (Need Fixing)

1. **test_profile_integration.py** (18 failures)
   - Remove `/me/` from all endpoint URLs

2. **test_lesson_views.py** (11 failures)
   - Add `@pytest.mark.django_db` to all test classes
   - Possibly fix endpoint URLs

3. **test_lesson_creation_flow.py** (4 failures)
   - Add `@pytest.mark.django_db` to test classes

4. **test_tutor_students_api.py** (12 failures)
   - Add `@pytest.mark.django_db` to test class
   - Possibly fix endpoint URLs

5. **test_forum_system_integration.py** (8 failures)
   - Add `@pytest.mark.django_db` if missing
   - Possibly fix endpoint URLs

6. **test_admin_user_creation.py** (6 failures)
   - Possibly add `@pytest.mark.django_db`
   - Verify admin endpoint URLs

### Code (Need Fixing)

1. **accounts/views.py** (5 failures)
   - Fix Supabase client initialization for test environment

2. **accounts/profile_views.py** (1 failure)
   - Add query optimization (select_related/prefetch_related)

---

## Re-run Commands

After applying fixes, use these commands to verify:

```bash
# Test single file
cd /home/mego/Python\ Projects/THE_BOT_platform/backend
source ../.venv/bin/activate
export ENVIRONMENT=test

# After login fix:
pytest tests/integration/test_wave2_critical_endpoints.py -v

# After profile URL fix:
pytest tests/integration/test_profile_integration.py -v

# After adding @django_db:
pytest tests/integration/scheduling/test_lesson_views.py -v

# Run all integration tests:
pytest tests/integration/ -v --tb=short
```

---

End of Document
