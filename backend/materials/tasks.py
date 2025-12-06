"""
Celery задачи для асинхронной генерации учебных планов
"""
import logging
from celery import shared_task
from django.contrib.auth import get_user_model

from materials.models import StudyPlanGeneration, Subject
from materials.services.study_plan_generator_service import StudyPlanGeneratorService
from materials.services.openrouter_service import OpenRouterError
from materials.services.latex_compiler import LaTeXCompilationError


logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(bind=True, max_retries=0)
def generate_study_plan_async(self, generation_id: int):
    """
    Асинхронная генерация учебного плана через Celery

    Выполняется в фоновом режиме для неблокирующего API.
    Обновляет progress_message на каждом этапе для отображения прогресса пользователю.

    Args:
        generation_id: ID записи StudyPlanGeneration

    Workflow:
        1. Получение записи StudyPlanGeneration
        2. Обновление статуса на processing
        3. Генерация 4 файлов с обновлением progress_message:
           - Problem set (Задачник)
           - Reference guide (Методичка)
           - Video list (Видео-подборка)
           - Weekly plan (Недельный план)
        4. Обновление статуса на completed/failed

    Raises:
        StudyPlanGeneration.DoesNotExist: Если запись не найдена
        OpenRouterError: Ошибка API OpenRouter
        LaTeXCompilationError: Ошибка компиляции LaTeX
    """
    try:
        # Шаг 1: Получение записи StudyPlanGeneration
        generation = StudyPlanGeneration.objects.select_related(
            'teacher', 'student', 'subject', 'enrollment'
        ).get(id=generation_id)

        logger.info(
            f"Начата асинхронная генерация учебного плана | "
            f"generation_id={generation.id} | "
            f"teacher={generation.teacher.email} | "
            f"student={generation.student.email} | "
            f"subject={generation.subject.name}"
        )

        # Шаг 2: Обновление статуса на processing
        generation.status = StudyPlanGeneration.Status.PROCESSING
        generation.progress_message = 'Подготовка к генерации...'
        generation.save(update_fields=['status', 'progress_message', 'updated_at'])

        # Шаг 3: Инициализация сервиса
        service = StudyPlanGeneratorService()

        # Шаг 4: Генерация problem set
        generation.progress_message = 'Генерация задачника (Problem Set)...'
        generation.save(update_fields=['progress_message', 'updated_at'])

        problem_set_pdf = service._generate_and_compile_problem_set(
            generation, generation.parameters
        )

        # Шаг 5: Генерация reference guide
        generation.progress_message = 'Генерация теоретического справочника (Reference Guide)...'
        generation.save(update_fields=['progress_message', 'updated_at'])

        reference_guide_pdf = service._generate_and_compile_reference_guide(
            generation, generation.parameters
        )

        # Шаг 6: Генерация video list
        generation.progress_message = 'Генерация списка видео (Video List)...'
        generation.save(update_fields=['progress_message', 'updated_at'])

        video_list_md = service._generate_video_list(
            generation, generation.parameters
        )

        # Шаг 7: Генерация weekly plan
        generation.progress_message = 'Генерация недельного плана (Weekly Plan)...'
        generation.save(update_fields=['progress_message', 'updated_at'])

        weekly_plan_txt = service._generate_weekly_plan(
            generation,
            generation.parameters,
            problem_set_pdf,
            reference_guide_pdf,
            video_list_md
        )

        # Шаг 8: Обновление статуса на completed
        generation.status = StudyPlanGeneration.Status.COMPLETED
        generation.progress_message = 'Генерация завершена успешно'
        generation.save(update_fields=['status', 'progress_message', 'completed_at', 'updated_at'])

        logger.info(
            f"Асинхронная генерация учебного плана завершена успешно | "
            f"generation_id={generation.id}"
        )

        return {
            'success': True,
            'generation_id': generation.id,
            'status': generation.status,
            'files_count': generation.generated_files.filter(status='compiled').count()
        }

    except StudyPlanGeneration.DoesNotExist:
        logger.error(
            f"StudyPlanGeneration с ID {generation_id} не найден"
        )
        raise

    except (OpenRouterError, LaTeXCompilationError) as e:
        # Специфичные ошибки AI/LaTeX - сохраняем детали
        logger.error(
            f"Ошибка генерации учебного плана | "
            f"generation_id={generation_id} | "
            f"error_type={type(e).__name__} | "
            f"error={str(e)}",
            exc_info=True
        )

        try:
            generation = StudyPlanGeneration.objects.get(id=generation_id)
            generation.status = StudyPlanGeneration.Status.FAILED
            generation.error_message = f'{type(e).__name__}: {str(e)}'
            generation.progress_message = 'Ошибка генерации'
            generation.save(update_fields=['status', 'error_message', 'progress_message', 'completed_at', 'updated_at'])
        except StudyPlanGeneration.DoesNotExist:
            pass

        raise

    except Exception as e:
        # Непредвиденная ошибка
        logger.error(
            f"Непредвиденная ошибка при асинхронной генерации учебного плана | "
            f"generation_id={generation_id} | "
            f"error={str(e)}",
            exc_info=True
        )

        try:
            generation = StudyPlanGeneration.objects.get(id=generation_id)
            generation.status = StudyPlanGeneration.Status.FAILED
            generation.error_message = f'Внутренняя ошибка: {str(e)}'
            generation.progress_message = 'Ошибка генерации'
            generation.save(update_fields=['status', 'error_message', 'progress_message', 'completed_at', 'updated_at'])
        except StudyPlanGeneration.DoesNotExist:
            pass

        raise
