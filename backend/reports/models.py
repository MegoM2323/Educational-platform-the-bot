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
    Configurable report templates with sections, layout, and format options.
    Supports template inheritance and versioning.
    """
    class Format(models.TextChoices):
        PDF = 'pdf', 'PDF'
        EXCEL = 'excel', 'Excel'
        JSON = 'json', 'JSON'
        CSV = 'csv', 'CSV'

    # Basic information
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')

    type = models.CharField(
        max_length=30,
        choices=Report.Type.choices,
        verbose_name='Тип отчета'
    )

    # Template sections configuration
    # Stores list of sections with data to include
    sections = models.JSONField(
        default=list,
        blank=True,
        verbose_name='Секции отчета',
        help_text='List of sections included in template: [{"name": "summary", "fields": [...]}]'
    )

    # Layout configuration
    # Stores layout settings: orientation, page_size, margins, etc.
    layout_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Конфигурация макета',
        help_text='Layout settings: orientation, page_size, margins, header, footer, etc.'
    )

    # Default export format
    default_format = models.CharField(
        max_length=10,
        choices=Format.choices,
        default=Format.PDF,
        verbose_name='Формат экспорта по умолчанию'
    )

    # Template content (legacy field, kept for backward compatibility)
    template_content = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Содержание шаблона'
    )

    # Template inheritance
    parent_template = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='child_templates',
        verbose_name='Родительский шаблон',
        help_text='Template this one is inherited from'
    )

    # Versioning
    version = models.PositiveIntegerField(
        default=1,
        verbose_name='Версия'
    )

    previous_version = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='next_versions',
        verbose_name='Предыдущая версия',
        help_text='Previous version of this template'
    )

    is_default = models.BooleanField(
        default=False,
        verbose_name='Шаблон по умолчанию'
    )

    is_archived = models.BooleanField(
        default=False,
        verbose_name='Архивирован'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_templates',
        verbose_name='Создатель'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived_at = models.DateTimeField(null=True, blank=True, verbose_name='Дата архивирования')

    class Meta:
        verbose_name = 'Шаблон отчета'
        verbose_name_plural = 'Шаблоны отчетов'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['type', 'is_default']),
            models.Index(fields=['created_by', '-created_at']),
            models.Index(fields=['parent_template', 'is_archived']),
        ]

    def __str__(self):
        version_str = f" (v{self.version})" if self.version > 1 else ""
        return f"{self.name}{version_str}"

    def validate_sections(self):
        """
        Validate section configuration.
        Ensures sections is a list and each section has required fields.
        """
        from django.core.exceptions import ValidationError

        if not isinstance(self.sections, list):
            raise ValidationError("Sections must be a list")

        valid_section_types = [
            'summary', 'metrics', 'progress', 'achievements', 'concerns',
            'recommendations', 'attendance', 'grades', 'performance',
            'engagement', 'behavioral', 'custom'
        ]

        for idx, section in enumerate(self.sections):
            if not isinstance(section, dict):
                raise ValidationError(f"Section {idx} must be a dictionary")

            if 'name' not in section:
                raise ValidationError(f"Section {idx} must have 'name' field")

            if section['name'] not in valid_section_types:
                raise ValidationError(
                    f"Section '{section['name']}' is not a valid type. "
                    f"Valid types: {', '.join(valid_section_types)}"
                )

            if 'fields' in section:
                if not isinstance(section['fields'], list):
                    raise ValidationError(f"Section {idx} 'fields' must be a list")

                if not section['fields']:
                    raise ValidationError(f"Section {idx} must have at least one field")

    def validate_layout_config(self):
        """
        Validate layout configuration.
        Checks for valid orientation, page size, and margins.
        """
        from django.core.exceptions import ValidationError

        if not isinstance(self.layout_config, dict):
            raise ValidationError("Layout config must be a dictionary")

        valid_orientations = ['portrait', 'landscape']
        valid_page_sizes = ['a4', 'letter', 'legal', 'a3', 'a5']

        if 'orientation' in self.layout_config:
            if self.layout_config['orientation'] not in valid_orientations:
                raise ValidationError(
                    f"Orientation must be one of: {', '.join(valid_orientations)}"
                )

        if 'page_size' in self.layout_config:
            if self.layout_config['page_size'] not in valid_page_sizes:
                raise ValidationError(
                    f"Page size must be one of: {', '.join(valid_page_sizes)}"
                )

        if 'margins' in self.layout_config:
            margins = self.layout_config['margins']
            if not isinstance(margins, dict):
                raise ValidationError("Margins must be a dictionary")

            for margin_key in ['top', 'bottom', 'left', 'right']:
                if margin_key in margins:
                    if not isinstance(margins[margin_key], (int, float)):
                        raise ValidationError(f"Margin '{margin_key}' must be numeric")

    def clean(self):
        """
        Validate template before saving.
        """
        from django.core.exceptions import ValidationError

        super().clean()

        if self.sections:
            self.validate_sections()

        if self.layout_config:
            self.validate_layout_config()

    def create_version(self, **kwargs):
        """
        Create a new version of this template.

        Args:
            **kwargs: Fields to override in the new version

        Returns:
            New ReportTemplate instance
        """
        # Copy current version fields
        new_version_data = {
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'sections': self.sections.copy() if isinstance(self.sections, list) else [],
            'layout_config': self.layout_config.copy() if isinstance(self.layout_config, dict) else {},
            'default_format': self.default_format,
            'template_content': self.template_content.copy() if isinstance(self.template_content, dict) else {},
            'parent_template': self.parent_template,
            'version': self.version + 1,
            'previous_version': self,
            'is_default': False,
            'is_archived': False,
            'created_by': self.created_by,
        }

        # Override with provided kwargs
        new_version_data.update(kwargs)

        return ReportTemplate.objects.create(**new_version_data)

    def get_sections(self):
        """Get list of sections in this template."""
        return self.sections if self.sections else []

    def get_layout_config(self):
        """Get layout configuration with defaults."""
        defaults = {
            'orientation': 'portrait',
            'page_size': 'a4',
            'margins': {'top': 1.0, 'bottom': 1.0, 'left': 1.0, 'right': 1.0}
        }

        if self.layout_config:
            defaults.update(self.layout_config)

        return defaults


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

    tutor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        related_name='received_student_reports',
        null=True,
        blank=True,
        verbose_name='Тьютор',
        limit_choices_to={'role': 'tutor'}
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

    # Видимость для родителя
    show_to_parent = models.BooleanField(
        default=True,
        verbose_name='Показывать родителю'
    )

    # Подтверждение родителя
    parent_acknowledged = models.BooleanField(
        default=False,
        verbose_name='Родитель подтвердил'
    )

    parent_acknowledged_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Дата подтверждения родителем'
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
    Email digest schedule for automated report delivery.
    Supports daily, weekly, and monthly delivery with customizable time and recipients.

    Can be used in two modes:
    1. Template-based (legacy): report_template + frequency
    2. Email digest (new): report_type + recipients + export_format
    """
    class ReportType(models.TextChoices):
        STUDENT_REPORT = 'student_report', 'Student Report'
        TUTOR_WEEKLY_REPORT = 'tutor_weekly_report', 'Tutor Weekly Report'
        TEACHER_WEEKLY_REPORT = 'teacher_weekly_report', 'Teacher Weekly Report'

    class Frequency(models.TextChoices):
        DAILY = 'daily', 'Daily'
        WEEKLY = 'weekly', 'Weekly'
        MONTHLY = 'monthly', 'Monthly'

    class ExportFormat(models.TextChoices):
        CSV = 'csv', 'CSV'
        XLSX = 'xlsx', 'Excel'
        PDF = 'pdf', 'PDF'

    # Legacy: template-based schedule
    report_template = models.ForeignKey(
        ReportTemplate,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='Report template',
        null=True,
        blank=True
    )

    # New: email digest fields
    name = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Schedule name'
    )

    report_type = models.CharField(
        max_length=30,
        choices=ReportType.choices,
        blank=True,
        verbose_name='Report type'
    )

    frequency = models.CharField(
        max_length=20,
        choices=Frequency.choices,
        default=Frequency.WEEKLY,
        verbose_name='Delivery frequency'
    )

    day_of_week = models.PositiveIntegerField(
        blank=True,
        null=True,
        choices=[(i, ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][i-1]) for i in range(1, 8)],
        verbose_name='Day of week (1=Monday)'
    )

    day_of_month = models.PositiveIntegerField(
        blank=True,
        null=True,
        choices=[(i, f'{i}') for i in range(1, 32)],
        verbose_name='Day of month (1-31)'
    )

    time = models.TimeField(verbose_name='Delivery time (HH:MM)', default='09:00')

    export_format = models.CharField(
        max_length=10,
        choices=ExportFormat.choices,
        default=ExportFormat.CSV,
        verbose_name='Export format'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_report_schedules',
        null=True,
        blank=True,
        verbose_name='Created by'
    )

    is_active = models.BooleanField(
        default=True,
        verbose_name='Is active'
    )

    last_sent = models.DateTimeField(blank=True, null=True, verbose_name='Last sent at')
    last_generated = models.DateTimeField(blank=True, null=True, verbose_name='Last generated at')
    next_scheduled = models.DateTimeField(blank=True, null=True, verbose_name='Next scheduled at')
    next_generation = models.DateTimeField(blank=True, null=True, verbose_name='Next generation (legacy)')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Report schedule'
        verbose_name_plural = 'Report schedules'
        ordering = ['next_scheduled', 'next_generation', '-created_at']
        indexes = [
            models.Index(fields=['is_active', 'next_scheduled']),
            models.Index(fields=['created_by', 'is_active']),
        ]

    def __str__(self):
        if self.name:
            return self.name
        if self.report_template:
            return f"{self.report_template} - {self.frequency}"
        return f"{self.get_report_type_display() or 'Report'} ({self.frequency})"


class TutorWeeklyReport(models.Model):
    """
    Еженедельные отчеты тьютора родителю о прогрессе ученика
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        SENT = 'sent', 'Отправлен'
        READ = 'read', 'Прочитан'
        ARCHIVED = 'archived', 'Архив'
    
    # Участники отчета
    tutor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_tutor_reports',
        verbose_name='Тьютор',
        limit_choices_to={'role': 'tutor'}
    )
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='tutor_weekly_reports',
        verbose_name='Ученик',
        limit_choices_to={'role': 'student'}
    )
    
    parent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_tutor_reports',
        verbose_name='Родитель',
        limit_choices_to={'role': 'parent'}
    )
    
    # Период отчета (неделя)
    week_start = models.DateField(verbose_name='Начало недели')
    week_end = models.DateField(verbose_name='Конец недели')
    
    # Основная информация
    title = models.CharField(max_length=200, default='Еженедельный отчет', verbose_name='Название')
    summary = models.TextField(verbose_name='Общее резюме')
    
    # Детали отчета
    academic_progress = models.TextField(blank=True, verbose_name='Академический прогресс')
    behavior_notes = models.TextField(blank=True, verbose_name='Заметки о поведении')
    achievements = models.TextField(blank=True, verbose_name='Достижения')
    concerns = models.TextField(blank=True, verbose_name='Обеспокоенности')
    recommendations = models.TextField(blank=True, verbose_name='Рекомендации')
    
    # Метрики
    attendance_days = models.PositiveIntegerField(default=0, verbose_name='Дней посещения')
    total_days = models.PositiveIntegerField(default=7, verbose_name='Всего дней')
    progress_percentage = models.PositiveIntegerField(default=0, verbose_name='Процент прогресса')
    
    # Статус и временные метки
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус'
    )
    
    # Файлы
    attachment = models.FileField(
        upload_to='tutor_reports/',
        blank=True,
        null=True,
        verbose_name='Приложение'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Еженедельный отчет тьютора'
        verbose_name_plural = 'Еженедельные отчеты тьютора'
        ordering = ['-week_start', '-created_at']
        unique_together = [['tutor', 'student', 'week_start']]
        indexes = [
            models.Index(fields=['tutor', 'student', '-week_start']),
            models.Index(fields=['parent', '-week_start']),
        ]
    
    def __str__(self):
        tutor_name = self.tutor.get_full_name() if self.tutor else 'Не назначен'
        student_name = self.student.get_full_name() if self.student else 'Не указан'
        return f"Отчет тьютора {tutor_name} о {student_name} за {self.week_start}"
    
    def save(self, *args, **kwargs):
        # Автоматически устанавливаем родителя из профиля ученика, если не установлен
        if not self.parent_id and self.student_id:
            try:
                from accounts.models import StudentProfile
                student_profile = StudentProfile.objects.select_related('parent').get(user_id=self.student_id)
                if student_profile.parent_id:
                    self.parent_id = student_profile.parent_id
            except StudentProfile.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class ParentReportPreference(models.Model):
    """
    Настройки видимости отчетов для родителя
    """
    parent = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='report_preferences',
        verbose_name='Родитель',
        limit_choices_to={'role': 'parent'}
    )

    # Получение уведомлений
    notify_on_report_created = models.BooleanField(
        default=True,
        verbose_name='Уведомление при создании отчета'
    )

    notify_on_grade_posted = models.BooleanField(
        default=True,
        verbose_name='Уведомление при выставлении оценки'
    )

    # Видимость данных
    show_grades = models.BooleanField(
        default=True,
        verbose_name='Показывать оценки'
    )

    show_progress = models.BooleanField(
        default=True,
        verbose_name='Показывать прогресс'
    )

    # Версионирование
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Настройки отчетов родителя'
        verbose_name_plural = 'Настройки отчетов родителей'

    def __str__(self):
        return f"Настройки отчетов для {self.parent.get_full_name()}"


class TeacherWeeklyReport(models.Model):
    """
    Еженедельные отчеты преподавателя тьютору о прогрессе ученика
    """
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Черновик'
        SENT = 'sent', 'Отправлен'
        READ = 'read', 'Прочитан'
        ARCHIVED = 'archived', 'Архив'
    
    # Участники отчета
    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='sent_teacher_reports',
        verbose_name='Преподаватель',
        limit_choices_to={'role': 'teacher'}
    )
    
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_weekly_reports',
        verbose_name='Ученик',
        limit_choices_to={'role': 'student'}
    )
    
    tutor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_teacher_reports',
        verbose_name='Тьютор',
        limit_choices_to={'role': 'tutor'}
    )
    
    # Предмет, по которому составлен отчет
    subject = models.ForeignKey(
        'materials.Subject',
        on_delete=models.CASCADE,
        related_name='teacher_weekly_reports',
        verbose_name='Предмет'
    )
    
    # Период отчета (неделя)
    week_start = models.DateField(verbose_name='Начало недели')
    week_end = models.DateField(verbose_name='Конец недели')
    
    # Основная информация
    title = models.CharField(max_length=200, default='Еженедельный отчет', verbose_name='Название')
    summary = models.TextField(verbose_name='Общее резюме')
    
    # Детали отчета
    academic_progress = models.TextField(blank=True, verbose_name='Академический прогресс')
    performance_notes = models.TextField(blank=True, verbose_name='Заметки об успеваемости')
    achievements = models.TextField(blank=True, verbose_name='Достижения')
    concerns = models.TextField(blank=True, verbose_name='Обеспокоенности')
    recommendations = models.TextField(blank=True, verbose_name='Рекомендации')
    
    # Метрики
    assignments_completed = models.PositiveIntegerField(default=0, verbose_name='Выполнено заданий')
    assignments_total = models.PositiveIntegerField(default=0, verbose_name='Всего заданий')
    average_score = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True, verbose_name='Средний балл')
    attendance_percentage = models.PositiveIntegerField(default=0, verbose_name='Процент посещаемости')
    
    # Статус и временные метки
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Статус'
    )
    
    # Файлы
    attachment = models.FileField(
        upload_to='teacher_reports/',
        blank=True,
        null=True,
        verbose_name='Приложение'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    read_at = models.DateTimeField(blank=True, null=True)
    
    class Meta:
        verbose_name = 'Еженедельный отчет преподавателя'
        verbose_name_plural = 'Еженедельные отчеты преподавателя'
        ordering = ['-week_start', '-created_at']
        unique_together = [['teacher', 'student', 'subject', 'week_start']]
        indexes = [
            models.Index(fields=['teacher', 'student', '-week_start']),
            models.Index(fields=['tutor', 'student', '-week_start']),
        ]
    
    def __str__(self):
        # Получаем кастомное название предмета из enrollment, если есть
        subject_name = 'Предмет не указан'
        try:
            if self.subject_id:
                subject_name = self.subject.name
                from materials.models import SubjectEnrollment
                enrollment = SubjectEnrollment.objects.filter(
                    student_id=self.student_id,
                    teacher_id=self.teacher_id,
                    subject_id=self.subject_id,
                    is_active=True
                ).select_related('subject').first()
                if enrollment:
                    subject_name = enrollment.get_subject_name()
        except Exception:
            # Если что-то пошло не так, используем стандартное название
            if self.subject:
                subject_name = self.subject.name
        teacher_name = self.teacher.get_full_name() if self.teacher else 'Не назначен'
        student_name = self.student.get_full_name() if self.student else 'Не указан'
        return f"Отчет преподавателя {teacher_name} о {student_name} по {subject_name} за {self.week_start}"
    
    def save(self, *args, **kwargs):
        # Автоматически устанавливаем тьютора из профиля ученика, если не установлен
        if not self.tutor_id and self.student_id:
            try:
                from accounts.models import StudentProfile
                student_profile = StudentProfile.objects.select_related('tutor').get(user_id=self.student_id)
                if student_profile.tutor_id:
                    self.tutor_id = student_profile.tutor_id
            except StudentProfile.DoesNotExist:
                pass
        super().save(*args, **kwargs)


class ReportScheduleRecipient(models.Model):
    """
    Track recipients and delivery status for scheduled reports.
    Supports unsubscribe functionality and delivery history.
    """
    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending'
        SENT = 'sent', 'Sent'
        FAILED = 'failed', 'Failed'
        SKIPPED = 'skipped', 'Skipped'

    schedule = models.ForeignKey(
        'ReportSchedule',
        on_delete=models.CASCADE,
        related_name='recipient_entries'
    )

    recipient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='report_subscriptions'
    )

    is_subscribed = models.BooleanField(
        default=True,
        verbose_name='Is subscribed'
    )

    unsubscribe_token = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
        verbose_name='Unsubscribe token'
    )

    added_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Unsubscribed at'
    )

    class Meta:
        verbose_name = 'Report schedule recipient'
        verbose_name_plural = 'Report schedule recipients'
        unique_together = ['schedule', 'recipient']
        indexes = [
            models.Index(fields=['schedule', 'is_subscribed']),
            models.Index(fields=['recipient', 'is_subscribed']),
        ]

    def __str__(self):
        return f"{self.recipient.email} - {self.schedule.name or self.schedule.id}"


class ReportScheduleExecution(models.Model):
    """
    Track execution history of scheduled report deliveries.
    Useful for debugging and monitoring report scheduling.
    """
    class ExecutionStatus(models.TextChoices):
        STARTED = 'started', 'Started'
        COMPLETED = 'completed', 'Completed'
        FAILED = 'failed', 'Failed'
        PARTIAL = 'partial', 'Partial (some recipients failed)'

    schedule = models.ForeignKey(
        'ReportSchedule',
        on_delete=models.CASCADE,
        related_name='executions'
    )

    status = models.CharField(
        max_length=20,
        choices=ExecutionStatus.choices,
        default=ExecutionStatus.STARTED
    )

    total_recipients = models.PositiveIntegerField(default=0)
    successful_sends = models.PositiveIntegerField(default=0)
    failed_sends = models.PositiveIntegerField(default=0)

    error_message = models.TextField(blank=True)

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = 'Report schedule execution'
        verbose_name_plural = 'Report schedule executions'
        ordering = ['-started_at']
        indexes = [
            models.Index(fields=['schedule', '-started_at']),
            models.Index(fields=['status', '-started_at']),
        ]

    def __str__(self):
        return f"{self.schedule} - {self.status} ({self.started_at.strftime('%Y-%m-%d %H:%M')})"

    @property
    def duration(self):
        """Get execution duration in seconds."""
        if self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None

    @property
    def success_rate(self):
        """Get success rate percentage."""
        if self.total_recipients == 0:
            return 0
        return round((self.successful_sends / self.total_recipients) * 100, 2)


# =====================================================
# Custom Report Builder Models
# =====================================================

class CustomReport(models.Model):
    """
    User-defined report configuration.
    Teachers can create custom reports with configurable fields, filters, and charts.
    """

    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        ACTIVE = 'active', 'Active'
        ARCHIVED = 'archived', 'Archived'

    # Basic info
    name = models.CharField(
        max_length=255,
        verbose_name='Report Name',
        help_text='User-friendly name for the report'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description',
        help_text='Detailed description of what the report shows'
    )

    # Ownership and access
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_custom_reports',
        verbose_name='Created By'
    )

    is_shared = models.BooleanField(
        default=False,
        verbose_name='Is Shared',
        help_text='If true, other teachers can use/clone this report'
    )

    shared_with = models.ManyToManyField(
        User,
        related_name='shared_custom_reports',
        blank=True,
        limit_choices_to={'role': 'teacher'},
        verbose_name='Shared With'
    )

    # Configuration
    config = models.JSONField(
        default=dict,
        verbose_name='Report Configuration',
        help_text='JSON config with fields, filters, chart_type, etc.'
    )

    # Status and timestamps
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name='Status'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Soft delete support
    deleted_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='Deleted At'
    )

    class Meta:
        verbose_name = 'Custom Report'
        verbose_name_plural = 'Custom Reports'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['is_shared', 'deleted_at']),
        ]

    def __str__(self):
        return f"{self.name} (by {self.created_by.get_full_name()})"

    def is_deleted(self) -> bool:
        """Check if report is soft-deleted."""
        return self.deleted_at is not None

    def soft_delete(self):
        """Soft-delete the report."""
        from django.utils import timezone
        self.deleted_at = timezone.now()
        self.save()

    def restore(self):
        """Restore a soft-deleted report."""
        self.deleted_at = None
        self.save()

    def validate_config(self):
        """Validate the report configuration."""
        from django.core.exceptions import ValidationError
        try:
            config = self.config

            # Validate required fields
            if 'fields' not in config or not isinstance(config['fields'], list):
                raise ValidationError("Config must contain 'fields' list")

            if not config['fields']:
                raise ValidationError("Config 'fields' cannot be empty")

            # Validate filters if present
            if 'filters' in config:
                if not isinstance(config['filters'], dict):
                    raise ValidationError("Config 'filters' must be a dictionary")

            # Validate chart_type if present
            if 'chart_type' in config:
                valid_charts = ['bar', 'line', 'pie', 'histogram', 'scatter']
                if config['chart_type'] not in valid_charts:
                    raise ValidationError(
                        f"Chart type must be one of: {', '.join(valid_charts)}"
                    )

            # Validate sort fields if present
            if 'sort_by' in config:
                if config['sort_by'] not in config['fields']:
                    raise ValidationError(
                        "sort_by field must be in the selected fields"
                    )

            if 'sort_order' in config:
                if config['sort_order'] not in ['asc', 'desc']:
                    raise ValidationError(
                        "sort_order must be 'asc' or 'desc'"
                    )

        except (ValueError, TypeError, KeyError) as e:
            raise ValidationError(f"Invalid config format: {str(e)}")

    def clean(self):
        """Validate model before saving."""
        super().clean()
        self.validate_config()

    def get_field_options(self):
        """Get available field options for different report types."""
        return {
            'student': [
                'student_name',
                'student_email',
                'grade',
                'submission_count',
                'progress',
                'attendance',
                'last_submission_date'
            ],
            'assignment': [
                'title',
                'due_date',
                'avg_score',
                'submission_rate',
                'completion_rate',
                'late_submissions',
                'total_submissions'
            ],
            'grade': [
                'score',
                'feedback',
                'graded_by',
                'graded_at',
                'student_name',
                'assignment_title',
                'status'
            ]
        }

    def get_filter_options(self):
        """Get available filter options."""
        return {
            'subject_id': 'Subject ID (integer)',
            'date_range': 'Date range {"start": "2025-01-01", "end": "2025-12-31"}',
            'grade_range': 'Grade range {"min": 0, "max": 100}',
            'status': 'Submission status (submitted, graded, late, pending)',
            'student_id': 'Individual student ID',
            'class_id': 'Class/Group ID',
            'assignment_id': 'Assignment ID'
        }


class CustomReportExecution(models.Model):
    """
    Record of each report execution for tracking and auditing.
    """

    report = models.ForeignKey(
        CustomReport,
        on_delete=models.CASCADE,
        related_name='executions',
        verbose_name='Report'
    )

    executed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='report_executions',
        verbose_name='Executed By'
    )

    # Execution details
    rows_returned = models.IntegerField(
        default=0,
        verbose_name='Rows Returned'
    )

    execution_time_ms = models.IntegerField(
        default=0,
        verbose_name='Execution Time (ms)'
    )

    # Result storage
    result_summary = models.JSONField(
        default=dict,
        verbose_name='Result Summary'
    )

    # Timestamps
    executed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Custom Report Execution'
        verbose_name_plural = 'Custom Report Executions'
        ordering = ['-executed_at']
        indexes = [
            models.Index(fields=['report', '-executed_at']),
            models.Index(fields=['executed_by', '-executed_at']),
        ]

    def __str__(self):
        return f"{self.report.name} - {self.executed_at}"


class CustomReportBuilderTemplate(models.Model):
    """
    Pre-built report templates for custom report builder.
    Teachers can clone and customize these templates.
    """

    class TemplateType(models.TextChoices):
        CLASS_PROGRESS = 'class_progress', 'Class Progress'
        STUDENT_GRADES = 'student_grades', 'Student Grades'
        ASSIGNMENT_ANALYSIS = 'assignment_analysis', 'Assignment Analysis'
        ATTENDANCE = 'attendance', 'Attendance Report'
        ENGAGEMENT = 'engagement', 'Student Engagement'

    # Basic info
    name = models.CharField(
        max_length=255,
        verbose_name='Template Name'
    )
    description = models.TextField(
        blank=True,
        verbose_name='Description'
    )

    template_type = models.CharField(
        max_length=50,
        choices=TemplateType.choices,
        verbose_name='Template Type'
    )

    # Template configuration
    base_config = models.JSONField(
        default=dict,
        verbose_name='Base Configuration'
    )

    # System or custom
    is_system = models.BooleanField(
        default=False,
        verbose_name='Is System Template'
    )

    created_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='custom_report_templates',
        verbose_name='Created By'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Custom Report Builder Template'
        verbose_name_plural = 'Custom Report Builder Templates'
        ordering = ['template_type', 'name']

    def __str__(self):
        return f"{self.name} ({self.template_type})"

    def create_custom_report(self, user: User, name: str, **overrides) -> CustomReport:
        """
        Create a custom report from this template.

        Args:
            user: Teacher creating the report
            name: Name for the custom report
            **overrides: Config overrides

        Returns:
            CustomReport instance
        """
        config = self.base_config.copy()
        config.update(overrides)

        report = CustomReport.objects.create(
            name=name,
            description=self.description,
            created_by=user,
            config=config
        )

        return report


# =====================================================
# Report Access Control Models
# =====================================================

class ReportAccessToken(models.Model):
    """
    Temporary access tokens for report sharing.
    Allows time-limited access to reports via unique links.
    """
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Active'
        EXPIRED = 'expired', 'Expired'
        REVOKED = 'revoked', 'Revoked'

    # Token identification
    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        verbose_name='Access Token'
    )

    # Report reference
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='access_tokens',
        verbose_name='Report'
    )

    # Token properties
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_access_tokens',
        verbose_name='Created By'
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name='Status'
    )

    # Expiration settings
    expires_at = models.DateTimeField(
        verbose_name='Expires At',
        help_text='Token becomes inactive after this time'
    )

    # Access tracking
    access_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Access Count'
    )

    max_accesses = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Max Accesses',
        help_text='Limit token usage, null means unlimited'
    )

    last_accessed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Last Accessed At'
    )

    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Report Access Token'
        verbose_name_plural = 'Report Access Tokens'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['report', 'status']),
            models.Index(fields=['created_by', 'status']),
            models.Index(fields=['expires_at', 'status']),
        ]

    def __str__(self):
        return f"{self.report.title} - {self.token[:10]}..."

    def is_valid(self) -> bool:
        """Check if token is still valid."""
        from django.utils import timezone

        if self.status != self.Status.ACTIVE:
            return False

        if timezone.now() > self.expires_at:
            self.status = self.Status.EXPIRED
            self.save(update_fields=['status'])
            return False

        if self.max_accesses and self.access_count >= self.max_accesses:
            return False

        return True

    def increment_access(self):
        """Record an access to this token."""
        from django.utils import timezone

        self.access_count += 1
        self.last_accessed_at = timezone.now()
        self.save(update_fields=['access_count', 'last_accessed_at'])

    def revoke(self):
        """Revoke this token."""
        self.status = self.Status.REVOKED
        self.save(update_fields=['status'])


class ReportAccessAuditLog(models.Model):
    """
    Comprehensive audit trail for report access.
    Tracks who accessed what report, when, for how long, and from where.
    """
    class AccessType(models.TextChoices):
        VIEW = 'view', 'Viewed'
        DOWNLOAD = 'download', 'Downloaded'
        SHARE = 'share', 'Shared'
        PRINT = 'print', 'Printed'
        EXPORT = 'export', 'Exported'

    # Access details
    access_type = models.CharField(
        max_length=20,
        choices=AccessType.choices,
        default=AccessType.VIEW,
        verbose_name='Access Type'
    )

    # Report and user
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='access_logs',
        verbose_name='Report'
    )

    accessed_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='report_access_logs',
        verbose_name='Accessed By'
    )

    # Access method
    access_method = models.CharField(
        max_length=50,
        choices=[
            ('direct', 'Direct Access'),
            ('token_link', 'Temporary Link'),
            ('shared_access', 'Shared Access'),
            ('role_based', 'Role-Based Access'),
        ],
        default='direct',
        verbose_name='Access Method'
    )

    # Session and request info
    session_id = models.CharField(
        max_length=100,
        blank=True,
        verbose_name='Session ID'
    )

    ip_address = models.GenericIPAddressField(
        verbose_name='IP Address'
    )

    user_agent = models.TextField(
        blank=True,
        verbose_name='User Agent'
    )

    # Duration tracking
    access_duration_seconds = models.PositiveIntegerField(
        default=0,
        verbose_name='Access Duration (seconds)'
    )

    # Additional metadata
    metadata = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='Additional Metadata',
        help_text='Custom data like device info, referer, etc.'
    )

    # Timestamps
    accessed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Accessed At'
    )

    class Meta:
        verbose_name = 'Report Access Audit Log'
        verbose_name_plural = 'Report Access Audit Logs'
        ordering = ['-accessed_at']
        indexes = [
            models.Index(fields=['report', '-accessed_at']),
            models.Index(fields=['accessed_by', '-accessed_at']),
            models.Index(fields=['access_type', '-accessed_at']),
            models.Index(fields=['access_method']),
            models.Index(fields=['ip_address']),
        ]

    def __str__(self):
        return f"{self.accessed_by.email} - {self.report.title} ({self.access_type})"


class ReportSharing(models.Model):
    """
    Manages report sharing with specific users.
    Supports role-based and user-specific sharing with granular permissions.
    """
    class Permission(models.TextChoices):
        VIEW = 'view', 'Can View'
        VIEW_DOWNLOAD = 'view_download', 'Can View & Download'
        VIEW_DOWNLOAD_EXPORT = 'view_download_export', 'Can View, Download & Export'

    class ShareType(models.TextChoices):
        USER = 'user', 'Shared with User'
        ROLE = 'role', 'Shared with Role'
        LINK = 'link', 'Shared via Link'

    # Core relations
    report = models.ForeignKey(
        Report,
        on_delete=models.CASCADE,
        related_name='sharings',
        verbose_name='Report'
    )

    shared_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_report_sharings',
        verbose_name='Shared By'
    )

    # Recipient (can be null for role-based sharing)
    shared_with_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='received_report_sharings',
        verbose_name='Shared With User'
    )

    # Type and scope
    share_type = models.CharField(
        max_length=20,
        choices=ShareType.choices,
        default=ShareType.USER,
        verbose_name='Share Type'
    )

    shared_role = models.CharField(
        max_length=20,
        blank=True,
        choices=[
            ('student', 'Student'),
            ('teacher', 'Teacher'),
            ('tutor', 'Tutor'),
            ('parent', 'Parent'),
            ('admin', 'Admin'),
        ],
        verbose_name='Shared Role'
    )

    # Permissions
    permission = models.CharField(
        max_length=50,
        choices=Permission.choices,
        default=Permission.VIEW,
        verbose_name='Permission'
    )

    # Expiration (optional)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='Expires At'
    )

    # Status
    is_active = models.BooleanField(
        default=True,
        verbose_name='Is Active'
    )

    # Metadata
    share_message = models.TextField(
        blank=True,
        verbose_name='Share Message'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Report Sharing'
        verbose_name_plural = 'Report Sharings'
        ordering = ['-created_at']
        unique_together = ['report', 'shared_with_user', 'shared_role']
        indexes = [
            models.Index(fields=['report', 'is_active']),
            models.Index(fields=['shared_with_user', 'is_active']),
            models.Index(fields=['share_type', 'shared_role']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        if self.shared_with_user:
            return f"{self.report.title} - shared with {self.shared_with_user.email}"
        return f"{self.report.title} - shared with {self.shared_role}"

    def is_valid(self) -> bool:
        """Check if sharing is still valid."""
        from django.utils import timezone

        if not self.is_active:
            return False

        if self.expires_at and timezone.now() > self.expires_at:
            return False

        return True
