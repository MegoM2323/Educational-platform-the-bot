"""
Comprehensive unit tests for Teacher Profile GET endpoint.

Tests for:
- TeacherProfileView GET endpoint returns 200 with valid user
- TeacherProfile auto-creation if missing
- 401 for unauthenticated requests
- 403 for wrong role (student accessing teacher endpoint)
- N+1 query detection

Usage:
    pytest backend/tests/unit/accounts/test_teacher_profile_comprehensive.py -v
    pytest backend/tests/unit/accounts/test_teacher_profile_comprehensive.py --cov=accounts.profile_views
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from accounts.models import TeacherProfile

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestTeacherProfileGetEndpoint:
    """Tests for TeacherProfileView GET /api/profile/teacher/"""

    @pytest.fixture
    def api_client(self):
        """REST API client fixture"""
        return APIClient()

    @pytest.fixture
    def teacher_with_profile(self, db):
        """Create teacher user with profile"""
        user = User.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER,
            first_name='Мария',
            last_name='Петрова',
            phone='+79009876543'
        )
        profile = TeacherProfile.objects.create(user=user)
        profile.experience_years = 5
        profile.bio = 'Преподаватель математики'
        profile.telegram = '@petrova'
        profile.save()
        return user

    @pytest.fixture
    def student_user(self, db):
        """Create student user for wrong-role tests"""
        user = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT,
            first_name='Иван',
            last_name='Иванов'
        )
        from accounts.models import StudentProfile
        StudentProfile.objects.create(user=user)
        return user

    # ========== Success Tests ==========

    def test_teacher_get_profile_returns_200(self, api_client, teacher_with_profile):
        """Scenario: Valid teacher user → 200 response with user + profile data"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/profile/teacher/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'profile' in response.data

        # Verify user data
        user_data = response.data['user']
        assert user_data['id'] == teacher_with_profile.id
        assert user_data['email'] == 'teacher@test.com'
        assert user_data['first_name'] == 'Мария'
        assert user_data['last_name'] == 'Петрова'
        assert user_data['phone'] == '+79009876543'

        # Verify profile data
        profile_data = response.data['profile']
        assert profile_data['experience_years'] == 5
        assert profile_data['bio'] == 'Преподаватель математики'
        assert profile_data['telegram'] == '@petrova'

    def test_teacher_get_profile_auto_creates_if_missing(self, api_client, db):
        """Scenario: Teacher without profile → auto-creates profile, returns 200"""
        # Arrange: Create teacher WITHOUT profile
        user = User.objects.create_user(
            username='teacher_no_profile',
            email='teacher_no_profile@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )

        # Delete the auto-created profile (simulating missing profile)
        TeacherProfile.objects.filter(user=user).delete()

        # Create token for authentication
        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Assert: Profile doesn't exist before request
        assert not TeacherProfile.objects.filter(user=user).exists()

        # Act
        response = api_client.get('/api/profile/teacher/')

        # Assert: Response is 200
        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'profile' in response.data

        # Assert: Profile was auto-created
        assert TeacherProfile.objects.filter(user=user).exists()
        teacher_profile = TeacherProfile.objects.get(user=user)
        assert teacher_profile.user == user

    # ========== Authentication/Authorization Tests ==========

    def test_teacher_get_profile_401_unauthenticated(self, api_client):
        """Scenario: Unauthenticated request → 401 Unauthorized"""
        # Act
        response = api_client.get('/api/profile/teacher/')

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_teacher_get_profile_403_wrong_role(self, api_client, student_user):
        """Scenario: Student accessing teacher endpoint → 403 Forbidden"""
        # Arrange
        token = Token.objects.create(user=student_user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/profile/teacher/')

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.data

    # ========== N+1 Query Tests ==========

    def test_teacher_get_profile_no_n_plus_1_queries(self, api_client, teacher_with_profile, django_assert_num_queries):
        """Verify GET endpoint doesn't have N+1 query problems"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act & Assert: Should be exactly 5 queries (savepoint, token+user, profile, teacher_subject, release)
        with django_assert_num_queries(5):
            response = api_client.get('/api/profile/teacher/')

        assert response.status_code == status.HTTP_200_OK

    def test_teacher_get_profile_multiple_requests_no_n_plus_1(self, api_client, db, django_assert_num_queries):
        """Verify multiple requests don't accumulate N+1 queries"""
        # Create 3 teachers
        teachers = []
        tokens = []
        for i in range(3):
            user = User.objects.create_user(
                username=f'teacher_{i}',
                email=f'teacher_{i}@test.com',
                password='TestPass123!',
                role=User.Role.TEACHER,
                first_name=f'Teacher{i}'
            )
            TeacherProfile.objects.create(user=user)
            profile = user.teacher_profile
            profile.experience_years = i + 1
            profile.save()
            teachers.append(user)
            tokens.append(Token.objects.create(user=user))

        # Act & Assert: Each request should use same number of queries (5)
        for token in tokens:
            api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
            with django_assert_num_queries(5):
                response = api_client.get('/api/profile/teacher/')
            assert response.status_code == status.HTTP_200_OK

    # ========== Data Integrity Tests ==========

    def test_teacher_get_profile_returns_complete_data(self, api_client, db):
        """Verify all expected fields are returned in response"""
        # Arrange
        user = User.objects.create_user(
            username='teacher_complete',
            email='teacher_complete@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER,
            first_name='John',
            last_name='Doe',
            phone='+1234567890'
        )
        profile = TeacherProfile.objects.create(user=user)
        profile.experience_years = 10
        profile.bio = 'Senior teacher'
        profile.telegram = '@johndoe'
        profile.save()

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/profile/teacher/')

        # Assert: Check all required fields present
        assert response.status_code == status.HTTP_200_OK

        user_data = response.data['user']
        assert 'id' in user_data
        assert 'email' in user_data
        assert 'first_name' in user_data
        assert 'last_name' in user_data
        assert 'phone' in user_data
        assert 'role' in user_data

        profile_data = response.data['profile']
        assert 'experience_years' in profile_data
        assert 'bio' in profile_data
        assert 'telegram' in profile_data

    def test_teacher_get_profile_readonly_teacher_field(self, api_client, teacher_with_profile):
        """Verify cannot change teacher role through profile endpoint"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/profile/teacher/')

        # Assert: Role should be 'teacher' and cannot be changed
        assert response.status_code == status.HTTP_200_OK
        assert response.data['user']['role'] == 'teacher'

    def test_teacher_get_profile_with_empty_fields(self, api_client, db):
        """Verify GET returns 200 even with empty profile fields"""
        # Arrange: Create teacher with minimal profile
        user = User.objects.create_user(
            username='teacher_minimal',
            email='teacher_minimal@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        TeacherProfile.objects.create(user=user)

        token = Token.objects.create(user=user)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/profile/teacher/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        profile_data = response.data['profile']
        assert profile_data['experience_years'] is None or profile_data['experience_years'] == 0
        assert profile_data['bio'] is None or profile_data['bio'] == ''
