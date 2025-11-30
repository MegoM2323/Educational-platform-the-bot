"""
Unit tests for forum message signals and Pachca integration.

Tests:
- Forum message signal triggers for FORUM_SUBJECT type chats
- Forum message signal triggers for FORUM_TUTOR type chats
- Forum message signal does NOT trigger for other chat types
- Forum message signal handles missing chat room gracefully
- Forum message signal calls PachcaService.notify_new_forum_message()
- Forum message signal does not block message creation if Pachca fails
- Error handling and logging in signal handlers
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from chat.models import ChatRoom, Message
from chat.signals import send_forum_notification
from materials.models import Subject, SubjectEnrollment


@pytest.mark.unit
@pytest.mark.django_db
class TestForumMessageSignal:
    """Tests for send_forum_notification signal handler"""

    def test_signal_triggers_on_forum_subject_message_creation(self, student_user, teacher_user):
        """Signal should trigger when message created in FORUM_SUBJECT chat"""
        # Create forum chat
        forum_chat = ChatRoom.objects.create(
            name="Test Forum Subject",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=teacher_user
        )
        forum_chat.participants.add(student_user, teacher_user)

        # Mock Pachca service
        with patch('chat.signals.PachcaService') as mock_pachca_class:
            mock_service = MagicMock()
            mock_service.is_configured.return_value = True
            mock_pachca_class.return_value = mock_service

            # Create message - signal should fire
            message = Message.objects.create(
                room=forum_chat,
                sender=student_user,
                content="Test forum message"
            )

            # Verify Pachca service was instantiated and notified
            mock_pachca_class.assert_called_once()
            mock_service.is_configured.assert_called()
            mock_service.notify_new_forum_message.assert_called_once_with(message, forum_chat)

    def test_signal_triggers_on_forum_tutor_message_creation(self, student_user, teacher_user):
        """Signal should trigger when message created in FORUM_TUTOR chat"""
        # Create tutor forum chat
        forum_chat = ChatRoom.objects.create(
            name="Test Forum Tutor",
            type=ChatRoom.Type.FORUM_TUTOR,
            created_by=student_user
        )
        forum_chat.participants.add(student_user, teacher_user)

        # Mock Pachca service
        with patch('chat.signals.PachcaService') as mock_pachca_class:
            mock_service = MagicMock()
            mock_service.is_configured.return_value = True
            mock_pachca_class.return_value = mock_service

            # Create message - signal should fire
            message = Message.objects.create(
                room=forum_chat,
                sender=student_user,
                content="Test tutor forum message"
            )

            # Verify notification was sent
            mock_service.notify_new_forum_message.assert_called_once_with(message, forum_chat)

    def test_signal_does_not_trigger_for_direct_chat(self, student_user, teacher_user):
        """Signal should NOT trigger for DIRECT type chats"""
        # Create direct chat (not forum)
        direct_chat = ChatRoom.objects.create(
            name="Direct Chat",
            type=ChatRoom.Type.DIRECT,
            created_by=teacher_user
        )
        direct_chat.participants.add(student_user, teacher_user)

        # Mock Pachca service
        with patch('chat.signals.PachcaService') as mock_pachca_class:
            mock_service = MagicMock()
            mock_pachca_class.return_value = mock_service

            # Create message - signal should NOT fire for this chat type
            message = Message.objects.create(
                room=direct_chat,
                sender=student_user,
                content="Direct message"
            )

            # Verify Pachca service was NOT called for notification
            mock_service.notify_new_forum_message.assert_not_called()

    def test_signal_does_not_trigger_for_general_forum(self, student_user, teacher_user):
        """Signal should NOT trigger for GENERAL forum chats (only forum_subject/forum_tutor)"""
        # Create general forum (not private forum)
        general_forum = ChatRoom.objects.create(
            name="General Forum",
            type=ChatRoom.Type.GENERAL,
            created_by=teacher_user
        )
        general_forum.participants.add(student_user, teacher_user)

        # Mock Pachca service
        with patch('chat.signals.PachcaService') as mock_pachca_class:
            mock_service = MagicMock()
            mock_pachca_class.return_value = mock_service

            # Create message - signal should NOT fire
            message = Message.objects.create(
                room=general_forum,
                sender=student_user,
                content="General forum message"
            )

            # Verify notification was NOT sent
            mock_service.notify_new_forum_message.assert_not_called()

    def test_signal_does_not_trigger_on_message_update(self, student_user, teacher_user):
        """Signal should only trigger on creation, not on message updates"""
        # Create forum chat
        forum_chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=teacher_user
        )
        forum_chat.participants.add(student_user, teacher_user)

        # Create message first (signal fires once)
        with patch('chat.signals.PachcaService') as mock_pachca_class:
            mock_service = MagicMock()
            mock_service.is_configured.return_value = True
            mock_pachca_class.return_value = mock_service

            message = Message.objects.create(
                room=forum_chat,
                sender=student_user,
                content="Original content"
            )

            # Reset mock to check that update doesn't trigger signal
            mock_pachca_class.reset_mock()
            mock_service.reset_mock()

            # Update message
            message.content = "Updated content"
            message.is_edited = True
            message.save()

            # Verify signal did NOT fire on update
            mock_service.notify_new_forum_message.assert_not_called()

    def test_signal_handles_pachca_not_configured(self, student_user, teacher_user):
        """Signal should handle gracefully when Pachca is not configured"""
        # Create forum chat
        forum_chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=teacher_user
        )
        forum_chat.participants.add(student_user, teacher_user)

        # Mock Pachca service - not configured
        with patch('chat.signals.PachcaService') as mock_pachca_class:
            mock_service = MagicMock()
            mock_service.is_configured.return_value = False
            mock_pachca_class.return_value = mock_service

            # Create message - should not error even if Pachca not configured
            message = Message.objects.create(
                room=forum_chat,
                sender=student_user,
                content="Message with Pachca disabled"
            )

            # Verify initialization happened but notification not called
            mock_pachca_class.assert_called_once()
            mock_service.is_configured.assert_called_once()
            mock_service.notify_new_forum_message.assert_not_called()

    def test_signal_does_not_block_message_creation_on_pachca_error(self, student_user, teacher_user):
        """Signal should not block message creation if Pachca API fails"""
        # Create forum chat
        forum_chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=teacher_user
        )
        forum_chat.participants.add(student_user, teacher_user)

        # Mock Pachca service to raise exception
        with patch('chat.signals.PachcaService') as mock_pachca_class:
            mock_service = MagicMock()
            mock_service.is_configured.return_value = True
            mock_service.notify_new_forum_message.side_effect = Exception("Pachca API error")
            mock_pachca_class.return_value = mock_service

            # Create message - should succeed despite Pachca error
            message = Message.objects.create(
                room=forum_chat,
                sender=student_user,
                content="Message created despite Pachca error"
            )

            # Message should be saved successfully
            assert message.id is not None
            assert message.content == "Message created despite Pachca error"

            # Pachca was attempted
            mock_service.notify_new_forum_message.assert_called_once()

    def test_signal_logs_error_on_pachca_failure(self, student_user, teacher_user):
        """Signal should log errors when Pachca notification fails"""
        # Create forum chat
        forum_chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=teacher_user
        )
        forum_chat.participants.add(student_user, teacher_user)

        # Mock Pachca service and logger
        with patch('chat.signals.PachcaService') as mock_pachca_class, \
             patch('chat.signals.logger') as mock_logger:
            mock_service = MagicMock()
            mock_service.is_configured.return_value = True
            error = Exception("Network timeout")
            mock_service.notify_new_forum_message.side_effect = error
            mock_pachca_class.return_value = mock_service

            # Create message
            message = Message.objects.create(
                room=forum_chat,
                sender=student_user,
                content="Test"
            )

            # Verify error was logged
            mock_logger.error.assert_called_once()
            error_call_args = mock_logger.error.call_args
            assert "Error sending Pachca notification" in error_call_args[0][0]
            assert str(message.id) in error_call_args[0][0]

    def test_signal_handles_missing_chat_room(self, student_user):
        """Signal should handle gracefully when message has no chat room"""
        # Create a message with None room (should not happen but be defensive)
        with patch('chat.signals.logger') as mock_logger:
            # We'll manually call the signal since creating Message with room=None
            # might fail due to database constraint
            from django.db.models.signals import post_save
            from chat.models import Message
            from chat.signals import send_forum_notification

            # Create a mock message instance
            mock_message = Mock(spec=Message)
            mock_message.id = 999
            mock_message.room = None

            # Call signal handler directly
            send_forum_notification(
                sender=Message,
                instance=mock_message,
                created=True
            )

            # Verify warning was logged for missing chat room
            mock_logger.warning.assert_called_once()
            warning_call_args = mock_logger.warning.call_args
            assert "has no associated ChatRoom" in warning_call_args[0][0]

    def test_signal_with_enrollment_link(self, student_user, teacher_user, db):
        """Signal should handle forum chats linked to SubjectEnrollment"""
        # Create subject
        subject = Subject.objects.create(
            name="Test Subject",
            description="Test Description"
        )

        # Create enrollment
        enrollment = SubjectEnrollment.objects.create(
            student=student_user,
            subject=subject,
            teacher=teacher_user
        )

        # Create forum chat with enrollment
        forum_chat = ChatRoom.objects.create(
            name="Test Forum with Enrollment",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=student_user,
            enrollment=enrollment
        )
        forum_chat.participants.add(student_user, teacher_user)

        # Mock Pachca service
        with patch('chat.signals.PachcaService') as mock_pachca_class:
            mock_service = MagicMock()
            mock_service.is_configured.return_value = True
            mock_pachca_class.return_value = mock_service

            # Create message
            message = Message.objects.create(
                room=forum_chat,
                sender=student_user,
                content="Forum message with enrollment"
            )

            # Verify Pachca was called with both message and chat room
            mock_service.notify_new_forum_message.assert_called_once()
            call_args = mock_service.notify_new_forum_message.call_args
            assert call_args[0][0] == message
            assert call_args[0][1] == forum_chat

    def test_signal_passes_correct_objects_to_pachca(self, student_user, teacher_user):
        """Signal should pass correct message and chat_room objects to PachcaService"""
        # Create forum chat
        forum_chat = ChatRoom.objects.create(
            name="Test Forum",
            type=ChatRoom.Type.FORUM_SUBJECT,
            created_by=teacher_user
        )
        forum_chat.participants.add(student_user, teacher_user)

        # Mock Pachca service
        with patch('chat.signals.PachcaService') as mock_pachca_class:
            mock_service = MagicMock()
            mock_service.is_configured.return_value = True
            mock_pachca_class.return_value = mock_service

            # Create message
            message = Message.objects.create(
                room=forum_chat,
                sender=student_user,
                content="Verify objects passed correctly"
            )

            # Capture call arguments
            call_args = mock_service.notify_new_forum_message.call_args
            passed_message = call_args[0][0]
            passed_chat_room = call_args[0][1]

            # Verify correct objects were passed
            assert isinstance(passed_message, Message)
            assert passed_message.id == message.id
            assert isinstance(passed_chat_room, ChatRoom)
            assert passed_chat_room.id == forum_chat.id
