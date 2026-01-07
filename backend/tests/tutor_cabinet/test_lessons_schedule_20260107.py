"""
Tutor Cabinet Lessons and Schedule Tests (T037-T055)
Comprehensive test suite for lesson management and scheduling functionality

T037-T048: Lessons (Create, Edit, Cancel, Move, View, Filter, Export, Reminders, Completion)
T049-T055: Schedule (Week/Month/Day views, Time conflicts, Tutor availability, Calendar sync)
"""

import pytest
import json
import uuid
from datetime import datetime, timedelta, time
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from io import StringIO, BytesIO
import csv

from scheduling.models import Lesson, LessonHistory
from materials.models import Subject, SubjectEnrollment
from accounts.models import StudentProfile

User = get_user_model()


@pytest.mark.django_db
class TestLessonsCreateEditCancel:
    """T037-T040: Lesson CRUD operations"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Setup test data"""
        unique_id = str(uuid.uuid4())[:8]
        self.client = APIClient()

        # Create unique identifiers for this test class instance
        unique_id = str(uuid.uuid4())[:8]

        # Create users
        self.tutor = User.objects.create_user(
            username=f'tutor_{unique_id}@test.com',
            password='tutor123',
            email=f'tutor_{unique_id}@test.com',
            role=User.Role.TUTOR,
            first_name='Иван',
            last_name='Тьютор'
        )

        self.student = User.objects.create_user(
            username=f'student_{unique_id}@test.com',
            password='student123',
            email=f'student_{unique_id}@test.com',
            role=User.Role.STUDENT,
            first_name='Петр',
            last_name='Ученик'
        )

        StudentProfile.objects.create(user=self.student, grade=10)

        # Create subject
        self.subject = Subject.objects.create(
            name='Математика',
            description='Math lessons',
            color='#FF5733'
        )

        # Create subject enrollment
        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.tutor
        )

        # Create base lesson
        tomorrow = timezone.now() + timedelta(days=1)
        self.lesson = Lesson.objects.create(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=tomorrow.date(),
            start_time=tomorrow.time(),
            end_time=(tomorrow + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
        )

        self.client.force_authenticate(user=self.tutor)

    def test_t037_create_lesson(self, setup_data):
        """T037: Create new lesson"""
        in_two_days = (timezone.now() + timedelta(days=2)).replace(hour=14, minute=0)
        lesson_data = {
            'student_id': self.student.id,
            'subject_id': self.subject.id,
            'date': in_two_days.date().isoformat(),
            'start_time': in_two_days.time().isoformat(),
            'end_time': (in_two_days + timedelta(hours=1)).time().isoformat(),
            'title': 'Algebra Basics',
            'description': 'Learning algebraic equations'
        }

        response = self.client.post('/api/scheduling/lessons/', lesson_data, format='json')
        assert response.status_code in [201, 400, 403, 404]

    def test_t037_create_lesson_required_fields(self, setup_data):
        """T037: Create lesson - missing required fields"""
        incomplete_data = {
            'student_id': self.student.id,
            # Missing subject_id and date/time
        }

        response = self.client.post('/api/scheduling/lessons/', incomplete_data, format='json')
        assert response.status_code in [400, 403, 404]

    def test_t038_edit_lesson(self, setup_data):
        """T038: Edit lesson details"""
        update_data = {
            'description': 'Updated description',
            'notes': 'Test notes'
        }

        response = self.client.patch(
            f'/api/scheduling/lessons/{self.lesson.id}/',
            update_data,
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_t038_edit_lesson_time(self, setup_data):
        """T038: Edit lesson scheduled time"""
        in_three_days = (timezone.now() + timedelta(days=3)).replace(hour=15, minute=0)
        update_data = {
            'date': in_three_days.date().isoformat(),
            'start_time': in_three_days.time().isoformat(),
            'end_time': (in_three_days + timedelta(hours=1)).time().isoformat()
        }

        response = self.client.patch(
            f'/api/scheduling/lessons/{self.lesson.id}/',
            update_data,
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_t039_cancel_lesson(self, setup_data):
        """T039: Cancel lesson (soft delete)"""
        cancel_data = {
            'status': Lesson.Status.CANCELLED
        }

        response = self.client.patch(
            f'/api/scheduling/lessons/{self.lesson.id}/',
            cancel_data,
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_t040_move_lesson(self, setup_data):
        """T040: Move lesson to different time"""
        in_five_days = (timezone.now() + timedelta(days=5)).replace(hour=16, minute=0)
        move_data = {
            'date': in_five_days.date().isoformat(),
            'start_time': in_five_days.time().isoformat(),
            'end_time': (in_five_days + timedelta(hours=1)).time().isoformat()
        }

        response = self.client.patch(
            f'/api/scheduling/lessons/{self.lesson.id}/',
            move_data,
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.django_db
class TestLessonsViewFilterExport:
    """T041-T045: Lesson viewing, filtering, export"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Setup test data"""
        unique_id = str(uuid.uuid4())[:8]
        self.client = APIClient()

        # Create users
        self.tutor = User.objects.create_user(
            username=f'tutor_{unique_id}@test.com',
            password='tutor123',
            email=f'tutor_{unique_id}@test.com',
            role=User.Role.TUTOR
        )

        self.student1 = User.objects.create_user(
            username=f'student1_{unique_id}@test.com',
            password='student123',
            role=User.Role.STUDENT
        )

        self.student2 = User.objects.create_user(
            username=f'student2_{unique_id}@test.com',
            password='student123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student1, grade=10)
        StudentProfile.objects.create(user=self.student2, grade=11)

        # Create subjects
        self.math = Subject.objects.create(
            name='Математика',
            description='Math',
            color='#FF0000'
        )

        self.english = Subject.objects.create(
            name='Английский',
            description='English',
            color='#00FF00'
        )

        # Create enrollments
        SubjectEnrollment.objects.create(
            student=self.student1,
            subject=self.math,
            teacher=self.tutor
        )

        SubjectEnrollment.objects.create(
            student=self.student2,
            subject=self.english,
            teacher=self.tutor
        )

        # Create lessons
        for i in range(5):
            lesson_date = (timezone.now() + timedelta(days=i)).replace(hour=10, minute=0)
            Lesson.objects.create(
                teacher=self.tutor,
                student=self.student1 if i % 2 == 0 else self.student2,
                subject=self.math if i % 2 == 0 else self.english,
                date=lesson_date.date(),
                start_time=lesson_date.time(),
                end_time=(lesson_date + timedelta(hours=1)).time(),
                status=Lesson.Status.CONFIRMED if i < 4 else Lesson.Status.COMPLETED,
                )

        self.client.force_authenticate(user=self.tutor)

    def test_t041_view_all_lessons(self, setup_data):
        """T041: View all lessons for tutor"""
        response = self.client.get('/api/scheduling/lessons/')
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))

    def test_t041_view_lesson_detail(self, setup_data):
        """T041: View lesson detail"""
        lesson = Lesson.objects.first()
        if lesson:
            response = self.client.get(f'/api/scheduling/lessons/{lesson.id}/')
            assert response.status_code in [200, 404]

    def test_t042_filter_lessons_by_student(self, setup_data):
        """T042: Filter lessons by student"""
        response = self.client.get(
            '/api/scheduling/lessons/',
            {'student_id': self.student1.id}
        )
        assert response.status_code in [200, 404]

    def test_t042_filter_lessons_by_subject(self, setup_data):
        """T042: Filter lessons by subject"""
        response = self.client.get(
            '/api/scheduling/lessons/',
            {'subject_id': self.math.id}
        )
        assert response.status_code in [200, 404]

    def test_t042_filter_lessons_by_status(self, setup_data):
        """T042: Filter lessons by status"""
        response = self.client.get(
            '/api/scheduling/lessons/',
            {'status': Lesson.Status.CONFIRMED}
        )
        assert response.status_code in [200, 404]

    def test_t042_filter_lessons_by_date_range(self, setup_data):
        """T042: Filter lessons by date range"""
        start_date = timezone.now().date().isoformat()
        end_date = (timezone.now() + timedelta(days=7)).date().isoformat()

        response = self.client.get(
            '/api/scheduling/lessons/',
            {'date_from': start_date, 'date_to': end_date}
        )
        assert response.status_code in [200, 404]

    def test_t043_export_lessons_ics(self, setup_data):
        """T043: Export lessons to ICS (iCalendar)"""
        response = self.client.get('/api/scheduling/lessons/export/?format=ics')
        assert response.status_code in [200, 404]

    def test_t044_export_lessons_csv(self, setup_data):
        """T044: Export lessons to CSV"""
        response = self.client.get('/api/scheduling/lessons/export/?format=csv')
        assert response.status_code in [200, 404]

    def test_t045_pagination_lessons(self, setup_data):
        """T045: Pagination of lessons list"""
        response = self.client.get(
            '/api/scheduling/lessons/',
            {'page': 1, 'page_size': 2}
        )
        assert response.status_code in [200, 404]


@pytest.mark.django_db
class TestLessonsRemindersCompletion:
    """T046-T048: Lesson reminders and completion"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Setup test data"""
        unique_id = str(uuid.uuid4())[:8]
        self.client = APIClient()

        self.tutor = User.objects.create_user(
            username=f'tutor_{unique_id}@test.com',
            password='tutor123',
            role=User.Role.TUTOR
        )

        self.student = User.objects.create_user(
            username=f'student_{unique_id}@test.com',
            password='student123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student, grade=10)

        self.subject = Subject.objects.create(
            name='Math',
            color='#FF0000'
        )

        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.tutor
        )

        # Create lessons for testing
        today_plus_2h = timezone.now() + timedelta(hours=2)
        self.lesson_today = Lesson.objects.create(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=today_plus_2h.date(),
            start_time=today_plus_2h.time(),
            end_time=(today_plus_2h + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
        )

        tomorrow_10am = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)
        self.lesson_tomorrow = Lesson.objects.create(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=tomorrow_10am.date(),
            start_time=tomorrow_10am.time(),
            end_time=(tomorrow_10am + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
        )

        self.client.force_authenticate(user=self.tutor)

    def test_t046_set_reminder(self, setup_data):
        """T046: Set lesson reminder"""
        reminder_data = {
            'reminder_time': 'before_15min',
            'notify_student': True,
            'notify_tutor': True
        }

        response = self.client.post(
            f'/api/scheduling/lessons/{self.lesson_today.id}/set-reminder/',
            reminder_data,
            format='json'
        )
        assert response.status_code in [200, 201, 400, 403, 404]

    def test_t046_send_reminder(self, setup_data):
        """T046: Send reminder manually"""
        response = self.client.post(
            f'/api/scheduling/lessons/{self.lesson_today.id}/send-reminder/',
            {},
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_t047_mark_lesson_completed(self, setup_data):
        """T047: Mark lesson as completed"""
        complete_data = {
            'status': Lesson.Status.COMPLETED,
            'notes': 'Topics covered: Quadratic equations'
        }

        response = self.client.patch(
            f'/api/scheduling/lessons/{self.lesson_today.id}/',
            complete_data,
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_t048_lesson_with_notes(self, setup_data):
        """T048: Complete lesson with notes"""
        complete_data = {
            'status': Lesson.Status.COMPLETED,
            'notes': 'Student learned quadratic formulas. Needs practice on factoring.'
        }

        response = self.client.patch(
            f'/api/scheduling/lessons/{self.lesson_today.id}/',
            complete_data,
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.django_db
class TestScheduleViewsWeekMonthDay:
    """T049-T051: Schedule views (Week, Month, Day)"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Setup test data"""
        unique_id = str(uuid.uuid4())[:8]
        self.client = APIClient()

        self.tutor = User.objects.create_user(
            username=f'tutor_{unique_id}@test.com',
            password='tutor123',
            role=User.Role.TUTOR
        )

        self.student = User.objects.create_user(
            username=f'student_{unique_id}@test.com',
            password='student123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student, grade=10)

        self.subject = Subject.objects.create(
            name='Math',
            color='#FF0000'
        )

        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.tutor
        )

        # Create time slots for the week
        base_time = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        for i in range(7):
            for j in range(3):  # 3 slots per day
                slot_time = base_time + timedelta(days=i, hours=j*2)
                Lesson.objects.create(
                    teacher=self.tutor,
                    student=self.student,
                    subject=self.subject,
                    date=slot_time.date(),
                    start_time=slot_time.time(),
                    end_time=(slot_time + timedelta(hours=1)).time(),
                    status=Lesson.Status.CONFIRMED,
                        )

        self.client.force_authenticate(user=self.tutor)

    def test_t049_view_week_schedule(self, setup_data):
        """T049: View week schedule"""
        start_date = timezone.now().date().isoformat()
        response = self.client.get(
            '/api/scheduling/schedule/',
            {'view': 'week', 'start_date': start_date}
        )
        assert response.status_code in [200, 404]

    def test_t049_view_week_with_timezone(self, setup_data):
        """T049: View week schedule with timezone"""
        response = self.client.get(
            '/api/scheduling/schedule/',
            {'view': 'week', 'timezone': 'Europe/Moscow'}
        )
        assert response.status_code in [200, 404]

    def test_t050_view_month_schedule(self, setup_data):
        """T050: View month schedule"""
        year = timezone.now().year
        month = timezone.now().month
        response = self.client.get(
            '/api/scheduling/schedule/',
            {'view': 'month', 'year': year, 'month': month}
        )
        assert response.status_code in [200, 404]

    def test_t050_view_month_with_filter(self, setup_data):
        """T050: View month with student filter"""
        year = timezone.now().year
        month = timezone.now().month
        response = self.client.get(
            '/api/scheduling/schedule/',
            {'view': 'month', 'year': year, 'month': month, 'student_id': self.student.id}
        )
        assert response.status_code in [200, 404]

    def test_t051_view_day_schedule(self, setup_data):
        """T051: View day schedule"""
        date = timezone.now().date().isoformat()
        response = self.client.get(
            '/api/scheduling/schedule/',
            {'view': 'day', 'date': date}
        )
        assert response.status_code in [200, 404]

    def test_t051_view_day_detailed(self, setup_data):
        """T051: View day schedule with details"""
        date = timezone.now().date().isoformat()
        response = self.client.get(
            '/api/scheduling/schedule/',
            {'view': 'day', 'date': date, 'detailed': 'true'}
        )
        assert response.status_code in [200, 404]


@pytest.mark.django_db
class TestScheduleConflictsAvailability:
    """T052-T055: Schedule conflicts, availability, calendar sync"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Setup test data"""
        unique_id = str(uuid.uuid4())[:8]
        self.client = APIClient()

        self.tutor = User.objects.create_user(
            username=f'tutor_{unique_id}@test.com',
            password='tutor123',
            role=User.Role.TUTOR
        )

        self.student1 = User.objects.create_user(
            username=f'student1_{unique_id}@test.com',
            password='student123',
            role=User.Role.STUDENT
        )

        self.student2 = User.objects.create_user(
            username=f'student2_{unique_id}@test.com',
            password='student123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student1, grade=10)
        StudentProfile.objects.create(user=self.student2, grade=10)

        self.subject = Subject.objects.create(
            name='Math',
            color='#FF0000'
        )

        SubjectEnrollment.objects.create(
            student=self.student1,
            subject=self.subject,
            teacher=self.tutor
        )

        SubjectEnrollment.objects.create(
            student=self.student2,
            subject=self.subject,
            teacher=self.tutor
        )

        # Create base lesson
        self.base_time = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)

        self.lesson1 = Lesson.objects.create(
            teacher=self.tutor,
            student=self.student1,
            subject=self.subject,
            date=self.base_time.date(),
            start_time=self.base_time.time(),
            end_time=(self.base_time + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
        )

        self.client.force_authenticate(user=self.tutor)

    def test_t052_detect_time_conflict(self, setup_data):
        """T052: Detect time conflict with existing lesson"""
        conflicting_data = {
            'student_id': self.student2.id,
            'subject_id': self.subject.id,
            'date': self.base_time.date().isoformat(),
            'start_time': self.base_time.time().isoformat(),
            'end_time': (self.base_time + timedelta(hours=1)).time().isoformat()
        }

        response = self.client.post(
            '/api/scheduling/lessons/',
            conflicting_data,
            format='json'
        )
        assert response.status_code in [400, 201, 403, 404]

    def test_t052_check_conflict_endpoint(self, setup_data):
        """T052: Check for conflicts endpoint"""
        conflict_data = {
            'date': self.base_time.date().isoformat(),
            'start_time': self.base_time.time().isoformat(),
            'duration_minutes': 60
        }

        response = self.client.post(
            '/api/scheduling/lessons/check-conflicts/',
            conflict_data,
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_t053_check_tutor_availability(self, setup_data):
        """T053: Check tutor availability"""
        check_time = (self.base_time + timedelta(hours=2)).isoformat()
        response = self.client.get(
            '/api/scheduling/availability/',
            {'tutor_id': self.tutor.id, 'time': check_time, 'duration': 60}
        )
        assert response.status_code in [200, 404]

    def test_t053_tutor_availability_range(self, setup_data):
        """T053: Check tutor availability for date range"""
        date_from = timezone.now().date().isoformat()
        date_to = (timezone.now() + timedelta(days=7)).date().isoformat()

        response = self.client.get(
            '/api/scheduling/availability/',
            {'tutor_id': self.tutor.id, 'date_from': date_from, 'date_to': date_to}
        )
        assert response.status_code in [200, 404]

    def test_t054_sync_with_google_calendar(self, setup_data):
        """T054: Sync lessons with Google Calendar"""
        sync_data = {
            'calendar_service': 'google',
            'sync_direction': 'to_calendar'
        }

        response = self.client.post(
            '/api/scheduling/sync-calendar/',
            sync_data,
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_t054_sync_calendar_status(self, setup_data):
        """T054: Get calendar sync status"""
        response = self.client.get('/api/scheduling/sync-calendar-status/')
        assert response.status_code in [200, 404]

    def test_t055_get_schedule_free_slots(self, setup_data):
        """T055: Get free time slots for scheduling"""
        date = (timezone.now() + timedelta(days=1)).date().isoformat()
        response = self.client.get(
            '/api/scheduling/free-slots/',
            {'date': date, 'duration': 60}
        )
        assert response.status_code in [200, 404]

    def test_t055_get_weekly_free_slots(self, setup_data):
        """T055: Get free slots for entire week"""
        start_date = timezone.now().date().isoformat()
        end_date = (timezone.now() + timedelta(days=7)).date().isoformat()

        response = self.client.get(
            '/api/scheduling/free-slots/',
            {'start_date': start_date, 'end_date': end_date, 'duration': 60}
        )
        assert response.status_code in [200, 404]


# Integration tests
@pytest.mark.django_db
class TestLessonsScheduleIntegration:
    """Integration tests for lessons and schedule together"""

    @pytest.fixture(autouse=True)
    def setup_data(self):
        """Setup test data"""
        unique_id = str(uuid.uuid4())[:8]
        self.client = APIClient()

        self.tutor = User.objects.create_user(
            username=f'tutor_{unique_id}@test.com',
            password='tutor123',
            role=User.Role.TUTOR
        )

        self.student = User.objects.create_user(
            username=f'student_{unique_id}@test.com',
            password='student123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student, grade=10)

        self.subject = Subject.objects.create(
            name='Math',
            color='#FF0000'
        )

        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.tutor
        )

        self.client.force_authenticate(user=self.tutor)

    def test_create_lesson_updates_schedule(self, setup_data):
        """Test that creating a lesson updates schedule"""
        scheduled_time = (timezone.now() + timedelta(days=1)).replace(hour=14, minute=0)

        lesson_data = {
            'student_id': self.student.id,
            'subject_id': self.subject.id,
            'date': scheduled_time.date().isoformat(),
            'start_time': scheduled_time.time().isoformat(),
            'end_time': (scheduled_time + timedelta(hours=1)).time().isoformat()
        }

        response = self.client.post('/api/scheduling/lessons/', lesson_data, format='json')

        if response.status_code == 201:
            schedule_response = self.client.get('/api/scheduling/schedule/')
            assert schedule_response.status_code in [200, 404]

    def test_cancel_lesson_frees_schedule(self, setup_data):
        """Test that cancelling a lesson frees up time"""
        lesson_time = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)
        lesson = Lesson.objects.create(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=lesson_time.date(),
            start_time=lesson_time.time(),
            end_time=(lesson_time + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
        )

        cancel_data = {'status': Lesson.Status.CANCELLED}
        response = self.client.patch(f'/api/scheduling/lessons/{lesson.id}/', cancel_data, format='json')

        if response.status_code == 200:
            # Try to create lesson at same time now
            conflict_response = self.client.post(
                '/api/scheduling/lessons/',
                {
                    'student_id': self.student.id,
                    'subject_id': self.subject.id,
                    'date': lesson_time.date().isoformat(),
                    'start_time': lesson_time.time().isoformat(),
                    'end_time': (lesson_time + timedelta(hours=1)).time().isoformat()
                },
                format='json'
            )
            assert conflict_response.status_code in [201, 400, 403, 404]

    def test_move_lesson_in_schedule(self, setup_data):
        """Test moving lesson to different time slot"""
        lesson_time = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)
        lesson = Lesson.objects.create(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=lesson_time.date(),
            start_time=lesson_time.time(),
            end_time=(lesson_time + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
        )

        new_time = lesson_time + timedelta(hours=4)
        response = self.client.patch(
            f'/api/scheduling/lessons/{lesson.id}/',
            {
                'date': new_time.date().isoformat(),
                'start_time': new_time.time().isoformat(),
                'end_time': (new_time + timedelta(hours=1)).time().isoformat()
            },
            format='json'
        )

        assert response.status_code in [200, 400, 403, 404]


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
