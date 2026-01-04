from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import (
    FileExtensionValidator,
    MinValueValidator,
    MaxValueValidator,
)
from django.utils import timezone
from datetime import timedelta
from django.core.exceptions import ValidationError

User = get_user_model()

__all__ = [
    "Subject",
    "TeacherSubject",
    "SubjectEnrollment",
    "SubjectPayment",
    "SubjectSubscription",
    "Material",
    "MaterialProgress",
    "MaterialComment",
    "MaterialSubmission",
    "MaterialFeedback",
    "StudyPlan",
    "StudyPlanFile",
    "StudyPlanGeneration",
    "GeneratedFile",
    "SubmissionFile",
    "MaterialDownloadLog",
    "BulkAssignmentAuditLog",
    "validate_submission_file",
]


class Subject(models.Model):
    """
    Предметы/дисциплины
    """

    name = models.CharField(max_length=100, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    color = models.CharField(max_length=7, default="#3B82F6", verbose_name="Цвет")

    class Meta:
        app_label = "materials"
        verbose_name = "Предмет"
        verbose_name_plural = "Предметы"
        ordering = ["name"]

    def __str__(self):
        return self.name


class TeacherSubject(models.Model):
    """
    Связь преподаватель - предмет (многие ко многим)
    Один преподаватель может вести несколько предметов
    """

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="teacher_subjects",
        verbose_name="Преподаватель",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="subject_teachers",
        verbose_name="Предмет",
    )

    # Дополнительная информация
    is_active = models.BooleanField(default=True, verbose_name="Активно")
    assigned_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата назначения")

    class Meta:
        verbose_name = "Предмет преподавателя"
        verbose_name_plural = "Предметы преподавателей"
        unique_together = ["teacher", "subject"]
        ordering = ["-assigned_at"]

    def __str__(self):
        return f"{self.teacher.get_full_name()} - {self.subject.name}"


class SubjectEnrollment(models.Model):
    """
    Зачисление студента на предмет
    """

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="subject_enrollments",
        verbose_name="Студент",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="enrollments",
        verbose_name="Предмет",
    )

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="taught_subjects",
        verbose_name="Преподаватель",
    )

    # Кто назначил предмет (обычно тьютор)
    assigned_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_enrollments",
        verbose_name="Назначено пользователем",
    )

    # Кастомное название предмета (если указано тьютором)
    custom_subject_name = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="Кастомное название предмета",
        help_text="Если указано, используется вместо стандартного названия предмета",
    )

    enrolled_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата зачисления")
    is_active = models.BooleanField(default=True, verbose_name="Активно")

    class Meta:
        verbose_name = "Зачисление на предмет"
        verbose_name_plural = "Зачисления на предметы"
        constraints = [
            models.UniqueConstraint(
                fields=["student", "subject"],
                condition=models.Q(is_active=True),
                name="unique_active_enrollment_per_subject",
            ),
            models.UniqueConstraint(
                fields=["student", "subject", "teacher"], name="unique_student_subject_teacher"
            ),
        ]
        ordering = ["-enrolled_at"]

    def __str__(self):
        subject_name = self.custom_subject_name or self.subject.name
        return f"{self.student} - {subject_name} ({self.teacher})"

    def get_subject_name(self):
        """Возвращает название предмета (кастомное или стандартное)"""
        return self.custom_subject_name or self.subject.name


class SubjectPayment(models.Model):
    """
    Платежи по предметам
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает оплаты"
        WAITING_FOR_PAYMENT = "waiting_for_payment", "Ожидание платежа"
        PAID = "paid", "Оплачен"
        EXPIRED = "expired", "Просрочен"
        REFUNDED = "refunded", "Возвращен"

    enrollment = models.ForeignKey(
        SubjectEnrollment,
        on_delete=models.CASCADE,
        related_name="payments",
        verbose_name="Зачисление",
    )

    payment = models.ForeignKey(
        "payments.Payment",
        on_delete=models.CASCADE,
        related_name="subject_payments",
        verbose_name="Платеж",
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )

    def _default_due_date():
        return timezone.now() + timedelta(days=7)

    due_date = models.DateTimeField(verbose_name="Срок оплаты", default=_default_due_date)
    paid_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата оплаты")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Платеж по предмету"
        verbose_name_plural = "Платежи по предметам"
        ordering = ["-created_at"]
        unique_together = [("enrollment", "payment")]

    def __str__(self):
        return f"Платеж {self.enrollment.student} - {self.enrollment.subject} ({self.amount})"


class SubjectSubscription(models.Model):
    """
    Регулярные платежи (подписки) по предметам
    Еженедельное списание средств
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Активна"
        PAUSED = "paused", "Приостановлена"
        CANCELLED = "cancelled", "Отменена"
        EXPIRED = "expired", "Истекла"

    enrollment = models.OneToOneField(
        SubjectEnrollment,
        on_delete=models.CASCADE,
        related_name="subscription",
        verbose_name="Зачисление",
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Сумма платежа")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        verbose_name="Статус",
    )

    # Настройки регулярных платежей
    next_payment_date = models.DateTimeField(verbose_name="Дата следующего платежа")
    payment_interval_weeks = models.PositiveIntegerField(
        default=1, verbose_name="Интервал платежей (недели)"
    )

    # ID подписки в ЮКассу (если используется)
    yookassa_subscription_id = models.CharField(
        max_length=255, blank=True, null=True, verbose_name="ID подписки в ЮКассу"
    )

    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    cancelled_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата отмены")
    expires_at = models.DateTimeField(blank=True, null=True, verbose_name="Дата истечения доступа")

    class Meta:
        verbose_name = "Подписка на предмет"
        verbose_name_plural = "Подписки на предметы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Подписка {self.enrollment.student} - {self.enrollment.subject} ({self.amount} руб/нед)"

    def schedule_next_payment(self):
        """Запланировать следующий платеж"""
        from django.utils import timezone
        from django.conf import settings

        # Определяем интервал следующего платежа в зависимости от режима
        if settings.PAYMENT_DEVELOPMENT_MODE:
            # В режиме разработки: используем минуты
            # Если payment_interval_weeks = 0, значит это режим разработки, используем настройку из settings
            if self.payment_interval_weeks == 0:
                next_payment_delta = timedelta(
                    minutes=settings.DEVELOPMENT_RECURRING_INTERVAL_MINUTES
                )
            else:
                # Для обратной совместимости, если есть значение в неделях, но режим разработки
                next_payment_delta = timedelta(
                    minutes=settings.DEVELOPMENT_RECURRING_INTERVAL_MINUTES
                )
        else:
            # В обычном режиме: используем недели
            if self.payment_interval_weeks > 0:
                next_payment_delta = timedelta(weeks=self.payment_interval_weeks)
            else:
                # Если payment_interval_weeks = 0, используем настройку из settings
                next_payment_delta = timedelta(weeks=settings.PRODUCTION_RECURRING_INTERVAL_WEEKS)

        self.next_payment_date = timezone.now() + next_payment_delta
        self.save(update_fields=["next_payment_date", "updated_at"])


class Material(models.Model):
    """
    Учебные материалы
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        ACTIVE = "active", "Активно"
        ARCHIVED = "archived", "Архив"

    class Type(models.TextChoices):
        LESSON = "lesson", "Урок"
        PRESENTATION = "presentation", "Презентация"
        VIDEO = "video", "Видео"
        DOCUMENT = "document", "Документ"
        TEST = "test", "Тест"
        HOMEWORK = "homework", "Домашнее задание"

    title = models.CharField(max_length=200, verbose_name="Название")
    description = models.TextField(blank=True, verbose_name="Описание")
    content = models.TextField(verbose_name="Содержание")

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="authored_materials",
        verbose_name="Автор",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="materials",
        verbose_name="Предмет",
    )

    type = models.CharField(
        max_length=20, choices=Type.choices, default=Type.LESSON, verbose_name="Тип"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Статус",
    )

    # Файлы
    file = models.FileField(
        upload_to="materials/files/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx", "ppt", "pptx", "txt"])
        ],
        verbose_name="Файл",
    )

    video_url = models.URLField(blank=True, verbose_name="Ссылка на видео")

    # Настройки доступа
    is_public = models.BooleanField(default=False, verbose_name="Публичный")
    assigned_to = models.ManyToManyField(
        User, related_name="assigned_materials", blank=True, verbose_name="Назначено"
    )

    # Метаданные
    tags = models.CharField(max_length=500, blank=True, verbose_name="Теги")
    difficulty_level = models.PositiveIntegerField(
        default=1,
        choices=[(i, f"Уровень {i}") for i in range(1, 6)],
        verbose_name="Уровень сложности",
    )

    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Материал"
        verbose_name_plural = "Материалы"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.status == self.Status.ACTIVE and not self.published_at:
            from django.utils import timezone

            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def download_count(self) -> int:
        """
        Получить общее количество загрузок материала.

        Returns:
            int: Количество записей о загрузках
        """
        return self.download_logs.count()

    @property
    def unique_downloaders(self) -> int:
        """
        Получить количество уникальных пользователей, загрузивших материал.

        Returns:
            int: Количество уникальных пользователей
        """
        return self.download_logs.values("user_id").distinct().count()

    @property
    def total_data_transferred(self) -> int:
        """
        Получить общий объем данных, загруженных для этого материала.

        Returns:
            int: Общий размер в байтах
        """
        from django.db.models import Sum

        result = self.download_logs.aggregate(total=Sum("file_size"))
        return result["total"] or 0


class MaterialProgress(models.Model):
    """
    Прогресс изучения материала студентом
    """

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="material_progress",
        verbose_name="Студент",
    )

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="progress",
        verbose_name="Материал",
    )

    is_completed = models.BooleanField(default=False, verbose_name="Завершен")
    progress_percentage = models.PositiveIntegerField(default=0, verbose_name="Прогресс (%)")
    time_spent = models.PositiveIntegerField(default=0, verbose_name="Время изучения (мин)")

    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    last_accessed = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Прогресс материала"
        verbose_name_plural = "Прогресс материалов"
        unique_together = ["student", "material"]

    def __str__(self):
        return f"{self.student} - {self.material} ({self.progress_percentage}%)"


class MaterialComment(models.Model):
    """
    Комментарии к материалам с поддержкой потокования

    Поддерживает:
    - Комментарии верхнего уровня
    - Ответы на комментарии (max 3 уровня вложенности)
    - Мягкое удаление (soft delete)
    - Модерирование (approval workflow)
    - Подсчет ответов (reply_count аннотация)
    """

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="Материал",
    )

    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="material_comments",
        verbose_name="Автор",
    )

    content = models.TextField(verbose_name="Содержание")
    is_question = models.BooleanField(default=False, verbose_name="Вопрос")

    # Threading support
    parent_comment = models.ForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="replies",
        verbose_name="Родительский комментарий",
    )

    # Soft delete and moderation
    is_deleted = models.BooleanField(default=False, verbose_name="Удален")
    is_approved = models.BooleanField(default=True, verbose_name="Одобрен")
    deleted_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата удаления")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Комментарий"
        verbose_name_plural = "Комментарии"
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["material", "parent_comment"], name="matcom_mat_parent_idx"),
            models.Index(fields=["author", "material"], name="matcom_author_mat_idx"),
            models.Index(fields=["-created_at"], name="matcom_created_idx"),
        ]

    def __str__(self):
        return f"Комментарий к {self.material} от {self.author}"

    def get_depth(self) -> int:
        """
        Получить глубину вложенности комментария в дереве

        0 = верхнеуровневый комментарий
        1 = ответ на верхнеуровневый комментарий
        2 = ответ на ответ
        3 = максимальная допустимая глубина

        Returns:
            int: Глубина вложенности (0-3)
        """
        depth = 0
        current = self
        while current.parent_comment is not None:
            depth += 1
            current = current.parent_comment
        return depth

    def can_have_replies(self) -> bool:
        """
        Проверить, можно ли добавлять ответы на этот комментарий

        Returns:
            bool: True если глубина < 3, False если достигнута максимальная глубина
        """
        return self.get_depth() < 3

    def delete(self, *args, **kwargs):
        """
        Мягкое удаление комментария (soft delete)

        Вместо физического удаления из БД, помечает комментарий как удаленный
        с сохранением timestamp удаления для аудита
        """
        from django.utils import timezone

        self.is_deleted = True
        self.deleted_at = timezone.now()
        self.save(update_fields=["is_deleted", "deleted_at"])

    def hard_delete(self):
        """
        Физическое удаление комментария из БД

        Используется только администраторами для очистки БД.
        Удаляет все дочерние комментарии каскадно.
        """
        super().delete()


def validate_submission_file(file):
    """Валидация файлов ответов учеников"""
    max_size = 10 * 1024 * 1024  # 10MB
    allowed_types = ["pdf", "doc", "docx", "txt", "jpg", "jpeg", "png", "zip", "rar"]

    if file.size > max_size:
        raise ValidationError("Файл слишком большой (максимум 10MB)")

    ext = file.name.split(".")[-1].lower()
    if ext not in allowed_types:
        raise ValidationError(f'Неподдерживаемый тип файла. Разрешены: {", ".join(allowed_types)}')


class MaterialSubmission(models.Model):
    """
    Ответы учеников на материалы
    """

    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Отправлено"
        REVIEWED = "reviewed", "Проверено"
        RETURNED = "returned", "Возвращено на доработку"

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name="Материал",
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="submissions",
        verbose_name="Студент",
    )

    submission_file = models.FileField(
        upload_to="submissions/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=[
                    "pdf",
                    "doc",
                    "docx",
                    "txt",
                    "jpg",
                    "jpeg",
                    "png",
                    "zip",
                    "rar",
                ]
            )
        ],
        verbose_name="Файл ответа",
    )

    submission_text = models.TextField(blank=True, verbose_name="Текстовый ответ")

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        verbose_name="Статус",
    )

    is_late = models.BooleanField(default=False, verbose_name="С опозданием")
    submitted_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата отправки")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Ответ на материал"
        verbose_name_plural = "Ответы на материалы"
        unique_together = ["material", "student"]
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"Ответ {self.student} на {self.material}"

    def clean(self):
        if not self.submission_file and not self.submission_text:
            raise ValidationError("Необходимо предоставить либо файл, либо текстовый ответ")

        if self.submission_file:
            validate_submission_file(self.submission_file)


class MaterialFeedback(models.Model):
    """
    Фидбэк преподавателей на ответы учеников
    """

    submission = models.OneToOneField(
        MaterialSubmission,
        on_delete=models.CASCADE,
        related_name="feedback",
        verbose_name="Ответ",
    )

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="given_feedback",
        verbose_name="Преподаватель",
    )

    feedback_text = models.TextField(verbose_name="Текст фидбэка")
    grade = models.PositiveIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="Оценка",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Фидбэк по материалу"
        verbose_name_plural = "Фидбэки по материалам"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Фидбэк для {self.submission.student} по {self.submission.material}"


class StudyPlan(models.Model):
    """
    Еженедельный план занятий по предмету для студента
    Преподаватель создает персональный план подготовки для каждого ученика
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Черновик"
        SENT = "sent", "Отправлен"
        ARCHIVED = "archived", "Архив"

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_study_plans",
        verbose_name="Преподаватель",
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="study_plans",
        limit_choices_to={"role": "student"},
        verbose_name="Студент",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="study_plans",
        verbose_name="Предмет",
    )

    # Связь с зачислением (для проверки, что студент зачислен на предмет к этому преподавателю)
    enrollment = models.ForeignKey(
        SubjectEnrollment,
        on_delete=models.CASCADE,
        related_name="study_plans",
        null=True,
        blank=True,
        verbose_name="Зачисление на предмет",
    )

    # Название плана (например, "Неделя 1: Алгебра")
    title = models.CharField(max_length=200, verbose_name="Название плана")

    # Содержание плана (структурированный текст или JSON)
    content = models.TextField(verbose_name="Содержание плана")

    # Дата начала недели
    week_start_date = models.DateField(verbose_name="Дата начала недели")

    # Дата окончания недели (вычисляется автоматически)
    week_end_date = models.DateField(verbose_name="Дата окончания недели")

    # Статус плана
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        verbose_name="Статус",
    )

    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата отправки")

    class Meta:
        verbose_name = "План занятий"
        verbose_name_plural = "Планы занятий"
        ordering = ["-week_start_date", "-created_at"]
        indexes = [
            models.Index(fields=["student", "subject", "week_start_date"]),
            models.Index(fields=["teacher", "status"]),
        ]

    def __str__(self):
        return f"План {self.student.get_full_name()} - {self.subject.name} ({self.week_start_date})"

    def save(self, *args, **kwargs):
        # Автоматически вычисляем дату окончания недели
        if self.week_start_date and not self.week_end_date:
            from datetime import timedelta

            self.week_end_date = self.week_start_date + timedelta(days=6)

        # Автоматически устанавливаем дату отправки при изменении статуса на SENT
        if self.status == self.Status.SENT and not self.sent_at:
            from django.utils import timezone

            self.sent_at = timezone.now()

        # Автоматически находим enrollment, если не указан
        if not self.enrollment:
            try:
                enrollment = SubjectEnrollment.objects.get(
                    student=self.student,
                    subject=self.subject,
                    teacher=self.teacher,
                    is_active=True,
                )
                self.enrollment = enrollment
            except SubjectEnrollment.DoesNotExist:
                pass

        super().save(*args, **kwargs)


class StudyPlanFile(models.Model):
    """
    Файлы, прикрепленные к плану занятий
    """

    study_plan = models.ForeignKey(
        StudyPlan,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="План занятий",
    )

    file = models.FileField(upload_to="study_plans/files/", verbose_name="Файл")

    name = models.CharField(max_length=255, verbose_name="Название файла")

    file_size = models.PositiveIntegerField(verbose_name="Размер файла (байт)")

    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="uploaded_study_plan_files",
        verbose_name="Загрузил",
    )

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Файл плана занятий"
        verbose_name_plural = "Файлы планов занятий"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} ({self.study_plan.title})"

    def save(self, *args, **kwargs):
        if self.file and not self.name:
            self.name = self.file.name
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class StudyPlanGeneration(models.Model):
    """
    Запросы на генерацию учебных планов через AI
    Хранит параметры запроса и статус генерации
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает обработки"
        PROCESSING = "processing", "Обрабатывается"
        COMPLETED = "completed", "Завершено"
        FAILED = "failed", "Ошибка"

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="study_plan_generations",
        limit_choices_to={"role": "teacher"},
        verbose_name="Преподаватель",
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="generated_study_plans",
        limit_choices_to={"role": "student"},
        verbose_name="Студент",
    )

    subject = models.ForeignKey(
        Subject,
        on_delete=models.CASCADE,
        related_name="study_plan_generations",
        verbose_name="Предмет",
    )

    # Связь с зачислением для валидации
    enrollment = models.ForeignKey(
        SubjectEnrollment,
        on_delete=models.CASCADE,
        related_name="study_plan_generations",
        verbose_name="Зачисление на предмет",
    )

    # Параметры генерации (JSON)
    # Содержит: subject, grade, topic, subtopics, goal, constraints
    parameters = models.JSONField(
        verbose_name="Параметры генерации",
        help_text="Содержит предмет, класс, тему, подтемы, цель, ограничения",
    )

    # Статус генерации
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )

    # Сообщение о прогрессе (для отображения пользователю во время генерации)
    progress_message = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Сообщение о прогрессе",
        help_text='Отображается во время генерации (например, "Генерация задачника...")',
    )

    # Сообщение об ошибке (если failed)
    error_message = models.TextField(null=True, blank=True, verbose_name="Сообщение об ошибке")

    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Дата завершения")

    class Meta:
        verbose_name = "Генерация учебного плана"
        verbose_name_plural = "Генерации учебных планов"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["teacher", "created_at"]),
            models.Index(fields=["student", "subject"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"Генерация плана {self.student.get_full_name()} - {self.subject.name} ({self.status})"
        )

    def clean(self):
        """
        Валидация перед сохранением
        Проверяет что студент зачислен на предмет к данному преподавателю
        """
        if self.enrollment:
            if self.enrollment.student != self.student:
                raise ValidationError("Студент в enrollment не совпадает")
            if self.enrollment.subject != self.subject:
                raise ValidationError("Предмет в enrollment не совпадает")
            if self.enrollment.teacher != self.teacher:
                raise ValidationError("Преподаватель в enrollment не совпадает")
            if not self.enrollment.is_active:
                raise ValidationError("Зачисление неактивно")

    def save(self, *args, **kwargs):
        # Автоматически установить completed_at при переходе в COMPLETED или FAILED
        if self.status in [self.Status.COMPLETED, self.Status.FAILED] and not self.completed_at:
            from django.utils import timezone

            self.completed_at = timezone.now()

        # Валидация enrollment если не указан
        if not self.enrollment:
            try:
                self.enrollment = SubjectEnrollment.objects.get(
                    student=self.student,
                    subject=self.subject,
                    teacher=self.teacher,
                    is_active=True,
                )
            except SubjectEnrollment.DoesNotExist:
                raise ValidationError("Студент не зачислен на этот предмет к данному преподавателю")

        super().save(*args, **kwargs)


class GeneratedFile(models.Model):
    """
    Файлы, сгенерированные в рамках учебного плана
    Один запрос генерации создает 4 файла: задачник, методичка, видео-подборка, недельный план
    """

    class FileType(models.TextChoices):
        PROBLEM_SET = "problem_set", "Задачник"
        REFERENCE_GUIDE = "reference_guide", "Методичка"
        VIDEO_LIST = "video_list", "Видео-подборка"
        WEEKLY_PLAN = "weekly_plan", "Недельный план"

    class Status(models.TextChoices):
        PENDING = "pending", "Ожидает генерации"
        GENERATING = "generating", "Генерируется"
        COMPILED = "compiled", "Скомпилирован"
        FAILED = "failed", "Ошибка"

    generation = models.ForeignKey(
        StudyPlanGeneration,
        on_delete=models.CASCADE,
        related_name="generated_files",
        verbose_name="Запрос на генерацию",
    )

    # Тип файла
    file_type = models.CharField(max_length=20, choices=FileType.choices, verbose_name="Тип файла")

    # Путь к сгенерированному файлу
    file = models.FileField(
        upload_to="study_plans/generated/", null=True, blank=True, verbose_name="Файл"
    )

    # Статус генерации файла
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Статус",
    )

    # Сообщение об ошибке (если failed)
    error_message = models.TextField(null=True, blank=True, verbose_name="Сообщение об ошибке")

    # Временные метки
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Сгенерированный файл"
        verbose_name_plural = "Сгенерированные файлы"
        ordering = ["generation", "file_type"]
        unique_together = ["generation", "file_type"]
        indexes = [
            models.Index(fields=["generation", "status"]),
        ]

    def __str__(self):
        return f"{self.get_file_type_display()} - {self.generation} ({self.status})"


class SubmissionFile(models.Model):
    """
    Файлы, загруженные в рамках ответа на материал.

    Каждый ответ (MaterialSubmission) может содержать несколько файлов.
    Максимум 10 файлов на ответ, максимум 50MB на файл, 200MB на ответ.
    """

    submission = models.ForeignKey(
        MaterialSubmission,
        on_delete=models.CASCADE,
        related_name="files",
        verbose_name="Ответ на материал",
    )

    file = models.FileField(upload_to="submissions/files/", verbose_name="Файл")

    original_filename = models.CharField(max_length=255, verbose_name="Исходное имя файла")

    file_size = models.PositiveIntegerField(verbose_name="Размер файла (байт)")

    file_type = models.CharField(
        max_length=20,
        verbose_name="Тип файла",
        help_text="Расширение файла (pdf, doc, jpg и т.д.)",
    )

    mime_type = models.CharField(max_length=100, verbose_name="MIME тип файла", blank=True)

    file_checksum = models.CharField(
        max_length=64,
        blank=True,
        verbose_name="SHA256 контрольная сумма",
        help_text="SHA256 hash для проверки целостности и обнаружения дубликатов",
    )

    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата загрузки")

    class Meta:
        verbose_name = "Файл ответа на материал"
        verbose_name_plural = "Файлы ответов на материалы"
        ordering = ["uploaded_at"]
        indexes = [
            models.Index(fields=["submission", "uploaded_at"]),
            models.Index(fields=["file_checksum", "submission"]),
        ]

    def __str__(self):
        return f"{self.original_filename} ({self.file_size} bytes)"

    def save(self, *args, **kwargs):
        """Автоматически заполнить размер файла при сохранении"""
        if self.file and not self.file_size:
            self.file_size = self.file.size
        super().save(*args, **kwargs)


class MaterialDownloadLog(models.Model):
    """
    Log всех загрузок материалов для отслеживания использования и аналитики.

    Отслеживает:
    - Какой пользователь загрузил материал
    - Когда загрузил
    - С какого IP адреса
    - Какой браузер/User-Agent
    - Размер файла для отслеживания пропускной способности
    """

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="download_logs",
        verbose_name="Материал",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="material_downloads",
        verbose_name="Пользователь",
    )

    ip_address = models.GenericIPAddressField(verbose_name="IP адрес")

    user_agent = models.TextField(verbose_name="User-Agent браузера")

    file_size = models.BigIntegerField(verbose_name="Размер файла (байты)", default=0)

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Время загрузки")

    class Meta:
        app_label = "materials"
        verbose_name = "Лог загрузки материала"
        verbose_name_plural = "Логи загрузок материалов"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["material", "timestamp"]),
            models.Index(fields=["user", "timestamp"]),
            models.Index(fields=["material", "user", "-timestamp"]),
            models.Index(fields=["ip_address", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.user.email} загрузил {self.material.title} ({self.timestamp})"

    @classmethod
    def should_log(cls, material_id: int, user_id: int, minutes: int = 60) -> bool:
        """
        Проверить, нужно ли логировать загрузку (не дублировать в течение времени).

        Если пользователь загружал один и тот же материал в течение N минут,
        это считается одной загрузкой (дедупликация).

        Args:
            material_id: ID материала
            user_id: ID пользователя
            minutes: Окно дедупликации (по умолчанию 60 минут)

        Returns:
            bool: True если нужно логировать, False если это дубль
        """
        cutoff_time = timezone.now() - timedelta(minutes=minutes)

        recent_log = cls.objects.filter(
            material_id=material_id, user_id=user_id, timestamp__gte=cutoff_time
        ).exists()

        return not recent_log


class BulkAssignmentAuditLog(models.Model):
    """
    Audit log for bulk material assignment operations.
    Tracks all bulk operations with details about what was performed,
    by whom, and the results.
    """

    class OperationType(models.TextChoices):
        BULK_ASSIGN_TO_STUDENTS = (
            "bulk_assign_to_students",
            "Bulk Assign Material to Students",
        )
        BULK_ASSIGN_MATERIALS = (
            "bulk_assign_materials",
            "Bulk Assign Materials to Student",
        )
        BULK_ASSIGN_TO_CLASS = (
            "bulk_assign_to_class",
            "Bulk Assign Materials to Class",
        )
        BULK_REMOVE = "bulk_remove", "Bulk Remove Assignments"
        BULK_UPDATE = "bulk_update", "Bulk Update Material Properties"
        BULK_DELETE = "bulk_delete", "Bulk Delete Materials"

    class Status(models.TextChoices):
        PROCESSING = "processing", "Processing"
        COMPLETED = "completed", "Completed"
        PARTIAL_FAILURE = "partial_failure", "Partial Failure"
        FAILED = "failed", "Failed"

    # Who performed the operation
    performed_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="bulk_assignment_logs",
        verbose_name="Performed By",
    )

    # Operation details
    operation_type = models.CharField(
        max_length=50,
        choices=OperationType.choices,
        verbose_name="Operation Type",
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PROCESSING,
        verbose_name="Status",
    )

    # Statistics
    total_items = models.IntegerField(default=0, verbose_name="Total Items")
    created_count = models.IntegerField(default=0, verbose_name="Created")
    skipped_count = models.IntegerField(default=0, verbose_name="Skipped")
    failed_count = models.IntegerField(default=0, verbose_name="Failed")

    # Failed items details (JSON format)
    failed_items = models.JSONField(default=list, blank=True, verbose_name="Failed Items")

    # Error message if operation failed
    error_message = models.TextField(null=True, blank=True, verbose_name="Error Message")

    # Operation metadata (JSON format)
    metadata = models.JSONField(default=dict, blank=True, verbose_name="Metadata")

    # Timing
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="Completed At")
    duration_seconds = models.FloatField(default=0, verbose_name="Duration (seconds)")

    class Meta:
        app_label = "materials"
        verbose_name = "Bulk Assignment Audit Log"
        verbose_name_plural = "Bulk Assignment Audit Logs"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["performed_by", "-created_at"]),
            models.Index(fields=["operation_type", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self):
        return (
            f"{self.get_operation_type_display()} - {self.get_status_display()} ({self.created_at})"
        )
