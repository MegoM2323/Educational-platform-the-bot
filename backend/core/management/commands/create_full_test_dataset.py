"""
Django management команда для создания полного тестового датасета.

КРИТИЧЕСКОЕ ТРЕБОВАНИЕ: Датасет создается ЕСТЕСТВЕННО, как если бы его создавали реальные пользователи.

Правильная последовательность создания:
1. Admin (admin@test.com) УЖЕ СУЩЕСТВУЕТ - НЕ создается
2. Проверяются существующие пользователи (созданные командой create_test_users_all)
3. Создаются/проверяются профили для всех ролей
4. Родитель ПРИВЯЗЫВАЕТСЯ к студентам через StudentProfile.parent
5. Tutor назначает студентам предметы с преподавателями (SubjectEnrollment)
6. После структуры создаются материалы, работы, планы, отчеты, чаты

Создает:
- Профили пользователей (StudentProfile, TeacherProfile, ParentProfile)
- Связь Parent → Students (StudentProfile.parent)
- Subject Enrollments (записи на предметы от тьютора)
- Materials (учебные материалы с файлами)
- Material Submissions (работы студентов)
- Study Plans (учебные планы с файлами)
- Assignments (домашние задания)
- Reports (отчеты преподавателей → тьютору, тьютора → родителю)
- Chat Rooms и Messages
- Notifications (включая специальные для родителей)
"""

import io
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List, Optional

from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from accounts.models import User, StudentProfile, TeacherProfile, ParentProfile
from materials.models import (
    Subject,
    TeacherSubject,
    SubjectEnrollment,
    Material,
    MaterialSubmission,
    StudyPlan,
    StudyPlanFile,
)
from assignments.models import Assignment, AssignmentSubmission
from reports.models import StudentReport, TutorWeeklyReport, TeacherWeeklyReport
from chat.models import ChatRoom, Message
from notifications.models import Notification


class Colors:
    """ANSI цвета для терминала."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class Command(BaseCommand):
    """Команда для создания полного тестового датасета."""

    help = 'Создает полный тестовый датасет для всех ролей пользователей (естественным образом)'

    def __init__(self):
        super().__init__()
        self.stats = {
            'profiles_created': 0,
            'parent_links': 0,
            'enrollments': 0,
            'materials': 0,
            'material_submissions': 0,
            'study_plans': 0,
            'study_plan_files': 0,
            'assignments': 0,
            'assignment_submissions': 0,
            'student_reports': 0,
            'tutor_reports': 0,
            'teacher_reports': 0,
            'chat_rooms': 0,
            'messages': 0,
            'notifications': 0,
        }
        self.errors: List[str] = []
        self.verbose = False

    def add_arguments(self, parser):
        """Добавляет аргументы командной строки."""
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Удалить все тестовые данные перед созданием новых',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Подробный вывод процесса создания',
        )

    def handle(self, *args, **options):
        """Главный метод выполнения команды."""
        self.verbose = options['verbose']

        self.print_header("Создание полного тестового датасета")
        self.print_info("Датасет создается ЕСТЕСТВЕННО, как реальными пользователями")

        if options['clear']:
            self.clear_test_data()

        # Проверяем существующих пользователей и создаем профили
        users = self.verify_and_prepare_users()
        if not users:
            self.print_error("Не найдены тестовые пользователи!")
            self.print_warning("Сначала запустите: python manage.py create_test_users_all")
            return

        # Получаем предметы
        subjects = self.get_subjects()
        if not subjects:
            self.print_error("Не найдены предметы!")
            self.print_warning("Сначала запустите: python manage.py create_test_subjects")
            return

        # Создаем данные в ЕСТЕСТВЕННОЙ последовательности
        try:
            with transaction.atomic():
                # 1. Привязываем родителя к студентам (Tutor связывает Parent → Students)
                self.link_parents_to_students(users)

                # 2. Tutor назначает студентам предметы с преподавателями
                enrollments = self.create_subject_enrollments(users, subjects)

                # 3. Преподаватели создают материалы для предметов
                self.create_materials(enrollments, users)

                # 4. Студенты выполняют работы по материалам
                self.create_material_submissions(enrollments, users)

                # 5. Преподаватели создают учебные планы для студентов
                self.create_study_plans(enrollments, users)

                # 6. Преподаватели создают домашние задания
                self.create_assignments(enrollments, users)

                # 7. Преподаватели → Тьютору, Тьютор → Родителю отчеты
                self.create_reports(users, enrollments)

                # 8. Создаем чаты и сообщения между всеми участниками
                self.create_chat_rooms_and_messages(users)

                # 9. Уведомления для всех (специальные для родителей)
                self.create_notifications(users)

            self.print_summary()

        except Exception as e:
            self.print_error(f"Критическая ошибка: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def verify_and_prepare_users(self) -> Dict[str, User]:
        """
        Проверяет существующих пользователей и создает профили где нужно.

        Пользователи ДОЛЖНЫ быть созданы командой create_test_users_all.
        Эта функция ТОЛЬКО проверяет их наличие и создает профили.
        """
        self.print_section("Проверка тестовых пользователей и создание профилей")

        users = {}
        test_users_config = [
            ('student@test.com', 'student', StudentProfile, {
                'grade': '10 класс',
                'goal': 'Подготовка к ЕГЭ по математике и физике',
                'progress_percentage': 65,
                'streak_days': 12,
                'total_points': 850,
                'accuracy_percentage': 78,
            }),
            ('student2@test.com', 'student', StudentProfile, {
                'grade': '9 класс',
                'goal': 'Улучшение успеваемости по русскому языку',
                'progress_percentage': 45,
                'streak_days': 5,
                'total_points': 420,
                'accuracy_percentage': 65,
            }),
            ('teacher@test.com', 'teacher', TeacherProfile, {
                'subject': 'Математика',
                'experience_years': 8,
                'bio': 'Опытный преподаватель математики, специализация - подготовка к ЕГЭ',
            }),
            ('teacher2@test.com', 'teacher', TeacherProfile, {
                'subject': 'Русский язык',
                'experience_years': 5,
                'bio': 'Преподаватель русского языка и литературы',
            }),
            ('tutor@test.com', 'tutor', None, {}),
            ('parent@test.com', 'parent', ParentProfile, {}),
        ]

        for email, expected_role, profile_model, profile_data in test_users_config:
            try:
                user = User.objects.get(email=email)

                if user.role != expected_role:
                    self.print_warning(f"  Пользователь {email} имеет роль {user.role}, ожидалась {expected_role}")

                users[email] = user

                # Создаем профиль если нужно
                if profile_model and expected_role != 'tutor':  # Tutor использует TeacherProfile
                    profile_attr = f"{expected_role}_profile"
                    if not hasattr(user, profile_attr) or getattr(user, profile_attr, None) is None:
                        profile = profile_model.objects.create(user=user, **profile_data)  # ✅ user, not recipient
                        self.stats['profiles_created'] += 1
                        self.print_success(f"  Создан профиль для {user.get_full_name()} ({user.role})")
                    else:
                        self.print_info(f"  Профиль существует: {user.get_full_name()} ({user.role})")
                else:
                    # Для тьютора проверяем TeacherProfile
                    if expected_role == 'tutor':
                        if not hasattr(user, 'teacher_profile') or user.teacher_profile is None:
                            profile = TeacherProfile.objects.create(
                                user=user,  # ✅ user, not recipient
                                subject='Тьюторство',
                                experience_years=3,
                                bio='Тьютор, координирует обучение студентов'
                            )
                            self.stats['profiles_created'] += 1
                            self.print_success(f"  Создан профиль тьютора для {user.get_full_name()}")
                        else:
                            self.print_info(f"  Профиль тьютора существует: {user.get_full_name()}")

                self.print_success(f"  {user.get_full_name()} ({user.role}) - OK")

            except User.DoesNotExist:
                self.print_warning(f"  Пользователь {email} не найден")
                self.errors.append(f"User {email} not found")

        if len(users) < 6:
            self.print_error("  Не хватает тестовых пользователей!")
            return {}

        return users

    def link_parents_to_students(self, users: Dict[str, User]):
        """
        Привязывает родителя к студентам через StudentProfile.parent.

        Это делает TUTOR через свой функционал создания учеников.
        """
        self.print_section("Привязка родителя к студентам (Tutor связывает Parent → Students)")

        parent = users.get('parent@test.com')
        tutor = users.get('tutor@test.com')

        if not parent or not tutor:
            self.print_error("  Родитель или тьютор не найдены")
            return

        # Привязываем обоих студентов к родителю
        students = [
            users.get('student@test.com'),
            users.get('student2@test.com'),
        ]

        for student in students:
            if not student:
                continue

            try:
                if hasattr(student, 'student_profile') and student.student_profile:
                    # Привязываем родителя
                    student.student_profile.parent = parent
                    # Устанавливаем тьютора
                    student.student_profile.tutor = tutor
                    student.student_profile.save()

                    self.stats['parent_links'] += 1
                    self.print_success(
                        f"  Родитель {parent.get_full_name()} привязан к "
                        f"{student.get_full_name()} (через тьютора {tutor.get_full_name()})"
                    )
                else:
                    self.print_error(f"  У студента {student.email} нет профиля")

            except Exception as e:
                self.print_error(f"  Ошибка привязки родителя: {e}")
                self.errors.append(f"Parent link error: {e}")

        self.print_info(f"  Создано связей родитель-студент: {self.stats['parent_links']}")

    def get_subjects(self) -> List[Subject]:
        """Получает все доступные предметы."""
        self.print_section("Загрузка предметов")

        subjects = list(Subject.objects.all())
        for subject in subjects:
            self.print_info(f"  {subject.name}")

        return subjects

    def clear_test_data(self):
        """Удаляет все тестовые данные (кроме пользователей и их профилей)."""
        self.print_section("Очистка тестовых данных")

        models_to_clear = [
            (Notification, 'Уведомления'),
            (Message, 'Сообщения'),
            (ChatRoom, 'Чат-комнаты'),
            (TutorWeeklyReport, 'Отчеты тьютора'),
            (TeacherWeeklyReport, 'Отчеты преподавателя'),
            (StudentReport, 'Отчеты студентов'),
            (AssignmentSubmission, 'Работы по заданиям'),
            (Assignment, 'Задания'),
            (StudyPlanFile, 'Файлы учебных планов'),
            (StudyPlan, 'Учебные планы'),
            (MaterialSubmission, 'Работы студентов'),
            (Material, 'Материалы'),
            (SubjectEnrollment, 'Записи на предметы'),
        ]

        for model, name in models_to_clear:
            count = model.objects.all().count()
            model.objects.all().delete()
            self.print_info(f"  Удалено {name}: {count}")

    def create_subject_enrollments(
        self,
        users: Dict[str, User],
        subjects: List[Subject]
    ) -> List[SubjectEnrollment]:
        """
        Создает записи студентов на предметы.

        ВАЖНО: Это делает TUTOR через свой функционал назначения предметов.
        Tutor назначает студентам предметы с конкретными преподавателями.
        """
        self.print_section("Создание записей на предметы (Tutor назначает)")

        enrollments = []

        # Студент 1: 3 предмета от тьютора
        student1 = users.get('student@test.com')
        teacher1 = users.get('teacher@test.com')
        tutor = users.get('tutor@test.com')

        if student1 and teacher1 and tutor:
            for subject in subjects[:3]:  # Первые 3 предмета
                try:
                    # Проверяем/создаем TeacherSubject (преподаватель может вести предмет)
                    teacher_subject, _ = TeacherSubject.objects.get_or_create(
                        teacher=teacher1,
                        subject=subject
                    )

                    # Tutor назначает студента на предмет к преподавателю
                    enrollment, created = SubjectEnrollment.objects.get_or_create(
                        student=student1,
                        subject=subject,
                        teacher=teacher1,
                        defaults={
                            'assigned_by': tutor,  # Кто назначил
                            'is_active': True,
                            'enrolled_at': timezone.now() - timedelta(days=30),
                        }
                    )

                    if created:
                        enrollments.append(enrollment)
                        self.stats['enrollments'] += 1
                        self.print_success(
                            f"  Tutor назначил: {student1.get_full_name()} → "
                            f"{subject.name} (преподаватель: {teacher1.get_full_name()})"
                        )
                except Exception as e:
                    self.print_error(f"  Ошибка создания записи: {e}")
                    self.errors.append(f"Enrollment error: {e}")

        # Студент 2: 2 предмета от тьютора
        student2 = users.get('student2@test.com')
        teacher2 = users.get('teacher2@test.com')

        if student2 and teacher2 and tutor:
            for subject in subjects[3:5]:  # Предметы 4-5
                try:
                    teacher_subject, _ = TeacherSubject.objects.get_or_create(
                        teacher=teacher2,
                        subject=subject
                    )

                    # Tutor назначает студента на предмет к преподавателю
                    enrollment, created = SubjectEnrollment.objects.get_or_create(
                        student=student2,
                        subject=subject,
                        teacher=teacher2,
                        defaults={
                            'assigned_by': tutor,  # Кто назначил
                            'is_active': True,
                            'enrolled_at': timezone.now() - timedelta(days=45),
                        }
                    )

                    if created:
                        enrollments.append(enrollment)
                        self.stats['enrollments'] += 1
                        self.print_success(
                            f"  Tutor назначил: {student2.get_full_name()} → "
                            f"{subject.name} (преподаватель: {teacher2.get_full_name()})"
                        )
                except Exception as e:
                    self.print_error(f"  Ошибка создания записи: {e}")
                    self.errors.append(f"Enrollment error: {e}")

        self.print_info(f"  Создано назначений на предметы: {self.stats['enrollments']}")
        return enrollments

    def create_materials(
        self,
        enrollments: List[SubjectEnrollment],
        users: Dict[str, User]
    ):
        """
        Создает учебные материалы с файлами.

        Преподаватели создают материалы для своих предметов.
        """
        self.print_section("Создание учебных материалов (Преподаватели создают)")

        material_titles = [
            "Введение в курс",
            "Основные понятия",
            "Практические примеры",
            "Теоретический материал",
            "Дополнительные материалы",
            "Контрольные вопросы",
            "Задачи для самостоятельной работы",
        ]

        for enrollment in enrollments:
            subject = enrollment.subject
            teacher = enrollment.teacher

            # 5-7 материалов на предмет
            for i in range(random.randint(5, 7)):
                try:
                    title = f"{material_titles[i % len(material_titles)]} - {subject.name}"

                    material = Material.objects.create(
                        subject=subject,
                        author=teacher,
                        title=title,
                        description=f"Учебный материал по теме: {title}",
                        content=f"Подробное содержание материала по теме '{title}'.\n\n"
                                f"Этот материал создан преподавателем {teacher.get_full_name()} "
                                f"для студентов курса {subject.name}.",
                        type=random.choice(['lesson', 'presentation', 'document']),
                        status=random.choice(['active', 'active', 'draft']),
                        created_at=timezone.now() - timedelta(days=random.randint(1, 60)),
                    )

                    self.stats['materials'] += 1

                    if self.verbose:
                        self.print_success(f"  {teacher.get_full_name()} создал: {title}")

                except Exception as e:
                    self.print_error(f"  Ошибка создания материала: {e}")
                    self.errors.append(f"Material error: {e}")

        self.print_info(f"  Создано материалов: {self.stats['materials']}")

    def create_material_submissions(
        self,
        enrollments: List[SubjectEnrollment],
        users: Dict[str, User]
    ):
        """
        Создает работы студентов по материалам.

        Студенты выполняют работы по материалам преподавателей.
        """
        self.print_section("Создание работ студентов (Студенты выполняют)")

        statuses = ['submitted', 'reviewed', 'reviewed', 'returned']

        for enrollment in enrollments:
            student = enrollment.student
            materials = Material.objects.filter(
                subject=enrollment.subject,
                status='active'
            )[:5]  # Первые 5 материалов

            for material in materials:
                try:
                    status = random.choice(statuses)

                    submission = MaterialSubmission.objects.create(
                        student=student,
                        material=material,
                        status=status,
                        submitted_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                        submission_text=f"Выполненная работа студента {student.get_full_name()} "
                                      f"по материалу '{material.title}'",
                    )

                    # Добавляем файл работы
                    work_file = self.create_test_pdf(
                        f"Работа: {material.title[:40]}"
                    )
                    submission.submission_file = work_file
                    submission.save()

                    self.stats['material_submissions'] += 1

                    if self.verbose:
                        self.print_success(
                            f"  {student.get_full_name()} отправил работу: {material.title[:40]}..."
                        )

                except Exception as e:
                    self.print_error(f"  Ошибка создания работы: {e}")
                    self.errors.append(f"Submission error: {e}")

        self.print_info(f"  Создано работ студентов: {self.stats['material_submissions']}")

    def create_study_plans(
        self,
        enrollments: List[SubjectEnrollment],
        users: Dict[str, User]
    ):
        """
        Создает учебные планы с файлами.

        Преподаватели создают персональные планы для каждого студента.
        """
        self.print_section("Создание учебных планов (Преподаватели создают)")

        weeks = [
            timezone.now() - timedelta(weeks=1),  # Прошлая неделя
            timezone.now(),  # Текущая неделя
            timezone.now() + timedelta(weeks=1),  # Следующая неделя
        ]

        for enrollment in enrollments:
            student = enrollment.student
            teacher = enrollment.teacher
            subject = enrollment.subject

            for week_start in weeks:
                try:
                    week_end = week_start + timedelta(days=6)

                    plan = StudyPlan.objects.create(
                        student=student,
                        teacher=teacher,
                        subject=subject,
                        enrollment=enrollment,
                        title=f"План {subject.name} - неделя {week_start.strftime('%d.%m.%Y')}",
                        content=f"Учебный план для {student.get_full_name()} по предмету {subject.name}\n\n"
                                f"Неделя: {week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}\n\n"
                                f"Темы недели:\n"
                                f"1. Теоретический материал\n"
                                f"2. Практические задания\n"
                                f"3. Домашняя работа",
                        week_start_date=week_start.date(),
                        week_end_date=week_end.date(),
                        status='sent',
                        created_at=week_start - timedelta(days=2),
                        sent_at=week_start - timedelta(days=1),
                    )

                    self.stats['study_plans'] += 1

                    # Создаем 1-2 файла плана
                    for i in range(random.randint(1, 2)):
                        pdf_file = self.create_test_pdf(
                            f"План: {subject.name} ({week_start.strftime('%d.%m')})"
                        )

                        plan_file = StudyPlanFile.objects.create(
                            study_plan=plan,
                            file=pdf_file,
                            name=f"План недели {week_start.strftime('%d.%m')}.pdf",
                            file_size=len(pdf_file.read()),
                            uploaded_by=teacher,
                            created_at=plan.created_at,
                        )

                        self.stats['study_plan_files'] += 1

                    if self.verbose:
                        self.print_success(
                            f"  {teacher.get_full_name()} создал план для "
                            f"{student.get_full_name()} - {subject.name} ({week_start.strftime('%d.%m')})"
                        )

                except Exception as e:
                    self.print_error(f"  Ошибка создания плана: {e}")
                    self.errors.append(f"Study plan error: {e}")

        self.print_info(
            f"  Создано планов: {self.stats['study_plans']}, "
            f"файлов: {self.stats['study_plan_files']}"
        )

    def create_assignments(
        self,
        enrollments: List[SubjectEnrollment],
        users: Dict[str, User]
    ):
        """
        Создает домашние задания и работы студентов.

        Преподаватели создают задания, студенты их выполняют.
        """
        self.print_section("Создание домашних заданий (Преподаватели создают)")

        assignment_titles = [
            "Контрольная работа №1",
            "Практическое задание",
            "Тестирование",
        ]

        for enrollment in enrollments:
            subject = enrollment.subject
            teacher = enrollment.teacher
            student = enrollment.student

            for i, title in enumerate(assignment_titles):
                try:
                    # Дедлайн: прошлый, текущий, будущий
                    deadline_days = [-5, 3, 10][i]
                    deadline = timezone.now() + timedelta(days=deadline_days)

                    assignment = Assignment.objects.create(
                        author=teacher,  # ✅ Правильное поле
                        title=f"{title} - {subject.name}",
                        description=f"Описание задания '{title}' по предмету {subject.name}",
                        instructions="Выполните задание и загрузите результаты",
                        type=Assignment.Type.HOMEWORK,
                        status=Assignment.Status.PUBLISHED,
                        start_date=deadline - timedelta(days=7),
                        due_date=deadline,  # ✅ Правильное поле
                        max_score=100,  # PositiveIntegerField
                    )

                    # Назначаем студенту через M2M
                    assignment.assigned_to.add(student)

                    self.stats['assignments'] += 1

                    # Создаем работу студента (если дедлайн не в будущем)
                    if deadline_days <= 3:
                        submitted_at = deadline - timedelta(days=random.randint(1, 3))

                        submission = AssignmentSubmission.objects.create(
                            assignment=assignment,
                            student=student,
                            content=f"Ответ студента {student.get_full_name()} на задание: {title}",  # ✅ Правильное поле
                        )

                        # Если дедлайн прошел - оцениваем
                        if deadline_days < 0:
                            submission.score = Decimal(str(random.randint(7, 10)))
                            submission.teacher_comment = "Хорошо выполнено!"
                            submission.graded_at = deadline + timedelta(days=1)
                            submission.save()

                        # Добавляем файл работы
                        work_file = self.create_test_pdf(
                            f"Работа: {assignment.title[:40]}"
                        )
                        submission.file = work_file
                        submission.save()

                        self.stats['assignment_submissions'] += 1

                    if self.verbose:
                        self.print_success(
                            f"  {teacher.get_full_name()} создал задание: {assignment.title}"
                        )

                except Exception as e:
                    self.print_error(f"  Ошибка создания задания: {e}")
                    self.errors.append(f"Assignment error: {e}")

        self.print_info(
            f"  Создано заданий: {self.stats['assignments']}, "
            f"работ: {self.stats['assignment_submissions']}"
        )

    def create_reports(
        self,
        users: Dict[str, User],
        enrollments: List[SubjectEnrollment]
    ):
        """
        Создает отчеты по цепочке: Преподаватель → Тьютор → Родитель.

        1. Преподаватели отправляют отчеты тьюторам о студентах (StudentReport + TeacherWeeklyReport)
        2. Тьютор собирает информацию и отправляет еженедельные отчеты родителям (TutorWeeklyReport)
        """
        self.print_section("Создание отчетов (Преподаватель → Тьютор → Родитель)")

        tutor = users.get('tutor@test.com')
        parent = users.get('parent@test.com')

        # 1. Отчеты преподавателей тьютору о студентах (StudentReport)
        self.print_info("  Создаются отчеты: Преподаватель → Тьютор")
        for enrollment in enrollments[:3]:  # Первые 3 записи
            try:
                teacher = enrollment.teacher
                student = enrollment.student
                subject = enrollment.subject

                if tutor:
                    # StudentReport: от преподавателя к тьютору о студенте
                    # Используем get_or_create чтобы избежать дубликатов
                    period_start = timezone.now() - timedelta(days=7)
                    period_end = timezone.now()

                    report, created = StudentReport.objects.get_or_create(
                        teacher=teacher,
                        student=student,
                        period_start=period_start,
                        period_end=period_end,
                        defaults={
                            'parent': parent,  # Родитель тоже может видеть
                            'title': f"Отчет о {student.get_full_name()} по {subject.name}",
                            'description': f"Еженедельный отчет преподавателя",
                            'content': {
                                'subject': subject.name,
                                'teacher': teacher.get_full_name(),
                                'student': student.get_full_name(),
                                'progress': 'Хороший прогресс в освоении материала',
                            },
                            'status': random.choice(['sent', 'sent', 'read']),
                            'overall_grade': '4',
                            'progress_percentage': random.randint(60, 90),
                            'attendance_percentage': random.randint(80, 100),
                            'behavior_rating': random.randint(7, 10),
                            'recommendations': "Продолжать в том же духе. Рекомендуется больше практики.",
                            'sent_at': timezone.now() - timedelta(days=1),
                        }
                    )

                    if created:
                        self.stats['student_reports'] += 1

                    if self.verbose and created:
                        self.print_success(
                            f"    {teacher.get_full_name()} → Тьютор: отчет о {student.get_full_name()}"
                        )

                    # TeacherWeeklyReport: еженедельный отчет преподавателя по предмету
                    teacher_report = TeacherWeeklyReport.objects.create(
                        teacher=teacher,
                        student=student,
                        tutor=tutor,
                        subject=subject,
                        week_start=(timezone.now() - timedelta(days=7)).date(),
                        week_end=timezone.now().date(),
                        title=f"Еженедельный отчет: {subject.name}",
                        summary=f"Отчет преподавателя {teacher.get_full_name()} о студенте "
                                f"{student.get_full_name()} по предмету {subject.name}",
                        academic_progress="Студент показывает стабильный прогресс",
                        performance_notes="Выполнены все домашние задания",
                        achievements="Отличное выполнение контрольной работы",
                        recommendations="Продолжать работу в текущем темпе",
                        assignments_completed=random.randint(3, 5),
                        assignments_total=5,
                        average_score=Decimal(str(random.randint(70, 95) / 10)),
                        attendance_percentage=random.randint(80, 100),
                        status=random.choice(['sent', 'sent', 'read']),
                        sent_at=timezone.now() - timedelta(hours=12),
                    )

                    self.stats['teacher_reports'] += 1

            except Exception as e:
                self.print_error(f"  Ошибка создания отчета преподавателя: {e}")
                self.errors.append(f"Teacher report error: {e}")

        # 2. Еженедельные отчеты тьютора родителю (TutorWeeklyReport)
        self.print_info("  Создаются отчеты: Тьютор → Родитель")
        if tutor and parent:
            # Тьютор собирает информацию от преподавателей и отправляет родителю
            for enrollment in enrollments[:2]:  # Для первых 2 студентов
                try:
                    student = enrollment.student
                    week_start = (timezone.now() - timedelta(days=7)).date()

                    # Используем get_or_create чтобы избежать дубликатов
                    report, created = TutorWeeklyReport.objects.get_or_create(
                        tutor=tutor,
                        student=student,
                        week_start=week_start,
                        defaults={
                            'parent': parent,
                            'week_end': timezone.now().date(),
                            'title': f"Еженедельный отчет о {student.get_full_name()}",
                            'summary': f"Тьютор {tutor.get_full_name()} собрал информацию от всех преподавателей "
                                      f"студента {student.get_full_name()} за прошедшую неделю.",
                            'academic_progress': "Студент показывает хороший прогресс по всем предметам",
                            'behavior_notes': "Активно участвует в занятиях, выполняет все задания вовремя",
                            'achievements': "Отличные результаты по математике и физике",
                            'concerns': "Небольшие трудности с русским языком, уделить больше внимания",
                            'recommendations': "Продолжать регулярные занятия, добавить дополнительную практику по русскому",
                            'attendance_days': random.randint(5, 7),
                            'total_days': 7,
                            'progress_percentage': random.randint(65, 85),
                            'status': random.choice(['sent', 'sent', 'read']),
                            'sent_at': timezone.now() - timedelta(hours=6),
                        }
                    )

                    if created:
                        self.stats['tutor_reports'] += 1

                    if self.verbose and created:
                        self.print_success(
                            f"    Тьютор → {parent.get_full_name()}: отчет о {student.get_full_name()}"
                        )

                except Exception as e:
                    self.print_error(f"  Ошибка создания отчета тьютора: {e}")
                    self.errors.append(f"Tutor report error: {e}")

        self.print_info(
            f"  Создано отчетов: преподавателей={self.stats['student_reports'] + self.stats['teacher_reports']}, "
            f"тьютора={self.stats['tutor_reports']}"
        )

    def create_chat_rooms_and_messages(self, users: Dict[str, User]):
        """
        Создает чат-комнаты и сообщения между всеми участниками.

        Включая чаты: Тьютор ↔ Родитель
        """
        self.print_section("Создание чатов и сообщений")

        # Пары пользователей для чатов (включая тьютор-родитель)
        chat_pairs = [
            ('student@test.com', 'teacher@test.com'),
            ('student@test.com', 'tutor@test.com'),
            ('teacher@test.com', 'tutor@test.com'),
            ('tutor@test.com', 'parent@test.com'),  # ВАЖНО: чат тьютора с родителем
            ('student2@test.com', 'teacher2@test.com'),
            ('student2@test.com', 'tutor@test.com'),
        ]

        message_templates = [
            "Здравствуйте!",
            "Как дела с учебой?",
            "Спасибо за материалы!",
            "Когда будет следующий урок?",
            "Я отправил домашнее задание",
            "Посмотрите, пожалуйста, мою работу",
            "Есть вопрос по теме...",
            "Всё понятно, спасибо!",
            "Отличная работа!",
            "Нужна дополнительная консультация",
        ]

        # Специальные шаблоны для чата тьютор-родитель
        tutor_parent_messages = [
            "Здравствуйте! Как успехи у ребенка?",
            "На этой неделе был хороший прогресс",
            "Отправил вам еженедельный отчет",
            "Есть небольшие замечания по математике",
            "Рекомендую уделить больше времени практике",
            "Ребенок молодец, показывает отличные результаты!",
            "Не забудьте проверить отчеты от преподавателей",
        ]

        for email1, email2 in chat_pairs:
            user1 = users.get(email1)
            user2 = users.get(email2)

            if not user1 or not user2:
                continue

            try:
                # Создаем комнату
                room = ChatRoom.objects.create(created_by=user1, name=f"Chat: {user1.get_full_name()} - {user2.get_full_name()}", type="direct")
                room.participants.add(user1, user2)

                self.stats['chat_rooms'] += 1

                # Определяем шаблоны сообщений
                is_tutor_parent_chat = (
                    (user1.role == 'tutor' and user2.role == 'parent') or
                    (user1.role == 'parent' and user2.role == 'tutor')
                )

                templates = tutor_parent_messages if is_tutor_parent_chat else message_templates

                # Создаем 10-15 сообщений
                num_messages = random.randint(10, 15)
                for i in range(num_messages):
                    sender = random.choice([user1, user2])

                    message = Message.objects.create(
                        room=room,
                        sender=sender,
                        content=random.choice(templates),
                        created_at=timezone.now() - timedelta(
                            hours=random.randint(1, 72)
                        ),
                    )

                    # Иногда добавляем файл
                    if random.random() < 0.2:  # 20% сообщений с файлом
                        file = self.create_test_pdf(
                            f"Файл в чате: {user1.get_full_name()} - {user2.get_full_name()}"
                        )
                        message.file = file
                        message.save()

                    self.stats['messages'] += 1

                if self.verbose:
                    self.print_success(
                        f"  Чат: {user1.get_full_name()} ↔ {user2.get_full_name()} "
                        f"({num_messages} сообщений)"
                    )

            except Exception as e:
                self.print_error(f"  Ошибка создания чата: {e}")
                self.errors.append(f"Chat error: {e}")

        self.print_info(
            f"  Создано чатов: {self.stats['chat_rooms']}, "
            f"сообщений: {self.stats['messages']}"
        )

    def create_notifications(self, users: Dict[str, User]):
        """
        Создает уведомления для всех ролей.

        ВАЖНО: Специальные уведомления для родителей о платежах и отчетах.
        """
        self.print_section("Создание уведомлений (включая специальные для родителей)")

        # Общие типы уведомлений
        general_notifications = [
            ('info', 'Новый материал доступен'),
            ('success', 'Работа проверена'),
            ('warning', 'Приближается дедлайн'),
            ('error', 'Пропущен дедлайн'),
            ('info', 'Новое сообщение в чате'),
            ('info', 'Новый отчет доступен'),
        ]

        # Специальные уведомления для родителей
        parent_notifications = [
            ('info', 'Новый отчет от тьютора'),
            ('info', 'Отчет преподавателя о вашем ребенке'),
            ('warning', 'Предстоящий платеж за обучение'),
            ('success', 'Платеж успешно проведен'),
            ('info', 'Прогресс ребенка за неделю'),
            ('success', 'Ребенок выполнил все задания'),
            ('warning', 'Ребенок пропустил дедлайн'),
            ('info', 'Новое сообщение от тьютора'),
        ]

        for email, user in users.items():
            # Определяем тип уведомлений в зависимости от роли
            if user.role == 'parent':
                notification_types = parent_notifications
                num_notifications = random.randint(8, 12)  # Родителям больше уведомлений
            else:
                notification_types = general_notifications
                num_notifications = random.randint(5, 10)

            for _ in range(num_notifications):
                try:
                    notif_type, title = random.choice(notification_types)

                    # Персонализированное сообщение для родителей
                    if user.role == 'parent':
                        message = f"{title}. Проверьте раздел 'Мои дети' для получения подробной информации."
                    else:
                        message = f"Детали уведомления для {user.get_full_name()}"

                    notification = Notification.objects.create(
                        recipient=user,
                        title=title,
                        message=message,
                        type=notif_type,
                        priority=Notification.Priority.NORMAL,
                    )

                    self.stats['notifications'] += 1

                except Exception as e:
                    self.print_error(f"  Ошибка создания уведомления: {e}")
                    self.errors.append(f"Notification error: {e}")

        self.print_info(f"  Создано уведомлений: {self.stats['notifications']}")

    def create_test_pdf(self, title: str) -> SimpleUploadedFile:
        """
        Создает тестовый PDF файл с использованием reportlab.

        Args:
            title: Заголовок документа

        Returns:
            SimpleUploadedFile: Файл готовый для загрузки
        """
        buffer = io.BytesIO()

        # Создаем PDF
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Заголовок
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, title)

        # Дата
        p.setFont("Helvetica", 10)
        p.drawString(50, height - 70, f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

        # Контент
        p.setFont("Helvetica", 12)
        y = height - 120
        lines = [
            "Это тестовый документ для демонстрации системы.",
            "",
            "Содержание документа:",
            "- Раздел 1: Введение",
            "- Раздел 2: Основная часть",
            "- Раздел 3: Заключение",
            "",
            "Тестовый текст для заполнения страницы.",
            "Дополнительная информация...",
        ]

        for line in lines:
            p.drawString(50, y, line)
            y -= 20

        p.showPage()
        p.save()

        # Получаем PDF из буфера
        pdf_data = buffer.getvalue()
        buffer.close()

        # Создаем имя файла
        filename = f"{title[:30].replace(' ', '_').replace(':', '')}.pdf"

        return SimpleUploadedFile(
            filename,
            pdf_data,
            content_type='application/pdf'
        )

    def print_summary(self):
        """Выводит финальную статистику."""
        self.print_section("Итоговая статистика")

        # Таблица статистики
        stats_table = [
            ("Профилей создано", self.stats['profiles_created']),
            ("Связей родитель-студент", self.stats['parent_links']),
            ("Записей на предметы", self.stats['enrollments']),
            ("Материалов", self.stats['materials']),
            ("Работ студентов", self.stats['material_submissions']),
            ("Учебных планов", self.stats['study_plans']),
            ("Файлов планов", self.stats['study_plan_files']),
            ("Заданий", self.stats['assignments']),
            ("Работ по заданиям", self.stats['assignment_submissions']),
            ("Отчетов студентов", self.stats['student_reports']),
            ("Отчетов тьютора", self.stats['tutor_reports']),
            ("Отчетов преподавателя", self.stats['teacher_reports']),
            ("Чат-комнат", self.stats['chat_rooms']),
            ("Сообщений", self.stats['messages']),
            ("Уведомлений", self.stats['notifications']),
        ]

        total = sum(count for _, count in stats_table)

        # Выводим таблицу
        max_label_len = max(len(label) for label, _ in stats_table)

        for label, count in stats_table:
            self.stdout.write(
                f"  {label.ljust(max_label_len)} : "
                f"{Colors.GREEN}{count:>5}{Colors.END}"
            )

        self.stdout.write(
            f"\n  {'─' * (max_label_len + 10)}\n"
            f"  {'ВСЕГО'.ljust(max_label_len)} : "
            f"{Colors.BOLD}{Colors.GREEN}{total:>5}{Colors.END}\n"
        )

        # Ошибки
        if self.errors:
            self.print_section("Ошибки")
            for error in self.errors[:10]:  # Показываем первые 10
                self.print_error(f"  {error}")

            if len(self.errors) > 10:
                self.print_warning(f"  ... и еще {len(self.errors) - 10} ошибок")

        # Финальное сообщение
        self.print_success(
            f"\nСоздание тестового датасета завершено! "
            f"Создано объектов: {total}"
        )
        self.print_info(
            "\nДатасет создан ЕСТЕСТВЕННЫМ образом:\n"
            "  1. Tutor привязал Parent к Students\n"
            "  2. Tutor назначил Students на предметы с Teachers\n"
            "  3. Teachers создали материалы и планы\n"
            "  4. Students выполнили работы\n"
            "  5. Teachers отправили отчеты Tutor\n"
            "  6. Tutor отправил отчеты Parent\n"
            "  7. Созданы чаты между всеми участниками\n"
            "  8. Созданы уведомления (специальные для родителей)"
        )

    # Утилиты для цветного вывода
    def print_header(self, text: str):
        """Выводит заголовок."""
        self.stdout.write(
            f"\n{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.END}"
        )
        self.stdout.write(
            f"{Colors.BOLD}{Colors.HEADER}{text.center(70)}{Colors.END}"
        )
        self.stdout.write(
            f"{Colors.BOLD}{Colors.HEADER}{'=' * 70}{Colors.END}\n"
        )

    def print_section(self, text: str):
        """Выводит секцию."""
        self.stdout.write(
            f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}\n"
        )

    def print_success(self, text: str):
        """Выводит успешное сообщение."""
        self.stdout.write(f"{Colors.GREEN}{text}{Colors.END}")

    def print_info(self, text: str):
        """Выводит информационное сообщение."""
        self.stdout.write(f"{Colors.BLUE}{text}{Colors.END}")

    def print_warning(self, text: str):
        """Выводит предупреждение."""
        self.stdout.write(f"{Colors.YELLOW}{text}{Colors.END}")

    def print_error(self, text: str):
        """Выводит ошибку."""
        self.stdout.write(f"{Colors.RED}{text}{Colors.END}")
