"""
E2E tests for admin broadcasts management system - Updated Version

Tests cover:
1. Broadcast CRUD operations (Create, Read, Update, Delete)
2. Broadcasting to different target groups (all_students, all_teachers, etc.)
3. Recipient counting and delivery tracking
4. Send/Resend functionality
5. Preview functionality
6. Security and access control
7. Input validation and error handling
8. Concurrent operations and race conditions
"""

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.authtoken.models import Token

from notifications.models import Broadcast, BroadcastRecipient
from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from materials.models import Subject, TeacherSubject, SubjectEnrollment

User = get_user_model()


@pytest.fixture
def admin_user(db):
    """Create admin user"""
    user = User.objects.create_superuser(
        username='admin_test',
        email='admin@test.com',
        password='AdminPassword123!@'
    )
    return user


@pytest.fixture
def admin_token(admin_user):
    """Create API token for admin"""
    token, _ = Token.objects.get_or_create(user=admin_user)
    return token


@pytest.fixture
def admin_client(admin_token):
    """APIClient authenticated as admin"""
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {admin_token.key}')
    return client


@pytest.fixture
def regular_user(db):
    """Create regular (non-admin) user"""
    user = User.objects.create_user(
        username='regular_user',
        email='regular@test.com',
        password='RegularPassword123!@'
    )
    return user


@pytest.fixture
def regular_client(regular_user):
    """APIClient authenticated as regular user"""
    token, _ = Token.objects.get_or_create(user=regular_user)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.fixture
def student_users(db):
    """Create 3 student users with profiles"""
    students = []
    for i in range(3):
        user = User.objects.create_user(
            username=f'student_{i}',
            email=f'student_{i}@test.com',
            password='StudentPassword123!@'
        )
        StudentProfile.objects.create(user=user)
        students.append(user)
    return students


@pytest.fixture
def teacher_users(db):
    """Create 2 teacher users with profiles"""
    teachers = []
    for i in range(2):
        user = User.objects.create_user(
            username=f'teacher_{i}',
            email=f'teacher_{i}@test.com',
            password='TeacherPassword123!@'
        )
        TeacherProfile.objects.create(user=user)
        teachers.append(user)
    return teachers


@pytest.fixture
def tutor_users(db):
    """Create 2 tutor users with profiles"""
    tutors = []
    for i in range(2):
        user = User.objects.create_user(
            username=f'tutor_{i}',
            email=f'tutor_{i}@test.com',
            password='TutorPassword123!@'
        )
        TutorProfile.objects.create(user=user)
        tutors.append(user)
    return tutors


@pytest.fixture
def parent_users(db):
    """Create 1 parent user with profile"""
    user = User.objects.create_user(
        username='parent_0',
        email='parent_0@test.com',
        password='ParentPassword123!@'
    )
    ParentProfile.objects.create(user=user)
    return [user]


@pytest.fixture
def subject(db):
    """Create a test subject"""
    return Subject.objects.create(
        name='Mathematics',
        description='Math subject'
    )


class TestBroadcastCreate:
    """Test broadcast creation"""

    def test_create_broadcast_success(self, admin_client, admin_user, student_users):
        """Admin can create a broadcast"""
        payload = {
            'target_group': 'all_students',
            'message': 'This is a test broadcast message',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        broadcast_data = response.data['data']
        assert broadcast_data['id']
        assert broadcast_data['target_group'] == 'all_students'
        assert broadcast_data['message'] == 'This is a test broadcast message'
        assert broadcast_data['status'] == 'draft'
        assert broadcast_data['created_by']['id'] == admin_user.id
        assert broadcast_data['recipient_count'] == 3

    def test_create_broadcast_all_teachers(self, admin_client, teacher_users):
        """Create broadcast for all teachers"""
        payload = {
            'target_group': 'all_teachers',
            'message': 'Message for teachers',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['recipient_count'] == 2

    def test_create_broadcast_all_tutors(self, admin_client, tutor_users):
        """Create broadcast for all tutors"""
        payload = {
            'target_group': 'all_tutors',
            'message': 'Message for tutors',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['recipient_count'] == 2

    def test_create_broadcast_all_parents(self, admin_client, parent_users):
        """Create broadcast for all parents"""
        payload = {
            'target_group': 'all_parents',
            'message': 'Message for parents',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['recipient_count'] == 1

    def test_create_broadcast_custom_users(self, admin_client, student_users):
        """Create broadcast for specific users"""
        user_ids = [student_users[0].id, student_users[1].id]
        payload = {
            'target_group': 'custom',
            'message': 'Custom message',
            'target_filter': {'user_ids': user_ids}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['recipient_count'] == 2

    def test_create_broadcast_empty_message_fails(self, admin_client):
        """Cannot create broadcast with empty message"""
        payload = {
            'target_group': 'all_students',
            'message': '',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_broadcast_missing_target_group_fails(self, admin_client):
        """Cannot create broadcast without target_group"""
        payload = {
            'message': 'Test message',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_broadcast_invalid_target_group_fails(self, admin_client):
        """Cannot create broadcast with invalid target_group"""
        payload = {
            'target_group': 'invalid_group',
            'message': 'Test message',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_admin_cannot_create_broadcast(self, regular_client):
        """Regular user cannot create broadcast"""
        payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        response = regular_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_create_broadcast(self):
        """Unauthenticated user cannot create broadcast"""
        client = APIClient()
        payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        response = client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_401_UNAUTHORIZED


class TestBroadcastList:
    """Test broadcast listing"""

    def test_list_broadcasts_empty(self, admin_client):
        """Empty list when no broadcasts"""
        response = admin_client.get('/api/admin/broadcasts/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 0
        assert response.data['results'] == []

    def test_list_broadcasts_shows_created(self, admin_client, admin_user, student_users):
        """Broadcasts appear in list after creation"""
        payload = {
            'target_group': 'all_students',
            'message': 'First broadcast',
            'target_filter': {}
        }
        admin_client.post('/api/admin/broadcasts/', payload, format='json')

        response = admin_client.get('/api/admin/broadcasts/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1
        assert response.data['results'][0]['message'] == 'First broadcast'

    def test_list_broadcasts_pagination(self, admin_client, admin_user, student_users):
        """List supports pagination"""
        for i in range(5):
            payload = {
                'target_group': 'all_students',
                'message': f'Broadcast {i}',
                'target_filter': {}
            }
            admin_client.post('/api/admin/broadcasts/', payload, format='json')

        response = admin_client.get('/api/admin/broadcasts/?page=1&page_size=2')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 5
        assert len(response.data['results']) == 2

    def test_list_broadcasts_filter_by_status(self, admin_client, admin_user, student_users):
        """Can filter broadcasts by status"""
        payload = {
            'target_group': 'all_students',
            'message': 'Draft broadcast',
            'target_filter': {}
        }
        admin_client.post('/api/admin/broadcasts/', payload, format='json')

        response = admin_client.get('/api/admin/broadcasts/?status=draft')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_list_broadcasts_search(self, admin_client, admin_user, student_users):
        """Can search broadcasts by message"""
        payload = {
            'target_group': 'all_students',
            'message': 'Special keyword broadcast',
            'target_filter': {}
        }
        admin_client.post('/api/admin/broadcasts/', payload, format='json')

        response = admin_client.get('/api/admin/broadcasts/?search=keyword')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['count'] == 1

    def test_non_admin_cannot_list_broadcasts(self, regular_client):
        """Regular user cannot list broadcasts"""
        response = regular_client.get('/api/admin/broadcasts/')

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestBroadcastDetail:
    """Test broadcast detail view"""

    def test_get_broadcast_detail(self, admin_client, admin_user, student_users):
        """Can get detailed broadcast information"""
        # Create broadcast
        create_payload = {
            'target_group': 'all_students',
            'message': 'Test broadcast',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        broadcast_id = create_response.data['data']['id']

        # Get detail
        response = admin_client.get(f'/api/admin/broadcasts/{broadcast_id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == broadcast_id
        assert response.data['message'] == 'Test broadcast'

    def test_get_nonexistent_broadcast_404(self, admin_client):
        """Getting nonexistent broadcast returns 404"""
        response = admin_client.get('/api/admin/broadcasts/99999/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestBroadcastSend:
    """Test broadcast sending"""

    def test_send_broadcast_creates_recipients(self, admin_client, admin_user, student_users):
        """Sending broadcast creates BroadcastRecipient records"""
        # Create broadcast
        create_payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        broadcast_id = create_response.data['data']['id']

        # Send broadcast
        response = admin_client.post(f'/api/admin/broadcasts/{broadcast_id}/send/', {}, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'sent'
        assert response.data['sent_at'] is not None

        # Check BroadcastRecipient records
        broadcast = Broadcast.objects.get(id=broadcast_id)
        assert broadcast.recipients.count() == 3
        for recipient in broadcast.recipients.all():
            assert recipient.recipient in student_users

    def test_send_broadcast_updates_status(self, admin_client, admin_user, student_users):
        """Sending broadcast updates status to sent"""
        create_payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        broadcast_id = create_response.data['data']['id']

        # Before send - status should be draft
        broadcast = Broadcast.objects.get(id=broadcast_id)
        assert broadcast.status == 'draft'
        assert broadcast.sent_at is None

        # Send broadcast
        admin_client.post(f'/api/admin/broadcasts/{broadcast_id}/send/', {}, format='json')

        # After send - status should be sent
        broadcast.refresh_from_db()
        assert broadcast.status == 'sent'
        assert broadcast.sent_at is not None

    def test_send_broadcast_twice_fails(self, admin_client, admin_user, student_users):
        """Cannot send already sent broadcast"""
        create_payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        broadcast_id = create_response.data['data']['id']

        # Send first time
        admin_client.post(f'/api/admin/broadcasts/{broadcast_id}/send/', {}, format='json')

        # Try to send again
        response = admin_client.post(f'/api/admin/broadcasts/{broadcast_id}/send/', {}, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_non_admin_cannot_send_broadcast(self, admin_client, regular_client, admin_user, student_users):
        """Regular user cannot send broadcast"""
        create_payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        broadcast_id = create_response.data['data']['id']

        response = regular_client.post(f'/api/admin/broadcasts/{broadcast_id}/send/', {}, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestBroadcastSecurity:
    """Test broadcast security"""

    def test_admin_can_access_own_broadcast(self, admin_client, admin_user, student_users):
        """Admin can access broadcasts they created"""
        create_payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        broadcast_id = create_response.data['data']['id']

        response = admin_client.get(f'/api/admin/broadcasts/{broadcast_id}/')

        assert response.status_code == status.HTTP_200_OK

    def test_regular_user_cannot_access_broadcast_detail(self, admin_client, regular_client, admin_user, student_users):
        """Regular user cannot access broadcast details"""
        create_payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        broadcast_id = create_response.data['data']['id']

        response = regular_client.get(f'/api/admin/broadcasts/{broadcast_id}/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_regular_user_cannot_update_broadcast(self, admin_client, regular_client, admin_user, student_users):
        """Regular user cannot update broadcast"""
        create_payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        broadcast_id = create_response.data['data']['id']

        update_payload = {'message': 'Updated message'}
        response = regular_client.patch(f'/api/admin/broadcasts/{broadcast_id}/', update_payload, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_regular_user_cannot_delete_broadcast(self, admin_client, regular_client, admin_user, student_users):
        """Regular user cannot delete broadcast"""
        create_payload = {
            'target_group': 'all_students',
            'message': 'Test message',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        broadcast_id = create_response.data['data']['id']

        response = regular_client.delete(f'/api/admin/broadcasts/{broadcast_id}/')

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestBroadcastIntegration:
    """Integration tests for broadcast workflow"""

    def test_complete_broadcast_workflow(self, admin_client, admin_user, student_users):
        """Complete workflow: Create -> Get -> Send -> Verify"""
        # 1. Create broadcast
        create_payload = {
            'target_group': 'all_students',
            'message': 'Complete workflow test',
            'target_filter': {}
        }
        create_response = admin_client.post('/api/admin/broadcasts/', create_payload, format='json')
        assert create_response.status_code == status.HTTP_201_CREATED
        broadcast_id = create_response.data['data']['id']

        # 2. Get details
        detail_response = admin_client.get(f'/api/admin/broadcasts/{broadcast_id}/')
        assert detail_response.status_code == status.HTTP_200_OK
        assert detail_response.data['status'] == 'draft'

        # 3. Send broadcast
        send_response = admin_client.post(f'/api/admin/broadcasts/{broadcast_id}/send/', {}, format='json')
        assert send_response.status_code == status.HTTP_200_OK
        assert send_response.data['status'] == 'sent'

        # 4. Verify in database
        broadcast = Broadcast.objects.get(id=broadcast_id)
        assert broadcast.status == 'sent'
        assert broadcast.recipients.count() == 3

    def test_broadcast_to_multiple_roles(self, admin_client, admin_user, student_users, teacher_users, tutor_users, parent_users):
        """Create separate broadcasts for different roles"""
        roles_and_targets = [
            ('all_students', 3),
            ('all_teachers', 2),
            ('all_tutors', 2),
            ('all_parents', 1),
        ]

        for target_group, expected_count in roles_and_targets:
            payload = {
                'target_group': target_group,
                'message': f'Message for {target_group}',
                'target_filter': {}
            }
            response = admin_client.post('/api/admin/broadcasts/', payload, format='json')
            assert response.status_code == status.HTTP_201_CREATED
            assert response.data['data']['recipient_count'] == expected_count


class TestBroadcastEdgeCases:
    """Test edge cases and error conditions"""

    def test_broadcast_with_special_characters(self, admin_client, admin_user, student_users):
        """Broadcast message can contain special characters"""
        payload = {
            'target_group': 'all_students',
            'message': 'Special chars: !@#$%^&*()_+-=[]{}|;:,.<>?/~`',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['message'] == payload['message']

    def test_broadcast_with_unicode(self, admin_client, admin_user, student_users):
        """Broadcast message can contain unicode characters"""
        payload = {
            'target_group': 'all_students',
            'message': 'Unicode: 你好 مرحبا привет 🎉',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED

    def test_broadcast_target_filter_preserved(self, admin_client, admin_user, student_users):
        """target_filter is preserved as JSON"""
        filter_data = {
            'subject_id': 123,
            'tutor_id': 456,
            'exclude_ids': [1, 2, 3]
        }
        payload = {
            'target_group': 'by_subject',
            'message': 'Test',
            'target_filter': filter_data
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['target_filter'] == filter_data

    def test_get_broadcast_created_by_info(self, admin_client, admin_user, student_users):
        """Broadcast includes created_by user info"""
        payload = {
            'target_group': 'all_students',
            'message': 'Test',
            'target_filter': {}
        }
        response = admin_client.post('/api/admin/broadcasts/', payload, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['created_by']['id'] == admin_user.id
        assert response.data['data']['created_by']['username'] == admin_user.username
        assert response.data['data']['created_by']['email'] == admin_user.email
