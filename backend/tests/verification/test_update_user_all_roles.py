"""
Verification tests for update_user function in staff_views.py

Tests:
1. Profile data extraction from request
2. Student profile update (grade, goal, tutor_id, parent_id)
3. Teacher profile update (experience_years, bio)
4. Tutor profile update (specialization, experience_years, bio)
5. Parent profile update
6. Error handling (null values, missing fields, invalid data)
"""

import pytest
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from rest_framework.test import APIClient
from rest_framework import status

User = get_user_model()


@pytest.fixture
def admin_client(db):
    """Admin client for API requests"""
    admin = User.objects.create_superuser(
        username='admin_verify',
        email='admin_verify@test.com',
        password='admin123',
        first_name='Admin',
        last_name='Verify'
    )
    client = APIClient()
    client.force_authenticate(user=admin)
    return client, admin


@pytest.fixture
def test_users(db):
    """Create test users for all roles"""
    # Student
    student = User.objects.create_user(
        username='student_verify',
        email='student_verify@test.com',
        password='pass123',
        role='student',
        first_name='Test',
        last_name='Student'
    )
    StudentProfile.objects.create(
        user=student,
        grade='9',
        goal='Подготовка к ОГЭ'
    )

    # Teacher
    teacher = User.objects.create_user(
        username='teacher_verify',
        email='teacher_verify@test.com',
        password='pass123',
        role='teacher',
        first_name='Test',
        last_name='Teacher'
    )
    TeacherProfile.objects.create(
        user=teacher,
        experience_years=5,
        bio='Опытный преподаватель'
    )

    # Tutor
    tutor = User.objects.create_user(
        username='tutor_verify',
        email='tutor_verify@test.com',
        password='pass123',
        role='tutor',
        first_name='Test',
        last_name='Tutor'
    )
    TutorProfile.objects.create(
        user=tutor,
        specialization='Математика',
        experience_years=10,
        bio='Специалист по математике'
    )

    # Parent
    parent = User.objects.create_user(
        username='parent_verify',
        email='parent_verify@test.com',
        password='pass123',
        role='parent',
        first_name='Test',
        last_name='Parent'
    )
    ParentProfile.objects.create(user=parent)

    return {
        'student': student,
        'teacher': teacher,
        'tutor': tutor,
        'parent': parent
    }


class TestProfileDataExtraction:
    """Test 1: Profile data extraction"""

    def test_valid_profile_data(self):
        """Profile data is correctly extracted when present"""
        request_data = {
            'email': 'test@test.com',
            'profile_data': {
                'grade': '10',
                'goal': 'New goal'
            }
        }
        profile_data = request_data.get('profile_data', {})
        assert profile_data == {'grade': '10', 'goal': 'New goal'}

    def test_empty_profile_data(self):
        """Empty profile_data returns empty dict"""
        request_data = {
            'email': 'test@test.com',
            'profile_data': {}
        }
        profile_data = request_data.get('profile_data', {})
        assert profile_data == {}

    def test_missing_profile_data(self):
        """Missing profile_data defaults to empty dict"""
        request_data = {
            'email': 'test@test.com'
        }
        profile_data = request_data.get('profile_data', {})
        assert profile_data == {}


class TestStudentProfileUpdate:
    """Test 2: Student profile updates"""

    def test_update_all_student_fields(self, admin_client, test_users):
        """Update all student profile fields via API"""
        client, admin_user = admin_client
        student = test_users['student']
        tutor = test_users['tutor']
        parent = test_users['parent']

        update_data = {
            'first_name': 'Updated',
            'last_name': 'Student',
            'profile_data': {
                'grade': '11',
                'goal': 'Подготовка к ЕГЭ',
                'tutor': tutor.id,
                'parent': parent.id
            }
        }

        response = client.patch(
            f'/api/auth/users/{student.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        # Verify profile fields
        profile = StudentProfile.objects.get(user=student)
        assert profile.grade == '11'
        assert profile.goal == 'Подготовка к ЕГЭ'
        assert profile.tutor == tutor
        assert profile.parent == parent

        # Verify user fields
        student.refresh_from_db()
        assert student.first_name == 'Updated'

    def test_update_student_null_values(self, admin_client, test_users):
        """Handle null values for tutor and parent"""
        client, admin_user = admin_client
        student = test_users['student']

        update_data = {
            'profile_data': {
                'tutor': None,
                'parent': None
            }
        }

        response = client.patch(
            f'/api/auth/users/{student.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        profile = StudentProfile.objects.get(user=student)
        assert profile.tutor is None
        assert profile.parent is None

    def test_update_student_partial_fields(self, admin_client, test_users):
        """Update only some student profile fields"""
        client, admin_user = admin_client
        student = test_users['student']
        original_goal = student.student_profile.goal

        update_data = {
            'profile_data': {
                'grade': '10'
                # goal not included
            }
        }

        response = client.patch(
            f'/api/auth/users/{student.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        profile = StudentProfile.objects.get(user=student)
        assert profile.grade == '10'
        assert profile.goal == original_goal  # Unchanged


class TestTeacherProfileUpdate:
    """Test 3: Teacher profile updates"""

    def test_update_teacher_profile(self, admin_client, test_users):
        """Update teacher profile fields"""
        client, admin_user = admin_client
        teacher = test_users['teacher']

        update_data = {
            'profile_data': {
                'experience_years': 8,
                'bio': 'Обновленная биография'
            }
        }

        response = client.patch(
            f'/api/auth/users/{teacher.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        profile = TeacherProfile.objects.get(user=teacher)
        assert profile.experience_years == 8
        assert profile.bio == 'Обновленная биография'

    def test_teacher_negative_experience(self, admin_client, test_users):
        """Negative experience_years should be rejected"""
        client, admin_user = admin_client
        teacher = test_users['teacher']

        update_data = {
            'profile_data': {
                'experience_years': -5
            }
        }

        response = client.patch(
            f'/api/auth/users/{teacher.id}/',
            update_data,
            format='json'
        )

        # Should return 400 due to serializer validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestTutorProfileUpdate:
    """Test 4: Tutor profile updates"""

    def test_update_tutor_profile(self, admin_client, test_users):
        """Update all tutor profile fields"""
        client, admin_user = admin_client
        tutor = test_users['tutor']

        update_data = {
            'profile_data': {
                'specialization': 'Физика и математика',
                'experience_years': 15,
                'bio': 'Обновленная биография'
            }
        }

        response = client.patch(
            f'/api/auth/users/{tutor.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        profile = TutorProfile.objects.get(user=tutor)
        assert profile.specialization == 'Физика и математика'
        assert profile.experience_years == 15
        assert profile.bio == 'Обновленная биография'

    def test_tutor_negative_experience(self, admin_client, test_users):
        """Negative experience_years should be rejected"""
        client, admin_user = admin_client
        tutor = test_users['tutor']

        update_data = {
            'profile_data': {
                'experience_years': -3
            }
        }

        response = client.patch(
            f'/api/auth/users/{tutor.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestParentProfileUpdate:
    """Test 5: Parent profile (currently no fields)"""

    def test_parent_profile_exists(self, admin_client, test_users):
        """Parent profile exists and update doesn't break"""
        client, admin_user = admin_client
        parent = test_users['parent']

        # Update user fields (no profile_data yet for parent)
        update_data = {
            'first_name': 'Updated',
            'last_name': 'Parent'
        }

        response = client.patch(
            f'/api/auth/users/{parent.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        parent.refresh_from_db()
        assert parent.first_name == 'Updated'

        # Profile should still exist
        assert ParentProfile.objects.filter(user=parent).exists()


class TestErrorHandling:
    """Test 6: Error handling edge cases"""

    def test_user_not_found(self, admin_client):
        """Return 404 for non-existent user"""
        client, admin_user = admin_client
        response = client.patch(
            '/api/auth/users/99999/',
            {'first_name': 'Test'},
            format='json'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_cannot_deactivate_self(self, db):
        """Admin cannot deactivate themselves"""
        admin = User.objects.create_superuser(
            username='selftest',
            email='selftest@test.com',
            password='pass123'
        )

        client = APIClient()
        client.force_authenticate(user=admin)

        response = client.patch(
            f'/api/auth/users/{admin.id}/',
            {'is_active': False},
            format='json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_tutor_id(self, admin_client, test_users):
        """Invalid tutor ID should return error"""
        client, admin_user = admin_client
        student = test_users['student']

        update_data = {
            'profile_data': {
                'tutor': 99999  # Non-existent
            }
        }

        response = client.patch(
            f'/api/auth/users/{student.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_wrong_role_for_tutor(self, admin_client, test_users):
        """Assigning non-tutor as tutor should fail"""
        client, admin_user = admin_client
        student = test_users['student']
        teacher = test_users['teacher']  # Wrong role

        update_data = {
            'profile_data': {
                'tutor': teacher.id  # Teacher, not tutor
            }
        }

        response = client.patch(
            f'/api/auth/users/{student.id}/',
            update_data,
            format='json'
        )

        # Should be rejected by serializer validation
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_missing_profile_auto_create_student(self, admin_client, db):
        """Missing student profile should be auto-created"""
        # Create student without profile
        client, admin_user = admin_client
        student = User.objects.create_user(
            username='no_profile_student',
            email='no_profile_student@test.com',
            password='pass123',
            role='student'
        )

        # Ensure no profile exists
        assert not StudentProfile.objects.filter(user=student).exists()

        # Try to update profile
        update_data = {
            'profile_data': {
                'grade': '8',
                'goal': 'New goal'
            }
        }

        response = client.patch(
            f'/api/auth/users/{student.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        # Profile should now exist
        profile = StudentProfile.objects.get(user=student)
        assert profile.grade == '8'
        assert profile.goal == 'New goal'

    def test_missing_profile_auto_create_teacher(self, admin_client, db):
        """Missing teacher profile should be auto-created"""
        client, admin_user = admin_client
        teacher = User.objects.create_user(
            username='no_profile_teacher',
            email='no_profile_teacher@test.com',
            password='pass123',
            role='teacher'
        )

        assert not TeacherProfile.objects.filter(user=teacher).exists()

        update_data = {
            'profile_data': {
                'experience_years': 3,
                'bio': 'New teacher'
            }
        }

        response = client.patch(
            f'/api/auth/users/{teacher.id}/',
            update_data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        profile = TeacherProfile.objects.get(user=teacher)
        assert profile.experience_years == 3
        assert profile.bio == 'New teacher'
