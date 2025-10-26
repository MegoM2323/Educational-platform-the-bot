from django.db import transaction
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import logging
from .models import ChatRoom, Message, MessageThread, ChatParticipant
from materials.cache_utils import cache_chat_data, ChatCacheManager

logger = logging.getLogger(__name__)
User = get_user_model()


class GeneralChatService:
    """
    Сервис для управления общим чатом-форумом
    """
    
    @staticmethod
    def get_or_create_general_chat():
        """
        Получить или создать общий чат-форум
        """
        # Получаем первого учителя для создания чата
        teacher = User.objects.filter(role=User.Role.TEACHER).first()
        if not teacher:
            # Если нет учителей, создаем системного пользователя
            teacher = User.objects.filter(is_superuser=True).first()
            if not teacher:
                raise ValueError("Нет пользователей с правами для создания общего чата")
        
        general_chat, created = ChatRoom.objects.get_or_create(
            type=ChatRoom.Type.GENERAL,
            defaults={
                'name': 'Общий форум',
                'description': 'Общий чат для общения студентов и преподавателей',
                'is_active': True,
                'created_by': teacher,
                'auto_delete_days': 7  # Автоудаление через 7 дней
            }
        )
        
        if created:
            # Автоматически добавляем всех учителей и студентов в общий чат
            GeneralChatService._add_all_teachers_and_students(general_chat)
        
        return general_chat
    
    @staticmethod
    def _add_all_teachers_and_students(chat_room):
        """
        Добавить всех учителей и студентов в общий чат
        """
        teachers_and_students = User.objects.filter(
            role__in=[User.Role.TEACHER, User.Role.STUDENT]
        )
        
        for user in teachers_and_students:
            chat_room.participants.add(user)
            # Создаем запись участника с правами администратора для учителей
            ChatParticipant.objects.get_or_create(
                room=chat_room,
                user=user,
                defaults={
                    'is_admin': user.role == User.Role.TEACHER,
                    'joined_at': timezone.now()
                }
            )
    
    @staticmethod
    def cleanup_old_messages():
        """
        Очистить старые сообщения во всех чатах согласно их настройкам auto_delete_days
        """
        try:
            total_deleted = 0
            
            # Получаем все активные чат-комнаты
            chat_rooms = ChatRoom.objects.filter(is_active=True)
            
            for room in chat_rooms:
                cutoff_date = timezone.now() - timedelta(days=room.auto_delete_days)
                
                # Удаляем сообщения старше указанного периода
                deleted_count = Message.objects.filter(
                    room=room,
                    created_at__lt=cutoff_date
                ).count()
                
                Message.objects.filter(
                    room=room,
                    created_at__lt=cutoff_date
                ).delete()
                
                total_deleted += deleted_count
                
                if deleted_count > 0:
                    logger.info(
                        f"Удалено {deleted_count} сообщений из чата '{room.name}' "
                        f"(старее {room.auto_delete_days} дней)"
                    )
            
            logger.info(f"Завершена очистка старых сообщений. Всего удалено: {total_deleted}")
            return total_deleted
            
        except Exception as e:
            logger.error(f"Ошибка при очистке старых сообщений: {str(e)}")
            raise
    
    @staticmethod
    def cleanup_old_general_chat_messages():
        """
        Очистить старые сообщения в общем чате (удобный метод для периодической задачи)
        """
        try:
            general_chat = GeneralChatService.get_or_create_general_chat()
            cutoff_date = timezone.now() - timedelta(days=general_chat.auto_delete_days)
            
            deleted_count = Message.objects.filter(
                room=general_chat,
                created_at__lt=cutoff_date
            ).count()
            
            Message.objects.filter(
                room=general_chat,
                created_at__lt=cutoff_date
            ).delete()
            
            logger.info(
                f"Удалено {deleted_count} сообщений из общего чата "
                f"(старее {general_chat.auto_delete_days} дней)"
            )
            
            return deleted_count
            
        except Exception as e:
            logger.error(f"Ошибка при очистке сообщений общего чата: {str(e)}")
            raise
    
    @staticmethod
    def add_user_to_general_chat(user):
        """
        Добавить пользователя в общий чат
        """
        if user.role not in [User.Role.TEACHER, User.Role.STUDENT]:
            return False
        
        general_chat = GeneralChatService.get_or_create_general_chat()
        
        if not general_chat.participants.filter(id=user.id).exists():
            general_chat.participants.add(user)
            ChatParticipant.objects.get_or_create(
                room=general_chat,
                user=user,
                defaults={
                    'is_admin': user.role == User.Role.TEACHER,
                    'joined_at': timezone.now()
                }
            )
            return True
        
        return False
    
    @staticmethod
    def create_thread(room, title, created_by):
        """
        Создать новый тред в чате
        """
        if not room.participants.filter(id=created_by.id).exists():
            raise PermissionError("Пользователь не является участником чата")
        
        thread = MessageThread.objects.create(
            room=room,
            title=title,
            created_by=created_by
        )
        return thread
    
    @staticmethod
    def send_message_to_thread(room, thread, sender, content, message_type=Message.Type.TEXT):
        """
        Отправить сообщение в тред
        """
        if not room.participants.filter(id=sender.id).exists():
            raise PermissionError("Пользователь не является участником чата")
        
        if thread.is_locked and not GeneralChatService._can_moderate(sender, room):
            raise PermissionError("Тред заблокирован")
        
        message = Message.objects.create(
            room=room,
            thread=thread,
            sender=sender,
            content=content,
            message_type=message_type
        )
        
        # Обновляем время последнего обновления треда
        thread.updated_at = timezone.now()
        thread.save(update_fields=['updated_at'])
        
        return message
    
    @staticmethod
    def send_general_message(sender, content, message_type=Message.Type.TEXT):
        """
        Отправить сообщение в общий чат без треда
        """
        general_chat = GeneralChatService.get_or_create_general_chat()
        
        if not general_chat.participants.filter(id=sender.id).exists():
            raise PermissionError("Пользователь не является участником общего чата")
        
        message = Message.objects.create(
            room=general_chat,
            sender=sender,
            content=content,
            message_type=message_type
        )
        
        return message
    
    @staticmethod
    def get_thread_messages(thread, limit=50, offset=0):
        """
        Получить сообщения треда с пагинацией
        """
        return thread.messages.all()[offset:offset + limit]
    
    @staticmethod
    @cache_chat_data(timeout=60)  # 1 минута
    def get_general_chat_messages(limit=50, offset=0):
        """
        Получить сообщения общего чата с пагинацией
        """
        general_chat = GeneralChatService.get_or_create_general_chat()
        return general_chat.messages.filter(thread__isnull=True)[offset:offset + limit]
    
    @staticmethod
    @cache_chat_data(timeout=300)  # 5 минут
    def get_general_chat_threads(limit=20, offset=0):
        """
        Получить треды общего чата с пагинацией
        """
        general_chat = GeneralChatService.get_or_create_general_chat()
        return general_chat.threads.all()[offset:offset + limit]
    
    @staticmethod
    def pin_thread(thread, user):
        """
        Закрепить тред (только для модераторов)
        """
        if not GeneralChatService._can_moderate(user, thread.room):
            raise PermissionError("Недостаточно прав для закрепления треда")
        
        thread.is_pinned = True
        thread.save(update_fields=['is_pinned'])
        return thread
    
    @staticmethod
    def unpin_thread(thread, user):
        """
        Открепить тред (только для модераторов)
        """
        if not GeneralChatService._can_moderate(user, thread.room):
            raise PermissionError("Недостаточно прав для открепления треда")
        
        thread.is_pinned = False
        thread.save(update_fields=['is_pinned'])
        return thread
    
    @staticmethod
    def lock_thread(thread, user):
        """
        Заблокировать тред (только для модераторов)
        """
        if not GeneralChatService._can_moderate(user, thread.room):
            raise PermissionError("Недостаточно прав для блокировки треда")
        
        thread.is_locked = True
        thread.save(update_fields=['is_locked'])
        return thread
    
    @staticmethod
    def unlock_thread(thread, user):
        """
        Разблокировать тред (только для модераторов)
        """
        if not GeneralChatService._can_moderate(user, thread.room):
            raise PermissionError("Недостаточно прав для разблокировки треда")
        
        thread.is_locked = False
        thread.save(update_fields=['is_locked'])
        return thread
    
    @staticmethod
    def _can_moderate(user, room):
        """
        Проверить, может ли пользователь модерировать чат
        """
        try:
            participant = room.room_participants.get(user=user)
            return participant.is_admin or user.role == User.Role.TEACHER
        except ChatParticipant.DoesNotExist:
            return False
    
    @staticmethod
    def get_user_role_in_chat(user, room):
        """
        Получить роль пользователя в чате
        """
        try:
            participant = room.room_participants.get(user=user)
            if participant.is_admin:
                return 'admin'
            return user.role
        except ChatParticipant.DoesNotExist:
            return None
