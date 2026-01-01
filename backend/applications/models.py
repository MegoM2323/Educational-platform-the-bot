import uuid
from django.db import models
from django.core.validators import EmailValidator
from django.utils import timezone
from django.conf import settings


class Application(models.Model):
    """
    Application model for user registration system
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    class ApplicantType(models.TextChoices):
        STUDENT = "student", "Student"
        TEACHER = "teacher", "Teacher"
        PARENT = "parent", "Parent"

    # Personal Information
    first_name = models.CharField(max_length=100, verbose_name="First Name")
    last_name = models.CharField(max_length=100, verbose_name="Last Name")
    email = models.EmailField(validators=[EmailValidator()], verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Phone")
    telegram_id = models.CharField(
        max_length=100, blank=True, verbose_name="Telegram ID"
    )

    # Application Details
    applicant_type = models.CharField(
        max_length=20,
        choices=ApplicantType.choices,
        default=ApplicantType.STUDENT,
        verbose_name="Applicant Type",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        verbose_name="Status",
    )
    tracking_token = models.UUIDField(
        default=uuid.uuid4, unique=True, verbose_name="Tracking Token"
    )

    # Additional Information
    grade = models.CharField(
        max_length=10, blank=True, verbose_name="Grade"
    )  # For students
    subject = models.CharField(
        max_length=100, blank=True, verbose_name="Subject"
    )  # For teachers
    experience = models.TextField(blank=True, verbose_name="Experience")
    motivation = models.TextField(blank=True, verbose_name="Motivation")

    # Parent Information (for student applications)
    parent_first_name = models.CharField(
        max_length=100, blank=True, verbose_name="Parent First Name"
    )
    parent_last_name = models.CharField(
        max_length=100, blank=True, verbose_name="Parent Last Name"
    )
    parent_email = models.EmailField(blank=True, verbose_name="Parent Email")
    parent_phone = models.CharField(
        max_length=20, blank=True, verbose_name="Parent Phone"
    )
    parent_telegram_id = models.CharField(
        max_length=100, blank=True, verbose_name="Parent Telegram ID"
    )

    # System Fields
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Created At")
    processed_at = models.DateTimeField(
        blank=True, null=True, verbose_name="Processed At"
    )
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="Processed By",
    )

    # Generated Credentials (только username, пароли не хранятся в БД)
    generated_username = models.CharField(
        max_length=150, blank=True, verbose_name="Generated Username"
    )
    parent_username = models.CharField(
        max_length=150, blank=True, verbose_name="Parent Username"
    )

    # Legacy fields for backward compatibility
    telegram_message_id = models.CharField(
        max_length=50, blank=True, null=True, verbose_name="Telegram Message ID"
    )
    notes = models.TextField(blank=True, verbose_name="Admin Notes")

    class Meta:
        verbose_name = "Application"
        verbose_name_plural = "Applications"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Application from {self.first_name} {self.last_name} ({self.get_applicant_type_display()})"

    def save(self, *args, **kwargs):
        # Automatically update processed_at when status changes from PENDING
        if self.status != self.Status.PENDING and not self.processed_at:
            self.processed_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def is_pending(self):
        return self.status == self.Status.PENDING

    @property
    def is_processed(self):
        return self.status in [self.Status.APPROVED, self.Status.REJECTED]

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def parent_full_name(self):
        if self.parent_first_name and self.parent_last_name:
            return f"{self.parent_first_name} {self.parent_last_name}"
        return ""
