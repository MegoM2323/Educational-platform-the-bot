"""
Расширенные методы для создания материалов, заданий и учебных планов.

Методы для использования с create_full_test_dataset.py:
- create_extended_materials: 7-10 материалов на предмет
- create_extended_assignments: 5-7 заданий на предмет
- create_extended_study_plans: 4 месячных плана с еженедельными вариантами
"""

import io
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List

from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from materials.models import SubjectEnrollment, Material, StudyPlan, StudyPlanFile
from assignments.models import Assignment


class ExtendedDataLoader:
    """Загрузчик расширенных данных для полного школьного окружения."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.stats = {
            "materials": 0,
            "assignments": 0,
            "study_plans": 0,
            "study_plan_files": 0,
        }
        self.errors: List[str] = []

    def create_test_pdf(self, title: str) -> SimpleUploadedFile:
        """Создает тестовый PDF файл с использованием reportlab."""
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, title)

        p.setFont("Helvetica", 10)
        p.drawString(
            50,
            height - 70,
            f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        )

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

        pdf_data = buffer.getvalue()
        buffer.close()

        filename = f"{title[:30].replace(' ', '_').replace(':', '')}.pdf"

        return SimpleUploadedFile(filename, pdf_data, content_type="application/pdf")

    def create_extended_materials(
        self,
        enrollments: List[SubjectEnrollment],
    ) -> int:
        """Создает 7-10 материалов на каждый SubjectEnrollment разных типов."""
        material_templates = {
            "lesson": [
                "Урок 1: Основные понятия",
                "Урок 2: Применение формул",
                "Урок 3: Практические примеры",
                "Урок 4: Углубленное изучение",
                "Урок 5: Экзаменационные вопросы",
            ],
            "presentation": [
                "Презентация: История развития",
                "Презентация: Ключевые концепции",
                "Презентация: Практическое применение",
                "Презентация: Выдающиеся деятели",
                "Презентация: Итоговый обзор",
            ],
            "document": [
                "Конспект: Теория основ",
                "Конспект: Подробный анализ",
                "Конспект: Справочный материал",
                "Конспект: Решение задач",
                "Конспект: Шпаргалка",
            ],
            "test": [
                "Тест: Проверка знаний",
                "Тест: Практические навыки",
                "Тест: Углубленное понимание",
                "Тест: Подготовка к ЕГЭ",
                "Тест: Самооценка",
            ],
        }

        created_count = 0

        for enrollment in enrollments:
            subject = enrollment.subject
            teacher = enrollment.teacher

            material_count = random.randint(7, 10)

            for i in range(material_count):
                try:
                    material_type = random.choice(list(material_templates.keys()))
                    templates = material_templates[material_type]
                    title = f"{templates[i % len(templates)]} - {subject.name}"

                    Material.objects.create(
                        subject=subject,
                        author=teacher,
                        title=title,
                        description=f"Учебный материал по теме: {title}",
                        content=f"Подробное содержание материала по теме '{title}'.\n\n"
                        f"Этот материал создан преподавателем {teacher.get_full_name()} "
                        f"для студентов курса {subject.name}.\n\n"
                        f"Материал содержит все необходимые теоретические сведения и "
                        f"практические примеры для глубокого понимания темы.",
                        type=material_type,
                        status=random.choice(["active", "active", "active", "draft"]),
                        created_at=timezone.now() - timedelta(days=random.randint(1, 120)),
                    )

                    self.stats["materials"] += 1
                    created_count += 1

                    if self.verbose:
                        print(f"  [{material_type}] {title}")

                except Exception as e:
                    error_msg = f"Material creation error for {subject.name}: {str(e)}"
                    self.errors.append(error_msg)

        return created_count

    def create_extended_assignments(
        self,
        enrollments: List[SubjectEnrollment],
    ) -> int:
        """Создает 5-7 заданий на каждый SubjectEnrollment разных типов."""
        assignment_types = [
            (Assignment.Type.HOMEWORK, "Домашнее задание"),
            (Assignment.Type.CLASSWORK, "Классная работа"),
            (Assignment.Type.EXAM, "Контрольная работа"),
            (Assignment.Type.PROJECT, "Проект"),
        ]

        created_count = 0

        for enrollment in enrollments:
            subject = enrollment.subject
            teacher = enrollment.teacher
            student = enrollment.student

            assignment_count = random.randint(5, 7)

            for i in range(assignment_count):
                try:
                    assignment_type, type_name = random.choice(assignment_types)

                    deadline_offset = random.choice([-30, -14, -7, -3, 0, 3, 7, 14, 30])
                    deadline = timezone.now() + timedelta(days=deadline_offset)

                    status = random.choice(
                        [
                            Assignment.Status.PUBLISHED,
                            Assignment.Status.PUBLISHED,
                            Assignment.Status.PUBLISHED,
                            Assignment.Status.DRAFT,
                        ]
                    )

                    assignment = Assignment.objects.create(
                        author=teacher,
                        title=f"{type_name} №{i + 1}: {subject.name}",
                        description=f"{type_name} по теме '{subject.name}'. "
                        f"Задание требует глубокого понимания материала.",
                        instructions="Выполните все задания и загрузите результаты. "
                        "Обязательно проверьте правильность расчетов.",
                        type=assignment_type,
                        status=status,
                        start_date=deadline - timedelta(days=random.randint(5, 15)),
                        due_date=deadline,
                        max_score=100,
                        created_at=timezone.now() - timedelta(days=random.randint(1, 60)),
                    )

                    assignment.assigned_to.add(student)

                    self.stats["assignments"] += 1
                    created_count += 1

                    if self.verbose:
                        status_str = (
                            "published" if status == Assignment.Status.PUBLISHED else "draft"
                        )
                        print(f"  [{type_name}] {assignment.title} ({status_str})")

                except Exception as e:
                    error_msg = f"Assignment creation error for {subject.name}: {str(e)}"
                    self.errors.append(error_msg)

        return created_count

    def create_extended_study_plans(
        self,
        enrollments: List[SubjectEnrollment],
    ) -> tuple:
        """Создает 4 месячных плана (еженедельно) на каждый SubjectEnrollment."""
        created_plans = 0
        created_files = 0

        today = timezone.now().date()

        for enrollment in enrollments:
            student = enrollment.student
            teacher = enrollment.teacher
            subject = enrollment.subject

            base_date = timezone.now() - timedelta(days=random.randint(5, 30))

            for month_offset in range(-2, 2):
                try:
                    month_start = base_date + timedelta(days=30 * month_offset)

                    for week_num in range(4):
                        try:
                            week_start = month_start + timedelta(weeks=week_num)
                            week_end = week_start + timedelta(days=6)

                            if week_end < today - timedelta(days=90):
                                status = "completed"
                            elif week_end < today:
                                status = random.choice(["sent", "confirmed", "completed"])
                            elif week_start <= today:
                                status = random.choice(["sent", "confirmed", "pending"])
                            else:
                                status = random.choice(["pending", "confirmed"])

                            plan_title = (
                                f"План {subject.name} - "
                                f"неделя {week_start.strftime('%d.%m.%Y')}"
                            )

                            plan = StudyPlan.objects.create(
                                student=student,
                                teacher=teacher,
                                subject=subject,
                                enrollment=enrollment,
                                title=plan_title,
                                content=f"Учебный план для {student.get_full_name()} "
                                f"по предмету {subject.name}\n\n"
                                f"Неделя: {week_start.strftime('%d.%m.%Y')} - "
                                f"{week_end.strftime('%d.%m.%Y')}\n\n"
                                f"Темы недели:\n"
                                f"1. Теоретический материал\n"
                                f"2. Практические задания\n"
                                f"3. Домашняя работа\n"
                                f"4. Самопроверка\n\n"
                                f"Рекомендуемое время: 5-7 часов на неделю",
                                week_start_date=week_start.date(),
                                week_end_date=week_end.date(),
                                status=status,
                                created_at=week_start - timedelta(days=2),
                                sent_at=(
                                    week_start - timedelta(days=1)
                                    if status in ["sent", "confirmed", "completed"]
                                    else None
                                ),
                            )

                            self.stats["study_plans"] += 1
                            created_plans += 1

                            for file_num in range(random.randint(1, 2)):
                                try:
                                    pdf_file = self.create_test_pdf(
                                        f"План: {subject.name} ({week_start.strftime('%d.%m')})"
                                    )

                                    StudyPlanFile.objects.create(
                                        study_plan=plan,
                                        file=pdf_file,
                                        name=f"План_{subject.name}_{week_start.strftime('%d_%m')}_v{file_num}.pdf",
                                        file_size=len(pdf_file.read()),
                                        uploaded_by=teacher,
                                        created_at=plan.created_at,
                                    )

                                    self.stats["study_plan_files"] += 1
                                    created_files += 1

                                except Exception as e:
                                    error_msg = f"Study plan file error: {str(e)}"
                                    self.errors.append(error_msg)

                            if self.verbose:
                                print(f"  [{status}] {plan_title}")

                        except Exception as e:
                            error_msg = f"Study plan week error: {str(e)}"
                            self.errors.append(error_msg)

                except Exception as e:
                    error_msg = f"Study plan month error: {str(e)}"
                    self.errors.append(error_msg)

        return created_plans, created_files
