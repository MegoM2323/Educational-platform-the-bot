"""
Comprehensive unit tests for Lesson Creation Service (LessonService).

Tests for:
- Lesson creation validates SubjectEnrollment
- Lesson creation fails with invalid data
- Lesson appears in teacher's lesson list
- Lesson appears in student's lesson list
- LessonHistory record created
- SubjectEnrollment validation

Usage:
    pytest backend/tests/unit/scheduling/test_lesson_service_comprehensive.py -v
    pytest backend/tests/unit/scheduling/test_lesson_service_comprehensive.py --cov=scheduling.services.lesson_service
"""

import pytest
from datetime import time, timedelta
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model

from scheduling.models import Lesson, LessonHistory
from scheduling.services.lesson_service import LessonService
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestLessonServiceCreateComprehensive:
    """Comprehensive tests for LessonService.create_lesson"""

    @pytest.fixture
    def setup_users_and_subject(self, db):
        """Setup users and subject for lesson creation"""
        teacher = User.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        from accounts.models import TeacherProfile
        TeacherProfile.objects.create(user=teacher)

        student = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        from accounts.models import StudentProfile
        StudentProfile.objects.create(user=student)

        subject = Subject.objects.create(
            name='Математика',
            description='Курс математики'
        )

        return teacher, student, subject

    # ========== Valid Lesson Creation Tests ==========

    def test_create_lesson_with_valid_data(self, setup_users_and_subject):
        """Scenario: Valid data → lesson created successfully"""
        teacher, student, subject = setup_users_and_subject

        # Create active enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        # Arrange
        future_date = timezone.now().date() + timedelta(days=3)

        # Act
        lesson = LessonService.create_lesson(
            teacher=teacher,
            student=student,
            subject=subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Алгебра',
            telemost_link='https://telemost.yandex.ru/test'
        )

        # Assert
        assert lesson.id is not None
        assert lesson.teacher == teacher
        assert lesson.student == student
        assert lesson.subject == subject
        assert lesson.date == future_date
        assert lesson.start_time == time(10, 0)
        assert lesson.end_time == time(11, 0)
        assert lesson.description == 'Алгебра'
        assert lesson.telemost_link == 'https://telemost.yandex.ru/test'
        assert lesson.status == 'pending'

    def test_create_lesson_creates_lesson_history(self, setup_users_and_subject):
        """Scenario: Lesson creation → LessonHistory record created"""
        teacher, student, subject = setup_users_and_subject

        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        future_date = timezone.now().date() + timedelta(days=3)

        # Act
        lesson = LessonService.create_lesson(
            teacher=teacher,
            student=student,
            subject=subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Assert: LessonHistory record created
        history = LessonHistory.objects.filter(lesson=lesson)
        assert history.exists()
        assert history.first().action == 'created'
        assert history.first().performed_by == teacher

    def test_lesson_appears_in_teacher_lesson_list(self, setup_users_and_subject):
        """Scenario: Created lesson → appears in teacher's lesson list"""
        teacher, student, subject = setup_users_and_subject

        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        future_date = timezone.now().date() + timedelta(days=3)

        # Act
        lesson = LessonService.create_lesson(
            teacher=teacher,
            student=student,
            subject=subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Assert: Lesson appears in teacher's lessons
        teacher_lessons = Lesson.objects.filter(teacher=teacher)
        assert teacher_lessons.exists()
        assert lesson in teacher_lessons

    def test_lesson_appears_in_student_lesson_list(self, setup_users_and_subject):
        """Scenario: Created lesson → appears in student's lesson list"""
        teacher, student, subject = setup_users_and_subject

        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        future_date = timezone.now().date() + timedelta(days=3)

        # Act
        lesson = LessonService.create_lesson(
            teacher=teacher,
            student=student,
            subject=subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Assert: Lesson appears in student's lessons
        student_lessons = Lesson.objects.filter(student=student)
        assert student_lessons.exists()
        assert lesson in student_lessons

    # ========== SubjectEnrollment Validation Tests ==========

    def test_create_lesson_validates_subject_enrollment(self, setup_users_and_subject):
        """Scenario: No active enrollment → validation fails"""
        teacher, student, subject = setup_users_and_subject

        # Do NOT create enrollment

        future_date = timezone.now().date() + timedelta(days=3)

        # Act & Assert
        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher,
                student=student,
                subject=subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert 'enrollment' in str(exc.value).lower() or 'subject' in str(exc.value).lower()

    def test_create_lesson_fails_with_inactive_enrollment(self, setup_users_and_subject):
        """Scenario: Inactive enrollment → lesson creation fails"""
        teacher, student, subject = setup_users_and_subject

        # Create INACTIVE enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=False  # INACTIVE
        )

        future_date = timezone.now().date() + timedelta(days=3)

        # Act & Assert
        with pytest.raises(ValidationError):
            LessonService.create_lesson(
                teacher=teacher,
                student=student,
                subject=subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

    def test_create_lesson_fails_teacher_mismatch(self, setup_users_and_subject):
        """Scenario: Teacher doesn't match enrollment → fails"""
        teacher, student, subject = setup_users_and_subject

        # Create different teacher
        other_teacher = User.objects.create_user(
            username='other_teacher',
            email='other_teacher@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        from accounts.models import TeacherProfile
        TeacherProfile.objects.create(user=other_teacher)

        # Create enrollment with original teacher
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        future_date = timezone.now().date() + timedelta(days=3)

        # Act & Assert: Try to create with different teacher
        with pytest.raises(ValidationError):
            LessonService.create_lesson(
                teacher=other_teacher,  # Different teacher
                student=student,
                subject=subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

    # ========== Invalid Data Tests ==========

    def test_create_lesson_fails_past_date(self, setup_users_and_subject):
        """Scenario: Past date → 400 Bad Request"""
        teacher, student, subject = setup_users_and_subject

        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        past_date = timezone.now().date() - timedelta(days=1)

        # Act & Assert
        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher,
                student=student,
                subject=subject,
                date=past_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert 'past' in str(exc.value).lower() or 'date' in str(exc.value).lower()

    def test_create_lesson_fails_invalid_time_range(self, setup_users_and_subject):
        """Scenario: start_time >= end_time → validation fails"""
        teacher, student, subject = setup_users_and_subject

        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        future_date = timezone.now().date() + timedelta(days=3)

        # Act & Assert
        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher,
                student=student,
                subject=subject,
                date=future_date,
                start_time=time(11, 0),  # AFTER end_time
                end_time=time(10, 0)
            )

        assert 'start' in str(exc.value).lower() and 'end' in str(exc.value).lower()

    def test_create_lesson_fails_equal_times(self, setup_users_and_subject):
        """Scenario: start_time == end_time → validation fails"""
        teacher, student, subject = setup_users_and_subject

        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        future_date = timezone.now().date() + timedelta(days=3)

        # Act & Assert
        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher,
                student=student,
                subject=subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(10, 0)  # SAME time
            )

        assert 'time' in str(exc.value).lower()

    def test_create_lesson_fails_non_teacher_user(self, setup_users_and_subject):
        """Scenario: Non-teacher user → validation fails"""
        teacher, student, subject = setup_users_and_subject

        # Try to create lesson with student as teacher
        future_date = timezone.now().date() + timedelta(days=3)

        # Act & Assert
        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=student,  # Not a teacher
                student=student,
                subject=subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert 'teacher' in str(exc.value).lower() or 'role' in str(exc.value).lower()

    def test_create_lesson_fails_non_student_user(self, setup_users_and_subject):
        """Scenario: Non-student user → validation fails"""
        teacher, student, subject = setup_users_and_subject

        # Try to create lesson with teacher as student
        future_date = timezone.now().date() + timedelta(days=3)

        # Act & Assert
        with pytest.raises(ValidationError) as exc:
            LessonService.create_lesson(
                teacher=teacher,
                student=teacher,  # Not a student
                subject=subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert 'student' in str(exc.value).lower() or 'role' in str(exc.value).lower()

    # ========== Boundary Tests ==========

    def test_create_lesson_today(self, setup_users_and_subject):
        """Scenario: Lesson for today → succeeds if valid time"""
        teacher, student, subject = setup_users_and_subject

        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        today = timezone.now().date()
        future_time = (timezone.now() + timedelta(hours=2)).time()
        end_time = (timezone.now() + timedelta(hours=3)).time()

        # Act
        lesson = LessonService.create_lesson(
            teacher=teacher,
            student=student,
            subject=subject,
            date=today,
            start_time=future_time,
            end_time=end_time
        )

        # Assert
        assert lesson.date == today

    def test_create_multiple_lessons_same_teacher(self, setup_users_and_subject):
        """Scenario: Same teacher creates multiple lessons → all saved"""
        teacher, student, subject = setup_users_and_subject

        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        # Act: Create 3 lessons
        lessons = []
        for i in range(3):
            future_date = timezone.now().date() + timedelta(days=i+1)
            lesson = LessonService.create_lesson(
                teacher=teacher,
                student=student,
                subject=subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )
            lessons.append(lesson)

        # Assert: All lessons created
        assert len(lessons) == 3
        assert all(l.teacher == teacher for l in lessons)
        teacher_lessons = Lesson.objects.filter(teacher=teacher)
        assert teacher_lessons.count() == 3

    # ========== N+1 Query Tests ==========

    def test_create_lesson_query_efficiency(self, setup_users_and_subject, django_assert_num_queries):
        """Verify lesson creation doesn't have excessive queries"""
        teacher, student, subject = setup_users_and_subject

        enrollment = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher,
            is_active=True
        )

        future_date = timezone.now().date() + timedelta(days=3)

        # Act: Should use ~5-6 queries (get user, check roles, get enrollment, create lesson, create history)
        with django_assert_num_queries(6):
            lesson = LessonService.create_lesson(
                teacher=teacher,
                student=student,
                subject=subject,
                date=future_date,
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        assert lesson.id is not None
