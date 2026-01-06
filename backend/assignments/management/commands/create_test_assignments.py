"""
Management команда для создания тестовых заданий со вопросами и ответами
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.db import transaction
from datetime import timedelta
import logging

from assignments.models import (
    Assignment,
    AssignmentQuestion,
    AssignmentSubmission,
    AssignmentAnswer,
)
from materials.models import SubjectEnrollment

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Создает тестовые задания, вопросы и ответы для разработки"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Удалить все существующие тестовые задания перед созданием",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        clear = options["clear"]

        self.stdout.write(self.style.SUCCESS("Запуск создания тестовых заданий..."))

        try:
            # Получаем тестовых пользователей
            teacher = User.objects.filter(email="teacher@test.com").first()
            student = User.objects.filter(email="student@test.com").first()

            if not teacher:
                self.stdout.write(self.style.ERROR("Не найден пользователь teacher@test.com"))
                return

            if not student:
                self.stdout.write(self.style.ERROR("Не найден пользователь student@test.com"))
                return

            self.stdout.write(f"Учитель: {teacher}")
            self.stdout.write(f"Студент: {student}")

            if clear:
                self._clear_test_data(teacher, student)

            # Данные для создания заданий
            subjects_data = [
                {"name": "Математика", "difficulty": 1},
                {"name": "Физика", "difficulty": 2},
                {"name": "Информатика", "difficulty": 2},
                {"name": "Русский", "difficulty": 1},
                {"name": "Английский", "difficulty": 3},
            ]

            assignments = self._create_assignments(teacher, subjects_data)
            self._create_questions(assignments)
            self._create_submissions(student, assignments[:3])

            self.stdout.write(self.style.SUCCESS("\nЗавершено успешно!"))
            self._print_summary(assignments)

        except Exception as e:
            logger.exception("Ошибка при создании тестовых заданий")
            self.stdout.write(self.style.ERROR(f"Ошибка: {str(e)}"))
            raise

    def _clear_test_data(self, teacher, student):
        """Удаляет тестовые данные"""
        self.stdout.write(self.style.WARNING("\nУдаление существующих тестовых данных..."))

        count = Assignment.objects.filter(author=teacher).delete()[0]
        self.stdout.write(f"Удалено заданий: {count}")

    def _create_assignments(self, teacher, subjects_data):
        """Создает 5 заданий по разным предметам"""
        self.stdout.write("\nСоздание заданий...")

        now = timezone.now()
        assignments = []

        for i, subject_data in enumerate(subjects_data):
            subject_name = subject_data["name"]
            difficulty = subject_data["difficulty"]

            title = f"Тест по {subject_name}"
            description = f"Проверка знаний по предмету {subject_name}"
            instructions = (
                f"Ответьте на все вопросы.\nПредмет: {subject_name}\nСложность: {difficulty}/3"
            )

            assignment, created = Assignment.objects.get_or_create(
                title=title,
                author=teacher,
                defaults={
                    "description": description,
                    "instructions": instructions,
                    "type": Assignment.Type.TEST,
                    "status": Assignment.Status.PUBLISHED,
                    "max_score": 100,
                    "time_limit": 60,
                    "attempts_limit": 2,
                    "start_date": now,
                    "due_date": now + timedelta(days=7),
                    "difficulty_level": difficulty,
                    "allow_late_submission": True,
                    "show_correct_answers": True,
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(f"  + {assignment.title} (ID: {assignment.id})")
                )
            else:
                self.stdout.write(self.style.WARNING(f"  ~ {assignment.title} (уже существует)"))

            assignments.append(assignment)

        return assignments

    def _create_questions(self, assignments):
        """Создает 10 вопросов (по 2 на каждое задание)"""
        self.stdout.write("\nСоздание вопросов...")

        question_types = [
            AssignmentQuestion.Type.SINGLE_CHOICE,
            AssignmentQuestion.Type.MULTIPLE_CHOICE,
            AssignmentQuestion.Type.TEXT,
        ]

        total_created = 0

        for assignment in assignments:
            for q_num in range(2):
                question_type = question_types[q_num % len(question_types)]
                order = q_num + 1

                question_text = f'Вопрос {order} по "{assignment.title}"'
                points = (q_num % 3) + 1

                # Готовим опции для выбора
                options = None
                correct_answer = {}

                if question_type in [
                    AssignmentQuestion.Type.SINGLE_CHOICE,
                    AssignmentQuestion.Type.MULTIPLE_CHOICE,
                ]:
                    options = [
                        {"id": "a", "text": "Вариант A"},
                        {"id": "b", "text": "Вариант B"},
                        {"id": "c", "text": "Вариант C"},
                        {"id": "d", "text": "Вариант D"},
                    ]
                    if question_type == AssignmentQuestion.Type.SINGLE_CHOICE:
                        correct_answer = {"answer": "a"}
                    else:
                        correct_answer = {"answers": ["a", "c"]}

                elif question_type == AssignmentQuestion.Type.TEXT:
                    correct_answer = {"answer": "правильный ответ"}

                question, created = AssignmentQuestion.objects.get_or_create(
                    assignment=assignment,
                    order=order,
                    defaults={
                        "question_text": question_text,
                        "question_type": question_type,
                        "points": points,
                        "options": options or [],
                        "correct_answer": correct_answer,
                        "randomize_options": False,
                    },
                )

                if created:
                    self.stdout.write(f"  + {question_text} (тип: {question_type})")
                    total_created += 1
                else:
                    self.stdout.write(f"  ~ {question_text} (уже существует)")

        self.stdout.write(self.style.SUCCESS(f"Создано вопросов: {total_created}"))

    def _create_submissions(self, student, assignments):
        """Создает 3 отправки со статусами"""
        self.stdout.write("\nСоздание отправок...")

        statuses = [
            AssignmentSubmission.Status.SUBMITTED,
            AssignmentSubmission.Status.GRADED,
            AssignmentSubmission.Status.SUBMITTED,
        ]

        total_created = 0

        for i, assignment in enumerate(assignments):
            status = statuses[i % len(statuses)]

            submission, created = AssignmentSubmission.objects.get_or_create(
                assignment=assignment,
                student=student,
                defaults={
                    "content": f'Ответ студента на задание "{assignment.title}"',
                    "status": status,
                    "is_late": False,
                    "max_score": assignment.max_score,
                },
            )

            if created:
                # Добавляем оценку для GRADED статуса
                if status == AssignmentSubmission.Status.GRADED:
                    submission.score = 85
                    submission.feedback = "Хорошая работа! Несколько ошибок в расчетах."
                    submission.graded_at = timezone.now()
                    submission.save()

                self.stdout.write(f"  + {assignment.title} -> {student.email} (статус: {status})")
                total_created += 1

                # Создаем ответы на вопросы
                self._create_question_answers(submission, assignment)
            else:
                self.stdout.write(f"  ~ {assignment.title} -> {student.email} (уже существует)")

        self.stdout.write(self.style.SUCCESS(f"Создано отправок: {total_created}"))

    def _create_question_answers(self, submission, assignment):
        """Создает ответы на вопросы в отправке"""
        questions = assignment.questions.all()

        for question in questions:
            answer_text = "Ответ студента на этот вопрос"
            answer_choice = ["a"]  # для choice questions
            is_correct = True
            points_earned = question.points

            _, created = AssignmentAnswer.objects.get_or_create(
                submission=submission,
                question=question,
                defaults={
                    "answer_text": answer_text,
                    "answer_choice": answer_choice,
                    "is_correct": is_correct,
                    "points_earned": points_earned,
                },
            )

    def _print_summary(self, assignments):
        """Выводит сводку созданных данных"""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("СВОДКА СОЗДАННЫХ ДАННЫХ"))
        self.stdout.write("=" * 60)

        for assignment in assignments:
            questions_count = assignment.questions.count()
            submissions_count = assignment.submissions.count()

            self.stdout.write(
                f"\n  Задание: {assignment.title}\n"
                f"    Вопросов: {questions_count}\n"
                f"    Отправок: {submissions_count}\n"
                f"    Автор: {assignment.author.email}\n"
                f"    Статус: {assignment.get_status_display()}"
            )

        total_questions = sum(a.questions.count() for a in assignments)
        total_submissions = sum(a.submissions.count() for a in assignments)

        self.stdout.write("\n" + "-" * 60)
        self.stdout.write(f"Всего заданий: {len(assignments)}")
        self.stdout.write(f"Всего вопросов: {total_questions}")
        self.stdout.write(f"Всего отправок: {total_submissions}")
        self.stdout.write("=" * 60)
