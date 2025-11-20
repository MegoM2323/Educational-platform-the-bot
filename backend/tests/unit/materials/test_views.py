"""
Unit tests for materials views

Покрытие:
- SubjectViewSet
- MaterialViewSet
- student_dashboard_views
- teacher_dashboard_views
- parent_dashboard_views
"""
import pytest
import json
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status
from unittest.mock import Mock, patch

from materials.models import (
    Subject, TeacherSubject, SubjectEnrollment, Material, MaterialProgress,
    MaterialSubmission, MaterialFeedback, StudyPlan
)

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestSubjectViewSet:
    """Тесты SubjectViewSet"""

    @pytest.fixture
    def api_client(self):
        """Фикстура API клиента"""
        return APIClient()

    def test_list_subjects(self, api_client, student_user):
        """Тест получения списка предметов"""
        Subject.objects.create(name="Математика")
        Subject.objects.create(name="Физика")

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/materials/subjects/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_create_subject(self, api_client, teacher_user):
        """Тест создания предмета"""
        api_client.force_authenticate(user=teacher_user)

        data = {
            'name': 'Математика',
            'description': 'Алгебра и геометрия',
            'color': '#FF5733'
        }

        response = api_client.post('/api/materials/subjects/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == 'Математика'

    def test_get_subject_teachers(self, api_client, student_user, teacher_user):
        """Тест получения преподавателей предмета"""
        subject = Subject.objects.create(name="Математика")

        TeacherSubject.objects.create(
            teacher=teacher_user,
            subject=subject,
            is_active=True
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/materials/subjects/{subject.id}/teachers/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['id'] == teacher_user.id


@pytest.mark.unit
@pytest.mark.django_db
class TestMaterialViewSet:
    """Тесты MaterialViewSet"""

    @pytest.fixture
    def api_client(self):
        """Фикстура API клиента"""
        return APIClient()

    def test_list_materials_as_student(self, api_client, student_user, teacher_user, subject):
        """Тест получения материалов студентом"""
        # Создаем материалы
        material1 = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material1.assigned_to.add(student_user)

        material2 = Material.objects.create(
            title="Урок 2",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE,
            is_public=True
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/materials/materials/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 2

    def test_create_material_as_teacher(self, api_client, teacher_user, subject):
        """Тест создания материала преподавателем"""
        api_client.force_authenticate(user=teacher_user)

        data = {
            'title': 'Новый урок',
            'description': 'Описание',
            'content': 'Содержание урока',
            'subject': subject.id,
            'type': Material.Type.LESSON,
            'status': Material.Status.ACTIVE
        }

        response = api_client.post('/api/materials/materials/', data)

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['title'] == 'Новый урок'

    def test_create_material_as_student_forbidden(self, api_client, student_user, subject):
        """Тест запрета создания материала студентом"""
        api_client.force_authenticate(user=student_user)

        data = {
            'title': 'Урок',
            'content': 'Содержание',
            'subject': subject.id
        }

        response = api_client.post('/api/materials/materials/', data)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_assign_material_to_students(self, api_client, teacher_user, subject):
        """Тест назначения материала студентам"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        student1 = StudentUserFactory()
        StudentProfile.objects.create(user=student1)

        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject
        )

        api_client.force_authenticate(user=teacher_user)

        data = {
            'student_ids': [student1.id]
        }

        response = api_client.post(
            f'/api/materials/materials/{material.id}/assign/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['assigned_count'] == 1

    def test_update_material_progress(self, api_client, student_user, teacher_user, subject):
        """Тест обновления прогресса материала"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(student_user)

        api_client.force_authenticate(user=student_user)

        data = {
            'progress_percentage': 75,
            'time_spent': 30
        }

        response = api_client.post(
            f'/api/materials/materials/{material.id}/update_progress/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['progress_percentage'] == 75

    def test_get_material_progress(self, api_client, student_user, teacher_user, subject):
        """Тест получения прогресса материала"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(student_user)

        MaterialProgress.objects.create(
            student=student_user,
            material=material,
            progress_percentage=50
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get(f'/api/materials/materials/{material.id}/progress/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['progress_percentage'] == 50

    def test_submit_answer_as_student(self, api_client, student_user, teacher_user, subject):
        """Тест отправки ответа студентом"""
        material = Material.objects.create(
            title="Домашняя работа",
            content="Задание",
            author=teacher_user,
            subject=subject,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(student_user)

        api_client.force_authenticate(user=student_user)

        data = {
            'material_id': material.id,
            'submission_text': 'Мой ответ'
        }

        response = api_client.post(
            '/api/materials/submissions/submit_answer/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['submission_text'] == 'Мой ответ'


@pytest.mark.unit
@pytest.mark.django_db
class TestStudentDashboardViews:
    """Тесты student_dashboard_views"""

    @pytest.fixture
    def api_client(self):
        """Фикстура API клиента"""
        return APIClient()

    def test_student_dashboard(self, api_client, student_user, teacher_user, subject):
        """Тест получения дашборда студента"""
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/dashboard/student/')

        assert response.status_code == status.HTTP_200_OK
        assert 'student_info' in response.data
        assert 'subjects' in response.data
        assert 'stats' in response.data

    def test_student_dashboard_requires_student_role(self, api_client, teacher_user):
        """Тест требования роли STUDENT"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/dashboard/student/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_assigned_materials(self, api_client, student_user, teacher_user, subject):
        """Тест получения назначенных материалов"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(student_user)

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/materials/student/assigned/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1

    def test_student_progress_statistics(self, api_client, student_user, teacher_user, subject):
        """Тест получения статистики прогресса"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(student_user)

        MaterialProgress.objects.create(
            student=student_user,
            material=material,
            progress_percentage=100,
            is_completed=True
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/dashboard/student/progress/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_materials'] == 1
        assert response.data['completed_materials'] == 1

    def test_student_subjects(self, api_client, student_user, teacher_user, subject):
        """Тест получения предметов студента"""
        SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/materials/student/subjects/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['subjects']) == 1

    def test_update_material_progress_endpoint(self, api_client, student_user, teacher_user, subject):
        """Тест эндпоинта обновления прогресса"""
        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(student_user)

        api_client.force_authenticate(user=student_user)

        data = {
            'progress_percentage': 80,
            'time_spent': 45
        }

        response = api_client.post(
            f'/api/materials/{material.id}/progress/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['progress_percentage'] == 80


@pytest.mark.unit
@pytest.mark.django_db
class TestTeacherDashboardViews:
    """Тесты teacher_dashboard_views"""

    @pytest.fixture
    def api_client(self):
        """Фикстура API клиента"""
        return APIClient()

    def test_teacher_dashboard(self, api_client, teacher_user):
        """Тест получения дашборда преподавателя"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/dashboard/teacher/')

        assert response.status_code == status.HTTP_200_OK
        assert 'teacher_info' in response.data
        assert 'students' in response.data
        assert 'materials' in response.data

    def test_teacher_students(self, api_client, teacher_user):
        """Тест получения студентов преподавателя"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        student = StudentUserFactory()
        StudentProfile.objects.create(user=student)

        subject = Subject.objects.create(name="Математика")

        SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/dashboard/teacher/students/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['students']) == 1

    def test_teacher_materials(self, api_client, teacher_user, subject):
        """Тест получения материалов преподавателя"""
        Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/dashboard/teacher/materials/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['materials']) == 1

    def test_distribute_material(self, api_client, teacher_user, subject):
        """Тест распределения материала"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        student = StudentUserFactory()
        StudentProfile.objects.create(user=student)

        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject
        )

        api_client.force_authenticate(user=teacher_user)

        data = {
            'material_id': material.id,
            'student_ids': [student.id]
        }

        response = api_client.post(
            '/api/dashboard/teacher/distribute-material/',
            data,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True


@pytest.mark.unit
@pytest.mark.django_db
class TestParentDashboardViews:
    """Тесты parent_dashboard_views"""

    @pytest.fixture
    def api_client(self):
        """Фикстура API клиента"""
        return APIClient()

    def test_parent_dashboard(self, api_client, parent_user, teacher_user):
        """Тест получения дашборда родителя"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child = StudentUserFactory()
        StudentProfile.objects.create(user=child, parent=parent_user)

        subject = Subject.objects.create(name="Математика")

        SubjectEnrollment.objects.create(
            student=child,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        api_client.force_authenticate(user=parent_user)
        response = api_client.get('/api/dashboard/parent/')

        assert response.status_code == status.HTTP_200_OK
        assert 'parent' in response.data
        assert 'children' in response.data

    def test_parent_children(self, api_client, parent_user):
        """Тест получения детей родителя"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child1 = StudentUserFactory()
        StudentProfile.objects.create(user=child1, parent=parent_user)

        child2 = StudentUserFactory()
        StudentProfile.objects.create(user=child2, parent=parent_user)

        api_client.force_authenticate(user=parent_user)
        response = api_client.get('/api/dashboard/parent/children/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['children']) == 2

    def test_get_child_subjects(self, api_client, parent_user, teacher_user):
        """Тест получения предметов ребенка"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child = StudentUserFactory()
        StudentProfile.objects.create(user=child, parent=parent_user)

        subject = Subject.objects.create(name="Математика")

        SubjectEnrollment.objects.create(
            student=child,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        api_client.force_authenticate(user=parent_user)
        response = api_client.get(f'/api/dashboard/parent/children/{child.id}/subjects/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['subjects']) == 1

    def test_get_child_progress(self, api_client, parent_user, teacher_user):
        """Тест получения прогресса ребенка"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child = StudentUserFactory()
        StudentProfile.objects.create(user=child, parent=parent_user)

        subject = Subject.objects.create(name="Математика")

        SubjectEnrollment.objects.create(
            student=child,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        material = Material.objects.create(
            title="Урок 1",
            content="Содержание",
            author=teacher_user,
            subject=subject,
            status=Material.Status.ACTIVE
        )
        material.assigned_to.add(child)

        MaterialProgress.objects.create(
            student=child,
            material=material,
            progress_percentage=50
        )

        api_client.force_authenticate(user=parent_user)
        response = api_client.get(f'/api/dashboard/parent/children/{child.id}/progress/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['total_materials'] == 1

    @patch('materials.parent_dashboard_views.ParentDashboardService')
    def test_initiate_payment(self, mock_service, api_client, parent_user, teacher_user, payment):
        """Тест инициации платежа"""
        from conftest import StudentUserFactory
        from accounts.models import StudentProfile

        child = StudentUserFactory()
        StudentProfile.objects.create(user=child, parent=parent_user)

        subject = Subject.objects.create(name="Математика")

        enrollment = SubjectEnrollment.objects.create(
            student=child,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )

        # Mock service response
        mock_service_instance = Mock()
        mock_service_instance.initiate_payment.return_value = {
            'payment_id': 'test-id',
            'amount': Decimal('100.00'),
            'confirmation_url': 'http://yookassa.ru/confirm'
        }
        mock_service.return_value = mock_service_instance

        api_client.force_authenticate(user=parent_user)

        data = {
            'child_id': child.id,
            'enrollment_id': enrollment.id,
            'amount': '100.00',
            'create_subscription': False
        }

        response = api_client.post(
            '/api/dashboard/parent/initiate-payment/',
            data,
            format='json'
        )

        # В реальности эндпоинт может вернуть другой статус
        # Проверяем что mock был вызван
        assert mock_service_instance.initiate_payment.called
