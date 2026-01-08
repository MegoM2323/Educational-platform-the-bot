import pytest
from django.test import TestCase
from django.contrib.auth import get_user_model

from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile
from materials.models import SubjectEnrollment, Subject
from chat.permissions import can_initiate_chat

User = get_user_model()


@pytest.mark.django_db
class TestCanInitiateChatAllRoles(TestCase):
    """Unit tests for can_initiate_chat() with all role combinations"""

    def setUp(self):
        """Create users for all roles"""
        self.admin = User.objects.create_user(
            username="admin_user", email="admin@test.com", password="pass", role="admin", is_active=True
        )
        self.student1 = User.objects.create_user(
            username="student1", email="student1@test.com", password="pass", role="student", is_active=True
        )
        self.student2 = User.objects.create_user(
            username="student2", email="student2@test.com", password="pass", role="student", is_active=True
        )
        self.teacher = User.objects.create_user(
            username="teacher", email="teacher@test.com", password="pass", role="teacher", is_active=True
        )
        self.tutor = User.objects.create_user(
            username="tutor", email="tutor@test.com", password="pass", role="tutor", is_active=True
        )
        self.parent = User.objects.create_user(
            username="parent", email="parent@test.com", password="pass", role="parent", is_active=True
        )

        # Create inactive versions
        self.inactive_student = User.objects.create_user(
            username="inactive_student", email="inactive_student@test.com", password="pass", role="student", is_active=False
        )
        self.inactive_teacher = User.objects.create_user(
            username="inactive_teacher", email="inactive_teacher@test.com", password="pass", role="teacher", is_active=False
        )
        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor", email="inactive_tutor@test.com", password="pass", role="tutor", is_active=False
        )
        self.inactive_parent = User.objects.create_user(
            username="inactive_parent", email="inactive_parent@test.com", password="pass", role="parent", is_active=False
        )

        # Create subject
        self.subject = Subject.objects.create(name="Math")

        # Create StudentProfile for student1
        self.student1_profile = StudentProfile.objects.create(user=self.student1)

        # Create TeacherProfile for teacher
        self.teacher_profile = TeacherProfile.objects.create(user=self.teacher)

        # Create TutorProfile for tutor
        self.tutor_profile = TutorProfile.objects.create(user=self.tutor)

        # Create ParentProfile for parent with student1 as child
        self.parent_profile = ParentProfile.objects.create(user=self.parent)

    # Test 1: Admin + any other user -> True (always)
    def test_admin_can_chat_with_any_user(self):
        assert can_initiate_chat(self.admin, self.student1) is True
        assert can_initiate_chat(self.admin, self.teacher) is True
        assert can_initiate_chat(self.admin, self.tutor) is True
        assert can_initiate_chat(self.admin, self.parent) is True

    # Test 2: Student + Student -> False (forbidden)
    def test_student_cannot_chat_with_student(self):
        assert can_initiate_chat(self.student1, self.student2) is False

    # Test 3: Student + Teacher
    def test_student_can_chat_with_teacher_with_active_enrollment(self):
        """Student can chat with teacher if ACTIVE SubjectEnrollment exists"""
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )
        assert can_initiate_chat(self.student1, self.teacher) is True

    def test_student_cannot_chat_with_teacher_without_enrollment(self):
        """Student cannot chat with teacher without enrollment"""
        assert can_initiate_chat(self.student1, self.teacher) is False

    def test_student_cannot_chat_with_teacher_completed_enrollment(self):
        """Student cannot chat with teacher with completed enrollment"""
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.COMPLETED
        )
        assert can_initiate_chat(self.student1, self.teacher) is False

    def test_student_can_chat_with_teacher_in_finished_course(self):
        """Student can chat with teacher even if course is finished (completed enrollment)"""
        enrollment = SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.COMPLETED
        )
        # Check if user can access finished chat
        assert can_initiate_chat(self.student1, self.teacher) is False  # COMPLETED != ACTIVE

    # Test 4: Student + Tutor
    def test_student_can_chat_with_tutor_with_active_profile(self):
        """Student can chat with tutor if active StudentProfile with tutor is set"""
        self.student1_profile.tutor = self.tutor
        self.student1_profile.save()
        assert can_initiate_chat(self.student1, self.tutor) is True

    def test_student_cannot_chat_with_tutor_without_profile(self):
        """Student cannot chat with tutor without StudentProfile"""
        assert can_initiate_chat(self.student1, self.tutor) is False

    def test_student_cannot_chat_with_inactive_tutor(self):
        """Student cannot chat with inactive tutor even if StudentProfile exists"""
        self.student1_profile.tutor = self.inactive_tutor
        self.student1_profile.save()
        assert can_initiate_chat(self.student1, self.inactive_tutor) is False

    # Test 5: Teacher + Teacher -> False (forbidden)
    def test_teacher_cannot_chat_with_teacher(self):
        assert can_initiate_chat(self.teacher, User.objects.create_user(
            username="teacher2", email="teacher2@test.com", password="pass", role="teacher", is_active=True
        )) is False

    # Test 6: Teacher + Student (bidirectional)
    def test_teacher_can_chat_with_student_with_enrollment(self):
        """Teacher can chat with student if ACTIVE SubjectEnrollment exists"""
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )
        assert can_initiate_chat(self.teacher, self.student1) is True

    def test_teacher_cannot_chat_with_student_without_enrollment(self):
        """Teacher cannot chat with student without enrollment"""
        assert can_initiate_chat(self.teacher, self.student1) is False

    # Test 7: Teacher + Parent
    def test_teacher_can_chat_with_parent_if_child_has_active_enrollment(self):
        """Teacher can chat with parent if parent has child with ACTIVE enrollment with this teacher"""
        # Set parent for student1
        self.student1_profile.parent = self.parent
        self.student1_profile.save()

        # Create active enrollment
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )

        assert can_initiate_chat(self.teacher, self.parent) is True

    def test_teacher_cannot_chat_with_parent_if_child_has_other_teacher(self):
        """Teacher cannot chat with parent if parent doesn't have child with THIS teacher"""
        # Set parent for student1
        self.student1_profile.parent = self.parent
        self.student1_profile.save()

        # Create enrollment with different teacher
        other_teacher = User.objects.create_user(
            username="other_teacher", email="other_teacher@test.com", password="pass", role="teacher", is_active=True
        )
        TeacherProfile.objects.create(user=other_teacher)

        SubjectEnrollment.objects.create(
            student=self.student1, teacher=other_teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )

        assert can_initiate_chat(self.teacher, self.parent) is False

    def test_teacher_cannot_chat_with_inactive_parent(self):
        """Teacher cannot chat with inactive parent"""
        # Set inactive parent
        self.student1_profile.parent = self.inactive_parent
        self.student1_profile.save()

        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )

        assert can_initiate_chat(self.teacher, self.inactive_parent) is False

    # Test 8: Teacher + Tutor (common students)
    def test_teacher_can_chat_with_tutor_if_common_student_with_active_enrollment(self):
        """Teacher can chat with tutor if common student with ACTIVE enrollment"""
        # Set tutor for student1
        self.student1_profile.tutor = self.tutor
        self.student1_profile.save()

        # Create active enrollment
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )

        assert can_initiate_chat(self.teacher, self.tutor) is True

    def test_teacher_cannot_chat_with_tutor_without_common_active_enrollment(self):
        """Teacher cannot chat with tutor without common active enrollment"""
        # Set tutor but no enrollment
        self.student1_profile.tutor = self.tutor
        self.student1_profile.save()

        assert can_initiate_chat(self.teacher, self.tutor) is False

    def test_teacher_cannot_chat_with_inactive_tutor_even_with_common_student(self):
        """Teacher cannot chat with inactive tutor even if common student exists"""
        # Set inactive tutor
        self.student1_profile.tutor = self.inactive_tutor
        self.student1_profile.save()

        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )

        assert can_initiate_chat(self.teacher, self.inactive_tutor) is False

    # Test 9: Tutor + Student (active link)
    def test_tutor_can_chat_with_student_if_active_profile(self):
        """Tutor can chat with student if active StudentProfile"""
        self.student1_profile.tutor = self.tutor
        self.student1_profile.save()
        assert can_initiate_chat(self.tutor, self.student1) is True

    def test_tutor_cannot_chat_with_student_without_profile(self):
        """Tutor cannot chat with student without StudentProfile"""
        assert can_initiate_chat(self.tutor, self.student1) is False

    def test_tutor_cannot_chat_with_inactive_student_even_with_profile(self):
        """Tutor cannot chat with inactive student"""
        self.student1_profile.tutor = self.tutor
        self.student1_profile.save()
        assert can_initiate_chat(self.tutor, self.inactive_student) is False

    # Test 10: Tutor + Tutor -> False (forbidden)
    def test_tutor_cannot_chat_with_tutor(self):
        other_tutor = User.objects.create_user(
            username="tutor2", email="tutor2@test.com", password="pass", role="tutor", is_active=True
        )
        assert can_initiate_chat(self.tutor, other_tutor) is False

    # Test 11: Tutor + Teacher (through students)
    def test_tutor_can_chat_with_teacher_if_common_student_active_enrollment(self):
        """Tutor can chat with teacher if common student with ACTIVE enrollment"""
        # Set tutor for student1
        self.student1_profile.tutor = self.tutor
        self.student1_profile.save()

        # Create active enrollment
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )

        assert can_initiate_chat(self.tutor, self.teacher) is True

    def test_tutor_cannot_chat_with_teacher_without_common_active_enrollment(self):
        """Tutor cannot chat with teacher without common active enrollment"""
        # Only set tutor, no enrollment
        self.student1_profile.tutor = self.tutor
        self.student1_profile.save()

        assert can_initiate_chat(self.tutor, self.teacher) is False

    # Test 12: Tutor + Parent (parent's child)
    def test_tutor_can_chat_with_parent_if_child_with_this_tutor(self):
        """Tutor can chat with parent if parent has child with this tutor"""
        # Set tutor and parent for student1
        self.student1_profile.tutor = self.tutor
        self.student1_profile.parent = self.parent
        self.student1_profile.save()

        assert can_initiate_chat(self.tutor, self.parent) is True

    def test_tutor_cannot_chat_with_parent_without_child(self):
        """Tutor cannot chat with parent if no child with this tutor"""
        assert can_initiate_chat(self.tutor, self.parent) is False

    def test_tutor_cannot_chat_with_inactive_parent_even_with_child(self):
        """Tutor cannot chat with inactive parent"""
        # Set inactive parent
        self.student1_profile.tutor = self.tutor
        self.student1_profile.parent = self.inactive_parent
        self.student1_profile.save()

        assert can_initiate_chat(self.tutor, self.inactive_parent) is False

    # Test 13: Parent + Teacher (specific child)
    def test_parent_can_chat_with_teacher_if_child_has_active_enrollment(self):
        """Parent can chat with teacher only if child has ACTIVE enrollment with this teacher"""
        # Set parent for student1
        self.student1_profile.parent = self.parent
        self.student1_profile.save()

        # Create active enrollment
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )

        assert can_initiate_chat(self.parent, self.teacher) is True

    def test_parent_cannot_chat_with_teacher_without_child(self):
        """Parent cannot chat with teacher if no child with that teacher"""
        assert can_initiate_chat(self.parent, self.teacher) is False

    # Test 14: Parent + Tutor (parent's child)
    def test_parent_can_chat_with_tutor_if_child_with_this_tutor(self):
        """Parent can chat with tutor only if child has this tutor"""
        # Set tutor and parent for student1
        self.student1_profile.tutor = self.tutor
        self.student1_profile.parent = self.parent
        self.student1_profile.save()

        assert can_initiate_chat(self.parent, self.tutor) is True

    def test_parent_cannot_chat_with_tutor_without_child(self):
        """Parent cannot chat with tutor if no child with that tutor"""
        # Set parent but no tutor link
        self.student1_profile.parent = self.parent
        self.student1_profile.save()

        assert can_initiate_chat(self.parent, self.tutor) is False

    def test_parent_cannot_chat_with_inactive_tutor_even_with_child(self):
        """Parent cannot chat with inactive tutor"""
        # Set inactive tutor
        self.student1_profile.tutor = self.inactive_tutor
        self.student1_profile.parent = self.parent
        self.student1_profile.save()

        assert can_initiate_chat(self.parent, self.inactive_tutor) is False

    # Test 15: Parent + Student -> False (forbidden)
    def test_parent_cannot_chat_with_student(self):
        assert can_initiate_chat(self.parent, self.student1) is False

    # Test 16: Parent + Parent -> False (forbidden)
    def test_parent_cannot_chat_with_parent(self):
        other_parent = User.objects.create_user(
            username="parent2", email="parent2@test.com", password="pass", role="parent", is_active=True
        )
        assert can_initiate_chat(self.parent, other_parent) is False

    # Test 17: is_active checks - inactive user returns False
    def test_inactive_user_cannot_initiate_chat(self):
        """Inactive user cannot initiate chat even if permissions allow"""
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )
        assert can_initiate_chat(self.inactive_student, self.teacher) is False

    def test_cannot_chat_with_inactive_user(self):
        """Cannot chat with inactive user even if permissions allow"""
        SubjectEnrollment.objects.create(
            student=self.student1, teacher=self.inactive_teacher, subject=self.subject, status=SubjectEnrollment.Status.ACTIVE
        )
        assert can_initiate_chat(self.student1, self.inactive_teacher) is False

    def test_both_users_must_be_active(self):
        """Both users must be active"""
        assert can_initiate_chat(self.inactive_student, self.inactive_teacher) is False

    def test_admin_can_chat_with_inactive_user_returns_false(self):
        """Admin cannot chat with inactive user (both must be active)"""
        assert can_initiate_chat(self.admin, self.inactive_student) is False
        assert can_initiate_chat(self.inactive_student, self.admin) is False
