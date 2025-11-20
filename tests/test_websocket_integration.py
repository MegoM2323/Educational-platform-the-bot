"""
Тесты для WebSocket интеграции
"""

import pytest
import json
import asyncio
from channels.testing import WebsocketCommunicator
from django.test import TestCase
from django.contrib.auth import get_user_model
from chat.consumers import ChatConsumer, GeneralChatConsumer, NotificationConsumer, DashboardConsumer
from chat.models import ChatRoom, Message
from config.asgi import application

User = get_user_model()


class WebSocketIntegrationTests(TestCase):
    """Тесты интеграции WebSocket"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='student'
        )
        
        self.teacher = User.objects.create_user(
            email='teacher@example.com',
            password='testpass123',
            first_name='Teacher',
            last_name='User',
            role='teacher'
        )
        
        self.chat_room = ChatRoom.objects.create(
            name='Test Room',
            description='Test Description',
            created_by=self.user
        )
        self.chat_room.participants.add(self.user, self.teacher)
    
    async def test_general_chat_connection(self):
        """Тест подключения к общему чату"""
        communicator = WebsocketCommunicator(application, "/ws/chat/general/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Отправляем сообщение
        await communicator.send_json_to({
            "type": "chat_message",
            "data": {"content": "Hello, world!"}
        })
        
        # Получаем ответ
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat_message")
        self.assertIn("message", response)
        
        await communicator.disconnect()
    
    async def test_room_chat_connection(self):
        """Тест подключения к чат-комнате"""
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.chat_room.id}/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Отправляем сообщение
        await communicator.send_json_to({
            "type": "chat_message",
            "data": {"content": "Hello, room!"}
        })
        
        # Получаем ответ
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "chat_message")
        self.assertIn("message", response)
        
        await communicator.disconnect()
    
    async def test_typing_indicator(self):
        """Тест индикатора печати"""
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.chat_room.id}/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Отправляем индикатор печати
        await communicator.send_json_to({
            "type": "typing",
            "data": {}
        })
        
        # Получаем ответ
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "typing")
        self.assertIn("user", response)
        
        await communicator.disconnect()
    
    async def test_typing_stop_indicator(self):
        """Тест остановки индикатора печати"""
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.chat_room.id}/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Отправляем остановку печати
        await communicator.send_json_to({
            "type": "typing_stop",
            "data": {}
        })
        
        # Получаем ответ
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "typing_stop")
        self.assertIn("user", response)
        
        await communicator.disconnect()
    
    async def test_message_read_marking(self):
        """Тест отметки сообщения как прочитанного"""
        # Создаем сообщение
        message = Message.objects.create(
            room=self.chat_room,
            sender=self.teacher,
            content="Test message"
        )
        
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.chat_room.id}/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Отправляем отметку о прочтении
        await communicator.send_json_to({
            "type": "mark_read",
            "data": {"message_id": message.id}
        })
        
        # Проверяем, что сообщение отмечено как прочитанное
        from chat.models import MessageRead
        self.assertTrue(MessageRead.objects.filter(
            message=message,
            user=self.user
        ).exists())
        
        await communicator.disconnect()
    
    async def test_notification_connection(self):
        """Тест подключения к уведомлениям"""
        communicator = WebsocketCommunicator(application, f"/ws/notifications/{self.user.id}/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Отправляем тестовое уведомление
        await communicator.send_json_to({
            "type": "notification",
            "data": {
                "type": "info",
                "title": "Test Notification",
                "message": "This is a test notification"
            }
        })
        
        await communicator.disconnect()
    
    async def test_dashboard_connection(self):
        """Тест подключения к обновлениям дашборда"""
        communicator = WebsocketCommunicator(application, f"/ws/dashboard/{self.user.id}/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Отправляем тестовое обновление дашборда
        await communicator.send_json_to({
            "type": "dashboard_update",
            "data": {
                "type": "materials",
                "data": {"new_materials": 5},
                "timestamp": "2024-01-01T00:00:00Z"
            }
        })
        
        await communicator.disconnect()
    
    async def test_unauthorized_access(self):
        """Тест неавторизованного доступа"""
        communicator = WebsocketCommunicator(application, "/ws/chat/general/")
        # Не устанавливаем пользователя
        
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)  # Должно быть отклонено
    
    async def test_room_access_control(self):
        """Тест контроля доступа к комнате"""
        # Создаем пользователя, который не является участником комнаты
        other_user = User.objects.create_user(
            email='other@example.com',
            password='testpass123',
            first_name='Other',
            last_name='User',
            role='student'
        )
        
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.chat_room.id}/")
        communicator.scope["user"] = other_user
        
        connected, subprotocol = await communicator.connect()
        self.assertFalse(connected)  # Должно быть отклонено
    
    async def test_invalid_json_message(self):
        """Тест обработки невалидного JSON"""
        communicator = WebsocketCommunicator(application, "/ws/chat/general/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Отправляем невалидный JSON
        await communicator.send_to(text_data="invalid json")
        
        # Получаем ответ об ошибке
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "error")
        self.assertIn("message", response)
        
        await communicator.disconnect()
    
    async def test_room_history_loading(self):
        """Тест загрузки истории сообщений"""
        # Создаем несколько сообщений
        for i in range(5):
            Message.objects.create(
                room=self.chat_room,
                sender=self.user,
                content=f"Test message {i}"
            )
        
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.chat_room.id}/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Получаем историю сообщений
        response = await communicator.receive_json_from()
        self.assertEqual(response["type"], "room_history")
        self.assertIn("messages", response)
        self.assertEqual(len(response["messages"]), 5)
        
        await communicator.disconnect()


class WebSocketPerformanceTests(TestCase):
    """Тесты производительности WebSocket"""
    
    def setUp(self):
        """Настройка тестовых данных"""
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User',
            role='student'
        )
        
        self.chat_room = ChatRoom.objects.create(
            name='Performance Test Room',
            description='Performance Test',
            created_by=self.user
        )
        self.chat_room.participants.add(self.user)
    
    async def test_concurrent_connections(self):
        """Тест множественных одновременных подключений"""
        communicators = []
        
        try:
            # Создаем 10 одновременных подключений
            for i in range(10):
                communicator = WebsocketCommunicator(application, f"/ws/chat/{self.chat_room.id}/")
                communicator.scope["user"] = self.user
                communicators.append(communicator)
            
            # Подключаемся ко всем
            connections = await asyncio.gather(
                *[comm.connect() for comm in communicators]
            )
            
            # Проверяем, что все подключения успешны
            for connected, subprotocol in connections:
                self.assertTrue(connected)
            
            # Отправляем сообщение через одно подключение
            await communicators[0].send_json_to({
                "type": "chat_message",
                "data": {"content": "Broadcast message"}
            })
            
            # Проверяем, что все остальные получили сообщение
            for i in range(1, 10):
                response = await communicators[i].receive_json_from()
                self.assertEqual(response["type"], "chat_message")
        
        finally:
            # Отключаемся от всех
            for communicator in communicators:
                await communicator.disconnect()
    
    async def test_message_broadcasting_performance(self):
        """Тест производительности broadcast сообщений"""
        communicator = WebsocketCommunicator(application, f"/ws/chat/{self.chat_room.id}/")
        communicator.scope["user"] = self.user
        
        connected, subprotocol = await communicator.connect()
        self.assertTrue(connected)
        
        # Отправляем 100 сообщений подряд
        start_time = asyncio.get_event_loop().time()
        
        for i in range(100):
            await communicator.send_json_to({
                "type": "chat_message",
                "data": {"content": f"Performance test message {i}"}
            })
        
        # Получаем все ответы
        for i in range(100):
            response = await communicator.receive_json_from()
            self.assertEqual(response["type"], "chat_message")
        
        end_time = asyncio.get_event_loop().time()
        duration = end_time - start_time
        
        # Проверяем, что время выполнения разумное (менее 10 секунд)
        self.assertLess(duration, 10.0)
        
        await communicator.disconnect()


if __name__ == '__main__':
    pytest.main([__file__])
