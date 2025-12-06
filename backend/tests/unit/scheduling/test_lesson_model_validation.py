"""
Unit tests for Lesson model validation enforcement.

Tests that validation is automatically enforced on save() via full_clean().
"""

import pytest
from datetime import time, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

from scheduling.models import Lesson
from accounts.models import User, StudentProfile, TeacherProfile
from materials.models import Subject, SubjectEnrollment


@pytest.mark.django_db
class TestLessonModelValidationEnforcement:
    """Test that Lesson.clean() validation is enforced on save()."""

    def test_save_with_past_date_raises_validation_error(
        self, teacher_user, student_user, math_subject, subject_enrollment
    ):
        """Попытка сохранить урок с прошедшей датой должна вызывать ValidationError"""
        past_date = timezone.now().date() - timedelta(days=1)

        lesson = Lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=past_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Прошлый урок',
            status='pending'
        )

        # save() должен вызывать full_clean() и отклонять прошедшую дату
        with pytest.raises(ValidationError) as exc_info:
            lesson.save()

        assert 'Cannot create lesson in the past' in str(exc_info.value)

    def test_save_with_future_date_succeeds(
        self, teacher_user, student_user, math_subject, subject_enrollment
    ):
        """Сохранение урока с будущей датой должно успешно работать"""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = Lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Будущий урок',
            status='pending'
        )

        # Не должно вызывать исключений
        lesson.save()

        # Проверяем что урок сохранился
        assert Lesson.objects.filter(id=lesson.id).exists()
        lesson.delete()

    def test_update_to_past_date_raises_validation_error(
        self, lesson
    ):
        """Обновление существующего урока на прошедшую дату должно вызывать ValidationError"""
        past_date = timezone.now().date() - timedelta(days=2)

        # Обновляем дату на прошедшую
        lesson.date = past_date

        # save() должен отклонить изменение
        with pytest.raises(ValidationError) as exc_info:
            lesson.save()

        assert 'Cannot create lesson in the past' in str(exc_info.value)

    def test_save_with_invalid_time_range_raises_validation_error(
        self, teacher_user, student_user, math_subject, subject_enrollment
    ):
        """Сохранение урока с некорректным временем (start >= end) должно вызывать ValidationError"""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = Lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(11, 0),  # Время начала после времени окончания
            end_time=time(10, 0),
            description='Некорректный урок',
            status='pending'
        )

        # save() должен отклонить некорректное время
        with pytest.raises(ValidationError) as exc_info:
            lesson.save()

        assert 'Start time must be before end time' in str(exc_info.value)

    def test_save_without_enrollment_raises_validation_error(
        self, teacher_user, student_user, math_subject
    ):
        """Сохранение урока без SubjectEnrollment должно вызывать ValidationError"""
        future_date = timezone.now().date() + timedelta(days=3)

        # Не создаём SubjectEnrollment
        lesson = Lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Урок без enrollment',
            status='pending'
        )

        # save() должен отклонить из-за отсутствия enrollment
        with pytest.raises(ValidationError) as exc_info:
            lesson.save()

        assert 'does not teach' in str(exc_info.value)

    def test_save_with_valid_enrollment_succeeds(
        self, teacher_user, student_user, math_subject, subject_enrollment
    ):
        """Сохранение урока с корректным SubjectEnrollment должно успешно работать"""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = Lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Валидный урок',
            status='pending'
        )

        # Не должно вызывать исключений
        lesson.save()

        # Проверяем что урок сохранился
        assert Lesson.objects.filter(id=lesson.id).exists()
        lesson.delete()


@pytest.mark.django_db
class TestSubjectEnrollmentQueryOptimization:
    """Test that SubjectEnrollment validation uses optimized query."""

    def test_enrollment_check_uses_select_related(
        self, teacher_user, student_user, math_subject, subject_enrollment, django_assert_num_queries
    ):
        """Проверка SubjectEnrollment должна использовать select_related для оптимизации"""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = Lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Оптимизированный урок',
            status='pending'
        )

        # save() вызывает full_clean(), который:
        # 1-3. Проверяет ForeignKey constraints (teacher, student, subject)
        # 4. SELECT SubjectEnrollment с join teacher, student, subject (оптимизировано!)
        # 5. SELECT для проверки unique id
        # 6. INSERT lesson
        # С select_related оптимизация: 1 запрос вместо 4 для enrollment
        with django_assert_num_queries(6):
            lesson.save()

        lesson.delete()

    def test_validation_error_messages_are_clear(
        self, teacher_user, student_user, math_subject
    ):
        """Сообщения об ошибках валидации должны быть понятными"""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = Lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        # Без enrollment должно быть понятное сообщение с именами
        with pytest.raises(ValidationError) as exc_info:
            lesson.save()

        error_message = str(exc_info.value)
        assert teacher_user.get_full_name() in error_message
        assert student_user.get_full_name() in error_message
        assert math_subject.name in error_message
        assert 'does not teach' in error_message
