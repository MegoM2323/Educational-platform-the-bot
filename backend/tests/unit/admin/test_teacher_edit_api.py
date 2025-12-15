"""
Unit tests for teacher edit API endpoints

Tests for:
- PATCH /api/auth/teachers/{id}/ endpoint
- User field updates (email, first_name, last_name, phone, is_active)
- TeacherProfile field updates (experience_years, bio)
- Subject management via subject_ids parameter
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from accounts.models import TeacherProfile
from materials.models import Subject, TeacherSubject

User = get_user_model()


@pytest.fixture
def admin_client(db):
    """Authenticated admin client"""
    admin_user = User.objects.create_user(
        username='admin',
        email='admin@test.com',
        password='testpass123',
        is_staff=True,
        is_superuser=True,
        role='teacher'
    )
    client = APIClient()
    client.force_authenticate(user=admin_user)
    return client


@pytest.fixture
def regular_user_client(db):
    """Authenticated regular user client (not admin)"""
    user = User.objects.create_user(
        username='regular',
        email='regular@test.com',
        password='testpass123',
        role='student'
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


@pytest.fixture
def unauthenticated_client():
    """Unauthenticated client"""
    return APIClient()


@pytest.fixture
def teacher_user(db):
    """Teacher user for editing"""
    teacher = User.objects.create_user(
        username='teacher',
        email='teacher@test.com',
        password='testpass123',
        first_name='John',
        last_name='Smith',
        phone='+79991234567',
        role='teacher',
        is_active=True
    )
    TeacherProfile.objects.create(
        user=teacher,
        experience_years=3,
        bio='Old bio',
        subject='Mathematics'
    )
    return teacher


@pytest.fixture
def subjects(db):
    """Create test subjects"""
    math = Subject.objects.create(name='Mathematics', description='Math course')
    physics = Subject.objects.create(name='Physics', description='Physics course')
    chemistry = Subject.objects.create(name='Chemistry', description='Chemistry course')
    biology = Subject.objects.create(name='Biology', description='Biology course')
    return {
        'math': math,
        'physics': physics,
        'chemistry': chemistry,
        'biology': biology
    }


class TestTeacherEditEndpoint:
    """Tests for PATCH /api/auth/teachers/{id}/ endpoint"""

    def test_update_user_fields_only(self, admin_client, teacher_user):
        """Update only user fields (name, email, phone)"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'first_name': 'Jane',
                'last_name': 'Doe',
                'email': 'jane.doe@test.com',
                'phone': '+79997654321'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['user']['first_name'] == 'Jane'
        assert response.data['user']['last_name'] == 'Doe'
        assert response.data['user']['email'] == 'jane.doe@test.com'
        assert response.data['user']['phone'] == '+79997654321'

        # Verify database
        teacher_user.refresh_from_db()
        assert teacher_user.first_name == 'Jane'
        assert teacher_user.last_name == 'Doe'
        assert teacher_user.email == 'jane.doe@test.com'

    def test_update_profile_fields_only(self, admin_client, teacher_user):
        """Update only profile fields (experience_years, bio)"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'experience_years': 10,
                'bio': 'New bio'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['profile']['experience_years'] == 10
        assert response.data['profile']['bio'] == 'New bio'

        # Verify database
        teacher_user.teacher_profile.refresh_from_db()
        assert teacher_user.teacher_profile.experience_years == 10
        assert teacher_user.teacher_profile.bio == 'New bio'

    def test_update_subject_field(self, admin_client, teacher_user):
        """Update legacy 'subject' field (string)"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'subject': 'Physics'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['profile']['subject'] == 'Physics'

        # Verify database
        teacher_user.teacher_profile.refresh_from_db()
        assert teacher_user.teacher_profile.subject == 'Physics'

    def test_update_is_active_field(self, admin_client, teacher_user):
        """Update is_active status"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'is_active': False
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['user']['is_active'] is False

        # Verify database
        teacher_user.refresh_from_db()
        assert teacher_user.is_active is False

    def test_add_subjects_via_subject_ids(self, admin_client, teacher_user, subjects):
        """Add subjects via subject_ids parameter"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'subject_ids': [subjects['math'].id, subjects['physics'].id]
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        # Verify TeacherSubject records created
        active_subjects = set(
            TeacherSubject.objects.filter(
                teacher=teacher_user,
                is_active=True
            ).values_list('subject_id', flat=True)
        )
        assert active_subjects == {subjects['math'].id, subjects['physics'].id}

        # Verify response includes subjects_list
        assert 'subjects_list' in response.data['profile']
        assert 'Mathematics' in response.data['profile']['subjects_list']
        assert 'Physics' in response.data['profile']['subjects_list']

    def test_remove_subjects_via_subject_ids(self, admin_client, teacher_user, subjects):
        """Remove subjects via subject_ids update"""
        # Add initial subjects
        TeacherSubject.objects.create(
            teacher=teacher_user, subject=subjects['math'], is_active=True
        )
        TeacherSubject.objects.create(
            teacher=teacher_user, subject=subjects['physics'], is_active=True
        )
        TeacherSubject.objects.create(
            teacher=teacher_user, subject=subjects['chemistry'], is_active=True
        )

        # Remove physics and chemistry, keep only math
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'subject_ids': [subjects['math'].id]
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        # Verify active subjects
        active_subjects = set(
            TeacherSubject.objects.filter(
                teacher=teacher_user,
                is_active=True
            ).values_list('subject_id', flat=True)
        )
        assert active_subjects == {subjects['math'].id}

        # Verify inactive records still exist
        inactive_count = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=False
        ).count()
        assert inactive_count == 2

    def test_clear_all_subjects(self, admin_client, teacher_user, subjects):
        """Clear all subjects by passing empty subject_ids"""
        # Add initial subjects
        TeacherSubject.objects.create(
            teacher=teacher_user, subject=subjects['math'], is_active=True
        )
        TeacherSubject.objects.create(
            teacher=teacher_user, subject=subjects['physics'], is_active=True
        )

        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'subject_ids': []
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        # Verify all are inactive
        active_count = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True
        ).count()
        assert active_count == 0

        # Verify subjects_list is empty
        assert response.data['profile']['subjects_list'] == []

    def test_update_all_fields_together(self, admin_client, teacher_user, subjects):
        """Update user, profile, and subjects all at once"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'first_name': 'Updated',
                'last_name': 'Teacher',
                'email': 'updated@test.com',
                'phone': '+79997654321',
                'is_active': False,
                'experience_years': 15,
                'bio': 'Updated bio',
                'subject_ids': [subjects['math'].id, subjects['physics'].id, subjects['chemistry'].id]
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        # Verify all updates
        assert response.data['user']['first_name'] == 'Updated'
        assert response.data['user']['last_name'] == 'Teacher'
        assert response.data['user']['email'] == 'updated@test.com'
        assert response.data['user']['phone'] == '+79997654321'
        assert response.data['user']['is_active'] is False
        assert response.data['profile']['experience_years'] == 15
        assert response.data['profile']['bio'] == 'Updated bio'
        assert len(response.data['profile']['subjects_list']) == 3

        # Verify database
        teacher_user.refresh_from_db()
        assert teacher_user.first_name == 'Updated'
        assert teacher_user.is_active is False

    def test_add_and_remove_subjects_in_same_request(self, admin_client, teacher_user, subjects):
        """Test adding new subjects and removing old ones simultaneously"""
        # Start with math and physics
        TeacherSubject.objects.create(
            teacher=teacher_user, subject=subjects['math'], is_active=True
        )
        TeacherSubject.objects.create(
            teacher=teacher_user, subject=subjects['physics'], is_active=True
        )

        # Update to physics, chemistry, biology (remove math, add chemistry and biology)
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'subject_ids': [
                    subjects['physics'].id,
                    subjects['chemistry'].id,
                    subjects['biology'].id
                ]
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify final state
        active_subjects = set(
            TeacherSubject.objects.filter(
                teacher=teacher_user,
                is_active=True
            ).values_list('subject_id', flat=True)
        )
        expected = {subjects['physics'].id, subjects['chemistry'].id, subjects['biology'].id}
        assert active_subjects == expected

        # Verify math is marked inactive
        math_record = TeacherSubject.objects.get(
            teacher=teacher_user, subject=subjects['math']
        )
        assert math_record.is_active is False

    def test_idempotent_subject_update(self, admin_client, teacher_user, subjects):
        """Verify subject update is idempotent (same request twice = same state)"""
        subject_ids = [subjects['math'].id, subjects['physics'].id]

        # First request
        response1 = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {'subject_ids': subject_ids},
            format='json'
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second request with same data
        response2 = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {'subject_ids': subject_ids},
            format='json'
        )
        assert response2.status_code == status.HTTP_200_OK

        # Verify same state
        active_count = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True
        ).count()
        assert active_count == 2

    def test_response_includes_subjects_list(self, admin_client, teacher_user, subjects):
        """Verify response includes subjects_list in profile"""
        TeacherSubject.objects.create(
            teacher=teacher_user, subject=subjects['math'], is_active=True
        )
        TeacherSubject.objects.create(
            teacher=teacher_user, subject=subjects['physics'], is_active=True
        )

        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {'experience_years': 5},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert 'subjects_list' in response.data['profile']
        assert isinstance(response.data['profile']['subjects_list'], list)
        assert 'Mathematics' in response.data['profile']['subjects_list']
        assert 'Physics' in response.data['profile']['subjects_list']


class TestTeacherEditValidation:
    """Tests for input validation"""

    def test_subject_ids_must_be_list(self, admin_client, teacher_user):
        """Verify subject_ids must be a list"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'subject_ids': 'not a list'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'error' in response.data

    def test_nonexistent_subject_id_ignored(self, admin_client, teacher_user):
        """Nonexistent subject IDs should be ignored gracefully"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'subject_ids': [99999]  # Nonexistent
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        # Verify no subjects added
        count = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True
        ).count()
        assert count == 0

    def test_mixed_valid_invalid_subject_ids(self, admin_client, teacher_user, subjects):
        """Mixed valid and invalid subject IDs - only valid ones added"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'subject_ids': [subjects['math'].id, 99999, subjects['physics'].id]
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify only valid subjects added
        active_subjects = set(
            TeacherSubject.objects.filter(
                teacher=teacher_user,
                is_active=True
            ).values_list('subject_id', flat=True)
        )
        assert active_subjects == {subjects['math'].id, subjects['physics'].id}

    def test_duplicate_subject_ids_handled(self, admin_client, teacher_user, subjects):
        """Duplicate subject IDs should not cause issues"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'subject_ids': [subjects['math'].id, subjects['math'].id]
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify only one record created
        count = TeacherSubject.objects.filter(
            teacher=teacher_user,
            is_active=True,
            subject=subjects['math']
        ).count()
        assert count == 1


class TestTeacherEditPermissions:
    """Tests for permission validation"""

    def test_teacher_not_found_returns_404(self, admin_client):
        """Attempt to update nonexistent teacher"""
        response = admin_client.patch(
            '/api/auth/teachers/99999/',
            {'first_name': 'Test'},
            format='json'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'not found' in response.data['error'].lower()

    def test_admin_only_access(self, regular_user_client, teacher_user):
        """Non-admin users cannot update teachers"""
        response = regular_user_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {'first_name': 'Hacked'},
            format='json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'error' in response.data

    def test_unauthenticated_access_denied(self, unauthenticated_client, teacher_user):
        """Unauthenticated requests should be denied"""
        response = unauthenticated_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {'first_name': 'Test'},
            format='json'
        )

        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_non_teacher_user_cannot_be_updated_as_teacher(self, admin_client, db):
        """Attempting to update non-teacher user via teacher endpoint"""
        student = User.objects.create_user(
            username='student',
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        response = admin_client.patch(
            f'/api/auth/teachers/{student.id}/',
            {'first_name': 'Test'},
            format='json'
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestTeacherEditEdgeCases:
    """Tests for edge cases and special scenarios"""

    def test_empty_patch_request(self, admin_client, teacher_user):
        """PATCH with no fields should still succeed"""
        original_name = teacher_user.first_name

        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        # Verify nothing changed
        teacher_user.refresh_from_db()
        assert teacher_user.first_name == original_name

    def test_whitespace_handling(self, admin_client, teacher_user):
        """Test handling of whitespace in string fields"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'first_name': 'John Doe',
                'last_name': 'Smith',
                'email': 'john@test.com'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify data saved
        teacher_user.refresh_from_db()
        assert teacher_user.first_name == 'John Doe'
        assert teacher_user.last_name == 'Smith'
        assert teacher_user.email == 'john@test.com'

    def test_email_case_preserved(self, admin_client, teacher_user):
        """Test email handling - case is preserved at backend level"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'email': 'John@Example.com'
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        teacher_user.refresh_from_db()
        # Backend preserves the case as sent (frontend does lowercasing)
        assert teacher_user.email == 'John@Example.com'

    def test_zero_experience_years_accepted(self, admin_client, teacher_user):
        """Verify 0 is valid for experience_years"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'experience_years': 0
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['profile']['experience_years'] == 0

    def test_large_experience_years_accepted(self, admin_client, teacher_user):
        """Large values for experience_years are accepted (no validation)"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'experience_years': 50
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['profile']['experience_years'] == 50

    def test_empty_bio_accepted(self, admin_client, teacher_user):
        """Empty bio should be accepted"""
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'bio': ''
            },
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['profile']['bio'] == ''

    def test_very_long_string_fields(self, admin_client, teacher_user):
        """Handle very long string values"""
        long_string = 'A' * 1000
        response = admin_client.patch(
            f'/api/auth/teachers/{teacher_user.id}/',
            {
                'bio': long_string
            },
            format='json'
        )

        # May succeed or fail depending on field constraints
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]


class TestTeacherProfileAutoCreation:
    """Tests for auto-creation of profile if missing"""

    def test_profile_auto_created_if_missing(self, admin_client, db):
        """If TeacherProfile doesn't exist, it should be created"""
        teacher = User.objects.create_user(
            username='teacher_no_profile',
            email='teacher_no_profile@test.com',
            password='testpass123',
            role='teacher'
        )
        # Don't create profile

        response = admin_client.patch(
            f'/api/auth/teachers/{teacher.id}/',
            {'experience_years': 5},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify profile was created
        teacher_profile = TeacherProfile.objects.filter(user=teacher).exists()
        assert teacher_profile is True
