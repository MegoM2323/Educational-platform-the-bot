from django.db import models
from django.contrib.auth import get_user_model

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
    
    class Meta:
        verbose_name = 'Уведомление'
        verbose_name_plural = 'Уведомления'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.recipient} - {self.title}"
    
    def mark_as_read(self):
        """Отметить как прочитанное"""
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save()


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
    
    # Время тишины
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