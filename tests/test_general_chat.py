from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils import timezone
from backend.chat.models import ChatRoom, Message, MessageThread
from backend.chat.general_chat_service import GeneralChatService

User = get_user_model()


class GeneralChatServiceTest(TestCase):
    """
    Тесты для сервиса общего чата
    """
    
    def setUp(self):
        """Настройка тестовых данных"""
        # Создаем пользователей разных ролей
        self.teacher = User.objects.create_user(
            username='teacher1',
            email='teacher1@test.com',
            first_name='Учитель',
            last_name='Тестовый',
            role=User.Role.TEACHER
        )
        
        self.student = User.objects.create_user(
            username='student1',
            email='student1@test.com',
            first_name='Студент',
            last_name='Тестовый',
            role=User.Role.STUDENT
        )
        
        self.parent = User.objects.create_user(
            username='parent1',
            email='parent1@test.com',
            first_name='Родитель',
            last_name='Тестовый',
            role=User.Role.PARENT
        )
    
    def test_get_or_create_general_chat(self):
        """Тест создания общего чата"""
        # Первый вызов должен создать чат
        chat1 = GeneralChatService.get_or_create_general_chat()
        self.assertEqual(chat1.type, ChatRoom.Type.GENERAL)
        self.assertEqual(chat1.name, 'Общий форум')
        
        # Второй вызов должен вернуть тот же чат
        chat2 = GeneralChatService.get_or_create_general_chat()
        self.assertEqual(chat1.id, chat2.id)
    
    def test_automatic_participant_management(self):
        """Тест автоматического добавления участников всех ролей"""
        # Создаем общий чат
        general_chat = GeneralChatService.get_or_create_general_chat()
        
        # Проверяем, что учитель, студент и родитель добавлены автоматически
        self.assertTrue(general_chat.participants.filter(id=self.teacher.id).exists())
        self.assertTrue(general_chat.participants.filter(id=self.student.id).exists())
        self.assertTrue(general_chat.participants.filter(id=self.parent.id).exists())
    
    def test_add_user_to_general_chat(self):
        """Тест добавления пользователя в общий чат (включая родителя)"""
        general_chat = GeneralChatService.get_or_create_general_chat()
        
        # Удалим родителя и добавим снова
        general_chat.participants.remove(self.parent)
        result = GeneralChatService.add_user_to_general_chat(self.parent)
        self.assertTrue(result)
        self.assertTrue(general_chat.participants.filter(id=self.parent.id).exists())
        
        # Добавляем студента (должен быть добавлен)
        result = GeneralChatService.add_user_to_general_chat(self.student)
        self.assertTrue(result)
        self.assertTrue(general_chat.participants.filter(id=self.student.id).exists())
    
    def test_create_thread(self):
        """Тест создания треда"""
        general_chat = GeneralChatService.get_or_create_general_chat()
        
        thread = GeneralChatService.create_thread(
            room=general_chat,
            title='Тестовый тред',
            created_by=self.teacher
        )
        
        self.assertEqual(thread.title, 'Тестовый тред')
        self.assertEqual(thread.room, general_chat)
        self.assertEqual(thread.created_by, self.teacher)
        self.assertFalse(thread.is_pinned)
        self.assertFalse(thread.is_locked)
    
    def test_send_message_to_thread(self):
        """Тест отправки сообщения в тред"""
        general_chat = GeneralChatService.get_or_create_general_chat()
        thread = GeneralChatService.create_thread(
            room=general_chat,
            title='Тестовый тред',
            created_by=self.teacher
        )
        
        message = GeneralChatService.send_message_to_thread(
            room=general_chat,
            thread=thread,
            sender=self.teacher,
            content='Тестовое сообщение'
        )
        
        self.assertEqual(message.content, 'Тестовое сообщение')
        self.assertEqual(message.thread, thread)
        self.assertEqual(message.sender, self.teacher)
        self.assertEqual(message.room, general_chat)
    
    def test_send_general_message(self):
        """Тест отправки сообщения в общий чат"""
        message = GeneralChatService.send_general_message(
            sender=self.teacher,
            content='Общее сообщение'
        )
        
        self.assertEqual(message.content, 'Общее сообщение')
        self.assertEqual(message.sender, self.teacher)
        self.assertEqual(message.room.type, ChatRoom.Type.GENERAL)
        self.assertIsNone(message.thread)
    
    def test_thread_moderation(self):
        """Тест модерации тредов"""
        general_chat = GeneralChatService.get_or_create_general_chat()
        thread = GeneralChatService.create_thread(
            room=general_chat,
            title='Тестовый тред',
            created_by=self.teacher
        )
        
        # Учитель может закрепить тред
        pinned_thread = GeneralChatService.pin_thread(thread, self.teacher)
        self.assertTrue(pinned_thread.is_pinned)
        
        # Учитель может заблокировать тред
        locked_thread = GeneralChatService.lock_thread(thread, self.teacher)
        self.assertTrue(locked_thread.is_locked)
        
        # Студент не может закрепить тред
        with self.assertRaises(PermissionError):
            GeneralChatService.pin_thread(thread, self.student)
    
    def test_get_thread_messages(self):
        """Тест получения сообщений треда"""
        general_chat = GeneralChatService.get_or_create_general_chat()
        thread = GeneralChatService.create_thread(
            room=general_chat,
            title='Тестовый тред',
            created_by=self.teacher
        )
        
        # Отправляем несколько сообщений
        for i in range(5):
            GeneralChatService.send_message_to_thread(
                room=general_chat,
                thread=thread,
                sender=self.teacher,
                content=f'Сообщение {i+1}'
            )
        
        # Получаем сообщения
        messages = GeneralChatService.get_thread_messages(thread, limit=3, offset=0)
        self.assertEqual(len(messages), 3)
        
        # Проверяем пагинацию
        messages_page2 = GeneralChatService.get_thread_messages(thread, limit=3, offset=3)
        self.assertEqual(len(messages_page2), 2)
    
    def test_get_general_chat_messages(self):
        """Тест получения сообщений общего чата"""
        # Отправляем несколько сообщений в общий чат
        for i in range(3):
            GeneralChatService.send_general_message(
                sender=self.teacher,
                content=f'Общее сообщение {i+1}'
            )
        
        # Получаем сообщения
        messages = GeneralChatService.get_general_chat_messages(limit=10, offset=0)
        self.assertEqual(len(messages), 3)
    
    def test_get_general_chat_threads(self):
        """Тест получения тредов общего чата"""
        general_chat = GeneralChatService.get_or_create_general_chat()
        
        # Создаем несколько тредов
        for i in range(3):
            GeneralChatService.create_thread(
                room=general_chat,
                title=f'Тред {i+1}',
                created_by=self.teacher
            )
        
        # Получаем треды
        threads = GeneralChatService.get_general_chat_threads(limit=10, offset=0)
        self.assertEqual(len(threads), 3)
    
    def test_user_role_in_chat(self):
        """Тест получения роли пользователя в чате"""
        general_chat = GeneralChatService.get_or_create_general_chat()
        
        # Учитель должен быть администратором
        teacher_role = GeneralChatService.get_user_role_in_chat(self.teacher, general_chat)
        self.assertEqual(teacher_role, 'admin')
        
        # Студент должен иметь роль студента
        student_role = GeneralChatService.get_user_role_in_chat(self.student, general_chat)
        self.assertEqual(student_role, 'student')
        
        # Родитель должен иметь роль родителя
        parent_role = GeneralChatService.get_user_role_in_chat(self.parent, general_chat)
        self.assertEqual(parent_role, 'parent')
