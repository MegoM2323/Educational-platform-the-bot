from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator

User = get_user_model()


class Assignment(models.Model):
    """
    Задания для студентов
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        PUBLISHED = 'published', 'Опубликовано'
        CLOSED = 'closed', 'Закрыто'
    
    class Type(models.TextChoices):
        HOMEWORK = 'homework', 'Домашнее задание'
        TEST = 'test', 'Тест'
        PROJECT = 'project', 'Проект'
        ESSAY = 'essay', 'Эссе'
        PRACTICAL = 'practical', 'Практическая работа'
    
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    instructions = models.TextField(verbose_name='Инструкции')
    
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_assignments',
        verbose_name='Автор'
    )
    
    type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.HOMEWORK,
        verbose_name='Тип'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус'
    )
    
    # Настройки задания
    max_score = models.PositiveIntegerField(
        default=100,
        verbose_name='Максимальный балл'
    )
    
    time_limit = models.PositiveIntegerField(
        blank=True,
        null=True,
        help_text='Время выполнения в минутах',
        verbose_name='Временной лимит'
    )
    
    attempts_limit = models.PositiveIntegerField(
        default=1,
        verbose_name='Лимит попыток'
    )
    
    # Назначение
    assigned_to = models.ManyToManyField(
        User,
        related_name='assigned_assignments',
        blank=True,
        verbose_name='Назначено'
    )
    
    # Временные рамки
    start_date = models.DateTimeField(verbose_name='Дата начала')
    due_date = models.DateTimeField(verbose_name='Срок сдачи')
    
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
    
    class Meta:
        verbose_name = 'Задание'
        verbose_name_plural = 'Задания'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_overdue(self):
        from django.utils import timezone
        return timezone.now() > self.due_date


class AssignmentSubmission(models.Model):
    """
    Ответы студентов на задания
    """
    class Status(models.TextChoices):
        SUBMITTED = 'submitted', 'Сдано'
        GRADED = 'graded', 'Оценено'
        RETURNED = 'returned', 'Возвращено на доработку'
    
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='submissions',
        verbose_name='Задание'
    )
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='assignment_submissions',
        verbose_name='Студент'
    )
    
    content = models.TextField(verbose_name='Ответ')
    
    # Файлы
    file = models.FileField(
        upload_to='assignments/submissions/',
        blank=True,
        null=True,
        verbose_name='Файл'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        verbose_name='Статус'
    )
    
    # Оценка
    score = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[MinValueValidator(0)],
        verbose_name='Балл'
    )
    
    max_score = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='Максимальный балл'
    )
    
    feedback = models.TextField(blank=True, verbose_name='Комментарий преподавателя')
    
    # Временные метки
    submitted_at = models.DateTimeField(auto_now_add=True)
    graded_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Ответ на задание'
        verbose_name_plural = 'Ответы на задания'
        unique_together = ['assignment', 'student']
        ordering = ['-submitted_at']
    
    def __str__(self):
        return f"{self.student} - {self.assignment}"
    
    @property
    def percentage(self):
        if self.max_score and self.score is not None:
            return round((self.score / self.max_score) * 100, 2)
        return None


class AssignmentQuestion(models.Model):
    """
    Вопросы в заданиях (для тестов)
    """
    class Type(models.TextChoices):
        SINGLE_CHOICE = 'single_choice', 'Один вариант'
        MULTIPLE_CHOICE = 'multiple_choice', 'Несколько вариантов'
        TEXT = 'text', 'Текстовый ответ'
        NUMBER = 'number', 'Числовой ответ'
    
    assignment = models.ForeignKey(
        Assignment,
        on_delete=models.CASCADE,
        related_name='questions',
        verbose_name='Задание'
    )
    
    question_text = models.TextField(verbose_name='Текст вопроса')
    question_type = models.CharField(
        max_length=20,
        choices=Type.choices,
        default=Type.SINGLE_CHOICE,
        verbose_name='Тип вопроса'
    )
    
    points = models.PositiveIntegerField(
        default=1,
        verbose_name='Баллы'
    )
    
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    
    # Для вопросов с вариантами ответов
    options = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Варианты ответов'
    )
    
    correct_answer = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Правильный ответ'
    )
    
    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        ordering = ['order']
    
    def __str__(self):
        return f"{self.assignment.title} - Вопрос {self.order}"


class AssignmentAnswer(models.Model):
    """
    Ответы студентов на вопросы
    """
    submission = models.ForeignKey(
        AssignmentSubmission,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='Ответ на задание'
    )
    
    question = models.ForeignKey(
        AssignmentQuestion,
        on_delete=models.CASCADE,
        related_name='answers',
        verbose_name='Вопрос'
    )
    
    answer_text = models.TextField(blank=True, verbose_name='Текстовый ответ')
    answer_choice = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Выбранные варианты'
    )
    
    is_correct = models.BooleanField(default=False, verbose_name='Правильный')
    points_earned = models.PositiveIntegerField(default=0, verbose_name='Заработанные баллы')
    
    class Meta:
        verbose_name = 'Ответ на вопрос'
        verbose_name_plural = 'Ответы на вопросы'
        unique_together = ['submission', 'question']
    
    def __str__(self):
        return f"{self.submission.student} - {self.question.question_text[:50]}"