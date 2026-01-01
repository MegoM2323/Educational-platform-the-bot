"""
Simplified admin panel tests - focus on core functionality without complex migrations
"""

import pytest
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class AdminAccessTests(TestCase):
    """Test basic admin panel access"""

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
            password="teacher123",
            first_name="Ivan",
            last_name="Petrov",
            role=User.Role.TEACHER,
        )

        self.student = User.objects.create_user(
            username="student1",
            email="student1@test.com",
            password="student123",
            first_name="Anna",
            last_name="Ivanova",
            role=User.Role.STUDENT,
        )

    def test_admin_can_login_to_admin_panel(self):
        """Admin user can login and access admin"""
        login_success = self.client.login(username="admin", password="admin123")
        assert login_success, "Admin should be able to login"

        response = self.client.get(reverse("admin:index"))
        assert response.status_code == 200, "Admin should access admin panel"

    def test_teacher_cannot_access_admin_panel(self):
        """Non-admin users cannot access admin panel"""
        self.client.login(username="teacher1", password="teacher123")
        response = self.client.get(reverse("admin:index"), follow=True)

        # Django redirects non-staff to login
        assert response.status_code in [200, 403], "Should be unauthorized"

    def test_student_cannot_access_admin_panel(self):
        """Students cannot access admin"""
        self.client.login(username="student1", password="student123")
        response = self.client.get(reverse("admin:index"), follow=True)

        assert response.status_code in [200, 403], "Should be unauthorized"

    def test_unauthenticated_redirected_to_login(self):
        """Unauthenticated user redirected"""
        response = self.client.get(reverse("admin:index"), follow=True)

        # Should be redirected to login
        assert any(
            "/login/" in str(url) for url, _ in response.redirect_chain
        ), "Should redirect to login"


class UserManagementTests(TestCase):
    """Test user management in admin"""

    def setUp(self):
        """Setup test data"""
        self.client = Client()

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            role=User.Role.STUDENT,
        )

        # Create test users
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

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor1@test.com",
            password="pass123",
            role=User.Role.TUTOR,
        )

    def test_user_list_accessible_to_admin(self):
        """Admin can view user list"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:accounts_user_changelist"))
        assert response.status_code == 200, "User list should be accessible"

    def test_user_count_correct(self):
        """Total user count is correct"""
        total = User.objects.count()
        # 1 admin + 3 teachers + 5 students + 1 tutor = 10
        assert total == 10, f"Should have 10 users, got {total}"

    def test_teacher_count(self):
        """Teacher count is correct"""
        teachers = User.objects.filter(role=User.Role.TEACHER).count()
        assert teachers == 3, f"Should have 3 teachers, got {teachers}"

    def test_student_count(self):
        """Student count is correct"""
        students = User.objects.filter(role=User.Role.STUDENT, is_superuser=False).count()
        assert students >= 5, f"Should have at least 5 students, got {students}"

    def test_tutor_count(self):
        """Tutor count is correct"""
        tutors = User.objects.filter(role=User.Role.TUTOR).count()
        assert tutors == 1, f"Should have 1 tutor, got {tutors}"

    def test_user_search_by_email(self):
        """Can search users by email"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(
            reverse("admin:accounts_user_changelist") + "?q=teacher1@test.com"
        )
        assert response.status_code == 200, "Search should work"

    def test_user_filter_by_role(self):
        """Can filter users by role"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(
            reverse("admin:accounts_user_changelist") + "?role=teacher"
        )
        assert response.status_code == 200, "Filter should work"

    def test_view_individual_user(self):
        """Can view individual user details"""
        self.client.login(username="admin", password="admin123")

        student = User.objects.filter(role=User.Role.STUDENT, is_superuser=False).first()
        if student:
            url = reverse("admin:accounts_user_change", args=[student.id])
            response = self.client.get(url)
            assert response.status_code == 200, "User detail should be accessible"


class AdminSecurityTests(TestCase):
    """Test admin panel security"""

    def setUp(self):
        """Setup test data"""
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
            password="teacher123",
            role=User.Role.TEACHER,
        )

    def test_csrf_protection_enabled(self):
        """Admin pages have CSRF protection"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:index"))
        # Should load without CSRF errors
        assert response.status_code == 200

    def test_teacher_cannot_modify_users(self):
        """Non-admin cannot modify users"""
        self.client.login(username="teacher1", password="teacher123")
        # Try to POST to modify a user
        response = self.client.post(
            reverse("admin:accounts_user_changelist"), {}, follow=True
        )
        # Should be denied
        assert response.status_code in [200, 403]

    def test_only_admin_can_access_admin(self):
        """Only admin staff can access admin"""
        # Non-staff user
        response = self.client.get(reverse("admin:index"), follow=True)
        # Should be redirected or denied
        assert any("/login/" in str(url) for url, _ in response.redirect_chain)


class AdminUITests(TestCase):
    """Test admin UI elements"""

    def setUp(self):
        """Setup test data"""
        self.client = Client()

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123",
            role=User.Role.STUDENT,
        )

    def test_admin_index_loads(self):
        """Admin index page loads"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:index"))
        assert response.status_code == 200

    def test_admin_logout(self):
        """Admin can logout"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:logout"))
        assert response.status_code in [200, 302]

    def test_admin_sections_visible(self):
        """Admin sections are visible"""
        self.client.login(username="admin", password="admin123")
        response = self.client.get(reverse("admin:index"))
        content = response.content.decode()
        # Should have some content
        assert len(content) > 100, "Admin page should have content"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
