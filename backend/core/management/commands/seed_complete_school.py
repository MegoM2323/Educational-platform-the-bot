import random
from pathlib import Path
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.core.management import call_command
from django.conf import settings

from accounts.models import User, StudentProfile
from materials.models import Subject, SubjectEnrollment, Material, StudyPlan
from scheduling.models import Lesson


class Command(BaseCommand):
    help = "Seed complete school environment with all relationships"

    def get_week_start(self, date):
        """Get Monday of the week containing given date."""
        weekday = date.weekday()
        return date - timedelta(days=weekday)

    def create_subject_enrollments(self):
        """PHASE 2: Create CRITICAL SubjectEnrollment relationships."""
        self.stdout.write("\n=== PHASE 2: Creating SubjectEnrollments ===")

        tutor = User.objects.get(email="tutor@test.com")
        student1 = User.objects.get(email="student@test.com")
        student2 = None
        if User.objects.filter(email="student2@test.com").exists():
            student2 = User.objects.get(email="student2@test.com")

        teacher1 = User.objects.get(email="teacher@test.com")
        teacher2 = teacher1
        if User.objects.filter(email="teacher2@test.com").exists():
            teacher2 = User.objects.get(email="teacher2@test.com")

        subjects = {s.name: s for s in Subject.objects.all()}

        enrollments = []

        enrollment1, created = SubjectEnrollment.objects.get_or_create(
            student=student1,
            subject=subjects.get("Математика"),
            teacher=teacher1,
            defaults={"assigned_by": tutor, "is_active": True},
        )
        enrollments.append(enrollment1)
        status = "создан" if created else "уже существует"
        self.stdout.write(
            f"  ✓ {student1.email} → Математика ({teacher1.email}) - {status}"
        )

        enrollment2, created = SubjectEnrollment.objects.get_or_create(
            student=student1,
            subject=subjects.get("Физика"),
            teacher=teacher2,
            defaults={"assigned_by": tutor, "is_active": True},
        )
        enrollments.append(enrollment2)
        status = "создан" if created else "уже существует"
        self.stdout.write(
            f"  ✓ {student1.email} → Физика ({teacher2.email}) - {status}"
        )

        if student2:
            enrollment3, created = SubjectEnrollment.objects.get_or_create(
                student=student2,
                subject=subjects.get("Математика"),
                teacher=teacher2,
                defaults={"assigned_by": tutor, "is_active": True},
            )
            enrollments.append(enrollment3)
            status = "создан" if created else "уже существует"
            self.stdout.write(
                f"  ✓ {student2.email} → Математика ({teacher2.email}) - {status}"
            )

            enrollment4, created = SubjectEnrollment.objects.get_or_create(
                student=student2,
                subject=subjects.get("Информатика"),
                teacher=teacher1,
                defaults={"assigned_by": tutor, "is_active": True},
            )
            enrollments.append(enrollment4)
            status = "создан" if created else "уже существует"
            self.stdout.write(
                f"  ✓ {student2.email} → Информатика ({teacher1.email}) - {status}"
            )

        return enrollments

    def create_lesson_schedule(self, enrollments):
        """PHASE 3: Generate Lessons schedule."""
        self.stdout.write("\n=== PHASE 3: Creating Lessons ===")

        today = timezone.now().date()
        statuses = [
            (Lesson.Status.PENDING, 0.2),
            (Lesson.Status.CONFIRMED, 0.5),
            (Lesson.Status.COMPLETED, 0.2),
            (Lesson.Status.CANCELLED, 0.1),
        ]
        times = ["09:00", "11:00", "14:00", "16:00"]

        created_count = 0

        for enrollment in enrollments:
            for week in range(3):
                for _ in range(2):
                    date = today + timedelta(
                        days=7 * week + random.choice([1, 2, 3, 4, 5])
                    )
                    start_time = random.choice(times)

                    hour, minute = map(int, start_time.split(":"))
                    end_hour = hour + 1
                    end_minute = minute + 30
                    if end_minute >= 60:
                        end_hour += 1
                        end_minute -= 60
                    end_time = f"{end_hour:02d}:{end_minute:02d}"

                    status = random.choices(
                        [s[0] for s in statuses], weights=[s[1] for s in statuses]
                    )[0]

                    if status == Lesson.Status.COMPLETED:
                        date = today - timedelta(days=random.randint(1, 14))

                    try:
                        lesson = Lesson(
                            teacher=enrollment.teacher,
                            student=enrollment.student,
                            subject=enrollment.subject,
                            date=date,
                            start_time=start_time,
                            end_time=end_time,
                            status=status,
                            notes=f"Test lesson for {enrollment.subject.name}",
                        )
                        lesson.save(skip_validation=(status == Lesson.Status.COMPLETED))
                        created_count += 1
                    except Exception as e:
                        self.stdout.write(
                            self.style.WARNING(f"  ⚠ Ошибка создания урока: {e}")
                        )

        self.stdout.write(self.style.SUCCESS(f"  ✓ Создано уроков: {created_count}"))

    def create_study_plans(self, enrollments):
        """PHASE 4: Generate StudyPlans."""
        self.stdout.write("\n=== PHASE 4: Creating StudyPlans ===")

        today = timezone.now().date()
        created_count = 0

        for enrollment in enrollments:
            for week_offset in [0, 1]:
                week_start = self.get_week_start(today) + timedelta(weeks=week_offset)

                plan, created = StudyPlan.objects.get_or_create(
                    teacher=enrollment.teacher,
                    student=enrollment.student,
                    subject=enrollment.subject,
                    week_start_date=week_start,
                    defaults={
                        "enrollment": enrollment,
                        "title": f"Week {week_offset+1}: {enrollment.subject.name}",
                        "content": f"Study plan for {enrollment.subject.name}. Topics: [fill in actual topics]",
                        "status": StudyPlan.Status.SENT
                        if week_offset == 0
                        else StudyPlan.Status.DRAFT,
                        "week_end_date": week_start + timedelta(days=6),
                    },
                )

                if created:
                    created_count += 1

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Создано планов занятий: {created_count}")
        )

    def generate_enrollment_table(self, enrollments):
        """Generate markdown table of enrollments."""
        lines = ["| Student | Subject | Teacher |", "|---------|---------|---------|"]

        for e in enrollments:
            lines.append(
                f"| {e.student.email} | {e.subject.name} | {e.teacher.email} |"
            )

        return "\n".join(lines)

    def export_credentials(self):
        """PHASE 5: Export credentials to ACCOUNTS.md."""
        self.stdout.write("\n=== PHASE 5: Exporting Credentials ===")

        enrollments = SubjectEnrollment.objects.filter(is_active=True)
        lessons = Lesson.objects.all()
        plans = StudyPlan.objects.all()

        content = f"""# THE_BOT Platform - Test Accounts

Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')}

## Login Credentials

| Role | Email | Password |
|------|-------|----------|
| Admin | admin@test.com | TestPass123! |
| Teacher | teacher@test.com | TestPass123! |
| Teacher | teacher2@test.com | TestPass123! |
| Student | student@test.com | TestPass123! |
| Student | student2@test.com | TestPass123! |
| Tutor | tutor@test.com | TestPass123! |
| Parent | parent@test.com | TestPass123! |

## Summary

- Users: {User.objects.count()}
- Subjects: {Subject.objects.count()}
- SubjectEnrollments: {enrollments.count()}
- Lessons: {lessons.count()}
- StudyPlans: {plans.count()}
- Materials: {Material.objects.count()}

## SubjectEnrollment Details

{self.generate_enrollment_table(enrollments)}

## Lessons Schedule

- Total: {lessons.count()}
- Pending: {lessons.filter(status='pending').count()}
- Confirmed: {lessons.filter(status='confirmed').count()}
- Completed: {lessons.filter(status='completed').count()}
- Cancelled: {lessons.filter(status='cancelled').count()}

## StudyPlans Status

- Total: {plans.count()}
- Draft: {plans.filter(status='draft').count()}
- Sent: {plans.filter(status='sent').count()}
- Archived: {plans.filter(status='archived').count()}
"""

        project_root = Path(settings.BASE_DIR).parent
        credentials_dir = project_root / ".claude" / "deployment"
        credentials_dir.mkdir(parents=True, exist_ok=True)
        output_path = credentials_dir / "ACCOUNTS.md"
        output_path.write_text(content)

        self.stdout.write(
            self.style.SUCCESS(f"  ✓ Credentials exported to {output_path}")
        )

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("SEED COMPLETE SCHOOL ENVIRONMENT"))
        self.stdout.write("=" * 80)

        self.stdout.write("\n=== PHASE 1: Calling Existing Seed Commands ===")
        call_command("create_test_users_all")
        call_command("create_test_subjects")
        call_command("seed_test_materials")

        enrollments = self.create_subject_enrollments()

        self.create_lesson_schedule(enrollments)

        self.create_study_plans(enrollments)

        self.export_credentials()

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("✅ COMPLETE SCHOOL ENVIRONMENT READY!"))
        self.stdout.write("=" * 80)
        self.stdout.write(
            f"""
Summary:
  • Users: {User.objects.count()}
  • Subjects: {Subject.objects.count()}
  • SubjectEnrollments: {SubjectEnrollment.objects.filter(is_active=True).count()}
  • Lessons: {Lesson.objects.count()}
  • StudyPlans: {StudyPlan.objects.count()}
  • Materials: {Material.objects.count()}

Next steps:
  1. Login with any test account (see ../../../.claude/deployment/ACCOUNTS.md)
  2. Test lesson scheduling
  3. Test study plan creation
  4. Test material assignments
"""
        )
        self.stdout.write("=" * 80 + "\n")
