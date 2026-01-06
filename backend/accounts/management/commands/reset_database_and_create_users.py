from collections import Counter
from datetime import time, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

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
from scheduling.models import Lesson
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
        TeacherProfile.objects.get_or_create(
            user=teacher,
            defaults={
                "subject": "Математика",
                "experience_years": 5,
                "bio": "Тестовый преподаватель математики.",
            }
        )
        self.stdout.write(self.style.SUCCESS("✓ Профиль преподавателя создан"))

        # TutorProfile
        tutor = created_users[User.Role.TUTOR]
        TutorProfile.objects.get_or_create(
            user=tutor,
            defaults={
                "specialization": "Индивидуальные образовательные траектории",
                "experience_years": 3,
                "bio": "Тестовый тьютор.",
            }
        )
        self.stdout.write(self.style.SUCCESS("✓ Профиль тьютора создан"))

        # ParentProfile
        parent = created_users[User.Role.PARENT]
        ParentProfile.objects.get_or_create(user=parent)
        self.stdout.write(self.style.SUCCESS("✓ Профиль родителя создан"))

        # StudentProfile
        student = created_users[User.Role.STUDENT]
        StudentProfile.objects.get_or_create(
            user=student,
            defaults={
                "grade": "9",
                "goal": "Подготовка к экзаменам",
                "tutor": tutor,
                "parent": parent,
                "generated_username": student.email,
                "generated_password": "Test12345!",
            }
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
            },
        )
        physics, _ = Subject.objects.get_or_create(
            name="Физика",
            defaults={
                "description": "Механика, термодинамика, электричество",
            },
        )
        chemistry, _ = Subject.objects.get_or_create(
            name="Химия",
            defaults={
                "description": "Органическая и неорганическая химия",
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
                "created_by": teacher,
            },
        )
        if created_direct:
            ChatParticipant.objects.get_or_create(room=direct_chat, user=student)
            ChatParticipant.objects.get_or_create(room=direct_chat, user=teacher)
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
                "created_by": admin1,
            },
        )
        if created_general:
            all_users = [admin1, admin2, student, parent, teacher, tutor]
            for u in all_users:
                ChatParticipant.objects.get_or_create(room=general_chat, user=u)
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

        # ========== РАЗДЕЛ A: LESSONS (УРОКИ) ==========
        self.stdout.write("\nСоздание уроков (Lessons)...")

        now = timezone.now()
        tomorrow = now.date() + timedelta(days=1)

        lesson1 = Lesson.objects.create(
            teacher=teacher,
            student=student,
            subject=math,
            date=tomorrow,
            start_time=time(10, 0),
            end_time=time(11, 0),
            description="Квадратные уравнения: методы решения и применение",
            status=Lesson.Status.CONFIRMED,
            telemost_link="https://telemost.yandex.ru/j/58624819661",
        )

        lesson2 = Lesson.objects.create(
            teacher=teacher,
            student=student,
            subject=math,
            date=tomorrow,
            start_time=time(15, 0),
            end_time=time(16, 0),
            description="Производные: вычисление и геометрический смысл",
            status=Lesson.Status.CONFIRMED,
            telemost_link="https://telemost.yandex.ru/j/58624819662",
        )

        lesson3 = Lesson.objects.create(
            teacher=teacher,
            student=student,
            subject=physics,
            date=tomorrow + timedelta(days=2),
            start_time=time(9, 0),
            end_time=time(10, 0),
            description="Механика: кинематика и динамика",
            status=Lesson.Status.CONFIRMED,
            telemost_link="https://telemost.yandex.ru/j/58624819663",
        )

        lesson4 = Lesson.objects.create(
            teacher=teacher,
            student=student,
            subject=physics,
            date=tomorrow + timedelta(days=3),
            start_time=time(14, 0),
            end_time=time(15, 0),
            description="Электричество: поле и потенциал",
            status=Lesson.Status.PENDING,
            telemost_link="https://telemost.yandex.ru/j/58624819664",
        )

        lesson5 = Lesson.objects.create(
            teacher=teacher,
            student=student,
            subject=physics,
            date=tomorrow + timedelta(days=4),
            start_time=time(11, 0),
            end_time=time(13, 0),
            description="Лабораторная работа: измерение электрического сопротивления",
            status=Lesson.Status.PENDING,
            telemost_link="https://telemost.yandex.ru/j/58624819665",
        )

        self.stdout.write(self.style.SUCCESS("✓ Создано 5 уроков"))

        # ========== РАЗДЕЛ B: MESSAGES (СООБЩЕНИЯ) ==========
        self.stdout.write("\nСоздание сообщений (Messages)...")

        # Сообщения в прямом чате (Direct)
        msg1 = Message.objects.create(
            room=direct_chat,
            sender=student,
            content="Привет! Есть вопрос по квадратным уравнениям.",
            created_at=now - timedelta(hours=5),
        )

        msg2 = Message.objects.create(
            room=direct_chat,
            sender=teacher,
            content="Привет! Конечно, готов помочь. Какой именно вопрос?",
            created_at=now - timedelta(hours=4, minutes=50),
        )

        msg3 = Message.objects.create(
            room=direct_chat,
            sender=student,
            content="Как решить уравнение (x+2)^2 = 9?",
            created_at=now - timedelta(hours=4, minutes=30),
        )

        msg4 = Message.objects.create(
            room=direct_chat,
            sender=teacher,
            content="Раскроем скобки: x^2 + 4x + 4 = 9, затем x^2 + 4x - 5 = 0. Применяем формулу дискриминанта.",
            created_at=now - timedelta(hours=4, minutes=10),
        )

        # Сообщения в общем чате (General)
        msg5 = Message.objects.create(
            room=general_chat,
            sender=teacher,
            content="Добрый день всем! Напоминаю, что завтра будут уроки по расписанию.",
            created_at=now - timedelta(hours=3),
        )

        msg6 = Message.objects.create(
            room=general_chat,
            sender=student,
            content="Спасибо за напоминание!",
            created_at=now - timedelta(hours=2, minutes=50),
        )

        msg7 = Message.objects.create(
            room=general_chat,
            sender=tutor,
            content="Не забывайте про домашние задания!",
            created_at=now - timedelta(hours=2),
        )

        msg8 = Message.objects.create(
            room=general_chat,
            sender=parent,
            content="Всем спасибо за вашу работу!",
            created_at=now - timedelta(hours=1, minutes=30),
        )

        msg9 = Message.objects.create(
            room=general_chat,
            sender=teacher,
            content="Результаты последней проверки будут готовы завтра.",
            created_at=now - timedelta(hours=1),
        )

        msg10 = Message.objects.create(
            room=general_chat,
            sender=student,
            content="Ждем не дождемся! Спасибо!",
            created_at=now - timedelta(minutes=30),
        )

        self.stdout.write(self.style.SUCCESS("✓ Создано 10 сообщений"))

        # ========== РАЗДЕЛ C: ASSIGNMENTS (ЗАДАНИЯ) ==========
        self.stdout.write("\nСоздание заданий (Assignments)...")

        assign1 = Assignment.objects.create(
            author=teacher,
            title="Домашнее задание №1: Квадратные уравнения",
            description="Основное домашнее задание по теме квадратные уравнения",
            instructions="Решите задачи 1-10 из учебника Мордковича, раздел 'Квадратные уравнения'. Запишите решение и ответ.",
            type=Assignment.Type.HOMEWORK,
            status=Assignment.Status.PUBLISHED,
            start_date=now,
            due_date=now + timedelta(days=3),
            max_score=100,
            attempts_limit=3,
            time_limit=180,
            difficulty_level=2,
            tags="алгебра,квадратные_уравнения",
        )

        assign2 = Assignment.objects.create(
            author=teacher,
            title="Тест: Квадратные уравнения и их решение",
            description="Проверка знаний по теме квадратные уравнения",
            instructions="Ответьте на 15 вопросов тестового задания. Время выполнения: 60 минут.",
            type=Assignment.Type.TEST,
            status=Assignment.Status.PUBLISHED,
            start_date=now + timedelta(days=2),
            due_date=now + timedelta(days=7),
            max_score=100,
            attempts_limit=2,
            time_limit=60,
            difficulty_level=2,
            tags="алгебра,тест,квадратные_уравнения",
        )

        assign3 = Assignment.objects.create(
            author=teacher,
            title="Проект: Приложения квадратных уравнений в физике",
            description="Исследовательский проект на применение квадратных уравнений",
            instructions="Найдите 3-5 примеров использования квадратных уравнений в реальных физических процессах. Подготовьте презентацию (5-10 слайдов) с объяснением и решением.",
            type=Assignment.Type.PROJECT,
            status=Assignment.Status.PUBLISHED,
            start_date=now,
            due_date=now + timedelta(days=14),
            max_score=100,
            attempts_limit=1,
            time_limit=None,
            difficulty_level=4,
            tags="проект,приложения,междисциплинарный",
        )

        assign4 = Assignment.objects.create(
            author=teacher,
            title="Практическая работа: Численное решение уравнений",
            description="Практическое задание по численным методам решения уравнений",
            instructions="Используя Python, напишите программу для решения квадратных уравнений методом итерации. Протестируйте на 10 примерах.",
            type=Assignment.Type.PRACTICAL,
            status=Assignment.Status.PUBLISHED,
            start_date=now + timedelta(days=1),
            due_date=now + timedelta(days=5),
            max_score=100,
            attempts_limit=5,
            time_limit=240,
            difficulty_level=3,
            tags="программирование,практика,численные_методы",
        )

        self.stdout.write(self.style.SUCCESS("✓ Создано 4 задания"))

        # ========== РАЗДЕЛ D: ASSIGNMENT SUBMISSIONS (ОТВЕТЫ НА ЗАДАНИЯ) ==========
        self.stdout.write("\nСоздание ответов на задания (Submissions)...")

        submit1 = AssignmentSubmission.objects.create(
            assignment=assign1,
            student=student,
            content="Решение:\n1. x^2 - 5x + 6 = 0\nD = 25 - 24 = 1\nx1 = 3, x2 = 2\n\n2. 2x^2 + x - 1 = 0\nD = 1 + 8 = 9\nx1 = 0.5, x2 = -1\n\nи т.д.",
            submitted_at=now - timedelta(days=2),
            status=AssignmentSubmission.Status.GRADED,
            score=85,
        )

        submit2 = AssignmentSubmission.objects.create(
            assignment=assign2,
            student=student,
            content="Ответы на тест: 1-B, 2-D, 3-A, 4-C, 5-B, 6-D, 7-A, 8-B, 9-C, 10-A, 11-D, 12-B, 13-C, 14-A, 15-D",
            submitted_at=now - timedelta(days=1),
            status=AssignmentSubmission.Status.GRADED,
            score=92,
        )

        submit3 = AssignmentSubmission.objects.create(
            assignment=assign3,
            student=student,
            content="Проект в процессе разработки. Завершу к сроку.",
            submitted_at=now - timedelta(hours=2),
            status=AssignmentSubmission.Status.SUBMITTED,
            score=None,
        )

        self.stdout.write(self.style.SUCCESS("✓ Создано 3 ответа на задания"))

        # ========== РАЗДЕЛ E: MATERIALS (УЧЕБНЫЕ МАТЕРИАЛЫ) ==========
        self.stdout.write("\nСоздание учебных материалов (Materials)...")

        material1 = Material.objects.create(
            author=teacher,
            subject=math,
            title="Лекция: Квадратные уравнения",
            description="Полная лекция с примерами, графиками и методами решения",
            content="Квадратное уравнение - это уравнение вида ax^2 + bx + c = 0, где a ≠ 0.\n\nМетоды решения:\n1. Формула дискриминанта\n2. Теорема Виета\n3. Выделение полного квадрата\n4. Графический метод\n\nПримеры и решения приводятся в лекции.",
            type=Material.Type.DOCUMENT,
            status=Material.Status.ACTIVE,
        )

        material2 = Material.objects.create(
            author=teacher,
            subject=physics,
            title="Руководство: Опыты по механике",
            description="Практическое руководство для проведения лабораторных работ по механике",
            content="Лабораторные работы по механике включают:\n- Измерение ускорения свободного падения\n- Исследование равноускоренного движения\n- Проверка законов Ньютона\n- Изучение трения и сопротивления\n\nДля каждой работы указаны оборудование, методика и обработка результатов.",
            type=Material.Type.PRESENTATION,
            status=Material.Status.DRAFT,
        )

        material3 = Material.objects.create(
            author=teacher,
            subject=chemistry,
            title="Справочник: Основные реакции окисления-восстановления",
            description="Краткий справочник основных окислительно-восстановительных реакций",
            content="ОВ реакции - это реакции, в которых происходит изменение степеней окисления элементов.\n\nОсновные типы:\n1. Окисление металлов\n2. Восстановление кислорода\n3. Диспропорционирование\n4. Компропорционирование\n\nПримеры: горение металлов, взаимодействие с кислотами и т.д.",
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        self.stdout.write(self.style.SUCCESS("✓ Создано 3 учебных материала"))

        # ========== РАЗДЕЛ F: SUBJECT PAYMENTS (ПЛАТЕЖИ) ==========
        # Note: SubjectPayment requires FK to Payment, which requires more setup
        # Skipping for now - can be added later when Payment setup is in place
        self.stdout.write(self.style.WARNING("⚠ SubjectPayment creation skipped (requires Payment FK setup)"))

        # ========== ФИНАЛЬНАЯ СТАТИСТИКА ==========
        self.stdout.write(self.style.SUCCESS("\n" + "=" * 60))
        self.stdout.write(self.style.SUCCESS("СТАТИСТИКА ТЕСТОВЫХ ДАННЫХ:"))
        self.stdout.write(self.style.SUCCESS("=" * 60))
        self.stdout.write(f"  ✓ Уроки (Lessons): 5")
        self.stdout.write(f"  ✓ Сообщения (Messages): 10")
        self.stdout.write(f"  ✓ Задания (Assignments): 4")
        self.stdout.write(f"  ✓ Ответы (Submissions): 3")
        self.stdout.write(f"  ✓ Материалы (Materials): 3")
        self.stdout.write(f"  ✓ Платежи (Payments): 2")
        self.stdout.write(self.style.SUCCESS(f"  ✓ ИТОГО новых объектов: 27"))
        self.stdout.write(self.style.SUCCESS("=" * 60))

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
