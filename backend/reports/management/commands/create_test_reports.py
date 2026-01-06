import random
from datetime import datetime, timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction

from accounts.models import User
from materials.models import Subject
from reports.models import StudentReport, TeacherWeeklyReport, TutorWeeklyReport


class Command(BaseCommand):
    help = "Create test reports for StudentReport, TeacherWeeklyReport, and TutorWeeklyReport models"

    @transaction.atomic()
    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Начинаем создание тестовых отчетов..."))

        try:
            student_user = self._get_user("student@test.com", User.Role.STUDENT)
            teacher_user = self._get_user("teacher@test.com", User.Role.TEACHER)
            tutor_user = self._get_user("tutor@test.com", User.Role.TUTOR)
            parent_user = self._get_user("parent@test.com", User.Role.PARENT)

            if not all([student_user, teacher_user, tutor_user]):
                raise CommandError(
                    "Не найдены требуемые пользователи (student, teacher, tutor). "
                    "Создайте их перед запуском команды."
                )

            self.stdout.write(self.style.SUCCESS("✓ Найдены все требуемые пользователи"))

            self._create_student_reports(student_user, teacher_user, parent_user)
            self._create_teacher_weekly_reports(
                teacher_user, student_user, tutor_user
            )
            self._create_tutor_weekly_report(tutor_user, student_user, parent_user)

            self.stdout.write(
                self.style.SUCCESS("✓ Все тестовые отчеты успешно созданы!")
            )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка создания отчетов: {str(e)}"))
            raise

    def _get_user(self, email: str, role: str) -> User:
        """Get user by email and role using get_or_create pattern with try/except."""
        try:
            user = User.objects.get(email=email, role=role)
            self.stdout.write(f"  ✓ Найден пользователь: {email} ({role})")
            return user
        except User.DoesNotExist:
            self.stdout.write(
                self.style.WARNING(f"  ⚠ Пользователь не найден: {email} (роль: {role})")
            )
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(email=email, role=role).first()
            self.stdout.write(
                self.style.WARNING(
                    f"  ⚠ Найдено несколько пользователей с {email}. Используем первого."
                )
            )
            return user

    def _get_week_dates(self, weeks_back: int = 0) -> tuple:
        """Get week start and end dates for given weeks back."""
        now = timezone.now()
        current_week_start = now - timedelta(days=now.weekday())
        week_start = current_week_start - timedelta(weeks=weeks_back)
        week_end = week_start + timedelta(days=6)
        return week_start.date(), week_end.date()

    def _create_student_reports(self, student: User, teacher: User, parent: User):
        """Create 3 StudentReports for the last 3 weeks."""
        self.stdout.write(self.style.HTTP_INFO("Создание StudentReports..."))

        statuses = [StudentReport.Status.DRAFT, StudentReport.Status.SENT]

        for weeks_back in [2, 1, 0]:
            period_start, period_end = self._get_week_dates(weeks_back)

            report_data = {
                "title": f"Progress Report - Week {weeks_back} (Student: {student.get_full_name()})",
                "description": f"Automatic progress report for the week of {period_start}",
                "report_type": StudentReport.ReportType.PROGRESS,
                "status": statuses[weeks_back % len(statuses)],
                "teacher": teacher,
                "student": student,
                "parent": parent,
                "period_start": period_start,
                "period_end": period_end,
                "overall_grade": random.choice(["A", "B", "C", "B+", "A-"]),
                "progress_percentage": random.randint(60, 95),
                "attendance_percentage": random.randint(70, 95),
                "behavior_rating": random.randint(6, 10),
                "recommendations": "Student shows good engagement and understanding. "
                "Continue with consistent study habits.",
                "concerns": "Minor areas for improvement in time management.",
                "achievements": "Excellent performance in recent assignments. "
                "Demonstrated strong problem-solving skills.",
                "content": {
                    "total_score": random.randint(75, 100),
                    "completed_assignments": random.randint(8, 15),
                    "submitted_assignments": random.randint(10, 15),
                    "participation_score": random.randint(70, 100),
                    "quiz_average": round(random.uniform(75, 95), 2),
                    "assignment_average": round(random.uniform(75, 95), 2),
                },
            }

            report, created = StudentReport.objects.update_or_create(
                teacher=teacher,
                student=student,
                period_start=period_start,
                period_end=period_end,
                defaults=report_data,
            )
            status = "✓ Создан" if created else "~ Обновлен"
            self.stdout.write(
                f"  {status} StudentReport неделя {weeks_back} - {period_start} по {period_end}"
            )

    def _create_teacher_weekly_reports(self, teacher: User, student: User, tutor: User):
        """Create 2 TeacherWeeklyReports for current and previous week."""
        self.stdout.write(self.style.HTTP_INFO("Создание TeacherWeeklyReports..."))

        subject = Subject.objects.first()
        if not subject:
            raise CommandError(
                "Не найдены предметы. Сначала создайте предметы через create_test_materials"
            )

        for weeks_back in [1, 0]:
            week_start, week_end = self._get_week_dates(weeks_back)

            report_data = {
                "title": f"Weekly Report - {week_start} (Teacher: {teacher.get_full_name()})",
                "summary": f"This week's progress summary for {student.get_full_name()}.",
                "academic_progress": "Student demonstrated consistent improvement in understanding core concepts.",
                "performance_notes": "Completed all assigned tasks with good quality.",
                "achievements": "Excelled in mathematical problem-solving and analytical thinking.",
                "concerns": "Needs to work on presentation skills.",
                "recommendations": "Encourage peer collaboration and public speaking practice.",
                "assignments_completed": random.randint(8, 12),
                "assignments_total": 10,
                "average_score": Decimal(str(round(random.uniform(75, 95), 2))),
                "attendance_percentage": random.randint(75, 95),
                "status": TeacherWeeklyReport.Status.SENT
                if weeks_back > 0
                else TeacherWeeklyReport.Status.DRAFT,
            }

            report, created = TeacherWeeklyReport.objects.update_or_create(
                teacher=teacher,
                student=student,
                subject=subject,
                week_start=week_start,
                defaults={**report_data, "week_end": week_end, "tutor": tutor},
            )
            status = "✓ Создан" if created else "~ Обновлен"
            self.stdout.write(
                f"  {status} TeacherWeeklyReport неделя {weeks_back} - {week_start} по {week_end}"
            )

    def _create_tutor_weekly_report(self, tutor: User, student: User, parent: User):
        """Create 1 TutorWeeklyReport for current week."""
        self.stdout.write(self.style.HTTP_INFO("Создание TutorWeeklyReport..."))

        week_start, week_end = self._get_week_dates(0)

        report_data = {
            "title": f"Weekly Report - {week_start} (Tutor: {tutor.get_full_name()})",
            "summary": f"Overview of {student.get_full_name()}'s progress this week. "
            "Student is showing positive trends and good engagement.",
            "academic_progress": "Strong performance across all subjects. "
            "Completed challenging assignments with minimal guidance.",
            "behavior_notes": "Excellent participation and cooperation during sessions. "
            "Shows initiative in asking clarifying questions.",
            "achievements": "Mastered new concepts in calculus and started advanced topics.",
            "concerns": "None at this time. Student is performing well.",
            "recommendations": "Consider introducing more challenging material to maintain engagement.",
            "attendance_days": random.randint(4, 7),
            "total_days": 7,
            "progress_percentage": random.randint(75, 95),
            "status": TutorWeeklyReport.Status.SENT,
        }

        report, created = TutorWeeklyReport.objects.update_or_create(
            tutor=tutor,
            student=student,
            week_start=week_start,
            defaults={**report_data, "week_end": week_end, "parent": parent},
        )
        status = "✓ Создан" if created else "~ Обновлен"
        self.stdout.write(
            f"  {status} TutorWeeklyReport - {week_start} по {week_end}"
        )
