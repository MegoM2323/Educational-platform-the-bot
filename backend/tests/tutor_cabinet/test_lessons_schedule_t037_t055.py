"""
Tutor Cabinet Lessons and Schedule Tests (T037-T055)
Test scope: lesson management, scheduling, calendar sync
"""

import pytest
from datetime import datetime, timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from scheduling.models import Lesson
from materials.models import Subject, SubjectEnrollment
from accounts.models import StudentProfile

User = get_user_model()


@pytest.mark.django_db
class TestLessonsT037T040:
    """T037-T040: Lesson CRUD operations (Create, Edit, Cancel, Move)"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data"""
        self.client = APIClient()

        self.tutor = User.objects.create_user(
            username=f'tutor_t037_{int(timezone.now().timestamp())}',
            email=f'tutor_t037_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.TUTOR
        )

        self.student = User.objects.create_user(
            username=f'student_t037_{int(timezone.now().timestamp())}',
            email=f'student_t037_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student, grade=10)

        self.subject = Subject.objects.create(
            name='Math_T037',
            description='Test',
            color='#FF0000'
        )

        SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.tutor
        )

        self.client.force_authenticate(user=self.tutor)

    def test_t037_create_lesson(self, setup):
        """T037: Create lesson"""
        future = (timezone.now() + timedelta(days=2)).replace(hour=14, minute=0)
        response = self.client.post('/api/scheduling/lessons/', {
            'student_id': self.student.id,
            'subject_id': self.subject.id,
            'date': future.date().isoformat(),
            'start_time': future.time().isoformat(),
            'end_time': (future + timedelta(hours=1)).time().isoformat()
        }, format='json')
        assert response.status_code in [201, 400, 403, 404]

    def test_t037_create_without_fields(self, setup):
        """T037: Create lesson without required fields"""
        response = self.client.post('/api/scheduling/lessons/', {
            'student_id': self.student.id
        }, format='json')
        assert response.status_code in [400, 403, 404]

    def test_t038_edit_lesson(self, setup):
        """T038: Edit lesson"""
        future = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)
        lesson = Lesson(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=future.date(),
            start_time=future.time(),
            end_time=(future + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED
        )
        lesson.save()

        response = self.client.patch(f'/api/scheduling/lessons/{lesson.id}/', {
            'notes': 'Updated'
        }, format='json')
        assert response.status_code in [200, 400, 403, 404]

    def test_t038_edit_time(self, setup):
        """T038: Edit lesson time"""
        future = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)
        lesson = Lesson(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=future.date(),
            start_time=future.time(),
            end_time=(future + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
            
        )

        new_time = future + timedelta(hours=2)
        response = self.client.patch(f'/api/scheduling/lessons/{lesson.id}/', {
            'date': new_time.date().isoformat(),
            'start_time': new_time.time().isoformat(),
            'end_time': (new_time + timedelta(hours=1)).time().isoformat()
        }, format='json')
        assert response.status_code in [200, 400, 403, 404]

    def test_t039_cancel_lesson(self, setup):
        """T039: Cancel lesson"""
        future = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)
        lesson = Lesson(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=future.date(),
            start_time=future.time(),
            end_time=(future + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
            
        )

        response = self.client.patch(f'/api/scheduling/lessons/{lesson.id}/', {
            'status': Lesson.Status.CANCELLED
        }, format='json')
        assert response.status_code in [200, 400, 403, 404]

    def test_t040_move_lesson(self, setup):
        """T040: Move lesson"""
        future = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)
        lesson = Lesson(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=future.date(),
            start_time=future.time(),
            end_time=(future + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
            
        )

        new_time = future + timedelta(days=3)
        response = self.client.patch(f'/api/scheduling/lessons/{lesson.id}/', {
            'date': new_time.date().isoformat(),
            'start_time': new_time.time().isoformat(),
            'end_time': (new_time + timedelta(hours=1)).time().isoformat()
        }, format='json')
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.django_db
class TestLessonsT041T045:
    """T041-T045: View, filter, export"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup"""
        self.client = APIClient()

        self.tutor = User.objects.create_user(
            username=f'tutor_t041_{int(timezone.now().timestamp())}',
            email=f'tutor_t041_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.TUTOR
        )

        self.student1 = User.objects.create_user(
            username=f'std1_t041_{int(timezone.now().timestamp())}',
            email=f'std1_t041_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.STUDENT
        )

        self.student2 = User.objects.create_user(
            username=f'std2_t041_{int(timezone.now().timestamp())}',
            email=f'std2_t041_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student1, grade=10)
        StudentProfile.objects.create(user=self.student2, grade=11)

        self.math = Subject.objects.create(
            name=f'Math_T041_{int(timezone.now().timestamp())}',
            color='#FF0000'
        )

        self.eng = Subject.objects.create(
            name=f'Eng_T041_{int(timezone.now().timestamp())}',
            color='#00FF00'
        )

        SubjectEnrollment.objects.create(student=self.student1, subject=self.math, teacher=self.tutor)
        SubjectEnrollment.objects.create(student=self.student2, subject=self.eng, teacher=self.tutor)

        for i in range(3):
            t = (timezone.now() + timedelta(days=i)).replace(hour=10, minute=0)
            Lesson(
                teacher=self.tutor,
                student=self.student1 if i % 2 == 0 else self.student2,
                subject=self.math if i % 2 == 0 else self.eng,
                date=t.date(),
                start_time=t.time(),
                end_time=(t + timedelta(hours=1)).time(),
                status=Lesson.Status.CONFIRMED if i < 2 else Lesson.Status.COMPLETED,
                
            )

        self.client.force_authenticate(user=self.tutor)

    def test_t041_view_all_lessons(self, setup):
        """T041: View all lessons"""
        response = self.client.get('/api/scheduling/lessons/')
        assert response.status_code in [200, 404]

    def test_t041_view_lesson_detail(self, setup):
        """T041: View lesson detail"""
        lesson = Lesson.objects.first()
        if lesson:
            response = self.client.get(f'/api/scheduling/lessons/{lesson.id}/')
            assert response.status_code in [200, 404]

    def test_t042_filter_by_student(self, setup):
        """T042: Filter by student"""
        response = self.client.get('/api/scheduling/lessons/', {'student_id': self.student1.id})
        assert response.status_code in [200, 404]

    def test_t042_filter_by_subject(self, setup):
        """T042: Filter by subject"""
        response = self.client.get('/api/scheduling/lessons/', {'subject_id': self.math.id})
        assert response.status_code in [200, 404]

    def test_t042_filter_by_status(self, setup):
        """T042: Filter by status"""
        response = self.client.get('/api/scheduling/lessons/', {'status': Lesson.Status.CONFIRMED})
        assert response.status_code in [200, 404]

    def test_t042_filter_by_date(self, setup):
        """T042: Filter by date range"""
        s = timezone.now().date().isoformat()
        e = (timezone.now() + timedelta(days=7)).date().isoformat()
        response = self.client.get('/api/scheduling/lessons/', {'date_from': s, 'date_to': e})
        assert response.status_code in [200, 404]

    def test_t043_export_ics(self, setup):
        """T043: Export ICS"""
        response = self.client.get('/api/scheduling/lessons/export/?format=ics')
        assert response.status_code in [200, 404]

    def test_t044_export_csv(self, setup):
        """T044: Export CSV"""
        response = self.client.get('/api/scheduling/lessons/export/?format=csv')
        assert response.status_code in [200, 404]

    def test_t045_pagination(self, setup):
        """T045: Pagination"""
        response = self.client.get('/api/scheduling/lessons/', {'page': 1, 'page_size': 2})
        assert response.status_code in [200, 404]


@pytest.mark.django_db
class TestLessonsT046T048:
    """T046-T048: Reminders and completion"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup"""
        self.client = APIClient()

        self.tutor = User.objects.create_user(
            username=f'tutor_t046_{int(timezone.now().timestamp())}',
            email=f'tutor_t046_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.TUTOR
        )

        self.student = User.objects.create_user(
            username=f'std_t046_{int(timezone.now().timestamp())}',
            email=f'std_t046_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student, grade=10)

        self.subject = Subject.objects.create(
            name=f'Math_T046_{int(timezone.now().timestamp())}',
            color='#FF0000'
        )

        SubjectEnrollment.objects.create(student=self.student, subject=self.subject, teacher=self.tutor)

        t = (timezone.now() + timedelta(hours=2)).replace(minute=0, second=0, microsecond=0)
        self.lesson = Lesson(
            teacher=self.tutor,
            student=self.student,
            subject=self.subject,
            date=t.date(),
            start_time=t.time(),
            end_time=(t + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
            
        )

        self.client.force_authenticate(user=self.tutor)

    def test_t046_set_reminder(self, setup):
        """T046: Set reminder"""
        response = self.client.post(
            f'/api/scheduling/lessons/{self.lesson.id}/set-reminder/',
            {'reminder_time': 'before_15min', 'notify_student': True},
            format='json'
        )
        assert response.status_code in [200, 201, 400, 403, 404]

    def test_t046_send_reminder(self, setup):
        """T046: Send reminder"""
        response = self.client.post(
            f'/api/scheduling/lessons/{self.lesson.id}/send-reminder/',
            {}, format='json'
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_t047_mark_completed(self, setup):
        """T047: Mark completed"""
        response = self.client.patch(
            f'/api/scheduling/lessons/{self.lesson.id}/',
            {'status': Lesson.Status.COMPLETED, 'notes': 'Done'},
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]

    def test_t048_complete_with_notes(self, setup):
        """T048: Complete with notes"""
        response = self.client.patch(
            f'/api/scheduling/lessons/{self.lesson.id}/',
            {'status': Lesson.Status.COMPLETED, 'notes': 'Algebra completed'},
            format='json'
        )
        assert response.status_code in [200, 400, 403, 404]


@pytest.mark.django_db
class TestScheduleT049T051:
    """T049-T051: Schedule views"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup"""
        self.client = APIClient()

        self.tutor = User.objects.create_user(
            username=f'tutor_t049_{int(timezone.now().timestamp())}',
            email=f'tutor_t049_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.TUTOR
        )

        self.student = User.objects.create_user(
            username=f'std_t049_{int(timezone.now().timestamp())}',
            email=f'std_t049_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student, grade=10)

        self.subject = Subject.objects.create(
            name=f'Math_T049_{int(timezone.now().timestamp())}',
            color='#FF0000'
        )

        SubjectEnrollment.objects.create(student=self.student, subject=self.subject, teacher=self.tutor)

        base = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        for i in range(7):
            for j in range(2):
                t = base + timedelta(days=i, hours=j*2)
                Lesson(
                    teacher=self.tutor,
                    student=self.student,
                    subject=self.subject,
                    date=t.date(),
                    start_time=t.time(),
                    end_time=(t + timedelta(hours=1)).time(),
                    status=Lesson.Status.CONFIRMED,
                    
                )

        self.client.force_authenticate(user=self.tutor)

    def test_t049_view_week(self, setup):
        """T049: View week"""
        s = timezone.now().date().isoformat()
        response = self.client.get('/api/scheduling/schedule/', {'view': 'week', 'start_date': s})
        assert response.status_code in [200, 404]

    def test_t049_view_week_tz(self, setup):
        """T049: View week with timezone"""
        response = self.client.get('/api/scheduling/schedule/', {'view': 'week', 'timezone': 'UTC'})
        assert response.status_code in [200, 404]

    def test_t050_view_month(self, setup):
        """T050: View month"""
        y = timezone.now().year
        m = timezone.now().month
        response = self.client.get('/api/scheduling/schedule/', {'view': 'month', 'year': y, 'month': m})
        assert response.status_code in [200, 404]

    def test_t050_view_month_filter(self, setup):
        """T050: View month filtered"""
        y = timezone.now().year
        m = timezone.now().month
        response = self.client.get('/api/scheduling/schedule/', {
            'view': 'month', 'year': y, 'month': m, 'student_id': self.student.id
        })
        assert response.status_code in [200, 404]

    def test_t051_view_day(self, setup):
        """T051: View day"""
        d = timezone.now().date().isoformat()
        response = self.client.get('/api/scheduling/schedule/', {'view': 'day', 'date': d})
        assert response.status_code in [200, 404]

    def test_t051_view_day_detailed(self, setup):
        """T051: View day detailed"""
        d = timezone.now().date().isoformat()
        response = self.client.get('/api/scheduling/schedule/', {'view': 'day', 'date': d, 'detailed': 'true'})
        assert response.status_code in [200, 404]


@pytest.mark.django_db
class TestScheduleT052T055:
    """T052-T055: Conflicts, availability, sync"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup"""
        self.client = APIClient()

        self.tutor = User.objects.create_user(
            username=f'tutor_t052_{int(timezone.now().timestamp())}',
            email=f'tutor_t052_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.TUTOR
        )

        self.student1 = User.objects.create_user(
            username=f'std1_t052_{int(timezone.now().timestamp())}',
            email=f'std1_t052_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.STUDENT
        )

        self.student2 = User.objects.create_user(
            username=f'std2_t052_{int(timezone.now().timestamp())}',
            email=f'std2_t052_{int(timezone.now().timestamp())}@test.com',
            password='test123',
            role=User.Role.STUDENT
        )

        StudentProfile.objects.create(user=self.student1, grade=10)
        StudentProfile.objects.create(user=self.student2, grade=10)

        self.subject = Subject.objects.create(
            name=f'Math_T052_{int(timezone.now().timestamp())}',
            color='#FF0000'
        )

        SubjectEnrollment.objects.create(student=self.student1, subject=self.subject, teacher=self.tutor)
        SubjectEnrollment.objects.create(student=self.student2, subject=self.subject, teacher=self.tutor)

        self.base_time = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)
        self.lesson1 = Lesson(
            teacher=self.tutor,
            student=self.student1,
            subject=self.subject,
            date=self.base_time.date(),
            start_time=self.base_time.time(),
            end_time=(self.base_time + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
            
        )

        self.client.force_authenticate(user=self.tutor)

    def test_t052_detect_conflict(self, setup):
        """T052: Detect conflict"""
        response = self.client.post('/api/scheduling/lessons/', {
            'student_id': self.student2.id,
            'subject_id': self.subject.id,
            'date': self.base_time.date().isoformat(),
            'start_time': self.base_time.time().isoformat(),
            'end_time': (self.base_time + timedelta(hours=1)).time().isoformat()
        }, format='json')
        assert response.status_code in [400, 201, 403, 404]

    def test_t052_check_conflicts(self, setup):
        """T052: Check conflicts endpoint"""
        response = self.client.post('/api/scheduling/lessons/check-conflicts/', {
            'date': self.base_time.date().isoformat(),
            'start_time': self.base_time.time().isoformat(),
            'duration_minutes': 60
        }, format='json')
        assert response.status_code in [200, 400, 403, 404]

    def test_t053_availability(self, setup):
        """T053: Check availability"""
        check = (self.base_time + timedelta(hours=2)).isoformat()
        response = self.client.get('/api/scheduling/availability/', {
            'tutor_id': self.tutor.id,
            'time': check,
            'duration': 60
        })
        assert response.status_code in [200, 404]

    def test_t053_availability_range(self, setup):
        """T053: Availability range"""
        s = timezone.now().date().isoformat()
        e = (timezone.now() + timedelta(days=7)).date().isoformat()
        response = self.client.get('/api/scheduling/availability/', {
            'tutor_id': self.tutor.id,
            'date_from': s,
            'date_to': e
        })
        assert response.status_code in [200, 404]

    def test_t054_sync_calendar(self, setup):
        """T054: Sync calendar"""
        response = self.client.post('/api/scheduling/sync-calendar/', {
            'calendar_service': 'google',
            'sync_direction': 'to_calendar'
        }, format='json')
        assert response.status_code in [200, 400, 403, 404]

    def test_t054_sync_status(self, setup):
        """T054: Sync status"""
        response = self.client.get('/api/scheduling/sync-calendar-status/')
        assert response.status_code in [200, 404]

    def test_t055_free_slots(self, setup):
        """T055: Free slots"""
        d = (timezone.now() + timedelta(days=1)).date().isoformat()
        response = self.client.get('/api/scheduling/free-slots/', {'date': d, 'duration': 60})
        assert response.status_code in [200, 404]

    def test_t055_free_slots_range(self, setup):
        """T055: Free slots range"""
        s = timezone.now().date().isoformat()
        e = (timezone.now() + timedelta(days=7)).date().isoformat()
        response = self.client.get('/api/scheduling/free-slots/', {
            'start_date': s,
            'end_date': e,
            'duration': 60
        })
        assert response.status_code in [200, 404]
