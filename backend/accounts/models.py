from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator, MaxValueValidator, MaxLengthValidator
from django.core.exceptions import ValidationError


class User(AbstractUser):
    """
    Расширенная модель пользователя с ролями
    """

    class Role(models.TextChoices):
        STUDENT = "student", "Студент"
        TEACHER = "teacher", "Преподаватель"
        TUTOR = "tutor", "Тьютор"
        PARENT = "parent", "Родитель"
        ADMIN = "admin", "Администратор"

    password = models.CharField(max_length=256, blank=True, null=True)

    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.STUDENT, verbose_name="Роль"
    )

    phone = models.CharField(
        max_length=20,
        validators=[
            RegexValidator(
                regex=r"^\+?1?\d{9,15}$",
                message="Номер телефона должен быть в формате: '+999999999'. До 15 цифр.",
            )
        ],
        blank=True,
        verbose_name="Телефон",
    )

    avatar = models.ImageField(
        upload_to="avatars/", blank=True, null=True, verbose_name="Аватар"
    )

    is_verified = models.BooleanField(default=False, verbose_name="Подтвержден")

    created_by_tutor = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_users",
        verbose_name="Создан тьютором",
    )

    telegram_id = models.BigIntegerField(
        null=True,
        blank=True,
        unique=True,
        verbose_name="Telegram ID",
        help_text="Числовой ID пользователя в Telegram",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    def clean(self):
        """
        Validate created_by_tutor relationship.

        IMPORTANT: This method is NOT automatically called on save().
        Callers MUST explicitly call full_clean() or clean() before save()
        to trigger this validation. This is by design - Django does not automatically
        call clean() in model.save() to avoid performance overhead.

        Validation is primarily handled in serializers via DRF's validation framework,
        which guarantees full_clean() is called on all model instances before creation.
        """
        errors = {}

        if self.created_by_tutor:
            if self.created_by_tutor.role != User.Role.TUTOR:
                errors["created_by_tutor"] = "created_by_tutor must have TUTOR role"
            elif not self.created_by_tutor.is_active:
                errors["created_by_tutor"] = "created_by_tutor must be active"
            elif self.created_by_tutor.id == self.id:
                errors["created_by_tutor"] = "Cannot set created_by_tutor to self"

        if errors:
            raise ValidationError(errors)


class StudentProfile(models.Model):
    """
    Профиль студента
    """

    GRADE_CHOICES = [(i, str(i)) for i in range(1, 13)]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )

    grade = models.IntegerField(
        choices=GRADE_CHOICES,
        blank=True,
        null=True,
        verbose_name="Класс",
        help_text="Student grade (1-12)",
    )

    goal = models.TextField(
        blank=True,
        max_length=1000,
        validators=[MaxLengthValidator(1000)],
        verbose_name="Цель обучения",
    )

    tutor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="tutored_students",
        limit_choices_to={"role": "tutor"},
        verbose_name="Тьютор",
    )

    parent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children_students",
        limit_choices_to={"role": "parent"},
        verbose_name="Родитель",
    )

    progress_percentage = models.PositiveIntegerField(
        default=0, validators=[MaxValueValidator(100)], verbose_name="Прогресс (%)"
    )

    streak_days = models.PositiveIntegerField(default=0, verbose_name="Дней подряд")

    total_points = models.PositiveIntegerField(default=0, verbose_name="Общие баллы")

    accuracy_percentage = models.PositiveIntegerField(
        default=0, validators=[MaxValueValidator(100)], verbose_name="Точность (%)"
    )

    generated_username = models.CharField(
        max_length=150, blank=True, verbose_name="Сгенерированное имя пользователя"
    )

    telegram = models.CharField(
        max_length=100, blank=True, verbose_name="Telegram (например: @username)"
    )

    telegram_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Telegram Chat ID",
        help_text="Числовой ID чата Telegram для отправки уведомлений (например: 123456789)",
    )

    def __str__(self):
        return f"Профиль студента: {self.user.get_full_name()}"

    def clean(self):
        """Валидация связей с тьютором и родителем"""
        errors = {}

        if self.tutor:
            if self.tutor.role != User.Role.TUTOR:
                errors["tutor"] = "Тьютор должен иметь роль 'Тьютор'"
            elif not self.tutor.is_active:
                errors["tutor"] = "Тьютор должен быть активным"

        if self.parent:
            if self.parent.role != User.Role.PARENT:
                errors["parent"] = "Родитель должен иметь роль 'Родитель'"
            elif not self.parent.is_active:
                errors["parent"] = "Родитель должен быть активным"

        if errors:
            raise ValidationError(errors)

    def delete(self, *args, **kwargs):
        """
        Cascade delete related data when StudentProfile is deleted.
        Removes all enrollments, lessons, chat participants associated with the student.
        """
        from materials.models import SubjectEnrollment
        from scheduling.models import Lesson
        from chat.models import ChatParticipant

        SubjectEnrollment.objects.filter(student=self.user).delete()
        Lesson.objects.filter(student=self.user).delete()
        ChatParticipant.objects.filter(user=self.user).delete()

        super().delete(*args, **kwargs)


class TeacherProfile(models.Model):
    """
    Профиль преподавателя
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="teacher_profile"
    )

    subject = models.CharField(
        max_length=100, blank=True, default="", verbose_name="Предмет"
    )

    experience_years = models.PositiveIntegerField(
        default=0, verbose_name="Опыт работы (лет)"
    )

    bio = models.TextField(blank=True, verbose_name="Биография")

    telegram = models.CharField(
        max_length=100, blank=True, verbose_name="Telegram (например: @username)"
    )

    telegram_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Telegram Chat ID",
        help_text="Числовой ID чата Telegram для отправки уведомлений (например: 123456789)",
    )

    def __str__(self):
        return f"Профиль преподавателя: {self.user.get_full_name()}"


class TutorProfile(models.Model):
    """
    Профиль тьютора
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="tutor_profile"
    )

    specialization = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Специализация"
    )

    experience_years = models.PositiveIntegerField(
        default=0, verbose_name="Опыт работы (лет)"
    )

    bio = models.TextField(blank=True, verbose_name="Биография")

    telegram = models.CharField(
        max_length=100, blank=True, verbose_name="Telegram (например: @username)"
    )

    telegram_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Telegram Chat ID",
        help_text="Числовой ID чата Telegram для отправки уведомлений (например: 123456789)",
    )

    def __str__(self):
        return f"Профиль тьютора: {self.user.get_full_name()}"


class ParentProfile(models.Model):
    """
    Профиль родителя
    """

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="parent_profile"
    )

    telegram = models.CharField(
        max_length=100, blank=True, verbose_name="Telegram (например: @username)"
    )

    telegram_id = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Telegram Chat ID",
        help_text="Числовой ID чата Telegram для отправки уведомлений (например: 123456789)",
    )

    def __str__(self):
        return f"Профиль родителя: {self.user.get_full_name()}"

    @property
    def children(self):
        """
        Получить детей родителя через обратную связь StudentProfile.parent
        """
        try:
            return User.objects.filter(
                student_profile__parent=self.user, role=User.Role.STUDENT
            )
        except Exception:
            return User.objects.none()


class TutorStudentCreation(models.Model):
    """
    Запись о создании ученика тьютором с сохранением выданных учетных данных
    """

    tutor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="created_students",
        verbose_name="Тьютор",
    )
    student = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="creation_record",
        verbose_name="Ученик",
    )
    parent = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="parent_creation_record",
        verbose_name="Родитель",
    )
    student_username = models.CharField(
        max_length=150, default="", verbose_name="Имя пользователя ученика"
    )
    parent_username = models.CharField(
        max_length=150, default="", verbose_name="Имя пользователя родителя"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Создание ученика тьютором"
        verbose_name_plural = "Создания учеников тьютором"
        ordering = ["-created_at"]


class TelegramLinkToken(models.Model):
    """
    Токен для привязки Telegram аккаунта к веб-аккаунту пользователя
    """

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="telegram_link_tokens",
        verbose_name="Пользователь",
    )
    token = models.CharField(
        max_length=256, unique=True, db_index=True, verbose_name="Токен"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Создан")
    expires_at = models.DateTimeField(verbose_name="Истекает")
    is_used = models.BooleanField(default=False, verbose_name="Использован")
    used_at = models.DateTimeField(null=True, blank=True, verbose_name="Использован в")

    class Meta:
        verbose_name = "Токен привязки Telegram"
        verbose_name_plural = "Токены привязки Telegram"
        ordering = ["-created_at"]

    def __str__(self):
        return f"TelegramLinkToken({self.user.email}, used={self.is_used})"

    def set_token(self, plain_token: str) -> None:
        """
        Хешируем и сохраняем токен.

        Args:
            plain_token: Plaintext токен для хеширования (UUID или подобное)
        """
        from django.contrib.auth.hashers import make_password

        self.token = make_password(plain_token)

    def verify_token(self, plain_token: str) -> bool:
        """
        Проверяем что plain_token совпадает с хешированным токеном.

        Args:
            plain_token: Plaintext токен для проверки

        Returns:
            True если токен совпадает, False иначе
        """
        from django.contrib.auth.hashers import check_password

        return check_password(plain_token, self.token)

    def is_expired(self) -> bool:
        """Проверяет истек ли токен"""
        from django.utils import timezone

        return timezone.now() > self.expires_at
