from django.core.management.base import BaseCommand
from django.db import transaction
from django.apps import apps

from accounts.models import (
    User,
    StudentProfile,
    TeacherProfile,
    TutorProfile,
    ParentProfile,
)


TEST_USERS = [
    {"email": "test_student@example.com", "first_name": "Test", "last_name": "Student", "role": User.Role.STUDENT},
    {"email": "test_parent@example.com", "first_name": "Test", "last_name": "Parent", "role": User.Role.PARENT},
    {"email": "test_teacher@example.com", "first_name": "Test", "last_name": "Teacher", "role": User.Role.TEACHER},
    {"email": "test_tutor@example.com", "first_name": "Test", "last_name": "Tutor", "role": User.Role.TUTOR},
]


class Command(BaseCommand):
    help = "Полная очистка данных БД и приведение к известному тестовому набору (4 пользователя). Пароль: test123"

    @transaction.atomic
    def handle(self, *args, **options):
        keep_emails = {u["email"] for u in TEST_USERS}

        # 1) Полностью очищаем все модели, кроме системных и User
        #    Системные: contenttypes.ContentType, auth.Permission, auth.Group, sessions.Session
        #    Пользователей удалим выборочно ниже
        system_models = {
            "contenttypes.ContentType",
            "auth.Permission",
            "auth.Group",
            "sessions.Session",
        }

        for model in apps.get_models():
            label = f"{model._meta.app_label}.{model.__name__}"
            if label in system_models:
                continue
            if model is User:
                continue
            try:
                model.objects.all().delete()
            except Exception:
                # В случае сложных зависимостей попробуем позже — но мы идём широкой зачисткой
                pass

        # 2) Удаляем всех пользователей, кроме тестовых
        User.objects.exclude(email__in=keep_emails).delete()

        # 3) Создаём/обновляем тестовых пользователей с паролем test123
        created = {}
        for spec in TEST_USERS:
            user, _ = User.objects.get_or_create(
                email=spec["email"],
                defaults={
                    "username": spec["email"],
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                    "role": spec["role"],
                    "is_active": True,
                    "is_verified": True,
                },
            )
            user.first_name = spec["first_name"]
            user.last_name = spec["last_name"]
            user.role = spec["role"]
            user.is_active = True
            user.is_verified = True
            user.set_password("test123")
            user.save()
            created[spec["role"]] = user
            self.stdout.write(self.style.SUCCESS(f"User ready: {user.email} / test123"))

        # 4) Воссоздаём базовые профили и связи
        student = created[User.Role.STUDENT]
        parent = created[User.Role.PARENT]
        teacher = created[User.Role.TEACHER]
        tutor = created[User.Role.TUTOR]

        TeacherProfile.objects.update_or_create(
            user=teacher,
            defaults={"subject": "Математика", "experience_years": 5, "bio": "Тестовый преподаватель."},
        )

        TutorProfile.objects.update_or_create(
            user=tutor,
            defaults={"specialization": "Индивидуальные траектории", "experience_years": 3, "bio": "Тестовый тьютор."},
        )

        parent_profile, _ = ParentProfile.objects.get_or_create(user=parent)

        StudentProfile.objects.update_or_create(
            user=student,
            defaults={
                "grade": "9",
                "goal": "Подготовка к экзаменам",
                "tutor": tutor,
                "parent": parent,
                "generated_username": student.email,
                "generated_password": "test123",
            },
        )

        self.stdout.write(self.style.SUCCESS("База данных очищена. Оставлены только 4 тестовых пользователя и профили."))


