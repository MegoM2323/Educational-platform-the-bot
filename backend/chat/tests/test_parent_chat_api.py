import pytest
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestParentChatAPI:
    def setup_method(self):
        self.client = APIClient()
        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="testpass123",
            role=User.Role.PARENT,
        )
        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
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

    def test_create_chat_message_requires_message(self):
        self.client.force_authenticate(user=self.parent)
        payload = {"recipient_id": self.teacher.id}
        response = self.client.post("/api/chat/", data=payload, format="json")
        assert response.status_code == 400

    def test_get_parent_chat_filter_by_user(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get(f"/api/chat/?user_id={self.teacher.id}")
        assert response.status_code == 200

    def test_get_parent_chat_pagination(self):
        self.client.force_authenticate(user=self.parent)
        response = self.client.get("/api/chat/?page=1&page_size=20")
        assert response.status_code == 200
