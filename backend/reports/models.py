from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()


class Report(models.Model):
    """
    Отчеты о прогрессе и успеваемости
    """
    class Type(models.TextChoices):
        STUDENT_PROGRESS = 'student_progress', 'Прогресс студента'
        CLASS_PERFORMANCE = 'class_performance', 'Успеваемость класса'
        SUBJECT_ANALYSIS = 'subject_analysis', 'Анализ по предмету'
        WEEKLY_SUMMARY = 'weekly_summary', 'Еженедельный отчет'
        MONTHLY_SUMMARY = 'monthly_summary', 'Месячный отчет'
        CUSTOM = 'custom', 'Пользовательский отчет'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        GENERATED = 'generated', 'Сгенерирован'
        SENT = 'sent', 'Отправлен'
        ARCHIVED = 'archived', 'Архив'
    
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    type = models.CharField(
        max_length=30,
        choices=Type.choices,
        default=Type.CUSTOM,
        verbose_name='Тип отчета'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус'
    )
    
    # Автор отчета
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_reports',
        verbose_name='Автор'
    )
    
    # Целевая аудитория
    target_students = models.ManyToManyField(
        User,
        related_name='reports_about_me',
        blank=True,
        verbose_name='Целевые студенты'
    )
    
    target_parents = models.ManyToManyField(
        User,
        related_name='reports_about_children',
        blank=True,
        verbose_name='Целевые родители'
    )
    
    # Период отчета
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    
    # Содержание отчета
    content = models.JSONField(
        default=dict,
        verbose_name='Содержание отчета'
    )
    
    # Файл отчета
    file = models.FileField(
        upload_to='reports/files/',
        blank=True,
        null=True,
        verbose_name='Файл отчета'
    )
    
    # Настройки автоматической генерации
    is_auto_generated = models.BooleanField(
        default=False,
        verbose_name='Автоматически генерируемый'
    )
    
    generation_frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Ежедневно'),
            ('weekly', 'Еженедельно'),
            ('monthly', 'Ежемесячно'),
        ],
        blank=True,
        verbose_name='Частота генерации'
    )
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generated_at = models.DateTimeField(blank=True, null=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Отчет'
        verbose_name_plural = 'Отчеты'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.title


class ReportTemplate(models.Model):
    """
    Шаблоны отчетов
    """
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    type = models.CharField(
        max_length=30,
        choices=Report.Type.choices,
        verbose_name='Тип отчета'
    )
    
    template_content = models.JSONField(
        default=dict,
        verbose_name='Содержание шаблона'
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name='Шаблон по умолчанию'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_templates',
        verbose_name='Создатель'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Шаблон отчета'
        verbose_name_plural = 'Шаблоны отчетов'
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name


class ReportRecipient(models.Model):
    """
    Получатели отчетов
    """
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='recipients',
        verbose_name='Отчет'
    )
    
    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='received_reports',
        verbose_name='Получатель'
    )
    
    is_sent = models.BooleanField(
        default=False,
        verbose_name='Отправлен'
    )
    
    sent_at = models.DateTimeField(blank=True, null=True, verbose_name='Отправлен')
    read_at = models.DateTimeField(blank=True, null=True, verbose_name='Прочитан')
    
    class Meta:
        verbose_name = 'Получатель отчета'
        verbose_name_plural = 'Получатели отчетов'
        unique_together = ['report', 'recipient']
    
    def __str__(self):
        return f"{self.recipient} - {self.report}"


class AnalyticsData(models.Model):
    """
    Аналитические данные для отчетов
    """
    class MetricType(models.TextChoices):
        STUDENT_PROGRESS = 'student_progress', 'Прогресс студента'
        ASSIGNMENT_COMPLETION = 'assignment_completion', 'Выполнение заданий'
        MATERIAL_STUDY = 'material_study', 'Изучение материалов'
        ATTENDANCE = 'attendance', 'Посещаемость'
        ENGAGEMENT = 'engagement', 'Вовлеченность'
        PERFORMANCE = 'performance', 'Успеваемость'
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='analytics_data',
        verbose_name='Студент'
    )
    
    metric_type = models.CharField(
        max_length=30,
        choices=MetricType.choices,
        verbose_name='Тип метрики'
    )
    
    value = models.FloatField(verbose_name='Значение')
    unit = models.CharField(max_length=20, verbose_name='Единица измерения')
    
    date = models.DateField(verbose_name='Дата')
    period_start = models.DateField(verbose_name='Начало периода')
    period_end = models.DateField(verbose_name='Конец периода')
    
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Дополнительные данные'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Аналитические данные'
        verbose_name_plural = 'Аналитические данные'
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.student} - {self.metric_type}: {self.value}"


class StudentReport(models.Model):
    """
    Отчеты о студентах от преподавателей
    """
    class ReportType(models.TextChoices):
        PROGRESS = 'progress', 'Отчет о прогрессе'
        BEHAVIOR = 'behavior', 'Отчет о поведении'
        ACHIEVEMENT = 'achievement', 'Отчет о достижениях'
        ATTENDANCE = 'attendance', 'Отчет о посещаемости'
        PERFORMANCE = 'performance', 'Отчет об успеваемости'
        CUSTOM = 'custom', 'Пользовательский отчет'
    
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        SENT = 'sent', 'Отправлен'
        READ = 'read', 'Прочитан'
        ARCHIVED = 'archived', 'Архив'
    
    # Основная информация
    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')
    
    # Тип и статус отчета
    report_type = models.CharField(
        max_length=20,
        choices=ReportType.choices,
        default=ReportType.PROGRESS,
        verbose_name='Тип отчета'
    )
    
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус'
    )
    
    # Участники отчета
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_student_reports',
        verbose_name='Преподаватель'
    )
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='student_reports',
        verbose_name='Студент'
    )
    
    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='child_reports',
        null=True,
        blank=True,
        verbose_name='Родитель'
    )
    
    # Период отчета
    period_start = models.DateField(verbose_name='Начало периода')
    period_end = models.DateField(verbose_name='Конец периода')
    
    # Содержание отчета
    content = models.JSONField(
        default=dict,
        verbose_name='Содержание отчета'
    )
    
    # Метрики и оценки
    overall_grade = models.CharField(
        max_length=10,
        blank=True,
        verbose_name='Общая оценка'
    )
    
    progress_percentage = models.PositiveIntegerField(
        default=0,
        verbose_name='Процент прогресса'
    )
    
    attendance_percentage = models.PositiveIntegerField(
        default=0,
        verbose_name='Процент посещаемости'
    )
    
    behavior_rating = models.PositiveIntegerField(
        default=5,
        choices=[(i, f'Оценка {i}') for i in range(1, 11)],
        verbose_name='Оценка поведения'
    )
    
    # Дополнительные данные
    recommendations = models.TextField(
        blank=True,
        verbose_name='Рекомендации'
    )
    
    concerns = models.TextField(
        blank=True,
        verbose_name='Обеспокоенности'
    )
    
    achievements = models.TextField(
        blank=True,
        verbose_name='Достижения'
    )
    
    # Файлы
    attachment = models.FileField(
        upload_to='student_reports/',
        blank=True,
        null=True,
        verbose_name='Приложение'
    )
    
    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Отчет о студенте'
        verbose_name_plural = 'Отчеты о студентах'
        ordering = ['-created_at']
        unique_together = ['teacher', 'student', 'period_start', 'period_end']
    
    def __str__(self):
        return f"{self.title} - {self.student.get_full_name()}"
    
    def save(self, *args, **kwargs):
        # Автоматически устанавливаем родителя, если не указан
        if not self.parent:
            try:
                parent = getattr(self.student.student_profile, 'parent', None) if hasattr(self.student, 'student_profile') else None
                if parent:
                    self.parent = parent
            except:
                pass
        super().save(*args, **kwargs)


class ReportSchedule(models.Model):
    """
    Расписание автоматической генерации отчетов
    """
    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='Шаблон отчета'
    )
    
    frequency = models.CharField(
        max_length=20,
        choices=[
            ('daily', 'Ежедневно'),
            ('weekly', 'Еженедельно'),
            ('monthly', 'Ежемесячно'),
        ],
        verbose_name='Частота'
    )
    
    day_of_week = models.PositiveIntegerField(
        blank=True,
        null=True,
        choices=[(i, f'День {i}') for i in range(1, 8)],
        verbose_name='День недели'
    )
    
    day_of_month = models.PositiveIntegerField(
        blank=True,
        null=True,
        choices=[(i, f'День {i}') for i in range(1, 32)],
        verbose_name='День месяца'
    )
    
    time = models.TimeField(verbose_name='Время генерации')
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='Активно'
    )
    
    last_generated = models.DateTimeField(blank=True, null=True, verbose_name='Последняя генерация')
    next_generation = models.DateTimeField(blank=True, null=True, verbose_name='Следующая генерация')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Расписание отчетов'
        verbose_name_plural = 'Расписания отчетов'
        ordering = ['next_generation']
    
    def __str__(self):
        return f"{self.report_template} - {self.frequency}"