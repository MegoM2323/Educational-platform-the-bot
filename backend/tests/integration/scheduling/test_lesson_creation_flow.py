"""
Integration tests for Lesson Creation API flow.

Tests cover complete request-response cycle for lesson creation and display:
- POST /api/scheduling/lessons/ - Create lesson
- GET /api/scheduling/lessons/ - List lessons with role-based filtering
- Database state verification after creation
- Lesson visibility for teacher and student
- Validation error handling
- LessonHistory record creation

Запуск:
    pytest backend/tests/integration/scheduling/test_lesson_creation_flow.py -v
"""

import pytest
from datetime import time, timedelta
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from scheduling.models import Lesson, LessonHistory
from materials.models import SubjectEnrollment

pytestmark = [pytest.mark.integration, pytest.mark.django_db]


@pytest.fixture
def api_client():
    """REST API client"""
    return APIClient()


class TestLessonCreationIntegration:
    """Test complete lesson creation workflow"""

    def test_teacher_create_lesson_full_flow(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Complete flow: teacher creates lesson, it appears in both teacher and student lists"""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=5)
        lesson_data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00',
            'description': 'Алгебра - решение уравнений',
            'telemost_link': 'https://telemost.yandex.ru/algebra'
        }

        # Step 1: POST to create lesson
        create_response = api_client.post('/api/scheduling/lessons/', lesson_data, format='json')
        assert create_response.status_code == status.HTTP_201_CREATED
        lesson_id = create_response.data['id']

        # Step 2: Verify lesson in database
        lesson = Lesson.objects.get(id=lesson_id)
        assert lesson.teacher == teacher_user
        assert lesson.student == student_user
        assert lesson.subject == math_subject
        assert str(lesson.date) == str(future_date)

        # Step 3: Verify lesson appears in teacher's lesson list
        api_client.force_authenticate(user=teacher_user)
        list_response = api_client.get('/api/scheduling/lessons/')
        assert list_response.status_code == status.HTTP_200_OK
        lesson_ids = [l['id'] for l in list_response.data]
        assert lesson_id in lesson_ids

        # Step 4: Verify lesson appears in student's lesson list
        api_client.force_authenticate(user=student_user)
        student_list_response = api_client.get('/api/scheduling/lessons/')
        assert student_list_response.status_code == status.HTTP_200_OK
        student_lesson_ids = [l['id'] for l in student_list_response.data]
        assert lesson_id in student_lesson_ids

    def test_lesson_creation_creates_history_record(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Creating lesson creates LessonHistory record"""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=5)
        lesson_data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00',
        }

        response = api_client.post('/api/scheduling/lessons/', lesson_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        lesson_id = response.data['id']
        lesson = Lesson.objects.get(id=lesson_id)

        # Verify history record created
        history = LessonHistory.objects.filter(lesson=lesson, action='created')
        assert history.exists()
        assert history.count() == 1
        assert history.first().created_by == teacher_user

    def test_lesson_response_contains_all_fields(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Lesson creation response contains all expected fields"""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=5)
        lesson_data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00',
            'description': 'Test lesson',
            'telemost_link': 'https://telemost.yandex.ru/test'
        }

        response = api_client.post('/api/scheduling/lessons/', lesson_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED

        lesson_response = response.data
        assert 'id' in lesson_response
        assert lesson_response['teacher'] == teacher_user.id
        assert lesson_response['student'] == student_user.id
        assert lesson_response['subject'] == math_subject.id
        assert lesson_response['description'] == 'Test lesson'
        assert lesson_response['telemost_link'] == 'https://telemost.yandex.ru/test'

    def test_lesson_validation_invalid_student_id(self, api_client, teacher_user, math_subject):
        """Creating lesson with non-existent student returns 400"""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=5)
        lesson_data = {
            'student': '99999',  # Non-existent student
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00',
        }

        response = api_client.post('/api/scheduling/lessons/', lesson_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_lesson_validation_no_enrollment(self, api_client, teacher_user, another_student_user, math_subject):
        """Cannot create lesson for student without SubjectEnrollment"""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=5)
        lesson_data = {
            'student': str(another_student_user.id),  # Not enrolled
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00',
        }

        response = api_client.post('/api/scheduling/lessons/', lesson_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_lesson_validation_past_date(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot create lesson with past date"""
        api_client.force_authenticate(user=teacher_user)

        past_date = timezone.now().date() - timedelta(days=1)
        lesson_data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(past_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00',
        }

        response = api_client.post('/api/scheduling/lessons/', lesson_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_lesson_validation_invalid_time(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot create lesson with start_time >= end_time"""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=5)
        lesson_data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '11:00:00',
            'end_time': '10:00:00',  # end before start
        }

        response = api_client.post('/api/scheduling/lessons/', lesson_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_lesson_validation_same_start_end_time(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot create lesson with start_time == end_time"""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=5)
        lesson_data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '10:00:00',  # same as start
        }

        response = api_client.post('/api/scheduling/lessons/', lesson_data, format='json')
        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLessonListingFiltering:
    """Test lesson list filtering for different roles"""

    def test_teacher_sees_only_their_lessons(self, api_client, teacher_user):
        """Teacher sees only lessons they created"""
        from accounts.models import StudentProfile
        from django.contrib.auth import get_user_model

        User = get_user_model()

        # Create second teacher with their own lessons
        teacher2 = User.objects.create_user(
            username='teacher2',
            email='teacher2@test.com',
            password='TestPass123!',
            role=User.Role.TEACHER
        )
        from accounts.models import TeacherProfile
        TeacherProfile.objects.create(user=teacher2)

        student = User.objects.create_user(
            username='student_test',
            email='student_test@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student)

        # Create enrollments
        from materials.models import Subject
        subject = Subject.objects.create(name='Test Subject')
        enrollment1 = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher_user,
            is_active=True
        )
        enrollment2 = SubjectEnrollment.objects.create(
            student=student,
            subject=subject,
            teacher=teacher2,
            is_active=True
        )

        # Create lessons
        future_date = timezone.now().date() + timedelta(days=5)
        lesson1 = Lesson.objects.create(
            teacher=teacher_user,
            student=student,
            subject=subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )
        lesson2 = Lesson.objects.create(
            teacher=teacher2,
            student=student,
            subject=subject,
            date=future_date,
            start_time=time(14, 0),
            end_time=time(15, 0)
        )

        # Teacher1 lists lessons
        api_client.force_authenticate(user=teacher_user)
        response = api_client.get('/api/scheduling/lessons/')
        assert response.status_code == status.HTTP_200_OK

        lesson_ids = [l['id'] for l in response.data]
        assert lesson1.id in lesson_ids
        assert lesson2.id not in lesson_ids  # Should not see teacher2's lessons

    def test_student_sees_only_their_lessons(self, api_client, student_user, teacher_user, math_subject, subject_enrollment):
        """Student sees only lessons assigned to them"""
        from django.contrib.auth import get_user_model

        User = get_user_model()
        other_student = User.objects.create_user(
            username='other_student',
            email='other@test.com',
            password='TestPass123!',
            role=User.Role.STUDENT
        )
        from accounts.models import StudentProfile
        StudentProfile.objects.create(user=other_student)

        # Create enrollments
        SubjectEnrollment.objects.create(
            student=other_student,
            subject=math_subject,
            teacher=teacher_user,
            is_active=True
        )

        # Create lessons
        future_date = timezone.now().date() + timedelta(days=5)
        lesson1 = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=future_date,
            start_time=time(10, 0),
            end_time=time(11, 0)
        )
        lesson2 = Lesson.objects.create(
            teacher=teacher_user,
            student=other_student,
            subject=math_subject,
            date=future_date,
            start_time=time(14, 0),
            end_time=time(15, 0)
        )

        # Student1 lists lessons
        api_client.force_authenticate(user=student_user)
        response = api_client.get('/api/scheduling/lessons/')
        assert response.status_code == status.HTTP_200_OK

        lesson_ids = [l['id'] for l in response.data]
        assert lesson1.id in lesson_ids
        assert lesson2.id not in lesson_ids  # Should not see other student's lessons
