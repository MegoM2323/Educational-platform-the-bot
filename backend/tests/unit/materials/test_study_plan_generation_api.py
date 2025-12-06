"""
Unit тесты для API endpoint генерации учебных планов
"""
import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from materials.models import Subject, SubjectEnrollment


User = get_user_model()


@pytest.fixture
def api_client():
    """API клиент"""
    return APIClient()


@pytest.fixture
def teacher_user(db):
    """Преподаватель"""
    return User.objects.create_user(
        email='teacher@test.com',
        password='testpass123',
        role=User.Role.TEACHER,
        username='teacher_test'
    )


@pytest.fixture
def student_user(db):
    """Студент"""
    return User.objects.create_user(
        email='student@test.com',
        password='testpass123',
        role=User.Role.STUDENT,
        username='student_test'
    )


@pytest.fixture
def subject(db):
    """Предмет"""
    return Subject.objects.create(
        name='Математика',
        description='Алгебра 9 класс'
    )


@pytest.fixture
def enrollment(teacher_user, student_user, subject):
    """Зачисление студента на предмет"""
    return SubjectEnrollment.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=subject,
        is_active=True
    )


@pytest.mark.django_db
class TestGenerateStudyPlanAPI:
    """Тесты для endpoint /api/materials/study-plan/generate/"""

    def test_endpoint_requires_authentication(self, api_client):
        """Endpoint требует аутентификации"""
        response = api_client.post('/api/materials/study-plan/generate/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_endpoint_requires_teacher_role(self, api_client, student_user):
        """Endpoint доступен только для преподавателей"""
        api_client.force_authenticate(user=student_user)
        response = api_client.post('/api/materials/study-plan/generate/')
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'преподавателя' in response.data['error'].lower()

    def test_missing_required_fields(self, api_client, teacher_user):
        """Валидация обязательных полей"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={}
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'обязательные поля' in response.data['error'].lower()

    def test_invalid_student_id(self, api_client, teacher_user, subject):
        """Валидация несуществующего студента"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': 99999,
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Квадратные уравнения',
                'subtopics': 'решение, дискриминант',
                'goal': 'ОГЭ',
                'task_counts': {'A': 12, 'B': 10, 'C': 6}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'не найден' in response.data['error'].lower()

    def test_enrollment_not_found(
        self,
        api_client,
        teacher_user,
        student_user,
        subject
    ):
        """Валидация отсутствия enrollment"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': student_user.id,
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Квадратные уравнения',
                'subtopics': 'решение, дискриминант',
                'goal': 'ОГЭ',
                'task_counts': {'A': 12, 'B': 10, 'C': 6}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'не зачислен' in response.data['error'].lower()

    @pytest.mark.skip(reason="Requires OpenRouter API mocking")
    def test_valid_request_with_enrollment(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        enrollment
    ):
        """Успешная генерация учебного плана (требует мокирование API)"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': student_user.id,
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Квадратные уравнения',
                'subtopics': 'решение, дискриминант, теорема Виета',
                'goal': 'ОГЭ',
                'task_counts': {'A': 12, 'B': 10, 'C': 6},
                'constraints': 'Время: 60 мин',
                'reference_level': 'средний',
                'video_duration': '10-25',
                'video_language': 'русский'
            },
            format='json'
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'generation_id' in response.data
        assert 'files' in response.data
        assert len(response.data['files']) == 4
