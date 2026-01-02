from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction

from accounts.models import (
    User,
    StudentProfile,
    TeacherProfile,
    TutorProfile,
    ParentProfile,
    TutorStudentCreation,
)
from materials.models import Subject, SubjectEnrollment
from rest_framework.authtoken.models import Token

from accounts.tutor_service import StudentCreationService


class Command(BaseCommand):
    help = (
        "Полная очистка пользователей платформы и пересоздание базовых учетных записей. "
        "Действие НЕОБРАТИМО. Используйте только в dev/тест окружениях."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Начинаю полную очистку пользователей и связанных профилей..."))

        # 1) Очистка зависимых сущностей, где есть ссылки на пользователей
        #    Порядок важен, чтобы избежать constraint ошибок.
        deleted_counts: list[tuple[str, int]] = []

        # Удаляем записи назначений предметов
        count, _ = SubjectEnrollment.objects.all().delete()
        deleted_counts.append(("SubjectEnrollment", count))

        # Удаляем логи создания учеников
        count, _ = TutorStudentCreation.objects.all().delete()
        deleted_counts.append(("TutorStudentCreation", count))

        # Удаляем токены аутентификации
        count, _ = Token.objects.all().delete()
        deleted_counts.append(("Token", count))

        # Профили удаляются каскадно при удалении пользователей, но подчистим явно
        for model in (StudentProfile, TeacherProfile, TutorProfile, ParentProfile):
            count, _ = model.objects.all().delete()
            deleted_counts.append((model.__name__, count))

        # 2) Удаляем всех пользователей, включая суперпользователей
        UserModel = get_user_model()
        count, _ = UserModel.objects.all().delete()
        deleted_counts.append((UserModel.__name__, count))

        self.stdout.write(self.style.SUCCESS("Очистка завершена."))
        for name, c in deleted_counts:
            self.stdout.write(f" - {name}: удалено {c}")

        # 3) Пересоздаем тестовые учетные записи как в create_test_users_all.py (логины/пароли те же)
        self.stdout.write(self.style.WARNING("Создаю тестовые учетные записи и профили (как в create_test_users_all.py)..."))

        # Администратор (оставим для удобства)
        UserModel.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="admin12345",
            first_name="Админ",
            last_name="Платформы",
        )

        # Пользователи из create_test_users_all.py
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

        created = {}
        for spec in users_spec:
            user = UserModel.objects.create_user(
                username=spec["email"],
                email=spec["email"],
                password=spec["password"],
                first_name=spec["first_name"],
                last_name=spec["last_name"],
                role=spec["role"],
                is_active=True,
                is_verified=True,
            )
            created[spec["role"]] = user

        student = created[User.Role.STUDENT]
        parent = created[User.Role.PARENT]
        teacher = created[User.Role.TEACHER]
        tutor = created[User.Role.TUTOR]

        # Профили и связи (прокаченные значения как в примере)
        TeacherProfile.objects.update_or_create(
            user=teacher,
            defaults={
                "subject": "Математика",
                "experience_years": 5,
                "bio": "Тестовый преподаватель.",
            },
        )

        TutorProfile.objects.update_or_create(
            user=tutor,
            defaults={
                "specialization": "Индивидуальные образовательные траектории",
                "experience_years": 3,
                "bio": "Тестовый тьютор.",
            },
        )

        parent_profile, _ = ParentProfile.objects.get_or_create(user=parent)

        StudentProfile.objects.update_or_create(
            user=student,
            defaults={
                "grade": "9",
                "goal": "Подготовка к экзаменам",
                "parent": parent,
                "tutor": tutor,
                "generated_username": student.email,
                "generated_password": "test123",
            },
        )

        # Для удобства отображения студентов у тьютора
        student.created_by_tutor = tutor
        student.save(update_fields=["created_by_tutor"])

        # Создаем SubjectEnrollment для активации forum chats
        # Получаем или создаем предмет "Математика"
        subject, _ = Subject.objects.get_or_create(
            name="Математика",
            defaults={
                "description": "Основной предмет для тестирования",
                "color": "#3B82F6",
            },
        )

        # Создаем SubjectEnrollment для связи student → teacher
        # Это триггирует сигнал create_forum_chat_on_enrollment
        # который создает FORUM_SUBJECT чат (student ↔ teacher)
        SubjectEnrollment.objects.get_or_create(
            student=student,
            subject=subject,
            teacher=teacher,
            defaults={
                "assigned_by": tutor,
                "is_active": True,
            },
        )

        # Создаем SubjectEnrollment для связи student → tutor
        # Это триггирует сигнал create_forum_chat_on_enrollment
        # который создает FORUM_TUTOR чат (student ↔ tutor)
        SubjectEnrollment.objects.get_or_create(
            student=student,
            subject=subject,
            teacher=tutor,
            defaults={
                "assigned_by": tutor,
                "is_active": True,
            },
        ) 

        # Итоговый вывод
        self.stdout.write(self.style.SUCCESS("Тестовые аккаунты и профили готовы."))
        self.stdout.write("Credentials:")
        self.stdout.write(" - admin / admin12345 (superuser)")
        self.stdout.write(" - test_student@example.com / test123 (student)")
        self.stdout.write(" - test_parent@example.com / test123 (parent)")
        self.stdout.write(" - test_teacher@example.com / test123 (teacher)")
        self.stdout.write(" - test_tutor@example.com / test123 (tutor)")

        self.stdout.write(self.style.SUCCESS("Готово."))


