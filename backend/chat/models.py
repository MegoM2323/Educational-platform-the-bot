from django.db import models
from django.db.models import Count, Q
from django.contrib.auth import get_user_model

User = get_user_model()


class ChatRoom(models.Model):
    """
    Чат-комнаты для общения
    """
    class Type(models.TextChoices):
        DIRECT = 'direct', 'Личный чат'
        GROUP = 'group', 'Групповой чат'
        SUPPORT = 'support', 'Поддержка'
        CLASS = 'class', 'Класс'
        GENERAL = 'general', 'Общий форум'
        FORUM_SUBJECT = 'forum_subject', 'Форум по предмету'
        FORUM_TUTOR = 'forum_tutor', 'Форум с тьютором'

    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.DIRECT,
        verbose_name='Тип'
    )

    # Связь с зачислением на предмет (для форума студент-преподаватель)
    enrollment = models.ForeignKey(
        'materials.SubjectEnrollment',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='forum_chats',
        verbose_name='Зачисление на предмет',
        help_text='Связь с зачислением студента на предмет (для forum_subject типа)'
    )
    
    participants = models.ManyToManyField(
        User,
        related_name='chat_rooms',
        verbose_name='Участники'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_rooms',
        verbose_name='Создатель'
    )
    
    is_active = models.BooleanField(default=True, verbose_name='Активен')
    
    # Автоудаление сообщений
    auto_delete_days = models.PositiveIntegerField(
        default=7,
        verbose_name='Дни до автоудаления сообщений',
        help_text='Сообщения старше указанного количества дней будут автоматически удалены'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Чат-комната'
        verbose_name_plural = 'Чат-комнаты'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['type', 'enrollment'], name='chat_type_enrollment_idx'),
            models.Index(fields=['type', 'is_active'], name='chat_type_active_idx'),
        ]
        # Предотвращение дубликатов при race conditions: один форум на (тип, зачисление)
        constraints = [
            models.UniqueConstraint(
                fields=['type', 'enrollment'],
                name='unique_forum_per_enrollment',
                condition=models.Q(enrollment__isnull=False)
            )
        ]
    
    def __str__(self):
        return self.name
    
    @property
    def last_message(self):
        return self.messages.filter(is_deleted=False).order_by('created_at').last()


class Message(models.Model):
    """
    Сообщения в чате
    """
    class Type(models.TextChoices):
        TEXT = 'text', 'Текст'
        IMAGE = 'image', 'Изображение'
        FILE = 'file', 'Файл'
        SYSTEM = 'system', 'Системное'
    
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='messages',
        verbose_name='Комната'
    )
    
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_messages',
        verbose_name='Отправитель'
    )
    
    content = models.TextField(blank=True, default='', verbose_name='Содержание')
    message_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.TEXT,
        verbose_name='Тип сообщения'
    )
    
    # Файлы
    file = models.FileField(
        upload_to='chat/files/',
        blank=True,
        null=True,
        verbose_name='Файл'
    )
    
    image = models.ImageField(
        upload_to='chat/images/',
        blank=True,
        null=True,
        verbose_name='Изображение'
    )
    
    # Метаданные
    is_edited = models.BooleanField(default=False, verbose_name='Отредактировано')
    reply_to = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='replies',
        verbose_name='Ответ на'
    )
    
    # Связь с тредом для форумного стиля
    thread = models.ForeignKey(
        'MessageThread',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='messages',
        verbose_name='Тред'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Soft delete fields
    is_deleted = models.BooleanField(default=False, verbose_name='Удалено')
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name='Время удаления')
    deleted_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='deleted_messages',
        verbose_name='Удалено пользователем'
    )

    class Meta:
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['is_deleted'], name='message_deleted_idx'),
            models.Index(fields=['room', 'is_deleted'], name='message_room_deleted_idx'),
            models.Index(fields=['room', 'created_at'], name='message_room_created_idx'),
        ]

    def __str__(self):
        return f"{self.sender} в {self.room}: {self.content[:50]}"

    def delete(self, using=None, keep_parents=False, deleted_by=None):
        """Soft delete - помечает сообщение как удалённое вместо удаления из БД"""
        from django.utils import timezone
        self.is_deleted = True
        self.deleted_at = timezone.now()
        if deleted_by:
            self.deleted_by = deleted_by
        self.save(update_fields=['is_deleted', 'deleted_at', 'deleted_by'])

    def hard_delete(self, using=None, keep_parents=False):
        """Hard delete - полное удаление из БД (только для админов)"""
        super().delete(using=using, keep_parents=keep_parents)


class MessageRead(models.Model):
    """
    Отметки о прочтении сообщений
    """
    message = models.ForeignKey(
        Message,
        on_delete=models.CASCADE,
        related_name='read_by',
        verbose_name='Сообщение'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='read_messages',
        verbose_name='Пользователь'
    )
    
    read_at = models.DateTimeField(auto_now_add=True, verbose_name='Прочитано')
    
    class Meta:
        verbose_name = 'Прочитанное сообщение'
        verbose_name_plural = 'Прочитанные сообщения'
        unique_together = ['message', 'user']
    
    def __str__(self):
        return f"{self.user} прочитал {self.message}"


class MessageThread(models.Model):
    """
    Треды сообщений для форумного стиля общения
    """
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='threads',
        verbose_name='Комната'
    )
    
    title = models.CharField(max_length=200, verbose_name='Заголовок треда')
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_threads',
        verbose_name='Создатель'
    )
    
    is_pinned = models.BooleanField(default=False, verbose_name='Закреплен')
    is_locked = models.BooleanField(default=False, verbose_name='Заблокирован')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Тред сообщений'
        verbose_name_plural = 'Треды сообщений'
        ordering = ['-is_pinned', '-updated_at']
    
    def __str__(self):
        return f"{self.title} в {self.room}"
    
    @property
    def messages_count(self):
        return self.messages.filter(is_deleted=False).count()

    @property
    def last_message(self):
        return self.messages.filter(is_deleted=False).order_by('created_at').last()


class ChatParticipant(models.Model):
    """
    Участники чата с дополнительной информацией
    """
    room = models.ForeignKey(
        ChatRoom,
        on_delete=models.CASCADE,
        related_name='room_participants',
        verbose_name='Комната'
    )
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='participant_rooms',
        verbose_name='Пользователь'
    )
    
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name='Присоединился')
    last_read_at = models.DateTimeField(blank=True, null=True, verbose_name='Последнее прочтение')
    is_muted = models.BooleanField(default=False, verbose_name='Заглушен')
    is_admin = models.BooleanField(default=False, verbose_name='Администратор')
    
    class Meta:
        verbose_name = 'Участник чата'
        verbose_name_plural = 'Участники чата'
        unique_together = ['room', 'user']
    
    def __str__(self):
        return f"{self.user} в {self.room}"

    @classmethod
    def with_unread_count(cls):
        """
        Возвращает queryset с аннотированным unread_count.
        Используйте для списков участников, чтобы избежать N+1 проблемы.

        Пример использования:
            participants = ChatParticipant.with_unread_count().filter(room=room)
            for p in participants:
                print(p.unread_count)  # Использует аннотацию, не делает запрос
        """
        from django.db.models.functions import Coalesce
        from django.db.models import Value

        return cls.objects.annotate(
            _annotated_unread_count=Count(
                'room__messages',
                filter=Q(
                    room__messages__is_deleted=False,
                    room__messages__created_at__gt=models.F('last_read_at')
                ) & ~Q(room__messages__sender=models.F('user'))
            )
        )

    @property
    def unread_count(self):
        """
        Возвращает количество непрочитанных сообщений.

        ВАЖНО: Для списков используйте ChatParticipant.with_unread_count()
        для получения queryset с аннотацией, чтобы избежать N+1 проблемы!
        """
        # Если есть аннотированное значение - используем его (для оптимизированных запросов)
        if hasattr(self, '_annotated_unread_count'):
            return self._annotated_unread_count

        # Fallback - делаем запрос (только для single object access)
        if self.last_read_at:
            return self.room.messages.filter(
                created_at__gt=self.last_read_at,
                is_deleted=False
            ).exclude(sender=self.user).count()
        return self.room.messages.filter(
            is_deleted=False
        ).exclude(sender=self.user).count()