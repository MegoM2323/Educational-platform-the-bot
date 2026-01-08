"""
Tests for forum contacts availability and chat status.

Tests the AvailableContactsView to ensure:
1. Users see correct contacts based on their role
2. has_active_chat field correctly indicates if chat exists
3. chat_id is populated when chat exists
"""

from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from chat.models import ChatRoom
from materials.models import SubjectEnrollment, Subject
from accounts.models import StudentProfile

User = get_user_model()


class TestAvailableContacts(TestCase):
    """Test suite for AvailableContactsView has_active_chat functionality"""

    def setUp(self):
        """Set up test users, subjects, and enrollments"""
        # Create users with different roles
        self.tutor = User.objects.create_user(
            username="tutor",
            email="tutor@test.com",
            password="test123",
            role="tutor",
            first_name="Tutor",
            last_name="User",
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="test123",
            role="teacher",
            first_name="Teacher",
            last_name="User",
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@test.com",
            password="test123",
            role="student",
            first_name="Student",
            last_name="User",
        )

        # Create student profile with tutor assignment
        self.student_profile = StudentProfile.objects.create(
            user=self.student, tutor=self.tutor
        )

        # Create a subject
        self.subject = Subject.objects.create(name="Mathematics")

        # Create subject enrollment (student-teacher)
        # NOTE: This will trigger signal to create forum chats automatically
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            is_active=True,
        )

        # Initialize API client
        self.client = APIClient()

    def test_tutor_sees_teacher_without_chat(self):
        """Test: Tutor sees teacher in contacts without active chat"""
        # Tutor and teacher are not in any existing chat (no enrollment shared)
        # Delete any existing chats to ensure clean state
        ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR, participants=self.tutor
        ).filter(participants=self.teacher).delete()

        # Authenticate as tutor
        self.client.force_authenticate(user=self.tutor)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data)

        # Find teacher in contacts
        teacher_contact = next(
            (c for c in response.data["results"] if c["id"] == self.teacher.id), None
        )

        # Verify teacher is in contacts without active chat
        self.assertIsNotNone(teacher_contact, "Teacher should be in tutor's contacts")
        self.assertEqual(
            teacher_contact["has_active_chat"],
            False,
            "has_active_chat should be False when no chat exists",
        )
        self.assertIsNone(
            teacher_contact["chat_id"], "chat_id should be None when no chat exists"
        )

    def test_tutor_sees_teacher_with_chat(self):
        """Test: Tutor sees teacher with active chat"""
        # Get existing FORUM_TUTOR chat or verify it exists
        chat = (
            ChatRoom.objects.filter(
                type=ChatRoom.Type.FORUM_TUTOR, participants=self.tutor
            )
            .filter(participants=self.teacher)
            .first()
        )

        # Authenticate as tutor
        self.client.force_authenticate(user=self.tutor)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find teacher in contacts
        teacher_contact = next(
            (c for c in response.data["results"] if c["id"] == self.teacher.id), None
        )

        # Verify teacher has active chat (if chat exists)
        if chat:
            self.assertIsNotNone(
                teacher_contact, "Teacher should be in tutor's contacts"
            )
            self.assertEqual(
                teacher_contact["has_active_chat"],
                True,
                "has_active_chat should be True when chat exists",
            )
            self.assertEqual(
                teacher_contact["chat_id"], chat.id, f"chat_id should be {chat.id}"
            )

    def test_tutor_sees_student_without_chat(self):
        """Test: Tutor sees their student in contacts without active chat"""
        # Delete any existing chats between tutor and student
        ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR, enrollment__student=self.student
        ).filter(participants=self.tutor).delete()

        # Authenticate as tutor
        self.client.force_authenticate(user=self.tutor)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find student in contacts
        student_contact = next(
            (c for c in response.data["results"] if c["id"] == self.student.id), None
        )

        # Verify student is in contacts without active chat
        self.assertIsNotNone(student_contact, "Student should be in tutor's contacts")
        self.assertEqual(
            student_contact["has_active_chat"],
            False,
            "has_active_chat should be False for student without chat",
        )
        self.assertIsNone(
            student_contact["chat_id"],
            "chat_id should be None for student without chat",
        )

    def test_tutor_sees_student_with_chat(self):
        """Test: Tutor sees student with active forum tutor chat"""
        # Get existing FORUM_TUTOR chat between tutor and student
        chat = (
            ChatRoom.objects.filter(
                type=ChatRoom.Type.FORUM_TUTOR, enrollment__student=self.student
            )
            .filter(participants=self.tutor)
            .first()
        )

        # Authenticate as tutor
        self.client.force_authenticate(user=self.tutor)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find student in contacts
        student_contact = next(
            (c for c in response.data["results"] if c["id"] == self.student.id), None
        )

        # Verify student has active chat
        if chat:
            self.assertIsNotNone(
                student_contact, "Student should be in tutor's contacts"
            )
            self.assertEqual(
                student_contact["has_active_chat"],
                True,
                "has_active_chat should be True for student with chat",
            )
            self.assertEqual(
                student_contact["chat_id"], chat.id, f"chat_id should be {chat.id}"
            )

    def test_teacher_sees_student_without_chat(self):
        """Test: Teacher sees student in contacts without active chat"""
        # Delete existing FORUM_SUBJECT chat to test without chat scenario
        ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=self.enrollment
        ).delete()

        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find student in contacts
        student_contact = next(
            (c for c in response.data["results"] if c["id"] == self.student.id), None
        )

        # Verify student is in contacts without active chat
        self.assertIsNotNone(student_contact, "Student should be in teacher's contacts")
        self.assertEqual(
            student_contact["has_active_chat"],
            False,
            "has_active_chat should be False when no forum chat exists",
        )
        self.assertIsNone(
            student_contact["chat_id"],
            "chat_id should be None when no forum chat exists",
        )

    def test_teacher_sees_student_with_chat(self):
        """Test: Teacher sees student with active forum subject chat"""
        # Get or ensure FORUM_SUBJECT chat exists
        chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=self.enrollment
        ).first()

        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find student in contacts
        student_contact = next(
            (c for c in response.data["results"] if c["id"] == self.student.id), None
        )

        # Verify student has active chat
        if chat:
            self.assertIsNotNone(
                student_contact, "Student should be in teacher's contacts"
            )
            self.assertEqual(
                student_contact["has_active_chat"],
                True,
                "has_active_chat should be True when forum chat exists",
            )
            self.assertEqual(
                student_contact["chat_id"], chat.id, f"chat_id should be {chat.id}"
            )

    def test_student_sees_teacher_without_chat(self):
        """Test: Student sees teacher in contacts without active chat"""
        # Delete existing FORUM_SUBJECT chat
        ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=self.enrollment
        ).delete()

        # Authenticate as student
        self.client.force_authenticate(user=self.student)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find teacher in contacts
        teacher_contact = next(
            (c for c in response.data["results"] if c["id"] == self.teacher.id), None
        )

        # Verify teacher is in contacts without active chat
        self.assertIsNotNone(teacher_contact, "Teacher should be in student's contacts")
        self.assertEqual(
            teacher_contact["has_active_chat"],
            False,
            "has_active_chat should be False when no forum chat exists",
        )
        self.assertIsNone(
            teacher_contact["chat_id"],
            "chat_id should be None when no forum chat exists",
        )

    def test_student_sees_teacher_with_chat(self):
        """Test: Student sees teacher with active forum subject chat"""
        # Get or ensure FORUM_SUBJECT chat exists
        chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=self.enrollment
        ).first()

        # Authenticate as student
        self.client.force_authenticate(user=self.student)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find teacher in contacts
        teacher_contact = next(
            (c for c in response.data["results"] if c["id"] == self.teacher.id), None
        )

        # Verify teacher has active chat
        if chat:
            self.assertIsNotNone(
                teacher_contact, "Teacher should be in student's contacts"
            )
            self.assertEqual(
                teacher_contact["has_active_chat"],
                True,
                "has_active_chat should be True when forum chat exists",
            )
            self.assertEqual(
                teacher_contact["chat_id"], chat.id, f"chat_id should be {chat.id}"
            )

    def test_student_sees_tutor_without_chat(self):
        """Test: Student sees assigned tutor in contacts without active chat"""
        # Delete any existing FORUM_TUTOR chats
        ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR, enrollment__student=self.student
        ).filter(participants=self.tutor).delete()

        # Authenticate as student
        self.client.force_authenticate(user=self.student)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find tutor in contacts
        tutor_contact = next(
            (c for c in response.data["results"] if c["id"] == self.tutor.id), None
        )

        # Verify tutor is in contacts without active chat
        self.assertIsNotNone(tutor_contact, "Tutor should be in student's contacts")
        self.assertEqual(
            tutor_contact["has_active_chat"],
            False,
            "has_active_chat should be False when no tutor forum chat exists",
        )
        self.assertIsNone(
            tutor_contact["chat_id"],
            "chat_id should be None when no tutor forum chat exists",
        )

    def test_student_sees_tutor_with_chat(self):
        """Test: Student sees tutor with active forum tutor chat"""
        # Get existing FORUM_TUTOR chat
        chat = (
            ChatRoom.objects.filter(
                type=ChatRoom.Type.FORUM_TUTOR, enrollment__student=self.student
            )
            .filter(participants=self.tutor)
            .first()
        )

        # Authenticate as student
        self.client.force_authenticate(user=self.student)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find tutor in contacts
        tutor_contact = next(
            (c for c in response.data["results"] if c["id"] == self.tutor.id), None
        )

        # Verify tutor has active chat
        if chat:
            self.assertIsNotNone(tutor_contact, "Tutor should be in student's contacts")
            self.assertEqual(
                tutor_contact["has_active_chat"],
                True,
                "has_active_chat should be True when tutor forum chat exists",
            )
            self.assertEqual(
                tutor_contact["chat_id"], chat.id, f"chat_id should be {chat.id}"
            )

    def test_inactive_chat_not_considered_active(self):
        """Test: Inactive chats are not shown as has_active_chat=True"""
        # Get the auto-created FORUM_SUBJECT chat and mark it as inactive
        chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=self.enrollment
        ).first()

        if chat:
            chat.is_active = False
            chat.save()

            # Authenticate as teacher
            self.client.force_authenticate(user=self.teacher)

            # Get available contacts
            response = self.client.get("/api/chat/available-contacts/")

            # Verify response
            self.assertEqual(response.status_code, 200)

            # Find student in contacts
            student_contact = next(
                (c for c in response.data["results"] if c["id"] == self.student.id),
                None,
            )

            # Verify student's inactive chat is not considered active
            self.assertIsNotNone(
                student_contact, "Student should be in teacher's contacts"
            )
            self.assertEqual(
                student_contact["has_active_chat"],
                False,
                "has_active_chat should be False when only inactive chat exists",
            )
            self.assertIsNone(
                student_contact["chat_id"],
                "chat_id should be None when only inactive chat exists",
            )

    def test_contact_fields_are_populated(self):
        """Test: Contact data includes all required fields"""
        # Get the auto-created FORUM_SUBJECT chat
        chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT, enrollment=self.enrollment
        ).first()

        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find student in contacts
        student_contact = next(
            (c for c in response.data["results"] if c["id"] == self.student.id), None
        )

        # Verify all required fields are present
        self.assertIsNotNone(student_contact)
        required_fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "has_active_chat",
            "chat_id",
        ]
        for field in required_fields:
            self.assertIn(
                field, student_contact, f"Field '{field}' should be in contact data"
            )

        # Verify field values
        self.assertEqual(student_contact["id"], self.student.id)
        self.assertEqual(student_contact["email"], self.student.email)
        self.assertEqual(student_contact["first_name"], self.student.first_name)
        self.assertEqual(student_contact["last_name"], self.student.last_name)
        self.assertEqual(student_contact["role"], self.student.role)
        if chat:
            self.assertEqual(student_contact["has_active_chat"], True)
            self.assertEqual(student_contact["chat_id"], chat.id)

    def test_contact_has_extended_fields(self):
        """Test: Contact data includes extended fields for display"""
        # Authenticate as teacher
        self.client.force_authenticate(user=self.teacher)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find student in contacts
        student_contact = next(
            (c for c in response.data["results"] if c["id"] == self.student.id), None
        )

        # Verify extended fields are present
        self.assertIsNotNone(student_contact)
        extended_fields = [
            "user_id",
            "full_name",
            "is_teacher",
            "is_tutor",
            "avatar",
            "avatar_url",
        ]
        for field in extended_fields:
            self.assertIn(
                field,
                student_contact,
                f"Extended field '{field}' should be in contact data",
            )

        # Verify field values for student
        self.assertEqual(student_contact["user_id"], self.student.id)
        self.assertEqual(student_contact["full_name"], self.student.get_full_name())
        self.assertEqual(student_contact["is_teacher"], False)
        self.assertEqual(student_contact["is_tutor"], False)
        self.assertIsNone(student_contact["avatar"])
        self.assertIsNone(student_contact["avatar_url"])

    def test_tutor_contact_fields_are_correct(self):
        """Test: Tutor contacts show correct role fields"""
        # Authenticate as student
        self.client.force_authenticate(user=self.student)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find tutor in contacts
        tutor_contact = next(
            (c for c in response.data["results"] if c["id"] == self.tutor.id), None
        )

        # Verify tutor fields
        self.assertIsNotNone(tutor_contact, "Tutor should be in student's contacts")
        self.assertEqual(tutor_contact["role"], "tutor")
        self.assertEqual(tutor_contact["is_teacher"], False)
        self.assertEqual(tutor_contact["is_tutor"], True)

    def test_teacher_contact_fields_are_correct(self):
        """Test: Teacher contacts show correct role fields"""
        # Authenticate as student
        self.client.force_authenticate(user=self.student)

        # Get available contacts
        response = self.client.get("/api/chat/available-contacts/")

        # Verify response
        self.assertEqual(response.status_code, 200)

        # Find teacher in contacts
        teacher_contact = next(
            (c for c in response.data["results"] if c["id"] == self.teacher.id), None
        )

        # Verify teacher fields
        self.assertIsNotNone(teacher_contact, "Teacher should be in student's contacts")
        self.assertEqual(teacher_contact["role"], "teacher")
        self.assertEqual(teacher_contact["is_teacher"], True)
        self.assertEqual(teacher_contact["is_tutor"], False)
