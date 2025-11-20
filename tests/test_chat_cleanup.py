"""
Тесты для проверки автоудаления сообщений в системе чата
"""
import os
import sys
import django

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from chat.models import ChatRoom, Message, ChatParticipant
from chat.general_chat_service import GeneralChatService


class ChatCleanupTestCase(TestCase):
    """Тесты для очистки старых сообщений"""
    
    def setUp(self):
        """Создание тестовых данных"""
        self.teacher = User.objects.create_user(
            username='teacher1',
            email='teacher@test.com',
            password='testpass123',
            first_name='Teacher',
            last_name='Test',
            role=User.Role.TEACHER
        )
        
        self.student = User.objects.create_user(
            username='student1',
            email='student@test.com',
            password='testpass123',
            first_name='Student',
            last_name='Test',
            role=User.Role.STUDENT
        )
        
        # Создаем чат-комнату с автоудалением через 2 дня
        self.chat_room = ChatRoom.objects.create(
            name='Test Chat',
            description='Test chat room',
            type=ChatRoom.Type.GENERAL,
            created_by=self.teacher,
            auto_delete_days=2
        )
        
        self.chat_room.participants.add(self.teacher, self.student)
    
    def test_cleanup_old_messages(self):
        """Тест очистки старых сообщений"""
        # Создаем старое сообщение (3 дня назад)
        old_message = Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content='Old message',
            created_at=timezone.now() - timedelta(days=3)
        )
        
        # Создаем новое сообщение (1 день назад)
        new_message = Message.objects.create(
            room=self.chat_room,
            sender=self.student,
            content='New message',
            created_at=timezone.now() - timedelta(days=1)
        )
        
        # Проверяем, что оба сообщения существуют
        self.assertEqual(Message.objects.count(), 2)
        
        # Запускаем очистку
        deleted_count = GeneralChatService.cleanup_old_messages()
        
        # Проверяем, что удалено только одно старое сообщение
        self.assertEqual(deleted_count, 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.first(), new_message)
    
    def test_cleanup_respects_room_settings(self):
        """Тест, что очистка учитывает настройки каждой комнаты"""
        # Создаем вторую комнату с автоудалением через 5 дней
        chat_room2 = ChatRoom.objects.create(
            name='Test Chat 2',
            description='Test chat room 2',
            type=ChatRoom.Type.GENERAL,
            created_by=self.teacher,
            auto_delete_days=5
        )
        
        # Сообщение 3 дня назад - должно быть удалено из первой комнаты
        Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content='Old message 1',
            created_at=timezone.now() - timedelta(days=3)
        )
        
        # Сообщение 3 дня назад - НЕ должно быть удалено из второй комнаты
        Message.objects.create(
            room=chat_room2,
            sender=self.teacher,
            content='Old message 2',
            created_at=timezone.now() - timedelta(days=3)
        )
        
        # Запускаем очистку
        deleted_count = GeneralChatService.cleanup_old_messages()
        
        # Проверяем, что удалено только одно сообщение
        self.assertEqual(deleted_count, 1)
        self.assertEqual(Message.objects.count(), 1)
    
    def test_general_chat_cleanup(self):
        """Тест очистки сообщений общего чата"""
        # Создаем общий чат
        general_chat = GeneralChatService.get_or_create_general_chat()
        
        # Создаем старое сообщение
        old_message = Message.objects.create(
            room=general_chat,
            sender=self.teacher,
            content='Old general message',
            created_at=timezone.now() - timedelta(days=8)
        )
        
        # Создаем новое сообщение
        new_message = Message.objects.create(
            room=general_chat,
            sender=self.student,
            content='New general message',
            created_at=timezone.now() - timedelta(days=1)
        )
        
        # Очищаем только общий чат
        deleted_count = GeneralChatService.cleanup_old_general_chat_messages()
        
        # Проверяем результат
        self.assertEqual(deleted_count, 1)
        self.assertEqual(Message.objects.count(), 1)
        self.assertEqual(Message.objects.first(), new_message)
    
    def test_no_messages_to_cleanup(self):
        """Тест, когда нет сообщений для очистки"""
        # Создаем только новое сообщение
        Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content='New message',
            created_at=timezone.now() - timedelta(hours=12)
        )
        
        # Запускаем очистку
        deleted_count = GeneralChatService.cleanup_old_messages()
        
        # Проверяем, что ничего не удалено
        self.assertEqual(deleted_count, 0)
        self.assertEqual(Message.objects.count(), 1)


if __name__ == '__main__':
    import unittest
    unittest.main()
