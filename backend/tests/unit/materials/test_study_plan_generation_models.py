"""
Тесты для моделей StudyPlanGeneration и GeneratedFile
"""
import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from materials.models import StudyPlanGeneration, GeneratedFile


@pytest.mark.django_db
class TestStudyPlanGenerationModel:
    """Тесты модели StudyPlanGeneration"""

    def test_create_study_plan_generation(self, student_user, teacher_user, subject, enrollment):
        """Создание записи генерации учебного плана"""
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={
                'subject': 'Математика',
                'grade': 9,
                'topic': 'Квадратные уравнения',
                'subtopics': ['Полные', 'Неполные'],
                'goal': 'Подготовка к экзамену',
                'constraints': 'Базовый уровень'
            }
        )

        assert generation.id is not None
        assert generation.teacher == teacher_user
        assert generation.student == student_user
        assert generation.subject == subject
        assert generation.enrollment == enrollment
        assert generation.status == StudyPlanGeneration.Status.PENDING
        assert generation.error_message is None
        assert generation.completed_at is None
        assert generation.created_at is not None

    def test_auto_find_enrollment(self, student_user, teacher_user, subject, enrollment):
        """Автоматический поиск enrollment если не указан"""
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            parameters={'test': 'data'}
        )

        # Enrollment должен быть найден автоматически
        assert generation.enrollment == enrollment

    def test_auto_set_completed_at(self, student_user, teacher_user, subject, enrollment):
        """Автоматическая установка completed_at при смене статуса"""
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={'test': 'data'}
        )

        assert generation.completed_at is None

        # Меняем статус на COMPLETED
        generation.status = StudyPlanGeneration.Status.COMPLETED
        generation.save()

        assert generation.completed_at is not None
        assert generation.completed_at <= timezone.now()

    def test_validation_enrollment_student_mismatch(self, student_user, teacher_user, subject, enrollment):
        """Валидация: студент в enrollment не совпадает"""
        # Создаем другого студента
        from accounts.models import User
        other_student = User.objects.create_user(
            email='other@test.com',
            password='password123',
            role='student'
        )

        generation = StudyPlanGeneration(
            teacher=teacher_user,
            student=other_student,  # Другой студент
            subject=subject,
            enrollment=enrollment,  # Enrollment для student_user
            parameters={'test': 'data'}
        )

        with pytest.raises(ValidationError, match='Студент в enrollment не совпадает'):
            generation.clean()

    def test_indexes_created(self):
        """Проверка что индексы созданы"""
        indexes = [idx.name for idx in StudyPlanGeneration._meta.indexes]
        assert 'materials_s_teacher_81decd_idx' in indexes
        assert 'materials_s_student_63eedf_idx' in indexes
        assert 'materials_s_status_98447a_idx' in indexes


@pytest.mark.django_db
class TestGeneratedFileModel:
    """Тесты модели GeneratedFile"""

    def test_create_generated_files(self, student_user, teacher_user, subject, enrollment):
        """Создание всех 4 типов файлов для генерации"""
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={'test': 'data'}
        )

        file_types = [
            GeneratedFile.FileType.PROBLEM_SET,
            GeneratedFile.FileType.REFERENCE_GUIDE,
            GeneratedFile.FileType.VIDEO_LIST,
            GeneratedFile.FileType.WEEKLY_PLAN,
        ]

        for file_type in file_types:
            generated_file = GeneratedFile.objects.create(
                generation=generation,
                file_type=file_type
            )
            assert generated_file.id is not None
            assert generated_file.generation == generation
            assert generated_file.status == GeneratedFile.Status.PENDING
            assert generated_file.file.name == ''

        # Проверяем что все 4 файла созданы
        assert generation.generated_files.count() == 4

    def test_unique_file_type_per_generation(self, student_user, teacher_user, subject, enrollment):
        """Один тип файла на генерацию (unique_together)"""
        from django.db import IntegrityError

        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={'test': 'data'}
        )

        # Создаем первый файл типа PROBLEM_SET
        GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.PROBLEM_SET
        )

        # Попытка создать второй файл того же типа должна вызвать ошибку
        with pytest.raises(IntegrityError):
            GeneratedFile.objects.create(
                generation=generation,
                file_type=GeneratedFile.FileType.PROBLEM_SET
            )

    def test_generated_file_status_choices(self, student_user, teacher_user, subject, enrollment):
        """Проверка всех статусов GeneratedFile"""
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={'test': 'data'}
        )

        file = GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.PROBLEM_SET
        )

        # Проверяем все статусы
        assert file.status == GeneratedFile.Status.PENDING

        file.status = GeneratedFile.Status.GENERATING
        file.save()
        assert file.status == GeneratedFile.Status.GENERATING

        file.status = GeneratedFile.Status.COMPILED
        file.save()
        assert file.status == GeneratedFile.Status.COMPILED

        file.status = GeneratedFile.Status.FAILED
        file.error_message = 'Test error'
        file.save()
        assert file.status == GeneratedFile.Status.FAILED
        assert file.error_message == 'Test error'

    def test_cascade_delete(self, student_user, teacher_user, subject, enrollment):
        """При удалении StudyPlanGeneration удаляются GeneratedFile"""
        generation = StudyPlanGeneration.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=subject,
            enrollment=enrollment,
            parameters={'test': 'data'}
        )

        # Создаем файлы
        GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.PROBLEM_SET
        )
        GeneratedFile.objects.create(
            generation=generation,
            file_type=GeneratedFile.FileType.WEEKLY_PLAN
        )

        assert GeneratedFile.objects.filter(generation=generation).count() == 2

        # Удаляем генерацию
        generation.delete()

        # Файлы тоже удалились
        assert GeneratedFile.objects.filter(generation_id=generation.id).count() == 0
