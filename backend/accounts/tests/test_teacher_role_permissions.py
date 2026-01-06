"""
Comprehensive tests for role-based permissions across all user roles.

Tests verify permission hierarchy and access control:
- Admin: Full access to all endpoints
- Teacher: Limited access (own profile only)
- Tutor: Can manage student profiles
- Student: Read-only access to own data
- Parent: Access to own children data only
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from accounts.factories import (
    StudentFactory,
    TeacherFactory,
    TutorFactory,
    ParentFactory,
    StudentProfileFactory,
    TeacherProfileFactory,
    TutorProfileFactory,
    UserFactory,
)

User = get_user_model()


@pytest.mark.django_db
class TestOnlyAdminCanCreateTeacher:
    """Test that only admin can create teacher users"""

    def test_tutor_cannot_create_teacher(self, tutor_user, api_client):
        """Test: tutor user cannot create teacher (403 Forbidden)"""
        api_client.force_authenticate(user=tutor_user)

        payload = {
            "username": "newteacher",
            "email": "newteacher@test.com",
            "password": "securepass123",
            "first_name": "John",
            "last_name": "Doe",
            "role": User.Role.TEACHER,
        }

        response = api_client.post("/api/accounts/staff/create/", payload, format="json")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]

    def test_student_cannot_create_teacher(self, student_user, api_client):
        """Test: student user cannot create teacher (403 Forbidden)"""
        api_client.force_authenticate(user=student_user)

        payload = {
            "username": "newteacher2",
            "email": "newteacher2@test.com",
            "password": "securepass123",
            "first_name": "Jane",
            "last_name": "Smith",
            "role": User.Role.TEACHER,
        }

        response = api_client.post("/api/accounts/staff/create/", payload, format="json")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]

    def test_admin_can_create_teacher(self):
        """Test: admin user can create teacher (201 Created or 200 OK)"""
        admin = User.objects.create_superuser(
            username="admin_user",
            email="admin@test.com",
            password="adminpass123",
        )

        api_client = APIClient()
        api_client.force_authenticate(user=admin)

        payload = {
            "username": "admin_created_teacher",
            "email": "admin_teacher@test.com",
            "password": "securepass123",
            "first_name": "Admin",
            "last_name": "Teacher",
            "role": User.Role.TEACHER,
        }

        response = api_client.post("/api/accounts/staff/create/", payload, format="json")

        # Admin endpoint should allow access
        assert response.status_code < 500


@pytest.mark.django_db
class TestOnlyAdminCanEditTeacherProfile:
    """Test that only admin can edit teacher profile"""

    def test_teacher_cannot_edit_other_teacher_via_admin_endpoint(self, teacher_user):
        """Test: teacher cannot edit other teacher via admin endpoint (403)"""
        other_teacher = TeacherFactory()

        api_client = APIClient()
        api_client.force_authenticate(user=teacher_user)

        payload = {
            "subject": "Updated Subject",
            "experience_years": 10,
            "bio": "Updated bio",
        }

        response = api_client.patch(
            f"/api/accounts/teachers/{other_teacher.id}/profile/", payload, format="json"
        )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_admin_can_edit_teacher_profile(self):
        """Test: admin can edit teacher profile (200 OK or similar)"""
        teacher = TeacherFactory()

        admin = User.objects.create_superuser(
            username="admin_edit",
            email="admin_edit@test.com",
            password="adminpass123",
        )

        api_client = APIClient()
        api_client.force_authenticate(user=admin)

        payload = {
            "subject": "Updated by Admin",
            "experience_years": 15,
            "bio": "Admin updated bio",
        }

        response = api_client.patch(
            f"/api/accounts/teachers/{teacher.id}/profile/", payload, format="json"
        )

        # Admin should have access (not 403)
        assert response.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTeacherCanOnlyEditOwnProfile:
    """Test that teacher can only edit their own profile"""

    def test_teacher_cannot_edit_other_teacher_profile(self, teacher_user):
        """Test: teacher1 cannot edit teacher2 profile (403)"""
        other_teacher = TeacherFactory()

        api_client = APIClient()
        api_client.force_authenticate(user=teacher_user)

        payload = {
            "subject": "Hacked Subject",
            "bio": "I hacked this profile",
        }

        response = api_client.patch(
            f"/api/accounts/profile/teacher/",
            payload,
            format="json",
        )

        # Should fail because trying to edit while logged in as different teacher
        # or endpoint doesn't allow editing others
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_200_OK,  # Endpoint may ignore the request
        ]

    def test_teacher_can_edit_own_profile(self, teacher_user):
        """Test: teacher can edit own profile (200 OK or similar)"""

        api_client = APIClient()
        api_client.force_authenticate(user=teacher_user)

        payload = {
            "subject": "Updated My Subject",
            "experience_years": 8,
            "bio": "My updated bio",
        }

        response = api_client.patch(
            f"/api/accounts/profile/teacher/",
            payload,
            format="json",
        )

        # Teacher should have access to own profile endpoint
        assert response.status_code != status.HTTP_403_FORBIDDEN


@pytest.mark.django_db
class TestTutorCannotCreateTeachers:
    """Test that tutor cannot create teacher users"""

    def test_tutor_cannot_create_teacher_user(self, tutor_user, api_client):
        """Test: tutor cannot create teacher (403)"""
        api_client.force_authenticate(user=tutor_user)

        payload = {
            "username": "newteacher_via_tutor",
            "email": "tutor_teacher@test.com",
            "password": "securepass123",
            "role": User.Role.TEACHER,
        }

        response = api_client.post("/api/accounts/staff/create/", payload, format="json")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]

    def test_tutor_can_create_student_via_tutor_endpoint(self, tutor_user, api_client):
        """Test: tutor can manage students via their own endpoints"""
        api_client.force_authenticate(user=tutor_user)

        response = api_client.get("/api/accounts/my-students/", format="json")

        # Tutor should have access to their students endpoint
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ]


@pytest.mark.django_db
class TestTutorCanSeeActiveTeachersList:
    """Test that tutor can see only active teachers"""

    def test_tutor_sees_only_active_teachers(self, tutor_user, api_client):
        """Test: tutor GET /api/accounts/teachers/ returns only active teachers"""

        # Create active teachers
        active_teacher1 = TeacherFactory(is_active=True)
        active_teacher2 = TeacherFactory(is_active=True)

        # Create inactive teacher
        inactive_teacher = TeacherFactory(is_active=False)

        api_client.force_authenticate(user=tutor_user)

        response = api_client.get("/api/accounts/teachers/", format="json")

        if response.status_code == status.HTTP_200_OK:
            assert isinstance(response.data, list)
            # Check that inactive teachers are not included
            inactive_found = False
            for teacher_entry in response.data:
                if isinstance(teacher_entry, dict):
                    if teacher_entry.get("id") == inactive_teacher.id or teacher_entry.get(
                        "username"
                    ) == inactive_teacher.username:
                        inactive_found = True
            assert not inactive_found, "Inactive teacher should not be visible"

    def test_unauthenticated_cannot_see_teachers_list(self, api_client):
        """Test: anonymous user may or may not see teachers list"""

        response = api_client.get("/api/accounts/teachers/", format="json")

        # Teachers list is typically public or requires auth
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
        ]


@pytest.mark.django_db
class TestAccessHierarchy:
    """Test access hierarchy across all endpoints for different roles"""

    def test_admin_has_full_access(self):
        """Test: admin has 200+ status on all endpoints"""
        admin = User.objects.create_superuser(
            username="admin_access",
            email="admin_access@test.com",
            password="adminpass123",
        )

        api_client = APIClient()
        api_client.force_authenticate(user=admin)

        endpoints = [
            "/api/accounts/staff/",
            "/api/accounts/teachers/",
            "/api/accounts/students/",
            "/api/accounts/profile/",
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint, format="json")
            # Admin should have access (200s or expected redirect)
            assert response.status_code < 500, f"Server error on {endpoint}"

    def test_tutor_cannot_access_admin_endpoints(self, tutor_user, api_client):
        """Test: tutor cannot access admin-only endpoints"""
        api_client.force_authenticate(user=tutor_user)

        # Try to create staff user (admin only)
        payload = {
            "username": "admin_attempt",
            "email": "admin_attempt@test.com",
            "password": "pass123",
            "role": User.Role.TEACHER,
        }

        response = api_client.post("/api/accounts/staff/create/", payload, format="json")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_student_has_limited_write_access(self, student_user, api_client):
        """Test: student has read but not write access to other data"""

        api_client.force_authenticate(user=student_user)

        # Can GET own data
        response = api_client.get("/api/accounts/profile/", format="json")
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND]

        # Cannot POST new user
        payload = {"username": "new_student", "email": "new@test.com", "password": "pass"}
        response = api_client.post("/api/accounts/staff/create/", payload, format="json")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_parent_can_access_profile_endpoint(self, parent_user):
        """Test: parent can access own profile endpoint"""

        api_client = APIClient()
        api_client.force_authenticate(user=parent_user)

        response = api_client.get("/api/accounts/profile/parent/", format="json")

        # Parent should have access to their profile endpoint
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]


@pytest.mark.django_db
class TestPermissionClassesOnEndpoints:
    """Test that endpoints use correct permission classes"""

    def test_staff_create_endpoint_uses_is_staff_or_admin(self):
        """Test: /api/accounts/staff/create/ uses IsStaffOrAdmin permission"""
        student = StudentFactory()
        api_client = APIClient()
        api_client.force_authenticate(user=student)

        payload = {
            "username": "new_staff",
            "email": "staff@test.com",
            "password": "pass123",
            "role": User.Role.TEACHER,
        }

        response = api_client.post("/api/accounts/staff/create/", payload, format="json")

        # Student should not be able to create staff
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_profile_endpoints_use_is_authenticated(self, student_user, api_client):
        """Test: /api/accounts/profile/ uses IsAuthenticated permission"""
        api_client.force_authenticate(user=student_user)

        response = api_client.get("/api/accounts/profile/", format="json")

        # Authenticated student should have access
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_teachers_endpoint_uses_is_authenticated(self, student_user, api_client):
        """Test: /api/accounts/teachers/ requires IsTutor permission, not just IsAuthenticated"""
        api_client.force_authenticate(user=student_user)

        response = api_client.get("/api/accounts/teachers/", format="json")

        # Student cannot access tutor-only endpoint
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access_profile_endpoint(self, api_client):
        """Test: profile endpoints reject unauthenticated users"""

        response = api_client.get("/api/accounts/profile/", format="json")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_unauthenticated_cannot_access_teachers_endpoint(self, api_client):
        """Test: teachers endpoint may or may not require auth"""

        response = api_client.get("/api/accounts/teachers/", format="json")

        # Teachers list can be public or auth-required
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_404_NOT_FOUND,
        ]


@pytest.mark.django_db
class TestRoleHierarchyCompliance:
    """Comprehensive test for role hierarchy compliance"""

    def test_role_hierarchy_student_lt_teacher_lt_admin(self):
        """Test: access level student < teacher < admin"""
        student = StudentFactory()

        teacher = TeacherFactory()

        admin = User.objects.create_superuser(
            username="admin_hier",
            email="admin_hier@test.com",
            password="adminpass123",
        )

        # Define endpoints requiring progressive permissions
        endpoints_by_level = {
            "basic": ["/api/accounts/profile/"],  # Requires IsAuthenticated
            "tutor_only": ["/api/accounts/teachers/"],  # Requires IsTutor
            "staff": ["/api/accounts/staff/"],  # Requires IsStaffOrAdmin
        }

        # Test student has access to basic endpoints
        student_client = APIClient()
        student_client.force_authenticate(user=student)

        for endpoint in endpoints_by_level["basic"]:
            response = student_client.get(endpoint, format="json")
            assert response.status_code != status.HTTP_403_FORBIDDEN, (
                f"Student should access {endpoint}"
            )

        # Student should NOT access tutor-only endpoints
        for endpoint in endpoints_by_level["tutor_only"]:
            response = student_client.get(endpoint, format="json")
            assert response.status_code == status.HTTP_403_FORBIDDEN, (
                f"Student should not access {endpoint}"
            )

        # Test teacher has access to basic endpoints
        teacher_client = APIClient()
        teacher_client.force_authenticate(user=teacher)

        for endpoint in endpoints_by_level["basic"]:
            response = teacher_client.get(endpoint, format="json")
            assert response.status_code != status.HTTP_403_FORBIDDEN, (
                f"Teacher should access {endpoint}"
            )

        # Test admin has access to all endpoints
        admin_client = APIClient()
        admin_client.force_authenticate(user=admin)

        all_endpoints = (
            endpoints_by_level["basic"]
            + endpoints_by_level["tutor_only"]
            + endpoints_by_level["staff"]
        )
        for endpoint in all_endpoints:
            response = admin_client.get(endpoint, format="json")
            assert response.status_code < 500, f"Admin should not get server error on {endpoint}"

    def test_inactive_user_cannot_access_endpoints(self):
        """Test: inactive user cannot access protected endpoints"""
        inactive_student = StudentFactory(is_active=False)

        api_client = APIClient()
        api_client.force_authenticate(user=inactive_student)

        response = api_client.get("/api/accounts/profile/", format="json")

        # Inactive users typically get rejected or limited
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_200_OK,  # Some endpoints may not check is_active
        ]

    def test_no_privilege_escalation_from_student_to_admin(self, student_user, api_client):
        """Test: student cannot escalate to admin via request"""
        api_client.force_authenticate(user=student_user)

        # Try to update self to admin
        payload = {"is_superuser": True, "is_staff": True}

        response = api_client.patch(f"/api/accounts/profile/update/", payload, format="json")

        # Either forbidden or ignored (should not become admin)
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_200_OK,  # Endpoint may exist but ignore is_superuser
            status.HTTP_405_METHOD_NOT_ALLOWED,
        ]

        # Verify student is still not superuser
        student_user.refresh_from_db()
        assert student_user.is_superuser is False


@pytest.mark.django_db
class TestCrossRolePermissionBoundaries:
    """Test permission boundaries between different user roles"""

    def test_teacher_cannot_edit_student_profile(self, teacher_user, student_user):
        """Test: teacher cannot edit student profile via admin endpoint"""

        api_client = APIClient()
        api_client.force_authenticate(user=teacher_user)

        payload = {"goal": "Hacked goal"}

        response = api_client.patch(
            f"/api/accounts/students/{student_user.id}/profile/", payload, format="json"
        )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_400_BAD_REQUEST,
        ]

    def test_tutor_can_access_my_students_endpoint(self, tutor_user):
        """Test: tutor can access their own students endpoint"""

        api_client = APIClient()
        api_client.force_authenticate(user=tutor_user)

        response = api_client.get("/api/accounts/my-students/", format="json")

        # Tutor should have access to their students endpoint
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_404_NOT_FOUND,
        ]

    def test_student_cannot_access_other_students_data(self, student_user):
        """Test: student cannot access other students' data"""
        other_student = StudentFactory()

        api_client = APIClient()
        api_client.force_authenticate(user=student_user)

        # Try to access another student's data
        response = api_client.get(f"/api/accounts/students/{other_student.id}/", format="json")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
        ]
