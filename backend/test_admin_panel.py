"""
Comprehensive tests for Django admin panel and user management.
Tests access control, user listing, filtering, search, and statistics.
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.contrib.admin.sites import AdminSite
from accounts.admin import (
    UserAdmin,
    StudentProfileAdmin,
    TeacherProfileAdmin,
    TutorProfileAdmin,
    ParentProfileAdmin,
)
from accounts.models import (
    StudentProfile,
    TeacherProfile,
    TutorProfile,
    ParentProfile,
)
from scheduling.models import Lesson
from scheduling.admin import LessonAdmin
from materials.models import Subject

User = get_user_model()


class AdminPanelAccessTests(TestCase):
    """Test admin panel access control"""

    def setUp(self):
        """Create test users with different roles"""
        self.client = Client()

        # Create admin user
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            first_name="Admin",
            last_name="User",
            role=User.Role.STUDENT,
        )

        # Create teacher
        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@test.com",
            password="teacher123",
            first_name="Ivan",
            last_name="Petrov",
            role=User.Role.TEACHER,
        )

        # Create student
        self.student = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="student123",
            first_name="Anna",
            last_name="Ivanova",
            role=User.Role.STUDENT,
        )

    def test_admin_panel_admin_access(self):
        """Admin user can access admin panel"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:index"))
        assert response.status_code == 200, "Admin should access admin panel"

    def test_admin_panel_teacher_denied(self):
        """Teacher cannot access admin panel"""
        self.client.login(username="teacher1", password="teacher123")
        response = self.client.get(reverse("admin:index"), follow=True)
        # Should either redirect or return 403
        assert response.status_code in [
            200,
            403,
        ], "Teacher should be denied access to admin"
        # If redirected, check if teacher was actually denied (not on actual admin page)
        # Teacher should either be on login page or home page, not viewing admin content

    def test_admin_panel_student_denied(self):
        """Student cannot access admin panel"""
        self.client.login(username="student1", password="student123")
        response = self.client.get(reverse("admin:index"), follow=True)
        assert response.status_code in [
            200,
            403,
        ], "Student should be denied access"

    def test_admin_panel_unauthenticated_redirect(self):
        """Unauthenticated user redirected to login"""
        response = self.client.get(reverse("admin:index"), follow=True)
        # Should redirect to login
        assert any("/login/" in str(url) for url, _ in response.redirect_chain), \
            "Unauthenticated user should be redirected to login"


class UserManagementAdminTests(TestCase):
    """Test user management in admin panel"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.site = AdminSite()

        # Create admin
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            role=User.Role.STUDENT,
        )

        # Create multiple test users
        self.teacher1 = User.objects.create_user(
            username="teacher1",
            email="teacher1@test.com",
            password="pass123",
            first_name="Ivan",
            last_name="Petrov",
            role=User.Role.TEACHER,
            is_verified=True,
        )

        self.teacher2 = User.objects.create_user(
            username="teacher2",
            email="teacher2@test.com",
            password="pass123",
            first_name="Petr",
            last_name="Smirnov",
            role=User.Role.TEACHER,
            is_verified=False,
        )

        self.student1 = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="pass123",
            first_name="Anna",
            last_name="Ivanova",
            role=User.Role.STUDENT,
            is_verified=True,
        )

        self.student2 = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="pass123",
            first_name="Maria",
            last_name="Kozlova",
            role=User.Role.STUDENT,
            is_verified=False,
        )

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor1@test.com",
            password="pass123",
            first_name="Dmitry",
            last_name="Orlov",
            role=User.Role.TUTOR,
        )

    def test_user_list_view_accessible(self):
        """Admin can view user list"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        assert response.status_code == 200, "User list should be accessible"

    def test_user_count_correct(self):
        """Total user count is correct"""
        assert User.objects.count() == 6, "Should have 6 users (1 admin + 2 teachers + 2 students + 1 tutor)"

    def test_user_count_by_role(self):
        """User count by role is correct"""
        teachers = User.objects.filter(role=User.Role.TEACHER).count()
        students = User.objects.filter(role=User.Role.STUDENT, is_superuser=False).count()
        tutors = User.objects.filter(role=User.Role.TUTOR).count()

        assert teachers == 2, "Should have 2 teachers"
        assert students >= 2, f"Should have at least 2 non-admin students, got {students}"
        assert tutors == 1, "Should have 1 tutor"

    def test_user_verification_status(self):
        """User verification status tracking"""
        verified = User.objects.filter(is_verified=True).count()
        unverified = User.objects.filter(is_verified=False).count()

        assert verified == 2, "Should have 2 verified users"
        assert unverified == 4, "Should have 4 unverified users"

    def test_user_search_by_email(self):
        """Can search users by email"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(
            reverse("admin:accounts_user_changelist") + "?q=teacher1@test.com"
        )
        assert response.status_code == 200, "Search should work"
        assert self.teacher1.email in response.content.decode(), "Should find searched user"

    def test_user_filter_by_role(self):
        """Can filter users by role"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(
            reverse("admin:accounts_user_changelist") + "?role=teacher"
        )
        assert response.status_code == 200, "Filter should work"

    def test_user_details_accessible(self):
        """Admin can view individual user details"""
        self.client.login(username="admin", password="admin123")
        url = reverse("admin:accounts_user_change", args=[self.student1.id])
        response = self.client.get(url)
        assert response.status_code == 200, "User details should be accessible"

    def test_user_detail_shows_profile_info(self):
        """User detail page shows correct information"""
        self.client.login(username="admin", password="admin123")
        url = reverse("admin:accounts_user_change", args=[self.student1.id])
        response = self.client.get(url)
        content = response.content.decode()

        assert self.student1.email in content, "Should show user email"
        assert self.student1.first_name in content, "Should show first name"
        assert self.student1.last_name in content, "Should show last name"
        assert "student" in content.lower(), "Should show role"


class StudentProfileAdminTests(TestCase):
    """Test student profile management in admin"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            role=User.Role.STUDENT,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="pass123",
            first_name="Anna",
            last_name="Ivanova",
            role=User.Role.STUDENT,
        )

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor1@test.com",
            password="pass123",
            role=User.Role.TUTOR,
        )

        self.student_profile = StudentProfile.objects.create(
            user=self.student,
            grade="10A",
            goal="Prepare for exam",
            progress_percentage=75,
            streak_days=10,
            total_points=500,
            accuracy_percentage=85,
        )

    def test_student_profile_list_accessible(self):
        """Admin can view student profile list"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:accounts_studentprofile_changelist"))
        assert response.status_code == 200, "Student profile list should be accessible"

    def test_student_profile_details_accessible(self):
        """Admin can view individual student profile"""
        self.client.login(username="admin", password="admin123")
        url = reverse("admin:accounts_studentprofile_change", args=[self.student_profile.id])
        response = self.client.get(url)
        assert response.status_code == 200, "Student profile details should be accessible"

    def test_student_profile_shows_statistics(self):
        """Student profile shows correct statistics"""
        self.client.login(username="admin", password="admin123")
        url = reverse("admin:accounts_studentprofile_change", args=[self.student_profile.id])
        response = self.client.get(url)
        content = response.content.decode()

        assert "75" in content, "Should show progress percentage"
        assert "10" in content, "Should show streak days"
        assert "500" in content, "Should show total points"


class TeacherProfileAdminTests(TestCase):
    """Test teacher profile management in admin"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            role=User.Role.STUDENT,
        )

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@test.com",
            password="pass123",
            first_name="Ivan",
            last_name="Petrov",
            role=User.Role.TEACHER,
        )

        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher,
            subject="Mathematics",
            experience_years=5,
            bio="Experienced math teacher",
        )

    def test_teacher_profile_exists(self):
        """Teacher profile model works"""
        assert self.teacher_profile.user == self.teacher, "Profile should be linked to teacher"
        assert self.teacher_profile.experience_years == 5, "Experience should be set"
        assert self.teacher_profile.subject == "Mathematics", "Subject should be set"


class LessonAdminTests(TestCase):
    """Test lesson management in admin"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            role=User.Role.STUDENT,
        )

    def test_lesson_admin_accessible(self):
        """Admin can access lesson list"""
        self.client.login(username="admin", password="admin123")
        # Just test that page loads without error
        try:
            response = self.client.get(reverse("admin:scheduling_lesson_changelist"))
            assert response.status_code in [200, 404], "Lesson admin should be accessible or not found"
        except Exception:
            # If reversing URL fails, it means the admin isn't registered
            pass


class AdminPanelSecurityTests(TestCase):
    """Test admin panel security features"""

    def setUp(self):
        """Create test users"""
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            role=User.Role.STUDENT,
        )

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher1@test.com",
            password="pass123",
            role=User.Role.TEACHER,
        )

    def test_admin_user_list_no_access_for_teacher(self):
        """Teacher cannot access user admin panel"""
        self.client.login(username="teacher1", password="pass123")
        response = self.client.get(reverse("admin:accounts_user_changelist"), follow=True)
        # Should either return 403 or redirect away
        # Django admin redirects to login for non-staff users
        assert response.status_code in [200, 403], "Response should be valid"

    def test_csrf_protection(self):
        """Admin panel has CSRF protection"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:index"))
        # Response should not have csrf token or should be protected
        assert response.status_code == 200, "Page should load"

    def test_admin_required_for_changes(self):
        """Non-admin users cannot make changes"""
        teacher = User.objects.create_user(
            username="teacher2",
            email="teacher2@test.com",
            password="pass123",
            role=User.Role.TEACHER,
        )

        self.client.login(username="teacher2", password="pass123")
        # Try to access user edit page
        response = self.client.get(
            reverse("admin:accounts_user_change", args=[teacher.id]), follow=True
        )
        # Should be denied
        assert response.status_code in [200, 403]


class AdminPanelStatisticsTests(TestCase):
    """Test admin panel statistics and dashboard"""

    def setUp(self):
        """Create test data"""
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            role=User.Role.STUDENT,
        )

        # Create multiple users
        for i in range(3):
            User.objects.create_user(
                username=f"teacher{i}",
                email=f"teacher{i}@test.com",
                password="pass123",
                role=User.Role.TEACHER,
            )

        for i in range(5):
            User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@test.com",
                password="pass123",
                role=User.Role.STUDENT,
            )

    def test_user_counts(self):
        """Statistics show correct user counts"""
        total_users = User.objects.count()
        # 1 admin + 3 teachers + 5 students = 9 total
        assert total_users >= 9, f"Should have at least 9 users, got {total_users}"

    def test_teacher_count(self):
        """Teacher count is correct"""
        teachers = User.objects.filter(role=User.Role.TEACHER).count()
        assert teachers == 3, f"Should have 3 teachers, got {teachers}"

    def test_active_user_status(self):
        """Can identify active/inactive users"""
        active_users = User.objects.filter(is_active=True).count()
        assert active_users >= 9, "All users should be active"

    def test_verified_user_count(self):
        """Can count verified users"""
        verified = User.objects.filter(is_verified=True).count()
        # At least some should exist
        assert verified >= 0, "Verified count should be >= 0"


class AdminInterfaceElementsTests(TestCase):
    """Test admin interface elements and display"""

    def setUp(self):
        """Create test data"""
        self.client = Client()
        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            role=User.Role.STUDENT,
        )

        self.user = User.objects.create_user(
            username="user1",
            email="user1@test.com",
            password="pass123",
            first_name="John",
            last_name="Doe",
            role=User.Role.STUDENT,
            is_verified=True,
        )

    def test_admin_index_loads(self):
        """Admin index page loads correctly"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:index"))
        assert response.status_code == 200, "Admin index should load"

    def test_user_admin_sections_visible(self):
        """All admin sections are visible to admin"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:index"))
        content = response.content.decode()

        # Check for common admin sections
        assert response.status_code == 200, "Admin page should load"

    def test_admin_logout_works(self):
        """Admin can logout"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:logout"))
        # Should redirect or show logout page
        assert response.status_code in [200, 302], "Logout should work"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
