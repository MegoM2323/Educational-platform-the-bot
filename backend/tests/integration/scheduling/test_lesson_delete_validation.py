"""
Integration tests for lesson deletion validation.

Tests the 2-hour cancellation window rule and status checks.
"""

import pytest
from django.utils import timezone
from datetime import timedelta
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

from scheduling.models import Lesson
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.django_db
class TestLessonDeleteValidation:
    """Test lesson deletion validation rules."""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test data."""
        self.client = APIClient()

        # Create teacher
        self.teacher = User.objects.create_user(
            username='teacher_test',
            email='teacher@test.com',
            password='testpass123',
            role='teacher',
            first_name='Test',
            last_name='Teacher'
        )

        # Create student
        self.student = User.objects.create_user(
            username='student_test',
            email='student@test.com',
            password='testpass123',
            role='student',
            first_name='Test',
            last_name='Student'
        )

        # Create subject
        self.subject = Subject.objects.create(
            name='Mathematics',
            description='Test subject'
        )

        # Create enrollment
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=self.subject,
            is_active=True
        )

    def test_delete_lesson_less_than_2_hours_before_start(self):
        """
        Test DELETE fails when lesson is less than 2 hours away.

        Expected: HTTP 400 with error message about 2-hour rule.
        """
        # Create lesson 1 hour in the future
        now = timezone.now()
        future_time = now + timedelta(hours=1)

        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=future_time.date(),
            start_time=future_time.time(),
            end_time=(future_time + timedelta(hours=1)).time(),
            status='pending'
        )

        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Attempt to delete
        response = self.client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        # Verify failure
        assert response.status_code == 400
        assert 'error' in response.data
        assert '2 hours' in response.data['error']

        # Verify lesson still exists and not cancelled
        lesson.refresh_from_db()
        assert lesson.status == 'pending'

    def test_delete_lesson_more_than_2_hours_before_start(self):
        """
        Test DELETE succeeds when lesson is more than 2 hours away.

        Expected: HTTP 204 No Content, lesson status = 'cancelled'.
        """
        # Create lesson 3 hours in the future
        now = timezone.now()
        future_time = now + timedelta(hours=3)

        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=future_time.date(),
            start_time=future_time.time(),
            end_time=(future_time + timedelta(hours=1)).time(),
            status='pending'
        )

        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Attempt to delete
        response = self.client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        # Verify success
        assert response.status_code == 204

        # Verify lesson marked as cancelled (soft delete)
        lesson.refresh_from_db()
        assert lesson.status == 'cancelled'

    def test_delete_already_cancelled_lesson(self):
        """
        Test DELETE fails when lesson is already cancelled.

        Expected: HTTP 400 with error message.
        """
        # Create lesson far in future but already cancelled
        now = timezone.now()
        future_time = now + timedelta(days=7)

        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=future_time.date(),
            start_time=future_time.time(),
            end_time=(future_time + timedelta(hours=1)).time(),
            status='cancelled'  # Already cancelled
        )

        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Attempt to delete
        response = self.client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        # Verify failure
        assert response.status_code == 400
        assert 'error' in response.data

    def test_delete_completed_lesson(self):
        """
        Test DELETE fails when lesson is completed.

        Expected: HTTP 400 with error message.
        """
        # Create lesson in past with completed status
        now = timezone.now()
        past_time = now - timedelta(days=1)

        # Use skip_validation to bypass past date check
        lesson = Lesson(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=past_time.date(),
            start_time=past_time.time(),
            end_time=(past_time + timedelta(hours=1)).time(),
            status='completed'
        )
        lesson.save(skip_validation=True)

        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Attempt to delete
        response = self.client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        # Verify failure
        assert response.status_code == 400
        assert 'error' in response.data

    def test_delete_lesson_by_non_owner_teacher(self):
        """
        Test DELETE fails when teacher didn't create the lesson.

        Expected: HTTP 403 Forbidden.
        """
        # Create another teacher
        other_teacher = User.objects.create_user(
            username='other_teacher_test',
            email='other_teacher@test.com',
            password='testpass123',
            role='teacher',
            first_name='Other',
            last_name='Teacher'
        )

        # Create lesson by original teacher
        now = timezone.now()
        future_time = now + timedelta(days=1)

        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=future_time.date(),
            start_time=future_time.time(),
            end_time=(future_time + timedelta(hours=1)).time(),
            status='pending'
        )

        # Authenticate as other teacher
        self.client.force_authenticate(user=other_teacher)

        # Attempt to delete
        response = self.client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        # Verify failure (403 from queryset filtering or 404 if not in queryset)
        assert response.status_code in [403, 404]

    def test_delete_lesson_by_student(self):
        """
        Test DELETE fails when student attempts to delete.

        Expected: HTTP 403 or 404 (students can't delete lessons).
        """
        # Create lesson
        now = timezone.now()
        future_time = now + timedelta(days=1)

        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=future_time.date(),
            start_time=future_time.time(),
            end_time=(future_time + timedelta(hours=1)).time(),
            status='pending'
        )

        # Authenticate as student
        self.client.force_authenticate(user=self.student)

        # Attempt to delete
        response = self.client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        # Verify failure
        # ViewSet destroy method checks if teacher matches, returns 403 or 404
        assert response.status_code in [403, 404]

    def test_delete_lesson_exactly_2_hours_before(self):
        """
        Test DELETE fails when lesson is exactly 2 hours away.

        Rule: time_until_lesson > timedelta(hours=2) (strict greater than)
        Expected: HTTP 400.
        """
        # Create lesson exactly 2 hours in the future
        now = timezone.now()
        future_time = now + timedelta(hours=2)

        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=future_time.date(),
            start_time=future_time.time(),
            end_time=(future_time + timedelta(hours=1)).time(),
            status='pending'
        )

        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Attempt to delete
        response = self.client.delete(f'/api/scheduling/lessons/{lesson.id}/')

        # Verify failure (exactly 2 hours = not > 2 hours)
        assert response.status_code == 400
        assert 'error' in response.data
        assert '2 hours' in response.data['error']

    def test_can_cancel_property_validation(self):
        """
        Test the can_cancel property logic directly.

        Documents the exact validation rules.
        """
        now = timezone.now()

        # Case 1: Lesson 1 hour away (can_cancel = False)
        lesson_1hr = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=(now + timedelta(hours=1)).date(),
            start_time=(now + timedelta(hours=1)).time(),
            end_time=(now + timedelta(hours=2)).time(),
            status='pending'
        )
        assert lesson_1hr.can_cancel is False

        # Case 2: Lesson 3 hours away (can_cancel = True)
        lesson_3hr = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=(now + timedelta(hours=3)).date(),
            start_time=(now + timedelta(hours=3)).time(),
            end_time=(now + timedelta(hours=4)).time(),
            status='pending'
        )
        assert lesson_3hr.can_cancel is True

        # Case 3: Cancelled lesson (can_cancel = False regardless of time)
        lesson_cancelled = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=(now + timedelta(days=7)).date(),
            start_time=(now + timedelta(days=7)).time(),
            end_time=(now + timedelta(days=7, hours=1)).time(),
            status='cancelled'
        )
        assert lesson_cancelled.can_cancel is False

        # Case 4: Completed lesson (can_cancel = False)
        # Use skip_validation to bypass past date check
        lesson_completed = Lesson(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=(now - timedelta(days=1)).date(),
            start_time=(now - timedelta(days=1)).time(),
            end_time=(now - timedelta(days=1, hours=-1)).time(),
            status='completed'
        )
        lesson_completed.save(skip_validation=True)
        assert lesson_completed.can_cancel is False
