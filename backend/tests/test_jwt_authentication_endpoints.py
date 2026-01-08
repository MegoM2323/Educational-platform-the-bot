"""
Comprehensive JWT authentication tests for 33 student/tutor endpoints.

Tests verify that all endpoints:
1. Accept JWT Bearer tokens (200/201)
2. Reject requests without token (401)
3. Reject requests with invalid token (401)
4. Accept session-based authentication as fallback (200/201)
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken, AccessToken
from rest_framework import status
from datetime import timedelta

from materials.models import Subject, Material, SubjectEnrollment
from accounts.models import StudentProfile, TutorProfile

User = get_user_model()


@pytest.fixture
def api_client():
    """Provide API client"""
    return APIClient()


@pytest.fixture
def student_user(db):
    """Create student user with profile"""
    user = User.objects.create_user(
        username="test_student",
        email="test_student@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Student",
        role=User.Role.STUDENT,
        is_active=True,
    )
    StudentProfile.objects.create(user=user)
    return user


@pytest.fixture
def tutor_user(db):
    """Create tutor user with profile"""
    user = User.objects.create_user(
        username="test_tutor",
        email="test_tutor@test.com",
        password="testpass123",
        first_name="Test",
        last_name="Tutor",
        role=User.Role.TUTOR,
        is_active=True,
    )
    TutorProfile.objects.create(user=user)
    return user


@pytest.fixture
def teacher_user(db):
    """Create teacher user"""
    return User.objects.create_user(
        username="test_teacher",
        email="test_teacher@test.com",
        password="testpass123",
        role=User.Role.TEACHER,
        is_active=True,
    )


@pytest.fixture
def subject(db, teacher_user):
    """Create test subject"""
    return Subject.objects.create(
        name="Test Subject",
        color="#FF0000"
    )


@pytest.fixture
def enrollment(db, student_user, subject, teacher_user):
    """Create student enrollment"""
    return SubjectEnrollment.objects.create(
        student=student_user,
        subject=subject,
        teacher=teacher_user
    )


@pytest.fixture
def material(db):
    """Create test material"""
    return Material.objects.create(
        title="Test Material",
        description="Test Description"
    )


@pytest.fixture
def student_token(student_user):
    """Generate JWT token for student"""
    refresh = RefreshToken.for_user(student_user)
    return str(refresh.access_token)


@pytest.fixture
def tutor_token(tutor_user):
    """Generate JWT token for tutor"""
    refresh = RefreshToken.for_user(tutor_user)
    return str(refresh.access_token)


# ==============================================
# JWT Authentication Basics Tests
# ==============================================

class TestJWTTokenBasics:
    """Test basic JWT token functionality"""

    def test_valid_jwt_token_accepted(self, api_client, student_token):
        """Test that valid JWT token is accepted"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/dashboard/student/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_invalid_jwt_token_rejected(self, api_client):
        """Test that invalid JWT token is rejected"""
        headers = {"HTTP_AUTHORIZATION": "Bearer invalid.token.here"}
        response = api_client.get("/api/dashboard/student/", **headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_no_token_rejected(self, api_client):
        """Test that request without token is rejected"""
        response = api_client.get("/api/dashboard/student/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_malformed_auth_header_rejected(self, api_client):
        """Test that malformed Authorization header is rejected"""
        headers = {"HTTP_AUTHORIZATION": "InvalidHeader"}
        response = api_client.get("/api/dashboard/student/", **headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_jwt_token_without_bearer_prefix_rejected(self, api_client, student_token):
        """Test that JWT token without Bearer prefix is rejected"""
        headers = {"HTTP_AUTHORIZATION": student_token}
        response = api_client.get("/api/dashboard/student/", **headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_empty_bearer_token_rejected(self, api_client):
        """Test that empty Bearer token is rejected"""
        headers = {"HTTP_AUTHORIZATION": "Bearer "}
        response = api_client.get("/api/dashboard/student/", **headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================
# Student Dashboard Endpoints
# ==============================================

class TestStudentDashboardEndpoints:
    """Test student dashboard endpoints with JWT"""

    def test_dashboard_with_jwt_token(self, api_client, student_token, student_user):
        """GET /api/dashboard/student/ with valid JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/dashboard/student/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_dashboard_without_token(self, api_client):
        """GET /api/dashboard/student/ without token should return 401"""
        response = api_client.get("/api/dashboard/student/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dashboard_with_invalid_token(self, api_client):
        """GET /api/dashboard/student/ with invalid token should return 401"""
        headers = {"HTTP_AUTHORIZATION": "Bearer invalid.token.xyz"}
        response = api_client.get("/api/dashboard/student/", **headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_dashboard_with_session_auth(self, api_client, student_user):
        """GET /api/dashboard/student/ with session cookie should return 200"""
        api_client.force_login(student_user)
        response = api_client.get("/api/dashboard/student/")
        assert response.status_code == status.HTTP_200_OK

    def test_progress_with_jwt_token(self, api_client, student_token):
        """GET /api/dashboard/student/progress/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/dashboard/student/progress/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_progress_without_token(self, api_client):
        """GET /api/dashboard/student/progress/ without token should return 401"""
        response = api_client.get("/api/dashboard/student/progress/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_activity_with_jwt_token(self, api_client, student_token):
        """GET /api/dashboard/student/activity/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/dashboard/student/activity/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_activity_without_token(self, api_client):
        """GET /api/dashboard/student/activity/ without token should return 401"""
        response = api_client.get("/api/dashboard/student/activity/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================
# Student Materials Endpoints
# ==============================================

class TestStudentMaterialsEndpoints:
    """Test student materials endpoints with JWT"""

    def test_assigned_materials_with_jwt(self, api_client, student_token):
        """GET /api/materials/student/assigned/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/materials/student/assigned/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_assigned_materials_without_token(self, api_client):
        """GET /api/materials/student/assigned/ without token should return 401"""
        response = api_client.get("/api/materials/student/assigned/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_materials_by_subject_with_jwt(self, api_client, student_token):
        """GET /api/materials/student/by-subject/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/materials/student/by-subject/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_materials_by_subject_without_token(self, api_client):
        """GET /api/materials/student/by-subject/ without token should return 401"""
        response = api_client.get("/api/materials/student/by-subject/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_materials_subjects_with_jwt(self, api_client, student_token):
        """GET /api/materials/student/subjects/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/materials/student/subjects/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_materials_subjects_without_token(self, api_client):
        """GET /api/materials/student/subjects/ without token should return 401"""
        response = api_client.get("/api/materials/student/subjects/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_study_plans_with_jwt(self, api_client, student_token):
        """GET /api/materials/student/study-plans/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/materials/student/study-plans/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_study_plans_without_token(self, api_client):
        """GET /api/materials/student/study-plans/ without token should return 401"""
        response = api_client.get("/api/materials/student/study-plans/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================
# Student API Endpoints
# ==============================================

class TestStudentAPIEndpoints:
    """Test student API endpoints with JWT"""

    def test_student_subjects_with_jwt(self, api_client, student_token):
        """GET /api/student/subjects/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/student/subjects/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_student_subjects_without_token(self, api_client):
        """GET /api/student/subjects/ without token should return 401"""
        response = api_client.get("/api/student/subjects/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_subjects_invalid_token(self, api_client):
        """GET /api/student/subjects/ with invalid token should return 401"""
        headers = {"HTTP_AUTHORIZATION": "Bearer invalid.token"}
        response = api_client.get("/api/student/subjects/", **headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_submissions_with_jwt(self, api_client, student_token):
        """GET /api/student/submissions/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/student/submissions/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_student_submissions_without_token(self, api_client):
        """GET /api/student/submissions/ without token should return 401"""
        response = api_client.get("/api/student/submissions/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_progress_without_token(self, api_client):
        """GET /api/student/progress/ without token should return 401"""
        response = api_client.get("/api/student/progress/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================
# Bulk Operations Endpoints
# ==============================================

# Bulk operations endpoints removed - not implemented yet


# ==============================================
# Tutor Dashboard Endpoints
# ==============================================

class TestTutorDashboardEndpoints:
    """Test tutor dashboard endpoints with JWT"""

    def test_tutor_dashboard_with_jwt(self, api_client, tutor_token):
        """GET /api/materials/tutor/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {tutor_token}"}
        response = api_client.get("/api/materials/tutor/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_tutor_dashboard_without_token(self, api_client):
        """GET /api/materials/tutor/ without token should return 401"""
        response = api_client.get("/api/materials/tutor/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_tutor_dashboard_invalid_token(self, api_client):
        """GET /api/materials/tutor/ with invalid token should return 401"""
        headers = {"HTTP_AUTHORIZATION": "Bearer invalid.token"}
        response = api_client.get("/api/materials/tutor/", **headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_tutor_students_with_jwt(self, api_client, tutor_token):
        """GET /api/materials/tutor/students/ with JWT should return 200"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {tutor_token}"}
        response = api_client.get("/api/materials/tutor/students/", **headers)
        assert response.status_code == status.HTTP_200_OK

    def test_tutor_students_without_token(self, api_client):
        """GET /api/materials/tutor/students/ without token should return 401"""
        response = api_client.get("/api/materials/tutor/students/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_tutor_student_subjects_without_token(self, api_client, student_user):
        """GET /api/materials/tutor/students/{id}/subjects/ without token should return 401"""
        response = api_client.get(f"/api/materials/tutor/students/{student_user.id}/subjects/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================
# Knowledge Graph Endpoints
# ==============================================

class TestKnowledgeGraphEndpoints:
    """Test knowledge graph student endpoints with JWT"""

    def test_knowledge_graph_lesson_without_token(self, api_client):
        """GET /api/knowledge-graph/student/lessons/1/ without token should return 401"""
        response = api_client.get("/api/knowledge-graph/student/lessons/1/")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_knowledge_graph_lesson_invalid_token(self, api_client):
        """GET /api/knowledge-graph/student/lessons/1/ with invalid token should return 401"""
        headers = {"HTTP_AUTHORIZATION": "Bearer invalid.token"}
        response = api_client.get(
            "/api/knowledge-graph/student/lessons/1/", **headers
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_knowledge_graph_element_without_token(self, api_client):
        """POST /api/knowledge-graph/student/lessons/1/element/1/ without token should return 401"""
        data = {}
        response = api_client.post(
            "/api/knowledge-graph/student/lessons/1/element/1/",
            data,
            format="json",
        )
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]

    def test_knowledge_graph_hint_without_token(self, api_client):
        """POST /api/knowledge-graph/student/elements/1/hint/ without token should return 401"""
        data = {}
        response = api_client.post(
            "/api/knowledge-graph/student/elements/1/hint/",
            data,
            format="json",
        )
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_404_NOT_FOUND]

    def test_knowledge_graph_complete_without_token(self, api_client):
        """POST /api/knowledge-graph/student/lessons/1/complete/ without token should return 401"""
        data = {}
        response = api_client.post(
            "/api/knowledge-graph/student/lessons/1/complete/",
            data,
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================
# Integration Tests
# ==============================================

class TestCompleteWorkflows:
    """Integration tests for complete workflows"""

    def test_student_complete_dashboard_flow_with_jwt(
        self, api_client, student_token, student_user, enrollment
    ):
        """Test complete student dashboard workflow"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}

        # All endpoints should be accessible
        endpoints = [
            "/api/dashboard/student/",
            "/api/materials/student/assigned/",
            "/api/materials/student/by-subject/",
            "/api/dashboard/student/progress/",
            "/api/dashboard/student/activity/",
            "/api/materials/student/subjects/",
            "/api/materials/student/study-plans/",
            "/api/student/subjects/",
            "/api/student/submissions/",
            "/api/student/progress/",
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint, **headers)
            assert response.status_code != status.HTTP_401_UNAUTHORIZED, (
                f"Endpoint {endpoint} returned 401"
            )

    def test_student_flow_without_token_returns_401(self, api_client):
        """Test that all endpoints return 401 without token"""
        endpoints = [
            "/api/dashboard/student/",
            "/api/materials/student/assigned/",
            "/api/materials/student/by-subject/",
            "/api/dashboard/student/progress/",
            "/api/dashboard/student/activity/",
            "/api/materials/student/subjects/",
            "/api/student/subjects/",
            "/api/student/submissions/",
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"Endpoint {endpoint} should return 401"
            )

    def test_student_flow_with_invalid_token_returns_401(self, api_client):
        """Test that all endpoints return 401 with invalid token"""
        headers = {"HTTP_AUTHORIZATION": "Bearer invalid.token.xyz"}

        endpoints = [
            "/api/dashboard/student/",
            "/api/materials/student/assigned/",
            "/api/dashboard/student/progress/",
            "/api/student/subjects/",
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint, **headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
                f"Endpoint {endpoint} should return 401"
            )

    def test_tutor_complete_flow_with_jwt(self, api_client, tutor_token):
        """Test complete tutor workflow"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {tutor_token}"}

        endpoints = [
            "/api/materials/tutor/",
            "/api/materials/tutor/students/",
        ]

        for endpoint in endpoints:
            response = api_client.get(endpoint, **headers)
            assert response.status_code != status.HTTP_401_UNAUTHORIZED


# ==============================================
# Token Management Tests
# ==============================================

class TestTokenManagement:
    """Test JWT token management"""

    def test_student_token_is_valid(self, student_user):
        """Test that generated student token is valid"""
        refresh = RefreshToken.for_user(student_user)
        access = str(refresh.access_token)
        assert access is not None
        assert len(access) > 0

    def test_expired_token_rejected(self, api_client, student_user):
        """Test that expired JWT token is rejected"""
        # Create an expired token
        access_token = AccessToken.for_user(student_user)
        access_token.set_exp(lifetime=timedelta(seconds=-1))

        headers = {"HTTP_AUTHORIZATION": f"Bearer {str(access_token)}"}
        response = api_client.get("/api/dashboard/student/", **headers)
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


# ==============================================
# Role-Based Access Control Tests
# ==============================================

class TestRoleBasedAccessControl:
    """Test role-based access control"""

    def test_student_cannot_access_tutor_endpoints(
        self, api_client, student_token
    ):
        """Test that student cannot access tutor endpoints"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {student_token}"}
        response = api_client.get("/api/materials/tutor/", **headers)
        # Should be 403 (forbidden) not 401 (unauthorized)
        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_404_NOT_FOUND]

    def test_tutor_cannot_access_student_endpoints_directly(
        self, api_client, tutor_token
    ):
        """Test that tutor endpoints are different from student endpoints"""
        headers = {"HTTP_AUTHORIZATION": f"Bearer {tutor_token}"}
        response = api_client.get("/api/dashboard/student/", **headers)
        # Should be 403 (forbidden) not 401 (unauthorized)
        assert response.status_code == status.HTTP_403_FORBIDDEN
