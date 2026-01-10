"""Unit tests for student deletion logic (M1)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from datetime import date, time, timedelta
from accounts.models import StudentProfile
from scheduling.models import Lesson
from materials.models import Subject, SubjectEnrollment
from chat.models import ChatRoom, ChatParticipant

User = get_user_model()


class StudentDeletionTests(TestCase):
    """Test StudentProfile deletion cascade logic."""

    def setUp(self):
        """Create test fixtures."""
        self.subject = Subject.objects.create(name="Math")
        self.teacher = User.objects.create(username="teacher_delete", role="teacher")
        self.student = User.objects.create(username="student_delete", role="student")
        self.student_profile = StudentProfile.objects.create(user=self.student)
        self.chat_room = ChatRoom.objects.create(is_active=True)

    def test_delete_student_profile_deletes_enrollments(self):
        """Deleting StudentProfile removes all SubjectEnrollment records."""
        enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            subject=self.subject,
            teacher=self.teacher,
            status="active",
            is_active=True
        )

        enrollment_id = enrollment.id
        self.student_profile.delete()
        self.assertFalse(SubjectEnrollment.objects.filter(id=enrollment_id).exists())

    def test_delete_student_profile_cancels_future_lessons(self):
        """Deleting StudentProfile cancels future lessons (doesn't hard delete)."""
        lesson = Lesson.objects.create(
            teacher=self.teacher,
            student=self.student,
            subject=self.subject,
            date=date.today() + timedelta(days=5),
            start_time=time(10, 0),
            end_time=time(11, 0),
            status="confirmed"
        )

        self.student_profile.delete()
        lesson.refresh_from_db()
        self.assertEqual(lesson.status, "cancelled")

    def test_delete_student_profile_removes_chat_participants(self):
        """Deleting StudentProfile removes ChatParticipant records."""
        participant = ChatParticipant.objects.create(
            room=self.chat_room,
            user=self.student
        )

        participant_id = participant.id
        self.student_profile.delete()
        self.assertFalse(ChatParticipant.objects.filter(id=participant_id).exists())

    def test_delete_student_multiple_enrollments(self):
        """Deleting student with multiple enrollments removes all."""
        for i in range(3):
            SubjectEnrollment.objects.create(
                student=self.student,
                subject=Subject.objects.create(name="Subject{}".format(i)),
                teacher=self.teacher,
                status="active",
                is_active=True
            )

        self.assertEqual(SubjectEnrollment.objects.filter(student=self.student).count(), 3)
        self.student_profile.delete()
        self.assertEqual(SubjectEnrollment.objects.filter(student=self.student).count(), 0)
