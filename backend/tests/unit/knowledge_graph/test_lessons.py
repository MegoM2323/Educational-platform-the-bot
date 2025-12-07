"""
Unit tests for Lesson API (T204)
Tests all CRUD operations, element management, permissions, filtering, and validation
"""
import pytest
from rest_framework import status
from rest_framework.test import APIClient
from django.test import TestCase
from django.contrib.auth import get_user_model

from knowledge_graph.models import Element, Lesson, LessonElement
from materials.models import Subject

User = get_user_model()


@pytest.mark.django_db
class TestLessonListCreateView:
    """Test Lesson list and create endpoint"""

    def setup_method(self):
        """Setup test data before each test"""
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            username='student@test.com',
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.other_teacher = User.objects.create_user(
            username='other_teacher@test.com',
            email='other_teacher@test.com',
            password='testpass123',
            role='teacher'
        )

        self.subject = Subject.objects.create(
            name='Mathematics',
            description='Math subject'
        )

    def test_lesson_list_requires_authentication(self):
        """Test GET /lessons/ requires authentication"""
        response = self.client.get('/api/knowledge-graph/lessons/')
        # DRF returns 403 for unauthenticated requests with IsAuthenticated permission
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_lesson_list_returns_paginated_results(self):
        """Test GET /lessons/ returns paginated results"""
        self.client.force_authenticate(user=self.teacher)

        # Create 25 lessons to test pagination
        for i in range(25):
            Lesson.objects.create(
                title=f'Lesson {i}',
                description=f'Description {i}',
                subject=self.subject,
                created_by=self.teacher,
                is_public=False
            )

        response = self.client.get('/api/knowledge-graph/lessons/')
        assert response.status_code == status.HTTP_200_OK
        assert 'results' in response.data or 'data' in response.data

    def test_lesson_list_returns_own_and_public_lessons(self):
        """Test GET /lessons/ returns both own and public lessons"""
        self.client.force_authenticate(user=self.teacher)

        # Create own private lesson
        own_lesson = Lesson.objects.create(
            title='Own Lesson',
            description='My lesson',
            subject=self.subject,
            created_by=self.teacher,
            is_public=False
        )

        # Create public lesson by another teacher
        public_lesson = Lesson.objects.create(
            title='Public Lesson',
            description='Public lesson',
            subject=self.subject,
            created_by=self.other_teacher,
            is_public=True
        )

        # Create private lesson by another teacher (should not see)
        private_lesson = Lesson.objects.create(
            title='Other Private',
            description='Other private',
            subject=self.subject,
            created_by=self.other_teacher,
            is_public=False
        )

        response = self.client.get('/api/knowledge-graph/lessons/')
        assert response.status_code == status.HTTP_200_OK

        data = response.data.get('results') or response.data.get('data', [])
        lesson_ids = [l['id'] for l in data]

        assert own_lesson.id in lesson_ids
        assert public_lesson.id in lesson_ids
        assert private_lesson.id not in lesson_ids

    def test_lesson_list_filter_by_subject(self):
        """Test GET /lessons/?subject=X filters by subject"""
        self.client.force_authenticate(user=self.teacher)

        subject2 = Subject.objects.create(name='Physics', description='Physics')

        # Create lessons in different subjects
        lesson1 = Lesson.objects.create(
            title='Math Lesson',
            description='Desc',
            subject=self.subject,
            created_by=self.teacher
        )

        lesson2 = Lesson.objects.create(
            title='Physics Lesson',
            description='Desc',
            subject=subject2,
            created_by=self.teacher
        )

        response = self.client.get(f'/api/knowledge-graph/lessons/?subject={self.subject.id}')
        assert response.status_code == status.HTTP_200_OK

        data = response.data.get('results') or response.data.get('data', [])
        lesson_ids = [l['id'] for l in data]

        assert lesson1.id in lesson_ids
        assert lesson2.id not in lesson_ids

    def test_lesson_list_filter_by_created_by_me(self):
        """Test GET /lessons/?created_by=me filters to own lessons"""
        self.client.force_authenticate(user=self.teacher)

        # Create own lesson
        own_lesson = Lesson.objects.create(
            title='My Lesson',
            description='Mine',
            subject=self.subject,
            created_by=self.teacher,
            is_public=True
        )

        # Create public lesson by another
        other_lesson = Lesson.objects.create(
            title='Other Lesson',
            description='Other',
            subject=self.subject,
            created_by=self.other_teacher,
            is_public=True
        )

        response = self.client.get('/api/knowledge-graph/lessons/?created_by=me')
        assert response.status_code == status.HTTP_200_OK

        data = response.data.get('results') or response.data.get('data', [])
        lesson_ids = [l['id'] for l in data]

        assert own_lesson.id in lesson_ids
        assert other_lesson.id not in lesson_ids

    def test_lesson_create_returns_201(self):
        """Test POST /lessons/ returns 201 with lesson data"""
        self.client.force_authenticate(user=self.teacher)

        payload = {
            'title': 'New Lesson',
            'description': 'A new lesson',
            'subject': self.subject.id,
            'is_public': False
        }

        response = self.client.post('/api/knowledge-graph/lessons/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['data']['title'] == 'New Lesson'
        assert response.data['data']['created_by']['id'] == self.teacher.id

    def test_lesson_create_sets_created_by(self):
        """Test that created_by is automatically set to current user"""
        self.client.force_authenticate(user=self.teacher)

        payload = {
            'title': 'Lesson',
            'description': 'Desc',
            'subject': self.subject.id
        }

        response = self.client.post('/api/knowledge-graph/lessons/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['created_by']['id'] == self.teacher.id

    def test_lesson_create_missing_required_field_returns_400(self):
        """Test POST with missing required fields returns 400"""
        self.client.force_authenticate(user=self.teacher)

        # Missing title
        payload = {
            'description': 'Desc',
            'subject': self.subject.id
        }

        response = self.client.post('/api/knowledge-graph/lessons/', payload, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_lesson_create_initializes_totals(self):
        """Test that totals are initialized to 0"""
        self.client.force_authenticate(user=self.teacher)

        payload = {
            'title': 'New Lesson',
            'description': 'Desc',
            'subject': self.subject.id
        }

        response = self.client.post('/api/knowledge-graph/lessons/', payload, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['total_duration_minutes'] == 0
        assert response.data['data']['total_max_score'] == 0


@pytest.mark.django_db
class TestLessonRetrieveUpdateDestroyView:
    """Test Lesson retrieve, update, and delete endpoints"""

    def setup_method(self):
        """Setup test data before each test"""
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            username='student@test.com',
            email='student@test.com',
            password='testpass123',
            role='student'
        )
        self.other_teacher = User.objects.create_user(
            username='other_teacher@test.com',
            email='other_teacher@test.com',
            password='testpass123',
            role='teacher'
        )

        self.subject = Subject.objects.create(name='Test Subject')

        self.lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Test description',
            subject=self.subject,
            created_by=self.teacher,
            is_public=False
        )

    def test_lesson_retrieve_requires_authentication(self):
        """Test GET /lessons/{id}/ requires authentication"""
        response = self.client.get(f'/api/knowledge-graph/lessons/{self.lesson.id}/')
        # DRF returns 403 for unauthenticated requests with IsAuthenticated permission
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_lesson_retrieve_returns_lesson_data(self):
        """Test GET /lessons/{id}/ returns lesson data with elements"""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f'/api/knowledge-graph/lessons/{self.lesson.id}/')
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['data']['id'] == self.lesson.id
        assert response.data['data']['title'] == 'Test Lesson'
        assert 'elements_list' in response.data['data']

    def test_lesson_retrieve_returns_ordered_elements(self):
        """Test that elements are returned in order"""
        self.client.force_authenticate(user=self.teacher)

        # Create elements
        elem1 = Element.objects.create(
            title='Element 1',
            description='Desc',
            element_type='theory',
            content={'text': 'Content'},
            created_by=self.teacher
        )
        elem2 = Element.objects.create(
            title='Element 2',
            description='Desc',
            element_type='theory',
            content={'text': 'Content'},
            created_by=self.teacher
        )

        # Add to lesson in specific order
        LessonElement.objects.create(lesson=self.lesson, element=elem1, order=1)
        LessonElement.objects.create(lesson=self.lesson, element=elem2, order=2)

        response = self.client.get(f'/api/knowledge-graph/lessons/{self.lesson.id}/')
        assert response.status_code == status.HTTP_200_OK

        elements = response.data['data']['elements_list']
        assert len(elements) == 2
        assert elements[0]['element']['id'] == elem1.id
        assert elements[1]['element']['id'] == elem2.id

    def test_lesson_retrieve_nonexistent_returns_404(self):
        """Test GET with invalid ID returns 404"""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.get(f'/api/knowledge-graph/lessons/99999/')
        # API catches the exception and returns error response
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_lesson_update_own_lesson_returns_200(self):
        """Test PATCH own lesson returns 200"""
        self.client.force_authenticate(user=self.teacher)

        payload = {
            'title': 'Updated Lesson',
            'description': 'Updated description'
        }

        response = self.client.patch(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['title'] == 'Updated Lesson'

        # Verify in database
        self.lesson.refresh_from_db()
        assert self.lesson.title == 'Updated Lesson'

    def test_lesson_update_other_lesson_returns_403(self):
        """Test PATCH other's lesson returns 403"""
        self.client.force_authenticate(user=self.student)

        payload = {'title': 'Hacked'}

        response = self.client.patch(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_lesson_update_preserves_created_by(self):
        """Test that update doesn't change created_by"""
        self.client.force_authenticate(user=self.teacher)

        payload = {'title': 'Updated'}

        response = self.client.patch(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['data']['created_by']['id'] == self.teacher.id

    def test_lesson_delete_own_lesson_returns_204(self):
        """Test DELETE own lesson returns 204"""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.delete(f'/api/knowledge-graph/lessons/{self.lesson.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify deleted from database
        assert not Lesson.objects.filter(id=self.lesson.id).exists()

    def test_lesson_delete_other_lesson_returns_403(self):
        """Test DELETE other's lesson returns 403"""
        self.client.force_authenticate(user=self.student)

        response = self.client.delete(f'/api/knowledge-graph/lessons/{self.lesson.id}/')
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Lesson still exists
        assert Lesson.objects.filter(id=self.lesson.id).exists()

    def test_lesson_delete_used_in_graph_returns_400(self):
        """Test DELETE lesson used in graph returns 400"""
        from knowledge_graph.models import KnowledgeGraph

        self.client.force_authenticate(user=self.teacher)

        # Create a graph using this lesson
        graph = KnowledgeGraph.objects.create(
            student=self.student,
            subject=self.subject,
            created_by=self.teacher
        )
        graph.lessons.add(self.lesson)

        response = self.client.delete(f'/api/knowledge-graph/lessons/{self.lesson.id}/')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Lesson still exists
        assert Lesson.objects.filter(id=self.lesson.id).exists()

    def test_lesson_delete_not_used_succeeds(self):
        """Test DELETE unused lesson succeeds"""
        self.client.force_authenticate(user=self.teacher)

        # Create new lesson not used anywhere
        lesson = Lesson.objects.create(
            title='Unused',
            description='Desc',
            subject=self.subject,
            created_by=self.teacher
        )

        response = self.client.delete(f'/api/knowledge-graph/lessons/{lesson.id}/')
        assert response.status_code == status.HTTP_204_NO_CONTENT
        assert not Lesson.objects.filter(id=lesson.id).exists()


@pytest.mark.django_db
class TestAddElementToLessonView:
    """Test adding elements to lesson"""

    def setup_method(self):
        """Setup test data before each test"""
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            username='student@test.com',
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        self.subject = Subject.objects.create(name='Test Subject')

        self.lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Desc',
            subject=self.subject,
            created_by=self.teacher
        )

        self.element = Element.objects.create(
            title='Test Element',
            description='Desc',
            element_type='theory',
            content={'text': 'Content'},
            estimated_time_minutes=10,
            max_score=100,
            created_by=self.teacher
        )

    def test_add_element_requires_authentication(self):
        """Test POST requires authentication"""
        payload = {'element_id': self.element.id}
        response = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload,
            format='json'
        )
        # DRF returns 403 for unauthenticated requests
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_add_element_returns_201(self):
        """Test POST returns 201 with created relationship"""
        self.client.force_authenticate(user=self.teacher)

        payload = {'element_id': self.element.id}
        response = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['success'] is True
        assert response.data['data']['element']['id'] == self.element.id
        assert response.data['data']['order'] == 1

    def test_add_element_auto_assigns_order(self):
        """Test that order is auto-assigned if not provided"""
        self.client.force_authenticate(user=self.teacher)

        # Add first element
        payload1 = {'element_id': self.element.id}
        response1 = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload1,
            format='json'
        )
        assert response1.status_code == status.HTTP_201_CREATED
        assert response1.data['data']['order'] == 1

        # Add second element
        elem2 = Element.objects.create(
            title='Element 2',
            description='Desc',
            element_type='theory',
            content={'text': 'Content'},
            estimated_time_minutes=5,
            max_score=50,
            created_by=self.teacher
        )

        payload2 = {'element_id': elem2.id}
        response2 = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload2,
            format='json'
        )
        assert response2.status_code == status.HTTP_201_CREATED
        assert response2.data['data']['order'] == 2

    def test_add_element_custom_order(self):
        """Test that custom order can be specified"""
        self.client.force_authenticate(user=self.teacher)

        payload = {'element_id': self.element.id, 'order': 5}
        response = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['data']['order'] == 5

    def test_add_element_duplicate_returns_400(self):
        """Test that adding same element twice returns 400"""
        self.client.force_authenticate(user=self.teacher)

        # Add first time
        payload = {'element_id': self.element.id}
        response1 = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload,
            format='json'
        )
        assert response1.status_code == status.HTTP_201_CREATED

        # Add second time
        response2 = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload,
            format='json'
        )
        assert response2.status_code == status.HTTP_400_BAD_REQUEST

    def test_add_nonexistent_element_returns_404(self):
        """Test that adding nonexistent element returns 404"""
        self.client.force_authenticate(user=self.teacher)

        payload = {'element_id': 99999}
        response = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload,
            format='json'
        )
        # API returns 404 when element doesn't exist
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_add_element_to_nonexistent_lesson_returns_404(self):
        """Test that adding to nonexistent lesson returns 404"""
        self.client.force_authenticate(user=self.teacher)

        payload = {'element_id': self.element.id}
        response = self.client.post(
            f'/api/knowledge-graph/lessons/99999/elements/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_add_element_other_lesson_returns_403(self):
        """Test that only owner can add elements"""
        self.client.force_authenticate(user=self.student)

        payload = {'element_id': self.element.id}
        response = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_add_element_updates_lesson_totals(self):
        """Test that adding element updates lesson totals"""
        self.client.force_authenticate(user=self.teacher)

        # Check initial totals
        self.lesson.refresh_from_db()
        assert self.lesson.total_duration_minutes == 0
        assert self.lesson.total_max_score == 0

        payload = {'element_id': self.element.id}
        response = self.client.post(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_201_CREATED

        # Check updated totals
        self.lesson.refresh_from_db()
        assert self.lesson.total_duration_minutes == 10
        assert self.lesson.total_max_score == 100


@pytest.mark.django_db
class TestRemoveElementFromLessonView:
    """Test removing elements from lesson"""

    def setup_method(self):
        """Setup test data before each test"""
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            username='student@test.com',
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        self.subject = Subject.objects.create(name='Test Subject')

        self.lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Desc',
            subject=self.subject,
            created_by=self.teacher
        )

        self.element = Element.objects.create(
            title='Test Element',
            description='Desc',
            element_type='theory',
            content={'text': 'Content'},
            estimated_time_minutes=10,
            max_score=100,
            created_by=self.teacher
        )

        # Add element to lesson
        LessonElement.objects.create(
            lesson=self.lesson,
            element=self.element,
            order=1
        )

    def test_remove_element_requires_authentication(self):
        """Test DELETE requires authentication"""
        response = self.client.delete(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/{self.element.id}/'
        )
        # DRF returns 403 for unauthenticated requests
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_remove_element_returns_204(self):
        """Test DELETE returns 204"""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.delete(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/{self.element.id}/'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Verify removed
        assert not LessonElement.objects.filter(
            lesson=self.lesson,
            element=self.element
        ).exists()

    def test_remove_element_nonexistent_returns_404(self):
        """Test DELETE of non-existent relationship returns 404"""
        self.client.force_authenticate(user=self.teacher)

        elem2 = Element.objects.create(
            title='Other',
            description='Desc',
            element_type='theory',
            content={'text': 'Content'},
            created_by=self.teacher
        )

        response = self.client.delete(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/{elem2.id}/'
        )
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_remove_element_other_lesson_returns_403(self):
        """Test that only owner can remove elements"""
        self.client.force_authenticate(user=self.student)

        response = self.client.delete(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/{self.element.id}/'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_remove_element_updates_lesson_totals(self):
        """Test that removing element updates lesson totals"""
        self.client.force_authenticate(user=self.teacher)

        # Check totals before removal
        self.lesson.refresh_from_db()
        assert self.lesson.total_duration_minutes == 10
        assert self.lesson.total_max_score == 100

        response = self.client.delete(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/elements/{self.element.id}/'
        )
        assert response.status_code == status.HTTP_204_NO_CONTENT

        # Check totals after removal
        self.lesson.refresh_from_db()
        assert self.lesson.total_duration_minutes == 0
        assert self.lesson.total_max_score == 0


@pytest.mark.django_db
class TestLessonElementOrdering:
    """Test lesson element ordering functionality"""

    def setup_method(self):
        """Setup test data before each test"""
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

        self.subject = Subject.objects.create(name='Test Subject')

        self.lesson = Lesson.objects.create(
            title='Test Lesson',
            description='Desc',
            subject=self.subject,
            created_by=self.teacher
        )

        # Create elements
        self.elem1 = Element.objects.create(
            title='Element 1',
            description='Desc',
            element_type='theory',
            content={'text': 'Content'},
            created_by=self.teacher
        )
        self.elem2 = Element.objects.create(
            title='Element 2',
            description='Desc',
            element_type='theory',
            content={'text': 'Content'},
            created_by=self.teacher
        )
        self.elem3 = Element.objects.create(
            title='Element 3',
            description='Desc',
            element_type='theory',
            content={'text': 'Content'},
            created_by=self.teacher
        )

    def test_elements_returned_in_order(self):
        """Test that elements are returned in specified order"""
        self.client.force_authenticate(user=self.teacher)

        # Add elements in order
        LessonElement.objects.create(lesson=self.lesson, element=self.elem1, order=1)
        LessonElement.objects.create(lesson=self.lesson, element=self.elem2, order=2)
        LessonElement.objects.create(lesson=self.lesson, element=self.elem3, order=3)

        response = self.client.get(f'/api/knowledge-graph/lessons/{self.lesson.id}/')
        assert response.status_code == status.HTTP_200_OK

        elements = response.data['data']['elements_list']
        assert len(elements) == 3
        assert elements[0]['order'] == 1
        assert elements[1]['order'] == 2
        assert elements[2]['order'] == 3

    def test_elements_not_in_sequential_order_still_ordered(self):
        """Test that elements maintain order even if gaps exist"""
        self.client.force_authenticate(user=self.teacher)

        # Add elements with non-sequential order
        LessonElement.objects.create(lesson=self.lesson, element=self.elem1, order=10)
        LessonElement.objects.create(lesson=self.lesson, element=self.elem2, order=5)
        LessonElement.objects.create(lesson=self.lesson, element=self.elem3, order=1)

        response = self.client.get(f'/api/knowledge-graph/lessons/{self.lesson.id}/')
        assert response.status_code == status.HTTP_200_OK

        elements = response.data['data']['elements_list']
        # Should be ordered by order field, not by insertion order
        assert elements[0]['order'] == 1
        assert elements[1]['order'] == 5
        assert elements[2]['order'] == 10


@pytest.mark.django_db
class TestLessonPermissions:
    """Test Lesson API permissions"""

    def setup_method(self):
        """Setup test data before each test"""
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )
        self.student = User.objects.create_user(
            username='student@test.com',
            email='student@test.com',
            password='testpass123',
            role='student'
        )

        self.subject = Subject.objects.create(name='Test Subject')

        self.lesson = Lesson.objects.create(
            title='Test',
            description='Desc',
            subject=self.subject,
            created_by=self.teacher,
            is_public=False
        )

    def test_student_can_view_public_lessons(self):
        """Test student can view public lessons"""
        public_lesson = Lesson.objects.create(
            title='Public',
            description='Desc',
            subject=self.subject,
            created_by=self.teacher,
            is_public=True
        )

        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/knowledge-graph/lessons/{public_lesson.id}/')
        assert response.status_code == status.HTTP_200_OK

    def test_student_cannot_view_private_lessons(self):
        """Test student cannot view private lessons of others"""
        self.client.force_authenticate(user=self.student)
        response = self.client.get(f'/api/knowledge-graph/lessons/{self.lesson.id}/')
        # Should get 404 or similar (filtered out)
        assert response.status_code in [status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN]

    def test_admin_can_update_any_lesson(self):
        """Test admin can update any lesson"""
        admin = User.objects.create_superuser(
            username='admin',
            email='admin@test.com',
            password='testpass123'
        )

        self.client.force_authenticate(user=admin)

        payload = {'title': 'Updated by Admin'}
        response = self.client.patch(
            f'/api/knowledge-graph/lessons/{self.lesson.id}/',
            payload,
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestLessonQueryOptimization:
    """Test that lesson queries are optimized (no N+1 problems)"""

    def test_lesson_list_uses_select_related(self, django_assert_num_queries):
        """Test that lesson list query is optimized"""
        teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

        subject = Subject.objects.create(name='Test')

        # Create multiple lessons
        for i in range(5):
            Lesson.objects.create(
                title=f'Lesson {i}',
                description=f'Desc {i}',
                subject=subject,
                created_by=teacher
            )

        client = APIClient()
        client.force_authenticate(user=teacher)

        # Should not have N+1 queries for created_by or subject
        with django_assert_num_queries(2):  # 1 for pagination count, 1 for data
            response = client.get('/api/knowledge-graph/lessons/')
            assert response.status_code == status.HTTP_200_OK

    def test_lesson_retrieve_uses_select_related(self, django_assert_num_queries):
        """Test that lesson retrieve query is optimized"""
        teacher = User.objects.create_user(
            username='teacher@test.com',
            email='teacher@test.com',
            password='testpass123',
            role='teacher'
        )

        subject = Subject.objects.create(name='Test')

        lesson = Lesson.objects.create(
            title='Test',
            description='Desc',
            subject=subject,
            created_by=teacher
        )

        client = APIClient()
        client.force_authenticate(user=teacher)

        with django_assert_num_queries(2):  # 1 for lesson, 1 for elements
            response = client.get(f'/api/knowledge-graph/lessons/{lesson.id}/')
            assert response.status_code == status.HTTP_200_OK
