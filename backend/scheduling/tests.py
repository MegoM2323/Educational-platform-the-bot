"""
Unit tests for scheduling models (T_SCH_001).

Tests focus on Lesson model validation and LessonHistory string representation.
"""

import pytest
from datetime import date, time, timedelta
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from scheduling.models import Lesson, LessonHistory


class TestLessonTimeValidation:
    """Test Lesson model time validation"""

    def test_zero_duration_lesson_rejected(self):
        """Lesson with start_time == end_time should raise ValidationError"""
        lesson = Lesson(
            start_time=time(10, 0),
            end_time=time(10, 0),  # Одинаковое время - нулевая длительность
            date=date.today() + timedelta(days=1)
        )

        with pytest.raises(ValidationError) as excinfo:
            lesson.clean()

        assert 'Start time must be before end time' in str(excinfo.value)

    def test_end_time_before_start_time_rejected(self):
        """Lesson with end_time before start_time should raise ValidationError"""
        lesson = Lesson(
            start_time=time(14, 0),
            end_time=time(10, 0),  # end раньше чем start
            date=date.today() + timedelta(days=1)
        )

        with pytest.raises(ValidationError) as excinfo:
            lesson.clean()

        assert 'Start time must be before end time' in str(excinfo.value)

    def test_valid_time_range_accepted(self):
        """Lesson with valid time range (start < end) should pass validation"""
        lesson = Lesson(
            start_time=time(10, 0),
            end_time=time(11, 0),  # Корректный диапазон
            date=date.today() + timedelta(days=1)
        )

        # Не должно выбрасывать исключение на валидацию времени
        # (может выбросить на другие поля, но не на время)
        try:
            lesson.clean()
        except ValidationError as e:
            # Проверяем что ошибка НЕ связана со временем
            assert 'Start time must be before end time' not in str(e)


class TestLessonDatetimeProperties:
    """Test Lesson datetime_start and datetime_end properties"""

    def test_datetime_start_handles_timezone_exception(self):
        """datetime_start should fallback to naive datetime on timezone error"""
        lesson = Lesson(
            date=date(2025, 1, 15),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Мокаем make_aware чтобы выбросить исключение
        with patch.object(timezone, 'make_aware', side_effect=Exception('Timezone error')):
            with patch.object(timezone, 'is_aware', return_value=False):
                result = lesson.datetime_start

        # Должен вернуть naive datetime без краша
        assert result is not None
        assert result.hour == 10
        assert result.minute == 0

    def test_datetime_end_handles_timezone_exception(self):
        """datetime_end should fallback to naive datetime on timezone error"""
        lesson = Lesson(
            date=date(2025, 1, 15),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Мокаем make_aware чтобы выбросить исключение
        with patch.object(timezone, 'make_aware', side_effect=Exception('Timezone error')):
            with patch.object(timezone, 'is_aware', return_value=False):
                result = lesson.datetime_end

        # Должен вернуть naive datetime без краша
        assert result is not None
        assert result.hour == 11
        assert result.minute == 0

    def test_datetime_start_returns_aware_if_already_aware(self):
        """datetime_start should return as-is if already timezone aware"""
        lesson = Lesson(
            date=date(2025, 1, 15),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # is_aware возвращает True - make_aware не должен вызываться
        with patch.object(timezone, 'is_aware', return_value=True):
            with patch.object(timezone, 'make_aware') as mock_make_aware:
                lesson.datetime_start
                mock_make_aware.assert_not_called()


class TestLessonHistoryStr:
    """Test LessonHistory __str__ method"""

    def test_str_with_none_performed_by(self):
        """LessonHistory.__str__() should handle None performed_by gracefully"""
        # Создаем mock для lesson
        mock_lesson = MagicMock()
        mock_lesson.__str__ = MagicMock(return_value='Teacher - Student - Math - 2025-01-15')

        history = LessonHistory(
            lesson=mock_lesson,
            action='created',
            performed_by=None  # None - системное действие
        )
        history.timestamp = timezone.now()

        result = str(history)

        # Должен содержать 'System' вместо имени пользователя
        assert 'System' in result
        assert 'Created' in result

    def test_str_with_performed_by_user(self):
        """LessonHistory.__str__() should show user name when performed_by is set"""
        mock_lesson = MagicMock()
        mock_lesson.__str__ = MagicMock(return_value='Teacher - Student - Math - 2025-01-15')

        mock_user = MagicMock()
        mock_user.get_full_name.return_value = 'John Doe'

        history = LessonHistory(
            lesson=mock_lesson,
            action='updated',
            performed_by=mock_user
        )
        history.timestamp = timezone.now()

        result = str(history)

        # Должен содержать имя пользователя
        assert 'John Doe' in result
        assert 'Updated' in result


class TestTutorAuthorization:
    """Test tutor authorization in tutor_views (T_SCH_012)"""

    def test_tutor_access_to_own_student(self):
        """Tutor should have access to their assigned student's schedule"""
        from scheduling.tutor_views import get_student_schedule
        from accounts.models import StudentProfile

        # Мок request с authenticated tutor
        mock_request = MagicMock()
        mock_tutor = MagicMock()
        mock_tutor.id = 1
        mock_request.user = mock_tutor
        mock_request.query_params = {}

        # Мок студента и его профиля
        mock_student = MagicMock()
        mock_student.id = 100
        mock_student.role = 'student'
        mock_student.get_full_name.return_value = 'Test Student'
        mock_student.email = 'student@test.com'

        mock_profile = MagicMock()
        mock_profile.tutor = mock_tutor

        # Патчим get_object_or_404 и StudentProfile.objects.get
        with patch('scheduling.tutor_views.get_object_or_404', return_value=mock_student):
            with patch.object(StudentProfile.objects, 'get', return_value=mock_profile):
                with patch('scheduling.tutor_views.Lesson.objects') as mock_lessons:
                    mock_lessons.filter.return_value.select_related.return_value.order_by.return_value = []

                    response = get_student_schedule(mock_request, 100)

                    # Должен вернуть 200, а не 403
                    assert response.status_code == 200
                    assert 'student' in response.data
                    assert response.data['student']['id'] == 100

    def test_tutor_denied_access_to_other_students(self):
        """Tutor should NOT have access to students not assigned to them"""
        from scheduling.tutor_views import get_student_schedule
        from accounts.models import StudentProfile

        # Мок request с authenticated tutor
        mock_request = MagicMock()
        mock_tutor = MagicMock()
        mock_tutor.id = 1
        mock_request.user = mock_tutor
        mock_request.query_params = {}

        # Мок студента, который принадлежит другому тьютору
        mock_student = MagicMock()
        mock_student.id = 200
        mock_student.role = 'student'

        # Патчим get_object_or_404, StudentProfile.objects.get выбросит DoesNotExist
        with patch('scheduling.tutor_views.get_object_or_404', return_value=mock_student):
            with patch.object(StudentProfile.objects, 'get', side_effect=StudentProfile.DoesNotExist):

                response = get_student_schedule(mock_request, 200)

                # Должен вернуть 403 Forbidden
                assert response.status_code == 403
                assert 'error' in response.data
                assert 'not assigned' in response.data['error'].lower()

    def test_tutor_denied_access_when_student_has_no_tutor(self):
        """Tutor should NOT have access when student has no tutor assigned (null check)"""
        from scheduling.tutor_views import get_student_schedule
        from accounts.models import StudentProfile

        # Мок request с authenticated tutor
        mock_request = MagicMock()
        mock_tutor = MagicMock()
        mock_tutor.id = 1
        mock_request.user = mock_tutor
        mock_request.query_params = {}

        # Мок студента без назначенного тьютора
        mock_student = MagicMock()
        mock_student.id = 300
        mock_student.role = 'student'

        # StudentProfile.objects.get выбросит DoesNotExist когда tutor != request.user
        with patch('scheduling.tutor_views.get_object_or_404', return_value=mock_student):
            with patch.object(StudentProfile.objects, 'get', side_effect=StudentProfile.DoesNotExist):

                response = get_student_schedule(mock_request, 300)

                # Должен вернуть 403 Forbidden
                assert response.status_code == 403
                assert 'error' in response.data
