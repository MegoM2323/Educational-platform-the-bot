from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.contrib.auth import get_user_model
from materials.models import SubjectEnrollment, Subject

User = get_user_model()


class Command(BaseCommand):
    help = "Setup production users: clear ALL users and create 7 test users"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Skip confirmation prompts (for non-interactive mode)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what will be created without making changes",
        )

    def handle(self, *args, **options):
        force = options["force"]
        dry_run = options["dry_run"]

        if dry_run:
            self.stdout.write(
                self.style.WARNING("DRY-RUN MODE: No changes will be made")
            )
            self.preview_setup()
            return

        if not force:
            self.stdout.write(
                self.style.WARNING(
                    "WARNING: This will DELETE ALL users and related data."
                )
            )
            confirm = input("Continue? [y/N]: ")
            if confirm.lower() != "y":
                self.stdout.write(self.style.ERROR("Aborted."))
                return

        try:
            with transaction.atomic():
                self.delete_all_users()
                self.create_users()
                self.create_profiles()
                self.create_relationships()
                self.verify_and_report()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            raise CommandError(str(e))

    def delete_all_users(self):
        count = User.objects.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS("No users to delete"))
            return

        from django.db import connection

        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM chat_chatroom_participants")
            cursor.execute("DELETE FROM chat_chatroom")
            cursor.execute("DELETE FROM chat_message")

        User.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f"Deleted {count} users and all related data (CASCADE)")
        )

    def create_users(self):
        users_data = [
            {
                "email": "alexander@master.com",
                "password": "bangbang",
                "first_name": "Alexander",
                "last_name": "Master",
                "role": User.Role.ADMIN,
            },
            {
                "email": "mikhail@master.com",
                "password": "fastestpass",
                "first_name": "Mikhail",
                "last_name": "Master",
                "role": User.Role.ADMIN,
            },
            {
                "email": "student@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Student",
                "role": User.Role.STUDENT,
            },
            {
                "email": "teacher@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Teacher",
                "role": User.Role.TEACHER,
            },
            {
                "email": "tutor@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Tutor",
                "role": User.Role.TUTOR,
            },
            {
                "email": "parent@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Parent",
                "role": User.Role.PARENT,
            },
            {
                "email": "admin@test.com",
                "password": "TestPass123!",
                "first_name": "Test",
                "last_name": "Admin",
                "role": User.Role.ADMIN,
            },
        ]

        for user_data in users_data:
            password = user_data.pop("password")
            user = User.objects.create_user(
                username=user_data["email"],
                is_verified=True,
                is_active=True,
                **user_data,
            )
            user.set_password(password)
            user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f"Created user: {user.email} ({user.get_role_display()})"
                )
            )

    def create_profiles(self):
        student_user = User.objects.get(email="student@test.com")
        teacher_user = User.objects.get(email="teacher@test.com")
        tutor_user = User.objects.get(email="tutor@test.com")

        student_profile = student_user.student_profile
        student_profile.grade = 10
        student_profile.goal = "Test learning"
        student_profile.progress_percentage = 0
        student_profile.streak_days = 0
        student_profile.total_points = 0
        student_profile.accuracy_percentage = 0
        student_profile.save()
        self.stdout.write(
            self.style.SUCCESS("Updated StudentProfile for student@test.com")
        )

        teacher_profile = teacher_user.teacher_profile
        teacher_profile.subject = "Математика"
        teacher_profile.experience_years = 5
        teacher_profile.save()
        self.stdout.write(
            self.style.SUCCESS("Updated TeacherProfile for teacher@test.com")
        )

        tutor_profile = tutor_user.tutor_profile
        tutor_profile.specialization = "Test Tutoring"
        tutor_profile.experience_years = 3
        tutor_profile.save()
        self.stdout.write(self.style.SUCCESS("Updated TutorProfile for tutor@test.com"))

    def create_relationships(self):
        student_user = User.objects.get(email="student@test.com")
        teacher_user = User.objects.get(email="teacher@test.com")
        tutor_user = User.objects.get(email="tutor@test.com")
        parent_user = User.objects.get(email="parent@test.com")

        student_profile = student_user.student_profile
        student_profile.tutor = tutor_user
        student_profile.parent = parent_user
        student_profile.save()
        self.stdout.write(
            self.style.SUCCESS("Set tutor and parent for student profile")
        )

        subject, created = Subject.objects.get_or_create(
            name="Математика", defaults={"description": "Test subject"}
        )

        SubjectEnrollment.objects.create(
            student=student_user,
            teacher=teacher_user,
            subject=subject,
            status=SubjectEnrollment.Status.ACTIVE,
            is_active=True,
        )
        self.stdout.write(self.style.SUCCESS("Created SubjectEnrollment for student"))

    def verify_and_report(self):
        total_users = User.objects.count()

        if total_users != 7:
            raise CommandError(f"Expected 7 users, but found {total_users}")

        self.stdout.write(
            self.style.SUCCESS(f"\n{total_users} users created successfully!")
        )
        self.stdout.write(self.style.SUCCESS("\nUser Report:"))
        self.stdout.write("-" * 60)

        for user in User.objects.all().order_by("created_at"):
            self.stdout.write(
                f"{user.email:<25} | Role: {user.get_role_display():<15} | Verified: {user.is_verified}"
            )

    def preview_setup(self):
        self.stdout.write(self.style.WARNING("\nPreview of users to be created:"))
        self.stdout.write("-" * 60)

        users_preview = [
            ("alexander@master.com", "ADMIN"),
            ("mikhail@master.com", "ADMIN"),
            ("student@test.com", "STUDENT"),
            ("teacher@test.com", "TEACHER"),
            ("tutor@test.com", "TUTOR"),
            ("parent@test.com", "PARENT"),
            ("admin@test.com", "ADMIN"),
        ]

        for email, role in users_preview:
            self.stdout.write(f"{email:<25} | Role: {role}")

        self.stdout.write("-" * 60)
        self.stdout.write(self.style.WARNING(f"Total: 7 users would be created\n"))
