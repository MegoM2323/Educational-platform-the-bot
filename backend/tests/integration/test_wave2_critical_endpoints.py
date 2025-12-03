"""
Integration tests for Wave 2 critical endpoints (T005-T009).

These tests verify that all critical backend endpoints work correctly
after the system audit and fixes.
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.mark.django_db
class TestT005TeacherAuthentication:
    """Test T005: Teacher login and dashboard access."""

    def test_teacher_login(self, teacher_user):
        """Teacher can login and receive token."""
        client = APIClient()
        response = client.post(
            '/api/auth/login/',
            {
                'email': teacher_user.email,
                'password': 'testpass123'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'token' in response.data['data']
        assert response.data['data']['user']['role'] == 'teacher'

    def test_teacher_dashboard_access(self, teacher_user):
        """Teacher can access their dashboard with token."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get('/api/materials/teacher/')

        assert response.status_code == status.HTTP_200_OK
        assert 'teacher_info' in response.data
        assert 'students' in response.data
        assert 'materials' in response.data


@pytest.mark.django_db
class TestT006StudentSchedule:
    """Test T006: Student schedule endpoint."""

    def test_student_schedule_endpoint_exists(self, student_user):
        """Student schedule endpoint returns 200 (not 404)."""
        client = APIClient()
        client.force_authenticate(user=student_user)

        # Note: endpoint uses underscore, not hyphen
        response = client.get('/api/scheduling/lessons/my_schedule/')

        assert response.status_code == status.HTTP_200_OK

    def test_student_schedule_returns_list(self, student_user):
        """Student schedule returns empty list when no lessons."""
        client = APIClient()
        client.force_authenticate(user=student_user)

        response = client.get('/api/scheduling/lessons/my_schedule/')

        assert response.status_code == status.HTTP_200_OK
        # Response can be empty list or paginated
        assert isinstance(response.data, (list, dict))


@pytest.mark.django_db
class TestT007ForumChats:
    """Test T007: Forum chats display."""

    def test_forum_endpoint_exists(self, student_user):
        """Forum endpoint returns 200."""
        client = APIClient()
        client.force_authenticate(user=student_user)

        response = client.get('/api/chat/forum/')

        assert response.status_code == status.HTTP_200_OK

    def test_forum_returns_data(self, student_user):
        """Forum returns valid data structure."""
        client = APIClient()
        client.force_authenticate(user=student_user)

        response = client.get('/api/chat/forum/')

        assert response.status_code == status.HTTP_200_OK
        # Check if paginated or list
        if 'results' in response.data:
            assert isinstance(response.data['results'], list)
        else:
            assert isinstance(response.data, list)


@pytest.mark.django_db
class TestT008ReportsSystem:
    """Test T008: Complete reports system."""

    def test_teacher_weekly_reports(self, teacher_user):
        """Teacher can access their weekly reports."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get('/api/reports/teacher-weekly-reports/')

        assert response.status_code == status.HTTP_200_OK

    def test_tutor_weekly_reports(self, tutor_user):
        """Tutor can access their weekly reports."""
        client = APIClient()
        client.force_authenticate(user=tutor_user)

        response = client.get('/api/reports/tutor-weekly-reports/')

        assert response.status_code == status.HTTP_200_OK

    def test_parent_views_tutor_reports(self, parent_user):
        """Parent can view tutor reports."""
        client = APIClient()
        client.force_authenticate(user=parent_user)

        response = client.get('/api/reports/tutor-weekly-reports/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestT009AssignmentsSystem:
    """Test T009: Complete assignments system."""

    def test_teacher_assignments(self, teacher_user):
        """Teacher can access assignments endpoint."""
        client = APIClient()
        client.force_authenticate(user=teacher_user)

        response = client.get('/api/assignments/')

        assert response.status_code == status.HTTP_200_OK

    def test_student_assignments(self, student_user):
        """Student can access their assignments."""
        client = APIClient()
        client.force_authenticate(user=student_user)

        response = client.get('/api/assignments/')

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestAllRolesAuthentication:
    """Verify all 4 roles can login successfully."""

    def test_student_login(self, student_user):
        """Student can login."""
        client = APIClient()
        response = client.post(
            '/api/auth/login/',
            {'email': student_user.email, 'password': 'testpass123'},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['role'] == 'student'

    def test_teacher_login(self, teacher_user):
        """Teacher can login."""
        client = APIClient()
        response = client.post(
            '/api/auth/login/',
            {'email': teacher_user.email, 'password': 'testpass123'},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['role'] == 'teacher'

    def test_tutor_login(self, tutor_user):
        """Tutor can login."""
        client = APIClient()
        response = client.post(
            '/api/auth/login/',
            {'email': tutor_user.email, 'password': 'testpass123'},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['role'] == 'tutor'

    def test_parent_login(self, parent_user):
        """Parent can login."""
        client = APIClient()
        response = client.post(
            '/api/auth/login/',
            {'email': parent_user.email, 'password': 'testpass123'},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['user']['role'] == 'parent'
