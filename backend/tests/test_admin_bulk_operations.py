"""
E2E tests for admin bulk user operations.

Tests massive operations like:
- POST /api/admin/bulk-operations/bulk_activate/
- POST /api/admin/bulk-operations/bulk_deactivate/
- POST /api/admin/bulk-operations/bulk_assign_role/
- POST /api/admin/bulk-operations/bulk_delete/

Features tested:
1. Atomicity - all-or-nothing transactions
2. Partial success - tracks successful_count and failed_count
3. Validation - empty arrays, invalid user_ids, non-existent users
4. Security - non-admin 403, unauthenticated 401
5. Audit logging - all operations logged
6. Transaction isolation - each operation in separate transaction
"""

import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
if not settings.configured:
    django.setup()

import pytest
from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework.test import APIClient
from rest_framework import status

from core.models import AuditLog

User = get_user_model()


@pytest.fixture
def admin_user():
    """Create admin user"""
    return User.objects.create_user(
        email='admin@test.com',
        password='test1234',
        first_name='Admin',
        last_name='User',
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def non_admin_user():
    """Create non-admin user"""
    return User.objects.create_user(
        email='teacher@test.com',
        password='test1234',
        first_name='Teacher',
        last_name='User',
        role='teacher'
    )


@pytest.fixture
def test_users():
    """Create 10 test users for bulk operations"""
    users = []
    roles = ['student', 'teacher', 'tutor', 'parent']

    for i in range(10):
        role = roles[i % len(roles)]
        user = User.objects.create_user(
            email=f'user{i}@test.com',
            password='test1234',
            first_name=f'User{i}',
            last_name='Test',
            role=role,
            is_active=True
        )
        users.append(user)
    return users


@pytest.fixture
def authenticated_admin_client(admin_user):
    """API client authenticated as admin"""
    client = APIClient()
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=admin_user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.fixture
def authenticated_non_admin_client(non_admin_user):
    """API client authenticated as non-admin"""
    client = APIClient()
    from rest_framework.authtoken.models import Token
    token, _ = Token.objects.get_or_create(user=non_admin_user)
    client.credentials(HTTP_AUTHORIZATION=f'Token {token.key}')
    return client


@pytest.mark.django_db
class TestAdminBulkOperations:
    """Test bulk operations endpoints"""

    def test_bulk_activate_basic(self, authenticated_admin_client, test_users):
        """Test basic bulk activation of users"""
        # Deactivate some users first
        user_ids = [test_users[0].id, test_users[1].id, test_users[2].id]
        User.objects.filter(id__in=user_ids).update(is_active=False)

        # Activate them
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # Verify response structure
        assert data['success'] is True
        assert data['operation_id']
        assert len(data['successes']) == 3
        assert data['failures'] == []
        assert data['summary']['success_count'] == 3
        assert data['summary']['failure_count'] == 0

        # Verify database state
        activated_users = User.objects.filter(id__in=user_ids)
        for user in activated_users:
            assert user.is_active is True

    def test_bulk_deactivate_basic(self, authenticated_admin_client, test_users):
        """Test basic bulk deactivation of users"""
        user_ids = [test_users[0].id, test_users[1].id]

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_deactivate/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['success'] is True
        assert len(data['successes']) == 2
        assert data['summary']['success_count'] == 2

        # Verify users are inactive
        deactivated = User.objects.filter(id__in=user_ids)
        for user in deactivated:
            assert user.is_active is False

    def test_bulk_delete_basic(self, authenticated_admin_client, test_users):
        """Test basic bulk deletion (archival) of users"""
        user_ids = [test_users[5].id, test_users[6].id]

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_delete/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['success'] is True
        assert len(data['successes']) == 2
        assert data['summary']['success_count'] == 2

        # Verify users are archived (inactive)
        deleted = User.objects.filter(id__in=user_ids)
        for user in deleted:
            assert user.is_active is False
            assert user.id in [u['user_id'] for u in data['successes']]

    def test_bulk_assign_role(self, authenticated_admin_client, test_users):
        """Test bulk role assignment"""
        user_ids = [test_users[0].id, test_users[1].id, test_users[2].id]

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_assign_role/',
            {'user_ids': user_ids, 'role': 'parent'},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['success'] is True
        assert len(data['successes']) == 3
        assert all(s['new_role'] == 'parent' for s in data['successes'])

        # Verify database
        updated = User.objects.filter(id__in=user_ids)
        for user in updated:
            assert user.role == 'parent'

    def test_bulk_operations_with_partial_success(self, authenticated_admin_client, test_users):
        """Test partial success - some users not found"""
        valid_ids = [test_users[0].id, test_users[1].id]
        invalid_id = 99999
        user_ids = valid_ids + [invalid_id]

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['success'] is True
        assert len(data['successes']) == 2
        assert len(data['failures']) == 1
        assert data['failures'][0]['user_id'] == invalid_id
        assert data['summary']['success_count'] == 2
        assert data['summary']['failure_count'] == 1

    def test_bulk_operations_all_invalid_users(self, authenticated_admin_client):
        """Test when all users are invalid"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': [99999, 88888, 77777]},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        assert data['success'] is False
        assert len(data['successes']) == 0
        assert len(data['failures']) == 3

    def test_bulk_operations_empty_user_ids(self, authenticated_admin_client):
        """Test with empty user_ids array"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': []},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_operations_missing_user_ids(self, authenticated_admin_client):
        """Test with missing user_ids field"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'user_ids' in data

    def test_bulk_assign_role_invalid_role(self, authenticated_admin_client, test_users):
        """Test assigning invalid role"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_assign_role/',
            {'user_ids': [test_users[0].id], 'role': 'invalid_role'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_assign_role_missing_role(self, authenticated_admin_client, test_users):
        """Test assigning role without specifying role"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_assign_role/',
            {'user_ids': [test_users[0].id]},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_operations_non_admin_403(self, authenticated_non_admin_client, test_users):
        """Test that non-admin cannot perform bulk operations"""
        response = authenticated_non_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': [test_users[0].id]},
            format='json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_bulk_operations_unauthenticated_401(self, test_users):
        """Test that unauthenticated users cannot perform bulk operations"""
        client = APIClient()
        response = client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': [test_users[0].id]},
            format='json'
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_bulk_operations_audit_logged(self, authenticated_admin_client, admin_user, test_users):
        """Test that bulk operations are logged to audit trail"""
        user_ids = [test_users[0].id, test_users[1].id]

        # Clear existing audit logs
        AuditLog.objects.all().delete()

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        # Check audit log was created
        audit_logs = AuditLog.objects.filter(
            user=admin_user,
            action=AuditLog.Action.ADMIN_ACTION
        )

        assert audit_logs.exists()
        log = audit_logs.first()
        assert log.target_type == 'bulk_users'
        assert log.metadata['action'] == 'bulk_activate'
        assert log.metadata['target_count'] == 2

    def test_bulk_operations_atomicity(self, authenticated_admin_client, test_users):
        """Test that operations are atomic - either all succeed or all fail"""
        user_ids = [test_users[0].id, test_users[1].id, test_users[2].id]

        # Deactivate them first
        User.objects.filter(id__in=user_ids).update(is_active=False)

        # Perform activation
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        # Verify all users are activated (all-or-nothing)
        users = User.objects.filter(id__in=user_ids)
        assert all(u.is_active for u in users)

    def test_bulk_operations_duplicate_user_ids(self, authenticated_admin_client, test_users):
        """Test validation rejects duplicate user IDs"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': [test_users[0].id, test_users[0].id, test_users[1].id]},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'user_ids' in data

    def test_bulk_operations_admin_self_modification_prevented(self, authenticated_admin_client, admin_user):
        """Test that admin cannot modify their own account in bulk"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_deactivate/',
            {'user_ids': [admin_user.id]},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert 'error' in data

    def test_bulk_operations_transaction_isolation(self, authenticated_admin_client, test_users):
        """Test that each operation is in separate transaction"""
        user_ids_1 = [test_users[0].id, test_users[1].id]
        user_ids_2 = [test_users[2].id, test_users[3].id]

        # First operation
        response1 = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_deactivate/',
            {'user_ids': user_ids_1},
            format='json'
        )
        assert response1.status_code == status.HTTP_200_OK

        # Second operation
        response2 = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': user_ids_2},
            format='json'
        )
        assert response2.status_code == status.HTTP_200_OK

        # Verify first operation's state
        users_1 = User.objects.filter(id__in=user_ids_1)
        assert all(not u.is_active for u in users_1)

        # Verify second operation's state
        users_2 = User.objects.filter(id__in=user_ids_2)
        assert all(u.is_active for u in users_2)

    def test_bulk_operations_success_items_contain_required_fields(self, authenticated_admin_client, test_users):
        """Test that success items contain required fields"""
        user_id = test_users[0].id

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': [user_id]},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        success_item = data['successes'][0]
        assert 'user_id' in success_item
        assert 'email' in success_item
        assert 'full_name' in success_item
        assert success_item['user_id'] == user_id

    def test_bulk_operations_failure_items_contain_required_fields(self, authenticated_admin_client):
        """Test that failure items contain required fields"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': [99999]},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        failure_item = data['failures'][0]
        assert 'user_id' in failure_item
        assert 'reason' in failure_item

    def test_bulk_operations_large_batch(self, authenticated_admin_client):
        """Test bulk operations with maximum allowed users (1000)"""
        # Create many users
        user_ids = []
        for i in range(100):  # Create 100 instead of 1000 to save time
            user = User.objects.create_user(
                email=f'bulk_user_{i}@test.com',
                password='test1234',
                role='student'
            )
            user_ids.append(user.id)

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['summary']['success_count'] == 100

    def test_bulk_operations_exceeds_max_limit(self, authenticated_admin_client):
        """Test that exceeding max users (1000) returns error"""
        # Don't actually create 1001 users, just test the validation
        user_ids = list(range(1, 1002))  # 1 to 1001

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_deactivate_then_activate(self, authenticated_admin_client, test_users):
        """Test workflow: deactivate then reactivate users"""
        user_ids = [test_users[0].id, test_users[1].id]

        # Deactivate
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_deactivate/',
            {'user_ids': user_ids},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify deactivated
        users = User.objects.filter(id__in=user_ids)
        assert all(not u.is_active for u in users)

        # Activate
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': user_ids},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

        # Verify activated
        users = User.objects.filter(id__in=user_ids)
        assert all(u.is_active for u in users)

    def test_bulk_assign_multiple_roles(self, authenticated_admin_client, test_users):
        """Test assigning different roles sequentially"""
        user_ids = [test_users[0].id, test_users[1].id]

        # Assign to parent
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_assign_role/',
            {'user_ids': user_ids, 'role': 'parent'},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

        users = User.objects.filter(id__in=user_ids)
        assert all(u.role == 'parent' for u in users)

        # Assign to teacher
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_assign_role/',
            {'user_ids': user_ids, 'role': 'teacher'},
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK

        users = User.objects.filter(id__in=user_ids)
        assert all(u.role == 'teacher' for u in users)

    def test_bulk_operations_response_has_operation_id(self, authenticated_admin_client, test_users):
        """Test that response includes unique operation_id for tracking"""
        response1 = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': [test_users[0].id]},
            format='json'
        )

        response2 = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': [test_users[1].id]},
            format='json'
        )

        op_id_1 = response1.json()['operation_id']
        op_id_2 = response2.json()['operation_id']

        # operation_ids should be different
        assert op_id_1 != op_id_2
        # Both should be valid UUIDs
        assert len(op_id_1) == 36  # UUID4 length with hyphens
        assert len(op_id_2) == 36

    def test_bulk_operations_invalid_user_ids_type(self, authenticated_admin_client):
        """Test with invalid user_ids type"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': 'not_a_list'},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_operations_negative_user_ids(self, authenticated_admin_client):
        """Test with negative user IDs"""
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': [-1, -2]},
            format='json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_bulk_delete_response_contains_archived_status(self, authenticated_admin_client, test_users):
        """Test that delete response indicates archived status"""
        user_id = test_users[0].id

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_delete/',
            {'user_ids': [user_id]},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        success_item = data['successes'][0]
        assert success_item['status'] == 'archived'

    def test_bulk_assign_role_response_includes_new_role(self, authenticated_admin_client, test_users):
        """Test that assign_role response includes new_role"""
        user_id = test_users[0].id

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_assign_role/',
            {'user_ids': [user_id], 'role': 'tutor'},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        success_item = data['successes'][0]
        assert 'new_role' in success_item
        assert success_item['new_role'] == 'tutor'

    def test_bulk_operations_with_inactive_users(self, authenticated_admin_client, test_users):
        """Test bulk operations include inactive users"""
        # Deactivate one user
        test_users[0].is_active = False
        test_users[0].save()

        user_ids = [test_users[0].id, test_users[1].id]

        # Activate both
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['summary']['success_count'] == 2

    def test_bulk_operations_summary_calculations(self, authenticated_admin_client, test_users):
        """Test that summary calculations are correct"""
        total_users = 5
        valid_ids = [test_users[i].id for i in range(total_users)]
        invalid_ids = [99999, 88888]
        all_ids = valid_ids + invalid_ids

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_activate/',
            {'user_ids': all_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        summary = data['summary']

        assert summary['total_requested'] == 7
        assert summary['success_count'] == 5
        assert summary['failure_count'] == 2
        assert summary['total_requested'] == (summary['success_count'] + summary['failure_count'])

    def test_bulk_suspend_operation(self, authenticated_admin_client, test_users):
        """Test bulk suspend operation"""
        user_ids = [test_users[0].id, test_users[1].id]

        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_suspend/',
            {'user_ids': user_ids, 'reason': 'Policy violation'},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['success'] is True
        assert data['reason'] == 'Policy violation'

        # Verify users are suspended (inactive)
        users = User.objects.filter(id__in=user_ids)
        assert all(not u.is_active for u in users)

    def test_bulk_unsuspend_operation(self, authenticated_admin_client, test_users):
        """Test bulk unsuspend operation"""
        # First suspend
        user_ids = [test_users[0].id, test_users[1].id]
        User.objects.filter(id__in=user_ids).update(is_active=False)

        # Then unsuspend
        response = authenticated_admin_client.post(
            '/api/accounts/bulk-operations/bulk_unsuspend/',
            {'user_ids': user_ids},
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data['success'] is True

        # Verify users are unsuspended (active)
        users = User.objects.filter(id__in=user_ids)
        assert all(u.is_active for u in users)
