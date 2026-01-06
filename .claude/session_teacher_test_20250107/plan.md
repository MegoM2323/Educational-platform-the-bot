# Wave 1 Testing Plan - Teacher Dashboard

## Scope
Testing core teacher dashboard functionality with focus on authentication, authorization, and CRUD operations for basic entities.

## Wave 1 Tasks

### Group T1: Foundation (Authentication & Basic CRUD)

#### T1.1: Teacher Authentication Tests
- test_login_success: Successful teacher login
- test_login_invalid_credentials: Failed login with wrong password
- test_login_inactive_teacher: Cannot login if account inactive
- test_login_non_teacher_role: Non-teacher cannot access teacher endpoints
- test_token_generation: JWT token properly generated on login
- test_token_validation: Token validation on protected endpoints

#### T1.2: Teacher Authorization Tests
- test_access_own_materials: Teacher can access own materials
- test_access_other_materials: Teacher cannot access others' materials
- test_edit_own_material: Teacher can edit own material
- test_edit_other_material: Teacher cannot edit others' material
- test_delete_own_material: Teacher can delete own material
- test_teacher_subject_access: Teacher can only work with assigned subjects
- test_tutor_cannot_access_teacher_endpoints: Tutor role blocked from teacher endpoints

#### T1.3: CRUD Operations for Basic Entities
- test_create_subject: Create new subject (admin only or teacher?)
- test_read_subjects: List all available subjects
- test_create_material: Create new material
- test_read_material: Retrieve material details
- test_update_material: Update material properties
- test_delete_material: Delete material (soft or hard)
- test_create_subject_enrollment: Enroll student to subject
- test_read_enrollments: List subject enrollments
- test_update_enrollment_status: Change enrollment status
- test_delete_enrollment: Remove enrollment

## Test Structure
```
backend/tests/teacher_dashboard/
├── conftest.py           # Fixtures and setup
├── test_authentication.py # T1.1 tests
├── test_permissions.py    # T1.2 tests
└── test_crud_basics.py   # T1.3 tests
```

## Fixtures Required
- teacher_user: Authenticated teacher
- student_user: Student for enrollment tests
- admin_user: Admin for setup
- subject: Sample subject
- material: Sample material
- auth_client: Authenticated API client
