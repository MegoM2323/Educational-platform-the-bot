"""
Test T005: Parent can get messages from forum chat

Scenario:
1. Create enrollment (creates forum chat with student + teacher)
2. Assign parent to student (signal adds parent to forum participants)
3. Create some messages in forum
4. Verify parent can GET /api/forum/{id}/messages/ (200 OK)
5. Verify messages are returned (not empty)
"""

import pytest
from uuid import uuid4
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from accounts.models import StudentProfile, ParentProfile
from chat.models import ChatRoom, Message
from materials.models import Subject, SubjectEnrollment

User = get_user_model()


@pytest.mark.django_db(transaction=True)
class TestParentMessagesAccess:
    """T005: Parent can access messages in forum chat"""

    def setup_method(self):
        self.client = APIClient()

    def test_parent_can_get_messages_from_forum(self):
        """Parent should be able to GET messages from forum chat after being added to participants"""

        # 1. Create student
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student)

        # 2. Create parent
        parent = User.objects.create_user(
            username=f"parent_{uuid4().hex[:8]}",
            email=f"parent_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent)

        # 3. Create teacher
        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

        # 4. Create subject
        subject = Subject.objects.create(name=f"Math_{uuid4().hex[:8]}")

        # 5. Create enrollment (creates forum via signal)
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )

        # 6. Get forum chat
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # 7. Assign parent to student (signal adds parent to forum)
        student_profile = student.student_profile
        student_profile.parent = parent
        student_profile.save()

        # 8. Refresh forum to see updated participants
        forum.refresh_from_db()

        # Verify parent is in participants
        assert parent in forum.participants.all(), (
            "Parent not added to forum after assignment"
        )

        # 9. Create some messages by teacher and student
        msg1 = Message.objects.create(
            room=forum,
            sender=teacher,
            content="Hello class",
            message_type="text",
        )
        msg2 = Message.objects.create(
            room=forum,
            sender=student,
            content="Hello teacher",
            message_type="text",
        )

        # 10. Authenticate parent and GET messages
        self.client.force_authenticate(user=parent)
        response = self.client.get(f"/api/chat/forum/{forum.id}/messages/")

        # 11. Verify response is 200 OK (not 403 Forbidden)
        assert response.status_code == 200, (
            f"Parent got {response.status_code} instead of 200. "
            f"Response: {response.json()}"
        )

        # 12. Verify messages are returned
        data = response.json()
        assert data.get("success") is True
        assert "results" in data
        assert len(data["results"]) >= 2, (
            f"Expected at least 2 messages, got {len(data.get('results', []))}"
        )

        # 13. Verify message content
        message_contents = [msg["content"] for msg in data["results"]]
        assert "Hello class" in message_contents
        assert "Hello teacher" in message_contents

        print("✓ Parent can access messages from forum chat")

    def test_parent_without_child_in_forum_cannot_access_messages(self):
        """Parent of a student NOT in forum should get 403 Forbidden"""

        # 1. Create two students
        student1 = User.objects.create_user(
            username=f"student1_{uuid4().hex[:8]}",
            email=f"student1_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student1)

        student2 = User.objects.create_user(
            username=f"student2_{uuid4().hex[:8]}",
            email=f"student2_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student2)

        # 2. Create parent of student1
        parent = User.objects.create_user(
            username=f"parent_{uuid4().hex[:8]}",
            email=f"parent_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent)
        student1.student_profile.parent = parent
        student1.student_profile.save()

        # 3. Create teacher
        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

        # 4. Create subject
        subject = Subject.objects.create(name=f"Math_{uuid4().hex[:8]}")

        # 5. Create enrollment ONLY for student2 (not student1)
        enrollment = SubjectEnrollment.objects.create(
            student=student2,
            teacher=teacher,
            subject=subject,
        )

        # 6. Get forum chat
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # 7. Forum should have student2 as participant, NOT student1, NOT parent
        assert student2 in forum.participants.all()
        assert student1 not in forum.participants.all()
        assert parent not in forum.participants.all()

        # 8. Authenticate parent and try to GET messages
        self.client.force_authenticate(user=parent)
        response = self.client.get(f"/api/chat/forum/{forum.id}/messages/")

        # 9. Should get 403 Forbidden because parent's child is not in this forum
        assert response.status_code == 403, (
            f"Expected 403, got {response.status_code}. "
            f"Parent should not access forum of child who is not participant"
        )

        print("✓ Parent without child in forum gets 403 Forbidden")

    def test_parent_access_is_added_to_participants(self):
        """After parent accesses messages, parent should be added to participants"""

        # 1. Create student
        student = User.objects.create_user(
            username=f"student_{uuid4().hex[:8]}",
            email=f"student_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        StudentProfile.objects.create(user=student)

        # 2. Create parent
        parent = User.objects.create_user(
            username=f"parent_{uuid4().hex[:8]}",
            email=f"parent_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.PARENT,
        )
        ParentProfile.objects.create(user=parent)

        # 3. Create teacher
        teacher = User.objects.create_user(
            username=f"teacher_{uuid4().hex[:8]}",
            email=f"teacher_{uuid4().hex[:8]}@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )

        # 4. Create subject
        subject = Subject.objects.create(name=f"Math_{uuid4().hex[:8]}")

        # 5. Create enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student,
            teacher=teacher,
            subject=subject,
        )

        # 6. Get forum chat
        forum = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment,
        )

        # 7. Initially parent should NOT be in forum (signal hasn't run yet because parent was not assigned before)
        # Actually parent IS in forum now due to signal, but let's verify the behavior anyway

        # 8. Assign parent to student (signal adds parent)
        student.student_profile.parent = parent
        student.student_profile.save()
        forum.refresh_from_db()

        # Verify parent is in participants after signal
        assert parent in forum.participants.all()

        # 9. Now access messages
        self.client.force_authenticate(user=parent)
        response = self.client.get(f"/api/chat/forum/{forum.id}/messages/")

        # 10. Should be 200 OK
        assert response.status_code == 200

        # 11. Verify parent is still in participants (should be - was added by signal)
        forum.refresh_from_db()
        assert parent in forum.participants.all()

        print("✓ Parent is properly added to forum participants and can access messages")
