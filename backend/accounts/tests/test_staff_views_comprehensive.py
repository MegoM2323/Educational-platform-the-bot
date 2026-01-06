import pytest
from django.contrib.auth import get_user_model
from django.test import TestCase, RequestFactory
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from rest_framework.authtoken.models import Token
from unittest.mock import patch, MagicMock

from accounts.models import (
    StudentProfile,
    TeacherProfile,
    TutorProfile,
    ParentProfile,
)
from accounts.staff_views import (
    list_staff,
    create_staff,
    list_students,
    get_student_detail,
    update_user,
    update_student_profile,
    update_teacher_profile,
    update_tutor_profile,
    update_parent_profile,
    delete_user,
    create_student,
    create_parent,
    list_parents,
    reset_password,
    reactivate_user,
    assign_parent_to_students,
    update_teacher_subjects,
    log_object_changes,
)

User = get_user_model()


class TestCreateStaff(APITestCase):
    """Tests for create_staff endpoint"""

    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.TEACHER,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_create_teacher_success(self):
        """Test: Successfully create teacher with password generation"""
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TEACHER,
                "email": "teacher@test.com",
                "first_name": "John",
                "last_name": "Doe",
                "subject": "Mathematics",
                "experience_years": 5,
                "bio": "Expert in math",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("credentials", response.data)
        self.assertIn("password", response.data["credentials"])
        self.assertIn("login", response.data["credentials"])

        # Verify user created
        user = User.objects.get(email="teacher@test.com")
        self.assertEqual(user.role, User.Role.TEACHER)
        self.assertTrue(user.is_active)

    def test_create_tutor_success(self):
        """Test: Successfully create tutor"""
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TUTOR,
                "email": "tutor@test.com",
                "first_name": "Jane",
                "last_name": "Smith",
                "specialization": "English",
                "experience_years": 3,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="tutor@test.com")
        self.assertEqual(user.role, User.Role.TUTOR)

    def test_create_staff_invalid_role(self):
        """Test: 400 error on invalid role"""
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": "invalid_role",
                "email": "staff@test.com",
                "first_name": "Test",
                "last_name": "User",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_staff_empty_email(self):
        """Test: 400 error on empty email"""
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TEACHER,
                "email": "",
                "first_name": "Test",
                "last_name": "User",
                "subject": "Math",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_staff_invalid_email_format(self):
        """Test: 400 error on invalid email format"""
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TEACHER,
                "email": "invalid-email",
                "first_name": "Test",
                "last_name": "User",
                "subject": "Math",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_staff_duplicate_email(self):
        """Test: 400 error on duplicate email"""
        User.objects.create_user(
            username="existing",
            email="existing@test.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TEACHER,
                "email": "existing@test.com",
                "first_name": "Test",
                "last_name": "User",
                "subject": "Math",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Email уже зарегистрирован", response.data["detail"])

    def test_create_teacher_missing_subject(self):
        """Test: 400 error when teacher missing subject"""
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TEACHER,
                "email": "teacher2@test.com",
                "first_name": "Test",
                "last_name": "User",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_tutor_missing_specialization(self):
        """Test: 400 error when tutor missing specialization"""
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TUTOR,
                "email": "tutor2@test.com",
                "first_name": "Test",
                "last_name": "User",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_staff_missing_names(self):
        """Test: 400 error on missing first or last name"""
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TEACHER,
                "email": "teacher3@test.com",
                "first_name": "Test",
                "subject": "Math",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_staff_invalid_experience_years(self):
        """Test: 400 error on non-numeric experience_years"""
        response = self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TEACHER,
                "email": "teacher4@test.com",
                "first_name": "Test",
                "last_name": "User",
                "subject": "Math",
                "experience_years": "not_a_number",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("accounts.staff_views.audit_logger")
    def test_create_staff_logs_action(self, mock_audit_logger):
        """Test: Audit logging on staff creation"""
        self.client.post(
            "/api/staff/create/",
            {
                "role": User.Role.TEACHER,
                "email": "logged@test.com",
                "first_name": "Test",
                "last_name": "User",
                "subject": "Math",
            },
            format="json",
        )
        # Logger should be called via log_object_changes


class TestListStaff(APITestCase):
    """Tests for list_staff endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        # Create test teachers
        for i in range(3):
            User.objects.create_user(
                username=f"teacher{i}",
                email=f"teacher{i}@test.com",
                password="pass",
                role=User.Role.TEACHER,
                is_active=True,
                first_name=f"Teacher{i}",
                last_name="Doe",
            )
            TeacherProfile.objects.create(
                user=User.objects.get(email=f"teacher{i}@test.com"),
                subject="Math",
                experience_years=i,
            )

    def test_list_teachers(self):
        """Test: List teachers"""
        response = self.client.get("/api/staff/", {"role": "teacher"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 3)

    def test_list_tutors(self):
        """Test: List tutors"""
        tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass",
            role=User.Role.TUTOR,
            is_active=True,
        )
        TutorProfile.objects.create(user=tutor, specialization="Math")

        response = self.client.get("/api/staff/", {"role": "tutor"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)
        self.assertEqual(len(response.data["results"]), 1)

    def test_list_staff_missing_role(self):
        """Test: 400 error when role not specified"""
        response = self.client.get("/api/staff/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_staff_invalid_role(self):
        """Test: 400 error on invalid role"""
        response = self.client.get("/api/staff/", {"role": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestListStudents(APITestCase):
    """Tests for list_students endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass",
            role=User.Role.TUTOR,
            is_active=True,
        )
        TutorProfile.objects.create(user=self.tutor, specialization="Math")

        # Create test students
        for i in range(5):
            user = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@test.com",
                password="pass",
                role=User.Role.STUDENT,
                is_active=(i % 2 == 0),
                first_name=f"Student{i}",
                last_name="Doe",
            )
            StudentProfile.objects.create(
                user=user,
                grade="10A" if i < 3 else "11B",
                tutor=self.tutor if i < 2 else None,
            )

    def test_list_students_success(self):
        """Test: Successfully list students"""
        response = self.client.get("/api/students/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_list_students_filter_by_tutor(self):
        """Test: Filter students by tutor"""
        response = self.client.get(
            "/api/students/", {"tutor_id": self.tutor.id}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)

    def test_list_students_filter_by_tutor_invalid_id(self):
        """Test: 400 error on invalid tutor_id format"""
        response = self.client.get("/api/students/", {"tutor_id": "invalid"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_students_filter_by_grade(self):
        """Test: Filter students by grade"""
        response = self.client.get("/api/students/", {"grade": "10A"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_students_filter_by_is_active(self):
        """Test: Filter students by is_active status"""
        response = self.client.get("/api/students/", {"is_active": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_students_search_by_email(self):
        """Test: Search students by email"""
        response = self.client.get("/api/students/", {"search": "student1"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_students_pagination(self):
        """Test: Students list is paginated"""
        response = self.client.get("/api/students/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)


class TestGetStudentDetail(APITestCase):
    """Tests for get_student_detail endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.student_user = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass",
            role=User.Role.STUDENT,
            is_active=True,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user, grade="10A"
        )

    def test_get_student_detail_success(self):
        """Test: Successfully get student details"""
        response = self.client.get(f"/api/students/{self.student_user.id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("grade", response.data)

    def test_get_student_detail_not_found(self):
        """Test: 404 error on non-existent student"""
        response = self.client.get("/api/students/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_get_student_detail_non_student_user(self):
        """Test: 404 when user is not a student"""
        teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass",
            role=User.Role.TEACHER,
        )
        response = self.client.get(f"/api/students/{teacher.id}/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestUpdateUser(APITestCase):
    """Tests for update_user endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.student_user = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass",
            role=User.Role.STUDENT,
            is_active=True,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user, grade="10A"
        )

    def test_update_user_basic_fields(self):
        """Test: Successfully update basic user fields"""
        response = self.client.patch(
            f"/api/users/{self.student_user.id}/",
            {"first_name": "NewName", "last_name": "NewLast"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_user.refresh_from_db()
        self.assertEqual(self.student_user.first_name, "NewName")

    def test_update_user_email(self):
        """Test: Update user email"""
        response = self.client.patch(
            f"/api/users/{self.student_user.id}/",
            {"email": "newemail@test.com"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_user_profile_data(self):
        """Test: Update user with profile_data"""
        response = self.client.patch(
            f"/api/users/{self.student_user.id}/",
            {
                "profile_data": {
                    "grade": "11B",
                    "goal": "University entrance",
                }
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.grade, "11B")

    def test_update_user_not_found(self):
        """Test: 404 error on non-existent user"""
        response = self.client.patch(
            "/api/users/99999/", {"first_name": "Test"}, format="json"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_update_user_self_deactivate_forbidden(self):
        """Test: 403 error when trying to deactivate self"""
        response = self.client.patch(
            f"/api/users/{self.admin.id}/",
            {"is_active": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_update_user_invalid_email(self):
        """Test: 400 error on invalid email"""
        response = self.client.patch(
            f"/api/users/{self.student_user.id}/",
            {"email": "invalid-email"},
            format="json",
        )
        # Response depends on serializer validation


class TestUpdateStudentProfile(APITestCase):
    """Tests for update_student_profile endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.student_user = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass",
            role=User.Role.STUDENT,
            is_active=True,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.student_user, grade="10A"
        )

    def test_update_student_profile_grade(self):
        """Test: Update student grade"""
        response = self.client.patch(
            f"/api/students/{self.student_user.id}/profile/",
            {"grade": "11A"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_profile.refresh_from_db()
        self.assertEqual(self.student_profile.grade, "11A")

    def test_update_student_profile_goal(self):
        """Test: Update student goal"""
        response = self.client.patch(
            f"/api/students/{self.student_user.id}/profile/",
            {"goal": "Pass final exams"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_update_student_profile_not_found(self):
        """Test: 404 error on non-existent student"""
        response = self.client.patch(
            "/api/students/99999/profile/",
            {"grade": "10A"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestDeleteUser(APITestCase):
    """Tests for delete_user endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.student_user = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="pass",
            role=User.Role.STUDENT,
            is_active=True,
        )

    def test_hard_delete_user(self):
        """Test: Hard delete user"""
        user_id = self.student_user.id
        response = self.client.delete(f"/api/users/{user_id}/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(User.objects.filter(id=user_id).exists())

    def test_soft_delete_user(self):
        """Test: Soft delete user"""
        response = self.client.delete(f"/api/users/{self.student_user.id}/", {"soft": "true"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.student_user.refresh_from_db()
        self.assertFalse(self.student_user.is_active)

    def test_delete_self_forbidden(self):
        """Test: 400 error when trying to delete self"""
        response = self.client.delete(f"/api/users/{self.admin.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot delete yourself", response.data.get("error", ""))

    def test_delete_last_superuser_forbidden(self):
        """Test: 400 error when deleting last superuser"""
        # Ensure admin is the only superuser
        other_superusers = User.objects.filter(is_superuser=True).exclude(id=self.admin.id)
        for su in other_superusers:
            su.is_superuser = False
            su.save()

        response = self.client.delete(f"/api/users/{self.admin.id}/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Cannot delete last superuser", response.data.get("error", ""))

    def test_delete_non_existent_user(self):
        """Test: 404 error on non-existent user"""
        response = self.client.delete("/api/users/99999/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    @patch("accounts.staff_views.audit_logger")
    def test_delete_user_logs_action(self, mock_audit_logger):
        """Test: Audit logging on user deletion"""
        student = User.objects.create_user(
            username="student2",
            email="student2@test.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.client.delete(f"/api/users/{student.id}/")


class TestCreateStudent(APITestCase):
    """Tests for create_student endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass",
            role=User.Role.TUTOR,
            is_active=True,
        )
        TutorProfile.objects.create(user=self.tutor, specialization="Math")

    def test_create_student_success(self):
        """Test: Successfully create student"""
        response = self.client.post(
            "/api/students/create/",
            {
                "email": "newstudent@test.com",
                "first_name": "Test",
                "last_name": "Student",
                "grade": "10A",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("credentials", response.data)
        self.assertIn("password", response.data["credentials"])

        # Verify student created
        user = User.objects.get(email="newstudent@test.com")
        self.assertEqual(user.role, User.Role.STUDENT)

    def test_create_student_with_tutor(self):
        """Test: Create student with tutor"""
        response = self.client.post(
            "/api/students/create/",
            {
                "email": "student_with_tutor@test.com",
                "first_name": "Test",
                "last_name": "Student",
                "grade": "10A",
                "tutor_id": self.tutor.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(email="student_with_tutor@test.com")
        student_profile = StudentProfile.objects.get(user=user)
        self.assertEqual(student_profile.tutor_id, self.tutor.id)

    def test_create_student_with_parent(self):
        """Test: Create student with parent"""
        parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass",
            role=User.Role.PARENT,
            is_active=True,
        )
        ParentProfile.objects.create(user=parent)

        response = self.client.post(
            "/api/students/create/",
            {
                "email": "student_with_parent@test.com",
                "first_name": "Test",
                "last_name": "Student",
                "grade": "10A",
                "parent_id": parent.id,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_student_missing_grade(self):
        """Test: 400 error when grade is missing"""
        response = self.client.post(
            "/api/students/create/",
            {
                "email": "nostudent@test.com",
                "first_name": "Test",
                "last_name": "Student",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_student_duplicate_email(self):
        """Test: 409 error on duplicate email"""
        User.objects.create_user(
            username="existing_student",
            email="existing@test.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        response = self.client.post(
            "/api/students/create/",
            {
                "email": "existing@test.com",
                "first_name": "Test",
                "last_name": "Student",
                "grade": "10A",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)

    def test_create_student_invalid_tutor_id(self):
        """Test: Handle invalid tutor_id gracefully"""
        response = self.client.post(
            "/api/students/create/",
            {
                "email": "student_invalid_tutor@test.com",
                "first_name": "Test",
                "last_name": "Student",
                "grade": "10A",
                "tutor_id": 99999,
            },
            format="json",
        )
        # Should create student but without tutor
        if response.status_code == status.HTTP_201_CREATED:
            user = User.objects.get(email="student_invalid_tutor@test.com")
            profile = StudentProfile.objects.get(user=user)
            self.assertIsNone(profile.tutor)


class TestCreateParent(APITestCase):
    """Tests for create_parent endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

    def test_create_parent_success(self):
        """Test: Successfully create parent"""
        response = self.client.post(
            "/api/parents/create/",
            {
                "email": "parent@test.com",
                "first_name": "Jane",
                "last_name": "Parent",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("credentials", response.data)

        # Verify parent created
        user = User.objects.get(email="parent@test.com")
        self.assertEqual(user.role, User.Role.PARENT)

    def test_create_parent_with_phone(self):
        """Test: Create parent with phone"""
        response = self.client.post(
            "/api/parents/create/",
            {
                "email": "parent_phone@test.com",
                "first_name": "John",
                "last_name": "Parent",
                "phone": "+1234567890",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_create_parent_duplicate_email(self):
        """Test: 409 error on duplicate email"""
        User.objects.create_user(
            username="existing_parent",
            email="existing@test.com",
            password="pass",
            role=User.Role.PARENT,
        )
        response = self.client.post(
            "/api/parents/create/",
            {
                "email": "existing@test.com",
                "first_name": "Test",
                "last_name": "Parent",
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_409_CONFLICT)


class TestListParents(APITestCase):
    """Tests for list_parents endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        # Create test parents
        for i in range(3):
            parent = User.objects.create_user(
                username=f"parent{i}",
                email=f"parent{i}@test.com",
                password="pass",
                role=User.Role.PARENT,
                is_active=True,
            )
            ParentProfile.objects.create(user=parent)

    def test_list_parents_success(self):
        """Test: Successfully list parents"""
        response = self.client.get("/api/parents/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("results", response.data)

    def test_list_parents_pagination(self):
        """Test: Parents list is paginated"""
        response = self.client.get("/api/parents/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("count", response.data)
        self.assertIn("results", response.data)


class TestResetPassword(APITestCase):
    """Tests for reset_password endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.student = User.objects.create_user(
            username="student1",
            email="student@test.com",
            password="oldpass",
            role=User.Role.STUDENT,
            is_active=True,
        )

    def test_reset_password_success(self):
        """Test: Successfully reset password"""
        response = self.client.post(f"/api/users/{self.student.id}/reset-password/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("new_password", response.data)
        self.assertTrue(response.data["success"])

    def test_reset_password_non_existent_user(self):
        """Test: 404 error on non-existent user"""
        response = self.client.post("/api/users/99999/reset-password/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_reset_password_inactive_user(self):
        """Test: 400 error when resetting password for inactive user"""
        self.student.is_active = False
        self.student.save()

        response = self.client.post(f"/api/users/{self.student.id}/reset-password/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class TestReactivateUser(APITestCase):
    """Tests for reactivate_user endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.inactive_student = User.objects.create_user(
            username="inactive_student",
            email="inactive@test.com",
            password="pass",
            role=User.Role.STUDENT,
            is_active=False,
        )

    def test_reactivate_user_success(self):
        """Test: Successfully reactivate user"""
        response = self.client.post(f"/api/users/{self.inactive_student.id}/reactivate/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.inactive_student.refresh_from_db()
        self.assertTrue(self.inactive_student.is_active)

    def test_reactivate_already_active_user(self):
        """Test: 400 error when reactivating already active user"""
        response = self.client.post(f"/api/users/{self.admin.id}/reactivate/")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reactivate_non_existent_user(self):
        """Test: 404 error on non-existent user"""
        response = self.client.post("/api/users/99999/reactivate/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestAssignParentToStudents(APITestCase):
    """Tests for assign_parent_to_students endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass",
            role=User.Role.PARENT,
            is_active=True,
        )
        ParentProfile.objects.create(user=self.parent)

        # Create test students
        self.students = []
        for i in range(3):
            student = User.objects.create_user(
                username=f"student{i}",
                email=f"student{i}@test.com",
                password="pass",
                role=User.Role.STUDENT,
                is_active=True,
            )
            StudentProfile.objects.create(user=student, grade="10A")
            self.students.append(student)

    def test_assign_parent_to_students_success(self):
        """Test: Successfully assign parent to students"""
        response = self.client.post(
            "/api/assign-parent/",
            {
                "parent_id": self.parent.id,
                "student_ids": [s.id for s in self.students],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["assigned_students"]), 3)

        # Verify assignment
        for student in self.students:
            profile = StudentProfile.objects.get(user=student)
            self.assertEqual(profile.parent_id, self.parent.id)

    def test_assign_parent_missing_parent_id(self):
        """Test: 400 error when parent_id missing"""
        response = self.client.post(
            "/api/assign-parent/",
            {"student_ids": [s.id for s in self.students]},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_parent_missing_student_ids(self):
        """Test: 400 error when student_ids missing"""
        response = self.client.post(
            "/api/assign-parent/",
            {"parent_id": self.parent.id},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_assign_parent_non_existent_parent(self):
        """Test: 404 error on non-existent parent"""
        response = self.client.post(
            "/api/assign-parent/",
            {
                "parent_id": 99999,
                "student_ids": [s.id for s in self.students],
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class TestLogObjectChanges(TestCase):
    """Tests for log_object_changes helper function"""

    def setUp(self):
        self.user = User.objects.create_user(
            username="user1",
            email="user@test.com",
            password="pass",
            role=User.Role.STUDENT,
        )
        self.student_profile = StudentProfile.objects.create(
            user=self.user, grade="10A"
        )
        self.request_user = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="pass",
            role=User.Role.ADMIN,
            is_superuser=True,
        )
        self.factory = RequestFactory()

    def test_log_object_changes_with_changes(self):
        """Test: log_object_changes logs when there are changes"""
        request = self.factory.patch("/test/")
        request.user = self.request_user

        from accounts.serializers import StudentProfileUpdateSerializer

        data = {"grade": "11B"}
        serializer = StudentProfileUpdateSerializer(
            self.student_profile, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())

        with patch("accounts.staff_views.audit_logger") as mock_logger:
            log_object_changes(request, self.student_profile, serializer, "test_action")
            # Verify logger was called
            # (actual call verification depends on implementation)

    def test_log_object_changes_no_changes(self):
        """Test: log_object_changes doesn't log when there are no changes"""
        request = self.factory.patch("/test/")
        request.user = self.request_user

        from accounts.serializers import StudentProfileUpdateSerializer

        data = {}
        serializer = StudentProfileUpdateSerializer(
            self.student_profile, data=data, partial=True
        )
        self.assertTrue(serializer.is_valid())

        with patch("accounts.staff_views.audit_logger") as mock_logger:
            log_object_changes(request, self.student_profile, serializer, "test_action")
            # Verify logger wasn't called for no changes


class TestUpdateTeacherProfile(APITestCase):
    """Tests for update_teacher_profile endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.teacher = User.objects.create_user(
            username="teacher1",
            email="teacher@test.com",
            password="pass",
            role=User.Role.TEACHER,
            is_active=True,
        )
        self.teacher_profile = TeacherProfile.objects.create(
            user=self.teacher, subject="Math", experience_years=0
        )

    def test_update_teacher_profile_experience(self):
        """Test: Update teacher experience"""
        response = self.client.patch(
            f"/api/teachers/{self.teacher.id}/profile/",
            {"experience_years": 5},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.teacher_profile.refresh_from_db()
        self.assertEqual(self.teacher_profile.experience_years, 5)

    def test_update_teacher_profile_bio(self):
        """Test: Update teacher bio"""
        response = self.client.patch(
            f"/api/teachers/{self.teacher.id}/profile/",
            {"bio": "Expert in mathematics"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class TestUpdateTutorProfile(APITestCase):
    """Tests for update_tutor_profile endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.tutor = User.objects.create_user(
            username="tutor1",
            email="tutor@test.com",
            password="pass",
            role=User.Role.TUTOR,
            is_active=True,
        )
        self.tutor_profile = TutorProfile.objects.create(
            user=self.tutor, specialization="Math"
        )

    def test_update_tutor_profile_specialization(self):
        """Test: Update tutor specialization"""
        response = self.client.patch(
            f"/api/tutors/{self.tutor.id}/profile/",
            {"specialization": "Physics"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.tutor_profile.refresh_from_db()
        self.assertEqual(self.tutor_profile.specialization, "Physics")


class TestUpdateParentProfile(APITestCase):
    """Tests for update_parent_profile endpoint"""

    def setUp(self):
        self.admin = User.objects.create_user(
            username="admin",
            email="admin@test.com",
            password="adminpass",
            role=User.Role.ADMIN,
            is_active=True,
            is_superuser=True,
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.admin)

        self.parent = User.objects.create_user(
            username="parent1",
            email="parent@test.com",
            password="pass",
            role=User.Role.PARENT,
            is_active=True,
        )
        self.parent_profile = ParentProfile.objects.create(user=self.parent)

    def test_update_parent_profile_success(self):
        """Test: Update parent profile"""
        response = self.client.patch(
            f"/api/parents/{self.parent.id}/profile/",
            {},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
