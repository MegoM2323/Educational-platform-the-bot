"""
Unit tests for FORUM_TUTOR chat auto-creation when tutor is assigned to student.

Tests automatic FORUM_TUTOR chat creation when StudentProfile.tutor is assigned,
covering cases where enrollments already exist before tutor assignment.
"""

import pytest
from django.contrib.auth import get_user_model

from chat.models import ChatRoom
from materials.models import SubjectEnrollment, Subject
from accounts.models import StudentProfile

User = get_user_model()


@pytest.mark.unit
@pytest.mark.django_db
class TestTutorAssignmentSignal:
    """Tests for automatic FORUM_TUTOR chat creation on tutor assignment"""

    def test_signal_creates_tutor_chats_for_existing_enrollments(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that assigning tutor creates FORUM_TUTOR chats for existing enrollments"""
        # Create enrollments BEFORE assigning tutor
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Verify only FORUM_SUBJECT chat exists initially
        initial_chats = ChatRoom.objects.filter(enrollment=enrollment)
        assert initial_chats.count() == 1
        assert initial_chats.first().type == ChatRoom.Type.FORUM_SUBJECT

        # Now assign tutor - signal should create FORUM_TUTOR chat
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify FORUM_TUTOR chat was created
        tutor_chats = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )
        assert tutor_chats.exists()
        assert tutor_chats.count() == 1

    def test_signal_creates_tutor_chats_for_multiple_enrollments(
        self, student_user, teacher_user, tutor_user
    ):
        """Test that signal creates FORUM_TUTOR chats for ALL existing enrollments"""
        # Create multiple subjects and enrollments
        subject1 = Subject.objects.create(name="Math")
        subject2 = Subject.objects.create(name="Physics")
        subject3 = Subject.objects.create(name="Chemistry")

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
        enrollment3 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject3,
            teacher=teacher_user
        )

        # Verify only FORUM_SUBJECT chats exist
        assert ChatRoom.objects.filter(type=ChatRoom.Type.FORUM_TUTOR).count() == 0

        # Assign tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify FORUM_TUTOR chats created for all enrollments
        tutor_chats = ChatRoom.objects.filter(type=ChatRoom.Type.FORUM_TUTOR)
        assert tutor_chats.count() == 3

        # Verify each enrollment has a FORUM_TUTOR chat
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment1
        ).exists()
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment2
        ).exists()
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment3
        ).exists()

    def test_signal_idempotent_no_duplicate_chats(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that signal is idempotent - doesn't create duplicates on re-save"""
        # Create enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Assign tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify chat was created
        initial_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        ).count()
        assert initial_count == 1

        # Re-save profile (shouldn't create duplicate)
        student_profile.save()

        # Verify still only 1 chat
        final_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        ).count()
        assert final_count == 1

    def test_signal_has_correct_chat_name_format(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that created chat has correct name format: {Subject} - {Student} ↔ {Tutor}"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Assign tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Check chat name
        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )

        expected_name = f"{subject.name} - {student_user.get_full_name()} ↔ {tutor_user.get_full_name()}"
        assert chat.name == expected_name

    def test_signal_adds_student_and_tutor_as_participants(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that signal adds student and tutor as chat participants"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Assign tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify participants
        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )

        assert chat.participants.count() == 2
        assert student_user in chat.participants.all()
        assert tutor_user in chat.participants.all()
        assert teacher_user not in chat.participants.all()  # Teacher should NOT be participant

    def test_signal_does_not_fire_when_tutor_is_none(
        self, student_user, teacher_user, subject
    ):
        """Test that signal doesn't fire when tutor is not assigned"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Update profile without setting tutor
        student_profile = student_user.student_profile
        student_profile.grade = "10"
        student_profile.save()

        # Verify no FORUM_TUTOR chat created
        tutor_chats = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )
        assert not tutor_chats.exists()

    def test_signal_does_not_fire_when_other_fields_updated(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that signal doesn't fire when tutor field is not in update_fields"""
        # First assign tutor and create enrollment
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # At this point, we have 2 FORUM_TUTOR chats from:
        # 1. Enrollment signal (when enrollment was created, tutor already assigned)
        initial_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        ).count()

        # Update only grade field (not tutor)
        student_profile.grade = "11"
        student_profile.save(update_fields=['grade'])

        # Count should remain the same (no new chats)
        final_count = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        ).count()
        assert final_count == initial_count

    def test_signal_only_creates_chats_for_active_enrollments(
        self, student_user, teacher_user, tutor_user
    ):
        """Test that signal only creates chats for active enrollments"""
        subject1 = Subject.objects.create(name="Math")
        subject2 = Subject.objects.create(name="Physics")

        # Create one active and one inactive enrollment
        active_enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject1,
            teacher=teacher_user,
            is_active=True
        )
        inactive_enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject2,
            teacher=teacher_user,
            is_active=False
        )

        # Assign tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify chat created only for active enrollment
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=active_enrollment
        ).exists()
        assert not ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=inactive_enrollment
        ).exists()

    def test_signal_works_with_custom_subject_name(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test signal works when enrollment has custom_subject_name"""
        custom_name = "Advanced Calculus"
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user,
            custom_subject_name=custom_name
        )

        # Assign tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify chat name uses custom subject name
        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )
        assert custom_name in chat.name

    def test_signal_sets_created_by_to_student(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that created chat has created_by set to student"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Assign tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify created_by
        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )
        assert chat.created_by == student_user

    def test_signal_sets_description(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that created chat has description set"""
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Assign tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify description
        chat = ChatRoom.objects.get(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        )
        assert chat.description is not None
        assert len(chat.description) > 0
        assert subject.name in chat.description

    def test_signal_does_not_create_chats_when_no_enrollments(
        self, student_user, tutor_user
    ):
        """Test that signal handles gracefully when student has no enrollments"""
        # Assign tutor before any enrollments exist
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # No chats should be created
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR
        ).count() == 0

    def test_signal_error_handling_does_not_block_save(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that signal errors don't prevent StudentProfile save"""
        # Create enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Mock ChatRoom.objects.create to raise exception
        from unittest.mock import patch

        with patch('chat.models.ChatRoom.objects.create', side_effect=Exception("Test error")):
            # This should not raise an exception
            student_profile = student_user.student_profile
            student_profile.tutor = tutor_user
            student_profile.save()

        # StudentProfile should be saved despite error
        student_profile.refresh_from_db()
        assert student_profile.tutor == tutor_user

    def test_combined_signals_enrollment_and_tutor_assignment(
        self, student_user, teacher_user, tutor_user
    ):
        """
        Test integration of both signals:
        1. Enrollment signal creates FORUM_SUBJECT + FORUM_TUTOR (if tutor exists)
        2. Tutor assignment signal creates FORUM_TUTOR for existing enrollments
        """
        subject1 = Subject.objects.create(name="Math")
        subject2 = Subject.objects.create(name="Physics")

        # Scenario 1: Create enrollment BEFORE tutor assignment
        enrollment1 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject1,
            teacher=teacher_user
        )

        # Should have only FORUM_SUBJECT
        assert ChatRoom.objects.filter(enrollment=enrollment1, type=ChatRoom.Type.FORUM_SUBJECT).exists()
        assert not ChatRoom.objects.filter(enrollment=enrollment1, type=ChatRoom.Type.FORUM_TUTOR).exists()

        # Now assign tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Now enrollment1 should have both chats
        assert ChatRoom.objects.filter(enrollment=enrollment1, type=ChatRoom.Type.FORUM_SUBJECT).exists()
        assert ChatRoom.objects.filter(enrollment=enrollment1, type=ChatRoom.Type.FORUM_TUTOR).exists()

        # Scenario 2: Create enrollment AFTER tutor assignment
        enrollment2 = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject2,
            teacher=teacher_user
        )

        # Should automatically have both chats (enrollment signal creates both)
        assert ChatRoom.objects.filter(enrollment=enrollment2, type=ChatRoom.Type.FORUM_SUBJECT).exists()
        assert ChatRoom.objects.filter(enrollment=enrollment2, type=ChatRoom.Type.FORUM_TUTOR).exists()


@pytest.mark.unit
@pytest.mark.django_db
class TestTutorReassignment:
    """Tests for tutor reassignment scenarios"""

    def test_reassigning_tutor_does_not_create_duplicate_chats(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that reassigning a different tutor doesn't create duplicate chats"""
        # Create enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Assign first tutor
        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify chat created
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        ).count() == 1

        # Create second tutor
        tutor2 = User.objects.create_user(
            username='tutor2',
            email='tutor2@test.com',
            password='testpass123',
            role='tutor',
            first_name='Tutor',
            last_name='Two'
        )

        # Reassign to different tutor
        student_profile.tutor = tutor2
        student_profile.save()

        # Should still have only 1 chat (idempotency check prevents duplicates)
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        ).count() == 1

    def test_removing_tutor_does_not_delete_chats(
        self, student_user, teacher_user, tutor_user, subject
    ):
        """Test that removing tutor doesn't delete existing FORUM_TUTOR chats"""
        # Create enrollment and assign tutor
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.save()

        # Verify chat exists
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        ).exists()

        # Remove tutor
        student_profile.tutor = None
        student_profile.save()

        # Chat should still exist
        assert ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_TUTOR,
            enrollment=enrollment
        ).exists()
