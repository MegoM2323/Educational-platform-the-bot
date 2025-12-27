"""
Админские API endpoints для управления чатами.
Read-only доступ к комнатам и сообщениям.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ValidationError
from accounts.permissions import IsAdminUser
from .models import ChatRoom, Message
from .serializers import ChatRoomListSerializer, MessageSerializer
from .services.admin_chat_service import AdminChatService
import logging

logger = logging.getLogger(__name__)


class AdminChatRoomListView(APIView):
    """
    GET /api/admin/chat/rooms/ - Список всех чат-комнат (admin only, read-only)

    Возвращает все чат-комнаты с участниками и последним сообщением.
    Оптимизированные запросы через AdminChatService.

    Permissions:
        - IsAdminUser (только staff/superuser)

    Response:
        200 OK:
            {
                "success": true,
                "data": {
                    "rooms": [...],
                    "count": 42
                }
            }
        403 Forbidden: Если не admin
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Получить список всех чат-комнат"""
        try:
            rooms = AdminChatService.get_all_rooms()
            serializer = ChatRoomListSerializer(
                rooms,
                many=True,
                context={'request': request}
            )

            return Response(
                {
                    'success': True,
                    'data': {
                        'rooms': serializer.data,
                        'count': rooms.count()
                    }
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error fetching admin chat rooms: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': 'Ошибка при получении списка комнат'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminChatRoomMessagesView(APIView):
    """
    GET /api/admin/chat/rooms/<room_id>/messages/ - Сообщения комнаты (admin only, read-only)

    Возвращает все сообщения указанной комнаты с информацией об отправителях.
    Поддерживает пагинацию через query параметры.

    Query Parameters:
        - limit (int, optional): Количество сообщений (default: 100, max: 500)
        - offset (int, optional): Смещение для пагинации (default: 0)

    Permissions:
        - IsAdminUser (только staff/superuser)

    Response:
        200 OK:
            {
                "success": true,
                "data": {
                    "room_id": 42,
                    "messages": [...],
                    "count": 157,
                    "limit": 100,
                    "offset": 0
                }
            }
        404 Not Found: Если комната не найдена
        403 Forbidden: Если не admin
    """
    permission_classes = [IsAdminUser]

    def get(self, request, room_id):
        """Получить сообщения комнаты"""
        try:
            # Валидация параметров
            limit = int(request.query_params.get('limit', 100))
            offset = int(request.query_params.get('offset', 0))

            # Ограничиваем максимум
            if limit > 500:
                limit = 500
            if offset < 0:
                offset = 0

            messages = AdminChatService.get_room_messages(
                room_id=room_id,
                limit=limit,
                offset=offset
            )

            serializer = MessageSerializer(
                messages,
                many=True,
                context={'request': request}
            )

            # Получаем общее количество сообщений в комнате
            total_count = Message.objects.filter(room_id=room_id).count()

            return Response(
                {
                    'success': True,
                    'data': {
                        'room_id': room_id,
                        'messages': serializer.data,
                        'count': total_count,
                        'limit': limit,
                        'offset': offset
                    }
                },
                status=status.HTTP_200_OK
            )

        except ChatRoom.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': f'Комната с ID {room_id} не найдена'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        except ValueError as e:
            return Response(
                {
                    'success': False,
                    'error': 'Неверные параметры запроса (limit, offset должны быть числами)'
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        except Exception as e:
            logger.error(f"Error fetching messages for room {room_id}: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': 'Ошибка при получении сообщений'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminChatRoomDetailView(APIView):
    """
    GET /api/admin/chat/rooms/<room_id>/ - Детальная информация о комнате (admin only, read-only)

    Возвращает полную информацию о комнате: участники, зачисление, статистика.

    Permissions:
        - IsAdminUser (только staff/superuser)

    Response:
        200 OK:
            {
                "success": true,
                "data": {
                    "room": {...},
                    "participants_count": 5,
                    "messages_count": 157
                }
            }
        404 Not Found: Если комната не найдена
        403 Forbidden: Если не admin
    """
    permission_classes = [IsAdminUser]

    def get(self, request, room_id):
        """Получить детальную информацию о комнате"""
        try:
            room = AdminChatService.get_room_by_id(room_id)
            serializer = ChatRoomListSerializer(room, context={'request': request})

            return Response(
                {
                    'success': True,
                    'data': {
                        'room': serializer.data,
                        'participants_count': room.participants_count,
                        'messages_count': room.messages_count
                    }
                },
                status=status.HTTP_200_OK
            )

        except ChatRoom.DoesNotExist:
            return Response(
                {
                    'success': False,
                    'error': f'Комната с ID {room_id} не найдена'
                },
                status=status.HTTP_404_NOT_FOUND
            )

        except Exception as e:
            logger.error(f"Error fetching room detail {room_id}: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': 'Ошибка при получении информации о комнате'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AdminChatStatsView(APIView):
    """
    GET /api/admin/chat/stats/ - Общая статистика по чатам (admin only, read-only)

    Возвращает агрегированную статистику по всем чатам платформы.

    Permissions:
        - IsAdminUser (только staff/superuser)

    Response:
        200 OK:
            {
                "success": true,
                "data": {
                    "total_rooms": 42,
                    "active_rooms": 38,
                    "total_messages": 1543,
                    "forum_subject_rooms": 25,
                    "direct_rooms": 10,
                    "group_rooms": 7
                }
            }
        403 Forbidden: Если не admin
    """
    permission_classes = [IsAdminUser]

    def get(self, request):
        """Получить статистику по чатам"""
        try:
            stats = AdminChatService.get_chat_stats()

            return Response(
                {
                    'success': True,
                    'data': stats
                },
                status=status.HTTP_200_OK
            )

        except Exception as e:
            logger.error(f"Error fetching chat stats: {e}", exc_info=True)
            return Response(
                {
                    'success': False,
                    'error': 'Ошибка при получении статистики'
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
