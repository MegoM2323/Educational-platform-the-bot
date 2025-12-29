from datetime import timedelta

from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

# Импортируем DeviceToken для регистрации в app notifications
from .channels.models import DeviceToken, UserPhoneNumber

User = get_user_model()


class Notification(models.Model):
    """
    Уведомления для пользователей
    """
    class Type(models.TextChoices):
        ASSIGNMENT_NEW = 'assignment_new', 'Новое задание'
        ASSIGNMENT_DUE = 'assignment_due', 'Срок сдачи задания'
        ASSIGNMENT_GRADED = 'assignment_graded', 'Задание оценено'
        MATERIAL_NEW = 'material_new', 'Новый материал'
        MESSAGE_NEW = 'message_new', 'Новое сообщение'
        REPORT_READY = 'report_ready', 'Отчет готов'
        PAYMENT_SUCCESS = 'payment_success', 'Платеж успешен'
        PAYMENT_FAILED = 'payment_failed', 'Платеж не прошел'
        SYSTEM = 'system', 'Системное уведомление'
        REMINDER = 'reminder', 'Напоминание'
        # Tutor/Student management system events
        STUDENT_CREATED = 'student_created', 'Ученик создан'
        SUBJECT_ASSIGNED = 'subject_assigned', 'Предмет назначен'
        MATERIAL_PUBLISHED = 'material_published', 'Материал опубликован'
        HOMEWORK_SUBMITTED = 'homework_submitted', 'Домашнее задание отправлено'
        PAYMENT_PROCESSED = 'payment_processed', 'Платеж обработан'
        # Invoice system events
        INVOICE_SENT = 'invoice_sent', 'Счет выставлен'
        INVOICE_PAID = 'invoice_paid', 'Счет оплачен'
        INVOICE_OVERDUE = 'invoice_overdue', 'Счет просрочен'
        INVOICE_VIEWED = 'invoice_viewed', 'Счет просмотрен'
    
    class Priority(models.TextChoices):
        LOW = 'low', 'Низкий'
        NORMAL = 'normal', 'Обычный'
        HIGH = 'high', 'Высокий'
        URGENT = 'urgent', 'Срочный'

    class Scope(models.TextChoices):
        USER = 'user', 'User-specific'
        SYSTEM = 'system', 'System-wide'
        ADMIN = 'admin', 'Admin-only'

    title = models.CharField(max_length=200, verbose_name='Заголовок')
    message = models.TextField(verbose_name='Сообщение')
    
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notifications',
        verbose_name='Получатель'
    )
    
    type = models.CharField(
        max_length=30,
        choices=Type.choices,
        default=Type.SYSTEM,
        verbose_name='Тип уведомления'
    )
    
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.NORMAL,
        verbose_name='Приоритет'
    )

    scope = models.CharField(
        max_length=20,
        choices=Scope.choices,
        default=Scope.USER,
        verbose_name='Scope (user/system/admin)',
        db_index=True
    )

    is_read = models.BooleanField(
        default=False,
        verbose_name='Прочитано'
    )
    
    is_sent = models.BooleanField(
        default=False,
        verbose_name='Отправлено'
    )
    
    # Связанные объекты
    related_object_type = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Тип связанного объекта'
    )
    
    related_object_id = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='ID связанного объекта'
    )
    
    # Дополнительные данные
    data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Дополнительные данные'
    )
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True, verbose_name='Прочитано')
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name='Отправлено')

    # Архивирование
    is_archived = models.BooleanField(
        default=False,
        verbose_name='Архивировано',
        db_index=True
    )
    archived_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Дата архивирования'
    )

    # Scheduling fields
    scheduled_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Запланировано на'
    )

    scheduled_status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Ожидает отправки'),
            ('sent', 'Отправлено'),
            ('cancelled', 'Отменено'),
        ],
        default='pending',
        verbose_name='Статус расписания'
    )

    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['recipient', 'is_archived', '-created_at']),
            models.Index(fields=['recipient', 'is_archived']),
            models.Index(fields=['scheduled_at', 'scheduled_status']),
            models.Index(fields=['recipient', 'scheduled_status']),
        ]
    
    def __str__(self):
        return f"{self.recipient} - {self.title}"
    
    def mark_as_read(self):
        """Отметить как прочитанное"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save()

    @classmethod
    def archived_notifications(cls, **filters):
        """Получить архивированные уведомления"""
        return cls.objects.filter(is_archived=True, **filters)


class NotificationTemplate(models.Model):
    """
    Шаблоны уведомлений
    """
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    type = models.CharField(
        max_length=30,
        choices=Notification.Type.choices,
        verbose_name='Тип уведомления'
    )
    
    title_template = models.CharField(
        max_length=200,
        verbose_name='Шаблон заголовка'
    )
    
    message_template = models.TextField(verbose_name='Шаблон сообщения')
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Шаблон уведомления'
        verbose_name_plural = 'Шаблоны уведомлений'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class NotificationSettings(models.Model):
    """
    Настройки уведомлений для пользователей
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='notification_settings',
        verbose_name='Пользователь'
    )
    
    # Настройки по типам уведомлений
    assignment_notifications = models.BooleanField(
        default=True,
        verbose_name='Уведомления о заданиях'
    )
    
    material_notifications = models.BooleanField(
        default=True,
        verbose_name='Уведомления о материалах'
    )
    
    message_notifications = models.BooleanField(
        default=True,
        verbose_name='Уведомления о сообщениях'
    )
    
    report_notifications = models.BooleanField(
        default=True,
        verbose_name='Уведомления об отчетах'
    )
    
    payment_notifications = models.BooleanField(
        default=True,
        verbose_name='Уведомления о платежах'
    )

    invoice_notifications = models.BooleanField(
        default=True,
        verbose_name='Уведомления о счетах'
    )

    system_notifications = models.BooleanField(
        default=True,
        verbose_name='Системные уведомления'
    )
    
    # Настройки каналов доставки
    email_notifications = models.BooleanField(
        default=True,
        verbose_name='Email уведомления'
    )
    
    push_notifications = models.BooleanField(
        default=True,
        verbose_name='Push уведомления'
    )
    
    sms_notifications = models.BooleanField(
        default=False,
        verbose_name='SMS уведомления'
    )

    # In-app notifications (always enabled by default)
    in_app_notifications = models.BooleanField(
        default=True,
        verbose_name='Уведомления в приложении'
    )

    # Время тишины
    quiet_hours_enabled = models.BooleanField(
        default=False,
        verbose_name='Включены тихие часы'
    )

    quiet_hours_start = models.TimeField(
        blank=True,
        null=True,
        verbose_name='Начало тихих часов'
    )

    quiet_hours_end = models.TimeField(
        blank=True,
        null=True,
        verbose_name='Конец тихих часов'
    )

    # Часовой пояс пользователя
    timezone = models.CharField(
        max_length=50,
        choices=[
            ('UTC', 'UTC'),
            ('US/Eastern', 'US/Eastern (EST)'),
            ('US/Central', 'US/Central (CST)'),
            ('US/Mountain', 'US/Mountain (MST)'),
            ('US/Pacific', 'US/Pacific (PST)'),
            ('Europe/London', 'Europe/London (GMT)'),
            ('Europe/Paris', 'Europe/Paris (CET)'),
            ('Europe/Moscow', 'Europe/Moscow (MSK)'),
            ('Asia/Tokyo', 'Asia/Tokyo (JST)'),
            ('Asia/Shanghai', 'Asia/Shanghai (CST)'),
            ('Asia/Hong_Kong', 'Asia/Hong_Kong (HKT)'),
            ('Asia/Bangkok', 'Asia/Bangkok (ICT)'),
            ('Australia/Sydney', 'Australia/Sydney (AEDT)'),
            ('Pacific/Auckland', 'Pacific/Auckland (NZDT)'),
        ],
        default='UTC',
        verbose_name='Часовой пояс'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Настройки уведомлений'
        verbose_name_plural = 'Настройки уведомлений'
    
    def __str__(self):
        return f"Настройки уведомлений для {self.user}"


class NotificationQueue(models.Model):
    """
    Очередь уведомлений для отправки
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает'
        PROCESSING = 'processing', 'Обрабатывается'
        SENT = 'sent', 'Отправлено'
        FAILED = 'failed', 'Ошибка'
        CANCELLED = 'cancelled', 'Отменено'
    
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='queue_entries',
        verbose_name='Уведомление'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус'
    )
    
    channel = models.CharField(
        max_length=20,
        choices=[
            ('email', 'Email'),
            ('push', 'Push'),
            ('sms', 'SMS'),
            ('in_app', 'В приложении'),
        ],
        verbose_name='Канал доставки'
    )
    
    scheduled_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Запланировано на'
    )
    
    attempts = models.PositiveIntegerField(
        default=0,
        verbose_name='Попытки отправки'
    )
    
    max_attempts = models.PositiveIntegerField(
        default=3,
        verbose_name='Максимум попыток'
    )
    
    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name='Обработано')
    
    class Meta:
        verbose_name = 'Запись очереди уведомлений'
        verbose_name_plural = 'Очередь уведомлений'
        ordering = ['scheduled_at', 'created_at']

    def __str__(self):
        return f"{self.notification} - {self.channel} ({self.status})"


class Broadcast(models.Model):
    """
    Массовая рассылка уведомлений для групп пользователей
    """
    class TargetGroup(models.TextChoices):
        ALL_STUDENTS = 'all_students', 'Все студенты'
        ALL_TEACHERS = 'all_teachers', 'Все преподаватели'
        ALL_TUTORS = 'all_tutors', 'Все тьюторы'
        ALL_PARENTS = 'all_parents', 'Все родители'
        BY_SUBJECT = 'by_subject', 'По предмету'
        BY_TUTOR = 'by_tutor', 'По тьютору'
        BY_TEACHER = 'by_teacher', 'По учителю'
        CUSTOM = 'custom', 'Кастомная группа'

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        SCHEDULED = 'scheduled', 'Запланирована'
        SENDING = 'sending', 'Отправляется'
        SENT = 'sent', 'Отправлена'
        COMPLETED = 'completed', 'Завершена'
        FAILED = 'failed', 'Ошибка'
        CANCELLED = 'cancelled', 'Отменена'

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='broadcasts',
        verbose_name='Создатель'
    )

    target_group = models.CharField(
        max_length=20,
        choices=TargetGroup.choices,
        verbose_name='Целевая группа'
    )

    target_filter = models.JSONField(
        default=dict,
        blank=True,
        help_text='Фильтры: {subject_id, tutor_id, teacher_id, user_ids}',
        verbose_name='Фильтр получателей'
    )

    message = models.TextField(
        max_length=1000,
        verbose_name='Сообщение'
    )

    recipient_count = models.IntegerField(
        default=0,
        verbose_name='Количество получателей'
    )

    sent_count = models.IntegerField(
        default=0,
        verbose_name='Количество отправленных'
    )

    failed_count = models.IntegerField(
        default=0,
        verbose_name='Количество неудачных'
    )

    error_log = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Лог ошибок при отправке',
        help_text='Список ошибок по получателям: [{"recipient_id": 123, "error": "Network error", "timestamp": "2024-01-01T00:00:00Z"}]'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус'
    )

    scheduled_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Запланирована на'
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Отправлена'
    )

    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Завершена'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Создана'
    )

    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Обновлена'
    )

    class Meta:
        verbose_name = 'Массовая рассылка'
        verbose_name_plural = 'Массовые рассылки'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['status', 'scheduled_at']),
        ]

    def __str__(self):
        return f"Broadcast #{self.id} - {self.get_target_group_display()} ({self.get_status_display()})"


class BroadcastRecipient(models.Model):
    """
    Отслеживание доставки рассылки конкретному получателю
    """
    broadcast = models.ForeignKey(
        Broadcast,
        on_delete=models.CASCADE,
        related_name='recipients',
        verbose_name='Рассылка'
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        verbose_name='Получатель'
    )

    telegram_sent = models.BooleanField(
        default=False,
        verbose_name='Отправлено в Telegram'
    )

    telegram_message_id = models.CharField(
        max_length=100,
        null=True,
        blank=True,
        verbose_name='ID сообщения в Telegram'
    )

    telegram_error = models.TextField(
        null=True,
        blank=True,
        verbose_name='Ошибка отправки в Telegram'
    )

    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Отправлено'
    )

    class Meta:
        verbose_name = 'Получатель рассылки'
        verbose_name_plural = 'Получатели рассылок'
        unique_together = ('broadcast', 'recipient')
        indexes = [
            models.Index(fields=['broadcast', 'telegram_sent']),
            models.Index(fields=['recipient', 'broadcast']),
        ]

    def __str__(self):
        return f"BroadcastRecipient: {self.recipient.email} <- {self.broadcast.id}"


class NotificationClick(models.Model):
    """
    Отслеживание кликов по уведомлениям для аналитики.

    Когда пользователь кликает по уведомлению (в приложении или по ссылке в email),
    создается запись в этой таблице для подсчета click rate.
    """
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='clicks',
        verbose_name='Уведомление'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_clicks',
        verbose_name='Пользователь'
    )

    action_type = models.CharField(
        max_length=50,
        choices=[
            ('link_click', 'Клик по ссылке'),
            ('in_app_click', 'Клик в приложении'),
            ('email_click', 'Клик в email'),
            ('button_click', 'Клик по кнопке'),
        ],
        default='link_click',
        verbose_name='Тип действия'
    )

    # URL или идентификатор действия
    action_url = models.URLField(
        blank=True,
        null=True,
        verbose_name='URL действия'
    )

    action_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Дополнительные данные действия'
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='IP адрес'
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата клика'
    )

    class Meta:
        verbose_name = 'Клик по уведомлению'
        verbose_name_plural = 'Клики по уведомлениям'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['notification', 'created_at']),
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['notification', 'user']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"Click: {self.user.email} -> {self.notification.id}"


class PushDeliveryLog(models.Model):
    """
    Лог отправки push-уведомлений через Firebase Cloud Messaging.

    Отслеживает статус доставки push-уведомлений на устройства пользователей,
    включая попытки отправки, ошибки и результаты.
    """

    class DeliveryStatus(models.TextChoices):
        PENDING = 'pending', 'В ожидании'
        SENT = 'sent', 'Отправлено'
        DELIVERED = 'delivered', 'Доставлено'
        FAILED = 'failed', 'Ошибка'
        PARTIAL = 'partial', 'Частичная доставка'
        SKIPPED = 'skipped', 'Пропущено'

    # Основные поля
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='push_delivery_logs',
        verbose_name='Уведомление'
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='push_delivery_logs',
        verbose_name='Получатель'
    )

    device_token = models.ForeignKey(
        'notifications.DeviceToken',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='delivery_logs',
        verbose_name='Токен устройства'
    )

    status = models.CharField(
        max_length=20,
        choices=DeliveryStatus.choices,
        default=DeliveryStatus.PENDING,
        verbose_name='Статус доставки',
        db_index=True
    )

    # Детали попытки
    attempt_number = models.PositiveIntegerField(
        default=1,
        verbose_name='Номер попытки'
    )

    max_attempts = models.PositiveIntegerField(
        default=3,
        verbose_name='Максимум попыток'
    )

    # Результаты
    success = models.BooleanField(
        default=False,
        verbose_name='Успешно отправлено',
        db_index=True
    )

    error_message = models.TextField(
        blank=True,
        verbose_name='Сообщение об ошибке'
    )

    error_code = models.CharField(
        max_length=50,
        blank=True,
        verbose_name='Код ошибки',
        help_text='Firebase error code (INVALID_ARGUMENT, NOT_FOUND, etc.)'
    )

    fcm_message_id = models.CharField(
        max_length=255,
        blank=True,
        verbose_name='FCM Message ID',
        help_text='ID сообщения от Firebase'
    )

    # Метаданные
    device_type = models.CharField(
        max_length=20,
        choices=[
            ('ios', 'iOS'),
            ('android', 'Android'),
            ('web', 'Web'),
        ],
        blank=True,
        verbose_name='Тип устройства'
    )

    payload_size = models.PositiveIntegerField(
        default=0,
        verbose_name='Размер payload (bytes)'
    )

    # Временные метки
    sent_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Отправлено'
    )

    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Доставлено'
    )

    retry_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Следующая попытка'
    )

    class Meta:
        verbose_name = 'Лог доставки push'
        verbose_name_plural = 'Логи доставки push'
        ordering = ['-sent_at']
        indexes = [
            models.Index(fields=['notification', 'user']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['notification', 'status']),
            models.Index(fields=['success', 'sent_at']),
            models.Index(fields=['-sent_at']),
        ]

    def __str__(self):
        return (f"Push delivery {self.notification.id} to {self.user.email} "
                f"({self.get_status_display()})")

    def mark_delivered(self, fcm_message_id: str = ''):
        """Отметить как доставленное."""
        self.status = self.DeliveryStatus.DELIVERED
        self.success = True
        self.delivered_at = timezone.now()
        if fcm_message_id:
            self.fcm_message_id = fcm_message_id
        self.save()

    def mark_failed(self, error_message: str, error_code: str = ''):
        """Отметить как не удачное."""
        from django.utils import timezone
        self.status = self.DeliveryStatus.FAILED
        self.success = False
        self.error_message = error_message
        if error_code:
            self.error_code = error_code

        # Планируем повторную попытку если есть оставшиеся попытки
        if self.attempt_number < self.max_attempts:
            self.retry_at = timezone.now() + timedelta(minutes=5 * self.attempt_number)

        self.save()

class NotificationUnsubscribe(models.Model):
    """
    GDPR-compliant tracking of user unsubscribe requests.
    
    Records:
    - User ID and email (for GDPR purposes)
    - What notification types were unsubscribed
    - What channels were affected
    - When the unsubscribe occurred
    - IP address and user agent (for audit trail)
    """
    
    class Channel(models.TextChoices):
        EMAIL = 'email', 'Email'
        PUSH = 'push', 'Push notifications'
        SMS = 'sms', 'SMS'
        ALL = 'all', 'All channels'
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='notification_unsubscribes',
        verbose_name='User'
    )
    
    notification_types = models.JSONField(
        default=list,
        blank=True,
        help_text='List of notification types unsubscribed from (e.g., [assignments, materials])',
        verbose_name='Notification types'
    )
    
    channel = models.CharField(
        max_length=10,
        choices=Channel.choices,
        default=Channel.EMAIL,
        verbose_name='Channel'
    )
    
    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='IP address'
    )
    
    user_agent = models.TextField(
        blank=True,
        verbose_name='User agent'
    )
    
    token_used = models.BooleanField(
        default=False,
        help_text='Whether unsubscribe was done via secure token link',
        verbose_name='Token-based unsubscribe'
    )
    
    reason = models.TextField(
        blank=True,
        help_text='User reason for unsubscribing (if provided)',
        verbose_name='Reason'
    )
    
    unsubscribed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Unsubscribed at'
    )
    
    resubscribed_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text='When user re-enabled notifications (if applicable)',
        verbose_name='Resubscribed at'
    )
    
    class Meta:
        verbose_name = 'Notification unsubscribe'
        verbose_name_plural = 'Notification unsubscribes'
        ordering = ['-unsubscribed_at']
        indexes = [
            models.Index(fields=['user', '-unsubscribed_at']),
            models.Index(fields=['channel', '-unsubscribed_at']),
            models.Index(fields=['-unsubscribed_at']),
            models.Index(fields=['user', 'resubscribed_at']),
        ]
    
    def __str__(self):
        types_str = ', '.join(self.notification_types) if self.notification_types else 'all'
        return f"{self.user.email} unsubscribed from {types_str} via {self.channel}"
    
    def is_active(self):
        """Check if unsubscribe is still active (not resubscribed)"""
        return self.resubscribed_at is None
