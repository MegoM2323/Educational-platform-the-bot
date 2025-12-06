"""
Unit tests for asynchronous study plan generation via Celery.

Tests cover:
- Immediate API response with generation_id
- Status endpoint polling
- Progress message updates
- Celery task execution
- Error handling in async context

Запуск:
    pytest backend/tests/unit/materials/test_async_generation.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient

from materials.models import (
    Subject,
    SubjectEnrollment,
    StudyPlanGeneration,
    GeneratedFile
)
from materials.tasks import generate_study_plan_async


User = get_user_model()
pytestmark = [pytest.mark.unit, pytest.mark.django_db]


@pytest.fixture
def api_client():
    """REST API client"""
    return APIClient()


@pytest.fixture
def teacher_user(db):
    """Преподаватель для тестов"""
    return User.objects.create_user(
        username='teacher_async@test.com',
        email='teacher_async@test.com',
        password='testpass123',
        role=User.Role.TEACHER,
        first_name='Test',
        last_name='Teacher'
    )


@pytest.fixture
def student_user(db):
    """Студент для тестов"""
    return User.objects.create_user(
        username='student_async@test.com',
        email='student_async@test.com',
        password='testpass123',
        role=User.Role.STUDENT,
        first_name='Test',
        last_name='Student'
    )


@pytest.fixture
def subject(db):
    """Предмет для тестов"""
    return Subject.objects.create(
        name='Математика',
        description='Тестовый предмет'
    )


@pytest.fixture
def enrollment(teacher_user, student_user, subject):
    """Зачисление студента на предмет к преподавателю"""
    return SubjectEnrollment.objects.create(
        teacher=teacher_user,
        student=student_user,
        subject=subject,
        is_active=True
    )


class TestAsyncGenerationAPI:
    """Тесты API endpoint для асинхронной генерации"""

    def test_generate_returns_immediately_with_generation_id(
        self, api_client, teacher_user, student_user, subject, enrollment
    ):
        """
        API должен вернуть ответ немедленно (< 1s) с generation_id,
        не дожидаясь завершения генерации
        """
        # Мокируем Celery task
        with patch('materials.study_plan_views.generate_study_plan_async') as mock_task:
            mock_task.delay = Mock()

            api_client.force_authenticate(user=teacher_user)

            payload = {
                'student_id': student_user.id,
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Квадратные уравнения',
                'subtopics': 'решение, дискриминант',
                'goal': 'ОГЭ',
                'task_counts': {'A': 12, 'B': 10, 'C': 6}
            }

            response = api_client.post(
                '/api/materials/study-plan/generate/',
                payload,
                format='json'
            )

            # Проверяем успешный ответ
            assert response.status_code == status.HTTP_200_OK
            assert response.data['success'] is True
            assert 'generation_id' in response.data
            assert response.data['status'] == 'pending'
            assert 'progress_message' in response.data

            # Проверяем что Celery task был запущен
            mock_task.delay.assert_called_once()

            # Проверяем что запись создана в БД
            generation = StudyPlanGeneration.objects.get(
                id=response.data['generation_id']
            )
            assert generation.status == StudyPlanGeneration.Status.PENDING
            assert generation.progress_message == 'Ожидает обработки...'

    def test_status_endpoint_returns_progress(
        self, api_client, teacher_user, student_user, subject, enrollment
    ):
        """
        Status endpoint должен возвращать текущий прогресс генерации
        """
        # Создаём запись генерации вручную
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={'grade': 9, 'topic': 'Test'},
            status=StudyPlanGeneration.Status.PROCESSING,
            progress_message='Генерация задачника...'
        )

        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(
            f'/api/materials/study-plan/generation/{generation.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert response.data['status'] == 'processing'
        assert response.data['progress_message'] == 'Генерация задачника...'
        assert 'files' in response.data
        assert response.data['files'] == []  # Пока нет файлов

    def test_status_endpoint_returns_files_when_completed(
        self, api_client, teacher_user, student_user, subject, enrollment
    ):
        """
        Status endpoint должен возвращать файлы при status=completed
        """
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={'grade': 9, 'topic': 'Test'},
            status=StudyPlanGeneration.Status.COMPLETED,
            progress_message='Генерация завершена успешно'
        )

        # Создаём сгенерированные файлы
        GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.PROBLEM_SET,
            status=GeneratedFile.Status.COMPILED
        )
        GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.REFERENCE_GUIDE,
            status=GeneratedFile.Status.COMPILED
        )

        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(
            f'/api/materials/study-plan/generation/{generation.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'completed'
        assert len(response.data['files']) == 2
        assert response.data['files'][0]['type'] == 'problem_set'

    def test_status_endpoint_returns_error_when_failed(
        self, api_client, teacher_user, student_user, subject, enrollment
    ):
        """
        Status endpoint должен возвращать ошибку при status=failed
        """
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={'grade': 9, 'topic': 'Test'},
            status=StudyPlanGeneration.Status.FAILED,
            error_message='OpenRouterError: API rate limit exceeded',
            progress_message='Ошибка генерации'
        )

        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(
            f'/api/materials/study-plan/generation/{generation.id}/'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'failed'
        assert 'error_message' in response.data
        assert 'API rate limit' in response.data['error_message']

    def test_status_endpoint_403_for_non_owner(
        self, api_client, teacher_user, student_user, subject, enrollment
    ):
        """
        Status endpoint должен возвращать 403 если запрашивает не владелец генерации
        """
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={'grade': 9, 'topic': 'Test'},
            status=StudyPlanGeneration.Status.PROCESSING
        )

        # Создаём другого teacher
        other_teacher = User.objects.create_user(
            username='other_teacher@test.com',
            email='other_teacher@test.com',
            password='testpass123',
            role=User.Role.TEACHER
        )

        api_client.force_authenticate(user=other_teacher)

        response = api_client.get(
            f'/api/materials/study-plan/generation/{generation.id}/'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert 'Доступ запрещён' in response.data['error']


class TestCeleryTaskExecution:
    """Тесты выполнения Celery задачи"""

    def test_celery_task_updates_progress_messages(
        self, teacher_user, student_user, subject, enrollment
    ):
        """
        Celery task должен обновлять progress_message на каждом этапе
        """
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={
                'subject': 'Математика',
                'grade': 9,
                'topic': 'Квадратные уравнения',
                'subtopics': 'решение',
                'goal': 'ОГЭ',
                'task_counts': {'A': 12, 'B': 10, 'C': 6},
                'reference_level': 'средний',
                'video_duration': '10-25',
                'video_language': 'русский'
            },
            status=StudyPlanGeneration.Status.PENDING
        )

        # Мокируем все внешние сервисы
        with patch(
            'materials.tasks.StudyPlanGeneratorService'
        ) as mock_service_class:
            mock_service = mock_service_class.return_value

            # Мокируем генерацию файлов
            mock_problem_set = GeneratedFile.objects.create(
                generation=generation,
                file_type=GeneratedFile.FileType.PROBLEM_SET,
                status=GeneratedFile.Status.COMPILED
            )
            mock_reference = GeneratedFile.objects.create(
                generation=generation,
                file_type=GeneratedFile.FileType.REFERENCE_GUIDE,
                status=GeneratedFile.Status.COMPILED
            )
            mock_videos = GeneratedFile.objects.create(
                generation=generation,
                file_type=GeneratedFile.FileType.VIDEO_LIST,
                status=GeneratedFile.Status.COMPILED
            )
            mock_weekly = GeneratedFile.objects.create(
                generation=generation,
                file_type=GeneratedFile.FileType.WEEKLY_PLAN,
                status=GeneratedFile.Status.COMPILED
            )

            mock_service._generate_and_compile_problem_set.return_value = mock_problem_set
            mock_service._generate_and_compile_reference_guide.return_value = mock_reference
            mock_service._generate_video_list.return_value = mock_videos
            mock_service._generate_weekly_plan.return_value = mock_weekly

            # Запускаем task
            result = generate_study_plan_async(generation.id)

            # Проверяем результат
            assert result['success'] is True
            assert result['generation_id'] == generation.id

            # Проверяем финальное состояние в БД
            generation.refresh_from_db()
            assert generation.status == StudyPlanGeneration.Status.COMPLETED
            assert generation.progress_message == 'Генерация завершена успешно'

    def test_celery_task_handles_errors_correctly(
        self, teacher_user, student_user, subject, enrollment
    ):
        """
        Celery task должен корректно обрабатывать ошибки и обновлять статус на failed
        """
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={
                'subject': 'Математика',
                'grade': 9,
                'topic': 'Test',
                'subtopics': 'test',
                'goal': 'test',
                'task_counts': {'A': 12, 'B': 10, 'C': 6}
            },
            status=StudyPlanGeneration.Status.PENDING
        )

        # Мокируем сервис чтобы выбросить ошибку
        with patch(
            'materials.tasks.StudyPlanGeneratorService'
        ) as mock_service_class:
            mock_service = mock_service_class.return_value
            mock_service._generate_and_compile_problem_set.side_effect = Exception(
                'Test error'
            )

            # Запускаем task (должен поймать ошибку)
            with pytest.raises(Exception):
                generate_study_plan_async(generation.id)

            # Проверяем что статус обновлён на failed
            generation.refresh_from_db()
            assert generation.status == StudyPlanGeneration.Status.FAILED
            assert 'Test error' in generation.error_message
            assert generation.progress_message == 'Ошибка генерации'
