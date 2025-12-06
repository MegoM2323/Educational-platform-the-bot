"""
Основной сервис генерации учебных планов
Оркеструет процесс: OpenRouter API → LaTeX compilation → 4 файла
"""
import logging
from typing import Dict, Any
from pathlib import Path
from datetime import datetime
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile

from materials.models import (
    SubjectEnrollment,
    StudyPlanGeneration,
    GeneratedFile,
    User,
    Subject
)
from materials.services.openrouter_service import (
    OpenRouterService,
    OpenRouterError
)
from materials.services.latex_compiler import (
    LatexCompilerService,
    LaTeXCompilationError
)


logger = logging.getLogger(__name__)


class StudyPlanGeneratorService:
    """
    Основной сервис генерации учебных планов

    Оркеструет полный цикл генерации:
    1. Валидация enrollment (teacher-student-subject)
    2. Создание StudyPlanGeneration записи
    3. Генерация 3 компонентов через OpenRouter API:
       - Problem set (LaTeX → PDF)
       - Reference guide (LaTeX → PDF)
       - Video list (Markdown → .md)
    4. Генерация weekly plan (текст из всех 3 результатов → .txt)
    5. Создание 4 GeneratedFile записей
    6. Обновление статуса StudyPlanGeneration
    """

    def __init__(self):
        """Инициализация сервисов"""
        self.openrouter_service = OpenRouterService()
        self.latex_compiler = LatexCompilerService()

    def generate_study_plan(
        self,
        teacher: User,
        student: User,
        subject: Subject,
        params: Dict[str, Any]
    ) -> StudyPlanGeneration:
        """
        Генерирует полный учебный план для студента

        Args:
            teacher: Преподаватель (User с role=teacher)
            student: Студент (User с role=student)
            subject: Предмет
            params: Параметры генерации (см. структуру ниже)

        Returns:
            StudyPlanGeneration: Запись с результатами генерации

        Raises:
            ValidationError: Если enrollment не найден или невалидные параметры
            OpenRouterError: Ошибка API OpenRouter
            LaTeXCompilationError: Ошибка компиляции LaTeX

        Структура params:
            {
                # Unified first 5 parameters (all prompts)
                'subject': str,      # e.g., "Математика"
                'grade': int,        # e.g., 9
                'topic': str,        # e.g., "Квадратные уравнения"
                'subtopics': str,    # e.g., "решение, дискриминант, теорема Виета"
                'goal': str,         # e.g., "ОГЭ", "ЕГЭ профиль", "Повышение успеваемости"

                # Additional for problem set
                'task_counts': dict, # e.g., {'A': 12, 'B': 10, 'C': 6}
                'constraints': str,  # Optional, e.g., "Время: 60 мин"

                # Additional for reference guide
                'reference_level': str,  # e.g., "средний" (базовый/средний/полный)
                'examples_count': str,   # e.g., "стандартный"

                # Additional for videos
                'video_duration': str,   # e.g., "10-25"
                'video_language': str,   # e.g., "русский"
            }
        """
        # Шаг 1: Валидация enrollment
        try:
            enrollment = SubjectEnrollment.objects.get(
                teacher=teacher,
                student=student,
                subject=subject,
                is_active=True
            )
        except SubjectEnrollment.DoesNotExist:
            raise ValidationError(
                f"Студент {student.get_full_name()} не зачислен на предмет "
                f"{subject.name} к преподавателю {teacher.get_full_name()}"
            )

        # Шаг 2: Создание StudyPlanGeneration записи
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher,
            student=student,
            subject=subject,
            enrollment=enrollment,
            parameters=params,
            status=StudyPlanGeneration.Status.PROCESSING
        )

        logger.info(
            f"Начата генерация учебного плана | "
            f"generation_id={generation.id} | "
            f"teacher={teacher.email} | "
            f"student={student.email} | "
            f"subject={subject.name}"
        )

        try:
            # Шаг 3: Генерация problem set (LaTeX → PDF)
            problem_set_pdf = self._generate_and_compile_problem_set(
                generation, params
            )

            # Шаг 4: Генерация reference guide (LaTeX → PDF)
            reference_guide_pdf = self._generate_and_compile_reference_guide(
                generation, params
            )

            # Шаг 5: Генерация video list (Markdown → .md)
            video_list_md = self._generate_video_list(generation, params)

            # Шаг 6: Генерация weekly plan (текст → .txt)
            weekly_plan_txt = self._generate_weekly_plan(
                generation, params, problem_set_pdf, reference_guide_pdf, video_list_md
            )

            # Шаг 7: Обновление статуса на completed
            generation.status = StudyPlanGeneration.Status.COMPLETED
            generation.save(update_fields=['status', 'completed_at', 'updated_at'])

            logger.info(
                f"Генерация учебного плана завершена успешно | "
                f"generation_id={generation.id}"
            )

            return generation

        except Exception as e:
            # Обработка ошибок: обновляем статус на failed
            generation.status = StudyPlanGeneration.Status.FAILED
            generation.error_message = str(e)
            generation.save(update_fields=['status', 'error_message', 'completed_at', 'updated_at'])

            logger.error(
                f"Генерация учебного плана завершилась с ошибкой | "
                f"generation_id={generation.id} | "
                f"error={str(e)}"
            )

            # Пробрасываем исключение дальше
            raise

    def _generate_and_compile_problem_set(
        self,
        generation: StudyPlanGeneration,
        params: Dict[str, Any]
    ) -> GeneratedFile:
        """
        Генерирует задачник: OpenRouter API → LaTeX → PDF

        Returns:
            GeneratedFile: Запись с problem_set PDF

        Raises:
            OpenRouterError: Ошибка генерации LaTeX кода
            LaTeXCompilationError: Ошибка компиляции PDF
        """
        logger.info(
            f"Генерация problem set | generation_id={generation.id}"
        )

        # Создаём GeneratedFile запись (pending)
        generated_file = GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.PROBLEM_SET,
            status=GeneratedFile.Status.PENDING
        )

        try:
            # Обновляем статус на generating
            generated_file.status = GeneratedFile.Status.GENERATING
            generated_file.save(update_fields=['status', 'updated_at'])

            # Генерация LaTeX кода через OpenRouter
            latex_code = self.openrouter_service.generate_problem_set(params)

            # Компиляция LaTeX → PDF
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"problem_set_{generation.id}_{timestamp}.pdf"
            temp_path = Path(settings.MEDIA_ROOT) / 'study_plans' / 'generated' / filename

            pdf_path = self.latex_compiler.compile_to_pdf(
                latex_code=latex_code,
                output_path=str(temp_path)
            )

            # Сохраняем PDF в GeneratedFile
            with open(pdf_path, 'rb') as pdf_file:
                generated_file.file.save(
                    filename,
                    ContentFile(pdf_file.read()),
                    save=False
                )

            # Обновляем статус на compiled
            generated_file.status = GeneratedFile.Status.COMPILED
            generated_file.save(update_fields=['file', 'status', 'updated_at'])

            logger.info(
                f"Problem set сгенерирован успешно | "
                f"generation_id={generation.id} | "
                f"file={generated_file.file.name}"
            )

            return generated_file

        except Exception as e:
            # Обновляем статус на failed
            generated_file.status = GeneratedFile.Status.FAILED
            generated_file.error_message = str(e)
            generated_file.save(update_fields=['status', 'error_message', 'updated_at'])

            logger.error(
                f"Ошибка генерации problem set | "
                f"generation_id={generation.id} | "
                f"error={str(e)}"
            )

            raise

    def _generate_and_compile_reference_guide(
        self,
        generation: StudyPlanGeneration,
        params: Dict[str, Any]
    ) -> GeneratedFile:
        """
        Генерирует методичку: OpenRouter API → LaTeX → PDF

        Returns:
            GeneratedFile: Запись с reference_guide PDF

        Raises:
            OpenRouterError: Ошибка генерации LaTeX кода
            LaTeXCompilationError: Ошибка компиляции PDF
        """
        logger.info(
            f"Генерация reference guide | generation_id={generation.id}"
        )

        # Создаём GeneratedFile запись (pending)
        generated_file = GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.REFERENCE_GUIDE,
            status=GeneratedFile.Status.PENDING
        )

        try:
            # Обновляем статус на generating
            generated_file.status = GeneratedFile.Status.GENERATING
            generated_file.save(update_fields=['status', 'updated_at'])

            # Подготовка параметров для reference guide
            reference_params = {
                **params,
                'level': params.get('reference_level', 'средний')
            }

            # Генерация LaTeX кода через OpenRouter
            latex_code = self.openrouter_service.generate_reference_guide(reference_params)

            # Компиляция LaTeX → PDF
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"reference_guide_{generation.id}_{timestamp}.pdf"
            temp_path = Path(settings.MEDIA_ROOT) / 'study_plans' / 'generated' / filename

            pdf_path = self.latex_compiler.compile_to_pdf(
                latex_code=latex_code,
                output_path=str(temp_path)
            )

            # Сохраняем PDF в GeneratedFile
            with open(pdf_path, 'rb') as pdf_file:
                generated_file.file.save(
                    filename,
                    ContentFile(pdf_file.read()),
                    save=False
                )

            # Обновляем статус на compiled
            generated_file.status = GeneratedFile.Status.COMPILED
            generated_file.save(update_fields=['file', 'status', 'updated_at'])

            logger.info(
                f"Reference guide сгенерирован успешно | "
                f"generation_id={generation.id} | "
                f"file={generated_file.file.name}"
            )

            return generated_file

        except Exception as e:
            # Обновляем статус на failed
            generated_file.status = GeneratedFile.Status.FAILED
            generated_file.error_message = str(e)
            generated_file.save(update_fields=['status', 'error_message', 'updated_at'])

            logger.error(
                f"Ошибка генерации reference guide | "
                f"generation_id={generation.id} | "
                f"error={str(e)}"
            )

            raise

    def _generate_video_list(
        self,
        generation: StudyPlanGeneration,
        params: Dict[str, Any]
    ) -> GeneratedFile:
        """
        Генерирует список видео: OpenRouter API → Markdown → .md

        Returns:
            GeneratedFile: Запись с video_list .md файлом

        Raises:
            OpenRouterError: Ошибка генерации Markdown
        """
        logger.info(
            f"Генерация video list | generation_id={generation.id}"
        )

        # Создаём GeneratedFile запись (pending)
        generated_file = GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.VIDEO_LIST,
            status=GeneratedFile.Status.PENDING
        )

        try:
            # Обновляем статус на generating
            generated_file.status = GeneratedFile.Status.GENERATING
            generated_file.save(update_fields=['status', 'updated_at'])

            # Подготовка параметров для video list
            video_params = {
                **params,
                'language': params.get('video_language', 'русский'),
                'duration': params.get('video_duration', '10-25')
            }

            # Генерация Markdown через OpenRouter
            markdown_content = self.openrouter_service.generate_video_list(video_params)

            # Сохранение Markdown в .md файл
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"video_list_{generation.id}_{timestamp}.md"

            generated_file.file.save(
                filename,
                ContentFile(markdown_content.encode('utf-8')),
                save=False
            )

            # Обновляем статус на compiled
            generated_file.status = GeneratedFile.Status.COMPILED
            generated_file.save(update_fields=['file', 'status', 'updated_at'])

            logger.info(
                f"Video list сгенерирован успешно | "
                f"generation_id={generation.id} | "
                f"file={generated_file.file.name}"
            )

            return generated_file

        except Exception as e:
            # Обновляем статус на failed
            generated_file.status = GeneratedFile.Status.FAILED
            generated_file.error_message = str(e)
            generated_file.save(update_fields=['status', 'error_message', 'updated_at'])

            logger.error(
                f"Ошибка генерации video list | "
                f"generation_id={generation.id} | "
                f"error={str(e)}"
            )

            raise

    def _generate_weekly_plan(
        self,
        generation: StudyPlanGeneration,
        params: Dict[str, Any],
        problem_set_file: GeneratedFile,
        reference_guide_file: GeneratedFile,
        video_list_file: GeneratedFile
    ) -> GeneratedFile:
        """
        Генерирует недельный план на основе 3 сгенерированных компонентов

        Args:
            generation: Запись StudyPlanGeneration
            params: Параметры генерации
            problem_set_file: Сгенерированный задачник
            reference_guide_file: Сгенерированная методичка
            video_list_file: Сгенерированный список видео

        Returns:
            GeneratedFile: Запись с weekly_plan .txt файлом
        """
        logger.info(
            f"Генерация weekly plan | generation_id={generation.id}"
        )

        # Создаём GeneratedFile запись (pending)
        generated_file = GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.WEEKLY_PLAN,
            status=GeneratedFile.Status.PENDING
        )

        try:
            # Обновляем статус на generating
            generated_file.status = GeneratedFile.Status.GENERATING
            generated_file.save(update_fields=['status', 'updated_at'])

            # Компилируем недельный план из всех 3 файлов
            weekly_plan_text = self._compile_weekly_plan_text(
                params=params,
                problem_set_url=problem_set_file.file.url if problem_set_file.file else '',
                reference_guide_url=reference_guide_file.file.url if reference_guide_file.file else '',
                video_list_url=video_list_file.file.url if video_list_file.file else ''
            )

            # Сохранение текста в .txt файл
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"weekly_plan_{generation.id}_{timestamp}.txt"

            generated_file.file.save(
                filename,
                ContentFile(weekly_plan_text.encode('utf-8')),
                save=False
            )

            # Обновляем статус на compiled
            generated_file.status = GeneratedFile.Status.COMPILED
            generated_file.save(update_fields=['file', 'status', 'updated_at'])

            logger.info(
                f"Weekly plan сгенерирован успешно | "
                f"generation_id={generation.id} | "
                f"file={generated_file.file.name}"
            )

            return generated_file

        except Exception as e:
            # Обновляем статус на failed
            generated_file.status = GeneratedFile.Status.FAILED
            generated_file.error_message = str(e)
            generated_file.save(update_fields=['status', 'error_message', 'updated_at'])

            logger.error(
                f"Ошибка генерации weekly plan | "
                f"generation_id={generation.id} | "
                f"error={str(e)}"
            )

            raise

    def _compile_weekly_plan_text(
        self,
        params: Dict[str, Any],
        problem_set_url: str,
        reference_guide_url: str,
        video_list_url: str
    ) -> str:
        """
        Компилирует текст недельного плана из параметров и ссылок на файлы

        Args:
            params: Параметры генерации
            problem_set_url: URL задачника
            reference_guide_url: URL методички
            video_list_url: URL списка видео

        Returns:
            str: Текст недельного плана
        """
        plan_text = f"""НЕДЕЛЬНЫЙ ПЛАН ЗАНЯТИЙ

Предмет: {params.get('subject', 'Не указан')}
Класс: {params.get('grade', 'Не указан')}
Тема: {params.get('topic', 'Не указана')}
Подтемы: {params.get('subtopics', 'Не указаны')}
Цель: {params.get('goal', 'Не указана')}

МАТЕРИАЛЫ ДЛЯ ИЗУЧЕНИЯ:

1. Задачник (Problem Set):
   - Уровень A: {params.get('task_counts', {}).get('A', 'N/A')} задач
   - Уровень B: {params.get('task_counts', {}).get('B', 'N/A')} задач
   - Уровень C: {params.get('task_counts', {}).get('C', 'N/A')} задач
   - Файл: {problem_set_url}

2. Теоретический справочник (Reference Guide):
   - Уровень: {params.get('reference_level', 'средний')}
   - Файл: {reference_guide_url}

3. Видео-материалы (Video List):
   - Язык: {params.get('video_language', 'русский')}
   - Длительность: {params.get('video_duration', '10-25')} минут
   - Файл: {video_list_url}

РЕКОМЕНДАЦИИ ПО ИЗУЧЕНИЮ:

День 1-2: Просмотр видео по базовым понятиям, изучение определений из справочника
День 3-4: Решение задач уровня A, закрепление базовых методов
День 5: Изучение углублённой теории из справочника, просмотр видео уровня B-C
День 6-7: Решение задач уровня B и C, разбор сложных примеров

Сгенерировано: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return plan_text
