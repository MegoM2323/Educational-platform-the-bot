"""
Integration tests for Study Plan Generation API endpoint.

Tests cover complete request-response cycle for:
- POST /api/materials/study-plan/generate/ - Generate study plan
- Authentication and authorization (teacher role required)
- Enrollment validation (teacher-student-subject relationship)
- Parameter validation
- External service mocking (OpenRouter API, LaTeX compiler)
- Full database state verification
- Error handling

Запуск:
    pytest backend/tests/integration/materials/test_study_plan_api.py -v
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from materials.models import Subject, SubjectEnrollment, StudyPlanGeneration, GeneratedFile
from materials.services.openrouter_service import OpenRouterError
from materials.services.latex_compiler import LaTeXCompilationError

User = get_user_model()

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def api_client():
    """REST API client"""
    return APIClient()


@pytest.fixture
def valid_request_payload(student_user, subject):
    """Valid request payload for study plan generation"""
    return {
        'student_id': student_user.id,
        'subject_id': subject.id,
        'grade': 9,
        'topic': 'Квадратные уравнения',
        'subtopics': 'решение, дискриминант, теорема Виета',
        'goal': 'ОГЭ',
        'task_counts': {'A': 12, 'B': 10, 'C': 6},
        'constraints': 'Время: 60 мин',
        'reference_level': 'средний',
        'examples_count': 'стандартный',
        'video_duration': '10-25',
        'video_language': 'русский'
    }


@pytest.fixture
def mock_openrouter_service(mocker):
    """Mock OpenRouterService to avoid real API calls"""
    mock_service = mocker.patch(
        'materials.services.study_plan_generator_service.OpenRouterService'
    )

    # Mock instance methods
    mock_instance = mock_service.return_value
    mock_instance.generate_problem_set.return_value = r"""
\documentclass{article}
\begin{document}
\section{Задачи}
Тестовая задача 1: Решите уравнение $x^2 - 5x + 6 = 0$
\end{document}
"""
    mock_instance.generate_reference_guide.return_value = r"""
\documentclass{article}
\begin{document}
\section{Справочник}
Квадратное уравнение имеет вид $ax^2 + bx + c = 0$
\end{document}
"""
    mock_instance.generate_video_list.return_value = """# Видео-подборка

1. [Квадратные уравнения - основы](https://youtube.com/test1)
2. [Дискриминант](https://youtube.com/test2)
"""

    return mock_instance


@pytest.fixture
def mock_latex_compiler(mocker, tmp_path):
    """Mock LatexCompilerService to avoid real LaTeX compilation"""
    mock_service = mocker.patch(
        'materials.services.study_plan_generator_service.LatexCompilerService'
    )

    # Create fake PDF file
    fake_pdf_path = tmp_path / "fake_output.pdf"
    fake_pdf_path.write_bytes(b"%PDF-1.4 fake pdf content")

    # Mock instance methods
    mock_instance = mock_service.return_value
    mock_instance.compile_to_pdf.return_value = str(fake_pdf_path)

    return mock_instance


class TestGenerateStudyPlanAuthentication:
    """Test authentication and authorization for generate endpoint"""

    def test_endpoint_requires_authentication(self, api_client, valid_request_payload):
        """Endpoint требует аутентификации"""
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_endpoint_requires_teacher_role(
        self,
        api_client,
        student_user,
        valid_request_payload
    ):
        """Endpoint доступен только для преподавателей"""
        api_client.force_authenticate(user=student_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data['success'] is False
        assert 'преподавателя' in response.data['error'].lower()

    def test_parent_role_forbidden(self, api_client, parent_user, valid_request_payload):
        """Parent role cannot access endpoint"""
        api_client.force_authenticate(user=parent_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tutor_role_forbidden(self, api_client, tutor_user, valid_request_payload):
        """Tutor role cannot access endpoint"""
        api_client.force_authenticate(user=tutor_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestGenerateStudyPlanValidation:
    """Test parameter validation"""

    def test_missing_required_fields(self, api_client, teacher_user):
        """Валидация обязательных полей"""
        api_client.force_authenticate(user=teacher_user)

        # Empty request
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={},
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data['success'] is False
        assert 'обязательные поля' in response.data['error'].lower()

    def test_missing_student_id(self, api_client, teacher_user, subject):
        """Отсутствует student_id"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Test',
                'subtopics': 'Test',
                'goal': 'Test',
                'task_counts': {'A': 10}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'обязательные поля' in response.data['error'].lower()

    def test_invalid_student_id_type(
        self,
        api_client,
        teacher_user,
        subject
    ):
        """student_id должен быть числом"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': 'not-a-number',
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Test',
                'subtopics': 'Test',
                'goal': 'Test',
                'task_counts': {'A': 10}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'должны быть числами' in response.data['error'].lower()

    def test_invalid_grade_type(
        self,
        api_client,
        teacher_user,
        student_user,
        subject
    ):
        """grade должен быть числом"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': student_user.id,
                'subject_id': subject.id,
                'grade': 'ninth',
                'topic': 'Test',
                'subtopics': 'Test',
                'goal': 'Test',
                'task_counts': {'A': 10}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'должны быть числами' in response.data['error'].lower()

    def test_invalid_task_counts_type(
        self,
        api_client,
        teacher_user,
        student_user,
        subject
    ):
        """task_counts должен быть объектом"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': student_user.id,
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Test',
                'subtopics': 'Test',
                'goal': 'Test',
                'task_counts': 'not-a-dict'
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'должен быть объектом' in response.data['error'].lower()

    def test_student_not_found(self, api_client, teacher_user, subject):
        """Студент с указанным ID не существует"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': 99999,
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Test',
                'subtopics': 'Test',
                'goal': 'Test',
                'task_counts': {'A': 10}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'не найден' in response.data['error'].lower()

    def test_subject_not_found(self, api_client, teacher_user, student_user):
        """Предмет с указанным ID не существует"""
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': student_user.id,
                'subject_id': 99999,
                'grade': 9,
                'topic': 'Test',
                'subtopics': 'Test',
                'goal': 'Test',
                'task_counts': {'A': 10}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'не найден' in response.data['error'].lower()


class TestGenerateStudyPlanEnrollmentValidation:
    """Test enrollment validation"""

    def test_enrollment_not_found(
        self,
        api_client,
        teacher_user,
        student_user,
        subject
    ):
        """Студент не зачислен на предмет к данному преподавателю"""
        # No enrollment exists
        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': student_user.id,
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Test',
                'subtopics': 'Test',
                'goal': 'Test',
                'task_counts': {'A': 10}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'не зачислен' in response.data['error'].lower()

    def test_inactive_enrollment_rejected(
        self,
        api_client,
        teacher_user,
        student_user,
        subject
    ):
        """Неактивное зачисление не проходит валидацию"""
        # Create inactive enrollment
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=False
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': student_user.id,
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Test',
                'subtopics': 'Test',
                'goal': 'Test',
                'task_counts': {'A': 10}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'не зачислен' in response.data['error'].lower()

    def test_wrong_teacher_enrollment(
        self,
        api_client,
        teacher_user,
        student_user,
        subject
    ):
        """Студент зачислен на предмет, но к другому преподавателю"""
        # Create another teacher
        other_teacher = User.objects.create_user(
            username='other_teacher',
            email='other_teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        from accounts.models import TeacherProfile
        TeacherProfile.objects.create(user=other_teacher)

        # Enrollment with other teacher
        SubjectEnrollment.objects.create(
            teacher=other_teacher,
            student=student_user,
            subject=subject,
            is_active=True
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data={
                'student_id': student_user.id,
                'subject_id': subject.id,
                'grade': 9,
                'topic': 'Test',
                'subtopics': 'Test',
                'goal': 'Test',
                'task_counts': {'A': 10}
            },
            format='json'
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'не зачислен' in response.data['error'].lower()


class TestGenerateStudyPlanSuccess:
    """Test successful study plan generation"""

    def test_valid_request_returns_200_with_generation_data(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        valid_request_payload,
        mock_openrouter_service,
        mock_latex_compiler
    ):
        """Успешная генерация учебного плана возвращает 200 и данные"""
        # Create enrollment
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True
        assert 'generation_id' in response.data
        assert 'status' in response.data
        assert 'files' in response.data
        assert response.data['status'] == 'completed'

    def test_response_includes_all_four_files(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        valid_request_payload,
        mock_openrouter_service,
        mock_latex_compiler
    ):
        """Ответ содержит все 4 файла: problem_set, reference_guide, video_list, weekly_plan"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        files = response.data['files']
        assert len(files) == 4

        file_types = [f['type'] for f in files]
        assert 'problem_set' in file_types
        assert 'reference_guide' in file_types
        assert 'video_list' in file_types
        assert 'weekly_plan' in file_types

    def test_all_files_have_urls(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        valid_request_payload,
        mock_openrouter_service,
        mock_latex_compiler
    ):
        """Все файлы имеют URL"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        files = response.data['files']

        for file_obj in files:
            assert 'url' in file_obj
            assert file_obj['url'] is not None
            assert file_obj['url'].startswith('/media/')

    def test_database_records_created(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        valid_request_payload,
        mock_openrouter_service,
        mock_latex_compiler
    ):
        """Создаются записи в БД: StudyPlanGeneration и GeneratedFile"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        generation_id = response.data['generation_id']

        # Check StudyPlanGeneration record
        generation = StudyPlanGeneration.objects.get(id=generation_id)
        assert generation.teacher == teacher_user
        assert generation.student == student_user
        assert generation.subject == subject
        assert generation.status == StudyPlanGeneration.Status.COMPLETED
        assert generation.parameters == {
            'subject': subject.name,
            'grade': 9,
            'topic': 'Квадратные уравнения',
            'subtopics': 'решение, дискриминант, теорема Виета',
            'goal': 'ОГЭ',
            'task_counts': {'A': 12, 'B': 10, 'C': 6},
            'constraints': 'Время: 60 мин',
            'reference_level': 'средний',
            'examples_count': 'стандартный',
            'video_duration': '10-25',
            'video_language': 'русский'
        }

        # Check GeneratedFile records
        generated_files = GeneratedFile.objects.filter(generation=generation)
        assert generated_files.count() == 4

        file_types = set(generated_files.values_list('file_type', flat=True))
        assert file_types == {
            GeneratedFile.FileType.PROBLEM_SET,
            GeneratedFile.FileType.REFERENCE_GUIDE,
            GeneratedFile.FileType.VIDEO_LIST,
            GeneratedFile.FileType.WEEKLY_PLAN
        }

        # All files should be compiled
        for gen_file in generated_files:
            assert gen_file.status == GeneratedFile.Status.COMPILED
            assert gen_file.file is not None

    def test_external_services_called_correctly(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        valid_request_payload,
        mock_openrouter_service,
        mock_latex_compiler
    ):
        """Внешние сервисы вызываются с правильными параметрами"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        # Check OpenRouterService calls
        assert mock_openrouter_service.generate_problem_set.called
        assert mock_openrouter_service.generate_reference_guide.called
        assert mock_openrouter_service.generate_video_list.called

        # Check LaTeX compiler calls (2 times: problem_set + reference_guide)
        assert mock_latex_compiler.compile_to_pdf.call_count == 2


class TestGenerateStudyPlanErrorHandling:
    """Test error handling scenarios"""

    def test_openrouter_api_error_returns_500(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        valid_request_payload,
        mocker
    ):
        """Ошибка OpenRouter API возвращает 500"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        # Mock OpenRouter to raise error
        mock_service = mocker.patch(
            'materials.services.study_plan_generator_service.OpenRouterService'
        )
        mock_instance = mock_service.return_value
        mock_instance.generate_problem_set.side_effect = OpenRouterError(
            "API rate limit exceeded"
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['success'] is False
        assert 'Ошибка AI сервиса' in response.data['error']
        assert 'API rate limit exceeded' in response.data['error']

    def test_latex_compilation_error_returns_500(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        valid_request_payload,
        mocker
    ):
        """Ошибка компиляции LaTeX возвращает 500"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        # Mock OpenRouter to succeed
        mock_openrouter = mocker.patch(
            'materials.services.study_plan_generator_service.OpenRouterService'
        )
        mock_openrouter.return_value.generate_problem_set.return_value = r"\invalid LaTeX"

        # Mock LaTeX compiler to fail
        mock_latex = mocker.patch(
            'materials.services.study_plan_generator_service.LatexCompilerService'
        )
        mock_latex.return_value.compile_to_pdf.side_effect = LaTeXCompilationError(
            "Invalid LaTeX syntax on line 5"
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['success'] is False
        assert 'Ошибка компиляции LaTeX' in response.data['error']
        assert 'Invalid LaTeX syntax' in response.data['error']

    def test_generation_record_marked_failed_on_error(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        valid_request_payload,
        mocker
    ):
        """При ошибке запись StudyPlanGeneration помечается как failed"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        # Mock to raise error
        mock_service = mocker.patch(
            'materials.services.study_plan_generator_service.OpenRouterService'
        )
        mock_instance = mock_service.return_value
        mock_instance.generate_problem_set.side_effect = OpenRouterError(
            "Test error"
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

        # Check that generation record is marked as failed
        generation = StudyPlanGeneration.objects.filter(
            teacher=teacher_user,
            student=student_user,
            subject=subject
        ).first()

        assert generation is not None
        assert generation.status == StudyPlanGeneration.Status.FAILED
        assert generation.error_message == "Test error"

    def test_unexpected_error_returns_500(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        valid_request_payload,
        mocker
    ):
        """Неожиданная ошибка возвращает 500"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        # Mock to raise unexpected exception
        mock_service = mocker.patch(
            'materials.services.study_plan_generator_service.OpenRouterService'
        )
        mock_instance = mock_service.return_value
        mock_instance.generate_problem_set.side_effect = Exception(
            "Unexpected internal error"
        )

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=valid_request_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data['success'] is False
        assert 'Внутренняя ошибка сервера' in response.data['error']


class TestGenerateStudyPlanOptionalParameters:
    """Test handling of optional parameters"""

    def test_minimal_payload_uses_defaults(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        mock_openrouter_service,
        mock_latex_compiler
    ):
        """Минимальный payload использует значения по умолчанию для опциональных параметров"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        minimal_payload = {
            'student_id': student_user.id,
            'subject_id': subject.id,
            'grade': 9,
            'topic': 'Тест',
            'subtopics': 'Подтемы',
            'goal': 'Цель',
            'task_counts': {'A': 10}
        }

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=minimal_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['success'] is True

        # Check that generation used default values
        generation = StudyPlanGeneration.objects.get(id=response.data['generation_id'])
        params = generation.parameters

        assert params['constraints'] == ''
        assert params['reference_level'] == 'средний'
        assert params['examples_count'] == 'стандартный'
        assert params['video_duration'] == '10-25'
        assert params['video_language'] == 'русский'

    def test_custom_optional_parameters_saved(
        self,
        api_client,
        teacher_user,
        student_user,
        subject,
        mock_openrouter_service,
        mock_latex_compiler
    ):
        """Пользовательские значения опциональных параметров сохраняются"""
        SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

        custom_payload = {
            'student_id': student_user.id,
            'subject_id': subject.id,
            'grade': 11,
            'topic': 'Интегралы',
            'subtopics': 'определённые, неопределённые',
            'goal': 'ЕГЭ профиль',
            'task_counts': {'A': 15, 'B': 12, 'C': 8},
            'constraints': 'Время: 90 мин, Без калькулятора',
            'reference_level': 'полный',
            'examples_count': 'увеличенный',
            'video_duration': '15-30',
            'video_language': 'английский'
        }

        api_client.force_authenticate(user=teacher_user)
        response = api_client.post(
            '/api/materials/study-plan/generate/',
            data=custom_payload,
            format='json'
        )

        assert response.status_code == status.HTTP_200_OK

        generation = StudyPlanGeneration.objects.get(id=response.data['generation_id'])
        params = generation.parameters

        assert params['constraints'] == 'Время: 90 мин, Без калькулятора'
        assert params['reference_level'] == 'полный'
        assert params['examples_count'] == 'увеличенный'
        assert params['video_duration'] == '15-30'
        assert params['video_language'] == 'английский'
