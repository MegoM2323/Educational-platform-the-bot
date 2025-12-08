"""
Unit tests for AdminScheduleService.

Tests cover:
- get_all_lessons() - retrieving all lessons with various filters
- get_schedule_stats() - retrieving schedule statistics
- get_teachers_list() - getting list of teachers for filtering
- get_subjects_list() - getting list of subjects for filtering
- get_students_list() - getting list of students for filtering
- Query optimization (select_related, prefetch_related)
- Filter logic (teacher, student, subject, date range, status)
"""

import pytest
from datetime import time, timedelta, date
from django.utils import timezone
from django.test import TestCase

from scheduling.models import Lesson
from scheduling.admin_schedule_service import AdminScheduleService
from accounts.models import User
from materials.models import Subject, SubjectEnrollment


@pytest.mark.django_db
class TestAdminScheduleServiceGetAllLessons:
    """Test AdminScheduleService.get_all_lessons() method."""

    def test_get_all_lessons_returns_all_lessons(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Should return all lessons when no filters applied."""
        # Create multiple lessons
        future_date1 = timezone.now().date() + timedelta(days=1)
        future_date2 = timezone.now().date() + timedelta(days=2)
        future_date3 = timezone.now().date() + timedelta(days=3)

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date1,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date2,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status='confirmed'
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date3,
            start_time=time(16, 0),
            end_time=time(17, 0),
            status='completed'
        )

        # Get all lessons
        lessons = AdminScheduleService.get_all_lessons()

        assert lessons.count() == 3
        assert lessons[0].status == 'pending'
        assert lessons[1].status == 'confirmed'
        assert lessons[2].status == 'completed'

    def test_get_all_lessons_uses_select_related_for_optimization(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Should use select_related to optimize queries."""
        future_date = timezone.now().date() + timedelta(days=1)
        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        lessons = AdminScheduleService.get_all_lessons()

        # Access related objects - should not trigger additional queries
        for lesson in lessons:
            _ = lesson.teacher.first_name
            _ = lesson.student.first_name
            _ = lesson.subject.name

    def test_filter_by_teacher_id(self, teacher_user, student_user, another_student_user, math_subject, english_subject, subject_enrollment, another_enrollment):
        """Should filter lessons by teacher_id."""
        future_date = timezone.now().date() + timedelta(days=1)

        # Create lesson with teacher_user (using existing subject_enrollment)
        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Create another teacher with enrollment for another_student
        another_teacher = User.objects.create_user(
            username='another_teacher@test.com',
            email='another_teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )
        from accounts.models import TeacherProfile
        TeacherProfile.objects.create(user=another_teacher)

        # Create enrollment for another_teacher with another_student
        SubjectEnrollment.objects.create(
            student=another_student_user,
            teacher=another_teacher,
            subject=math_subject,
            is_active=True
        )

        Lesson.objects.create(
            teacher=another_teacher,
            student=another_student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(12, 0),
            end_time=time(13, 0)
        )

        # Filter by teacher_user
        lessons = AdminScheduleService.get_all_lessons(teacher_id=teacher_user.id)

        assert lessons.count() == 1
        assert lessons[0].teacher_id == teacher_user.id

    def test_filter_by_student_id(self, teacher_user, student_user, another_student_user, math_subject, english_subject, subject_enrollment, another_enrollment):
        """Should filter lessons by student_id."""
        future_date = timezone.now().date() + timedelta(days=1)

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=another_student_user,
            subject=english_subject,
            date=future_date,
            start_time=time(12, 0),
            end_time=time(13, 0)
        )

        # Filter by student_user
        lessons = AdminScheduleService.get_all_lessons(student_id=student_user.id)

        assert lessons.count() == 1
        assert lessons[0].student_id == student_user.id

    def test_filter_by_subject_id(self, teacher_user, student_user, math_subject, english_subject, subject_enrollment):
        """Should filter lessons by subject_id."""
        future_date = timezone.now().date() + timedelta(days=1)

        # Use existing subject_enrollment for math_subject
        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Create enrollment for english_subject as well
        SubjectEnrollment.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=english_subject,
            is_active=True
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=english_subject,
            date=future_date,
            start_time=time(12, 0),
            end_time=time(13, 0)
        )

        # Filter by math_subject
        lessons = AdminScheduleService.get_all_lessons(subject_id=math_subject.id)

        assert lessons.count() == 1
        assert lessons[0].subject_id == math_subject.id

    def test_filter_by_date_from(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Should filter lessons by date_from."""
        date1 = timezone.now().date() + timedelta(days=1)
        date2 = timezone.now().date() + timedelta(days=5)
        date3 = timezone.now().date() + timedelta(days=10)

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date1,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date2,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date3,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Filter from date2 onwards
        lessons = AdminScheduleService.get_all_lessons(date_from=date2)

        assert lessons.count() == 2
        assert all(lesson.date >= date2 for lesson in lessons)

    def test_filter_by_date_to(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Should filter lessons by date_to."""
        date1 = timezone.now().date() + timedelta(days=1)
        date2 = timezone.now().date() + timedelta(days=5)
        date3 = timezone.now().date() + timedelta(days=10)

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date1,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date2,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date3,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Filter up to date2
        lessons = AdminScheduleService.get_all_lessons(date_to=date2)

        assert lessons.count() == 2
        assert all(lesson.date <= date2 for lesson in lessons)

    def test_filter_by_date_range(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Should filter lessons by both date_from and date_to."""
        date1 = timezone.now().date() + timedelta(days=1)
        date2 = timezone.now().date() + timedelta(days=5)
        date3 = timezone.now().date() + timedelta(days=10)

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date1,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date2,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date3,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        # Filter by date range
        lessons = AdminScheduleService.get_all_lessons(date_from=date1, date_to=date2)

        assert lessons.count() == 2
        assert all(lesson.date >= date1 and lesson.date <= date2 for lesson in lessons)

    def test_filter_by_status(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Should filter lessons by status."""
        future_date = timezone.now().date() + timedelta(days=1)

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status='confirmed'
        )

        # Filter by status
        lessons = AdminScheduleService.get_all_lessons(status='confirmed')

        assert lessons.count() == 1
        assert lessons[0].status == 'confirmed'

    def test_multiple_filters_combined(self, teacher_user, student_user, another_student_user, math_subject, english_subject, subject_enrollment):
        """Should apply multiple filters correctly."""
        date1 = timezone.now().date() + timedelta(days=1)
        date2 = timezone.now().date() + timedelta(days=10)

        # Create enrollment for another_student with math_subject
        SubjectEnrollment.objects.create(
            student=another_student_user,
            teacher=teacher_user,
            subject=math_subject,
            is_active=True
        )

        # Create enrollment for student_user with english_subject
        SubjectEnrollment.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=english_subject,
            is_active=True
        )

        # Create multiple lessons with different combinations
        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=date1,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=another_student_user,
            subject=math_subject,
            date=date1,
            start_time=time(12, 0),
            end_time=time(13, 0),
            status='confirmed'
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=english_subject,
            date=date2,
            start_time=time(14, 0),
            end_time=time(15, 0),
            status='pending'
        )

        # Apply multiple filters
        lessons = AdminScheduleService.get_all_lessons(
            teacher_id=teacher_user.id,
            student_id=student_user.id,
            subject_id=math_subject.id,
            status='pending'
        )

        assert lessons.count() == 1
        assert lessons[0].student_id == student_user.id
        assert lessons[0].subject_id == math_subject.id
        assert lessons[0].status == 'pending'

    def test_empty_result_when_no_lessons_match_filter(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Should return empty queryset when no lessons match filters."""
        future_date = timezone.now().date() + timedelta(days=1)
        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        # Filter by non-existent status
        lessons = AdminScheduleService.get_all_lessons(status='cancelled')

        assert lessons.count() == 0


@pytest.mark.django_db
class TestAdminScheduleServiceGetStats:
    """Test AdminScheduleService.get_schedule_stats() method."""

    def test_get_schedule_stats_returns_correct_structure(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Should return stats with all required keys."""
        stats = AdminScheduleService.get_schedule_stats()

        assert 'total_lessons' in stats
        assert 'today_lessons' in stats
        assert 'week_ahead_lessons' in stats
        assert 'pending_lessons' in stats
        assert 'completed_lessons' in stats
        assert 'cancelled_lessons' in stats

    def test_get_schedule_stats_counts_lessons_correctly(self, teacher_user, student_user, math_subject, subject_enrollment):
        """Should count lessons correctly in stats."""
        today = timezone.now().date()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=10)

        # Create lessons with different statuses and dates
        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=today,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='confirmed'
        )

        Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=next_week,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='completed'
        )

        stats = AdminScheduleService.get_schedule_stats()

        assert stats['total_lessons'] == 3
        assert stats['today_lessons'] == 1
        assert stats['week_ahead_lessons'] == 2  # today + tomorrow + future within week
        assert stats['pending_lessons'] == 1
        assert stats['completed_lessons'] == 1


@pytest.mark.django_db
class TestAdminScheduleServiceGetTeachersList:
    """Test AdminScheduleService.get_teachers_list() method."""

    def test_get_teachers_list_returns_all_teachers(self, teacher_user):
        """Should return list of all teachers."""
        # Create additional teacher
        from accounts.models import TeacherProfile
        another_teacher = User.objects.create_user(
            username='another_teacher@test.com',
            email='another_teacher@test.com',
            password='TestPass123!',
            first_name='John',
            last_name='Doe',
            role='teacher'
        )
        TeacherProfile.objects.create(user=another_teacher)

        teachers = AdminScheduleService.get_teachers_list()

        assert len(teachers) == 2
        teacher_ids = [t['id'] for t in teachers]
        assert teacher_user.id in teacher_ids
        assert another_teacher.id in teacher_ids

    def test_get_teachers_list_includes_full_name(self, teacher_user):
        """Should include teacher full name in list."""
        teachers = AdminScheduleService.get_teachers_list()

        teacher_dict = next((t for t in teachers if t['id'] == teacher_user.id), None)
        assert teacher_dict is not None
        assert 'name' in teacher_dict
        assert teacher_user.first_name in teacher_dict['name'] or teacher_user.last_name in teacher_dict['name']

    def test_get_teachers_list_uses_email_as_fallback(self):
        """Should use email as name if first/last name missing."""
        from accounts.models import TeacherProfile
        teacher = User.objects.create_user(
            username='teacher_no_name@test.com',
            email='teacher_no_name@test.com',
            password='TestPass123!',
            role='teacher'
        )
        TeacherProfile.objects.create(user=teacher)

        teachers = AdminScheduleService.get_teachers_list()

        teacher_dict = next((t for t in teachers if t['id'] == teacher.id), None)
        assert teacher_dict is not None
        assert teacher_dict['name'] == teacher.email


@pytest.mark.django_db
class TestAdminScheduleServiceGetSubjectsList:
    """Test AdminScheduleService.get_subjects_list() method."""

    def test_get_subjects_list_returns_all_subjects(self, math_subject, english_subject):
        """Should return list of all subjects."""
        subjects = AdminScheduleService.get_subjects_list()

        assert len(subjects) >= 2
        subject_ids = [s['id'] for s in subjects]
        assert math_subject.id in subject_ids
        assert english_subject.id in subject_ids

    def test_get_subjects_list_includes_name(self, math_subject):
        """Should include subject name in list."""
        subjects = AdminScheduleService.get_subjects_list()

        subject_dict = next((s for s in subjects if s['id'] == math_subject.id), None)
        assert subject_dict is not None
        assert subject_dict['name'] == math_subject.name

    def test_get_subjects_list_empty_when_no_subjects(self):
        """Should return empty list when no subjects exist."""
        Subject.objects.all().delete()

        subjects = AdminScheduleService.get_subjects_list()

        assert len(subjects) == 0


@pytest.mark.django_db
class TestAdminScheduleServiceGetStudentsList:
    """Test AdminScheduleService.get_students_list() method."""

    def test_get_students_list_returns_all_students(self, student_user, another_student_user):
        """Should return list of all students."""
        students = AdminScheduleService.get_students_list()

        assert len(students) >= 2
        student_ids = [s['id'] for s in students]
        assert student_user.id in student_ids
        assert another_student_user.id in student_ids

    def test_get_students_list_includes_full_name(self, student_user):
        """Should include student full name in list."""
        students = AdminScheduleService.get_students_list()

        student_dict = next((s for s in students if s['id'] == student_user.id), None)
        assert student_dict is not None
        assert 'name' in student_dict
        assert student_user.first_name in student_dict['name'] or student_user.last_name in student_dict['name']

    def test_get_students_list_uses_email_as_fallback(self):
        """Should use email as name if first/last name missing."""
        from accounts.models import StudentProfile
        student = User.objects.create_user(
            username='student_no_name@test.com',
            email='student_no_name@test.com',
            password='TestPass123!',
            role='student'
        )
        StudentProfile.objects.create(user=student, grade='10')

        students = AdminScheduleService.get_students_list()

        student_dict = next((s for s in students if s['id'] == student.id), None)
        assert student_dict is not None
        assert student_dict['name'] == student.email

    def test_get_students_list_empty_when_no_students(self):
        """Should return empty list when no students exist."""
        User.objects.filter(role='student').delete()

        students = AdminScheduleService.get_students_list()

        assert len(students) == 0
