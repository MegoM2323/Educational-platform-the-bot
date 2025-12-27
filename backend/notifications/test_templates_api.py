"""
API Integration tests for Notification Templates
Tests the full CRUD operations and advanced features
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from .models import NotificationTemplate

User = get_user_model()


@pytest.mark.django_db
class TestNotificationTemplatesAPI:
    """Tests for Notification Templates API endpoints"""

    def setup_method(self):
        """Setup test fixtures"""
        self.client = APIClient()
        self.user = User.objects.create_user(
            email='test@example.com',
            password='TestPassword123!',
            first_name='Test',
            last_name='User'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_template(self):
        """Test creating a notification template"""
        payload = {
            'name': 'Assignment Graded',
            'description': 'Template for grade notifications',
            'type': 'assignment_graded',
            'title_template': 'Your assignment was graded',
            'message_template': 'You got {{grade}} on {{title}}',
            'is_active': True
        }
        response = self.client.post('/api/notifications/templates/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Assignment Graded'
        assert response.data['type'] == 'assignment_graded'

    def test_list_templates(self):
        """Test listing templates"""
        NotificationTemplate.objects.create(
            name='Test Template',
            type='assignment_graded',
            title_template='Title {{user_name}}',
            message_template='Message {{grade}}'
        )
        response = self.client.get('/api/notifications/templates/')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0

    def test_retrieve_template(self):
        """Test retrieving a specific template"""
        template = NotificationTemplate.objects.create(
            name='Test Template',
            type='assignment_graded',
            title_template='Title',
            message_template='Message'
        )
        response = self.client.get(f'/api/notifications/templates/{template.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Test Template'

    def test_update_template(self):
        """Test updating a template"""
        template = NotificationTemplate.objects.create(
            name='Original',
            type='assignment_graded',
            title_template='Title',
            message_template='Message'
        )
        payload = {'name': 'Updated'}
        response = self.client.patch(f'/api/notifications/templates/{template.id}/', payload, format='json')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == 'Updated'

    def test_delete_template(self):
        """Test deleting a template"""
        template = NotificationTemplate.objects.create(
            name='To Delete',
            type='assignment_graded',
            title_template='Title',
            message_template='Message'
        )
        response = self.client.delete(f'/api/notifications/templates/{template.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not NotificationTemplate.objects.filter(id=template.id).exists()

    def test_preview_template(self):
        """Test template preview with variable substitution"""
        template = NotificationTemplate.objects.create(
            name='Grade Notification',
            type='assignment_graded',
            title_template='New grade in {{subject}}',
            message_template='You got {{grade}} on {{title}}'
        )
        payload = {
            'context': {
                'subject': 'Mathematics',
                'grade': '95',
                'title': 'Quiz 1'
            }
        }
        response = self.client.post(
            f'/api/notifications/templates/{template.id}/preview/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['rendered_title'] == 'New grade in Mathematics'
        assert response.data['rendered_message'] == 'You got 95 on Quiz 1'

    def test_validate_template(self):
        """Test template validation endpoint"""
        payload = {
            'title_template': 'Hello {{user_name}}',
            'message_template': 'Welcome {{user_email}}'
        }
        response = self.client.post(
            '/api/notifications/templates/validate/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_valid'] is True
        assert response.data['errors'] == []

    def test_validate_template_with_errors(self):
        """Test template validation with syntax errors"""
        payload = {
            'title_template': 'Hello {{unknown_var}}',
            'message_template': 'Message {{{'
        }
        response = self.client.post(
            '/api/notifications/templates/validate/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['is_valid'] is False
        assert len(response.data['errors']) > 0

    def test_clone_template(self):
        """Test cloning a template"""
        template = NotificationTemplate.objects.create(
            name='Original Template',
            type='assignment_graded',
            title_template='Title',
            message_template='Message',
            description='Test description'
        )
        response = self.client.post(f'/api/notifications/templates/{template.id}/clone/')
        assert response.status_code == status.HTTP_201_CREATED
        assert 'copy' in response.data['name']
        assert response.data['description'] == 'Test description'

    def test_filter_by_type(self):
        """Test filtering templates by type"""
        NotificationTemplate.objects.create(
            name='Assignment Template',
            type='assignment_graded',
            title_template='Title',
            message_template='Message'
        )
        NotificationTemplate.objects.create(
            name='Payment Template',
            type='payment_success',
            title_template='Title',
            message_template='Message'
        )
        response = self.client.get('/api/notifications/templates/?type=assignment_graded')
        assert response.status_code == status.HTTP_200_OK
        results = response.data['results']
        assert all(t['type'] == 'assignment_graded' for t in results)

    def test_search_templates(self):
        """Test searching templates by name"""
        NotificationTemplate.objects.create(
            name='Assignment Graded',
            type='assignment_graded',
            title_template='Title',
            message_template='Message'
        )
        response = self.client.get('/api/notifications/templates/?search=Assignment')
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) > 0
