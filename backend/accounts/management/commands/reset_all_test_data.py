"""
Master test data generation script combining all functionality.

This command creates a complete test dataset with:
1. Fresh users (student, teacher, tutor, parent, admin)
2. User profiles for all roles
3. Test subjects and teacher assignments
4. Comprehensive test data (materials, assignments, reports, etc.)

Usage:
  python manage.py reset_all_test_data
  python manage.py reset_all_test_data --clear
  python manage.py reset_all_test_data --clear --verbose
"""

import io
import random
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Dict, List

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
    """ANSI terminal colors."""
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    END = '\033[0m'
    BOLD = '\033[1m'


class Command(BaseCommand):
    """Master command for complete test data generation and reset."""

    help = 'Resets database and creates complete test dataset with all roles and data'

    def __init__(self):
        super().__init__()
        self.stats = {
            'users_created': 0,
            'profiles_created': 0,
            'subjects_created': 0,
            'teacher_subjects': 0,
            'parent_links': 0,
            'enrollments': 0,
            'materials': 0,
            'material_submissions': 0,
            'study_plans': 0,
            'study_plan_files': 0,
            'assignments': 0,
            'assignment_submissions': 0,
            'student_reports': 0,
            'teacher_reports': 0,
            'tutor_reports': 0,
            'chat_rooms': 0,
            'messages': 0,
            'notifications': 0,
        }
        self.errors: List[str] = []
        self.verbose = False
        self.created_users: Dict[str, User] = {}

    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear test data before creating new (except users)',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output',
        )

    def handle(self, *args, **options):
        """Main command execution."""
        self.verbose = options['verbose']

        self.print_header("Master Test Data Generation")
        self.print_info("Creating complete test dataset with all roles and dependencies")

        if options['clear']:
            self.clear_test_data()

        # Phase 1: Create/verify users
        self.create_or_verify_users()

        # Phase 2: Create/verify profiles
        self.create_user_profiles()

        # Phase 3: Create subjects
        self.create_subjects()

        # Phase 4: Create data in natural order
        try:
            with transaction.atomic():
                # Get data
                subjects = list(Subject.objects.all())
                if subjects:
                    # Link parent to students
                    self.link_parents_to_students()

                    # Create enrollments
                    enrollments = self.create_subject_enrollments(subjects)

                    # Create materials
                    if enrollments:
                        self.create_materials(enrollments)
                        self.create_material_submissions(enrollments)
                        self.create_study_plans(enrollments)
                        self.create_assignments(enrollments)
                        self.create_reports(enrollments)

                    # Create chat rooms
                    self.create_chat_rooms_and_messages()

                    # Create notifications
                    self.create_notifications()

            self.print_summary()

        except Exception as e:
            self.print_error(f"Critical error: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    def clear_test_data(self):
        """Clear all test data except users and profiles."""
        self.print_section("Clearing test data")

        models_to_clear = [
            (Notification, 'Notifications'),
            (Message, 'Messages'),
            (ChatRoom, 'Chat rooms'),
            (TutorWeeklyReport, 'Tutor reports'),
            (TeacherWeeklyReport, 'Teacher reports'),
            (StudentReport, 'Student reports'),
            (AssignmentSubmission, 'Assignment submissions'),
            (Assignment, 'Assignments'),
            (StudyPlanFile, 'Study plan files'),
            (StudyPlan, 'Study plans'),
            (MaterialSubmission, 'Material submissions'),
            (Material, 'Materials'),
            (SubjectEnrollment, 'Subject enrollments'),
            (TeacherSubject, 'Teacher-subject assignments'),
        ]

        for model, name in models_to_clear:
            count = model.objects.all().count()
            model.objects.all().delete()
            if count > 0:
                self.print_info(f"  Cleared {name}: {count}")

    def create_or_verify_users(self):
        """Create or verify test users with known passwords."""
        self.print_section("Creating/verifying test users")

        test_password = "TestPass123!"

        users_spec = [
            {
                "email": "student@test.com",
                "first_name": "Ivan",
                "last_name": "Sokolov",
                "role": User.Role.STUDENT,
            },
            {
                "email": "student2@test.com",
                "first_name": "Alexander",
                "last_name": "Petrov",
                "role": User.Role.STUDENT,
            },
            {
                "email": "teacher@test.com",
                "first_name": "Peter",
                "last_name": "Ivanov",
                "role": User.Role.TEACHER,
            },
            {
                "email": "teacher2@test.com",
                "first_name": "Elena",
                "last_name": "Kuznetsova",
                "role": User.Role.TEACHER,
            },
            {
                "email": "tutor@test.com",
                "first_name": "Sergey",
                "last_name": "Smirnov",
                "role": User.Role.TUTOR,
            },
            {
                "email": "parent@test.com",
                "first_name": "Maria",
                "last_name": "Sokolova",
                "role": User.Role.PARENT,
            },
            {
                "email": "admin@test.com",
                "first_name": "Admin",
                "last_name": "Administrator",
                "role": User.Role.PARENT,
                "is_staff": True,
                "is_superuser": True,
            },
        ]

        for spec in users_spec:
            try:
                user, created = User.objects.get_or_create(
                    email=spec["email"],
                    defaults={
                        "username": spec["email"],
                        "first_name": spec["first_name"],
                        "last_name": spec["last_name"],
                        "role": spec["role"],
                        "is_active": True,
                        "is_verified": True,
                        "is_staff": spec.get("is_staff", False),
                        "is_superuser": spec.get("is_superuser", False),
                    },
                )

                # Set password
                user.set_password(test_password)
                user.is_active = True
                user.is_verified = True
                user.save()

                self.created_users[spec["email"]] = user

                if created:
                    self.stats['users_created'] += 1
                    status = "NEW"
                else:
                    status = "EXISTS"

                self.print_success(f"  [{status}] {user.get_full_name()} ({user.get_role_display()})")

            except Exception as e:
                self.print_error(f"  Error creating user {spec['email']}: {e}")
                self.errors.append(f"User creation error: {e}")

        self.print_info(f"  Created users: {self.stats['users_created']}")

    def create_user_profiles(self):
        """Create profiles for all users."""
        self.print_section("Creating user profiles")

        for email, user in self.created_users.items():
            try:
                if user.role == User.Role.STUDENT:
                    StudentProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            "grade": "10",
                            "goal": "Prepare for exams",
                            "tutor": self.created_users.get('tutor@test.com'),
                            "parent": self.created_users.get('parent@test.com'),
                        }
                    )
                    self.stats['profiles_created'] += 1
                    self.print_success(f"  StudentProfile created: {user.get_full_name()}")

                elif user.role == User.Role.TEACHER:
                    TeacherProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            "subject": "Math" if "teacher@test.com" == email else "Russian",
                            "experience_years": 5,
                            "bio": "Experienced teacher"
                        }
                    )
                    self.stats['profiles_created'] += 1
                    self.print_success(f"  TeacherProfile created: {user.get_full_name()}")

                elif user.role == User.Role.TUTOR:
                    TeacherProfile.objects.get_or_create(
                        user=user,
                        defaults={
                            "subject": "Tutoring",
                            "experience_years": 3,
                            "bio": "Tutor - coordinates learning"
                        }
                    )
                    self.stats['profiles_created'] += 1
                    self.print_success(f"  TutorProfile created: {user.get_full_name()}")

                elif user.role == User.Role.PARENT:
                    ParentProfile.objects.get_or_create(user=user)
                    self.stats['profiles_created'] += 1
                    self.print_success(f"  ParentProfile created: {user.get_full_name()}")

            except Exception as e:
                self.print_error(f"  Error creating profile for {email}: {e}")
                self.errors.append(f"Profile error: {e}")

    def create_subjects(self):
        """Create test subjects."""
        self.print_section("Creating subjects")

        subjects_data = [
            {'name': 'Mathematics', 'color': '#3B82F6'},
            {'name': 'Physics', 'color': '#10B981'},
            {'name': 'Chemistry', 'color': '#F59E0B'},
            {'name': 'Biology', 'color': '#06B6D4'},
            {'name': 'History', 'color': '#8B5CF6'},
            {'name': 'Russian', 'color': '#EF4444'},
            {'name': 'English', 'color': '#F97316'},
            {'name': 'Literature', 'color': '#EC4899'},
        ]

        for subj_data in subjects_data:
            try:
                subject, created = Subject.objects.get_or_create(
                    name=subj_data['name'],
                    defaults={'color': subj_data['color']}
                )

                if created:
                    self.stats['subjects_created'] += 1
                    self.print_success(f"  Created: {subject.name}")

                    # Assign to teachers
                    for teacher_email in ['teacher@test.com', 'teacher2@test.com']:
                        teacher = self.created_users.get(teacher_email)
                        if teacher:
                            TeacherSubject.objects.get_or_create(
                                teacher=teacher,
                                subject=subject,
                                defaults={'is_active': True}
                            )
                            self.stats['teacher_subjects'] += 1

            except Exception as e:
                self.print_error(f"  Error creating subject: {e}")
                self.errors.append(f"Subject error: {e}")

    def link_parents_to_students(self):
        """Link parent to students via StudentProfile."""
        self.print_section("Linking parents to students")

        parent = self.created_users.get('parent@test.com')
        tutor = self.created_users.get('tutor@test.com')

        if not parent or not tutor:
            self.print_warning("  Parent or tutor not found")
            return

        for email in ['student@test.com', 'student2@test.com']:
            student = self.created_users.get(email)
            if not student:
                continue

            try:
                profile = StudentProfile.objects.get(user=student)
                profile.parent = parent
                profile.tutor = tutor
                profile.save()
                self.stats['parent_links'] += 1
                self.print_success(f"  Linked: {student.get_full_name()} → {parent.get_full_name()}")

            except Exception as e:
                self.print_error(f"  Error linking parent: {e}")
                self.errors.append(f"Parent link error: {e}")

    def create_subject_enrollments(self, subjects: List[Subject]) -> List[SubjectEnrollment]:
        """Create subject enrollments for students."""
        self.print_section("Creating subject enrollments")

        enrollments = []
        tutor = self.created_users.get('tutor@test.com')

        if not tutor:
            return []

        # Student 1: 3 subjects
        student1 = self.created_users.get('student@test.com')
        teacher1 = self.created_users.get('teacher@test.com')

        if student1 and teacher1:
            for subject in subjects[:3]:
                try:
                    TeacherSubject.objects.get_or_create(
                        teacher=teacher1,
                        subject=subject
                    )

                    enrollment, created = SubjectEnrollment.objects.get_or_create(
                        student=student1,
                        subject=subject,
                        teacher=teacher1,
                        defaults={
                            'assigned_by': tutor,
                            'is_active': True,
                            'enrolled_at': timezone.now() - timedelta(days=30),
                        }
                    )

                    if created:
                        enrollments.append(enrollment)
                        self.stats['enrollments'] += 1
                        self.print_success(
                            f"  {student1.get_full_name()} → {subject.name} "
                            f"({teacher1.get_full_name()})"
                        )

                except Exception as e:
                    self.print_error(f"  Error creating enrollment: {e}")
                    self.errors.append(f"Enrollment error: {e}")

        # Student 2: 2 subjects
        student2 = self.created_users.get('student2@test.com')
        teacher2 = self.created_users.get('teacher2@test.com')

        if student2 and teacher2:
            for subject in subjects[3:5]:
                try:
                    TeacherSubject.objects.get_or_create(
                        teacher=teacher2,
                        subject=subject
                    )

                    enrollment, created = SubjectEnrollment.objects.get_or_create(
                        student=student2,
                        subject=subject,
                        teacher=teacher2,
                        defaults={
                            'assigned_by': tutor,
                            'is_active': True,
                            'enrolled_at': timezone.now() - timedelta(days=45),
                        }
                    )

                    if created:
                        enrollments.append(enrollment)
                        self.stats['enrollments'] += 1
                        self.print_success(
                            f"  {student2.get_full_name()} → {subject.name} "
                            f"({teacher2.get_full_name()})"
                        )

                except Exception as e:
                    self.print_error(f"  Error creating enrollment: {e}")
                    self.errors.append(f"Enrollment error: {e}")

        return enrollments

    def create_materials(self, enrollments: List[SubjectEnrollment]):
        """Create test materials."""
        self.print_section("Creating materials")

        titles = [
            "Introduction to Course",
            "Core Concepts",
            "Practical Examples",
            "Theory",
            "Additional Materials",
        ]

        for enrollment in enrollments:
            for i in range(random.randint(3, 5)):
                try:
                    title = f"{titles[i % len(titles)]} - {enrollment.subject.name}"

                    Material.objects.create(
                        subject=enrollment.subject,
                        author=enrollment.teacher,
                        title=title,
                        description=f"Material on {title}",
                        content=f"Detailed content for {title}",
                        type=random.choice(['lesson', 'presentation', 'document']),
                        status=random.choice(['active', 'active', 'draft']),
                        created_at=timezone.now() - timedelta(days=random.randint(1, 30)),
                    )

                    self.stats['materials'] += 1

                    if self.verbose:
                        self.print_success(f"  Material created: {title}")

                except Exception as e:
                    self.print_error(f"  Error creating material: {e}")
                    self.errors.append(f"Material error: {e}")

        self.print_info(f"  Created materials: {self.stats['materials']}")

    def create_material_submissions(self, enrollments: List[SubjectEnrollment]):
        """Create student submissions for materials."""
        self.print_section("Creating material submissions")

        for enrollment in enrollments:
            materials = Material.objects.filter(
                subject=enrollment.subject,
                status='active'
            )[:3]

            for material in materials:
                try:
                    submission = MaterialSubmission.objects.create(
                        student=enrollment.student,
                        material=material,
                        status=random.choice(['submitted', 'reviewed', 'returned']),
                        submitted_at=timezone.now() - timedelta(days=random.randint(1, 20)),
                        submission_text=f"Student work for {material.title}",
                    )

                    # Add file
                    submission.submission_file = self.create_test_pdf(f"Work: {material.title[:30]}")
                    submission.save()

                    self.stats['material_submissions'] += 1

                except Exception as e:
                    self.print_error(f"  Error creating submission: {e}")
                    self.errors.append(f"Submission error: {e}")

        self.print_info(f"  Created submissions: {self.stats['material_submissions']}")

    def create_study_plans(self, enrollments: List[SubjectEnrollment]):
        """Create study plans for students."""
        self.print_section("Creating study plans")

        weeks = [
            timezone.now() - timedelta(weeks=1),
            timezone.now(),
            timezone.now() + timedelta(weeks=1),
        ]

        for enrollment in enrollments:
            for week_start in weeks:
                try:
                    week_end = week_start + timedelta(days=6)

                    plan = StudyPlan.objects.create(
                        student=enrollment.student,
                        teacher=enrollment.teacher,
                        subject=enrollment.subject,
                        enrollment=enrollment,
                        title=f"Plan {enrollment.subject.name} - {week_start.strftime('%d.%m.%Y')}",
                        content=f"Study plan for {enrollment.student.get_full_name()}",
                        week_start_date=week_start.date(),
                        week_end_date=week_end.date(),
                        status='sent',
                        created_at=week_start - timedelta(days=2),
                        sent_at=week_start - timedelta(days=1),
                    )

                    self.stats['study_plans'] += 1

                    # Add files
                    for i in range(random.randint(1, 2)):
                        pdf_file = self.create_test_pdf(f"Plan: {enrollment.subject.name}")

                        StudyPlanFile.objects.create(
                            study_plan=plan,
                            file=pdf_file,
                            name=f"Plan {week_start.strftime('%d.%m')}.pdf",
                            file_size=len(pdf_file.read()),
                            uploaded_by=enrollment.teacher,
                            created_at=plan.created_at,
                        )

                        self.stats['study_plan_files'] += 1

                except Exception as e:
                    self.print_error(f"  Error creating study plan: {e}")
                    self.errors.append(f"Study plan error: {e}")

        self.print_info(f"  Created plans: {self.stats['study_plans']}, files: {self.stats['study_plan_files']}")

    def create_assignments(self, enrollments: List[SubjectEnrollment]):
        """Create homework assignments."""
        self.print_section("Creating assignments")

        titles = [
            "Control Work №1",
            "Practical Assignment",
            "Test",
        ]

        for enrollment in enrollments:
            for i, title in enumerate(titles):
                try:
                    deadline_days = [-5, 3, 10][i]
                    deadline = timezone.now() + timedelta(days=deadline_days)

                    assignment = Assignment.objects.create(
                        author=enrollment.teacher,
                        title=f"{title} - {enrollment.subject.name}",
                        description=f"Assignment description",
                        instructions="Complete and submit results",
                        type=Assignment.Type.HOMEWORK,
                        status=Assignment.Status.PUBLISHED,
                        start_date=deadline - timedelta(days=7),
                        due_date=deadline,
                        max_score=100,
                    )

                    assignment.assigned_to.add(enrollment.student)

                    self.stats['assignments'] += 1

                    # Create submission if deadline passed
                    if deadline_days <= 3:
                        submission = AssignmentSubmission.objects.create(
                            assignment=assignment,
                            student=enrollment.student,
                            content=f"Student answer for {title}",
                        )

                        if deadline_days < 0:
                            submission.score = Decimal(str(random.randint(7, 10)))
                            submission.teacher_comment = "Well done!"
                            submission.graded_at = deadline + timedelta(days=1)
                            submission.save()

                        # Add file
                        submission.file = self.create_test_pdf(f"Work: {assignment.title[:30]}")
                        submission.save()

                        self.stats['assignment_submissions'] += 1

                except Exception as e:
                    self.print_error(f"  Error creating assignment: {e}")
                    self.errors.append(f"Assignment error: {e}")

        self.print_info(
            f"  Created assignments: {self.stats['assignments']}, "
            f"submissions: {self.stats['assignment_submissions']}"
        )

    def create_reports(self, enrollments: List[SubjectEnrollment]):
        """Create reports between teachers, tutors, and parents."""
        self.print_section("Creating reports")

        tutor = self.created_users.get('tutor@test.com')
        parent = self.created_users.get('parent@test.com')

        if not tutor or not parent:
            return

        # Teacher reports
        for enrollment in enrollments[:3]:
            try:
                period_start = timezone.now() - timedelta(days=7)

                StudentReport.objects.get_or_create(
                    teacher=enrollment.teacher,
                    student=enrollment.student,
                    period_start=period_start,
                    period_end=timezone.now(),
                    defaults={
                        'parent': parent,
                        'title': f"Report on {enrollment.student.get_full_name()}",
                        'description': 'Weekly report',
                        'content': {'subject': enrollment.subject.name},
                        'status': random.choice(['sent', 'read']),
                        'overall_grade': '4',
                        'progress_percentage': random.randint(60, 90),
                        'sent_at': timezone.now() - timedelta(days=1),
                    }
                )

                self.stats['student_reports'] += 1

                # Teacher weekly report
                TeacherWeeklyReport.objects.create(
                    teacher=enrollment.teacher,
                    student=enrollment.student,
                    tutor=tutor,
                    subject=enrollment.subject,
                    week_start=(timezone.now() - timedelta(days=7)).date(),
                    week_end=timezone.now().date(),
                    title=f"Weekly report: {enrollment.subject.name}",
                    summary=f"Report for {enrollment.student.get_full_name()}",
                    academic_progress="Good progress",
                    performance_notes="Completed all homework",
                    achievements="Good control work results",
                    recommendations="Continue current pace",
                    assignments_completed=random.randint(3, 5),
                    assignments_total=5,
                    average_score=Decimal(str(random.randint(70, 95) / 10)),
                    attendance_percentage=random.randint(80, 100),
                    status=random.choice(['sent', 'read']),
                    sent_at=timezone.now() - timedelta(hours=12),
                )

                self.stats['teacher_reports'] += 1

            except Exception as e:
                self.print_error(f"  Error creating teacher report: {e}")
                self.errors.append(f"Teacher report error: {e}")

        # Tutor reports to parent
        for enrollment in enrollments[:2]:
            try:
                week_start = (timezone.now() - timedelta(days=7)).date()

                TutorWeeklyReport.objects.get_or_create(
                    tutor=tutor,
                    student=enrollment.student,
                    week_start=week_start,
                    defaults={
                        'parent': parent,
                        'week_end': timezone.now().date(),
                        'title': f"Weekly report on {enrollment.student.get_full_name()}",
                        'summary': f"Tutor report for week",
                        'academic_progress': "Good progress on all subjects",
                        'behavior_notes': "Actively participates in lessons",
                        'achievements': "Good results",
                        'concerns': "Minor difficulties",
                        'recommendations': "Continue regular lessons",
                        'attendance_days': random.randint(5, 7),
                        'total_days': 7,
                        'progress_percentage': random.randint(65, 85),
                        'status': random.choice(['sent', 'read']),
                        'sent_at': timezone.now() - timedelta(hours=6),
                    }
                )

                self.stats['tutor_reports'] += 1

            except Exception as e:
                self.print_error(f"  Error creating tutor report: {e}")
                self.errors.append(f"Tutor report error: {e}")

        self.print_info(
            f"  Created reports: student={self.stats['student_reports']}, "
            f"teacher={self.stats['teacher_reports']}, tutor={self.stats['tutor_reports']}"
        )

    def create_chat_rooms_and_messages(self):
        """Create chat rooms and messages."""
        self.print_section("Creating chat rooms and messages")

        # Chat pairs
        pairs = [
            ('student@test.com', 'teacher@test.com'),
            ('student@test.com', 'tutor@test.com'),
            ('teacher@test.com', 'tutor@test.com'),
            ('tutor@test.com', 'parent@test.com'),
            ('student2@test.com', 'teacher2@test.com'),
        ]

        messages = [
            "Hello!",
            "How's the learning going?",
            "Thanks for the materials",
            "When is the next lesson?",
            "I submitted my homework",
            "Please review my work",
            "I have a question",
            "All clear, thanks!",
            "Great work!",
            "Need extra consultation",
        ]

        for email1, email2 in pairs:
            user1 = self.created_users.get(email1)
            user2 = self.created_users.get(email2)

            if not user1 or not user2:
                continue

            try:
                room = ChatRoom.objects.create(
                    created_by=user1,
                    name=f"Chat: {user1.get_full_name()} - {user2.get_full_name()}",
                    type="direct"
                )
                room.participants.add(user1, user2)

                self.stats['chat_rooms'] += 1

                # Create messages
                for _ in range(random.randint(5, 10)):
                    sender = random.choice([user1, user2])

                    message = Message.objects.create(
                        room=room,
                        sender=sender,
                        content=random.choice(messages),
                        created_at=timezone.now() - timedelta(
                            hours=random.randint(1, 72)
                        ),
                    )

                    # Occasionally add file
                    if random.random() < 0.2:
                        message.file = self.create_test_pdf(
                            f"File: {user1.get_full_name()} - {user2.get_full_name()}"
                        )
                        message.save()

                    self.stats['messages'] += 1

                if self.verbose:
                    self.print_success(
                        f"  Chat: {user1.get_full_name()} ↔ {user2.get_full_name()}"
                    )

            except Exception as e:
                self.print_error(f"  Error creating chat: {e}")
                self.errors.append(f"Chat error: {e}")

        self.print_info(
            f"  Created chat rooms: {self.stats['chat_rooms']}, "
            f"messages: {self.stats['messages']}"
        )

    def create_notifications(self):
        """Create notifications for all users."""
        self.print_section("Creating notifications")

        general_notifs = [
            ('info', 'New material available'),
            ('success', 'Work reviewed'),
            ('warning', 'Deadline approaching'),
            ('error', 'Deadline missed'),
            ('info', 'New message in chat'),
        ]

        parent_notifs = [
            ('info', 'New tutor report'),
            ('info', 'Teacher report on child'),
            ('warning', 'Upcoming payment'),
            ('success', 'Payment received'),
            ('info', 'Child progress update'),
        ]

        for email, user in self.created_users.items():
            notifs = parent_notifs if user.role == User.Role.PARENT else general_notifs
            num_notifs = random.randint(8, 12) if user.role == User.Role.PARENT else random.randint(5, 8)

            for _ in range(num_notifs):
                try:
                    notif_type, title = random.choice(notifs)

                    Notification.objects.create(
                        recipient=user,
                        title=title,
                        message=f"Details for {user.get_full_name()}",
                        type=notif_type,
                        priority=Notification.Priority.NORMAL,
                    )

                    self.stats['notifications'] += 1

                except Exception as e:
                    self.print_error(f"  Error creating notification: {e}")
                    self.errors.append(f"Notification error: {e}")

        self.print_info(f"  Created notifications: {self.stats['notifications']}")

    def create_test_pdf(self, title: str) -> SimpleUploadedFile:
        """Create a test PDF file."""
        buffer = io.BytesIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, height - 50, title)

        p.setFont("Helvetica", 10)
        p.drawString(50, height - 70, f"Created: {datetime.now().strftime('%d.%m.%Y %H:%M')}")

        p.setFont("Helvetica", 12)
        y = height - 120
        lines = [
            "Test document for the system.",
            "",
            "Contents:",
            "- Section 1: Introduction",
            "- Section 2: Main part",
            "- Section 3: Conclusion",
        ]

        for line in lines:
            p.drawString(50, y, line)
            y -= 20

        p.showPage()
        p.save()

        pdf_data = buffer.getvalue()
        buffer.close()

        filename = f"{title[:30].replace(' ', '_')}.pdf"

        return SimpleUploadedFile(
            filename,
            pdf_data,
            content_type='application/pdf'
        )

    def print_summary(self):
        """Print final statistics."""
        self.print_section("FINAL STATISTICS")

        stats_table = [
            ("Users created", self.stats['users_created']),
            ("User profiles", self.stats['profiles_created']),
            ("Subjects", self.stats['subjects_created']),
            ("Teacher-subject links", self.stats['teacher_subjects']),
            ("Parent-student links", self.stats['parent_links']),
            ("Subject enrollments", self.stats['enrollments']),
            ("Materials", self.stats['materials']),
            ("Material submissions", self.stats['material_submissions']),
            ("Study plans", self.stats['study_plans']),
            ("Study plan files", self.stats['study_plan_files']),
            ("Assignments", self.stats['assignments']),
            ("Assignment submissions", self.stats['assignment_submissions']),
            ("Student reports", self.stats['student_reports']),
            ("Teacher reports", self.stats['teacher_reports']),
            ("Tutor reports", self.stats['tutor_reports']),
            ("Chat rooms", self.stats['chat_rooms']),
            ("Chat messages", self.stats['messages']),
            ("Notifications", self.stats['notifications']),
        ]

        total = sum(count for _, count in stats_table)

        max_label_len = max(len(label) for label, _ in stats_table)

        for label, count in stats_table:
            self.stdout.write(
                f"  {label.ljust(max_label_len)} : "
                f"{Colors.GREEN}{count:>5}{Colors.END}"
            )

        self.stdout.write(
            f"\n  {'─' * (max_label_len + 10)}\n"
            f"  {'TOTAL'.ljust(max_label_len)} : "
            f"{Colors.BOLD}{Colors.GREEN}{total:>5}{Colors.END}\n"
        )

        if self.errors:
            self.print_section("Errors")
            for error in self.errors[:10]:
                self.print_error(f"  {error}")

            if len(self.errors) > 10:
                self.print_warning(f"  ... and {len(self.errors) - 10} more errors")

        self.print_success(
            f"\nTest dataset created successfully!\n"
            f"Total objects created: {total}"
        )

        self.print_section("TEST CREDENTIALS")
        self.stdout.write("\n" + "─" * 80)
        for email, user in sorted(self.created_users.items()):
            self.stdout.write(
                f"  {user.get_full_name():<30} | "
                f"{email:<25} | "
                f"Password: TestPass123!"
            )
        self.stdout.write("─" * 80 + "\n")

    # Utility methods for colored output
    def print_header(self, text: str):
        """Print header."""
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
        """Print section."""
        self.stdout.write(
            f"\n{Colors.BOLD}{Colors.CYAN}{text}{Colors.END}\n"
        )

    def print_success(self, text: str):
        """Print success message."""
        self.stdout.write(f"{Colors.GREEN}{text}{Colors.END}")

    def print_info(self, text: str):
        """Print info message."""
        self.stdout.write(f"{Colors.BLUE}{text}{Colors.END}")

    def print_warning(self, text: str):
        """Print warning message."""
        self.stdout.write(f"{Colors.YELLOW}{text}{Colors.END}")

    def print_error(self, text: str):
        """Print error message."""
        self.stdout.write(f"{Colors.RED}{text}{Colors.END}")
