from collections import Counter

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
from materials.models import (
    Subject,
    TeacherSubject,
    SubjectEnrollment,
    SubjectPayment,
    SubjectSubscription,
    Material,
    MaterialProgress,
    MaterialComment,
    MaterialSubmission,
    MaterialFeedback,
)
from chat.models import (
    ChatRoom,
    Message,
    MessageRead,
    MessageThread,
    ChatParticipant,
)
from assignments.models import (
    Assignment,
    AssignmentSubmission,
    AssignmentQuestion,
    AssignmentAnswer,
)
from payments.models import Payment
from reports.models import (
    Report,
    ReportTemplate,
    ReportRecipient,
    AnalyticsData,
    StudentReport,
    ReportSchedule,
)
from notifications.models import (
    Notification,
    NotificationTemplate,
    NotificationSettings,
    NotificationQueue,
)
from applications.models import Application
from rest_framework.authtoken.models import Token


class Command(BaseCommand):
    help = (
        "Полная очистка всех данных из БД платформы и создание 2 админов "
        "и тестовых пользователей. Действие НЕОБРАТИМО. Используйте только в dev/тест окружениях."
    )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("=" * 60))
        self.stdout.write(self.style.WARNING("НАЧИНАЮ ПОЛНУЮ ОЧИСТКУ БД"))
        self.stdout.write(self.style.WARNING("=" * 60))

        deleted_counts = []

        # Порядок удаления важен из-за внешних ключей
        # Сначала удаляем модели с зависимостями, потом основные

        # 1. Уведомления
        self.stdout.write("Удаление уведомлений...")
        count, _ = NotificationQueue.objects.all().delete()
        deleted_counts.append(("NotificationQueue", count))
        count, _ = Notification.objects.all().delete()
        deleted_counts.append(("Notification", count))
        count, _ = NotificationSettings.objects.all().delete()
        deleted_counts.append(("NotificationSettings", count))
        count, _ = NotificationTemplate.objects.all().delete()
        deleted_counts.append(("NotificationTemplate", count))

        # 2. Отчеты
        self.stdout.write("Удаление отчетов...")
        count, _ = ReportSchedule.objects.all().delete()
        deleted_counts.append(("ReportSchedule", count))
        count, _ = StudentReport.objects.all().delete()
        deleted_counts.append(("StudentReport", count))
        count, _ = AnalyticsData.objects.all().delete()
        deleted_counts.append(("AnalyticsData", count))
        count, _ = ReportRecipient.objects.all().delete()
        deleted_counts.append(("ReportRecipient", count))
        count, _ = ReportTemplate.objects.all().delete()
        deleted_counts.append(("ReportTemplate", count))
        count, _ = Report.objects.all().delete()
        deleted_counts.append(("Report", count))

        # 3. Платежи
        self.stdout.write("Удаление платежей...")
        count, _ = Payment.objects.all().delete()
        deleted_counts.append(("Payment", count))
        count, _ = SubjectPayment.objects.all().delete()
        deleted_counts.append(("SubjectPayment", count))
        count, _ = SubjectSubscription.objects.all().delete()
        deleted_counts.append(("SubjectSubscription", count))

        # 4. Задания
        self.stdout.write("Удаление заданий...")
        count, _ = AssignmentAnswer.objects.all().delete()
        deleted_counts.append(("AssignmentAnswer", count))
        count, _ = AssignmentQuestion.objects.all().delete()
        deleted_counts.append(("AssignmentQuestion", count))
        count, _ = AssignmentSubmission.objects.all().delete()
        deleted_counts.append(("AssignmentSubmission", count))
        count, _ = Assignment.objects.all().delete()
        deleted_counts.append(("Assignment", count))

        # 5. Материалы
        self.stdout.write("Удаление материалов...")
        count, _ = MaterialFeedback.objects.all().delete()
        deleted_counts.append(("MaterialFeedback", count))
        count, _ = MaterialSubmission.objects.all().delete()
        deleted_counts.append(("MaterialSubmission", count))
        count, _ = MaterialComment.objects.all().delete()
        deleted_counts.append(("MaterialComment", count))
        count, _ = MaterialProgress.objects.all().delete()
        deleted_counts.append(("MaterialProgress", count))
        count, _ = Material.objects.all().delete()
        deleted_counts.append(("Material", count))
        count, _ = SubjectEnrollment.objects.all().delete()
        deleted_counts.append(("SubjectEnrollment", count))
        count, _ = TeacherSubject.objects.all().delete()
        deleted_counts.append(("TeacherSubject", count))
        count, _ = Subject.objects.all().delete()
        deleted_counts.append(("Subject", count))

        # 6. Чат
        self.stdout.write("Удаление чатов...")
        count, _ = MessageRead.objects.all().delete()
        deleted_counts.append(("MessageRead", count))
        count, _ = MessageThread.objects.all().delete()
        deleted_counts.append(("MessageThread", count))
        count, _ = Message.objects.all().delete()
        deleted_counts.append(("Message", count))
        count, _ = ChatParticipant.objects.all().delete()
        deleted_counts.append(("ChatParticipant", count))
        count, _ = ChatRoom.objects.all().delete()
        deleted_counts.append(("ChatRoom", count))

        # 7. Заявки
        self.stdout.write("Удаление заявок...")
        count, _ = Application.objects.all().delete()
        deleted_counts.append(("Application", count))

        # 8. Профили пользователей и связанные данные
        self.stdout.write("Удаление профилей пользователей...")
        count, _ = TutorStudentCreation.objects.all().delete()
        deleted_counts.append(("TutorStudentCreation", count))
        count, _ = StudentProfile.objects.all().delete()
        deleted_counts.append(("StudentProfile", count))
        count, _ = TeacherProfile.objects.all().delete()
        deleted_counts.append(("TeacherProfile", count))
        count, _ = TutorProfile.objects.all().delete()
        deleted_counts.append(("TutorProfile", count))
        count, _ = ParentProfile.objects.all().delete()
        deleted_counts.append(("ParentProfile", count))

        # 9. Токены аутентификации
        self.stdout.write("Удаление токенов...")
        count, _ = Token.objects.all().delete()
        deleted_counts.append(("Token", count))

        # 10. Пользователи (в последнюю очередь)
        self.stdout.write("Удаление пользователей...")
        UserModel = get_user_model()
        count, _ = UserModel.objects.all().delete()
        deleted_counts.append(("User", count))

        self.stdout.write(self.style.SUCCESS("\nОчистка завершена. Статистика:"))
        total_deleted = 0
        for name, c in deleted_counts:
            if c > 0:
                self.stdout.write(f"  - {name}: {c}")
                total_deleted += c
        self.stdout.write(f"\nВсего удалено записей: {total_deleted}")

        # Создание пользователей
        self.stdout.write(self.style.WARNING("\n" + "=" * 60))
        self.stdout.write(self.style.WARNING("СОЗДАНИЕ ПОЛЬЗОВАТЕЛЕЙ"))
        self.stdout.write(self.style.WARNING("=" * 60))

        # Создаем 2 админов
        admin1 = UserModel.objects.create_superuser(
            username="admin1",
            email="admin1@example.com",
            password="Admin12345!",
            first_name="Админ",
            last_name="Первый",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(
            self.style.SUCCESS(f"✓ Админ 1 создан: admin1@example.com / Admin12345!")
        )

        admin2 = UserModel.objects.create_superuser(
            username="admin2",
            email="admin2@example.com",
            password="Admin12345!",
            first_name="Админ",
            last_name="Второй",
            is_active=True,
            is_staff=True,
            is_superuser=True,
        )
        self.stdout.write(
            self.style.SUCCESS(f"✓ Админ 2 создан: admin2@example.com / Admin12345!")
        )

        # Создаем тестовых пользователей
        test_users = [
            {
                "email": "test_student@example.com",
                "username": "test_student@example.com",
                "first_name": "Test",
                "last_name": "Student",
                "role": User.Role.STUDENT,
                "password": "Test12345!",
            },
            {
                "email": "test_parent@example.com",
                "username": "test_parent@example.com",
                "first_name": "Test",
                "last_name": "Parent",
                "role": User.Role.PARENT,
                "password": "Test12345!",
            },
            {
                "email": "test_teacher@example.com",
                "username": "test_teacher@example.com",
                "first_name": "Test",
                "last_name": "Teacher",
                "role": User.Role.TEACHER,
                "password": "Test12345!",
            },
            {
                "email": "test_tutor@example.com",
                "username": "test_tutor@example.com",
                "first_name": "Test",
                "last_name": "Tutor",
                "role": User.Role.TUTOR,
                "password": "Test12345!",
            },
        ]

        created_users = {}
        for user_spec in test_users:
            user = UserModel.objects.create_user(
                username=user_spec["username"],
                email=user_spec["email"],
                password=user_spec["password"],
                first_name=user_spec["first_name"],
                last_name=user_spec["last_name"],
                role=user_spec["role"],
                is_active=True,
                is_verified=True,
            )
            created_users[user_spec["role"]] = user
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ {user_spec['role']} создан: {user_spec['email']} / {user_spec['password']}"
                )
            )

        # Создаем профили для пользователей
        self.stdout.write("\nСоздание профилей...")

        # TeacherProfile
        teacher = created_users[User.Role.TEACHER]
        TeacherProfile.objects.create(
            user=teacher,
            subject="Математика",
            experience_years=5,
            bio="Тестовый преподаватель математики.",
        )
        self.stdout.write(self.style.SUCCESS("✓ Профиль преподавателя создан"))

        # TutorProfile
        tutor = created_users[User.Role.TUTOR]
        TutorProfile.objects.create(
            user=tutor,
            specialization="Индивидуальные образовательные траектории",
            experience_years=3,
            bio="Тестовый тьютор.",
        )
        self.stdout.write(self.style.SUCCESS("✓ Профиль тьютора создан"))

        # ParentProfile
        parent = created_users[User.Role.PARENT]
        ParentProfile.objects.create(user=parent)
        self.stdout.write(self.style.SUCCESS("✓ Профиль родителя создан"))

        # StudentProfile
        student = created_users[User.Role.STUDENT]
        StudentProfile.objects.create(
            user=student,
            grade="9",
            goal="Подготовка к экзаменам",
            tutor=tutor,
            parent=parent,
            generated_username=student.email,
            generated_password="Test12345!",
        )
        student.created_by_tutor = tutor
        student.save(update_fields=["created_by_tutor"])
        self.stdout.write(self.style.SUCCESS("✓ Профиль студента создан"))

        # Создание предметов и связей
        self.stdout.write("\nСоздание предметов и связей...")

        # 1. Создание предметов
        math, _ = Subject.objects.get_or_create(
            name="Математика",
            defaults={
                "description": "Алгебра, геометрия, математический анализ",
                "grade_level": "9-11",
            },
        )
        physics, _ = Subject.objects.get_or_create(
            name="Физика",
            defaults={
                "description": "Механика, термодинамика, электричество",
                "grade_level": "9-11",
            },
        )
        chemistry, _ = Subject.objects.get_or_create(
            name="Химия",
            defaults={
                "description": "Органическая и неорганическая химия",
                "grade_level": "9-11",
            },
        )
        self.stdout.write(
            self.style.SUCCESS("✓ Создано 3 предмета: Математика, Физика, Химия")
        )

        # 2. TeacherSubject связи
        ts1, created1 = TeacherSubject.objects.get_or_create(
            teacher=teacher, subject=math
        )
        ts2, created2 = TeacherSubject.objects.get_or_create(
            teacher=teacher, subject=physics
        )
        count_ts = sum([created1, created2])
        self.stdout.write(
            self.style.SUCCESS(f"✓ Создано {count_ts} связей Teacher → Subject")
        )

        # 3. SubjectEnrollment (КРИТИЧНО - автоматически создаст чаты через сигналы)
        enrollment1, created_e1 = SubjectEnrollment.objects.get_or_create(
            student=student,
            teacher=teacher,
            subject=math,
            defaults={"assigned_by": teacher},
        )
        enrollment2, created_e2 = SubjectEnrollment.objects.get_or_create(
            student=student,
            teacher=teacher,
            subject=physics,
            defaults={"assigned_by": teacher},
        )
        count_enrollments = sum([created_e1, created_e2])
        self.stdout.write(
            self.style.SUCCESS(
                f"✓ Создано {count_enrollments} SubjectEnrollment (Student → Teacher → Subject)"
            )
        )

        # 4. Явное создание DIRECT чата (если сигналы не сработали)
        direct_chat, created_direct = ChatRoom.objects.get_or_create(
            type="DIRECT",
            defaults={
                "name": f"Chat: {student.first_name} ↔ {teacher.first_name}",
                "description": "Direct message between student and teacher",
            },
        )
        if created_direct:
            ChatParticipant.objects.get_or_create(chat_room=direct_chat, user=student)
            ChatParticipant.objects.get_or_create(chat_room=direct_chat, user=teacher)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Создан DIRECT чат: {direct_chat.name} (2 участника)"
                )
            )
        else:
            self.stdout.write(self.style.WARNING("⚠ DIRECT чат уже существовал"))

        # 5. Явное создание GENERAL чата
        general_chat, created_general = ChatRoom.objects.get_or_create(
            type="GENERAL",
            defaults={
                "name": "Общий чат",
                "description": "Общий чат для всех пользователей платформы",
            },
        )
        if created_general:
            all_users = [admin1, admin2, student, parent, teacher, tutor]
            for u in all_users:
                ChatParticipant.objects.get_or_create(chat_room=general_chat, user=u)
            self.stdout.write(
                self.style.SUCCESS(
                    f"✓ Создан GENERAL чат: {general_chat.name} ({len(all_users)} участников)"
                )
            )
        else:
            self.stdout.write(self.style.WARNING("⚠ GENERAL чат уже существовал"))

        # Подсчет всех чатов
        total_chats = ChatRoom.objects.count()
        total_participants = ChatParticipant.objects.count()
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ ИТОГО чатов: {total_chats} (участников: {total_participants})"
            )
        )

        # Вывод типов созданных чатов
        chat_types = ChatRoom.objects.values_list("type", flat=True)
        chat_type_counts = Counter(chat_types)
        for chat_type, count in chat_type_counts.items():
            self.stdout.write(f"  - {chat_type}: {count}")

        # Итоговый вывод
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("ГОТОВО! Созданные учетные записи:"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write("\nАдминистраторы:")
        self.stdout.write("  - admin1@example.com / Admin12345!")
        self.stdout.write("  - admin2@example.com / Admin12345!")
        self.stdout.write("\nТестовые пользователи:")
        self.stdout.write("  - test_student@example.com / Test12345! (student)")
        self.stdout.write("  - test_parent@example.com / Test12345! (parent)")
        self.stdout.write("  - test_teacher@example.com / Test12345! (teacher)")
        self.stdout.write("  - test_tutor@example.com / Test12345! (tutor)")
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
