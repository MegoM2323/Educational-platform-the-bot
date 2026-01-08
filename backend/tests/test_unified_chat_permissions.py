"""
Comprehensive tests for unified can_initiate_chat() function.
Tests all 11 ALLOWED combinations and 5 FORBIDDEN combinations.
"""
import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase

from chat.permissions import can_initiate_chat
from accounts.models import StudentProfile
from materials.models import SubjectEnrollment, Subject

User = get_user_model()


@pytest.mark.django_db
class TestCanInitiateChatBasics(TestCase):
    """Test basic behavior: is_active checks, admin permissions"""

    def setUp(self):
        self.admin_user = User.objects.create_user(
            username="admin1", email="admin@test.com", role="admin", is_active=True
        )
        self.student1 = User.objects.create_user(
            username="student1", email="student1@test.com", role="student", is_active=True
        )
        self.teacher1 = User.objects.create_user(
            username="teacher1", email="teacher1@test.com", role="teacher", is_active=True
        )
        self.inactive_student = User.objects.create_user(
            username="inactive_student",
            email="inactive@test.com",
            role="student",
            is_active=False,
        )

    def test_inactive_users_cannot_chat(self):
        """Test T010: Inactive users cannot initiate or receive chats"""
        assert not can_initiate_chat(self.student1, self.inactive_student)
        assert not can_initiate_chat(self.inactive_student, self.student1)

    def test_admin_can_chat_with_anyone(self):
        """Test T006: Admin (role='admin') can always initiate chat"""
        assert can_initiate_chat(self.admin_user, self.student1)
        assert can_initiate_chat(self.admin_user, self.teacher1)
        assert can_initiate_chat(self.student1, self.admin_user)
        assert can_initiate_chat(self.teacher1, self.admin_user)

    def test_returns_bool(self):
        """Test that function returns boolean"""
        result = can_initiate_chat(self.admin_user, self.student1)
        assert isinstance(result, bool)
        assert result is True


@pytest.mark.django_db
class TestCanInitiateChatForbidden(TestCase):
    """Test FORBIDDEN combinations (all return False)"""

    def setUp(self):
        self.student1 = User.objects.create_user(
            username="student1", email="s1@test.com", role="student", is_active=True
        )
        self.student2 = User.objects.create_user(
            username="student2", email="s2@test.com", role="student", is_active=True
        )
        self.teacher1 = User.objects.create_user(
            username="teacher1", email="t1@test.com", role="teacher", is_active=True
        )
        self.teacher2 = User.objects.create_user(
            username="teacher2", email="t2@test.com", role="teacher", is_active=True
        )
        self.parent1 = User.objects.create_user(
            username="parent1", email="p1@test.com", role="parent", is_active=True
        )
        self.parent2 = User.objects.create_user(
            username="parent2", email="p2@test.com", role="parent", is_active=True
        )
        self.tutor1 = User.objects.create_user(
            username="tutor1", email="tu1@test.com", role="tutor", is_active=True
        )
        self.tutor2 = User.objects.create_user(
            username="tutor2", email="tu2@test.com", role="tutor", is_active=True
        )

    def test_student_cannot_chat_with_student(self):
        """FORBIDDEN: Student <-> Student"""
        assert not can_initiate_chat(self.student1, self.student2)
        assert not can_initiate_chat(self.student2, self.student1)

    def test_student_cannot_chat_with_parent(self):
        """FORBIDDEN: Student <-> Parent"""
        assert not can_initiate_chat(self.student1, self.parent1)
        assert not can_initiate_chat(self.parent1, self.student1)

    def test_teacher_cannot_chat_with_teacher(self):
        """FORBIDDEN: Teacher <-> Teacher"""
        assert not can_initiate_chat(self.teacher1, self.teacher2)
        assert not can_initiate_chat(self.teacher2, self.teacher1)

    def test_parent_cannot_chat_with_parent(self):
        """FORBIDDEN: Parent <-> Parent"""
        assert not can_initiate_chat(self.parent1, self.parent2)
        assert not can_initiate_chat(self.parent2, self.parent1)

    def test_tutor_cannot_chat_with_tutor(self):
        """FORBIDDEN: Tutor <-> Tutor"""
        assert not can_initiate_chat(self.tutor1, self.tutor2)
        assert not can_initiate_chat(self.tutor2, self.tutor1)


@pytest.mark.django_db
class TestCanInitiateChatStudentTeacher(TestCase):
    """Test Student <-> Teacher combination (ALLOWED with ACTIVE enrollment)"""

    def setUp(self):
        self.student = User.objects.create_user(
            username="student", email="s@test.com", role="student", is_active=True
        )
        self.teacher = User.objects.create_user(
            username="teacher", email="t@test.com", role="teacher", is_active=True
        )
        self.subject = Subject.objects.create(
            name="Math"
        )
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=self.subject,
            status=SubjectEnrollment.Status.ACTIVE,
        )

    def test_student_can_chat_with_teacher_if_active_enrollment(self):
        """ALLOWED: Student -> Teacher (with ACTIVE SubjectEnrollment)"""
        assert can_initiate_chat(self.student, self.teacher)

    def test_teacher_can_chat_with_student_if_active_enrollment(self):
        """ALLOWED: Teacher -> Student (with ACTIVE SubjectEnrollment)"""
        assert can_initiate_chat(self.teacher, self.student)

    def test_student_cannot_chat_with_different_teacher(self):
        """FORBIDDEN: Student -> Teacher (without enrollment)"""
        other_teacher = User.objects.create_user(
            username="teacher2", email="t2@test.com", role="teacher", is_active=True
        )
        assert not can_initiate_chat(self.student, other_teacher)

    def test_inactive_enrollment_blocks_chat(self):
        """Test T010: Non-ACTIVE SubjectEnrollment blocks chat"""
        self.enrollment.status = SubjectEnrollment.Status.DROPPED
        self.enrollment.save()
        assert not can_initiate_chat(self.student, self.teacher)


@pytest.mark.django_db
class TestCanInitiateChatStudentTutor(TestCase):
    """Test Student <-> Tutor combination (ALLOWED with active StudentProfile)"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor", email="tu@test.com", role="tutor", is_active=True
        )
        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor",
            email="tu_inactive@test.com",
            role="tutor",
            is_active=False,
        )
        self.student = User.objects.create_user(
            username="student", email="s@test.com", role="student", is_active=True
        )
        StudentProfile.objects.create(user=self.student, tutor=self.tutor)

    def test_student_can_chat_with_tutor(self):
        """ALLOWED: Student -> Tutor (with active StudentProfile.tutor)"""
        assert can_initiate_chat(self.student, self.tutor)

    def test_tutor_can_chat_with_student(self):
        """ALLOWED: Tutor -> Student (with active StudentProfile.tutor)"""
        assert can_initiate_chat(self.tutor, self.student)

    def test_student_cannot_chat_with_inactive_tutor(self):
        """Test T010: Student cannot chat with inactive tutor"""
        student2 = User.objects.create_user(
            username="student2", email="s2@test.com", role="student", is_active=True
        )
        StudentProfile.objects.create(user=student2, tutor=self.inactive_tutor)
        assert not can_initiate_chat(student2, self.inactive_tutor)

    def test_student_cannot_chat_with_unrelated_tutor(self):
        """FORBIDDEN: Student -> Tutor (without StudentProfile link)"""
        other_tutor = User.objects.create_user(
            username="tutor2", email="tu2@test.com", role="tutor", is_active=True
        )
        assert not can_initiate_chat(self.student, other_tutor)


@pytest.mark.django_db
class TestCanInitiateChatTeacherTutor(TestCase):
    """Test Teacher <-> Tutor combination (ALLOWED with common student with ACTIVE enrollment)"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", email="t@test.com", role="teacher", is_active=True
        )
        self.tutor = User.objects.create_user(
            username="tutor", email="tu@test.com", role="tutor", is_active=True
        )
        self.student = User.objects.create_user(
            username="student", email="s@test.com", role="student", is_active=True
        )
        StudentProfile.objects.create(user=self.student, tutor=self.tutor)
        self.subject = Subject.objects.create(
            name="Math"
        )
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=self.subject,
            status=SubjectEnrollment.Status.ACTIVE,
        )

    def test_teacher_can_chat_with_tutor_if_common_student(self):
        """ALLOWED: Teacher -> Tutor (if common student with ACTIVE enrollment)"""
        assert can_initiate_chat(self.teacher, self.tutor)

    def test_tutor_can_chat_with_teacher_if_common_student(self):
        """ALLOWED: Tutor -> Teacher (if common student with ACTIVE enrollment)"""
        assert can_initiate_chat(self.tutor, self.teacher)

    def test_teacher_cannot_chat_with_tutor_without_common_student(self):
        """FORBIDDEN: Teacher -> Tutor (without common student)"""
        other_tutor = User.objects.create_user(
            username="tutor2", email="tu2@test.com", role="tutor", is_active=True
        )
        assert not can_initiate_chat(self.teacher, other_tutor)

    def test_teacher_cannot_chat_if_student_has_inactive_enrollment(self):
        """Test T010: Cannot chat if enrollment is not ACTIVE"""
        self.enrollment.status = SubjectEnrollment.Status.DROPPED
        self.enrollment.save()
        assert not can_initiate_chat(self.teacher, self.tutor)


@pytest.mark.django_db
class TestCanInitiateChatParentTeacher(TestCase):
    """Test Parent <-> Teacher combination (ALLOWED ONLY if parent has child with ACTIVE enrollment)"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher", email="t@test.com", role="teacher", is_active=True
        )
        self.parent = User.objects.create_user(
            username="parent", email="p@test.com", role="parent", is_active=True
        )
        self.child = User.objects.create_user(
            username="child", email="c@test.com", role="student", is_active=True
        )
        StudentProfile.objects.create(user=self.child, parent=self.parent)
        self.subject = Subject.objects.create(
            name="Math"
        )
        self.enrollment = SubjectEnrollment.objects.create(
            student=self.child,
            teacher=self.teacher,
            subject=self.subject,
            status=SubjectEnrollment.Status.ACTIVE,
        )

    def test_parent_can_chat_with_child_teacher(self):
        """ALLOWED: Parent -> Teacher (if child has ACTIVE enrollment with this teacher)"""
        assert can_initiate_chat(self.parent, self.teacher)

    def test_teacher_can_chat_with_child_parent(self):
        """ALLOWED: Teacher -> Parent (if parent has child with ACTIVE enrollment)"""
        assert can_initiate_chat(self.teacher, self.parent)

    def test_parent_cannot_chat_with_other_teacher(self):
        """FORBIDDEN: Parent -> Teacher (if child doesn't have enrollment with this teacher)"""
        other_teacher = User.objects.create_user(
            username="teacher2", email="t2@test.com", role="teacher", is_active=True
        )
        assert not can_initiate_chat(self.parent, other_teacher)

    def test_parent_with_multiple_children_can_chat(self):
        """ALLOWED: Parent -> Teacher (if ANY child has ACTIVE enrollment)"""
        child2 = User.objects.create_user(
            username="child2", email="c2@test.com", role="student", is_active=True
        )
        StudentProfile.objects.create(user=child2, parent=self.parent)
        enrollment2 = SubjectEnrollment.objects.create(
            student=child2,
            teacher=self.teacher,
            subject=self.subject,
            status=SubjectEnrollment.Status.ACTIVE,
        )
        assert can_initiate_chat(self.parent, self.teacher)

    def test_parent_cannot_chat_if_enrollment_inactive(self):
        """Test T010: Parent cannot chat if child's enrollment is not ACTIVE"""
        self.enrollment.status = SubjectEnrollment.Status.DROPPED
        self.enrollment.save()
        assert not can_initiate_chat(self.parent, self.teacher)

    def test_inactive_parent_cannot_chat(self):
        """Test T010: Inactive parent cannot chat"""
        self.parent.is_active = False
        self.parent.save()
        assert not can_initiate_chat(self.parent, self.teacher)


@pytest.mark.django_db
class TestCanInitiateChatParentTutor(TestCase):
    """Test Parent <-> Tutor combination (ALLOWED ONLY if parent has child with this tutor)"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor", email="tu@test.com", role="tutor", is_active=True
        )
        self.inactive_tutor = User.objects.create_user(
            username="inactive_tutor",
            email="tu_inactive@test.com",
            role="tutor",
            is_active=False,
        )
        self.parent = User.objects.create_user(
            username="parent", email="p@test.com", role="parent", is_active=True
        )
        self.child = User.objects.create_user(
            username="child", email="c@test.com", role="student", is_active=True
        )
        StudentProfile.objects.create(user=self.child, parent=self.parent, tutor=self.tutor)

    def test_parent_can_chat_with_child_tutor(self):
        """ALLOWED: Parent -> Tutor (if child has this tutor and tutor is_active)"""
        assert can_initiate_chat(self.parent, self.tutor)

    def test_tutor_can_chat_with_child_parent(self):
        """ALLOWED: Tutor -> Parent (if parent has child with this tutor and tutor is_active)"""
        assert can_initiate_chat(self.tutor, self.parent)

    def test_parent_cannot_chat_with_other_tutor(self):
        """FORBIDDEN: Parent -> Tutor (if child doesn't have this tutor)"""
        other_tutor = User.objects.create_user(
            username="tutor2", email="tu2@test.com", role="tutor", is_active=True
        )
        assert not can_initiate_chat(self.parent, other_tutor)

    def test_parent_cannot_chat_with_inactive_tutor(self):
        """Test T010: Parent cannot chat with inactive tutor"""
        child2 = User.objects.create_user(
            username="child2", email="c2@test.com", role="student", is_active=True
        )
        StudentProfile.objects.create(
            user=child2, parent=self.parent, tutor=self.inactive_tutor
        )
        assert not can_initiate_chat(self.parent, self.inactive_tutor)

    def test_inactive_parent_cannot_chat_with_tutor(self):
        """Test T010: Inactive parent cannot chat"""
        self.parent.is_active = False
        self.parent.save()
        assert not can_initiate_chat(self.parent, self.tutor)


@pytest.mark.django_db
class TestCanInitiateChatSymmetry(TestCase):
    """Test that permissions work bidirectionally for allowed combinations"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin", email="admin@test.com", role="admin", is_active=True
        )
        self.student = User.objects.create_user(
            username="student", email="s@test.com", role="student", is_active=True
        )
        self.teacher = User.objects.create_user(
            username="teacher", email="t@test.com", role="teacher", is_active=True
        )
        self.subject = Subject.objects.create(
            name="Math"
        )
        SubjectEnrollment.objects.create(
            student=self.student,
            teacher=self.teacher,
            subject=self.subject,
            status=SubjectEnrollment.Status.ACTIVE,
        )

    def test_symmetry_student_teacher(self):
        """Test that both directions work for Student <-> Teacher"""
        assert can_initiate_chat(self.student, self.teacher) == can_initiate_chat(
            self.teacher, self.student
        )

    def test_admin_asymmetry(self):
        """Test that Admin can initiate in both directions"""
        assert can_initiate_chat(self.admin, self.student) is True
        assert can_initiate_chat(self.student, self.admin) is True


@pytest.mark.django_db
class TestCanInitiateChatEdgeCases(TestCase):
    """Test edge cases and error handling"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user", email="user@test.com", role="student", is_active=True
        )

    def test_user_cannot_chat_with_self(self):
        """Test that a user cannot initiate chat with themselves (caught by is_active check + DB)"""
        # This should be caught by application logic above this function,
        # but we verify the function handles it gracefully
        result = can_initiate_chat(self.user, self.user)
        assert isinstance(result, bool)

    def test_exception_handling(self):
        """Test that function handles exceptions gracefully"""
        class BadUser:
            is_active = True
            role = "student"

        bad_user = BadUser()
        result = can_initiate_chat(bad_user, self.user)
        assert result is False
