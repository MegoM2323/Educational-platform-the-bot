"""
Management команда для создания тестовых материалов и предметов
"""
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from materials.models import Subject, Material, SubjectEnrollment, TeacherSubject
from django.utils import timezone

User = get_user_model()


class Command(BaseCommand):
    help = "Создает тестовые предметы, материалы и зачисления студентов"

    @transaction.atomic()
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Начинаем создание тестовых материалов..."))

        # Проверяем наличие тестовых пользователей
        student_user = User.objects.filter(email="student@test.com").first()
        if not student_user:
            raise CommandError(
                "Не найден пользователь student@test.com. "
                "Создайте его перед запуском команды."
            )
        self.stdout.write(self.style.SUCCESS(f"✓ Найден студент: {student_user.email}"))

        teacher_user = User.objects.filter(email="teacher@test.com").first()
        if not teacher_user:
            raise CommandError(
                "Не найден пользователь teacher@test.com. "
                "Создайте его перед запуском команды."
            )
        self.stdout.write(self.style.SUCCESS(f"✓ Найден преподаватель: {teacher_user.email}"))

        # Данные для предметов
        subjects_data = [
            {
                "name": "Математика",
                "description": "Основной курс математики",
                "color": "#FF6B6B",
            },
            {
                "name": "Физика",
                "description": "Курс физики для школьников",
                "color": "#4ECDC4",
            },
            {
                "name": "Информатика",
                "description": "Программирование и IT",
                "color": "#45B7D1",
            },
            {
                "name": "Русский язык",
                "description": "Русский язык и литература",
                "color": "#FFA07A",
            },
            {
                "name": "Английский язык",
                "description": "Английский язык для начинающих",
                "color": "#98D8C8",
            },
        ]

        # Создаем предметы
        subjects = {}
        created_subjects_count = 0
        for subject_data in subjects_data:
            subject, created = Subject.objects.get_or_create(
                name=subject_data["name"],
                defaults={
                    "description": subject_data["description"],
                    "color": subject_data["color"],
                },
            )
            subjects[subject_data["name"]] = subject
            if created:
                created_subjects_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f"✓ Создан предмет: {subject.name}")
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f"~ Предмет уже существует: {subject.name}")
                )

        self.stdout.write(
            self.style.SUCCESS(f"\nВсего создано предметов: {created_subjects_count}")
        )

        # Данные для материалов (по 2 на каждый предмет)
        materials_data = [
            {
                "subject": "Математика",
                "materials": [
                    {
                        "title": "Введение в алгебру",
                        "description": "Основные понятия алгебры",
                        "content": "Содержание материала по введению в алгебру",
                        "type": Material.Type.LESSON,
                    },
                    {
                        "title": "Решение уравнений",
                        "description": "Методы решения линейных уравнений",
                        "content": "Содержание материала по решению уравнений",
                        "type": Material.Type.LESSON,
                    },
                ],
            },
            {
                "subject": "Физика",
                "materials": [
                    {
                        "title": "Механика - основы",
                        "description": "Введение в механику",
                        "content": "Содержание материала по механике",
                        "type": Material.Type.PRESENTATION,
                    },
                    {
                        "title": "Законы Ньютона",
                        "description": "Три закона движения Ньютона",
                        "content": "Подробное описание законов Ньютона",
                        "type": Material.Type.DOCUMENT,
                    },
                ],
            },
            {
                "subject": "Информатика",
                "materials": [
                    {
                        "title": "Основы Python",
                        "description": "Введение в язык программирования Python",
                        "content": "Содержание курса по основам Python",
                        "type": Material.Type.LESSON,
                    },
                    {
                        "title": "Структуры данных",
                        "description": "Списки, кортежи, словари в Python",
                        "content": "Подробное описание структур данных",
                        "type": Material.Type.VIDEO,
                    },
                ],
            },
            {
                "subject": "Русский язык",
                "materials": [
                    {
                        "title": "Синтаксис простого предложения",
                        "description": "Члены предложения и их функции",
                        "content": "Содержание материала по синтаксису",
                        "type": Material.Type.LESSON,
                    },
                    {
                        "title": "Пунктуация в простом предложении",
                        "description": "Правила постановки знаков препинания",
                        "content": "Подробное описание пунктуации",
                        "type": Material.Type.DOCUMENT,
                    },
                ],
            },
            {
                "subject": "Английский язык",
                "materials": [
                    {
                        "title": "Present Simple Tense",
                        "description": "Настоящее простое время в английском",
                        "content": "Правила использования Present Simple",
                        "type": Material.Type.PRESENTATION,
                    },
                    {
                        "title": "Словарь базовых фраз",
                        "description": "Самые полезные фразы для общения",
                        "content": "Список и примеры базовых фраз",
                        "type": Material.Type.DOCUMENT,
                    },
                ],
            },
        ]

        # Создаем материалы
        created_materials_count = 0
        for subject_materials in materials_data:
            subject_name = subject_materials["subject"]
            subject = subjects[subject_name]

            for material_data in subject_materials["materials"]:
                material, created = Material.objects.get_or_create(
                    title=material_data["title"],
                    subject=subject,
                    defaults={
                        "description": material_data["description"],
                        "content": material_data["content"],
                        "type": material_data["type"],
                        "author": teacher_user,
                        "status": Material.Status.ACTIVE,
                    },
                )

                if created:
                    created_materials_count += 1
                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✓ Создан материал: {material.title} ({subject_name})"
                        )
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"~ Материал уже существует: {material.title}"
                        )
                    )

        self.stdout.write(
            self.style.SUCCESS(f"\nВсего создано материалов: {created_materials_count}")
        )

        # Создаем зачисления студента на все предметы
        student_enrollments_count = 0
        for subject in subjects.values():
            enrollment, created = SubjectEnrollment.objects.get_or_create(
                student=student_user,
                subject=subject,
                defaults={
                    "teacher": teacher_user,
                    "enrolled_at": timezone.now(),
                    "is_active": True,
                },
            )
            if created:
                student_enrollments_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Студент зачислен на: {subject.name}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"~ Студент уже зачислен на: {subject.name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nВсего создано зачислений студента: {student_enrollments_count}"
            )
        )

        # Создаем зачисления преподавателя на Математику и Физику
        teacher_subjects = ["Математика", "Физика"]
        teacher_enrollments_count = 0
        for subject_name in teacher_subjects:
            subject = subjects[subject_name]
            enrollment, created = SubjectEnrollment.objects.get_or_create(
                student=teacher_user,
                subject=subject,
                defaults={
                    "teacher": teacher_user,
                    "enrolled_at": timezone.now(),
                    "is_active": True,
                },
            )
            if created:
                teacher_enrollments_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Преподаватель зачислен на: {subject.name}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"~ Преподаватель уже зачислен на: {subject.name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nВсего создано зачислений преподавателя: {teacher_enrollments_count}"
            )
        )

        # Создаем связи TeacherSubject
        teacher_subject_count = 0
        for subject_name in teacher_subjects:
            subject = subjects[subject_name]
            teacher_subject, created = TeacherSubject.objects.get_or_create(
                teacher=teacher_user,
                subject=subject,
                defaults={
                    "is_active": True,
                },
            )
            if created:
                teacher_subject_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ Создана связь преподаватель-предмет: {subject.name}"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"~ Связь уже существует: {subject.name}"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nВсего создано связей преподаватель-предмет: {teacher_subject_count}"
            )
        )

        # Итоговый отчет
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("ИТОГОВЫЙ ОТЧЕТ"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"Предметов создано:                    {created_subjects_count}")
        self.stdout.write(f"Материалов создано:                  {created_materials_count}")
        self.stdout.write(
            f"Зачислений студента на предметы:    {student_enrollments_count}"
        )
        self.stdout.write(
            f"Зачислений преподавателя:           {teacher_enrollments_count}"
        )
        self.stdout.write(
            f"Связей преподаватель-предмет:      {teacher_subject_count}"
        )
        self.stdout.write("=" * 60)
        self.stdout.write(
            self.style.SUCCESS("Тестовые материалы успешно созданы!")
        )
