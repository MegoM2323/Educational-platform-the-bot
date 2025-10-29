from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import (
    User,
    StudentProfile,
    TeacherProfile,
    TutorProfile,
    ParentProfile,
)


class Command(BaseCommand):
    help = "Создаёт тестовые учётные записи и профили для student/parent/teacher/tutor"

    @transaction.atomic
    def handle(self, *args, **options):
        # Предсказуемые тестовые данные
        users_spec = [
            {
                "email": "test_student@example.com",
                "first_name": "Test",
                "last_name": "Student",
                "role": User.Role.STUDENT,
                "password": "test123",
            },
            {
                "email": "test_parent@example.com",
                "first_name": "Test",
                "last_name": "Parent",
                "role": User.Role.PARENT,
                "password": "test123",
            },
            {
                "email": "test_teacher@example.com",
                "first_name": "Test",
                "last_name": "Teacher",
                "role": User.Role.TEACHER,
                "password": "test123",
            },
            {
                "email": "test_tutor@example.com",
                "first_name": "Test",
                "last_name": "Tutor",
                "role": User.Role.TUTOR,
                "password": "test123",
            },
        ]

        created_or_existing = {}

        # Создаём/обновляем пользователей
        for spec in users_spec:
            user, created = User.objects.get_or_create(
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

            # Устанавливаем/обновляем пароль (для повторного запуска)
            if spec.get("password"):
                user.set_password(spec["password"])
            # Обновляем базовые поля на случай, если пользователь существовал
            user.first_name = spec["first_name"]
            user.last_name = spec["last_name"]
            user.role = spec["role"]
            user.is_active = True
            user.is_verified = True
            user.save()

            created_or_existing[spec["role"]] = user
            self.stdout.write(self.style.SUCCESS(f"OK: {spec['role']} -> {spec['email']} / {spec['password']}"))

        # Профили и связи
        student = created_or_existing[User.Role.STUDENT]
        parent = created_or_existing[User.Role.PARENT]
        teacher = created_or_existing[User.Role.TEACHER]
        tutor = created_or_existing[User.Role.TUTOR]

        # TeacherProfile
        TeacherProfile.objects.update_or_create(
            user=teacher,
            defaults={
                "subject": "Математика",
                "experience_years": 5,
                "bio": "Тестовый преподаватель."
            },
        )

        # TutorProfile
        TutorProfile.objects.update_or_create(
            user=tutor,
            defaults={
                "specialization": "Индивидуальные образовательные траектории",
                "experience_years": 3,
                "bio": "Тестовый тьютор."
            },
        )

        # ParentProfile + связь с ребёнком
        parent_profile, _ = ParentProfile.objects.get_or_create(user=parent)
        parent_profile.children.set([student])
        parent_profile.save()

        # StudentProfile + связи с тьютором/родителем
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

        self.stdout.write(self.style.SUCCESS("Тестовые аккаунты и профили готовы."))


