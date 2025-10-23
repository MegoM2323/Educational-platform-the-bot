from django.db import models
from django.core.validators import EmailValidator
from django.utils import timezone


class Application(models.Model):
    """
    Модель заявки на обучение
    """
    class Status(models.TextChoices):
        NEW = 'new', 'Новая'
        PROCESSING = 'processing', 'В обработке'
        APPROVED = 'approved', 'Одобрена'
        REJECTED = 'rejected', 'Отклонена'
        COMPLETED = 'completed', 'Завершена'
    
    # Основная информация
    student_name = models.CharField(max_length=100, verbose_name='Имя ученика')
    parent_name = models.CharField(max_length=100, verbose_name='Имя родителя')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    email = models.EmailField(validators=[EmailValidator()], verbose_name='Email')
    
    # Образовательная информация
    grade = models.PositiveIntegerField(verbose_name='Класс')
    goal = models.CharField(max_length=500, blank=True, verbose_name='Образовательная цель')
    message = models.TextField(blank=True, verbose_name='Дополнительная информация')
    
    # Статус и обработка
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
        verbose_name='Статус'
    )
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    processed_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата обработки')
    
    # Дополнительные поля
    telegram_message_id = models.CharField(
        max_length=50, 
        blank=True, 
        null=True, 
        verbose_name='ID сообщения в Telegram'
    )
    notes = models.TextField(blank=True, verbose_name='Заметки администратора')
    
    class Meta:
        verbose_name = 'Заявка'
        verbose_name_plural = 'Заявки'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Заявка от {self.student_name} ({self.created_at.strftime('%d.%m.%Y')})"
    
    def save(self, *args, **kwargs):
        # Автоматически обновляем processed_at при изменении статуса
        if self.status != self.Status.NEW and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)
    
    @property
    def is_new(self):
        return self.status == self.Status.NEW
    
    @property
    def is_processed(self):
        return self.status in [self.Status.APPROVED, self.Status.REJECTED, self.Status.COMPLETED]
