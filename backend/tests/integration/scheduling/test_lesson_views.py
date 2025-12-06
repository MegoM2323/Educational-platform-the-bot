"""
Integration tests for LessonViewSet API endpoints.

Tests cover:
- POST /api/scheduling/lessons/ - Create lesson
- GET /api/scheduling/lessons/ - List lessons with role-based filtering
- GET /api/scheduling/lessons/{id}/ - Retrieve lesson
- PATCH /api/scheduling/lessons/{id}/ - Update lesson
- DELETE /api/scheduling/lessons/{id}/ - Delete lesson
- GET /api/scheduling/lessons/my_schedule/ - Current user schedule
- GET /api/scheduling/lessons/student_schedule/ - Tutor view of student schedule
- GET /api/scheduling/lessons/upcoming/ - Upcoming lessons
- GET /api/scheduling/lessons/{id}/history/ - Lesson history
"""

import pytest
from datetime import time, timedelta
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from scheduling.models import Lesson, LessonHistory
from accounts.models import StudentProfile


def get_results(response_data):
    """Extract results from paginated or non-paginated response."""
    if isinstance(response_data, dict) and 'results' in response_data:
        return response_data['results']
    return response_data


@pytest.fixture
def api_client():
    """Create API client for testing."""
    return APIClient()


class TestLessonCreateEndpoint:
    """Test POST /api/scheduling/lessons/"""

    def test_teacher_can_create_lesson(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Teacher can create lesson via API."""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=3)
        data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00',
            'description': 'Алгебра',
            'telemost_link': 'https://telemost.yandex.ru/test'
        }

        response = api_client.post('/api/scheduling/lessons/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED
        assert str(response.data['teacher']) == str(teacher_user.id)
        assert str(response.data['student']) == str(student_user.id)
        assert str(response.data['subject']) == str(math_subject.id)

    def test_lesson_creation_creates_history(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Creating lesson via API creates history entry."""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=3)
        data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00'
        }

        response = api_client.post('/api/scheduling/lessons/', data, format='json')

        lesson_id = response.data['id']
        lesson = Lesson.objects.get(id=lesson_id)
        history = LessonHistory.objects.filter(lesson=lesson, action='created')

        assert history.exists()

    def test_student_cannot_create_lesson(self, api_client, student_user, teacher_user, math_subject):
        """Student cannot create lessons."""
        api_client.force_authenticate(user=student_user)

        future_date = timezone.now().date() + timedelta(days=3)
        data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00'
        }

        response = api_client.post('/api/scheduling/lessons/', data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tutor_cannot_create_lesson(self, api_client, tutor_user, student_user, math_subject):
        """Tutor cannot create lessons."""
        api_client.force_authenticate(user=tutor_user)

        future_date = timezone.now().date() + timedelta(days=3)
        data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00'
        }

        response = api_client.post('/api/scheduling/lessons/', data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_unauthenticated_cannot_create(self, api_client, student_user, math_subject):
        """Unauthenticated user cannot create lesson."""
        future_date = timezone.now().date() + timedelta(days=3)
        data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00'
        }

        response = api_client.post('/api/scheduling/lessons/', data, format='json')

        # DRF returns 403 for unauthenticated when IsAuthenticated is used
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_lesson_validation_no_enrollment(self, api_client, teacher_user, another_student_user, math_subject):
        """Cannot create lesson for student without enrollment."""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=3)
        data = {
            'student': str(another_student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00'
        }

        response = api_client.post('/api/scheduling/lessons/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_lesson_validation_past_date(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot create lesson in past."""
        api_client.force_authenticate(user=teacher_user)

        past_date = timezone.now().date() - timedelta(days=1)
        data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(past_date),
            'start_time': '10:00:00',
            'end_time': '11:00:00'
        }

        response = api_client.post('/api/scheduling/lessons/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_lesson_validation_invalid_time(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Cannot create lesson with start_time >= end_time."""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=3)
        data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '11:00:00',
            'end_time': '10:00:00'
        }

        response = api_client.post('/api/scheduling/lessons/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_lesson_with_hh_mm_time_format(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Creating lesson with HH:MM format auto-converts to HH:MM:SS."""
        api_client.force_authenticate(user=teacher_user)

        future_date = timezone.now().date() + timedelta(days=3)
        data = {
            'student': str(student_user.id),
            'subject': str(math_subject.id),
            'date': str(future_date),
            'start_time': '09:00',  # HH:MM format
            'end_time': '10:00',    # HH:MM format
            'description': 'Test lesson with HH:MM format'
        }

        response = api_client.post('/api/scheduling/lessons/', data, format='json')

        assert response.status_code == status.HTTP_201_CREATED

        # Verify lesson was created with correct times
        lesson = Lesson.objects.get(id=response.data['id'])
        assert lesson.start_time == time(9, 0, 0)
        assert lesson.end_time == time(10, 0, 0)


class TestLessonListEndpoint:
    """Test GET /api/scheduling/lessons/"""

    def test_teacher_sees_own_lessons(self, api_client, teacher_user, student_user, math_subject, lesson, another_enrollment):
        """Teacher sees only their own lessons."""
        api_client.force_authenticate(user=teacher_user)

        # Create lesson by different teacher
        from accounts.models import User, TeacherProfile
        from materials.models import SubjectEnrollment
        other_teacher = User.objects.create_user(
            username='other_teacher@test.com',
            email='other_teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )
        TeacherProfile.objects.create(user=other_teacher)

        # Create enrollment for other_teacher
        other_enrollment = SubjectEnrollment.objects.create(
            student=another_enrollment.student,
            teacher=other_teacher,
            subject=another_enrollment.subject,
            is_active=True
        )

        other_lesson = Lesson.objects.create(
            teacher=other_teacher,
            student=another_enrollment.student,
            subject=another_enrollment.subject,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        ids = [l['id'] for l in results]
        assert str(lesson.id) in ids
        assert str(other_lesson.id) not in ids

    def test_student_sees_own_lessons(self, api_client, student_user, teacher_user, math_subject, lesson):
        """Student sees only their own lessons."""
        api_client.force_authenticate(user=student_user)

        # Create lesson for another student
        from accounts.models import User, StudentProfile
        other_student = User.objects.create_user(
            username='other_student@test.com',
            email='other_student@test.com',
            password='TestPass123!',
            role='student'
        )
        StudentProfile.objects.create(user=other_student)

        from materials.models import SubjectEnrollment
        SubjectEnrollment.objects.create(
            student=other_student,
            teacher=teacher_user,
            subject=math_subject,
            is_active=True
        )

        other_lesson = Lesson.objects.create(
            teacher=teacher_user,
            student=other_student,
            subject=math_subject,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )

        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        ids = [l['id'] for l in results]
        assert str(lesson.id) in ids
        assert str(other_lesson.id) not in ids

    def test_tutor_sees_students_lessons(self, api_client, tutor_user, student_user, teacher_user, math_subject, lesson):
        """Tutor sees lessons for their managed students."""
        # Link student to tutor
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)

        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1
        results = get_results(response.data)
        assert str(lesson.id) in [l['id'] for l in results]

    @pytest.mark.django_db
    def test_list_returns_empty_for_no_access(self, api_client):
        """User with no lessons sees empty list."""
        from accounts.models import User, TeacherProfile
        teacher = User.objects.create_user(
            username='lonely_teacher@test.com',
            email='lonely_teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )
        TeacherProfile.objects.create(user=teacher)

        api_client.force_authenticate(user=teacher)

        response = api_client.get('/api/scheduling/lessons/')

        assert response.status_code == status.HTTP_200_OK
        # Paginated response with empty results
        results = get_results(response.data)
        assert results == []


class TestLessonRetrieveEndpoint:
    """Test GET /api/scheduling/lessons/{id}/"""

    def test_teacher_can_retrieve_own_lesson(self, api_client, teacher_user, lesson):
        """Teacher can retrieve their own lesson."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(f'/api/scheduling/lessons/{lesson.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(lesson.id)
        assert str(response.data['teacher']) == str(teacher_user.id)

    def test_student_can_retrieve_own_lesson(self, api_client, student_user, lesson):
        """Student can retrieve their own lesson."""
        api_client.force_authenticate(user=student_user)

        response = api_client.get(f'/api/scheduling/lessons/{lesson.id}/')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == str(lesson.id)

    def test_lesson_not_found(self, api_client, teacher_user):
        """Non-existent lesson returns 404."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/scheduling/lessons/00000000-0000-0000-0000-000000000000/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestLessonUpdateEndpoint:
    """Test PATCH /api/scheduling/lessons/{id}/"""

    def test_teacher_can_update_own_lesson(self, api_client, teacher_user, lesson):
        """Teacher can update their own lesson."""
        api_client.force_authenticate(user=teacher_user)

        data = {'description': 'Updated description'}

        response = api_client.patch(f'/api/scheduling/lessons/{lesson.id}/', data, format='json')

        assert response.status_code == status.HTTP_200_OK
        assert response.data['description'] == 'Updated description'

        lesson.refresh_from_db()
        assert lesson.description == 'Updated description'

    def test_update_creates_history(self, api_client, teacher_user, lesson):
        """Updating lesson via API creates history entry."""
        api_client.force_authenticate(user=teacher_user)

        old_desc = lesson.description
        data = {'description': 'New description'}

        response = api_client.patch(f'/api/scheduling/lessons/{lesson.id}/', data, format='json')

        history = LessonHistory.objects.filter(lesson=lesson, action='updated')
        assert history.exists()

    def test_student_cannot_update_lesson(self, api_client, student_user, lesson):
        """Student cannot update lesson."""
        api_client.force_authenticate(user=student_user)

        data = {'description': 'Hacked'}

        response = api_client.patch(f'/api/scheduling/lessons/{lesson.id}/', data, format='json')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_teacher_cannot_update_other_lesson(self, api_client, lesson):
        """Teacher cannot update lesson they didn't create."""
        from accounts.models import User, TeacherProfile
        other_teacher = User.objects.create_user(
            username='other_teacher@test.com',
            email='other_teacher@test.com',
            password='TestPass123!',
            role='teacher'
        )
        TeacherProfile.objects.create(user=other_teacher)

        api_client.force_authenticate(user=other_teacher)

        data = {'description': 'Hacked'}

        response = api_client.patch(f'/api/scheduling/lessons/{lesson.id}/', data, format='json')

        # Returns 404 because queryset filtering excludes lessons by other teachers
        # This is correct - don't reveal existence of resources user can't access
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_update_past_lesson_fails(self, api_client, teacher_user, subject_enrollment):
        """Cannot update past lesson."""
        # Create past lesson with skip_validation to bypass date check
        past_lesson = Lesson(
            teacher=teacher_user,
            student=subject_enrollment.student,
            subject=subject_enrollment.subject,
            date=timezone.now().date() - timedelta(days=1),
            start_time=time(10, 0),
            end_time=time(11, 0)
        )
        past_lesson.save(skip_validation=True)

        api_client.force_authenticate(user=teacher_user)

        data = {'description': 'New'}

        response = api_client.patch(f'/api/scheduling/lessons/{past_lesson.id}/', data, format='json')

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestLessonDeleteEndpoint:
    """Test DELETE /api/scheduling/lessons/{id}/"""

    def test_teacher_can_delete_own_lesson(self, api_client, teacher_user, lesson):
        """Teacher can delete their own lesson."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        assert response.status_code == status.HTTP_204_NO_CONTENT

        lesson.refresh_from_db()
        assert lesson.status == 'cancelled'

    def test_delete_creates_history(self, api_client, teacher_user, lesson):
        """Deleting lesson via API creates history entry."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        history = LessonHistory.objects.filter(lesson=lesson, action='cancelled')
        assert history.exists()

    def test_student_cannot_delete_lesson(self, api_client, student_user, lesson):
        """Student cannot delete lesson."""
        api_client.force_authenticate(user=student_user)

        response = api_client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_near_future_lesson_fails(self, api_client, teacher_user, near_future_lesson):
        """Cannot delete lesson less than 2 hours away."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.delete(f'/api/scheduling/lessons/{near_future_lesson.id}/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert '2 hour' in response.data.get('error', '').lower()

    def test_delete_non_existent_lesson(self, api_client, teacher_user):
        """Deleting non-existent lesson returns 404."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.delete('/api/scheduling/lessons/00000000-0000-0000-0000-000000000000/')

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestLessonMyScheduleEndpoint:
    """Test GET /api/scheduling/lessons/my_schedule/"""

    def test_teacher_gets_own_schedule(self, api_client, teacher_user, lesson):
        """Teacher can get their schedule."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/scheduling/lessons/my_schedule/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1
        results = get_results(response.data)
        assert str(lesson.id) in [l['id'] for l in results]

    def test_student_gets_own_schedule(self, api_client, student_user, lesson):
        """Student can get their schedule."""
        api_client.force_authenticate(user=student_user)

        response = api_client.get('/api/scheduling/lessons/my_schedule/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert str(lesson.id) in [l['id'] for l in results]

    def test_my_schedule_with_date_filter(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Can filter my-schedule by date."""
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

        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(f'/api/scheduling/lessons/my_schedule/?date_from={date2}')

        results = get_results(response.data)
        ids = [l['id'] for l in results]
        assert str(lesson2.id) in ids
        assert str(lesson1.id) not in ids

    def test_my_schedule_with_subject_filter(self, api_client, teacher_user, student_user, math_subject, english_subject, subject_enrollment, another_enrollment):
        """Can filter my-schedule by subject."""
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

        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(f'/api/scheduling/lessons/my_schedule/?subject_id={math_subject.id}')

        results = get_results(response.data)
        ids = [l['id'] for l in results]
        assert str(lesson1.id) in ids
        assert str(lesson2.id) not in ids


class TestLessonStudentScheduleEndpoint:
    """Test GET /api/scheduling/lessons/student_schedule/"""

    def test_tutor_can_view_student_schedule(self, api_client, tutor_user, student_user, teacher_user, math_subject, lesson):
        """Tutor can view their student's schedule."""
        student_user.student_profile.tutor = tutor_user
        student_user.student_profile.save()

        api_client.force_authenticate(user=tutor_user)

        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1
        results = get_results(response.data)
        assert str(lesson.id) in [l['id'] for l in results]

    def test_teacher_cannot_view_student_schedule(self, api_client, teacher_user, student_user):
        """Teacher cannot view student schedule."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={student_user.id}')

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_schedule_requires_student_id(self, api_client, tutor_user):
        """student_schedule endpoint requires student_id parameter."""
        api_client.force_authenticate(user=tutor_user)

        response = api_client.get('/api/scheduling/lessons/student_schedule/')

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_tutor_cannot_view_unmanaged_student(self, api_client, tutor_user, another_student_user):
        """Tutor cannot view unmanaged student's schedule."""
        api_client.force_authenticate(user=tutor_user)

        response = api_client.get(f'/api/scheduling/lessons/student_schedule/?student_id={another_student_user.id}')

        assert response.status_code == status.HTTP_403_FORBIDDEN


class TestLessonUpcomingEndpoint:
    """Test GET /api/scheduling/lessons/upcoming/"""

    def test_teacher_gets_upcoming_lessons(self, api_client, teacher_user, student_user, math_subject, subject_enrollment):
        """Teacher can get upcoming lessons."""
        future = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        api_client.force_authenticate(user=teacher_user)

        response = api_client.get('/api/scheduling/lessons/upcoming/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        ids = [l['id'] for l in results]
        assert str(future.id) in ids

    def test_student_gets_upcoming_lessons(self, api_client, student_user, teacher_user, math_subject, subject_enrollment):
        """Student can get upcoming lessons."""
        future = Lesson.objects.create(
            teacher=teacher_user,
            student=student_user,
            subject=math_subject,
            date=timezone.now().date() + timedelta(days=2),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status='pending'
        )

        api_client.force_authenticate(user=student_user)

        response = api_client.get('/api/scheduling/lessons/upcoming/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 1


class TestLessonHistoryEndpoint:
    """Test GET /api/scheduling/lessons/{id}/history/"""

    def test_teacher_can_view_history(self, api_client, teacher_user, lesson):
        """Teacher can view lesson history."""
        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(f'/api/scheduling/lessons/{lesson.id}/history/')

        assert response.status_code == status.HTTP_200_OK

    def test_student_can_view_history(self, api_client, student_user, lesson):
        """Student can view their lesson history."""
        api_client.force_authenticate(user=student_user)

        response = api_client.get(f'/api/scheduling/lessons/{lesson.id}/history/')

        assert response.status_code == status.HTTP_200_OK

    def test_history_ordered_by_timestamp(self, api_client, teacher_user, lesson):
        """History entries ordered by timestamp descending."""
        from scheduling.services.lesson_service import LessonService

        # Create initial history entry (simulating lesson creation via service)
        LessonHistory.objects.create(
            lesson=lesson,
            action='created',
            performed_by=teacher_user
        )

        # Update lesson to create second history entry
        LessonService.update_lesson(
            lesson=lesson,
            updates={'description': 'Updated'},
            user=teacher_user
        )

        api_client.force_authenticate(user=teacher_user)

        response = api_client.get(f'/api/scheduling/lessons/{lesson.id}/history/')

        assert response.status_code == status.HTTP_200_OK
        results = get_results(response.data)
        assert len(results) >= 2
        # Most recent should be update (history is ordered by -timestamp)
        assert results[0]['action'] == 'updated'
