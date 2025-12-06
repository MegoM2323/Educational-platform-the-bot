"""
Unit тесты для StudyPlanGeneratorService
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from materials.services.study_plan_generator_service import StudyPlanGeneratorService
from materials.models import (
    StudyPlanGeneration,
    GeneratedFile,
    SubjectEnrollment
)


@pytest.mark.django_db
class TestStudyPlanGeneratorService:
    """Тесты основного сервиса генерации учебных планов"""

    @pytest.fixture
    def service(self):
        """Фикстура сервиса"""
        return StudyPlanGeneratorService()

    @pytest.fixture
    def valid_params(self):
        """Валидные параметры генерации"""
        return {
            'subject': 'Математика',
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
    def enrollment(self, teacher_user, student_user, subject):
        """Фикстура enrollment"""
        return SubjectEnrollment.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            is_active=True
        )

    def test_service_initialization(self, service):
        """Тест: сервис инициализируется с OpenRouter и LaTeX компилятором"""
        assert service.openrouter_service is not None
        assert service.latex_compiler is not None

    def test_generate_study_plan_validates_enrollment(
        self, service, teacher_user, student_user, subject, valid_params
    ):
        """Тест: генерация выбрасывает ValidationError если enrollment не найден"""
        # Enrollment не существует
        with pytest.raises(ValidationError) as exc_info:
            service.generate_study_plan(
                teacher=teacher_user,
                student=student_user,
                subject=subject,
                params=valid_params
            )

        assert 'не зачислен на предмет' in str(exc_info.value)

    @patch('materials.services.study_plan_generator_service.OpenRouterService')
    @patch('materials.services.study_plan_generator_service.LatexCompilerService')
    def test_generate_study_plan_creates_generation_record(
        self,
        mock_latex_compiler_class,
        mock_openrouter_class,
        service,
        teacher_user,
        student_user,
        subject,
        enrollment,
        valid_params
    ):
        """Тест: создается StudyPlanGeneration запись со статусом PROCESSING"""
        # Mock сервисы
        mock_openrouter = MagicMock()
        mock_openrouter.generate_problem_set.return_value = "\\documentclass{article}\\begin{document}Test\\end{document}"
        mock_openrouter.generate_reference_guide.return_value = "\\documentclass{article}\\begin{document}Ref\\end{document}"
        mock_openrouter.generate_video_list.return_value = "# Videos\n- Video 1"

        mock_latex = MagicMock()
        mock_latex.compile_to_pdf.return_value = "/tmp/test.pdf"

        mock_openrouter_class.return_value = mock_openrouter
        mock_latex_compiler_class.return_value = mock_latex

        # Переопределяем сервисы в экземпляре
        service.openrouter_service = mock_openrouter
        service.latex_compiler = mock_latex

        # Mock file save
        with patch('materials.services.study_plan_generator_service.ContentFile'):
            with patch('builtins.open', create=True):
                # Вызываем генерацию
                try:
                    generation = service.generate_study_plan(
                        teacher=teacher_user,
                        student=student_user,
                        subject=subject,
                        params=valid_params
                    )
                except Exception:
                    # Игнорируем ошибки файловой системы в тесте
                    pass

        # Проверяем что запись создана
        generations = StudyPlanGeneration.objects.filter(
            teacher=teacher_user,
            student=student_user,
            subject=subject
        )
        assert generations.exists()

        generation = generations.first()
        assert generation.enrollment == enrollment
        assert generation.parameters == valid_params

    @patch('materials.services.study_plan_generator_service.OpenRouterService')
    def test_generate_study_plan_handles_openrouter_error(
        self,
        mock_openrouter_class,
        service,
        teacher_user,
        student_user,
        subject,
        enrollment,
        valid_params
    ):
        """Тест: при ошибке OpenRouter статус обновляется на FAILED"""
        from materials.services.openrouter_service import OpenRouterError

        # Mock OpenRouter выбрасывает ошибку
        mock_openrouter = MagicMock()
        mock_openrouter.generate_problem_set.side_effect = OpenRouterError("API Error")

        mock_openrouter_class.return_value = mock_openrouter
        service.openrouter_service = mock_openrouter

        # Вызываем генерацию
        with pytest.raises(OpenRouterError):
            service.generate_study_plan(
                teacher=teacher_user,
                student=student_user,
                subject=subject,
                params=valid_params
            )

        # Проверяем что статус FAILED
        generation = StudyPlanGeneration.objects.get(
            teacher=teacher_user,
            student=student_user,
            subject=subject
        )
        assert generation.status == StudyPlanGeneration.Status.FAILED
        assert 'API Error' in generation.error_message

    def test_compile_weekly_plan_text_format(self, service, valid_params):
        """Тест: weekly plan имеет правильный формат"""
        plan_text = service._compile_weekly_plan_text(
            params=valid_params,
            problem_set_url='/media/problem_set.pdf',
            reference_guide_url='/media/reference.pdf',
            video_list_url='/media/videos.md'
        )

        # Проверяем ключевые разделы
        assert 'НЕДЕЛЬНЫЙ ПЛАН ЗАНЯТИЙ' in plan_text
        assert 'Математика' in plan_text
        assert 'Квадратные уравнения' in plan_text
        assert 'ОГЭ' in plan_text
        assert 'Problem Set' in plan_text
        assert 'Reference Guide' in plan_text
        assert 'Video List' in plan_text
        assert '/media/problem_set.pdf' in plan_text
        assert '/media/reference.pdf' in plan_text
        assert '/media/videos.md' in plan_text
        assert 'День 1-2' in plan_text  # Рекомендации по дням
        assert 'Уровень A: 12 задач' in plan_text
        assert 'Уровень B: 10 задач' in plan_text
        assert 'Уровень C: 6 задач' in plan_text
