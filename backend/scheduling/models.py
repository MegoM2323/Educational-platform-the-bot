"""
Simplified lesson scheduling models.

Single Lesson model replacing TeacherAvailability, TimeSlot, and Booking.
"""

import uuid
import datetime
from datetime import timedelta
from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone

User = get_user_model()


class LessonManager(models.Manager):
    """
    Кастомный менеджер для модели Lesson.

    Обеспечивает вызов валидации при создании через Manager.create().
    Это предотвращает обход валидации при использовании Lesson.objects.create().
    """

    def create(self, **kwargs):
        """
        Создание урока с обязательной валидацией.

        Переопределяет стандартный create() чтобы гарантировать вызов full_clean()
        перед сохранением, независимо от способа создания объекта.
        """
        obj = self.model(**kwargs)
        obj.full_clean()
        obj.save(force_insert=True, using=self.db)
        return obj


class Lesson(models.Model):
    """
    Single lesson between teacher and student.

    Replaces complex TeacherAvailability + TimeSlot + Booking system
    with direct lesson creation by teachers.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending confirmation"
        CONFIRMED = "confirmed", "Confirmed"
        COMPLETED = "completed", "Completed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    teacher = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="taught_lessons",
        limit_choices_to={"role": "teacher"},
        verbose_name="Teacher",
    )

    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="student_lessons",
        limit_choices_to={"role": "student"},
        verbose_name="Student",
    )

    subject = models.ForeignKey(
        "materials.Subject",
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="Subject",
    )

    date = models.DateField(verbose_name="Lesson date")
    start_time = models.TimeField(verbose_name="Start time")
    end_time = models.TimeField(verbose_name="End time")

    description = models.TextField(blank=True, verbose_name="Lesson description")

    notes = models.TextField(blank=True, default="", verbose_name="Lesson notes")

    telemost_link = models.URLField(
        blank=True, max_length=500, verbose_name="Yandex Telemost link"
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Кастомный менеджер для валидации при create()
    objects = LessonManager()

    class Meta:
        verbose_name = "Lesson"
        verbose_name_plural = "Lessons"
        ordering = ["date", "start_time"]
        indexes = [
            models.Index(fields=["teacher", "date"]),
            models.Index(fields=["student", "date"]),
            models.Index(fields=["subject", "date"]),
            models.Index(fields=["status"]),
            models.Index(fields=["teacher", "student", "status"]),
        ]

    def __str__(self):
        return (
            f"{self.teacher.get_full_name()} - {self.student.get_full_name()} - "
            f"{self.subject.name} - {self.date} {self.start_time}"
        )

    @property
    def datetime_start(self):
        """Full datetime of lesson start."""
        dt = datetime.datetime.combine(self.date, self.start_time)
        if timezone.is_aware(dt):
            return dt
        try:
            return timezone.make_aware(dt)
        except Exception:
            # Если не удалось сделать datetime aware, возвращаем naive datetime
            return dt

    @property
    def datetime_end(self):
        """Full datetime of lesson end."""
        dt = datetime.datetime.combine(self.date, self.end_time)
        if timezone.is_aware(dt):
            return dt
        try:
            return timezone.make_aware(dt)
        except Exception:
            # Если не удалось сделать datetime aware, возвращаем naive datetime
            return dt

    @property
    def is_upcoming(self):
        """Check if lesson is in the future."""
        return self.datetime_start > timezone.now()

    @property
    def can_cancel(self):
        """Check if lesson can be cancelled (at least 2 hours before start)."""
        if self.status in ["cancelled", "completed"]:
            return False
        time_until_lesson = self.datetime_start - timezone.now()
        return time_until_lesson > timedelta(hours=2)

    def clean(self):
        """Validate lesson data."""
        # Validate time range
        if self.start_time and self.end_time:
            if self.start_time >= self.end_time:
                raise ValidationError("Start time must be before end time")

            duration = datetime.datetime.combine(
                datetime.date.today(), self.end_time
            ) - datetime.datetime.combine(datetime.date.today(), self.start_time)
            min_duration = timedelta(minutes=30)
            max_duration = timedelta(hours=4)
            if duration < min_duration:
                raise ValidationError("Lesson duration must be at least 30 minutes")
            if duration > max_duration:
                raise ValidationError("Lesson duration must not exceed 4 hours")

        # Validate date not in past
        now = timezone.now()
        if self.date:
            if self.date < now.date():
                raise ValidationError("Cannot create lesson in the past")
            # Validate start_time for today's date
            if (
                self.date == now.date()
                and self.start_time
                and self.start_time < now.time()
            ):
                raise ValidationError(
                    "Cannot create lesson with start time in the past for today"
                )

        # Validate teacher teaches subject to student (via SubjectEnrollment)
        if self.teacher and self.student and self.subject:
            from materials.models import SubjectEnrollment

            try:
                enrollment = SubjectEnrollment.objects.select_related(
                    "teacher", "student", "subject"
                ).get(
                    student=self.student,
                    teacher=self.teacher,
                    subject=self.subject,
                    is_active=True,
                )
            except SubjectEnrollment.DoesNotExist:
                raise ValidationError(
                    f"Teacher {self.teacher.get_full_name()} does not teach "
                    f"{self.subject.name} to student {self.student.get_full_name()}"
                )

    def save(self, *args, skip_validation=False, **kwargs):
        """
        Override save to enforce validation.

        Всегда вызывает full_clean() перед сохранением.
        Это гарантирует что:
        - start_time < end_time
        - date не в прошлом
        - Существует активный SubjectEnrollment для teacher/student/subject

        Args:
            skip_validation: If True, skip full_clean() (only for testing past dates)
        """
        # Запускаем полную валидацию перед сохранением, если не пропущена
        if not skip_validation:
            self.full_clean()
        super().save(*args, **kwargs)


class LessonHistory(models.Model):
    """
    Audit trail for lesson changes.

    Tracks all modifications to lessons for accountability.
    """

    ACTION_CHOICES = [
        ("created", "Created"),
        ("updated", "Updated"),
        ("cancelled", "Cancelled"),
        ("completed", "Completed"),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    lesson = models.ForeignKey(
        Lesson, on_delete=models.CASCADE, related_name="history", verbose_name="Lesson"
    )

    action = models.CharField(
        max_length=20, choices=ACTION_CHOICES, verbose_name="Action"
    )

    performed_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, verbose_name="Performed by"
    )

    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="Timestamp")

    old_values = models.JSONField(null=True, blank=True, verbose_name="Old values")

    new_values = models.JSONField(null=True, blank=True, verbose_name="New values")

    class Meta:
        verbose_name = "Lesson history"
        verbose_name_plural = "Lesson histories"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["lesson", "-timestamp"]),
        ]

    def __str__(self):
        # Обрабатываем случай когда performed_by может быть None
        performer = self.performed_by.get_full_name() if self.performed_by else "System"
        return f"{self.lesson} - {self.get_action_display()} by {performer} - {self.timestamp}"
