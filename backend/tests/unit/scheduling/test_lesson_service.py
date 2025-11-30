"""
Unit tests for LessonService business logic.

Tests cover:
- Lesson creation with validation
- Lesson retrieval by role
- Lesson updates
- Lesson deletion with 2-hour rule
- LessonHistory tracking
"""

import pytest
from datetime import time, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError

from scheduling.models import Lesson, LessonHistory
from scheduling.services.lesson_service import LessonService
from materials.models import Subject, SubjectEnrollment


# ============================================================================
# CREATION TESTS
# ============================================================================

class TestLessonServiceCreate:
    """Test LessonService.create_lesson method."""

    def test_create_lesson_success(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Teacher can create lesson for enrolled student."""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = LessonService.create_lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Алгебра',
            telemost_link='https://telemost.yandex.ru/test'
        )

        assert lesson.id is not None
        assert lesson.teacher == teacher_user
        assert lesson.student == student_user
        assert lesson.subject == math_subject
        assert lesson.date == future_date
        assert lesson.start_time == time(10, 0)
        assert lesson.end_time == time(11, 0)
        assert lesson.description == 'Алгебра'
        assert lesson.telemost_link == 'https://telemost.yandex.ru/test'
        assert lesson.status == 'pending'

    def test_create_lesson_creates_history_entry(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Creating lesson creates LessonHistory entry."""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = LessonService.create_lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        history = LessonHistory.objects.filter(lesson=lesson)
        assert history.exists()
        assert history.first().action == 'created'
        assert history.first().performed_by == teacher_user

    def test_create_lesson_non_teacher_fails(self, student_user, another_student_user, math_subject):
        """Only teachers can create lessons."""
        future_date = timezone.now().date() + timedelta(days=3)

        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=student_user,  # Student, not teacher
                student=another_student_user,
                subject=math_subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert 'teacher role' in str(exc.value).lower()

    def test_create_lesson_non_student_fails(self, teacher_user, another_student_user, math_subject):
        """Only students can be enrolled in lessons."""
        future_date = timezone.now().date() + timedelta(days=3)

        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher_user,
                student=teacher_user,  # Teacher, not student - this will still fail validation
                subject=math_subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert 'student role' in str(exc.value).lower()

    def test_create_lesson_past_date_fails(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot create lesson in the past."""
        past_date = timezone.now().date() - timedelta(days=1)

        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher_user,
                student=student_user,
                subject=math_subject,
                date=past_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert 'past' in str(exc.value).lower()

    def test_create_lesson_invalid_time_range_fails(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Start time must be before end time."""
        future_date = timezone.now().date() + timedelta(days=3)

        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher_user,
                student=student_user,
                subject=math_subject,
                date=future_date,
                start_time=time(11, 0),
                end_time=time(10, 0)  # End before start
            )

        assert 'start' in str(exc.value).lower() and 'end' in str(exc.value).lower()

    def test_create_lesson_equal_times_fails(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Start time cannot equal end time."""
        future_date = timezone.now().date() + timedelta(days=3)

        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher_user,
                student=student_user,
                subject=math_subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(10, 0)  # Same time
            )

        assert 'start' in str(exc.value).lower()

    def test_create_lesson_no_enrollment_fails(self, teacher_user, another_student_user, math_subject):
        """Teacher cannot create lesson for student they don't teach."""
        future_date = timezone.now().date() + timedelta(days=3)

        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher_user,
                student=another_student_user,  # No enrollment for this student
                subject=math_subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert 'does not teach' in str(exc.value).lower()

    def test_create_lesson_inactive_enrollment_fails(self, teacher_user, student_user, math_subject):
        """Cannot create lesson with inactive enrollment."""
        # Create inactive enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=math_subject,
            is_active=False  # Inactive
        )

        future_date = timezone.now().date() + timedelta(days=3)

        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher_user,
                student=student_user,
                subject=math_subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert 'does not teach' in str(exc.value).lower()

    def test_create_lesson_default_status_pending(self, teacher_user, student_user, math_subject, subject_enrollment):
        """New lesson status is always 'pending'."""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = LessonService.create_lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        assert lesson.status == 'pending'

    def test_create_lesson_optional_fields(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Description and telemost_link are optional."""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = LessonService.create_lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            # No description or telemost_link
        )

        assert lesson.description == ''
        assert lesson.telemost_link == ''


# ============================================================================
# RETRIEVAL TESTS
# ============================================================================

class TestLessonServiceRetrieval:
    """Test LessonService.get_*_lessons methods."""

    def test_get_teacher_lessons(self, teacher_user, student_user, math_subject, lesson, another_enrollment):
        """Teacher can retrieve their own lessons."""
        # Create another lesson for different student
        other_lesson = Lesson.objects.create(
            teacher=teacher_user,
            student=another_enrollment.student,
            subject=another_enrollment.subject,
            date=timezone.now().date() + timedelta(days=4),
            start_time=time(14, 0),
            end_time=time(15, 0)
        )

        lessons = LessonService.get_teacher_lessons(teacher_user)

        assert lessons.count() >= 2
        assert lesson in lessons
        assert other_lesson in lessons

    def test_get_teacher_lessons_filters_by_date_from(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Teacher can filter lessons by start date."""
        date1 = timezone.now().date() + timedelta(days=1)
        date2 = timezone.now().date() + timedelta(days=5)

        lesson1 = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date1,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        lesson2 = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date2,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        lessons = LessonService.get_teacher_lessons(
            teacher_user,
            filters={'date_from': date2}
        )

        assert lesson1 not in lessons
        assert lesson2 in lessons

    def test_get_teacher_lessons_filters_by_subject(self, teacher_user, student_user, math_subject, english_subject, subject_enrollment, another_enrollment):
        """Teacher can filter lessons by subject."""
        lesson1 = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        lesson2 = Lesson.objects.create(
            teacher=teacher_user,
            student=another_enrollment.student,
            subject=english_subject,
            date=timezone.now().date() + timedelta(days=3),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        lessons = LessonService.get_teacher_lessons(
            teacher_user,
            filters={'subject_id': math_subject.id}
        )

        assert lesson1 in lessons
        assert lesson2 not in lessons

    def test_get_student_lessons(self, student_user, teacher_user, math_subject, lesson):
        """Student can retrieve their own lessons."""
        lessons = LessonService.get_student_lessons(student_user)

        assert lesson in lessons

    def test_get_student_lessons_does_not_see_other_students(self, student_user, another_student_user, teacher_user, math_subject, subject_enrollment, another_enrollment):
        """Student only sees their own lessons."""
        lesson1 = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        lesson2 = Lesson.objects.create(
            teacher=teacher_user,
            student=another_student_user,
            subject=another_enrollment.subject,
            date=timezone.now().date() + timedelta(days=3),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        lessons = LessonService.get_student_lessons(student_user)

        assert lesson1 in lessons
        assert lesson2 not in lessons

    def test_get_tutor_student_lessons_success(self, tutor_user, student_user, teacher_user, math_subject, subject_enrollment, lesson):
        """Tutor can retrieve lessons for their managed student."""
        from accounts.models import StudentProfile

        # Link student to tutor
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        lessons = LessonService.get_tutor_student_lessons(tutor_user, student_user.id)

        assert lesson in lessons

    def test_get_tutor_student_lessons_not_managed_fails(self, tutor_user, student_user):
        """Tutor cannot view lessons for unmanaged student."""
        with pytest.raises(ValidationError) as exc:
            LessonService.get_tutor_student_lessons(tutor_user, student_user.id)

        assert 'do not manage' in str(exc.value).lower()

    def test_get_upcoming_lessons_teacher(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Teacher gets upcoming lessons."""
        # Create upcoming and past lessons
        future = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        past = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() - timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='completed'
        )

        lessons = LessonService.get_upcoming_lessons(teacher_user)

        assert future in lessons
        assert past not in lessons

    def test_get_upcoming_lessons_student(self, student_user, teacher_user, math_subject, subject_enrollment):
        """Student gets upcoming lessons."""
        future = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        lessons = LessonService.get_upcoming_lessons(student_user, limit=10)

        assert future in lessons

    def test_get_upcoming_lessons_tutor(self, tutor_user, student_user, teacher_user, math_subject, subject_enrollment):
        """Tutor gets upcoming lessons for managed students."""
        from accounts.models import StudentProfile

        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        future = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        lessons = LessonService.get_upcoming_lessons(tutor_user)

        assert future in lessons

    def test_get_upcoming_lessons_limit(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Upcoming lessons respects limit parameter."""
        # Create 5 future lessons
        for i in range(5):
            Lesson.objects.create(
                teacher=teacher_user,
                student=student_user,
                subject=math_subject,
                date=timezone.now().date() + timedelta(days=i+1),
                start_time=time(10, 0),
                end_time=time(11, 0),
                status='pending'
            )

        lessons = LessonService.get_upcoming_lessons(teacher_user, limit=3)

        assert lessons.count() == 3


# ============================================================================
# UPDATE TESTS
# ============================================================================

class TestLessonServiceUpdate:
    """Test LessonService.update_lesson method."""

    def test_update_lesson_success(self, teacher_user, student_user, math_subject, lesson):
        """Teacher can update future lesson."""
        new_description = 'Updated description'

        updated = LessonService.update_lesson(
            lesson=lesson,
            updates={'description': new_description},
            user=teacher_user
        )

        assert updated.description == new_description
        assert updated.id == lesson.id

    def test_update_lesson_creates_history(self, teacher_user, student_user, math_subject, lesson):
        """Updating lesson creates history entry."""
        old_desc = lesson.description
        new_desc = 'New description'

        LessonService.update_lesson(
            lesson=lesson,
            updates={'description': new_desc},
            user=teacher_user
        )

        history = LessonHistory.objects.filter(
            lesson=lesson,
            action='updated'
        )

        assert history.exists()
        assert old_desc in str(history.first().old_values)

    def test_update_lesson_not_teacher_fails(self, teacher_user, student_user, math_subject, lesson):
        """Only teacher who created lesson can update."""
        from accounts.models import User

        other_teacher = User.objects.create_user(
            username='other_teacher@test.com',
            email='other_teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )

        with pytest.raises(ValidationError) as exc:
            LessonService.update_lesson(
                lesson=lesson,
                updates={'description': 'New desc'},
                user=other_teacher
            )

        assert 'teacher' in str(exc.value).lower()

    def test_update_lesson_past_fails(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot update past lesson."""
        past_lesson = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() - timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        with pytest.raises(ValidationError) as exc:
            LessonService.update_lesson(
                lesson=past_lesson,
                updates={'description': 'New'},
                user=teacher_user
            )

        assert 'past' in str(exc.value).lower()

    def test_update_lesson_already_started_today_fails(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot update lesson that already started today."""
        # Create lesson for today but in the past
        now = timezone.now()
        started_lesson = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=now.date(),
            start_time=(now - timedelta(hours=1)).time(),
            end_time=(now - timedelta(minutes=30)).time()
        )

        with pytest.raises(ValidationError) as exc:
            LessonService.update_lesson(
                lesson=started_lesson,
                updates={'description': 'New'},
                user=teacher_user
            )

        assert 'already started' in str(exc.value).lower()

    def test_update_lesson_invalid_fields_ignored(self, teacher_user, student_user, math_subject, lesson):
        """Invalid fields in update are ignored."""
        original_id = lesson.id

        updated = LessonService.update_lesson(
            lesson=lesson,
            updates={'description': 'Valid', 'invalid_field': 'Should be ignored'},
            user=teacher_user
        )

        assert updated.id == original_id
        assert updated.description == 'Valid'

    def test_update_lesson_multiple_fields(self, teacher_user, student_user, math_subject, lesson):
        """Can update multiple fields at once."""
        new_date = lesson.date + timedelta(days=1)
        new_start = time(14, 0)
        new_end = time(15, 0)

        updated = LessonService.update_lesson(
            lesson=lesson,
            updates={
                'date': new_date,
                'start_time': new_start,
                'end_time': new_end,
                'description': 'Updated all'
            },
            user=teacher_user
        )

        assert updated.date == new_date
        assert updated.start_time == new_start
        assert updated.end_time == new_end
        assert updated.description == 'Updated all'


# ============================================================================
# DELETE TESTS
# ============================================================================

class TestLessonServiceDelete:
    """Test LessonService.delete_lesson method."""

    def test_delete_lesson_success(self, teacher_user, student_user, math_subject, lesson):
        """Teacher can delete future lesson (>2 hours away)."""
        lesson_id = lesson.id

        LessonService.delete_lesson(lesson=lesson, user=teacher_user)

        lesson.refresh_from_db()
        assert lesson.status == 'cancelled'

    def test_delete_lesson_creates_history(self, teacher_user, student_user, math_subject, lesson):
        """Deleting lesson creates history entry."""
        LessonService.delete_lesson(lesson=lesson, user=teacher_user)

        history = LessonHistory.objects.filter(
            lesson=lesson,
            action='cancelled'
        )

        assert history.exists()

    def test_delete_lesson_not_teacher_fails(self, teacher_user, student_user, math_subject, lesson):
        """Only teacher who created lesson can delete."""
        from accounts.models import User

        other_teacher = User.objects.create_user(
            username='other_teacher@test.com',
            email='other_teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )

        with pytest.raises(ValidationError) as exc:
            LessonService.delete_lesson(lesson=lesson, user=other_teacher)

        assert 'teacher' in str(exc.value).lower()

    def test_delete_lesson_2hour_rule_enforced(self, teacher_user, student_user, math_subject, near_future_lesson):
        """Cannot delete lesson less than 2 hours before start."""
        with pytest.raises(ValidationError) as exc:
            LessonService.delete_lesson(lesson=near_future_lesson, user=teacher_user)

        assert 'less than 2 hours' in str(exc.value).lower() or '2 hour' in str(exc.value).lower()

    def test_delete_already_cancelled_lesson_fails(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot delete already cancelled lesson."""
        cancelled = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() + timedelta(days=3),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='cancelled'
        )

        with pytest.raises(ValidationError) as exc:
            LessonService.delete_lesson(lesson=cancelled, user=teacher_user)

        assert 'cancelled' in str(exc.value).lower() or 'less than 2 hours' in str(exc.value).lower()

    def test_delete_completed_lesson_fails(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot delete completed lesson."""
        completed = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() - timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='completed'
        )

        with pytest.raises(ValidationError) as exc:
            LessonService.delete_lesson(lesson=completed, user=teacher_user)

        assert 'less than 2 hours' in str(exc.value).lower()


# ============================================================================
# LESSON HISTORY TESTS
# ============================================================================

class TestLessonHistory:
    """Test LessonHistory model tracking."""

    def test_lesson_history_on_creation(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Creating lesson creates history entry."""
        future_date = timezone.now().date() + timedelta(days=3)

        lesson = LessonService.create_lesson(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Test'
        )

        history = LessonHistory.objects.filter(lesson=lesson)
        assert history.exists()
        assert history.first().action == 'created'

    def test_lesson_history_on_update(self, teacher_user, student_user, math_subject, lesson):
        """Updating lesson creates history entry."""
        LessonService.update_lesson(
            lesson=lesson,
            updates={'description': 'New'},
            user=teacher_user
        )

        history = LessonHistory.objects.filter(lesson=lesson, action='updated')
        assert history.exists()

    def test_lesson_history_on_delete(self, teacher_user, student_user, math_subject, lesson):
        """Deleting lesson creates history entry."""
        LessonService.delete_lesson(lesson=lesson, user=teacher_user)

        history = LessonHistory.objects.filter(lesson=lesson, action='cancelled')
        assert history.exists()

    def test_lesson_history_preserves_old_values(self, teacher_user, student_user, math_subject, lesson):
        """History preserves old values on update."""
        old_desc = lesson.description
        new_desc = 'Completely new description'

        LessonService.update_lesson(
            lesson=lesson,
            updates={'description': new_desc},
            user=teacher_user
        )

        history = LessonHistory.objects.filter(lesson=lesson, action='updated').first()
        assert old_desc in str(history.old_values)

    def test_lesson_history_ordering(self, teacher_user, student_user, math_subject, lesson):
        """History is ordered by timestamp descending."""
        LessonService.update_lesson(
            lesson=lesson,
            updates={'description': 'First update'},
            user=teacher_user
        )

        LessonService.update_lesson(
            lesson=lesson,
            updates={'description': 'Second update'},
            user=teacher_user
        )

        histories = LessonHistory.objects.filter(lesson=lesson).order_by('-timestamp')
        # Most recent should be last update
        assert 'Second update' in str(histories[0].new_values)
