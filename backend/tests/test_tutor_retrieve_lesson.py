"""
Test Tutor access to GET /api/scheduling/lessons/{id}/
Ensures tutors can retrieve only their students' lessons
"""

import pytest
from datetime import timedelta
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status

from scheduling.models import Lesson
from materials.models import Subject, SubjectEnrollment
from accounts.models import StudentProfile

User = get_user_model()


@pytest.mark.django_db
class TestTutorRetrieveLesson:
    """Test Tutor access to retrieve() endpoint"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Setup test data with two tutors and students"""
        self.client = APIClient()

        # Tutor 1 with Student 1
        self.tutor1 = User.objects.create_user(
            username="tutor1_retrieve_test",
            email="tutor1_retrieve@test.com",
            password="test123",
            role=User.Role.TUTOR,
        )

        self.student1 = User.objects.create_user(
            username="student1_retrieve_test",
            email="student1_retrieve@test.com",
            password="test123",
            role=User.Role.STUDENT,
        )

        StudentProfile.objects.create(user=self.student1, tutor=self.tutor1, grade=10)

        # Tutor 2 with Student 2
        self.tutor2 = User.objects.create_user(
            username="tutor2_retrieve_test",
            email="tutor2_retrieve@test.com",
            password="test123",
            role=User.Role.TUTOR,
        )

        self.student2 = User.objects.create_user(
            username="student2_retrieve_test",
            email="student2_retrieve@test.com",
            password="test123",
            role=User.Role.STUDENT,
        )

        StudentProfile.objects.create(user=self.student2, tutor=self.tutor2, grade=11)

        # Create subject
        self.subject = Subject.objects.create(
            name="Math_Retrieve_Test",
            description="Test",
            color="#FF0000",
        )

        SubjectEnrollment.objects.create(
            student=self.student1, subject=self.subject, teacher=self.tutor1
        )
        SubjectEnrollment.objects.create(
            student=self.student2, subject=self.subject, teacher=self.tutor2
        )

        # Create lessons
        future = (timezone.now() + timedelta(days=1)).replace(hour=10, minute=0)

        self.lesson1 = Lesson.objects.create(
            teacher=self.tutor1,
            student=self.student1,
            subject=self.subject,
            date=future.date(),
            start_time=future.time(),
            end_time=(future + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
        )

        self.lesson2 = Lesson.objects.create(
            teacher=self.tutor2,
            student=self.student2,
            subject=self.subject,
            date=future.date(),
            start_time=future.time(),
            end_time=(future + timedelta(hours=1)).time(),
            status=Lesson.Status.CONFIRMED,
        )

    def test_tutor_can_retrieve_own_lesson(self):
        """Tutor 1 can GET /api/scheduling/lessons/{id}/ for their student's lesson"""
        self.client.force_authenticate(user=self.tutor1)

        response = self.client.get(f"/api/scheduling/lessons/{self.lesson1.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(self.lesson1.id)
        assert response.data["student"] == self.student1.id
        assert response.data["teacher"] == self.tutor1.id

    def test_tutor_cannot_retrieve_other_tutor_lesson(self):
        """Tutor 1 gets 404 for Tutor 2's student's lesson"""
        self.client.force_authenticate(user=self.tutor1)

        response = self.client.get(f"/api/scheduling/lessons/{self.lesson2.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_tutor_cannot_retrieve_nonexistent_lesson(self):
        """Tutor 1 gets 404 for nonexistent lesson"""
        self.client.force_authenticate(user=self.tutor1)

        # UUID that doesn't exist
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = self.client.get(f"/api/scheduling/lessons/{fake_id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_unauthenticated_cannot_retrieve_lesson(self):
        """Unauthenticated user gets 401"""
        response = self.client.get(f"/api/scheduling/lessons/{self.lesson1.id}/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_student_can_retrieve_own_lesson(self):
        """Student can GET their own lesson"""
        self.client.force_authenticate(user=self.student1)

        response = self.client.get(f"/api/scheduling/lessons/{self.lesson1.id}/")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == str(self.lesson1.id)

    def test_student_cannot_retrieve_other_student_lesson(self):
        """Student 1 gets 404 for Student 2's lesson"""
        self.client.force_authenticate(user=self.student1)

        response = self.client.get(f"/api/scheduling/lessons/{self.lesson2.id}/")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_lesson_data_includes_required_fields(self):
        """Retrieved lesson includes all required fields"""
        self.client.force_authenticate(user=self.tutor1)

        response = self.client.get(f"/api/scheduling/lessons/{self.lesson1.id}/")

        assert response.status_code == status.HTTP_200_OK
        data = response.data

        assert "id" in data
        assert "teacher" in data
        assert "student" in data
        assert "subject" in data
        assert "date" in data
        assert "start_time" in data
        assert "end_time" in data
        assert "status" in data
