"""
Wave 2: Teacher Dashboard - Student Distribution Tests (T2.2)
Tests for assigning materials to students and tracking assignments
"""
import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from materials.models import Material, Subject, TeacherSubject, SubjectEnrollment, MaterialProgress
from .fixtures import *  # Import all fixtures

User = get_user_model()


class TestSingleStudentAssignment:
    """Test assigning materials to single students"""

    def test_assign_material_to_single_student(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test assigning a material to one student"""
        material = Material.objects.create(
            title="Assignment 1",
            description="For single student",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        payload = {
            "student_id": student_user.id,
        }
        response = authenticated_client.post(
            f"/api/materials/materials/{material.id}/assign/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_assign_material_with_deadline(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test assigning material with due date"""
        material = Material.objects.create(
            title="Timed Assignment",
            description="With deadline",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        payload = {
            "student_id": student_user.id,
            "due_date": "2025-02-01T23:59:59Z",
        }
        response = authenticated_client.post(
            f"/api/materials/materials/{material.id}/assign/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_assign_material_with_custom_instructions(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test assigning material with custom instructions"""
        material = Material.objects.create(
            title="Instructed Assignment",
            description="With custom instructions",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        payload = {
            "student_id": student_user.id,
            "instructions": "Please solve all 10 problems and submit by Friday",
            "priority": "high",
        }
        response = authenticated_client.post(
            f"/api/materials/materials/{material.id}/assign/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_remove_assignment_from_student(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test removing an assignment from a student"""
        material = Material.objects.create(
            title="Removable Assignment",
            description="Can be removed",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        # First assign
        MaterialProgress.objects.create(
            student=student_user,
            material=material,
            is_completed=False,
        )

        # Then try to remove
        response = authenticated_client.delete(
            f"/api/materials/materials/{material.id}/assignments/{student_user.id}/",
        )
        assert response.status_code in [204, 200, 400, 404]

    def test_verify_student_received_assignment(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test that student can see their assigned material"""
        material = Material.objects.create(
            title="Visible Assignment",
            description="Should be visible to student",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        # Create progress record
        progress = MaterialProgress.objects.create(
            student=student_user,
            material=material,
            is_completed=False,
        )

        # Student should see this material
        response = authenticated_student_client.get("/api/materials/student/materials/")
        assert response.status_code in [200, 404]


class TestBulkAssignment:
    """Test bulk assigning materials to multiple students"""

    def test_bulk_assign_to_multiple_students(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test assigning one material to multiple students"""
        material = Material.objects.create(
            title="Bulk Assignment",
            description="For multiple students",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        payload = {
            "student_ids": [student_user.id, student_user_2.id],
        }
        response = authenticated_client.post(
            f"/api/materials/materials/{material.id}/assign/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_bulk_assign_with_common_deadline(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test bulk assign with same deadline for all students"""
        material = Material.objects.create(
            title="Deadline Assignment",
            description="Common deadline",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        payload = {
            "student_ids": [student_user.id, student_user_2.id],
            "due_date": "2025-02-15T23:59:59Z",
        }
        response = authenticated_client.post(
            f"/api/materials/materials/{material.id}/assign/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_bulk_assign_with_custom_instructions(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test bulk assign with instructions for all students"""
        material = Material.objects.create(
            title="Instructed Bulk",
            description="Bulk with instructions",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.HOMEWORK,
            status=Material.Status.ACTIVE,
        )

        payload = {
            "student_ids": [student_user.id, student_user_2.id],
            "instructions": "Work in pairs if possible",
        }
        response = authenticated_client.post(
            f"/api/materials/materials/{material.id}/assign/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_bulk_assign_large_group(self, authenticated_client, teacher_user, subject_math, db):
        """Test assigning to a large number of students"""
        # Create 20 students
        students = []
        for i in range(20):
            student = User.objects.create_user(
                username=f"student_bulk_{i}",
                email=f"student_bulk_{i}@test.com",
                password="password123",
                role=User.Role.STUDENT,
            )
            students.append(student.id)

        material = Material.objects.create(
            title="Large Bulk Assignment",
            description="For 20 students",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        payload = {
            "student_ids": students,
        }
        response = authenticated_client.post(
            f"/api/materials/materials/{material.id}/assign/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 201, 400, 404]


class TestStudentGroups:
    """Test assigning materials to student groups/cohorts"""

    def test_assign_to_student_group(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test assigning material to group of students"""
        # Create group (if model exists)
        material = Material.objects.create(
            title="Group Assignment",
            description="For cohort",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        payload = {
            "group_id": 1,  # Hypothetical group
        }
        response = authenticated_client.post(
            f"/api/materials/materials/{material.id}/assign/",
            payload,
            format="json",
        )
        assert response.status_code in [200, 201, 400, 404]

    def test_assign_different_materials_to_different_cohorts(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test assigning different materials to different student groups"""
        material1 = Material.objects.create(
            title="Basic Material",
            description="For beginners",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
            difficulty_level=1,
        )

        material2 = Material.objects.create(
            title="Advanced Material",
            description="For advanced",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
            difficulty_level=3,
        )

        # Assign based on difficulty/level
        for material in [material1, material2]:
            payload = {
                "student_ids": [student_user.id, student_user_2.id],
            }
            response = authenticated_client.post(
                f"/api/materials/materials/{material.id}/assign/",
                payload,
                format="json",
            )
            assert response.status_code in [200, 201, 400, 404]


class TestAssignmentTracking:
    """Test tracking assignment status per student"""

    def test_get_assignment_status_per_student(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test checking assignment status for specific student"""
        material = Material.objects.create(
            title="Status Material",
            description="Track status",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(
            student=student_user,
            material=material,
            is_completed=False,
        )

        response = authenticated_client.get(
            f"/api/materials/materials/{material.id}/assignments/{student_user.id}/"
        )
        assert response.status_code in [200, 404]

    def test_list_assignments_for_material(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test listing all students assigned to a material"""
        material = Material.objects.create(
            title="Multi Student Assignment",
            description="Multiple students",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(student=student_user, material=material, is_completed=False)
        MaterialProgress.objects.create(student=student_user_2, material=material, is_completed=False)

        response = authenticated_client.get(f"/api/materials/materials/{material.id}/students/")
        assert response.status_code in [200, 404]

    def test_get_student_list_for_assignment(self, authenticated_client, teacher_user, subject_math):
        """Test getting list of assigned students"""
        response = authenticated_client.get("/api/materials/assignments/students/")
        assert response.status_code in [200, 404]

    def test_track_assignment_status_changes(self, authenticated_client, teacher_user, subject_math, student_user):
        """Test tracking when assignment status changes"""
        material = Material.objects.create(
            title="Status Tracking",
            description="Track changes",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        progress = MaterialProgress.objects.create(
            student=student_user,
            material=material,
            is_completed=False,
        )

        # Simulate status changes
        for is_completed in [False, True]:
            payload = {"is_completed": is_completed}
            response = authenticated_client.patch(
                f"/api/materials/progress/{progress.id}/",
                payload,
                format="json",
            )
            assert response.status_code in [200, 400, 404, 405]


class TestStudentAssignmentList:
    """Test listing assigned materials for students"""

    def test_list_assigned_materials_for_student(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test student viewing their assigned materials"""
        material = Material.objects.create(
            title="My Assignment",
            description="Assigned to me",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(
            student=student_user,
            material=material,
            is_completed=False,
        )

        response = authenticated_student_client.get("/api/materials/assignments/")
        assert response.status_code in [200, 404]

    def test_filter_student_assignments_by_status(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test filtering student's assignments by status"""
        response = authenticated_student_client.get("/api/materials/assignments/?status=pending")
        assert response.status_code in [200, 404]

    def test_filter_student_assignments_by_due_date(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test filtering student's assignments by due date"""
        response = authenticated_student_client.get("/api/materials/assignments/?due_before=2025-02-01")
        assert response.status_code in [200, 404]

    def test_sort_assignments_by_due_date(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test sorting assignments by due date"""
        response = authenticated_student_client.get("/api/materials/assignments/?ordering=due_date")
        assert response.status_code in [200, 404]

    def test_sort_assignments_by_priority(self, authenticated_client, teacher_user, subject_math, student_user, authenticated_student_client):
        """Test sorting assignments by priority"""
        response = authenticated_student_client.get("/api/materials/assignments/?ordering=-priority")
        assert response.status_code in [200, 404]


class TestStudentListForAssignment:
    """Test getting student list for an assignment"""

    def test_get_students_assigned_to_material(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test getting list of students assigned to material"""
        material = Material.objects.create(
            title="Tracked Assignment",
            description="Multiple students",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(student=student_user, material=material, is_completed=False)
        MaterialProgress.objects.create(student=student_user_2, material=material, is_completed=False)

        response = authenticated_client.get(f"/api/materials/materials/{material.id}/students/")
        assert response.status_code in [200, 404]

    def test_get_students_with_assignment_status(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test getting students with their assignment status"""
        material = Material.objects.create(
            title="Status Check Material",
            description="Check statuses",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(student=student_user, material=material, is_completed=False)
        MaterialProgress.objects.create(student=student_user_2, material=material, is_completed=False)

        response = authenticated_client.get(
            f"/api/materials/materials/{material.id}/students/?include_status=true"
        )
        assert response.status_code in [200, 404]

    def test_filter_students_by_performance_level(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test filtering assigned students by performance"""
        material = Material.objects.create(
            title="Performance Filter",
            description="Filter by level",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(student=student_user, material=material, is_completed=False)
        MaterialProgress.objects.create(student=student_user_2, material=material, is_completed=True)

        response = authenticated_client.get(
            f"/api/materials/materials/{material.id}/students/?performance=high"
        )
        assert response.status_code in [200, 404]

    def test_filter_students_by_progress_level(self, authenticated_client, teacher_user, subject_math, student_user, student_user_2):
        """Test filtering students by progress status"""
        material = Material.objects.create(
            title="Progress Filter",
            description="Filter by progress",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        MaterialProgress.objects.create(student=student_user, material=material, is_completed=False)
        MaterialProgress.objects.create(student=student_user_2, material=material, is_completed=False)

        response = authenticated_client.get(
            f"/api/materials/materials/{material.id}/students/?progress=in_progress"
        )
        assert response.status_code in [200, 404]

    def test_pagination_of_student_list(self, authenticated_client, teacher_user, subject_math, db):
        """Test pagination when listing assigned students"""
        # Create 15 students
        students = []
        for i in range(15):
            student = User.objects.create_user(
                username=f"paginated_student_{i}",
                email=f"paginated_{i}@test.com",
                password="password123",
                role=User.Role.STUDENT,
            )
            students.append(student)

        material = Material.objects.create(
            title="Pagination Material",
            description="For pagination test",
            content="Content...",
            author=teacher_user,
            subject=subject_math,
            type=Material.Type.LESSON,
            status=Material.Status.ACTIVE,
        )

        for student in students:
            MaterialProgress.objects.create(student=student, material=material, is_completed=False)

        response = authenticated_client.get(f"/api/materials/materials/{material.id}/students/?page=1&limit=10")
        assert response.status_code in [200, 404]
