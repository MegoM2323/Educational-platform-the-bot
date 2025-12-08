from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import json

User = get_user_model()


# ============================================
# T101: Element and Lesson Models
# ============================================

class Element(models.Model):
    """
    Базовый строительный блок образовательного контента
    """
    ELEMENT_TYPES = (
        ('text_problem', 'Текстовая задача'),
        ('quick_question', 'Быстрый вопрос'),
        ('theory', 'Теория'),
        ('video', 'Видео'),
    )

    # Основные поля
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    element_type = models.CharField(
        max_length=20,
        choices=ELEMENT_TYPES,
        verbose_name='Тип элемента'
    )

    # Содержимое элемента (JSON для гибкости)
    content = models.JSONField(
        verbose_name='Содержимое',
        help_text='Структура зависит от типа элемента'
    )

    # Параметры элемента
    difficulty = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        default=5,
        verbose_name='Сложность (1-10)'
    )
    estimated_time_minutes = models.IntegerField(
        validators=[MinValueValidator(1)],
        default=5,
        verbose_name='Время выполнения (минуты)'
    )
    max_score = models.IntegerField(
        default=100,
        verbose_name='Максимальный балл'
    )

    # Метаданные
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Теги'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_elements',
        verbose_name='Автор'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Флаг публичности
    is_public = models.BooleanField(
        default=False,
        verbose_name='Доступен всем учителям'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['element_type']),
            models.Index(fields=['created_by']),
            models.Index(fields=['difficulty']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Элемент'
        verbose_name_plural = 'Элементы'

    def __str__(self):
        return f"{self.title} ({self.get_element_type_display()})"


class Lesson(models.Model):
    """
    Урок - последовательность элементов
    """
    title = models.CharField(max_length=200, verbose_name='Название урока')
    description = models.TextField(verbose_name='Описание урока')

    # Элементы урока через промежуточную модель
    elements = models.ManyToManyField(
        Element,
        through='LessonElement',
        related_name='lessons',
        verbose_name='Элементы'
    )

    # Метаданные
    subject = models.ForeignKey(
        'materials.Subject',
        on_delete=models.CASCADE,
        related_name='knowledge_lessons',
        verbose_name='Предмет'
    )
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_lessons',
        verbose_name='Автор'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Флаг публичности
    is_public = models.BooleanField(
        default=False,
        verbose_name='Доступен всем учителям'
    )

    # Вычисляемые поля (кешируются)
    total_duration_minutes = models.IntegerField(
        default=0,
        verbose_name='Общая продолжительность (минуты)'
    )
    total_max_score = models.IntegerField(
        default=0,
        verbose_name='Максимальный общий балл'
    )

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['subject']),
            models.Index(fields=['created_by']),
            models.Index(fields=['-created_at']),
        ]
        verbose_name = 'Урок'
        verbose_name_plural = 'Уроки'

    def __str__(self):
        return self.title

    def recalculate_totals(self):
        """Пересчитать общую продолжительность и баллы"""
        elements = self.elements.through.objects.filter(lesson=self).select_related('element')
        self.total_duration_minutes = sum(le.element.estimated_time_minutes for le in elements)
        self.total_max_score = sum(le.element.max_score for le in elements)
        self.save(update_fields=['total_duration_minutes', 'total_max_score'])


class LessonElement(models.Model):
    """
    Связь урока с элементом (с порядком)
    """
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        verbose_name='Урок'
    )
    element = models.ForeignKey(
        Element,
        on_delete=models.CASCADE,
        verbose_name='Элемент'
    )
    order = models.IntegerField(
        verbose_name='Порядок в уроке'
    )

    # Опциональные настройки для элемента в контексте урока
    is_optional = models.BooleanField(
        default=False,
        verbose_name='Необязательный элемент'
    )
    custom_instructions = models.TextField(
        blank=True,
        verbose_name='Дополнительные инструкции'
    )

    class Meta:
        ordering = ['lesson', 'order']
        unique_together = [
            ['lesson', 'element'],
            ['lesson', 'order'],
        ]
        indexes = [
            models.Index(fields=['lesson', 'order']),
        ]
        verbose_name = 'Элемент урока'
        verbose_name_plural = 'Элементы уроков'

    def __str__(self):
        return f"{self.lesson.title} - {self.order}. {self.element.title}"


# ============================================
# T102: Knowledge Graph Models
# ============================================

class KnowledgeGraph(models.Model):
    """
    Граф знаний для студента по предмету
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='knowledge_graphs',
        limit_choices_to={'role': 'student'},
        verbose_name='Студент'
    )
    subject = models.ForeignKey(
        'materials.Subject',
        on_delete=models.CASCADE,
        related_name='knowledge_graphs',
        verbose_name='Предмет'
    )

    # Уроки в графе через промежуточную модель
    lessons = models.ManyToManyField(
        Lesson,
        through='GraphLesson',
        related_name='graphs',
        verbose_name='Уроки'
    )

    # Метаданные
    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='created_graphs',
        verbose_name='Создан учителем'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Настройки графа
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активен'
    )
    allow_skip = models.BooleanField(
        default=False,
        verbose_name='Разрешить пропуск уроков'
    )

    class Meta:
        ordering = ['student', 'subject']
        unique_together = [['student', 'subject']]
        indexes = [
            models.Index(fields=['student', 'subject']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = 'Граф знаний'
        verbose_name_plural = 'Графы знаний'

    def __str__(self):
        return f"Граф: {self.student.get_full_name()} - {self.subject.name}"


class GraphLesson(models.Model):
    """
    Урок в графе знаний с позицией для визуализации
    """
    graph = models.ForeignKey(
        KnowledgeGraph,
        on_delete=models.CASCADE,
        verbose_name='Граф'
    )
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        verbose_name='Урок'
    )

    # Позиция для визуализации (координаты на canvas)
    position_x = models.FloatField(
        default=0,
        verbose_name='Позиция X'
    )
    position_y = models.FloatField(
        default=0,
        verbose_name='Позиция Y'
    )

    # Метаданные узла
    is_unlocked = models.BooleanField(
        default=False,
        verbose_name='Разблокирован'
    )
    unlocked_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время разблокировки'
    )

    # Визуальные настройки
    node_color = models.CharField(
        max_length=7,
        default='#4F46E5',
        verbose_name='Цвет узла'
    )
    node_size = models.IntegerField(
        default=50,
        verbose_name='Размер узла'
    )

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['graph', 'added_at']
        unique_together = [['graph', 'lesson']]
        indexes = [
            models.Index(fields=['graph', 'lesson']),
            models.Index(fields=['is_unlocked']),
        ]
        verbose_name = 'Урок в графе'
        verbose_name_plural = 'Уроки в графах'

    def __str__(self):
        return f"{self.graph} - {self.lesson.title}"

    def unlock(self):
        """Разблокировать урок"""
        if not self.is_unlocked:
            self.is_unlocked = True
            self.unlocked_at = timezone.now()
            self.save(update_fields=['is_unlocked', 'unlocked_at'])


class LessonDependency(models.Model):
    """
    Зависимость между уроками (ребро графа)
    """
    graph = models.ForeignKey(
        KnowledgeGraph,
        on_delete=models.CASCADE,
        related_name='dependencies',
        verbose_name='Граф'
    )
    from_lesson = models.ForeignKey(
        GraphLesson,
        on_delete=models.CASCADE,
        related_name='outgoing_dependencies',
        verbose_name='Предыдущий урок'
    )
    to_lesson = models.ForeignKey(
        GraphLesson,
        on_delete=models.CASCADE,
        related_name='incoming_dependencies',
        verbose_name='Следующий урок'
    )

    # Тип зависимости
    DEPENDENCY_TYPES = (
        ('required', 'Обязательная'),
        ('recommended', 'Рекомендованная'),
        ('optional', 'Опциональная'),
    )
    dependency_type = models.CharField(
        max_length=20,
        choices=DEPENDENCY_TYPES,
        default='required',
        verbose_name='Тип зависимости'
    )

    # Условие для разблокировки
    min_score_percent = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Минимальный процент для разблокировки'
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['graph', 'from_lesson', 'to_lesson']
        unique_together = [['graph', 'from_lesson', 'to_lesson']]
        indexes = [
            models.Index(fields=['graph']),
            models.Index(fields=['from_lesson']),
            models.Index(fields=['to_lesson']),
        ]
        verbose_name = 'Зависимость уроков'
        verbose_name_plural = 'Зависимости уроков'

    def __str__(self):
        return f"{self.from_lesson.lesson.title} -> {self.to_lesson.lesson.title}"


# ============================================
# T103: Progress Tracking Models
# ============================================

class ElementProgress(models.Model):
    """
    Прогресс студента по элементу
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='element_progress',
        verbose_name='Студент'
    )
    element = models.ForeignKey(
        Element,
        on_delete=models.CASCADE,
        related_name='student_progress',
        verbose_name='Элемент'
    )
    graph_lesson = models.ForeignKey(
        GraphLesson,
        on_delete=models.CASCADE,
        related_name='element_progress',
        verbose_name='Урок в графе'
    )

    # Ответ студента (JSON для разных типов)
    answer = models.JSONField(
        null=True,
        blank=True,
        verbose_name='Ответ'
    )

    # Оценка
    score = models.IntegerField(
        null=True,
        blank=True,
        verbose_name='Баллы'
    )
    max_score = models.IntegerField(
        verbose_name='Максимальный балл'
    )

    # Статус
    STATUS_CHOICES = (
        ('not_started', 'Не начат'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершён'),
        ('skipped', 'Пропущен'),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started',
        verbose_name='Статус'
    )

    # Временные метки
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время начала'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время завершения'
    )
    time_spent_seconds = models.IntegerField(
        default=0,
        verbose_name='Затрачено времени (секунды)'
    )

    # Попытки
    attempts = models.IntegerField(
        default=0,
        verbose_name='Количество попыток'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['graph_lesson', 'created_at']
        unique_together = [['student', 'element', 'graph_lesson']]
        indexes = [
            models.Index(fields=['student', 'element']),
            models.Index(fields=['graph_lesson']),
            models.Index(fields=['status']),
            models.Index(fields=['-updated_at']),
        ]
        verbose_name = 'Прогресс по элементу'
        verbose_name_plural = 'Прогресс по элементам'

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.element.title} ({self.get_status_display()})"

    def start(self):
        """Начать выполнение элемента"""
        if self.status == 'not_started':
            self.status = 'in_progress'
            self.started_at = timezone.now()
            self.attempts += 1
            self.save(update_fields=['status', 'started_at', 'attempts'])

    def complete(self, answer, score=None):
        """Завершить выполнение элемента"""
        self.answer = answer
        self.score = score
        self.status = 'completed'
        self.completed_at = timezone.now()

        if self.started_at:
            self.time_spent_seconds = (self.completed_at - self.started_at).total_seconds()

        self.save(update_fields=['answer', 'score', 'status', 'completed_at', 'time_spent_seconds'])

    @property
    def score_percent(self):
        """Процент выполнения"""
        if self.score is not None and self.max_score > 0:
            return round((self.score / self.max_score) * 100)
        return 0


class LessonProgress(models.Model):
    """
    Прогресс студента по уроку
    """
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='lesson_progress',
        verbose_name='Студент'
    )
    graph_lesson = models.ForeignKey(
        GraphLesson,
        on_delete=models.CASCADE,
        related_name='progress',
        verbose_name='Урок в графе'
    )

    # Статус урока
    STATUS_CHOICES = (
        ('not_started', 'Не начат'),
        ('in_progress', 'В процессе'),
        ('completed', 'Завершён'),
        ('failed', 'Не пройден'),
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='not_started',
        verbose_name='Статус'
    )

    # Прогресс
    completed_elements = models.IntegerField(
        default=0,
        verbose_name='Завершено элементов'
    )
    total_elements = models.IntegerField(
        default=0,
        verbose_name='Всего элементов'
    )
    completion_percent = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Процент завершения'
    )

    # Баллы
    total_score = models.IntegerField(
        default=0,
        verbose_name='Общий балл'
    )
    max_possible_score = models.IntegerField(
        default=0,
        verbose_name='Максимально возможный балл'
    )

    # Временные метки
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время начала'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Время завершения'
    )
    last_activity = models.DateTimeField(
        auto_now=True,
        verbose_name='Последняя активность'
    )

    # Общее время
    total_time_spent_seconds = models.IntegerField(
        default=0,
        verbose_name='Общее время (секунды)'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['student', 'graph_lesson']
        unique_together = [['student', 'graph_lesson']]
        indexes = [
            models.Index(fields=['student', 'graph_lesson']),
            models.Index(fields=['status']),
            models.Index(fields=['-last_activity']),
        ]
        verbose_name = 'Прогресс по уроку'
        verbose_name_plural = 'Прогресс по урокам'

    def __str__(self):
        return f"{self.student.get_full_name()} - {self.graph_lesson.lesson.title} ({self.completion_percent}%)"

    def start(self):
        """Начать урок"""
        if self.status == 'not_started':
            self.status = 'in_progress'
            self.started_at = timezone.now()

            # Подсчитать количество элементов
            self.total_elements = self.graph_lesson.lesson.elements.count()
            self.max_possible_score = self.graph_lesson.lesson.total_max_score

            self.save(update_fields=[
                'status', 'started_at', 'total_elements', 'max_possible_score'
            ])

    def update_progress(self):
        """Обновить прогресс на основе прогресса элементов"""
        element_progress = ElementProgress.objects.filter(
            student=self.student,
            graph_lesson=self.graph_lesson
        )

        self.completed_elements = element_progress.filter(status='completed').count()
        self.total_score = sum(
            ep.score for ep in element_progress if ep.score is not None
        )
        self.total_time_spent_seconds = sum(
            ep.time_spent_seconds for ep in element_progress
        )

        # Вычислить процент завершения
        if self.total_elements > 0:
            self.completion_percent = round(
                (self.completed_elements / self.total_elements) * 100
            )

        # Обновить статус
        if self.completion_percent == 100:
            self.status = 'completed'
            self.completed_at = timezone.now()
        elif self.completion_percent > 0:
            self.status = 'in_progress'

        self.save(update_fields=[
            'completed_elements', 'total_score', 'total_time_spent_seconds',
            'completion_percent', 'status', 'completed_at'
        ])

    def check_unlock_next(self):
        """
        Проверить и разблокировать следующие уроки
        FIX T019: добавлена защита от race condition через transaction.atomic
        """
        from django.db import transaction
        import logging

        logger = logging.getLogger(__name__)

        if self.status != 'completed':
            return

        try:
            with transaction.atomic():
                # Обновить состояние из БД (защита от race condition)
                self.refresh_from_db()

                # Найти зависимые уроки с оптимизацией запросов
                dependencies = LessonDependency.objects.filter(
                    from_lesson=self.graph_lesson,
                    dependency_type='required'
                ).select_related('to_lesson', 'to_lesson__graph')

                for dep in dependencies:
                    # Проверить, выполнено ли условие по баллам
                    score_percent = (self.total_score / self.max_possible_score * 100) if self.max_possible_score > 0 else 0

                    if score_percent >= dep.min_score_percent:
                        # Проверить все другие зависимости для целевого урока
                        all_deps = LessonDependency.objects.filter(
                            to_lesson=dep.to_lesson,
                            dependency_type='required'
                        ).select_related('from_lesson')

                        all_met = True
                        for other_dep in all_deps:
                            other_progress = LessonProgress.objects.filter(
                                student=self.student,
                                graph_lesson=other_dep.from_lesson
                            ).first()

                            if not other_progress or other_progress.status != 'completed':
                                all_met = False
                                break

                            other_score_percent = (
                                other_progress.total_score / other_progress.max_possible_score * 100
                            ) if other_progress.max_possible_score > 0 else 0

                            if other_score_percent < other_dep.min_score_percent:
                                all_met = False
                                break

                        if all_met:
                            dep.to_lesson.unlock()

        except Exception as e:
            # Логировать ошибку, но не прерывать выполнение
            # Прогресс записан, разблокировка - бонус
            logger.error(f"Ошибка при проверке разблокировки урока {self.graph_lesson.id}: {e}", exc_info=True)
