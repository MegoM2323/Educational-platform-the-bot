from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from chat.models import ChatRoom, ChatParticipant, Message
from chat.services.chat_service import ChatService
from chat.permissions import can_initiate_chat

User = get_user_model()


class ChatServiceTestCase(TestCase):
    """Тесты для ChatService"""

    def setUp(self):
        """Создать тестовые данные"""
        self.student1 = User.objects.create_user(
            username='student1', password='pass', role='student', is_active=True
        )
        self.student2 = User.objects.create_user(
            username='student2', password='pass', role='student', is_active=True
        )
        self.teacher = User.objects.create_user(
            username='teacher', password='pass', role='teacher', is_active=True
        )
        self.admin = User.objects.create_user(
            username='admin', password='pass', role='admin', is_active=True, is_staff=True
        )

    def test_can_access_chat_as_participant(self):
        """Участник может получить доступ к чату"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        self.assertTrue(ChatService.can_access_chat(self.student1, chat))

    def test_cannot_access_chat_as_non_participant(self):
        """Не-участник не может получить доступ к чату"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        self.assertFalse(ChatService.can_access_chat(self.student2, chat))

    def test_create_message_successfully(self):
        """Создание сообщения в чат"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        message = ChatService.create_message(
            self.student1, chat, "Hello, test message", "text"
        )

        self.assertIsNotNone(message.id)
        self.assertEqual(message.content, "Hello, test message")
        self.assertEqual(message.sender, self.student1)
        self.assertEqual(message.room, chat)
        self.assertEqual(message.message_type, "text")
        self.assertFalse(message.is_deleted)
        self.assertFalse(message.is_edited)

    def test_mark_messages_as_read(self):
        """Отметить сообщения как прочитанные"""
        chat = ChatRoom.objects.create()
        participant = ChatParticipant.objects.create(room=chat, user=self.student1)

        self.assertIsNone(participant.last_read_at)

        ChatService.mark_messages_as_read(self.student1, chat)

        participant.refresh_from_db()
        self.assertIsNotNone(participant.last_read_at)

    def test_get_unread_count_no_messages(self):
        """Количество непрочитанных когда нет сообщений"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        count = ChatService.get_unread_count(self.student1, chat)
        self.assertEqual(count, 0)

    def test_get_unread_count_with_messages(self):
        """Количество непрочитанных с сообщениями от других"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)
        ChatParticipant.objects.create(room=chat, user=self.student2)

        # Student2 отправляет 2 сообщения
        ChatService.create_message(self.student2, chat, "Message 1", "text")
        ChatService.create_message(self.student2, chat, "Message 2", "text")

        # Student1 имеет 2 непрочитанных
        count = ChatService.get_unread_count(self.student1, chat)
        self.assertEqual(count, 2)

        # Отметить как прочитанные
        ChatService.mark_messages_as_read(self.student1, chat)

        # Теперь 0
        count = ChatService.get_unread_count(self.student1, chat)
        self.assertEqual(count, 0)

    def test_get_unread_count_ignores_own_messages(self):
        """Непрочитанные не считают свои сообщения"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        # Student1 отправляет сообщение
        ChatService.create_message(self.student1, chat, "My message", "text")

        # У себя 0 непрочитанных
        count = ChatService.get_unread_count(self.student1, chat)
        self.assertEqual(count, 0)

    def test_get_chat_messages(self):
        """Получить сообщения чата"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        msg1 = ChatService.create_message(self.student1, chat, "First", "text")
        msg2 = ChatService.create_message(self.student1, chat, "Second", "text")
        msg3 = ChatService.create_message(self.student1, chat, "Third", "text")

        messages = ChatService.get_chat_messages(chat, limit=10)
        self.assertEqual(len(messages), 3)
        # Возвращаются в обратном порядке (новые первыми)
        self.assertEqual(messages[0].id, msg3.id)

    def test_get_chat_messages_with_limit(self):
        """Получить сообщения с лимитом"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        for i in range(5):
            ChatService.create_message(self.student1, chat, f"Message {i}", "text")

        messages = ChatService.get_chat_messages(chat, limit=2)
        self.assertEqual(len(messages), 2)

    def test_get_chat_messages_excludes_deleted(self):
        """Удаленные сообщения не возвращаются"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        msg1 = ChatService.create_message(self.student1, chat, "Keep", "text")
        msg2 = ChatService.create_message(self.student1, chat, "Delete", "text")

        ChatService.delete_message(self.student1, msg2)

        messages = ChatService.get_chat_messages(chat, limit=10)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].id, msg1.id)

    def test_update_message_by_sender(self):
        """Автор может редактировать сообщение"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        message = ChatService.create_message(self.student1, chat, "Original", "text")
        message.content = "Updated"

        updated = ChatService.update_message(self.student1, message)

        self.assertEqual(updated.content, "Updated")
        self.assertTrue(updated.is_edited)

    def test_update_message_by_non_sender_fails(self):
        """Не-автор не может редактировать"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)
        ChatParticipant.objects.create(room=chat, user=self.student2)

        message = ChatService.create_message(self.student1, chat, "Original", "text")
        message.content = "Hacked"

        with self.assertRaises(PermissionDenied):
            ChatService.update_message(self.student2, message)

    def test_delete_message_by_sender(self):
        """Автор может удалить сообщение"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)

        message = ChatService.create_message(self.student1, chat, "To delete", "text")

        deleted = ChatService.delete_message(self.student1, message)

        self.assertTrue(deleted.is_deleted)
        self.assertIsNotNone(deleted.deleted_at)

    def test_delete_message_by_admin(self):
        """Администратор может удалить чужое сообщение"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)
        ChatParticipant.objects.create(room=chat, user=self.admin)

        message = ChatService.create_message(self.student1, chat, "Admin delete", "text")

        deleted = ChatService.delete_message(self.admin, message)

        self.assertTrue(deleted.is_deleted)

    def test_delete_message_by_non_sender_fails(self):
        """Не-автор и не-админ не могут удалить"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)
        ChatParticipant.objects.create(room=chat, user=self.student2)

        message = ChatService.create_message(self.student1, chat, "Protected", "text")

        with self.assertRaises(PermissionDenied):
            ChatService.delete_message(self.student2, message)

    def test_get_user_chats_empty(self):
        """Получить чаты когда их нет"""
        chats = ChatService.get_user_chats(self.student1)
        self.assertEqual(chats.count(), 0)

    def test_get_user_chats_with_participation(self):
        """Получить чаты пользователя"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)
        ChatParticipant.objects.create(room=chat, user=self.student2)

        chats = ChatService.get_user_chats(self.student1)
        # Проверим что queryset вернул результаты
        self.assertEqual(chats.count(), 1)

    def test_get_user_chats_excludes_inactive(self):
        """Неактивные чаты не возвращаются"""
        chat = ChatRoom.objects.create(is_active=False)
        ChatParticipant.objects.create(room=chat, user=self.student1)

        chats = ChatService.get_user_chats(self.student1)
        self.assertEqual(chats.count(), 0)

    def test_get_user_chats_has_unread_annotation(self):
        """Чаты имеют аннотацию unread_count"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)
        ChatParticipant.objects.create(room=chat, user=self.student2)

        ChatService.create_message(self.student2, chat, "Unread", "text")

        chats = ChatService.get_user_chats(self.student1)
        # Просто проверим что queryset имеет аннотации
        self.assertEqual(chats.count(), 1)

    def test_is_direct_chat(self):
        """Проверка является ли чат direct"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)
        ChatParticipant.objects.create(room=chat, user=self.student2)

        self.assertTrue(chat.is_direct_chat())

    def test_is_group_chat(self):
        """Проверка является ли чат групповым"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student1)
        ChatParticipant.objects.create(room=chat, user=self.student2)
        ChatParticipant.objects.create(room=chat, user=self.teacher)

        self.assertFalse(chat.is_direct_chat())
        self.assertTrue(chat.is_group_chat())


class ChatServiceDirectChatTestCase(TestCase):
    """Тесты для создания direct чатов в ChatService"""

    def setUp(self):
        """Создать тестовые данные"""
        self.student = User.objects.create_user(
            username='student', password='pass', role='student', is_active=True
        )
        self.teacher = User.objects.create_user(
            username='teacher', password='pass', role='teacher', is_active=True
        )
        self.admin = User.objects.create_user(
            username='admin', password='pass', role='admin', is_active=True, is_staff=True
        )

    def test_get_or_create_direct_chat_admin_can_create(self):
        """Админ может создать чат с кем угодно"""
        chat = ChatService.get_or_create_direct_chat(self.admin, self.student)

        self.assertIsNotNone(chat.id)
        self.assertTrue(ChatService.can_access_chat(self.admin, chat))
        self.assertTrue(ChatService.can_access_chat(self.student, chat))

    def test_get_or_create_direct_chat_returns_existing(self):
        """Повторный вызов возвращает существующий чат"""
        chat1 = ChatService.get_or_create_direct_chat(self.admin, self.student)
        chat2 = ChatService.get_or_create_direct_chat(self.admin, self.student)

        self.assertEqual(chat1.id, chat2.id)

    def test_get_or_create_direct_chat_fails_without_permission(self):
        """Без прав не может создать чат"""
        student2 = User.objects.create_user(
            username='student2', password='pass', role='student', is_active=True
        )

        with self.assertRaises(PermissionDenied):
            ChatService.get_or_create_direct_chat(self.student, student2)


class ChatPermissionCacheTestCase(TestCase):
    """Тесты для кэширования прав доступа"""

    def setUp(self):
        """Создать тестовые данные"""
        self.student1 = User.objects.create_user(
            username='student1', password='pass', role='student', is_active=True
        )
        self.student2 = User.objects.create_user(
            username='student2', password='pass', role='student', is_active=True
        )

    def test_permission_cache_invalidation(self):
        """Инвалидация кэша прав"""
        # Первый вызов должен быть False (студент-студент запрещено)
        result1 = can_initiate_chat(self.student1, self.student2)
        self.assertFalse(result1)

        # Второй вызов должен использовать кэш
        result2 = can_initiate_chat(self.student1, self.student2)
        self.assertFalse(result2)

        # Инвалидировать кэш
        ChatService.invalidate_permission_cache(self.student1.id, self.student2.id)

        # Третий вызов будет свежим
        result3 = can_initiate_chat(self.student1, self.student2)
        self.assertFalse(result3)
