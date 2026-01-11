# Task Plan: Create Comprehensive STUDENT Creation Tests

## Task Group 1 (Single Independent Task)

### Task t_student_creation_tests: Create comprehensive test suite for STUDENT creation
**Objective**: Create comprehensive pytest tests for STUDENT user creation through API endpoints with full validation coverage

**File**: `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/tests/test_roles_create_students.py` (NEW)

**Test Classes & Methods Required**:

#### 1. TestStudentCreationBasic (Basic creation scenarios)
- `test_create_student_via_general_endpoint` - POST /api/accounts/users/ with role=student
- `test_create_student_minimal_fields` - Only required fields (email, password, username)
- `test_student_profile_auto_created` - StudentProfile OneToOne auto-created
- `test_student_user_properties` - Verify role=student, is_active=True

#### 2. TestStudentCreationValidation (Field validation)
- `test_email_validation_valid` - Valid email accepted
- `test_email_validation_invalid_format` - Invalid email rejected with 400
- `test_email_unique_constraint` - Duplicate email rejected (409 or 400)
- `test_phone_validation_valid_formats` - Valid phone patterns (+79991234567, 79991234567, 9991234567)
- `test_phone_validation_invalid_formats` - Invalid phone rejected
- `test_phone_optional` - Empty phone accepted
- `test_username_unique_constraint` - Duplicate username rejected
- `test_first_name_optional` - First name can be empty
- `test_last_name_optional` - Last name can be empty
- `test_password_strong_requirement` - Weak passwords rejected
- `test_password_strong_accepted` - Strong passwords accepted (min 8 chars, mixed case, numbers)

#### 3. TestStudentCreationProfile (StudentProfile initialization)
- `test_profile_grade_initialized_null` - grade field is null initially
- `test_profile_goal_initialized_null` - goal field is null initially
- `test_profile_tutor_initialized_null` - tutor relationship is null
- `test_profile_parent_initialized_null` - parent relationship is null
- `test_profile_progress_percentage_initialized_zero` - progress_percentage=0
- `test_profile_streak_days_initialized_zero` - streak_days=0
- `test_profile_total_points_initialized_zero` - total_points=0
- `test_profile_accuracy_percentage_initialized_zero` - accuracy_percentage=0

#### 4. TestStudentCreationNotifications (NotificationSettings auto-creation)
- `test_notification_settings_auto_created` - NotificationSettings auto-created for new student
- `test_notification_settings_defaults` - All notification defaults are correct
- `test_notification_settings_linked_to_user` - Correctly linked to User via OneToOne

#### 5. TestStudentCreationTelegram (Telegram integration)
- `test_telegram_id_saved` - telegram_id saved if provided
- `test_telegram_id_unique` - Duplicate telegram_id rejected
- `test_telegram_id_optional` - telegram_id can be null
- `test_telegram_id_numeric_validation` - Non-numeric telegram_id rejected

#### 6. TestStudentCreationErrors (Error cases & edge cases)
- `test_create_student_missing_email` - Missing email returns 400
- `test_create_student_missing_password` - Missing password returns 400
- `test_create_student_missing_username` - Missing username returns 400
- `test_create_student_duplicate_email` - Duplicate email returns 400/409
- `test_create_student_duplicate_username` - Duplicate username returns 400/409
- `test_create_student_duplicate_telegram_id` - Duplicate telegram_id returns 400/409
- `test_create_student_invalid_phone` - Invalid phone returns 400
- `test_create_student_weak_password` - Weak password returns 400
- `test_create_student_inactive_tutor_creator` - Creating by inactive tutor fails
- `test_create_student_invalid_created_by_tutor` - Non-tutor as created_by_tutor fails

#### 7. TestStudentCreationTutorEndpoint (POST /api/accounts/students/create/)
- `test_create_student_via_tutor_endpoint` - POST /api/accounts/students/create/
- `test_tutor_endpoint_creates_with_role_student` - Ensures role=student
- `test_tutor_endpoint_requires_auth` - Anonymous request rejected
- `test_tutor_endpoint_requires_tutor_role` - Non-tutor rejected (only TUTOR role allowed)
- `test_tutor_endpoint_sets_created_by_tutor` - Automatically sets created_by_tutor=current_user
- `test_tutor_endpoint_student_linked_to_tutor` - Student created_by_tutor relationship correct

#### 8. TestStudentCreationDatabasePersistence (DB verification)
- `test_data_persisted_in_db` - Verify all fields saved correctly (.refresh_from_db())
- `test_multiple_students_creation` - Create multiple students, all unique
- `test_queryset_filtering` - assertQuerySetEqual for created students
- `test_transaction_rollback_on_error` - Transaction rolls back on validation error

**Testing Patterns**:
- Use `pytest-django` with `db` fixture for database isolation
- Use `APIClient` from `rest_framework.test` for endpoint testing
- Use `StudentFactory`, `UserFactory`, `TutorFactory` from conftest.py
- Use `assertQuerySetEqual` for database assertion
- Use `.refresh_from_db()` to verify persistence
- Mock/patch where needed (e.g., file upload for avatar)
- Include parametrized tests for multiple phone format validations

**Dependencies**:
- `pytest-django`
- `django-rest-framework`
- `factory-boy`
- Fixtures from `/home/mego/Python Projects/THE_BOT_platform/backend/tests/conftest.py`
- Models: User, StudentProfile, NotificationSettings (if exists)
- Views: UserCreateViewSet or similar (POST /api/accounts/users/)
- Serializers: UserSerializer, StudentProfileSerializer

**Success Criteria**:
- All 50+ test methods written and passing
- Full coverage of validation logic
- Database persistence verified
- Error cases comprehensive
- Both endpoints tested (general + tutor-specific)
- Profile auto-creation verified
- Notification settings auto-creation verified
- File: created at `/home/mego/Python Projects/THE_BOT_platform/backend/accounts/tests/test_roles_create_students.py`
- Syntax valid (black formatted)
- No import errors
- All pytest fixtures properly used

**Estimated Duration**: 40-50 minutes

---

## Notes:
- Tests should be independent and not rely on execution order
- Each test should use fresh factory instances
- Use parametrize for testing multiple similar cases
- Document complex test logic with brief comments
- Follow existing test patterns from codebase
