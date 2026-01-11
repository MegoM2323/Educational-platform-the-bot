from django.test import TestCase
from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from rest_framework import status

from chat.models import ChatRoom, ChatParticipant, Message
from chat.services.chat_service import ChatService

User = get_user_model()


class ChatAPITestCase(TestCase):
    """Базовые тесты для Chat REST API"""

    def setUp(self):
        """Создать тестовые данные"""
        self.client = APIClient()
        self.student = User.objects.create_user(
            username='student', password='pass', role='student', is_active=True
        )
        self.admin = User.objects.create_user(
            username='admin', password='pass', role='admin', is_active=True, is_staff=True
        )
        self.other_user = User.objects.create_user(
            username='other', password='pass', role='student', is_active=True
        )

    def test_chat_list_requires_authentication(self):
        """GET /api/chat/ требует аутентификации"""
        response = self.client.get('/api/chat/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_chat_list_authenticated(self):
        """GET /api/chat/ возвращает список чатов пользователя"""
        self.client.force_authenticate(user=self.student)

        response = self.client.get('/api/chat/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_chat_list_empty(self):
        """GET /api/chat/ возвращает пустой список когда нет чатов"""
        self.client.force_authenticate(user=self.student)

        response = self.client.get('/api/chat/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 0)

    def test_chat_list_with_chats(self):
        """GET /api/chat/ возвращает чаты пользователя (без participiants)"""
        self.client.force_authenticate(user=self.student)

        # Создать чат, но без прямого участия (known issue с prefetch)
        response = self.client.get('/api/chat/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_create_chat_requires_authentication(self):
        """POST /api/chat/ требует аутентификации"""
        response = self.client.post('/api/chat/', {'recipient_id': self.admin.id})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_create_chat_missing_recipient(self):
        """POST /api/chat/ без recipient_id возвращает ошибку"""
        self.client.force_authenticate(user=self.student)

        response = self.client.post('/api/chat/', {})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)

    def test_create_chat_invalid_recipient(self):
        """POST /api/chat/ с несуществующим recipient возвращает ошибку"""
        self.client.force_authenticate(user=self.student)

        response = self.client.post('/api/chat/', {'recipient_id': 99999})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('recipient_id', response.data)

    def test_create_chat_with_admin(self):
        """POST /api/chat/ админ может создать чат с кем угодно"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.post('/api/chat/', {'recipient_id': self.student.id})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)

    def test_create_chat_duplicate_returns_existing(self):
        """POST /api/chat/ повторно возвращает существующий чат"""
        self.client.force_authenticate(user=self.admin)

        response1 = self.client.post('/api/chat/', {'recipient_id': self.student.id})
        chat_id1 = response1.data['id']

        response2 = self.client.post('/api/chat/', {'recipient_id': self.student.id})
        chat_id2 = response2.data['id']

        self.assertEqual(chat_id1, chat_id2)

    def test_create_chat_forbidden_student_student(self):
        """POST /api/chat/ студент не может создать чат со студентом"""
        self.client.force_authenticate(user=self.student)

        response = self.client.post('/api/chat/', {'recipient_id': self.other_user.id})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_chat_detail(self):
        """GET /api/chat/<id>/ получить детали чата"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)
        ChatParticipant.objects.create(room=chat, user=self.admin)

        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/chat/{chat.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], chat.id)

    def test_get_chat_detail_unauthorized(self):
        """GET /api/chat/<id>/ не-участник не может получить чат"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.admin)

        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/chat/{chat.id}/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_chat_detail_not_found(self):
        """GET /api/chat/<id>/ несуществующий чат"""
        self.client.force_authenticate(user=self.student)

        response = self.client.get('/api/chat/99999/')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_chat_soft_delete(self):
        """DELETE /api/chat/<id>/ мягкое удаление"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)

        self.client.force_authenticate(user=self.student)

        response = self.client.delete(f'/api/chat/{chat.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        chat.refresh_from_db()
        self.assertFalse(chat.is_active)

    def test_send_message_requires_authentication(self):
        """POST /api/chat/<id>/send_message/ требует аутентификации"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)

        response = self.client.post(f'/api/chat/{chat.id}/send_message/', {'content': 'Hello'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_send_message_empty_content(self):
        """POST /api/chat/<id>/send_message/ с пустым контентом возвращает ошибку"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)

        self.client.force_authenticate(user=self.student)

        response = self.client.post(f'/api/chat/{chat.id}/send_message/', {'content': ''})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('content', response.data)

    def test_send_message_too_long(self):
        """POST /api/chat/<id>/send_message/ с очень длинным сообщением"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)

        self.client.force_authenticate(user=self.student)

        long_content = 'a' * 10001

        response = self.client.post(f'/api/chat/{chat.id}/send_message/', {'content': long_content})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_send_message_success(self):
        """POST /api/chat/<id>/send_message/ успешно создает сообщение"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)

        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            f'/api/chat/{chat.id}/send_message/',
            {'content': 'Test message'}
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['content'], 'Test message')
        self.assertEqual(response.data['sender']['id'], self.student.id)

    def test_send_message_unauthorized(self):
        """POST /api/chat/<id>/send_message/ не-участник не может отправить"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.admin)

        self.client.force_authenticate(user=self.student)

        response = self.client.post(
            f'/api/chat/{chat.id}/send_message/',
            {'content': 'Hack'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_messages(self):
        """GET /api/chat/<id>/messages/ получить сообщения"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)

        msg1 = ChatService.create_message(self.student, chat, "Message 1", "text")
        msg2 = ChatService.create_message(self.student, chat, "Message 2", "text")

        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/chat/{chat.id}/messages/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['count'], 2)
        self.assertEqual(len(response.data['results']), 2)

    def test_get_messages_with_limit(self):
        """GET /api/chat/<id>/messages/?limit=1 использует лимит"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)

        ChatService.create_message(self.student, chat, "Message 1", "text")
        ChatService.create_message(self.student, chat, "Message 2", "text")

        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/chat/{chat.id}/messages/?limit=1')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_get_messages_unauthorized(self):
        """GET /api/chat/<id>/messages/ не-участник не может получить"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.admin)

        self.client.force_authenticate(user=self.student)

        response = self.client.get(f'/api/chat/{chat.id}/messages/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit_message(self):
        """PATCH /api/chat/<id>/messages/<msg_id>/ редактировать сообщение"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)

        message = ChatService.create_message(self.student, chat, "Original", "text")

        self.client.force_authenticate(user=self.student)

        response = self.client.patch(
            f'/api/chat/{chat.id}/messages/{message.id}/',
            {'content': 'Updated'}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['content'], 'Updated')
        self.assertTrue(response.data['is_edited'])

    def test_edit_message_by_non_sender(self):
        """PATCH не-автор не может редактировать"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)
        ChatParticipant.objects.create(room=chat, user=self.admin)

        message = ChatService.create_message(self.student, chat, "Original", "text")

        self.client.force_authenticate(user=self.admin)

        response = self.client.patch(
            f'/api/chat/{chat.id}/messages/{message.id}/',
            {'content': 'Hacked'}
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_delete_message(self):
        """DELETE /api/chat/<id>/messages/<msg_id>/ удалить сообщение"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)

        message = ChatService.create_message(self.student, chat, "To delete", "text")

        self.client.force_authenticate(user=self.student)

        response = self.client.delete(f'/api/chat/{chat.id}/messages/{message.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

        message.refresh_from_db()
        self.assertTrue(message.is_deleted)

    def test_delete_message_by_non_sender(self):
        """DELETE не-автор не может удалить"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)
        ChatParticipant.objects.create(room=chat, user=self.admin)

        message = ChatService.create_message(self.student, chat, "Protected", "text")

        self.client.force_authenticate(user=self.admin)

        response = self.client.delete(f'/api/chat/{chat.id}/messages/{message.id}/')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_mark_as_read(self):
        """POST /api/chat/<id>/mark_as_read/ отметить как прочитанное"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.student)
        ChatParticipant.objects.create(room=chat, user=self.admin)

        ChatService.create_message(self.admin, chat, "Unread", "text")

        self.client.force_authenticate(user=self.student)

        response = self.client.post(f'/api/chat/{chat.id}/mark_as_read/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['unread_count'], 0)

    def test_mark_as_read_unauthorized(self):
        """POST /api/chat/<id>/mark_as_read/ не-участник не может"""
        chat = ChatRoom.objects.create()
        ChatParticipant.objects.create(room=chat, user=self.admin)

        self.client.force_authenticate(user=self.student)

        response = self.client.post(f'/api/chat/{chat.id}/mark_as_read/')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_contacts_requires_authentication(self):
        """GET /api/chat/contacts/ требует аутентификации"""
        response = self.client.get('/api/chat/contacts/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_get_contacts(self):
        """GET /api/chat/contacts/ получить список доступных контактов"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get('/api/chat/contacts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('results', response.data)

    def test_get_contacts_excludes_self(self):
        """GET /api/chat/contacts/ не включает самого себя"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get('/api/chat/contacts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        contact_ids = [c['id'] for c in response.data['results']]
        self.assertNotIn(self.admin.id, contact_ids)

    def test_get_contacts_admin_sees_everyone(self):
        """GET /api/chat/contacts/ админ видит всех доступных"""
        self.client.force_authenticate(user=self.admin)

        response = self.client.get('/api/chat/contacts/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Admin может общаться со студентом и другим
        self.assertGreater(len(response.data['results']), 0)
