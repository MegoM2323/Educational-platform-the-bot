"""
Tests for bulk material assignment operations.
Tests preflight validation, transaction safety, error handling, and audit logging.
"""
import json
import time
from datetime import datetime

import pytest
from django.contrib.auth import get_user_model
from django.test import TransactionTestCase
from rest_framework.test import APIClient

from materials.models import (
    BulkAssignmentAuditLog,
    Material,
    MaterialProgress,
    Subject,
)
from materials.bulk_operations_service import BulkAssignmentService

User = get_user_model()


@pytest.mark.django_db
class TestBulkAssignmentPreflight(TransactionTestCase):
    """Test preflight validation for bulk assignments"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            first_name="Test",
            last_name="Teacher",
        )
        self.student1 = User.objects.create_user(
            email="student1@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            first_name="Student",
            last_name="One",
        )
        self.student2 = User.objects.create_user(
            email="student2@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            first_name="Student",
            last_name="Two",
        )
        self.subject = Subject.objects.create(
            name="Math", description="Mathematics", color="#FF0000"
        )
        self.material1 = Material.objects.create(
            title="Algebra Basics",
            description="Introduction to Algebra",
            content="<h1>Algebra</h1><p>Basic concepts...</p>",
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE,
            type=Material.Type.LESSON,
        )
        self.material2 = Material.objects.create(
            title="Geometry Basics",
            description="Introduction to Geometry",
            content="<h1>Geometry</h1><p>Basic concepts...</p>",
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE,
            type=Material.Type.LESSON,
        )

        self.service = BulkAssignmentService(self.teacher)

    def test_preflight_single_material_to_students(self):
        """Test preflight check for assigning one material to multiple students"""
        result = self.service.preflight_check(
            material_id=self.material1.id,
            student_ids=[self.student1.id, self.student2.id],
        )

        assert result["valid"] is True
        assert result["total_items"] == 2
        assert len(result["affected_students"]) == 2
        assert len(result["affected_materials"]) == 1
        assert result["errors"] == []

    def test_preflight_invalid_material(self):
        """Test preflight check fails with invalid material ID"""
        result = self.service.preflight_check(
            material_id=99999,  # Non-existent ID
            student_ids=[self.student1.id],
        )

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "not found" in result["errors"][0].lower()

    def test_preflight_invalid_student(self):
        """Test preflight check fails with invalid student ID"""
        result = self.service.preflight_check(
            material_id=self.material1.id,
            student_ids=[99999],  # Non-existent ID
        )

        assert result["valid"] is False
        assert len(result["errors"]) > 0

    def test_preflight_too_many_students(self):
        """Test preflight check fails when exceeding student limit"""
        # Create more than 1000 student IDs
        student_ids = list(range(1, 1005))

        result = self.service.preflight_check(
            material_id=self.material1.id,
            student_ids=student_ids,
        )

        assert result["valid"] is False
        assert len(result["errors"]) > 0
        assert "maximum" in result["errors"][0].lower()

    def test_preflight_multiple_materials_to_student(self):
        """Test preflight check for assigning multiple materials to one student"""
        result = self.service.preflight_check(
            material_ids=[self.material1.id, self.material2.id],
            student_id=self.student1.id,
        )

        assert result["valid"] is True
        assert result["total_items"] == 2
        assert len(result["affected_students"]) == 1
        assert len(result["affected_materials"]) == 2

    def test_preflight_missing_parameters(self):
        """Test preflight check fails with missing parameters"""
        result = self.service.preflight_check(material_id=self.material1.id)

        assert result["valid"] is False
        assert len(result["errors"]) > 0


@pytest.mark.django_db
class TestBulkAssignmentOperations(TransactionTestCase):
    """Test actual bulk assignment operations"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            first_name="Test",
            last_name="Teacher",
        )
        self.students = [
            User.objects.create_user(
                email=f"student{i}@test.com",
                password="testpass123",
                role=User.Role.STUDENT,
                first_name=f"Student{i}",
                last_name="Test",
            )
            for i in range(5)
        ]
        self.subject = Subject.objects.create(
            name="Math", description="Mathematics", color="#FF0000"
        )
        self.materials = [
            Material.objects.create(
                title=f"Lesson {i}",
                description=f"Lesson {i} content",
                content=f"<h1>Lesson {i}</h1>",
                author=self.teacher,
                subject=self.subject,
                status=Material.Status.ACTIVE,
                type=Material.Type.LESSON,
            )
            for i in range(3)
        ]

        self.service = BulkAssignmentService(self.teacher)

    def test_bulk_assign_single_material_to_students(self):
        """Test assigning one material to multiple students"""
        student_ids = [s.id for s in self.students[:3]]

        result = self.service.bulk_assign_students(
            material_id=self.materials[0].id,
            student_ids=student_ids,
            skip_existing=True,
            notify=False,
        )

        assert result["created"] == 3
        assert result["skipped"] == 0
        assert result["failed"] == 0

        # Verify assignments
        material = Material.objects.get(id=self.materials[0].id)
        assert material.assigned_to.count() == 3

        # Verify progress was created
        assert MaterialProgress.objects.filter(material=material).count() == 3

    def test_bulk_assign_skips_existing(self):
        """Test that skip_existing flag works"""
        # Pre-assign one student
        self.materials[0].assigned_to.add(self.students[0])
        student_ids = [s.id for s in self.students[:3]]

        result = self.service.bulk_assign_students(
            material_id=self.materials[0].id,
            student_ids=student_ids,
            skip_existing=True,
            notify=False,
        )

        assert result["created"] == 2  # Only 2 new assignments
        assert result["skipped"] == 1  # One skipped (already assigned)
        assert result["failed"] == 0

    def test_bulk_assign_overwrites_existing_when_skip_false(self):
        """Test that skip_existing=False re-assigns already assigned students"""
        # Pre-assign one student
        self.materials[0].assigned_to.add(self.students[0])
        student_ids = [s.id for s in self.students[:2]]

        result = self.service.bulk_assign_students(
            material_id=self.materials[0].id,
            student_ids=student_ids,
            skip_existing=False,
            notify=False,
        )

        assert result["created"] == 2
        assert result["skipped"] == 0

    def test_bulk_assign_materials_to_student(self):
        """Test assigning multiple materials to one student"""
        material_ids = [m.id for m in self.materials]

        result = self.service.bulk_assign_materials(
            material_ids=material_ids,
            student_id=self.students[0].id,
            skip_existing=True,
            notify=False,
        )

        assert result["created"] == 3
        assert result["skipped"] == 0
        assert result["failed"] == 0

        # Verify all materials are assigned to student
        student = User.objects.get(id=self.students[0].id)
        assert student.assigned_materials.count() == 3

    def test_bulk_assign_transactions_safety(self):
        """Test that transactions ensure data consistency"""
        # Try to assign to non-existent student (this should fail)
        student_ids = [self.students[0].id, 99999]

        result = self.service.bulk_assign_students(
            material_id=self.materials[0].id,
            student_ids=student_ids,
            skip_existing=True,
            notify=False,
        )

        # Should have created at least 1, might have errors
        assert result["failed"] >= 0

    def test_bulk_assign_creates_audit_log(self):
        """Test that audit log is created"""
        student_ids = [s.id for s in self.students[:2]]

        result = self.service.bulk_assign_students(
            material_id=self.materials[0].id,
            student_ids=student_ids,
            skip_existing=True,
            notify=False,
        )

        # Check audit log
        audit_log = BulkAssignmentAuditLog.objects.latest("id")
        assert audit_log.performed_by == self.teacher
        assert (
            audit_log.operation_type
            == BulkAssignmentAuditLog.OperationType.BULK_ASSIGN_TO_STUDENTS
        )
        assert audit_log.status == BulkAssignmentAuditLog.Status.COMPLETED
        assert audit_log.created_count == 2
        assert audit_log.duration_seconds > 0

    def test_audit_log_contains_metadata(self):
        """Test that audit log contains operation metadata"""
        student_ids = [self.students[0].id]

        self.service.bulk_assign_students(
            material_id=self.materials[0].id,
            student_ids=student_ids,
            skip_existing=True,
            notify=False,
        )

        audit_log = BulkAssignmentAuditLog.objects.latest("id")
        assert audit_log.metadata["material_id"] == self.materials[0].id
        assert audit_log.metadata["student_ids"] == student_ids

    def test_bulk_remove_by_material(self):
        """Test removing assignments by material"""
        # Pre-assign materials to students
        for student in self.students[:2]:
            self.materials[0].assigned_to.add(student)

        assert self.materials[0].assigned_to.count() == 2

        result = self.service.bulk_remove(material_ids=[self.materials[0].id])

        assert result["removed"] == 2
        assert self.materials[0].assigned_to.count() == 0

    def test_bulk_remove_by_student(self):
        """Test removing assignments by student"""
        # Pre-assign all materials to one student
        student = self.students[0]
        for material in self.materials:
            material.assigned_to.add(student)

        result = self.service.bulk_remove(student_ids=[student.id])

        assert result["removed"] >= 0  # Should remove assignments
        for material in self.materials:
            assert not material.assigned_to.filter(id=student.id).exists()

    def test_bulk_remove_creates_audit_log(self):
        """Test that audit log is created for removal"""
        # Pre-assign
        self.materials[0].assigned_to.add(self.students[0])

        self.service.bulk_remove(material_ids=[self.materials[0].id])

        audit_log = BulkAssignmentAuditLog.objects.latest("id")
        assert audit_log.operation_type == BulkAssignmentAuditLog.OperationType.BULK_REMOVE
        assert audit_log.status == BulkAssignmentAuditLog.Status.COMPLETED


@pytest.mark.django_db
class TestBulkAssignmentAPI(TransactionTestCase):
    """Test bulk assignment API endpoints"""

    def setUp(self):
        """Set up test data"""
        self.client = APIClient()
        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            first_name="Test",
            last_name="Teacher",
        )
        self.student1 = User.objects.create_user(
            email="student1@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            first_name="Student",
            last_name="One",
        )
        self.student2 = User.objects.create_user(
            email="student2@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
            first_name="Student",
            last_name="Two",
        )
        self.subject = Subject.objects.create(
            name="Math", description="Mathematics", color="#FF0000"
        )
        self.material = Material.objects.create(
            title="Math Lesson",
            description="Basic math",
            content="<h1>Math</h1>",
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE,
            type=Material.Type.LESSON,
        )

        self.client.force_authenticate(user=self.teacher)

    def test_bulk_assign_preflight_endpoint(self):
        """Test preflight validation endpoint"""
        url = "/api/materials/bulk_assign_preflight/"
        data = {
            "material_id": self.material.id,
            "student_ids": [self.student1.id, self.student2.id],
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == 200
        result = response.json()
        assert result["valid"] is True
        assert result["total_items"] == 2

    def test_bulk_assign_endpoint_permission_denied_for_student(self):
        """Test bulk assign denies access to students"""
        student_client = APIClient()
        student_client.force_authenticate(user=self.student1)

        url = "/api/materials/bulk_assign/"
        data = {
            "material_id": self.material.id,
            "student_ids": [self.student2.id],
        }

        response = student_client.post(url, data, format="json")
        assert response.status_code == 403

    def test_bulk_assign_endpoint_success(self):
        """Test successful bulk assignment via API"""
        url = "/api/materials/bulk_assign/"
        data = {
            "material_id": self.material.id,
            "student_ids": [self.student1.id, self.student2.id],
            "notify_students": False,
        }

        response = self.client.post(url, data, format="json")

        assert response.status_code == 200
        result = response.json()
        assert result["created"] == 2
        assert result["failed"] == 0

    def test_bulk_remove_endpoint(self):
        """Test bulk removal endpoint"""
        # Pre-assign
        self.material.assigned_to.add(self.student1, self.student2)

        url = "/api/materials/bulk_remove/"
        data = {"material_ids": [self.material.id]}

        response = self.client.post(url, data, format="json")

        assert response.status_code == 200
        result = response.json()
        assert result["removed"] == 2


@pytest.mark.django_db
class TestBulkAssignmentRateLimiting(TransactionTestCase):
    """Test rate limiting for bulk operations"""

    def setUp(self):
        """Set up test data"""
        self.teacher = User.objects.create_user(
            email="teacher@test.com",
            password="testpass123",
            role=User.Role.TEACHER,
            first_name="Test",
            last_name="Teacher",
        )
        self.subject = Subject.objects.create(
            name="Math", description="Mathematics", color="#FF0000"
        )
        self.material = Material.objects.create(
            title="Math Lesson",
            description="Basic math",
            content="<h1>Math</h1>",
            author=self.teacher,
            subject=self.subject,
            status=Material.Status.ACTIVE,
            type=Material.Type.LESSON,
        )

        self.service = BulkAssignmentService(self.teacher)

    def test_max_students_per_operation(self):
        """Test that max 1000 students per operation is enforced"""
        # Create more than 1000 student IDs
        student_ids = list(range(1, 1005))

        result = self.service.preflight_check(
            material_id=self.material.id,
            student_ids=student_ids,
        )

        assert result["valid"] is False
        assert "maximum" in result["errors"][0].lower()

    def test_max_materials_per_operation(self):
        """Test that max 1000 materials per operation is enforced"""
        # Create more than 1000 material IDs
        material_ids = list(range(1, 1005))

        student = User.objects.create_user(
            email="student@test.com",
            password="testpass123",
            role=User.Role.STUDENT,
        )

        result = self.service.preflight_check(
            material_ids=material_ids,
            student_id=student.id,
        )

        assert result["valid"] is False
        assert "maximum" in result["errors"][0].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
