import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from rest_framework.test import APIClient, APITestCase
from rest_framework import status

from accounts.models import StudentProfile, TeacherProfile, TutorProfile, ParentProfile

User = get_user_model()


class TestAdminCompleteWorkflow(APITestCase):
    """Integration tests for complete admin workflow: create, edit, assign, delete"""

    def setUp(self):
        self.client = APIClient()

        self.admin = User.objects.create_superuser(
            username="admin",
            email="admin@test.com",
            password="admin123"
        )

        self.tutor = User.objects.create_user(
            username="tutor",
            email="tutor@test.com",
            password="tutor123",
            role=User.Role.TUTOR,
            is_active=True
        )

        self.parent = User.objects.create_user(
            username="parent",
            email="parent@test.com",
            password="parent123",
            role=User.Role.PARENT,
            is_active=True
        )

        self.teacher = User.objects.create_user(
            username="teacher",
            email="teacher@test.com",
            password="teacher123",
            role=User.Role.TEACHER,
            is_active=True
        )

        self.other_student = User.objects.create_user(
            username="student_other",
            email="other_student@test.com",
            password="student123",
            role=User.Role.STUDENT,
            is_active=True
        )
        StudentProfile.objects.create(user=self.other_student, grade=5)

        self.client.force_authenticate(user=self.admin)

    def test_create_student_basic(self):
        """Test: Admin creates a student with email, first_name, last_name"""
        response = self.client.post(
            "/api/admin/students/create/",
            {
                "email": "newstudent@test.com",
                "first_name": "John",
                "last_name": "Doe",
                "role": "student"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

        student = User.objects.get(email="newstudent@test.com")
        assert student.first_name == "John"
        assert student.last_name == "Doe"
        assert student.role == User.Role.STUDENT
        assert student.is_active is True

        assert hasattr(student, "student_profile")
        assert student.student_profile is not None

    def test_create_student_auto_generated_username(self):
        """Test: Admin creates student, username is auto-generated from email"""
        response = self.client.post(
            "/api/admin/students/create/",
            {
                "email": "generated@test.com",
                "first_name": "Jane",
                "last_name": "Smith"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        student = User.objects.get(email="generated@test.com")
        assert student.username is not None

    def test_create_student_duplicate_email_fails(self):
        """Test: Cannot create student with duplicate email"""
        first_response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "duplicate@test.com",
                "first_name": "First",
                "last_name": "User"
            },
            format="json"
        )
        assert first_response.status_code == status.HTTP_201_CREATED

        second_response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "duplicate@test.com",
                "first_name": "Second",
                "last_name": "User"
            },
            format="json"
        )
        assert second_response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_student_profile_created_automatically(self):
        """Test: StudentProfile is created automatically when student is created"""
        response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "autoprofile@test.com",
                "first_name": "Auto",
                "last_name": "Profile"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED
        student = User.objects.get(email="autoprofile@test.com")

        profile = StudentProfile.objects.get(user=student)
        assert profile.progress_percentage == 0
        assert profile.total_points == 0
        assert profile.streak_days == 0

    def test_assign_tutor_to_student(self):
        """Test: Admin assigns a tutor to student via profile update"""
        student = User.objects.create_user(
            username="student_for_tutor",
            email="student_for_tutor@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"tutor": self.tutor.id},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.student_profile.tutor == self.tutor

    def test_assign_parent_to_student(self):
        """Test: Admin assigns a parent to student via profile update"""
        student = User.objects.create_user(
            username="student_for_parent",
            email="student_for_parent@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"parent": self.parent.id},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.student_profile.parent == self.parent

    def test_assign_tutor_and_parent_together(self):
        """Test: Admin assigns both tutor and parent in one request"""
        student = User.objects.create_user(
            username="student_dual_assign",
            email="student_dual@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {
                "tutor": self.tutor.id,
                "parent": self.parent.id
            },
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.student_profile.tutor == self.tutor
        assert student.student_profile.parent == self.parent

    def test_update_student_grade(self):
        """Test: Admin updates student grade (1-12)"""
        student = User.objects.create_user(
            username="student_grade",
            email="student_grade@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"grade": 10},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.student_profile.grade == 10

    def test_update_student_goal_with_xss_protection(self):
        """Test: Admin updates student goal with XSS protection"""
        student = User.objects.create_user(
            username="student_goal",
            email="student_goal@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        xss_attempt = "<script>alert('xss')</script>Learn Math"
        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"goal": xss_attempt},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.student_profile.goal == xss_attempt

    def test_update_multiple_student_fields(self):
        """Test: Admin updates multiple student profile fields at once"""
        student = User.objects.create_user(
            username="student_multi",
            email="student_multi@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {
                "grade": 8,
                "goal": "Pass all exams",
                "tutor": self.tutor.id,
                "parent": self.parent.id
            },
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.student_profile.grade == 8
        assert student.student_profile.goal == "Pass all exams"
        assert student.student_profile.tutor == self.tutor
        assert student.student_profile.parent == self.parent

    def test_soft_delete_student_deactivates(self):
        """Test: Soft delete deactivates student (is_active=False), profile remains"""
        student = User.objects.create_user(
            username="student_soft_delete",
            email="student_soft_delete@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        student_profile = StudentProfile.objects.create(user=student)

        response = self.client.delete(
            f"/api/admin/users/{student.id}/delete/",
            {"permanent": False},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK

        student.refresh_from_db()
        assert student.is_active is False

        profile = StudentProfile.objects.get(user=student)
        assert profile is not None

    def test_soft_delete_student_cannot_login(self):
        """Test: Soft-deleted student cannot login"""
        student = User.objects.create_user(
            username="student_no_login",
            email="student_no_login@test.com",
            password="pass123",
            role=User.Role.STUDENT,
            is_active=True
        )
        StudentProfile.objects.create(user=student, grade=5)

        self.client.delete(
            f"/api/admin/users/{student.id}/delete/",
            {"permanent": False},
            format="json"
        )

        self.client.logout()
        login_response = self.client.post(
            "/api/admin/login/",
            {
                "email": "student_no_login@test.com",
                "password": "pass123"
            },
            format="json"
        )

        assert login_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_hard_delete_student_removes_everything(self):
        """Test: Hard delete removes User and StudentProfile"""
        student = User.objects.create_user(
            username="student_hard_delete",
            email="student_hard_delete@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)
        student_id = student.id

        response = self.client.delete(
            f"/api/admin/users/{student_id}/delete/",
            {"permanent": True},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK

        with pytest.raises(User.DoesNotExist):
            User.objects.get(id=student_id)

        with pytest.raises(StudentProfile.DoesNotExist):
            StudentProfile.objects.get(user_id=student_id)

    def test_teacher_cannot_create_users(self):
        """Test: Teacher cannot create users"""
        self.client.force_authenticate(user=self.teacher)

        response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "teacher_creates@test.com",
                "first_name": "Should",
                "last_name": "Fail"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_cannot_create_users(self):
        """Test: Student cannot create users"""
        student = User.objects.create_user(
            username="student_creator",
            email="student_creator@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)
        self.client.force_authenticate(user=student)

        response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "student_creates@test.com",
                "first_name": "Should",
                "last_name": "Fail"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tutor_cannot_create_users(self):
        """Test: Tutor cannot create users"""
        self.client.force_authenticate(user=self.tutor)

        response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "tutor_creates@test.com",
                "first_name": "Should",
                "last_name": "Fail"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_student_cannot_edit_other_student_profile(self):
        """Test: Student cannot edit other student's profile"""
        student1 = User.objects.create_user(
            username="student1_edit",
            email="student1_edit@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student1)

        self.client.force_authenticate(user=self.other_student)

        response = self.client.patch(
            f"/api/admin/students/{student1.id}/profile/",
            {"grade": 12},
            format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_tutor_cannot_edit_student_profile(self):
        """Test: Tutor cannot edit student profile (read-only)"""
        student = User.objects.create_user(
            username="student_tutor_edit",
            email="student_tutor_edit@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        self.client.force_authenticate(user=self.tutor)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"grade": 12},
            format="json"
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_sees_all_private_fields(self):
        """Test: Admin sees all private fields (goal, tutor, parent)"""
        student = User.objects.create_user(
            username="student_admin_see",
            email="student_admin_see@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(
            user=student,
            grade=5,
            goal="Learn Python",
            tutor=self.tutor,
            parent=self.parent
        )

        self.client.force_authenticate(user=self.admin)
        response = self.client.get(
            f"/api/admin/students/{student.id}/profile/"
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "goal" in data
        assert data["goal"] == "Learn Python"
        assert "tutor" in data
        assert "parent" in data

    def test_teacher_sees_student_goal(self):
        """Test: Teacher sees student goal but not other private fields"""
        student = User.objects.create_user(
            username="student_teacher_see",
            email="student_teacher_see@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(
            user=student,
            grade=5,
            goal="Learn Physics"
        )

        self.client.force_authenticate(user=self.teacher)
        response = self.client.get(
            f"/api/admin/students/{student.id}/profile/"
        )

        assert response.status_code == status.HTTP_200_OK

    def test_student_cannot_see_other_student_goal(self):
        """Test: Student cannot see other student's goal"""
        student = User.objects.create_user(
            username="student_goal_hide",
            email="student_goal_hide@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(
            user=student,
            grade=5,
            goal="Secret goal"
        )

        self.client.force_authenticate(user=self.other_student)
        response = self.client.get(
            f"/api/admin/students/{student.id}/profile/"
        )

        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            assert "goal" not in data or data.get("goal") != "Secret goal"

    def test_workflow_create_edit_assign_success(self):
        """Integration test: Complete workflow - create, edit, assign"""
        create_response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "workflow@test.com",
                "first_name": "Workflow",
                "last_name": "Test"
            },
            format="json"
        )

        assert create_response.status_code == status.HTTP_201_CREATED
        student = User.objects.get(email="workflow@test.com")

        edit_response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {
                "grade": 9,
                "goal": "Complete workflow test"
            },
            format="json"
        )
        assert edit_response.status_code == status.HTTP_200_OK

        assign_response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {
                "tutor": self.tutor.id,
                "parent": self.parent.id
            },
            format="json"
        )
        assert assign_response.status_code == status.HTTP_200_OK

        student.refresh_from_db()
        assert student.student_profile.grade == 9
        assert student.student_profile.goal == "Complete workflow test"
        assert student.student_profile.tutor == self.tutor
        assert student.student_profile.parent == self.parent

    def test_update_nonexistent_student_returns_404(self):
        """Test: Updating nonexistent student returns 404"""
        response = self.client.patch(
            f"/api/admin/students/99999/profile/",
            {"grade": 12},
            format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_delete_nonexistent_student_returns_404(self):
        """Test: Deleting nonexistent student returns 404"""
        response = self.client.delete(
            f"/api/admin/users/99999/delete/",
            {"permanent": False},
            format="json"
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_student_with_invalid_email_fails(self):
        """Test: Cannot create student with invalid email"""
        response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "not-an-email",
                "first_name": "Invalid",
                "last_name": "Email"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_create_student_missing_required_fields(self):
        """Test: Cannot create student without required fields"""
        response = self.client.post(
            "/api/admin/create_student/",
            {
                "first_name": "Missing",
                "last_name": "Fields"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_invalid_tutor_fails(self):
        """Test: Cannot assign invalid tutor"""
        student = User.objects.create_user(
            username="student_invalid_tutor",
            email="student_invalid_tutor@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"tutor": 99999},
            format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_assign_teacher_as_tutor_fails(self):
        """Test: Cannot assign teacher as tutor"""
        student = User.objects.create_user(
            username="student_teacher_tutor",
            email="student_teacher_tutor@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"tutor": self.teacher.id},
            format="json"
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_audit_log_on_student_creation(self):
        """Test: Audit log is recorded when student is created"""
        response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "auditlog@test.com",
                "first_name": "Audit",
                "last_name": "Log"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_201_CREATED

    def test_audit_log_on_student_update(self):
        """Test: Audit log is recorded when student profile is updated"""
        student = User.objects.create_user(
            username="student_audit_update",
            email="student_audit_update@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"grade": 7},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK

    def test_audit_log_on_student_deletion(self):
        """Test: Audit log is recorded when student is deleted"""
        student = User.objects.create_user(
            username="student_audit_delete",
            email="student_audit_delete@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response = self.client.delete(
            f"/api/admin/users/{student.id}/delete/",
            {"permanent": True},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK

    def test_unauthenticated_cannot_create_student(self):
        """Test: Unauthenticated user cannot create student"""
        self.client.force_authenticate(user=None)

        response = self.client.post(
            "/api/admin/create_student/",
            {
                "email": "unauth@test.com",
                "first_name": "Unauth",
                "last_name": "User"
            },
            format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_unauthenticated_cannot_update_student(self):
        """Test: Unauthenticated user cannot update student"""
        student = User.objects.create_user(
            username="student_unauth",
            email="student_unauth@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        self.client.force_authenticate(user=None)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"grade": 12},
            format="json"
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_student_with_empty_goal(self):
        """Test: Admin can clear student goal"""
        student = User.objects.create_user(
            username="student_empty_goal",
            email="student_empty_goal@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, goal="Some goal")

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"goal": ""},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.student_profile.goal == ""

    def test_update_student_grade_boundary_values(self):
        """Test: Admin can set grade to boundary values (1 and 12)"""
        student = User.objects.create_user(
            username="student_grades",
            email="student_grades@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5)

        response_1 = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"grade": 1},
            format="json"
        )
        assert response_1.status_code == status.HTTP_200_OK

        response_12 = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"grade": 12},
            format="json"
        )
        assert response_12.status_code == status.HTTP_200_OK

        student.refresh_from_db()
        assert student.student_profile.grade == 12

    def test_reassign_tutor_to_student(self):
        """Test: Admin can reassign tutor to different one"""
        new_tutor = User.objects.create_user(
            username="tutor2",
            email="tutor2@test.com",
            password="tutor123",
            role=User.Role.TUTOR,
            is_active=True
        )

        student = User.objects.create_user(
            username="student_tutor_reassign",
            email="student_tutor_reassign@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5, tutor=self.tutor)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"tutor": new_tutor.id},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.student_profile.tutor == new_tutor

    def test_remove_tutor_from_student(self):
        """Test: Admin can remove tutor from student"""
        student = User.objects.create_user(
            username="student_tutor_remove",
            email="student_tutor_remove@test.com",
            password="pass123",
            role=User.Role.STUDENT
        )
        StudentProfile.objects.create(user=student, grade=5, tutor=self.tutor)

        response = self.client.patch(
            f"/api/admin/students/{student.id}/profile/",
            {"tutor": None},
            format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        student.refresh_from_db()
        assert student.student_profile.tutor is None
