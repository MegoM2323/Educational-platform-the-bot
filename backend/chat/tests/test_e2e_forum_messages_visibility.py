"""
E2E Tests: Forum Message Visibility (API-based)
===============================================

Tests that verify Student, Teacher, and Parent can see forum messages
via REST API endpoints.

Scenarios:
1. Student sends message → Teacher can see it via API
2. Teacher sends message → Student can see it via API
3. Parent can see all forum messages via API

These tests can run against production or staging servers.
"""

import pytest
from typing import Optional, Dict, List
import requests
from datetime import datetime


class TestForumMessageVisibilityE2E:
    """E2E tests for forum message visibility across roles"""

    BASE_URL = "https://the-bot.ru"
    API_URL = "https://the-bot.ru/api"

    # Test credentials (should be created on production)
    STUDENT_EMAIL = "student@test.com"
    STUDENT_PASSWORD = "testpass123"

    TEACHER_EMAIL = "teacher@test.com"
    TEACHER_PASSWORD = "testpass123"

    PARENT_EMAIL = "parent@test.com"
    PARENT_PASSWORD = "testpass123"

    @pytest.fixture
    def api_client(self):
        """Create API client for HTTP requests"""
        return requests.Session()

    @pytest.fixture
    def student_token(self, api_client) -> Optional[str]:
        """Get student auth token"""
        response = api_client.post(
            f"{self.API_URL}/accounts/login/",
            json={
                "email": self.STUDENT_EMAIL,
                "password": self.STUDENT_PASSWORD,
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access")
        return None

    @pytest.fixture
    def teacher_token(self, api_client) -> Optional[str]:
        """Get teacher auth token"""
        response = api_client.post(
            f"{self.API_URL}/accounts/login/",
            json={
                "email": self.TEACHER_EMAIL,
                "password": self.TEACHER_PASSWORD,
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access")
        return None

    @pytest.fixture
    def parent_token(self, api_client) -> Optional[str]:
        """Get parent auth token"""
        response = api_client.post(
            f"{self.API_URL}/accounts/login/",
            json={
                "email": self.PARENT_EMAIL,
                "password": self.PARENT_PASSWORD,
            },
            timeout=10,
        )
        if response.status_code == 200:
            return response.json().get("access")
        return None

    def get_student_forum_chat(
        self, api_client: requests.Session, token: str
    ) -> Optional[Dict]:
        """Get the student-teacher forum chat"""
        headers = {"Authorization": f"Bearer {token}"}
        response = api_client.get(
            f"{self.API_URL}/chat/forum/",
            headers=headers,
            timeout=10,
        )

        assert response.status_code == 200, (
            f"Failed to get forum list: {response.status_code} - "
            f"{response.text}"
        )

        forums = response.json()
        if isinstance(forums, dict):
            forums = forums.get("results", [])

        assert len(forums) > 0, "No forum chats found for student"
        return forums[0]

    def test_scenario_1_student_sends_teacher_receives(
        self, api_client: requests.Session, student_token: str, teacher_token: str
    ):
        """
        Scenario 1: Student sends message in forum

        Expected:
        - Student can send message (HTTP 201)
        - Message appears in student's message list
        - Message appears in teacher's message list
        """
        pytest.importorskip("playwright")

        # Skip if tokens not available
        if not student_token or not teacher_token:
            pytest.skip("Student or teacher token not available")

        # Step 1: Get forum chat
        forum = self.get_student_forum_chat(api_client, student_token)
        forum_id = forum.get("id")
        assert forum_id, "Forum ID not found"

        # Step 2: Student sends message
        student_headers = {"Authorization": f"Bearer {student_token}"}
        message_text = f"Test from Student - {datetime.now().isoformat()}"

        send_response = api_client.post(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            json={"text": message_text},
            headers=student_headers,
            timeout=10,
        )

        assert send_response.status_code == 201, (
            f"Failed to send message: {send_response.status_code} - "
            f"{send_response.text}"
        )

        sent_message = send_response.json()
        assert sent_message.get("text") == message_text

        # Step 3: Verify student can see their message
        student_messages_response = api_client.get(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            headers=student_headers,
            timeout=10,
        )

        assert student_messages_response.status_code == 200
        student_messages = student_messages_response.json()

        if isinstance(student_messages, dict):
            student_messages = student_messages.get("results", [])

        assert len(student_messages) > 0, "Student message list is empty"
        assert any(
            m.get("text") == message_text for m in student_messages
        ), "Student message not found in student's message list"

        # Step 4: Verify teacher can see student's message
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        teacher_messages_response = api_client.get(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            headers=teacher_headers,
            timeout=10,
        )

        assert teacher_messages_response.status_code == 200
        teacher_messages = teacher_messages_response.json()

        if isinstance(teacher_messages, dict):
            teacher_messages = teacher_messages.get("results", [])

        assert len(teacher_messages) > 0, "Teacher message list is empty"
        assert any(
            m.get("text") == message_text for m in teacher_messages
        ), "Student message not found in teacher's message list"

    def test_scenario_2_teacher_sends_student_receives(
        self, api_client: requests.Session, student_token: str, teacher_token: str
    ):
        """
        Scenario 2: Teacher sends message in forum

        Expected:
        - Teacher can send message (HTTP 201)
        - Message appears in teacher's message list
        - Message appears in student's message list
        """
        pytest.importorskip("playwright")

        # Skip if tokens not available
        if not student_token or not teacher_token:
            pytest.skip("Student or teacher token not available")

        # Step 1: Get forum chat
        forum = self.get_student_forum_chat(api_client, teacher_token)
        forum_id = forum.get("id")
        assert forum_id, "Forum ID not found"

        # Step 2: Teacher sends message
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        message_text = f"Test from Teacher - {datetime.now().isoformat()}"

        send_response = api_client.post(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            json={"text": message_text},
            headers=teacher_headers,
            timeout=10,
        )

        assert send_response.status_code == 201, (
            f"Failed to send message: {send_response.status_code} - "
            f"{send_response.text}"
        )

        sent_message = send_response.json()
        assert sent_message.get("text") == message_text

        # Step 3: Verify teacher can see their message
        teacher_messages_response = api_client.get(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            headers=teacher_headers,
            timeout=10,
        )

        assert teacher_messages_response.status_code == 200
        teacher_messages = teacher_messages_response.json()

        if isinstance(teacher_messages, dict):
            teacher_messages = teacher_messages.get("results", [])

        assert len(teacher_messages) > 0, "Teacher message list is empty"
        assert any(
            m.get("text") == message_text for m in teacher_messages
        ), "Teacher message not found in teacher's message list"

        # Step 4: Verify student can see teacher's message
        student_headers = {"Authorization": f"Bearer {student_token}"}
        student_messages_response = api_client.get(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            headers=student_headers,
            timeout=10,
        )

        assert student_messages_response.status_code == 200
        student_messages = student_messages_response.json()

        if isinstance(student_messages, dict):
            student_messages = student_messages.get("results", [])

        assert len(student_messages) > 0, "Student message list is empty"
        assert any(
            m.get("text") == message_text for m in student_messages
        ), "Teacher message not found in student's message list"

    def test_scenario_3_parent_sees_forum_and_messages(
        self, api_client: requests.Session, parent_token: str
    ):
        """
        Scenario 3: Parent can see forum list and messages

        Expected:
        - Parent can get forum list (HTTP 200, at least 1 forum)
        - Parent can get messages from forum (HTTP 200, count > 0)
        - Forum chat contains messages
        """
        pytest.importorskip("playwright")

        # Skip if token not available
        if not parent_token:
            pytest.skip("Parent token not available")

        parent_headers = {"Authorization": f"Bearer {parent_token}"}

        # Step 1: Get forum list
        forum_list_response = api_client.get(
            f"{self.API_URL}/chat/forum/",
            headers=parent_headers,
            timeout=10,
        )

        assert forum_list_response.status_code == 200, (
            f"Failed to get forum list: {forum_list_response.status_code} - "
            f"{forum_list_response.text}"
        )

        forum_list = forum_list_response.json()
        if isinstance(forum_list, dict):
            forum_list = forum_list.get("results", [])

        assert len(forum_list) > 0, (
            "Parent has no forums - check parent assignment to student"
        )

        # Step 2: Get messages from first forum
        forum = forum_list[0]
        forum_id = forum.get("id")
        assert forum_id, "Forum ID not found"

        messages_response = api_client.get(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            headers=parent_headers,
            timeout=10,
        )

        assert messages_response.status_code == 200, (
            f"Failed to get messages: {messages_response.status_code} - "
            f"{messages_response.text}"
        )

        messages = messages_response.json()
        if isinstance(messages, dict):
            messages = messages.get("results", [])
            total_count = messages_response.json().get("count", len(messages))
        else:
            total_count = len(messages)

        assert total_count > 0, (
            "Parent message list is empty - messages not visible to parent"
        )

    def test_integration_all_roles_see_messages(
        self,
        api_client: requests.Session,
        student_token: str,
        teacher_token: str,
        parent_token: str,
    ):
        """
        Integration test: All roles (student, teacher, parent) see the same messages

        Expected:
        - All roles can access the same forum
        - All roles see at least one message
        - Message counts should match (or similar)
        """
        pytest.importorskip("playwright")

        # Skip if not all tokens available
        if not all([student_token, teacher_token, parent_token]):
            pytest.skip("Not all user tokens available")

        student_headers = {"Authorization": f"Bearer {student_token}"}
        teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
        parent_headers = {"Authorization": f"Bearer {parent_token}"}

        # Get forum via student
        forum = self.get_student_forum_chat(api_client, student_token)
        forum_id = forum.get("id")

        # Get messages from all roles
        student_messages_response = api_client.get(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            headers=student_headers,
            timeout=10,
        )
        teacher_messages_response = api_client.get(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            headers=teacher_headers,
            timeout=10,
        )
        parent_messages_response = api_client.get(
            f"{self.API_URL}/chat/forum/{forum_id}/messages/",
            headers=parent_headers,
            timeout=10,
        )

        # Verify all got HTTP 200
        assert student_messages_response.status_code == 200
        assert teacher_messages_response.status_code == 200
        assert parent_messages_response.status_code == 200

        # Extract message lists
        student_messages = student_messages_response.json()
        teacher_messages = teacher_messages_response.json()
        parent_messages = parent_messages_response.json()

        # Handle paginated responses
        if isinstance(student_messages, dict):
            student_messages = student_messages.get("results", [])
            student_count = student_messages_response.json().get(
                "count", len(student_messages)
            )
        else:
            student_count = len(student_messages)

        if isinstance(teacher_messages, dict):
            teacher_messages = teacher_messages.get("results", [])
            teacher_count = teacher_messages_response.json().get(
                "count", len(teacher_messages)
            )
        else:
            teacher_count = len(teacher_messages)

        if isinstance(parent_messages, dict):
            parent_messages = parent_messages.get("results", [])
            parent_count = parent_messages_response.json().get(
                "count", len(parent_messages)
            )
        else:
            parent_count = len(parent_messages)

        # Verify all have messages
        assert student_count > 0, "Student has no messages"
        assert teacher_count > 0, "Teacher has no messages"
        assert parent_count > 0, "Parent has no messages"

        # Verify counts are the same or similar (within 1 due to race conditions)
        assert abs(student_count - teacher_count) <= 1, (
            f"Student ({student_count}) and teacher ({teacher_count}) "
            f"see different message counts"
        )
        assert abs(teacher_count - parent_count) <= 1, (
            f"Teacher ({teacher_count}) and parent ({parent_count}) "
            f"see different message counts"
        )
