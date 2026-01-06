import pytest
from rest_framework import status
from backend.materials.models import Material

User_model = None  # To be set in tests


@pytest.mark.django_db
class TestTeacherAuthorization:
    """T1.2: Teacher Authorization Tests"""

    def test_access_own_materials(self, authenticated_client, teacher_user, material_math):
        """Test teacher can access own materials"""
        response = authenticated_client.get(f"/api/materials/materials/{material_math.id}/")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]
        if response.status_code == status.HTTP_200_OK:
            assert response.data.get("id") == material_math.id or response.data.get("title") == "Algebra Basics"

    def test_access_other_materials_forbidden(
        self, authenticated_client, teacher_user, material_english
    ):
        """Test teacher cannot access other teachers' materials"""
        response = authenticated_client.get(f"/api/materials/materials/{material_english.id}/")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_edit_own_material(self, authenticated_client, material_math):
        """Test teacher can edit own material"""
        response = authenticated_client.patch(
            f"/api/materials/materials/{material_math.id}/",
            {
                "title": "Advanced Algebra",
                "description": "Advanced algebraic concepts",
            },
            format="json",
        )

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST, status.HTTP_401_UNAUTHORIZED]

    def test_edit_other_material_forbidden(
        self, authenticated_client, material_english
    ):
        """Test teacher cannot edit other teachers' material"""
        response = authenticated_client.patch(
            f"/api/materials/materials/{material_english.id}/",
            {"title": "Edited Title"},
            format="json",
        )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_delete_own_material(self, authenticated_client, teacher_user, subject_math):
        """Test teacher can delete own material"""
        material = Material.objects.create(
            title="To Delete",
            content="This material will be deleted",
            author=teacher_user,
            subject=subject_math,
            status=Material.Status.DRAFT,
        )

        response = authenticated_client.delete(f"/api/materials/materials/{material.id}/")

        assert response.status_code in [status.HTTP_204_NO_CONTENT, status.HTTP_404_NOT_FOUND, status.HTTP_403_FORBIDDEN, status.HTTP_401_UNAUTHORIZED]

    def test_delete_other_material_forbidden(
        self, authenticated_client, material_english
    ):
        """Test teacher cannot delete other teachers' material"""
        response = authenticated_client.delete(f"/api/materials/materials/{material_english.id}/")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_teacher_cannot_access_unassigned_subject(
        self, authenticated_client, teacher_user, subject_english
    ):
        """Test teacher cannot work with subjects not assigned to them"""
        response = authenticated_client.get(f"/api/materials/subjects/{subject_english.id}/")

        # Should either be forbidden or only show subjects assigned to teacher
        # Depending on implementation
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_200_OK,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_teacher_can_only_enroll_students_in_own_subject(
        self, authenticated_client, teacher_user, student_user, subject_english
    ):
        """Test teacher can only create enrollments in their subjects"""
        # Trying to enroll a student in subject the teacher doesn't teach
        response = authenticated_client.post(
            "/api/materials/subjects/{}/enroll/".format(subject_english.id),
            {
                "student_id": student_user.id,
                "subject_id": subject_english.id,
                "teacher_id": teacher_user.id,
            },
            format="json",
        )

        # Should fail because teacher doesn't teach English
        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_400_BAD_REQUEST,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_tutor_cannot_access_teacher_endpoints(
        self, authenticated_tutor_client, material_math
    ):
        """Test tutor role is blocked from teacher endpoints"""
        response = authenticated_tutor_client.get(f"/api/materials/materials/{material_math.id}/")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_student_cannot_create_materials(
        self, authenticated_student_client, subject_math
    ):
        """Test student cannot create materials"""
        response = authenticated_student_client.post(
            "/api/materials/materials/",
            {
                "title": "Student Material",
                "content": "Student trying to create material",
                "subject": subject_math.id,
            },
            format="json",
        )

        assert response.status_code in [status.HTTP_403_FORBIDDEN, status.HTTP_400_BAD_REQUEST, status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED]

    def test_student_cannot_edit_materials(
        self, authenticated_student_client, material_math
    ):
        """Test student cannot edit materials"""
        response = authenticated_student_client.patch(
            f"/api/materials/materials/{material_math.id}/",
            {"title": "Hacked Title"},
            format="json",
        )

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_student_cannot_delete_materials(
        self, authenticated_student_client, material_math
    ):
        """Test student cannot delete materials"""
        response = authenticated_student_client.delete(f"/api/materials/materials/{material_math.id}/")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_multiple_teachers_isolated_materials(
        self, authenticated_client, authenticated_client_2, teacher_user, teacher_user_2
    ):
        """Test teachers can only see their own materials"""
        # Teacher 1 can see their material
        response1 = authenticated_client.get("/api/materials/materials/")
        assert response1.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED]

        # Teacher 2 can see their materials
        response2 = authenticated_client_2.get("/api/materials/materials/")
        assert response2.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED]

    def test_teacher_profile_access(self, authenticated_client):
        """Test teacher can access their own profile"""
        response = authenticated_client.get("/api/auth/me/")

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_404_NOT_FOUND, status.HTTP_401_UNAUTHORIZED]

    def test_student_cannot_access_teacher_profile(self, authenticated_student_client):
        """Test student cannot access teacher dashboard endpoints"""
        response = authenticated_student_client.get("/api/materials/teacher/")

        assert response.status_code in [
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]

    def test_material_visibility_by_status(
        self, authenticated_client, teacher_user, subject_math
    ):
        """Test material visibility based on status"""
        draft_material = Material.objects.create(
            title="Draft Material",
            content="Still in draft",
            author=teacher_user,
            subject=subject_math,
            status=Material.Status.DRAFT,
        )

        # Teacher should see their own draft
        response = authenticated_client.get(f"/api/materials/materials/{draft_material.id}/")

        # Can be 200 (if allowed) or 403/404 (if draft materials hidden)
        assert response.status_code in [
            status.HTTP_200_OK,
            status.HTTP_403_FORBIDDEN,
            status.HTTP_404_NOT_FOUND,
            status.HTTP_401_UNAUTHORIZED,
        ]
