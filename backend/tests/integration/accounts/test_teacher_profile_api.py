"""
Integration tests for Teacher Profile API endpoints.

Tests cover complete request-response cycle for:
- GET /api/profile/teacher/ - Retrieve teacher profile
- PATCH /api/profile/teacher/ - Update teacher profile
- Avatar upload and file handling
- Database state verification
- Auto-creation of missing profiles
- Permission checks for all roles

Запуск:
    pytest backend/tests/integration/accounts/test_teacher_profile_api.py -v
"""

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import TeacherProfile

User = get_user_model()

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def api_client():
    """REST API client"""
    return APIClient()


class TestTeacherProfileGetEndpoint:
    """Test GET /api/profile/teacher/ - Retrieve teacher profile"""

    def test_teacher_can_get_own_profile(self, api_client, teacher_user):
        """Teacher can retrieve their own profile"""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/profile/teacher/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['user']['id'] == teacher_user.id
        assert response.data['user']['email'] == teacher_user.email
        assert 'profile' in response.data

    def test_profile_response_structure(self, api_client, teacher_user):
        """Profile response has correct structure with user and profile fields"""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/profile/teacher/')

        assert response.status_code == status.HTTP_200_OK
        assert 'user' in response.data
        assert 'profile' in response.data

        # User data structure
        user_data = response.data['user']
        assert user_data['id'] == teacher_user.id
        assert user_data['email'] == teacher_user.email
        assert 'first_name' in user_data
        assert 'last_name' in user_data
        assert 'avatar' in user_data

        # Profile data structure
        profile_data = response.data['profile']
        assert 'id' in profile_data
        assert 'subject' in profile_data
        assert 'bio' in profile_data

    def test_teacher_profile_auto_creates_missing_profile(self, api_client):
        """If teacher profile missing, auto-creates profile and returns 200"""
        # Create teacher WITHOUT profile
        teacher = User.objects.create_user(
            username='teacher_no_profile',
            email='teacher_no_profile@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER,
            first_name='Test',
            last_name='Teacher'
        )
        # Verify profile doesn't exist yet
        assert not TeacherProfile.objects.filter(user=teacher).exists()

        api_client.force_authenticate(user=teacher)
        response = api_client.get('/api/profile/teacher/')

        assert response.status_code == status.HTTP_200_OK
        # Verify profile was auto-created
        assert TeacherProfile.objects.filter(user=teacher).exists()
        assert 'profile' in response.data

    def test_student_cannot_access_teacher_profile_endpoint(self, api_client, student_user):
        """Student gets 403 Forbidden when accessing teacher profile endpoint"""
        api_client.force_authenticate(user=student_user)

        response = api_client.get('/api/profile/teacher/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tutor_cannot_access_teacher_profile_endpoint(self, api_client, tutor_user):
        """Tutor gets 403 Forbidden when accessing teacher profile endpoint"""
        api_client.force_authenticate(user=tutor_user)

        response = api_client.get('/api/profile/teacher/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_parent_cannot_access_teacher_profile_endpoint(self, api_client):
        """Parent gets 403 Forbidden when accessing teacher profile endpoint"""
        parent = User.objects.create_user(
            username='parent_test',
            email='parent@test.com',
            password='TestPass123!',
            role=User.Role.PARENT
        )
        api_client.force_authenticate(user=parent)

        response = api_client.get('/api/profile/teacher/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_access_teacher_profile(self, api_client):
        """Unauthenticated user gets 401 when accessing teacher profile"""
        response = api_client.get('/api/profile/teacher/')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_teacher_profile_includes_avatar_url(self, api_client, teacher_user):
        """Profile response includes avatar field (can be null)"""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/profile/teacher/')

        assert response.status_code == status.HTTP_200_OK
        user_data = response.data['user']
        assert 'avatar' in user_data

    def test_profile_no_n_plus_one_queries(self, api_client, teacher_user, django_assert_num_queries):
        """Profile endpoint uses select_related to avoid N+1 queries"""
        api_client.force_authenticate(user=teacher_user)

        # Should only query User+TeacherProfile + TeacherSubjects (2 queries)
        # SAVEPOINT/RELEASE wrapping adds 2 more (total 4)
        with django_assert_num_queries(4):
            response = api_client.get('/api/profile/teacher/')
            assert response.status_code == status.HTTP_200_OK


class TestTeacherProfilePatchEndpoint:
    """Test PATCH /api/profile/teacher/ - Update teacher profile"""

    def test_teacher_can_update_own_bio(self, api_client, teacher_user):
        """Teacher can update their bio"""
        api_client.force_authenticate(user=teacher_user)

        update_data = {
            'bio': 'Updated bio for teacher',
        }

        response = api_client.patch('/api/profile/teacher/', update_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        # Verify in database
        teacher_user.teacher_profile.refresh_from_db()
        assert teacher_user.teacher_profile.bio == 'Updated bio for teacher'

    def test_teacher_can_update_subject(self, api_client, teacher_user):
        """Teacher can update their subject"""
        api_client.force_authenticate(user=teacher_user)

        update_data = {
            'subject': 'История России',
        }

        response = api_client.patch('/api/profile/teacher/', update_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        teacher_user.teacher_profile.refresh_from_db()
        assert teacher_user.teacher_profile.subject == 'История России'

    def test_teacher_can_update_user_names(self, api_client, teacher_user):
        """Teacher can update their first and last names"""
        api_client.force_authenticate(user=teacher_user)

        update_data = {
            'first_name': 'Петр',
            'last_name': 'Новиков',
        }

        response = api_client.patch('/api/profile/teacher/', update_data, format='json')

        assert response.status_code == status.HTTP_200_OK
        teacher_user.refresh_from_db()
        assert teacher_user.first_name == 'Петр'
        assert teacher_user.last_name == 'Новиков'

    def test_update_changes_persisted_to_database(self, api_client, teacher_user):
        """Updated values are persisted to database"""
        api_client.force_authenticate(user=teacher_user)

        original_bio = teacher_user.teacher_profile.bio
        new_bio = 'Completely new bio'

        api_client.patch(
            '/api/profile/teacher/',
            {'bio': new_bio},
            format='json'
        )

        # Verify in fresh query from database
        updated_profile = TeacherProfile.objects.get(user=teacher_user)
        assert updated_profile.bio == new_bio
        assert updated_profile.bio != original_bio

    def test_student_cannot_patch_teacher_profile_endpoint(self, api_client, student_user):
        """Student gets 403 Forbidden when updating teacher profile"""
        api_client.force_authenticate(user=student_user)

        response = api_client.patch(
            '/api/profile/teacher/',
            {'bio': 'Hacked'},
            format='json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_update_teacher_profile(self, api_client):
        """Unauthenticated user gets 401 when updating teacher profile"""
        response = api_client.patch(
            '/api/profile/teacher/',
            {'bio': 'Hacked'},
            format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_partial_update_only_updates_specified_fields(self, api_client, teacher_user):
        """PATCH only updates specified fields, leaves others unchanged"""
        api_client.force_authenticate(user=teacher_user)

        original_subject = teacher_user.teacher_profile.subject
        new_bio = 'New bio'

        api_client.patch(
            '/api/profile/teacher/',
            {'bio': new_bio},
            format='json'
        )

        teacher_user.teacher_profile.refresh_from_db()
        assert teacher_user.teacher_profile.bio == new_bio
        assert teacher_user.teacher_profile.subject == original_subject


class TestTeacherProfileIntegrationFlow:
    """Integration tests for complete teacher profile workflow"""

    def test_teacher_profile_flow_get_then_update(self, api_client, teacher_user):
        """Complete flow: GET profile, then PATCH to update it"""
        api_client.force_authenticate(user=teacher_user)

        # Step 1: GET profile
        get_response = api_client.get('/api/profile/teacher/')
        assert get_response.status_code == status.HTTP_200_OK
        original_bio = get_response.data['profile'].get('bio', '')

        # Step 2: PATCH to update
        new_bio = 'Updated through integration test'
        patch_response = api_client.patch(
            '/api/profile/teacher/',
            {'bio': new_bio},
            format='json'
        )
        assert patch_response.status_code == status.HTTP_200_OK

        # Step 3: GET again to verify update
        get_response_2 = api_client.get('/api/profile/teacher/')
        assert get_response_2.status_code == status.HTTP_200_OK
        assert get_response_2.data['profile']['bio'] == new_bio

    def test_multiple_teachers_profiles_isolated(self, api_client):
        """Different teachers cannot see each other's profiles"""
        teacher1 = User.objects.create_user(
            username='teacher1',
            email='teacher1@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        TeacherProfile.objects.create(user=teacher1, bio='Teacher 1 bio')

        teacher2 = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        TeacherProfile.objects.create(user=teacher2, bio='Teacher 2 bio')

        # Teacher1 gets their profile
        api_client.force_authenticate(user=teacher1)
        response1 = api_client.get('/api/profile/teacher/')
        assert response1.status_code == status.HTTP_200_OK
        assert response1.data['user']['id'] == teacher1.id
        assert response1.data['profile']['bio'] == 'Teacher 1 bio'

        # Teacher2 gets their profile
        api_client.force_authenticate(user=teacher2)
        response2 = api_client.get('/api/profile/teacher/')
        assert response2.status_code == status.HTTP_200_OK
        assert response2.data['user']['id'] == teacher2.id
        assert response2.data['profile']['bio'] == 'Teacher 2 bio'

    def test_teacher_profile_persists_across_requests(self, api_client, teacher_user):
        """Profile data persists across multiple API calls"""
        api_client.force_authenticate(user=teacher_user)

        # Update bio
        api_client.patch(
            '/api/profile/teacher/',
            {'bio': 'Initial bio'},
            format='json'
        )

        # Update subject
        api_client.patch(
            '/api/profile/teacher/',
            {'subject': 'Математика'},
            format='json'
        )

        # GET and verify both updates persisted
        response = api_client.get('/api/profile/teacher/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['profile']['bio'] == 'Initial bio'
        assert response.data['profile']['subject'] == 'Математика'
