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
    help = "Создаёт тестовые учётные записи и профили для student/parent/teacher/tutor с одинаковым паролем"

    @transaction.atomic
    def handle(self, *args, **options):
        # ЕДИНЫЙ ПАРОЛЬ для всех тестовых аккаунтов
        TEST_PASSWORD = "TestPass123!"

        # Предсказуемые тестовые данные
        users_spec = [
            {
                "email": "student@test.com",
                "first_name": "Иван",
                "last_name": "Соколов",
                "role": User.Role.STUDENT,
                "password": TEST_PASSWORD,
            },
            {
                "email": "parent@test.com",
                "first_name": "Мария",
                "last_name": "Соколова",
                "role": User.Role.PARENT,
                "password": TEST_PASSWORD,
            },
            {
                "email": "teacher@test.com",
                "first_name": "Петр",
                "last_name": "Иванов",
                "role": User.Role.TEACHER,
                "password": TEST_PASSWORD,
            },
            {
                "email": "tutor@test.com",
                "first_name": "Сергей",
                "last_name": "Смирнов",
                "role": User.Role.TUTOR,
                "password": TEST_PASSWORD,
            },
            # Дополнительные тестовые аккаунты для разнообразия
            {
                "email": "student2@test.com",
                "first_name": "Александр",
                "last_name": "Петров",
                "role": User.Role.STUDENT,
                "password": TEST_PASSWORD,
            },
            {
                "email": "teacher2@test.com",
                "first_name": "Елена",
                "last_name": "Кузнецова",
                "role": User.Role.TEACHER,
                "password": TEST_PASSWORD,
            },
            {
                "email": "admin@test.com",
                "first_name": "Админ",
                "last_name": "Администратор",
                "role": User.Role.PARENT,  # Обычная роль для админа
                "password": TEST_PASSWORD,
                "is_staff": True,
                "is_superuser": True,
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
                    "is_staff": spec.get("is_staff", False),
                    "is_superuser": spec.get("is_superuser", False),
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
            user.is_staff = spec.get("is_staff", False)
            user.is_superuser = spec.get("is_superuser", False)
            user.save()

            # Сохраняем первого найденного пользователя каждой роли (кроме дублей)
            if spec["role"] not in created_or_existing:
                created_or_existing[spec["role"]] = user

            status = "🆕" if created else "♻️"
            self.stdout.write(
                self.style.SUCCESS(
                    f"{status} {spec['role']:10} -> {spec['email']:25} / {spec['password']}"
                )
            )

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

        # ParentProfile
        parent_profile, _ = ParentProfile.objects.get_or_create(user=parent)

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

        self.stdout.write("\n" + "="*80)
        self.stdout.write(self.style.SUCCESS("✅ ТЕСТОВЫЕ АККАУНТЫ ГОТОВЫ!"))
        self.stdout.write("="*80)
        self.stdout.write(f"\n🔐 ЕДИНЫЙ ПАРОЛЬ ДЛЯ ВСЕХ: {TEST_PASSWORD}\n")
        self.stdout.write(self.style.WARNING("📋 ТЕСТОВЫЕ УЧЁТНЫЕ ДАННЫЕ:"))
        self.stdout.write("-"*80)
        self.stdout.write(f"👨‍🎓 СТУДЕНТ        | Email: student@test.com           | Пароль: {TEST_PASSWORD}")
        self.stdout.write(f"👩‍👧 РОДИТЕЛЬ       | Email: parent@test.com            | Пароль: {TEST_PASSWORD}")
        self.stdout.write(f"👨‍🏫 ПРЕПОДАВАТЕЛЬ | Email: teacher@test.com           | Пароль: {TEST_PASSWORD}")
        self.stdout.write(f"👨‍💼 ТЬЮТОР        | Email: tutor@test.com             | Пароль: {TEST_PASSWORD}")
        self.stdout.write(f"👨‍🎓 СТУДЕНТ 2      | Email: student2@test.com          | Пароль: {TEST_PASSWORD}")
        self.stdout.write(f"👩‍🏫 ПРЕПОДАВАТЕЛЬ 2| Email: teacher2@test.com          | Пароль: {TEST_PASSWORD}")
        self.stdout.write(f"👑 АДМИНИСТРАТОР  | Email: admin@test.com             | Пароль: {TEST_PASSWORD}")
        self.stdout.write("-"*80)
        self.stdout.write("\n⚙️  СВЯЗИ:")
        self.stdout.write(f"   • Студент связан с тьютором '{tutor.get_full_name()}' и родителем '{parent.get_full_name()}'")
        self.stdout.write(f"   • Студент 2 независим (может быть связан через админ панель)")
        self.stdout.write("\n💡 СОВЕТ: Запомните email и пароль выше для входа в приложение")
        self.stdout.write("="*80 + "\n")


