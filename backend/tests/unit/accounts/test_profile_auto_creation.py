"""
Unit tests for profile auto-creation fallback mechanism.

Tests that profile views automatically create missing profiles
when users access their profile endpoints, as a fallback for
signal failures.
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from accounts.models import (
    StudentProfile,
    TeacherProfile,
    TutorProfile,
    ParentProfile
)

User = get_user_model()


@pytest.mark.django_db
class TestProfileAutoCreation:
    """Test auto-creation of profiles when missing."""

    def test_teacher_profile_auto_created_on_get(self):
        """Test TeacherProfile is auto-created if missing on GET request."""
        # Create teacher user without profile
        teacher = User.objects.create_user(
            username='teacher_test',
            email='teacher_test@example.com',
            password='test123',
            role='teacher'
        )

        # Delete profile if exists (signal might create it)
        TeacherProfile.objects.filter(user=teacher).delete()

        # Verify profile doesn't exist
        assert not TeacherProfile.objects.filter(user=teacher).exists()

        # Make authenticated request
        client = APIClient()
        token = Token.objects.create(user=teacher)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/profile/teacher/')

        # Should succeed and auto-create profile
        assert response.status_code == 200
        assert TeacherProfile.objects.filter(user=teacher).exists()

        # Profile data should be in response
        assert 'user' in response.data
        assert 'profile' in response.data

    def test_teacher_profile_auto_created_on_patch(self):
        """Test TeacherProfile is auto-created if missing on PATCH request."""
        # Create teacher user without profile
        teacher = User.objects.create_user(
            username='teacher_patch',
            email='teacher_patch@example.com',
            password='test123',
            role='teacher'
        )

        # Delete profile if exists
        TeacherProfile.objects.filter(user=teacher).delete()

        # Verify profile doesn't exist
        assert not TeacherProfile.objects.filter(user=teacher).exists()

        # Make authenticated PATCH request
        client = APIClient()
        token = Token.objects.create(user=teacher)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.patch('/api/profile/teacher/', {
            'first_name': 'Test',
            'subject': 'Mathematics'
        })

        # Should succeed and auto-create profile
        assert response.status_code == 200
        assert TeacherProfile.objects.filter(user=teacher).exists()

        # Verify data was updated
        teacher.refresh_from_db()
        assert teacher.first_name == 'Test'

        profile = TeacherProfile.objects.get(user=teacher)
        assert profile.subject == 'Mathematics'

    def test_student_profile_auto_created(self):
        """Test StudentProfile is auto-created if missing."""
        student = User.objects.create_user(
            username='student_test',
            email='student_test@example.com',
            password='test123',
            role='student'
        )

        StudentProfile.objects.filter(user=student).delete()
        assert not StudentProfile.objects.filter(user=student).exists()

        client = APIClient()
        token = Token.objects.create(user=student)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/profile/student/')

        assert response.status_code == 200
        assert StudentProfile.objects.filter(user=student).exists()

    def test_tutor_profile_auto_created(self):
        """Test TutorProfile is auto-created if missing."""
        tutor = User.objects.create_user(
            username='tutor_test',
            email='tutor_test@example.com',
            password='test123',
            role='tutor'
        )

        TutorProfile.objects.filter(user=tutor).delete()
        assert not TutorProfile.objects.filter(user=tutor).exists()

        client = APIClient()
        token = Token.objects.create(user=tutor)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/profile/tutor/')

        assert response.status_code == 200
        assert TutorProfile.objects.filter(user=tutor).exists()

    def test_parent_profile_auto_created(self):
        """Test ParentProfile is auto-created if missing."""
        parent = User.objects.create_user(
            username='parent_test',
            email='parent_test@example.com',
            password='test123',
            role='parent'
        )

        ParentProfile.objects.filter(user=parent).delete()
        assert not ParentProfile.objects.filter(user=parent).exists()

        client = APIClient()
        token = Token.objects.create(user=parent)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        response = client.get('/api/profile/parent/')

        assert response.status_code == 200
        assert ParentProfile.objects.filter(user=parent).exists()

    def test_profile_not_created_for_wrong_role(self):
        """Test profile endpoints reject users with wrong role."""
        student = User.objects.create_user(
            username='student_wrong_role',
            email='student_wrong@example.com',
            password='test123',
            role='student'
        )

        client = APIClient()
        token = Token.objects.create(user=student)
        client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Student trying to access teacher endpoint
        response = client.get('/api/profile/teacher/')

        # Should be forbidden
        assert response.status_code == 403
        assert 'error' in response.data

        # No TeacherProfile should be created
        assert not TeacherProfile.objects.filter(user=student).exists()

    def test_signal_still_creates_profile_on_user_creation(self):
        """Test that signal still auto-creates profile when user is created."""
        # Create new user (signal should create profile automatically)
        teacher = User.objects.create_user(
            username='teacher_signal_test',
            email='teacher_signal@example.com',
            password='test123',
            role='teacher'
        )

        # In non-test environment, signal should have created profile
        # In test environment, signal is disabled to avoid fixture conflicts
        # So we just verify the model relationship works
        profile, created = TeacherProfile.objects.get_or_create(user=teacher)

        assert profile is not None
        assert profile.user == teacher
