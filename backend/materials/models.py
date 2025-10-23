from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator

User = get_user_model()


class Subject(models.Model):
    """
    Предметы/дисциплины
    """
    name = models.CharField(max_length=100, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    color = models.CharField(max_length=7, default='#3B82F6', verbose_name='Цвет')
    
    class Meta:
        verbose_name = 'Предмет'
        verbose_name_plural = 'Предметы'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Material(models.Model):
    """
    Учебные материалы
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        ACTIVE = 'active', 'Активно'
        ARCHIVED = 'archived', 'Архив'
    
    class Type(models.TextChoices):
        LESSON = 'lesson', 'Урок'
        PRESENTATION = 'presentation', 'Презентация'
        VIDEO = 'video', 'Видео'
        DOCUMENT = 'document', 'Документ'
        TEST = 'test', 'Тест'
        HOMEWORK = 'homework', 'Домашнее задание'
    
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    content = models.TextField(verbose_name='Содержание')
    
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='authored_materials',
        verbose_name='Автор'
    )
    
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='materials',
        verbose_name='Предмет'
    )
    
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.LESSON,
        verbose_name='Тип'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус'
    )
    
    # Файлы
    file = models.FileField(
        upload_to='materials/files/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt'])],
        verbose_name='Файл'
    )
    
    video_url = models.URLField(blank=True, verbose_name='Ссылка на видео')
    
    # Настройки доступа
    is_public = models.BooleanField(default=False, verbose_name='Публичный')
    assigned_to = models.ManyToManyField(
        User,
        related_name='assigned_materials',
        blank=True,
        verbose_name='Назначено'
    )
    
    # Метаданные
    tags = models.CharField(max_length=500, blank=True, verbose_name='Теги')
    difficulty_level = models.PositiveIntegerField(
        default=1,
        choices=[(i, f'Уровень {i}') for i in range(1, 6)],
        verbose_name='Уровень сложности'
    )
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Материал'
        verbose_name_plural = 'Материалы'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    def save(self, *args, **kwargs):
        if self.status == self.Status.ACTIVE and not self.published_at:
            from django.utils import timezone
            self.published_at = timezone.now()
        super().save(*args, **kwargs)


class MaterialProgress(models.Model):
    """
    Прогресс изучения материала студентом
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='material_progress',
        verbose_name='Студент'
    )
    
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='progress',
        verbose_name='Материал'
    )
    
    is_completed = models.BooleanField(default=False, verbose_name='Завершен')
    progress_percentage = models.PositiveIntegerField(default=0, verbose_name='Прогресс (%)')
    time_spent = models.PositiveIntegerField(default=0, verbose_name='Время изучения (мин)')
    
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    last_accessed = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Прогресс материала'
        verbose_name_plural = 'Прогресс материалов'
        unique_together = ['student', 'material']
    
    def __str__(self):
        return f"{self.student} - {self.material} ({self.progress_percentage}%)"


class MaterialComment(models.Model):
    """
    Комментарии к материалам
    """
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='Материал'
    )
    
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='material_comments',
        verbose_name='Автор'
    )
    
    content = models.TextField(verbose_name='Содержание')
    is_question = models.BooleanField(default=False, verbose_name='Вопрос')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Комментарий'
        verbose_name_plural = 'Комментарии'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Комментарий к {self.material} от {self.author}"