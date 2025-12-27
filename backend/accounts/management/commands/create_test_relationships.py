"""
Management command to create relationships between test users.

Creates:
1. SubjectEnrollment between student@test.com and teacher@test.com
2. Direct chat room between them for messaging
3. Links student with tutor in StudentProfile
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from accounts.models import User, StudentProfile, TutorProfile
from materials.models import Subject, SubjectEnrollment, TeacherSubject
from chat.models import ChatRoom


class Command(BaseCommand):
    help = "Creates relationships between test users so they can chat"

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("Creating test user relationships..."))
        self.stdout.write("=" * 80 + "\n")

        # Get test users
        try:
            student = User.objects.get(email="student@test.com")
            teacher = User.objects.get(email="teacher@test.com")
            tutor = User.objects.get(email="tutor@test.com")
            parent = User.objects.get(email="parent@test.com")
        except User.DoesNotExist as e:
            self.stdout.write(self.style.ERROR(
                f"Test user not found: {e}\n"
                f"Run 'python manage.py create_test_users_all' first."
            ))
            return

        self.stdout.write(f"Found users:")
        self.stdout.write(f"  Student: {student.email} (id={student.id})")
        self.stdout.write(f"  Teacher: {teacher.email} (id={teacher.id})")
        self.stdout.write(f"  Tutor:   {tutor.email} (id={tutor.id})")
        self.stdout.write(f"  Parent:  {parent.email} (id={parent.id})")

        # 1. Ensure StudentProfile exists and has tutor/parent links
        student_profile, created = StudentProfile.objects.get_or_create(
            user=student,
            defaults={
                "grade": "9",
                "goal": "Test goal",
                "tutor": tutor,
                "parent": parent,
            }
        )
        if not created:
            # Update existing profile
            student_profile.tutor = tutor
            student_profile.parent = parent
            student_profile.save(update_fields=["tutor", "parent"])
            self.stdout.write(f"  Updated StudentProfile: tutor={tutor.email}, parent={parent.email}")
        else:
            self.stdout.write(f"  Created StudentProfile with tutor={tutor.email}, parent={parent.email}")

        # 2. Create or get Subject
        math_subject, created = Subject.objects.get_or_create(
            name="Mathematics",
            defaults={
                "description": "Test math subject",
                "color": "#3B82F6"
            }
        )
        if created:
            self.stdout.write(f"\n  Created Subject: {math_subject.name}")
        else:
            self.stdout.write(f"\n  Found Subject: {math_subject.name}")

        # 3. Link teacher to subject via TeacherSubject
        teacher_subject, ts_created = TeacherSubject.objects.get_or_create(
            teacher=teacher,
            subject=math_subject,
            defaults={"is_active": True}
        )
        if ts_created:
            self.stdout.write(f"  Created TeacherSubject: {teacher.email} -> {math_subject.name}")
        else:
            self.stdout.write(f"  Found TeacherSubject: {teacher.email} -> {math_subject.name}")

        # 4. Create SubjectEnrollment (student-subject-teacher)
        enrollment, enr_created = SubjectEnrollment.objects.get_or_create(
            student=student,
            subject=math_subject,
            teacher=teacher,
            defaults={
                "assigned_by": tutor,
                "is_active": True
            }
        )
        if enr_created:
            self.stdout.write(f"\n  Created SubjectEnrollment:")
            self.stdout.write(f"    Student: {student.email}")
            self.stdout.write(f"    Subject: {math_subject.name}")
            self.stdout.write(f"    Teacher: {teacher.email}")
        else:
            self.stdout.write(f"\n  Found existing SubjectEnrollment (id={enrollment.id})")

        # 5. Create Direct Chat between student and teacher
        direct_chat_name = f"Chat: {student.get_full_name()} - {teacher.get_full_name()}"

        # Check if direct chat already exists between these users
        existing_direct_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.DIRECT,
            participants=student
        ).filter(participants=teacher).first()

        if existing_direct_chat:
            self.stdout.write(f"\n  Found existing direct chat: {existing_direct_chat.name}")
            direct_chat = existing_direct_chat
        else:
            direct_chat = ChatRoom.objects.create(
                name=direct_chat_name,
                description=f"Direct chat between {student.email} and {teacher.email}",
                type=ChatRoom.Type.DIRECT,
                created_by=teacher
            )
            direct_chat.participants.add(student, teacher)
            self.stdout.write(f"\n  Created direct chat: {direct_chat.name}")

        # 6. Create Forum chat for the enrollment (if not exists)
        forum_chat_name = f"Forum: {math_subject.name} - {student.get_full_name()}"

        existing_forum = ChatRoom.objects.filter(
            type=ChatRoom.Type.FORUM_SUBJECT,
            enrollment=enrollment
        ).first()

        if existing_forum:
            self.stdout.write(f"  Found existing forum chat: {existing_forum.name}")
        else:
            forum_chat = ChatRoom.objects.create(
                name=forum_chat_name,
                description=f"Forum for {math_subject.name} between {student.email} and {teacher.email}",
                type=ChatRoom.Type.FORUM_SUBJECT,
                enrollment=enrollment,
                created_by=teacher
            )
            forum_chat.participants.add(student, teacher)
            # Add tutor if exists
            if tutor:
                forum_chat.participants.add(tutor)
            self.stdout.write(f"  Created forum chat: {forum_chat.name}")

        # 7. Create Direct Chat between student and tutor
        student_tutor_chat_name = f"Chat: {student.get_full_name()} - {tutor.get_full_name()}"

        existing_tutor_chat = ChatRoom.objects.filter(
            type=ChatRoom.Type.DIRECT,
            participants=student
        ).filter(participants=tutor).first()

        if existing_tutor_chat:
            self.stdout.write(f"  Found existing tutor chat: {existing_tutor_chat.name}")
        else:
            tutor_chat = ChatRoom.objects.create(
                name=student_tutor_chat_name,
                description=f"Direct chat between {student.email} and {tutor.email}",
                type=ChatRoom.Type.DIRECT,
                created_by=tutor
            )
            tutor_chat.participants.add(student, tutor)
            self.stdout.write(f"  Created tutor chat: {student_tutor_chat_name}")

        # Summary
        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("RELATIONSHIPS CREATED SUCCESSFULLY!"))
        self.stdout.write("=" * 80)

        # Show contacts for each user
        self.stdout.write("\nContacts for each user:")

        for user in [student, teacher, tutor]:
            rooms = ChatRoom.objects.filter(participants=user, is_active=True)
            contacts = set()
            for room in rooms:
                for participant in room.participants.exclude(id=user.id):
                    contacts.add(participant.email)
            self.stdout.write(f"\n  {user.email}:")
            for contact in sorted(contacts):
                self.stdout.write(f"    - {contact}")

        self.stdout.write("\n" + "=" * 80)
        self.stdout.write(self.style.SUCCESS("Now users can chat with each other!"))
        self.stdout.write("=" * 80 + "\n")
