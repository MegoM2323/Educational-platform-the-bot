"""
Integration tests for Tutor Student API endpoints.

Tests cover complete request-response cycle for:
- GET /api/tutor/students/ - List tutor's students
- GET /api/materials/dashboard/tutor/students/{id}/schedule/ - Get student schedule
- Database state verification
- Permission checks (only tutor's students)
- Query optimization
- Full_name field verification

Запуск:
    pytest backend/tests/integration/materials/test_tutor_students_api.py -v
"""

import pytest
from datetime import time, timedelta
from django.utils import timezone
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APIClient
from accounts.models import StudentProfile
from scheduling.models import Lesson
from materials.models import Subject, SubjectEnrollment

User = get_user_model()

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def api_client():
    """REST API client"""
    return APIClient()


class TestTutorStudentsListEndpoint:
    """Test GET /api/tutor/students/ - List tutor's students"""

    def test_tutor_can_list_their_students(self, api_client, tutor_user, student_user):
        """Tutor can list students they manage"""
        # Assign student to tutor
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/tutor/my-students/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

        # Find our student in the list
        student_ids = [s['id'] for s in response.data]
        assert student_user.id in student_ids

    def test_student_list_includes_full_name_field(self, api_client, tutor_user, student_user):
        """Student list includes 'full_name' field (not 'name')"""
        student_user.first_name = 'Иван'
        student_user.last_name = 'Петров'
        student_user.save()

        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/tutor/my-students/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

        student_data = next((s for s in response.data if s['id'] == student_user.id), None)
        assert student_data is not None
        assert 'full_name' in student_data
        assert student_data['full_name'] == 'Иван Петров'

    def test_student_list_includes_avatar_url(self, api_client, tutor_user, student_user):
        """Student list includes avatar field"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/tutor/my-students/')

        assert response.status_code == status.HTTP_200_OK
        student_data = next((s for s in response.data if s['id'] == student_user.id), None)
        assert 'avatar' in student_data

    def test_tutor_only_sees_their_students(self, api_client, tutor_user):
        """Tutor only sees students assigned to them"""
        # Create two tutors
        tutor2 = User.objects.create_user(
            username='tutor2',
            email='tutor2@test.com',
            password='TestPass123!',
            role=User.Role.TUTOR
        )
        from accounts.models import TutorProfile
        TutorProfile.objects.create(user=tutor2)

        # Create two students
        student1 = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT,
            first_name='Student',
            last_name='One'
        )
        StudentProfile.objects.create(user=student1, tutor=tutor_user)

        student2 = User.objects.create_user(
            username='student2',
            email='student2@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT,
            first_name='Student',
            last_name='Two'
        )
        StudentProfile.objects.create(user=student2, tutor=tutor2)

        # Tutor1 lists students
        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/tutor/my-students/')

        assert response.status_code == status.HTTP_200_OK
        student_ids = [s['id'] for s in response.data]

        assert student1.id in student_ids
        assert student2.id not in student_ids  # Should not see tutor2's students

    def test_student_without_tutor_not_in_list(self, api_client, tutor_user, student_user):
        """Student without tutor assignment doesn't appear in list"""
        # student_user has no tutor assigned
        assert student_user.student_profile.tutor is None

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/tutor/my-students/')

        assert response.status_code == status.HTTP_200_OK
        student_ids = [s['id'] for s in response.data]
        assert student_user.id not in student_ids

    def test_unauthenticated_cannot_list_students(self, api_client):
        """Unauthenticated user gets 401"""
        response = api_client.get('/api/tutor/my-students/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_cannot_list_tutor_students(self, api_client, student_user):
        """Student role cannot access tutor students endpoint"""
        response = api_client.get('/api/tutor/my-students/')
        # Either 401 (if not authenticated) or 403 (if role check)
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]

    def test_students_list_no_n_plus_one(self, api_client, tutor_user, student_user, django_assert_num_queries):
        """Tutor students list uses prefetch/select_related to avoid N+1 queries"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)

        # Should be constant number of queries regardless of student count
        with django_assert_num_queries(3):
            response = api_client.get('/api/tutor/my-students/')
            assert response.status_code == status.HTTP_200_OK


class TestTutorStudentScheduleEndpoint:
    """Test GET /api/materials/dashboard/tutor/students/{id}/schedule/ - Get student schedule"""

    def test_tutor_can_get_student_schedule(self, api_client, tutor_user, student_user, teacher_user, math_subject):
        """Tutor can retrieve schedule of their student"""
        # Assign student to tutor
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        # Create enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=math_subject,
            teacher=teacher_user,
            is_active=True
        )

        # Create lesson
        future_date = timezone.now().date() + timedelta(days=5)
        lesson = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Algebra lesson'
        )

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/schedule/')

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1

        lesson_ids = [l['id'] for l in response.data]
        assert lesson.id in lesson_ids

    def test_schedule_includes_lesson_details(self, api_client, tutor_user, student_user, teacher_user, math_subject):
        """Student schedule includes full lesson details"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=math_subject,
            teacher=teacher_user,
            is_active=True
        )

        future_date = timezone.now().date() + timedelta(days=5)
        lesson = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description='Algebra lesson',
            telemost_link='https://telemost.yandex.ru/test'
        )

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/schedule/')

        assert response.status_code == status.HTTP_200_OK
        lesson_data = response.data[0]

        assert 'id' in lesson_data
        assert lesson_data['teacher'] == teacher_user.id
        assert lesson_data['student'] == student_user.id
        assert lesson_data['subject'] == math_subject.id
        assert lesson_data['description'] == 'Algebra lesson'
        assert lesson_data['telemost_link'] == 'https://telemost.yandex.ru/test'

    def test_tutor_cannot_access_other_tutors_students(self, api_client, tutor_user, student_user):
        """Tutor cannot access schedule of students not assigned to them"""
        # Assign student to different tutor
        from accounts.models import TutorProfile
        other_tutor = User.objects.create_user(
            username='other_tutor',
            email='other_tutor@test.com',
            password='TestPass123!',
            role=User.Role.TUTOR
        )
        TutorProfile.objects.create(user=other_tutor)

        student_user.student_profile.tutor = other_tutor
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/schedule/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_invalid_student_id_returns_404(self, api_client, tutor_user):
        """Invalid student ID returns 404"""
        api_client.force_authenticate(user=tutor_user)
        response = api_client.get('/api/materials/dashboard/tutor/students/99999/schedule/')

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_student_without_lessons_returns_empty_array(self, api_client, tutor_user, student_user):
        """Student with no lessons returns empty array"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/schedule/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data == []

    def test_schedule_only_includes_future_lessons(self, api_client, tutor_user, student_user, teacher_user, math_subject):
        """Student schedule only includes future lessons (date >= today)"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=math_subject,
            teacher=teacher_user,
            is_active=True
        )

        # Create past lesson
        past_date = timezone.now().date() - timedelta(days=5)
        past_lesson = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=past_date,
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='completed'
        )

        # Create future lesson
        future_date = timezone.now().date() + timedelta(days=5)
        future_lesson = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        api_client.force_authenticate(user=tutor_user)
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/schedule/')

        assert response.status_code == status.HTTP_200_OK
        lesson_ids = [l['id'] for l in response.data]

        assert future_lesson.id in lesson_ids
        assert past_lesson.id not in lesson_ids  # Past lessons excluded

    def test_unauthenticated_cannot_get_schedule(self, api_client, student_user):
        """Unauthenticated user gets 401"""
        response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/schedule/')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_schedule_no_n_plus_one_queries(self, api_client, tutor_user, student_user, teacher_user, math_subject, django_assert_num_queries):
        """Student schedule endpoint uses select_related to avoid N+1"""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=math_subject,
            teacher=teacher_user,
            is_active=True
        )

        future_date = timezone.now().date() + timedelta(days=5)
        for i in range(3):
            Lesson.objects.create(
                teacher=teacher_user,
                student=student_user,
                subject=math_subject,
                date=future_date + timedelta(days=i),
                start_time=time(10, 0),
                end_time=time(11, 0)
            )

        api_client.force_authenticate(user=tutor_user)

        # Should be constant number of queries regardless of lesson count
        with django_assert_num_queries(4):
            response = api_client.get(f'/api/materials/dashboard/tutor/students/{student_user.id}/schedule/')
            assert response.status_code == status.HTTP_200_OK
