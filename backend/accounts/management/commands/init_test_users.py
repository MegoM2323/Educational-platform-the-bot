"""
Management command to initialize test users for development/testing
Based on TESTING_SCENARIOS.md
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from materials.models import Subject, SubjectEnrollment
import logging

User = get_user_model()
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Initialize test users for development/testing based on TESTING_SCENARIOS.md'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear all existing users before creating test users'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initializing test users...'))

        # Clear existing users if requested
        if options['clear']:
            User.objects.all().delete()
            self.stdout.write(self.style.WARNING('Cleared all existing users'))

        test_users_data = [
            {
                'email': 'admin@test.com',
                'password': 'admin123',
                'role': 'admin',
                'first_name': 'Admin',
                'last_name': 'User',
                'is_staff': True,
                'is_superuser': True,
            },
            {
                'email': 'teacher1@test.com',
                'password': 'teacher123',
                'role': 'teacher',
                'first_name': 'Иван',
                'last_name': 'Иванов',
            },
            {
                'email': 'teacher2@test.com',
                'password': 'teacher123',
                'role': 'teacher',
                'first_name': 'Петр',
                'last_name': 'Петров',
            },
            {
                'email': 'tutor1@test.com',
                'password': 'tutor123',
                'role': 'tutor',
                'first_name': 'Сергей',
                'last_name': 'Сергеев',
            },
            {
                'email': 'tutor2@test.com',
                'password': 'tutor123',
                'role': 'tutor',
                'first_name': 'Александр',
                'last_name': 'Александров',
            },
            {
                'email': 'student1@test.com',
                'password': 'student123',
                'role': 'student',
                'first_name': 'Иван',
                'last_name': 'Сидоров',
            },
            {
                'email': 'student2@test.com',
                'password': 'student123',
                'role': 'student',
                'first_name': 'Мария',
                'last_name': 'Сидорова',
            },
            {
                'email': 'student3@test.com',
                'password': 'student123',
                'role': 'student',
                'first_name': 'Алексей',
                'last_name': 'Смирнов',
            },
            {
                'email': 'parent1@test.com',
                'password': 'parent123',
                'role': 'parent',
                'first_name': 'Иван',
                'last_name': 'Петров',
            },
            {
                'email': 'parent2@test.com',
                'password': 'parent123',
                'role': 'parent',
                'first_name': 'Мария',
                'last_name': 'Сидорова',
            },
        ]

        created_users = {}
        for user_data in test_users_data:
            email = user_data['email']
            password = user_data.pop('password')
            role = user_data['role']

            # Check if user already exists
            if User.objects.filter(email=email).exists():
                self.stdout.write(self.style.WARNING(f'  ⊘ {email} already exists'))
                created_users[email] = User.objects.get(email=email)
                continue

            # Create user
            user = User.objects.create_user(**user_data, password=password)
            created_users[email] = user

            # Create role-specific profile
            if role == 'student':
                StudentProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'goal': 'Подготовка к экзамену',
                        'accuracy': 75.0,
                    }
                )
                self.stdout.write(self.style.SUCCESS(f'  ✓ {email} (Student)'))

            elif role == 'teacher':
                TeacherProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'bio': 'Профессиональный преподаватель',
                        'experience_years': 5,
                    }
                )
                self.stdout.write(self.style.SUCCESS(f'  ✓ {email} (Teacher)'))

            elif role == 'tutor':
                TutorProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'bio': 'Опытный репетитор',
                        'experience_years': 5,
                    }
                )
                self.stdout.write(self.style.SUCCESS(f'  ✓ {email} (Tutor)'))

            elif role == 'parent':
                ParentProfile.objects.get_or_create(
                    user=user,
                )
                self.stdout.write(self.style.SUCCESS(f'  ✓ {email} (Parent)'))

        # Create subjects
        self.stdout.write('\nInitializing subjects...')
        subjects_data = [
            {'name': 'Математика', 'code': 'mathematics', 'color': '#FF6B6B'},
            {'name': 'Английский язык', 'code': 'english', 'color': '#4ECDC4'},
            {'name': 'Физика', 'code': 'physics', 'color': '#45B7D1'},
        ]

        created_subjects = {}
        for subject_data in subjects_data:
            subject, created = Subject.objects.get_or_create(
                code=subject_data['code'],
                defaults={
                    'name': subject_data['name'],
                    'color': subject_data['color'],
                    'description': f'Курс {subject_data["name"]}',
                }
            )
            created_subjects[subject_data['code']] = subject
            status = '✓ Created' if created else '⊘ Exists'
            self.stdout.write(self.style.SUCCESS(f'  {status}: {subject_data["name"]}'))

        # Create subject enrollments
        self.stdout.write('\nInitializing subject enrollments...')
        enrollments_data = [
            ('student1@test.com', 'mathematics'),
            ('student1@test.com', 'physics'),
            ('student2@test.com', 'english'),
            ('student3@test.com', 'mathematics'),
        ]

        for student_email, subject_code in enrollments_data:
            if student_email in created_users and subject_code in created_subjects:
                student = created_users[student_email]
                subject = created_subjects[subject_code]
                enrollment, created = SubjectEnrollment.objects.get_or_create(
                    student=student,
                    subject=subject,
                    defaults={'enrolled_at': None}
                )
                status = '✓ Created' if created else '⊘ Exists'
                self.stdout.write(self.style.SUCCESS(
                    f'  {status}: {student_email} → {subject.name}'
                ))

        # Set parent-student relationships
        self.stdout.write('\nInitializing parent-student relationships...')
        relationships = [
            ('parent1@test.com', 'student1@test.com'),
            ('parent2@test.com', 'student2@test.com'),
        ]

        for parent_email, student_email in relationships:
            if parent_email in created_users and student_email in created_users:
                parent = created_users[parent_email]
                student = created_users[student_email]
                student_profile = StudentProfile.objects.get(user=student)
                student_profile.parent = parent
                student_profile.save()
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ {parent_email} is parent of {student_email}'
                ))

        # Set tutor-student relationships
        self.stdout.write('\nInitializing tutor-student relationships...')
        tutor_relationships = [
            ('tutor1@test.com', 'student1@test.com'),
            ('tutor1@test.com', 'student3@test.com'),
            ('tutor2@test.com', 'student2@test.com'),
        ]

        for tutor_email, student_email in tutor_relationships:
            if tutor_email in created_users and student_email in created_users:
                tutor = created_users[tutor_email]
                student = created_users[student_email]
                student_profile = StudentProfile.objects.get(user=student)
                student_profile.tutor = tutor
                student_profile.save()
                self.stdout.write(self.style.SUCCESS(
                    f'  ✓ {tutor_email} is tutor of {student_email}'
                ))

        self.stdout.write(self.style.SUCCESS('\n✓ Test users initialized successfully!'))
        self.stdout.write('\nYou can now test the API with:')
        self.stdout.write('  Email: student1@test.com, Password: student123')
        self.stdout.write('  Email: teacher1@test.com, Password: teacher123')
        self.stdout.write('  Email: admin@test.com, Password: admin123')
