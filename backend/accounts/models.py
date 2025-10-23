from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import RegexValidator


class User(AbstractUser):
    """
    Расширенная модель пользователя с ролями
    Аутентификация происходит через Supabase
    """
    class Role(models.TextChoices):
        STUDENT = 'student', 'Студент'
        TEACHER = 'teacher', 'Преподаватель'
        TUTOR = 'tutor', 'Тьютор'
        PARENT = 'parent', 'Родитель'

    # Делаем пароль необязательным, так как аутентификация через Supabase
    password = models.CharField(max_length=128, blank=True, null=True)
    
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STUDENT,
        verbose_name='Роль'
    )
    
    phone = models.CharField(
        max_length=20,
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message="Номер телефона должен быть в формате: '+999999999'. До 15 цифр."
        )],
        blank=True,
        verbose_name='Телефон'
    )
    
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        verbose_name='Аватар'
    )
    
    is_verified = models.BooleanField(
        default=False,
        verbose_name='Подтвержден'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"


class StudentProfile(models.Model):
    """
    Профиль студента
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='student_profile'
    )
    
    grade = models.CharField(
        max_length=10,
        verbose_name='Класс'
    )
    
    goal = models.TextField(
        blank=True,
        verbose_name='Цель обучения'
    )
    
    tutor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tutored_students',
        verbose_name='Тьютор'
    )
    
    parent = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='children',
        verbose_name='Родитель'
    )
    
    progress_percentage = models.PositiveIntegerField(
        default=0,
        verbose_name='Прогресс (%)'
    )
    
    streak_days = models.PositiveIntegerField(
        default=0,
        verbose_name='Дней подряд'
    )
    
    total_points = models.PositiveIntegerField(
        default=0,
        verbose_name='Общие баллы'
    )
    
    accuracy_percentage = models.PositiveIntegerField(
        default=0,
        verbose_name='Точность (%)'
    )

    def __str__(self):
        return f"Профиль студента: {self.user.get_full_name()}"


class TeacherProfile(models.Model):
    """
    Профиль преподавателя
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='teacher_profile'
    )
    
    subject = models.CharField(
        max_length=100,
        verbose_name='Предмет'
    )
    
    experience_years = models.PositiveIntegerField(
        default=0,
        verbose_name='Опыт работы (лет)'
    )
    
    bio = models.TextField(
        blank=True,
        verbose_name='Биография'
    )

    def __str__(self):
        return f"Профиль преподавателя: {self.user.get_full_name()}"


class TutorProfile(models.Model):
    """
    Профиль тьютора
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='tutor_profile'
    )
    
    specialization = models.CharField(
        max_length=200,
        verbose_name='Специализация'
    )
    
    experience_years = models.PositiveIntegerField(
        default=0,
        verbose_name='Опыт работы (лет)'
    )
    
    bio = models.TextField(
        blank=True,
        verbose_name='Биография'
    )

    def __str__(self):
        return f"Профиль тьютора: {self.user.get_full_name()}"


class ParentProfile(models.Model):
    """
    Профиль родителя
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='parent_profile'
    )
    
    children = models.ManyToManyField(
        User,
        related_name='parents',
        blank=True,
        verbose_name='Дети'
    )

    def __str__(self):
        return f"Профиль родителя: {self.user.get_full_name()}"
