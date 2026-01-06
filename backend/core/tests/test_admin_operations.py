"""
Tests for Admin module operations.
Tests: User management, Staff views, Admin operations.
"""
from django.test import TestCase
from django.contrib.auth.models import Group, Permission
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.contenttypes.models import ContentType

from accounts.models import User, StudentProfile
from chat.models import ChatRoom, Message


class AdminUserManagementTests(TestCase):
    """Tests for admin user management"""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            role=User.Role.TEACHER,
        )
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staffpass123",
            role=User.Role.TEACHER,
            is_staff=True,
        )
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

    def test_admin_is_superuser(self):
        """Test that admin is superuser"""
        self.assertTrue(self.admin.is_superuser)
        self.assertTrue(self.admin.is_staff)

    def test_staff_is_staff_but_not_superuser(self):
        """Test staff user properties"""
        self.assertTrue(self.staff.is_staff)
        self.assertFalse(self.staff.is_superuser)

    def test_create_user_with_role(self):
        """Test creating user with specific role"""
        tutor = User.objects.create_user(
            username="tutor",
            email="tutor@example.com",
            password="testpass123",
            role=User.Role.TUTOR,
        )

        self.assertEqual(tutor.role, User.Role.TUTOR)
        self.assertEqual(tutor.get_role_display(), "Тьютор")

    def test_create_parent_user(self):
        """Test creating parent user"""
        parent = User.objects.create_user(
            username="parent",
            email="parent@example.com",
            password="testpass123",
            role=User.Role.PARENT,
        )

        self.assertEqual(parent.role, User.Role.PARENT)

    def test_update_user_profile(self):
        """Test updating user profile"""
        self.teacher.first_name = "John"
        self.teacher.last_name = "Doe"
        self.teacher.phone = "+79991234567"
        self.teacher.save()

        self.teacher.refresh_from_db()
        self.assertEqual(self.teacher.first_name, "John")
        self.assertEqual(self.teacher.last_name, "Doe")
        self.assertEqual(self.teacher.phone, "+79991234567")

    def test_get_all_users(self):
        """Test retrieving all users"""
        users = User.objects.all()
        self.assertEqual(users.count(), 4)

    def test_filter_users_by_role(self):
        """Test filtering users by role"""
        teachers = User.objects.filter(role=User.Role.TEACHER)
        students = User.objects.filter(role=User.Role.STUDENT)

        self.assertEqual(teachers.count(), 2)  # admin and teacher
        self.assertEqual(students.count(), 1)

    def test_deactivate_user(self):
        """Test deactivating user account"""
        self.teacher.is_active = False
        self.teacher.save()

        self.assertFalse(self.teacher.is_active)

    def test_activate_user(self):
        """Test reactivating user account"""
        self.teacher.is_active = False
        self.teacher.save()

        self.teacher.is_active = True
        self.teacher.save()

        self.assertTrue(self.teacher.is_active)

    def test_user_verification_status(self):
        """Test user verification status"""
        self.assertFalse(self.student.is_verified)

        self.student.is_verified = True
        self.student.save()

        self.assertTrue(self.student.is_verified)


class AdminBulkOperationsTests(TestCase):
    """Tests for admin bulk operations"""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            role=User.Role.TEACHER,
        )
        # Create 5 students
        self.students = [
            User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@example.com",
                password="testpass123",
                role=User.Role.STUDENT,
            )
            for i in range(5)
        ]

    def test_bulk_verify_users(self):
        """Test bulk verification of users"""
        User.objects.filter(role=User.Role.STUDENT).update(is_verified=True)

        verified = User.objects.filter(role=User.Role.STUDENT, is_verified=True)
        self.assertEqual(verified.count(), 5)

    def test_bulk_deactivate_users(self):
        """Test bulk deactivation"""
        User.objects.filter(role=User.Role.STUDENT).update(is_active=False)

        inactive = User.objects.filter(role=User.Role.STUDENT, is_active=False)
        self.assertEqual(inactive.count(), 5)

    def test_bulk_update_roles(self):
        """Test bulk role updates"""
        User.objects.filter(role=User.Role.STUDENT).update(role=User.Role.TUTOR)

        tutors = User.objects.filter(role=User.Role.TUTOR)
        self.assertEqual(tutors.count(), 5)

    def test_delete_users(self):
        """Test user deletion"""
        student_id = self.students[0].id
        self.students[0].delete()

        with self.assertRaises(User.DoesNotExist):
            User.objects.get(id=student_id)

    def test_bulk_add_to_group(self):
        """Test adding users to groups in bulk"""
        group, _ = Group.objects.get_or_create(name="Teachers")

        for student in self.students:
            student.groups.add(group)

        group_members = group.user_set.all()
        self.assertEqual(group_members.count(), 5)


class AdminAccessControlTests(TestCase):
    """Tests for admin access control"""

    def setUp(self):
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="adminpass123",
            role=User.Role.TEACHER,
        )
        self.staff = User.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="staffpass123",
            role=User.Role.TEACHER,
            is_staff=True,
        )
        self.regular_user = User.objects.create_user(
            username="user",
            email="user@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

    def test_admin_has_all_permissions(self):
        """Test admin has all permissions"""
        self.assertTrue(self.admin.is_superuser)
        # Superusers have all permissions
        self.assertTrue(self.admin.has_perm("auth.add_user"))
        self.assertTrue(self.admin.has_perm("auth.change_user"))
        self.assertTrue(self.admin.has_perm("auth.delete_user"))

    def test_staff_can_have_specific_permissions(self):
        """Test assigning specific permissions to staff"""
        content_type = ContentType.objects.get_for_model(User)
        permission = Permission.objects.get(
            content_type=content_type,
            codename="add_user"
        )
        self.staff.user_permissions.add(permission)

        self.assertTrue(self.staff.has_perm("auth.add_user"))

    def test_regular_user_no_admin_permissions(self):
        """Test regular user has no admin permissions"""
        self.assertFalse(self.regular_user.is_staff)
        self.assertFalse(self.regular_user.is_superuser)


class AdminReportingTests(TestCase):
    """Tests for admin reporting functionality"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="testpass123",
            role=User.Role.TEACHER,
        )
        self.students = [
            User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@example.com",
                password="testpass123",
                role=User.Role.STUDENT,
            )
            for i in range(3)
        ]

    def test_count_users_by_role(self):
        """Test counting users by role"""
        teacher_count = User.objects.filter(role=User.Role.TEACHER).count()
        student_count = User.objects.filter(role=User.Role.STUDENT).count()

        self.assertEqual(teacher_count, 1)
        self.assertEqual(student_count, 3)

    def test_count_active_inactive_users(self):
        """Test counting active/inactive users"""
        self.students[0].is_active = False
        self.students[0].save()

        active = User.objects.filter(is_active=True).count()
        inactive = User.objects.filter(is_active=False).count()

        self.assertEqual(active, 4)  # teacher + 2 students
        self.assertEqual(inactive, 1)

    def test_count_verified_users(self):
        """Test counting verified users"""
        self.students[0].is_verified = True
        self.students[0].save()
        self.students[1].is_verified = True
        self.students[1].save()

        verified = User.objects.filter(is_verified=True).count()
        self.assertEqual(verified, 2)

    def test_user_creation_distribution(self):
        """Test user creation date distribution"""
        from django.utils import timezone

        # All users created "now" (in test)
        recent_users = User.objects.filter(created_at__isnull=False)
        self.assertEqual(recent_users.count(), 4)


class AdminDataSecurityTests(TestCase):
    """Tests for admin data security"""

    def setUp(self):
        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@example.com",
            password="teacherpass123",
            role=User.Role.TEACHER,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="studentpass123",
            role=User.Role.STUDENT,
        )

    def test_password_hashing(self):
        """Test that passwords are hashed"""
        self.assertNotEqual(self.teacher.password, "teacherpass123")
        self.assertTrue(self.teacher.check_password("teacherpass123"))

    def test_user_cannot_see_other_passwords(self):
        """Test password field is not exposed"""
        # Password should be hashed, not plain text
        self.assertTrue(self.student.password.startswith("pbkdf2_sha256$") or
                       self.student.password.startswith("bcrypt$"))

    def test_telegram_id_unique_constraint(self):
        """Test telegram_id uniqueness"""
        self.teacher.telegram_id = 123456789
        self.teacher.save()

        with self.assertRaises(Exception):  # IntegrityError
            self.student.telegram_id = 123456789
            self.student.save()


class AdminStudentProfileManagementTests(TestCase):
    """Tests for admin management of student profiles"""

    def setUp(self):
        self.tutor = User.objects.create_user(
            username="tutor",
            email="tutor@example.com",
            password="testpass123",
            role=User.Role.TUTOR,
        )
        self.parent = User.objects.create_user(
            username="parent",
            email="parent@example.com",
            password="testpass123",
            role=User.Role.PARENT,
        )
        self.student = User.objects.create_user(
            username="student",
            email="student@example.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )
        self.profile = StudentProfile.objects.create(
            user=self.student,
            grade="10",
            tutor=self.tutor,
            parent=self.parent,
        )

    def test_assign_tutor_to_student(self):
        """Test assigning tutor to student"""
        self.assertEqual(self.profile.tutor, self.tutor)

    def test_assign_parent_to_student(self):
        """Test assigning parent to student"""
        self.assertEqual(self.profile.parent, self.parent)

    def test_update_student_grade(self):
        """Test updating student grade"""
        self.profile.grade = "11"
        self.profile.save()

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.grade, "11")

    def test_update_student_goal(self):
        """Test updating student learning goal"""
        goal = "Get 100% on final exam"
        self.profile.goal = goal
        self.profile.save()

        self.profile.refresh_from_db()
        self.assertEqual(self.profile.goal, goal)

    def test_remove_tutor(self):
        """Test removing tutor assignment"""
        self.profile.tutor = None
        self.profile.save()

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.tutor)

    def test_remove_parent(self):
        """Test removing parent assignment"""
        self.profile.parent = None
        self.profile.save()

        self.profile.refresh_from_db()
        self.assertIsNone(self.profile.parent)
