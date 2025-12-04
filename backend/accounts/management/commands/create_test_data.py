"""
Management command to create complete test data for all user roles.
Creates users with proper password hashing, profiles, subjects, enrollments, and lessons.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import User, StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from materials.models import Subject, TeacherSubject, SubjectEnrollment
from scheduling.models import Lesson


class Command(BaseCommand):
    help = 'Create complete test data for all user roles'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING('Creating test data...'))

        # Create or update users with proper password hashing
        student1, created = User.objects.get_or_create(
            username='student1',
            defaults={
                'email': 'student1@test.com',
                'role': 'student',
                'first_name': 'Алексей',
                'last_name': 'Иванов'
            }
        )
        student1.set_password('test123')
        student1.save()
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} student1: {student1.email}'))

        student2, created = User.objects.get_or_create(
            username='student2',
            defaults={
                'email': 'student2@test.com',
                'role': 'student',
                'first_name': 'Мария',
                'last_name': 'Петрова'
            }
        )
        student2.set_password('test123')
        student2.save()
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} student2: {student2.email}'))

        teacher, created = User.objects.get_or_create(
            username='teacher',
            defaults={
                'email': 'teacher@test.com',
                'role': 'teacher',
                'first_name': 'Ирина',
                'last_name': 'Сидорова'
            }
        )
        teacher.set_password('test123')
        teacher.save()
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} teacher: {teacher.email}'))

        tutor, created = User.objects.get_or_create(
            username='tutor',
            defaults={
                'email': 'tutor@test.com',
                'role': 'tutor',
                'first_name': 'Дмитрий',
                'last_name': 'Смирнов'
            }
        )
        tutor.set_password('test123')
        tutor.save()
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} tutor: {tutor.email}'))

        parent, created = User.objects.get_or_create(
            username='parent',
            defaults={
                'email': 'parent@test.com',
                'role': 'parent',
                'first_name': 'Елена',
                'last_name': 'Иванова'
            }
        )
        parent.set_password('test123')
        parent.save()
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} parent: {parent.email}'))

        # Create or update profiles
        student1_profile, created = StudentProfile.objects.get_or_create(
            user=student1,
            defaults={'tutor': tutor, 'grade': '9'}
        )
        if not created:
            student1_profile.tutor = tutor
            student1_profile.grade = '9'
            student1_profile.save()
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} profile for student1 (tutor: {tutor.email})'))

        student2_profile, created = StudentProfile.objects.get_or_create(
            user=student2,
            defaults={'tutor': tutor, 'grade': '10'}
        )
        if not created:
            student2_profile.tutor = tutor
            student2_profile.grade = '10'
            student2_profile.save()
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} profile for student2 (tutor: {tutor.email})'))

        teacher_profile, created = TeacherProfile.objects.get_or_create(
            user=teacher,
            defaults={'bio': 'Experienced math teacher'}
        )
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} profile for teacher'))

        tutor_profile, created = TutorProfile.objects.get_or_create(
            user=tutor,
            defaults={'bio': 'Professional tutor'}
        )
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} profile for tutor'))

        parent_profile, created = ParentProfile.objects.get_or_create(user=parent)
        # Link students to parent (via StudentProfile.parent field)
        student1_profile.parent = parent
        student1_profile.save()
        student2_profile.parent = parent
        student2_profile.save()
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Updated"} profile for parent (linked to student1, student2)'))

        # Create or update subjects
        math_subject, created = Subject.objects.get_or_create(
            name='Математика',
            defaults={
                'description': 'Алгебра и геометрия 9-10 класс',
                'grade_level': '9-10'
            }
        )
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Found"} subject: {math_subject.name}'))

        physics_subject, created = Subject.objects.get_or_create(
            name='Физика',
            defaults={
                'description': 'Механика и термодинамика',
                'grade_level': '9-10'
            }
        )
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Found"} subject: {physics_subject.name}'))

        # Link teacher to subjects
        TeacherSubject.objects.get_or_create(teacher=teacher, subject=math_subject)
        TeacherSubject.objects.get_or_create(teacher=teacher, subject=physics_subject)
        self.stdout.write(self.style.SUCCESS(f'✓ Linked teacher to subjects (Math, Physics)'))

        # Create subject enrollments (triggers forum chat creation signals)
        enrollment1, created = SubjectEnrollment.objects.get_or_create(
            student=student1,
            subject=math_subject,
            teacher=teacher
        )
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Found"} enrollment: student1 → Math → teacher'))

        enrollment2, created = SubjectEnrollment.objects.get_or_create(
            student=student1,
            subject=physics_subject,
            teacher=teacher
        )
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Found"} enrollment: student1 → Physics → teacher'))

        enrollment3, created = SubjectEnrollment.objects.get_or_create(
            student=student2,
            subject=math_subject,
            teacher=teacher
        )
        self.stdout.write(self.style.SUCCESS(f'✓ {"Created" if created else "Found"} enrollment: student2 → Math → teacher'))

        # Delete old test lessons and create fresh ones
        Lesson.objects.filter(
            teacher=teacher,
            student__in=[student1, student2]
        ).delete()
        self.stdout.write(self.style.WARNING('Deleted old test lessons'))

        # Create lessons (future dates)
        now = timezone.now()
        tomorrow = now + timedelta(days=1)
        next_week = now + timedelta(days=7)

        lesson1 = Lesson.objects.create(
            teacher=teacher,
            student=student1,
            subject=math_subject,
            date=tomorrow.date(),
            start_time=timezone.datetime.strptime('10:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            description='Квадратные уравнения',
            telemost_link='https://telemost.yandex.ru/test1'
        )
        self.stdout.write(self.style.SUCCESS(f'✓ Created lesson1: Math for student1 on {tomorrow.date()} 10:00-11:00'))

        lesson2 = Lesson.objects.create(
            teacher=teacher,
            student=student1,
            subject=physics_subject,
            date=tomorrow.date(),
            start_time=timezone.datetime.strptime('14:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('15:00', '%H:%M').time(),
            description='Законы Ньютона',
            telemost_link='https://telemost.yandex.ru/test2'
        )
        self.stdout.write(self.style.SUCCESS(f'✓ Created lesson2: Physics for student1 on {tomorrow.date()} 14:00-15:00'))

        lesson3 = Lesson.objects.create(
            teacher=teacher,
            student=student2,
            subject=math_subject,
            date=next_week.date(),
            start_time=timezone.datetime.strptime('11:00', '%H:%M').time(),
            end_time=timezone.datetime.strptime('12:00', '%H:%M').time(),
            description='Тригонометрия',
            telemost_link='https://telemost.yandex.ru/test3'
        )
        self.stdout.write(self.style.SUCCESS(f'✓ Created lesson3: Math for student2 on {next_week.date()} 11:00-12:00'))

        # Verify forum chats were created by signals
        from chat.models import ChatRoom
        forum_chats = ChatRoom.objects.filter(type__in=['FORUM_SUBJECT', 'FORUM_TUTOR'])
        self.stdout.write(self.style.SUCCESS(f'✓ Verified: {forum_chats.count()} forum chats created by signals'))

        # Output credentials
        self.stdout.write(self.style.SUCCESS('\n' + '='*60))
        self.stdout.write(self.style.SUCCESS('TEST CREDENTIALS (email / password):'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.WARNING('Student 1: student1@test.com / test123'))
        self.stdout.write(self.style.WARNING('Student 2: student2@test.com / test123'))
        self.stdout.write(self.style.WARNING('Teacher:   teacher@test.com / test123'))
        self.stdout.write(self.style.WARNING('Tutor:     tutor@test.com / test123'))
        self.stdout.write(self.style.WARNING('Parent:    parent@test.com / test123'))
        self.stdout.write(self.style.SUCCESS('='*60))
        self.stdout.write(self.style.SUCCESS('\n✓ Test data creation complete!'))
