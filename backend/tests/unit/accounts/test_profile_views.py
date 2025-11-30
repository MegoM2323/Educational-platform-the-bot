"""
Unit tests for Profile API views.

Tests coverage for:
- StudentProfileView (GET/PATCH /api/profile/student/)
- TeacherProfileView (GET/PATCH /api/profile/teacher/)
- TutorProfileView (GET/PATCH /api/profile/tutor/)

Test cases for each view:
- GET returns user + profile data (success)
- PATCH updates user fields (first_name, last_name, email, phone)
- PATCH updates profile fields (role-specific)
- PATCH uploads avatar (multipart/form-data)
- Permission denied if wrong role
- Permission denied if not authenticated
- 404 if profile doesn't exist
- Validation errors (invalid email, etc.)
- Can only edit own profile

Usage:
    pytest backend/tests/unit/accounts/test_profile_views.py -v
    pytest backend/tests/unit/accounts/test_profile_views.py --cov=accounts.profile_views --cov-report=html
"""
import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from accounts.models import StudentProfile, TeacherProfile, TutorProfile
from materials.models import Subject, TeacherSubject

User = get_user_model()


@pytest.fixture
def api_client():
    """Fixture for REST API client"""
    return APIClient()


@pytest.fixture
def student_with_profile(db):
    """Create student user with profile.

    Note: In test mode, auto_create_user_profile signal is disabled,
    so we explicitly create the profile here.
    """
    user = User.objects.create_user(
        username='student_test',
        email='student@test.com',
        password='TestPass123!',
        role=User.Role.STUDENT,
        first_name='Иван',
        last_name='Иванов',
        phone='+79001234567'
    )
    profile = StudentProfile.objects.create(user=user)
    profile.grade = '10'
    profile.goal = 'Подготовка к ЕГЭ'
    profile.telegram = '@ivanov'
    profile.save()
    return user


@pytest.fixture
def teacher_with_profile(db):
    """Create teacher user with profile.

    Note: In test mode, auto_create_user_profile signal is disabled,
    so we explicitly create the profile here.
    """
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
def tutor_with_profile(db):
    """Create tutor user with profile.

    Note: In test mode, auto_create_user_profile signal is disabled,
    so we explicitly create the profile here.
    """
    user = User.objects.create_user(
        username='tutor_test',
        email='tutor@test.com',
        password='TestPass123!',
        role=User.Role.TUTOR,
        first_name='Сергей',
        last_name='Сидоров',
        phone='+79007654321'
    )
    profile = TutorProfile.objects.create(user=user)
    profile.specialization = 'Тьютор по математике'
    profile.experience_years = 3
    profile.bio = 'Опытный тьютор'
    profile.telegram = '@sidorov'
    profile.save()
    return user


@pytest.fixture
def sample_subjects(db):
    """Create sample subjects for testing"""
    math = Subject.objects.create(name='Математика', description='Курс математики')
    physics = Subject.objects.create(name='Физика', description='Курс физики')
    return [math, physics]


@pytest.fixture
def sample_avatar():
    """Create sample avatar image for upload testing"""
    from PIL import Image
    from io import BytesIO

    image = Image.new('RGB', (100, 100), color='red')
    buffer = BytesIO()
    image.save(buffer, format='PNG')
    buffer.seek(0)

    return SimpleUploadedFile(
        name='test_avatar.png',
        content=buffer.read(),
        content_type='image/png'
    )


# ============================================================================
# StudentProfileView Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.django_db
class TestStudentProfileView:
    """Tests for StudentProfileView (GET/PATCH /api/profile/student/)"""

    # ========== GET Tests (Success) ==========

    def test_student_can_get_own_profile(self, api_client, student_with_profile):
        """Student can retrieve their own profile"""
        # Arrange
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/student/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'profile' in response.data

        # Check user data
        user_data = response.data['user']
        assert user_data['id'] == student_with_profile.id
        assert user_data['email'] == 'student@test.com'
        assert user_data['first_name'] == 'Иван'
        assert user_data['last_name'] == 'Иванов'
        assert user_data['phone'] == '+79001234567'

        # Check profile data
        profile_data = response.data['profile']
        assert profile_data['grade'] == '10'
        assert profile_data['goal'] == 'Подготовка к ЕГЭ'
        assert profile_data['telegram'] == '@ivanov'

    # ========== GET Tests (Errors) ==========

    def test_get_student_profile_unauthenticated(self, api_client):
        """Unauthenticated user cannot access student profile"""
        # Act
        response = api_client.get('/api/auth/profile/student/')

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_student_profile_wrong_role(self, api_client, teacher_with_profile):
        """Teacher cannot access student profile endpoint"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/student/')

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.data
        assert 'students' in response.data['error'].lower()

    def test_get_student_profile_not_found(self, api_client, student_with_profile):
        """404 if student profile doesn't exist"""
        # Arrange
        StudentProfile.objects.filter(user=student_with_profile).delete()
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/student/')

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'error' in response.data
        assert 'not found' in response.data['error'].lower()

    # ========== PATCH Tests (Success) ==========

    def test_student_can_update_user_fields(self, api_client, student_with_profile):
        """Student can update their user fields (first_name, last_name, email, phone)"""
        # Arrange
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'first_name': 'Петр',
            'last_name': 'Петров',
            'email': 'petrov@test.com',
            'phone': '+79111111111'
        }

        # Act
        response = api_client.patch('/api/auth/profile/student/', update_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert 'message' in response.data
        assert 'updated successfully' in response.data['message'].lower()

        # Verify database update
        student_with_profile.refresh_from_db()
        assert student_with_profile.first_name == 'Петр'
        assert student_with_profile.last_name == 'Петров'
        assert student_with_profile.email == 'petrov@test.com'
        assert student_with_profile.phone == '+79111111111'

    def test_student_can_update_profile_fields(self, api_client, student_with_profile):
        """Student can update their profile fields (grade, goal, telegram)"""
        # Arrange
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'grade': '11',
            'goal': 'Поступление в МГУ',
            'telegram': '@new_username'
        }

        # Act
        response = api_client.patch('/api/auth/profile/student/', update_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify profile update
        profile = StudentProfile.objects.get(user=student_with_profile)
        assert profile.grade == '11'
        assert profile.goal == 'Поступление в МГУ'
        assert profile.telegram == '@new_username'

    def test_student_can_upload_avatar(self, api_client, student_with_profile, sample_avatar):
        """Student can upload avatar image"""
        # Arrange
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch(
            '/api/auth/profile/student/',
            {'avatar': sample_avatar},
            format='multipart'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        student_with_profile.refresh_from_db()
        assert student_with_profile.avatar is not None
        assert 'user' in response.data
        assert response.data['user']['avatar'] is not None

    def test_student_can_update_mixed_fields(self, api_client, student_with_profile):
        """Student can update both user and profile fields in single request"""
        # Arrange
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'first_name': 'Новое Имя',
            'grade': '12',
            'goal': 'Новая цель'
        }

        # Act
        response = api_client.patch('/api/auth/profile/student/', update_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        student_with_profile.refresh_from_db()
        profile = student_with_profile.student_profile

        assert student_with_profile.first_name == 'Новое Имя'
        assert profile.grade == '12'
        assert profile.goal == 'Новая цель'

    # ========== PATCH Tests (Validation Errors) ==========

    def test_student_update_invalid_email(self, api_client, student_with_profile):
        """PATCH with invalid email returns validation error"""
        # Arrange
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch('/api/auth/profile/student/', {'email': 'not-an-email'})

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_student_update_invalid_telegram(self, api_client, student_with_profile):
        """PATCH with invalid telegram returns validation error"""
        # Arrange
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch('/api/auth/profile/student/', {'telegram': '!@invalid'})

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ========== PATCH Tests (Permission Errors) ==========

    def test_patch_student_profile_unauthenticated(self, api_client):
        """Unauthenticated user cannot update student profile"""
        # Act
        response = api_client.patch('/api/auth/profile/student/', {'first_name': 'Test'})

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_student_profile_wrong_role(self, api_client, teacher_with_profile):
        """Teacher cannot update student profile endpoint"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch('/api/auth/profile/student/', {'first_name': 'Test'})

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# TeacherProfileView Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.django_db
class TestTeacherProfileView:
    """Tests for TeacherProfileView (GET/PATCH /api/profile/teacher/)"""

    # ========== GET Tests (Success) ==========

    def test_teacher_can_get_own_profile(self, api_client, teacher_with_profile):
        """Teacher can retrieve their own profile"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/teacher/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'profile' in response.data

        # Check user data
        user_data = response.data['user']
        assert user_data['email'] == 'teacher@test.com'
        assert user_data['first_name'] == 'Мария'
        assert user_data['last_name'] == 'Петрова'

        # Check profile data
        profile_data = response.data['profile']
        assert profile_data['experience_years'] == 5
        assert profile_data['bio'] == 'Преподаватель математики'

    # ========== GET Tests (Errors) ==========

    def test_get_teacher_profile_unauthenticated(self, api_client):
        """Unauthenticated user cannot access teacher profile"""
        # Act
        response = api_client.get('/api/auth/profile/teacher/')

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_teacher_profile_wrong_role(self, api_client, student_with_profile):
        """Student cannot access teacher profile endpoint"""
        # Arrange
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/teacher/')

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'teachers' in response.data['error'].lower()

    def test_get_teacher_profile_not_found(self, api_client, teacher_with_profile):
        """404 if teacher profile doesn't exist"""
        # Arrange
        TeacherProfile.objects.filter(user=teacher_with_profile).delete()
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/teacher/')

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ========== PATCH Tests (Success) ==========

    def test_teacher_can_update_user_fields(self, api_client, teacher_with_profile):
        """Teacher can update their user fields"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'first_name': 'Анна',
            'last_name': 'Смирнова',
            'phone': '+79222222222'
        }

        # Act
        response = api_client.patch('/api/auth/profile/teacher/', update_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        teacher_with_profile.refresh_from_db()
        assert teacher_with_profile.first_name == 'Анна'
        assert teacher_with_profile.last_name == 'Смирнова'
        assert teacher_with_profile.phone == '+79222222222'

    def test_teacher_can_update_profile_fields(self, api_client, teacher_with_profile):
        """Teacher can update their profile fields (experience_years, bio, telegram)"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'experience_years': 10,
            'bio': 'Опытный преподаватель',
            'telegram': '@new_teacher'
        }

        # Act
        response = api_client.patch('/api/auth/profile/teacher/', update_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        profile = TeacherProfile.objects.get(user=teacher_with_profile)
        assert profile.experience_years == 10
        assert profile.bio == 'Опытный преподаватель'
        assert profile.telegram == '@new_teacher'

    def test_teacher_can_upload_avatar(self, api_client, teacher_with_profile, sample_avatar):
        """Teacher can upload avatar image"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch(
            '/api/auth/profile/teacher/',
            {'avatar': sample_avatar},
            format='multipart'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        teacher_with_profile.refresh_from_db()
        assert teacher_with_profile.avatar is not None

    def test_teacher_can_update_subject_ids(self, api_client, teacher_with_profile, sample_subjects):
        """Teacher can update their subject assignments via subject_ids"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        subject_ids = [subject.id for subject in sample_subjects]

        # Act
        response = api_client.patch(
            '/api/auth/profile/teacher/',
            {'subject_ids': subject_ids},
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK

        # Verify TeacherSubject records created
        teacher_subjects = TeacherSubject.objects.filter(
            teacher=teacher_with_profile,
            is_active=True
        )
        assert teacher_subjects.count() == len(subject_ids)
        assert set(teacher_subjects.values_list('subject_id', flat=True)) == set(subject_ids)

    def test_teacher_can_remove_subjects(self, api_client, teacher_with_profile, sample_subjects):
        """Teacher can remove subjects by updating subject_ids with empty list"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # First, add subjects
        for subject in sample_subjects:
            TeacherSubject.objects.create(
                teacher=teacher_with_profile,
                subject=subject,
                is_active=True
            )

        # Act - remove all subjects
        response = api_client.patch(
            '/api/auth/profile/teacher/',
            {'subject_ids': []},
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        active_subjects = TeacherSubject.objects.filter(
            teacher=teacher_with_profile,
            is_active=True
        )
        assert active_subjects.count() == 0

    # ========== PATCH Tests (Validation Errors) ==========

    def test_teacher_update_invalid_subject_ids(self, api_client, teacher_with_profile):
        """PATCH with invalid subject_ids format returns error"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch(
            '/api/auth/profile/teacher/',
            {'subject_ids': 'not-a-list'},
            format='json'
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_teacher_update_negative_experience(self, api_client, teacher_with_profile):
        """PATCH with negative experience_years returns validation error"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch('/api/auth/profile/teacher/', {'experience_years': -5})

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ========== PATCH Tests (Permission Errors) ==========

    def test_patch_teacher_profile_unauthenticated(self, api_client):
        """Unauthenticated user cannot update teacher profile"""
        # Act
        response = api_client.patch('/api/auth/profile/teacher/', {'first_name': 'Test'})

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_teacher_profile_wrong_role(self, api_client, tutor_with_profile):
        """Tutor cannot update teacher profile endpoint"""
        # Arrange
        token = Token.objects.create(user=tutor_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch('/api/auth/profile/teacher/', {'first_name': 'Test'})

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN


# ============================================================================
# TutorProfileView Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.django_db
class TestTutorProfileView:
    """Tests for TutorProfileView (GET/PATCH /api/profile/tutor/)"""

    # ========== GET Tests (Success) ==========

    def test_tutor_can_get_own_profile(self, api_client, tutor_with_profile):
        """Tutor can retrieve their own profile"""
        # Arrange
        token = Token.objects.create(user=tutor_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/tutor/')

        # Assert
        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'profile' in response.data

        # Check user data
        user_data = response.data['user']
        assert user_data['email'] == 'tutor@test.com'
        assert user_data['first_name'] == 'Сергей'
        assert user_data['last_name'] == 'Сидоров'

        # Check profile data
        profile_data = response.data['profile']
        assert profile_data['specialization'] == 'Тьютор по математике'
        assert profile_data['experience_years'] == 3
        assert profile_data['bio'] == 'Опытный тьютор'

    # ========== GET Tests (Errors) ==========

    def test_get_tutor_profile_unauthenticated(self, api_client):
        """Unauthenticated user cannot access tutor profile"""
        # Act
        response = api_client.get('/api/auth/profile/tutor/')

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_tutor_profile_wrong_role(self, api_client, student_with_profile):
        """Student cannot access tutor profile endpoint"""
        # Arrange
        token = Token.objects.create(user=student_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/tutor/')

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'tutors' in response.data['error'].lower()

    def test_get_tutor_profile_not_found(self, api_client, tutor_with_profile):
        """404 if tutor profile doesn't exist"""
        # Arrange
        TutorProfile.objects.filter(user=tutor_with_profile).delete()
        token = Token.objects.create(user=tutor_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.get('/api/auth/profile/tutor/')

        # Assert
        assert response.status_code == status.HTTP_404_NOT_FOUND

    # ========== PATCH Tests (Success) ==========

    def test_tutor_can_update_user_fields(self, api_client, tutor_with_profile):
        """Tutor can update their user fields"""
        # Arrange
        token = Token.objects.create(user=tutor_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'first_name': 'Алексей',
            'last_name': 'Козлов',
            'email': 'new_tutor@test.com',
            'phone': '+79333333333'
        }

        # Act
        response = api_client.patch('/api/auth/profile/tutor/', update_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        tutor_with_profile.refresh_from_db()
        assert tutor_with_profile.first_name == 'Алексей'
        assert tutor_with_profile.last_name == 'Козлов'
        assert tutor_with_profile.email == 'new_tutor@test.com'
        assert tutor_with_profile.phone == '+79333333333'

    def test_tutor_can_update_profile_fields(self, api_client, tutor_with_profile):
        """Tutor can update their profile fields (specialization, experience_years, bio, telegram)"""
        # Arrange
        token = Token.objects.create(user=tutor_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'specialization': 'Тьютор по физике',
            'experience_years': 7,
            'bio': 'Высококвалифицированный тьютор',
            'telegram': '@new_tutor'
        }

        # Act
        response = api_client.patch('/api/auth/profile/tutor/', update_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        profile = TutorProfile.objects.get(user=tutor_with_profile)
        assert profile.specialization == 'Тьютор по физике'
        assert profile.experience_years == 7
        assert profile.bio == 'Высококвалифицированный тьютор'
        assert profile.telegram == '@new_tutor'

    def test_tutor_can_upload_avatar(self, api_client, tutor_with_profile, sample_avatar):
        """Tutor can upload avatar image"""
        # Arrange
        token = Token.objects.create(user=tutor_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch(
            '/api/auth/profile/tutor/',
            {'avatar': sample_avatar},
            format='multipart'
        )

        # Assert
        assert response.status_code == status.HTTP_200_OK
        tutor_with_profile.refresh_from_db()
        assert tutor_with_profile.avatar is not None
        assert response.data['user']['avatar'] is not None

    def test_tutor_can_update_mixed_fields(self, api_client, tutor_with_profile):
        """Tutor can update both user and profile fields in single request"""
        # Arrange
        token = Token.objects.create(user=tutor_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        update_data = {
            'first_name': 'Новое Имя',
            'specialization': 'Новая специализация',
            'bio': 'Новая биография'
        }

        # Act
        response = api_client.patch('/api/auth/profile/tutor/', update_data)

        # Assert
        assert response.status_code == status.HTTP_200_OK
        tutor_with_profile.refresh_from_db()
        profile = tutor_with_profile.tutor_profile

        assert tutor_with_profile.first_name == 'Новое Имя'
        assert profile.specialization == 'Новая специализация'
        assert profile.bio == 'Новая биография'

    # ========== PATCH Tests (Validation Errors) ==========

    def test_tutor_update_too_long_specialization(self, api_client, tutor_with_profile):
        """PATCH with too long specialization returns validation error"""
        # Arrange
        token = Token.objects.create(user=tutor_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch(
            '/api/auth/profile/tutor/',
            {'specialization': 'A' * 600}  # Too long
        )

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_tutor_update_invalid_experience(self, api_client, tutor_with_profile):
        """PATCH with invalid experience_years returns validation error"""
        # Arrange
        token = Token.objects.create(user=tutor_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch('/api/auth/profile/tutor/', {'experience_years': -10})

        # Assert
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    # ========== PATCH Tests (Permission Errors) ==========

    def test_patch_tutor_profile_unauthenticated(self, api_client):
        """Unauthenticated user cannot update tutor profile"""
        # Act
        response = api_client.patch('/api/auth/profile/tutor/', {'first_name': 'Test'})

        # Assert
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_patch_tutor_profile_wrong_role(self, api_client, teacher_with_profile):
        """Teacher cannot update tutor profile endpoint"""
        # Arrange
        token = Token.objects.create(user=teacher_with_profile)
        api_client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')

        # Act
        response = api_client.patch('/api/auth/profile/tutor/', {'first_name': 'Test'})

        # Assert
        assert response.status_code == status.HTTP_403_FORBIDDEN
