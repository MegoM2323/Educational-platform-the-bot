"""
Unit tests for forum chat auto-creation signal on SubjectEnrollment.

Tests automatic forum chat creation when SubjectEnrollment is created,
including both FORUM_SUBJECT (student-teacher) and FORUM_TUTOR (student-tutor) chats.
"""

import pytest
from django.contrib.auth import get_user_model

from chat.models import ChatRoom
from materials.models import SubjectEnrollment, Subject
from accounts.models import StudentProfile

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestForumChatSignalCreation:
    """Tests for automatic forum chat creation signal"""

    def test_signal_creates_forum_chat_on_enrollment(self, student_user, teacher_user, subject):
        """Test that SubjectEnrollment creation triggers chat creation"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Check that FORUM_SUBJECT chat was created
        forum_chats = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        assert forum_chats.exists()
        assert forum_chats.count() == 1

    def test_signal_creates_forum_subject_chat_with_correct_name(
        self, student_user, teacher_user, subject
    ):
        """Test forum chat name format: {Subject} - {Student} ↔ {Teacher}"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        expected_name = f"{subject.name} - {student_user.get_full_name()} ↔ {teacher_user.get_full_name()}"
        assert chat.name == expected_name

    def test_signal_adds_student_and_teacher_as_participants(
        self, student_user, teacher_user, subject
    ):
        """Test that signal adds both student and teacher to chat participants"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        assert chat.participants.count() == 2
        assert student_user in chat.participants.all()
        assert teacher_user in chat.participants.all()

    def test_signal_creates_tutor_chat_if_student_has_tutor(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that FORUM_TUTOR chat is created if student has tutor assigned"""
        # Assign tutor to student
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Create enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Check that FORUM_TUTOR chat was created
        tutor_chats = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )

        assert tutor_chats.exists()
        assert tutor_chats.count() == 1

    def test_tutor_chat_has_correct_name(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test tutor chat name format"""
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )

        expected_name = f"{subject.name} - {student_user.get_full_name()} ↔ {tutor_user.get_full_name()}"
        assert chat.name == expected_name

    def test_tutor_chat_has_student_and_tutor_participants(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test tutor chat has student and tutor as participants"""
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )

        assert chat.participants.count() == 2
        assert student_user in chat.participants.all()
        assert tutor_user in chat.participants.all()

    def test_no_tutor_chat_created_if_no_tutor(self, student_user, teacher_user, subject):
        """Test that FORUM_TUTOR chat is NOT created if student has no tutor"""
        # Ensure student has no tutor
        student_profile = student_user.student_profile
        student_profile.tutor = None
        student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Should have only FORUM_SUBJECT chat, not FORUM_TUTOR
        forum_chats = ChatRoom.objects.filter(enrollment=enrollment)
        assert forum_chats.count() == 1
        assert forum_chats.first().type == ChatRoom.Type.FORUM_SUBJECT

    def test_signal_idempotent_no_duplicate_chats(self, student_user, teacher_user, subject):
        """Test signal is idempotent - re-saving enrollment doesn't create duplicate chats"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        initial_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).count()
        assert initial_count == 1

        # Re-save enrollment (trigger post_save signal again)
        enrollment.save()

        final_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).count()
        assert final_count == 1  # Should still be 1, not 2

    def test_signal_sets_created_by_to_student(self, student_user, teacher_user, subject):
        """Test that forum chat created_by is set to the student"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        assert chat.created_by == student_user

    def test_signal_links_chat_to_enrollment(self, student_user, teacher_user, subject):
        """Test that created chat is linked to the enrollment"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        assert chat.enrollment == enrollment
        assert chat.enrollment.student == student_user
        assert chat.enrollment.teacher == teacher_user

    def test_signal_works_with_custom_subject_name(
        self, student_user, teacher_user, subject
    ):
        """Test signal works when enrollment has custom_subject_name"""
        custom_name = "Custom Subject Name"
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            custom_subject_name=custom_name
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        # Should use custom name
        assert custom_name in chat.name

    def test_signal_handles_missing_student_profile(self, student_user, teacher_user, subject):
        """Test signal handles gracefully if StudentProfile is missing"""
        # Delete student profile
        student_user.student_profile.delete()

        # This should not crash the signal
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # FORUM_SUBJECT chat should still be created
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).exists()

        # But no FORUM_TUTOR chat
        assert not ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        ).exists()

    def test_signal_only_fires_on_creation_not_update(
        self, student_user, teacher_user, subject
    ):
        """Test signal only fires when created=True, not on subsequent updates"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        initial_chat_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).count()
        assert initial_chat_count == 1

        # Update enrollment without changing critical fields
        enrollment.is_active = False
        enrollment.save()

        # Should still have only 1 chat
        final_chat_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).count()
        assert final_chat_count == 1

    def test_signal_creates_both_chat_types_for_student_with_tutor(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that both FORUM_SUBJECT and FORUM_TUTOR chats are created"""
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        all_chats = ChatRoom.objects.filter(enrollment=enrollment)
        assert all_chats.count() == 2

        types = [chat.type for chat in all_chats]
        assert ChatRoom.Type.FORUM_SUBJECT in types
        assert ChatRoom.Type.FORUM_TUTOR in types

    def test_signal_chat_descriptions_are_set(self, student_user, teacher_user, subject):
        """Test that forum chats have descriptions set"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        assert chat.description is not None
        assert len(chat.description) > 0
        assert subject.name in chat.description

    def test_signal_chat_is_active_by_default(self, student_user, teacher_user, subject):
        """Test that created chats are active by default"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        )

        assert chat.is_active is True


@pytest.mark.unit
@pytest.mark.django_db
class TestForumSignalEdgeCases:
    """Tests for edge cases and error handling in forum signals"""

    def test_multiple_enrollments_create_separate_chats(
        self, student_user, teacher_user, subject
    ):
        """Test that multiple enrollments for same student in different subjects create separate chats"""
        subject2 = Subject.objects.create(name="English")

        enrollment1 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        enrollment2 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject2,
            teacher=teacher_user
        )

        chat1 = ChatRoom.objects.get(enrollment=enrollment1)
        chat2 = ChatRoom.objects.get(enrollment=enrollment2)

        assert chat1.id != chat2.id
        assert chat1.name != chat2.name

    def test_same_student_teacher_different_subjects(
        self, student_user, teacher_user
    ):
        """Test multiple enrollments of same student with same teacher in different subjects"""
        subject1 = Subject.objects.create(name="Math")
        subject2 = Subject.objects.create(name="Physics")

        enrollment1 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject1,
            teacher=teacher_user
        )

        enrollment2 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject2,
            teacher=teacher_user
        )

        # Both should have separate chats
        assert ChatRoom.objects.filter(enrollment=enrollment1).exists()
        assert ChatRoom.objects.filter(enrollment=enrollment2).exists()

        # Chats should be different
        chat1 = ChatRoom.objects.get(enrollment=enrollment1)
        chat2 = ChatRoom.objects.get(enrollment=enrollment2)
        assert chat1.id != chat2.id
