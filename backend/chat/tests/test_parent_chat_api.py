import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestParentChatAPI:
    def setup_method(self):
        from accounts.models import StudentProfile, ParentProfile
        from materials.models import Subject, SubjectEnrollment

        self.client = APIClient()
        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="testpass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=self.parent)

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

        # Create child student for parent
        self.student = User.objects.create_user(
            username="student_child",
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=self.student, parent=self.parent)

        # Create enrollment between student and teacher
        subject = Subject.objects.create(name="Test Subject")
        SubjectEnrollment.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=subject,
            status=SubjectEnrollment.Status.ACTIVE,
        )

    def test_get_parent_chat_messages_returns_200(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get("/api/chat/")
        assert response.status_code == 200

    def test_get_parent_chat_messages_requires_auth(self):
        response = self.client.get("/api/chat/")
        assert response.status_code == 401

    def test_get_parent_chat_messages_returns_list(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get("/api/chat/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) or (isinstance(data, dict) and "results" in data)

    def test_create_chat_message_returns_201(self):
        self.client.force_authenticate(user=self.parent)
        payload = {"recipient_id": self.teacher.id, "message": "Hello teacher"}
        response = self.client.post("/api/chat/", data=payload, format="json")
        assert response.status_code == 201

    def test_create_chat_message_requires_auth(self):
        payload = {"recipient_id": self.teacher.id, "message": "Hello teacher"}
        response = self.client.post("/api/chat/", data=payload, format="json")
        assert response.status_code == 401

    def test_create_chat_without_message_returns_201(self):
        """Creating chat without initial message should succeed"""
        self.client.force_authenticate(user=self.parent)
        payload = {"recipient_id": self.teacher.id}
        response = self.client.post("/api/chat/", data=payload, format="json")
        # Chat creation succeeds, message is optional
        assert response.status_code in [200, 201]

    def test_get_parent_chat_filter_by_user(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f"/api/chat/?user_id={self.teacher.id}")
        assert response.status_code == 200

    def test_get_parent_chat_pagination(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get("/api/chat/?page=1&page_size=20")
        assert response.status_code == 200
