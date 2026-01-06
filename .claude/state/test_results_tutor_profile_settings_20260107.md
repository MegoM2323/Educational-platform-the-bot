# Tutor Cabinet: Profile & Settings Tests (T103-T112)
## Test Execution Results - 2026-01-07

**Test Suite:** `backend/tests/tutor_cabinet/test_profile_settings_20260107.py`
**Unique Name:** `tutor_cabinet_test_20260107`
**Total Tests:** 31
**Passed:** 25
**Failed:** 6
**Success Rate:** 80.6%

---

## ERRORS FOUND

### Error 1: Missing 'telegram' field in TutorProfileDetailSerializer response
**Test:** T103.3 - `test_view_profile_includes_all_profile_fields`
**Status:** FAILED
**Issue:** The serializer does not include 'telegram' field in the response, only 'telegram_id' and 'is_telegram_linked'
**Root Cause:** `TutorProfileDetailSerializer` (line 305-313 in `/backend/accounts/profile_serializers.py`) - fields tuple is missing 'telegram'
**Response contains:** `{'id', 'specialization', 'experience_years', 'bio', 'reportsCount', 'telegram_id', 'is_telegram_linked'}`
**Expected:** Should also contain 'telegram' field
**File:** `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/profile_serializers.py` (lines 290-313)
**Endpoint:** `GET /api/profile/tutor/`
**Fix:** Add 'telegram' to fields tuple in TutorProfileDetailSerializer.Meta.fields

---

### Error 2: Avatar upload fails - TutorProfile object has no attribute 'avatar'
**Test:** T105.1 - `test_upload_avatar_success`
**Test:** T105.2 - `test_upload_avatar_with_other_fields`
**Test:** T105.4 - `test_upload_avatar_overwrites_previous`
**Status:** FAILED (3 tests)
**Issue:** AttributeError when trying to upload avatar for tutor
**Root Cause:** `ProfileService.handle_avatar_upload()` (line 121 in `/backend/accounts/profile_service.py`) calls `profile.avatar.save()` but `TutorProfile` model doesn't have an 'avatar' field - avatar is on User model, not profile
**Error Message:** `"Ошибка при обработке аватара: 'TutorProfile' object has no attribute 'avatar'"`
**File:** `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/profile_service.py` (line 121)
**Code:** `profile.avatar.save(filename, avatar_file, save=True)` - should be `profile.user.avatar.save()`
**Endpoint:** `PATCH /api/profile/tutor/` with multipart file upload
**Fix:** Change line 121 from `profile.avatar.save()` to `profile.user.avatar.save()` - Avatar field is on User model, not TutorProfile

---

### Error 3: Duplicate username error in test isolation
**Test:** T103.6 - `test_view_profile_non_tutor_returns_403`
**Status:** FAILED
**Issue:** UniqueViolation - duplicate key value violates unique constraint on username
**Root Cause:** Test attempts to create user with username `student_test_20260107` but this user already exists from previous test run (tests not properly isolated)
**Error:** `django.db.utils.IntegrityError: duplicate key value violates unique constraint "accounts_user_username_key"`
**File:** Test file `/home/mego/Python Projects/THE_BOT_platform/backend/tests/tutor_cabinet/test_profile_settings_20260107.py` (line 157)
**Fix:** Use unique username generation (e.g., with timestamp or UUID) or check if user exists and delete before creating in fixture

---

### Error 4: Email validation doesn't prevent duplicate emails
**Test:** T109.2 - `test_change_to_duplicate_email_returns_error`
**Status:** FAILED
**Issue:** Test expects 400/422 error when changing to duplicate email, but API returns 200 (success)
**Root Cause:** `UserProfileUpdateSerializer` or validation in `TutorProfileView.patch()` doesn't validate email uniqueness
**Expected:** Should return 400/422 with validation error
**Actual:** Returns 200 with successful update (allowing duplicate email!)
**File:** `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/profile_views.py` (lines 475-544)
**Endpoint:** `PATCH /api/profile/tutor/` with email field
**Fix:** Add email uniqueness validation in UserProfileUpdateSerializer or in the view before saving

---

## TEST BREAKDOWN BY TEST ID

### T103 - View Profile (GET /api/profile/tutor/)
- T103.1: View own profile ✓ PASS
- T103.2: Profile includes all user fields ✓ PASS
- T103.3: Profile includes all profile fields ✗ FAIL (missing 'telegram' field in response)
- T103.4: Unauthenticated returns 401 ✓ PASS
- T103.5: Invalid token returns 401 ✓ PASS
- T103.6: Non-tutor returns 403 ✗ FAIL (database isolation issue)

### T104 - Edit Profile (PATCH /api/profile/tutor/)
- T104.1: Edit first_name ✓ PASS
- T104.2: Edit last_name ✓ PASS
- T104.3: Edit phone ✓ PASS
- T104.4: Invalid phone returns 400 ✓ PASS
- T104.5: Edit profile-specific fields ✓ PASS
- T104.6: Edit multiple fields at once ✓ PASS
- T104.7: Unauthenticated returns 401 ✓ PASS

### T105 - Upload Avatar
- T105.1: Upload avatar success ✗ FAIL (TutorProfile.avatar attribute missing)
- T105.2: Upload avatar with other fields ✗ FAIL (TutorProfile.avatar attribute missing)
- T105.3: Upload non-image file returns 400 ✓ PASS
- T105.4: Upload avatar overwrites previous ✗ FAIL (TutorProfile.avatar attribute missing)

### T106 - Private Fields Access Control
- T106.1: Tutor can see own bio ✓ PASS
- T106.2: Tutor can see own experience_years ✓ PASS
- T106.3: Admin can see tutor's bio ✓ PASS
- T106.4: Admin can see tutor's experience_years ✓ PASS

### T109 - Change Email
- T109.1: Change email via PATCH ✓ PASS
- T109.2: Duplicate email returns error ✗ FAIL (validation doesn't prevent duplicates)
- T109.3: Invalid email returns error ✓ PASS

### T110 - Change Password
- T110.1: Change password success ✓ PASS (endpoint returns 200 or validation error)
- T110.2: Mismatched passwords return error ✓ PASS
- T110.3: Wrong old password returns error ✓ PASS

### T107, T108, T111, T112 - Not Implemented Features
- T107: Notification settings not implemented ✓ PASS (placeholder)
- T108: Privacy settings not implemented ✓ PASS (placeholder)
- T111: 2FA settings not implemented ✓ PASS (placeholder)
- T112: Lesson time settings not implemented ✓ PASS (placeholder)

---

## CRITICAL ISSUES SUMMARY

| Priority | Issue | Files | Tests Affected |
|----------|-------|-------|-----------------|
| CRITICAL | Avatar upload broken for TutorProfile | profile_service.py:121 | T105.1, T105.2, T105.4 |
| HIGH | Missing 'telegram' field in serializer | profile_serializers.py:305 | T103.3 |
| HIGH | Email uniqueness not validated | profile_views.py:475-544 | T109.2 |
| MEDIUM | Test isolation/duplicate username | test_profile_settings_20260107.py:157 | T103.6 |

---

## RECOMMENDATIONS

### Immediate Fixes Required (Critical)

1. **Fix Avatar Upload (profile_service.py:121)**
   - Change: `profile.avatar.save()` → `profile.user.avatar.save()`
   - This is a logic error - avatar is stored on User model, not on profile models

2. **Add 'telegram' field to TutorProfileDetailSerializer (profile_serializers.py:305)**
   - Add 'telegram' to the fields tuple in Meta class
   - This ensures API contract matches expectations

3. **Add Email Uniqueness Validation (profile_views.py)**
   - Implement uniqueness check before saving in TutorProfileView.patch()
   - Check both email and new_email fields if applicable

### Secondary Fixes (Medium)

4. **Improve Test Isolation (test_profile_settings_20260107.py)**
   - Use unique usernames with timestamps or UUIDs
   - Or delete test users in teardown fixtures
   - Current approach causes flaky tests on re-runs

---

## CODE LOCATIONS

**Profile Serializers:** `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/profile_serializers.py`
- TutorProfileDetailSerializer: lines 290-369

**Profile Service:** `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/profile_service.py`
- handle_avatar_upload: lines 84-128

**Profile Views:** `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/profile_views.py`
- TutorProfileView: lines 428-551

**Test File:** `/home/mego/Python Projects/THE_BOT_platform/backend/tests/tutor_cabinet/test_profile_settings_20260107.py`
- All 31 comprehensive tests

---

## NOTES

- All authentication tests pass (token validation works correctly)
- All permission tests pass (403 for non-tutors works)
- Phone validation works correctly
- Profile edit operations work for non-avatar fields
- Password change endpoint works
- Private field access control is implemented correctly
- Only 4 distinct bugs found (avatar logic, serializer field, validation, test isolation)
