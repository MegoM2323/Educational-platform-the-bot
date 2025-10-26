from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import FileExtensionValidator, MinValueValidator, MaxValueValidator
from django.core.exceptions import ValidationError

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


class SubjectEnrollment(models.Model):
    """
    Зачисление студента на предмет
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='subject_enrollments',
        verbose_name='Студент'
    )
    
    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name='enrollments',
        verbose_name='Предмет'
    )
    
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='taught_subjects',
        verbose_name='Преподаватель'
    )
    
    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата зачисления')
    is_active = models.BooleanField(default=True, verbose_name='Активно')
    
    class Meta:
        verbose_name = 'Зачисление на предмет'
        verbose_name_plural = 'Зачисления на предметы'
        unique_together = ['student', 'subject']
        ordering = ['-enrolled_at']
    
    def __str__(self):
        return f"{self.student} - {self.subject} ({self.teacher})"


class SubjectPayment(models.Model):
    """
    Платежи по предметам
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Ожидает оплаты'
        PAID = 'paid', 'Оплачен'
        EXPIRED = 'expired', 'Просрочен'
        REFUNDED = 'refunded', 'Возвращен'
    
    enrollment = models.ForeignKey(
        SubjectEnrollment,
        on_delete=models.CASCADE,
        related_name='payments',
        verbose_name='Зачисление'
    )
    
    payment = models.ForeignKey(
        'payments.Payment',
        on_delete=models.CASCADE,
        related_name='subject_payments',
        verbose_name='Платеж'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Сумма'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name='Статус'
    )
    
    due_date = models.DateTimeField(verbose_name='Срок оплаты')
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name='Дата оплаты')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Платеж по предмету'
        verbose_name_plural = 'Платежи по предметам'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Платеж {self.enrollment.student} - {self.enrollment.subject} ({self.amount})"


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


def validate_submission_file(file):
    """Валидация файлов ответов учеников"""
    max_size = 10 * 1024 * 1024  # 10MB
    allowed_types = ['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'zip', 'rar']
    
    if file.size > max_size:
        raise ValidationError('Файл слишком большой (максимум 10MB)')
    
    ext = file.name.split('.')[-1].lower()
    if ext not in allowed_types:
        raise ValidationError(f'Неподдерживаемый тип файла. Разрешены: {", ".join(allowed_types)}')


class MaterialSubmission(models.Model):
    """
    Ответы учеников на материалы
    """
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Отправлено'
        REVIEWED = 'reviewed', 'Проверено'
        RETURNED = 'returned', 'Возвращено на доработку'
    
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name='Материал'
    )
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name='Студент'
    )
    
    submission_file = models.FileField(
        upload_to='submissions/',
        blank=True,
        null=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx', 'txt', 'jpg', 'jpeg', 'png', 'zip', 'rar'])],
        verbose_name='Файл ответа'
    )
    
    submission_text = models.TextField(
        blank=True,
        verbose_name='Текстовый ответ'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        verbose_name='Статус'
    )
    
    is_late = models.BooleanField(default=False, verbose_name='С опозданием')
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата отправки')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Ответ на материал'
        verbose_name_plural = 'Ответы на материалы'
        unique_together = ['material', 'student']
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"Ответ {self.student} на {self.material}"
    
    def clean(self):
        if not self.submission_file and not self.submission_text:
            raise ValidationError('Необходимо предоставить либо файл, либо текстовый ответ')
        
        if self.submission_file:
            validate_submission_file(self.submission_file)


class MaterialFeedback(models.Model):
    """
    Фидбэк преподавателей на ответы учеников
    """
    submission = models.OneToOneField(
        MaterialSubmission,
        on_delete=models.CASCADE,
        related_name='feedback',
        verbose_name='Ответ'
    )
    
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='given_feedback',
        verbose_name='Преподаватель'
    )
    
    feedback_text = models.TextField(verbose_name='Текст фидбэка')
    grade = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='Оценка'
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Фидбэк по материалу'
        verbose_name_plural = 'Фидбэки по материалам'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Фидбэк для {self.submission.student} по {self.submission.material}"